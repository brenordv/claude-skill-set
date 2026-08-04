## Text search and inspection

There is a read-only, root-confined text-search MCP server registered as `text-search`. Its tools list,
grep, read, and inspect text files under one configured **base root** (the directory that holds the
projects), plus optional named **package roots** exposing locally cached dependency sources (NuGet,
cargo, npm, Maven). A per-call `cwd` argument picks the scope: pass the absolute path of one project
inside the base to work in that project, omit it to search every project at once (the heavy path), or
pass `@name[/subpath]` to target a package root. Every path in and out is scope-relative, the server
never reads denylisted secret files, and no argument, `cwd` included, can widen a call past its root.

### ⛔ Hard Rules

1. **Never shell out for read-only text probing.** `grep`/`rg`, `find`, `cat`, `head`, `tail`, `ls -R`,
   `sed -n`, read-only `awk`, and their PowerShell equivalents (`Select-String`, `Get-Content`,
   `Get-ChildItem -Recurse`) are banned when the point of the command is to locate, list, read, or
   inspect file content. This binds in every context: main conversation, subagents, review panels,
   workflow stages. One-liners included.
2. **Dispatch order.** The agent runtime's native structured file tools (Read/Grep/Glob in Claude Code)
   stay first choice where they reach. `text-search` is mandatory the moment the need leaves that reach:
   a search across projects (the whole base root), dependency sources, encoding or text-shape questions,
   or a runtime with no native file tools. Shell is never in the order.
3. **Dependency source goes through package roots.** To read or grep a cached dependency, pass
   `cwd: "@<name>"` (`describe_scope` lists the names), preferably scoped to one package with
   `@<name>/<package>/<version>`. Never point shell tools, or broad native reads, at a package cache
   directly.
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

1. **Tell the user** exactly what couldn't be done and what you needed it for. A path outside the base
   root and every package root is a configuration limit, not a server bug: ask the user to adjust the
   configuration (or use a native tool if the runtime reaches the path) instead of filing a ticket.
2. **File a ticket** (if the vault MCP is available) in the pinned vault project `text-search-backlog`:
   - `vault_list` with `project: "text-search-backlog"` first. If a ticket for the same gap exists, add
     an entry under its `## Occurrences` heading with `vault_edit_section`; never bare `vault_append`.
   - Otherwise `vault_save` with `project: "text-search-backlog"`, name
     `textsearch-gap--<slug>--<YYYY-MM-DD>`, `format: markdown`. Body: the operation needed, the shell
     command it would map to (paths rewritten scope-relative or as `<scope>`), proposed tool/params, the
     task that surfaced it, and a `## Occurrences` section. Under `## Occurrences`, every entry records
     the **exact input used** (the text-search tool and parameters you called, or would call to hit the
     gap) and the **output received** (the returned `error.code` and message, or a note that no call
     was possible because the capability is absent), so a later agent can reproduce, analyze, and fix
     it. Capture input and output in scrubbed form, never raw: rewrite paths scope-relative or as
     `<scope>` and strip machine-identifying details and secrets; the ticket passes the
     `machine-privacy.md` self-check like any other save.
3. Inside an autonomous workflow, don't pause to ask: work around the gap with the available tools (the
   no-shell rule holds even when you can't ask), file the ticket, and note the limitation in the report.

### Dispatch restatement (copy verbatim into every subagent prompt)

> Use the runtime's native file tools or the `text-search` MCP tools for every read-only file search,
> listing, read, or encoding inspection; never shell out to grep/rg/find/cat/head/tail/ls -R or their
> PowerShell equivalents, even one-liners. Scope text-search calls with `cwd` (the project's absolute
> path); dependency-source reads go through package roots (`cwd: "@<name>"`, ideally
> `@<name>/<package>/<version>`). If neither covers what you need, report the gap and file a ticket in
> the `text-search-backlog` vault project (recording the exact input used and the output received,
> scrubbed) per `brain/knowledge/text-search-operations.md`.

### Use these instead of shell probing

| Instead of                                              | Use                                                        |
|---------------------------------------------------------|------------------------------------------------------------|
| `find`, `ls -R`, `Get-ChildItem -Recurse`               | `find_files` (glob/regex/paths selector, size + mtime out) |
| `grep -rn`, `rg`, `Select-String`                       | `search_text` (literal by default, `is_regex: true` for regex) |
| `cat`, `head`, `tail`, `sed -n 'a,bp'`, `Get-Content`   | `read_lines` (numbered, span-capped slice of one file)     |
| `file`, encoding/line-ending guesswork                  | `inspect_files` (encoding + confidence, BOM, endings, counts) |
| orienting in an unknown scope                           | `describe_scope` (base root, package roots, ignore tiers, denylist, caps; call it first) |

