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
import logging

from odoo import models
from odoo import api
from odoo import osv
from odoo import _
from odoo.exceptions import UserError


class ProductProductExtension(models.Model):
    _inherit = 'product.product'

    @api.model
    def create_bom_from_ebom(self, obj_product_product_brw, new_bom_type, summarize=False, migrate_custom_lines=True):
        """
            create a new bom starting from ebom
        """
        bom_type = self.env['mrp.bom']
        bom_l_type = self.env['mrp.bom.line']
        prod_tmpl_obj = self.env['product.template']
        stock_config_settings = self.env['res.config.settings']
        variant_is_installed = False
        if len(stock_config_settings.search([('group_product_variant', '=', 1)])) > 0:
            variant_is_installed = True
        collect_list = []

        def get_previous_normal_bom(bomBrws, exclude_bom_id=False):
            out_bom_brws = []
            engineering_code = bomBrws.product_tmpl_id.engineering_code
            previous_rev_product_brws_list = prod_tmpl_obj.search([('engineering_code', '=', engineering_code)], order='engineering_revision desc')
            for prod_brws in previous_rev_product_brws_list:
                old_bom_brws_list = bom_type.search([('product_tmpl_id', '=', prod_brws.id),
                                                     ('type', '=', new_bom_type)])
                for old_bom_brws in old_bom_brws_list:
                    if old_bom_brws == exclude_bom_id:
                        continue
                    out_bom_brws.append(old_bom_brws)
                if out_bom_brws:
                    break
            return out_bom_brws

        e_bom_id = False
        new_nbom_id = False
        if new_bom_type not in ['normal', 'phantom']:
            raise UserError(_("Could not convert source bom to %r" % new_bom_type))
        product_template_id = obj_product_product_brw.product_tmpl_id.id
        bom_brws_list = bom_type.search([('product_tmpl_id', '=', product_template_id),
                                         ('type', '=', new_bom_type)], order='engineering_revision DESC', limit=1)
        if bom_brws_list:
            for bom_brws in bom_brws_list:
                for bom_line in bom_brws.bom_line_ids:
                    self.create_bom_from_ebom(bom_line.product_id, new_bom_type, summarize)
                break
        else:
            eng_bom_brws_list = bom_type.search([('product_tmpl_id', '=', product_template_id),
                                                 ('type', '=', 'ebom')], order='engineering_revision DESC', limit=1)
            if not eng_bom_brws_list:
                logging.info('No EBOM or NBOM found for template id: {}'.format(product_template_id))
                return []
            for e_bom_brws in eng_bom_brws_list:
                e_bom_id = e_bom_brws.id
                new_bom_brws = e_bom_brws.copy({})
                new_nbom_id = new_bom_brws
                values = {'name': obj_product_product_brw.name,
                          'product_tmpl_id': product_template_id,
                          'type': new_bom_type,
                          'ebom_source_id': e_bom_id, }
                if not variant_is_installed:
                    values['product_id'] = False
                new_bom_brws.write(values)

                if summarize:
                    ok_rows = self._summarizeBom(new_bom_brws.bom_line_ids)
                    # remove not summarized lines
                    for bom_line in list(set(new_bom_brws.bom_line_ids) ^ set(ok_rows)):
                        bom_line.unlink()
                    # update the quantity with the summarized values
                    for bom_line in ok_rows:
                        bom_line.write({
                            'type': new_bom_type,
                            'source_id': False,
                            'product_qty': bom_line.product_qty,
                            'ebom_source_id': e_bom_id,
                        })
                        self.create_bom_from_ebom(bom_line.product_id, new_bom_type, summarize=summarize)
                else:
                    for line_brws in new_bom_brws.bom_line_ids:
                        self.create_bom_from_ebom(line_brws.product_id, new_bom_type, summarize=summarize)
                        line_brws.type = new_bom_type
                        line_brws.ebom_source_id = e_bom_id
                obj_product_product_brw.wf_message_post(body=_('Created %r' % new_bom_type))
                break
        if new_nbom_id and e_bom_id and migrate_custom_lines:
            # if e_bom_id --> normal BOM was not existing
            ebom_id = bom_type.browse(e_bom_id)
            old_bom_list = get_previous_normal_bom(ebom_id, new_nbom_id)
            for old_n_bom in old_bom_list:
                collect_list.extend(
                    self.addOldBomLines(old_n_bom, new_nbom_id, bom_l_type, new_bom_type, ebom_id, bom_type,
                                        summarize))
        return collect_list

    @api.model
    def addOldBomLines(self, old_n_bom, new_bom_brws, bom_line_obj, new_bom_type, bom_brws, bom_type, summarize=False):
        collect_list = []

        def verify_summarize(product_id, old_prod_qty):
            to_return = old_prod_qty, False
            template_name = new_bom_brws.product_tmpl_id.name
            out_msg = ''
            for new_line in new_bom_brws.bom_line_ids:
                if new_line.product_id.id == product_id:
                    product_name = new_line.product_id.name
                    to_return = 0, False
                    if summarize:
                        out_msg = out_msg + 'In BOM "%s" line "%s" has been summarized.' % (template_name, product_name)
                        to_return = new_line.product_qty + old_prod_qty, new_line.id
                    else:
                        out_msg = out_msg + 'In BOM "%s" line "%s" has been not summarized.' % (template_name, product_name)
                        to_return = new_line.product_qty, False
                    collect_list.append(out_msg)
                    return to_return
            return to_return

        for old_brws_line in old_n_bom.bom_line_ids:
            if not old_brws_line.ebom_source_id:
                qty, found_line_id = verify_summarize(old_brws_line.product_id.id, old_brws_line.product_qty)
                if not found_line_id:
                    new_bom_line_brws = old_brws_line.copy()
                    new_bom_line_brws.write({
                        'type': new_bom_type,
                        'source_id': False,
                        'product_qty': old_brws_line.product_qty,
                        'ebom_source_id': False,
                    })
                    new_bom_brws.write({'bom_line_ids': [(4, new_bom_line_brws.id, 0)]})
                else:
                    bom_line_obj.browse(found_line_id).write({'product_qty': qty})
        return collect_list

    @api.model
    def _create_normalBom(self, idd):
        """
            Create a new Normal Bom (recursive on all EBom children)
        """
        defaults = {}
        if idd in self.processedIds:
            return False
        check_obj = self.browse(idd)
        if not check_obj:
            return False
        bom_type = self.env['mrp.bom']
        bom_l_type = self.env['mrp.bom.line']
        product_template_id = check_obj.product_tmpl_id.id
        obj_boms = bom_type.search([('product_tmpl_id', '=', product_template_id),
                                    ('type', '=', 'normal')])
        if not obj_boms:
            bom_brws_list = bom_type.search([('product_tmpl_id', '=', product_template_id),
                                             ('type', '=', 'ebom')])
            for bom_brws in bom_brws_list:
                new_bom_brws = bom_brws.copy(defaults)
                self.processedIds.append(idd)
                if new_bom_brws:
                    new_bom_brws.write(
                        {'name': check_obj.name,
                         'product_id': check_obj.id,
                         'type': 'normal'},
                        check=False)
                    ok_rows = self._summarizeBom(new_bom_brws.bom_line_ids)
                    for bom_line in list(set(new_bom_brws.bom_line_ids) ^ set(ok_rows)):
                        bom_line.unlink()
                    for bom_line in ok_rows:
                        bom_l_type.browse([bom_line.id]).write({
                            'type': 'normal',
                            'source_id': False,
                            'name': bom_line.product_id.name,
                            'product_qty': bom_line.product_qty
                        })
                        self._create_normalBom(bom_line.product_id.id)
        else:
            for objBom in obj_boms:
                for bom_line in objBom.bom_line_ids:
                    self._create_normalBom(bom_line.product_id.id)
        return False


