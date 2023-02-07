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
#
import os
import sys
import json
import shutil
import base64
import logging
import tempfile
#
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
#
# conversion
#
from ezdxf import recover
from ezdxf.addons.drawing import matplotlib
ALLOW_CONVERSION_FORMAT = ['.dxf','.obj','.stp','.step','.stl']
#
from .obj2png import ObjFile 
#
from stl import mesh
import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d
try:
    import cadquery as cq
except Exception as ex:
    logging.error(ex)
#
#
from .cad_excenge import convert as exConvert
from .cad_excenge import FORMAT_FROM as ex_from_format
from .cad_excenge import FORMAT_TO as ex_from_to
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

    def convert_from_obj_to(self, toFormat):
        """
            convert using the exdxf library
        """
        if toFormat.replace(".", "") not in ['png','pdf','svg','jpg']:
            raise UserError("Format %s not supported" % toFormat)
            
        store_fname = self._full_path(self.store_fname)
        o=ObjFile(store_fname)
        tmpdirname = tempfile.gettempdir()
        name, exte = os.path.splitext(self.name)   
        newFileName=os.path.join(tmpdirname, '%s%s' % (name, toFormat))
        o.Plot(newFileName, dpi=100)
        return newFileName
    
    def convert_from_step_to(self, toFormat):
        newFileName = ''
        try:
            if toFormat.replace(".", "").lower() not in ['png','pdf','svg','jpg','stl']:
                raise UserError("Format %s not supported" % toFormat)
            store_fname = self._full_path(self.store_fname)
            result = cq.importers.importStep(store_fname)
            with tempfile.TemporaryDirectory() as tmpdirname:
                name, exte = os.path.splitext(self.name)
                stlName=os.path.join(tmpdirname, '%s.stl' % name)
                cq.exporters.export(result,
                                    stlName,
                                    tolerance=1.0,
                                    angularTolerance=1.0)
                newFileName=os.path.join(tempfile.gettempdir(), '%s%s' % (name, toFormat))   
                if  '.stl'.lower() in toFormat:
                    shutil.copy(stlName, newFileName)
                    return newFileName
                #
                # Create a new plot
                #
                figure = plt.figure()
                axes = mplot3d.Axes3D(figure)
                #
                # Load the STL files and add the vectors to the plot
                #
                your_mesh = mesh.Mesh.from_file(stlName)
                axes.add_collection3d(mplot3d.art3d.Poly3DCollection(your_mesh.vectors))
                #
                # Auto scale to the mesh size
                #
                scale = your_mesh.points.flatten()
                axes.auto_scale_xyz(scale, scale, scale)
                #
             
                plt.savefig(newFileName,
                            dpi=100,
                            transparent=True)
                plt.close()
        except Exception as ex:
            raise UserError('Cannot convert due to error %r' % (ex))
        return newFileName

    def convert_from_stl_to(self, toFormat):
        newFileName = ''
        if toFormat.replace(".", "").lower() not in ['png','pdf','svg','jpg']:
            raise UserError("Format %s not supported" % toFormat)
        store_fname = self._full_path(self.store_fname)
        with tempfile.TemporaryDirectory() as tmpdirname:
            name, exte = os.path.splitext(self.name)
            newFileName=os.path.join(tempfile.gettempdir(), '%s%s' % (name, toFormat))   
            #
            # Create a new plot
            #
            figure = plt.figure()
            axes = mplot3d.Axes3D(figure)
            #
            # Load the STL files and add the vectors to the plot
            #
            your_mesh = mesh.Mesh.from_file(store_fname)
            axes.add_collection3d(mplot3d.art3d.Poly3DCollection(your_mesh.vectors))
            #
            # Auto scale to the mesh size
            #
            scale = your_mesh.points.flatten()
            axes.auto_scale_xyz(scale, scale, scale)
            #
         
            plt.savefig(newFileName,
                        dpi=100,
                        transparent=True)
            plt.close()
        return newFileName

    def convert_to_format(self, toFormat, excangePath=None):
        """
            convert the attachment to the given format
        """
        obj_attachment = self.env['ir.attachment']
        for ir_attachment in self:
            #
            # check before cad excange
            #
            name, exte = os.path.splitext(os.path.basename(ir_attachment.name))
            if excangePath and os.path.exists(excangePath) and exte.lower() in ex_from_format and toFormat.lower() in ex_from_to:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    full_path_parent_target = os.path.join(tmpdirname, ir_attachment.name)
                    shutil.copy(ir_attachment._full_path(ir_attachment.store_fname),
                                full_path_parent_target)
                    for docu_id_child_id in ir_attachment.getRelatedHiTree(ir_attachment.id, True, True):
                        ir_attachment_child = obj_attachment.browse(docu_id_child_id)
                        full_path_child = obj_attachment._full_path(ir_attachment_child.store_fname)
                        shutil.copy(full_path_child,
                                    os.path.join(tmpdirname, ir_attachment_child.name))
                    return exConvert(excangePath,
                                     full_path_parent_target,
                                     toFormat)
            else:
                for extention in ALLOW_CONVERSION_FORMAT:
                    if extention in ir_attachment.name.lower():
                        if extention.lower()=='.dxf':
                            return ir_attachment.convert_from_dxf_to(toFormat)
                        elif extention.lower()=='.obj':
                            return ir_attachment.convert_from_obj_to(toFormat)
                        elif extention.lower() in ['.stp', '.step']:
                            return ir_attachment.convert_from_step_to(toFormat)
                        elif extention.lower()=='.stl':
                            return ir_attachment.convert_from_stl_to(toFormat)
                        else:
                            raise UserError(_("Format %s not supported") % toFormat)
            raise UserError(_("Format %s not supported") % toFormat)
                        
    def _updatePreview(self):
        for ir_attachment in self:
            store_fname = ir_attachment._full_path(ir_attachment.store_fname)
            if '.dxf' in ir_attachment.name.lower():
                ir_attachment._updatePreviewFromDxf(store_fname)
            if '.obj' in ir_attachment.name.lower():
                 ir_attachment._updatePreviewFromObj(store_fname)
            if '.stp' in ir_attachment.name.lower() or 'step' in ir_attachment.name.lower():
                ir_attachment._updatePreviewFromStp(store_fname)
            if '.stl' in ir_attachment.name.lower():
                ir_attachment._updatePreviewFromStl(store_fname)

    def _updatePreviewFromStl(self, fromFile):
        with tempfile.TemporaryDirectory() as tmpdirname:
            name, exte = os.path.splitext(self.name) 
            pngName=os.path.join(tmpdirname, '%s.png' % name)
            converted_file = self.convert_from_stl_to('.png')
            with open(converted_file,'rb') as pngStream:
                self.preview =  base64.b64encode(pngStream.read())

    
    def _updatePreviewFromStp(self, fromFile):
        with tempfile.TemporaryDirectory() as tmpdirname:
            name, exte = os.path.splitext(self.name) 
            pngName=os.path.join(tmpdirname, '%s.png' % name)
            converted_file = self.convert_from_step_to('.png')
            with open(converted_file,'rb') as pngStream:
                self.preview =  base64.b64encode(pngStream.read())

    def _updatePreviewFromObj(self, fromFile):
        with tempfile.TemporaryDirectory() as tmpdirname:
            name, exte = os.path.splitext(self.name) 
            pngName=os.path.join(tmpdirname, '%s.png' % name)
            converted_file = self.convert_from_obj_to('.png')
            with open(converted_file,'rb') as pngStream:
                self.preview =  base64.b64encode(pngStream.read())
                    
    def _updatePreviewFromDxf(self, fromFile):
            doc, auditor = recover.readfile(fromFile)
            if not auditor.has_errors:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    name, exte = os.path.splitext(self.name)   
                    pngName=os.path.join(tmpdirname, '%s.png' % name)
                    matplotlib.qsave(doc.modelspace(), pngName)
                    pdfName=os.path.join(tmpdirname, '%s.pdf' % name)
                    matplotlib.qsave(doc.modelspace(), pdfName)
                    with open(pngName,'rb') as pngStream:
                        self.preview =  base64.b64encode(pngStream.read())
                    with open(pdfName,'rb') as pdfStream:
                        self.printout =  base64.b64encode(pdfStream.read())
            
            
    def createPreviewStack(self):
        obj_stack = self.env['plm.convert.stack']
        for ir_attachment in self:
            for extention in ALLOW_CONVERSION_FORMAT:
                if extention in ir_attachment.name.lower():
                    if not obj_stack.search_count([('start_document_id','=',ir_attachment.id),
                                                   ('operation_type','=', 'UPDATE')]):
                        conv_format = self.checkCreateDefaultPreviewFormat(extention)
                        obj_stack.create({
                            'operation_type': 'UPDATE',
                            'start_document_id': ir_attachment.id,
                            'convrsion_rule': conv_format.id
                            })

    def checkCreateDefaultPreviewFormat(self, start_format):
        format_model = self.env['plm.convert.format']
        if start_format.upper() in ['.STP']:
            format_model =  self.env.ref('plm_automated_convertion.update_stp_preview_png')
        elif start_format.upper() in ['.STEP']:
            format_model =  self.env.ref('plm_automated_convertion.update_step_preview_png')
        elif start_format.upper() in ['.DXF']:
            format_model =  self.env.ref('plm_automated_convertion.update_dxf_preview_png')
        elif start_format.upper() in ['.OBJ']:
            format_model =  self.env.ref('plm_automated_convertion.update_obj_preview_png')
        elif start_format.upper() in ['.STL']:
            format_model =  self.env.ref('plm_automated_convertion.update_stl_preview_png')
        else:
            if not format_ids:
                format_ids = format_model.search([
                    ('end_format', '=', '.png'),
                    ('start_format', '=', start_format),
                    ('available', '=', True)
                    ])
                for format in format_ids:
                    format_model = format
                    break
        return format_model

    @api.model
    def create(self, vals):
        ret = super(ir_attachment, self).create(vals)
        ret.createPreviewStack()
        return ret

    def write(self, vals):
        ret = super(ir_attachment, self).write(vals)
        self.createPreviewStack()
        return ret
