#!/usr/bin/env python3
"""Copy into plm_web_3d/static/lib the three.js and dxf-viewer files the 3D viewer uses.

three.js and dxf-viewer are git submodules under third_party/, kept so a
developer has their whole source at hand. Odoo serves the copy kept in
plm_web_3d/static/lib/three.js and plm_web_3d/static/lib/dxf-viewer, which is
committed: a clone or a zip without submodules, and the PyPI wheel, still carry
a working viewer.

The files copied are found, not listed by hand:

* every file reached by following the ES module imports from the viewer's own
  code (plm_web_3d/static/src and plm_web_3d/static/lib/odoocad), the bare
  specifier "three" being the import map entry of views/web_template.xml;
* every library file the viewer's code or views name in a string
  (".../plm_web_3d/static/lib/three.js/...", e.g. the measurement font);
* the LICENSE files of the folders they come from.

Files are read from the commit the superproject records for each submodule
(its gitlink in the index), never from the submodule's working tree, so the
copy always matches the recorded commit. Files no longer needed are removed.

When a submodule is not initialized, the copy already committed is checked
instead: the script fails when the viewer needs a file the copy lacks.

Usage, from the repository root:

    python3 scripts/sync_web3d_libs.py             # sync, then git add (pre-commit hook)
    python3 scripts/sync_web3d_libs.py --check     # report only; exit 1 when out of date
    python3 scripts/sync_web3d_libs.py --worktree  # copy from the submodules' working
                                                   # trees, to try an uncommitted library
                                                   # change in the browser; no git add
"""
import argparse
import os
import posixpath
import re
import subprocess
import sys

ADDON = "plm_web_3d"
STATIC_LIB = ADDON + "/static/lib"
# Name of the copy under static/lib -> submodule path.
LIBRARIES = {
    "three.js": "third_party/three.js",
    "dxf-viewer": "third_party/dxf-viewer",
}
# Bare specifiers resolved by the import map of views/web_template.xml.
BARE_SPECIFIERS = {"three": "three.js/build/three.module.js"}
# The viewer's own code, where the search starts.
ENTRY_FOLDERS = [ADDON + "/static/src", STATIC_LIB + "/odoocad"]
# Files that may name a library file by URL.
URL_FOLDERS = ENTRY_FOLDERS + [ADDON + "/views"]
LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt")

IMPORT_RE = re.compile(
    r"""(?:import|export)[^'";]*?from\s*['"]([^'"]+)['"]"""
    r"""|import\s*\(\s*['"]([^'"]+)['"]\s*\)"""
    r"""|^\s*import\s*['"]([^'"]+)['"]""",
    re.MULTILINE,
)
URL_RE = re.compile(
    r"plm_web_3d/static/lib/((?:%s)/[^'\"\s)<>]+)"
    % "|".join(re.escape(name) for name in LIBRARIES)
)


def git(*args, cwd=None):
    return subprocess.run(
        ["git"] + list(args), cwd=cwd, check=True, capture_output=True
    ).stdout


class Source:
    """Reads one library: from the recorded submodule commit, or the copy."""

    def __init__(self, name, submodule, worktree):
        self.name = name
        self.submodule = submodule
        self.worktree = worktree
        self.copy_root = posixpath.join(STATIC_LIB, name)
        self.commit = None
        self.files = None
        self.initialized = os.path.exists(os.path.join(submodule, ".git"))
        if not self.initialized:
            return
        if worktree:
            self.files = set()
            for root, dirs, names in os.walk(submodule):
                dirs[:] = [d for d in dirs if d != ".git"]
                for n in names:
                    rel = os.path.relpath(os.path.join(root, n), submodule)
                    self.files.add(rel.replace(os.sep, "/"))
            return
        entry = git("ls-files", "-s", "--", submodule).decode().split()
        if not entry or entry[0] != "160000":
            sys.exit("%s is not a submodule in the index" % submodule)
        self.commit = entry[1]
        try:
            listing = git("ls-tree", "-r", "--name-only", self.commit, cwd=submodule)
        except subprocess.CalledProcessError:
            sys.exit(
                "%s: commit %s is not in the submodule; run "
                "'git submodule update' first" % (submodule, self.commit)
            )
        self.files = set(listing.decode().splitlines())

    @property
    def from_copy(self):
        return not self.initialized

    def exists(self, rel):
        if self.from_copy:
            return os.path.isfile(os.path.join(self.copy_root, rel))
        return rel in self.files

    def read(self, rel):
        if self.from_copy:
            with open(os.path.join(self.copy_root, rel), "rb") as f:
                return f.read()
        if self.worktree:
            with open(os.path.join(self.submodule, rel), "rb") as f:
                return f.read()
        return git("cat-file", "blob", "%s:%s" % (self.commit, rel), cwd=self.submodule)


def strip_line_comments(text):
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("//")
    )


def own_files(folders, suffixes):
    for folder in folders:
        for root, _dirs, names in os.walk(folder):
            for n in sorted(names):
                if n.endswith(suffixes):
                    yield os.path.join(root, n).replace(os.sep, "/")


def to_library(path):
    """Map a path under static/lib to (library name, path inside it), or None."""
    for name in LIBRARIES:
        prefix = posixpath.join(STATIC_LIB, name) + "/"
        if path.startswith(prefix):
            return name, path[len(prefix) :]
    return None


