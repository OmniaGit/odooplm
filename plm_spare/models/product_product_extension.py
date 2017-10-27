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


class PlmComponentExtension(models.Model):
    _inherit = 'product.product'

    @api.multi
    def action_create_spareBom_WF(self):
        """
            Create a new Spare Bom if doesn't exist (action callable from code)
        """
        self._create_spareBom()
        return False

    @api.multi
    def _create_spareBom(self):
        """
            Create a new Spare Bom (recursive on all EBom children)
        """
        self.processedIds = []
        self._createLocalSparebom(self.id)

    def _createLocalSparebom(self, prodId):
        newBomBrws = None
        if prodId in self.processedIds:
            return False
        self.processedIds.append(prodId)
        for spareBomBrws in self.browse(prodId):
            if not spareBomBrws:
                return False
            if '-Spare' in spareBomBrws.name:
                return False
            sourceBomType = self.env.context.get('sourceBomType', 'ebom')
            bomType = self.env['mrp.bom']
            bomLType = self.env['mrp.bom.line']
            spareBomBrwsList = bomType.search([('product_tmpl_id', '=', spareBomBrws.product_tmpl_id.id),
                                               ('type', '=', 'spbom')])
            normalBomBrwsList = bomType.search([('product_tmpl_id', '=', spareBomBrws.product_tmpl_id.id),
                                                ('type', '=', 'normal')])
            if not normalBomBrwsList:
                normalBomBrwsList = bomType.search([('product_tmpl_id', '=', spareBomBrws.product_tmpl_id.id),
                                                    ('type', '=', sourceBomType)])
            defaults = {}
            if not spareBomBrwsList:
                if spareBomBrws.std_description.bom_tmpl:
                    newBomBrws = bomType.browse(spareBomBrws.std_description.bom_tmpl.id).copy(defaults)
                if (not newBomBrws) and normalBomBrwsList:
                        newBomBrws = normalBomBrwsList[0].copy(defaults)
                if newBomBrws:
                    newBomBrws.write({'name': spareBomBrws.name,
                                      'product_id': spareBomBrws.id,
                                      'type': 'spbom'},
                                     check=False)
                    ok_rows = self._summarizeBom(newBomBrws.bom_line_ids)
                    for bom_line in list(set(newBomBrws.bom_line_ids) ^ set(ok_rows)):
                        bomLType.browse(bom_line.id).unlink()
                    for bom_line in ok_rows:
                        bomLType.browse(bom_line.id).write({'type': 'spbom',
                                                            'source_id': False,
                                                            'name': bom_line.product_id.name,
                                                            'product_qty': bom_line.product_qty})
                        self._createLocalSparebom(bom_line.product_id.id)
            else:
                for bom_line in spareBomBrwsList[0].bom_line_ids:
                    self._createLocalSparebom(bom_line.product_id.id)
            return False

PlmComponentExtension()
