## Vault (persistent notes)

There is a personal, cross-conversation file vault registered as the `vault` MCP server. Its own tool
instructions load each session; this file is the standing directive on *when* to reach for it.

### ⛔ Hard Rules

1. **The vault is reachable only through the `vault` MCP tools.** Never locate, list, read, or
   modify its on-disk backing store with file tools, text-search, or shell; not to "just check
   what's there", not to recover from a failed tool call, not because the storage path happens to
   be known. What the tools return is the vault; whatever sits on disk behind them is server
   internals, as off-limits as a database's data files. This binds in every context: main
   conversation, subagents, workflow stages.
2. **The same goes for every MCP server's private store.** The text-edit journal and any other
   store an MCP server owns are reached through that server's tools or not at all. (The working
   tree git-ops reports on is not such a store; project files stay ordinary files.)
3. **A failing or missing tool is a report, never a bypass.** When a vault tool errors, or the
   server isn't registered this session, say so and stop. Routing around it via the filesystem is
   the exact move this block exists to stop.
4. **Precedence**: discovering the storage location (in config, a transcript, an error message) is
   not permission, and an example, script, or earlier step that read the store directly is a bug
   to flag, not a pattern to imitate.

**Self-check**: before any file search, listing, or read, ask "is this path inside an MCP server's
backing store (the vault's storage, the text-edit journal)?" If it is, stop: use that server's
tools, or report what they couldn't do. The `guard-file-targets` and `block-secrets` hooks can
enforce this for configured store paths (their `PROTECTED_STORES` tunable; see the hooks README),
but the rule binds first, in your reasoning.

### Dispatch restatement (copy verbatim into every subagent prompt that may touch the vault)

> Vault content is accessed only through the `vault` MCP tools (`vault_list`, `vault_get`,
> `vault_save`, ...). Never locate or read the vault's on-disk storage with file tools or shell,
> even if you know or discover where it lives; the same goes for any MCP server's private store. A
> failing tool call is reported, never worked around via the filesystem. Full rules in
> `brain/knowledge/vault-operations.md` ⛔ Hard Rules.

### Default to the vault for durable, user-scoped content

- Prefer `vault` over ad-hoc scratch files or "remember this" phrasing whenever the user asks to save,
  stash, or recall something that should outlive the current conversation (notes, drafts, snippets,
  decisions, reference material).
- On any request to "remember / save / note / keep" something durable, save it to the vault with a clear
  name and a one-line summary rather than only holding it in conversation context.
- When the user refers to something they saved before ("the note about X", "what I stashed on Y"),
  `vault_list` / `vault_get` first before assuming it's lost or re-deriving it.

### Rules

- **Names are strict**: single segment, `[A-Za-z0-9._-]` only, max 128 chars. No spaces, no slashes, no
  other punctuation. Anything else fails with `invalid_name`, so slugify before saving.
- Writes use optimistic concurrency: pass the `base_version` you read. A stale write fails with `conflict`
  carrying the `current_version` and usually a base-to-current diff. Use the diff to fold the other
  change into yours and retry against the current version, rather than re-reading and blindly overwriting.
- **Edit surgically, not wholesale.** To change one markdown section, `vault_edit_section` by heading; to
  set one value in JSON/YAML, `vault_edit_key` with a dotted key path; to add to the end, `vault_append`.
  A full `vault_save` resend is for when the whole body actually changed.
- `vault_edit_section` matches a heading by its rendered plain text (inline markdown stripped) and, on
  server v3.1.0+, also by its verbatim source text with the delimiters kept, so a heading containing a
  code span, emphasis, or a link can be targeted with the text copied straight from the note. A leading
  `#` run is tolerated either way; the rendered form is the one older builds accept. It replaces the
  body up to the next heading of the same or higher level, subsections included. Duplicate or colliding
  heading text fails as `ambiguous_heading`, never a wrong-section edit, so keep headings unique within
  a note.
- `vault_append` concatenates with **no separator**; start appended content with its own newline(s).
- To change only a note's summary, tags, or parent, use `vault_set_meta`: no new version, no content resend.
- **Restate `format` and `summary` on every `vault_save`**, not just the first. Save always replaces the
  summary (omitted blanks it). Omitted `format` keeps the note's stored format on server v2.1.0+, but
  older builds reset it to `text` and break future `vault_edit_section` (markdown-only), so restating it
  costs nothing and protects against a stale binary. Omitted tags keep the existing set. The surgical
  edit tools preserve all three.
- **Honor the split hint.** When a write result carries a `hint`, the note has outgrown one file:
  restructure it into a summary-plus-index parent with the detail moved to child notes (linked via
  `parent`). Don't keep appending to a note the server is already flagging.
- Mutating an archived note fails with `archived`: run `vault_restore` first, or pick a new name.
- **The store is plain text; never save secrets.** Redact tokens, connection strings, and credentials
  before archiving anything (review and PR bodies quote diffs; scrub them first). Machine-identifying
  details get the same scrub: absolute local paths, OS usernames, and hostnames never go into a note,
  per `machine-privacy.md`.
- This is separate from the auto-memory index (`MEMORY.md`): the vault is for user content the user owns
  and names; memory is for facts *you* record about how to work. Don't conflate them.

### Artifact archives (pinned vault projects)

Recurring work artifacts are archived in **dedicated, pinned vault projects** so past work becomes
cross-repo searchable precedent:

| Project (pass as `project`) | Holds                                              |
|-----------------------------|----------------------------------------------------|
| `implementation-plans`      | every finalised implementation / architecture plan |
| `code-reviews`              | every code or branch review result                 |
| `pr-descriptions`           | every pull-request description you author           |
| `ticket-descriptions`       | every ticket / issue description you draft           |
| `git-ops-backlog`           | capability-gap tickets for the git-ops MCP (see `git-readonly-operations.md` §"Capability-gap protocol") |
| `text-search-backlog`       | capability-gap tickets for the text-search MCP (see `text-search-operations.md` §"Capability-gap protocol") |
| `text-edit-backlog`         | capability-gap tickets for the text-edit MCP (see `text-edit-operations.md` §"Capability-gap protocol") |

**Pin the project on every call.** Pass `project: "<name>"` explicitly on every `vault_save`,
`vault_list`, and `vault_get` against these archives. On `vault_save`/`vault_get`, an omitted project is
inferred from the working directory and silos the artifact per-repo, which defeats the entire point of a
cross-project reference library. `vault_list` is the one exception: omitting the project there means
"across ALL projects" with no inference. Pin it anyway to keep archive queries scoped, but reach for an
unpinned `vault_list` deliberately when you don't know which archive (or repo namespace) holds the note
you're after. This is the same linchpin as the `lessons` namespace.

`project` is the namespace (*which* archive); `parent` is for hierarchy *within* a namespace (splitting one
large note into linked children). Never use `parent` to group artifacts into an archive; that is what
`project` is for.

**Progress checkpoints** live in `implementation-plans` too: `parent`-linked to their plan note, named
`<repo>--<scope>-progress--<YYYY-MM-DD>`, summary prefixed `PROGRESS:` while live and flipped to `DONE:`
(via `vault_set_meta`) when the work lands. The prefix is what lets plan retrieval skip them, so keep it
accurate. Mechanics live in `task-workflows.md` §"Progress checkpoints (crash recovery)".

This is a **two-sided** protocol; the save half is worthless without the retrieve half.

**Retrieve first, before producing one of these artifacts:**
- `vault_list` with `project: "<archive>"` and a `query`/`tags` drawn from the task; triage on the returned
  names + summaries, then `vault_get` only the close matches.
- Let them inform the new artifact: prior approaches, pitfalls, wording, structure, decisions already made.
- Treat them as **dated precedent, not current truth.** Re-verify against the repo / current state; do not
  assume the code, plan, PR, or ticket they describe still reflects reality. When age matters,
  `vault_history` shows when a note was created and last revised.

**Save after, once the artifact is finalised:**
- `vault_save` with `project: "<archive>"`, `format: "markdown"` (on every save, per the Rules above), and
  the full artifact as the body verbatim (secrets redacted). First save omits `base_version`; later updates
  read `current_version` and pass it as `base_version`. If only one section changed (a revised review
  verdict, an updated plan stage), prefer `vault_edit_section` over resending the whole artifact.
- Name: `<repo>--<scope-slug>--<YYYY-MM-DD>` using the current date, e.g.
  `billing-api--webhook-retries--2026-07-09`. Kebab-case throughout: names take only `[A-Za-z0-9._-]`,
  so no spaces and no dash characters other than plain hyphens. Uniqueness is `(project, name)`, so
  `repo + scope` keeps names distinct within the shared archive.
- Summary (one line, specific; this is what retrieval scans): repo, what it covers, and the outcome where
  one exists (plan status; review verdict APPROVED / CHANGES REQUESTED / CONCERNS; PR or ticket title).
- Tags: always include a concept/topic tag, plus the repo and primary language/tech; never tag with tech
  alone, or it won't surface cross-stack.

**When each fires:**
- **Plans**: retrieve at the start of planning; save once the plan is finalised/approved. (Hooked in
  `system-architect` and the planning workflow.)
- **Reviews**: retrieve at the start of a review; save once it is complete. (Hooked in `branch-review`.)
- **PR descriptions**: whenever you draft a PR description (e.g. before `gh pr create`), use the
  `pr-description` skill; it retrieves similar past PRs first and saves the final description.
- **Ticket descriptions**: whenever you draft a ticket or issue, use the `ticket-description` skill; it
  retrieves similar past tickets first and saves the final title and description.
