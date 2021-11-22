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

    def document_extra(self, document):
        """
            this function id for customising the documents attributes
        """
        return document
    
    def component_extra(self, components):
        """
            this function id for customising the component attributes
        """
        return components
        
    @route('/plm/get_product_info', type='http', auth="user")
    @webservice
    def getProductInfo(self, document_id):
        out={}
        for ir_attachment in request.env['ir.attachment'].sudo().search([('id','=', int(document_id))]):
            if ir_attachment.has_web3d:
                document = """
                <li class="attribute_info"><b>Name:</b> %s</li>
                <li class="attribute_info"><b>Revision:</b> %s</li>
                <li class="attribute_info"><b>Description:</b> %s</li>
                """ % (
                    ir_attachment.engineering_document_name or ir_attachment.name,
                    ir_attachment.revisionid,
                    ir_attachment.state
                    )
                document = self.document_extra(document)
                out['document']=document
                for component in ir_attachment.linkedcomponents:
                    components = """
                    <li class="attribute_info"><b>Product Name:</b> %s</li>
                    <li class="attribute_info"><b>Product Revision:</b> %s</li>
                    <li class="attribute_info"><b>Description:</b> %s</li>
                    """ % ( component.engineering_code,
                            component.engineering_revision,
                            component.name)
                    components = self.component_extra(components)
                    out['component']=components
        return json.dumps(out)
  