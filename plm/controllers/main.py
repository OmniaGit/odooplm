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


class UploadDocument(Controller):

    @route('/plm_document_upload/isalive', type='http', auth='none', methods=['GET'], csrf=False)
    @webservice
    def isalive(self):
        return Response('True', status=200)

    @route('/plm_document_upload/login', type='http', auth='none', methods=['POST'], csrf=False)
    @webservice
    def login(self, login, password, db=None):
        if db and db != request.db:
            raise Exception(_("Could not select database '%s'") % db)
        uid = request.session.authenticate(request.db, login, password)
        if not uid:
            return Response(response="Wrong login/password", status=401)
        return Response(headers={
            'X-CSRF-TOKEN': request.csrf_token(),
        })

    @route('/plm_document_upload/upload_pdf', type='http', auth='user', methods=['POST'], csrf=False)
    @webservice
    def upload_pdf(self, file_stream=None, doc_id=False, **kw):
        logging.info('start upload PDF %r' % (doc_id))
        if doc_id:
            logging.info('start json %r' % (doc_id))
            doc_id = json.loads(doc_id)
            logging.info('start write %r' % (doc_id))
            value1 = file_stream.stream.read()
            request.env['ir.attachment'].browse(doc_id).write(
                {'printout': base64.b64encode(value1),
                 })
            logging.info('upload %r' % (doc_id))
            return Response('Upload succeeded', status=200)
        logging.info('no upload %r' % (doc_id))
        return Response('Failed upload', status=400)

    @route('/plm_document_upload/upload', type='http', auth='user', methods=['POST'], csrf=False)
    @webservice
    def upload(self, mod_file=None, doc_id=False, filename='', **kw):
        logging.info('start upload %r' % (doc_id))
        if doc_id:
            logging.info('start json %r' % (doc_id))
            doc_id = json.loads(doc_id)
            logging.info('start write %r' % (doc_id))
            value1 = mod_file.stream.read()
            to_write = {'datas': base64.b64encode(value1),
                        'name': filename}
            preview = kw.get('preview', '')
            if preview:
                #to_write['preview'] = preview.stream.read()
                val_2 = base64.b64encode(preview.stream.read())
                to_write['preview'] = val_2
            doc_brws = request.env['ir.attachment'].browse(doc_id)
            doc_brws.write(to_write)
            doc_brws.setupCadOpen(kw.get('hostname', ''), kw.get('hostpws', ''), operation_type='save')
            logging.info('upload %r' % (doc_id))
            return Response('Upload succeeded', status=200)
        logging.info('no upload %r' % (doc_id))
        return Response('Failed upload', status=400)      
        
    @route('/plm_document_upload/download', type='http', auth='user', methods=['GET'])
    @webservice
    def download(self, requestvals='[[],[],-1]', **kw):
        logging.info('Download with arguments %r kw %r' % (requestvals, kw))
        if not requestvals:
            logging.info('No file requests to download')
            return Response([], status=200)
        requestvals = json.loads(requestvals)
        plmDocEnv = request.env['ir.attachment']
        result = plmDocEnv.GetSomeFiles(requestvals)
        docContent = ''
        result2 = {}
        for docTuple in result:
            docId, docName, docContent, checkOutByMe, timeDoc = docTuple
            if not docContent:
                docContent = ''
                docTuple = (docId, docName, docContent, checkOutByMe, timeDoc)
            result2 = copy.deepcopy(list(docTuple))
            docContent = result2[2]
            result2[2] = ''
            break
        return Response(docContent,
                        headers={'result': [result2]})

    @route('/plm_document_upload/upload_preview', type='http', auth='user', methods=['POST'], csrf=False)
    @webservice
    def upload_preview(self, mod_file=None, doc_id=False, **kw):
        logging.info('start upload preview %r' % (doc_id))
        if doc_id:
            logging.info('start json %r' % (doc_id))
            doc_id = json.loads(doc_id)
            logging.info('start write %r' % (doc_id))
            value1 = mod_file.stream.read()
            request.env['ir.attachment'].browse(doc_id).write(
                {'preview': base64.b64encode(value1),
                 })
            logging.info('upload %r' % (doc_id))
            return Response('Upload succeeded', status=200)
        logging.info('no upload %r' % (doc_id))
        return Response('Failed upload', status=400)

    @route('/plm_document_upload/zip_archive', type='http', auth='user', methods=['POST'], csrf=False)
    @webservice
    def upload_zip(self, attachment_id=None, filename='', **kw):
        logging.info('start upload zip %r' % (attachment_id))
        if attachment_id:
            attachment_id = json.loads(attachment_id)
            value1 = kw.get('file_stream').stream.read()
            from_ir_attachment_id = request.env['ir.attachment'].browse(attachment_id)
            zip_name, _zipExtention = os.path.splitext(filename)
            zip_ir_attachment_id  = request.env['ir.attachment'].search([('engineering_document_name',  'in', [zip_name, filename]),
                                                                         ('revisionid', '=', from_ir_attachment_id.revisionid),
                                                                         ('document_type', '=', 'other'),
                                                                         ('name', '=', filename)
                                                                         ])
            to_write = {'datas': base64.b64encode(value1),
                        'name': filename,
                        'engineering_document_name': zip_name,
                        'revisionid': from_ir_attachment_id.revisionid}
            link_id =  request.env['ir.attachment.relation']
            new_context = request.env.context.copy()
            new_context['backup'] = False
            new_context['check'] = False    # Or zip file will not be updated if in check-in
            contex_brw = request.env['ir.attachment'].with_context(new_context)
            to_write['is_plm'] = True
            if not zip_ir_attachment_id:
                if from_ir_attachment_id.engineering_document_name == zip_name:
                    to_write['engineering_document_name'] = filename
                zip_ir_attachment_id  = contex_brw.create(to_write)
            else:
                del to_write['name']
                del to_write['engineering_document_name']
                del to_write['revisionid']
                zip_ir_attachment_id.with_context(new_context).write(to_write)
                link_id = link_id.search([('parent_id', '=', from_ir_attachment_id.id),
                                          ('child_id', '=', zip_ir_attachment_id.id),
                                          ('link_kind', '=', 'PkgTree')])
            if not link_id:
                request.env['ir.attachment.relation'].create({'parent_id': from_ir_attachment_id.id,
                                                              'child_id': zip_ir_attachment_id.id,
                                                              'link_kind': 'PkgTree'})                     
            return Response('Zip Upload succeeded', status=200)
        logging.info('Zip no upload %r' % (attachment_id))
        return Response('Zip Failed upload', status=400)

    @route('/plm_document_upload/get_zip_archive', type='http', auth='user', methods=['get'], csrf=False)
    @webservice
    def download_zip(self, ir_attachment_id=None, **kw):
        try:
            ir_attachment_id = json.loads(ir_attachment_id)
            attachment = request.env['ir.attachment']
            pkg_ids = attachment.getRelatedPkgTree(ir_attachment_id)
            for pkg_id in pkg_ids:
                pkg_brws = attachment.browse(pkg_id)
                return Response(pkg_brws.datas,
                                headers={'file_name': pkg_brws.name})
            return Response(status=200)
        except Exception as ex:
            return Response(ex, json.dumps({}),status=500)

    @route('/plm_document_upload/get_files_write_time', type='http', auth='user', methods=['get'], csrf=False)
    @webservice
    def get_files_write_time(self, ir_attachment_ids=None, **kw):
        try:
            ir_attachment_ids = json.loads(ir_attachment_ids)
            attachment = request.env['ir.attachment']
            out = []
            for attachment_id in ir_attachment_ids:
                attachment_brws = attachment.browse(attachment_id)
                out.append((attachment_brws.id, attachment_brws.name, attachment_brws.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)))
            return Response(json.dumps(out))
        except Exception as ex:
            return Response(ex, json.dumps([]),status=500)

    @route('/plm_document_upload/extra_file', type='http', auth='user', methods=['POST'], csrf=False)
    @webservice
    def upload_extra_file(self, product_id='', doc_name='', doc_rev='0', related_attachment_id='', **kw):
        logging.info('Start upload extra file %r' % (product_id))
        product_id = eval(product_id)
        doc_rev = eval(doc_rev)
        related_attachment_id = eval(related_attachment_id)
        if doc_name:
            value1 = kw.get('file_stream').stream.read()
            ir_attachment_id  = request.env['ir.attachment'].search([('engineering_document_name',  '=', doc_name),
                                                                     ('revisionid', '=', doc_rev)])
            to_write = {'datas': base64.b64encode(value1),
                        'name': doc_name,
                        'engineering_document_name': doc_name,
                        'revisionid': doc_rev}
            link_id =  request.env['ir.attachment.relation']
            new_context = request.env.context.copy()
            new_context['backup'] = False
            new_context['check'] = False    # Or zip file will not be updated if in check-in
            contex_brw = request.env['ir.attachment'].with_context(new_context)
            to_write['is_plm'] = True
            if not ir_attachment_id:
                ir_attachment_id = contex_brw.create(to_write)
            else:
                ir_attachment_id.with_context(new_context).write(to_write)
            if ir_attachment_id and related_attachment_id:
                link_id = link_id.search([('parent_id', '=', related_attachment_id),
                                          ('child_id', '=', ir_attachment_id.id),
                                          ('link_kind', '=', 'ExtraTree')])
            if not link_id:
                request.env['ir.attachment.relation'].create({'parent_id': related_attachment_id,
                                                              'child_id': ir_attachment_id.id,
                                                              'link_kind': 'ExtraTree'})    
            if product_id:
                product_id = request.env['product.product'].browse(product_id)
                request.env['plm.component.document.rel'].createFromIds(product_id, ir_attachment_id)           
            return Response('Extra file Upload succeeded', status=200)
        logging.info('Extra file no upload %r' % (ir_attachment_id))
        return Response('Extra file Failed upload', status=400)

    @route('/plm/ir_attachment_preview/<int:id>', type='http', auth='user', methods=['GET'], csrf=False)
    @webservice
    def get_preview(self, id):
        ir_attachement = request.env['ir.attachment'].sudo()
        for record in ir_attachement.search_read([('id','=', id)], ['preview']):
            return base64.b64decode(record.get('preview'))
        