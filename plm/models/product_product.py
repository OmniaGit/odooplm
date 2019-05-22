##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
#    $Id$F
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
import os
import json

from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import ValidationError
from odoo.exceptions import AccessError
from odoo.exceptions import UserError
from odoo import osv
import odoo.tools as tools

_logger = logging.getLogger(__name__)

USED_STATES = [
    ('draft', _('Draft')),
    ('confirmed', _('Confirmed')),
    ('released', _('Released')),
    ('undermodify', _('UnderModify')),
    ('obsoleted', _('Obsoleted'))
]
USE_DIC_STATES = dict(USED_STATES)


def emptyStringIfFalse(value):
    """
        return an empty string if the value is False
    """
    if value:
        return str(value)
    else:
        return ''


class PlmComponent(models.Model):
    _inherit = 'product.product'

    @api.multi
    def action_show_reference(self):
        ctx = self.env.context.copy()
        ctx.update({'active_id': self.id,
                    'active_ids': self.ids})
        return {'type': 'ir.actions.client',
                'tag': 'plm_exploded_view',
                'context': ctx}

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

    linkeddocuments = fields.Many2many('ir.attachment',
                                       'plm_component_document_rel',
                                       'component_id',
                                       'document_id',
                                       _('Linked Docs'))
    tmp_material = fields.Many2one('plm.material',
                                   _('Raw Material'),
                                   required=False,
                                   help=_("Select raw material for current product"))
    tmp_surface = fields.Many2one('plm.finishing',
                                  _('Surface Finishing'),
                                  required=False,
                                  help=_("Select surface finishing for current product"))
    tmp_treatment = fields.Many2one('plm.treatment',
                                    _('Termic Treatment'),
                                    required=False,
                                    help=_("Select termic treatment for current product"))
    father_part_ids = fields.Many2many('product.product',
                                       compute=_father_part_compute,
                                       string=_("BoM Hierarchy"),
                                       store=False)
    create_date = fields.Datetime(_('Date Created'),
                                  readonly=True)
    write_date = fields.Datetime(_('Date Modified'),
                                 readonly=True)
    release_date = fields.Datetime(_('Release Date'),
                                   readonly=True)
    std_description = fields.Many2one('plm.description',
                                      _('Standard Description'),
                                      required=False,
                                      default=False,
                                      help=_("Select standard description for current product."))
    std_umc1 = fields.Char(_('UM / Feature 1'),
                           size=32,
                           default='',
                           help=_("Allow to specify a unit measure for the first feature."))
    std_value1 = fields.Float(_('Value 1'),
                              default=0,
                              help=_("Assign value to the first characteristic."))
    std_umc2 = fields.Char(_('UM / Feature 2'),
                           size=32,
                           default='',
                           help=_("Allow to specify a unit measure for the second feature."))
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

    desc_modify = fields.Text(_('Modification Description'), default='')
    source_product = fields.Many2one('product.product', _('Generated From'))
    # Don't overload std_umc1, std_umc2, std_umc3 setting them related to std_description because odoo try to set value
    # of related fields and integration users doesn't have write permissions in std_description. The result is that
    # integration users can't create products if in changed values there is std_description

    @api.onchange('std_description')
    def on_change_stddesc(self):
        if self.std_description:
            if self.std_description.description:
                self.name = self.std_description.description
                if self.std_description.umc1:
                    self.std_umc1 = self.std_description.umc1
                if self.std_description.umc2:
                    self.std_umc2 = self.std_description.umc2
                if self.std_description.umc3:
                    self.std_umc3 = self.std_description.umc3
                if self.std_description.unitab:
                    self.name = self.name + " " + self.std_description.unitab

    @api.onchange('std_value1', 'std_value2', 'std_value3')
    def on_change_stdvalue(self):
        if self.std_description:
            if self.std_description.description:
                self.name = self.computeDescription(self.std_description, self.std_description.description, self.std_umc1, self.std_umc2, self.std_umc3, self.std_value1, self.std_value2, self.std_value3)

    @api.onchange('name')
    def on_change_name(self):
        if self.name:
            results = self.search([('name', '=', self.name)])
            if len(results) > 0:
                raise UserError(_("Part %s already exists.\nClose with OK to reuse, with Cancel to discharge." % (self.name)))
            if not self.engineering_code or self.engineering_code == '-':
                self.engineering_code = self.name

    @api.onchange('tmp_material')
    def on_change_tmpmater(self):
        if self.tmp_material:
            if self.tmp_material.name:
                self.engineering_material = self.tmp_material.name

    @api.onchange('tmp_surface')
    def on_change_tmpsurface(self):
        if self.tmp_surface:
            if self.tmp_surface.name:
                self.engineering_surface = str(self.tmp_surface.name)

    @api.onchange('tmp_treatment')
    def on_change_tmptreatment(self):
        if self.tmp_treatment:
            if self.tmp_treatment.name:
                self.engineering_treatment = str(self.tmp_treatment.name)

    @api.model
    def getParentBomStructure(self, filterBomType=''):
        bom_line_filter = [('product_id', '=', self.id)]
        if filterBomType:
            bom_line_filter.append(('type', '=', filterBomType))
        mrpBomLines = self.env['mrp.bom.line'].search(bom_line_filter)
        out = []
        for mrpBomLine in mrpBomLines:
            out.append((self.env['mrp.bom'].where_used_header(mrpBomLine),
                        mrpBomLine.bom_id.get_where_used_structure(filterBomType)))
        return out


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
            return obj.write_date
        else:
            return obj.create_date

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
        plmDocObj = self.env['ir.attachment']

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
            docBrw = plmDocObj.browse(docIdToOpen)
            checkOutUser = docBrw.get_checkout_user()
            if checkOutUser:
                isMyDocument = docBrw.isCheckedOutByMe()
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
                retValues.append(partVals)
                continue
            existingCompBrwsList = self.search([('engineering_code', '=', partVals['engineering_code']),
                                                ('engineering_revision', '=', partVals['engineering_revision'])], order='engineering_revision ASC')
            if not existingCompBrwsList:
                existingCompBrwsList = [self.create(partVals)]
                hasSaved = True
            for existingCompBrws in existingCompBrwsList:
                if not hasSaved:
                    partVals['name'] = existingCompBrws.name
                    if self._iswritable(existingCompBrws):
                        hasSaved = True
                        existingCompBrws.write(partVals)
                        weight = partVals.get('weight')
                        if (weight):
                            if not self.write({'weight': weight}):
                                raise UserError(_("Part %r cannot be updated" % (partVals['engineering_code'])))
                        else:
                            logging.warning("No Weight property set unable to update !!")
                partVals['componentID'] = existingCompBrws.id
                partVals['hasSaved'] = hasSaved
                break
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
        retd = list(dic.values())
        return retd

    @api.multi
    def _get_recursive_parts(self, exclude_statuses, include_statuses):
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
                if (childProdBrws.state not in exclude_statuses) and (childProdBrws.state not in include_statuses):
                    errors.append(_("Product code: %r revision %r status %r") % (childProdBrws.engineering_code, childProdBrws.engineering_revision, childProdBrws.state))
                    continue
                if childProdBrws.state in include_statuses:
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
        documentType = self.env['ir.attachment']
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
            msg = _("Error on workflow operation")
            for e in docInError:
                msg = msg + "\n" + e
            msg = msg + _("\n\nCheck-In All the document in order to proceed !!")
            raise UserError(msg)

        if len(docIDs) > 0:
            docBrws = documentType.browse(docIDs)
            if action_name == 'confirm':
                docBrws.action_confirm()
            elif action_name == 'transmit':  # TODO: Why is used? Is correct?
                docBrws.action_confirm()
            elif action_name == 'draft':
                docBrws.action_draft()
            elif action_name == 'correct':  # TODO: Why is used? Is correct?
                docBrws.action_draft()
            elif action_name == 'reject':
                docBrws.action_draft()
            elif action_name == 'release':
                docBrws.action_release()
            elif action_name == 'undermodify':
                docBrws.action_cancel()
            elif action_name == 'suspend':
                docBrws.action_suspend()
            elif action_name == 'reactivate':
                docBrws.action_reactivate()
            elif action_name == 'obsolete':
                docBrws.action_obsolete()
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
            for comp_obj in self:
                comp_obj.sudo().message_post(body=_(body))

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
        for comp_obj in self:
            defaults = {}
            status = 'draft'
            action = 'draft'
            doc_action = 'draft'
            defaults['engineering_writable'] = True
            defaults['state'] = status
            exclude_statuses = ['draft', 'released', 'undermodify', 'obsoleted']
            include_statuses = ['confirmed']
            comp_obj.commonWFAction(status, action, doc_action, defaults, exclude_statuses, include_statuses)
        return True

    @api.multi
    def action_confirm(self):
        """
            action to be executed for Draft state
        """
        for comp_obj in self:
            defaults = {}
            status = 'confirmed'
            action = 'confirm'
            doc_action = 'confirm'
            defaults['engineering_writable'] = False
            defaults['state'] = status
            exclude_statuses = ['confirmed', 'released', 'undermodify', 'obsoleted']
            include_statuses = ['draft']
            comp_obj.commonWFAction(status, action, doc_action, defaults, exclude_statuses, include_statuses)
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
        for comp_obj in self:
            children_product_to_emit = []
            product_tmpl_ids = []
            defaults = {}
            prodTmplType = self.env['product.template']
            exclude_statuses = ['released', 'undermodify', 'obsoleted']
            include_statuses = ['confirmed']
            errors, product_ids = comp_obj._get_recursive_parts(exclude_statuses, include_statuses)
            if len(product_ids) < 1 or len(errors) > 0:
                raise UserError(errors)
            allProdObjs = self.browse(product_ids)
            for productBrw in allProdObjs:
                old_revision = self._getbyrevision(productBrw.engineering_code, productBrw.engineering_revision - 1)
                if old_revision is not None:
                    defaults['engineering_writable'] = False
                    defaults['state'] = 'obsoleted'
                    old_revision.product_tmpl_id.write(defaults)
                    old_revision.wf_message_post(body=_('Status moved to: %s.' % (USE_DIC_STATES[defaults['state']])))
            defaults['engineering_writable'] = False
            defaults['state'] = 'released'
            self.browse(product_ids)._action_ondocuments('release')
            for currentProductId in allProdObjs:
                if not currentProductId.release_date:
                    currentProductId.release_date = datetime.now()
                if not(currentProductId.id in self.ids):
                    children_product_to_emit.append(currentProductId.id)
                product_tmpl_ids.append(currentProductId.product_tmpl_id.id)
            self.browse(children_product_to_emit).action_release()
            objId = prodTmplType.browse(product_tmpl_ids).write(defaults)
            if (objId):
                self.browse(product_ids).wf_message_post(body=_('Status moved to: %s.' % (USE_DIC_STATES[defaults['state']])))
            return objId
        return False

    @api.multi
    def action_obsolete(self):
        """
            obsolete the object
        """
        for comp_obj in self:
            defaults = {}
            status = 'obsoleted'
            action = 'obsolete'
            doc_action = 'obsolete'
            defaults['engineering_writable'] = False
            defaults['state'] = status
            exclude_statuses = ['draft', 'confirmed', 'undermodify', 'obsoleted']
            include_statuses = ['released']
            comp_obj.commonWFAction(status, action, doc_action, defaults, exclude_statuses, include_statuses)
        return True

    @api.multi
    def action_reactivate(self):
        """
            reactivate the object
        """
        for comp_obj in self:
            defaults = {}
            status = 'released'
            action = ''
            doc_action = 'release'
            defaults['engineering_writable'] = True
            defaults['state'] = status
            exclude_statuses = ['draft', 'confirmed', 'released', 'undermodify', 'obsoleted']
            include_statuses = ['obsoleted']
            comp_obj.commonWFAction(status, action, doc_action, defaults, exclude_statuses, include_statuses)
        return True

    def perform_action(self, action):
        actions = {'reactivate': self.action_reactivate,
                   'obsolete': self.action_obsolete,
                   'release': self.action_release,
                   'confirm': self.action_confirm,
                   'draft': self.action_draft}
        toCall = actions.get(action)
        return toCall()

    @api.multi
    def commonWFAction(self, status, action, doc_action, defaults=[], exclude_statuses=[], include_statuses=[]):
        product_product_ids = []
        product_template_ids = []
        userErrors, allIDs = self._get_recursive_parts(exclude_statuses, include_statuses)
        if userErrors:
            raise UserError(userErrors)
        allIdsBrwsList = self.browse(allIDs)
        allIdsBrwsList._action_ondocuments(doc_action)
        for currId in allIdsBrwsList:
            if not(currId.id in self.ids):
                product_product_ids.append(currId.id)
            product_template_ids.append(currId.product_tmpl_id.id)
        if action:
            self.browse(product_product_ids).perform_action(action)
        objId = self.env['product.template'].browse(product_template_ids).write(defaults)
        if objId:
            self.browse(allIDs).wf_message_post(body=_('Status moved to: %s.' % (USE_DIC_STATES[defaults['state']])))
        return objId

