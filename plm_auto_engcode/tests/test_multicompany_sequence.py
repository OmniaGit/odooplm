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
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

#
# --test-tags=odoo_plm_multicompany
#


@tagged("-standard", "odoo_plm_multicompany")
class PlmAutoEngcodeMultiCompany(TransactionCase):
    """The plm_auto_engcode sequences are global, as every PLM sequence: a company other
    than the one the module was installed in still gets a code."""

    def test_sequences_in_another_company(self):
        company_b = self.env["res.company"].create({"name": "PLM company B"})
        sequence = self.env["ir.sequence"].with_company(company_b)
        for xmlid, code in (("plm_auto_engcode.seq_plm_eng_code", "plm.eng.code"),):
            self.assertFalse(self.env.ref(xmlid).company_id, xmlid)
            self.assertTrue(sequence.next_by_code(code), code)
