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
Created on 30 Aug 2016

@author: Daniel Smerghetto
"""
from odoo import fields, models, _
from datetime import datetime


class ProductExtension(models.Model):
    _inherit = 'product.product'

    project_ids = fields.Many2many(
        'project.project',
        'project_product_rel',
        'product_id',
        'project_id',
        string=_('Projects')
    )
    activity_task_id = fields.Many2one('project.task', _('Task'))

    def createConfirmActivity(self):
        for comp_obj in self:
            ref_user = self.env['res.users']
            if comp_obj.activity_task_id:
                ref_user = comp_obj.activity_task_id.project_id.user_id
            if not ref_user and comp_obj.project_ids:
                for project in comp_obj.project_ids:
                    ref_user += project.user_id
            ref_user.union()
            if ref_user:
                mail_activity = self.env['mail.activity']
                mail_activity.create({
                    'res_model_id': self.env['ir.model'].search([('model', '=', self._name)]).id,
                    'res_id': comp_obj.id,
                    'recommended_activity_type_id': False,
                    'activity_type_id': self.env.ref('plm_project.mail_activity_product_confirmed').id,
                    'summary': 'Product %r confirmed' % (comp_obj.display_name),
                    'date_deadline': str(datetime.now().date()),
                    'user_id': ref_user.id,
                    'note': '<div>Confirmed product: %s</div>' % (comp_obj.display_name)})

    def action_confirm(self):
        for comp_obj in self:
            if not self.env.context.get('activity_created', False):
                comp_obj.createConfirmActivity()
            super(ProductExtension, comp_obj.with_context(activity_created=True)).action_confirm()
        return True

    def action_release(self):
        for product in self:
            self.env['mail.activity'].search([
                ('activity_type_id', '=', self.env.ref('plm_project.mail_activity_product_confirmed').id),
                ('res_id', '=', product.id),
                ('res_model_id', '=', self.env['ir.model'].search([('model', '=', self._name)]).id),
                ]).action_done()
        return super(ProductExtension, self).action_release()
