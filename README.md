# OdooPLM — Product Lifecycle Management for Odoo 18

OdooPLM is a full-featured PLM/PDM suite built as a collection of Odoo 18 addons.
It integrates directly with major CAD editors (SolidWorks, SolidEdge, Inventor,
AutoCAD, FreeCAD, DraftSight) and manages the complete product lifecycle inside Odoo.

## Features

- **Engineering lifecycle** — draft → confirmed → released → under modify → obsoleted
- **Revision control** — unique `(engineering_code, revision)` pairs, full history
- **CAD integration** — checkout/check-in locking, automatic preview images, PDF printouts
- **BOM management** — engineering BOMs with weight calculations, BOM diff tool, BOM aggregation
- **Document management** — version snapshots, backup/restore, multi-site sync
- **3D viewer** — in-browser Three.js based 3D file viewer
- **Activity validation** — structured approval workflows on PLM entities
- **Spare parts, packaging, engineering workflows** — 30+ specialized addons

## CAD Addin

OdooPLM includes a native CAD addin for SolidWorks, SolidEdge, Inventor, AutoCAD,
FreeCAD, DraftSight and ThinkDesign that enables direct synchronization between your
CAD environment and Odoo (checkout/check-in, upload, preview generation).

The CAD addin is distributed separately and can be downloaded from:
- **Download**: https://sourceforge.net/projects/openerpplm/
- **More info**: https://www.omniasolutions.website/odooplm/

## Installation

```bash
pip install odooplm          # base (requires a running Odoo 18 instance)
pip install odooplm[cad]     # + DXF/STL/3MF CAD format conversion
pip install odooplm[3d]      # + CadQuery 3D modelling
pip install odooplm[full]    # everything
```

## Requirements

- Odoo 18.0
- Python ≥ 3.10

## Links

- **Website**: https://odooplm.omniasolutions.website
- **Documentation**: https://odooplm.omniasolutions.website
- **Source**: https://github.com/OmniaGit/odooplm
- **Issues**: https://github.com/OmniaGit/odooplm/issues
- **Support**: info@omniasolutions.eu

## License

LGPL-3
