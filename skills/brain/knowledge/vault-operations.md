## Vault (persistent notes)

There is a personal, cross-conversation file vault registered as the `vault` MCP server. Its own tool
instructions load each session; this file is the standing directive on *when* to reach for it.

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
- `vault_edit_section` matches the heading text exactly (a leading `#` run is tolerated) and replaces the
  body up to the next heading of the same or higher level, subsections included. Duplicate heading text
  fails as `ambiguous_heading`, so keep headings unique within a note.
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
