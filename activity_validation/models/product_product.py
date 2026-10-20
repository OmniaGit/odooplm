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
import json
import logging
from lxml import etree
from odoo.tools.safe_eval import safe_eval
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('activity_ids.plm_state')
    def _compute_opened_activities(self):
        for product in self:
            product.opened_activities = False
            for activity in product.activity_ids:
                if activity.plm_state != 'finished':
                    product.opened_activities = True
                    break

    opened_activities = fields.Boolean(compute='_compute_opened_activities', store=True)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        from_activity = self.env.context.get('from_activity_counter', False)
        if from_activity == 1:
            domain.append(('opened_activities', '=', True))
        return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit,
                                                       order=order)

    @api.model
    def get_user_activities(self, ids_to_read=[]):
        activity = self.env['mail.activity']
        act_filter = [
            ('activity_type_id', 'in', [self.env.ref('plm.mail_activity_plm_activity').id,
                                        self.env.ref('plm.mail_activity_check_out_request').id]),
            ('user_id', '=', self.env.uid),
            ('plm_state', 'not in', [False, 'done', 'cancel'])
        ]
        if ids_to_read:
            act_filter.append(('id', 'in', ids_to_read))
        activities = activity.search(act_filter)
        out = []
        headers_mapping = [
            {'name': 'Name', 'key': 'res_name', 'readonly': True, 'type': 'CHAR'},
            {'name': 'Title', 'key': 'summary', 'readonly': True, 'type': 'CHAR'},
            {'name': 'Note', 'key': 'note', 'readonly': True, 'type': 'HTML'},
            {'name': 'Date', 'key': 'date_deadline', 'readonly': True, 'type': 'CHAR'},
            {'name': 'User', 'key': 'user_id', 'readonly': True, 'type': 'CHAR'},
            {'name': 'State', 'key': 'plm_state', 'readonly': True, 'type': 'CHAR'},
            {'name': 'Project', 'key': 'project_id', 'readonly': True, 'type': 'CHAR'},
            {'name': 'Task', 'key': 'task_id', 'readonly': True, 'type': 'CHAR'},
            {'name': 'Progress', 'key': 'action_in_progress', 'readonly': False, 'type': 'BUTTON',
             'callback': 'activitiesCallback'},
            {'name': 'Draft', 'key': 'action_to_draft', 'readonly': False, 'type': 'BUTTON',
             'callback': 'activitiesCallback'},
            {'name': 'Exception', 'key': 'action_to_exception', 'readonly': False, 'type': 'BUTTON',
             'callback': 'activitiesCallback'},
            {'name': 'Cancel', 'key': 'action_to_cancel', 'readonly': False, 'type': 'BUTTON',
             'callback': 'activitiesCallback'},
            {'name': 'Done', 'key': 'action_to_done', 'readonly': False, 'type': 'BUTTON',
             'callback': 'activitiesCallback'},
        ]
        to_read = [x['key'] for x in headers_mapping]
        if not to_read:
            to_read = ['res_name', 'summary', 'date_deadline', 'user_id']
        fields_def = activity.fields_get(to_read)
        buttons = self._get_state_buttons(
            [x['key'] for x in headers_mapping if x.get('type') == 'BUTTON'])
        for read_dict in activities.read():
            tmp_read = {'id': read_dict.get('id')}
            self._set_buttons_readonly(read_dict, buttons)
            for fieldName in to_read:
                try:
                    tmp_read[fieldName] = read_dict.get(fieldName, '')
                    field_type = fields_def.get(fieldName, {}).get('type', '')
                    if field_type in ['date', 'datetime']:
                        tmp_read[fieldName] = str(tmp_read[fieldName])
                    elif field_type in ['many2one']:
                        val = ''
                        if tmp_read[fieldName]:
                            val = tmp_read[fieldName][1]
                        tmp_read[fieldName] = val
                except Exception as ex:
                    logging.error(ex)
                    tmp_read[fieldName] = ''
            out.append(tmp_read)
        return json.dumps([headers_mapping, out])

    @api.model
    def _get_state_buttons(self, button_names):
        """
        {button name: [its invisible expressions]} of the state buttons of the
        activity form: the form decides which state changes an activity allows,
        the client asks the same through get_user_activities. A name can appear
        more than once (Progress), with one condition each
        """
        form_view = self.env.ref('mail.mail_activity_view_form_popup')
        arch = self.env['mail.activity'].get_views([(form_view.id, 'form')])['views']['form']['arch']
        buttons = {}
        for button in etree.fromstring(arch).iter('button'):
            name = button.get('name')
            if name in button_names:
                buttons.setdefault(name, []).append(button.get('invisible') or 'False')
        return buttons

    @api.model
    def _set_buttons_readonly(self, read_dict, buttons):
        """
        read_dict[button name] = True when the button is hidden in the form for
        this activity, that is when every one of its conditions hides it
        """
        for name, expressions in buttons.items():
            readonly = True
            for expression in expressions:
                try:
                    if not safe_eval(expression, dict(read_dict)):
                        readonly = False
                        break
                except Exception as ex:
                    logging.error('Cannot evaluate %r of button %r: %r' % (expression, name, ex))
            read_dict[name] = readonly
        return True
