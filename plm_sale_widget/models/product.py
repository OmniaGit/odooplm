import os
from urllib.parse import urlsplit

from odoo import _, fields, models
from odoo.exceptions import UserError

# The 3D web formats the sales are shown, first found first: one 3D button,
# no choice of format (the sales are not technical)
WEB3D_PRIORITY = (".3mf", ".obj", ".stl")


def _image_unique(record):
    """The write date of the product when it has an image, False otherwise."""
    if record.with_context(bin_size=True).image_128:
        return fields.Datetime.to_string(record.write_date)
    return False


def _relative_url(url):
    """The url without its host, so it opens on the server the user is on."""
    parts = urlsplit(url)
    return parts.path + ("?" + parts.query if parts.query else "")


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _plm_sale_readable(self, documents):
        """The documents the user reads as themselves, as the viewer and the
        printout routes do: a button the route would refuse is not shown."""
        if not documents:
            return documents
        return self.env["ir.attachment"].search(
            [("id", "in", documents.ids), ("is_plm", "=", True)]
        )

    def _plm_sale_linked_documents(self):
        """The documents of the product and the 3D web files of those
        documents (Web3DTree children), read under sudo: only to choose."""
        documents = self.sudo().linkeddocuments
        web_files = (
            self.env["ir.attachment.relation"]
            .sudo()
            .search(
                [
                    ("parent_id", "in", documents.ids),
                    ("link_kind", "=", "Web3DTree"),
                ]
            )
            .child_id
        )
        return documents | web_files

    def _plm_sale_web3d_document(self):
        """The 3D web model shown to the sales: the first by WEB3D_PRIORITY
        (the latest one when several share the format). A native CAD file is
        never one of them."""
        candidates = self._plm_sale_readable(
            self._plm_sale_linked_documents().filtered(
                lambda doc: os.path.splitext(doc.name or "")[1].lower()
                in WEB3D_PRIORITY
            )
        )
        for extension in WEB3D_PRIORITY:
            found = candidates.filtered(
                lambda doc: os.path.splitext(doc.name or "")[1].lower() == extension
            )
            if found:
                return found.sorted("id", reverse=True)[:1]
        return self.env["ir.attachment"]

    def _plm_sale_pdf_document(self):
        """The printout shown to the sales: a drawing with its PDF, the same
        condition as the portal (res.users._plm_portal_document_policy);
        the first one when there are several."""
        policy = self.env["res.users"]._plm_portal_document_policy
        drawings = self.sudo().linkeddocuments.filtered(lambda doc: "pdf" in policy(doc))
        return self._plm_sale_readable(drawings).sorted("id")[:1]

    def _plm_sale_documents_info(self):
        """The 3D model and the PDF of these products (the variants of one
        template, or one product), by id and name only."""
        web3d = self._plm_sale_web3d_document()
        pdf = self._plm_sale_pdf_document()
        return {
            "web3d": {"id": web3d.id, "name": web3d.sudo().name} if web3d else False,
            "pdf": {"id": pdf.id, "name": pdf.sudo().printout_name or pdf.sudo().name}
            if pdf
            else False,
        }

    def _plm_sale_open_3d(self):
        document = self._plm_sale_web3d_document()
        url = document.get_url_for_3dWebModel() if document else False
        if not url:
            raise UserError(_("This product has no 3D model to show."))
        return {"type": "ir.actions.act_url", "url": _relative_url(url), "target": "new"}

    def _plm_sale_open_pdf(self):
        document = self._plm_sale_pdf_document()
        if not document:
            raise UserError(_("This product has no PDF to show."))
        return {
            "type": "ir.actions.act_url",
            "url": _relative_url(document.getPrintoutUrl()),
            "target": "new",
        }

    def get_plm_sale_documents(self):
        """What the sales widget shows for the product: the image, the 3D
        model and the PDF."""
        self.ensure_one()
        return {"unique": _image_unique(self), **self._plm_sale_documents_info()}

    def action_plm_sale_open_3d(self):
        self.ensure_one()
        return self._plm_sale_open_3d()

    def action_plm_sale_open_pdf(self):
        self.ensure_one()
        return self._plm_sale_open_pdf()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # the documents are linked to the variants (linkeddocuments of the
    # template is related to product_variant_ids); the image is the template's

    def get_plm_sale_documents(self):
        self.ensure_one()
        return {
            "unique": _image_unique(self),
            **self.product_variant_ids._plm_sale_documents_info(),
        }

    def action_plm_sale_open_3d(self):
        self.ensure_one()
        return self.product_variant_ids._plm_sale_open_3d()

    def action_plm_sale_open_pdf(self):
        self.ensure_one()
        return self.product_variant_ids._plm_sale_open_pdf()
