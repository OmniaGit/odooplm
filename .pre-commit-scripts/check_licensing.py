#!/usr/bin/env python3
"""
Pre-commit hook: keep the licensing of the suite declared and consistent.

LICENSING.md is what an integrator, a compliance office or a reviewer reads
instead of opening every manifest. That only holds if it cannot drift, so this
hook fails the commit when:

- a module has no ``license`` key in its ``__manifest__.py``, or declares one
  outside the two the suite uses (an automated scanner reads "undeclared" as a
  higher risk than any licence you could have picked);
- a module is missing from the LICENSING.md table, is listed there but no
  longer exists, or is listed with a licence its manifest contradicts;
- a licence in use has no full text under ``LICENSES/``, or the root ``LICENSE``
  is gone (which is what makes GitHub and the scanners see the aggregate).

Only the module name and its licence are compared: the summary column is
editorial text, and reformatting it must not fail a commit.

Modules are taken from the git index, so a module added in this very commit is
checked, and a directory that was never committed (a local scratch module) is
ignored.
"""
# The hook runs with language: system, so it gets whatever python3 the developer
# has. Postponed annotations keep `dict[...]` working down to 3.7 — without this
# the script dies on Python 3.9, which is what Debian 11 ships.
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

DOC = "LICENSING.md"
MANIFEST = "__manifest__.py"

# The manifest spelling Odoo uses, mapped to the SPDX identifier LICENSING.md,
# LICENSES/ and the PyPI metadata speak. Both are used in their "or later"
# form, which is what the header of every source file grants.
SPDX = {
    "AGPL-3": "AGPL-3.0-or-later",
    "LGPL-3": "LGPL-3.0-or-later",
}

# | `plm_spare` | AGPL-3.0-or-later | Add spare BOM ... |
# The licence cell may be bolded, as the LGPL core is in the table.
ROW_RE = re.compile(
    r"^\|\s*`([A-Za-z0-9_]+)`\s*\|\s*\*{0,2}([A-Za-z0-9.+-]+)\*{0,2}\s*\|"
)


def repo_root() -> Path:
    out = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
    return Path(out).resolve()


def tracked_manifests(root: Path) -> list[Path]:
    """Manifests known to git, including those staged in this commit."""
    out = subprocess.check_output(
        ["git", "ls-files", "--", "*/" + MANIFEST], text=True, cwd=str(root)
    )
    return [root / line for line in out.split("\n") if line.strip()]


def declared_license(manifest: Path) -> str | None:
    """The ``license`` key, read without importing the manifest."""
    try:
        tree = ast.parse(manifest.read_text(encoding="utf-8"))
        data = ast.literal_eval(tree.body[0].value)
    except (SyntaxError, ValueError, IndexError, AttributeError):
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("license")
    return value if isinstance(value, str) else None


def documented_licenses(doc: Path) -> dict[str, str]:
    """The module → SPDX map as the LICENSING.md table states it."""
    found = {}
    for line in doc.read_text(encoding="utf-8").split("\n"):
        match = ROW_RE.match(line)
        if match and match.group(2) in SPDX.values():
            found[match.group(1)] = match.group(2)
    return found


def main() -> int:
    root = repo_root()
    errors: list[str] = []

    doc = root / DOC
    if not doc.is_file():
        print(f"[check-licensing] {DOC} is missing.")
        return 1

    declared: dict[str, str] = {}
    # Modules whose manifest could not be read: they exist, so reporting their
    # row in LICENSING.md as orphaned on top of the real error is only noise.
    unreadable: set[str] = set()
    for manifest in tracked_manifests(root):
        module = manifest.parent.name
        value = declared_license(manifest)
        if value is None:
            unreadable.add(module)
            errors.append(
                f"{module}: no readable 'license' key in {MANIFEST}. Every module "
                f"must declare one; unless it belongs to the LGPL core it is "
                f"AGPL-3."
            )
            continue
        if value not in SPDX:
            unreadable.add(module)
            errors.append(
                f"{module}: declares license {value!r}, which the suite does not "
                f"use. Expected one of {', '.join(sorted(SPDX))}. Introducing a "
                f"third licence is a deliberate decision: add it to {DOC}, to "
                f"LICENSES/ and to SPDX in this script first."
            )
            continue
        declared[module] = SPDX[value]

    documented = documented_licenses(doc)

    for module in sorted(set(declared) - set(documented)):
        errors.append(
            f"{module}: declares {declared[module]} but is not in the {DOC} "
            f"table. Add the row in this commit:\n"
            f"    | `{module}` | {declared[module]} | <one-line summary> |"
        )

    for module in sorted(set(documented) - set(declared) - unreadable):
        errors.append(
            f"{module}: listed in {DOC} but no tracked module declares it. "
            f"Remove the row if the module is gone."
        )

    for module in sorted(set(declared) & set(documented)):
        if declared[module] != documented[module]:
            errors.append(
                f"{module}: {MANIFEST} says {declared[module]}, {DOC} says "
                f"{documented[module]}. The manifest is authoritative — fix "
                f"whichever of the two is wrong."
            )

    if not (root / "LICENSE").is_file():
        errors.append(
            "LICENSE is missing from the repository root. Without it GitHub and "
            "the compliance scanners report the suite as unlicensed, which "
            "ranks worse than any licence it could have found."
        )

    for spdx in sorted(set(declared.values())):
        if not (root / "LICENSES" / f"{spdx}.txt").is_file():
            errors.append(
                f"LICENSES/{spdx}.txt is missing, but modules are distributed "
                f"under it."
            )

    if errors:
        print("[check-licensing] licensing is inconsistent:\n")
        for error in errors:
            print(f"  - {error}")
        print(f"\n{DOC} is the reference the whole suite is read through.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
