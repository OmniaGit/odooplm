# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2026 OmniaSolutions (<http://www.omniasolutions.eu>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""Build the demo PLM environment from ``data/dataset.json`` and ``files/``.

The dataset is loaded through the ORM rather than declared in XML: the payloads
are real CAD files kept as files on disk (no base64 bloat in the repository), and
records such as 3D markups have to be created in a specific order so their chatter
links point at the right ids.

Every record gets an external id, so uninstalling the module removes the demo data.
Re-running the hook is safe: records that already exist are left alone.

The dataset is produced by ``tools/export_demo.py`` — do not edit it by hand.
"""
import base64
import json
import logging
import os
from urllib.parse import quote

from odoo import fields

_logger = logging.getLogger(__name__)

MODULE = "plm_demo"
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "data", "dataset.json")
CURATED_CHATTER = os.path.join(HERE, "data", "curated_chatter.json")
LIFECYCLE = os.path.join(HERE, "data", "lifecycle.json")
FILES = os.path.join(HERE, "files")

VIEWER_LINK = (
    '<p>%(comment)s</p>'
    '<p><a href="/plm/show_treejs_model?document_id=%(document_id)s'
    '&amp;document_name=%(document_name)s&amp;markup_id=%(markup_id)s" '
    'target="_blank">🔗 click here to View document in 3D Viewer</a></p>'
)


def _read(*path):
    with open(os.path.join(FILES, *path), "rb") as fh:
        return fh.read()


def _b64(*path):
    return base64.b64encode(_read(*path))


class DemoLoader:
    def __init__(self, env):
        self.env = env
        self.refs = {}

    # ------------------------------------------------------------------ helpers
    def _xmlid(self, name):
        return "%s.%s" % (MODULE, name)

    def _existing(self, name):
        return self.env.ref(self._xmlid(name), raise_if_not_found=False)

    def _register(self, name, record):
        self.env["ir.model.data"]._update_xmlids([{
            "xml_id": self._xmlid(name),
            "record": record,
            "noupdate": True,
        }])
        self.refs[name] = record
        return record

    def _get(self, name):
        if name not in self.refs:
            self.refs[name] = self._existing(name)
        return self.refs[name]

    # ------------------------------------------------------------------- loaders
    def load_products(self, products):
        created = 0
        for p in products:
            if self._existing(p["xml_id"]):
                continue
            values = {
                "name": p["name"],
                "default_code": p["default_code"],
                "engineering_code": p["engineering_code"],
                "engineering_revision": p["engineering_revision"],
                "engineering_state": p["engineering_state"] or "draft",
                "type": p["type"] or "consu",
                "is_storable": bool(p["is_storable"]),
                "weight": p["weight"] or 0.0,
            }
            for optional in ("engineering_revision_letter", "engineering_material",
                             "engineering_surface", "engineering_treatment",
                             "description"):
                if p.get(optional):
                    values[optional] = p[optional]
            if p.get("image"):
                values["image_1920"] = _b64("images", p["image"])
            self._register(p["xml_id"], self.env["product.template"].create(values))
            created += 1
        _logger.info("plm_demo: %s parts created", created)

    def load_boms(self, boms):
        created = 0
        for b in boms:
            if self._existing(b["xml_id"]):
                continue
            template = self._get(b["product"])
            if not template:
                continue
            lines = []
            for line in b["lines"]:
                component = self._get(line["product"])
                if not component:
                    continue
                values = {
                    "product_id": component.product_variant_id.id,
                    "product_qty": line["qty"],
                    "sequence": line["sequence"] or 1,
                }
                # the balloon the component carries on the assembly drawing; the
                # CAD client fills the same field on check-in
                if line.get("itemnum"):
                    values["itemnum"] = line["itemnum"]
                    values["itemlbl"] = str(line["itemnum"])
                lines.append((0, 0, values))
            if not lines:
                continue
            self._register(b["xml_id"], self.env["mrp.bom"].create({
                "product_tmpl_id": template.id,
                "type": b["type"] or "normal",
                "code": b["code"] or False,
                "product_qty": b["product_qty"] or 1.0,
                "bom_line_ids": lines,
            }))
            created += 1
        _logger.info("plm_demo: %s bills of material created", created)

    def load_documents(self, documents):
        created = 0
        for d in documents:
            if self._existing(d["xml_id"]):
                continue
            values = {
                "name": d["name"],
                "datas": _b64("documents", d["file"]),
                "document_type": d["document_type"] or "other",
                "engineering_code": d["engineering_code"] or d["name"],
                "engineering_revision": d["engineering_revision"] or 0,
                "engineering_state": d["engineering_state"] or "draft",
                "is_library": bool(d["is_library"]),
            }
            if d.get("mimetype"):
                values["mimetype"] = d["mimetype"]
            if d.get("engineering_revision_letter"):
                values["engineering_revision_letter"] = d["engineering_revision_letter"]
            if d.get("desc_modify"):
                values["desc_modify"] = d["desc_modify"]
            if d.get("preview"):
                values["preview"] = _b64("previews", d["preview"])
            # a 2D document carries its printable sheet in printout, the way the
            # CAD client publishes it; the file is not a document of its own
            if d.get("printout"):
                values["printout"] = _b64("documents", d["printout"])
            # plm_spare prints the documents flagged here in the Spare Parts Manual
            if d.get("used_for_spare"):
                values["used_for_spare"] = True
            # The odooPLM context is what the CAD client uses: it flags the
            # attachment as a PLM document (is_plm), attaches it to the PLM access
            # model and runs the uniqueness checks. Without it the document is a
            # plain attachment and every PLM record rule filters it out.
            document = self.env["ir.attachment"].with_context(odooPLM=True).create(values)

            components = self.env["product.product"]
            for part in d["linked_products"]:
                template = self._get(part)
                if template:
                    components |= template.product_variant_id
            if components:
                document.write({"linkedcomponents": [(6, 0, components.ids)]})

            self._register(d["xml_id"], document)
            created += 1
        _logger.info("plm_demo: %s engineering documents created", created)

    def load_document_relations(self, relations):
        created = 0
        for r in relations:
            parent, child = self._get(r["parent"]), self._get(r["child"])
            if not parent or not child:
                continue
            existing = self.env["ir.attachment.relation"].search([
                ("parent_id", "=", parent.id), ("child_id", "=", child.id),
            ], limit=1)
            if existing:
                continue
            self.env["ir.attachment.relation"].create({
                "parent_id": parent.id,
                "child_id": child.id,
                "link_kind": r["link_kind"] or "HiTree",
            })
            created += 1
        _logger.info("plm_demo: %s document relations created", created)

    def load_markups(self, markups):
        """3D markups plus the chatter message each one produced.

        The markup is created first so the message body can link to it, then the
        message is attached back to the markup — which is the order the viewer
        itself uses.
        """
        created = 0
        for m in markups:
            if self._existing(m["xml_id"]):
                continue
            document = self._get(m["document"])
            if not document:
                continue
            values = {
                "res_model": "ir.attachment",
                "res_id": document.id,
                "comment": m["comment"],
                "filename": m["filename"],
                "canvas_data": m["canvas_data"],
            }
            if m.get("base_image"):
                values["base_image"] = _b64("markups", m["base_image"])
            markup = self.env["plm.markup.log"].create(values)
            message = document.message_post(
                body=VIEWER_LINK % {
                    "comment": m["comment"],
                    "document_id": document.id,
                    "document_name": quote(document.name or ""),
                    "markup_id": markup.id,
                },
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            markup.message_id = message.id
            self._register(m["xml_id"], markup)
            created += 1
        _logger.info("plm_demo: %s 3D markups created", created)

    def load_chatter(self, messages):
        posted = 0
        for m in messages:
            record = self._get(m["target"])
            if not record:
                continue
            if m["model"] == "ir.attachment":
                target = record
            else:
                target = record  # product.template
            body = m["body"]
            if any(body == existing.body for existing in target.message_ids):
                continue
            target.message_post(body=body, message_type="comment",
                                subtype_xmlid="mail.mt_comment")
            posted += 1
        _logger.info("plm_demo: %s chatter messages posted", posted)

    # ------------------------------------------------------------- lifecycle
    # dataset.json describes records; lifecycle.json describes what happens to
    # them. Everything below goes through the same api the buttons and the CAD
    # client use, so the demo shows the workflow behaving, not states written
    # into the database by hand.

    WORKFLOW_ACTIONS = {
        "confirm": "action_confirm",
        "release": "action_release",
        "draft": "action_draft",
        "obsolete": "action_obsolete",
    }

    def _part(self, name):
        """The product.product behind a dataset entry, which registers templates.

        The engineering workflow and the revision api live on the variant, not
        on the template.
        """
        template = self._get(name)
        return template.product_variant_id if template else None

    def _step_workflow(self, step):
        part = self._part(step["part"])
        if not part:
            return False
        getattr(part, self.WORKFLOW_ACTIONS[step["action"]])()
        return True

    def _step_part_revision(self, step):
        """A new revision of a part, plus new revisions of its documents.

        ``NewRevision`` clears the linked documents of the new revision — the CAD
        client attaches them again when it checks the new geometry in — so the
        documents are revised here and linked back.
        """
        if self._existing(step["xml_id"]):
            return False
        part = self._part(step["part"])
        if not part:
            return False

        new_id, revision = part.NewRevision()
        if not new_id:
            _logger.warning("plm_demo: no revision created for %s", step["part"])
            return False
        new_part = self.env["product.product"].browse(new_id)
        if step.get("desc_modify"):
            new_part.desc_modify = step["desc_modify"]
        # the dataset registers templates, so the revision is registered the
        # same way and the uninstall hook takes it down with the rest
        self._register(step["xml_id"], new_part.product_tmpl_id)

        documents = self.env["ir.attachment"]
        for spec in step.get("documents", []):
            if self._existing(spec["xml_id"]):
                continue
            document = self._get(spec["document"])
            if not document:
                continue
            new_doc_id, _revision = document.NewRevision(document.id)
            if not new_doc_id:
                continue
            new_document = self.env["ir.attachment"].browse(new_doc_id)
            if step.get("desc_modify"):
                new_document.desc_modify = step["desc_modify"]
            documents |= new_document
            self._register(spec["xml_id"], new_document)

        if documents:
            documents.write({"linkedcomponents": [(6, 0, [new_part.id])]})
        _logger.info(
            "plm_demo: %s revision %s created with %s documents",
            new_part.engineering_code, revision, len(documents),
        )
        return True

    def _activity(self, step, is_eco):
        """An ECR or an ECO on a part: activity_validation extends mail.activity."""
        part = self._part(step["part"])
        if not part:
            return None
        model = self.env["ir.model"]._get("product.product")
        activity = self.env["mail.activity"].create({
            "activity_type_id": self.env.ref(
                "activity_validation.mail_activity_change_request"
            ).id,
            "res_model_id": model.id,
            "res_id": part.id,
            "user_id": self.env.uid,
            "date_deadline": fields.Date.context_today(part),
            "summary": step["name"],
            "name": step["name"],
            "note": step["note"],
        })
        # action_in_progress returns the action that reopens the activity form;
        # here only its side effect matters
        activity.action_in_progress()
        if is_eco:
            activity.action_to_eco()
        return activity

    def _step_change_request(self, step):
        if step.get("xml_id") and self._existing(step["xml_id"]):
            return False
        activity = self._activity(step, is_eco=False)
        if not activity:
            return False
        if step.get("close"):
            # action_to_done posts the message and archives the activity —
            # _action_done ends on action_archive(), it does not delete. The
            # record survives with plm_state 'done', so it is registered like
            # any other and the uninstall hook takes it down.
            activity.action_to_done()
        if step.get("xml_id"):
            self._register(step["xml_id"], activity)
        return True

    def _step_change_order(self, step):
        if step.get("xml_id") and self._existing(step["xml_id"]):
            return False
        activity = self._activity(step, is_eco=True)
        if not activity:
            return False
        if step.get("xml_id"):
            self._register(step["xml_id"], activity)
        return True

    def _step_checkout(self, step):
        document = self._get(step["document"])
        if not document:
            return False
        if self.env["plm.checkout"].search([("documentid", "=", document.id)], limit=1):
            return False
        self.env["plm.checkout"].create({
            "documentid": document.id,
            "userid": self.env.uid,
            "hostname": step.get("hostname") or "",
            "hostpws": step.get("pws") or "",
        })
        return True

    def load_lifecycle(self, steps):
        handlers = {
            "workflow": self._step_workflow,
            "part_revision": self._step_part_revision,
            "change_request": self._step_change_request,
            "change_order": self._step_change_order,
            "checkout": self._step_checkout,
        }
        applied = 0
        for step in steps:
            handler = handlers.get(step["op"])
            if handler is None:
                _logger.warning("plm_demo: unknown lifecycle step %r", step["op"])
                continue
            if handler(step):
                applied += 1
        _logger.info("plm_demo: %s lifecycle steps applied", applied)

    # ----------------------------------------------------------------------- run
    def run(self):
        with open(DATASET) as fh:
            data = json.load(fh)
        self.load_products(data["products"])
        self.load_boms(data["boms"])
        self.load_documents(data["documents"])
        self.load_document_relations(data["document_relations"])
        self.load_markups(data.get("markups", []))

        messages = list(data.get("chatter", []))
        if os.path.exists(CURATED_CHATTER):
            with open(CURATED_CHATTER) as fh:
                messages += json.load(fh).get("chatter", [])
        self.load_chatter(messages)

        # last: the lifecycle runs the workflow over the records above, and a
        # released or checked out record is no longer freely writable
        if os.path.exists(LIFECYCLE):
            with open(LIFECYCLE) as fh:
                self.load_lifecycle(json.load(fh).get("steps", []))


def post_init_hook(env):
    _logger.info("plm_demo: building the demo PLM environment")
    DemoLoader(env).run()
    _logger.info("plm_demo: done")


def uninstall_hook(env):
    """Remove the demo records in an order the PLM checks accept.

    ``plm`` refuses to delete a document that is the child of another document, or
    a part that is still used in a bill of material — which is correct behaviour,
    but it makes the standard external id cleanup skip most of the demo data. This
    hook runs before that cleanup and takes the records down in dependency order.

    It only ever touches records carried by this module's external ids: nothing
    that belongs to the database itself is searched for, let alone deleted.
    """
    records = {}
    for data in env["ir.model.data"].search([("module", "=", MODULE)]):
        records.setdefault(data.model, []).append(data.res_id)

    def demo(model):
        return env[model].browse(records.get(model, [])).exists()

    demo("mrp.bom").unlink()            # frees the parts used in their lines
    demo("plm.markup.log").unlink()
    demo("mail.activity").unlink()      # the open change order
    # a checked out document is flagged as being edited elsewhere; the checkout
    # goes first so the document is releasable again
    demo("plm.checkout").unlink()

    # The lifecycle leaves records released, obsoleted or under modification,
    # and those states are write protected — which would make the deletion below
    # fail on exactly the records the lifecycle created. check=False is the same
    # escape hatch action_un_release uses in the core.
    for model in ("ir.attachment", "product.template"):
        protected = demo(model)
        if protected:
            protected.with_context(check=False).write({"engineering_state": "draft"})

    documents = demo("ir.attachment")
    if documents:
        # document to document links block the deletion of the child document
        env["ir.attachment.relation"].search([
            "|", ("parent_id", "in", documents.ids), ("child_id", "in", documents.ids),
        ]).unlink()
        # the document/part table keeps a plain foreign key on the document, so the
        # links have to go before the documents themselves
        documents.write({"linkedcomponents": [(5, 0, 0)]})
        documents.unlink()

    demo("product.template").unlink()
    _logger.info("plm_demo: demo data removed")
