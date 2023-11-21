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
'''
Created on Nov 16, 2019

@author: mboscolo
'''
from odoo import models
from odoo import fields
from odoo import api
import logging
import json
import xml.etree.cElementTree as ElementTree


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
        return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

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
            {'name': 'Name', 'key': 'res_name', 'readonly':True, 'type': 'CHAR'},
            {'name': 'Title', 'key': 'summary', 'readonly':True, 'type': 'CHAR'},
            {'name': 'Note', 'key': 'note', 'readonly':True, 'type': 'HTML'},
            {'name': 'Date', 'key': 'date_deadline', 'readonly':True, 'type': 'CHAR'},
            {'name': 'User', 'key': 'user_id', 'readonly':True, 'type': 'CHAR'},
            {'name': 'State', 'key': 'plm_state', 'readonly':True, 'type': 'CHAR'},
            {'name': 'Project', 'key': 'project_id', 'readonly':True, 'type': 'CHAR'},
            {'name': 'Task', 'key': 'task_id', 'readonly':True, 'type': 'CHAR'},
            {'name': 'Progress', 'key': 'action_in_progress', 'readonly':False, 'type': 'BUTTON', 'callback': 'activitiesCallback'},
            {'name': 'Draft', 'key': 'action_to_draft', 'readonly':False, 'type': 'BUTTON', 'callback': 'activitiesCallback'},
            {'name': 'Exception', 'key': 'action_to_exception', 'readonly':False, 'type': 'BUTTON', 'callback': 'activitiesCallback'},
            {'name': 'Cancel', 'key': 'action_to_cancel', 'readonly':False, 'type': 'BUTTON', 'callback': 'activitiesCallback'},
            {'name': 'Done', 'key': 'action_to_done', 'readonly':False, 'type': 'BUTTON', 'callback': 'activitiesCallback'},
            ]
        to_read = [x['key'] for x in headers_mapping]
        if not to_read:
            to_read = ['res_name', 'summary', 'date_deadline', 'user_id']
        fields_def = activity.fields_get(to_read)
        form_view = self.env.ref('mail.mail_activity_view_form_popup')
        activity_view = self.fields_view_get(form_view.id)['arch']
        buttons = self.getButtons(activity_view)
        for read_dict in activities.read():
            tmp_read = {'id': read_dict.get('id')}
            self.parseViewForButtons(headers_mapping, read_dict, buttons)
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

    def getButtons(self, activity_view_arch):
        buttons = {}
        elementObj = ElementTree.XML(activity_view_arch.encode('utf-8'))
        for sheet in elementObj.findall('sheet'):
            for elem in list(sheet):
                if elem.attrib.get('name', '') == 'plm_state_buttons':
                    for button in list(elem):
                        modifiers = button.attrib.get('modifiers', '')
                        butt_name = button.attrib.get('name', '')
                        try:
                            modifiers = eval(modifiers)
                            buttons[butt_name] = modifiers.get('invisible', modifiers.get('readonly', []))
                        except Exception as ex:
                            pass
                    break
        return buttons
        
    def parseViewForButtons(self, headers_mapping, read_dict, buttons):
        for map_dict in headers_mapping:
            if map_dict.get('type', 'CHAR') == 'BUTTON':
                key = map_dict.get('key', '')
                modifiers = buttons.get(key, [])
                if modifiers:
                    try:
                        read_dict[key] = evaluateAttrs(read_dict, modifiers)
                    except Exception as ex:
                        logging.error(ex)
        return True

def evaluateAttrs(fieldsDict, toCompute):
    def evalSingleCondition(cond):
        if len(cond) != 3:
            logging.warning('Condition lenght != 3: %r' % (str(cond)), 'evalSingleCondition')
            return False
        fieldName, operator, valToCompare = cond
        fieldVal = fieldsDict.get(fieldName, None)
        if operator == '=':
            return fieldVal == valToCompare
        elif operator == '!=':
            return fieldVal != valToCompare
        elif operator == '>':
            return fieldVal > valToCompare
        elif operator == '<':
            return fieldVal < valToCompare
        elif operator == '>=':
            return fieldVal >= valToCompare
        elif operator == '<=':
            return fieldVal <= valToCompare
        elif operator == 'in':
            if not isinstance(valToCompare, (list, tuple)):
                logging.warning('valToCompare: %r is not a list for operator: %r' % (valToCompare, operator), 'evalSingleCondition')
                return False
            return fieldVal in valToCompare
        elif operator == 'not in':
            if not isinstance(valToCompare, (list, tuple)):
                logging.warning('valToCompare: %r is not a list for operator: %r' % (valToCompare, operator), 'evalSingleCondition')
                return False
            return fieldVal not in valToCompare
        elif operator == 'like':
            if not isinstance(valToCompare, (str, str)):
                logging.warning('valToCompare: %r is not a char for operator: %r' % (valToCompare, operator), 'evalSingleCondition')
                return False
            return fieldVal in valToCompare
        elif operator == 'ilike':
            if not isinstance(valToCompare, (str, str)):
                logging.warning('valToCompare: %r is not a char for operator: %r' % (valToCompare, operator), 'evalSingleCondition')
                return False
            return fieldVal.lower() in valToCompare.lower()

    if isinstance(toCompute, bool):
        return toCompute
    if len(toCompute) == 1:
        return evalSingleCondition(toCompute[0])

    conditions = []
    operators = []
    for singleCompute in toCompute:
        if isinstance(singleCompute, (str, str)):
            if singleCompute == '|':
                operators.append(singleCompute)
                continue
            elif singleCompute == '&':
                operators.append(singleCompute)
                continue
            else:
                logging.warning('Operator %r not implemented' % (singleCompute), 'evaluateAttrs')
        if not operators:
            operators.append('&')
        res = evalSingleCondition(singleCompute)
        conditions.append(res)

    return _evalSimple(conditions, operators)


def _evalSimple(conditions, operators):
    if len(operators) != len(conditions) - 1:
        logging.warning("Cannot eval with conditions: %s and operators: %s" % (str(conditions), str(operators)), "_evalSimple")
        for _elem in range(len(conditions) -1 - len(operators)):
            operators.append('&')
    count = 0
    lastCond = False
    for cond in conditions:
        if count == 0:
            lastCond = cond
        else:
            oper = operators[count - 1]
            if oper == '&':
                lastCond = lastCond and cond
            elif oper == '|':
                lastCond = lastCond or cond
        count = count + 1
    return lastCond