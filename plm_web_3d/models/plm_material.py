# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2020 https://OmniaSolutions.website
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
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import fields, models


class PlmMaterial(models.Model):
    """How a material looks in the 3D viewer. A CAD export names its material
    (cad3d JSON, plm.appearance.material); the viewer looks it up here by
    designation and renders the part with this appearance."""

    _inherit = "plm.material"

    web3d_color = fields.Char(
        "3D Color",
        help="Colour of the material in the 3D viewer. Empty: the colour the CAD gave.",
    )
    web3d_metalness = fields.Float(
        "3D Metalness",
        default=0.3,
        help="0 for plastics, 1 for metals.",
    )
    web3d_roughness = fields.Float(
        "3D Roughness",
        default=0.5,
        help="0 polished, 1 matte.",
    )
    web3d_opacity = fields.Float(
        "3D Opacity",
        default=1.0,
        help="1 opaque, lower for glass and clear plastics.",
    )
    web3d_texture = fields.Image(
        "3D Texture",
        max_width=1024,
        max_height=1024,
        help="Image laid on the part, repeated every texture size.",
    )
    web3d_texture_size = fields.Float(
        "3D Texture Size (mm)",
        default=100.0,
        help="How many millimetres of the part one copy of the texture covers.",
    )

    _web3d_ranges = models.Constraint(
        "CHECK(web3d_metalness BETWEEN 0 AND 1 AND web3d_roughness BETWEEN 0 AND 1"
        " AND web3d_opacity BETWEEN 0 AND 1 AND web3d_texture_size > 0)",
        "Metalness, roughness and opacity go from 0 to 1; the texture size is above 0.",
    )
