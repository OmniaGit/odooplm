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


class report_ir_attachment_file(models.Model):
    _name = "report.ir_attachment.file"
    _description = "Files details by Directory"
    _auto = False

    file_size = fields.Integer(_('File Size'),
                               readonly=True)
    nbr = fields.Integer(_('# of Files'),
                         readonly=True)
    month = fields.Char(_('Month'),
                        size=24,
                        readonly=True)
    write_uid = fields.Integer(_('Write User'),
                               readonly=True)
    _order = "month"

    @api.model
    def init(self):
        cr = self.env.cr
        tools.drop_view_if_exists(cr, 'report_ir_attachment_file')
        cr.execute("""
            create or replace view report_ir_attachment_file as (
                select min(f.id) as id,
                       count(*) as nbr,
                       min(EXTRACT(YEAR FROM f.create_date)||'-'||EXTRACT(MONTH FROM f.create_date)) as month,
                       sum(f.file_size) as file_size,
                       f.write_uid as write_uid
                from ir_attachment f
                group by EXTRACT(MONTH FROM f.create_date), write_uid
             )
        """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
