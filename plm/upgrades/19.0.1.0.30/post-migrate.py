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
"""Make the PLM sequences global, and give every company its PLM documents.

ir.sequence.company_id defaults to env.company, so the sequences of
data/sequence.xml were bound to the company the module was installed in, and
next_by_code returned False in every other company. The XML now declares them
with company_id False, but those records are noupdate: this brings the
databases installed before in line. It touches only the sequences created by
the module, not the ones made by hand, and it runs once: a company an
administrator sets on them after the upgrade is not undone by the next one.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

MODULE = "plm"
SEQUENCE_XMLIDS = (
    "seq_plm_finishing",
    "seq_plm_description",
    "seq_plm_treatment",
    "seq_plm_material",
    "sequence_document",
    "sequence_plm_dbthread",
)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_sequence
           SET company_id = NULL
          FROM ir_model_data
         WHERE ir_model_data.model = 'ir.sequence'
           AND ir_model_data.res_id = ir_sequence.id
           AND ir_model_data.module = %s
           AND ir_model_data.name IN %s
           AND ir_sequence.company_id IS NOT NULL
        """,
        (MODULE, SEQUENCE_XMLIDS),
    )
    _logger.info("%s: %s sequences made global", MODULE, cr.rowcount)
    # product.template.getSequenceFrom creates PLM_SEQUENCE_<prefix> on the fly,
    # with no xmlid, and got env.company as well until it passed company_id.
    cr.execute(
        """
        UPDATE ir_sequence
           SET company_id = NULL
         WHERE code LIKE %s
           AND company_id IS NOT NULL
        """,
        ("PLM\\_SEQUENCE\\_%",),
    )
    _logger.info("%s: %s PLM_SEQUENCE_ sequences made global", MODULE, cr.rowcount)
    _attach_documents_to_company_roots(cr)


def _attach_documents_to_company_roots(cr):
    """Every PLM document was attached to plm_basic_access_model, one node for
    the whole database, so every user saw every company's documents. The data
    of the module has by now made that node the root of the main company and
    given every other company its own root: each document moves to the root of
    its company, and one with no company goes to the main company."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    basic = env.ref("plm.plm_basic_access_model")
    main_company = env.ref("base.main_company")
    # A PLM document attached to nothing, made by a module converting files for
    # instance, was visible to its creator only: it joins the basic node too,
    # as 18.0.8.0.1 did for the ones before it, and then its company's root.
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
