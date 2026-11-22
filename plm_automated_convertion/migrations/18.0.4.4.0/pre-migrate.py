# -*- coding: utf-8 -*-
"""The conversion wizard is new: the view that hid the conversions of the CAD
workstations from the old one (first in omnia_cad_version_update, then here)
points at a field that no longer exists, and would stop the update."""

OLD_VIEWS = [
    ("omnia_cad_version_update", "plm_convert_form_cad_agent"),
    ("plm_automated_convertion", "plm_convert_form_cad_agent"),
]


def migrate(cr, version):
    if not version:
        return
    for module, name in OLD_VIEWS:
        cr.execute(
            "SELECT res_id FROM ir_model_data WHERE module = %s AND name = %s AND model = 'ir.ui.view'",
            [module, name],
        )
        row = cr.fetchone()
        if not row:
            continue
        cr.execute("DELETE FROM ir_ui_view WHERE id = %s", [row[0]])
        cr.execute("DELETE FROM ir_model_data WHERE module = %s AND name = %s", [module, name])
