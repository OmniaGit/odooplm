import base64
import functools
import json

from markupsafe import Markup

from odoo import http
from odoo.http import Controller, Response, request, route


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
    def get_3d_web_document_info(self, src_name, parent_id=None):
        if not parent_id or not str(parent_id).isdigit():
            return src_name

        parent_doc = request.env["ir.attachment"].sudo().browse(int(parent_id))
        if not parent_doc.exists():
            return src_name

        if parent_doc.linkedcomponents:
            p = parent_doc.linkedcomponents[0]
            code = p.engineering_code or ""
            name = p.name or ""
            if code:
                return f"{code} - {name}"
            return name
        # we can here manage the name of the document by parent_doc.
        return src_name

    @http.route("/plm_web_3d/save_markup", type="json", auth="user")
    def save_markup(
        self,
        image=None,
        base_image=None,
        filename=None,
        comment=None,
        res_model=None,
        res_id=None,
        canvas_json=None,
        schedule_activity=False,
        activity_summary=None,
        activity_due_date=None,
        activity_user_id=None,
    ):

        image_binary = base64.b64decode(image.split(",")[1])
        base_binary = (
            base64.b64decode(base_image.split(",")[1]) if base_image else image_binary
        )

        filename = filename or "markup.jpg"
        default_note = f"{filename} - Markup Logged"

        Activity = request.env["mail.activity"].sudo()
        ActivityType = request.env["mail.activity.type"].sudo()
        IrModel = request.env["ir.model"].sudo()

        activity_type = ActivityType.search([("name", "ilike", "to")], limit=1)
        activity_type_id = activity_type.id if activity_type else 1

        markup_log = (
            request.env["plm.markup.log"]
            .sudo()
            .create(
                {
                    "comment": comment,
                    "snapshot": base64.b64encode(image_binary),
                    "base_image": base64.b64encode(base_binary),
                    "filename": filename,
                    "canvas_data": canvas_json,
                    "res_id": int(res_id) if res_id else 0,
                    "res_model": res_model or "",
                }
            )
        )

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

                has_components = (
                    hasattr(record, "linkedcomponents") and record.linkedcomponents
                )

                if schedule_activity:
                    attachment = (
                        request.env["ir.attachment"]
                        .sudo()
                        .create(
                            {
                                "name": filename,
                                "type": "binary",
                                "datas": base64.b64encode(image_binary).decode(),
                                "res_model": res_model,
                                "res_id": int(res_id),
                                "mimetype": "image/jpeg",
                            }
                        )
                    )

                    note_html = f"<p>{comment if comment else default_note}</p>"
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
                        model_rec = IrModel.search(
                            [("model", "=", target._name)], limit=1
                        )
                        if model_rec:
                            Activity.create(
                                {
                                    "res_model_id": model_rec.id,
                                    "res_id": target.id,
                                    "activity_type_id": activity_type_id,
                                    "summary": activity_summary or "Markup Activity",
                                    "note": Markup(note_html),
                                    "user_id": (
                                        int(activity_user_id)
                                        if activity_user_id
                                        else request.env.user.id
                                    ),
                                    "date_deadline": activity_due_date or False,
                                }
                            )

                    if has_components:
                        for component in record.linkedcomponents:
                            target = component
                            if (
                                component._name == "product.product"
                                and component.product_tmpl_id
                            ):
                                target = component.product_tmpl_id
                            create_activity(target)
                    else:
                        create_activity(record)

                else:
                    chatter_body = f"<p>{comment if comment else default_note}</p>"
                    chatter_body += hyperlink

                    if has_components:
                        for component in record.linkedcomponents:
                            msg = component.message_post(
                                body=Markup(chatter_body),
                                attachments=[(filename, image_binary)],
                            )
                            if not markup_log.message_id:
                                markup_log.sudo().write({"message_id": msg.id})
                    else:
                        msg = record.message_post(
                            body=Markup(chatter_body),
                            attachments=[(filename, image_binary)],
                        )
                        markup_log.sudo().write({"message_id": msg.id})

        return {"status": "ok"}

    @http.route("/plm/markup/load", type="json", auth="user")
    def load_markup(self, res_id=None, res_model=None):
        domain = []
        if res_id:
            domain.append(("res_id", "=", int(res_id)))
        if res_model:
            domain.append(("res_model", "=", res_model))

        logs = (
            request.env["plm.markup.log"]
            .sudo()
            .search(domain, order="create_date desc")
        )

        return {
            "markups": [
                {
                    "id": l.id,
                    "comment": l.comment,
                    "filename": l.filename or "markup.jpg",
                    "snapshot": l.snapshot.decode() if l.snapshot else False,
                    "base_image": l.base_image.decode() if l.base_image else False,
                    "canvas_data": l.canvas_data,
                    "create_date": str(l.create_date),
                }
                for l in logs
            ]
        }

    @http.route("/plm/markup/delete", type="json", auth="user")
    def delete_markup(self, markup_id=None):
        if not markup_id:
            return {"success": False}

        log = request.env["plm.markup.log"].sudo().browse(int(markup_id))
        if not log.exists():
            return {"success": False}

        user = request.env.user
        is_creator = log.create_uid.id == user.id
        is_admin = user.has_group("plm.group_plm_admin")

        if not (is_creator or is_admin):
            return {"success": False}

        if log.message_id:
            log.message_id.sudo().unlink()
        log.sudo().unlink()

        return {"success": True}

    @http.route("/plm_web_3d/markup/addon", type="json", auth="user")
    def load_markup_addon(self, markup_id=None):
        if not markup_id:
            return {"markup": False}

        log = request.env["plm.markup.log"].sudo().browse(int(markup_id))
        if not log.exists():
            return {"markup": False}

        return {
            "markup": {
                "id": log.id,
                "comment": log.comment,
                "snapshot": log.snapshot.decode() if log.snapshot else False,
                "base_image": log.base_image.decode() if log.base_image else False,
                "canvas_data": log.canvas_data,
            }
        }

    @http.route("/plm/markup/update", type="json", auth="user")
    def update_markup(self, markup_id, image, base_image, canvas_json, **kwargs):
        if not markup_id:
            return {"success": False}

        log = request.env["plm.markup.log"].sudo().browse(int(markup_id))
        if not log.exists():
            return {"success": False}

        user = request.env.user
        is_creator = log.create_uid.id == user.id
        is_admin = user.has_group("plm.group_plm_admin")

        if not (is_creator or is_admin):
            return {"success": False, "error": "Not allowed"}

        image_binary = base64.b64decode(image.split(",")[1] if "," in image else image)
        base_binary = base64.b64decode(
            base_image.split(",")[1] if base_image and "," in base_image else base_image
        )

        log.sudo().write(
            {
                "snapshot": base64.b64encode(image_binary),
                "base_image": base64.b64encode(base_binary),
                "canvas_data": canvas_json,
            }
        )

        # ── Post updated markup to chatter ──
        if log.res_model and log.res_id:
            record = request.env[log.res_model].sudo().browse(log.res_id)
            if record.exists():
                filename = log.filename or "markup.jpg"
                chatter_body = f"<p>Markup updated by {user.name}</p>"

                viewer_url = (
                    f"/plm/show_treejs_model"
                    f"?document_id={log.res_id}"
                    f"&document_name={record.name}"
                    f"&markup_id={log.id}"
                )
                chatter_body += f'<p><a href="{viewer_url}" target="_blank">🔗 Click here to view updated markup in 3D Viewer</a></p>'

                has_components = (
                    hasattr(record, "linkedcomponents") and record.linkedcomponents
                )

                if has_components:
                    for component in record.linkedcomponents:
                        component.message_post(
                            body=Markup(chatter_body),
                            attachments=[(filename, image_binary)],
                        )
                else:
                    record.message_post(
                        body=Markup(chatter_body),
                        attachments=[(filename, image_binary)],
                    )

        return {"success": True}
