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
"""Binary fields of ir.attachment that can be searched.

A binary field stored in the filestore keeps its value in an attachment of its
record, and Odoo answers ``(field, '!=', False)`` with
``EXISTS (SELECT 1 FROM ir_attachment WHERE ... AND res_id = <record>.id)``.
On ir.attachment itself the record's table is ir_attachment too: the subquery,
without an alias of its own, hides the outer one, ``res_id`` is compared with
the id of the same row and the search never finds anything (Odoo 20). These
fields give the subquery an alias; anything else is the Odoo field.
"""
from odoo import fields
from odoo.tools import SQL

SUBQUERY_ALIAS = "plm_field_attachment"


class _AttachmentSearchMixin:

    def condition_to_sql(self, table, field_expr, operator, value):
        if (
            field_expr == self.name
            and self.attachment
            and operator in ("in", "not in")
            and set(value) == {False}
        ):
            return SQL(
                "%sEXISTS (SELECT 1 FROM ir_attachment %s"
                " WHERE %s.res_model = %s AND %s.res_field = %s AND %s.res_id = %s)",
                SQL("NOT ") if operator == "in" else SQL(),
                SQL.identifier(SUBQUERY_ALIAS),
                SQL.identifier(SUBQUERY_ALIAS),
                table._model._name,
                SQL.identifier(SUBQUERY_ALIAS),
                self.name,
                SQL.identifier(SUBQUERY_ALIAS),
                table.id,
            )
        return super().condition_to_sql(table, field_expr, operator, value)


class AttachmentBinary(_AttachmentSearchMixin, fields.Binary):
    pass


class AttachmentImage(_AttachmentSearchMixin, fields.Image):
    pass
