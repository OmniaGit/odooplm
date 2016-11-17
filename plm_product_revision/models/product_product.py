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

'''
Created on 31 Aug 2016

@author: Daniel Smerghetto
'''
import logging
from datetime import datetime
from openerp import models
from openerp import fields
from openerp import api
from openerp import _
from openerp.exceptions import ValidationError
from openerp.exceptions import UserError
from openerp import osv
import openerp.tools as tools

USED_STATES = [('draft', _('Draft')),
               ('confirmed', _('Confirmed')),
               ('released', _('Released')),
               ('undermodify', _('UnderModify')),
               ('obsoleted', _('Obsoleted'))]
USEDIC_STATES = dict(USED_STATES)


class PlmComponent(models.Model):
    _inherit = 'product.product'

    @api.model
    def _getbyrevision(self, name, revision):
        return self.search([('engineering_code', '=', name),
                            ('engineering_revision', '=', revision)])

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
            if 'engineering_code' not in partVals or 'engineering_revision' not in partVals:
                partVals['componentID'] = False
                partVals['hasSaved'] = hasSaved
                continue
            existingCompBrws = self.search([('engineering_code', '=', partVals['engineering_code']),
                                            ('engineering_revision', '=', partVals['engineering_revision'])])
            if not existingCompBrws:
                existingCompBrws = self.create(partVals)
                hasSaved = True
            else:
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
    def action_release(self):
        """
           action to be executed for Released state
        """
        tmpl_ids = []
        full_ids = []
        defaults = {}
        excludeStatuses = ['released', 'undermodify', 'obsoleted']
        includeStatuses = ['confirmed']
        errors, allIDs = self._get_recursive_parts(excludeStatuses, includeStatuses)
        if len(allIDs) < 1 or len(errors) > 0:
            raise UserError(errors)
        allProdObjs = self.browse(allIDs)
        for oldObject in allProdObjs:
            last_id = self._getbyrevision(oldObject.engineering_code, oldObject.engineering_revision - 1)
            if last_id is not None:
                defaults['engineering_writable'] = False
                defaults['state'] = 'obsoleted'
                prodObj = self.browse([last_id])
                prodObj.write(defaults)
                self.browse(last_id).wf_message_post(body=_('Status moved to: %s.' % (USEDIC_STATES[defaults['state']])))
            defaults['engineering_writable'] = False
            defaults['state'] = 'released'
        self._action_ondocuments('release')
        for currId in allProdObjs:
            if not(currId.id in self.ids):
                tmpl_ids.append(currId.product_tmpl_id.id)
            full_ids.append(currId.product_tmpl_id.id)
        self.browse(tmpl_ids).signal_workflow(tmpl_ids, 'release')
        objId = self.env['product.template'].browse(full_ids).write(defaults)
        if (objId):
            self.browse(allIDs).wf_message_post(body=_('Status moved to: %s.' % (USEDIC_STATES[defaults['state']])))
        return objId

    @api.model
    def create(self, vals):
        if not vals:
            raise ValidationError(_("""You are trying to create a product without values"""))
        if ('name' in vals):
            if not vals['name']:
                return False
            prodBrwsList = self.search([('name', '=', vals['name'])],
                                       order='engineering_revision')
            if 'engineering_code' in vals:
                if vals['engineering_code'] == False:
                    vals['engineering_code'] = vals['name']
            else:
                vals['engineering_code'] = vals['name']
            if prodBrwsList:
                existObj = prodBrwsList[len(prodBrwsList) - 1]
                if ('engineering_revision' in vals):
                    if existObj:
                        if vals['engineering_revision'] > existObj.engineering_revision:
                            vals['name'] = existObj.name
                        else:
                            return existObj
                else:
                    return existObj
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

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        result = super(PlmComponent, self).name_search(name, args, operator, limit)
        newResult = []
        for productId, oldName in result:
            objBrowse = self.browse([productId])
            newName = "%r [%r] " % (oldName, objBrowse.engineering_revision)
            newResult.append((productId, newName))
        return newResult

PlmComponent()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
