# CHANGELOG.md
All notable changes to this module will be documented in this file.

## 19.0.1.0.2 - (23-09-2026)

### Fixed

- The Pack and Go archive is downloaded from `/plm_pack_and_go/download/<id>` with a GET, instead of the binary field widget's POST, which failed with "Session expired (invalid CSRF token)" on a page opened before the session was renewed. Only the user who built the archive can download it.

## 19.0.1.0.1 - (08-01-2026)

## [released]
### Added

- Added checkout ZIP export feature (action_create_zip_checkout) to export selected products.
- ZIP includes linked product documents, Json Metadata file.
