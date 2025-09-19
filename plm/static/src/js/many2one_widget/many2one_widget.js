/** @odoo-module */
import {registry} from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import {Many2OneField, many2OneField, extractM2OFieldProps, buildM2OFieldDescription, m2oSupportedOptions} from "@web/views/fields/many2one/many2one_field";
import {onWillUpdateProps} from "@odoo/owl";
import { Many2One } from "@web/views/fields/many2one/many2one";
import {
    many2OneAvatarUserField,
    Many2OneAvatarUserField,
} from "@mail/views/web/fields/many2one_avatar_user_field/many2one_avatar_user_field";
import { Component, useState, useEffect } from "@odoo/owl";



export class PlmMany2oneWidget extends Component {

    static template = "plm.PlmMany2oneWidget";
    static props = {
        ...Many2OneField.props,
        options: {type: Object, optional: true},
    };
    static defaultProps = {
        ...Many2OneField.defaultProps,
        options: false,
    };

    async setup() {
        super.setup();
        this.imageData = false;
        this.relatedField = false;
        this.imageToolTipData = false;
        onWillUpdateProps(async (nextProps) => {
            this.imageData = false;
            this.imageToolTipData = false;
            let fieldName = nextProps.name;
            if (nextProps && nextProps.record && nextProps.record.data && nextProps.record.data[fieldName] && nextProps.record.data[fieldName].length != 0) {
                let imageData = await this.env.model.orm.call("product.template", "search_read", [], {
                    domain: [["id", "=", nextProps.record.data[fieldName][0]]],
                    fields: [nextProps.options.image_field],
                });
                if (imageData && imageData.length != 0 && imageData[0][nextProps.options.image_field]) {
                    this.imageData = "data:image/png;base64, " + imageData[0][nextProps.options.image_field];
                    this.imageToolTipData = JSON.stringify({"url": this.imageData});
                    this.render();
                }
            }
        });
        console.log("\n\n\n", "thiss-------->>>>>>>>>", this, "\n\n\n")
        if (this.props && this.props.record && this.props.record.data && this.props.record.data[this.props.name] && this.props.record.data[this.props.name].length != 0) {

            let imageData = await this.env.model.orm.call("product.template", "search_read", [], {
                domain: [["id", "=", this.props.record.data[this.props.name][0]]],
                fields: [this.props.options.image_field],
            });
            this.relatedField = await this.env.model.orm.call("product.template", "search_read", [], {
                domain: [["id", "=", this.props.record.data[this.props.name][0]]],
                fields: [this.props.options.linked_field],
            });
            if (imageData && imageData.length != 0 && imageData[0][this.props.options.image_field]) {
                this.imageData = "data:image/png;base64, " + imageData[0][this.props.options.image_field];
                this.imageToolTipData = JSON.stringify({"url": this.imageData});
                this.render();
            }
        }
    }

    async onImageClicked(event) {
        event.stopPropagation(); // It stops the event from triggering any additional event handlers
        let selectedProductId = this.props.record.data.product_id[0];
        let relatedFieldName = this.props.options.linked_field;
        let model = this.props.record.model.root.model.config.fields[this.props.name].relation;
        let action_open_linked_field = await this.props.record.model.orm.call(model, "action_open_linked_field", [selectedProductId, relatedFieldName]);
        return this.action.doAction(action_open_linked_field);
    }
}

export const plmMany2oneField = {
    ...buildM2OFieldDescription(PlmMany2oneWidget),
    extractProps({ options }) {
        const props = extractM2OFieldProps(...arguments);
        props.options = options;
        return props;
    },
};
registry.category("fields").add("plm_many2one_image", plmMany2oneField);


// -----------------------------------------------------
// export class PlmMany2oneWidget extends Component {

//     static template = "plm.PlmMany2oneWidget";
//     static props = {
//         ...Many2OneField.props,
//         options: {type: Object, optional: true},
//     };
//     static defaultProps = {
//         ...Many2OneField.defaultProps,
//         options: false,
//     };

//     async setup() {
//         super.setup();
//         this.imageData = false;
//         this.relatedField = false;
//         this.imageToolTipData = false;
//         onWillUpdateProps(async (nextProps) => {
//             this.imageData = false;
//             this.imageToolTipData = false;
//             let fieldName = nextProps.name;
//             if (nextProps && nextProps.record && nextProps.record.data && nextProps.record.data[fieldName] && nextProps.record.data[fieldName].length != 0) {
//                 let imageData = await this.env.model.orm.call("product.template", "search_read", [], {
//                     domain: [["id", "=", nextProps.record.data[fieldName][0]]],
//                     fields: [nextProps.options.image_field],
//                 });
//                 if (imageData && imageData.length != 0 && imageData[0][nextProps.options.image_field]) {
//                     this.imageData = "data:image/png;base64, " + imageData[0][nextProps.options.image_field];
//                     this.imageToolTipData = JSON.stringify({"url": this.imageData});
//                     this.render();
//                 }
//             }
//         });
//         console.log("\n\n\n", "thiss-------->>>>>>>>>", this, "\n\n\n")
//         if (this.props && this.props.record && this.props.record.data && this.props.record.data[this.props.name] && this.props.record.data[this.props.name].length != 0) {

//             let imageData = await this.env.model.orm.call("product.template", "search_read", [], {
//                 domain: [["id", "=", this.props.record.data[this.props.name][0]]],
//                 fields: [this.props.options.image_field],
//             });
//             this.relatedField = await this.env.model.orm.call("product.template", "search_read", [], {
//                 domain: [["id", "=", this.props.record.data[this.props.name][0]]],
//                 fields: [this.props.options.linked_field],
//             });
//             if (imageData && imageData.length != 0 && imageData[0][this.props.options.image_field]) {
//                 this.imageData = "data:image/png;base64, " + imageData[0][this.props.options.image_field];
//                 this.imageToolTipData = JSON.stringify({"url": this.imageData});
//                 this.render();
//             }
//         }
//     }

//     async onImageClicked(event) {
//         event.stopPropagation(); // It stops the event from triggering any additional event handlers
//         let selectedProductId = this.props.record.data.product_id[0];
//         let relatedFieldName = this.props.options.linked_field;
//         let model = this.props.record.model.root.model.config.fields[this.props.name].relation;
//         let action_open_linked_field = await this.props.record.model.orm.call(model, "action_open_linked_field", [selectedProductId, relatedFieldName]);
//         return this.action.doAction(action_open_linked_field);
//     }
// }

// export const plmMany2oneField = {
//     ...buildM2OFieldDescription(PlmMany2oneWidget),
//     extractProps({ options }) {
//         const props = extractM2OFieldProps(...arguments);
//         props.options = options;
//         return props;
//     },
// };
// registry.category("fields").add("plm_many2one_image", plmMany2oneField);
