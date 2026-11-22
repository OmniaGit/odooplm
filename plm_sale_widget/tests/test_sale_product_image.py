from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

# 1x1 pixel PNG
PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@tagged("post_install", "-at_install")
class TestSaleProductImage(HttpCase):
    """The product of a sale order line shows its image and the buttons 3D and
    PDF; the native CAD files are never listed nor sent."""

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
        # a native CAD file with a printout, its STEP conversion (support file,
        # ExtraTree) and a 3D web model (Web3DTree)
        attachment = cls.env["ir.attachment"].with_context(check=False)
        cls.native = attachment.create(
            {
                "name": "plm_sale_widget_part.ipt",
                "engineering_code": "PLM_SALE_WIDGET_PART",
                "engineering_revision": 0,
                "is_plm": True,
                "res_model": "plm.access",
                "res_id": cls.env.ref("plm.plm_basic_access_model").id,
                "datas": PNG,
                "printout": PNG,
            }
        )
        cls.env["plm.component.document.rel"].createFromIds(cls.product, cls.native)
        cls.step = attachment._save_extra_file(
            b"step",
            "PLM_SALE_WIDGET_PART_STEP",
            file_name="plm_sale_widget_part.step",
            related_attachment_id=cls.native.id,
            product_id=cls.product.id,
        )
        cls.web3d = attachment._save_extra_file(
            b"glb",
            "PLM_SALE_WIDGET_PART_GLB",
            file_name="plm_sale_widget_part.glb",
            product_id=cls.product.id,
        )
        cls.env["ir.attachment.relation"].create(
            {"parent_id": cls.native.id, "child_id": cls.web3d.id, "link_kind": "Web3DTree"}
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

    def test_documents_for_the_sales(self):
        for product in (self.product, self.product.product_tmpl_id):
            info = product.get_plm_sale_documents()
            self.assertTrue(info["unique"])
            self.assertEqual(
                {document["id"] for document in info["web3d"]}, {self.step.id, self.web3d.id}
            )
            self.assertEqual([document["id"] for document in info["pdf"]], [self.native.id])
        info = self.product_without_image.product_tmpl_id.get_plm_sale_documents()
        self.assertEqual(info, {"unique": False, "web3d": [], "pdf": []})

    def test_native_file_is_never_opened(self):
        with self.assertRaises(UserError):
            self.product.action_plm_sale_open_3d(self.native.id)
        with self.assertRaises(UserError):
            self.product.action_plm_sale_open_pdf(self.step.id)
        action = self.product.product_tmpl_id.action_plm_sale_open_pdf(self.native.id)
        self.assertEqual(action["url"], f"/plm/ir_attachment_printout/{self.native.id}")
        action = self.product.action_plm_sale_open_3d(self.web3d.id)
        self.assertTrue(action["url"].startswith("/plm/show_treejs_model?"))
        self.assertIn(f"document_id={self.web3d.id}", action["url"])

    def test_viewer_does_not_send_native_file(self):
        # has_web3d is true for the native file (it has a Web3DTree child)
        self.assertTrue(self.native.has_web3d)
        self.authenticate("admin", "admin")
        response = self.url_open(f"/plm/download_treejs_model?document_id={self.native.id}")
        self.assertEqual(response.status_code, 500)
        response = self.url_open(f"/plm/download_treejs_model?document_id={self.web3d.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"glb")

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
            // two 3D models: a menu; one PDF: a button
            const menu = await waitFor(cell + " .fa-cube");
            const pdf = await waitFor(cell + " .fa-file-pdf-o");
            image.click();
            menu.closest("button").click();
            const items = [...(await waitFor(".o-dropdown--menu")).querySelectorAll(".o-dropdown-item")];
            const names = items.map((item) => item.textContent.trim()).sort().join(",");
            if (names !== "plm_sale_widget_part.glb,plm_sale_widget_part.step") {
                throw new Error("wrong 3D models: " + names);
            }
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
