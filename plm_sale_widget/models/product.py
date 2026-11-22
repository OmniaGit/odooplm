import os
from urllib.parse import urlsplit

from odoo import _, fields, models
from odoo.exceptions import UserError

# The 3D file the sales open, first found by this order: the .glb of
# CoreBomGLTF (OmniaGLTFConverter) first. The sales are not technical, so they
# get one 3D button, never a choice of formats (Matteo, 2026-11-22).
WEB3D_PRIORITY = (".glb", ".3mf", ".obj", ".stl")


def _extension(document):
    return os.path.splitext(document.name or "")[1].lower()


def _relative_url(url):
    """The url without its host, so it opens on the server the user is on."""
    parts = urlsplit(url)
    return parts.path + ("?" + parts.query if parts.query else "")


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _plm_sale_web3d_document(self):
        """The 3D web file the sales open: the first by WEB3D_PRIORITY (then the
        oldest) among the linked documents and their Web3DTree children, which
        is where the CAD client and the GLB structure import put the .glb.
        Only web formats are candidates, so never a native CAD file; read as
        the user, as the viewer reads it, so a file the viewer would refuse
        is not offered."""
        documents = self.mapped("linkeddocuments")
        # the relations are read in sudo: only the ids of the children
        children = (
            self.env["ir.attachment.relation"]
            .sudo()
            .search([("parent_id", "in", documents.ids), ("link_kind", "=", "Web3DTree")])
            .child_id
        )
        candidates = self.env["ir.attachment"].search(
            [("id", "in", (documents.ids + children.ids)), ("is_plm", "=", True)]
        )
        candidates = candidates.filtered(lambda doc: _extension(doc) in WEB3D_PRIORITY)
        return candidates.sorted(
            lambda doc: (WEB3D_PRIORITY.index(_extension(doc)), doc.id)
        )[:1]

    def _plm_sale_pdf_document(self):
        """The drawing whose printout the sales open: the first (oldest)
        linked document of which res.users._plm_portal_document_policy allows
        the pdf, a 2D drawing with its printout; read as the user, as the
        printout route reads it."""
        policy = self.env.user._plm_portal_document_policy
        documents = self.mapped("linkeddocuments").filtered(lambda doc: "pdf" in policy(doc))
        return documents.sorted("id")[:1]

    def _plm_sale_documents(self, image_record):
        web3d = self._plm_sale_web3d_document()
        pdf = self._plm_sale_pdf_document()
        return {
            "unique": (
                fields.Datetime.to_string(image_record.write_date)
                if image_record.image_128
                else False
            ),
            "web3d": bool(web3d),
            "pdf": bool(pdf),
        }

    def get_plm_sale_documents(self):
        """What the sales widget shows for the product: whether it has an
        image, a 3D web model and a PDF; the files are opened by the actions
        below, which find them again on the server."""
        self.ensure_one()
        return self._plm_sale_documents(self)

    def action_plm_sale_open_3d(self):
        document = self._plm_sale_web3d_document()
        if not document:
            raise UserError(_("No 3D model is available for this product."))
        url = document.get_url_for_3dWebModel()
        if not url:
            raise UserError(_("No 3D model is available for this product."))
        return {"type": "ir.actions.act_url", "url": _relative_url(url), "target": "new"}

    def action_plm_sale_open_pdf(self):
        document = self._plm_sale_pdf_document()
        if not document:
            raise UserError(_("No PDF is available for this product."))
        return {
            "type": "ir.actions.act_url",
            "url": _relative_url(document.getPrintoutUrl()),
            "target": "new",
        }


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # the documents are linked to the variants (linkeddocuments of the
    # template is related to product_variant_ids); the image is the template's

    def get_plm_sale_documents(self):
        self.ensure_one()
        return self.product_variant_ids._plm_sale_documents(self)

    def action_plm_sale_open_3d(self):
        self.ensure_one()
        return self.product_variant_ids.action_plm_sale_open_3d()

    def action_plm_sale_open_pdf(self):
        self.ensure_one()
        return self.product_variant_ids.action_plm_sale_open_pdf()
