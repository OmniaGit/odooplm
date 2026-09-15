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
"""One rule for engineering codes: a set code is unique per revision.

'' and '-' once stood for "no code", to skip the checks while cloning and
revising; they become NULL, as the models now store them.

The unique index of ir_attachment was declared with
``engineering_code IS NOT NULL OR engineering_code NOT IN ('-','')``, which is
the same as ``IS NOT NULL`` but reads as something else; it is dropped here and
RevisionBaseMixin.init recreates it with the plain condition, on product_template
too, which never had it.

ir_attachment.plm_access_id is a new stored field computed from res_model and
res_id: its column is created and filled here, so that the update does not
recompute it in Python for every attachment of the database.

plm.access gets a company, which every node must have: the nodes already there,
plm_basic_access_model first, belong to the main company until the data of the
module and the post-migrate script give each company its own root.
"""
import logging

_logger = logging.getLogger(__name__)

TABLES = ("product_template", "ir_attachment")


def migrate(cr, version):
    for table in TABLES:
        cr.execute(
            "UPDATE {table} SET engineering_code = NULL"
            " WHERE engineering_code IN ('', '-')".format(table=table)
        )
        _logger.info("plm: %s %s placeholder codes cleared", cr.rowcount, table)
        cr.execute("DROP INDEX IF EXISTS unique_index_{table}".format(table=table))
    cr.execute("ALTER TABLE plm_access ADD COLUMN IF NOT EXISTS company_id int4")
    cr.execute(
        """
        UPDATE plm_access
           SET company_id = (SELECT res_id FROM ir_model_data
                              WHERE module = 'base' AND name = 'main_company')
         WHERE company_id IS NULL
        """
    )
    cr.execute("ALTER TABLE ir_attachment ADD COLUMN IF NOT EXISTS plm_access_id int4")
    cr.execute(
        """
        UPDATE ir_attachment
           SET plm_access_id = res_id
         WHERE res_model = 'plm.access'
           AND res_id IN (SELECT id FROM plm_access)
        """
    )
    _logger.info("plm: %s documents attached to their PLM access", cr.rowcount)
