# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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


import openerp.tools as tools
import logging
from openerp import models
from openerp import fields
from openerp import api
from openerp import _
_logger = logging.getLogger(__name__)


class report_plm_document_file(models.Model):
    _name = "report.plm_document.file"
    _description = "Files details by Directory"
    _auto = False

    file_size = fields.Integer(_('File Size'),
                               readonly=True)
    nbr = fields.Integer(_('# of Files'),
                         readonly=True)
    month = fields.Char(_('Month'),
                        size=24,
                        readonly=True)

    _order = "month"

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_plm_document_file')
        cr.execute("""
            create or replace view report_plm_document_file as (
                select min(f.id) as id,
                       count(*) as nbr,
                       min(EXTRACT(MONTH FROM f.create_date)||'-'||to_char(f.create_date,'Month')) as month,
                       sum(f.file_size) as file_size
                from plm_document f
                group by EXTRACT(MONTH FROM f.create_date)
             )
        """)

report_plm_document_file()


class report_plm_document_user(models.Model):
    _name = "report.plm_document.user"
    _description = "Files details by Users"
    _auto = False

    name            =   fields.Char(_('Year'), size=64,readonly=True)
    month           =   fields.Selection([('01',_('January')), ('02',_('February')), ('03',_('March')), ('04',_('April')), ('05',_('May')), ('06',_('June')),
                                  ('07',_('July')), ('08',_('August')), ('09',_('September')), ('10',_('October')), ('11',_('November')), ('12',_('December'))],_('Month'),readonly=True, transalte=True)
    day             =   fields.Char(_('Day'), size=64,readonly=True)
    user_id         =   fields.Integer(_('Owner'), readonly=True)
    user            =   fields.Char(_('User'),size=64,readonly=True)
    directory       =   fields.Char(_('Directory'),size=64,readonly=True)
    datas_fname     =   fields.Char(_('File'),size=64,readonly=True)
    create_date     =   fields.Datetime(_('Date Created'), readonly=True)
    change_date     =   fields.Datetime(_('Modified Date'), readonly=True)
    file_size       =   fields.Integer(_('File Size'), readonly=True)
    nbr             =   fields.Integer(_('# of Files'), readonly=True)
    type            =   fields.Char(_('Directory Type'),size=64,readonly=True)

#     def init(self, cr):
#         pass
#         tools.drop_view_if_exists(cr, 'report_plm_document_user')
#         cr.execute("""
#             CREATE OR REPLACE VIEW report_plm_document_user as (
#                  SELECT
#                      min(f.id) as id,
#                      to_char(f.create_date, 'YYYY') as name,
#                      to_char(f.create_date, 'MM') as month,
#                      to_char(f.create_date, 'DD') as day,
#                      f.user_id as user_id,
#                      u.login as user,
#                      count(*) as nbr,
#                      d.name as directory,
#                      f.datas_fname as datas_fname,
#                      f.create_date as create_date,
#                      f.file_size as file_size,
#                      min(d.type) as type,
#                      f.write_date as change_date
#                  FROM plm_document f
#                      left join document_directory d on (f.parent_id=d.id and d.name<>'' and f.type='binary')
#                      inner join res_users u on (f.user_id=u.id)
#                  group by to_char(f.create_date, 'YYYY'), to_char(f.create_date, 'MM'),to_char(f.create_date, 'DD'),d.name,f.parent_id,d.type,f.create_date,f.user_id,f.file_size,u.login,d.type,f.write_date,f.datas_fname
#              )
#         """)
report_plm_document_user()



class report_plm_files_partner(models.Model):
    _name = "report.plm_files.partner"
    _description = "Files details by Partners"
    _auto = False

    name        =   fields.Char(_('Year'),size=64,required=False, readonly=True)
    file_size   =   fields.Integer(_('File Size'), readonly=True)
    nbr         =   fields.Integer(_('# of Files'), readonly=True)
    partner     =   fields.Char(_('Partner'),size=64,readonly=True)
    month       =   fields.Selection([('01',_('January')), ('02',_('February')), ('03',_('March')), ('04',_('April')), ('05',_('May')), ('06',_('June')),
                                  ('07',_('July')), ('08',_('August')), ('09',_('September')), ('10',_('October')), ('11',_('November')), ('12',_('December'))],_('Month'),readonly=True, translate=True)

#     def init(self, cr):
#         tools.drop_view_if_exists(cr, 'report_plm_files_partner')
#         cr.execute("""
#             CREATE VIEW report_plm_files_partner as (
#                 SELECT min(f.id) AS id,
#                        COUNT(*) AS nbr,
#                        to_char(date_trunc('month', f.create_date),'YYYY') AS name,
#                        to_char(date_trunc('month', f.create_date),'MM') AS month,
#                        SUM(f.file_size) AS file_size,
#                        p.name AS partner
# 
#                 FROM plm_document f
#                   LEFT JOIN res_partner p ON (f.partner_id=p.id)
#                 WHERE f.datas_fname IS NOT NULL
#                 GROUP BY p.name, date_trunc('month', f.create_date)
#              )
#          """)
report_plm_files_partner()



class report_plm_document_wall(models.Model):
    _name = "report.plm_document.wall"
    _description = "Users that did not inserted documents since one month"
    _auto = False

    name        =   fields.Date(_('Month'), readonly=True)
    user_id     =   fields.Many2one('res.users', _('Owner'),readonly=True)
    user        =   fields.Char(_('User'),size=64,readonly=True)
    month       =   fields.Char(_('Month'), size=24,readonly=True)
    last        =   fields.Datetime(_('Last Posted Time'), readonly=True)


#     def init(self, cr):
#         tools.drop_view_if_exists(cr, 'report_document_wall')
#         cr.execute("""
#             create or replace view report_document_wall as (
#                select max(f.id) as id,
#                to_char(min(f.create_date),'YYYY-MM-DD HH24:MI:SS') as last,
#                f.user_id as user_id, f.user_id as user,
#                to_char(f.create_date,'Month') as month
#                from plm_document f
#                where f.create_date in (
#                    select max(i.create_date)
#                    from ir_attachment i
#                    inner join res_users u on (i.user_id=u.id)
#                    group by i.user_id) group by f.user_id,f.create_date
#                    having (CURRENT_DATE - to_date(to_char(f.create_date,'YYYY-MM-DD'),'YYYY-MM-DD')) > 30
#              )
#         """)
report_plm_document_wall()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

