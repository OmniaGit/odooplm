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
Created on 30 Aug 2016

@author: Daniel Smerghetto
'''

from openerp import models
from openerp import api
from openerp import _


class ProdProdKanbanExtension(models.Model):
    _inherit = 'product.product'

    @api.multi
    def open_engin_bom(self):
        boms = self.get_related_boms()
        domain = [('id', 'in', boms.ids), ('type', '=', 'ebom')]
        return self.common_open(_('Related Boms'), 'mrp.bom', 'tree,form', 'form', boms.ids, self.env.context, domain)

ProdProdKanbanExtension()
