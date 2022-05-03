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
#
# preview pdf conversion
#
import os
import sys
import json
import base64
import tempfile
from ezdxf import recover
from ezdxf.addons.drawing import matplotlib
ALLOW_CONVERSION_FORMAT = ['.dxf']
#
#
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

    def convert_from_dxf_to(self, toFormat):
        """
            convert using the exdxf library
        """
        if toFormat.replace(".", "") not in ['png','pdf','svg','jpg']:
            raise UserError("Format %s not supported" % toFormat)
            
        store_fname = self._full_path(self.store_fname)
        doc, auditor = recover.readfile(store_fname)
        if not auditor.has_errors:
            tmpdirname = tempfile.gettempdir()
            name, exte = os.path.splitext(self.name)   
            newFileName=os.path.join(tmpdirname, '%s%s' % (name, toFormat))
            matplotlib.qsave(doc.modelspace(), newFileName)
            return newFileName
        raise Exception("Unable to perform the conversion Error: %s" % auditor.has_errors)
                            
    def convert_to_format(self, toFormat):
        """
            convert the attachment to the given format
        """
        for ir_attachment in self:
            for extention in ALLOW_CONVERSION_FORMAT:
                if extention in ir_attachment.name.lower():
                    return ir_attachment.convert_from_dxf_to(toFormat)


    def _updatePreview(self):
        for ir_attachment in self:
            store_fname = ir_attachment._full_path(ir_attachment.store_fname)
            doc, auditor = recover.readfile(store_fname)
            if not auditor.has_errors:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    name, exte = os.path.splitext(ir_attachment.name)   
                    pngName=os.path.join(tmpdirname, '%s.png' % name)
                    matplotlib.qsave(doc.modelspace(), pngName)
                    pdfName=os.path.join(tmpdirname, '%s.pdf' % name)
                    matplotlib.qsave(doc.modelspace(), pdfName)
                    with open(pngName,'rb') as pngStream:
                        ir_attachment.preview =  base64.b64encode(pngStream.read())
                    with open(pdfName,'rb') as pdfStream:
                        ir_attachment.printout =  base64.b64encode(pdfStream.read())
            
            
    def createPreview(self):
        obj_stack = self.env['plm.convert.stack']
        for ir_attachment in self:
            for extention in ALLOW_CONVERSION_FORMAT:
                if extention in ir_attachment.name.lower():
                    end_format = json.dumps(['png_pdf_update']) 
                    if not obj_stack.search_count([('start_document_id','=',ir_attachment.id),('end_format','=', end_format)]):
                        obj_stack.create({
                            'start_format': extention,
                            'end_format': end_format,
                            'start_document_id': ir_attachment.id,
                            'server_id': self.env.ref('plm_automated_convertion.odoo_local_server').id,
                            })
    @api.model
    def create(self, vals):
        ret = super(ir_attachment, self).create(vals)
        #ret.createPreview()
        return ret

    def write(self, vals):
        ret = super(ir_attachment, self).write(vals)
        #self.createPreview()
        return ret
