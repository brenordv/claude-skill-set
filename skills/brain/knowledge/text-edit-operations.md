## Bulk text edits

There is a root-confined, journaled text-mutation MCP server registered as `text-edit`. It is the
mutating counterpart of `text-search`: bulk pattern replacement and whitespace/encoding normalization
across many files, with per-batch undo backed by an append-only journal stored outside the root. It
shares text-search's scope model: one configured **base root** holding the projects, with a per-call
`cwd` scoping each edit to one project. It has **no package roots** (dependency caches are read-only;
text-search reads them, text-edit can never touch them), refuses secret files via the same
non-overridable denylist, and round-trips encodings and line endings byte-faithfully.

### ⛔ Hard Rules

1. **Never rewrite an existing file's content through a shell.** `sed -i`, `perl -i`, awk-and-redirect,
   PowerShell `-replace` piped to `Set-Content`/`Out-File`, and any loop that writes file content are
   banned. This binds in every context: main conversation, subagents, workflow stages. One-liners
   included.
2. **Dispatch order.** The runtime's native edit tools (Edit/Write in Claude Code) stay first choice
   for ordinary, hand-shaped code changes. `text-edit` is mandatory the moment the edit is
   pattern-shaped across files: a find-and-replace sweep, a rename across the tree, trailing
   whitespace, line endings, final newlines, BOMs. Shell is never in the order.
3. **Scope every mutation with `cwd`.** The base root spans every project, so an unscoped call sweeps
   them all. Pass the absolute path of the project being edited (`cwd` is a per-call write firewall:
   nothing outside it can be written, even via an explicit `../other` path). Omit `cwd` only when a
   cross-project sweep is the explicit, stated intent of the task.
4. **`replace_text` runs gated, always**: `dry_run: true` first, review the diff and the match count,
   then the real run with `expected_match_count` set from what the dry run showed. An unguarded
   repo-wide replace is exactly the shell-sed failure mode this server exists to prevent.
5. **Write tools stay on prompt.** Never suggest blanket-approving `replace_text` or
   `normalize_files`, and treat a denied call as the user declining that change, not an obstacle to
   route around.
6. **Precedence**: a skill, doc, or example that shows in-place shell editing is a bug to flag, not
   permission.
7. **A capability gap is not a fallback license.** When text-edit can't express the edit, fall back to
   the native edit tools file by file, and follow the capability-gap protocol below. Shell remains
   banned either way.

**Self-check**: before any Bash/PowerShell call whose command writes into an existing file
(`-i` flags, output redirection onto a source file, `Set-Content`, `Out-File`, `tee`), stop: this
belongs in a native edit tool or text-edit.

### Capability-gap protocol

When text-edit lacks a capability you need:

1. **Tell the user** what it couldn't do and what you needed it for, then do the work with the native
   edit tools. A target outside the configured base root is a configuration limit: surface it rather
   than filing a server ticket.
2. **File a ticket** (if the vault MCP is available) in the pinned vault project `text-edit-backlog`:
   - `vault_list` with `project: "text-edit-backlog"` first. If a ticket for the same gap exists, add
     an entry under its `## Occurrences` heading with `vault_edit_section`; never bare `vault_append`.
   - Otherwise `vault_save` with `project: "text-edit-backlog"`, name
     `textedit-gap--<slug>--<YYYY-MM-DD>`, `format: markdown`. Body: the edit needed, the shell command
     it would map to (paths rewritten scope-relative or as `<scope>`), proposed tool/params, the task
     that surfaced it, and a `## Occurrences` section. Under `## Occurrences`, every entry records the
     **exact input used** (the text-edit tool and parameters you called, or would call to hit the gap)
     and the **output received** (the returned `error.code` and message, or a note that no call was
     possible because the capability is absent), so a later agent can reproduce, analyze, and fix it.
     Capture input and output in scrubbed form, never raw: rewrite paths scope-relative or as
     `<scope>` and strip machine-identifying details and secrets, per `machine-privacy.md`.
3. Inside an autonomous workflow, don't pause to ask: use the native edit tools, file the ticket, and
   note the limitation in the report.

### Dispatch restatement (copy verbatim into every subagent prompt that may edit files)

