# -*- coding: utf-8 -*-
import base64
import functools
import json
import logging
from odoo import http
from odoo.http import Controller, route, request, Response
from markupsafe import Markup

_logger = logging.getLogger(__name__)


def _resolve_components(record):
    """Return linked product.product records for a document.

    Walks the source chain so converted files (e.g. 3MF from STEP) still
    find the products attached to the original engineering document:
      1. direct linkedcomponents on the record
      2. linkedcomponents of source_convert_document (conversion source)
      3. linkedcomponents of the Web3DTree parent relation
    """
    if hasattr(record, 'linkedcomponents') and record.linkedcomponents:
        return record.linkedcomponents
    if hasattr(record, 'source_convert_document') and record.source_convert_document:
        src = record.source_convert_document
        if hasattr(src, 'linkedcomponents') and src.linkedcomponents:
            return src.linkedcomponents
    parent_rel = record.env['ir.attachment.relation'].search([
        ('child_id', '=', record.id),
        ('link_kind', '=', 'Web3DTree'),
    ], limit=1)
    if parent_rel and hasattr(parent_rel.parent_id, 'linkedcomponents'):
        return parent_rel.parent_id.linkedcomponents
    return record.env['product.product']


def webservice(f):
    @functools.wraps(f)
    def wrap(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception as e:
            return Response(response=str(e), status=500)

    return wrap


class Web3DView(Controller):
    @route("/plm/show_treejs_model", type="http", auth="user")
    @webservice
    def show_treejs_model(self, document_id, document_name):
        return request.render(
            "plm_web_3d.main_treejs_view",
            {"document_id": document_id, "document_name": document_name},
        )

    @route("/plm/download_treejs_model", type="http", auth="user")
    @webservice
    def download_treejs_model(self, document_id):
        if not request.env.user.has_group("plm.group_plm_view_user"):
            return Response(response="Access denied", status=403)
        # No sudo: record rules decide which attachments this user may read,
        # so a user cannot download CAD files they have no access to.
        for ir_attachment in request.env["ir.attachment"].search(
            [("id", "=", int(document_id))]
        ):
            if ir_attachment.has_web3d:
                headers = []
                content_base64 = base64.b64decode(ir_attachment.datas)
                headers.append(("Content-Length", len(content_base64)))
                headers.append(("file_name", ir_attachment.name))
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

    @route("/plm/get_product_info", type="http", auth="user")
    @webservice
    def getProductInfo(self, document_id=None):
        if not document_id:
            return json.dumps({})
        out = {}
        ir_attachment = request.env["ir.attachment"].sudo().browse(int(document_id))
        if not ir_attachment.exists():
            return json.dumps(out)
        if ir_attachment.has_web3d:
            # For 3mf conversions, follow source document for PLM metadata and linked product
            info_doc = ir_attachment
            if (
                ir_attachment.name
                and ir_attachment.name.lower().endswith(".3mf")
                and ir_attachment.source_convert_document
            ):
                info_doc = ir_attachment.source_convert_document
            doc_name = info_doc.engineering_code or info_doc.name
            document = Markup("""
            <li class="attribute_info"><b>Name:</b> <span class="plm_link" data-doc-id="%s">%s</span></li>
            <li class="attribute_info"><b>Revision:</b> %s</li>
            <li class="attribute_info"><b>Description:</b> %s</li>
            """ % (
                info_doc.id,
                doc_name,
                info_doc.engineering_revision,
                info_doc.engineering_state,
            ))
            document = self.document_extra(document)
            out["document"] = document
            for component in info_doc.linkedcomponents:
                components = Markup("""
                <li class="attribute_info" id="linked_component_id" data-id="%s"><b>Product Name:</b> <span class="plm_link" data-prod-id="%s">%s</span></li>
                <li class="attribute_info"><b>Product Revision:</b> %s</li>
                <li class="attribute_info"><b>Description:</b> %s</li>
                """ % (
                    component.id,
                    component.id,
                    component.engineering_code or component.name,
                    component.engineering_revision,
                    component.name,
                ))
                components = self.component_extra(components)
                out["component"] = components
        return json.dumps(out)

    @route("/plm/get_product_id", type="http", auth="user")
    def get_product_id(self, src_name, parent_id=None):
        """Return JSON {product_id: N} for the product matching src_name."""
        env = request.env
        if parent_id and str(parent_id).isdigit():
            parent_doc = env["ir.attachment"].sudo().browse(int(parent_id))
            if parent_doc.exists():
                for p in parent_doc.linkedcomponents:
                    if p.engineering_code == src_name or p.name == src_name or p.default_code == src_name:
                        return json.dumps({"product_id": p.id})
        prod = env["product.product"].sudo().search(
            ["|", "|",
             ("engineering_code", "=", src_name),
             ("default_code", "=", src_name),
             ("name", "=", src_name)],
            limit=1,
        )
        return json.dumps({"product_id": prod.id if prod else None})

    @route("/plm/get_3d_web_document_info", type="http", auth="user")
    def get_3d_web_document_info(self, src_name, parent_id=None):
        if not parent_id or not str(parent_id).isdigit():
            return src_name

        parent_doc = request.env["ir.attachment"].sudo().browse(int(parent_id))
        if not parent_doc.exists():
            return src_name

        for p in parent_doc.linkedcomponents:
            if p.engineering_code == src_name or p.name == src_name or p.default_code == src_name:
                code = p.engineering_code or p.default_code or ''
                name = p.name or ''
                if code:
                    return f"{code} - {name}"
                return name

        prod = request.env['product.product'].sudo().search([
            '|', '|', ('engineering_code', '=', src_name), ('default_code', '=', src_name), ('name', '=', src_name)
        ], limit=1)
        if prod:
            code = prod.engineering_code or prod.default_code or ''
            name = prod.name or ''
            if code:
                return f"{code} - {name}"
            return name

        return src_name


    @http.route('/plm/save_preview', type='jsonrpc', auth='user')
    def save_preview(self, document_id=None, image_data=None):
        if not document_id or not image_data:
            return {'success': False}
        doc = request.env['ir.attachment'].sudo().browse(int(document_id))
        if not doc.exists():
            return {'success': False}
        try:
            image_bytes = base64.b64decode(image_data)
            image_b64 = base64.b64encode(image_bytes)
            doc.sudo().write({'preview': image_b64})
            components = _resolve_components(doc)
            updated = 0
            seen_tmpl = set()
            for comp in components:
                tmpl = comp.product_tmpl_id
                if tmpl and tmpl.id not in seen_tmpl:
                    seen_tmpl.add(tmpl.id)
                    tmpl.sudo().write({'image_1920': image_b64})
                    updated += 1
            return {'success': True, 'products_updated': updated}
        except Exception as e:
            _logger.warning("Failed to save preview: %s", e)
            return {'success': False, 'error': str(e)}

    @http.route('/plm/part_colors/load', type='http', auth='user')
    def part_colors_load(self, document_id=None):
        if not document_id or not str(document_id).isdigit():
            return json.dumps({})
        doc = request.env['ir.attachment'].sudo().browse(int(document_id))
        if not doc.exists() or not doc.web3d_part_colors:
            return json.dumps({})
        try:
            return doc.web3d_part_colors
        except Exception:
            return json.dumps({})

    @http.route('/plm/part_colors/save', type='jsonrpc', auth='user')
    def part_colors_save(self, document_id=None, colors=None):
        if not document_id or not colors:
            return {'success': False}
        doc = request.env['ir.attachment'].sudo().browse(int(document_id))
        if not doc.exists():
            return {'success': False}
        try:
            doc.sudo().write({'web3d_part_colors': json.dumps(colors)})
            return {'success': True}
        except Exception as e:
            _logger.warning("Failed to save part colors: %s", e)
            return {'success': False, 'error': str(e)}

    @http.route('/plm/save_markup', type='jsonrpc', auth='user')
    def save_markup(self, image=None, base_image=None, filename=None, comment=None,
                    res_model=None, res_id=None, canvas_json=None,
                    schedule_activity=False,
                    activity_summary=None,
                    activity_due_date=None,
                    activity_user_id=None):

        image_binary = base64.b64decode(image.split(',')[1])
        base_binary = base64.b64decode(base_image.split(',')[1]) if base_image else image_binary

        filename = filename or 'markup.jpg'
        default_note = f"{filename} - Markup Logged"

        Activity = request.env['mail.activity'].sudo()
        ActivityType = request.env['mail.activity.type'].sudo()
        IrModel = request.env['ir.model'].sudo()

        activity_type = ActivityType.search([('name', 'ilike', 'to')], limit=1)
        activity_type_id = activity_type.id if activity_type else 1

        markup_log = request.env['plm.markup.log'].sudo().create({
            'comment': comment,
            'snapshot': base64.b64encode(image_binary),
            'base_image': base64.b64encode(base_binary),
            'filename': filename,
            'canvas_data': canvas_json,
            'res_id': int(res_id) if res_id else 0,
            'res_model': res_model or '',
        })

        if res_model and res_id:
            record = request.env[res_model].sudo().browse(int(res_id))

            if record.exists():
                viewer_url = (
                    f"/plm/show_treejs_model"
                    f"?document_id={res_id}"
                    f"&document_name={record.name}"
                    f"&markup_id={markup_log.id}"
                )
                hyperlink = f'<p><a href="{viewer_url}" target="_blank">🔗 click here to View document in 3D Viewer</a></p>'

                components = _resolve_components(record)

                if schedule_activity:
                    attachment = request.env['ir.attachment'].sudo().create({
                        'name': filename,
                        'type': 'binary',
                        'datas': base64.b64encode(image_binary).decode(),
                        'res_model': res_model,
                        'res_id': int(res_id),
                        'mimetype': 'image/jpeg',
                    })

                    note_html = f'<p>{comment if comment else default_note}</p>'
                    note_html += hyperlink
                    note_html += (
                        f'<p><img src="/web/image/ir.attachment/{attachment.id}/datas" '
                        f'style="max-width:500px; border-radius:4px; margin-top:6px;" '
                        f'alt="Markup"/></p>'
                    )

                    created_targets = set()

                    def create_activity(target):
                        key = (target._name, target.id)
                        if key in created_targets:
                            return
                        created_targets.add(key)
                        model_rec = IrModel.search([('model', '=', target._name)], limit=1)
                        if model_rec:
                            Activity.create({
                                'res_model_id': model_rec.id,
                                'res_id': target.id,
                                'activity_type_id': activity_type_id,
                                'summary': activity_summary or 'Markup Activity',
                                'note': Markup(note_html),
                                'user_id': int(activity_user_id) if activity_user_id else request.env.user.id,
                                'date_deadline': activity_due_date or False,
                            })

                    create_activity(record)
                    for component in components:
                        target = component
                        if component._name == 'product.product' and component.product_tmpl_id:
                            target = component.product_tmpl_id
                        create_activity(target)

                else:
                    chatter_body = f'<p>{comment if comment else default_note}</p>'
                    chatter_body += hyperlink

                    try:
                        msg = record.message_post(
                            body=Markup(chatter_body),
                            attachments=[(filename, image_binary)]
                        )
                        markup_log.sudo().write({'message_id': msg.id})
                        for component in components:
                            component.message_post(
                                body=Markup(chatter_body),
                                attachments=[(filename, image_binary)],
                            )
                    except Exception as e:
                        _logger.warning("Failed to post markup chatter message: %s", e)

        return {"success": True, "markup_id": markup_log.id}

    @http.route('/plm/markup/load', type='jsonrpc', auth='user')
    def load_markup(self, res_id=None, res_model=None):
        domain = []
        if res_id:
            domain.append(('res_id', '=', int(res_id)))
        if res_model:
            domain.append(('res_model', '=', res_model))

        logs = request.env['plm.markup.log'].sudo().search(domain, order='create_date desc')

        return {
            'markups': [{
                'id': l.id,
                'comment': l.comment,
                'filename': l.filename or 'markup.jpg',
                'snapshot': l.snapshot.decode() if l.snapshot else False,
                'base_image': l.base_image.decode() if l.base_image else False,
                'canvas_data': l.canvas_data,
                'create_date': str(l.create_date),
            } for l in logs]
        }

    @http.route('/plm/markup/delete', type='jsonrpc', auth='user')
    def delete_markup(self, markup_id=None):
        if not markup_id:
            return {'success': False}

        log = request.env['plm.markup.log'].sudo().browse(int(markup_id))
        if not log.exists():
            return {'success': False}

        user = request.env.user
        is_creator = log.create_uid.id == user.id
        is_admin = user.has_group('plm.group_plm_admin')

        if not (is_creator or is_admin):
            return {'success': False}

        if log.message_id:
            log.message_id.sudo().unlink()
        log.sudo().unlink()

        return {'success': True}

    @http.route('/plm/markup/addon', type='jsonrpc', auth='user')
    def load_markup_addon(self, markup_id=None):
        if not markup_id:
            return {'markup': False}

        log = request.env['plm.markup.log'].sudo().browse(int(markup_id))
        if not log.exists():
            return {'markup': False}

        return {
            'markup': {
                'id': log.id,
                'comment': log.comment,
                'snapshot': log.snapshot.decode() if log.snapshot else False,
                'base_image': log.base_image.decode() if log.base_image else False,
                'canvas_data': log.canvas_data,
            }
        }

    @http.route('/plm/markup/update', type='jsonrpc', auth='user')
    def update_markup(self, markup_id, image, base_image, canvas_json, **kwargs):
        if not markup_id:
            return {'success': False}

        log = request.env['plm.markup.log'].sudo().browse(int(markup_id))
        if not log.exists():
            return {'success': False}

        user = request.env.user
        is_creator = log.create_uid.id == user.id
        is_admin = user.has_group('plm.group_plm_admin')

        if not (is_creator or is_admin):
            return {'success': False, 'error': 'Not allowed'}

        image_binary = base64.b64decode(image.split(',')[1] if ',' in image else image)
        base_binary = base64.b64decode(base_image.split(',')[1] if base_image and ',' in base_image else base_image)

        log.sudo().write({
            'snapshot': base64.b64encode(image_binary),
            'base_image': base64.b64encode(base_binary),
            'canvas_data': canvas_json,
        })

        # ── Post updated markup to chatter ──
        if log.res_model and log.res_id:
            record = request.env[log.res_model].sudo().browse(log.res_id)
            if record.exists():
                filename = log.filename or 'markup.jpg'
                chatter_body = f'<p>Markup updated by {user.name}</p>'

                viewer_url = (
                    f"/plm/show_treejs_model"
                    f"?document_id={log.res_id}"
                    f"&document_name={record.name}"
                    f"&markup_id={log.id}"
                )
                chatter_body += f'<p><a href="{viewer_url}" target="_blank">🔗 Click here to view updated markup in 3D Viewer</a></p>'

                components = _resolve_components(record)

                try:
                    record.message_post(
                        body=Markup(chatter_body),
                        attachments=[(filename, image_binary)],
                    )
                    for component in components:
                        component.message_post(
                            body=Markup(chatter_body),
                            attachments=[(filename, image_binary)],
                        )
                except Exception as e:
                    _logger.warning("Failed to post update_markup chatter message: %s", e)

        return {'success': True}
