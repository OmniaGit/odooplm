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
"""The new columns of the PLM access tree, filled in SQL.

plm.access gets a company, and every node must have one: the nodes already
there, plm_basic_access_model first, belong to the main company until the data
of the module and the post-migrate script give each company its own root. This
has to happen before the ORM sets the models up, because the constraint on the
node is checked while the module loads, well before data.xml runs.

ir_attachment.plm_access_id is a new stored field computed from res_model and
res_id: its column is created and filled here, so that the update does not
recompute it in Python for every attachment of the database.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("ALTER TABLE plm_access ADD COLUMN IF NOT EXISTS company_id int4")
    cr.execute(
        """
        UPDATE plm_access
           SET company_id = (SELECT res_id FROM ir_model_data
                              WHERE module = 'base' AND name = 'main_company')
         WHERE company_id IS NULL
        """
    )
    _logger.info("plm: %s PLM access nodes given the main company", cr.rowcount)
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
