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
import json

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
    document_rel = fields.Many2many('ir.attachment',
                                    'ir_attachment_rel',
                                    'name',
                                    'ir_attachment_id',
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
        def check(docs_to_unlink):
            for doc_to_unlink in docs_to_unlink:
                doc_brws = self.env['ir.attachment'].browse(doc_to_unlink)
                if doc_brws.is_checkout:
                    raise UserError('You cannot unlink a document in check-out %r, file name %r' % (doc_brws.display_name, doc_brws.datas_fname))

        for brwsObj in self:
            name = brwsObj.name
            if name in [False, '']:
                name = self.getNewSequencedName()
                vals['name'] = name
            documents = vals.get('document_rel', [])
            for elem in documents:
                if elem[0] in [2, 3]: # Unlink document or remove relation
                    docs_to_unlink = elem[1]
                    check(docs_to_unlink)
                elif elem[0] == 5:
                    check(brwsObj.document_rel.ids)
                elif elem[0] == 6:
                    docs_to_keep = elem[2]
                    docs_to_unlink = [x for x in brwsObj.document_rel.ids if x not in docs_to_keep]
                    check(docs_to_unlink)
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
    def getBoxesByUser(self):
        return self.search([('user_rel_id.id', '=', self.env.uid)]).ids

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
    def setRelatedEntities(self, parentBrws, outDict):
        
        def populationLoop(brws_record, outDict, field_name):
            obj_name = self.env['ir.model'].search([('model', '=', brws_record._name)]).display_name
            for brws in brws_record:
                if field_name not in outDict['entities']:
                    outDict['entities'][field_name] = {}
                outDict['entities'][field_name][str(brws.id)] = {'obj_name': obj_name, 'obj_type': brws._name, 'obj_rel_name': brws.display_name, 'id': brws.id}
        
        outDict['document_rel'] = parentBrws.document_rel.ids
        outDict['product_id'] = parentBrws.product_id.ids
        outDict['project_id'] = parentBrws.project_id.ids
        outDict['task_id'] = parentBrws.task_id.ids
        outDict['sale_ord_id'] = parentBrws.sale_ord_id.ids
        outDict['user_rel_id'] = parentBrws.user_rel_id.ids
        outDict['bom_id'] = parentBrws.bom_id.ids
        outDict['wc_id'] = parentBrws.wc_id.ids
        outDict['entities'] = {}
        
        populationLoop(parentBrws.product_id, outDict, 'product_id')
        populationLoop(parentBrws.project_id, outDict, 'project_id')
        populationLoop(parentBrws.task_id, outDict, 'task_id')
        populationLoop(parentBrws.sale_ord_id, outDict, 'sale_ord_id')
        populationLoop(parentBrws.user_rel_id, outDict, 'user_rel_id')
        populationLoop(parentBrws.bom_id, outDict, 'bom_id')
        populationLoop(parentBrws.wc_id, outDict, 'wc_id')
        for document in parentBrws.document_rel:
            if 'document_rel' not in outDict['entities']:
                outDict['entities']['document_rel'] = {}
            outDict['entities']['document_rel'][str(document.id)] = self.getDocDictValues(document)

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
        docBrws = self.env.get('ir.attachment').browse(docIds)
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
    def getDocDictValues(self, docBrws):
        getCheckOutUser = ''
        docState = docBrws.getDocumentState()
        if docState in ['check-out', 'check-out-by-me']:
            getCheckOutUser = docBrws.getCheckOutUser()
        return {'revisionid': docBrws.revisionid,
                'datas_fname': docBrws.datas_fname,
                'create_date': docBrws.create_date,
                'write_date': correctDate(docBrws.write_date, self.env.context),
                'description': docBrws.description,
                'fileName': docBrws.datas_fname,
                'state': docBrws.state,
                'readonly': self.docReadonlyCompute(docBrws.id),
                'checkoutUser': getCheckOutUser,
                'id': docBrws.id,
                'name': docBrws.name,
                }

    @api.model
    def getDocs(self, docsToUpdate=[]):
        outDocDict = {}
        docIds = []
        plmDocObj = self.env.get('ir.attachment')
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
        avaibleBoxIds += self.search([('groups_rel.id', 'in', groupsIds)]).ids
        #avaibleBoxIds += self.getBoxesByAvaibleParent(avaibleBoxIds, [])
        avaibleBoxIds += self.getBoxesByUser()
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
    def checkForNewBoxes(self, boxIds, avaibleBoxes):
        outList = []
        avaibleNewBoxes = list(set(avaibleBoxes) - set(boxIds))
        for boxId in avaibleNewBoxes:
            outList.append([self.browse(boxId).name, 'box'])
        return outList

    @api.model
    def getBoxesStructureFromServer(self, box_ids):
        outDict = {}
        available_boxes = self.getAvaiableBoxIds()
        notFoundBoxes = []
        if not box_ids:
            return (outDict, notFoundBoxes)
        for box_obj in self.browse(box_ids):
            outDict[box_obj.name] = box_obj.getBoxStructure0(available_boxes=available_boxes)
        return (outDict, notFoundBoxes)

    @api.multi
    def getBoxStructure0(self, primary=False, available_boxes=[]):
        '''
            *** CLIENT ***
        '''
        outDict = {'primary': primary,
                   'children': {}
                   }
        for boxBrws in self:
            if boxBrws.id not in available_boxes:
                return {}
            for boxChildBrws in boxBrws.plm_box_rel:
                outDict['children'].setdefault(boxChildBrws.name, {})
                outDict['children'][boxChildBrws.name] = boxChildBrws.getBoxStructure0(False, available_boxes)
            self.setRelatedEntities(boxBrws, outDict)
            outDict['description'] = boxBrws.description or ''
            outDict['state'] = boxBrws.state
            outDict['readonly'] = boxBrws.boxReadonlyCompute()
            outDict['id'] = boxBrws.id
        return outDict


    def checkRecursiveBoxPresent(self, targetBox):
        evaluated = []
        ret = False
        for parentBox in self:
            if parentBox.id in evaluated:
                continue
            for child in parentBox.plm_box_rel:
                if targetBox == child:
                    ret = True
                    break
                ret, childEval = child.checkRecursiveBoxPresent(targetBox)
                evaluated.extend(childEval)
                if ret:
                    break
            evaluated.append(parentBox.id)
        return ret, evaluated

    @api.model
    def canDeleteLocalBox(self, boxName, primaryBoxes):
        targetBox = self.search([('name', '=', boxName)])
        if not targetBox:
            return True
        for primaryBoxName in primaryBoxes:
            if primaryBoxName == boxName:
                continue
            primaryBox = self.search([('name', '=', primaryBoxName)])
            present, _ = primaryBox.checkRecursiveBoxPresent(targetBox)
            if present:
                return False
        return True

    @api.model
    def getBoxStructure(self, box_ids=[]):
        headers = {'name': 'Name',
                   'description': 'Description',
                   'document_rel': 'Documents',
                   'state': 'State',
                   'entities': 'Entities'
                   }
        
        def recursion(box_ids, available_boxes=[]):
            out = []
            for box in self.browse(box_ids):
                if box.id in available_boxes:
                    vals_list = box.read(headers.keys())
                    for vals in vals_list:
                        vals['entities'] = box.computeEntities()
                        children = recursion(box.plm_box_rel.ids, available_boxes)            
                        out.append([vals, children])
            return out
        
        available_boxes = self.getAvaiableBoxIds()
        structure = recursion(box_ids, available_boxes)
        return json.dumps([headers, structure])

    def computeEntities(self):
        
        def compute_obj(out, model_str, brws_rec):
            if brws_rec:
                out += '%s: ' % (model_str)
                for obj in brws_rec:
                    out += ' %r /' % (obj.display_name)
                out = out[:-2]
                out += '\n'
            return out
        
        out = ''
        for box in self:
            out = compute_obj(out, 'Product', box.product_id)
            out = compute_obj(out, 'Project', box.project_id)
            out = compute_obj(out, 'Task', box.task_id)
            out = compute_obj(out, 'Sale Order', box.sale_ord_id)
            out = compute_obj(out, 'Users', box.user_rel_id)
            out = compute_obj(out, 'BOM', box.bom_id)
            out = compute_obj(out, 'Work Centers', box.wc_id)
            out = out[:-2]
            break
        return out

    @api.model
    def verifyBoxesPermissions(self, box_ids):
        to_del = []
        available_boxes = self.getAvaiableBoxIds()
        for box_id in box_ids:
            if box_id not in available_boxes:
                to_del.append(box_id)
        return to_del

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        search_recursion = self.env.context.get('search_recursion', True)
        if not self.env.user.has_group('plm_box.group_plm_box_admin') and search_recursion:
            box_ids = self.with_context(search_recursion=False).getAvaiableBoxIds()
            args.append(('id', 'in', box_ids))
        ret = super(Plm_box, self).search(args, offset=offset, limit=limit, order=order, count=count)
        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
