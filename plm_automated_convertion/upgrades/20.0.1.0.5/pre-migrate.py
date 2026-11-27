# -*- coding: utf-8 -*-
"""The conversion wizard is new: the view that hid the conversions of the CAD
workstations from the old one points at a field that no longer exists, and
would stop the update. It exists only where the queue of the CAD workstations
was installed before the new wizard (ported from 18.0 1baa8ebe)."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT res_id FROM ir_model_data WHERE module = %s AND name = %s AND model = 'ir.ui.view'",
        ["plm_automated_convertion", "plm_convert_form_cad_agent"],
    )
    row = cr.fetchone()
    if not row:
        return
    cr.execute("DELETE FROM ir_ui_view WHERE id = %s", [row[0]])
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = %s AND name = %s",
        ["plm_automated_convertion", "plm_convert_form_cad_agent"],
    )
