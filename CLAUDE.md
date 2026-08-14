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
- **local hooks** — `bump-manifest-version` and `bump-plm-version` (version bumps), `sync-requirements` (regenerates `aaa_requirements.txt` from the manifests), `check-licensing` (manifests ↔ `LICENSING.md` ↔ `LICENSES/`), `forbidden-files`
- **from pre-commit-hooks** — `check-xml`, `check-yaml`, `check-merge-conflict`, `check-case-conflict`, `check-symlinks`, `check-docstring-first`, `debug-statements`

`.editorconfig` still asks for UTF-8, LF line endings and 4-space indent (2-space for JSON/YAML/RST/MD), but no hook enforces it.

`pre-commit run --all-files` is not side-effect free: `bump-plm-version` always runs and bumps `plm/__manifest__.py`, staging it. To check without that, run a hook by id — `pre-commit run flake8 --files <paths>`. CI runs pre-commit through `.github/workflows/pre-commit.yml`.

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

