import io
import zipfile

from odoo import http
from odoo.http import request


class PortalPurchaseDownload(http.Controller):

    @http.route(
        "/my/purchase/<int:order_id>/download_docs",
        type="http",
        auth="public",
        website=True,
    )
    def download_purchase_documents(self, order_id, **kwargs):
        order = request.env["purchase.order"].sudo().browse(order_id)
        if not order or not order.exists():
            return request.not_found()

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
