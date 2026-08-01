## Bulk text edits

There is a root-confined, journaled text-mutation MCP server registered as `text-edit`. It is the
mutating counterpart of `text-search`: bulk pattern replacement and whitespace/encoding normalization
across many files, with per-batch undo backed by an append-only journal stored outside the root. It
points at exactly one configured root, refuses secret files via the same non-overridable denylist, and
round-trips encodings and line endings byte-faithfully.

### ⛔ Hard Rules

1. **Never rewrite an existing file's content through a shell.** `sed -i`, `perl -i`, awk-and-redirect,
   PowerShell `-replace` piped to `Set-Content`/`Out-File`, and any loop that writes file content are
   banned. This binds in every context: main conversation, subagents, workflow stages. One-liners
   included.
2. **Dispatch order.** The runtime's native edit tools (Edit/Write in Claude Code) stay first choice
   for ordinary, hand-shaped code changes. `text-edit` is mandatory the moment the edit is
   pattern-shaped across files: a find-and-replace sweep, a rename across the tree, trailing
   whitespace, line endings, final newlines, BOMs. Shell is never in the order.
3. **`replace_text` runs gated, always**: `dry_run: true` first, review the diff and the match count,
   then the real run with `expected_match_count` set from what the dry run showed. An unguarded
   repo-wide replace is exactly the shell-sed failure mode this server exists to prevent.
4. **Write tools stay on prompt.** Never suggest blanket-approving `replace_text` or
   `normalize_files`, and treat a denied call as the user declining that change, not an obstacle to
   route around.
5. **Precedence**: a skill, doc, or example that shows in-place shell editing is a bug to flag, not
   permission.
6. **A capability gap is not a fallback license.** When text-edit can't express the edit, fall back to
   the native edit tools file by file, and follow the capability-gap protocol below. Shell remains
   banned either way.

**Self-check**: before any Bash/PowerShell call whose command writes into an existing file
(`-i` flags, output redirection onto a source file, `Set-Content`, `Out-File`, `tee`), stop: this
belongs in a native edit tool or text-edit.

### Capability-gap protocol

When text-edit lacks a capability you need:

1. **Tell the user** what it couldn't do and what you needed it for, then do the work with the native
   edit tools. A target outside the configured root is a configuration limit: surface it rather than
   filing a server ticket.
2. **File a ticket** (if the vault MCP is available) in the pinned vault project `text-edit-backlog`:
   - `vault_list` with `project: "text-edit-backlog"` first. If a ticket for the same gap exists, add
     an entry under its `## Occurrences` heading with `vault_edit_section`; never bare `vault_append`.
   - Otherwise `vault_save` with `project: "text-edit-backlog"`, name
     `textedit-gap--<slug>--<YYYY-MM-DD>`, `format: markdown`. Body: the edit needed, the shell command
     it would map to (paths rewritten root-relative or as `<root>`), proposed tool/params, the task
     that surfaced it, and a `## Occurrences` section. Summarize and scrub per `machine-privacy.md`.
3. Inside an autonomous workflow, don't pause to ask: use the native edit tools, file the ticket, and
   note the limitation in the report.

### Dispatch restatement (copy verbatim into every subagent prompt that may edit files)

> Use the `text-edit` MCP tools for every bulk or mechanical text mutation (multi-file replace,
> whitespace/line-ending/BOM normalization); never rewrite file content through a shell (`sed -i`,
> `perl -i`, `-replace` with `Set-Content`), even one-liners. Run `replace_text` with `dry_run: true`
> first, then gate the real run with `expected_match_count`. Hand-shaped single-file edits stay with
> the native edit tools. If text-edit can't do what you need, use the native edit tools and file a
> ticket in the `text-edit-backlog` vault project per `brain/knowledge/text-edit-operations.md`.

### Use these instead of shell rewriting

