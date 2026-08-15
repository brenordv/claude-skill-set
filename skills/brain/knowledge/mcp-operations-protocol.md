# Shared MCP operations protocol

The custom MCP servers (`git-ops`, `text-search`, `text-edit`; `vault` and `os-doctor` where noted)
share one operating protocol. The per-server files (`git-readonly-operations.md`,
`text-search-operations.md`, `text-edit-operations.md`, `vault-operations.md`,
`os-doctor-operations.md`) define each server's scope, tools, and hard rules; this file holds the
mechanics they share, so the rules live once. When a per-server file points here, follow this file
with that server's parameters from the table below.

## Shared principles

These are restated as ⛔ Hard Rules in each per-server file; the statement here is the common
ground, not a replacement for those blocks.

- **Never shell out for an operation a server covers.** Binds in every context: main conversation,
  subagents, review panels, workflow stages. One-liners included.
- **Precedence**: a skill, doc, or example that demonstrates the shell form is a bug to flag, not
  permission to imitate.
- **A capability gap is not a fallback license.** When a server can't do what you need, follow the
  capability-gap protocol below; silently reaching for shell is never the answer.
- **Deliverable exemption**: these rules govern what the agent executes, not what it authors.
  Shell commands inside scripts written as deliverables for the user are product code.
- **Envelope discipline**: check the result's `error` first and branch on `error.code`, never on
  message text. On truncation, narrow the query instead of guessing what got cut.

## Capability-gap protocol

Server parameters:

| Server        | Backlog project (pass as `project`) | Ticket name prefix |
|---------------|-------------------------------------|--------------------|
| `git-ops`     | `git-ops-backlog`                   | `gitops-gap`       |
| `text-search` | `text-search-backlog`               | `textsearch-gap`   |
| `text-edit`   | `text-edit-backlog`                 | `textedit-gap`     |

When a server lacks a capability you need:

1. **Tell the user** exactly what the server couldn't do and what you needed it for. Check the
   per-server file first: some misses are configuration limits (a path outside a configured root,
   for example), which get surfaced to the user, not ticketed as server gaps.
2. **File a ticket** (if the vault MCP is available) in the server's pinned backlog project:
   - `vault_list` with `project: "<backlog>"` first. If a ticket for the same gap already exists,
     add an entry under its `## Occurrences` heading with `vault_edit_section`; never bare
     `vault_append`.
   - Otherwise `vault_save` with `project: "<backlog>"`, name `<prefix>--<slug>--<YYYY-MM-DD>`,
     `format: markdown`. Body: the operation needed, the shell command it would map to (paths
     rewritten repo-/scope-relative or as `<repo-root>`/`<scope>`), proposed tool and parameters,
     the task that surfaced it, and a `## Occurrences` section.
   - Under `## Occurrences`, every entry records the **exact input used** (the tool and parameters
     you called, or would call to hit the gap) and the **output received** (the returned
     `error.code` and message, or a note that no call was possible because the capability is
     absent), so a later agent can reproduce, analyze, and fix it. Capture both in scrubbed form,
     never raw: paths rewritten relative or as placeholders, machine-identifying details and
     secrets stripped, so the ticket passes the `machine-privacy.md` self-check like any other
     save.
3. **Work the task with what exists.** Each per-server file states its own fallback (native tools,
   asking the user, or nothing). Inside an autonomous workflow, don't pause to ask: work around the
   gap with the available tools (the no-shell rule holds even when you can't ask), file the ticket,
   and note the limitation in the final report.

The extra tokens this protocol costs are accepted: the backlogs are what make evolving the servers
easy.

## Dispatch restatements

Subagents don't inherit knowledge-file discipline on their own; the dispatcher carries it to them.
Every subagent prompt includes, verbatim, the "Dispatch restatement" block of each per-server file
whose territory the subagent may touch (git-ops and text-search always; text-edit when it may edit
files; vault when it may touch the vault), plus the machine-privacy restatement. The canonical
texts live in the per-server files; see `task-workflows.md` §"Subagent dispatch protocol" for when
this fires.
