from odoo import SUPERUSER_ID, api

from odoo.addons.plm_auto_internalref.hooks import set_manual_internal_references


def migrate(cr, version):
    set_manual_internal_references(api.Environment(cr, SUPERUSER_ID, {}))
