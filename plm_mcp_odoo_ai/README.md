# PLM Tools for the Odoo AI Agent

The tools of the [MCP server](../plm_mcp), published where Odoo's own chat
assistant can use them.

> Requires **Odoo Enterprise** — it depends on the `ai` module, which is
> proprietary. Without it this module cannot be installed, and `plm_mcp` works
> perfectly well on its own.

## What it is for

`plm_mcp` answers questions asked from outside Odoo. Odoo Enterprise has an
assistant of its own, in the chat, and it does not speak MCP: its tools are
server actions.

This module gives that assistant the same tools. Ask it in the Odoo chat:

```
> which components of BRG-HSG-001 are steel?
> what breaks if I change CLP-020-001?
```

## Nothing is written twice

The server actions are generated from the same registry the MCP endpoint reads.
The names, the descriptions and the parameter schemas are the ones already
declared for MCP — turned into `ir.actions.server` records and gathered in a
topic the agent can be given.

A tool added to `plm_mcp` tomorrow appears in the chat on the next module
update, without this module being touched.

```
plm.mcp.tool registry
        │
        ├── MCP endpoint ─────────► external clients
        └── generated server actions ─────────► Odoo's chat agent
```

## Installing

```bash
odoo -d <database> -i plm_mcp_odoo_ai
```

The actions are generated on install and refreshed on every update. To
regenerate them by hand:

```python
env["plm.mcp.tool"]._sync_odoo_ai_tools()
```

## Using it

The module creates an `ai.topic` named **OdooPLM**, carrying the tools and the
instructions the agent needs to read their answers properly. Assign that topic
to an `ai.agent` — *AI → Agents* — and the agent can answer PLM questions.

Calls run as the user talking to the agent, not in sudo: the environment is
rebuilt with `su=False` before the code is evaluated, so the same record rules
that bind the MCP server bind the chat.

## Notes

Three details of the Odoo side shape the implementation, all read from the `ai`
module rather than assumed:

- the tool's name, as the model sees it, is the **external id** of the action —
  so each is registered under an id equal to the tool name, otherwise the model
  would be offered `action_412`;
- a code action returns whatever it leaves in `ai['result']`; setting `action`
  instead makes it interactive, which the agent refuses;
- every declared argument reaches the code as a variable, filled with `None`
  when the model omitted it — which is why the generated call passes them all
  and lets `_call_tool` drop the empty ones.

## Testing

```bash
odoo --test-tags=odoo_plm_mcp -i plm_mcp_odoo_ai -d <database>
```

## Licence

AGPL-3.0-or-later. See [LICENSING.md](../LICENSING.md). The `ai` module it
depends on is Odoo Enterprise, under OEEL-1.
