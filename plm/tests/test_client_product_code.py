# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
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
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Created on 16 Oct 2026

@author: mboscolo
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

#
# --test-tags=odoo_plm_next_product_code
#


@tagged("-standard", "odoo_plm_next_product_code")
class PlmClientNextProductCode(TransactionCase):
    """plm.client.get_next_product_code: the CAD client's unique product code."""

    def test_the_2019_sequence_by_default(self):
        client = self.env["plm.client"]
        first = client.get_next_product_code()
        second = client.get_next_product_code()
        self.assertTrue(first.startswith("PROD"))
        self.assertEqual(len(first), len("PROD") + 5)
        self.assertNotEqual(first, second)
        sequence = self.env["ir.sequence"].search([("code", "=", "PLM_SEQUENCE_PROD")])
        self.assertEqual(len(sequence), 1)

    def test_its_own_prefix_and_digits(self):
        code = self.env["plm.client"].get_next_product_code("CLT", "3")
        self.assertTrue(code.startswith("CLT"))
        self.assertEqual(len(code), len("CLT") + 3)
