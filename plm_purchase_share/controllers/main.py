# -*- coding: utf-8 -*-
import io
import logging
import zipfile

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from odoo.http import content_disposition, request

_logger = logging.getLogger(__name__)


def _printouts_pdf(documents):
    """The PDF of the drawings *documents*, read with sudo: the portal cannot
    read attachments, and the caller has already decided they are the user's
    to get (res.users._plm_portal_printouts)."""
    return request.env["report.plm.product_pdf"].sudo()._render_documents_pdf(
        documents
    )


def _pdf_file_name(product):
    return "%s.pdf" % product.sudo().display_name.replace("/", "_")


class PortalPurchaseDownload(CustomerPortal):

    @http.route(
        "/my/plm/product/<int:product_id>/pdf",
        type="http",
        auth="user",
        website=True,
    )
    def download_product_printouts(self, product_id, **kwargs):
        """The PDF of the drawings of one product, for a customer or a vendor.

        The backend report route (/report/html/...) renders as the user, and a
        portal user can read neither products nor attachments: this one asks
        the portal scope instead, and a product outside it answers like a
        missing one.
        """
        product = request.env["product.product"].sudo().browse(product_id).exists()
        documents = request.env.user._plm_portal_printouts(product)
        if not documents:
            _logger.warning(
                "/my/plm/product/pdf: user %s (id %s) asked for the drawings of "
                "the product %s, which does not exist or is not theirs to get",
                request.env.user.login,
                request.env.uid,
                product_id,
            )
            raise request.not_found()
        pdf = _printouts_pdf(documents)
        return request.make_response(
            pdf,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
                (
                    "Content-Disposition",
                    content_disposition(_pdf_file_name(product), "inline"),
                ),
            ],
        )

    @http.route('/my/purchase/<int:order_id>/download_docs', type='http', auth='user', website=True)
    def download_purchase_documents(self, order_id, access_token=None, **kwargs):
        # Enforce that the caller may actually see this order: portal record
        # rules for a logged-in owner, or a valid share access_token. Raises
        # AccessError/MissingError otherwise — never sudo-browse a raw id.
        try:
            order = self._document_check_access(
                "purchase.order", order_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        user = request.env.user
        scope = user._plm_portal_products()
        zip_buffer = io.BytesIO()
        file_count = 0
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for product in order.order_line.product_id:
                documents = user._plm_portal_printouts(product, scope)
                if not documents:
                    continue
                zip_file.writestr(_pdf_file_name(product), _printouts_pdf(documents))
                file_count += 1
        if not file_count:
            return request.redirect(order.get_portal_url())

        zip_filename = f"PO_{order.name}_Documents.zip"
        return request.make_response(
            zip_buffer.getvalue(),
            headers=[
                ('Content-Type', 'application/zip'),
                ('Content-Disposition', content_disposition(zip_filename)),
            ]
        )
