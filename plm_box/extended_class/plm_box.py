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
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import _
from odoo import api

import datetime
from dateutil import parser
import pytz

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_TIME_FORMAT)

USED_STATES = [('draft', _('Draft')),
               ('confirmed', _('Confirmed')),
               ('released', _('Released')),
               ('undermodify', _('UnderModify')),
               ('obsoleted', _('Obsoleted'))]


def correctDate(fromTimeStr, context):
    serverUtcTime = parser.parse(fromTimeStr.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
    utcDate = serverUtcTime.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(context.get('tz', 'Europe/Rome')))
    return utcDate.replace(tzinfo=None)


class Plm_box(models.Model):
    _name = 'plm.box'
    _inherit = 'mail.thread'

    name = fields.Char(_('Code'))
    box_id = fields.Integer(_('Box ID'))
    version = fields.Integer(_('Version'))
    description = fields.Text(_('Description'))
    document_rel = fields.Many2many('plm.document',
                                    'plm_document_rel',
                                    'name',
                                    'plm_document_id',
                                    _('Documents')
                                    )
    plm_box_rel = fields.Many2many('plm.box',
                                   'plm_box_box_rel',
                                   'plm_box_parent_id',
                                   'plm_box_child_id',
                                   _('Children Box')
                                   )
    state = fields.Char(_('State'))
    groups_rel = fields.Many2many('res.groups',
                                  'plm_box_groups_rel',
                                  'plm_box_id',
                                  'group_id',
                                  _('Groups Allowed')
                                  )
    create_date = fields.Datetime(_('Date Created'), readonly=True)
    write_date = fields.Datetime(_('Date Modified'), readonly=True)
    state = fields.Selection(USED_STATES, _('Status'), help=_("The status of the box."), readonly="True", required=True, default='draft')
    product_id = fields.Many2many('product.product', 'plm_box_products_rel', 'box_id', 'product_id', _('Product'))
    project_id = fields.Many2many('project.project', 'plm_box_proj_rel', 'box_id', 'project_id', _('Project'))
    task_id = fields.Many2many('project.task', 'plm_box_task_rel', 'box_id', 'task_id', _('Task'))
    sale_ord_id = fields.Many2many('sale.order', 'plm_box_sale_ord_rel', 'box_id', 'sale_ord_id', _('Sale Order'))
    user_rel_id = fields.Many2many('res.users', 'plm_box_user_rel', 'box_id', 'user_id', _('User'))
    bom_id = fields.Many2many('mrp.bom', 'plm_box_bom_rel', 'box_id', 'bom_id', _('Bill Of Material'))
    wc_id = fields.Many2many('mrp.workcenter', 'plm_box_wc_rel', 'box_id', 'wc_id', _('Work Center'))

    @api.multi
    def unlink(self):
        for boxBrws in self:
            if not self.boxUnlinkPossible(boxBrws):
                continue
            super(Plm_box, boxBrws).unlink()
        return True

    @api.model
    def boxUnlinkPossible(self, boxBrws):
        for childBox in boxBrws.plm_box_rel:
            if not self.boxUnlinkPossible(childBox):
                return False
        for docBrws in boxBrws.document_rel:
            if not docBrws.ischecked_in():
                raise UserError(_('Document %r of box %r is in check-in state, so could not delete') % (docBrws.name, boxBrws.name))
        return True

    @api.model
    def connectionOk(self, vals):
        '''
            Test connection with client
        '''
        return True

    @api.model
    def saveStructure(self, vals):
        for boxName, item in vals.items():
            docIds = []
            box_id = self.env.context.get('parentId', False)
            child_plm_box = item.get('child_plm_box')
            child_docs = item.get('child_docs')
            for childDoc in child_docs:
                documentID = childDoc.get('documentID')
                if documentID:
                    docIds.append(documentID)
            outVals = {'name': boxName,
                       'description': item.get('description', ''),
                       'plm_box_rel': [],
                       'obj_rel': False,
                       'box_id': box_id,
                       'document_rel': [[6, False, docIds]],
                       }
            BoxId = self.createBox(outVals)
            newContext = self.env.context.copy()
            newContext['parentId'] = BoxId
            for childPlm in child_plm_box:
                self.with_context(newContext).saveStructure(childPlm)
        return True

    @api.model
    def createBox(self, vals):
        '''
            Create a box
        '''
        return self.create(vals)

    @api.model
    def create(self, vals):
        if not vals.get('name', False):
            name = self.getNewSequencedName()
            vals['name'] = name
        return super(Plm_box, self).create(vals)

    @api.multi
    def write(self, vals):
        '''
            Write a new name if not provided
        '''
        for brwsObj in self:
            name = brwsObj.name
            if name in [False, '']:
                name = self.getNewSequencedName()
                vals['name'] = name
        return super(Plm_box, self).write(vals)

    @api.model
    def getNewSequencedName(self):
        '''
            Get new name from sequence
        '''
        return self.env.get('ir.sequence').get('plm.box')

    @api.model
    def getAvaibleGroupsByUser(self):
        '''
            Return ids of avaible groups for user
        '''
        return self.env.get('res.groups').search([('users.id', '=', self.env.uid)]).ids

    @api.model
    def setRelatedDocs(self, parentBrws):
        docRelList = []
        for docBrws in parentBrws.document_rel:
            docRelList.append(docBrws.name)
            if docBrws.name not in self.docs.keys():
                if self.isDocAvaibleForUser(docBrws):
                    self.docs[docBrws.name] = self.getDocDictValues(docBrws)
        self.box_doc_rel[parentBrws.name] = docRelList

    @api.model
    def getRelatedEntities(self, parentBrws):
        objRelList = []
        for brws in parentBrws.product_id:
            outName = brws.name
            objRelList.append({'obj_name': 'Product', 'obj_type': 'product.product', 'obj_rel_name': outName})
        for brws in parentBrws.project_id:
            outName = brws.name
            objRelList.append({'obj_name': 'Project', 'obj_type': 'project.project', 'obj_rel_name': outName})
        for brws in parentBrws.task_id:
            outName = brws.name
            objRelList.append({'obj_name': 'Task', 'obj_type': 'project.task', 'obj_rel_name': outName})
        for brws in parentBrws.sale_ord_id:
            outName = brws.name
            objRelList.append({'obj_name': 'Sale Order', 'obj_type': 'sale.order', 'obj_rel_name': outName})
        for brws in parentBrws.user_rel_id:
            outName = brws.name
            objRelList.append({'obj_name': 'User', 'obj_type': 'res.users', 'obj_rel_name': outName})
        for brws in parentBrws.bom_id:
            outName = brws.name
            objRelList.append({'obj_name': 'Bill of Material', 'obj_type': 'mrp.bom', 'obj_rel_name': outName})
        for brws in parentBrws.wc_id:
            outName = brws.name
            objRelList.append({'obj_name': 'Work Center', 'obj_type': 'mrp.workcenter', 'obj_rel_name': outName})
        return objRelList

    @api.model
    def setRelatedBoxes(self, parentBrws):
        childBoxNames = []
        childBoxes = []
        for boxBrws in parentBrws.plm_box_rel:
            childBoxNames.append(boxBrws.name)
            childBoxes.append(boxBrws)
        self.box_box_rel[parentBrws.name] = childBoxNames
        return childBoxes

    @api.model
    def docReadonlyCompute(self, docIds):
        '''
            Compute if document is readonly
        '''
        docBrws = self.env.get('plm.document').browse(docIds)
        if docBrws.state in ['released', 'undermodify', 'obsoleted']:
            return True
        if not docBrws.ischecked_in():
            check_out_by_me = docBrws._is_checkedout_for_me()
            if check_out_by_me:
                return False
        return True

    @api.multi
    def boxReadonlyCompute(self):
        '''
            Compute if box is readonly
        '''
        for boxBrws in self:
            if boxBrws.state in ['released', 'undermodify', 'obsoleted']:
                return True
        return False

    @api.model
    def getBoxesByFollower(self, avaibleBoxIds):
        '''
            Update avaible boxes due to follower
        '''
        userBrws = self.env.get('res.users').browse(self.env.uid)
        if userBrws:
            if userBrws.partner_id:
                avaibleIds = self.search([('message_follower_ids.id', '=', userBrws.partner_id.id)]).ids
                for idd in avaibleIds:
                    if idd not in avaibleBoxIds:
                        avaibleBoxIds.append(idd)
        return avaibleBoxIds

    @api.model
    def getBoxesByAvaibleParent(self, parents, outList):
        for boxId in parents:
            childBoxes = self.browse(boxId).plm_box_rel
            localList = []
            for brws in childBoxes:
                if brws.id in parents or brws.id in outList:
                    continue
                localList.append(brws.id)
            if not localList:
                continue
            outList = self.getBoxesByAvaibleParent(localList, outList)
            for elem in localList:
                outList.append(elem)
        return outList

    @api.model
    def getBoxes(self, boxes={}):
        '''
            *** CLIENT ***
        '''
        outBoxDict = {}
        avaibleBoxIds = []
        if not boxes:
            return {}
        if boxes:
            for boxName in boxes.keys():
                boxBrwsList = self.search([('name', '=', boxName)])
                avaibleBoxIds.extend(boxBrwsList.ids)
        for boxId in avaibleBoxIds:
            boxBrws = self.browse(boxId)
            self.setRelatedDocs(boxBrws)
            self.box_ent_rel[boxBrws.name] = self.getRelatedEntities(boxBrws)
            childList = self.setRelatedBoxes(boxBrws)
            for childBrws in childList:
                if childBrws.id not in avaibleBoxIds:
                    avaibleBoxIds.append(childBrws.id)
            writeVal = datetime.datetime.strptime(boxBrws.write_date,
                                                  DEFAULT_SERVER_DATETIME_FORMAT)
            outBoxDict[boxBrws.name] = {'boxVersion': boxBrws.version,
                                        'boxDesc': boxBrws.description,
                                        'boxState': boxBrws.state,
                                        'boxReadonly': boxBrws.boxReadonlyCompute(),
                                        'boxWriteDate': correctDate(writeVal, self.env.context),
                                        'boxPrimary': False,
                                        }
            if boxBrws.name in boxes.keys():
                boxPrimary = boxes[boxBrws.name][1]
                outBoxDict[boxBrws.name]['boxPrimary'] = boxPrimary
        return outBoxDict

    @api.model
    def getDocDictValues(self, docBrws):
        getCheckOutUser = ''
        plmDocObj = self.env.get('plm.document')
        docState = plmDocObj.getDocumentState({'docName': docBrws.name})
        if docState in ['check-out', 'check-out-by-me']:
            getCheckOutUser = docBrws.getCheckOutUser()
        writeVal = datetime.datetime.strptime(docBrws.write_date, DEFAULT_SERVER_DATETIME_FORMAT)
        return {'revisionid': docBrws.revisionid,
                'datas_fname': docBrws.datas_fname,
                'create_date': docBrws.create_date,
                'write_date': correctDate(writeVal, self.env.context),
                'description': docBrws.description,
                'fileName': docBrws.datas_fname,
                'state': docBrws.state,
                'readonly': self.docReadonlyCompute(docBrws.id),
                'checkoutUser': getCheckOutUser,
                }

    @api.model
    def getDocs(self, docsToUpdate=[]):
        outDocDict = {}
        docIds = []
        plmDocObj = self.env.get('plm.document')
        userAvaibleBoxIds = self.getAvaibleGroupsByUser()
        if isinstance(docsToUpdate, list):
            for doc in docsToUpdate:
                docBrwsList = plmDocObj.search([('name', '=', doc[0])])
                if not docBrwsList:
                    outDocDict[doc[0]] = {}
                else:
                    docIds.extend(docBrwsList.ids)
        elif docsToUpdate == 'all':
            docIds = plmDocObj.search([]).ids
        else:
            return []
        for docId in docIds:
            boxIds = self.search([('document_rel.id', '=', docId)]).ids
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
        plmUserGroupBrwsList = self.env.get('res.groups').search([('name', '=', 'PLM / Integration User')])
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
            userBrwsList = self.env.get('res.users').search([('partner_id', '=', elem.id)])
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
        self.boxis = self.getBoxes(vals.get('boxesList', []))
        outDict = {'plm_box': self.boxis,
                   'docs': self.docs,
                   'box_doc_rel': self.box_doc_rel,
                   'box_ent_rel': self.box_ent_rel,
                   'box_box_rel': self.box_box_rel,
                   }
        return outDict

    @api.multi
    def action_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def action_confirm(self):
        return self.write({'state': 'confirmed'})

    @api.multi
    def action_release(self):
        return self.write({'state': 'released'})

    @api.multi
    def action_obsolete(self):
        return self.write({'state': 'obsoleted'})

    @api.multi
    def action_reactivate(self):
        return self.write({'state': 'released'})

    @api.model
    def getAvaiableBoxIds(self):
        avaibleBoxIds = []
        groupsIds = self.getAvaibleGroupsByUser()
        avaibleBoxIds = avaibleBoxIds + self.search([('groups_rel.id', 'in', groupsIds)]).ids
        avaibleBoxIds = avaibleBoxIds + self.getBoxesByAvaibleParent(avaibleBoxIds, [])
        avaibleBoxIds = self.getBoxesByFollower(avaibleBoxIds)
        return avaibleBoxIds

    @api.model
    def getAvaiableBoxes(self, vals={}):
        outList = []
        boxesIds = self.getAvaiableBoxIds()
        for boxBrwse in self.browse(boxesIds):
            outList.append([boxBrwse.name,
                            boxBrwse.description,
                            boxBrwse.version,
                            boxBrwse.state,
                            ])
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
                if values[1] == 'box':
                    valsList, boxId = self.checkIfBoxChanged(values)
                    if valsList:
                        outList.append(valsList)
                    if boxId:
                        boxIds.append(boxId)
                elif values[1] == 'document':
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
            outList.append([self.browse(boxId).name, 'box'])
        return outList

    @api.model
    def checkForNewDocuments(self, docIds, avaibleBoxes, outList):
        for boxId in avaibleBoxes:
            boxBrws = self.browse(boxId)
            if boxBrws:
                docBrwsIds = boxBrws.document_rel
                for docBrws in docBrwsIds:
                    if docBrws.id not in docIds:
                        docIds.append(docBrws.id)
                        outList.append([docBrws.name, 'document'])
        return outList

    @api.model
    def checkIfBoxChanged(self, values):
        name, typee, datetimee = values
        boxBrwsList = self.search([('name', '=', name)])
        for boxBrws in boxBrwsList:
            boxId = boxBrws.id
            wr_date = boxBrws.write_date
            if wr_date != 'n/a':
                wr_date = wr_date.split('.')[0]
                serverDatetime = datetime.datetime.strptime(wr_date, DEFAULT_SERVER_DATETIME_FORMAT)
                serverDatetime = correctDate(serverDatetime, self.env.context)
                clientDatetime = datetime.datetime.strptime(datetimee.value, "%Y%m%dT%H:%M:%S")
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
        docObj = self.env.get('plm.document')
        docBrwsList = docObj.search([('name', '=', name)])
        for docBrws in docBrwsList:
            docId = docBrws.id
            if docObj.getDocumentState({'docName': name}) != 'check-in':
                return [], docId
            wr_date = docBrws.write_date
            if wr_date != 'n/a':
                wr_date = wr_date.split('.')[0]
                serverDatetime = datetime.datetime.strptime(wr_date, DEFAULT_SERVER_DATETIME_FORMAT)
                serverDatetime = correctDate(serverDatetime, self.env.context)
                clientDatetime = datetime.datetime.strptime(datetimee.value, "%Y%m%dT%H:%M:%S")
                if serverDatetime > clientDatetime:
                    deltaTime = serverDatetime - clientDatetime
                    if deltaTime.total_seconds() > 2:
                        return [name, typee, ''], docId
                else:
                    return [], docId
        else:
            return [name, typee, 'deleted'], False
        return [], False

    @api.model
    def getBoxesStructureFromServer(self, primaryBoxes):
        '''
            *** CLIENT ***
            Function called by "Add" button in the plm client
        '''
        outDict = {}
        notFoundBoxes = []
        if not primaryBoxes:
            return (outDict, notFoundBoxes)
        for boxName in primaryBoxes:
            boxBrwsList = self.search([('name', '=', boxName)])
            if boxBrwsList:
                outDict[boxName] = boxBrwsList[0].getBoxStructure(True)
            else:
                notFoundBoxes.append(boxName)
        return (outDict, notFoundBoxes)

    @api.multi
    def getBoxStructure(self, primary=False):
        '''
            *** CLIENT ***
            Used in the client in "Add" button procedure
        '''
        outDict = {'children': {},
                   'documents': {},
                   'entities': [],
                   'description': '',
                   'state': 'draft',
                   'readonly': True,
                   'primary': primary,
                   }
        for boxBrws in self:
            for boxChildBrws in boxBrws.plm_box_rel:
                outDict['children'][boxChildBrws.name] = boxChildBrws.getBoxStructure(primary)
            for docBrws in boxBrws.document_rel:
                outDict['documents'][docBrws.name] = self.getDocDictValues(docBrws)
            outDict['entities'] = self.getRelatedEntities(boxBrws)
            outDict['description'] = boxBrws.description
            outDict['state'] = boxBrws.state
            outDict['readonly'] = boxBrws.boxReadonlyCompute()
        return outDict


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
