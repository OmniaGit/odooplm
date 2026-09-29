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
import base64
import io
import os
import tempfile
import zipfile

from odoo.tests import TransactionCase, tagged

try:
    import cadquery as cq
except ImportError:
    cq = None

#
# --test-tags=odoo_plm_web_3d_step
#


def _empty_3mf():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("3D/3dmodel.model",
                    '<?xml version="1.0" encoding="UTF-8"?><model><resources/>'
                    '<build/></model>')
    return buffer.getvalue()


@tagged("-standard", "odoo_plm_web_3d_step", "post_install", "-at_install")
class TestStepTo3mf(TransactionCase):
    """The 3D viewer of a STEP file does not keep showing an empty 3MF left by
    an older conversion (issue #109)."""

    def setUp(self):
        super().setUp()
        Attachment = self.env["ir.attachment"]
        if cq is None:
            self.skipTest("cadquery is not installed")
        if "source_convert_document" not in Attachment._fields:
            self.skipTest("plm_automated_convertion is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            step = os.path.join(tmp, "part.step")
            cq.exporters.export(cq.Workplane().box(10, 20, 30), step)
            with open(step, "rb") as fh:
                data = base64.b64encode(fh.read())
        self.step = Attachment.create({"name": "WEB3D-STEP.step", "datas": data})

    def test_single_part_step_gives_objects(self):
        converted = self.step._get_or_create_3mf_from_step()
        self.assertTrue(converted._3mf_has_objects(converted.raw))
        # Reused as it is the next time
        self.assertEqual(self.step._get_or_create_3mf_from_step(), converted)

    def test_empty_conversion_is_redone(self):
        stale = self.env["ir.attachment"].create({
            "name": "WEB3D-STEP.3mf",
            "raw": _empty_3mf(),
            "is_converted_document": True,
            "source_convert_document": self.step.id,
        })
        self.assertFalse(stale._3mf_has_objects(stale.raw))
        converted = self.step._get_or_create_3mf_from_step()
        self.assertEqual(converted, stale)
        self.assertTrue(converted._3mf_has_objects(converted.raw))
