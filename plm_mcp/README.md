# PLM MCP Server

Ask the engineering database questions, from an AI assistant, in the language
engineers use.

OdooPLM already knows where a part is used, what changed between two revisions,
which components still have no drawing and who has a file checked out. This
module makes that knowledge reachable over the [Model Context
Protocol](https://modelcontextprotocol.io), so any MCP client can ask — and get
an answer from the live database instead of a plausible guess.

```
> which components of BRG-HSG-001 are steel?
> what breaks if I change CLP-020-001?
> how many parts of BASE-100 have a 3D model but no drawing?
> what did revision 1 change in this BOM?
```

## What makes it different from a generic Odoo MCP server

There are many MCP servers that expose the Odoo ORM: `search_read` with a coat
of paint. They can fetch a record, and they cannot answer any of the questions
above, because the answers are not in a record — they are in the relations
between parts, revisions, BOMs and documents.

The 14 tools here are engineering questions, not ORM operations. Each returns
what a person would need to read, with the counts that make it comparable.

## Installing

Requires the `mcp-types` package:

```bash
pip install mcp-types
```

Then install `plm_mcp` from the *Apps* menu, or:

```bash
odoo -d <database> -i plm_mcp
```

## Issuing a key

*PLM → Configuration → MCP Keys → New*. Give it a name and the user its calls
should run as, then save.

**The token is shown once.** It is not stored — only its SHA-256 is — so if it
is lost the only way forward is to regenerate, which invalidates the previous
one immediately.

The user matters more than it looks: every tool call runs in that user's
environment, so the PLM record rules that apply to the person apply to the
agent. There is no second permission model to keep in step, and no way for a key
to reach further than the person it was issued for.

## Connecting a client

| | |
|---|---|
| **URL** | `https://<your-odoo>/plm/mcp` |
| **Transport** | Streamable HTTP (POST) |
| **Authentication** | `Authorization: Bearer <token>` |
| **Database** | `X-Odoo-Database: <database>` on a multi-database server |

```bash
curl -s https://odoo.example.com/plm/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

> Clients that require OAuth 2.0 for remote servers cannot connect directly.
> A bridge that presents the bearer token on their behalf works.

## The tools

**Finding and reading a part**

| Tool | Answers |
|---|---|
| `plm_find_part` | "give me the steel parts", "which codes are cast" — search by code, name, material, surface, treatment, category or tag |
| `plm_part_detail` | everything about one part: title block, catalogue, features, documents, and whether this is the current revision |
| `plm_list_materials` | which materials are actually in use, and how often |
| `plm_list_finishings` | the same, for surface finishes |
| `plm_list_treatments` | the same, for treatments |

**Structure**

| Tool | Answers |
|---|---|
| `plm_bom` | walk a bill of material down as many levels as asked |
| `plm_where_used` | every assembly a part is used in, **grouped by revision** — because "used in" is a different answer for revision 0 and revision 1 |
| `plm_compare_bom` | what changed between two BOMs: added, removed, quantity changed, revision changed |
| `plm_spare_parts` | the spare parts of a product, kits included, with total quantities |

**Documents**

| Tool | Answers |
|---|---|
| `plm_documents` | which components have a model, a drawing, a printout — and which are missing one |

**Change and workflow**

| Tool | Answers |
|---|---|
| `plm_change_impact` | what modifying a part would touch, before it is touched |
| `plm_in_progress` | what is under modification right now, and by whom |
| `plm_recent_releases` | what was released in a period, and by whom |
| `plm_overview` | how much of everything there is — a starting point when the question is vague |

Two more (`plm_change_requests`, `plm_my_validations`) come with
[`plm_mcp_ecr`](../plm_mcp_ecr), and
[`plm_mcp_odoo_ai`](../plm_mcp_odoo_ai) publishes all of them to Odoo's own
chat assistant.

## Adding a tool

Inherit the model and decorate a method. There is nothing to register:

```python
from odoo import models
from odoo.addons.plm_mcp.models.plm_mcp_tool import mcp_tool


class MyTools(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    @mcp_tool(
        "plm_my_question",
        """
        What this returns, and when it is the right tool to reach for.
        """,
        properties={"code": {"type": "string", "description": "..."}},
        required=["code"],
    )
    def plm_my_question(self, code=None):
        return {"answer": "..."}
```

The description is the part worth the effort. What reaches the model at
`tools/list` is the name, the description and the schema — that is all it has to
decide whether this tool answers the question in front of it.

## Design notes

**No separate process.** The transport is a POST carrying one JSON-RPC message,
so it fits in an ordinary Odoo controller. Nothing here needs an event loop, a
sidecar or a second deployment.

**The wire types come from `mcp-types`**, published by the protocol's authors,
so message shapes follow the specification through a dependency bump rather than
a reading exercise.

**Record rules are the permission model.** Tools run as the key's user. A part
that user cannot see is a part the agent will not be told about.

## Testing

```bash
odoo --test-tags=odoo_plm_mcp -i plm_mcp -d <database>
```

## Licence

AGPL-3.0-or-later. See [LICENSING.md](../LICENSING.md).
