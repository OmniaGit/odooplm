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

"""
Created on 30 Aug 2016

@author: Daniel Smerghetto
"""

from odoo import models
from odoo import api


class ProductTemplate(models.Model):
    _inherit = 'product.product'

    def open_spare_bom(self):
        boms = self.get_related_boms()
        domain = [('id', 'in', boms.ids), ('type', '=', 'spbom')]
        return self.common_open(_('Related Boms'), 'mrp.bom', 'tree,form', 'form', boms.ids, self.env.context, domain)

    def create_spare_bom(self):
        context = self.env.context.copy()
        context.update({'default_type': 'spbom'})
        doc_ids = self.get_related_docs()
        if doc_ids:
            context.update(
                {'default_product_tmpl_id': self.product_tmpl_id.id})
        return self.common_open(_('Related Boms'), 'mrp.bom', 'form', 'form', False, context)
    
    def action_create_spare_bom_wf(self):
        """
            Create a new Spare Bom if doesn't exist (action callable from code)
        """
        self._create_spare_bom()
        return False

    def _create_spare_bom(self):
        """
            Create a new Spare Bom (recursive on all EBom children)
        """
        processed_ids = []

        def _create_local_spare_bom(prod_id):
            new_bom_brws = None
            if prod_id in processed_ids:
                return False
            processed_ids.append(prod_id)
            for spare_bom_brws in self.browse(prod_id):
                if not spare_bom_brws:
                    return False
                if '-Spare' in spare_bom_brws.name:
                    return False
                source_bom_type = self.env.context.get('source_bom_type', 'ebom')
                bom_type = self.env['mrp.bom']
                bom_l_type = self.env['mrp.bom.line']
                spare_bom_brws_list = bom_type.search([('product_tmpl_id', '=', spare_bom_brws.product_tmpl_id.id),
                                                   ('type', '=', 'spbom')])
                normal_bom_brws_list = bom_type.search([('product_tmpl_id', '=', spare_bom_brws.product_tmpl_id.id),
                                                    ('type', '=', 'normal')])
                if not normal_bom_brws_list:
                    normal_bom_brws_list = bom_type.search([('product_tmpl_id', '=', spare_bom_brws.product_tmpl_id.id),
                                                        ('type', '=', source_bom_type)])
                defaults = {}
                if not spare_bom_brws_list:
                    if spare_bom_brws.std_description.bom_tmpl:
                        new_bom_brws = bom_type.browse(spare_bom_brws.std_description.bom_tmpl.id).copy(defaults)
                    if (not new_bom_brws) and normal_bom_brws_list:
                            new_bom_brws = normal_bom_brws_list[0].copy(defaults)
                    if new_bom_brws:
                        new_bom_brws.write({'name': spare_bom_brws.name,
                                            'product_id': spare_bom_brws.id,
                                            'type': 'spbom'})
                        ok_rows = self._summarizeBom(new_bom_brws.bom_line_ids)
                        for bom_line in list(set(new_bom_brws.bom_line_ids) ^ set(ok_rows)):
                            bom_l_type.browse(bom_line.id).unlink()
                        for bom_line in ok_rows:
                            bom_l_type.browse(bom_line.id).write({'type': 'spbom',
                                                                'source_id': False,
                                                                'name': bom_line.product_id.name,
                                                                'product_qty': bom_line.product_qty})
                            _create_local_spare_bom(bom_line.product_id.id)
                else:
                    for bom_line in spare_bom_brws_list[0].bom_line_ids:
                        _create_local_spare_bom(bom_line.product_id.id)
                return False
        return _create_local_spare_bom(self.id)