import io
import zipfile

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class PortalPurchaseDownload(CustomerPortal):

    @http.route(
        "/my/purchase/<int:order_id>/download_docs",
        type="http",
        auth="user",
        website=True,
    )
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

        zip_buffer = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED)

        report_action = request.env.ref("plm.report_product_product_pdf_latest").sudo()

        Report = request.env["ir.actions.report"].sudo()

        for line in order.order_line:
            product = line.product_id
            if not product:
                continue

            html_content, _ = report_action._render_qweb_html(
                "plm.report_product_product_pdf_latest", product.id
            )

            wrapped_html = f"""
                            <html>
                                <main>
                                    {html_content}
                                </main>
                            </html>
                        """

            bodies = Report._prepare_html(wrapped_html)[0]

            pdf_content = Report._run_wkhtmltopdf(bodies)

            filename = f"{product.display_name.replace('/', '_')}.pdf"
            zip_file.writestr(filename, pdf_content)

        zip_file.close()
        zip_buffer.seek(0)

        zip_filename = f"PO_{order.name}_Documents.zip"
        return request.make_response(
            zip_buffer.getvalue(),
            headers=[
                ("Content-Type", "application/zip"),
                ("Content-Disposition", f'attachment; filename="{zip_filename}"'),
            ],
        )
