##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models
from odoo.tools import formatLang


class UomUom(models.Model):
    _inherit = 'uom.uom'

    def get_report_qty_uom(self, qty):
        """Return ``(display_qty, display_uom_name)`` for ``qty`` expressed in
        ``self``.

        The target unit is taken from the per-language configuration
        (``plm.uom.lang``) resolved against the language currently in context
        (i.e. the language chosen when printing the report). When a target UoM
        is configured for that language and this UoM's category, the quantity is
        converted with Odoo's own conversion rate (``_compute_quantity``) and the
        target UoM name is returned. For any UoM whose category has no
        configured target (e.g. Speed, Mass, or any category left unset for the
        language) the original quantity and UoM name are returned unchanged.

        The quantity is formatted with ``formatLang`` so it uses the decimal and
        thousands separators of the language in context (e.g. ``1.234,56`` in
        Italian, ``1,234.56`` in English).
        """
        self.ensure_one()
        lang_code = self.env.context.get('lang')
        uom = self
        target = self.env['plm.uom.lang']._get_report_target_uom(lang_code, self.category_id)
        if target and target != self and target.category_id == self.category_id:
            qty = self._compute_quantity(qty, target)
            uom = target
        qty_display = formatLang(self.env, qty, dp='Product Unit of Measure')
        return qty_display, uom.name
