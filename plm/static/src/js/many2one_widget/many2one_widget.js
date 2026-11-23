import { t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";
import { PlmProductImage } from "@plm/js/product_image/product_image";

/**
 * A product many2one with the image of the product in front of it: the zoom
 * on hover, a click opens its linked documents (PlmProductImage).
 * Options: image_field (the image of the zoom, image_1920 by default) and
 * linked_field (the documents opened, linkeddocuments by default).
 */
export class Many2OnePlmField extends Many2OneField {
    static template = "plm.Many2OnePlmField";
    static components = { ...Many2OneField.components, PlmProductImage };
    props = useProps({ ...many2OneFieldProps, options: t.object().optional({}) });

    plmProductImageProps() {
        // the product of this field, whatever the field is called
        const value = this.props.record.data[this.props.name];
        const options = this.props.options || {};
        return {
            resModel: this.props.record.fields[this.props.name].relation,
            resId: (value && value.id) || false,
            imageField: options.image_field || "image_1920",
            linkedField: options.linked_field || "linkeddocuments",
        };
    }
}

export const many2OnePlmField = {
    ...buildM2OFieldDescription(Many2OnePlmField),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            options: staticInfo.options,
        };
    },
};

registry.category("fields").add("plm_many2one_image", many2OnePlmField);
