from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from odoo.addons.plm.tests.entity_creator import DUMMY_CONTENT

# 1x1 pixel PNG
PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@tagged("post_install", "-at_install")
class TestSaleProductImage(HttpCase):
    """The product of a sale order line shows its image, one 3D button and one
    PDF button; the native CAD files are never listed nor sent."""

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
        # .stl and .obj linked to the product, .3mf a Web3DTree child of the
        # native model only
        cls.native = cls._document("PLM-SALE-WIDGET.sldprt", cls.product)
        cls.drawing = cls._document("PLM-SALE-WIDGET.slddrw", cls.product, printout=True)
        cls.stl = cls._document("PLM-SALE-WIDGET.stl", cls.product)
        cls.obj = cls._document("PLM-SALE-WIDGET.obj", cls.product)
        cls.web3mf = cls._document("PLM-SALE-WIDGET.3mf")
        cls.env["ir.attachment.relation"].create(
            {"parent_id": cls.native.id, "child_id": cls.web3mf.id, "link_kind": "Web3DTree"}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    Command.create({"product_id": cls.product.id}),
                    Command.create({"product_id": cls.product_without_image.id}),
                ],
            }
        )

    @classmethod
    def _document(cls, name, product=None, printout=False):
        document = cls.env["ir.attachment"].create(
            {
                "name": name,
                "engineering_code": name,
                "datas": DUMMY_CONTENT,
                "is_plm": True,
                "printout": DUMMY_CONTENT if printout else False,
            }
        )
        if product:
            document.linkedcomponents = product
        return document

    def test_documents_for_the_sales(self):
        for product in (self.product, self.product.product_tmpl_id):
            info = product.get_plm_sale_documents()
            self.assertTrue(info["unique"])
            # .3mf first, even as a Web3DTree child only
            self.assertEqual(info["web3d"]["id"], self.web3mf.id)
            self.assertEqual(info["pdf"]["id"], self.drawing.id)
        self.env["ir.attachment.relation"].search([("child_id", "=", self.web3mf.id)]).unlink()
        self.assertEqual(self.product.get_plm_sale_documents()["web3d"]["id"], self.obj.id)
        self.obj.linkedcomponents = False
        self.assertEqual(self.product.get_plm_sale_documents()["web3d"]["id"], self.stl.id)
        info = self.product_without_image.product_tmpl_id.get_plm_sale_documents()
        self.assertEqual(info, {"unique": False, "web3d": False, "pdf": False})

    def test_actions(self):
        action = self.product.product_tmpl_id.action_plm_sale_open_pdf()
        self.assertEqual(action["url"], f"/plm/ir_attachment_printout/{self.drawing.id}")
        action = self.product.action_plm_sale_open_3d()
        self.assertTrue(action["url"].startswith("/plm/show_treejs_model?"))
        self.assertIn(f"document_id={self.web3mf.id}", action["url"])
        self.assertNotIn(f"document_id={self.native.id}&", action["url"] + "&")
        with self.assertRaises(UserError):
            self.product_without_image.action_plm_sale_open_3d()
        with self.assertRaises(UserError):
            self.product_without_image.action_plm_sale_open_pdf()

    def test_viewer_does_not_send_native_file(self):
        # has_web3d is true for the native file (it has a Web3DTree child)
        self.assertTrue(self.native.has_web3d)
        self.authenticate("admin", "admin")
        response = self.url_open(f"/plm/download_treejs_model?document_id={self.native.id}")
        self.assertEqual(response.status_code, 500)
        response = self.url_open(f"/plm/download_treejs_model?document_id={self.web3mf.id}")
        self.assertEqual(response.status_code, 200)

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
            const cell = "td[name='product_template_id'] .plm_m2o_avatar";
            const image = await waitFor(cell + " img");
            if (!image.getAttribute("src").includes("/product.template/")) {
                throw new Error("wrong image url: " + image.getAttribute("src"));
            }
            await waitFor(cell + " .fa-folder-open");
            await waitFor(cell + " .o_plm_sale_3d");
            await waitFor(cell + " .o_plm_sale_pdf");
            if (document.querySelectorAll(cell + " .o_plm_sale_3d").length !== 1) {
                throw new Error("one 3D button only, on the product that has it");
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
