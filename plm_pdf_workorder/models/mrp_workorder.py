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
"""
Created on Mar 30, 2016
@author: Daniel Smerghetto
"""
import base64
from odoo import _, api, fields, models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    use_plm_docs = fields.Boolean(
        related="operation_id.use_plm_docs", string=_("Use PLM Docs")
    )
    production_doc_ids = fields.Many2many("ir.attachment",
                                          compute="_compute_production_doc_ids",
                                          inverse="_set_production_doc_ids",
                                          store=True)

    def _set_production_doc_ids(self):
        for rec in self:
            for doc_id in rec.production_doc_ids:
                attachment_id = rec.product_id.linkeddocuments.filtered(
                    lambda attachment: attachment.id == doc_id.id)
                attachment_id = doc_id

    @api.depends("product_id.linkeddocuments.is_production_doc")
    def _compute_production_doc_ids(self):
        for rec in self:
            if rec.use_plm_docs:
                if rec.product_id.linkeddocuments:
                    rec.production_doc_ids = rec.product_id.linkeddocuments.filtered(
                        lambda doc: doc.is_production_doc == True
                    )
                else:
                    rec.production_doc_ids = False
