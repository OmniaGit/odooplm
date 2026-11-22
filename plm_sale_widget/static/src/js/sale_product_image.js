import { _t } from "@web/core/l10n/translation";
import { PlmProductImage } from "@plm/js/product_image/product_image";

/**
 * PlmProductImage for the sales: the image (zoom on hover) and one 3D button
 * and one PDF button, shown when the product has them. No linked documents,
 * so the native CAD files are never shown nor opened; the server chooses the
 * file each button opens.
 * A widget uses it in place of PlmProductImage through its components:
 * { PlmProductImage: PlmSaleProductImage }.
 */
export class PlmSaleProductImage extends PlmProductImage {
    static template = "plm_sale_widget.PlmSaleProductImage";
    static infoKind = "sale";

    async fetchInfo(props) {
        return this.orm.call(props.resModel, "get_plm_sale_documents", [[props.resId]]);
    }

    onClick(ev) {
        // the image shows its zoom only
        ev.preventDefault();
        ev.stopPropagation();
    }

    buttonTitle(kind) {
        return kind === "3d" ? _t("Show the 3D model") : _t("Show the PDF of the drawing");
    }

    async open(kind) {
        const method = kind === "3d" ? "action_plm_sale_open_3d" : "action_plm_sale_open_pdf";
        const action = await this.orm.call(this.props.resModel, method, [[this.props.resId]]);
        return this.action.doAction(action);
    }
}
