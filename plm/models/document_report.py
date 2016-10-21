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


import odoo.tools as tools
import logging
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
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

    @api.model
    def init(self):
        cr = self.env.cr
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

    name = fields.Char(_('Year'), size=64, readonly=True)
    month = fields.Selection([('01', _('January')),
                              ('02', _('February')),
                              ('03', _('March')),
                              ('04', _('April')),
                              ('05', _('May')),
                              ('06', _('June')),
                              ('07', _('July')),
                              ('08', _('August')),
                              ('09', _('September')),
                              ('10', _('October')),
                              ('11', _('November')),
                              ('12', _('December'))],
                             _('Month'),
                             readonly=True,
                             transalte=True)
    day = fields.Char(_('Day'),
                      size=64,
                      readonly=True)
    user_id = fields.Integer(_('Owner'),
                             readonly=True)
    user = fields.Char(_('User'),
                       size=64,
                       readonly=True)
    directory = fields.Char(_('Directory'),
                            size=64,
                            readonly=True)
    datas_fname = fields.Char(_('File'),
                              size=64,
                              readonly=True)
    create_date = fields.Datetime(_('Date Created'),
                                  readonly=True)
    change_date = fields.Datetime(_('Modified Date'),
                                  readonly=True)
    file_size = fields.Integer(_('File Size'),
                               readonly=True)
    nbr = fields.Integer(_('# of Files'),
                         readonly=True)
    type = fields.Char(_('Directory Type'),
                       size=64,
                       readonly=True)

report_plm_document_user()


class report_plm_files_partner(models.Model):
    _name = "report.plm_files.partner"
    _description = "Files details by Partners"
    _auto = False

    name = fields.Char(_('Year'),
                       size=64,
                       required=False,
                       readonly=True)
    file_size = fields.Integer(_('File Size'),
                               readonly=True)
    nbr = fields.Integer(_('# of Files'),
                         readonly=True)
    partner = fields.Char(_('Partner'),
                          size=64,
                          readonly=True)
    month = fields.Selection([('01', _('January')),
                              ('02', _('February')),
                              ('03', _('March')),
                              ('04', _('April')),
                              ('05', _('May')),
                              ('06', _('June')),
                              ('07', _('July')),
                              ('08', _('August')),
                              ('09', _('September')),
                              ('10', _('October')),
                              ('11', _('November')),
                              ('12', _('December'))],
                             _('Month'),
                             readonly=True,
                             translate=True)

report_plm_files_partner()


class report_plm_document_wall(models.Model):
    _name = "report.plm_document.wall"
    _description = "Users that did not inserted documents since one month"
    _auto = False

    name = fields.Date(_('Month'),
                       readonly=True)
    user_id = fields.Many2one('res.users',
                              _('Owner'),
                              readonly=True)
    user = fields.Char(_('User'), size=64,
                       readonly=True)
    month = fields.Char(_('Month'),
                        size=24,
                        readonly=True)
    last = fields.Datetime(_('Last Posted Time'),
                           readonly=True)

report_plm_document_wall()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
