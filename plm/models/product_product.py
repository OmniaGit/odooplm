# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
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
import logging
from datetime import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo import osv
import odoo.tools as tools

_logger = logging.getLogger(__name__)

USED_STATES = [('draft', _('Draft')),
               ('confirmed', _('Confirmed')),
               ('released', _('Released')),
               ('undermodify', _('UnderModify')),
               ('obsoleted', _('Obsoleted'))]
USEDIC_STATES = dict(USED_STATES)


def emptyStringIfFalse(value):
    """
        return an empty string if the value is False
    """
    if value:
        return unicode(value)
    else:
        return ''


class PlmComponent(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _father_part_compute(self, name='', arg={}):
        """ Gets father bom.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param name: Name of the field
        @param arg: User defined argument
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        bom_line_objType = self.env['mrp.bom.line']
        prod_objs = self.browse(self.ids)
        for prod_obj in prod_objs:
            prod_ids = []
            bom_line_objs = bom_line_objType.search([('product_id', '=', prod_obj.id)])
            for bom_line_obj in bom_line_objs:
                for objPrd in self.search([('product_tmpl_id', '=', bom_line_obj.bom_id.product_tmpl_id.id)]):
                    prod_ids.append(objPrd.id)
            prod_obj.father_part_ids = prod_ids

    linkeddocuments = fields.Many2many('plm.document',
                                       'plm_component_document_rel',
                                       'component_id',
                                       'document_id',
                                       _('Linked Docs'))
    tmp_material = fields.Many2one('plm.material',
                                   _('Raw Material'),
                                   required=False,
                                   change_default=True,
                                   help=_("Select raw material for current product"))
    tmp_surface = fields.Many2one('plm.finishing',
                                  _('Surface Finishing'),
                                  required=False,
                                  change_default=True,
                                  help=_("Select surface finishing for current product"))
    father_part_ids = fields.Many2many('product.product',
                                       compute=_father_part_compute,
                                       string=_("BoM Hierarchy"),
                                       store=False)
    create_date = fields.Datetime(_('Date Created'),
                                  readonly=True)
    write_date = fields.Datetime(_('Date Modified'),
                                 readonly=True)
    std_description = fields.Many2one('plm.description',
                                      _('Standard Description'),
                                      required=False,
                                      change_default=True,
                                      default=False,
                                      help=_("Select standard description for current product."))
    std_umc1 = fields.Char(_('UM / Feature 1'),
                           size=32,
                           default='',
                           help=_("Allow to specifiy a unit measure for the first feature."))
    std_value1 = fields.Float(_('Value 1'),
                              default=0,
                              help=_("Assign value to the first characteristic."))
    std_umc2 = fields.Char(_('UM / Feature 2'),
                           size=32,
                           default='',
                           help=_("Allow to specifiy a unit measure for the second feature."))
    std_value2 = fields.Float(_('Value 2'),
                              default=0,
                              help=_("Assign value to the second characteristic."))
    std_umc3 = fields.Char(_('UM / Feature 3'),
                           size=32,
                           default='',
                           help=_("Allow to specifiy a unit measure for the third feature."))
    std_value3 = fields.Float(_('Value 3'),
                              default=0,
                              help=_("Assign value to the second characteristic."))

    # Don't overload std_umc1, std_umc2, std_umc3 setting them related to std_description because odoo try to set value
    # of related fields and integration users doesn't have write permissions in std_description. The result is that
    # integration users can't create products if in changed values there is std_description

    @api.onchange('std_description')
    def on_change_stddesc(self):
        if self.std_description:
            if self.std_description.description:
                self.description = self.std_description.description
                if self.std_description.umc1:
                    self.std_umc1 = self.std_description.umc1
                if self.std_description.umc2:
                    self.std_umc2 = self.std_description.umc2
                if self.std_description.umc3:
                    self.std_umc3 = self.std_description.umc3
                if self.std_description.unitab:
                    self.description = self.description + " " + self.std_description.unitab

    @api.onchange('std_value1', 'std_value2', 'std_value3')
    def on_change_stdvalue(self):
        if self.std_description:
            if self.std_description.description:
                self.description = self.computeDescription(self.std_description, self.std_description.description, self.std_umc1, self.std_umc2, self.std_umc3, self.std_value1, self.std_value2, self.std_value3)

    @api.onchange('name')
    def on_change_name(self):
        if self.name:
            results = self.search([('name', '=', self.name)])
            if len(results) > 0:
                raise UserError(_("Part %s already exists.\nClose with OK to reuse, with Cancel to discharge." % (self.name)))
            if not self.engineering_code:
                self.engineering_code = self.name

    @api.onchange('tmp_material')
    def on_change_tmpmater(self):
        if self.tmp_material:
            if self.tmp_material.name:
                self.engineering_material = unicode(self.tmp_material.name)

    @api.onchange('tmp_surface')
    def on_change_tmpsurface(self):
        if self.tmp_surface:
            if self.tmp_surface.name:
                self.engineering_surface = unicode(self.tmp_surface.name)

#   Internal methods
    def _packfinalvalues(self, fmt, value=False, value2=False, value3=False):
        """
            Pack a string formatting it like specified in fmt
            mixing both label and value or only label.
        """
        retvalue = ''
        if value3:
            if isinstance(value3, float):
                svalue3 = "%g" % value3
            else:
                svalue3 = value3
        else:
            svalue3 = ''

        if value2:
            if isinstance(value2, float):
                svalue2 = "%g" % value2
            else:
                svalue2 = value2
        else:
            svalue2 = ''

        if value:
            if isinstance(value, float):
                svalue = "%g" % value
            else:
                svalue = value
        else:
            svalue = ''

        if svalue or svalue2 or svalue3:
            cnt = fmt.count('%s')
            if cnt == 3:
                retvalue = fmt % (svalue, svalue2, svalue3)
            if cnt == 2:
                retvalue = fmt % (svalue, svalue2)
            elif cnt == 1:
                retvalue = fmt % (svalue)
        return retvalue

    def _packvalues(self, fmt, label=False, value=False):
        """
            Pack a string formatting it like specified in fmt
            mixing both label and value or only label.
        """
        retvalue = ''
        if value:
            if isinstance(value, float):
                svalue = "%g" % value
            else:
                svalue = value
        else:
            svalue = ''

        if label:
            if isinstance(label, float):
                slabel = "%g" % label
            else:
                slabel = label
        else:
            slabel = ''

        if svalue:
            cnt = fmt.count('%s')

            if cnt == 2:
                retvalue = fmt % (slabel, svalue)
            elif cnt == 1:
                retvalue = fmt % (svalue)
        return retvalue

    def computeDescription(self, thisObject, initialVal, std_umc1, std_umc2, std_umc3, std_value1, std_value2, std_value3):
        description1 = False
        description2 = False
        description3 = False
        description = initialVal
        if thisObject.fmtend:
            if std_umc1 and std_value1:
                description1 = self._packvalues(thisObject.fmt1, std_umc1, std_value1)
            if std_umc2 and std_value2:
                description2 = self._packvalues(thisObject.fmt2, std_umc2, std_value2)
            if std_umc3 and std_value3:
                description3 = self._packvalues(thisObject.fmt3, std_umc3, std_value3)
            description = description + " " + self._packfinalvalues(thisObject.fmtend, description1, description2, description3)
        else:
            if std_umc1 and std_value1:
                description = description + " " + self._packvalues(thisObject.fmt1, std_umc1, std_value1)
            if std_umc2 and std_value2:
                description = description + " " + self._packvalues(thisObject.fmt2, std_umc2, std_value2)
            if std_umc3 and std_value3:
                description = description + " " + self._packvalues(thisObject.fmt3, std_umc3, std_value3)
        if thisObject.unitab:
            description = description + " " + thisObject.unitab
        return description


    @api.multi
    def product_template_open(self):
        product_id = self.product_tmpl_id.id
        mod_obj = self.env['ir.model.data']
        search_res = mod_obj.get_object_reference('plm', 'product_template_form_view_plm_custom')
        form_id = search_res and search_res[1] or False
        if product_id and form_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Product Engineering'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.template',
                'res_id': product_id,
                'views': [(form_id, 'form')],
            }

    @api.multi
    def open_boms(self):
        product_tmpl_id = self.product_tmpl_id.id
        if product_tmpl_id:
            localCtx = self.env.context.copy()
            localCtx.update({'default_product_tmpl_id': product_tmpl_id,
                             'search_default_product_tmpl_id': product_tmpl_id})
            return {'type': 'ir.actions.act_window',
                    'name': _('Mrp Bom'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'mrp.bom',
                    'context': localCtx,
                    }

    @api.model
    def _getChildrenBom(self, component, level=0, currlevel=0):
        """
            Return a flat list of each child, listed once, in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        result = []
        bufferdata = []
        if level == 0 and currlevel > 1:
            return bufferdata
        for bomid in component.product_tmpl_id.bom_ids:
            for bomline in bomid.bom_line_ids:
                children = self._getChildrenBom(bomline.product_id, level, currlevel + 1)
                bufferdata.extend(children)
                bufferdata.append(bomline.product_id.id)
        result.extend(bufferdata)
        return list(set(result))

    @api.model
    def RegMessage(self, request, default=None):
        """
            Registers a message for requested component
        """
        oid, message = request
        self.browse([oid]).wf_message_post(body=_(message))
        return False

    @api.model
    def getLastTime(self, oid, default=None):
        return self.getUpdTime(self.browse(oid))

    def getUpdTime(self, obj):
        if(obj.write_date is not False):
            return datetime.strptime(obj.write_date, '%Y-%m-%d %H:%M:%S')
        else:
            return datetime.strptime(obj.create_date, '%Y-%m-%d %H:%M:%S')

    @api.multi
    def Clone(self, defaults={}):
        exitValues = {}
        newCompBrws = self.copy(defaults)
        if newCompBrws not in (None, False):
            exitValues['_id'] = newCompBrws.id
            exitValues['name'] = newCompBrws.name
            exitValues['engineering_code'] = newCompBrws.engineering_code
            exitValues['engineering_revision'] = newCompBrws.engineering_revision
        return exitValues

    @api.model
    def GetUpdated(self, vals):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        partData, attribNames, forceCADProperties = vals
        ids = self.GetLatestIds(partData, forceCADProperties=forceCADProperties)
        return self.browse(list(set(ids))).read(attribNames)

    @api.model
    def GetLatestIds(self, vals, forceCADProperties=False):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        ids = []
        plmDocObj = self.env['plm.document']

        def getCompIds(partName, partRev):
            if docRev is None or docRev is False:
                partIds = self.search([('engineering_code', '=', partName)],
                                      order='engineering_revision').ids
                if len(partIds) > 0:
                    ids.append(partIds[-1])
            else:
                ids.extend(self.search([('engineering_code', '=', partName),
                                        ('engineering_revision', '=', partRev)]).ids)

        for docName, docRev, docIdToOpen in vals:
            checkOutUser = plmDocObj.browse(docIdToOpen).get_checkout_user()
            if checkOutUser:
                isMyDocument = plmDocObj.isCheckedOutByMe(docIdToOpen)
                if isMyDocument and forceCADProperties:
                    return []    # Document properties will be not updated
                else:
                    getCompIds(docName, docRev)
            else:
                getCompIds(docName, docRev)
        return list(set(ids))

    @api.model
    def SaveOrUpdate(self, vals):
        """
            Save or Update Parts
        """
        listedParts = []
        retValues = []
        for partVals in vals:
            hasSaved = False
            if partVals.get('engineering_code', '') in listedParts:
                continue
            if 'engineering_code' not in partVals:
                partVals['componentID'] = False
                partVals['hasSaved'] = hasSaved
                continue
            existingCompBrwsList = self.search([('engineering_code', '=', partVals['engineering_code']),
                                                ('engineering_revision', '=', partVals['engineering_revision'])], order='engineering_revision ASC')
            if not existingCompBrwsList:
                existingCompBrwsList = [self.create(partVals)]
                hasSaved = True
            for existingCompBrws in existingCompBrwsList:
                partVals['name'] = existingCompBrws.name
                if (self.getUpdTime(existingCompBrws) < datetime.strptime(partVals['lastupdate'], '%Y-%m-%d %H:%M:%S')):
                    if self._iswritable(existingCompBrws):
                        del(partVals['lastupdate'])
                        if not existingCompBrws.write(partVals):
                            raise UserError(_("Part %r cannot be updated" % (partVals['engineering_code'])))
                        hasSaved = True
            partVals['componentID'] = existingCompBrws.id
            partVals['hasSaved'] = hasSaved
            retValues.append(partVals)
            listedParts.append(partVals['engineering_code'])
        return retValues

    @api.model
    def QueryLast(self, request=([], []), default=None):
        """
            Query to return values based on columns selected.
        """
        objId = False
        expData = []
        queryFilter, columns = request
        if len(columns) < 1:
            return expData
        if 'engineering_revision' in queryFilter:
            del queryFilter['engineering_revision']
        allIDs = self.search(queryFilter,
                             order='engineering_revision').ids
        if len(allIDs) > 0:
            allIDs.sort()
            objId = allIDs[len(allIDs) - 1]
        if objId:
            tmpData = self.export_data([objId], columns)
            if 'datas' in tmpData:
                expData = tmpData['datas']
        return expData

    @api.model
    def _summarizeBom(self, datarows):
        dic = {}
        for datarow in datarows:
            key = str(datarow.product_id.id)
            if key in dic:
                dic[key].product_qty = float(dic[key].product_qty) + float(datarow.product_qty)
            else:
                dic[key] = datarow
        retd = dic.values()
        return retd

    @api.multi
    def _get_recursive_parts(self, excludeStatuses, includeStatuses):
        """
           Get all ids related to current one as children
        """
        errors = []
        tobeReleasedIDs = []
        if not isinstance(self.ids, (list, tuple)):
            self.ids = [self.ids]
        tobeReleasedIDs.extend(self.ids)
        for prodBrws in self:
            for childProdBrws in self.browse(self._getChildrenBom(prodBrws, 1)):
                if (childProdBrws.state not in excludeStatuses) and (childProdBrws.state not in includeStatuses):
                    errors.append(_("Product code: %r revision %r status %r") % (childProdBrws.engineering_code, childProdBrws.engineering_revision, childProdBrws.state))
                    continue
                if childProdBrws.state in includeStatuses:
                    if childProdBrws.id not in tobeReleasedIDs:
                        tobeReleasedIDs.append(childProdBrws.id)
        msg = ''
        if errors:
            msg = _("Unable to perform workFlow action due")
            for subMsg in errors:
                msg = msg + "\n" + subMsg
        return (msg, list(set(tobeReleasedIDs)))

    @api.multi
    def action_create_normalBom_WF(self):
        """
            Create a new Normal Bom if doesn't exist (action callable from code)
        """
        for prodId in self.ids:
            self.processedIds = []
            self._create_normalBom(prodId)
        self.wf_message_post(body=_('Created Normal Bom.'))
        return False

    @api.multi
    def _action_ondocuments(self, action_name):
        """
            move workflow on documents having the same state of component
        """
        docIDs = []
        docInError = []
        documentType = self.env['plm.document']
        for oldObject in self:
            if (action_name != 'transmit') and (action_name != 'reject') and (action_name != 'release'):
                check_state = oldObject.state
            else:
                check_state = 'confirmed'
            for documentBrws in oldObject.linkeddocuments:
                if documentBrws.state == check_state:
                    if documentBrws.is_checkout:
                        docInError.append(_("Document %r : %r is checked out by user %r") % (documentBrws.name, documentBrws.revisionid, documentBrws.checkout_user))
                        continue
                    if documentBrws.id not in docIDs:
                        docIDs.append(documentBrws.id)
        if docInError:
            msg = "Error on workflow operation"
            for e in docInError:
                msg = msg + "\n" + e
            raise UserError(msg)

        if len(docIDs) > 0:
            docBrws = documentType.browse(docIDs)
            if action_name == 'confirm':
                docBrws.signal_workflow(action_name)
            elif action_name == 'transmit':
                docBrws.signal_workflow('confirm')
            elif action_name == 'draft':
                docBrws.signal_workflow('correct')
            elif action_name == 'correct':
                docBrws.signal_workflow(action_name)
            elif action_name == 'reject':
                docBrws.signal_workflow('correct')
            elif action_name == 'release':
                docBrws.signal_workflow(action_name)
            elif action_name == 'undermodify':
                docBrws.action_cancel()
            elif action_name == 'suspend':
                docBrws.action_suspend()
            elif action_name == 'reactivate':
                docBrws.signal_workflow('release')
            elif action_name == 'obsolete':
                docBrws.signal_workflow(action_name)
        return docIDs

    @api.model
    def _iswritable(self, oid):
        checkState = ('draft')
        if not oid.engineering_writable:
            logging.warning("_iswritable : Part (%r - %d) is not writable." % (oid.engineering_code, oid.engineering_revision))
            return False
        if oid.state not in checkState:
            logging.warning("_iswritable : Part (%r - %d) is in status %r." % (oid.engineering_code, oid.engineering_revision, oid.state))
            return False
        if not oid.engineering_code:
            logging.warning("_iswritable : Part (%r - %d) is without Engineering P/N." % (oid.name, oid.engineering_revision))
            return False
        return True

    @api.multi
    def wf_message_post(self, body=''):
        """
            Writing messages to follower, on multiple objects
        """
        if not (body == ''):
            for compObj in self:
                compObj.message_post(body=_(body))

    @api.multi
    def unlink(self):
        values = {'state': 'released'}
        checkState = ('undermodify', 'obsoleted')
        for checkObj in self:
            prodBrwsList = self.search([('engineering_code', '=', checkObj.engineering_code),
                                        ('engineering_revision', '=', checkObj.engineering_revision - 1)])
            if len(prodBrwsList) > 0:
                oldObject = prodBrwsList[0]
                if oldObject.state in checkState:
                    oldObject.wf_message_post(body=_('Removed : Latest Revision.'))
                    if not self.browse([oldObject.id]).write(values):
                        logging.warning("unlink : Unable to update state to old component (%r - %d)." % (oldObject.engineering_code, oldObject.engineering_revision))
                        return False
        return super(PlmComponent, self).unlink()

    @api.multi
    def action_draft(self):
        """
            release the object
        """
        for compObj in self:
            defaults = {}
            status = 'draft'
            action = 'draft'
            docaction = 'draft'
            defaults['engineering_writable'] = True
            defaults['state'] = status
            excludeStatuses = ['draft', 'released', 'undermodify', 'obsoleted']
            includeStatuses = ['confirmed', 'transmitted']
            compObj._action_to_perform(status, action, docaction, defaults, excludeStatuses, includeStatuses)
        return True

    @api.multi
    def action_confirm(self):
        """
            action to be executed for Draft state
        """
        for compObj in self:
            defaults = {}
            status = 'confirmed'
            action = 'confirm'
            docaction = 'confirm'
            defaults['engineering_writable'] = False
            defaults['state'] = status
            excludeStatuses = ['confirmed', 'transmitted', 'released', 'undermodify', 'obsoleted']
            includeStatuses = ['draft']
            compObj._action_to_perform(status, action, docaction, defaults, excludeStatuses, includeStatuses)
        return True

    @api.model
    def _getbyrevision(self, name, revision):
        return self.search([('engineering_code', '=', name),
                            ('engineering_revision', '=', revision)])

    @api.multi
    def action_release(self):
        """
           action to be executed for Released state
        """
        for compObj in self:
            childrenProductToEmit = []
            product_tmpl_ids = []
            defaults = {}
            prodTmplType = self.env['product.template']
            excludeStatuses = ['released', 'undermodify', 'obsoleted']
            includeStatuses = ['confirmed']
            errors, product_ids = compObj._get_recursive_parts(excludeStatuses, includeStatuses)
            if len(product_ids) < 1 or len(errors) > 0:
                raise UserError(errors)
            allProdObjs = self.browse(product_ids)
            for oldProductBrw in allProdObjs:
                last_id = self._getbyrevision(oldProductBrw.engineering_code, oldProductBrw.engineering_revision - 1)
                if last_id is not None:
                    defaults['engineering_writable'] = False
                    defaults['state'] = 'obsoleted'
                    last_id.product_tmpl_id.write(defaults)
                    last_id.wf_message_post(body=_('Status moved to: %s.' % (USEDIC_STATES[defaults['state']])))
                defaults['engineering_writable'] = False
                defaults['state'] = 'released'
            self.browse(product_ids)._action_ondocuments('release')
            for currentProductId in allProdObjs:
                if not(currentProductId.id in self.ids):
                    childrenProductToEmit.append(currentProductId.id)
                product_tmpl_ids.append(currentProductId.product_tmpl_id.id)
            self.browse(childrenProductToEmit).signal_workflow('release')
            objId = prodTmplType.browse(product_tmpl_ids).write(defaults)
            if (objId):
                self.browse(product_ids).wf_message_post(body=_('Status moved to: %s.' % (USEDIC_STATES[defaults['state']])))
            return objId
        return False

    @api.multi
    def action_obsolete(self):
        """
            obsolete the object
        """
        for compObj in self:
            defaults = {}
            status = 'obsoleted'
            action = 'obsolete'
            docaction = 'obsolete'
            defaults['engineering_writable'] = False
            defaults['state'] = status
            excludeStatuses = ['draft', 'confirmed', 'transmitted', 'undermodify', 'obsoleted']
            includeStatuses = ['released']
            compObj._action_to_perform(status, action, docaction, defaults, excludeStatuses, includeStatuses)
        return True

    @api.multi
    def action_reactivate(self):
        """
            reactivate the object
        """
        for compObj in self:
            defaults = {}
            status = 'released'
            action = ''
            docaction = 'release'
            defaults['engineering_writable'] = True
            defaults['state'] = status
            excludeStatuses = ['draft', 'confirmed', 'transmitted', 'released', 'undermodify', 'obsoleted']
            includeStatuses = ['obsoleted']
            compObj._action_to_perform(status, action, docaction, defaults, excludeStatuses, includeStatuses)
        return True

    @api.multi
    def _action_to_perform(self, status, action, docaction, defaults=[], excludeStatuses=[], includeStatuses=[]):
        tmpl_ids = []
        full_ids = []
        userErrors, allIDs = self._get_recursive_parts(excludeStatuses, includeStatuses)
        if userErrors:
            raise UserError(userErrors)
        allIdsBrwsList = self.browse(allIDs)
        allIdsBrwsList._action_ondocuments(docaction)
        for currId in allIdsBrwsList:
            if not(currId.id in self.ids):
                tmpl_ids.append(currId.product_tmpl_id.id)
            full_ids.append(currId.product_tmpl_id.id)
        if action:
            self.browse(tmpl_ids).signal_workflow(action)
        objId = self.env['product.template'].browse(full_ids).write(defaults)
        if objId:
            self.browse(allIDs).wf_message_post(body=_('Status moved to: %s.' % (USEDIC_STATES[defaults['state']])))
        return objId

#  ######################################################################################################################################33

    @api.model
    def create(self, vals):
        if not vals:
            raise ValidationError(_("""You are trying to create a product without values"""))
        if ('name' in vals):
            if not vals['name']:
                return False
            if 'engineering_code' in vals:
                if vals['engineering_code'] == False:
                    vals['engineering_code'] = vals['name']
            else:
                vals['engineering_code'] = vals['name']
            if 'engineering_revision' in vals:
                prodBrwsList = self.search([('engineering_code', '=', vals['engineering_code']),
                                            ('engineering_revision', '=', vals['engineering_revision'])
                                            ])
                if prodBrwsList:
                    raise UserError('Component %r already exists' % (vals['engineering_code']))
                    #return prodBrwsList[len(prodBrwsList) - 1]
        try:
            return super(PlmComponent, self).create(vals)
        except Exception, ex:
            import psycopg2
            if isinstance(ex, psycopg2.IntegrityError):
                raise ex
            logging.error("(%s). It has tried to create with values : (%s)." % (unicode(ex), unicode(vals)))
            raise Exception(_(" (%r). It has tried to create with values : (%r).") % (ex, vals))

    @api.multi
    def copy(self, defaults={}):
        """
            Overwrite the default copy method
        """
        previous_name = self.name
        if not defaults.get('name', False):
            defaults['name'] = '-'                   # If field is required super of clone will fail returning False, this is the case
            defaults['engineering_code'] = '-'
            defaults['engineering_revision'] = 0
        # assign default value
        defaults['state'] = 'draft'
        defaults['engineering_writable'] = True
        defaults['write_date'] = None
        defaults['linkeddocuments'] = []
        objId = super(PlmComponent, self).copy(defaults)
        if (objId):
            self.wf_message_post(body=_('Copied starting from : %s.' % previous_name))
        return objId

    @api.model
    def translateForClient(self, values=[], forcedLang=''):
        '''
            Get values attribute in this format:
            values = [{'field1':value1,'field2':value2,...}]     only one element in the list!!!
            and return computed values due to language
            Get also forcedLang attribute in this format:
            forcedLang = 'en_US'
            if is not set it takes language from user
        '''
        language = forcedLang
        if not forcedLang:
            resDict = self.env['res.users'].read(['lang'])
            language = resDict.get('lang', '')
        if values:
            values = values[0]
        if language and values:
            toRead = filter(lambda x: type(x) in [str, unicode] and x, values.values())     # Where computed only string and not null string values (for performance improvement)
            toRead = list(set(toRead))                                                      # Remove duplicates
            for fieldName, valueToTranslate in values.items():
                if valueToTranslate not in toRead:
                    continue
                translationObj = self.env['ir.translation']
                translationBrwsList = translationObj.search([('lang', '=', language),
                                                             ('src', '=', valueToTranslate)])
                if translationBrwsList:
                    readDict = translationBrwsList[0].read(['value'])
                    values[fieldName] = readDict.get('value', '')
        return values

    @api.multi
    def action_rev_docs(self):
        '''
            This function is called by the button on component view, section LinkedDocuments
            Clicking that button all documents related to all revisions of this component are opened in a tree view
        '''
        docIds = []
        for compBrws in self:
            engineering_code = compBrws.engineering_code
            if not engineering_code:
                logging.warning("Part %s doesn't have and engineering code!" % (compBrws.name))
                continue
            compBrwsList = self.search([('engineering_code', '=', engineering_code)])
            for compBrws in compBrwsList:
                docIds.extend(compBrws.linkeddocuments.ids)
        return {'domain': [('id', 'in', docIds)],
                'name': _('Related documents'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'plm.document',
                'type': 'ir.actions.act_window',
                }

    @api.multi
    def action_view_mos(self):
        tmplBrws = self.product_tmpl_id
        if tmplBrws:
            return tmplBrws.action_view_mos()
        logging.warning('[action_view_mos] product with id %s does not have a related template' % (self.id))

    @api.multi
    def NewRevision(self):
        """
            create a new revision of current component
        """
        newComponentId = False
        engineering_revision = 0
        for tmpObject in self:
            latestIDs = self.GetLatestIds([(tmpObject.engineering_code, tmpObject.engineering_revision, False)])
            for oldObject in self.browse(latestIDs[-1]):
                engineering_revision = int(oldObject.engineering_revision) + 1
                oldProdVals = {'engineering_writable': False,
                               'state': 'undermodify'}
                self.browse([oldObject.id]).write(oldProdVals)
                oldObject.wf_message_post(body=_('Status moved to: %s.' % (USEDIC_STATES[oldProdVals['state']])))
                # store updated infos in "revision" object
                defaults = {}
                defaults['name'] = oldObject.name                 # copy function needs an explicit name value
                defaults['engineering_code'] = oldObject.engineering_code
                defaults['engineering_revision'] = engineering_revision
                defaults['engineering_writable'] = True
                defaults['state'] = 'draft'
                defaults['linkeddocuments'] = []                  # Clean attached documents for new revision object
                newCompBrws = oldObject.copy(defaults)
                oldObject.wf_message_post(body=_('Created : New Revision.'))
                newComponentId = newCompBrws.id
                break
            break
        return (newComponentId, engineering_revision)

    @api.model
    def wf_message_post_client(self, args):
        '''
            args = [objId, objMessage]
        '''
        objId, objMessage = args
        self.browse(objId).wf_message_post(objMessage)
        return True

    @api.model
    def getBomRowCad(self, bomLineBrowse):
        """
        give back the lines
        """
        return [bomLineBrowse.itemnum,
                emptyStringIfFalse(bomLineBrowse.product_id.description),
                self._translate(emptyStringIfFalse(bomLineBrowse.product_id.description), 'english'),
                bomLineBrowse.product_id.engineering_code,
                bomLineBrowse.product_qty]

    @api.model
    def getNormalBomStd(self, args):
        """
            get the normal bom from the given name and revision
            RELPOS,
            $G{COMPDES="-"} / $G{COMPDES_L2="-"},
            $G{COMPNAME:f("#clear(<undef>@)")},
            $G{RELQTY},
            $G{COMPR1="-"}
            $G{COMPR2="-"}
        """
        componentName, componentRev, bomType = args
        logging.info('getNormalBom for compoent: %s, componentRev: %s' % (componentName, componentRev))
        out = []
        searchFilter = [('engineering_code', '=', componentName),
                        ('engineering_revision', '=', componentRev)]
        compBrwsList = self.search(searchFilter)
        for objBrowse in compBrwsList:
            for bomBrowse in objBrowse.bom_ids:
                if str(bomBrowse.type).lower() == bomType:
                    for bomLineBrowse in bomBrowse.bom_line_ids:
                        out.append(self.getBomRowCad(bomLineBrowse))
        return out

    def _translate(self, cr, uid, dataValue="", languageName=""):
        _LOCALLANGS = {'french': ('French_France', 'fr_FR',),
                       'italian': ('Italian_Italy', 'it_IT',),
                       'polish': ('Polish_Poland', 'pl_PL',),
                       'svedish': ('Svedish_Svenska', 'sw_SE',),
                       'russian': ('Russian_Russia', 'ru_RU',),
                       'english': ('English UK', 'en_GB',),
                       'spanish': ('Spanish_Spain', 'es_ES',),
                       'german': ('German_Germany', 'de_DE',),
                       }
        if not dataValue:
            return ""
        if languageName in _LOCALLANGS:
            language = _LOCALLANGS[languageName][1]
            transObj = self.pool.get('ir.translation')
            resIds = transObj.search(cr, uid,
                                     [('src', '=', dataValue),
                                      ('lang', '=', language)])
            for trans in transObj.browse(cr, uid, resIds):
                return trans.value
        return ""

PlmComponent()


class PlmTemporayMessage(osv.osv.osv_memory):
    _name = "plm.temporary.message"
    _description = "Temporary Class"
    name = fields.Text(_('Bom Result'), readonly=True)

PlmTemporayMessage()


class ProductProductDashboard(models.Model):
    _name = "report.plm_component"
    _description = "Report Component"
    _auto = False
    count_component_draft = fields.Integer(_('Draft'),
                                           readonly=True,
                                           translate=True)
    count_component_confirmed = fields.Integer(_('Confirmed'),
                                               readonly=True,
                                               translate=True)
    count_component_released = fields.Integer(_('Released'),
                                              readonly=True,
                                              translate=True)
    count_component_modified = fields.Integer(_('Under Modify'),
                                              readonly=True,
                                              translate=True)
    count_component_obsoleted = fields.Integer(_('Obsoleted'),
                                               readonly=True,
                                               translate=True)

    @api.model
    def init(self):
        cr = self.env.cr
        tools.drop_view_if_exists(cr, 'report_plm_component')
        cr.execute("""
            CREATE OR REPLACE VIEW report_plm_component AS (
                SELECT
                    (SELECT min(id) FROM product_template) as id,
                    (SELECT count(*) FROM product_template WHERE state = 'draft') AS count_component_draft,
                    (SELECT count(*) FROM product_template WHERE state = 'confirmed') AS count_component_confirmed,
                    (SELECT count(*) FROM product_template WHERE state = 'released') AS count_component_released,
                    (SELECT count(*) FROM product_template WHERE state = 'undermodify') AS count_component_modified,
                    (SELECT count(*) FROM product_template WHERE state = 'obsoleted') AS count_component_obsoleted
             )
        """)

ProductProductDashboard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
