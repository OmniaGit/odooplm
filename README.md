# OdooPLM — Product Lifecycle Management for Odoo

**OdooPLM** is an open-source PLM/PDM extension for [Odoo](https://www.odoo.com/),
developed and maintained by [OmniaSolutions](https://www.omniasolutions.website).
It integrates Odoo with the most popular CAD editors and provides document
management, BOM versioning, revision workflows, and a browser-based 3D/2D viewer.

This branch targets **Odoo 19.0** and contains **36 modules**, all built on the
core `plm` module.

> 📖 Wiki (install, CAD client, user guide, FAQ): **https://github.com/OmniaGit/odooplm/wiki**
> 🌐 Full documentation: **https://odooplm.omniasolutions.website**
> 🐛 Issues and support: **https://github.com/OmniaGit/odooplm/issues**
> 🚀 Live demo: **https://v19.odooplm.cloud** — `admin` / `admin`

---

## Run it with Docker

OdooPLM is published as a ready-to-run Docker image, on GitHub Container Registry
and on Docker Hub. A single command gives you Odoo with the whole community PLM
suite in the addons path, a PostgreSQL database and a working PLM server on the
first boot — no database wizard, no dependency installation.

```bash
git clone --branch 19.0 https://github.com/OmniaGit/DockerOdooPLM.git odooplm-19
cd odooplm-19
docker compose up
```

Then open <http://localhost:8069>.

| Variant | Size | Contains |
|---|---|---|
| **full** | ~4.4 GB | the CAD conversion stack, for batch STEP to 3MF, STL and PNG conversion |
| **slim** | ~2.5 GB | the same modules without the conversion stack |

Each variant also has a **`-demo`** tag that boots already populated — the sample
product of `plm_demo` over three BOM levels, its 3D models, ballooned assembly
drawings and the spare parts manual that prints from them. Log in with
`admin` / `admin`.

| Registry | Tags |
|---|---|
| GHCR | `ghcr.io/omniagit/odooplm:19.0` · `19.0-slim` · `19.0-demo` · `19.0-slim-demo` |
| Docker Hub | `mboscolo/odooplm:19.0` · `19.0-slim` · `19.0-demo` · `19.0-slim-demo` |

The images are rebuilt every week, against both the PLM sources and the official
Odoo image, and every build is started and verified before it is published.
Images, Compose stack and documentation: **https://github.com/OmniaGit/DockerOdooPLM**

---

## CAD Client

The desktop CAD client (connector) is hosted on SourceForge:

**https://sourceforge.net/projects/openerpplm/**

It is a proprietary application distributed by OmniaSolutions; the server modules
in this repository are open source.

The client supports the following CAD editors:

| CAD Editor | Notes |
|---|---|
| SolidWorks | Full integration (checkout, upload, BOM sync) |
| SolidEdge | Full integration |
| Autodesk Inventor | Full integration |
| AutoCAD / DraftSight | 2D drawings |
| ThinkDesign | Full integration |
| FreeCAD | Open-source integration |

The client communicates with Odoo via the REST API exposed by the `plm` module
(`/plm_document_upload/login`, `/plm_document_upload/upload`, etc.) over **HTTP on
port 80**.

---

## Modules

### Core

| Module | Description |
|---|---|
| `plm` | Foundation module — versioned products, engineering documents, BOM lifecycle, checkout system, CAD client REST API |
| `plm_demo` | A populated PLM environment instead of an empty one: the LSU-100 sample product, 12 parts over three BOM levels, spare BOMs, 29 STEP/3MF/DXF/PDF documents with previews, ballooned assembly sheets, 3D markups. Evaluation and training only |

### Document & Viewer

| Module | Description |
|---|---|
| `plm_web_3d` | Browser-based 3D/2D viewer (Three.js). Supports 3MF, STEP, GLTF, STL, OBJ, DXF, SVG. Features: section plane with stencil cap, measurement tool (point/face snap), zoom window, part colour and transparency picker with persistence, markup system with chatter integration, model screenshot saved as attachment preview |
| `plm_web_3d_sale` | 3D product previews on the eCommerce pages, from the engineering models already in the document management |
| `plm_automated_convertion` | Batch CAD format conversion (STEP→3MF, STEP→STL, STEP→PNG preview). Preserves assembly structure and component names |
| `plm_web_revision` | Trigger PLM revision workflows from the web interface |
| `plm_pack_and_go` | Download the full BOM file tree (all CAD documents of an assembly) as a ZIP |

### BOM

| Module | Description |
|---|---|
| `plm_engineering` | Engineering BOMs — separate from manufacturing BOMs |
| `plm_spare` | Spare parts BOMs and spare parts manual generation |
| `plm_date_bom` | Date-effective BOMs — resolve the correct BOM for a given date |
| `plm_compare_bom` | Side-by-side BOM comparison between two revisions |
| `plm_bom_summarize` | Flatten/summarize a BOM uploaded from a CAD client |
| `plm_automate_normal_bom` | Automatically create/update standard manufacturing BOMs |

### Product & Weight

| Module | Description |
|---|---|
| `plm_automatic_weight` | Automatic weight calculation propagated through the BOM |
| `plm_breakages` | Breakage and consumable parts management |
| `plm_ent_breakages_helpdesk` | Breakages through the Odoo Helpdesk (Enterprise) |
| `plm_cutted_parts` | Cut parts and raw material management |
| `plm_auto_engcode` | Auto-generate engineering codes for new parts |
| `plm_auto_internalref` | Auto-generate internal references |

### Manufacturing & Production

| Module | Description |
|---|---|
| `plm_pdf_workorder` | Attach PLM PDF documents to MRP work orders |
| `plm_pdf_workorder_enterprise` | Enterprise variant of the above |
| `plm_project` | Link Odoo Projects to PLM documents and components |
| `plm_consumption_plans` | Reference maintenance and consumption plans for products and BOM lines |

### Purchasing & Sales

| Module | Description |
|---|---|
| `plm_purchase_share` | Share PLM documents with purchase orders |
| `plm_purchase_only_latest` | Restrict purchasing to latest-revision parts only |
| `plm_sale_only_latest` | Restrict sales to latest-revision parts only |
| `plm_product_only_latest` | Enforce latest-revision constraint on products |

### Reporting & Language

| Module | Description |
|---|---|
| `plm_report_language_helper` | Multi-language report helpers |
| `plm_product_description_language_helper` | Product description per language |
| `plm_auto_translator` | Automatic translation of PLM descriptions |

### Misc

| Module | Description |
|---|---|
| `plm_workflow_custom_action` | Custom server actions triggered by PLM state transitions |
| `plm_client_customprocedure` | Custom procedures executed by the CAD client |
| `plm_document_multi_site` | Multi-site document storage |
| `plm_suspended` | Mark components as suspended/obsolete |
| `plm_box` | Document management inside Odoo: nested folders, versions, check out and access rights, on standard Odoo attachments |
| `activity_validation` | Validation workflow using Odoo activities |

### Not an Odoo module

| Folder | Description |
|---|---|
| `mirror_document_server` | Standalone **Flask** service (`flask`, `flask_httpauth`) that mirrors PLM documents to a remote storage node. Used together with `plm_document_multi_site` |
| `documents` | Legacy design documents |

---

## Architecture Overview

### Versioned objects — `revision.plm.mixin`

Every PLM object (product, document, BOM) inherits `plm/models/plm_mixin.py`.
It provides:
- `engineering_code` + `engineering_revision` — unique pair, DB-enforced
- `engineering_state` — lifecycle state machine:
  `draft → confirmed → released ↔ undermodify → obsoleted`
- Write-protection in `confirmed`, `released`, `undermodify`, `obsoleted` states
- Chatter (`mail.thread`) and activity tracking

### Key models

| Model | Role |
|---|---|
| `ir.attachment` | Engineering documents (drawings, CAD files, 3D models) |
| `product.template` / `product.product` | Parts with engineering fields |
| `mrp.bom` | BOMs with engineering state and where-used analysis |
| `plm.checkout` | Document checkout to prevent concurrent CAD editing |
| `plm.cad_open` | CAD editor session tracking |
| `ir.attachment.relation` | Document-to-document relationships (parent/child, 3D tree) |

---

## Installation

The [Docker images](#run-it-with-docker) are the quickest way to a running
server. To add OdooPLM to an Odoo instance you already run, follow this section.

### Requirements

The core `plm` module declares **no external Python dependency** — it installs on
a stock Odoo 19.0, and pulls in `base`, `board`, `product`, `mrp` and
`stock_account`. The extra packages belong to specific optional modules:

| Module | Python packages |
|---|---|
| `plm_automated_convertion` | `ezdxf`, `matplotlib`, `cadquery`, `numpy-stl`, `to-3mf` |
| `plm_pack_and_go` | `base64io` |
| `plm_auto_translator` | `googletrans`, `polib` |
| `mirror_document_server` | `flask`, `flask_httpauth` |

`aaa_requirements.txt` collects the whole set, with the versions the conversion
stack needs pinned:

```bash
pip install -r aaa_requirements.txt
```

### Install from PyPI

The whole suite is published as a single wheel, versioned after the `plm`
module:

```bash
pip install odooplm            # the modules alone
pip install "odooplm[full]"    # with every optional module's dependency
```

Extras follow the modules that declare them: `cad` (the conversion stack),
`pack` (`plm_pack_and_go`), `translate` (`plm_auto_translator`), `full` (all).
The addons land in `odoo/addons`, so they are on the addons path with no
further configuration.

> `cadquery` is installed from git in `aaa_requirements.txt`, because no PyPI
> release carries the OCP build the STEP reader needs. PyPI forbids a URL in a
> wheel's dependencies, so `pip install "odooplm[cad]"` takes the PyPI release
> instead. For server-side conversion, install from `aaa_requirements.txt`.

### Get the source

The 3D and DXF viewer libraries are git submodules, so clone recursively:

```bash
git clone --recurse-submodules -b 19.0 https://github.com/OmniaGit/odooplm.git
```

Add the directory to `addons_path` in `odoo.conf`, restart Odoo and install from
the **Apps** menu, or from the command line:

```bash
# Core only
odoo -d <database> -i plm

# Core, web viewer and server-side conversion
odoo -d <database> -i plm,plm_web_3d,plm_automated_convertion

# A populated PLM to look at — evaluation and training only
odoo -d <database> -i plm_demo
```

---

## Development

```bash
# Auto-reload XML (frontend development)
odoo --dev=xml

# Run all PLM tests
odoo --test-tags=odoo_plm

# Run specific module tests
odoo --test-tags=odoo_plm,odoo_plm_web_revision,plm_automatic_weight
```

Commit message format: `[TAG] | Description` — tags: `FIX`, `ADD`, `IMP`, `MOD`.

Code quality: `pre-commit run --all-files`

The hooks are deliberately small: the checks that find real breakage without
rewriting a line — check-xml, check-yaml, merge and case conflicts, broken
symlinks, debug statements, docstring first — plus flake8 as a report only, and
a local hook that bumps the `__manifest__.py` patch version of every module with
staged changes. The formatters (black, isort, prettier) were dropped: they no
longer install on current Python, and bringing them back means reformatting the
repository in one go. See the comment at the top of `.pre-commit-config.yaml`.

See the [Contributing](https://github.com/OmniaGit/odooplm/wiki/Contributing)
wiki page before opening a pull request.

### Python dependencies are generated

`aaa_requirements.txt` is **generated** — do not edit it. A module's python
packages are declared in the `external_dependencies` of its `__manifest__.py`,
their versions in `scripts/requirements_pins.txt`, and the file is written from
both:

```bash
python3 scripts/sync_requirements.py           # regenerate
python3 scripts/sync_requirements.py --check   # fail if it drifted
```

The pre-commit hook regenerates and stages it whenever a manifest changes, and
the same data feeds `extras_require` in `setup.py`, so the requirements file
and the wheel cannot disagree.

### Releasing

Tag the commit `v19.0.<something>` and `.github/workflows/publish.yml` builds
the sdist and wheel, verifies the requirements file matches the manifests, runs
`twine check` and publishes to PyPI through an OIDC trusted publisher. The
package version is the `plm` module's version, which a pre-commit hook bumps on
every commit so a tag is always publishable.

---

## License

The suite is deliberately split in two.

The core module `plm` is **LGPL-3**: it can be integrated into other products,
including proprietary ones, without those products having to be published.

Every other module is **AGPL-3**: extending them, distributing the result or
serving it over a network carries the obligation to publish the work under the
same licence. The intent is simple — anyone is welcome to build on the core,
and whoever builds a business on top of the extensions gives back what they add.

The licence of each module is declared in its `__manifest__.py`, which is the
authoritative source, and repeated in the header of its sources.

The desktop CAD client is a separate, proprietary product and is not covered by
these licences.

[`LICENSING.md`](LICENSING.md) is the full reference: the module-by-module map,
what the split means for integrators, hosters and researchers, the licensing of
the aggregates (git, PyPI, Docker) and of the vendored third-party components.
The root [`LICENSE`](LICENSE) carries the AGPL-3.0 text, the strongest
obligation present in the aggregate; it does not relicense `plm`.

© OmniaSolutions — https://www.omniasolutions.website
