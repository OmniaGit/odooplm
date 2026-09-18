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
"""Give every company its PLM documents.

Every PLM document was attached to plm_basic_access_model, one node for the
whole database, so every user saw every company's documents. The data of the
module has by now made that node the root of the main company and given every
other company its own root: each document moves to the root of its company, and
one with no company goes to the main company.

A document attached to nothing carries res_id 0 as often as NULL -- the CAD
client and the routines that convert files write either -- and the script of
18.0.8.0.1 looked for NULL alone, so part of them never joined a node at all.
Both are taken here.
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
    _logger.info("plm: %s documents attached to nothing given a node", cr.rowcount)
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
            """,
            {"root": company.plm_access_id.id, "company": company.id, "basic": basic.id},
        )
        _logger.info(
            "plm: %s documents of %s attached to its PLM access root",
            cr.rowcount,
            company.name,
        )
    cr.execute(
        """
        SELECT engineering_code FROM ir_attachment
         WHERE is_plm AND engineering_code IS NOT NULL AND plm_access_id IS NOT NULL
      GROUP BY engineering_code
        HAVING count(DISTINCT plm_access_id) > 1
        """
    )
    split = [code for (code,) in cr.fetchall()]
    if split:
        _logger.warning(
            "plm: the revisions of these document codes belong to different "
            "companies, so they now live in different PLM access nodes; move them "
            "to one: %s",
            ", ".join(split),
        )
    env.invalidate_all()
