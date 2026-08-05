#!/usr/bin/env python3
"""Extract the OdooPLM demo dataset from a live database.

Reads a source Odoo database (read-only) and writes everything ``plm_demo`` needs
to rebuild the same PLM environment on a fresh install:

    ../data/dataset.json   parts, BOMs, document metadata, links, chatter
    ../files/documents/    the CAD documents themselves
    ../files/images/       product images

Re-run it whenever the source dataset improves; the output is deterministic, so
the diff shows exactly what changed.

    python3 export_demo.py --dbname V19C_demo --roots PROD00023 "Thimble Engine.STEP"

Nothing is ever written to the source database: the connection is opened
read-only.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from collections import OrderedDict

try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover
    sys.exit("psycopg2 is required: pip install psycopg2-binary")

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)

# Documents worth publishing: open formats the browser viewer can actually render.
# SolidWorks natives are deliberately excluded — they are proprietary, they cannot
# be displayed by plm_web_3d, and they weigh ~20 MB.
DEFAULT_EXTENSIONS = ("step", "stp", "3mf", "stl", "dxf", "svg", "pdf", "png", "jpg")

# Skip individual files bigger than this (bytes): a demo module has to stay clonable.
DEFAULT_MAX_FILE = 6 * 1024 * 1024


def slug(value):
    """Stable, readable xml_id fragment."""
    out = re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")
    return out or "x"


class Exporter:
    def __init__(self, args):
        self.args = args
        self.conn = psycopg2.connect(
            host=args.host, port=args.port, user=args.user,
            password=args.password, dbname=args.dbname,
        )
        self.conn.set_session(readonly=True)
        self.cr = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        self.filestore = os.path.expanduser(
            args.filestore or f"~/.local/share/Odoo/filestore/{args.dbname}"
        )
        self.docs_dir = os.path.join(MODULE, "files", "documents")
        self.images_dir = os.path.join(MODULE, "files", "images")
        self.previews_dir = os.path.join(MODULE, "files", "previews")
        self.markups_dir = os.path.join(MODULE, "files", "markups")
        self.stats = OrderedDict()
        self.skipped = []

    # ------------------------------------------------------------------ helpers
    def q(self, sql, *params):
        self.cr.execute(sql, params)
        return self.cr.fetchall()

    def payload(self, store_fname):
        """Absolute path of an attachment payload in the filestore."""
        if not store_fname:
            return None
        path = os.path.join(self.filestore, store_fname)
        return path if os.path.exists(path) else None

    # ------------------------------------------------------------------- extract
    def template_ids(self, roots):
        rows = self.q(
            """
            WITH RECURSIVE tree AS (
                SELECT id FROM product_template WHERE engineering_code = ANY(%s)
              UNION
                SELECT pt.id
                FROM tree t
                JOIN mrp_bom b ON b.product_tmpl_id = t.id
                JOIN mrp_bom_line l ON l.bom_id = b.id
                JOIN product_product pp ON l.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
            )
            SELECT id FROM tree ORDER BY id
            """,
            list(roots),
        )
        return [r[0] for r in rows]

    def export_products(self, tmpl_ids):
        products = []
        for r in self.q(
            """SELECT pt.id, pt.name->>'en_US' AS name, pt.default_code,
                      pt.engineering_code, pt.engineering_revision, pt.engineering_state,
                      pt.engineering_revision_letter, pt.engineering_material,
                      pt.engineering_surface, pt.engineering_treatment,
                      pt.type, pt.is_storable, pt.weight,
                      pt.description->>'en_US' AS description,
                      pp.id AS variant_id
               FROM product_template pt
               JOIN product_product pp ON pp.product_tmpl_id = pt.id
               WHERE pt.id = ANY(%s)
               ORDER BY pt.engineering_code, pt.engineering_revision""",
            tmpl_ids,
        ):
            products.append({
                "xml_id": "part_%s_%s" % (slug(r["engineering_code"]), r["engineering_revision"]),
                "src_tmpl_id": r["id"],
                "src_variant_id": r["variant_id"],
                "name": r["name"],
                "default_code": r["default_code"],
                "engineering_code": r["engineering_code"],
                "engineering_revision": r["engineering_revision"],
                "engineering_state": r["engineering_state"],
                "engineering_revision_letter": r["engineering_revision_letter"],
                "engineering_material": r["engineering_material"],
                "engineering_surface": r["engineering_surface"],
                "engineering_treatment": r["engineering_treatment"],
                "type": r["type"],
                "is_storable": r["is_storable"],
                "weight": float(r["weight"] or 0.0),
                "description": r["description"],
                "image": self.export_image(r["id"]),
            })
        self.stats["products"] = len(products)
        return products

    def export_image(self, tmpl_id):
        rows = self.q(
            """SELECT store_fname, mimetype, file_size FROM ir_attachment
               WHERE res_model='product.template' AND res_id=%s AND res_field='image_1920'
               LIMIT 1""",
            tmpl_id,
        )
        if not rows:
            return None
        src = self.payload(rows[0]["store_fname"])
        if not src:
            return None
        ext = "png" if "png" in (rows[0]["mimetype"] or "") else "jpg"
        name = f"tmpl_{tmpl_id}.{ext}"
        shutil.copyfile(src, os.path.join(self.images_dir, name))
        return name

    def export_boms(self, tmpl_ids, by_variant):
        boms = []
        for b in self.q(
            """SELECT id, code, type, product_tmpl_id, product_qty, sequence
               FROM mrp_bom WHERE product_tmpl_id = ANY(%s) ORDER BY product_tmpl_id, id""",
            tmpl_ids,
        ):
            lines = []
            for l in self.q(
                """SELECT product_id, product_qty, sequence FROM mrp_bom_line
                   WHERE bom_id=%s ORDER BY sequence, id""",
                b["id"],
            ):
                target = by_variant.get(l["product_id"])
                if not target:          # component outside the exported scope
                    continue
                lines.append({
                    "product": target,
                    "qty": float(l["product_qty"]),
                    "sequence": l["sequence"],
                })
            if not lines:
                continue
            boms.append({
                "xml_id": "bom_%s_%s" % (slug(b["type"]), b["id"]),
                "src_id": b["id"],
                "code": b["code"],
                "type": b["type"],
                "product": by_variant_tmpl(by_variant, b["product_tmpl_id"]),
                "product_qty": float(b["product_qty"]),
                "lines": lines,
            })
        self.stats["boms"] = len(boms)
        self.stats["bom_lines"] = sum(len(b["lines"]) for b in boms)
        return boms

    def export_documents(self, tmpl_ids, by_variant, extensions, max_file):
        rows = self.q(
            """SELECT DISTINCT a.id, a.name, a.document_type, a.mimetype, a.file_size,
                      a.store_fname, a.engineering_code, a.engineering_revision,
                      a.engineering_state, a.engineering_revision_letter, a.desc_modify,
                      a.is_library
               FROM plm_component_document_rel r
               JOIN ir_attachment a ON a.id = r.document_id
               JOIN product_product pp ON pp.id = r.component_id
               WHERE pp.product_tmpl_id = ANY(%s)
               ORDER BY a.id""",
            tmpl_ids,
        )
        documents, skipped = [], []
        for d in rows:
            ext = (d["name"] or "").rsplit(".", 1)[-1].lower()
            if ext not in extensions:
                skipped.append((d["name"], "format"))
                continue
            if (d["file_size"] or 0) > max_file:
                skipped.append((d["name"], "size"))
                continue
            src = self.payload(d["store_fname"])
            if not src:
                skipped.append((d["name"], "missing payload"))
                continue
            fname = d["name"]
            shutil.copyfile(src, os.path.join(self.docs_dir, fname))
            preview = self.export_preview(d["id"], fname)
            documents.append({
                "xml_id": "doc_%s_%s" % (slug(d["engineering_code"] or d["name"]),
                                         d["engineering_revision"] or 0),
                "src_id": d["id"],
                "file": fname,
                "name": d["name"],
                "document_type": d["document_type"],
                "mimetype": d["mimetype"],
                "engineering_code": d["engineering_code"],
                "engineering_revision": d["engineering_revision"],
                "engineering_state": d["engineering_state"],
                "engineering_revision_letter": d["engineering_revision_letter"],
                "desc_modify": d["desc_modify"],
                "is_library": d["is_library"],
                "sha1": hashlib.sha1(open(src, "rb").read()).hexdigest(),
                "preview": preview,
                "linked_products": [],
            })
        by_src = {d["src_id"]: d for d in documents}

        # document -> product links, restricted to what we actually exported
        for r in self.q(
            """SELECT r.document_id, r.component_id FROM plm_component_document_rel r
               JOIN product_product pp ON pp.id = r.component_id
               WHERE pp.product_tmpl_id = ANY(%s) ORDER BY r.document_id, r.component_id""",
            tmpl_ids,
        ):
            doc = by_src.get(r["document_id"])
            target = by_variant.get(r["component_id"])
            if doc and target and target not in doc["linked_products"]:
                doc["linked_products"].append(target)

        # document -> document relations (assembly hierarchy, drawing layouts)
        relations = []
        ids = list(by_src)
        for r in self.q(
            """SELECT parent_id, child_id, link_kind FROM ir_attachment_relation
               WHERE parent_id = ANY(%s) AND child_id = ANY(%s)
               ORDER BY parent_id, child_id""",
            ids, ids,
        ):
            relations.append({
                "parent": by_src[r["parent_id"]]["xml_id"],
                "child": by_src[r["child_id"]]["xml_id"],
                "link_kind": r["link_kind"] or "",
            })

        self.stats["documents"] = len(documents)
        self.stats["document_relations"] = len(relations)
        self.stats["documents_skipped"] = len(skipped)
        self.skipped = skipped
        return documents, relations

    def export_preview(self, attachment_id, doc_name):
        """The thumbnail shown in the document views (a bytea column, not a file)."""
        rows = self.q("SELECT preview FROM ir_attachment WHERE id=%s", attachment_id)
        blob = rows[0]["preview"] if rows else None
        if not blob:
            return None
        name = slug(doc_name) + ".png"
        with open(os.path.join(self.previews_dir, name), "wb") as fh:
            fh.write(bytes(blob))
        return name

    def export_markups(self, by_doc):
        """3D markups and the chatter message each one produced.

        The message body is not copied verbatim: it embeds the document and markup
        ids of the source database. It is rebuilt at install time from the comment,
        so the link points at the records the demo actually created.
        """
        markups = []
        if not by_doc:
            return markups
        for m in self.q(
            """SELECT k.id, k.res_id, k.comment, k.filename, k.canvas_data,
                      msg.date AS message_date
               FROM plm_markup_log k
               LEFT JOIN mail_message msg ON msg.id = k.message_id
               WHERE k.res_model='ir.attachment' AND k.res_id = ANY(%s)
               ORDER BY k.id""",
            list(by_doc),
        ):
            base_image = None
            rows = self.q(
                """SELECT store_fname FROM ir_attachment
                   WHERE res_model='plm.markup.log' AND res_id=%s AND res_field='base_image'
                   LIMIT 1""",
                m["id"],
            )
            if rows:
                src = self.payload(rows[0]["store_fname"])
                if src:
                    base_image = f"markup_{m['id']}.png"
                    shutil.copyfile(src, os.path.join(self.markups_dir, base_image))
            markups.append({
                "xml_id": "markup_%s" % m["id"],
                "document": by_doc[m["res_id"]],
                "comment": m["comment"] or "",
                "filename": m["filename"],
                "canvas_data": m["canvas_data"],
                "base_image": base_image,
                "message_date": m["message_date"].isoformat() if m["message_date"] else None,
            })
        self.stats["markups"] = len(markups)
        return markups

    def export_chatter(self, tmpl_ids, doc_src_ids, by_variant, by_doc, limit_per_record):
        """Human comments only.

        Automatic notifications ("X created", field tracking) are dropped: Odoo
        writes them again by itself when the demo records are created. Markup
        messages are dropped too — export_markups rebuilds them with working links.
        Authors are not exported; everything is posted by the installing user.
        """
        messages = []
        for model, ids, mapping in (
            ("product.template", tmpl_ids, None),
            ("ir.attachment", doc_src_ids, by_doc),
        ):
            if not ids:
                continue
            for m in self.q(
                """SELECT model, res_id, body, message_type, date,
                          row_number() OVER (PARTITION BY res_id ORDER BY id) AS rn
                   FROM mail_message
                   WHERE model=%s AND res_id = ANY(%s)
                     AND message_type = 'comment'
                     AND body IS NOT NULL AND body <> '' AND body <> '<p><br></p>'
                     AND body NOT LIKE '%%show_treejs_model%%'
                   ORDER BY res_id, id""",
                model, list(ids),
            ):
                if m["rn"] > limit_per_record:
                    continue
                if model == "product.template":
                    target = by_variant_tmpl(by_variant, m["res_id"])
                else:
                    target = mapping.get(m["res_id"])
                if not target:
                    continue
                messages.append({
                    "model": model,
                    "target": target,
                    "body": m["body"],
                    "date": m["date"].isoformat() if m["date"] else None,
                })
        self.stats["chatter"] = len(messages)
        return messages

    # ---------------------------------------------------------------------- run
    def run(self):
        args = self.args
        for path in (self.docs_dir, self.images_dir, self.previews_dir, self.markups_dir):
            if os.path.isdir(path):
                shutil.rmtree(path)
            os.makedirs(path)

        tmpl_ids = self.template_ids(args.roots)
        if not tmpl_ids:
            sys.exit(f"no product found for engineering_code in {args.roots}")

        products = self.export_products(tmpl_ids)
        by_variant = {p["src_variant_id"]: p["xml_id"] for p in products}
        by_variant.update({p["src_tmpl_id"]: p["xml_id"] for p in products})  # tmpl lookup

        boms = self.export_boms(tmpl_ids, by_variant)

        # Documents may come from a narrower set of assemblies than the structure:
        # a BOM tree is safe to publish, a customer's geometry usually is not.
        doc_tmpl_ids = tmpl_ids
        if args.doc_roots:
            doc_tmpl_ids = self.template_ids(args.doc_roots)
            if not doc_tmpl_ids:
                sys.exit(f"no product found for engineering_code in {args.doc_roots}")
        documents, relations = self.export_documents(
            doc_tmpl_ids, by_variant, tuple(args.extensions), args.max_file
        )
        by_doc = {d["src_id"]: d["xml_id"] for d in documents}
        markups = self.export_markups(by_doc)
        chatter = self.export_chatter(
            tmpl_ids, list(by_doc), by_variant, by_doc, args.max_messages
        )

        for p in products:                      # source ids are not part of the dataset
            p.pop("src_tmpl_id"), p.pop("src_variant_id")
        for d in documents:
            d.pop("src_id")
        for b in boms:
            b.pop("src_id")

        dataset = {
            "source": {"roots": list(args.roots)},
            "products": products,
            "boms": boms,
            "documents": documents,
            "document_relations": relations,
            "markups": markups,
            "chatter": chatter,
        }
        out = os.path.join(MODULE, "data", "dataset.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as fh:
            json.dump(dataset, fh, indent=1, sort_keys=True)
            fh.write("\n")

        size = sum(
            os.path.getsize(os.path.join(d, f))
            for d in (self.docs_dir, self.images_dir, self.previews_dir, self.markups_dir)
            for f in os.listdir(d)
        )
        print("exported to", out)
        for k, v in self.stats.items():
            print(f"  {k:22} {v}")
        print(f"  {'payload':22} {size/1e6:.2f} MB")
        if self.skipped:
            print(f"  skipped {len(self.skipped)} documents:")
            for name, why in self.skipped[:10]:
                print(f"    - {name} ({why})")
            if len(self.skipped) > 10:
                print(f"    ... and {len(self.skipped)-10} more")


def by_variant_tmpl(mapping, tmpl_id):
    return mapping.get(tmpl_id)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dbname", required=True)
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", default=5432, type=int)
    p.add_argument("--user", default="odoo")
    p.add_argument("--password", default="odoo")
    p.add_argument("--filestore", help="defaults to ~/.local/share/Odoo/filestore/<dbname>")
    p.add_argument("--roots", nargs="+", required=True,
                   help="engineering_code of the assemblies to export")
    p.add_argument("--doc-roots", nargs="+",
                   help="export documents only for these assemblies (default: all roots). "
                        "Use it to publish a BOM structure without publishing its CAD files.")
    p.add_argument("--extensions", nargs="+", default=list(DEFAULT_EXTENSIONS),
                   help="document formats to publish (default: open formats only)")
    p.add_argument("--max-file", type=int, default=DEFAULT_MAX_FILE,
                   help="skip documents bigger than this many bytes")
    p.add_argument("--max-messages", type=int, default=6,
                   help="chatter messages kept per record")
    Exporter(p.parse_args()).run()


if __name__ == "__main__":
    main()
