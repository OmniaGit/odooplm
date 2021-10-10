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
"""
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""
from odoo import models
from odoo import fields
from odoo import api
import logging
from odoo import _


class PlmComponentDocumentRel(models.Model):
    _name = 'plm.component.document.rel'
    _description = "Component Document Relations"



    component_id = fields.Many2one('product.product',
                                   _('Linked Component'),
                                   required=True,
                                   #ondelete='cascade'
                                   )


    document_id = fields.Many2one('ir.attachment',
                                  _('Linked Document'),
                                  required=True,
                                  #ondelete='cascade'
                                  )


    _sql_constraints = [
        ('relation_unique', 'unique(component_id,document_id)', _('Component and Document relation has to be unique !')),
    ]

    @api.model
    def SaveStructure(self, relations, level=0, currlevel=0):
        """
            Save Document relations
        """
        def cleanStructure(relations):
            res = []
            for document_id, component_id in relations:
                latest = (document_id, component_id)
                if latest in res:
                    continue
                res.append(latest)
                prodProdObj = self.env['product.product']
                prodProdObj.write({'linkeddocuments': [(3, document_id, False)]})   # Clear link between component and document

        def saveChild(args):
            """
                save the relation
            """
            try:
                docId, compId = args
                if compId and docId:
                    compBrws = self.env['product.product'].browse(compId)
                    compBrws.write({'linkeddocuments': [(4, docId, False)]})    # Update with existing id
            except Exception as ex:
                logging.warning(ex)
                logging.warning("saveChild : Unable to create a link. Arguments (%s)." % (str(args)))
                raise Exception(_("saveChild: Unable to create a link."))

        if len(relations) < 1:  # no relation to save
            return False
        cleanStructure(relations)
        for relation in relations:
            saveChild(relation)
        return False

    @api.model
    def createFromIds(self, product_product_id, ir_attachment_id):
        exsist = self.search_count([('component_id', '=', product_product_id.id),
                                    ('document_id', '=', ir_attachment_id.id)])
        if not exsist:
            product_product_id.linkeddocuments = [(4, ir_attachment_id.id, False)]
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
