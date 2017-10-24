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

from odoo import models
from odoo import api
from odoo import osv
from odoo import _
from odoo.exceptions import UserError
import logging


class ProductProductExtension(models.Model):
    _inherit = 'product.product'

    @api.model
    def create_bom_from_ebom(self, objProductProductBrw, newBomType, summarize=False, migrate_custom_lines=True):
        """
            create a new bom starting from ebom
        """
        bomType = self.env['mrp.bom']
        bomLType = self.env['mrp.bom.line']
        prodTmplObj = self.env['product.template']
        stockConfigSettings = self.env['res.config.settings']
        variantIsInstalled = False
        if len(stockConfigSettings.search([('group_product_variant', '=', 1)])) > 0:
            variantIsInstalled = True
        collectList = []

        def getPreviousNormalBOM(bomBrws):
            outBomBrws = []
            engineering_code = bomBrws.product_tmpl_id.engineering_code
            previousRevProductBrwsList = prodTmplObj.search([('engineering_code', '=', engineering_code)])
            for prodBrws in previousRevProductBrwsList:
                oldBomBrwsList = bomType.search([('product_tmpl_id', '=', prodBrws.id),
                                                 ('type', '=', newBomType)])
                for oldBomBrws in oldBomBrwsList:
                    outBomBrws.append(oldBomBrws)
                break
            return outBomBrws

        eBomId = False
        newidBom = False
        if newBomType not in ['normal', 'phantom']:
            raise UserError(_("Could not convert source bom to %r" % newBomType))
        product_template_id = objProductProductBrw.product_tmpl_id.id
        bomBrwsList = bomType.search([('product_tmpl_id', '=', product_template_id),
                                      ('type', '=', newBomType)])
        if bomBrwsList:
            for bomBrws in bomBrwsList:
                for bom_line in bomBrws.bom_line_ids:
                    self.create_bom_from_ebom(bom_line.product_id, newBomType, summarize)
                break
        else:
            engBomBrwsList = bomType.search([('product_tmpl_id', '=', product_template_id),
                                             ('type', '=', 'ebom')])
            if not engBomBrwsList:
                logging.info('No EBOM or NBOM found for template id: %r' % (product_template_id))
                return []
            for eBomBrws in engBomBrwsList:
                eBomId = eBomBrws.id
                newBomBrws = eBomBrws.copy({})
                newidBom = newBomBrws
                values = {'name': objProductProductBrw.name,
                          'product_tmpl_id': product_template_id,
                          'type': newBomType,
                          'ebom_source_id': eBomId,
                          }
                if not variantIsInstalled:
                    values['product_id'] = False
                newBomBrws.write(values,
                                 check=False)

                if summarize:
                    ok_rows = self._summarizeBom(newBomBrws.bom_line_ids)
                    # remove not summarized lines
                    for bom_line in list(set(newBomBrws.bom_line_ids) ^ set(ok_rows)):
                        bom_line.unlink()
                    # update the quantity with the summarized values
                    for bom_line in ok_rows:
                        bom_line.write({'type': newBomType,
                                        'source_id': False,
                                        'product_qty': bom_line.product_qty,
                                        'ebom_source_id': eBomId,
                                        })
                        self.create_bom_from_ebom(bom_line.product_id, newBomType, summarize=summarize)
                else:
                    for lineBrws in newBomBrws.bom_line_ids:
                        self.create_bom_from_ebom(lineBrws.product_id, newBomType, summarize=summarize)
                objProductProductBrw.wf_message_post(body=_('Created %r' % newBomType))
                break
        if newidBom and eBomId and migrate_custom_lines:
            bomBrws = bomType.browse(eBomId)
            oldBomList = getPreviousNormalBOM(bomBrws)
            for oldNBom in oldBomList:
                newBomBrws = newidBom
                if oldNBom != oldBomList[-1]:       # Because in the previous loop I already have a copy of the normal BOM
                    newBomBrws = bomType.copy(newidBom)
                collectList.extend(self.addOldBomLines(oldNBom, newBomBrws, bomLType, newBomType, bomBrws, bomType, summarize))
        return collectList

    @api.model
    def addOldBomLines(self, oldNBom, newBomBrws, bomLineObj, newBomType, bomBrws, bomType, summarize=False):
        collectList = []

        def verifySummarize(product_id, old_prod_qty):
            toReturn = old_prod_qty, False
            for newLine in newBomBrws.bom_line_ids:
                if newLine.product_id.id == product_id:
                    templateName = newBomBrws.product_tmpl_id.name
                    product_name = newLine.product_id.name
                    outMsg = 'In BOM "%s" ' % (templateName)
                    toReturn = 0, False
                    if summarize:
                        outMsg = outMsg + 'line "%s" has been summarized.' % (product_name)
                        toReturn = newLine.product_qty + old_prod_qty, newLine.id
                    else:
                        outMsg = outMsg + 'line "%s" has been not summarized.' % (product_name)
                        toReturn = newLine.product_qty, newLine.id
                    collectList.append(outMsg)
                    return toReturn
            return toReturn

        for oldBrwsLine in oldNBom.bom_line_ids:
            if not oldBrwsLine.ebom_source_id:
                qty, foundLineId = verifySummarize(oldBrwsLine.product_id.id, oldBrwsLine.product_qty)
                if not foundLineId:
                    newbomLineBrws = oldBrwsLine.copy()
                    newbomLineBrws.write({'type': newBomType,
                                          'source_id': False,
                                          'product_qty': oldBrwsLine.product_qty,
                                          'ebom_source_id': False,
                                          })
                    newBomBrws.write({'bom_line_ids': [(4, newbomLineBrws.id, 0)]})
                else:
                    bomLineObj.browse(foundLineId).write({'product_qty': qty})
        return collectList

    @api.model
    def _create_normalBom(self, idd):
        """
            Create a new Normal Bom (recursive on all EBom children)
        """
        defaults = {}
        if idd in self.processedIds:
            return False
        checkObj = self.browse(idd)
        if not checkObj:
            return False
        bomType = self.env['mrp.bom']
        bomLType = self.env['mrp.bom.line']
        product_template_id = checkObj.product_tmpl_id.id
        objBoms = bomType.search([('product_tmpl_id', '=', product_template_id),
                                  ('type', '=', 'normal')])
        if not objBoms:
            bomBrwsList = bomType.search([('product_tmpl_id', '=', product_template_id),
                                          ('type', '=', 'ebom')])
            for bomBrws in bomBrwsList:
                newBomBrws = bomBrws.copy(defaults)
                self.processedIds.append(idd)
                if newBomBrws:
                    newBomBrws.write({'name': checkObj.name,
                                      'product_id': checkObj.id,
                                      'type': 'normal'},
                                     check=False)
                    ok_rows = self._summarizeBom(newBomBrws.bom_line_ids)
                    for bom_line in list(set(newBomBrws.bom_line_ids) ^ set(ok_rows)):
                        bom_line.unlink()
                    for bom_line in ok_rows:
                        bomLType.browse([bom_line.id]).write({'type': 'normal',
                                                              'source_id': False,
                                                              'name': bom_line.product_id.name,
                                                              'product_qty': bom_line.product_qty})
                        self._create_normalBom(bom_line.product_id.id)
        else:
            for objBom in objBoms:
                for bom_line in objBom.bom_line_ids:
                    self._create_normalBom(bom_line.product_id.id)
        return False


