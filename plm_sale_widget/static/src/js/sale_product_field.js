/** @odoo-module */
import {registry} from "@web/core/registry";
import {
    SaleOrderLineProductField,
    saleOrderLineProductField,
} from "@sale/js/sale_product_field";
import {PlmMany2oneWidget, plmMany2oneField} from "@plm/js/many2one_widget/many2one_widget";
import {PlmSaleProductImage} from "@plm_sale_widget/js/sale_product_image";

/**
 * The product widget of the sale order lines, with the image of the product
 * and its buttons 3D and PDF (PlmSaleProductImage).
 */
export class PlmSaleOrderLineProductField extends SaleOrderLineProductField {
    static template = "plm_sale_widget.SaleProductField";
    static components = {
        ...SaleOrderLineProductField.components,
        PlmProductImage: PlmSaleProductImage,
    };

    get plmProductImageProps() {
        return {
            resModel: this.relation,
            resId: this.resId || false,
        };
    }
}

registry.category("fields").add("plm_sol_product_many2one", {
    ...saleOrderLineProductField,
    component: PlmSaleOrderLineProductField,
});

/**
 * plm_many2one_image for the sales: any product field, with the buttons 3D
 * and PDF in place of the linked documents.
 */
export class PlmSaleMany2oneWidget extends PlmMany2oneWidget {
    static components = {
        ...PlmMany2oneWidget.components,
        PlmProductImage: PlmSaleProductImage,
    };
}

registry.category("fields").add("plm_sale_many2one_image", {
    ...plmMany2oneField,
    component: PlmSaleMany2oneWidget,
});
