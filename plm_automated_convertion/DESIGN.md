# CAD Conversion: design of the new module

Status: **design, not implemented yet** (decisions of 2026-11-14). The module
`plm_automated_convertion` is rewritten after this document; when it is
done, this text becomes its README. Until then the code of the module still
works as the old one (push to the CadWebServer, see "What changes").

## The idea

Odoo never calls a conversion server any more. Every conversion, update of
CAD version and update of CAD attributes is a **job in a queue**. The
**CAD workstations** (CoreBomWeb, a Windows service with the CAD installed)
connect to Odoo, take the jobs they can do, work them in the CAD and send
the result back. Odoo itself keeps doing the conversions it can do alone
(previews, STEP to STL/3MF, DXF): it is the **internal server**.

One product for every customer: the customization made for Nisbau
(`omnia_cad_version_update`: CAD version update of the Inventor files,
DWG/STEP/flat pattern DXF made by a workstation) becomes the standard
behaviour of this module; Nisbau keeps only its data (its Inventor rules,
target version Inventor 2027).

## CAD workstations (the list of servers)

The list of servers **fills itself**: a workstation appears in it the first
time it connects.

- **Identity.** Each CoreBomWeb is known by a GUID, computed as the machine
  UUID of the license (client_utils `get_pc_serial_number()`: the serial
  number of the system disk, else a fingerprint of the network card and the
  CPU). The function is moved out of `license_validator.py` (which needs
  PySide6) into a module without Qt, so that the license keeps the same id.
- **Presentation.** When it starts, and then at every contact, a workstation
  tells Odoo what it can do:
  - its GUID, computer name, CoreBomWeb version;
  - the CADs installed (recognized by their COM ProgID / CLSID), with
    their version;
  - for each CAD, the conversions it can make: start format, end format,
    export mode (one file, one file per model state / configuration, sheet
    metal flat pattern);
  - the other functions it has (CAD version update, CAD attributes update,
    and the ones added later);
  - its work hours (crontab expressions).
- Odoo keeps, per workstation: the last contact (so whether it is alive),
  what it presented, and whether it is **enabled** (the only field set by
  hand, with the groups below).

## Who works a job: workstations and groups

**By default every user can convert, and the first free workstation able to
do the job takes it.**

A large company can tie workstations to **groups of users**: one or more
workstations are linked to one or more groups (`res.groups`).

- A workstation **without groups** is shared: it works the jobs of every user
  who is not served by a workstation of his own groups.
- A workstation **with groups** works only the jobs requested by the users of
  those groups.
- A user who belongs to a group tied to workstations has his jobs worked
  **only by those workstations**: all the users of that group work with the
  same workstations. If those workstations are off, his jobs wait for them;
  they do not move to the shared ones.
- The requester of a job is the user who asked for it: the user of the
  conversion wizard, the user of the check-in for the support files, the
  user who started a massive update.
- Among the workstations allowed for a job, the first free one able to do
  it (its CAD, the conversion, inside its work hours) takes it.

## One conversion command

The conversion wizard of a document comes back as the only command (instead
of the commands made for Nisbau). It offers:

- the conversions the enabled workstations presented for that extension and
  CAD, and the ones Odoo makes alone;
- **update to the target CAD version** for that single file;
- **update the CAD attributes** of that file (see below);
- **conversion templates**: a template sets several conversions at once (for
  example: DWG of the drawing, one STEP per model state, flat pattern DXF).
  A template without owner is predefined, for everybody (made by the
  administrator or loaded by a module); a template with an owner is a
  personal one: **"Save as my template"** in the wizard keeps the
  conversions the user always makes.

The job goes into the queue; the converted file arrives when a workstation
has made it ("download" and "shared folder" are no longer immediate).

## Support files at check-in (option)

Today the CAD client makes the support files at check-in (DWG of a drawing,
STEP, flat pattern DXF), from the list `applicationHook_alternative_check_file_format`
of its CustomProcedure. The CustomProcedure is the client's: its form does
not change. A setting chooses who makes the support files:

- **the client** (as today), or
- **a workstation**: the check-in creates the jobs; the client reads the
  setting and converts nothing at check-in.

When a workstation makes them, Odoo reads the same CustomProcedure the client
uses: the one of the user who checked in, else the one of his PLM groups
(module `plm_client_customprocedure`; at Nisbau it is on the integration
group). Odoo **never runs it**: it imports the client (PyQt4,
`plmintegration`) and can be Python 2 (Nisbau's does not even parse as
Python 3). Odoo takes only the text of that list and reads its literal
values (checked on the Nisbau, Mach and odoov18 CustomProcedures,
2026-11-14). Each entry becomes jobs as the client does:

- `(from, to)`: on a drawing one file; on a part or assembly one file per
  configuration / model state with a component code (export mode per model
  state), one file when it has none;
- `(from, to, 'FlatPattern')`: the sheet metal flat pattern;
- `('', '', function)`: a function of the CustomProcedure (Mach:
  `create_from_category`, the formats of the product category). Odoo cannot
  run it: for these customers the dedicated tool is the conversion rules of
  Odoo by product category (`plm.convert.rule`, to be repaired).

## CAD versions

`plm.cad` / `plm.cad.version` (module `plm`): the CADs, their versions from
2020, and the **target version** of each CAD. A CAD version update opens and
saves the file in the CAD of the workstation and uploads it without
changing the history of the document; the clients download the new file at
the next open.

## CAD attributes from the PLM

The old client command that wrote the PLM values into the CAD properties is
disabled in the client (Client2019 `UpdateAllLevelsDocument`: "Must be
reimplemented"). It comes back as a job of the workstation:

- a table of **CAD attributes**: CAD, name of the CAD property, product or
  document, and where the value comes from: an **Odoo field**, or a
  **Python expression** that computes it from the product or the document
  (evaluated sandboxed, like the output name rule);
- the job carries the values; the workstation writes them into the file
  (CoreBomCad `SetPropertyValuesToDocumentConfiguration`), saves it and
  uploads it without changing the history of the document;
- started from the conversion wizard (also inside a template), from a button
  on the product or the document, or automatically (for example at release).

The mapping for these jobs lives in Odoo; the CustomProcedure is not
touched (it is the client's).

## Menu

**PLM Configuration → CAD Conversion**: Workstations, Formats and rules,
Conversion templates, CAD Versions, Queue, Massive CAD version update.

## What changes

- The push to the CadWebServer goes away: `saveas`, `isalive`, kill
  process, process list, `getAvailableExtention`, the parameter
  `plm_convetion_server` (also used by Pack & Go, which takes the documents
  already converted and queues the missing ones).
- Found broken in 18.0 while reading the code (not run):
  `generateConvertedFiles` (the rules by category, `forceRecursiveConvert`)
  creates queue rows with fields the queue does not have; Pack & Go calls
  `plm.convert.getFileConverted`, which exists only on the queue.

## Order of the work

1. client_utils: the machine UUID without Qt.
2. Odoo 18.0: the new module (workstations and groups, one queue and one
   wizard with templates, menu, check-in rules, CAD attributes), the
   migration of `omnia_cad_version_update`.
3. CoreBomWeb: the presentation to Odoo; the CAD attributes job.
4. Client: it reads the setting and leaves the support files to the
   workstation (the CustomProcedure does not change).
5. Odoo 19.0 and 20.0.
