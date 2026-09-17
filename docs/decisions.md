# Decision log

Decisions that shaped the suite and are not readable from the code: why a road
was taken, and which ones were left behind. Code shows what was built; this
shows what was chosen.

Each entry: the date it was decided, the decision, why, and what was rejected.

---

## 2026-08-13 — MCP and the OCA/ai repository

### Do not propose a new MCP server module to OCA

**Decision.** Issue [OCA/ai#99](https://github.com/OCA/ai/issues/99), proposing
an `ai_mcp_server` module, was opened and withdrawn the same morning.

**Why.** The module already exists. `ai_oca_mcp` was merged into the 16.0 branch
on 2026-05-15 (PR #68, Dixmit / etobella), with migrations to 17.0 (#85) and
18.0 (#76) open. The earlier search that found "no occurrence of mcp" had looked
only at the 18.0 and 19.0 branches, where the module has not landed yet — a
branch-level absence read as a repository-level one. The roadmap issue #73 also
lists `ai_mcp` as a planned module and states that `ai_tool` is deliberately
structured "to be used by MCP".

**Alternatives rejected.**

- *Publish the proposal and let the community answer.* It would have asked OCA
  to review a proposal for something they had already built and shipped.
- *Propose the tool-declaration decorator as a novel contribution.* `ai_tool`
  already has one — `@aitool(input_schema, output_schema, required_inputs)`,
  which sets `_ai_tool` on the method exactly as our `@mcp_tool` sets
  `_mcp_tool`. The two designs converged independently; neither is news to the
  other.

### Contribute the 19.0 migrations instead

**Decision.** Migrate `ai_tool` ([#101](https://github.com/OCA/ai/pull/101)) and
`ai_oca_mcp` ([#102](https://github.com/OCA/ai/pull/102)) to 19.0, from a fork
at `OmniaGit/ai`.

**Why.** It is the work actually missing: the 19.0 branch carries no modules at
all, and nobody had claimed either one. It is also what makes any later option
real — nothing can be built on `ai_oca_mcp` at 19.0 until `ai_oca_mcp` exists at
19.0.

**Alternatives rejected.**

- *Wait for someone else to migrate them.* The 17.0 and 18.0 migrations have
  been open since June with no movement; waiting had no visible end.
- *Fork `ai_oca_mcp` into this repository.* It would have created a second
  maintained copy of somebody else's module, diverging from the day it landed.

### The PLM tool suite stays in this repository

**Decision.** `plm_mcp` and its 16 tools are not offered to OCA, neither to
`OCA/ai` nor to the `ai-tools` repository proposed in #73.

**Why.** A module in an OCA repository may depend on Odoo core and other OCA
modules. Ours depends on `plm`, which lives here. The tools are also meaningless
without the PLM models — they are about engineering codes, revisions, BOM types
and document relations, not about generic records.

**Alternatives rejected.**

- *Contribute them to the proposed `ai-tools` repository.* Same dependency
  problem, one repository further away.
- *Generalise the tools until they no longer need `plm`.* What would survive is
  a generic ORM wrapper — which is what the ~170 existing Odoo MCP servers
  already are, and the reason none of them can answer an engineering question.

### Base the `ai_oca_mcp` migration on PR #76 rather than redo it

**Decision.** The 19.0 branch replays the history of PR #76, so the 16.0 → 18.0
work of @angelmoya is preserved and credited, and our commit sits on top of it.

**Why.** That PR had already done the view syntax, the whool `pyproject.toml`
and the readme generation. Redoing 16.0 → 19.0 from scratch would have discarded
it and made two contributors' work compete instead of stack.

**Alternatives rejected.**

- *Replay from the 16.0 branch.* Cleaner history on paper, but it throws away
  work that is already correct and already reviewed.

### `readonly=False` belongs in the migration; the cache bucket does not

**Decision.** The migration adds `readonly=False` to the MCP route. It does not
change how `expire_key()` invalidates its cache.

**Why.** Two changes, two different natures. Since 18.0 a route declared
`auth="none"` is served with a read-only cursor unless it says otherwise; the
MCP endpoint writes, so every call was running, failing on the first `INSERT`
and being replayed by the framework with a read/write cursor. Declaring the
route read/write restores the behaviour the module always intended under the new
framework rules — that is what a migration is for, and it is measurable (131 →
119 queries in the module's own tests).

The cache is a different matter. `self.env.registry.clear_cache()` is a faithful
replacement for the removed `clear_cache`: the old one ignored its arguments and
called `model.pool._clear_cache()` anyway, and the new one defaults to the
`default` bucket, where that `ormcache` lives. Making the invalidation narrower
would be a behaviour change, and a migration that changes behaviour stalls in
review.

**Alternatives rejected.**

- *Override `expire_key()` in our own module to restore a "planned" behaviour.*
  There was nothing to restore: the old call was never targeted.
- *Invalidate only the revoked key's entry.* Impossible by construction. The
  cache key is `(server uuid, plaintext token)` and only the SHA-256 is stored;
  computing the key would mean storing the token in clear, which is exactly what
  the hashing exists to avoid.
- *Give the `ormcache` its own cache bucket.* Requires touching `_REGISTRY_CACHES`
  in core. Worth a separate discussion, not a migration.

### Protocol improvements excluded from the migration PRs

**Decision.** `initialize` still answers the hardcoded `2025-03-26`, and `ping`
still falls through to "Method not found". Both are named in the PR description
as future work.

**Why.** A migration PR that also improves the module invites review of two
things at once, and the migration is the part that unblocks other people.

**Alternatives rejected.**

- *Bring `mcp-types` and version negotiation into the migration.* It would add
  a Python dependency to somebody else's module inside a PR they expected to be
  mechanical.

---

## 2026-08-14 — The MCP modules in this repository

### Three modules, committed as they stand

**Decision.** `plm_mcp`, `plm_mcp_ecr` and `plm_mcp_odoo_ai` were committed
(`53f3c08e`) with tests and per-module READMEs explicitly declared as missing in
the commit message, and rows added to `LICENSING.md`.

**Why.** The code was written, reviewed method by method and exercised by hand
against a live database; leaving it untracked was the larger risk. Declaring the
gap in the commit message is what keeps it from being discovered as a surprise.

**Alternatives rejected.**

- *Hold the commit until tests exist.* Weeks of untracked work in a working
  directory, protected by nothing.
- *Commit quietly and open an issue for the tests.* An issue is easier to lose
  than a paragraph in the commit that introduced the gap.

### New modules start at `19.0.1.0.0`

**Decision.** The three manifests were reset to `19.0.1.0.0` before committing.

**Why.** `bump-manifest-version` had raised them on every failed commit attempt
— `plm_mcp` had reached `19.0.1.0.31` without ever being released. A patch
number counts released changes; for a module entering the repository it is zero.

### The commit bypassed the pre-commit hooks, and the hook was not fixed

**Decision.** Committed with `--no-verify`, after running every other hook by
hand. `bump_manifest_version.py` was left untouched.

**Why.** The hook calls `git add` from inside a pre-commit hook. With git 2.30.2
`git commit` already holds `.git/index.lock` while hooks run, so that call
always fails with `check=True` and aborts the commit — deterministically, for
any commit touching a module file other than its manifest. Skipping it was the
only way to commit at all; every substantive check (licensing, xml, merge
conflicts, docstring-first, debug statements, requirements) was run manually and
passed.

The hook itself is repository tooling and its fix — dropping the `git add` and
letting pre-commit report "files were modified by this hook", which is the
framework's own mechanism — is a change to how everyone commits. That is the
maintainer's call, not a side effect of an unrelated commit.

**Alternatives rejected.**

- *Fix the hook inside this commit.* It would bury a change to shared tooling
  inside a feature commit.
- *Keep retrying.* Each attempt bumped every manifest again and committed
  nothing.

### No assistant named in the sources

**Decision.** The `description` of `plm_mcp` and `plm_mcp_odoo_ai` no longer
name a specific AI assistant; they say "any client that speaks the protocol".

**Why.** The point of MCP is that the server does not care which client is
asking. Naming one dates the text and reads as an endorsement.

---

## 2026-09-15 — Module versions are bumped when pushing

**Decision.** The `bump-manifest-version` and `bump-plm-version` commit hooks
are gone. `scripts/push.py` raises the versions of the modules a push carries —
and `plm`, whose version is the pip package's — in one commit, then pushes; the
`check-pushed-versions` pre-push hook refuses a plain `git push` that skipped it.

**Why.** A module version is meant to count what reached the server: bumping at
every commit raised it several times for one delivered change. The commit hook
also could not work with git 2.30.2 — `git commit` holds `.git/index.lock`
while hooks run, so its `git add` failed (see 2026-08-14) — and every failed
attempt bumped the manifests once more. Bumping outside any hook removes that
too. The version a push gives a module is now predictable, the remote one plus
one, which is what an upgrade script folder has to be named after.

**Alternatives rejected.**

- *Bump in the pre-push hook.* A pre-push hook cannot change what is being
  pushed: a commit it creates is left out of the push in progress.
- *A GitHub Action bumping after the push.* It would commit on the server at
  every push, leaving every local clone behind until the next pull.
- *Keep the commit hooks with `require_serial`.* It does not cure the
  `index.lock` failure, and the version would still count commits.

---

## 2026-09-17 — The CAD context is not a permission

### `ir.attachment.read` no longer runs as the superuser

**Decision.** The `sudo()` in `ir.attachment.read`, applied whenever the call
carried the `odooPLM` context and the user was in a PLM group, is gone.

**Why.** Both conditions are met by every CAD client call and every PLM user, so
the escalation was the rule, not the exception: measured on a test database, a
View User read the content of another user's private attachment, and of a
document of a department they are not in, where the same read without the
context was refused. It also went past the company and node isolation added the
day before. What a user may read is what the rules say; the levels and the
`plm.access` nodes now say it properly, which is what the sudo was covering for.

**Alternatives rejected.**

- *Narrow the sudo to PLM documents.* It would still hand every PLM document of
  every company and department to every PLM user.

### `ir.ui.view.search` keeps its sudo

**Decision.** The same context still elevates the search of view definitions
(`plm/models/ir_ui_view.py`).

**Why.** Odoo grants read on `ir.ui.view` to no group but the system one
(`base/security/ir.model.access.csv`), and the CAD client reads the definitions
to build its dialogs. Those are interface metadata, not data.

---

## 2026-09-16 — The four PLM permission levels

### The levels are readonly state, readonly, integration, admin

**Decision.** The PLM groups are a scale: read the released records only, read
everything, read/write/create with deletion of one's own drafts, and everything.
It applies to PLM documents, to components, their templates and their bills of
materials. `group_plm_release_users` and `group_plm_admin_unrelease` stay
service groups, orthogonal to the scale.

**Why.** The groups already carried these names and access rights, but the rules
said something else: "PLM Integration Readonly" implied the integration group,
so the read-only level could write and create; the View User level could write
and delete PLM documents through `group_non_plm_view_plm_document`; and every
integration user could delete any document, released ones included.

### A restriction is a global rule, not a group rule

**Decision.** The released-only level is enforced by global rules
(`plm_readonly_state_*`), one per model, whose domain is empty for every user
outside that level.

**Why.** Record rules of a group are OR-ed: a group rule can only grant. A level
that must see *less* than another cannot be expressed as a group rule at all —
which is exactly how the group ended up granting what its name denied.

**Alternatives rejected.**

- *Give the level its own access rights instead of implying View User.* The same
  dozen access records, copied and kept in step by hand.

### Deleting is for one's own drafts, and for the administrator

**Decision.** An integration user deletes only what they created and only while
it is a draft (`plm_integration_unlink_*`); the administrator deletes anything
(`plm_admin_*`).

**Why.** A released record is history: whoever needs it gone has to be an
administrator. The CAD client never deletes records through RPC, so nothing in
the client flow depends on this.

---

## 2026-09-15 — PLM documents in a multi-company database

### Documents are attached to a tree of `plm.access` nodes

**Decision.** Every company has a root `plm.access` node and may add department
nodes below it. A PLM document is attached to a node; the node says which groups
may read, write, create and delete its documents.

**Why.** Every PLM document was attached to one `plm.access` record for the
whole database, and the record rules on `ir.attachment` never looked at the
company: every user read, wrote and checked out every company's drawings. Odoo
19 already grants an attachment through the record it is attached to, so
giving that record a company and groups uses the core mechanism instead of
repeating a company clause in every PLM rule — it also covers the searches, and
the downloads through `ir.binary`.

**Alternatives rejected.**

- *A company clause and a `plm_share_scope` field on each document*, the 18.0
  approach (`83261af`). The clause has to be repeated in every PLM rule, it
  rests on a `check()` override Odoo 19 never calls, and sharing is decided
  document by document.
- *One `plm.access` per company, 1 to 1.* No room for departments.
- *A many2many between `plm.access` and companies.* Documents could become more
  visible than their products, which have a single company or none.

### Groups are inherited until a node redefines them

**Decision.** For each permission a node either names its groups or names none
and takes its parent's; a root naming none leaves the whole company open. The
record rules read the resolved, stored `effective_*_group_ids`.

**Alternatives rejected.**

- *Additive inheritance* (a group on a node counts for every descendant). Once a
  root is open to the company no branch below can be restricted.
- *Restrictive inheritance* (every node of the path must allow the user). It
  works, but each rule has to walk every ancestor, and it is harder to explain.

A node a user can read may sit under one they cannot: the hierarchy view does
not reach it, the list view does. Accepted: the tree is the administrator's
tool, and forbidding it would take away what this inheritance model is for.

### No bypass for the PLM administrator

**Decision.** The PLM administrator sees the documents of the companies and
departments they belong to, as any user; they manage every node of their
companies through `plm.access.write`.

**Alternatives rejected.**

- *See every company, as in 18.0.* The administrator would see documents whose
  products and bills of materials the company rules still hide.

### Products keep the standard Odoo company

**Decision.** A product created by the CAD client or in PLM gets no company,
unless one is set on it, exactly as in standard Odoo; only documents are placed
in the company chosen at login.

**Why.** It is how Odoo itself treats products. A product with a company can
only be a component of that company's bills of materials, so components used
across companies would have to be made shared one by one, or the CAD client
would fail saving the BoM.

**Alternatives rejected.**

- *A new component takes the active company*, as the 18.0 commit `83261af`
  did, with a setting to keep components shared. Possible later, together with
  the shared tree for commercial components (see Open).

### Users outside the PLM groups see no PLM document

**Decision.** A rule for `base.group_user` confines every internal user to the
attachments that are not PLM documents; the PLM rules add the documents back for
the PLM groups.

**Why.** Group rules only restrict the users of the group: an internal user in
no PLM group had no rule at all and read and downloaded every PLM document.

---

## 2026-09-15 — Engineering codes in a multi-company database

### A code is unique in the whole database, visible only to its company

**Decision.** Two companies cannot create the same engineering code and
revision; a code is seen only by the users of the company that holds it. The
checks that decide whether a code exists, or which revision is the latest, look
past the record rules (`sudo()`); their message is generic and does not name the
other company. What users are shown keeps following the record rules.

**Why.** The unique index was on `ir_attachment` only: `product_template`
overrode `init` without calling the mixin's, so for products nothing but a
Python `search_count` stood between two companies and the same code, and that
search only saw the user's companies. A company could create a code another one
already had, silently. The index now exists on every table of the mixin, and
the existence checks see every company.

**Alternatives rejected.**

- *Codes unique per company.* The index, the constraint and the ~60 searches by
  code — CAD client doors included — would all have to carry the company.
- *Name the company holding the code in the message.* It tells a user something
  about a company they have no access to.

### One rule for the index: a set code

**Decision.** The index condition is `engineering_code IS NOT NULL`. `''` and
`'-'` are stored as `False` by the mixin, and turned to NULL on existing data.

**Why.** The old condition, `IS NOT NULL OR NOT IN ('-','')`, already meant
`IS NOT NULL` — the second half never excluded anything — while reading as if
placeholders were exempt. Those placeholders date from when cloning and revising
needed codes that skipped the checks; neither does any more, and no database
examined holds one.

### The revisions of a code share its company

**Decision.** Every revision of a product code belongs to the same company. A
revision created without a company joins the one of the existing revisions; a
product changes company only while it is a draft with no bill of materials, not
used in one, and with no linked document.

**Why.** If a user sees one revision, they see the whole chain: the searches
that walk revisions (`_getlastrev`, the revision chain rule) stay consistent
without being rewritten. Past draft, or once something is bound to it, moving a
product would leave its BoMs and documents in the old company.

**Alternatives rejected.**

- *Propagate a company change to every revision.* It writes records the user
  may not see, without saying so.

### A database holding duplicates is updated without the index

**Decision.** When the unique index cannot be created because of duplicates,
the update goes on, the index is not created and the duplicate codes are logged;
the next update creates it once they are fixed.

**Alternatives rejected.**

- *Stop the update.* It would block a customer's upgrade on data only they can
  fix.

---

## 2026-09-15 — Sequences in a multi-company database

### The PLM sequences are global

**Decision.** Every sequence the PLM modules create — the ones in
`plm/data/sequence.xml`, `plm_auto_engcode/data/ir_sequence.xml`,
`plm_box/data/plm_box_sequence_data.xml`, and the `PLM_SEQUENCE_<prefix>` ones
`product.template.getSequenceFrom` makes on the fly — has `company_id` False:
one counter, shared by every company. A company gets its own numbering only if
an administrator gives it one explicitly, by copying the sequence and setting
the company on the copy. `next_by_code` orders by `company_id`, so the copy of
the current company wins over the global sequence.

**Why.** `ir.sequence.company_id` defaults to `env.company`, so the sequences
declared without a company were bound to the company the module was installed
in, and `next_by_code` — which looks only for the current company's sequence or
a global one — returned `False` everywhere else: `GetNextDocumentName` raised
`TypeError`, a cloned document got the code `XXX-False`, `plm_auto_engcode`
gave products no code. A global counter is also what the database-wide unique
index on `(engineering_code, engineering_revision)` needs: two companies
counting from 1 with the same prefix would collide on it. `plm_breakages`
already declared its sequence this way.

Databases installed before are brought in line by an upgrade script per module
(`upgrades/<version>/post-migrate.py`), since the records are `noupdate`. It
runs once and only on the sequences the modules created; tests are tagged
`odoo_plm_multicompany`.

**Alternatives rejected.**

- *A `<function>` in the data file resetting the company.* It would run at
  every update and undo a company an administrator set on purpose.
- *Create the sequences per company automatically.* Without a prefix per
  company the codes collide on the unique index; see Open.

---

## Open

Not decided yet, recorded so the question is not lost.

- **A company flag to create its own PLM sequences automatically.** When set, the
  new company would get a copy of the PLM sequences. It only works with a
  prefix per company (a field on the company, prepended to the sequence
  prefix), or with engineering codes unique per company rather than
  database-wide, which is still to be decided. Not a priority: the documented
  manual copy reaches the same result.
- **A shared `plm.access` tree with no company**, for commercial components used
  by every company: a product with no company is visible everywhere, but its
  documents live in one company's tree. To take up when the module description
  is updated.

- **Whether `plm_mcp` should sit on `ai_oca_mcp` instead of carrying its own
  transport.** It would cost two OCA dependencies and give up the protocol
  handling we control, in exchange for call logging, key expiry and per-server
  tool curation, which we lack. The question only becomes real once #101 and
  #102 are merged.
- **Whether `plm_mcp` belongs in the PyPI package.**
- **Whether the database should be named in the URL** (`/plm/mcp/<db>`) instead
  of the `X-Odoo-Database` header.