> Use the `text-edit` MCP tools for every bulk or mechanical text mutation (multi-file replace,
> whitespace/line-ending/BOM normalization); never rewrite file content through a shell (`sed -i`,
> `perl -i`, `-replace` with `Set-Content`), even one-liners. Scope every call with `cwd` (the
> project's absolute path), run `replace_text` with `dry_run: true` first, then gate the real run with
> `expected_match_count`. Hand-shaped single-file edits stay with the native edit tools. If text-edit
> can't do what you need, use the native edit tools and file a ticket in the `text-edit-backlog` vault
> project (recording the exact input used and the output received, scrubbed) per
> `brain/knowledge/text-edit-operations.md`.

### Use these instead of shell rewriting

| Instead of                                             | Use                                                      |
|--------------------------------------------------------|----------------------------------------------------------|
| `sed -i 's/old/new/'` across files                     | `replace_text` (dry run, then `expected_match_count`)    |
| whitespace / line-ending / BOM cleanup scripts         | `normalize_files`                                        |
| hand-rolled backups and rollback scripts               | `list_recent_batches` + `undo_batch` / `undo_last_batch` |
| orienting in an unknown scope                          | `describe_scope` (base root, scope model, denylist, caps, journal retention) |

### Usage notes

- **Scoping with `cwd`**: pass the absolute path of the project being edited. Any directory inside the
  base works, so a subfolder tightens the firewall further, but prefer the project root: ignore files
  in directories *between* the base root and the `cwd` are not consulted, so a `cwd` deep inside a
  project stops the project's own `.gitignore` from shielding its generated files. A `cwd` that
  escapes the base, is not a directory, or lands on or inside a protected directory is refused
  (`InvalidArgument`) with a path-free message. `@` has no special meaning here; there are no package
  roots on the write path.
- **Input is cwd-relative, reporting is base-relative, undo is base-global.** Explicit `paths` resolve
  against the `cwd` and are confined to it. Per-file results, the journal, and undo always speak
  base-relative paths; a batch is base-scoped, so `undo_batch` and `list_recent_batches` see every
  batch regardless of the `cwd` it was created under.
- **Selector** (shared with text-search): exactly one of `glob` (primary), `regex` (over the path), or
  `paths`, or none for the whole scope; `extensions` ANDs with it; a glob with no `/` matches the
  basename at any depth. `case_sensitive: true` makes glob/regex (and `replace_text` content) matching
  case-sensitive; `max_files` caps the files acted on (0 uses the server default, clamped to the
  ceiling). The ignore tiers (a built-in default set of heavy build and dependency directories, then
  `.gitignore`, then `.mcpignore`) always apply on the write path; there is no `include_ignored`.
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
  since-deleted file is recreated. A journal row that no longer confines under the base, or is now
  denylisted, is skipped as a security measure. Retention defaults to 50 batches / 48 hours: the
  journal is a session-scale safety net, not version control, and it never substitutes for the user's
  own git review (standing rule: never stage, never commit).
- Denylisted files are omitted from selector walks; one named explicitly in `paths` is reported as
  refused.

### Reading the result envelope

Every tool returns `{ results, count, filters_applied, error }` (mutations are single-element
`results`), and `filters_applied.cwd` echoes the scope base-relative (`.` when `cwd` was omitted),
never an absolute path. Check `error` first and branch on `error.code`: `SelectorInvalid`,
`PatternInvalid`, `PathOutsideRoot`, `NotFound`, `ExpectedMatchCountMismatch`, `BatchNotFound`,
`OperationBudgetExceeded`, `InvalidArgument`, `InternalError`. `InvalidArgument` also covers every bad
`cwd` (escapes the base, not a directory, denylisted) and an unknown `source_encoding`.
`OperationBudgetExceeded` means narrow the selector or pattern and rerun.

### Common patterns

- Rename a config key across one repo: `replace_text` with `cwd: "<absolute path of the repo>"`,
  `glob: "**/*.json"`, `dry_run: true`; inspect the diff; rerun with `expected_match_count` from the
  dry run.
- Normalize a repo's sources to LF with final newlines: `normalize_files` with
  `cwd: "<absolute path of the repo>"`, `glob: "src/**"`, `line_endings: "lf"`,
  `final_newline: "ensure"`.
- "Undo that last sweep": `undo_last_batch`; for an older one, `list_recent_batches` then
  `undo_batch` with its `batch_id` (both are base-global; no `cwd` needed).
- Regex-replace with capture groups: `replace_text` with `is_regex: true`, replacement using `$1` /
  `${name}`; still dry run first.
- A deliberate cross-project sweep: omit `cwd`, state that intent in the report, and keep the dry-run
  plus `expected_match_count` gate; the blast radius is every project under the base.
