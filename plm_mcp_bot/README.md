# PLM Commands for OdooBot

The tools of the [MCP server](../plm_mcp), reachable by typing `/plm` in a chat
with OdooBot. No language model, so no API key and no cost per question.

```
/plm                        the commands
/plm bom BASE-100           the bill of material
/plm parte CLP-020-001      the title block and documents
/plm dove CLP-020-001       where it is used, by revision
/plm impatto CLP-020-001    what modifying it would touch
/plm mancanti BASE-100      the components with no drawing
/plm aperti                 what is under modification, and by whom
```

Named arguments work where the tool declares them:

```
/plm bom BASE-100 depth=3
```

## Installing

```bash
odoo -d <database> -i plm_mcp_bot
```

Then open Discuss and write to OdooBot, or mention it in a channel.

## What it is, and what it is not

**It is a console.** `/plm bom BASE-100` names the tool and its argument. That
is quick, deterministic and free.

**It is not a small agent.** A question like *"which components of this assembly
are steel"* needs the bill of material crossed with the materials, and a
decision about what counts as steel. Something has to make that decision: either
you, by chaining two commands, or a model. If you want the second, the same
tools are already exposed over MCP — see [`plm_mcp`](../plm_mcp) — and to Odoo's
own assistant through [`plm_mcp_odoo_ai`](../plm_mcp_odoo_ai).

**It works in a chat with OdooBot**, or when OdooBot is mentioned in a channel.
It does **not** work in the chatter of a product or a document: Odoo does not
route those messages through the bot at all.

## Security

A command runs in the environment of whoever typed it, so the record rules that
apply to the person apply to the answer. There is nothing to configure, and no
way for a command to show data the user could not open by hand.

## Adding a command

Extend `_commands()` on `plm.mcp.bot` with a name, the tool it calls and a
formatter. The help is generated from that table, so it stays in step on its
own.

## Testing

```bash
odoo --test-tags=odoo_plm_mcp -i plm_mcp_bot -d <database>
```

## Licence

AGPL-3.0-or-later. See [LICENSING.md](../LICENSING.md).
