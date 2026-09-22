#!/usr/bin/env python3
"""Bump the version of the modules a push carries, then push.

A module version counts what reached the server, not what was committed
locally: three commits on plm pushed together raise it once. So the versions
are raised here, right before pushing, and not by a commit hook.

For the commits between the remote branch and HEAD this script:

* finds the modules they touch (the directories owning a ``__manifest__.py``);
* raises the patch number of each one whose version is still the remote one —
  a version already raised by hand is left as it is;
* always raises ``plm`` when it is not already ahead: its version is the
  version of the ``odooplm`` pip package, and PyPI refuses a version it already
  holds, so a tag built on an unchanged plm version could not be published;
* commits the manifests it changed in one commit, and pushes.

An upgrade script is therefore named after the remote version plus one:
``upgrades/19.0.1.0.30/`` for a module that is ``19.0.1.0.29`` on the remote.

The same file is the ``pre-push`` hook (``--check``): it refuses a push that
carries a module whose version is not higher than the remote one, so a plain
``git push`` cannot skip the bump.

Usage::

    python3 scripts/push.py                 # bump, commit, git push origin <branch>
    python3 scripts/push.py --dry-run       # only print what would be bumped
    python3 scripts/push.py -- --force-with-lease   # extra arguments for git push
    python3 scripts/push.py --check         # the pre-push hook
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

MANIFEST = "__manifest__.py"
PLM = "plm"
VERSION_RE = re.compile(r'("version"\s*:\s*")(\d+(?:\.\d+)*)(")')
NULL_SHA = "0" * 40


def git(*args, check=True):
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit("git %s failed" % " ".join(args))
    return result


def version_at(ref, module):
    """The version of *module* in *ref*, as a tuple; None if it is not there."""
    result = git("show", "%s:%s/%s" % (ref, module, MANIFEST), check=False)
    if result.returncode != 0:
        return None
    match = VERSION_RE.search(result.stdout)
    return tuple(int(part) for part in match.group(2).split(".")) if match else None


def changed_modules(base, head):
    """Top level modules with files changed between *base* and *head*."""
    names = git("diff", "--name-only", base, head).stdout.split()
    modules = set()
    for name in names:
        top = name.split("/", 1)[0]
        if "/" in name and version_at(head, top) is not None:
            modules.add(top)
    return modules


def modules_to_bump(base, head):
    """The modules the push from *base* to *head* carries whose version is not
    higher than in *base*. Modules new in *head* start at their own version."""
    modules = changed_modules(base, head)
    if git("rev-list", "--count", "%s..%s" % (base, head)).stdout.strip() != "0":
        modules.add(PLM)
    late = []
    for module in sorted(modules):
        before = version_at(base, module)
        after = version_at(head, module)
        if before is not None and after is not None and after <= before:
            late.append(module)
    return late


def bump(module, write=True):
    path = os.path.join(module, MANIFEST)
    with open(path, encoding="utf-8") as fobj:
        content = fobj.read()
    match = VERSION_RE.search(content)
    parts = match.group(2).split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    new = ".".join(parts)
    if write:
        with open(path, "w", encoding="utf-8") as fobj:
            fobj.write(content[: match.start(2)] + new + content[match.end(2) :])
    return match.group(2), new


def push(args):
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch == "HEAD":
        raise SystemExit("Detached HEAD: check out the branch to push.")
    remote_ref = "%s/%s" % (args.remote, branch)
    git("fetch", args.remote, branch)
    if git("merge-base", "--is-ancestor", remote_ref, "HEAD", check=False).returncode:
        raise SystemExit("%s has commits HEAD lacks: pull first." % remote_ref)

    late = modules_to_bump(remote_ref, "HEAD")
    if not late:
        print("Nothing to bump.", flush=True)
    for module in late:
        old, new = bump(module, write=False)
        print("%-40s %s -> %s" % (module, old, new), flush=True)
    if args.dry_run:
        return 0
    if late:
        manifests = ["%s/%s" % (m, MANIFEST) for m in late]
        dirty = git("status", "--porcelain", "--", *manifests).stdout
        staged = git("diff", "--cached", "--name-only").stdout
        if dirty or staged:
            raise SystemExit(
                "Staged changes, or uncommitted manifests of the modules to bump:"
                " commit or stash them first.\n" + (dirty or staged)
            )
        for module in late:
            bump(module)
        git("add", "--", *manifests)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "[MOD] | Bump the versions of the modules changed since %s"
                % remote_ref,
                "--",
                *manifests,
            ],
            check=True,
        )
    return subprocess.run(
        ["git", "push", args.remote, branch, *args.push_args], check=False
    ).returncode


def check():
    """pre-push hook. pre-commit passes the refs of the push in the environment."""
    local = os.environ.get("PRE_COMMIT_TO_REF")
    remote = os.environ.get("PRE_COMMIT_FROM_REF")
    if not local or not remote or NULL_SHA in (local, remote):
        # A deleted branch, or a new one: no remote version to compare with.
        return 0
    if git("cat-file", "-e", remote, check=False).returncode:
        sys.stderr.write("The remote commit is not known locally: fetch first.\n")
        return 1
    late = modules_to_bump(remote, local)
    if not late:
        return 0
    sys.stderr.write(
        "The version of these modules is not higher than on the remote:\n  %s\n"
        "Push with  python3 scripts/push.py  to bump them first.\n"
        % "\n  ".join(late)
    )
    return 1


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true", help="pre-push hook mode")
    parser.add_argument("push_args", nargs="*", help="extra arguments for git push")
    args = parser.parse_args(argv)
    return check() if args.check else push(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
