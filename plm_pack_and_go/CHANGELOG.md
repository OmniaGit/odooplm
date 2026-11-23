# CHANGELOG.md
All notable changes to this module will be documented in this file.

## 20.0.1.0.2 - (16-11-2026)

### Added

- Create zip archive checkout fix checks out every exported document, all or nothing, and adds a manifest (`exported_data.json`) to the zip listing them.
- New "Import zip (check-in)" wizard, opened from a button on the Pack and Go wizard: uploads a zip built by "Create zip archive checkout", replaces each matching document's content in Odoo and checks it back in.
- The import wizard has an preview step ("Load preview"): documents are grouped into 2D/3D/Other tabs, each with a status of Changed or Unchanged (decided by comparing checksums), Not checked out by you, or No matching file in zip, before anything is actually written. "Import" is still available directly, without going through the preview.

## 19.0.1.0.2 - (23-09-2026)

### Fixed

- The Pack and Go archive is downloaded from `/plm_pack_and_go/download/<id>` with a GET, instead of the binary field widget's POST, which failed with "Session expired (invalid CSRF token)" on a page opened before the session was renewed. Only the user who built the archive can download it.

## 19.0.1.0.1 - (08-01-2026)

## [released]
### Added

- Added checkout ZIP export feature (action_create_zip_checkout) to export selected products.
- ZIP includes linked product documents, Json Metadata file.
