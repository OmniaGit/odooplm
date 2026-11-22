import os
from urllib.parse import urlsplit

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.plm.models.ir_attachment_relations import SUPPORT_LINK_KINDS

# 3D formats the web viewer of plm_web_3d shows (a STEP is converted to 3MF
# the first time it is opened); 2D formats (DXF, SVG) are left out
WEB3D_EXTENSIONS = (".3mf", ".gltf", ".glb", ".fbx", ".obj", ".wrl", ".stl", ".stp", ".step")


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

    def _plm_sale_web3d_documents(self):
        """The 3D web models the sales may open: support files only
        (conversions, 3D web models), never the native CAD files."""
        if not self.env.user.has_group("plm.group_plm_view_user"):
            # the 3D web viewer refuses the users without PLM view access
            return self.env["ir.attachment"]
        return self.linkeddocuments.filtered(
            lambda document: os.path.splitext(document.name or "")[1].lower()
            in WEB3D_EXTENSIONS
            and any(
                relation.link_kind in SUPPORT_LINK_KINDS
                for relation in document.parent_relation_ids
            )
        )

    def _plm_sale_pdf_documents(self):
        """The documents with a printout (the PDF of a drawing)."""
        return self.linkeddocuments.with_context(bin_size=True).filtered("printout")

    def get_plm_sale_documents(self):
        """What the sales widget shows for the product: the image, the 3D web
        models and the PDFs, by id and name only."""
        self.ensure_one()
        # sudo: only names are sent, the files are opened by the actions below
        product = self.sudo()
        return {
            "unique": _image_unique(self),
            "web3d": [
                {"id": document.id, "name": document.name}
                for document in product._plm_sale_web3d_documents()
            ],
            "pdf": [
                {"id": document.id, "name": document.printout_name or document.name}
                for document in product._plm_sale_pdf_documents()
            ],
        }

    def action_plm_sale_open_3d(self, document_id):
        self.ensure_one()
        document = self.sudo()._plm_sale_web3d_documents().filtered(
            lambda doc: doc.id == document_id
        )
        if not document:
            raise UserError(_("This 3D model is not available for this product."))
        # sudo: the 3MF of a STEP is created the first time, whoever opens it
        action = document.show_releted_3d()
        if not action or not action.get("url"):
            raise UserError(_("No 3D web model can be shown for %s.", document.name))
        return {
            "type": "ir.actions.act_url",
            "url": _relative_url(action["url"]),
            "target": "new",
        }

    def action_plm_sale_open_pdf(self, document_id):
        self.ensure_one()
        document = self.sudo()._plm_sale_pdf_documents().filtered(
            lambda doc: doc.id == document_id
        )
        if not document:
            raise UserError(_("This PDF is not available for this product."))
        return {
            "type": "ir.actions.act_url",
            "url": _relative_url(document.getPrintoutUrl()),
            "target": "new",
        }


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # the documents are linked to the variant (linkeddocuments of the template
    # is related to product_variant_id); the image is the template's own

    def get_plm_sale_documents(self):
        self.ensure_one()
        result = {"web3d": [], "pdf": []}
        if self.product_variant_id:
            result = self.product_variant_id.get_plm_sale_documents()
        result["unique"] = _image_unique(self)
        return result

    def action_plm_sale_open_3d(self, document_id):
        self.ensure_one()
        return self.product_variant_id.action_plm_sale_open_3d(document_id)

    def action_plm_sale_open_pdf(self, document_id):
        self.ensure_one()
        return self.product_variant_id.action_plm_sale_open_pdf(document_id)
