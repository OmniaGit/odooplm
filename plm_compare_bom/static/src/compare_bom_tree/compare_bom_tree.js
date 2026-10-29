import { Component, onWillStart, proxy, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

export const STATUSES = {
    qty_changed: { label: _t("Quantity changed"), row: "table-warning", badge: "text-bg-warning" },
    revision_changed: { label: _t("Revision changed"), row: "table-info", badge: "text-bg-info" },
    only_left: { label: _t("Only left"), row: "table-danger", badge: "text-bg-danger" },
    only_right: { label: _t("Only right"), row: "table-success", badge: "text-bg-success" },
    unchanged: { label: _t("Unchanged"), row: "", badge: "text-bg-light" },
};

export class CompareBomTree extends Component {
    static template = "plm_compare_bom.CompareBomTree";
    static components = { Layout };
    props = useProps(standardActionServiceProps);

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.statuses = STATUSES;
        const params = this.props.action.params || {};
        const context = this.props.action.context || {};
        this.bomLeftId = params.bom_left_id || context.bom_left_id;
        this.bomRightId = params.bom_right_id || context.bom_right_id;
        // folded: {path: true}; a plain object keeps the reactivity simple
        // pending: {bom line id: quantity} edited and not saved yet
        this.state = proxy({
            data: null,
            onlyDifferences: true,
            folded: {},
            pending: {},
        });
        onWillStart(async () => {
            await this.load();
        });
    }

    async load() {
        if (this.bomLeftId && this.bomRightId) {
            this.state.data = await this.orm.call(
                "plm.compare.bom.tree",
                "get_tree_data",
                [this.bomLeftId, this.bomRightId]
            );
        }
    }

    // ------------------------------------------------------------- rows
    walk(callback, respectFolds = true) {
        const visit = (components, depth, parent) => {
            components.forEach((row, index) => {
                const path = `${parent}${index}`;
                if (this.state.onlyDifferences && !this.isDifferent(row)) {
                    return;
                }
                const foldable = Boolean(row.components && row.components.length);
                callback({ row, path, depth, foldable });
                if (foldable && !(respectFolds && this.state.folded[path])) {
                    visit(row.components, depth + 1, `${path}.`);
                }
            });
        };
        visit((this.state.data && this.state.data.tree.components) || [], 0, "");
    }

    get rows() {
        const rows = [];
        this.walk((line) => rows.push(line));
        return rows;
    }

    get summary() {
        const counts = {};
        const visit = (components) => {
            for (const row of components) {
                if (row.status !== "unchanged") {
                    counts[row.status] = (counts[row.status] || 0) + 1;
                }
                visit(row.components || []);
            }
        };
        visit((this.state.data && this.state.data.tree.components) || []);
        return Object.keys(STATUSES)
            .filter((status) => counts[status])
            .map((status) => ({ status, count: counts[status], ...STATUSES[status] }));
    }

    isDifferent(row) {
        return (
            row.status !== "unchanged" ||
            Boolean(row.components && row.components.length) ||
            Boolean(row.note)
        );
    }

    label(row) {
        return row.engineering_code || row.default_code || row.name;
    }

    revision(row, side) {
        if (!row.engineering_code || row.status === this.otherOnly(side)) {
            return "";
        }
        if (row.status === "revision_changed") {
            return row[`revision_${side}`];
        }
        return row.engineering_revision;
    }

    quantity(row, side) {
        if (row.status === this.otherOnly(side)) {
            return "";
        }
        return "quantity" in row ? row.quantity : row[`quantity_${side}`];
    }

    otherOnly(side) {
        return side === "left" ? "only_right" : "only_left";
    }

    // ------------------------------------------------------- quantities
    /** The bom line a side quantity can be written to: only one, since a
     * quantity summed from several lines says nothing on which to change. */
    editableLine(row, side) {
        const ids = row[`line_${side}_ids`];
        return ids && ids.length === 1 ? ids[0] : false;
    }

    shownQuantity(row, side) {
        const lineId = this.editableLine(row, side);
        return lineId in this.state.pending
            ? this.state.pending[lineId]
            : this.quantity(row, side);
    }

    onQuantityChange(lineId, ev) {
        const quantity = parseFloat(ev.target.value);
        if (isNaN(quantity)) {
            ev.target.value = "";
            delete this.state.pending[lineId];
            return;
        }
        this.state.pending[lineId] = quantity;
    }

    get hasPending() {
        return Object.keys(this.state.pending).length > 0;
    }

    async saveQuantities() {
        const quantities = Object.entries(this.state.pending).map(
            ([lineId, quantity]) => [Number(lineId), quantity]
        );
        await this.orm.call("plm.compare.bom.tree", "set_line_quantities", [quantities]);
        this.state.pending = {};
        await this.load();
    }

    async discardQuantities() {
        this.state.pending = {};
        await this.load();
    }

    // ---------------------------------------------------------- actions
    toggleFold(path) {
        this.state.folded[path] = !this.state.folded[path];
    }

    foldAll(fold) {
        const folded = {};
        if (fold) {
            this.walk((line) => {
                if (line.foldable) {
                    folded[line.path] = true;
                }
            }, false);
        }
        this.state.folded = folded;
    }

    async openLevel(bomLeftId, bomRightId) {
        const action = await this.orm.call("plm.compare.bom", "action_compare_level", [
            bomLeftId,
            bomRightId,
        ]);
        return this.actionService.doAction(action);
    }

    openBom(bomId) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "mrp.bom",
            res_id: bomId,
            views: [[false, "form"]],
        });
    }
}

registry.category("actions").add("plm_compare_bom_tree", CompareBomTree);
