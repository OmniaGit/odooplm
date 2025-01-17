/** @odoo-module **/
import { MrpWorksheet } from "@mrp_workorder/mrp_display/mrp_record_line/mrp_worksheet";
import { MrpDisplayRecord } from '@mrp_workorder/mrp_display/mrp_display_record'

export class PlmMrpWorksheet extends MrpWorksheet{
    async setup(){
        super.setup();
        this.showPlmDocs = false;
        if(this.props && this.props.record && this.props.record.data && this.props.record.data.operation_id && this.props.record.data.operation_id.length !=0){
            let displayDocs = await this.props.record.model.orm.read(
                    "mrp.routing.workcenter",
                    [ this.props.record.data.operation_id[0]],
                    ["use_plm_docs"]
            );
            if(displayDocs.length !=0){
                this.showPlmDocs = displayDocs[0].use_plm_docs;
                this.render();
            }
        }
    }

    get showPlmDocCheck() {
        return this.showPlmDocs;
    }

     async clicked() {
     let action_open_workorder_kanban = await this.props.record.model.orm.call("mrp.workorder", "action_open_workorder_kanban", [this.props.record.resId]);
        return this.action.doAction(action_open_workorder_kanban);
     }
}

PlmMrpWorksheet.template = 'plm_pdf_workorder_enterprise.MrpWorksheet'

MrpDisplayRecord.components = {
    ...MrpDisplayRecord.components,
    PlmMrpWorksheet,
};
