# Licensing

This document is the single reference for the licensing of the OdooPLM suite.
It exists so that nobody — an integrator, a compliance office, a reviewer — has
to open 36 manifests to reconstruct the answer.

## In short

The suite is deliberately split in two.

- The core module **`plm` is LGPL-3.0-or-later**. It can be integrated into
  other products, including proprietary ones, without those products having to
  be published.
- **Every other module is AGPL-3.0-or-later**. Extending them, distributing the
  result or serving it over a network carries the obligation to publish the work
  under the same licence.

The repository as a whole, and every artefact that bundles it, is therefore an
aggregate that contains both licences. The root `LICENSE` file carries the
AGPL-3.0 text because that is the strongest obligation present in the aggregate;
it does **not** relicense `plm`, which stays LGPL as declared in its manifest.

Both licences are used in their *or-later* form: the header of every source file
grants the terms of "either version 3 of the License, or (at your option) any
later version".

## Why the split

The intent is simple: anyone is welcome to build on the core, and whoever builds
a business on top of the extensions gives back what they add.

The LGPL core is the open door. It is what makes a third-party ecosystem
possible — CAD connectors, vertical customisations and commercial products can
link against `plm` without being forced open. The AGPL extensions are the fence:
they protect the differentiating functionality from being taken, hosted as a
service and never returned.

It is the same arrangement Odoo itself uses — an LGPL core with modules on top —
and it is a deliberate open-core boundary, not an ambiguity.

## Module map

The `license` key of each `__manifest__.py` is the authoritative declaration for
that module, and is repeated in the header of its sources. This table is
generated from those manifests.

| Module | Licence (SPDX) | Summary |
|---|---|---|
| `activity_validation` | AGPL-3.0-or-later | Engineering change requests and orders: modification requests from Odoo and from the CAD |
| `plm` | **LGPL-3.0-or-later** | PLM, PDM and engineering document management, integrated with the main CAD editors |
| `plm_auto_engcode` | AGPL-3.0-or-later | This Module Create Part Number for PLM Automatic Engineering Code |
| `plm_auto_internalref` | AGPL-3.0-or-later | This Module Create Auto Internal Reference |
| `plm_auto_translator` | AGPL-3.0-or-later | PLM Auto Translator |
| `plm_automate_normal_bom` | AGPL-3.0-or-later | Allow to create normal boms if not exists and product are released |
| `plm_automated_convertion` | AGPL-3.0-or-later | CAD editors batch conversion tool |
| `plm_automatic_weight` | AGPL-3.0-or-later | PLM Weight Automatic Calculation |
| `plm_bom_summarize` | AGPL-3.0-or-later | Summarize bom when client upload it |
| `plm_box` | AGPL-3.0-or-later | Document management inside Odoo: nested folders, versions, check out and access rights |
| `plm_breakages` | AGPL-3.0-or-later | PLM Breakages |
| `plm_client_customprocedure` | AGPL-3.0-or-later | PLM Client Custom Procedure |
| `plm_compare_bom` | AGPL-3.0-or-later | Allow to compare two boms |
| `plm_consumption_plans` | AGPL-3.0-or-later | Manage reference maintenance and consumption plans for products and BoM lines |
| `plm_cutted_parts` | AGPL-3.0-or-later | Manage bom explosion for cutted parts |
| `plm_date_bom` | AGPL-3.0-or-later | Allow to compute boms due to date |
| `plm_demo` | AGPL-3.0-or-later | A populated PLM environment to look at, instead of an empty one |
| `plm_document_multi_site` | AGPL-3.0-or-later | Multi site document management: synchronise engineering documents between plants |
| `plm_engineering` | AGPL-3.0-or-later | Allow to use engineering boms |
| `plm_ent_breakages_helpdesk` | AGPL-3.0-or-later | PLM Breakages, connected to Helpdesk |
| `plm_pack_and_go` | AGPL-3.0-or-later | Download BOM structure files from a component |
| `plm_pdf_workorder` | AGPL-3.0-or-later | Engineering document management on the shop floor: the PLM 2D drawing in the work order |
| `plm_pdf_workorder_enterprise` | AGPL-3.0-or-later | The PLM pdf document available into the workorder workspace |
| `plm_product_description_language_helper` | AGPL-3.0-or-later | PLM Product Description Language Helper |
| `plm_product_only_latest` | AGPL-3.0-or-later | Show only latest product version in production |
| `plm_project` | AGPL-3.0-or-later | Connect odoo project with odooPLM |
| `plm_purchase_only_latest` | AGPL-3.0-or-later | Show only latest product version in purchase |
| `plm_purchase_share` | AGPL-3.0-or-later | Supplier document sharing: engineering documents of a purchase order from the portal |
| `plm_report_language_helper` | AGPL-3.0-or-later | Manage multilanguage PLM reports |
| `plm_sale_only_latest` | AGPL-3.0-or-later | Show only latest product version in sale |
| `plm_spare` | AGPL-3.0-or-later | Add spare BOM and Spare Parts Manual |
| `plm_suspended` | AGPL-3.0-or-later | Add a suspended state to the engineering workflow, for products and documents |
| `plm_web_3d` | AGPL-3.0-or-later | View 3D model files and 2D documents in Odoo |
| `plm_web_3d_sale` | AGPL-3.0-or-later | 3D product previews on the e-commerce pages, from the engineering models |
| `plm_web_revision` | AGPL-3.0-or-later | PLM Revision from web side |
| `plm_workflow_custom_action` | AGPL-3.0-or-later | Custom automated actions on the engineering workflow of parts and documents |