class ProductTemporaryNormalBom(osv.osv.osv_memory):
    _inherit = "plm.temporary"

    @api.multi
    def action_create_normalBom(self):
        """
            Create a new Normal Bom if doesn't exist (action callable from views)
        """
        for objBrws in self:
            migrate_custom_lines = objBrws.migrate_custom_lines
            selectdIds = objBrws.env.context.get('active_ids', [])
            objType = objBrws.env.context.get('active_model', '')
            if objType != 'product.product':
                raise UserError(_("The creation of the normalBom works only on product_product object"))
            if not selectdIds:
                raise UserError(_("Select a product before to continue"))
            objType = objBrws.env.context.get('active_model', False)
            product_product_type_object = objBrws.env[objType]
            for productBrowse in product_product_type_object.browse(selectdIds):
                idTemplate = productBrowse.product_tmpl_id.id
                objBoms = objBrws.env['mrp.bom'].search([('product_tmpl_id', '=', idTemplate),
                                                         ('type', '=', 'normal')])
                if objBoms:
                    raise UserError(_("Normal BoM for Part %r already exists." % (objBoms)))
                lineMessaggesList = product_product_type_object.create_bom_from_ebom(productBrowse, 'normal', objBrws.summarize, migrate_custom_lines)
                if lineMessaggesList:
                    outMess = ''
                    for mess in lineMessaggesList:
                        outMess = outMess + '\n' + mess
                    t_mess_obj = objBrws.env["plm.temporary.message"]
                    t_mess_id = t_mess_obj.create({'name': outMess})
                    return {'name': _('Result'),
                            'view_type': 'form',
                            "view_mode": 'form',
                            'res_model': "plm.temporary.message",
                            'res_id': t_mess_id.id,
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            }
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
