##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 03/nov/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    info@omniasolutions.eu
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
Created on 03/nov/2016

@author: mboscolo
'''

from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
import os


class ir_attachment(models.Model):
    _inherit = 'ir.attachment'

    is_converted_document = fields.Boolean('Is Converted Document')
    source_convert_document = fields.Many2one('ir.attachment', 'Source Convert Document')
    converted_documents = fields.One2many('ir.attachment', 'source_convert_document', 'Converted documents')

    def show_convert_wizard(self):
        context = dict(self.env.context or {})
        context['default_document_id'] = self.id
        context['name'] = self.name
        out = {'view_type': 'form',
               'view_mode': 'form',
               'res_model': 'plm.convert',
               'view_id': self.env.ref('plm_automated_convertion.act_plm_convert_form').id,
               'type': 'ir.actions.act_window',
               'context': context,
               'target': 'new'
               }
        return out

    def checkParentCateg(self, categ):
        all_categs = categ
        for categ_id in categ.parent_id:
            all_categs += categ_id
            all_categs += self.checkParentCateg(categ_id)
        return all_categs

    def generateConvertedFiles(self):
        convert_stacks = self.env["plm.convert.stack"]
        for document in self:
            if document.document_type in ['2d', '3d']:
                categ = self.env['product.category']
                components = document.linkedcomponents.sorted(lambda line: line.engineering_revision)
                if components:
                    component = components[0]
                    categ = component.categ_id
                convert_rule = self.env["plm.convert.rule"].sudo()
                convert_stack = self.env["plm.convert.stack"].sudo()
                _clean_name, ext = os.path.splitext(document.name)
                parent_categs = self.checkParentCateg(categ)
                rules = convert_rule.search([('product_category', 'in', parent_categs.ids),
                                             ('start_format', 'ilike', ext) 
                                             ])
                rules += convert_rule.search([('convert_alone_documents', '=', True),
                                             ('start_format', 'ilike', ext) 
                                             ])
                for rule in rules:
                    if not components and not rule.convert_alone_documents:
                        continue
                    stacks = convert_stack.search([
                        ('start_format', '=', ext),
                        ('end_format', '=', rule.end_format),
                        ('start_document_id', '=', document.id),
                        ('server_id', '=', rule.server_id.id),
                        ('conversion_done', '=', False)
                        ])
                    if not stacks:
                        convert_stacks += convert_stack.create({
                            'start_format': ext,
                            'end_format' : rule.end_format,
                            'product_category': categ.id,
                            'start_document_id': document.id,
                            'output_name_rule': rule.output_name_rule,
                            'server_id': rule.server_id.id,
                            })
                    else:
                        convert_stacks += stacks
        return convert_stacks

