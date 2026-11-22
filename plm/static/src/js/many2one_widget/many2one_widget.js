/** @odoo-module */
import {registry} from "@web/core/registry";
import {Many2OneField, many2OneField} from "@web/views/fields/many2one/many2one_field";
import {PlmProductImage} from "@plm/js/product_image/product_image";

export class PlmMany2oneWidget extends Many2OneField {
    static template = "plm.PlmMany2oneWidget";
    static components = {...Many2OneField.components, PlmProductImage};
    static props = {
        ...Many2OneField.props,
        options: {type: Object, optional: true},
    };
    static defaultProps = {
        ...Many2OneField.defaultProps,
        options: {},
    };

    get plmProductImageProps() {
        // the product of this field, whatever the field is called
        return {
            resModel: this.relation,
            resId: this.resId || false,
            imageField: this.props.options.image_field || "image_1920",
            linkedField: this.props.options.linked_field || "linkeddocuments",
        };
    }
}

export const plmMany2oneField = {
    ...many2OneField,
    component: PlmMany2oneWidget,
    extractProps: ({attrs, context, decorations, options, string}, dynamicInfo) => ({
        ...many2OneField.extractProps(
            {attrs, context, decorations, options, string},
            dynamicInfo
        ),
        options: options,
    }),
};
registry.category("fields").add("plm_many2one_image", plmMany2oneField);