| Instead of                                             | Use                                                      |
|--------------------------------------------------------|----------------------------------------------------------|
| `sed -i 's/old/new/'` across files                     | `replace_text` (dry run, then `expected_match_count`)    |
| whitespace / line-ending / BOM cleanup scripts         | `normalize_files`                                        |
| hand-rolled backups and rollback scripts               | `list_recent_batches` + `undo_batch` / `undo_last_batch` |
| orienting in an unknown scope                          | `describe_scope` (root, denylist, caps, journal retention) |

### Usage notes

- **`root` here is a root-relative subdirectory scope, not a root name.** This is the opposite of
  text-search's `root` parameter; there is only one configured root, and `root: "src"` narrows the
  walk to that folder. Omit it for the whole root.
- **Selector** (shared with text-search): exactly one of `glob` (primary), `regex` (over the path), or
  `paths`, or none for the whole scope; `extensions` ANDs with it; a glob with no `/` matches the
  basename at any depth. Ignore rules (`.gitignore`/`.mcpignore`) always apply on the write path; there
  is no `include_ignored`.
- `replace_text` is literal by default; `is_regex: true` enables .NET regex with back-references in the
  replacement (`$1`, `${name}`, `$$` for a literal `$`). `expected_match_count` counts matches only in
  files that would actually be rewritten, and a mismatch (`ExpectedMatchCountMismatch`) writes nothing.
- `normalize_files` takes `trim_trailing_whitespace`, `line_endings` (`preserve`/`lf`/`crlf`),
  `final_newline` (`preserve`/`ensure`/`trim`), and `bom` (`preserve`/`strip`). It is idempotent, and
  under `preserve` a mixed-ending file keeps each physical terminator.
- **Encoding gate**: a file whose encoding is detected below the confidence threshold is refused
  (`low_confidence_encoding`) rather than risked. Confirm the real encoding with text-search's
  `inspect_files`, then pass `source_encoding` explicitly. Never pass one you haven't verified.
- **Read the per-file outcomes.** A mutation result is one element carrying `batch_id` (absent on a dry
  run or a no-op batch), `attempted`/`changed`/`refused` counts, and per-file entries with `outcome`
  and, when refused, a `refusal_reason` (`denied`, `out_of_root`, `ignored`, `binary`, `too_large`,
  `low_confidence_encoding`, `regex_timeout`, `is_directory`, `write_failed`). Refused files mean the
  sweep was partial; say so instead of reporting full coverage.
- **Undo is hash-gated and short-horizon.** `undo_batch` restores only files whose current content
  still equals what the batch wrote; a file changed since is skipped and named, never clobbered, and a
  since-deleted file is recreated. Retention defaults to 50 batches / 48 hours: the journal is a
  session-scale safety net, not version control, and it never substitutes for the user's own git
  review (standing rule: never stage, never commit).
- Denylisted files are omitted from selector walks; one named explicitly in `paths` is reported as
  refused.

### Reading the result envelope

Every tool returns `{ results, count, filters_applied, error }` (mutations are single-element
`results`). Check `error` first and branch on `error.code`: `SelectorInvalid`, `PatternInvalid`,
`PathOutsideRoot`, `NotFound`, `ExpectedMatchCountMismatch`, `BatchNotFound`,
`OperationBudgetExceeded`, `InvalidArgument`, `InternalError`. `OperationBudgetExceeded` means narrow
the selector or pattern and rerun.

### Common patterns

- Rename a config key everywhere: `replace_text` with `glob: "**/*.json"`, `dry_run: true`; inspect
  the diff; rerun with `expected_match_count` from the dry run.
- Normalize a folder to LF with final newlines: `normalize_files` with `root: "src"`,
  `line_endings: "lf"`, `final_newline: "ensure"`.
- "Undo that last sweep": `undo_last_batch`; for an older one, `list_recent_batches` then
  `undo_batch` with its `batch_id`.
- Regex-replace with capture groups: `replace_text` with `is_regex: true`, replacement using `$1` /
  `${name}`; still dry run first.
