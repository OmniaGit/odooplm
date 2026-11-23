import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";
import {
    ListSaleOrderLineLabelTextField,
    listSaleOrderLineLabelText,
    SaleLabelTextField,
    saleOrderLineLabelText,
} from "@sale/js/sale_label_text/sale_label_text";
import {
    SaleOrderLineProductField,
    saleOrderLineProductField,
} from "@sale/js/sale_product_field/sale_product_field";
import { Many2OnePlmField, many2OnePlmField } from "@plm/js/many2one_widget/many2one_widget";
import { PlmSaleProductImage } from "@plm_sale_widget/js/sale_product_image";

/**
 * The product widget of the sale order lines, with the image of the product
 * and its buttons 3D and PDF (PlmSaleProductImage).
 */
export class PlmSaleOrderLineProductField extends SaleOrderLineProductField {
    static template = "plm_sale_widget.SaleProductField";
    static components = {
        ...SaleOrderLineProductField.components,
        PlmSaleProductImage,
    };

    plmProductImageProps() {
        const value = this.props.record.data[this.props.name];
        return {
            resModel: this.props.record.fields[this.props.name].relation,
            resId: (value && value.id) || false,
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
export class PlmSaleMany2oneField extends Many2OnePlmField {
    static components = {
        ...Many2OnePlmField.components,
        PlmProductImage: PlmSaleProductImage,
    };
}

registry.category("fields").add("plm_sale_many2one_image", {
    ...many2OnePlmField,
    component: PlmSaleMany2oneField,
});

/**
 * The description of the sale order lines (the label, where Odoo 20 shows the
 * product of the line), with the image of the product and its buttons 3D and
 * PDF in front of it when the line is not in edition.
 */
export class PlmSaleLabelTextField extends SaleLabelTextField {
    static template = "plm_sale_widget.SaleLabelTextField";
    static components = {
        ...SaleLabelTextField.components,
        PlmSaleProductImage,
    };

    plmProductImageProps() {
        const product = this.props.record.data.product_template_id;
        return {
            resModel: "product.template",
            resId: (product && product.id) || false,
        };
    }
}

export class PlmListSaleOrderLineLabelTextField extends ListSaleOrderLineLabelTextField {
    get componentToUse() {
        const component = super.componentToUse;
        return component === SaleLabelTextField ? PlmSaleLabelTextField : component;
    }

    get componentProps() {
        if (this.componentToUse === PlmSaleLabelTextField) {
            return this.props;
        }
        return omit(this.props, "context");
    }
}

registry.category("fields").add("plm_sol_label_text", saleOrderLineLabelText);
registry.category("fields").add("list.plm_sol_label_text", {
    ...listSaleOrderLineLabelText,
    component: PlmListSaleOrderLineLabelTextField,
});
