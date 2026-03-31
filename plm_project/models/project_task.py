# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Created on Nov 16, 2019

@author: mboscolo
"""
import json
from odoo import _, fields, models, api


def _json_param(env, key, default):
    val = env['ir.config_parameter'].sudo().get_param(key)
    if not val:
        return default
    try:
        return json.loads(val)
    except Exception:
        return default


def _default_chain(env):
    chain = _json_param(env, 'plm_project.workflow_chain',
                        ["draft", "3dc", "2d", "confirmed", "released"])
    labels = _json_param(env, 'plm_project.workflow_labels', {
        "draft": "Draft",
        "3dc": "3D Confirmed",
        "2d": "2D",
        "confirmed": "Confirmed",
        "released": "Released",
    })
    methods = _json_param(env, 'plm_project.workflow_methods', {})
    return chain, labels, methods


class ProjectTask(models.Model):
    _inherit = "project.task"

    activity_product_ids = fields.One2many(
        "product.product", "activity_task_id", string="Activite Products"
    )
    plm_step_key = fields.Selection(
        selection=lambda self: [(k, v) for k, v in _default_chain(self.env)[1].items()],
        string='PLM Step',
        index=True,
        copy=False,
        default='draft',
    )
    plm_subtasks_generated = fields.Boolean(default=False, copy=False)

    plm_product_ids = fields.Many2many(
        "product.product",
        "project_task_rel",
        "task_id",
        "product_id",
        string="Task Products",
    )
    
    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _plm_chain(self):
        return _default_chain(self.env)[0]

    def _plm_labels(self):
        return _default_chain(self.env)[1]

    def _plm_methods(self):
        return _default_chain(self.env)[2]

    def _plm_get_product(self):
        self.ensure_one()
        if hasattr(self, 'plm_product_id') and self.plm_product_id:
            return self.plm_product_id
        if hasattr(self, 'product_id') and self.product_id:
            return self.product_id
        if hasattr(self, 'product_tmpl_id') and self.product_tmpl_id:
            return self.product_tmpl_id.product_variant_id
        return self.env['product.product']

    def _plm_get_product_template(self):
        prod = self._plm_get_product()
        if prod and prod._name == 'product.product':
            return prod.product_tmpl_id
        return prod if prod._name == 'product.template' else self.env['product.template']

    def _next_step_after(self, step):
        chain = self._plm_chain()
        if step not in chain:
            return False
        idx = chain.index(step)
        return chain[idx + 1] if idx + 1 < len(chain) else False

    def _is_stage_done(self, stage):
        return bool(getattr(stage, 'is_closed', False) or getattr(stage, 'fold', False))

    def _push_product_state(self, product_tmpl, current_step, next_step):
        if not product_tmpl or not next_step:
            return
        try:
            mm = self._plm_methods()
            key = f"{current_step}->{next_step}"
            meth = mm.get(key) if isinstance(mm, dict) else None
            if meth and hasattr(product_tmpl, meth):
                getattr(product_tmpl.sudo().with_context(from_task=True), meth)()
                return

            # Explicit fallbacks
            if (current_step in (None, 'SD')) and next_step == 'draft':
                if hasattr(product_tmpl, 'action_from_SD_to_draft'):
                    product_tmpl.sudo().action_from_SD_to_draft()
                else:
                    product_tmpl.sudo().write({'engineering_state': 'draft'})
                return
            if current_step == 'draft' and next_step == '3dc' and hasattr(product_tmpl, 'action_from_draft_to_3dc'):
                product_tmpl.sudo().action_from_draft_to_3dc()
                return
            if current_step == '3dc' and next_step == '2d' and hasattr(product_tmpl, 'action_from_3dc_to_2d'):
                product_tmpl.sudo().action_from_3dc_to_2d()
                return
            if current_step == '2d' and next_step == 'confirmed' and hasattr(product_tmpl, 'action_from_2d_to_confirmed'):
                product_tmpl.sudo().action_from_2d_to_confirmed()
                return
            if current_step == 'confirmed' and next_step == 'released':
                product_tmpl.sudo().write({'engineering_state': 'released'})
                return

            product_tmpl.sudo().write({'engineering_state': next_step})
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Subtask Generation – Exact Workflow as Requested
    # ------------------------------------------------------------------
    def action_generate_plm_subtasks(self):
        labels = self._plm_labels()

        WORKFLOW_MAP = {
            'draft':     ['3dc', '2d', 'confirmed', 'released'],
            '3dc':       ['2d', 'confirmed', 'released'],
            '2d':        ['confirmed', 'released'],
            'confirmed': ['released'],
            'released':  [],
        }

        def _norm(key):
            s = (key or '').strip().lower()
            s = s.replace('-', ' ').replace('/', ' ')
            s = ' '.join(s.split())
            if s in ('sd', 'sale draft', 'sale_draft'):
                return 'draft'
            if s in ('3d', '3d confirmed', '3d_confirmed', '3dconfirmed'):
                return '3dc'
            return s

        for task in self:
            if task.parent_id:  # Only main tasks generate subtasks
                continue

            current = _norm(task.plm_step_key or 'draft')
            target_steps = [_norm(s) for s in WORKFLOW_MAP.get(current, [])]
            target_steps = [s for s in target_steps if s != current]

            if not target_steps:
                task.plm_subtasks_generated = True
                continue

            existing = { _norm(c.plm_step_key) for c in task.child_ids if c.plm_step_key }

            for nxt in target_steps:
                if nxt in existing:
                    continue

                child_vals = {
                    'name': labels.get(nxt, nxt.replace('_', ' ').title()),
                    'project_id': task.project_id.id,
                    'parent_id': task.id,
                    'plm_step_key': nxt,
                    'description': _("Auto-created PLM subtask (%s)") % labels.get(nxt, nxt),
                }
                child = self.env['project.task'].create(child_vals)

                # Link product to subtask
                prod = task._plm_get_product()
                if prod:
                    if hasattr(child, 'plm_product_id'):
                        child.plm_product_id = prod if prod._name == 'product.product' else prod.product_variant_id
                    elif hasattr(child, 'product_id'):
                        child.product_id = prod if prod._name == 'product.product' else prod.product_variant_id
                    elif hasattr(child, 'product_tmpl_id'):
                        child.product_tmpl_id = prod.product_tmpl_id if prod._name == 'product.product' else prod

            task.plm_subtasks_generated = True
        return True

    # ------------------------------------------------------------------
    # When subtask is closed → advance parent
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals:
            for rec in self:
                if (rec.parent_id and rec.stage_id and
                        self._is_stage_done(rec.stage_id) and rec.plm_step_key):

                    parent = rec.parent_id
                    prev_key = parent.plm_step_key
                    next_key = parent._next_step_after(rec.plm_step_key)

                    if next_key:
                        parent.sudo().write({
                            'plm_step_key': next_key,
                            'plm_subtasks_generated': False
                        })

                        tmpl = parent._plm_get_product_template()
                        if tmpl:
                            parent._push_product_state(tmpl, prev_key, next_key)

                        parent.action_generate_plm_subtasks()
        return res

    # ------------------------------------------------------------------
    # On create: align step with product + generate subtasks
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        chain = self._plm_chain()

        for rec in records:
            if not rec.plm_step_key:
                tmpl = rec._plm_get_product_template()
                if tmpl and getattr(tmpl, 'engineering_state', False):
                    start = tmpl.engineering_state
                    if start == 'SD':
                        try:
                            if hasattr(tmpl, 'action_from_SD_to_draft'):
                                tmpl.sudo().action_from_SD_to_draft()
                            else:
                                tmpl.sudo().write({'engineering_state': 'draft'})
                        except Exception:
                            pass
                        start = 'draft'
                    if start in chain:
                        rec.sudo().write({'plm_step_key': start})

            if not rec.plm_subtasks_generated:
                rec.action_generate_plm_subtasks()

        return records
