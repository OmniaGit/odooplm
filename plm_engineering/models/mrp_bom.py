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

"""
Created on 31 Aug 2016

@author: Daniel Smerghetto
"""

from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class MrpBomExtension(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def _get_reference_eng_type(self):
        module_brws_list = self.env['ir.module.module'].sudo().search([('name', '=', 'plm_spare')])
        for mod_brws in module_brws_list:
            if mod_brws.state == 'installed':
                return [('normal', _('Normal BoM')),
                        ('phantom', _('Sets / Phantom')),
                        ('ebom', _('Engineering BoM')),
                        ('spbom', _('Spare BoM'))]
        return [('normal', _('Normal BoM')),
                ('phantom', _('Sets / Phantom')),
                ('ebom', _('Engineering BoM'))]

    type = fields.Selection(
        '_get_reference_eng_type',
        _('BoM Type'),
        required=True,
        default='normal',
        help=_(
            "Phantom BOM: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product."
            "Ship this product as a set of components (kit).")
    )
    ebom_source_id = fields.Integer('Source Ebom ID')

    @api.model
    def _getinbom(self, pid, sid=False):
        bom_l_type = self.env['mrp.bom.line']
        bom_line_brws_list = bom_l_type.search(
            [('product_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'ebom')])
        if not bom_line_brws_list:
            bom_line_brws_list = bom_l_type.search(
                [('product_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')])
            if not bom_line_brws_list:
                bom_line_brws_list = bom_l_type.search(
                    [('product_id', '=', pid), ('source_id', '=', False), ('type', '=', 'ebom')])
            if not bom_line_brws_list:
                bom_line_brws_list = bom_l_type.search(
                    [('product_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')])
                if not bom_line_brws_list:
                    bom_line_brws_list = bom_l_type.search([('product_id', '=', pid), ('type', '=', 'ebom')])
                if not bom_line_brws_list:
                    bom_line_brws_list = bom_l_type.search([('product_id', '=', pid), ('type', '=', 'normal')])
        return bom_line_brws_list

    @api.model
    def _getbom(self, pid, sid=False):
        if sid is None:
            sid = False
        bom_brws_list = self.search([('product_tmpl_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'ebom')])
        if not bom_brws_list:
            bom_brws_list = self.search(
                [('product_tmpl_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')])
            if not bom_brws_list:
                bom_brws_list = self.search(
                    [('product_tmpl_id', '=', pid), ('source_id', '=', False), ('type', '=', 'ebom')])
                if not bom_brws_list:
                    bom_brws_list = self.search(
                        [('product_tmpl_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')])
                    if not bom_brws_list:
                        bom_brws_list = self.search([('product_tmpl_id', '=', pid), ('type', '=', 'ebom')])
                        if not bom_brws_list:
                            bom_brws_list = self.search([('product_tmpl_id', '=', pid), ('type', '=', 'normal')])
        return bom_brws_list

    @api.model
    def SaveStructure(self, relations, level=0, curr_level=0, kind_bom='ebom'):
        """
            Save EBom relations
        """
        return super(MrpBomExtension, self).save_structure(relations, level, curr_level, kind_bom='ebom')
