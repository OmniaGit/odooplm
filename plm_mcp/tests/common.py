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
"""A small assembly the tool tests can ask questions about.

Built by hand rather than through the wider helpers of PlmEntityCreator,
because these tests assert on engineering codes and the helpers generate them
from the product name. A test that says "MCPT-ASM-001 has two components" is
readable six months later; one that says "eng_code_PP_product_child_1 has two"
is not.

The shape is the smallest one that still exercises what the tools are for:

    MCPT-ASM-001   assembly, revision 0 and revision 1
    ├── MCPT-PRT-001  x2   steel, with a 3D model and a 2D drawing
    └── MCPT-SUB-001  x1   sub-assembly
        └── MCPT-PRT-002  x3   aluminium, no documents at all

Two revisions of the top assembly are what makes plm_where_used and
plm_compare_bom testable; the missing documents on MCPT-PRT-002 are what makes
plm_documents' "missing" filter testable.
"""
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


class McpCommon(TransactionCase, PlmEntityCreator):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool = cls.env["plm.mcp.tool"]

    def build_assembly(self):
        """The structure above, returned as a dict of its parts."""
        assembly = self.create_product_product("Assembly", "MCPT-ASM-001")
        part = self.create_product_product("Machined part", "MCPT-PRT-001")
        sub = self.create_product_product("Sub assembly", "MCPT-SUB-001")
        child = self.create_product_product("Small part", "MCPT-PRT-002")

        part.product_tmpl_id.engineering_material = "Steel"
        child.product_tmpl_id.engineering_material = "Aluminium"

        self.create_bom(assembly, part, qty=2)
        self.create_bom(assembly, sub, qty=1)
        self.create_bom(sub, child, qty=3)

        # A model and a drawing on the machined part, tied by the relation the
        # suite uses for that pair. MCPT-PRT-002 deliberately gets nothing.
        model = self.create_document("MCPT-PRT-001 model", "MCPT-PRT-001-3D", "3d")
        drawing = self.create_document("MCPT-PRT-001 sheet", "MCPT-PRT-001-2D", "2d")
        model.linkedcomponents = [(4, part.id)]
        drawing.linkedcomponents = [(4, part.id)]
        self.create_link_document(model, drawing, "LyTree")

        return {
            "assembly": assembly,
            "part": part,
            "sub": sub,
            "child": child,
            "model": model,
            "drawing": drawing,
        }

    def new_revision(self, product):
        """A further revision of a part, as the suite records them.

        The revision is created directly rather than through the wizard: what
        the tools read is the (engineering_code, engineering_revision) pair, and
        going through the interface would test the wizard instead.
        """
        template = product.product_tmpl_id.copy({
            "engineering_code": product.engineering_code,
            "engineering_revision": product.engineering_revision + 1,
        })
        return template.product_variant_id
