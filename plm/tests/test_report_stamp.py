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
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.report.book_collector import BookCollector
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm
#


@tagged("-standard", "odoo_plm")
class PlmReportStamp(TransactionCase, PlmEntityCreator):
    """The line printed at the foot of every page of a PLM PDF: who printed it,
    when, and the state of the document."""

    def test_the_stamp_names_the_user_and_the_state(self):
        document = self.create_document("STAMP-1.slddrw")
        collector = BookCollector(poolObj=self.env)
        values = collector.evalDictVals(
            {
                "print_user": "user_id.name",
                "date_now": "Thu Oct  1 10:00:00 2026",
                "state": "doc_obj.engineering_state",
            },
            document,
            1,
            self.env.user,
        )
        self.assertEqual(
            values,
            {
                "print_user": self.env.user.name,
                "date_now": "Thu Oct  1 10:00:00 2026",
                "state": "draft",
            },
        )
