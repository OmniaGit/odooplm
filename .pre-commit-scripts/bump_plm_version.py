#!/usr/bin/env python3
"""Pre-commit hook: keep plm/__manifest__.py ahead of the published release.

The version of the core plm module is the version of the `odooplm` pip package
(setup.py reads it from there). PyPI refuses to accept a version it already
holds, so a tag built on an unchanged plm version cannot be published — and the
failure only shows up at release time, long after the commit that caused it.
Bumping it on every commit keeps any tag publishable.

This runs alongside bump_manifest_version.py, which bumps the modules that
actually changed. When that hook has already bumped plm, or a developer set the
version by hand, the manifest differs from HEAD and this hook leaves it alone —
so the two never double-bump.

Version format: {odoo}.{odoo_minor}.{major}.{minor}.{patch}
                 e.g.  19.0.1.0.12  ->  19.0.1.0.13
"""

from __future__ import annotations

import re
import subprocess
import sys

MANIFEST = "plm/__manifest__.py"
VERSION_RE = re.compile(r'("version"\s*:\s*")(\d+\.\d+\.\d+\.\d+\.)(\d+)(")')


def version_of(content):
    match = VERSION_RE.search(content)
    return match.group(2) + match.group(3) if match else None


def committed_version():
    """The version in HEAD, or None when it cannot be read (first commit)."""
    result = subprocess.run(
        ["git", "show", "HEAD:" + MANIFEST],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return version_of(result.stdout)


def main():
    with open(MANIFEST, encoding="utf-8") as fobj:
        content = fobj.read()

    match = VERSION_RE.search(content)
    if not match:
        sys.stderr.write("ERROR: could not parse the version in {}\n".format(MANIFEST))
        return 1

    current = version_of(content)
    committed = committed_version()
    if committed is not None and current != committed:
        # Already moved in this commit — by the per-module hook or by hand.
        return 0

    old_patch = int(match.group(3))
    new_patch = old_patch + 1
    updated = content[: match.start(3)] + str(new_patch) + content[match.end(3) :]

    with open(MANIFEST, "w", encoding="utf-8") as fobj:
        fobj.write(updated)

    subprocess.run(["git", "add", MANIFEST], check=True)
    print(
        "plm version bumped: {}{}  ->  {}{}".format(
            match.group(2), old_patch, match.group(2), new_patch
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
