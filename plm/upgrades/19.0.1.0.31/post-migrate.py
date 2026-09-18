# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""Attach the PLM documents that 19.0.1.0.30 left without an access node.

A document attached to nothing carries res_id 0 as often as NULL -- the CAD
client and the routines that convert files write either -- and both that script
and the 18.0.8.0.1 one before it looked for NULL alone. The documents with 0
kept res_model NULL, so they never joined a plm.access node; and read access to
a PLM document is granted through the node it hangs from, so they were outside
the company isolation altogether, readable by any PLM user of any company.

Both conditions are fixed now, which is enough for a database that has not yet
reached 19.0.1.0.30. This script is for the ones that already have: it repeats
the attachment with the condition that catches them.

It is safe to run on a healthy database: with nothing left to attach the first
statement matches no row, and the rest sets the values the documents already
have.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    basic = env.ref("plm.plm_basic_access_model")
    main_company = env.ref("base.main_company")
    cr.execute(
        """
        UPDATE ir_attachment SET res_model = 'plm.access', res_id = %s
         WHERE is_plm AND res_model IS NULL AND coalesce(res_id, 0) = 0
           AND res_field IS NULL
        """,
        (basic.id,),
    )
    left_behind = cr.rowcount
    _logger.info("plm: %s documents attached to nothing given a node", left_behind)
    if not left_behind:
        return
    cr.execute(
        """
        UPDATE ir_attachment SET company_id = %s
         WHERE is_plm AND company_id IS NULL
           AND res_model = 'plm.access' AND res_id = %s
        """,
        (main_company.id, basic.id),
    )
    companies = env["res.company"].with_context(active_test=False).search([])
    for company in companies.filtered("plm_access_id"):
        cr.execute(
            """
            UPDATE ir_attachment
               SET res_id = %(root)s, plm_access_id = %(root)s
             WHERE is_plm AND company_id = %(company)s
               AND res_model = 'plm.access' AND res_id IN (%(basic)s, %(root)s)
               AND plm_access_id IS DISTINCT FROM %(root)s
            """,
            {"root": company.plm_access_id.id, "company": company.id, "basic": basic.id},
        )
        _logger.info(
            "plm: %s documents of %s attached to its PLM access root",
            cr.rowcount,
            company.name,
        )
    env.invalidate_all()
