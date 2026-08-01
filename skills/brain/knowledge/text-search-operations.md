## Text search and inspection

There is a read-only, root-confined text-search MCP server registered as `text-search`. Its tools list,
grep, read, and inspect text files across one or more configured roots: workspace folders, plus optional
**package roots** exposing locally cached dependency sources (NuGet, cargo, npm, Maven). Every path in
and out is root-relative, it never reads denylisted secret files, and no argument can widen it past its
roots.

### ⛔ Hard Rules

1. **Never shell out for read-only text probing.** `grep`/`rg`, `find`, `cat`, `head`, `tail`, `ls -R`,
   `sed -n`, read-only `awk`, and their PowerShell equivalents (`Select-String`, `Get-Content`,
   `Get-ChildItem -Recurse`) are banned when the point of the command is to locate, list, read, or
   inspect file content. This binds in every context: main conversation, subagents, review panels,
   workflow stages. One-liners included.
2. **Dispatch order.** The agent runtime's native structured file tools (Read/Grep/Glob in Claude Code)
   stay first choice where they reach. `text-search` is mandatory the moment the need leaves that reach:
   another configured root, dependency sources, encoding or text-shape questions, or a runtime with no
   native file tools. Shell is never in the order.
3. **Dependency source goes through package roots.** To read or grep a cached dependency, use
   `root: "@packages"` (narrowed by a selector or `extensions`). Never point shell tools, or broad
   native reads, at a package cache directly.
4. **Encoding and text-shape questions have exactly one answer: `inspect_files`.** Encoding, BOM, line
   endings, and final-newline state are detected and reported with a confidence; never guess them from
   raw bytes or shell out to `file`.
5. **Precedence**: a skill, doc, or example that shows shell text probing is a bug to flag, not
   permission. Fix it or report it; don't imitate it.
6. **A capability gap is not a fallback license.** When neither the native tools nor text-search can do
   what you need, follow the capability-gap protocol below. Silently reaching for shell is never the
   answer.
7. **Exemption against over-application**: piping a command's *own output* through `head`/`grep`
   (`dotnet test | tail -20`) is output trimming, not file probing, and stays fine. So does shell text
   tooling inside scripts authored as deliverables for the user; the rule governs what the agent
   executes, not what it writes for others to run.

**Self-check**: before any Bash/PowerShell call containing `grep`, `rg`, `find`, `cat`, `head`, `tail`,
`sed`, `awk`, `Select-String`, `Get-Content`, or `Get-ChildItem`, ask "is this command reading files to
locate or inspect content?" If it is, stop and use a native file tool or text-search.

### Capability-gap protocol

When text-search (and the native tools) lack a capability you need:

1. **Tell the user** exactly what couldn't be done and what you needed it for. A path outside every
   configured root is a configuration limit, not a server bug: ask the user to add the root (or use a
   native tool if the runtime reaches the path) instead of filing a ticket.
2. **File a ticket** (if the vault MCP is available) in the pinned vault project `text-search-backlog`:
   - `vault_list` with `project: "text-search-backlog"` first. If a ticket for the same gap exists, add
     an entry under its `## Occurrences` heading with `vault_edit_section`; never bare `vault_append`.
   - Otherwise `vault_save` with `project: "text-search-backlog"`, name
     `textsearch-gap--<slug>--<YYYY-MM-DD>`, `format: markdown`. Body: the operation needed, the shell
     command it would map to (paths rewritten root-relative or as `<root>`), proposed tool/params, the
     task that surfaced it, and a `## Occurrences` section. Summarize and scrub; the ticket passes the
     `machine-privacy.md` self-check like any other save.
3. Inside an autonomous workflow, don't pause to ask: work around the gap with the available tools (the
   no-shell rule holds even when you can't ask), file the ticket, and note the limitation in the report.

### Dispatch restatement (copy verbatim into every subagent prompt)

