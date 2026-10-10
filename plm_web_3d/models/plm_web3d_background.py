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
import os

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

HDR_EXTENSIONS = (".hdr",)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


class PlmWeb3dBackground(models.Model):
    """A background of the 3D viewer: an HDRI, which also lights the parts and
    shows in their reflections, or a 360 degree photo (equirectangular, 2:1).
    An HDRI sharp enough to look at is heavy: the backdrop, a 360 degree photo
    of the same place, can be shown in its place while the HDRI only lights.
    The viewer lists the active ones after its two built-in backgrounds,
    Tecnical and Clean."""

    _name = "plm.web3d.background"
    _description = "3D Viewer Background"
    _order = "sequence, id"

    name = fields.Char("Name", required=True, translate=True)
    sequence = fields.Integer("Sequence", default=10)
    active = fields.Boolean("Active", default=True)
    file = fields.Binary("File", attachment=True, required=True,
                         help="An HDRI (.hdr) or a 360 degree photo (.jpg, .png, 2:1).")
    file_name = fields.Char("File Name")
    backdrop = fields.Binary(
        "Backdrop Image", attachment=True,
        help="A sharper 360 degree photo of the same place (.jpg, .png, 2:1), shown "
             "behind the parts instead of the file, which then only lights them.",
    )
    backdrop_name = fields.Char("Backdrop File Name")
    file_type = fields.Selection(
        [("hdr", "HDRI"), ("image", "Photo")],
        string="Type",
        compute="_compute_file_type",
        store=True,
    )

    @api.depends("file_name")
    def _compute_file_type(self):
        for background in self:
            extension = os.path.splitext(background.file_name or "")[1].lower()
            background.file_type = "hdr" if extension in HDR_EXTENSIONS else "image"

    @api.constrains("file_name", "backdrop_name")
    def _check_file_name(self):
        for background in self:
            extension = os.path.splitext(background.file_name or "")[1].lower()
            if extension not in HDR_EXTENSIONS + IMAGE_EXTENSIONS:
                raise ValidationError(_(
                    "A 3D background is an HDRI (.hdr) or a 360 degree photo "
                    "(.jpg, .png): %(name)s is neither.", name=background.file_name or "?",
                ))
            backdrop = os.path.splitext(background.backdrop_name or "")[1].lower()
            if background.backdrop_name and backdrop not in IMAGE_EXTENSIONS:
                raise ValidationError(_(
                    "The backdrop of a 3D background is a 360 degree photo (.jpg, "
                    ".png): %(name)s is not.", name=background.backdrop_name,
                ))
