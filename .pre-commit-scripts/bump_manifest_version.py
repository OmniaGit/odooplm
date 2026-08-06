#!/usr/bin/env python3
"""
Pre-commit hook: bump the patch (last) component of the version string in
__manifest__.py for every Odoo module that has staged changes.

Rules:
- Only files staged for the current commit are considered.
- If the ONLY staged file in a module is __manifest__.py itself, it is skipped
  (the user edited the version manually; we must not override it).
- Only the standard OCA five-part format  MAJOR.MINOR.SERIES.MINOR.PATCH  is
  handled; other formats are left untouched.
- The updated manifest is staged automatically so the bump is part of the commit.
"""
# The hook runs with language: system, so it gets whatever python3 the developer
# has. Postponed annotations keep `Path | None` and `dict[...]` working down to
# 3.7 — without this the script dies on Python 3.9, which is what Debian 11 ships.
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MANIFEST = "__manifest__.py"
# Matches:  "version": "19.0.1.0.7"
#            ^^^^^^^^^^^^^^^^  ^^  ^
#            prefix group      4th  patch
VERSION_RE = re.compile(
    r'("version"\s*:\s*")(\d+\.\d+\.\d+\.\d+\.)(\d+)(")'
)


def repo_root() -> Path:
    out = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
    return Path(out).resolve()


def find_module_root(file_path: Path, root: Path) -> Path | None:
    """Walk up from *file_path* until a directory that owns a __manifest__.py."""
    current = file_path.resolve().parent
    while True:
        if (current / MANIFEST).is_file():
            return current
        if current == root or current == current.parent:
            return None
        current = current.parent


def bump_version(manifest_path: Path) -> bool:
    """Increment the patch number in-place. Returns True when the file changed."""
    text = manifest_path.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if not match:
        return False  # non-standard format — skip

    new_text = VERSION_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2)}{int(m.group(3)) + 1}{m.group(4)}",
        text,
        count=1,
    )
    if new_text == text:
        return False  # already at that value (shouldn't happen)

    manifest_path.write_text(new_text, encoding="utf-8")
    return True


def staged_files(root: Path) -> set[Path]:
    """Paths staged for the current commit."""
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], text=True
    )
    return {(root / line).resolve() for line in out.split("\n") if line.strip()}


def main(argv: list[str]) -> int:
    root = repo_root()

    # pre-commit hands over whatever it was asked to check, which on a
    # `--all-files` run — what the CI workflow does — is the entire repository.
    # Bumping every manifest there would be wrong, so the argument list is
    # intersected with what is actually staged: nothing staged, nothing bumped.
    staged = staged_files(root)
    if not staged:
        return 0

    # Group staged files by their module root.
    # key: module root Path  →  value: set of staged paths inside that module
    module_files: dict[Path, set[Path]] = {}
    for raw in argv:
        path = Path(raw).resolve()
        if path not in staged:
            continue
        module = find_module_root(path, root)
        if module is None:
            continue
        module_files.setdefault(module, set()).add(path)

    bumped: list[Path] = []
    for module, files in sorted(module_files.items()):
        manifest = module / MANIFEST

        # Skip if the only staged file in this module is the manifest itself
        # (the developer edited the version by hand).
        non_manifest = files - {manifest.resolve()}
        if not non_manifest:
            continue

        if bump_version(manifest):
            subprocess.run(["git", "add", "--", str(manifest)], check=True)
            bumped.append(manifest.relative_to(root))

    if bumped:
        print(
            "[bump-manifest-version] version bumped in:",
            ", ".join(str(p) for p in bumped),
        )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
