# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the OmniaSolutions OdoPLM repository — a multi-module Odoo 19.0 extension for Product Lifecycle Management (PLM). It integrates Odoo with CAD editors (SolidWorks, Inventor, SolidEdge, Autocad, FreeCAD, etc.) and provides document management, BOM versioning, and revision workflows.

The `plm` module is the foundation all other modules depend on. Feature modules are largely independent add-ons on top of it.

## Development Commands

```bash
# Start Odoo with XML auto-reload (for frontend/view development)
odoo --dev=xml

# Run all PLM tests
odoo --test-tags=odoo_plm

# Run tests for specific modules
odoo --test-tags=odoo_plm,odoo_plm_check_in
odoo --test-tags=odoo_plm,odoo_plm_web_revision,plm_automatic_weight
odoo --test-tags=odoo_plm_suspended
odoo --test-tags=odoo_pack_and_go
odoo --test-tags=plm_date_bom
odoo --test-tags=odoo_plm_mcp
```

## Code Quality

The pre-commit configuration is deliberately small. black, isort, prettier, eslint and pylint-odoo were **removed**: the pinned 2020 versions no longer build on Python 3.12, and reinstating them would mean a repository-wide reformat (128 files for black, 151 for isort, 167 XML files for prettier). Do not assume the repository is black-formatted. What actually runs (`.pre-commit-config.yaml`):

- **flake8**, report only (`--exit-zero`) — it reports but never blocks; there is a backlog of ~1300 findings. Python: max line length 88, max complexity 16 (`.flake8`)
- **local hooks** — `check-pushed-versions` (pre-push, see below), `sync-requirements` (regenerates `aaa_requirements.txt` from the manifests), `check-licensing` (manifests ↔ `LICENSING.md` ↔ `LICENSES/`), `forbidden-files`
- **from pre-commit-hooks** — `check-xml`, `check-yaml`, `check-merge-conflict`, `check-case-conflict`, `check-symlinks`, `check-docstring-first`, `debug-statements`

`.editorconfig` still asks for UTF-8, LF line endings and 4-space indent (2-space for JSON/YAML/RST/MD), but no hook enforces it.

CI runs pre-commit through `.github/workflows/pre-commit.yml`. To check a few files, run a hook by id — `pre-commit run flake8 --files <paths>`.

**Module versions are bumped when pushing, not when committing** (decided 2026-09-15). Push with `python3 scripts/push.py` (`--dry-run` to preview): for the commits between `origin/<branch>` and `HEAD` it raises the patch of every module they touch whose version is still the remote one, always raises `plm` (the `odooplm` pip package version, so any tag stays publishable), commits the manifests in one `[MOD]` commit and pushes. A version raised by hand is left alone. The `check-pushed-versions` pre-push hook refuses a plain `git push` that skips it; `pre-commit install` installs both hook types. So an upgrade script is named after the **remote** version plus one, however many commits the push carries. Do not bump manifests in feature commits.

Commit message format: `[TAG] | Description` where TAG is `FIX`, `ADD`, `IMP`, or `MOD`.

## Licensing

`plm` is LGPL-3, every other module is AGPL-3, both in their *or-later* form. The `license` key of each `__manifest__.py` is authoritative; [`LICENSING.md`](LICENSING.md) is the full map and the `check-licensing` hook fails any commit where the two disagree. A new module must declare its licence and get its row in that table in the same commit.

## Architecture

### Core Abstraction: `revision.plm.mixin`

Every versioned PLM object (products, documents, BOMs) inherits from `plm/models/plm_mixin.py:RevisionBaseMixin`. It provides:

- `engineering_code` + `engineering_revision` — unique pair enforced by DB constraint
- `engineering_state` — the PLM lifecycle state machine
- Chatter (`mail.thread`) and activity tracking

**State machine** (constants exported from `plm_mixin.py`):
```
draft → confirmed → released ↔ undermodify → obsoleted
```
Records in `confirmed`, `released`, `undermodify`, or `obsoleted` states are **write-protected** (`PLM_NO_WRITE_STATE`).

**Revisions are linked only by `engineering_code` + `engineering_revision`**, never by a key, and they can be created by anyone: `new_version()`, the CAD client computing its own revision, a historical import. Revision numbers can have gaps (3 in the db, 5 saved from the CAD), so `get_previus_version()` returns the nearest *lower* revision, not `revision - 1`.

**Revision chain rule** (decided 2026-09-14, `RevisionBaseMixin._fix_previous_revisions_state`, called from `create`, tests tagged `odoo_plm_revision_chain`). When a record with a code and a revision > 0 is created, the lower revisions of that code are brought in line:

1. any of them in `draft` → the creation is refused with a `UserError`: the code was never settled;
2. any document among them checked out → refused (`refuseIfCheckedOut`), as for every workflow move;
3. `confirmed` ones are released ex officio, with a chatter line;
4. the nearest lower revision, if `released`, goes to `undermodify`;
5. every older `released` / `undermodify` one goes to `obsoleted`.

