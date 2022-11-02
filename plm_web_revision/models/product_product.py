# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
Created on 22 Aug 2016

@author: Daniel Smerghetto
'''
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging


class ProductProductExtended(models.Model):
    _name = 'product.rev_wizard'
    _description = "Product Revision wizard"

    reviseDocument = fields.Boolean(_('Document Revision'), help=_("""Make new revision of the linked document ?"""))
    reviseEbom = fields.Boolean(_('Engineering Bom Revision'), help=_("""Make new revision of the linked Engineering BOM ?"""))
    reviseNbom = fields.Boolean(_('Normal Bom Revision'), help=_("""Make new revision of the linked Normal BOM ?"""))
    reviseSbom = fields.Boolean(_('Spare Bom Revision'), help=_("""Make new revision of the linked Spare BOM ?"""))

    def action_create_new_revision_by_server(self):
        product_id = self.env.context.get('active_id', False)
        active_model = self.env.context.get('active_model', False)
        if product_id and active_model:
            old_product_product_id = self.env[active_model].browse(product_id)
            old_product_template_id =old_product_product_id.product_tmpl_id
            old_product_template_id.new_version()
            new_product_template_id = old_product_product_id.product_tmpl_id.get_next_version()

            if self.reviseDocument:
                self.revise_related_attachment(old_product_template_id, new_product_template_id, prodProdEnv)
            if self.reviseEbom:
                self.common_bom_revision(old_product_template_id, new_product_template_id, prodProdEnv, 'ebom')
            if self.reviseNbom:
                self.common_bom_revision(old_product_template_id, new_product_template_id, prodProdEnv, 'normal')
            if self.reviseSbom:
                self.common_bom_revision(old_product_template_id, new_product_template_id, prodProdEnv, 'spbom')
            
            new_product_id = self.env['product.product'].search([('product_tmpl_id','=', new_product_template_id.id)], limit=1)
            
            return {'name': _('Revised Product'),
                    'view_type': 'tree,form',
                    "view_mode": 'form',
                    'res_model': 'product.product',
                    'res_id': new_product_id.id,
                    'type': 'ir.actions.act_window'}
            
        else:
            logging.error('[action_create_new_revision_by_server] Cannot revise because product_id is %r' % (product_id))
            raise UserError(_('Current component cannot be revised!'))

    def revise_related_attachment(self, old_product_id, new_product_id, prodProdEnv):
        new_ir_attachment_ids = self.env['ir.attachment']
        for old_ir_attachment_id in old_product_id.linkeddocuments:
            try:
                old_ir_attachment_id.new_version()
                new_ir_attachment_id = old_ir_attachment_id.get_next_version()
                new_ir_attachment_ids+=new_ir_attachment_id
            except Exception as ex:
                logging.warning("ex")
        new_product_id.linkeddocuments = new_ir_attachment_ids

    def common_bom_revision(self, oldProdBrws, new_obj_brw, prodProdEnv, bomType):
        bomObj = self.env['mrp.bom']
        for bomBrws in bomObj.search([('product_tmpl_id', '=', oldProdBrws.product_tmpl_id.id), ('type', '=', bomType)]):
            newBomBrws = bomBrws.copy()
            source_id = False
            if new_obj_brw.linkeddocuments.ids:
                source_id = newProdBrws.linkeddocuments.ids[0]
            new_obj_brw.sudo().write({'product_tmpl_id': new_obj_brw.product_tmpl_id.id, 'source_id': source_id})
