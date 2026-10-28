from odoo import _, api, models

MAX_DEPTH = 10
# What product.template._compute_eng_code_editable treats as a code still to
# be given: such a component has no identity of its own but its product.
NO_ENGINEERING_CODE = ("", "-")


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
    - an assembly that contains itself stops the walk with a note.

    Every row carries the products and the bills of both sides, so that a
    screen can open the single level comparison of any pair.
    """

    _name = "plm.compare.bom.tree"
    _description = "Multilevel BoM Comparison"

    @api.model
    def compare_boms(self, bom_left, bom_right, max_depth=MAX_DEPTH):
        """Compare two bills of material, starting from the bills themselves."""
        return self._compare_boms(
            bom_left,
            bom_right,
            bom_left.type,
            bom_right.type,
            self._depth(max_depth),
            frozenset(),
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

    # -------------------------------------------------------------- helpers
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
                }
            entry["quantity"] += line.product_qty
            if line.itemnum and (
                entry["itemnum"] is None or line.itemnum < entry["itemnum"]
            ):
                entry["itemnum"] = line.itemnum
        return by_key

    # ------------------------------------------------------------- the walk
    @api.model
    def _compare_boms(self, bom_left, bom_right, type_left, type_right, depth, seen):
        """Compare one pair of bills, and nest each component's own comparison
        under it."""
        if not bom_left and not bom_right:
            return {
                "note": _("Neither side has a bill of material of this type."),
                "components": [],
            }
        if not bom_left or not bom_right:
            return {
                "note": _(
                    "Only the %(side)s side has a %(type)s bill of material; "
                    "there is nothing to compare at this level.",
                    side=_("right") if bom_right else _("left"),
                    type=type_left if bom_right else type_right,
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
        self._flag_components(entries, type_left, type_right)

        Bom = self.env["mrp.bom"]
        for entry in entries:
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
                )
                # Attached only when there is something to report: an
                # identical subassembly is has_components with no list.
                if self._is_different(child):
                    if child.get("note"):
                        entry["note"] = child["note"]
                    if child.get("summary"):
                        entry["summary"] = child["summary"]
                    entry["components"] = child["components"]

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
    def _flag_components(self, entries, type_left, type_right):
        """Say of each entry whether anything hangs below it, and which bill
        of each side that is; one query per side for the whole level."""
        Product = self.env["product.product"]
        lefts = Product.concat(*[e["_left"] for e in entries if e.get("_left")])
        rights = Product.concat(*[e["_right"] for e in entries if e.get("_right")])
        boms_left = self._boms_by_template(lefts, type_left)
        boms_right = self._boms_by_template(rights, type_right)
        for entry in entries:
            left = entry.pop("_left", None)
            right = entry.pop("_right", None)
            bom_left = left and boms_left.get(left.product_tmpl_id.id)
            bom_right = right and boms_right.get(right.product_tmpl_id.id)
            entry["product_left_id"] = left.id if left else False
            entry["product_right_id"] = right.id if right else False
            entry["bom_left_id"] = bom_left.id if bom_left else False
            entry["bom_right_id"] = bom_right.id if bom_right else False
            entry["has_components"] = bool(bom_left or bom_right)
        return entries

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
