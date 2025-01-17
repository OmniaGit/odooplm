# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
from odoo import models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def action_open_workorder_kanban(self):
        view_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "plm.document_kanban_view"
        )
        ctx = self.env.context.copy()
        domain = [('is_plm', '=', True),
                  ('is_production_doc', '=', True),
                  ('id', 'in', self.production_doc_ids.ids)]
        ctx.update({
            "create": False,
            "delete": False,
            'default_res_ids': self.production_doc_ids.ids,
            'readonly': True
        })

        return {
            "type": "ir.actions.act_window",
            "view_type": "kanban",
            "view_mode": "kanban",
            'domain': domain,
            "res_model": "ir.attachment",
            "target": "new",
            "views": [[view_id, "kanban"]],
            "context": ctx,
        }
