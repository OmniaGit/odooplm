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
Created on 12 Dec 2016

@author: Daniel Smerghetto
"""
import json
import logging

from odoo import fields
from odoo import models
from odoo import _
from odoo import api

class ProductTemporary(models.TransientModel):
    _name = "plm.temporary"
    _description = "Temporary Class"
    name = fields.Char(_('Temp'), size=128)
    summarize = fields.Boolean(
        'Summarise Bom Lines if needed.',
        help="If set as true, when a Bom line comes from EBOM was in the old normal BOM two lines where been summarized."
    )
    migrate_custom_lines = fields.Boolean(
        _('Preserve custom BOM lines from previous Normal BOM revision'),
        default=True,
        help=_(
            "If the user adds custom BOM lines in the revision 0 BOM, than makes the revision 1, "
            "creates it's engineering BOM and than create the new Normal BOM form EBOM your revision 0"
            " custom BOM lines are created in the new BOM")
    )

    @api.model
    def writeUpdateNode(self, jinfos="{}"):
        allProps = json.loads(jinfos)
        product_props = allProps.get('product.product', {})
        ir_attachment_props = allProps.get('ir.attachment', {})
        #
        def writeOrUpdate(model, code, revision, propsVal):
            out_id = None
            modelObj = self.env[model]
            eng_code = propsVal.get(code)
            domain = []
            if eng_code:
                domain.append((code, '=', eng_code))
                eng_rev  = propsVal.get(revision) or 0
                domain.append((revision, '=', eng_rev))
                for out_id in modelObj.search(domain):
                    break
            if out_id:
                out_id.write(propsVal)
                return out_id
            else:
                return modelObj.create(propsVal)
        #
        product_id = False
        if product_props:
            product_id = writeOrUpdate('product.product',
                                       'engineering_code',
                                       'engineering_revision',
                                       product_props).id
        ir_attachemnt_id = False
        if ir_attachment_props :
            ir_attachemnt_id = writeOrUpdate('ir.attachment',
                                             'engineering_document_name',
                                             'revisionid',
                                             ir_attachment_props).id
        return ir_attachemnt_id, product_id 

    
        
        