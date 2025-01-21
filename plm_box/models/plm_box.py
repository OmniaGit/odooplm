# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
import datetime
import logging

import pytz
from dateutil import parser
from odoo import _, api, fields, models
from odoo.addons.plm.models.plm_mixin import (
    START_STATUS,
    CONFIRMED_STATUS,
    RELEASED_STATUS,
    OBSOLATED_STATUS,
)
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT,
)


def correctDate(fromTimeStr, context):
    if isinstance(fromTimeStr, str):
        serverUtcTime = parser.parse(fromTimeStr)
    else:
        serverUtcTime = fromTimeStr

    utcDate = serverUtcTime.replace(tzinfo=pytz.utc).astimezone(
        pytz.timezone(context.get("tz", "Europe/Rome"))
    )
    return utcDate.replace(tzinfo=None)


class Plm_box(models.Model):
    _name = "plm.box"
    _description = "Model to manage a box inside the plm module"
    _inherit = "revision.plm.mixin"
    _rec_name = "engineering_code"

    box_id = fields.Integer(_("Box ID"))
    version = fields.Integer(_("Version"))
    description = fields.Text(_("Description"))
    csv_structure = fields.Text(
        _("CSV Structure"),
        default="""{"engineering_code": "","engineering_revision": "","qty": ""}""",
    )

    document_rel = fields.One2many("ir.attachment", "plm_box_id", "Documents")
    plm_box_rel = fields.Many2many(
        "plm.box",
        "plm_box_box_rel",
        "plm_box_parent_id",
        "plm_box_child_id",
        _("Children Box"),
    )
    groups_rel = fields.Many2many(
        "res.groups",
        "plm_box_groups_rel",
        "plm_box_id",
        "group_id",
        _("Groups Allowed"),
    )
    create_date = fields.Datetime(_("Date Created"), readonly=True)
    write_date = fields.Datetime(_("Date Modified"), readonly=True)
    product_id = fields.Many2many(
        "product.product", "plm_box_products_rel", "box_id", "product_id", _("Product")
    )
    project_id = fields.Many2many(
        "project.project", "plm_box_proj_rel", "box_id", "project_id", _("Project")
    )
    task_id = fields.Many2many(
        "project.task", "plm_box_task_rel", "box_id", "task_id", _("Task")
    )
    sale_ord_id = fields.Many2many(
        "sale.order", "plm_box_sale_ord_rel", "box_id", "sale_ord_id", _("Sale Order")
    )
    user_rel_id = fields.Many2many(
        "res.users", "plm_box_user_rel", "box_id", "user_id", _("User")
    )
    bom_id = fields.Many2many(
        "mrp.bom", "plm_box_bom_rel", "box_id", "bom_id", _("Bill Of Material")
    )
    wc_id = fields.Many2many(
        "mrp.workcenter", "plm_box_wc_rel", "box_id", "wc_id", _("Work Center")
    )

    def unlink(self):
        for plm_box_id in self:
            if not self.boxUnlinkPossible(plm_box_id):
                continue
            super(Plm_box, plm_box_id).unlink()
        return True

    @api.model
    def boxUnlinkPossible(self, plm_box_id):
        for child_plm_box_id in plm_box_id.plm_box_rel:
            if not self.boxUnlinkPossible(child_plm_box_id):
                return False
        for ir_attachment_id in plm_box_id.document_rel:
            if not ir_attachment_id.ischecked_in():
                raise UserError(
                    _("Document %r of box %r is in check-in state, so could not delete")
                    % (ir_attachment_id.engineering_code, plm_box_id.engineering_code)
                )
        return True

    @api.model
    def connectionOk(self, vals):
        """
        Test connection with client
        """
        return True

    @api.model
    def saveStructure(self, vals):
        for boxName, item in vals.items():
            docIds = []
            box_id = self.env.context.get("parentId", False)
            child_plm_box = item.get("child_plm_box")
            child_docs = item.get("child_docs")
            for childDoc in child_docs:
                documentID = childDoc.get("documentID")
                if documentID:
                    docIds.append(documentID)
            outVals = {
                "engineering_code": boxName,
                "description": item.get("description", ""),
                "plm_box_rel": [],
                "obj_rel": False,
                "box_id": box_id,
                "document_rel": [[6, False, docIds]],
            }
            plm_box_id = self.createBox(outVals)
            newContext = self.env.context.copy()
            newContext["parentId"] = plm_box_id
            for childPlm in child_plm_box:
                self.with_context(newContext).saveStructure(childPlm)
        return True

    @api.model
    def createBox(self, vals):
        """
        Create a box
        """
        return self.create(vals)

    @api.model_create_multi
    def create(self, vals):
        _logger.warning(vals)
        for rec in vals:
            _logger.info(rec)
            if not rec.get("engineering_code", False):
                name = self.getNewSequencedName()
                rec["engineering_code"] = name
        return super(Plm_box, self).create(vals)

    def write(self, vals):
        """
        Write a new name if not provided
        """
        for plm_box_id in self:
            name = plm_box_id.engineering_code
            if name in [False, ""]:
                name = self.getNewSequencedName()
                vals["engineering_code"] = name
        return super(Plm_box, self).write(vals)

    def action_add_view_dox_document(self):

        return {
            "type": "ir.actions.act_window",
            "name": "Attachments",
            "res_model": "ir.attachment",
            "view_mode": "list,form",
            "target": "current",
            "domain": [("id", "in", self.document_rel.ids)],
            "context": {
                "default_plm_box_id": self.id,
            },
        }

    @api.model
    def getNewSequencedName(self):
        """
        Get new name from sequence
        """
        return self.env.get("ir.sequence").next_by_code("plm.box")

    @api.model
    def getAvaibleGroupsByUser(self):
        """
        Return ids of avaible groups for user
        """
        return self.env.get("res.groups").search([("users.id", "=", self.env.uid)]).ids

    @api.model
    def setRelatedDocs(self, parentBrws):
        docRelList = []
        for ir_attachment_id in parentBrws.document_rel:
            docRelList.append(ir_attachment_id.engineering_code)
            if ir_attachment_id.engineering_code not in self.docs.keys():
                if self.isDocAvaibleForUser(ir_attachment_id):
                    self.docs[
                        ir_attachment_id.engineering_code
                    ] = self.getDocDictValues(ir_attachment_id)
        self.box_doc_rel[parentBrws.engineering_code] = docRelList

    @api.model
    def getRelatedEntities(self, parentBrws):
        objRelList = []
        document_data = dict()
        for doc in parentBrws.document_rel:
            document_data[str(doc.id)] = {
                "name": doc.engineering_code or "",
                "description": doc.description or "",
                "state": doc.engineering_state or "",
                "readonly": self.docReadonlyCompute(doc.id),
                "write_date": doc.write_date or "",
                "revisionid": doc.engineering_revision or "",
                "fileName": doc.name or "",
                "checkoutUser": doc.checkout_user or False,
            }
        objRelList.append({"document_rel": document_data})

        for product_product_id in parentBrws.product_id:
            objRelList.append(
                {
                    "obj_name": "Product",
                    "obj_type": "product.product",
                    "obj_rel_name": product_product_id.name,
                }
            )
        for project_id in parentBrws.project_id:
            objRelList.append(
                {
                    "obj_name": "Project",
                    "obj_type": "project.project",
                    "obj_rel_name": project_id.name,
                }
            )
        for task_id in parentBrws.task_id:
            objRelList.append(
                {
                    "obj_name": "Task",
                    "obj_type": "project.task",
                    "obj_rel_name": task_id.name,
                }
            )
        for sale_order_id in parentBrws.sale_ord_id:
            objRelList.append(
                {
                    "obj_name": "Sale Order",
                    "obj_type": "sale.order",
                    "obj_rel_name": sale_order_id.name,
                }
            )
        for res_user_id in parentBrws.user_rel_id:
            objRelList.append(
                {
                    "obj_name": "User",
                    "obj_type": "res.users",
                    "obj_rel_name": res_user_id.name,
                }
            )
        for mrp_bom_id in parentBrws.bom_id:
            objRelList.append(
                {
                    "obj_name": "Bill of Material",
                    "obj_type": "mrp.bom",
                    "obj_rel_name": mrp_bom_id.name,
                }
            )
        for mrp_workcenter_id in parentBrws.wc_id:
            objRelList.append(
                {
                    "obj_name": "Work Center",
                    "obj_type": "mrp.workcenter",
                    "obj_rel_name": mrp_workcenter_id.name,
                }
            )
        return objRelList

    @api.model
    def setRelatedBoxes(self, parentBrws):
        childBoxNames = []
        childBoxes = []
        for plm_box_id in parentBrws.plm_box_rel:
            childBoxNames.append(plm_box_id.engineering_code)
            childBoxes.append(plm_box_id)
        self.box_box_rel[parentBrws.engineering_code] = childBoxNames
        return childBoxes

    @api.model
    def docReadonlyCompute(self, docIds):
        """
        Compute if document is readonly
        """
        ir_attachment_id = self.env.get("ir.attachment").browse(docIds)
        if ir_attachment_id.engineering_state in [
            "released",
            "undermodify",
            "obsoleted",
        ]:
            return True
        if not ir_attachment_id.ischecked_in():
            check_out_by_me = ir_attachment_id._is_checkedout_for_me()
            if check_out_by_me:
                return False
        return True

    def boxReadonlyCompute(self):
        """
        Compute if box is readonly
        """
        for plm_box_id in self:
            if plm_box_id.engineering_state in ["released", "undermodify", "obsoleted"]:
                return True
        return False

    @api.model
    def getBoxesByFollower(self, avaibleBoxIds):
        """
        Update avaible boxes due to follower
        """
        res_user_id = self.env.get("res.users").browse(self.env.uid)
        if res_user_id:
            if res_user_id.partner_id:
                plm_box_ids = self.search(
                    [("message_follower_ids.id", "=", res_user_id.partner_id.id)]
                ).ids
                for plm_box_id in plm_box_ids:
                    if plm_box_id not in avaibleBoxIds:
                        avaibleBoxIds.append(plm_box_id)
        return avaibleBoxIds

    @api.model
    def getBoxesByAvaibleParent(self, parents, outList):
        for boxId in parents:
            child_plm_box_ids = self.browse(boxId).plm_box_rel
            localList = []
            for plm_box_id in child_plm_box_ids:
                if plm_box_id.id in parents or plm_box_id.id in outList:
                    continue
                localList.append(plm_box_id.id)
            if not localList:
                continue
            outList = self.getBoxesByAvaibleParent(localList, outList)
            for elem in localList:
                outList.append(elem)
        return outList

    @api.model
    def getBoxes(self, boxes={}):
        """
        *** CLIENT ***
        """
        outBoxDict = {}
        avaibleBoxIds = []
        if not boxes:
            return {}
        if boxes:
            for boxName in boxes.keys():
                plm_box_id = self.search([("engineering_code", "=", boxName)])
                avaibleBoxIds.extend(plm_box_id.ids)
        for boxId in avaibleBoxIds:
            plm_box_id = self.browse(boxId)
            self.setRelatedDocs(plm_box_id)
            self.box_ent_rel[plm_box_id.engineering_code] = self.getRelatedEntities(
                plm_box_id
            )
            childList = self.setRelatedBoxes(plm_box_id)
            for childBrws in childList:
                if childBrws.id not in avaibleBoxIds:
                    avaibleBoxIds.append(childBrws.id)
            writeVal = datetime.datetime.strptime(
                plm_box_id.write_date, DEFAULT_SERVER_DATETIME_FORMAT
            )
            outBoxDict[plm_box_id.engineering_code] = {
                "boxVersion": plm_box_id.version,
                "boxDesc": plm_box_id.description,
                "boxState": plm_box_id.engineering_state,
                "boxReadonly": plm_box_id.boxReadonlyCompute(),
                "boxWriteDate": correctDate(writeVal, self.env.context),
                "boxPrimary": False,
            }
            if plm_box_id.engineering_code in boxes.keys():
                boxPrimary = boxes[plm_box_id.engineering_code][1]
                outBoxDict[plm_box_id.engineering_code]["boxPrimary"] = boxPrimary
        return outBoxDict

    @api.model
    def getDocs(self, docsToUpdate=[]):
        outDocDict = {}
        docIds = []
        plmDocObj = self.env.get("ir.attachment")
        userAvaibleBoxIds = self.getAvaibleGroupsByUser()
        if isinstance(docsToUpdate, list):
            for doc in docsToUpdate:
                docBrwsList = plmDocObj.search([("engineering_code", "=", doc[0])])
                if not docBrwsList:
                    outDocDict[doc[0]] = {}
                else:
                    docIds.extend(docBrwsList.ids)
        elif docsToUpdate == "all":
            docIds = plmDocObj.search([]).ids
        else:
            return []
        for docId in docIds:
            boxIds = self.search([("document_rel.id", "=", docId)]).ids
            docBrws = plmDocObj.browse(docId)
            found = False
            for boxId in boxIds:
                if boxId in userAvaibleBoxIds:
                    found = True
                    break
            if found is True:
                if self.isDocAvaibleForUser(docBrws):
                    outDocDict[docBrws.name] = self.getDocDictValues(docBrws)
        return outDocDict

    @api.model
    def isDocAvaibleForUser(self, docBrws):
        found = self.userInTheFollowers(docBrws)
        if found is not False:
            res = self.userInAdminOrPlmItegration(docBrws)
            if res:
                return True
        else:
            return True
        return False

    @api.model
    def userInAdminOrPlmItegration(self, docBrws):
        plmUserGroupBrwsList = self.env.get("res.groups").search(
            [("name", "=", "PLM / Integration User")]
        )
        if self.env._is_superuser():
            return True
        else:
            for plmUserGroupBrws in plmUserGroupBrwsList:
                for brwsUser in plmUserGroupBrws.users:
                    if self.env.uid == brwsUser.id:
                        return True
        return False

    @api.model
    def userInTheFollowers(self, docBrws):
        for elem in docBrws.message_follower_ids:
            userBrwsList = self.env.get("res.users").search(
                [("partner_id", "=", elem.id)]
            )
            for userBrws in userBrwsList:
                if self.env.uid == userBrws.id:
                    return True
        return False

    @api.model
    def getBoxesAndStructure(self, vals={}):
        self.box_doc_rel = {}
        self.box_ent_rel = {}
        self.box_box_rel = {}
        self.docs = {}
        self.boxis = self.getBoxes(vals.get("boxesList", []))
        outDict = {
            "plm_box": self.boxis,
            "docs": self.docs,
            "box_doc_rel": self.box_doc_rel,
            "box_ent_rel": self.box_ent_rel,
            "box_box_rel": self.box_box_rel,
        }
        return outDict

    def action_draft(self):
        self.move_to_state(START_STATUS)
        return False

    def action_confirm(self):
        """
        action to be executed for Confirm state
        """
        message = self.move_children_object_to_state(CONFIRMED_STATUS, "action_confirm")
        if not message:
            self.move_to_state(CONFIRMED_STATUS)
        else:
            raise UserError(message)
        return False

    def action_release(self):
        """
        release the object
        """
        message = self.move_children_object_to_state(RELEASED_STATUS, "action_release")
        if not message:
            self.move_to_state(RELEASED_STATUS)
        else:
            raise UserError(message)
        return False

    def action_obsolete(self):
        """
        obsolete the object
        """
        self.move_to_state(OBSOLATED_STATUS)
        return False

    def action_reactivate(self):
        """
        reactivate the object
        """
        self.move_to_state(START_STATUS)
        return False

    def move_children_object_to_state(self, state, call_name):
        message = ""
        for attachment_id in self.document_rel:
            if attachment_id.ischecked_in():
                attachment_id.commonWFAction(True, state, True)
            else:
                message += _(
                    f"\n document {attachment_id.name} not checked-in impossible"
                    f"to move to state {state}"
                )
        for plm_box_id in self.plm_box_rel:
            sub_message = getattr(plm_box_id, call_name)()
            if sub_message:
                message += sub_message
        return message

    @api.model
    def getAvaiableBoxIds(self):
        avaibleBoxIds = []
        groupsIds = self.getAvaibleGroupsByUser()
        avaibleBoxIds = (
            avaibleBoxIds + self.search([("groups_rel.id", "in", groupsIds)]).ids
        )
        avaibleBoxIds = avaibleBoxIds + self.getBoxesByAvaibleParent(avaibleBoxIds, [])
        avaibleBoxIds = self.getBoxesByFollower(avaibleBoxIds)
        return avaibleBoxIds

    @api.model
    def getAvaiableBoxes(self, vals={}):
        outList = []
        boxesIds = self.getAvaiableBoxIds()
        for plm_box_id in self.browse(boxesIds):
            outList.append(
                [
                    plm_box_id.engineering_code,
                    plm_box_id.description,
                    plm_box_id.version,
                    plm_box_id.engineering_state,
                ]
            )
        return outList

    @api.model
    def getDifferences(self, localDict):
        outList = []
        if not localDict:
            return []
        else:
            boxIds = []
            docIds = []
            for values in localDict.values():
                if values[1] == "box":
                    valsList, boxId = self.checkIfBoxChanged(values)
                    if valsList:
                        outList.append(valsList)
                    if boxId:
                        boxIds.append(boxId)
                elif values[1] == "document":
                    valsList, docId = self.checkIfDocChanged(values)
                    if valsList:
                        outList.append(valsList)
                    if docId:
                        docIds.append(docId)
            outList = self.checkForNewDocuments(docIds, boxIds, outList)
        return outList

    @api.model
    def checkForNewBoxes(self, boxIds, avaibleBoxes):
        outList = []
        avaibleNewBoxes = list(set(avaibleBoxes) - set(boxIds))
        for boxId in avaibleNewBoxes:
            outList.append([self.browse(boxId).engineering_code, "box"])
        return outList

    @api.model
    def checkForNewDocuments(self, docIds, avaibleBoxes, outList):
        for boxId in avaibleBoxes:
            plm_box_id = self.browse(boxId)
            if plm_box_id:
                for ir_attachment_id in plm_box_id.document_rel:
                    if ir_attachment_id.id not in docIds:
                        docIds.append(ir_attachment_id.id)
                        outList.append([ir_attachment_id.name, "document"])
        return outList

    @api.model
    def checkIfBoxChanged(self, values):
        name, typee, datetimee = values
        for plm_box_id in self.search([("engineering_code", "=", name)]):
            boxId = plm_box_id.id
            wr_date = plm_box_id.write_date
            if wr_date != "n/a":
                wr_date = wr_date.split(".")[0]
                serverDatetime = datetime.datetime.strptime(
                    wr_date, DEFAULT_SERVER_DATETIME_FORMAT
                )
                serverDatetime = correctDate(serverDatetime, self.env.context)
                clientDatetime = datetime.datetime.strptime(
                    datetimee.value, "%Y%m%dT%H:%M:%S"
                )
                if serverDatetime > clientDatetime:
                    deltaTime = serverDatetime - clientDatetime
                    if deltaTime.total_seconds() > 2:
                        return [name, typee], boxId
                else:
                    return [], boxId
        return [], False

    @api.model
    def checkIfDocChanged(self, values):
        name, typee, datetimee = values
        ir_attachment = self.env.get("ir.attachment")
        docBrwsList = ir_attachment.search([("name", "=", name)])
        for docBrws in docBrwsList:
            docId = docBrws.id
            if ir_attachment.getDocumentState() != "check-in":
                return [], docId
            wr_date = docBrws.write_date
            if wr_date != "n/a":
                wr_date = wr_date.split(".")[0]
                serverDatetime = datetime.datetime.strptime(
                    wr_date, DEFAULT_SERVER_DATETIME_FORMAT
                )
                serverDatetime = correctDate(serverDatetime, self.env.context)
                clientDatetime = datetime.datetime.strptime(
                    datetimee.value, "%Y%m%dT%H:%M:%S"
                )
                if serverDatetime > clientDatetime:
                    deltaTime = serverDatetime - clientDatetime
                    if deltaTime.total_seconds() > 2:
                        return [name, typee, ""], docId
                else:
                    return [], docId
        else:
            return [name, typee, "deleted"], False
        return [], False

    @api.model
    def getBoxesStructureFromServer(
        self, box_ids, primary_box_ids=[], download_all=False
    ):
        outDict = {}
        available_box_ids = self.getAvaiableBoxIds()
        if not box_ids and not download_all:
            return outDict
        all_boxes = {}
        for box_obj in self.browse(box_ids):
            outDict[str(box_obj.id)], all_boxes_children = box_obj.createBoxStructure(
                primary=True,
                available_box_ids=available_box_ids,
                all_boxes=all_boxes,
                primary_box_ids=primary_box_ids,
            )
            all_boxes.update(all_boxes_children)
        if download_all:
            for available_box_id in available_box_ids:
                if available_box_id not in all_boxes.keys():
                    box_obj = self.browse(available_box_id)
                    outDict[str(box_obj.id)], _ = box_obj.createBoxStructure(
                        primary=True,
                        available_box_ids=available_box_ids,
                        all_boxes=all_boxes,
                        primary_box_ids=primary_box_ids,
                    )
        return outDict

    def createBoxStructure(
        self, primary=False, available_box_ids=[], all_boxes={}, primary_box_ids=[]
    ):
        """
        *** CLIENT ***
        """
        outDict = {"primary": primary, "children": {}}
        for boxBrws in self:
            if boxBrws.id not in available_box_ids:
                return {}, all_boxes
            for boxChildBrws in boxBrws.plm_box_rel:
                outDict["children"].setdefault(boxChildBrws.engineering_code, {})
                (
                    outDict["children"][boxChildBrws.engineering_code],
                    all_boxes,
                ) = boxChildBrws.createBoxStructure(False, available_box_ids, all_boxes)
            self.setRelatedEntities(boxBrws, outDict)
            outDict["description"] = boxBrws.description or ""
            outDict["state"] = boxBrws.engineering_state
            outDict["name"] = boxBrws.engineering_code
            outDict["readonly"] = boxBrws.boxReadonlyCompute()
            outDict["id"] = boxBrws.id
            if boxBrws.id in primary_box_ids:
                outDict["primary"] = True
            all_boxes[boxBrws.id] = boxBrws
        return outDict, all_boxes

    @api.model
    def getBoxStructure(
        self, box_ids=[], headers={}, fields_to_read=[], tooltip_fields={}
    ):
        if not headers:
            headers = {
                "name": "Name",
                "description": "Description",
                "state": "State",
                # 'entities': 'Entities',
            }
        if not fields_to_read:
            fields_to_read = [
                "engineering_code",
                "description",
                "engineering_state",
                "document_rel",
            ]
        available_boxes = self.getAvaiableBoxIds()
        structure = self.boxStructureRecursion(
            fields_to_read, tooltip_fields, box_ids, available_boxes
        )
        if structure:
            for box in structure:
                for record in box:
                    if isinstance(record, dict):
                        if (
                            "engineering_state" in record
                            and "engineering_code" in record
                        ):
                            record["name"] = record.pop(
                                "engineering_code", record.get("name")
                            )
                            record["state"] = record.pop(
                                "engineering_state", record.get("state")
                            )

        return [headers, structure]

    @api.model
    def boxStructureRecursion(
        self, to_read, tooltip_fields, box_ids, available_boxes=[]
    ):
        out = []
        for box in self.browse(box_ids):
            if box.id in available_boxes:
                vals_list = box.read(to_read)
                for vals in vals_list:
                    vals["entities"] = box.computeEntities()
                    children = self.boxStructureRecursion(
                        to_read, tooltip_fields, box.plm_box_rel.ids, available_boxes
                    )
                    vals = self.setupTooltipFields(vals, tooltip_fields)
                    out.append([vals, children])
        return out

    def computeEntities(self):
        def compute_obj(out, model_str, brws_rec):
            if brws_rec:
                for obj in brws_rec:
                    out = obj.display_name
            return out

        out = ""
        for box in self:
            out += compute_obj(out, "Product", box.product_id)
            out += compute_obj(out, "Project", box.project_id)
            out += compute_obj(out, "Task", box.task_id)
            out += compute_obj(out, "Sale Order", box.sale_ord_id)
            out += compute_obj(out, "Users", box.user_rel_id)
            out += compute_obj(out, "BOM", box.bom_id)
            out += compute_obj(out, "Work Centers", box.wc_id)
            break
        return out

    @api.model
    def setupTooltipFields(self, vals, tooltip_fields):
        out = {}
        for field_name, field_value in vals.items():
            tooltip_field = tooltip_fields.get(field_name)
            if tooltip_field:
                out[tooltip_field] = field_value
            else:
                out[field_name] = field_value
        return out

    @api.model
    def getDocDictValues(self, ir_attachment_id):
        getCheckOutUser = ""
        docState = ir_attachment_id.getDocumentState()
        if docState in ["check-out", "check-out-by-me"]:
            getCheckOutUser = ir_attachment_id.getCheckOutUser()
        writeVal = ir_attachment_id.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        return {
            "id": ir_attachment_id.id,
            "name": ir_attachment_id.engineering_code,
            "engineering_revision": ir_attachment_id.engineering_revision,
            "datas_fname": ir_attachment_id.name,
            "create_date": ir_attachment_id.create_date,
            "write_date": correctDate(writeVal, self.env.context),
            "description": ir_attachment_id.description,
            "fileName": ir_attachment_id.name,
            "state": ir_attachment_id.engineering_state,
            "readonly": self.docReadonlyCompute(ir_attachment_id.id),
            "checkoutUser": getCheckOutUser,
        }

    @api.model
    def verifyBoxesPermissions(self, box_ids):
        to_del = []
        available_boxes = self.getAvaiableBoxIds()
        for box_id in box_ids:
            if box_id not in available_boxes:
                to_del.append(box_id)
        return to_del

    @api.model
    def setRelatedEntities(self, parentBrws, outDict):
        def populationLoop(brws_record, outDict, field_name):
            obj_name = (
                self.env["ir.model"]
                .search([("model", "=", brws_record._name)])
                .display_name
            )
            for brws in brws_record:
                if field_name not in outDict["entities"]:
                    outDict["entities"][field_name] = {}
                outDict["entities"][field_name][str(brws.id)] = {
                    "obj_name": obj_name,
                    "obj_type": brws._name,
                    "obj_rel_name": brws.display_name,
                    "id": brws.id,
                }

        outDict["document_rel"] = parentBrws.document_rel.ids
        outDict["product_id"] = parentBrws.product_id.ids
        outDict["project_id"] = parentBrws.project_id.ids
        outDict["task_id"] = parentBrws.task_id.ids
        outDict["sale_ord_id"] = parentBrws.sale_ord_id.ids
        outDict["user_rel_id"] = parentBrws.user_rel_id.ids
        outDict["bom_id"] = parentBrws.bom_id.ids
        outDict["wc_id"] = parentBrws.wc_id.ids
        outDict["entities"] = {}

        populationLoop(parentBrws.product_id, outDict, "product_id")
        populationLoop(parentBrws.project_id, outDict, "project_id")
        populationLoop(parentBrws.task_id, outDict, "task_id")
        populationLoop(parentBrws.sale_ord_id, outDict, "sale_ord_id")
        populationLoop(parentBrws.user_rel_id, outDict, "user_rel_id")
        populationLoop(parentBrws.bom_id, outDict, "bom_id")
        populationLoop(parentBrws.wc_id, outDict, "wc_id")
        for document in parentBrws.document_rel:
            if "document_rel" not in outDict["entities"]:
                outDict["entities"]["document_rel"] = {}
            outDict["entities"]["document_rel"][
                str(document.id)
            ] = self.getDocDictValues(document)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
