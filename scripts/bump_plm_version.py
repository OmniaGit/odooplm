#!/usr/bin/env python3
"""Pre-commit hook: bump the patch segment of plm/__manifest__.py version.

The plm module is the app root whose version drives the pip package version.
It must be incremented on every commit regardless of which modules changed.
Version format: {odoo}.{odoo_minor}.{major}.{minor}.{patch}
                 e.g.  18.0.21.0.4  →  18.0.21.0.5
"""
import re
import subprocess
import sys

MANIFEST = "plm/__manifest__.py"

with open(MANIFEST) as f:
    content = f.read()

match = re.search(r'("version"\s*:\s*")(\d+\.\d+\.\d+\.\d+\.)(\d+)(")', content)
if not match:
    print("ERROR: could not parse version in {}".format(MANIFEST))
    sys.exit(1)

old_patch = int(match.group(3))
new_patch = old_patch + 1
new_content = content[: match.start(3)] + str(new_patch) + content[match.end(3) :]

with open(MANIFEST, "w") as f:
    f.write(new_content)

subprocess.run(["git", "add", MANIFEST], check=True)
print(
    "plm version bumped: {}{}  →  {}{}".format(
        match.group(2), old_patch, match.group(2), new_patch
    )
)