def collect(sources):
    """Return {library name: set of paths inside it} the viewer needs."""
    needed = {name: set() for name in sources}
    problems = []
    todo = []  # (library name, path inside it, referrer)

    for own in own_files(ENTRY_FOLDERS, (".js",)):
        with open(own, encoding="utf-8") as f:
            text = strip_line_comments(f.read())
        for match in IMPORT_RE.finditer(text):
            spec = next(g for g in match.groups() if g)
            if spec in BARE_SPECIFIERS:
                name, rel = BARE_SPECIFIERS[spec].split("/", 1)
                todo.append((name, rel, own))
            elif spec.startswith("."):
                target = posixpath.normpath(posixpath.join(posixpath.dirname(own), spec))
                hit = to_library(target)
                if hit:
                    todo.append(hit + (own,))
                elif not os.path.isfile(target):
                    problems.append("%s imports %s, which does not exist" % (own, spec))
            else:
                problems.append("%s imports the unknown specifier %s" % (own, spec))

    for own in own_files(URL_FOLDERS, (".js", ".xml")):
        with open(own, encoding="utf-8") as f:
            for match in URL_RE.finditer(f.read()):
                name, rel = match.group(1).split("/", 1)
                todo.append((name, rel, own))

    while todo:
        name, rel, referrer = todo.pop()
        if rel in needed[name]:
            continue
        if not sources[name].exists(rel):
            problems.append("%s needs %s/%s, which is missing" % (referrer, name, rel))
            continue
        needed[name].add(rel)
        if not rel.endswith(".js"):
            continue
        text = strip_line_comments(sources[name].read(rel).decode("utf-8", "replace"))
        for match in IMPORT_RE.finditer(text):
            spec = next(g for g in match.groups() if g)
            here = "%s/%s" % (name, rel)
            if spec in BARE_SPECIFIERS:
                bare_name, bare_rel = BARE_SPECIFIERS[spec].split("/", 1)
                todo.append((bare_name, bare_rel, here))
            elif spec.startswith("."):
                # Resolved as the browser does, from the file's place under
                # static/lib: dxf-viewer imports ../../three.js/src/... of its sibling.
                target = posixpath.normpath(
                    posixpath.join(STATIC_LIB, name, posixpath.dirname(rel), spec)
                )
                hit = to_library(target)
                if hit:
                    todo.append(hit + (here,))
                else:
                    problems.append("%s imports %s, outside the libraries" % (here, spec))
            else:
                problems.append("%s imports the unknown specifier %s" % (here, spec))

    for name, rels in needed.items():
        for rel in list(rels):
            folder = posixpath.dirname(rel)
            while True:
                for license_name in LICENSE_NAMES:
                    candidate = posixpath.join(folder, license_name)
                    if sources[name].exists(candidate):
                        rels.add(candidate)
                if not folder:
                    break
                folder = posixpath.dirname(folder)
    return needed, problems


def copy_state(name):
    root = posixpath.join(STATIC_LIB, name)
    found = set()
    for path in own_files([root], ("",)):
        found.add(path[len(root) + 1 :])
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report only")
    parser.add_argument(
        "--worktree", action="store_true", help="read the submodules' working trees"
    )
    args = parser.parse_args()
    os.chdir(git("rev-parse", "--show-toplevel").decode().strip())

    sources = {
        name: Source(name, submodule, args.worktree)
        for name, submodule in LIBRARIES.items()
    }
    needed, problems = collect(sources)
    if problems:
        print("sync_web3d_libs: the viewer needs files that cannot be found:")
        for problem in sorted(set(problems)):
            print("  " + problem)
        return 1

    changed = []
    for name, source in sources.items():
        if source.from_copy:
            print(
                "sync_web3d_libs: %s is not initialized; the copy in %s/%s holds "
                "every file the viewer needs" % (source.submodule, STATIC_LIB, name)
            )
            continue
        root = posixpath.join(STATIC_LIB, name)
        present = copy_state(name)
        for rel in sorted(needed[name]):
            data = source.read(rel)
            target = posixpath.join(root, rel)
            if rel in present:
                with open(target, "rb") as f:
                    if f.read() == data:
                        continue
            changed.append(target)
            if not args.check:
                os.makedirs(posixpath.dirname(target), exist_ok=True)
                with open(target, "wb") as f:
                    f.write(data)
        for rel in sorted(present - needed[name]):
            target = posixpath.join(root, rel)
            changed.append(target)
            if not args.check:
                os.remove(target)
        if not args.check:
            for folder, _dirs, _names in os.walk(root, topdown=False):
                if not os.listdir(folder):
                    os.rmdir(folder)

    total = sum(len(rels) for rels in needed.values())
    if not changed:
        print("sync_web3d_libs: %d library files, the copy is up to date" % total)
        return 0
    if args.check:
        print("sync_web3d_libs: the copy is out of date:")
        for path in changed:
            print("  " + path)
        return 1
    if not args.worktree:
        git("add", "-A", "--", *[posixpath.join(STATIC_LIB, n) for n in LIBRARIES])
    print(
        "sync_web3d_libs: %d library files, %d copied or removed%s"
        % (total, len(changed), "" if args.worktree else ", added to the index")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
