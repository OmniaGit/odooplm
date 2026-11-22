/** @odoo-module */
import {_t} from "@web/core/l10n/translation";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {PlmProductImage} from "@plm/js/product_image/product_image";

/**
 * PlmProductImage for the sales: the image (zoom on hover) and the buttons 3D
 * and PDF, a menu when the product has more than one; no linked documents,
 * so the native CAD files are never shown nor downloadable.
 * A widget uses it in place of PlmProductImage through its components:
 * {PlmProductImage: PlmSaleProductImage}.
 */
export class PlmSaleProductImage extends PlmProductImage {
    static template = "plm_sale_widget.PlmSaleProductImage";
    static components = {...PlmProductImage.components, Dropdown, DropdownItem};
    static infoKind = "sale";

    async fetchInfo(props) {
        return this.orm.call(props.resModel, "get_plm_sale_documents", [[props.resId]]);
    }

    get buttons() {
        return [
            {
                kind: "3d",
                label: _t("3D"),
                title: _t("Show the 3D model"),
                icon: "fa fa-cube",
                documents: this.state.info.web3d || [],
            },
            {
                kind: "pdf",
                label: _t("PDF"),
                title: _t("Show the PDF of the drawing"),
                icon: "fa fa-file-pdf-o",
                documents: this.state.info.pdf || [],
            },
        ];
    }

    onClick(ev) {
        // the image shows its zoom only
        ev.preventDefault();
        ev.stopPropagation();
    }

    async openDocument(kind, document) {
        const method = kind === "3d" ? "action_plm_sale_open_3d" : "action_plm_sale_open_pdf";
        const action = await this.orm.call(this.props.resModel, method, [
            [this.props.resId],
            document.id,
        ]);
        return this.action.doAction(action);
    }
}
