/** @odoo-module **/

import { Component } from "@odoo/owl";

export class MrpDisplayEmployeesPanel extends Component {
    static template = "plm_mrp_workorder.MrpDisplayEmployeesPanel";
    static props = {
        employees: { type: Object },
        setSessionOwner: { type: Function },
        popupAddEmployee: { type: Function },
        logout: { type: Function },
    };
}
