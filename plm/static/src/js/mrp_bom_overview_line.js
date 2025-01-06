/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { BomOverviewLine } from "@mrp/components/bom_overview_line/mrp_bom_overview_line";

patch(BomOverviewLine.prototype, {
    setup() {
        super.setup();
        this.image_data = false;
        if(this.data && this.data.image_component){
            this.image_data = 'data:image/png;base64, ' + this.data.image_component
        }
    }
});
