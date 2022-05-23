# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
'''
Created on Sep 7, 2019

@author: dsmerghetto
'''
import logging
from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class PlmCadOpen(models.Model):
    _name = "plm.cad.open"
    _description = "Opens made by the client"
    _order = 'id DESC'

    plm_backup_doc_id = fields.Many2one('plm.backupdoc', 'Backup Document Reference', index=True)
    userid = fields.Many2one('res.users', _('Related User'), index=True)
    document_id = fields.Many2one('ir.attachment', _('Related Document'), index=True)
    rel_doc_rev = fields.Integer(related='document_id.revisionid', string="Revision", store=True)
    pws_path = fields.Char(_('PWS Path'))
    hostname = fields.Char(_('Hostname'))
    operation_type = fields.Char(_('Operation Type'), index=True)

    @api.model
    def getLastCadOpenByUser(self, doc_id, user_id):
        for plm_cad_open in self.search([
            ('document_id', '=', doc_id.id),
            ('userid', '=', user_id.id),
            ], order='create_date DESC', limit=1):
            return plm_cad_open
        return self

    @api.model
    def run_clean_cad_open_bck_scheduler(self):
        logging.info('Start Cad open Clean Scheduler')
        rel_dict = {}
        cad_open_ids = self.search(args=[], order='create_date desc')
        for index, cad_open_id in enumerate(cad_open_ids):
            if index % 1000 == 0:
                self.env.cr.commit()
            doc_id = cad_open_id.document_id.id
            if doc_id not in rel_dict:
                rel_dict[doc_id] = []
            if cad_open_id.operation_type not in rel_dict[doc_id]:
                rel_dict[doc_id].append(cad_open_id.operation_type)
            else:
                self.env['plm.cad.open.bck'].create({
                    'plm_backup_doc_id': cad_open_id.plm_backup_doc_id.id,
                    'userid': cad_open_id.userid.id,
                    'document_id': cad_open_id.document_id.id,
                    'pws_path': cad_open_id.pws_path,
                    'hostname': cad_open_id.hostname,
                    'operation_type': cad_open_id.operation_type,
                    })
                cad_open_id.unlink()
        logging.info('End Cad open Clean Scheduler')
        
    def name_get(self):
        result = []
        for r in self:
            if r.document_id and r.userid:
                name = "%s - R:%s - [%s]" % (r.document_id.engineering_document_name, r.document_id.revisionid, r.userid.display_name)
            else:
                name = "Error"
            result.append((r.id, name))
        return result
