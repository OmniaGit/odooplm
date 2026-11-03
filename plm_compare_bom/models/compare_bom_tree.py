from odoo import _, api, models
from odoo.exceptions import UserError

MAX_DEPTH = 10
# What product.template._compute_eng_code_editable treats as a code still to
# be given: such a component has no identity of its own but its product.
NO_ENGINEERING_CODE = ("", "-")
# The bill types a comparison of two normal bills follows when asked to, in the
# order they are picked when both sides have more than one in common.
FOLLOWED_BOM_TYPES = ("normal", "phantom", "subcontract")


class PlmCompareBomTree(models.AbstractModel):
    """Multilevel comparison of two bills of material.

    The rules are the ones plm_mcp settled on (odooplm 20.0 53f3c08e):

    - a component is its engineering code and its revision; the same code at
      another revision on the other side is revision_changed, and the walk goes
      down into it, because that is the only pair that can differ underneath;
    - a component without an engineering code (a commercial part known by its
      default_code, or '-') is matched by product;
    - lines of the same component in one bill are summed before comparing;
    - each side keeps its own bill type all the way down;
    - two normal bills can be asked to follow kit and subcontracting
      subassemblies too (follow_kit_subcontract). The components are always
      compared: two bills of different types are a difference of the parent,
      which says so, while what they hold is compared as usual and the same
      components stay no difference. Two sides with more than one type in
      common walk the first, and a note says when another differs too. Unasked,
      a revised component with such a bill says so in a note;
    - an assembly that contains itself stops the walk with a note.

    Every row carries the products and the bills of both sides, so that a
    screen can open the single level comparison of any pair.
    """

    _name = "plm.compare.bom.tree"
    _description = "Multilevel BoM Comparison"

    @api.model
    def compare_boms(
        self, bom_left, bom_right, max_depth=MAX_DEPTH, follow_kit_subcontract=False
    ):
        """Compare two bills of material, starting from the bills themselves.

        follow_kit_subcontract counts only between two normal bills: a
        comparison of other types, or of two different ones, was asked for
        those types and stays on them.
        """
        both_normal = bom_left.type == "normal" and bom_right.type == "normal"
        return self._compare_boms(
            bom_left,
            bom_right,
            bom_left.type,
            bom_right.type,
            self._depth(max_depth),
            frozenset(),
            aligned=both_normal and follow_kit_subcontract,
            warn_other_types=both_normal and not follow_kit_subcontract,
        )

    @api.model
    def compare_products(
        self, left, type_left, right, type_right, max_depth=MAX_DEPTH
    ):
        """Compare the bill of type type_left of left with the bill of type
        type_right of right."""
        return self._compare_boms(
            self._bom_of(left, type_left),
            self._bom_of(right, type_right),
            type_left,
            type_right,
            self._depth(max_depth),
            frozenset(),
        )

    @api.model
    def get_tree_data(self, bom_left_id, bom_right_id, follow_kit_subcontract=False):
        """What the multilevel comparison screen shows: the two bills and the
        tree between them."""
        Bom = self.env["mrp.bom"]
        bom_left = Bom.browse(bom_left_id).exists()
        bom_right = Bom.browse(bom_right_id).exists()
        if not bom_left or not bom_right:
            raise UserError(_("Both bills of material must exist to be compared."))
        return {
            "left": self._bom_header(bom_left),
            "right": self._bom_header(bom_right),
            "bom_types_differ": bom_left.type != bom_right.type,
            "tree": self.compare_boms(
                bom_left, bom_right, follow_kit_subcontract=follow_kit_subcontract
            ),
        }

    @api.model
    def set_line_quantities(self, quantities):
        """Write the quantities edited on the screen: [[bom line id, qty]]."""
        Line = self.env["mrp.bom.line"]
        for line_id, quantity in quantities:
            line = Line.browse(line_id).exists()
            if line:
                line.product_qty = quantity
        return True

    @api.model
    def _bom_header(self, bom):
        product = bom.product_id or bom.product_tmpl_id
        types = self._bom_type_labels()
        return {
            "id": bom.id,
            "name": bom.display_name,
            "engineering_code": product.engineering_code or False,
            "engineering_revision": product.engineering_revision,
            "type": types.get(bom.type, bom.type),
        }

    # -------------------------------------------------------------- helpers
    @api.model
    def _bom_type_labels(self):
        """{bill type: label} of the types this database has: subcontract comes
        with mrp_subcontracting."""
        field = self.env["mrp.bom"]._fields["type"]
        return dict(field._description_selection(self.env))

    @api.model
    def _depth(self, max_depth):
        return max(1, min(int(max_depth or MAX_DEPTH), MAX_DEPTH))

    @api.model
    def _bom_of(self, product, bom_type):
        return self._boms_by_template(product, bom_type).get(
            product.product_tmpl_id.id, self.env["mrp.bom"]
        )

    @api.model
    def _boms_by_template(self, products, bom_type):
        """The bill of each product's template, in one query for the level:
        the first in the mrp.bom order, as a search with limit=1 would pick."""
        boms = {}
        if products:
            for bom in self.env["mrp.bom"].search(
                [
                    ("product_tmpl_id", "in", products.product_tmpl_id.ids),
                    ("type", "=", bom_type),
                ]
            ):
                boms.setdefault(bom.product_tmpl_id.id, bom)
        return boms

    @api.model
    def _boms_by_type(self, products, bom_types):
        """{template id: {bill type: bill}}, in one query for the level; of a
        type the first in the mrp.bom order, as _boms_by_template picks."""
        boms = {}
        if products:
            for bom in self.env["mrp.bom"].search(
                [
                    ("product_tmpl_id", "in", products.product_tmpl_id.ids),
                    ("type", "in", list(bom_types)),
                ]
            ):
                boms.setdefault(bom.product_tmpl_id.id, {}).setdefault(bom.type, bom)
        return boms

    @api.model
    def _lines_by_key(self, bom):
        """Bill lines as {key: {revision: entry}}, quantities of the same
        component summed: two rows of one part are one fact, and left apart
        they would show as a difference whenever the other side lists it once.
        """
        by_key = {}
        for line in bom.bom_line_ids:
            component = line.product_id
            code = (component.engineering_code or "").strip()
            if code in NO_ENGINEERING_CODE:
                code = False
                key = "product:%s" % component.id
            else:
                key = "code:%s" % code
            entries = by_key.setdefault(key, {})
            revision = component.engineering_revision
            entry = entries.get(revision)
            if entry is None:
                entry = entries[revision] = {
                    "engineering_code": code,
                    "engineering_revision": revision,
                    "engineering_state": component.engineering_state,
                    "default_code": component.default_code or False,
                    "name": component.name,
                    "quantity": 0.0,
                    "itemnum": line.itemnum or None,
                    "product": component,
                    "lines": self.env["mrp.bom.line"],
                }
            entry["quantity"] += line.product_qty
            entry["lines"] |= line
            if line.itemnum and (
                entry["itemnum"] is None or line.itemnum < entry["itemnum"]
            ):
                entry["itemnum"] = line.itemnum
        return by_key

    # ------------------------------------------------------------- the walk
    @api.model
    def _compare_boms(
        self,
        bom_left,
        bom_right,
        type_left,
        type_right,
        depth,
        seen,
        aligned=False,
        warn_other_types=False,
    ):
        """Compare one pair of bills, and nest each component's own comparison
        under it.

        aligned: follow the FOLLOWED_BOM_TYPES, one type per level.
        warn_other_types: stay on the type, and note what is left out.
        """
        if not bom_left and not bom_right:
            return {
                "note": _("Neither side has a bill of material of this type."),
                "components": [],
            }
        if not bom_left or not bom_right:
            missing_type = type_left if bom_right else type_right
            if aligned:
                existing_type = (bom_left or bom_right).type
                missing_type = self._bom_type_labels().get(existing_type)
            return {
                "note": _(
                    "Only the %(side)s side has a %(type)s bill of material; "
                    "there is nothing to compare at this level.",
                    side=_("right") if bom_right else _("left"),
                    type=missing_type,
                ),
                "components": [],
            }
        pair = (bom_left.id, bom_right.id)
        if pair in seen:
            return {
                "note": _("Already compared higher up: cycle stopped."),
                "components": [],
            }
        seen = seen | {pair}

        entries = self._compare_entries(
            self._lines_by_key(bom_left), self._lines_by_key(bom_right)
        )
        self._flag_components(
            entries, type_left, type_right, aligned, warn_other_types
        )

        Bom = self.env["mrp.bom"]
        for entry in entries:
            other_common_boms = entry.pop("_other_common_boms", [])
            if (
                depth > 1
                and entry["has_components"]
                and entry["product_left_id"]
                and entry["product_right_id"]
            ):
                child = self._compare_boms(
                    Bom.browse(entry["bom_left_id"]),
                    Bom.browse(entry["bom_right_id"]),
                    type_left,
                    type_right,
                    depth - 1,
                    seen,
                    aligned,
                    warn_other_types,
                )
                # Attached only when there is something to report: an
                # identical subassembly is has_components with no list.
                if self._is_different(child):
                    if child.get("note"):
                        entry["note"] = " ".join(
                            filter(None, [entry.get("note"), child["note"]])
                        )
                    if child.get("summary"):
                        entry["summary"] = child["summary"]
                    entry["components"] = child["components"]
                for other_left, other_right in other_common_boms:
                    other = self._compare_boms(
                        other_left,
                        other_right,
                        type_left,
                        type_right,
                        depth - 1,
                        seen,
                        aligned,
                        warn_other_types,
                    )
                    if self._is_different(other):
                        note = _(
                            "The %(type)s bills differ too.",
                            type=self._bom_type_labels()[other_left.type],
                        )
                        entry["note"] = " ".join(
                            filter(None, [entry.get("note"), note])
                        )

        # In the order of the drawing: the balloon number is how an engineer
        # finds the row being talked about.
        entries.sort(
            key=lambda row: (
                row.get("itemnum") or 9999,
                row["engineering_code"] or row["default_code"] or "",
            )
        )
        return {"summary": self._summarise(entries), "components": entries}

    @api.model
    def _flag_components(
        self, entries, type_left, type_right, aligned=False, warn_other_types=False
    ):
        """Say of each entry whether anything hangs below it, and which bill
        of each side that is; one query per side for the whole level."""
        Product = self.env["product.product"]
        lefts = Product.concat(e["_left"] for e in entries if e.get("_left"))
        rights = Product.concat(e["_right"] for e in entries if e.get("_right"))
        followed = [t for t in FOLLOWED_BOM_TYPES if t in self._bom_type_labels()]
        read_all = aligned or warn_other_types
        boms_left = self._boms_by_type(lefts, followed if read_all else [type_left])
        boms_right = self._boms_by_type(rights, followed if read_all else [type_right])
        for entry in entries:
            left = entry.pop("_left", None)
            right = entry.pop("_right", None)
            by_left = boms_left.get(left.product_tmpl_id.id, {}) if left else {}
            by_right = boms_right.get(right.product_tmpl_id.id, {}) if right else {}
            if aligned:
                bom_left, bom_right = self._align_boms(
                    entry, by_left, by_right, followed
                )
            else:
                bom_left = by_left.get(type_left)
                bom_right = by_right.get(type_right)
                if warn_other_types and entry["status"] == "revision_changed":
                    self._note_other_types(entry, by_left, by_right, type_left)
            entry["product_left_id"] = left.id if left else False
            entry["product_right_id"] = right.id if right else False
            entry["bom_left_id"] = bom_left.id if bom_left else False
            entry["bom_right_id"] = bom_right.id if bom_right else False
            entry["has_components"] = bool(bom_left or bom_right)
        return entries

    @api.model
    def _align_boms(self, entry, by_left, by_right, followed):
        """Which bill of each side this row compares: one type for both, the
        first they have in common, else the first of each. With no type in
        common the row says the bills differ, whatever they contain, and the
        walk compares their components all the same. The same product has the
        same bills, so this can only be said of a revised row.
        """
        labels = self._bom_type_labels()
        commons = [t for t in followed if t in by_left and t in by_right]
        common = commons[0] if commons else None
        if common:
            bom_left, bom_right = by_left[common], by_right[common]
            if by_left[common] != by_right[common]:
                entry["_other_common_boms"] = [
                    (by_left[t], by_right[t]) for t in commons[1:]
                ]
        else:
            first_left = next((t for t in followed if t in by_left), None)
            first_right = next((t for t in followed if t in by_right), None)
            bom_left = by_left.get(first_left)
            bom_right = by_right.get(first_right)

        def names(boms):
            return ", ".join(labels[t] for t in followed if t in boms)

        if by_left and by_right and set(by_left) != set(by_right):
            if common:
                entry["note"] = _(
                    "Compared the %(type)s bills; the bill types differ: "
                    "left %(left)s, right %(right)s.",
                    type=labels[common],
                    left=names(by_left),
                    right=names(by_right),
                )
            else:
                entry["bom_types_differ"] = True
                entry["note"] = _(
                    "Different BoM type: left %(left)s, right %(right)s.",
                    left=names(by_left),
                    right=names(by_right),
                )
        shown = {bom.type for bom in (bom_left, bom_right) if bom}
        if shown and shown != {"normal"}:
            entry["bom_type_label"] = " / ".join(
                labels[t] for t in followed if t in shown
            )
        return bom_left, bom_right

    @api.model
    def _note_other_types(self, entry, by_left, by_right, walked_type):
        """A revised component whose bills of other types are not looked at.
        Only there something can be lost: an unrevised one is the same product
        on both sides, with the same bills."""
        labels = self._bom_type_labels()
        others = [
            labels[t]
            for t in FOLLOWED_BOM_TYPES
            if t != walked_type and (t in by_left or t in by_right)
        ]
        if others:
            entry["note"] = _(
                "Has a %(types)s bill of material that is not compared.",
                types=", ".join(others),
            )

    @api.model
    def _compare_entries(self, lines_left, lines_right):
        """Classify every component into one of the five states."""
        entries = []
        for key in sorted(set(lines_left) | set(lines_right)):
            left_entries = dict(lines_left.get(key, {}))
            right_entries = dict(lines_right.get(key, {}))

            # Exact matches first: same code (or product), same revision.
            for revision in sorted(set(left_entries) & set(right_entries)):
                entry_left = left_entries.pop(revision)
                entry_right = right_entries.pop(revision)
                same_qty = entry_left["quantity"] == entry_right["quantity"]
                entry = {
                    "status": "unchanged" if same_qty else "qty_changed",
                    "engineering_code": entry_left["engineering_code"],
                    "engineering_revision": revision,
                    "engineering_state": entry_left["engineering_state"],
                    "default_code": entry_left["default_code"],
                    "name": entry_left["name"],
                    "itemnum": entry_left["itemnum"],
                    "_left": entry_left["product"],
                    "_right": entry_right["product"],
                    "line_left_ids": entry_left["lines"].ids,
                    "line_right_ids": entry_right["lines"].ids,
                }
                if same_qty:
                    entry["quantity"] = entry_left["quantity"]
                else:
                    entry["quantity_left"] = entry_left["quantity"]
                    entry["quantity_right"] = entry_right["quantity"]
                entries.append(entry)

            # The same code at different revisions on the two sides, paired
            # oldest to oldest so it reads as one change. A product key has a
            # single revision, so it never gets here.
            for entry_left, entry_right in zip(
                [left_entries[r] for r in sorted(left_entries)],
                [right_entries[r] for r in sorted(right_entries)],
            ):
                entries.append(
                    {
                        "status": "revision_changed",
                        "engineering_code": entry_left["engineering_code"],
                        "revision_left": entry_left["engineering_revision"],
                        "revision_right": entry_right["engineering_revision"],
                        "state_left": entry_left["engineering_state"],
                        "state_right": entry_right["engineering_state"],
                        "default_code": entry_right["default_code"],
                        "name": entry_right["name"],
                        "itemnum": entry_right["itemnum"] or entry_left["itemnum"],
                        "quantity_left": entry_left["quantity"],
                        "quantity_right": entry_right["quantity"],
                        "_left": entry_left["product"],
                        "_right": entry_right["product"],
                        "line_left_ids": entry_left["lines"].ids,
                        "line_right_ids": entry_right["lines"].ids,
                    }
                )
                left_entries.pop(entry_left["engineering_revision"], None)
                right_entries.pop(entry_right["engineering_revision"], None)

            for revision in sorted(left_entries):
                entries.append(
                    self._one_sided("only_left", left_entries[revision], "_left")
                )
            for revision in sorted(right_entries):
                entries.append(
                    self._one_sided("only_right", right_entries[revision], "_right")
                )
        return entries

    @api.model
    def _one_sided(self, status, entry, side_key):
        return {
            "status": status,
            "engineering_code": entry["engineering_code"],
            "engineering_revision": entry["engineering_revision"],
            "engineering_state": entry["engineering_state"],
            "default_code": entry["default_code"],
            "name": entry["name"],
            "itemnum": entry["itemnum"],
            "quantity": entry["quantity"],
            side_key: entry["product"],
            "line%s_ids" % side_key: entry["lines"].ids,
        }

    @api.model
    def _summarise(self, components):
        counts = {}
        for component in components:
            counts[component["status"]] = counts.get(component["status"], 0) + 1
        return counts

    @api.model
    def _is_different(self, node):
        """Whether a compared branch holds anything worth reporting: a
        difference, or a note (a cycle, a missing bill) at any depth."""
        if node.get("note"):
            return True
        return any(
            component["status"] != "unchanged"
            or component.get("components")
            or component.get("note")
            for component in node.get("components", [])
        )
