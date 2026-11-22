/** @odoo-module **/

import { registry } from "@web/core/registry";
import { buildM2OFieldDescription, extractM2OFieldProps, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { PlmProductImage } from "@plm/js/product_image/product_image";

/**
 * Many2one of a product with its image (PlmProductImage): the zoom on hover,
 * a click opens the linked documents of the product of this field.
 * options: image_field (the image of the zoom), linked_field.
 */
export class Many2OnePlmField extends Many2OneField {
    static template = "plm.CustomImageM2oField";
    static components = { ...Many2OneField.components, PlmProductImage };
    static props = {
        ...Many2OneField.props,
        imageField: { type: String, optional: true },
        linkedField: { type: String, optional: true },
    };

    get plmProductImageProps() {
        // the product of this field, whatever the field is called
        const value = this.props.record.data[this.props.name];
        return {
            resModel: this.props.record.fields[this.props.name].relation,
            resId: (value && value.id) || false,
            imageField: this.props.imageField || "image_1920",
            linkedField: this.props.linkedField || "linkeddocuments",
        };
    }
}

export const many2OnePlmField = {
    ...buildM2OFieldDescription(Many2OnePlmField),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            imageField: staticInfo.options.image_field,
            linkedField: staticInfo.options.linked_field,
        };
    },
};

registry.category("fields").add("plm_many2one_image", many2OnePlmField);
