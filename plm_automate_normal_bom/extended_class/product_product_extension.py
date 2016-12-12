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
Created on 26 Jul 2016

@author: Daniel Smerghetto
'''
import logging
from openerp import models
from openerp import api


class ProdProdExtension(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    @api.multi
    def generateAutomatedNBoms(self):
        '''
            Generate all normal boms starting from released components.
        '''
        errors = []
        mrpBomObj = self.env['mrp.bom']
        releasedComponents = self.search([('state', '=', 'released')])
        logging.info('[Automate Nbom scheduler started] found %s components' % (len(releasedComponents.ids)))
        for prodBrws in releasedComponents:
            try:
                bomBrwsList = mrpBomObj.search([('product_id', '=', prodBrws.id), ('type', '=', 'normal')])
                if not bomBrwsList:
                    engBoms = mrpBomObj.search([('product_id', '=', prodBrws.id), ('type', '=', 'ebom')])
                    if engBoms:
                        prodBrws.action_create_normalBom_WF()
                        logging.info('Created Normal bom of %s component on %s' % (releasedComponents.ids.index(prodBrws.id), len(releasedComponents.ids)))
            except Exception, ex:
                errors.append(ex)
        logging.info('[Automate Nbom scheduler ended]')
        if errors:
            logging.warning('[Automate Nbom scheduler errors] some errors are found during normal bom computation.')
        for error in errors:
            logging.warning(error)

ProdProdExtension()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
