# -*- coding: utf-8 -*-
import base64
import functools
import json
from odoo import http
from odoo.http import Controller, route, request, Response


def webservice(f):
    @functools.wraps(f)
    def wrap(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception as e:
            return Response(response=str(e), status=500)

    return wrap


class Web3DView(Controller):
    @route("/plm/show_treejs_model", type="http", auth="public")
    @webservice
    def show_treejs_model(self, document_id, document_name):
        return request.render(
            "plm_web_3d.main_treejs_view",
            {"document_id": document_id, "document_name": document_name},
        )

    @route("/plm/download_treejs_model", type="http", auth="public")
    @webservice
    def download_treejs_model(self, document_id):
        for ir_attachment in (
            request.env["ir.attachment"].sudo().search([("id", "=", int(document_id))])
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
    def getProductInfo(self, document_id):
        out = {}
        for ir_attachment in (
            request.env["ir.attachment"].sudo().search([("id", "=", int(document_id))])
        ):
            if ir_attachment.has_web3d:
                document = """
                <li class="attribute_info"><b>Name:</b> %s</li>
                <li class="attribute_info"><b>Revision:</b> %s</li>
                <li class="attribute_info"><b>Description:</b> %s</li>
                """ % (
                    ir_attachment.engineering_code or ir_attachment.name,
                    ir_attachment.engineering_revision,
                    ir_attachment.engineering_state,
                )
                document = self.document_extra(document)
                out["document"] = document
                for component in ir_attachment.linkedcomponents:
                    components = """
                    <li class="attribute_info" id="linked_component_id" data-id=%s><b>Product Name:</b> %s</li>
                    <li class="attribute_info"><b>Product Revision:</b> %s</li>
                    <li class="attribute_info"><b>Description:</b> %s</li>
                    """ % (
                        component.id,
                        component.engineering_code,
                        component.engineering_revision,
                        component.name,
                    )
                    components = self.component_extra(components)
                    out["component"] = components
        return json.dumps(out)

    @route("/plm/get_3d_web_document_info", type="http", auth="user")
    @webservice
    def get_3d_web_document_info(self, src_name):
        src_name = src_name.split("(")[0]
        # this split is needed for solidwoks file the put the configuration
        # on the name filename(<configuration name>)description
        out = f"""<span>{src_name}</span>"""
        for ir_attachment in (
            request.env["ir.attachment"].sudo().search([
                "|", ("name", "ilike", src_name),
                ("engineering_code", "ilike", src_name)
            ])
        ):
            for product_product_id in ir_attachment.linkedcomponents:
                out = f"""
                <span title={product_product_id.name}>
                {product_product_id.engineering_code}
                Rev. {product_product_id.engineering_revision}
                </span>
                """
                break

        return out

    @http.route('/plm_web_3d/save_markup', type='json', auth='user')
    def save_markup(self, image=None, filename=None, comment=None,
                    res_model=None, res_id=None, canvas_json=None,
                    schedule_activity=False,
                    activity_summary=None,
                    activity_due_date=None,
                    activity_user_id=None):

        image_binary = base64.b64decode(image.split(',')[1])
        filename = filename or 'markup.jpg'

        Activity = request.env['mail.activity'].sudo()
        ActivityType = request.env['mail.activity.type'].sudo()
        IrModel = request.env['ir.model'].sudo()

        activity_type = ActivityType.search([('name', 'ilike', 'to')], limit=1)
        activity_type_id = activity_type.id if activity_type else 1

        if res_model and res_id:
            record = request.env[res_model].sudo().browse(int(res_id))

            if record.exists():

                if schedule_activity:

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
                                'note': comment or '',
                                'user_id': int(activity_user_id) if activity_user_id else request.env.user.id,
                                'date_deadline': activity_due_date or False,
                            })

                    # Main record
                    create_activity(record)

                    # Linked components
                    if hasattr(record, 'linkedcomponents') and record.linkedcomponents:
                        for component in record.linkedcomponents:
                            target = component
                            if component._name == 'product.product' and component.product_tmpl_id:
                                target = component.product_tmpl_id
                            create_activity(target)

                else:
                    # Post message with attachment
                    record.message_post(
                        body=comment or 'Markup added',
                        attachments=[(filename, image_binary)]
                    )

                    if hasattr(record, 'linkedcomponents') and record.linkedcomponents:
                        for component in record.linkedcomponents:
                            component.message_post(
                                body=comment or 'Markup added',
                                attachments=[(filename, image_binary)],
                            )

        # Save markup log
        request.env['plm.markup.log'].sudo().create({
            'comment': comment,
            'snapshot': base64.b64encode(image_binary),
            'filename': filename,
            'canvas_data': canvas_json,
            'res_id': int(res_id) if res_id else 0,
            'res_model': res_model or '',
        })

        return {"status": "ok"}


    @http.route('/plm/markup/load', type='json', auth='user')
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
                'snapshot': l.snapshot.decode() if l.snapshot else False,
                'canvas_data': l.canvas_data,
                'create_date': str(l.create_date),
            } for l in logs]
        }

    @http.route('/plm/markup/delete', type='json', auth='user')
    def delete_markup(self, markup_id=None):
        log = request.env['plm.markup.log'].sudo().browse(int(markup_id))
        if log.exists():
            log.unlink()
            return {'success': True}
        return {'success': False}
