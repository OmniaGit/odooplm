import base64

from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

# 1x1 pixel PNG
PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@tagged("post_install", "-at_install", "plm_sale_widget")
class TestSaleProductImage(HttpCase):
    """The product of a sale order line shows its image and one 3D and one PDF
    button; the native CAD files are never offered nor sent."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner = cls.env["res.partner"].create({"name": "PLM sale widget customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "PLM sale widget with image", "image_1920": PNG, "sale_ok": True}
        )
        cls.product_without_image = cls.env["product.product"].create(
            {"name": "PLM sale widget without image", "sale_ok": True}
        )
        # the native model, its drawing with the printout, and web files:
        # a .3mf and a .stl linked to the product, a .glb child of the model
        cls.native = cls._document("PLMSW-1.sldprt", cls.product)
        cls.drawing = cls._document("PLMSW-1.slddrw", cls.product, printout=True)
        cls.stl = cls._document("PLMSW-1.stl", cls.product)
        cls.web3mf = cls._document("PLMSW-1.3mf", cls.product)
        cls.glb = cls._document("PLMSW-1.glb")
        cls.env["ir.attachment.relation"].create(
            {"parent_id": cls.native.id, "child_id": cls.glb.id, "link_kind": "Web3DTree"}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (0, 0, {"product_id": cls.product.id, "product_uom_qty": 1}),
                    (0, 0, {"product_id": cls.product_without_image.id, "product_uom_qty": 1}),
                ],
            }
        )

    @classmethod
    def _document(cls, name, product=None, printout=False):
        document = cls.env["ir.attachment"].create(
            {
                "name": name,
                "engineering_code": name,
                "raw": b"content of " + name.encode(),
                "is_plm": True,
                "printout": PNG if printout else False,
            }
        )
        if product:
            document.linkedcomponents = product
        return document

    def test_one_3d_file_by_priority(self):
        # the .glb (a Web3DTree child of the native model) before .3mf and .stl
        self.assertEqual(self.product._plm_sale_web3d_document(), self.glb)
        self.env["ir.attachment.relation"].search([("child_id", "=", self.glb.id)]).unlink()
        self.assertEqual(self.product._plm_sale_web3d_document(), self.web3mf)
        self.web3mf.linkedcomponents = False
        self.assertEqual(self.product._plm_sale_web3d_document(), self.stl)

    def test_documents_for_the_sales(self):
        for product in (self.product, self.product.product_tmpl_id):
            info = product.get_plm_sale_documents()
            self.assertTrue(info["unique"])
            self.assertTrue(info["web3d"])
            self.assertTrue(info["pdf"])
        info = self.product_without_image.product_tmpl_id.get_plm_sale_documents()
        self.assertEqual(info, {"unique": False, "web3d": False, "pdf": False})

    def test_the_actions_open_web_files_and_printouts_only(self):
        action = self.product.product_tmpl_id.action_plm_sale_open_3d()
        self.assertTrue(action["url"].startswith("/plm/show_treejs_model?"))
        self.assertIn(f"document_id={self.glb.id}", action["url"])
        action = self.product.product_tmpl_id.action_plm_sale_open_pdf()
        self.assertEqual(action["url"], f"/plm/ir_attachment_printout/{self.drawing.id}")
        with self.assertRaises(UserError):
            self.product_without_image.action_plm_sale_open_3d()
        with self.assertRaises(UserError):
            self.product_without_image.action_plm_sale_open_pdf()

    def test_viewer_does_not_send_native_file(self):
        # has_web3d is true for the native model (it has a Web3DTree child)
        self.assertTrue(self.native.has_web3d)
        self.authenticate("admin", "admin")
        response = self.url_open(f"/plm/download_treejs_model?document_id={self.native.id}")
        self.assertEqual(response.status_code, 500)
        response = self.url_open(f"/plm/download_treejs_model?document_id={self.glb.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"content of PLMSW-1.glb")

    def test_order_line_buttons(self):
        code = """
          (async () => {
            const waitFor = async (selector) => {
                for (let i = 0; i < 100; i++) {
                    const node = document.querySelector(selector);
                    if (node) {
                        return node;
                    }
                    await new Promise((resolve) => setTimeout(resolve, 100));
                }
                throw new Error("not found: " + selector);
            };
            // Odoo 20 shows the product of the line in its description (label)
            const avatar = ".o_field_widget[name='label'] .plm_m2o_avatar";
            const image = await waitFor(avatar + " img");
            if (!image.getAttribute("src").includes("/product.template/")) {
                throw new Error("wrong image url: " + image.getAttribute("src"));
            }
            await waitFor(avatar + " [data-icon='folder']");
            const buttons = document.querySelectorAll(avatar + " .o_plm_sale_3d").length
                + "," + document.querySelectorAll(avatar + " .o_plm_sale_pdf").length;
            if (buttons !== "1,1") {
                throw new Error("3D and PDF buttons of the first line only, got " + buttons);
            }
            image.click();
            await new Promise((resolve) => setTimeout(resolve, 300));
            if (document.querySelector(".modal")) {
                throw new Error("a dialog opened");
            }
            if (document.querySelector(".o_selected_row")) {
                throw new Error("the click put the line in edition");
            }
            console.log("test successful");
          })().catch((error) => console.error(error.message));
        """
        self.browser_js(f"/odoo/sale.order/{self.order.id}", code, login="admin")
