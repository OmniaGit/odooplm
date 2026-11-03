
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

const openWizard = {
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
};

registry.category("web_tour.tours").add("plm_compare_bom_tree_kit_tour", {
    steps: () => [
        openWizard,
        {
            content: "Two normal BoMs: ask to follow the kits",
            trigger: ".modal div[name='follow_kit_subcontract'] input",
            run: "click",
        },
        {
            trigger: ".modal div[name='follow_kit_subcontract'] input:checked",
        },
        {
            content: "Open the multilevel comparison",
            trigger: ".modal button[name='action_compare_tree']",
            run: "click",
        },
        {
            content: "The kit carries its type",
            trigger: `${TREE} tr[data-code='CBT-SUB-001'] .o_plm_bom_type:contains(Kit)`,
        },
        {
            content: "The part changed inside the kit is shown",
            trigger: `${TREE} tr[data-code='CBT-PRT-003'].table-warning`,
        },
    ],
});

registry.category("web_tour.tours").add("plm_compare_bom_tree_schema_tour", {
    steps: () => [
        openWizard,
        {
            trigger: ".modal div[name='follow_kit_subcontract'] input",
            run: "click",
        },
        {
            trigger: ".modal div[name='follow_kit_subcontract'] input:checked",
        },
        {
            trigger: ".modal button[name='action_compare_tree']",
            run: "click",
        },
        {
            content: "The parent says its bills are of different types",
            trigger: `${TREE} tr[data-code='FIGLIO']:contains(Different BoM type) .o_plm_bom_type:contains(Normal BoM / Kit)`,
        },
        {
            content: "A component on the left only",
            trigger: `${TREE} tr[data-code='NIPOTE1'].table-danger`,
        },
        {
            content: "A component on the right only",
            trigger: `${TREE} tr[data-code='NIPOTE2'].table-success`,
        },
        {
            content: "The revised parent of the difference",
            trigger: `${TREE} tr[data-code='NIPOTE4'].table-info`,
        },
        {
            trigger: `${TREE} tr[data-code='NIPOTE4F2'].table-danger`,
        },
        {
            trigger: `${TREE} tr[data-code='NIPOTE4F3'].table-success`,
        },
        {
            content: "The same component under the different types is hidden",
            trigger: `${TREE}:not(:has(tr[data-code='NIPOTE3']))`,
        },
        {
            content: "The same component further down is hidden",
            trigger: `${TREE}:not(:has(tr[data-code='NIPOTE4F1']))`,
        },
        {
            content: "The root is not a row",
            trigger: `${TREE}:not(:has(tr[data-code='PAPA']))`,
        },
    ],
});

registry.category("web_tour.tours").add("plm_compare_bom_tree_header_tour", {
    steps: () => [
        openWizard,
        {
            trigger: ".modal button[name='action_compare_tree']",
            run: "click",
        },
        {
            content: "The header says the two types differ",
            trigger: `${TREE} .o_plm_bom_types_differ:contains(Normal BoM):contains(Kit)`,
        },
        {
            content: "And the two bills are not called identical",
            trigger: `${TREE}:not(:has(.o_plm_compare_summary .badge))`,
        },
    ],
});
