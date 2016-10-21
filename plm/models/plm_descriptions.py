# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
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

import logging
from odoo import models
from odoo import fields
from odoo import _
_logger = logging.getLogger(__name__)
# Customized Automation to standardize and normalize descriptions and characteristics.
# It will allow to insert unit of measure (or label) and values, so to allow search on parts
# and it will build standardized description and labels and values to compose part description.


class PlmDescription(models.Model):
    _name = "plm.description"
    _description = "PLM Descriptions"

    name = fields.Char(_('Note to Description'),
                       size=128)
    description = fields.Char(_('Standard Description'),
                              default='',
                              size=128)
    description_en = fields.Char(_('Description English'),
                                 size=128)
    umc1 = fields.Char(_('UM / Feature 1'),
                       size=32,
                       help=_("Allow to specify a unit measure or a label for the feature."))
    fmt1 = fields.Char(_('Format Feature 1'),
                       size=32,
                       default='',
                       help=_("Allow to represent the measure: %s%s allow to build um and value, %s builds only value, none builds only value."))
    umc2 = fields.Char(_('UM / Feature 2'),
                       size=32,
                       help=_("Allow to specify a unit measure or a label for the feature."))
    fmt2 = fields.Char(_('Format Feature 2'),
                       size=32,
                       default='',
                       help=_("Allow to represent the measure: %s%s allow to build um and value, %s builds only value, none builds only value."))
    umc3 = fields.Char(_('UM / Feature 3'),
                       size=32,
                       help=_("Allow to specify a unit measure or a label for the feature."))
    fmt3 = fields.Char(_('Format Feature 3'),
                       size=32,
                       default='',
                       help=_("Allow to represent the measure: %s%s allow to build um and value, %s builds only value, none builds only value."))
    fmtend = fields.Char(_('Format Feature Composed'),
                         size=32,
                         default='',
                         help=_("Allow to represent a normalized composition of technical features : %s%s allows to build chained values."))
    unitab = fields.Char(_('Normative Rule'),
                         size=32,
                         default='',
                         help=_("Specify normative rule (UNI, ISO, DIN...). It will be queued to build the product description."))
    sequence = fields.Integer(_('Sequence'),
                              help=_("Assign the sequence order when displaying a list of product categories."))

PlmDescription()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