### Usage notes

- **Selector (shared by the multi-file tools)**: give exactly one of `glob` (primary), `regex` (over the
  path), or `paths`, or none for everything in the scope; `extensions` ANDs with it. A glob with no `/`
  matches the basename at any depth, so `*.cs` is recursive.
- **Scoping with `cwd`**: for work inside a repo, pass that repo's absolute path as `cwd`; input and
  output paths are then project-relative. This is the default posture. Omit `cwd` only when the question
  genuinely spans projects; the whole-base walk is the heavy path, and paths come back base-relative so
  a hit still says which project it is in. A `cwd` that escapes the base, is not a directory, or lands
  on or inside a protected directory is refused (`InvalidArgument`) with a path-free message.
- **Package roots**: `cwd: "@name"` targets a whole dependency cache, `@name/<subpath>` one package
  (for example `@nuget/Newtonsoft.Json/13.0.1`). `@name`, `@name/`, and `@name/.` are the same scope.
  Prefer a package subpath, or at least a narrowing selector; a whole-cache sweep is heavy.
- `read_lines` targets one file: `path` is relative to `cwd`, or to the base root when `cwd` is
  omitted. `end_line: 0` reads a capped span from `start_line`.
- `search_text` matches **per line**; a pattern spanning a newline never matches. `column`,
  `match_start`, and `match_end` are 1-based UTF-16 code units. `files_only: true` lists matching files
  instead of matches. `case_sensitive: true` applies to both file selection and content matching
  (default false).
- **`include_ignored` takes globs, not a boolean.** Three ignore tiers prune every walk: a built-in
  default set (heavy build and dependency directories like `node_modules/`, `bin/`, `obj/`, `target/`),
  then `.gitignore`, then `.mcpignore`, most specific tier winning. Pass globs (for example
  `["node_modules/**"]`) to re-include named ignored paths for one call; omit or pass an empty list to
  keep every tier in force. It never bypasses the secret denylist. Ignored files are where local secrets
  live; reach for it only when the ignored or generated content is the point.
- **Scoped calls skip ancestor ignore files.** Ignore files in directories between the base root and the
  `cwd` are not consulted, so a scoped call can surface a non-secret file a parent `.gitignore` would
  hide. The whole-base walk does honor each project's ignore files, and the denylist is unaffected
  either way.
- **Denylisted files are silently omitted** from walks, and a direct read of one reports `NotFound`
  rather than confirming the file exists. Don't read `NotFound` as proof of absence.
- Every result carries a scope-relative path, and the `filters_applied.cwd` echo is base-relative (`.`
  for the whole base), never an absolute path. Those paths are already scrubbed for
  `machine-privacy.md` purposes and safe to quote in durable artifacts; content still gets the usual
  secret scrub.

### Reading the result envelope

Every tool returns `{ results, count, truncated, cursor, skipped_symlinks, filters_applied, error }`.

- Check `error` first; branch on `error.code` (stable values: `SelectorInvalid`, `PatternInvalid`,
  `PathOutsideRoot`, `NotFound`, `IsBinary`, `TooLarge`, `OperationBudgetExceeded`, `InvalidArgument`,
  `InternalError`), not on message text. `InvalidArgument` also covers a malformed cursor and every bad
  `cwd`: one that escapes its root, is not a directory, is denylisted, names an unknown package root,
  or carries a subpath escaping its cache.
- `truncated: true` with a `cursor` means more pages: pass the cursor back, keeping `cwd` and
  `files_only` stable across pages. `truncated: true` with a null cursor means a ceiling was hit:
  narrow the selector instead of guessing what got cut.
- `OperationBudgetExceeded` means the call ran past its wall-clock budget. Same fix: narrow, starting
  with a tighter `cwd`.

### Common patterns

- "Which files in this repo mention X?": `search_text` with `pattern: "X"`, `files_only: true`, and
  `cwd` set to the repo's absolute path.
- "Show matches with context": `search_text` with `context_lines`.
- "Read lines 120-180 of that file": `read_lines` with `start_line: 120`, `end_line: 180` (and the
  same `cwd` the file was found under).
- "Which of my projects use X?": `search_text` with no `cwd`, accepting the heavy whole-base walk.
- "What does this dependency's source actually do?": `find_files`/`search_text` with
  `cwd: "@nuget/<Package>/<version>"` (or another cache name from `describe_scope`).
- "Is this file UTF-16? CRLF? Missing a final newline?": `inspect_files` with `paths: ["<the file>"]`.
- "Search untracked or generated files" (which `git_grep` can't see): `search_text`; add an
  `include_ignored` glob only when the ignored content itself is the point.
