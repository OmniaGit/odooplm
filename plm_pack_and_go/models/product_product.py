# -*- encoding: utf-8 -*-
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

'''
Created on Nov 21, 2017

@author: dsmerghetto
'''
from odoo import models

class PlmComponent(models.Model):
    _inherit = 'product.product'

    def unlink(self):
        for prodBrws in self:
            packAndGoObj = self.env['pack.and_go']
            presentPackAndGo = packAndGoObj.search([('component_id', '=', prodBrws.product_tmpl_id.id)])
            presentPackAndGo.unlink()
        return super(PlmComponent, self).unlink()
