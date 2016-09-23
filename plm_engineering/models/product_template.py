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

'''
Created on 23 Sep 2016

@author: Daniel Smerghetto
'''
from openerp import models
from openerp import fields
from openerp import api
from openerp import _


class ProductTemplateExtension(models.Model):
    _inherit = 'product.template'

    engineering_revision = fields.Integer(_('Revision'), required=True, help=_("The revision of the product."))

    @api.multi
    def name_get(self):
        result = []
        for inv in self:
            newName = "%s [Rev %r]" % (inv.name, inv.engineering_revision)
            result.append((inv.id, newName))
        return result

ProductTemplateExtension()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
