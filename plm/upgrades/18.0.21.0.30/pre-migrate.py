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
"""An archived record hands its engineering code back.

An archived record used to keep its code, which locked it away: the unique
index counted the archived rows, while the checks in create and write did not,
because search_count skips them. The two disagreed, and a code held only by an
archived record could be given to a new one and then be refused by the index,
with a raw IntegrityError instead of the message that names it.

The code of an archived record now moves to engineering_code_archived, and the
index only looks at the live rows. This does both for the records already
archived, before RevisionBaseMixin.init recreates the index with the new
condition; the old one is dropped here, or the new condition would never be
applied to an index that already exists.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        "ALTER TABLE product_template"
        " ADD COLUMN IF NOT EXISTS engineering_code_archived varchar"
    )
    cr.execute(
        """
        UPDATE product_template
           SET engineering_code_archived = engineering_code,
               engineering_code = NULL
         WHERE NOT active AND engineering_code IS NOT NULL
        """
    )
    _logger.info("plm: %s archived codes handed back", cr.rowcount)
    # product_template is the only table of the mixin with an active field, so
    # it is the only index whose condition changes.
    cr.execute("DROP INDEX IF EXISTS unique_index_product_template")
