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
Created on 22 Aug 2016

@author: Daniel Smerghetto
'''
from openerp.exceptions import UserError
from openerp import models
from openerp import fields
from openerp import api
from openerp import SUPERUSER_ID
from openerp import _
import logging


class ProductProductExtended(models.Model):
    _name = 'product.rev_wizard'
    reviseDocument = fields.Boolean(_('Document Revision'), help=_("""Make new revision of the linked document ?"""))
    reviseEbom = fields.Boolean(_('Engineering Bom Revision'), help=_("""Make new revision of the linked Engineering BOM ?"""))
    reviseNbom = fields.Boolean(_('Normal Bom Revision'), help=_("""Make new revision of the linked Normal BOM ?"""))
    reviseSbom = fields.Boolean(_('Spare Bom Revision'), help=_("""Make new revision of the linked Spare BOM ?"""))

    @api.multi
    def action_create_new_revision_by_server(self):
        product_id = self.env.context.get('default_product_id', False)
        if not product_id:
            logging.error('[action_create_new_revision_by_server] Cannot revise because product_id is %r' % (product_id))
            raise UserError(_('Current component cannot be revised!'))
        prodProdEnv = self.env['product.product']
        prodBrws = prodProdEnv.browse(product_id)
        if self.stateAllows(prodBrws, 'Component'):
            revRes = prodBrws.NewRevision()
            newID, newIndex = revRes
            newIndex
            if not newID:
                logging.error('[action_create_new_revision_by_server] newID: %r' % (newID))
                raise UserError(_('Something wrong happens during new component revision process.'))
            if self.reviseDocument:
                self.docRev(prodBrws, newID, prodProdEnv)
            if self.reviseEbom:
                self.commonBomRev(prodBrws, newID, prodProdEnv, 'ebom')
            if self.reviseNbom:
                self.commonBomRev(prodBrws, newID, prodProdEnv, 'normal')
            if self.reviseSbom:
                self.commonBomRev(prodBrws, newID, prodProdEnv, 'spbom')
            return {'name': _('Revised Product'),
                    'view_type': 'tree,form',
                    "view_mode": 'form',
                    'res_model': 'product.product',
                    'res_id': newID,
                    'type': 'ir.actions.act_window'}

    @api.multi
    def stateAllows(self, brwsObj, objType):
        if brwsObj.state != 'released':
            logging.error('[action_create_new_revision_by_server:stateAllows] Cannot revise obj %s, Id: %r because state is %r' % (objType, brwsObj.id, brwsObj.state))
            raise UserError(_("%s cannot be revised because the state isn't released!" % (objType)))
        return True

    @api.multi
    def docRev(self, prodBrws, newID, prodProdEnv):
        createdDocIds = []
        for docBrws in prodBrws.linkeddocuments:
            if self.stateAllows(docBrws, 'Document'):
                resDoc = docBrws.NewRevision()
                newDocID, newDocIndex = resDoc
                newDocIndex
                if not newDocID:
                    logging.error('[action_create_new_revision_by_server] newDocID: %r' % (newDocID))
                    raise UserError(_('Something wrong happens during new document revision process.'))
                createdDocIds.append(newDocID)
        prodProdEnv.browse(newID).linkeddocuments = createdDocIds

    @api.multi
    def commonBomRev(self, oldProdBrws, newID, prodProdEnv, bomType):
        bomObj = self.env['mrp.bom']
        newProdBrws = prodProdEnv.browse(newID)
        for bomBrws in bomObj.search([('product_tmpl_id', '=', oldProdBrws.product_tmpl_id.id), ('type', '=', bomType)]):
            newBomBrws = bomObj.copy(bomBrws.id)
            newBomBrws.product_tmpl_id = newProdBrws.product_tmpl_id.id
            newBomBrws.source_id = newProdBrws.linkeddocuments.ids[0]

ProductProductExtended()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
