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
Created on Aug 30, 2019

@author: mboscolo
'''
import os
import requests
import hashlib
from requests.auth import HTTPBasicAuth
import logging
import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from io import BytesIO
import base64


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class PlmRemoteServer(models.Model):
    _name = "plm.remote.server"
    _description = "Plm Remote server"
    name = fields.Char("Server Name")
    login = fields.Char("Login")
    password = fields.Char("Password")
    address = fields.Char("Server Ip Address")

    _sql_constraints = [('name',
                         'unique (name)',
                         'Server name must be unique !!!')]

    @api.model
    def document_is_there(self, ir_attachment_id):
        url = '%s/document_is_there/%s' % (self.address, ir_attachment_id)
        r = requests.get(url,
                         auth=HTTPBasicAuth(self.login,
                                            self.password))
        if r.status_code == 200:
            return r.text == 'true'
        else:
            raise Exception("Get %s from server %s" % (r.status_code, self.name))

    @api.model
    def push_document_to_remote(self, ir_attachment_id):
        try:
            logging.info("push_document_to_remote")
            url = '%s/upload_file' % self.address
            file_path = ir_attachment_id.full_path()
            files = {'file': (str(ir_attachment_id.id), open(file_path, 'rb'))}
            r = requests.post(url,
                              auth=HTTPBasicAuth(self.login,
                                                 self.password),
                              files=files)
            out = r.status_code == 200
            if not out:
                logging.error("Bad response from server %r" % r.status_code)
            return out
        except Exception as ex:
            logging.error(ex)
            return False

    @api.model
    def pull_document_to_odoo(self, ir_attachment_id):
        try:
            url = '%s/download_file/%s' % (self.address, ir_attachment_id.id)
            r = requests.get(url, auth=HTTPBasicAuth(self.login,
                                                     self.password))
            r.raise_for_status()
            ret = r.status_code == 200
            if ret:
                f = BytesIO()
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
                ir_attachment_id.datas = base64.encodestring(f.getvalue())
            return ret
        except Exception as ex:
            logging.error(ex)
            return False
