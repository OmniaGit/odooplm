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
"""The previews move from the database to the filestore.

ir.attachment.preview and ir.attachment.relation.preview_related were Image
fields kept in bytea columns (attachment=False). They are now stored like every
other binary field, in an attachment of their record (res_model, res_id,
res_field). The update leaves the old columns where they are: this script moves
every value into its attachment, checks that none is missing, then drops the
columns.

The attachments are created by the base ORM, without the odooPLM context, so
nothing of the CAD client's path runs: no check-out or state check (released
documents are moved too), no workflow change. The images are moved as they
are, already resized when they were saved. Identical images share one file in
the filestore, which is named by its checksum, so the copies preview_related
keeps of the parent's preview take no space of their own.

Run again after an interruption, it skips the records already moved.
"""
import logging

from odoo import SUPERUSER_ID, api
from odoo.tools.binary import BinaryBytes

_logger = logging.getLogger(__name__)

BATCH = 1000

# (table, model, field): the column and the field have the same name.
MOVES = (
    ("ir_attachment", "ir.attachment", "preview"),
    ("ir_attachment_relation", "ir.attachment.relation", "preview_related"),
)


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.rowcount)


def _not_moved_sql(table, field):
    return """
        FROM {table} t
       WHERE t.{field} IS NOT NULL AND octet_length(t.{field}) > 0
         AND NOT EXISTS (
             SELECT 1 FROM ir_attachment a
              WHERE a.res_model = %(model)s AND a.res_field = %(field)s
                AND a.res_id = t.id)
    """.format(table=table, field=field)


def move_column_to_filestore(env, table, model, field):
    cr = env.cr
    if not _column_exists(cr, table, field):
        return 0
    params = {"model": model, "field": field}
    cr.execute("SELECT count(*) " + _not_moved_sql(table, field), params)
    total = cr.fetchone()[0]
    _logger.info("plm: %s %s.%s values to move to the filestore", total, model, field)
    attachments = env["ir.attachment"].sudo()
    moved = 0
    last_id = 0
    while True:
        cr.execute(
            "SELECT t.id, t.{field} ".format(field=field)
            + _not_moved_sql(table, field)
            + " AND t.id > %(last_id)s ORDER BY t.id LIMIT %(limit)s",
            dict(params, last_id=last_id, limit=BATCH),
        )
        rows = cr.fetchall()
        if not rows:
            break
        attachments.create([
            {
                "name": field,
                "res_model": model,
                "res_field": field,
                "res_id": record_id,
                "type": "binary",
                "raw": BinaryBytes(bytes(value)),
            }
            for record_id, value in rows
        ])
        env.flush_all()
        env.invalidate_all()
        moved += len(rows)
        last_id = rows[-1][0]
        _logger.info("plm: %s/%s %s.%s moved", moved, total, model, field)
    cr.execute("SELECT count(*) " + _not_moved_sql(table, field), params)
    left = cr.fetchone()[0]
    if left:
        # The update stops and rolls back: the column keeps every value.
        raise RuntimeError(
            "plm: %s %s.%s values were not moved to the filestore"
            % (left, model, field)
        )
    cr.execute('ALTER TABLE "{table}" DROP COLUMN "{field}"'.format(
        table=table, field=field))
    _logger.info("plm: column %s.%s dropped", table, field)
    return moved


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for table, model, field in MOVES:
        move_column_to_filestore(env, table, model, field)
