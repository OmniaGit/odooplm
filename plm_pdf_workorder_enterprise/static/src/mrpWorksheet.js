/** @odoo-module **/

import { MrpWorksheet } from "@mrp_workorder/mrp_display/mrp_record_line/mrp_worksheet";
import { MrpWorksheetDialog } from "@mrp_workorder/mrp_display/dialog/mrp_worksheet_dialog";
import { MrpDisplayRecord } from '@mrp_workorder/mrp_display/mrp_display_record'
import { markup } from "@odoo/owl";
export class PlmMrpWorksheet extends MrpWorksheet{
    setup(){
        super.setup();
    }
     async clicked() {
        let worksheetData = false;
            const sheet = await this.props.record.model.orm.read(
                    "mrp.workorder",
                    [this.props.record.resId],
                    ["plm_pdf"]
            );
            if(sheet && sheet.length !=0){

                worksheetData = {
                    resModel: "mrp.workorder",
                    resId: this.props.record.resId,
                    resField: "plm_pdf",
                    value: sheet[0].plm_pdf,
                    page: 1,
                };
                this.dialog.add(MrpWorksheetDialog, {
                worksheetText: markup(''),
                worksheetData,
            });
            }
     }
}
PlmMrpWorksheet.template = 'plm_pdf_workorder_enterprise.MrpWorksheet'
MrpDisplayRecord.components = {
    ...MrpDisplayRecord.components,
    PlmMrpWorksheet,
};
