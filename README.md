  # OdoPLM — Product Lifecycle Management for Odoo

  **OdoPLM** is an open-source PLM/PDM extension for [Odoo](https://www.odoo.com/),
  developed and maintained by [OmniaSolutions](https://www.omniasolutions.website).
  It integrates Odoo with the most popular CAD editors and provides document
  management, BOM versioning, revision workflows, and a browser-based 3D/2D viewer.

  > For issues or support: **info@omniasolutions.eu**
  > Full documentation: **https://odooplm.omniasolutions.website**

  ---

  ## CAD Client

  The desktop CAD client (connector) is hosted on SourceForge:

  **https://sourceforge.net/projects/openerpplm/**

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
  (`/plm_document_upload/login`, `/plm_document_upload/upload`, etc.).

  ---

  ## Modules

  ### Core

  | Module | Description |
  |---|---|
  | `plm` | Foundation module — versioned products, engineering documents, BOM lifecycle, checkout system, CAD client REST API |

  ### Document & Viewer

  | Module | Description |
  |---|---|
  | `plm_web_3d` | Browser-based 3D/2D viewer (Three.js). Supports 3MF, STEP, GLTF, STL, OBJ, DXF, SVG. Features: section plane with stencil
  cap, measurement tool (point/face snap), zoom window, part colour and transparency picker with persistence, markup system with chatter
  integration, model screenshot saved as attachment preview |
  | `plm_automated_convertion` | Batch CAD format conversion (STEP→3MF, STEP→STL, STEP→PNG preview). Preserves assembly structure and
  component names |
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
  | `plm_cutted_parts` | Cut parts and raw material management |
  | `plm_auto_engcode` | Auto-generate engineering codes for new parts |
  | `plm_auto_internalref` | Auto-generate internal references |

  ### Manufacturing & Production

  | Module | Description |
  |---|---|
  | `plm_pdf_workorder` | Attach PLM PDF documents to MRP work orders |
  | `plm_pdf_workorder_enterprise` | Enterprise variant of the above |
  | `plm_project` | Link Odoo Projects to PLM documents and components |
  | `plm_consumption_plans` | Consumption plan management for production |

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
  | `plm_box` | Packaging and box management |
  | `activity_validation` | Validation workflow using Odoo activities |
  
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
  
  ### Requirements
  
  ```bash
  pip install -r aaa_requirements.txt

  Key Python dependencies: cadquery, ezdxf, matplotlib, numpy-stl, to-3mf.

  Odoo

  # Install with Odoo
  odoo -d <database> -i plm,plm_web_3d,plm_automated_convertion

  ---
  Development

  # Auto-reload XML (frontend development)
  odoo --dev=xml

  # Run all PLM tests
  odoo --test-tags=odoo_plm

  # Run specific module tests
  odoo --test-tags=odoo_plm,odoo_plm_web_revision,plm_automatic_weight

  Commit message format: [TAG] | Description
  Tags: FIX, ADD, IMP, MOD

  Code quality: pre-commit run --all-files (black, isort, flake8, pylint-odoo, prettier, eslint)

  ---
  License

  LGPL-3 — see individual module manifests for details.

  © OmniaSolutions — https://www.omniasolutions.website