36 modules: 1 LGPL-3.0-or-later, 35 AGPL-3.0-or-later.

### Code outside the modules

`mirror_document_server/` is a standalone document-mirroring service, not an
Odoo module, and carries AGPL headers. Development utilities at the root of the
repository (`scripts/`, `step_tree_viewer.py`) and any file without an explicit
header fall under the repository default, AGPL-3.0-or-later.

## What this means in practice

**If you integrate OdooPLM into your own product.** Depending on `plm` alone —
calling it, extending it, linking against it — puts you under the LGPL. You must
publish your modifications *to `plm` itself* and let your users relink against a
modified `plm`, but the product you build around it stays yours. The moment you
depend on any other module in the table, the AGPL applies to your work.

**If you host OdooPLM as a service.** The AGPL's network clause is the point of
the split. If you run any of the AGPL modules — modified or extended — and let
users interact with it over a network, those users are entitled to the
corresponding source of what you run. Running the suite unmodified for your own
company triggers no publication duty.

**If you use OdooPLM in research.** Both licences permit use, modification and
redistribution for research, with the publication duties above. See *Citing this
software* below for the availability statement.

**The desktop CAD client** is a separate, proprietary product of OmniaSolutions
and is not covered by these licences. It communicates with the suite through the
documented REST API of `plm/controllers/main.py`.

## Aggregates

Any artefact that bundles the suite — the git repository, the `odooplm` PyPI
sdist and wheel, the Docker image — contains both licences. The PyPI package is
the one exception to completeness: it leaves out `plm_demo`, an evaluation
module that has no place on the production database a pip install targets. That
changes what is shipped, not under what terms.

Redistributing such an aggregate means honouring the AGPL for the modules that
carry it and the LGPL for `plm`. The per-module declaration always governs; the
aggregate label is the strongest obligation contained, never a relicensing of
the parts.

## Licence texts

Full texts live in `LICENSES/`:

- `LICENSES/AGPL-3.0-or-later.txt` — also copied to the root as `LICENSE`, so
  that GitHub and automated scanners detect the aggregate.
- `LICENSES/LGPL-3.0-or-later.txt` — the LGPLv3 supplement, which grants
  additional permissions on top of the GPLv3 and has no meaning without it.
- `LICENSES/GPL-3.0-or-later.txt` — included because the LGPL above incorporates
  it by reference. No part of this suite is offered under the plain GPL.

All three are the verbatim texts published by the Free Software Foundation.

## Third-party components

These are vendored as git submodules. They keep their own licences, which are
compatible with the above and are not changed by inclusion here.

| Component | Location | Licence |
|---|---|---|
| three.js | `plm_web_3d/static/src/js/lib/three.js` | MIT |
| dxf-viewer (OmniaGit fork) | `plm_web_3d/static/src/js/lib/dxf-viewer` | MPL-2.0 |
| CadQuery | `plm_automated_convertion/cadquery` | Apache-2.0 |

Python dependencies declared in the manifests' `external_dependencies` and
collected in `aaa_requirements.txt` are not distributed with this repository and
carry their own upstream licences.

## Citing this software

> OdooPLM — Product Lifecycle Management for Odoo. OmniaSolutions.
> https://github.com/OmniaSolutions/OdooPLM
> Core module `plm` licensed under LGPL-3.0-or-later; all other modules under
> AGPL-3.0-or-later.

## Adding a module

A new module must declare `"license"` in its `__manifest__.py` and repeat it in
the header of its sources. Unless it is part of the LGPL core, it is
AGPL-3.0-or-later. This table must be updated in the same commit.

That last part is not left to memory: the `check-licensing` pre-commit hook
(`.pre-commit-scripts/check_licensing.py`, also run in CI) fails the commit when
a module declares no licence, declares one the suite does not use, is missing
from the table above, is listed there after being removed, or is listed with a
licence its manifest contradicts. Manifests are read from the git index, so a
module added in the same commit is checked too.

---

© OmniaSolutions — https://www.omniasolutions.website
