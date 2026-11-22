/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { PlmProductImage } from "@plm/js/product_image/product_image";

/**
 * PlmProductImage for the sales: the image (zoom on hover) and one 3D button
 * and one PDF button, shown when the product has them. The server chooses
 * the file (no choice of format for the sales) and never a native CAD file.
 * A widget uses it in place of PlmProductImage through its components:
 * {PlmProductImage: PlmSaleProductImage}.
 */
export class PlmSaleProductImage extends PlmProductImage {
    static template = "plm_sale_widget.PlmSaleProductImage";
    static infoKind = "sale";

    async fetchInfo(props) {
        return this.orm.call(props.resModel, "get_plm_sale_documents", [[props.resId]]);
    }

    get buttons() {
        const info = this.state.info;
        const buttons = [];
        if (info.web3d) {
            buttons.push({
                kind: "3d",
                label: _t("3D"),
                title: _t("Show the 3D model"),
                icon: "fa fa-cube",
                method: "action_plm_sale_open_3d",
            });
        }
        if (info.pdf) {
            buttons.push({
                kind: "pdf",
                label: _t("PDF"),
                title: _t("Show the PDF of the drawing"),
                icon: "fa fa-file-pdf-o",
                method: "action_plm_sale_open_pdf",
            });
        }
        return buttons;
    }

    onClick(ev) {
        // the image shows its zoom only
        ev.preventDefault();
        ev.stopPropagation();
    }

    async openDocument(button) {
        const action = await this.orm.call(this.props.resModel, button.method, [
            [this.props.resId],
        ]);
        return this.action.doAction(action);
    }
}
