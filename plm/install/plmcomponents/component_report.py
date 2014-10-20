# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 OmniaSolutions snc (www.omniasolutions.eu).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
import openerp.tools as tools

class report_plm_component(osv.osv):
    _name = "report.plm_component"
    _description = "Report Component"
    _auto = False
            
    _columns = {
        'count_component_draft': fields.integer('Draft', readonly=True),
        'count_component_confirmed': fields.integer('Confirmed', readonly=True),
        'count_component_released': fields.integer('Released', readonly=True),
        'count_component_modified': fields.integer('Under Modify', readonly=True),
        'count_component_obsoleted': fields.integer('Obsoleted', readonly=True),

#         'rate_component_draft': fields.integer('Percent of Parts', readonly=True),
#         'rate_component_released': fields.integer('Percent of Parts', readonly=True),
#         'rate_component_modified': fields.integer('Percent of Parts', readonly=True),
     }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_plm_component')
        cr.execute("""
            CREATE OR REPLACE VIEW report_plm_component AS (
                SELECT
                    (SELECT min(id) FROM product_template) as id,
                    (SELECT count(*) FROM product_template WHERE state = 'draft') AS count_component_draft,
                    (SELECT count(*) FROM product_template WHERE state = 'confirmed') AS count_component_confirmed,
                    (SELECT count(*) FROM product_template WHERE state = 'released') AS count_component_released,
                    (SELECT count(*) FROM product_template WHERE state = 'undermodify') AS count_component_modified,
                    (SELECT count(*) FROM product_template WHERE state = 'obsoleted') AS count_component_obsoleted
             )
        """)
 
#     def _get_status_count(self, cr, uid, ids, field_names, arg, context=None):
#         objType = self.pool.get('product.product')
#         domains = {
#             'count_component_draft': [('state', '=', 'draft')],
#             'count_component_modified': [('state', '=', 'undermodify')],
#             'count_component_released': [('state', '=', 'released')],
#         }
#         result = {}
#         alldata = objType.search(cr, uid, [('state', 'not in', ('false', 'cancel'))])
#         count_all=len(alldata)
#         for field in domains:
#             data = objType.search(cr, uid, domains[field], context=context)
#             result[field] = len(data)
# 
#         for field in domains:
#             if field == 'count_component_draft':
#                 if result['count_component_draft']:
#                     result['rate_component_draft'] = result['count_component_draft'] * 100 / count_all
#                 else:
#                     result['rate_component_draft'] = 0
#             if field == 'count_component_modified':
#                 if result['count_component_modified'] and result['count_component_released']:
#                     result['count_component_released']=result['count_component_released']+result['count_component_modified']
#                 else:
#                     result['count_component_released'] = 0
#             if field == 'count_component_modified':
#                 if result['count_component_modified'] and result['count_component_released']:
#                     result['rate_component_modified'] = result['count_component_modified'] * 100 / result['count_component_released']
#                 else:
#                     result['rate_component_modified'] = 0
# 
#         return result

#     _columns = {
#         'count_component_draft': fields.function(_get_status_count, type='integer', multi='_get_status_count'),
#         'count_component_all': fields.function(_get_status_count, type='integer', multi='_get_status_count'),
#         'count_component_released': fields.function(_get_status_count, type='integer', multi='_get_status_count'),
#         'count_component_modified': fields.function(_get_status_count, type='integer', multi='_get_status_count'),
# 
#         'rate_component_draft': fields.function(_get_status_count, type='integer', multi='_get_status_count'),
#         'rate_component_released': fields.function(_get_status_count, type='integer', multi='_get_status_count'),
#         'rate_component_modified': fields.function(_get_status_count, type='integer', multi='_get_status_count'),
#      }


report_plm_component()
