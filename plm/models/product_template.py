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
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""
import odoo.addons.decimal_precision as dp
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging

USED_STATES = [('draft', _('Draft')),
               ('confirmed', _('Confirmed')),
               ('released', _('Released')),
               ('undermodify', _('UnderModify')),
               ('obsoleted', _('Obsoleted'))]


class ProductTemplateExtension(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    state = fields.Selection(USED_STATES,
                             _('Status'),
                             default='draft',
                             help=_("The status of the product in its LifeCycle."),
                             readonly="True",
                             index=True)
    engineering_material = fields.Char(_('Cad Raw Material'),
                                       size=128,
                                       required=False,
                                       help=_("Raw material for current product, only description for titleblock."))
    engineering_surface = fields.Char(
        _('Cad Surface Finishing'),
        size=128,
        required=False,
        help=_("Surface finishing for current product, only description for titleblock.")
    )

    engineering_treatment = fields.Char(_('Cad Termic Treatment'),
                                        size=128,
                                        required=False,
                                        help=_("Termic treatment for current product, only description for titleblock."))

    engineering_revision = fields.Integer(_('Revision'),
                                          required=True,
                                          help=_("The revision of the product."),
                                          index=True,
                                          default=0)

    engineering_code = fields.Char(_('Part Number'),
                                   index=True,
                                   help=_("This is engineering reference to manage a different P/N from item Name."),
                                   size=256)

    #   ####################################    Overload to set default values    ####################################
    standard_price = fields.Float('Cost',
                                  compute='_compute_standard_price',
                                  inverse='_set_standard_price',
                                  search='_search_standard_price',
                                  digits='Product Price',
                                  groups="base.group_user",
                                  default=0,
                                  help="Cost of the product, in the default unit of measure of the product.")

    sale_ok = fields.Boolean('Can be Sold',
                             default=False,
                             help="Specify if the product can be selected in a sales order line.")

    engineering_writable = fields.Boolean(_('Writable'),
                                          default=True)
    is_engcode_editable = fields.Boolean(_('Engineering Editable'), default=True, compute='_compute_eng_code_editable')

    revision_count = fields.Integer(compute='_revisions_count')

    _sql_constraints = [
        ('partnumber_uniq', 'unique (engineering_code,engineering_revision)', _('Part Number has to be unique!'))
    ]

    def isLastVersion(self):
        for tempate_id in self:
            if tempate_id.id in tempate_id._getlastrev():
                return True
            return False
        
        
    def _getlastrev(self):
        result = []
        for product_template_id in self:
            product_template_ids = self.search([('engineering_code', '=', product_template_id.engineering_code)], order='engineering_revision DESC')
            for prod in product_template_ids:
                result.append(prod.id)
                break
            if not product_template_ids:
                logging.warning('[_getlastrev] No Product are found for object with engineering_code: "%s"' % (product_template_id.engineering_code))
        return list(set(result))  
        
    def _compute_eng_code_editable(self):
        for productBrws in self:
            if productBrws.engineering_code in ['', False, '-']:
                productBrws.is_engcode_editable = True
            else:
                productBrws.is_engcode_editable = False

    def engineering_products_open(self):
        product_id = False
        related_product_brws_list = self.env['product.product'].search([('product_tmpl_id', '=', self.id)])
        for related_product_brws in related_product_brws_list:
            product_id = related_product_brws.id
        form_id = self.env.ref("plm.plm_component_base_form")
        if product_id and form_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Product Engineering'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.product',
                'res_id': product_id,
                'views': [(form_id.id, 'form')],
            }

    @api.model
    def getAllVersionTemplate(self):
        """
        get All version product_tempate based on this one
        """
        return self.search([('engineering_code', '=', self.engineering_code)])

    def _revisions_count(self):
        """
        get All version product_tempate based on this one
        """
        for product_template_id in self:
            if product_template_id.engineering_code:
                product_template_id.revision_count = product_template_id.search_count([('engineering_code', '=', product_template_id.engineering_code)])
            else:
                product_template_id.revision_count = 0

    def open_related_revisions(self):
        return {'name': _('Products'),
                'res_model': 'product.template',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.getAllVersionTemplate().ids)],
                'context': {}}

    def plm_sanitize(self, vals):
        fields_view_get = self.fields_get_keys()
        out = []
        if isinstance(vals, (list, tuple)):
            for k in vals:
                if k in fields_view_get:
                    out.append(k)
            return out
        else:
            valsKey = list(vals.keys())
            for k in valsKey:
                if k not in fields_view_get:
                    del vals[k]
        return vals

    @api.model
    def create(self, vals):
        vals = self.plm_sanitize(vals)
        return super(ProductTemplateExtension, self).create(vals)

    def write(self, vals):
        vals = self.plm_sanitize(vals)
        return super(ProductTemplateExtension, self).write(vals)

    def copy(self, default={}):
        """
            Overwrite the default copy method
        """
        if not self.engineering_code:
            return super(ProductTemplateExtension, self).copy(default)
        if not default:
            default = {}

        def clearBrokenComponents():
            """
                Remove broken components before make the copy. So the procedure will not fail
            """
            # Do not check also for name because may cause an error in revision procedure
            # due to translations
            brokenComponents = self.search([('engineering_code', '=', '-')])
            for brokenComp in brokenComponents:
                brokenComp.unlink()

        if not default.get('name', False):
            default['name'] = '-'                   # If field is required super of clone will fail returning False, this is the case
            default['engineering_code'] = '-'
            default['engineering_revision'] = 0
            clearBrokenComponents()
        if default.get('engineering_code', '') == '-':
            clearBrokenComponents()
        # assign default value
        default['state'] = 'draft'
        default['engineering_writable'] = True
        default['linkeddocuments'] = []
        default['release_date'] = False
        objId = super(ProductTemplateExtension, self).copy(default)
        if objId:
            objId.is_engcode_editable = True
        return objId

    @api.model
    def init(self):
        cr = self.env.cr
        cr.execute("""
        -- Index: product_template_engcode_index
        -- Index: product_template_engcode_index
        DROP INDEX IF EXISTS product_template_engcode_index;
        CREATE INDEX product_template_engcode_index
          ON product_template
          USING btree
          (engineering_code);
        """)

        cr.execute("""
        -- Index: product_template_engcoderev_index
        DROP INDEX IF EXISTS product_template_engcoderev_index;
        CREATE INDEX product_template_engcoderev_index
          ON product_template
          USING btree
          (engineering_code, engineering_revision);
        """)
