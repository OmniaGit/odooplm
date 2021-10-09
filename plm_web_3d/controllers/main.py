# -*- coding: utf-8 -*-
import functools
import base64
import json
import logging
import os
from odoo import _
from odoo.http import Controller, route, request, Response
import copy
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


def webservice(f):
    @functools.wraps(f)
    def wrap(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception as e:
            return Response(response=str(e), status=500)
    return wrap

class Web3DView(Controller):
    @route('/plm/show_treejs_model', type='http', auth='public')
    @webservice
    def show_treejs_model(self, document_id, document_name):
        return request.render('plm_web_3d.main_treejs_view', {'document_id': document_id,
                                                              'document_name': document_name})

    @route('/plm/download_treejs_model', type='http', auth='public')
    @webservice
    def download_treejs_model(self, document_id):
        for ir_attachment in request.env['ir.attachment'].sudo().search([('id','=', int(document_id))]):
            if ir_attachment.has_web3d:
                headers = []
                content_base64 = base64.b64decode(ir_attachment.datas)
                headers.append(('Content-Length', len(content_base64)))
                headers.append(('file_name', ir_attachment.name))
                response = request.make_response(content_base64, headers)
                return response
        return Response(response="Document Not Found %r " % document_id, status=500)


  