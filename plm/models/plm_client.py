# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Created on 1 Dec 2021

@author: mboscolo
"""
import hashlib
import json

from odoo import models, fields, api

# SaveStructure
# GetExploseSum
# GetExplose
# GetWhereUsedSum
# GetWhereUsed
# ConvertToPlmProduct
# createOrUpdate
# getLastTime
# SaveOrUpdate
# Clone
# NewRevision
# GetUpdated
# GetLatestIds
# SaveStructure
# getLastTime
# GetNextDocumentName
# Clone
# NewRevision
# GetUpdated
# GetLatestIds
# GetRelatedDocs
# GetLastNamesFromID
# CheckIn
# RegMessage
# CheckSaveUpdate
# SaveOrUpdate
# CheckedIn
# UpdateDocuments
# CleanUp
# getCheckedOut
# SaveStructure
# checkout
# search_read
# getServerTime
# getServerTime
# getRelatedLyTree
# action_confirm
# action_release
# wf_message_post_client
# saveRelationNew
# CheckAllFiles
# getPartOfFile
# isDownloadableFromServer
# GetSomeFiles
# CheckIn2
# CheckInRecursive2
# isLatestRevision
# getUserSign
# QueryLast
# GetSomeFiles
# getNewThreadTransaction
# getErrorMissingDocument
# GetProductDocumentId
# getRelated3DFiles
#
#
# CallCustomFunction
# cleanZipArchives
# checkNewer
# checkUnlinkCadOpen
#
# callCustomMethodNoDisplay
#
# getCustomProcedure
# getMacros
# getMacroUserInfos
# create_server_syncronize
# clientCanIUpload
# notifieDoneToDbThread
# freezeDbThread
# saveSingleLevel
# preCheckInRecursive
# preCheckOutRecursive
#


class PlmClient(models.TransientModel):
    _name = "plm.client"
    _description = "PLM Client Support object"

    def getFileStructure(self, ir_attachemnt_id, hostname, pws_path, latest=False):
        """
        get all the relation of the passed attachment and their status
        :ir_attachment_id int id of object ir_attachment
        :hostname client host name
        :pws_path client pws path
        :return: list of [{<ir_attachment_attrivutes>}]
        """
        out = []
        ir_attachemnt = self.env["ir.attachment"]
        for ir_attachment_id in ir_attachemnt.search([("id", "=", ir_attachemnt_id)]):
            #
            if latest:
                ir_attachment_id = ir_attachment_id.get_latest_version()[0]
            out.extend(ir_attachment_id.computeDownloadStatus(hostname, pws_path))
            #
            if ir_attachment_id.is2D():
                for related_attachment_id in ir_attachment_id.getRelatedLyTreeNew(
                    latest=latest
                ):
                    out.extend(
                        related_attachment_id.computeDownloadStatus(hostname, pws_path)
                    )
            #
            for children_attachment_id in ir_attachment_id.getRelatedHiTreeNew(
                recursion=True, getRftree=True, latest=latest
            ):
                #
                out.extend(
                    children_attachment_id.computeDownloadStatus(hostname, pws_path)
                )
            #
        return out

    @api.model
    def get_file_structure(self, ir_attachemnt_id, hostname, pws_path, latest=False):
        """
        The door onto getFileStructure for a client that calls it the way it
        calls everything else on this model: plain positional arguments.

        Without @api.model Odoo reads the first positional argument as the ids of
        the recordset the method runs on, so a client that puts the attachment id
        there leaves the method one argument short and the server answers
        "missing 1 required positional argument: 'pws_path'".

        getFileStructure itself is left exactly as it is: the 2019 client sends an
        empty id list and the rest by name, and that form works only undecorated.
        """
        return self.getFileStructure(
            ir_attachemnt_id, hostname, pws_path, latest=latest
        )

    @api.model
    def pre_check_in_recursive_all(self, doc_props_json):
        """The check-in analysis, reached through this model like everything else.

        ir.attachment.preCheckInRecursive_all reads the first element of a list,
        which is how the 2019 client happened to call it. The shape is adapted
        here, so a client passes the one thing it has -- the document's
        attributes as JSON -- and gets the answer back as JSON.

        preCheckInRecursive, which the previous client called, raises
        DeprecationWarning("this function must be cancelled in the 20 version").
        """
        return (
            self.env["ir.attachment"]
            .preCheckInRecursive_all([doc_props_json])
        )

    @api.model
    def check_in_documents(self, to_check_in_json, force=False):
        """Check in the documents the analysis and the user agreed on.

        `to_check_in_json` is {"to_check_in": [<doc_vals>, ...]} as JSON -- the
        same thing CheckIn2 wants -- and each entry needs either an id or enough
        properties for getDocId to find the document.
        """
        return self.env["ir.attachment"].CheckIn2([to_check_in_json], force=force)

    @api.model
    def client_can_check_out(self, doc_props):
        """(document_id, flag, message) for the document those attributes name.

        `doc_props` is a list whose first entry carries HOST_NAME and HOST_PWS:
        who holds a check-out is a question about a machine and not only about a
        user, and clientCanCheckOut reads them straight out of it.

        The flags are check_in (it can be taken), check_out_by_me,
        check_out_by_user, check_out_released and not_found.
        """
        return self.env["ir.attachment"].clientCanCheckOut(doc_props)

    @api.model
    def pre_check_out_recursive(self, structure_json):
        """What a check-out would involve, and which files here are behind Odoo."""
        return self.env["ir.attachment"].preCheckOutRecursive(structure_json)

    @api.model
    def check_out_recursive(self, structure_json, pws_path="", hostname="", force=False):
        """Take the documents the analysis and the user agreed on."""
        return self.env["ir.attachment"].CheckOutRecursive(
            structure_json, pws_path=pws_path, hostname=hostname, force=force
        )

    @api.model
    def send_check_out_request(self, document_id, host_name, host_pws):
        """Ask whoever holds the document to check it in."""
        return self.env["ir.attachment"].sent_check_out_requests(
            document_id, host_name, host_pws
        )

    @api.model
    def get_checkout_snapshot(self, stamp=""):
        """Who holds each checked-out document, for the OdooPLM checkout helper.

        The helper runs on the user's machine and keeps a local copy, so that the
        CAD add-ins can say who holds a read-only file without asking the server.
        plm.checkout only holds what is checked out right now, so the answer is
        small.

        Check-ins delete rows, so a date cannot tell whether anything changed:
        `stamp` is a hash of the (document, user) pairs, as the previous answer
        returned it. When it still matches, only {"stamp", "changed": False} comes
        back and the rows are not sent again.

        plm.checkout is read as superuser, because who holds a document is
        something every PLM user may know, but only the documents this user can
        read are kept: with several companies the file names of another company
        stay out of the answer.

        Each row: document_id, file_name (the attachment name, which is the file
        name in the PWS), user, user_id, hostname, checkout_date.
        """
        checkouts = (
            self.env["plm.checkout"]
            .sudo()
            .search_read([], ["documentid", "userid", "hostname", "create_date"])
        )
        readable_ids = set(
            self.env["ir.attachment"]
            .search(
                [
                    (
                        "id",
                        "in",
                        [c["documentid"][0] for c in checkouts if c["documentid"]],
                    )
                ]
            )
            .ids
        )
        checkouts = [
            c
            for c in checkouts
            if c["documentid"] and c["documentid"][0] in readable_ids
        ]
        pairs = sorted(
            (c["documentid"][0], c["userid"][0] if c["userid"] else 0)
            for c in checkouts
        )
        new_stamp = hashlib.sha1(json.dumps(pairs).encode("utf-8")).hexdigest()
        if stamp and stamp == new_stamp:
            return {"stamp": new_stamp, "changed": False, "rows": []}
        file_names = {
            attachment.id: attachment.name
            for attachment in self.env["ir.attachment"]
            .sudo()
            .browse(sorted(readable_ids))
        }
        rows = [
            {
                "document_id": c["documentid"][0],
                "file_name": file_names.get(c["documentid"][0], ""),
                "user": c["userid"][1] if c["userid"] else "",
                "user_id": c["userid"][0] if c["userid"] else 0,
                "hostname": c["hostname"] or "",
                "checkout_date": fields.Datetime.to_string(c["create_date"]),
            }
            for c in checkouts
        ]
        rows.sort(key=lambda row: row["file_name"].lower())
        return {"stamp": new_stamp, "changed": True, "rows": rows}

    def getAttachmentFromProp(self, document_attributes):
        """
        Get The attachment from a dictionary
        check before from id and the from minimun property
        """
        attach_object = self.env["ir.attachment"]
        attach_id = document_attributes.get("id")
        if attach_id:
            ir_browse = attach_object.browse(attach_id)
        elif self.env.context.get("odooPLM") and not document_attributes.get(
            "engineering_code"
        ):
            # No code is no document. Odoo reads `= ''` as "this field is empty",
            # so searching anyway returns every attachment that has no code --
            # web assets included -- and the caller answers about the first of
            # them: a new drawing was refused as "in check-in" that way. Only for
            # the CAD client, so no other Odoo flow is touched.
            ir_browse = attach_object
        else:
            ir_browse = attach_object.search(
                [
                    (
                        "engineering_code",
                        "=",
                        document_attributes.get("engineering_code", ""),
                    ),
                    (
                        "engineering_revision",
                        "=",
                        document_attributes.get("engineering_revision", -1),
                    ),
                ]
            )
        return ir_browse

    @api.model
    def attachmentCanBeSaved(
        self,
        document_attributes,
        raiseError=False,
        returnCode=False,
        skipCheckOutControl=False,
    ):
        """
        Check if the document can be saved !!
        """
        for brwItem in self.getAttachmentFromProp(document_attributes):
            return brwItem.canBeSaved(
                raiseError=raiseError,
                returnCode=returnCode,
                skipCheckOutControl=skipCheckOutControl,
            )
        return True, ""

    @api.model
    def attachmentCheckOut(
        self, document_attributes, hostName, hostPws, showError=True
    ):
        """
        perform the check out operation from document attributes
        """
        for brwItem in self.getAttachmentFromProp(document_attributes):
            return brwItem.checkout(
                hostName=hostName, hostPws=hostPws, showError=showError
            )
        return True, ""

    @api.model
    def getNotCopiableFields(self, model_name):
        """
        return a non copiable fields name
        """
        return (
            self.env["ir.model.fields"]
            .sudo()
            .search([("model", "in", model_name), ("copied", "=", False)])
            .mapped("name")
        )

    @api.model
    def check_pre_download_data(self, args):
        """
        function used for prefetch easely the data fro the download function
        :attachemnt id to downalod
        :last_revision get latest version of the file
        :out list of result
        """
        attachment_ids, last_revision = args
        out = []
        for attachment_id in self.env["ir.attachment"].search(
            [("id", "in", attachment_ids)]
        ):
            if last_revision:
                attachment_id = attachment_id.get_latest_version()[0]
            out.append(attachment_id.get_open_attachment_data_out())
        return out

    def CheckAllFiles(self, request, default=None):
        """
        Evaluate documents to return
        """
        forceFlag = False
        outIds = []
        doc_id, listedFiles, selection, hostname, hostpws = request
        docBrws = self.browse(doc_id)
        outIds.append(doc_id)
        if selection is False:
            selection = 1  # Case of selected
        if selection < 0:  # Case of force refresh PWS
            forceFlag = True
            selection = selection * (-1)
        if docBrws.is2D():
            outIds.extend(self.getRelatedLyTree(doc_id))
        outIds.extend(self.getRelatedHiTree(doc_id, recursion=True, getRftree=True))
        outIds = list(set(outIds))
        if selection == 2:  # Case of latest
            outIds = self._getlastrev(outIds)
        return self._data_check_files(
            outIds, listedFiles, forceFlag, False, hostname, hostpws
        )

    def getCopyField(self, src_model):
        return (
            self.env["ir.model.fields"]
            .sudo()
            .search([("model", "=", src_model), ("copied", "=", True)])
            .mapped("name")
        )