**Branches are out of this rule, on purpose.** `new_branch()` / `_new_branch_version()` create parallel lines of one code (`engineering_branch_parent_id`, sub revision paths like `0.1`), not a sequence, and the feature is still to be designed properly: nothing in the modules or in the CAD client uses it yet. So a branch record is neither checked when created nor touched when a normal revision is created. `_new_branch` passes the branch fields to the copy, so `create` already sees them. When branches are developed, their own chain rule has to be decided and this exclusion revisited.

### Multi-company

The suite is being made multi-company aware; the decisions so far are in [`docs/decisions.md`](docs/decisions.md), tests tagged `odoo_plm_multicompany`.

**Sequences are global** (decided 2026-09-15). Every `ir.sequence` a PLM module creates, in its data XML or from code, declares `company_id` False: without it the sequence takes `env.company` and `next_by_code` returns `False` in every other company. A company gets its own numbering only when an administrator copies the sequence and sets the company on the copy, which `next_by_code` then prefers. A new data sequence needs `<field name="company_id" eval="False"/>`; data sequences are `noupdate`, so changing an existing one needs an upgrade script under `upgrades/<version>/`, named after the remote version plus one (see Code Quality).

**Engineering codes are unique in the whole database** (decided 2026-09-15). Two companies cannot create the same code and revision, while a code stays visible only to the users of its company. The unique index `(engineering_code, engineering_revision) WHERE engineering_code IS NOT NULL` is created by `RevisionBaseMixin.init` on every table of the mixin (`product_template` skipped it until then); a database holding duplicates is updated without it and the duplicates are logged. `''` and `'-'` are no code: the mixin stores them as `False`. So every check that decides whether a code exists, or which revision is the latest, searches in `sudo()` and answers with a generic message that does not name the other company; what a user is shown stays under the record rules. All the revisions of a product code belong to the same company (a revision created without `company_id` joins theirs), and a product changes company only while it is a draft with no bill of materials, no BoM line using it and no linked document. Tests tagged `odoo_plm_multicompany`.

### Key Models

| Model | File | Role |
|---|---|---|
| `revision.plm.mixin` | `plm/models/plm_mixin.py` | Abstract base for all versioned objects |
| `product.template` / `product.product` | `plm/models/product_template.py`, `product_product.py` | Parts with engineering fields and revision |
| `ir.attachment` | `plm/models/ir_attachment.py` | Engineering documents (drawings, CAD files) |
| `mrp.bom` | `plm/models/mrp_bom.py` | BOMs with engineering state and where-used analysis |
| `plm.checkout` | `plm/models/plm_checkout.py` | Document checkout to prevent concurrent CAD editing |
| `plm.cad_open` | `plm/models/plm_cad_open.py` | CAD editor session management |
| `ir_attachment_relations` | `plm/models/ir_attachment_relations.py` | Document-to-document relationships |

### CAD Client REST API

`plm/controllers/main.py` exposes:
- `POST /plm_document_upload/login` — CAD client authentication
- `GET /plm_document_upload/isalive` — health check
- `POST /plm_document_upload/upload` — document/model upload
- `POST /plm_document_upload/upload_pdf` — PDF printout upload

### Document Types

`ir.attachment.document_type` distinguishes: `2d` (drawings), `3d` (CAD models), `other`, `pr` (presentations).

### BOM Variants

- Normal manufacturing BOMs
- Engineering BOMs (`plm_engineering/`)
- Spare parts BOMs (`plm_spare/`)
- Date-effective BOMs (`plm_date_bom/`)
- Kit BOMs (field on `product.template`)

### 3D Viewer (`plm_web_3d/`)

Uses Three.js and a DXF viewer (both as git submodules under `static/src/js/lib/`). The submodule at `plm_web_3d/static/src/js/lib/dxf-viewer` may appear dirty in git status — this is expected.

### External Python Dependencies

Declared in `aaa_requirements.txt` and individual module manifests: `ezdxf`, `matplotlib`, `cadquery`, `numpy-stl`, `base64io`, `to-3mf`. These must be installed in the Odoo environment before installing the corresponding modules.

## Test Structure

Tests use `odoo.tests.common.TransactionCase` and mix in `PlmEntityCreator` (from `plm/tests/entity_creator.py`) for factory helpers. All test classes opt out of the standard test suite with `@tagged("-standard", "<tag>")`.

```python
@tagged("-standard", "odoo_plm")
class MyTest(TransactionCase, PlmEntityCreator):
    def test_something(self):
        product = self.create_product_product("name", "ENG-001")
        ...
```

The `PlmEntityCreator` mixin provides: `create_product_product()`, `create_product_template()`, `create_document()`, `create_uom()`, and BOM-creation helpers.

## Workflow
  Always present a written plan and wait for explicit approval before writing or editing any code.


## CAD Client (separate project)
The Python 2.7 CAD client, its Solid Edge test VM, and the shared-folder setup are documented in the client repository. That file is the single source of truth — do not duplicate those paths here:

@/home/mboscolo/workspace_virtual_machine/Client2019/CLAUDE.md

The current Python 3 / PySide6 CAD client (OdooPLM, CoreBom) is a separate workspace; its decisions and this module's bind each other:

@/media/TwoTDisk/workspace_new_client/CLAUDE.md