#  ######################################################################################################################################33

    @api.multi
    def write(self, vals):
        if 'is_engcode_editable' not in vals:
            vals['is_engcode_editable'] = False
        vals.update(self.checkMany2oneClient(vals))
        return super(PlmComponent, self).write(vals)

    @api.model
    def variant_fields_to_keep(self):
        return [
            'name',
            'tmp_material',
            'tmp_surface',
            'tmp_treatment',
            'weight',
            'uom_id',
            'std_umc1',
            'std_umc2',
            'std_umc3',
            'std_value1',
            'std_value2',
            'std_value3',
            'engineering_surface',
            'engineering_treatment',
            'type',
            'categ_id',
            'sale_ok',
            'purchase_ok',
            'route_ids',
            'linkeddocuments',
            'std_description',
            'default_code'
            ]
        
    @api.model
    def checkSetupDueToVariants(self, vals):
        tmplt_id = vals.get('product_tmpl_id')
        attribute_value_ids = vals.get('attribute_value_ids')
        if tmplt_id and attribute_value_ids:
            outVals = {}
            tmplBrws = self.env['product.template'].browse(tmplt_id)
            for variant in tmplBrws.product_variant_ids:
                outVals = variant.read(self.variant_fields_to_keep())[0]
                del outVals['id']
                for key, val in outVals.items():
                    if isinstance(val, (list)):  # many2many
                        outVals[key] = [[6, 0, val]]
                    if isinstance(val, (tuple)): # many2one
                        outVals[key] = val[0]
                break
            outVals.update(vals)
            vals = outVals
        return vals

    @api.model
    def create(self, vals):
        if not vals:
            raise ValidationError(_("""You are trying to create a product without values"""))
        eng_code = vals.get('engineering_code')
        name = vals.get('name')
        if not name and eng_code:
            vals['name'] = eng_code
        if not vals.get('engineering_code') and name:
            vals['engineering_code'] = name
        eng_rev = vals.get('engineering_revision', 0)
        eng_code = vals.get('engineering_code')
        if eng_code:
            prodBrwsList = self.search([('engineering_code', '=', vals['engineering_code']),
                                        ('engineering_revision', '=', eng_rev)
                                        ])
            if prodBrwsList:
                raise UserError('Component %r already exists' % (vals['engineering_code']))
        try:
            vals['is_engcode_editable'] = False
            vals.update(self.checkMany2oneClient(vals))
            vals = self.checkSetupDueToVariants(vals)
            res = super(PlmComponent, self).create(vals)
            return res
        except Exception as ex:
            import psycopg2
            if isinstance(ex, psycopg2.IntegrityError):
                msg = _('Error during component creation with values:\n')
                for key, value in vals.items():
                    msg = msg + '%r = %r\n' % (key, value)
                try:
                    msg = msg + str(ex.message) + '\n'
                except:
                    pass
                msg = msg + '\n\n------------------------------\n\n' + str(ex)
                raise Exception(msg)
            logging.error("(%s). It has tried to create with values : (%s)." % (str(ex), str(vals)))
            raise Exception(_(" (%r). It has tried to create with values : (%r).") % (ex, vals))

    @api.multi
    def read(self, fields=[], load='_classic_read'):
        try:
            customFields = [field.replace('plm_m2o_', '') for field in fields if field.startswith('plm_m2o_')]
            fields.extend(customFields)
            fields = list(set(fields))
            res = super(PlmComponent, self).read(fields=fields, load=load)
            res = self.readMany2oneFields(res, fields)
            return res
        except Exception as ex:
            if isinstance(ex, AccessError) and 'sale.report' in ex.name:
                return """
Your user does not have enough permissions to make this operation. Error: \n
%r\n
Please try to contact OmniaSolutions to solve this error, or install Plm Sale Fix module to solve the problem.""" % (ex)
            raise ex

    @api.multi
    def copy(self, defaults={}):
        """
            Overwrite the default copy method
        """
        if not defaults:
            defaults = {}

        def clearBrokenComponents():
            """
                Remove broken components before make the copy. So the procedure will not fail
            """
            # Do not check also for name because may cause an error in revision procedure
            # due to translations
            brokenComponents = self.search([('engineering_code', '=', '-')])
            for brokenComp in brokenComponents:
                brokenComp.unlink()

        previous_name = self.name
        if not defaults.get('name', False):
            defaults['name'] = '-'                   # If field is required super of clone will fail returning False, this is the case
            defaults['engineering_code'] = '-'
            defaults['engineering_revision'] = 0
            clearBrokenComponents()
        if defaults.get('engineering_code', '') == '-':
            clearBrokenComponents()
        # assign default value
        defaults['state'] = 'draft'
        defaults['engineering_writable'] = True
        defaults['linkeddocuments'] = []
        defaults['release_date'] = False
        objId = super(PlmComponent, self).copy(defaults)
        if objId:
            objId.is_engcode_editable = True
            self.sudo().wf_message_post(body=_('Copied starting from : %s.' % previous_name))
        return objId

    @api.multi
    def readMany2oneFields(self, readVals, fields):
        out = []
        for vals in readVals:
            tmpVals = vals.copy()
            for fieldName, fieldVal in vals.items():
                customField = 'plm_m2o_' + fieldName
                if customField in fields:
                    if fieldVal:
                        tmpVals[customField] = fieldVal[1]
                    else:
                        tmpVals[customField] = ''
            out.append(tmpVals)
        return out

    @api.multi
    def checkMany2oneClient(self, vals):
        out = {}
        customFields = [field.replace('plm_m2o_', '') for field in vals.keys() if field.startswith('plm_m2o_')]
        fieldsGet = self.fields_get(customFields)
        for fieldName, fieldDefinition in fieldsGet.items():
            refId = self.customFieldConvert(fieldDefinition, vals, fieldName)
            if refId:
                out[fieldName] = refId.id
        return out

    @api.multi
    def customFieldConvert(self, fieldDefinition, vals, fieldName):
        refId = False
        fieldType = fieldDefinition.get('type', '')
        referredModel = fieldDefinition.get('relation', '')
        oldFieldName = 'plm_m2o_' + fieldName
        cadVal = vals.get(oldFieldName, '')
        if fieldType == 'many2one':
            try:
                refId = self.env[referredModel].search([('name', '=', cadVal)])
            except Exception as ex:
                logging.warning(ex)
        return refId

    @api.model
    def translateForClient(self, values=[], forcedLang=''):
        """
            Get values attribute in this format:
            values = [{'field1':value1,'field2':value2,...}]     only one element in the list!!!
            and return computed values due to language
            Get also forcedLang attribute in this format:
            forcedLang = 'en_US'
            if is not set it takes language from user
        """
        language = forcedLang
        if not forcedLang:
            resDict = self.env['res.users'].read(['lang'])
            language = resDict.get('lang', '')
        if values:
            values = values[0]
        if language and values:
            toRead = [x for x in list(values.values()) if type(x) in [str] and x]     # Where computed only string and not null string values (for performance improvement)
            toRead = list(set(toRead))                                                      # Remove duplicates
            for fieldName, valueToTranslate in list(values.items()):
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
        """
            This function is called by the button on component view, section LinkedDocuments
            Clicking that button all documents related to all revisions of this component are opened in a tree view
        """
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
                'res_model': 'ir.attachment',
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
                self.browse([oldObject.id]).sudo().write(oldProdVals)
                oldObject.wf_message_post(body=_('Status moved to: %s.' % (USE_DIC_STATES[oldProdVals['state']])))
                # store updated infos in "revision" object
                defaults = {}
                defaults['name'] = oldObject.name                 # copy function needs an explicit name value
                defaults['engineering_code'] = oldObject.engineering_code
                defaults['engineering_revision'] = engineering_revision
                defaults['engineering_writable'] = True
                defaults['state'] = 'draft'
                defaults['linkeddocuments'] = []                  # Clean attached documents for new revision object
                newCompBrws = oldObject.with_context({'new_revision': True}).copy(defaults)
                oldObject.wf_message_post(body=_('Created : New Revision.'))
                newComponentId = newCompBrws.id
                break
            break
        return (newComponentId, engineering_revision)

    @api.model
    def wf_message_post_client(self, args):
        """
            args = [objId, objMessage]
        """
        objId, objMessage = args
        self.browse(objId).wf_message_post(objMessage)
        return True

    @api.model
    def getBomRowCad(self, bomLineBrowse):
        """
        give back the lines
        """
        return [bomLineBrowse.itemnum,
                emptyStringIfFalse(bomLineBrowse.product_id.name),
                bomLineBrowse.product_id.with_context({'lang': 'en_GB'}).name,
                bomLineBrowse.product_id.engineering_code,
                bomLineBrowse.product_qty]

    @api.model
    def getNormalBomStd(self):
        """
            get the normal bom from the given name and revision
            RELPOS,
            $G{COMPDES="-"} / $G{COMPDES_L2="-"},
            $G{COMPNAME:f("#clear(<undef>@)")},
            $G{RELQTY},
        """
        componentName = self.env.context.get('componentName', '')
        componentRev = self.env.context.get('componentRev', 0)
        bomType = 'normal'
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

    @api.model
    def _getChildrenBomWithDocuments(self, component, level=0, currlevel=0):
        """
            Return a flat list of each child, listed once, in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        result = []
        bufferdata = []
        if level == 0 and currlevel > 1:
            return bufferdata
        for bomid in component.product_tmpl_id.bom_ids:  # TODO: Bom type??
            for bomline in bomid.bom_line_ids:
                levelDict = {}
                prodBrws = bomline.product_id
                levelDict['root_props'] = prodBrws.getComponentInfos()
                levelDict['documents'] = self.computeLikedDocuments(prodBrws)
                levelDict['bom'] = self._getChildrenBom(bomline.product_id, level, currlevel + 1)
                bufferdata.append(levelDict)
            break
        result.extend(bufferdata)
        return list(set(result))

    def computeLikedDocuments(self, prodBrws):
        docList = []
        compInfos = prodBrws.getComponentInfos()
        for docBrws in prodBrws.linkeddocuments:
            docList.append({'component': compInfos, 'document': docBrws.getDocumentInfos()})
        return docList

    def getComponentInfos(self):
        return {'engineering_code': self.engineering_code or '',
                'engineering_revision': self.engineering_revision,
                'description': self.name or '',
                'desc_modify': self.desc_modify or '',    # To be created
                'name': self.name,
                '_id': self.id,
                'can_revise': self.canBeRevised(),
                }

    @api.model
    def getCloneRevisionStructure(self, values=[]):
        """
            out = {
                'root_props': {},
                'documents': [],
                'bom': [
                    {
                    'documents': [],
                    'bom': []
                    },
                ]
                }
        """
        def computeBomAllLevels(prodBrws):
            return prodBrws._getChildrenBomWithDocuments(prodBrws, level=1)

        def computeBomOneLevel(prodBrws):
            return prodBrws._getChildrenBomWithDocuments(prodBrws, level=0)

        if not values:
            return {}
        componentDict = values[0]
        computeType = values[1]  # Possible values = 'no-bom' / 'bom-all-levels' / 'bom-one-level'
        eng_code = componentDict.get('engineering_code', '')
        eng_rev = componentDict.get('engineering_revision', None)
        if not eng_code:
            logging.warning('No engineering code passed by the client %r' % (componentDict))
            return {}
        if eng_rev is None:
            logging.warning('No engineering revision passed by the client %r' % (componentDict))
            return {}
        componentId = componentDict.get('_id', None)
        if not componentId:
            prodBrws = self.search([('engineering_code', '=', eng_code),
                                    ('engineering_revision', '=', eng_rev)])
        else:
            prodBrws = self.browse(componentId)
        if not prodBrws:
            logging.warning('No component found for arguments %r' % (componentDict))
            return {}
        if computeType == 'no-bom':
            rootProps = prodBrws.getComponentInfos()
            rootProps['can_revise'] = True   # Because cames from previous new revision. So it can be revised
            return {
                'root_props': rootProps,
                'documents': self.computeLikedDocuments(prodBrws),
                'bom': []}
        elif computeType == 'bom-all-levels':
            return computeBomAllLevels(prodBrws)
        elif computeType == 'bom-one-level':
            return computeBomOneLevel(prodBrws)
        else:
            logging.warning('Unable to find computation type %r' % (componentDict))
            return {}
        return {}

    @api.multi
    def canBeRevised(self):
        for compBrws in self:
            if compBrws.state == 'released':
                return True
        return False

    @api.model
    def reviseCompAndDoc(self, elementsToClone):
        docEnv = self.env['ir.attachment']
        updatedJsonNode = elementsToClone[0]
        updatedNode = json.loads(updatedJsonNode)
        hostName, hostPws = elementsToClone[1], elementsToClone[2]
        _oldRootCompVals, _oldRootDocVals = elementsToClone[3]

        def updateDocAttrs(node, datasName):
            node['DOCUMENT_ATTRIBUTES']['OLD_FILE_NAME'] = datasName
            node['DOCUMENT_ATTRIBUTES']['CHECK_OUT_BY_ME'] = True

        def cleanRootUnCheckedComponent(compBrws, node):
            # User made and edit parts in the client but he unchecked the component in the interface
            # So I need to delete it, restore previous revision and revise only the document
            compBrws.unlink()
            return restorePreviousComponentRevision(node)

        def cleanRootUnCheckedDocument(docBrws, node):
            # User made and edit document in the client but he unchecked the component in the interface
            # So I need to delete it and restore previous revision
            docBrws.unlink()
            return restorePreviousDocumentRevision(node)

        def restorePreviousDocumentRevision(node):
            node['DOCUMENT_ATTRIBUTES']['revisionid'] = node['DOCUMENT_ATTRIBUTES']['revisionid'] - 1
            return docEnv.getDocumentBrws(node['DOCUMENT_ATTRIBUTES'])  # Try to restore previous revision (case of only document revision)

        def restorePreviousComponentRevision(node):
            node['PRODUCT_ATTRIBUTES']['engineering_revision'] = node['PRODUCT_ATTRIBUTES']['engineering_revision'] - 1
            return self.getCompBrws(node['PRODUCT_ATTRIBUTES'])  # Try to restore previous revision (case of only document revision)

        def updateCompDescModify(newCompBrwse, node):
            newCompBrwse.desc_modify = node['PRODUCT_ATTRIBUTES'].get('desc_modify', '')

        def updateDocDescModify(newDocBrws, node):
            newDocBrws.desc_modify = node['DOCUMENT_ATTRIBUTES'].get('desc_modify', '')

        def updateDocNodeByBrws(node, newDocBrws):
            node['DOCUMENT_ATTRIBUTES'].update(newDocBrws.getDocumentInfos())

        def updateCompNodeByBrws(node, newCompBrwse):
            node['PRODUCT_ATTRIBUTES'].update(newCompBrwse.getComponentInfos())

        def updateRootDocument(docBrws, node):
            if docBrws:
                newDocBrws = docBrws
                updateDocAttrs(node, docBrws.datas_fname)
                docBrws.checkout(hostName, hostPws)
                newDocBrws.desc_modify = node['DOCUMENT_ATTRIBUTES'].get('desc_modify', '')
                return newDocBrws
            return False

        def reviseCompObj(compBrws, node):
            # Raw component because BOM is not managed
            newCompId, _newCompRev = compBrws.NewRevision()
            newCompBrwse = self.browse(newCompId)
            updateCompDescModify(newCompBrwse, node)
            updateCompNodeByBrws(node, newCompBrwse)
            return newCompBrwse

        def reviseDocObj(docBrws, node):
            newDocId, _newDocIndex = docBrws.NewRevision()
            newDocBrws = docEnv.browse(newDocId)
            updateDocDescModify(newDocBrws, node)
            updateDocNodeByBrws(node, newDocBrws)
            updateDocAttrs(node, docBrws.datas_fname)
            newDocBrws.checkout(hostName, hostPws)
            return newDocBrws

        def reviseComp(node, isRoot, compBrws, docBrws, reviseDocument, reviseComponent):
            newCompBrwse = False
            newDocBrws = False
            deleted = False
            if not reviseComponent:
                if compBrws and isRoot:
                    compBrws = cleanRootUnCheckedComponent(compBrws, node)
                else:
                    compBrws = restorePreviousComponentRevision(node)
                deleted = True
            if not deleted:
                if isRoot:
                    newCompBrwse = compBrws
                    updateCompDescModify(newCompBrwse, node)
                else:
                    newCompBrwse = reviseCompObj(compBrws, node)
            if reviseDocument:
                newDocBrws = reviseDocObj(docBrws, node)
            return newCompBrwse, newDocBrws

        def reviseDoc(node, reviseDocument, docBrws, isRoot):
            newDocBrws = False
            if not reviseDocument:
                if docBrws and isRoot:
                    cleanRootUnCheckedDocument(docBrws, node)
                else:
                    restorePreviousDocumentRevision(node)
                return False
            if isRoot:
                newDocBrws = updateRootDocument(docBrws, node)
            else:
                newDocBrws = reviseDocObj(docBrws, node)
            return newDocBrws

        def setupRelations(newDocBrws, newCompBrwse):
            if newDocBrws:
                newDocBrws.write({'linkedcomponents': [(5, 0, 0)]})  # Clean copied links
                if newCompBrwse:
                    newCompBrwse.write({'linkeddocuments': [(4, newDocBrws.id, False)]})  # Add link to component

        def nodeResursionUpdate(node, isRoot=False):
            newDocBrws = False
            newCompBrwse = False
            reviseComponent = node.get('COMPONENT_CHECKED', False)
            reviseDocument = node.get('DOCUMENT_CHECKED', False)
            compProps = node.get('PRODUCT_ATTRIBUTES', {})
            docProps = node.get('DOCUMENT_ATTRIBUTES', {})
            engCode = compProps.get('engineering_code', '')
            docName = docProps.get('name', '')
            docId = docProps.get('_id', None)
            docBrws = self.getDocBrws(docId, docProps)
            compBrws = self.getCompBrws(compProps)
            if engCode:
                newCompBrwse, newDocBrws = reviseComp(node, isRoot, compBrws, docBrws, reviseDocument, reviseComponent)
            elif docName:
                newDocBrws = reviseDoc(node, reviseDocument, docBrws, isRoot)
            setupRelations(newDocBrws, newCompBrwse)
            for childNode in node.get('RELATIONS', []):
                if childNode.get('DOCUMENT_ATTRIBUTES', {}).get('DOC_TYPE').upper() == '2D':
                    childNode['PRODUCT_ATTRIBUTES'] = {'engineering_code': ''}    # Setup the correct parent component
                nodeResursionUpdate(childNode)

        nodeResursionUpdate(updatedNode, True)
        return json.dumps(updatedNode)

    def getDocBrws(self, docId, docProps):
        docEnv = self.env['ir.attachment']
        oldDocBrws = False
        if docId:
            oldDocBrws = docEnv.browse(docId)
        else:
            oldDocBrws = docEnv.getDocumentBrws(docProps)
        return oldDocBrws

    def getCompBrws(self, compProps):
        compId = compProps.get('_id', None)
        compBrws = False
        if compId:
            compBrws = self.browse(compId)
        else:
            compBrws = self.getComponentBrws(compProps)
        return compBrws

    @api.model
    def cloneCompAndDoc(self, elementsToClone):
        docEnv = self.env['ir.attachment']
        updatedJsonNode = elementsToClone[0]
        updatedNode = json.loads(updatedJsonNode)
        hostName, hostPws = elementsToClone[1], elementsToClone[2]
        _oldRootCompVals, oldRootDocVals = elementsToClone[3]
        newRootCompProps = updatedNode.get('PRODUCT_ATTRIBUTES')
        newRootDocProps = updatedNode.get('DOCUMENT_ATTRIBUTES')

        def cleanRootDocument(oldDocBrws, node):
            oldDocBrws.unlink()
            cleanDocumentAttrs(node)

        def cleanDocumentAttrs(node):
            node['DOCUMENT_ATTRIBUTES'] = {}

        def cleanRootComponent(compBrws, node):
            # User made and edit parts in the client but he unchecked the component in the interface
            # So I need to delete it and clone only the document
            compBrws.unlink()
            cleanEngCode(node)

        def cleanEngCode(node):
            node['PRODUCT_ATTRIBUTES'] = {'engineering_code': ''}

        def createClonedRawComponent(engCode, compBrws, node):
            newBaseName = engCode + '_raw'
            newCode = docEnv.GetNextDocumentName(newBaseName)
            default = {'name': newCode,
                       'engineering_code': newCode}
            newRawComponent = compBrws.copy(default)
            node['PRODUCT_ATTRIBUTES'] = newRawComponent.getComponentInfos()
            return newCode, newRawComponent

        def cloneDocumentObj(oldDocBrws, engCode, node):
            newDocBrws = False
            if oldDocBrws.id:
                _filename, file_extension = os.path.splitext(oldDocBrws.datas_fname)
                newDocBrws = self.getNewDoc(oldDocBrws, engCode, file_extension)
                newDocBrws.checkout(hostName, hostPws)
                node['DOCUMENT_ATTRIBUTES'] = newDocBrws.getDocumentInfos()
                node['DOCUMENT_ATTRIBUTES']['OLD_FILE_NAME'] = oldDocBrws.datas_fname
                node['DOCUMENT_ATTRIBUTES']['CHECK_OUT_BY_ME'] = oldDocBrws._is_checkedout_for_me()
            return newDocBrws

        def setupRootDocument(clonedDocBrws, node):
            # oldRootDocVals are starting document properties
            # clonedDocBrws is cloned document browse
            rootOldDocBrws = docEnv.getDocumentBrws(oldRootDocVals)
            _filename, file_extension = os.path.splitext(rootOldDocBrws.datas_fname)
            clonedDocBrws.datas_fname = '%s%s' % (clonedDocBrws.name, file_extension)
            node['DOCUMENT_ATTRIBUTES']['datas_fname'] = clonedDocBrws.datas_fname
            node['DOCUMENT_ATTRIBUTES']['CHECK_OUT_BY_ME'] = True
            node['DOCUMENT_ATTRIBUTES']['OLD_FILE_NAME'] = rootOldDocBrws.datas_fname
            clonedDocBrws.checkout(hostName, hostPws)
            return clonedDocBrws

        def cloneWithComp(cloneComponent, cloneDocument, rootEngCode, oldDocBrws, compBrws, node, isRoot=False):
            newDocBrws = False
            newRawComponent = False
            if not cloneComponent:
                if compBrws and isRoot:  # Only root component has to be deleted
                    cleanRootComponent(compBrws, node)
                else:
                    cleanEngCode(node)
            else:   # Root case --> already cloned in the CAD otherwise ir a raw component
                if not isRoot:  # Part-Part case because BOM is not managed
                    rootEngCode, newRawComponent = createClonedRawComponent(rootEngCode, compBrws, node)
            if cloneDocument:
                newDocBrws = cloneDocumentObj(oldDocBrws, rootEngCode, node)
            else:
                node['DOCUMENT_ATTRIBUTES'] = {}
            return newDocBrws, newRawComponent

        def cloneWithDoc(cloneDocument, oldDocBrws, node, isRoot, baseName):
            newDocBrws = False
            if not cloneDocument:
                if oldDocBrws and isRoot:
                    cleanRootDocument(oldDocBrws, node)
                else:
                    cleanDocumentAttrs(node)
                return newDocBrws
            if isRoot:
                newDocBrws = setupRootDocument(oldDocBrws, node)
            else:
                newDocBrws = cloneDocumentObj(oldDocBrws, baseName, node)
            return newDocBrws

        def cleanAndSetupRelations(newDocBrws, compBrws):
            if newDocBrws:
                newDocBrws.write({'linkedcomponents': [(5, 0, 0)]})  # Clean copied links
                if compBrws:
                    compBrws.write({'linkeddocuments': [(4, newDocBrws.id, False)]})  # Add link to component

        def nodeResursionUpdate(node, isRoot=False):
            cloneDocument = node.get('DOCUMENT_CHECKED', False)
            compProps = node.get('PRODUCT_ATTRIBUTES', {})
            docProps = node.get('DOCUMENT_ATTRIBUTES', {})
            rootEngCode = newRootCompProps.get('engineering_code', '')
            docName = docProps.get('name', '')
            docId = docProps.get('_id', None)
            newDocBrws = False
            oldDocBrws = self.getDocBrws(docId, docProps)
            compBrws = self.getCompBrws(compProps)
            if compProps.get('engineering_code', ''):    # Node is a component-document node
                newDocBrws, newRawComponent = cloneWithComp(node.get('COMPONENT_CHECKED', False),
                                                            cloneDocument,
                                                            rootEngCode,
                                                            oldDocBrws,
                                                            compBrws,
                                                            node,
                                                            isRoot)
                compBrws = newRawComponent
            elif docName:    # Node is a document node
                baseName = docName
                rootDocName = newRootDocProps.get('name', '')
                if rootEngCode or rootDocName:
                    baseName = rootEngCode or rootDocName
                newDocBrws = cloneWithDoc(cloneDocument,
                                          oldDocBrws,
                                          node,
                                          isRoot,
                                          baseName)
            cleanAndSetupRelations(newDocBrws, compBrws)
            for childNode in node.get('RELATIONS', []):
                if childNode.get('DOCUMENT_ATTRIBUTES', {}).get('DOC_TYPE').upper() == '2D':
                    childNode['PRODUCT_ATTRIBUTES'] = {'engineering_code': ''}
                nodeResursionUpdate(childNode)

        nodeResursionUpdate(updatedNode, True)
        return json.dumps(updatedNode)

    def getNewDoc(self, oldDocBrws, startingComputeName, file_extension):
        docEnv = self.env['ir.attachment']
        newDocName = docEnv.GetNextDocumentName(startingComputeName)
        docDefaultVals = {
            'revisionid': 0,
            'name': newDocName,
            'datas_fname': '%s%s' % (newDocName, file_extension),
            'checkout_user': self.env.uid}
        newDocVals = oldDocBrws.Clone(docDefaultVals)
        newDocId = newDocVals.get('_id')
        newDocBrws = docEnv.browse(newDocId)
        return newDocBrws

    def getComponentBrws(self, componentVals):
        engCode = componentVals.get('engineering_code', '')
        engRev = componentVals.get('engineering_revision', None)
        if not engCode or engRev is None:
            return self.browse()
        return self.search([
            ('engineering_code', '=', engCode),
            ('engineering_revision', '=', engRev)])


class PlmTemporayMessage(osv.osv.osv_memory):
    _name = "plm.temporary.message"
    _description = "Temporary Class"
    name = fields.Text(_('Bom Result'), readonly=True)


class ProductProductDashboard(models.Model):
    _name = "report.plmcomponent"
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
            CREATE OR REPLACE VIEW report_plmcomponent AS (
                SELECT
                    (SELECT min(id) FROM product_template where engineering_code<>'') as id,
                    (SELECT count(*) FROM product_template WHERE state = 'draft' and  engineering_code<>'') AS count_component_draft,
                    (SELECT count(*) FROM product_template WHERE state = 'confirmed' and  engineering_code<>'') AS count_component_confirmed,
                    (SELECT count(*) FROM product_template WHERE state = 'released' and  engineering_code<>'') AS count_component_released,
                    (SELECT count(*) FROM product_template WHERE state = 'undermodify' and  engineering_code<>'') AS count_component_modified,
                    (SELECT count(*) FROM product_template WHERE state = 'obsoleted' and  engineering_code<>'') AS count_component_obsoleted
             )
        """)
