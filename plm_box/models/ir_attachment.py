# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2017 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Created on Mar 8, 2017
@author: daniel
"""
import base64
import csv
import datetime
import json
import logging
import os
import pytz

from dateutil import parser

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT,
)


def correctDate(fromTimeStr, context):
    serverUtcTime = parser.parse(fromTimeStr.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
    utcDate = serverUtcTime.replace(tzinfo=pytz.utc).astimezone(
        pytz.timezone(context.get("tz", "Europe/Rome"))
    )
    return utcDate.replace(tzinfo=None)


class Plm_box_document(models.Model):
    _inherit = "ir.attachment"

    name = fields.Char(_("Attachment Name"), required=False)
    is_plm_box = fields.Boolean("Is Plm Box document")
    plm_box_id = fields.Many2one("plm.box")

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if not val.get("name", False):
                name = self.getNewSequencedName()
                val["name"] = name
        return super(Plm_box_document, self).create(vals)

    def getCheckOutUser(self):
        for checkOutBrws in self._getCheckOutUser():
            if checkOutBrws:
                return checkOutBrws.name
        return ""

    @api.model
    def getUserNameFromId(self, userId):
        userBrws = self.env.get("res.users").browse(userId)
        if not userBrws:
            logging.warning(
                "[getUserNameFromId] Couldn able to find user name with id %r"
                % (userId)
            )
            return ""
        return userBrws.name

    @api.model
    def getNewSequencedName(self):
        return self.env.get("ir.sequence").next_by_code("ir.attachment")

    @api.model
    def getFilesFromName(self, vals):
        docName, docRevision = vals
        docIds = self.search(
            [("name", "=", docName), ("engineering_revision", "=", docRevision)]
        ).ids
        if docIds:
            files = self.GetSomeFiles((docIds, [[], []], False))
            if files:
                files[0] = list(files[0])
                files[0][0] = docName
                return files

    @api.model
    def checkInOrFalse(self, docDict):
        docName = docDict.get("name", "")
        docRev = docDict.get("engineering_revision", "")
        docContent = docDict.get("fileContent", "")
        force = docDict.get("force", False)
        docBrowseList = self.search([("name", "=", docName)])
        if docBrowseList and not force:
            clientBytesContent = docContent.encode(encoding="utf_8", errors="strict")
            if (
                docBrowseList[0].datas + "\n".encode(encoding="utf_8", errors="strict")
                != clientBytesContent
            ):
                return "File changed"
        docIds = self.search(
            [("name", "=", docName), ("engineering_revision", "=", docRev)]
        ).ids
        if len(docIds) == 1:
            chckOutDocs = self.env.get("plm.checkout").search(
                [("documentid", "=", docIds[0]), ("userid", "=", self.env.uid)]
            )
            chckOutDocs.unlink()
            return True
        return False

    @api.model
    def checkOutOrFalse(self, docDict):
        docName = docDict.get("name", "")
        docRev = docDict.get("engineering_revision", "")
        plmCheckOutObj = self.env.get("plm.checkout")
        docBrwsList = self.search(
            [("name", "=", docName), ("engineering_revision", "=", docRev)]
        )
        for docBrws in docBrwsList:
            docState = docBrws.engineering_state
            docId = docBrws.id
            if not docState or docState != "draft":
                return False
            if plmCheckOutObj.search(
                [("documentid", "=", docId), ("userid", "=", self.env.uid)]
            ):
                return True
            res = plmCheckOutObj.create({"documentid": docId, "userid": self.env.uid})
            if res:
                return True
        return False

    @api.model
    def saveBoxDocRel(self, box_id, doc_id):
        boxObj = self.env.get("plm.box")
        for boxBrws in boxObj.search([("id", "=", box_id)]):
            if doc_id:
                boxBrws.write({"document_rel": [(4, doc_id)]})
                return True
        return False

    @api.model
    def updateDocValues(self, valuesDict):
        docBrwsList = self.search([("name", "=", valuesDict.get("docName", ""))])
        for docBrws in docBrwsList:
            del valuesDict["docName"]
            if docBrws.write(valuesDict):
                writeVal = datetime.datetime.strptime(
                    docBrws.write_date, DEFAULT_SERVER_DATETIME_FORMAT
                )
                return correctDate(writeVal, self.env.context)
        return False

    @api.model
    def returnDocsOfFilesChanged(self, valuesDict):
        outDocs = []
        for docName, (docContent, _writeDateClient) in valuesDict.items():
            for ir_attachment_id in self.search([("name", "=", docName)]):
                if (
                    ir_attachment_id.datas != docContent
                    and ir_attachment_id.getDocumentState() == "check-out-by-me"
                ):
                    outDocs.append(docName)
        return outDocs

    def getDocumentState(self):
        self.ensure_one()
        checkedOutByMe = self._is_checkedout_for_me()
        checkedIn = self.ischecked_in()
        if checkedOutByMe:
            return "check-out-by-me"
        if checkedIn:
            return "check-in"
        else:
            return "check-out"

    @api.model
    def checkDocumentPresent(self, doc_dict={}):
        for str_box_id, vals in doc_dict.items():
            box_id = int(str_box_id)
            box_brws = self.env["plm.box"].browse(box_id)
            for str_doc_id, doc_vals in vals.items():
                doc_id = int(str_doc_id)
                for doc_brws in self.search([("id", "=", doc_id)]):
                    checksum = doc_vals.get("checksum", "")
                    doc_dict[str_box_id][str_doc_id][
                        "check_mode"
                    ] = doc_brws.getDocumentState()
                    if doc_id in box_brws.document_rel.ids:
                        if not checksum:
                            doc_dict[str_box_id][str_doc_id]["update"] = "download"
                        elif doc_brws.checksum != checksum:
                            doc_condition = doc_brws.getDocumentState()
                            if doc_condition == "check-out-by-me":
                                doc_dict[str_box_id][str_doc_id]["update"] = "upload"
                            else:
                                doc_dict[str_box_id][str_doc_id]["update"] = "download"
                        else:
                            doc_dict[str_box_id][str_doc_id]["update"] = "none"
                    else:
                        cad_opens = self.env["plm.cad.open"].search(
                            [("document_id", "=", doc_id)]
                        )
                        if len(cad_opens.ids) > 1:
                            doc_dict[str_box_id][str_doc_id]["update"] = "delete"
                        elif doc_brws:
                            doc_dict[str_box_id][str_doc_id]["update"] = "delete"
                        else:
                            doc_dict[str_box_id][str_doc_id]["update"] = "upload"
        logging.info("Box sincronize res %r" % (doc_dict))
        return doc_dict

    def getDocumentStateMulty(self):
        ret = {}
        for doc in self:
            ret[str(doc.id)] = doc.getDocumentState()
        return ret

    @api.model
    def import_bom_from_csv(self, box_id, doc_id):
        """
        This method processes a CSV file attached to a specific box, extracts
        product details, and creates BOM and BOM lines based on the column mapping defined
        in the box.

        Args:
        box_id (int): The ID of the PLM box containing the CSV structure mapping.
        doc_id (int): The ID of the attachment (CSV file) to be processed.

        Sample :
        clientArgs formate should be
        (
             # parentOdooTuple
            (l_tree_document_id, parent_product_product_id, parent_ir_attachment_id),
            # childrenOdooTuple
            [
                (child_product_product_id_1, child_ir_attachment_id_1, {'product_qty': 2, 'link_kind': 'HiTree'}),
                (child_product_product_id_2, child_ir_attachment_id_2, {'product_qty': 1, 'link_kind': 'RfTree'}),
                # Add more child tuples as needed
            ]
        )
        """

        if doc_id and box_id:
            attachment_id = self.env["ir.attachment"].browse(doc_id)
            box_id = self.env["plm.box"].browse(box_id)
            product_details = self.parse_file_name(attachment_id.name)
            if product_details and product_details.get("prefix") == "IMP_BOM":
                product_id = self.product_by_engcode(product_details.get("part_number"),
                                                     product_details.get("revision"))
                csv_column_mapping = json.loads(box_id.csv_structure)
                file_content = base64.b64decode(attachment_id.datas)
                csv_reader = csv.reader(file_content.decode("utf-8").splitlines())
                headers = next(csv_reader)
                child_data = []
                for row in csv_reader:
                    bom_line_data = {}
                    for odoo_field, csv_column in csv_column_mapping.items():
                        if csv_column in headers:
                            index = headers.index(csv_column)
                            bom_line_data[odoo_field] = row[index]
                    child_data.append(self.create_bom_line_data(bom_line_data,
                                                                product_id,
                                                                attachment_id))
                clientArgs = ((False, product_id.id, attachment_id.id), child_data)
                self.env['mrp.bom'].saveRelationNew(clientArgs)

            return True

    @api.model
    def create_bom_line_data(self, bom_line_data, product_id, attachment_id):
        """
        a custom method will use to prepare BOM line data and return dictionary of
        updated data which will directly use to create BoM line recode.
        """

        if bom_line_data  and product_id and attachment_id:
            line_product_id = self.product_by_engcode(
                engcode=bom_line_data.get("engineering_code"),
                revision=bom_line_data.get("engineering_revision"),
            )

            return [
                line_product_id.id,
                False,
                {'product_qty': bom_line_data.get("qty", 1), 'link_kind': 'HiTree'}
            ]

    @api.model
    def parse_file_name(self, fname):
        """
        a custom method take file name as string and extract details from the file name.
        return product_details dictionary
        """
        if fname.endswith(".csv"):
            parts = fname.split("_")
            if parts[0] == "IMP" or parts[1] == "BOM":
                try:
                    part_number = parts[2]
                    revision = parts[3].split(".")[0]
                except IndexError:
                    return "Invalid file: missing part number or revision"

                return {
                    "prefix": f"{parts[0]}_{parts[1]}",
                    "part_number": part_number,
                    "revision": revision,
                    "file_extension": os.path.splitext(fname)[1],
                }

    @api.model
    def product_by_engcode(self, engcode, revision):
        """
        a custom method takes engcode and revision as parameter and return product_id
        if product not available then create it and return product_id.
        """

        if engcode and revision:
            product_id = self.env["product.product"].search(
                [
                    ("engineering_code", "=", engcode),
                    ("engineering_revision", "=", revision),
                ],
                limit=1,
            )
            if not product_id:
                product_id = self.env["product.product"].create(
                    {
                        "engineering_code": engcode,
                        "name": f"{engcode}_{revision}",
                        "engineering_revision": revision,
                    }
                )
            return product_id
        raise UserError(_("Invalid File Name: missing part number or revision"))
