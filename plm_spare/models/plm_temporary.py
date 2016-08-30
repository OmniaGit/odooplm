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
from openerp import _
from openerp import api
from openerp import osv
import logging
_logger = logging.getLogger(__name__)

RETDMESSAGE = ''


class plm_temporary(osv.osv.osv_memory):
    _inherit = "plm.temporary"

    @api.multi
    def action_create_spareBom(self):
        """
            Create a new Spare Bom if doesn't exist (action callable from views)
        """
        if 'active_id' not in self.env.context:
            return False
        if 'active_ids' not in self.env.context:
            return False
        productType = self.env['product.product']
        active_ids = self.env.context.get('active_ids', [])
        for prod_ids in active_ids:
            prodProdObj = productType.browse(prod_ids)
            if not prodProdObj:
                logging.warning('[action_create_spareBom] product_id %s not found' % (prod_ids))
                continue
            objBoms = self.env['mrp.bom'].search([('product_tmpl_id', '=', prodProdObj.product_tmpl_id.id),
                                                  ('type', '=', 'spbom')])
            if objBoms:
                raise osv.osv.except_osv(_('Creating a new Spare Bom Error.'), _("BoM for Part %r already exists." % (prodProdObj.name)))

        productType.browse(active_ids).action_create_spareBom_WF()
        return {'name': _('Bill of Materials'),
                'view_type': 'form',
                "view_mode": 'tree,form',
                'res_model': 'mrp.bom',
                'type': 'ir.actions.act_window',
                'domain': "[('product_id','in', [" + ','.join(map(str, active_ids)) + "])]",
                }

plm_temporary()
