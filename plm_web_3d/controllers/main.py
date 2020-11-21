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
        for ir_attachment in request.sudo().env['ir.attachment'].browse(document_id):
            Response(ir_attachment.datas,
                     headers={'file_name': ir_attachment.name})
        return Response(response="Document Not Found %r " % document_id, status=500)


  