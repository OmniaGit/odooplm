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
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..models import ir_attachment as ir_attachment_module

#
# --test-tags=plm_automated_convertion_missing_libraries
#


@tagged("-standard", "plm_automated_convertion_missing_libraries")
class TestMissingLibraries(TransactionCase):
    """Without cadquery or to_3mf the module still loads: a feature started
    by the operator refuses with a UserError, an automatic one only logs."""

    def setUp(self):
        super().setUp()
        patcher = patch.multiple(
            ir_attachment_module,
            cq=None,
            _CADQUERY_ERROR="No module named 'typish'",
            stl_to_3mf=None,
            _TO_3MF_ERROR="No module named 'to_3mf'",
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        # Odoo 20 removed datas: the content goes through raw
        self.step = self.env["ir.attachment"].create(
            {"name": "missing_lib.step", "raw": b"ISO-10303-21;\nEND-ISO-10303-21;\n"}
        )
        self.stl = self.env["ir.attachment"].create(
            {"name": "missing_lib.stl", "raw": b"solid x\nendsolid x\n"}
        )

    def _assert_cadquery_refused(self, method, *args, **kwargs):
        with self.assertRaises(UserError) as error:
            method(*args, **kwargs)
        self.assertIn("cadquery", str(error.exception))
        self.assertIn("typish", str(error.exception))

    def test_step_conversion_refused(self):
        self._assert_cadquery_refused(self.step.convert_from_step_to, ".3mf")

    def test_step_split_refused(self):
        self._assert_cadquery_refused(self.step.split_step_assembly)

    def test_step_bom_recovery_refused(self):
        self._assert_cadquery_refused(self.step.recover_bom_from_step)

    def test_refusal_is_translated(self):
        self.env["res.lang"]._activate_lang("it_IT")
        step = self.step.with_context(lang="it_IT")
        with self.assertRaises(UserError) as error:
            step.convert_from_step_to(".3mf")
        self.assertIn("libreria Python cadquery", str(error.exception))

    def test_step_preview_only_logged(self):
        with self.assertLogs(ir_attachment_module._logger, "WARNING"):
            self.assertIsNone(self.step._generate_step_preview_b64())

    def test_stl_to_3mf_refused(self):
        with self.assertRaises(UserError) as error:
            self.stl.convert_from_stl_to(".3mf")
        self.assertIn("to_3mf", str(error.exception))
