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
Created on 18 Jul 2016

@author: Daniel Smerghetto
'''

import logging
from openerp import models
from openerp import fields
from openerp import api
from openerp import _
from openerp.exceptions import UserError


class mrp_bom_extension_data(models.Model):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'

    @api.multi
    def _obsolete_compute(self):
        '''
            Verify if obsolete lines are present in current bom
        '''
        for bomObj in self:
            obsoleteFlag = False
            for bomLine in bomObj.bom_line_ids:
                if bomLine.product_id.state == 'obsoleted':
                    obsoleteFlag = True
                    break
            bomObj.obsolete_presents = obsoleteFlag
            bomObj.write({'obsolete_presents': obsoleteFlag})   # don't remove this force write or when form is opened the value is not updated

    # If store = True is set you need to provide @api.depends because odoo has to know when to compute that field.
    # If you decide to compute that field each time without store you have always to put it in the view or the field will not be computed
    obsolete_presents_computed = fields.Boolean(string=_("Obsolete presents computed"), compute='_obsolete_compute')
    obsolete_presents = fields.Boolean(_("Obsolete presents"))

    @api.onchange('bom_line_ids')
    def onchangeBomLine(self):
        self._obsolete_compute()

    @api.multi
    def action_wizard_compute_bom(self):
        return {
            'domain': [],
            'name': _('Bom Computation Type'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'plm.temporary_date_compute',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def showAllBomsToCompute(self):
        outLines = []

        def recursion(bomBrwsList):
            for bomBrws in bomBrwsList:
                for bomLineBrws in bomBrws.bom_line_ids:
                    templateBrws = bomLineBrws.product_id.product_tmpl_id
                    bomIds = self.getBomFromTemplate(templateBrws, 'normal')
                    recursion(bomIds)
                    if not templateBrws:
                        logging.warning('Product %s is not related to a product template.' % (bomLineBrws.product_id.id))
                        continue
                    if templateBrws.state == 'obsoleted':
                        outLines.append(bomBrws.id)
        recursion(self)
        outLines = list(set(outLines))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Engineering'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'mrp.bom',
            'domain': [('id', 'in', outLines)],
        }

    def getBomFromTemplate(self, prodTmplBrws, bomType):
        '''
            Return bom object from product template and bom type
        '''
        return self.search([('product_tmpl_id', '=', prodTmplBrws.id), ('type', '=', bomType)])

mrp_bom_extension_data()


class mrp_bom_data_compute(models.Model):
    _name = 'plm.temporary_date_compute'

    compute_type = fields.Selection([
                                    ('update', _('Update Bom replacing obsoleted bom lines with components at the latest revision.')),
                                    ('new_bom', _('Create new bom using last revision of all components.'))
                                    ],
                                    _('Compute Type'),
                                    required=True)

    @api.multi
    def action_compute_bom(self):
        '''
            Divide due to choosen operation
        '''
        bomIds = self.env.context.get('active_ids', [])     # Surely one record a time arrive here because comes from xml
        if self.compute_type == 'update':
            self.updateObsoleteBom(bomIds)
        elif self.compute_type == 'new_bom':
            self.copyObsoleteBom(bomIds)
        else:
            raise _('You must select at least one option!')

    def updateObsoleteBom(self, bomIds=[], recursive=False):
        '''
            Update all obsoleted bom lines with last released product
        '''
        bomObj = self.env['mrp.bom']
        prodProdObj = self.env['product.product']
        for bomBrws in bomObj.browse(bomIds):
            if bomBrws.type != 'normal':
                raise UserError(_('This functionality is avaible only for normal bom.'))
            for bomLineBrws in bomBrws.bom_line_ids:
                templateBrws = bomLineBrws.product_id.product_tmpl_id
                if recursive:
                    bomIds = bomObj.getBomFromTemplate(templateBrws, 'normal').ids
                    self.updateObsoleteBom(bomIds)
                if not templateBrws:
                    logging.warning('Product %s is not related to a product template.' % (bomLineBrws.product_id.id))
                    continue
                if templateBrws.state == 'obsoleted':
                    eng_code = templateBrws.engineering_code
                    prodProdBrws = prodProdObj.search([('engineering_code', '=', eng_code)], order='engineering_revision DESC', limit=1)
                    for prodBrws in prodProdBrws:
                        bomLineBrws.product_id = prodBrws
                        if recursive:
                            # Check if new added product has boms
                            self.updateObsoleteBom(prodBrws.product_tmpl_id.bom_ids.ids)
            bomBrws._obsolete_compute()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Engineering'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.bom',
            'domain': [('id', 'in', bomIds)],
        }

    def copyObsoleteBom(self, bomIds=[]):
        '''
            Copy current bom containing obsoleted components and update the copy with the last product revisions
        '''
        bomObject = self.env['mrp.bom']
        for bomId in bomIds:
            newBomBrws = bomObject.copy(bomId)
            self.updateObsoleteBom(newBomBrws.ids)
        bomObject.browse(bomIds).write({'active': False})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Engineering'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.bom',
            'domain': [('id', 'in', newBomBrws.id)],
        }

mrp_bom_data_compute()


class bom_line_obsoleted_extension(models.Model):
    _name = 'mrp.bom.line'
    _inherit = 'mrp.bom.line'

    @api.onchange('state')
    def onchange_line_state(self):
        '''
            Force update flag every time bom line state changes
        '''
        for bomLineObj in self:
            bomBrws = bomLineObj.bom_id
            bomBrws._obsolete_compute()

bom_line_obsoleted_extension()
