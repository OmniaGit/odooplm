# PLM MCP Server — Change Requests

Two more tools for the [MCP server](../plm_mcp): the engineering changes that
are open, and the ones waiting on you.

```
> what change requests are open?
> which changes are on CLP-020-001?
> what do I have to validate?
```

## Why it is a separate module

The change workflow lives in `activity_validation`, which not every installation
has. Keeping these two tools here means `plm_mcp` stays installable without it —
and when both are present, the tools simply join the same registry and appear in
`tools/list` alongside the rest. Nothing has to be configured for that to
happen.

## Installing

```bash
odoo -d <database> -i plm_mcp_ecr
```

Pulls in `plm_mcp` and `activity_validation`.

## The tools

### `plm_change_requests`

What was asked, on which part, who has it, and where it stands.

| Filter | |
|---|---|
| `part` | only changes on one engineering code |
| `state` | `draft`, `in_progress`, `eco`, `exception`, `done`, `cancel` |
| `kind` | `request` for ECRs, `order` for ECOs |
| `include_closed` | closed changes are archived, not deleted — off by default |

Closed changes are left out unless asked for, and the answer says so
(`open_only`). Mixing them in would inflate every count, and "what is open" is
the question this actually answers.

### `plm_my_validations`

What is assigned to the person the connection belongs to, and still waiting on
them. Ordered by deadline, with the overdue ones counted separately.

**It takes no user argument, deliberately.** Tools run in the environment of the
API key's user, so the person is already known. A tool that accepted a name
would let any key read anybody else's queue.

## Testing

```bash
odoo --test-tags=odoo_plm_mcp -i plm_mcp_ecr -d <database>
```

## Licence

AGPL-3.0-or-later. See [LICENSING.md](../LICENSING.md).
