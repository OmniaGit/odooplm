/** @odoo-module **/

import { registry } from "@web/core/registry";

const TREE = ".o_plm_compare_bom_tree";

registry.category("web_tour.tours").add("plm_compare_bom_tree_tour", {
    steps: () => [
        {
            content: "Open the wizard record in a dialog, as Compare BoMs does (target new)",
            trigger: ".o_form_view",
            run: async () => {
                const wizardId = Number(window.location.pathname.split("/").pop());
                await odoo.__WOWL_DEBUG__.root.env.services.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "plm.compare.bom",
                    res_id: wizardId,
                    views: [[false, "form"]],
                    target: "new",
                });
            },
        },
        {
            content: "Open the multilevel comparison from the wizard",
            trigger: ".modal button[name='action_compare_tree']",
            run: "click",
        },
        {
            content: "The changed part, three levels down, is shown",
            trigger: `${TREE} tr[data-code='CBT-PRT-003'].table-warning`,
        },
        {
            content: "Its path is shown as revised",
            trigger: `${TREE} tr[data-code='CBT-SUB-001'].table-info`,
        },
        {
            content: "A subassembly on the right only can be opened",
            trigger: `${TREE} tr[data-code='CBT-SUB-003'].table-success .o_plm_open_bom`,
            run: "click",
        },
        {
            content: "Its bill of material opens",
            trigger: ".o_form_view .o_field_widget[name='bom_line_ids']",
        },
        {
            content: "Go back to the comparison",
            trigger: ".o_breadcrumb li.o_back_button a",
            run: "click",
        },
        {
            trigger: `${TREE} tr[data-code='CBT-SUB-003']`,
        },
        {
            content: "Set the right quantity of the changed part as the left one",
            trigger: `${TREE} tr[data-code='CBT-PRT-003'] input.o_plm_qty[data-side='right']`,
            run: "edit 4 && click body",
        },
        {
            content: "Save it",
            trigger: ".o_plm_save_quantities",
            run: "click",
        },
        {
            content: "Saved: the part is no longer a difference, so it is hidden",
            trigger: `${TREE}:not(:has(tr[data-code='CBT-PRT-003']))`,
        },
        {
            content: "An unchanged part is hidden",
            trigger: `${TREE}:not(:has(tr[data-code='CBT-PRT-001']))`,
        },
        {
            content: "Show the unchanged rows too",
            trigger: "input.o_plm_only_differences",
            run: "click",
        },
        {
            trigger: `${TREE} tr[data-code='CBT-PRT-001']`,
        },
        {
            content: "Fold the revised subassembly",
            trigger: `${TREE} tr[data-code='CBT-SUB-001'] .o_plm_fold`,
            run: "click",
        },
        {
            trigger: `${TREE}:not(:has(tr[data-code='CBT-SUB-002']))`,
        },
        {
            content: "Open the single level comparison of the two bills",
            trigger: ".o_plm_compare_level_root",
            run: "click",
        },
        {
            content: "The single level comparison is shown",
            trigger: ".o_field_widget[name='anotinb']",
        },
        {
            content: "Its two bills are shown as cards, like the multilevel page",
            trigger: ".o_plm_compare_bom_cards .card .o_field_widget[name='bom_id2']",
        },
    ],
});