> Use the runtime's native file tools or the `text-search` MCP tools for every read-only file search,
> listing, read, or encoding inspection; never shell out to grep/rg/find/cat/head/tail/ls -R or their
> PowerShell equivalents, even one-liners. Dependency-source reads go through text-search package roots
> (`root: "@packages"`). If neither covers what you need, report the gap and file a ticket in the
> `text-search-backlog` vault project per `brain/knowledge/text-search-operations.md`.

### Use these instead of shell probing

| Instead of                                              | Use                                                        |
|---------------------------------------------------------|------------------------------------------------------------|
| `find`, `ls -R`, `Get-ChildItem -Recurse`               | `find_files` (glob/regex/paths selector, size + mtime out) |
| `grep -rn`, `rg`, `Select-String`                       | `search_text` (literal by default, `is_regex: true` for regex) |
| `cat`, `head`, `tail`, `sed -n 'a,bp'`, `Get-Content`   | `read_lines` (numbered, span-capped slice of one file)     |
| `file`, encoding/line-ending guesswork                  | `inspect_files` (encoding + confidence, BOM, endings, counts) |
| orienting in an unknown scope                           | `describe_scope` (roots, denylist, caps; call it first)    |

### Usage notes

- **Selector (shared by the multi-file tools)**: give exactly one of `glob` (primary), `regex` (over the
  path), or `paths`, or none for everything under the root; `extensions` ANDs with it. A glob with no
  `/` matches the basename at any depth, so `*.cs` is recursive.
- **Root targeting**: omit `root` for all workspace roots (the common case), a name for one root,
  `@packages` for all package roots, `@all` for everything. A search reaching a package root must be
  narrowed by `glob`, `regex`, `paths`, or `extensions` or it fails.
- `read_lines` targets one file in one specific root: the `root` name is required when more than one
  root is configured, and groups like `@all` are invalid there. `end_line: 0` reads a capped span from
  `start_line`.
- `search_text` matches **per line**; a pattern spanning a newline never matches. `column`,
  `match_start`, and `match_end` are 1-based UTF-16 code units. `files_only: true` lists matching files
  instead of matches.
- `include_ignored` is off by default and never bypasses the secret denylist. Ignored files are where
  local secrets live; keep it off unless the task genuinely needs generated or ignored content.
- **Denylisted files are silently omitted** from walks, and a direct read of one reports `NotFound`
  rather than confirming the file exists. Don't read `NotFound` as proof of absence.
- Every result carries its `root` name plus a root-relative path. Those paths are already scrubbed for
  `machine-privacy.md` purposes and safe to quote in durable artifacts; content still gets the usual
  secret scrub.

### Reading the result envelope

Every tool returns `{ results, count, truncated, cursor, skipped_symlinks, filters_applied, error }`.

- Check `error` first; branch on `error.code` (stable values: `SelectorInvalid`, `PatternInvalid`,
  `PathOutsideRoot`, `NotFound`, `IsBinary`, `TooLarge`, `OperationBudgetExceeded`, `InvalidArgument`,
  `InternalError`), not on message text.
- `truncated: true` with a `cursor` means more pages: pass the cursor back, keeping `root` and
  `files_only` stable across pages. `truncated: true` with a null cursor means a ceiling was hit:
  narrow the selector instead of guessing what got cut.
- `OperationBudgetExceeded` means the call ran past its wall-clock budget. Same fix: narrow.

### Common patterns

- "Which files mention X?": `search_text` with `pattern: "X"`, `files_only: true`.
- "Show matches with context": `search_text` with `context_lines`.
- "Read lines 120-180 of that file": `read_lines` with `start_line: 120`, `end_line: 180`.
- "What does this dependency's source actually do?": `find_files`/`search_text` with
  `root: "@packages"` plus a narrowing glob or `extensions`.
- "Is this file UTF-16? CRLF? Missing a final newline?": `inspect_files` with `paths: ["<the file>"]`.
- "Search untracked or generated files" (which `git_grep` can't see): `search_text`, with
  `include_ignored: true` only when the ignored content is the point.