class ProductTemporaryNormalBom(osv.osv.osv_memory):
    _inherit = "plm.temporary"


    def action_create_normalBom(self):
        """
            Create a new Normal Bom if doesn't exist (action callable from views)
        """
        for obj_brws in self:
            migrate_custom_lines = obj_brws.migrate_custom_lines
            selected_ids = obj_brws.env.context.get('active_ids', [])
            obj_type = obj_brws.env.context.get('active_model', '')
            if obj_type != 'product.product':
                raise UserError(_("The creation of the normalBom works only on product_product object"))
            if not selected_ids:
                raise UserError(_("Select a product before to continue"))
            obj_type = obj_brws.env.context.get('active_model', False)
            product_product_type_object = obj_brws.env[obj_type]
            for product_browse in product_product_type_object.browse(selected_ids):
                id_template = product_browse.product_tmpl_id.id
                obj_boms = obj_brws.env['mrp.bom'].search([('product_tmpl_id', '=', id_template),
                                                           ('type', '=', 'normal')])
                if obj_boms:
                    raise UserError(_("Normal BoM for Part '%s' and revision '%s' already exists." % (obj_boms.product_tmpl_id.engineering_code, obj_boms.product_tmpl_id.engineering_revision)))
                
                if obj_brws.env['mrp.bom'].search_count([('product_tmpl_id', '=', id_template),
                                                                 ('type', '=', 'phantom')]):
                    raise UserError(_("""Normal BoM for Part '%s' and revision '%s' have a kit bom present.\n"""
                                      """If you whant to create the normal bom please delete the kit bom first !
                                        """ % (product_browse.engineering_code, obj_boms.product_tmpl_id.engineering_revision)))
                line_messages_list = product_product_type_object.create_bom_from_ebom(
                    product_browse, 'normal',
                    obj_brws.summarize,
                    migrate_custom_lines
                )
                if line_messages_list:
                    out_mess = ''
                    for mess in line_messages_list:
                        out_mess = out_mess + '\n' + mess
                    t_mess_obj = obj_brws.env["plm.temporary.message"]
                    t_mess_id = t_mess_obj.create({'name': out_mess})
                    return {
                        'name': _('Result'),
                        'view_type': 'form',
                        "view_mode": 'form',
                        'res_model': "plm.temporary.message",
                        'res_id': t_mess_id.id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                    }
        return {}
