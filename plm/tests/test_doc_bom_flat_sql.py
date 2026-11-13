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

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_doc_bom_flat
#
SUPPORT_LINK_KINDS = ("ExtraTree", "PkgTree", "Web3DTree")


@tagged("-standard", "odoo_plm", "odoo_plm_doc_bom_flat")
class PlmDocBomFlatSql(TransactionCase, PlmEntityCreator):
    """getDocBomFlatSql (the structure /plm/download_structure sends to the
    CAD client) holds the documents of the structure only: the support files
    of a document (derived DWG, STEP, DXF, zip, 3D web file) stay out."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        creator = PlmEntityCreator()
        creator.env = cls.env
        cls.assembly = creator.create_document("FLAT-ASM.iam", doc_type="3d")
        cls.part = creator.create_document("FLAT-PART.ipt", doc_type="3d")
        cls.reference = creator.create_document("FLAT-REF.ipt", doc_type="3d")
        cls.drawing = creator.create_document("FLAT-ASM.idw", doc_type="2d")
        creator.create_link_document(cls.assembly, cls.part, "HiTree")
        creator.create_link_document(cls.assembly, cls.reference, "RfTree")
        creator.create_link_document(cls.drawing, cls.assembly, "LyTree")
        cls.support = cls.env["ir.attachment"]
        for document in (cls.assembly, cls.part, cls.drawing):
            for link_kind in SUPPORT_LINK_KINDS:
                support = creator.create_document("%s_%s.bin" % (document.name, link_kind))
                creator.create_link_document(document, support, link_kind)
                cls.support |= support
            # a flat pattern DXF or a DWG is a 2D document
            dxf = creator.create_document("%s_dxf.dxf" % document.name, doc_type="2d")
            creator.create_link_document(document, dxf, "ExtraTree")
            cls.support |= dxf

    def _flat(self, document):
        return {attachment.id for attachment in document.getDocBomFlatSql()}

    def test_assembly_structure_only(self):
        self.assertEqual(self._flat(self.assembly), set((self.assembly | self.part | self.reference).ids))

    def test_part_alone(self):
        self.assertEqual(self._flat(self.part), {self.part.id})

    def test_drawing_with_its_models(self):
        self.assertEqual(
            self._flat(self.drawing),
            set((self.drawing | self.assembly | self.part | self.reference).ids),
        )

    def test_no_support_file(self):
        for document in (self.assembly, self.part, self.drawing):
            self.assertFalse(self._flat(document) & set(self.support.ids), document.name)
