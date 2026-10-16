/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

/**
 * x2many field whose records open as a full form in the current tab, with a
 * breadcrumb back to the parent, instead of a dialog. The context key
 * plm_open_action names the action (xml id) the form opens in. A record not
 * saved yet, or a field without that key, opens in the standard dialog.
 */
export class X2ManyOpenFormField extends X2ManyField {
    async openRecord(record) {
        const action = this.props.context.plm_open_action;
        if (!action || !record.resId) {
            return super.openRecord(record);
        }
        const resIds = this.list.records.map((r) => r.resId).filter(Boolean);
        return this.action.doAction(action, {
            viewType: "form",
            props: { resId: record.resId, resIds },
        });
    }
}

registry.category("fields").add("plm_x2many_open_form", {
    ...x2ManyField,
    component: X2ManyOpenFormField,
});
