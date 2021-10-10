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
from odoo import _
from odoo import api
from odoo import models
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class PlmTemporary(models.TransientModel):
    _inherit = "plm.temporary"

    def action_create_spare_bom(self):
        """
            Create a new Spare Bom if doesn't exist (action callable from views)
        """
        if 'active_id' not in self.env.context:
            return False
        if 'active_ids' not in self.env.context:
            return False
        product_type = self.env['product.product']
        active_ids = self.env.context.get('active_ids', [])
        for prod_ids in active_ids:
            prod_prod_obj = product_type.browse(prod_ids)
            if not prod_prod_obj:
                logging.warning('[action_create_spareBom] product_id {} not found'.format(prod_ids))
                continue
            obj_boms = self.env['mrp.bom'].search([('product_tmpl_id', '=', prod_prod_obj.product_tmpl_id.id),
                                                   ('type', '=', 'spbom')])
            if obj_boms:
                raise UserError(_('Creating a new Spare Bom Error.'),
                                         _("BoM for Part {} already exists.".format(prod_prod_obj.name))
                                         )

        product_type.browse(active_ids).action_create_spare_bom_wf()
        return {'name': _('Bill of Materials'),
                'view_type': 'form',
                "view_mode": 'tree,form',
                'res_model': 'mrp.bom',
                'type': 'ir.actions.act_window',
                'domain': "[('product_id','in', [" + ','.join(map(str, active_ids)) + "])]",
                }
