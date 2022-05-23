##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 03/nov/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    info@omniasolutions.eu
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
Created on 03/nov/2016

@author: mboscolo
'''

from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def forceRecursiveConvert(self, recursive=True):
        convert_stacks = self.env['plm.convert.stack']
        for product in self:
            document_ids = []
            for document in product.linkeddocuments:
                if recursive:
                    document_ids.extend(document.getRelatedAllLevelDocumentsTree(document))
                else:
                    document_ids.append(document.id)
            convert_stacks = self.env['ir.attachment'].browse(list(set(document_ids))).generateConvertedFiles()
        return {'name': _('Convert Stack'),
                'res_model': "plm.convert.stack",
                'view_type': 'form',
                'view_mode': 'tree,form',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', convert_stacks.ids)],
                'context': {}}
            
