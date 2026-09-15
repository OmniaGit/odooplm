# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
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
"""Make the PLM sequences global.

ir.sequence.company_id defaults to env.company, so the sequences of
data/plm_box_sequence_data.xml were bound to the company the module was
installed in, and next_by_code returned False in every other company. The XML
now declares them with company_id False, but those records are noupdate: this
brings the databases installed before in line. It touches only the sequences
created by the module, not the ones made by hand, and it runs once: a company
an administrator sets on them after the upgrade is not undone by the next one.
"""
import logging

_logger = logging.getLogger(__name__)

MODULE = "plm_box"
SEQUENCE_XMLIDS = (
    "seq_plm_box",
    "seq_doc_name",
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
