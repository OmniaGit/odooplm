/** @odoo-module **/

import { registry } from "@web/core/registry";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2One } from "@web/views/fields/many2one/many2one";
import { useService } from "@web/core/utils/hooks";
import { onWillUpdateProps, useState } from "@odoo/owl";

export class CustomImageM2oField extends Many2One {
    static props = {
        ...Many2One.props,
    };
    static components = {
        ...Many2One.components,
    };
    get many2XAutocompleteProps() {
        const props = super.many2XAutocompleteProps;
        return { ...props };
    }
}

export class Many2OnePlmField extends Many2OneField {
    static template = "plm.CustomImageM2oField";
    static components = {
        ...Many2OneField.components,
        Many2One: CustomImageM2oField,
    };

    getRelationModel() {
        const relFromConfig = this.props?.record?.model?.root?.model?.config?.fields?.[this.props.name]?.relation;
        const relFromField = this.props?.field?.relation;
        return relFromConfig || relFromField;
    }

    async setup() {
        super.setup();
        this.relatedField = false;
        this.imageToolTipData = false;
        this.actionService = useService("action");
        this.state = useState({ imageData: false });

        onWillUpdateProps(async (nextProps) => {
            this.state.imageData = false;
            this.imageToolTipData = false;

            const fieldName = nextProps?.name;
            const value = nextProps?.record?.data?.[fieldName];
            const imageField = "image_1920";
            const linkedField = "linkeddocuments";

            let recordId = null;
            if (Array.isArray(value) && value.length > 0) {
                recordId = value[0];
            } else if (value && typeof value === "object" && value.id) {
                recordId = value.id;
            } else {
                // no-op
            }

            const model = this.getRelationModel();

            if (recordId && imageField && model) {
                const imageData = await this.env.model.orm.call(
                    model,
                    "search_read",
                    [],
                    {
                        domain: [["id", "=", recordId]],
                        fields: [imageField],
                    }
                );

                if (imageData?.length && imageData[0][imageField]) {
                    this.state.imageData = "data:image/png;base64," + imageData[0][imageField];
                    this.imageToolTipData = JSON.stringify({ url: this.state.imageData });
                }
            }
        });

        // Initial load
        const value = this.props?.record?.data?.[this.props.name];
        const imageField = "image_1920";
        const linkedField = "linkeddocuments";

        let recordId = null;
        if (Array.isArray(value) && value.length > 0) {
            recordId = value[0];
        } else if (value && typeof value === "object" && value.id) {
            recordId = value.id;
        } else {
            // no-op
        }

        const model = this.getRelationModel();

        if (recordId && (imageField || linkedField) && model) {
            // Load image
            if (imageField) {
                const imageData = await this.env.model.orm.call(
                    model,
                    "search_read",
                    [],
                    {
                        domain: [["id", "=", recordId]],
                        fields: [imageField],
                    }
                );
                if (imageData?.length && imageData[0][imageField]) {
                    this.state.imageData = "data:image/png;base64," + imageData[0][imageField];
                    this.imageToolTipData = JSON.stringify({ url: this.state.imageData });
                }
            }

            // Load linked field
            if (linkedField) {
                this.relatedField = await this.env.model.orm.call(
                    model,
                    "search_read",
                    [],
                    {
                        domain: [["id", "=", recordId]],
                        fields: [linkedField],
                    }
                );
            }
        }
    }

    async onImageClicked(event) {
        event.stopPropagation();
        const productId = this.props?.record?.data?.product_tmpl_id?.id;
        const relatedFieldName = "linkeddocuments";
        if (!productId || !relatedFieldName) {
            return;
        }
        const model =
            this.props.record.model.root.model.config.fields[this.props.name].relation;
        const action_open_linked_field = await this.props.record.model.orm.call(
            model,
            "action_open_linked_field",
            [productId, "linkeddocuments"]
        );
        return this.actionService.doAction(action_open_linked_field);
    }
}

export const many2OnePlmField = {
    ...buildM2OFieldDescription(Many2OnePlmField),
};

registry.category("fields").add("plm_many2one_image", many2OnePlmField);