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
import os
import tempfile
import zipfile

from odoo.tests import BaseCase, tagged

from ..models.ir_attachment import (
    _export_assembly_to_3mf,
    _import_step_preserve_names,
)

try:
    import cadquery as cq
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
except ImportError:
    cq = None

#
# --test-tags=plm_automated_convertion_step
#


def _count_3mf_objects(path):
    with zipfile.ZipFile(path) as zf:
        return zf.read("3D/3dmodel.model").count(b"<object ")


@tagged("-standard", "plm_automated_convertion_step")
class TestStepImport(BaseCase):
    """A STEP file is imported whole, whatever its structure (issue #109: a
    single part STEP gave an empty 3MF)."""

    def setUp(self):
        super().setUp()
        if cq is None:
            self.skipTest("cadquery is not installed")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def _path(self, name):
        return os.path.join(self.tmp, name)

    def _to_3mf(self, step_path):
        assembly = _import_step_preserve_names(step_path)
        out = self._path("out.3mf")
        _export_assembly_to_3mf(assembly, out)
        return assembly, _count_3mf_objects(out)

    def test_single_part(self):
        step = self._path("part.step")
        cq.exporters.export(cq.Workplane().box(10, 20, 30), step)
        assembly, objects = self._to_3mf(step)
        self.assertEqual(objects, 1)
        self.assertIsNotNone(assembly.obj)
        # Nothing to split: the part is not a child of itself
        self.assertFalse(assembly.children)

    def test_assembly(self):
        step = self._path("assembly.step")
        assy = cq.Assembly(name="ASSY")
        assy.add(cq.Workplane().box(10, 10, 10), name="A")
        assy.add(cq.Workplane().sphere(5), name="B", loc=cq.Location((30, 0, 0)))
        assy.export(step)
        assembly, objects = self._to_3mf(step)
        self.assertEqual(objects, 2)
        self.assertEqual(len(assembly.children), 2)

    def test_several_free_shapes(self):
        step = self._path("free.step")
        writer = STEPControl_Writer()
        for solid in (cq.Workplane().box(10, 10, 10),
                      cq.Workplane().sphere(5).translate((30, 0, 0))):
            writer.Transfer(solid.val().wrapped, STEPControl_AsIs)
        writer.Write(step)
        _assembly, objects = self._to_3mf(step)
        self.assertEqual(objects, 2)

    def test_empty_assembly_is_refused(self):
        with self.assertRaises(ValueError):
            _export_assembly_to_3mf(cq.Assembly(name="empty"), self._path("e.3mf"))
