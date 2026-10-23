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
from lxml import etree

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_support_files
#
SUPPORT_LINK_KINDS = ("ExtraTree", "PkgTree", "Web3DTree")


@tagged("-standard", "odoo_plm", "odoo_plm_support_files")
class PlmSupportFilesFilter(TransactionCase, PlmEntityCreator):

    def _filter_domain(self):
        """The domain of the Hide Support Files filter, read from the search view."""
        arch = etree.fromstring(self.env.ref("plm.ir_attachment_search").arch)
        node = arch.xpath("//filter[@name='hide_support_files']")[0]
        return safe_eval(node.get("domain"))

    def test_support_files_hidden(self):
        """Children of a support link are hidden, the other documents are not."""
        cad = self.create_document("support_cad.sldprt")
        child = self.create_document("support_child.sldprt")
        self.create_link_document(cad, child, "HiTree")
        support = self.env["ir.attachment"]
        for link_kind in SUPPORT_LINK_KINDS:
            support_file = self.create_document("support_%s.bin" % link_kind)
            self.create_link_document(cad, support_file, link_kind)
            support |= support_file
        found = self.env["ir.attachment"].search(
            self._filter_domain() + [("id", "in", (cad | child | support).ids)]
        )
        self.assertEqual(found, cad | child)

    def test_document_actions(self):
        """The menu hides support files by default, the restore list does not."""
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "plm.plm_action_document_form"
        )
        context = safe_eval(action["context"])
        self.assertEqual(context.get("search_default_hide_support_files"), 1)
        restore = self.env["plm.backupdoc_wizard"]._document_list_action()
        self.assertTrue(restore["context"].get("odooPLM"))
        self.assertFalse(
            [key for key in restore["context"] if key.startswith("search_default_")]
        )
