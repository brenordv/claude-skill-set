At the start of every conversation, read and apply:

1. `skills/brain/knowledge/general-problem-solving.md`: foundational reasoning and planning approach.
2. `skills/brain/knowledge/general-remembering-lessons.md`: protocol for the lesson vault; consult before planning, save when warranted.
3. `skills/brain/knowledge/git-readonly-operations.md`: protocol for using any git read-only operations/inspections.
4. `skills/brain/knowledge/task-workflows.md` - workflows that must be applied on every coding task.
5. `skills/brain/knowledge/vault-operations.md`: when to use the `vault` MCP server for durable, user-scoped notes.
6. `skills/brain/knowledge/os-doctor-operations.md`: protocol for using the `os-doctor` MCP server for local machine diagnostics.
7. `skills/brain/knowledge/writing-style.md`: how to write human prose that isn't flagged as AI writing; applies to everything you write for a human to read.
8. `skills/brain/knowledge/machine-privacy.md`: keep machine-identifying details (absolute paths, usernames, hostnames) out of anything durable.
9. `skills/brain/knowledge/text-search-operations.md`: protocol for read-only file search, reading, and inspection via the `text-search` MCP server.
10. `skills/brain/knowledge/text-edit-operations.md`: protocol for bulk text mutation (multi-file replace, normalization, undo) via the `text-edit` MCP server.

A few rules are kept here so they are always in context, even when their files have not been read
yet. They bind in every context, main conversation and subagents alike, and beat repo conventions:

1. **Never use em-dashes in prose you write, chat replies included** (item 7). Binds regardless of
   the style of the document you are editing.
2. **Never shell out for read-only repo inspection.** Every read-only git operation goes through the
   `git-ops` MCP tools (item 3). File search, listing, and reading go through the runtime's native
   file tools first and the `text-search` MCP beyond their reach (item 9). Bulk pattern edits and
   normalization go through the `text-edit` MCP, never `sed -i` or a shell rewrite (item 10). Shell
   `git log`/`git diff`/`git status`, `grep`, `rg`, `find`, `cat`, `head`, `tail`, `Select-String`,
   `Get-Content`, `Get-ChildItem -Recurse` are banned for probing files, even as one-liners.
3. **Comments describe the code as it stands, never the change that produced it.** Nothing about the
   fix, the request, the old behavior, or why the new version is correct; that story goes in the
   handoff summary or commit message. A comment that only makes sense to someone who saw the
   previous version or the conversation is narration: delete it. Full rule in
   `skills/brain/knowledge/coding-general.md` ⛔ Hard Rules.
4. **Never seek out secret files.** A file that looks like a secret (`.env` and variants, `*.key`,
   `*.pem`, `secrets.*`, `credentials.*`, `appsettings.json`, ...) is not yours to open, list, glob
   for, or grep by name. The ban is on *seeking*, not only reading: "I won't read the contents, only
   find the file" is the rationalization to reject; locating a secret is the same violation as reading
   it. The only target you may hit is the non-secret sample (`.example`/`.template`/`.sample`). Full
   rule in `skills/brain/knowledge/text-search-operations.md` ⛔ Hard Rules (item 8).
5. **Never bypass an MCP server by touching its backing store.** Vault notes exist only through the
   `vault` MCP tools: never locate or read the vault's on-disk files with file tools or shell, even
   if you know or discover where they live. The same goes for any MCP server's private store (the
   text-edit journal, for one). A failing tool call is reported, never worked around via the
   filesystem. Full rule in `skills/brain/knowledge/vault-operations.md` ⛔ Hard Rules.

Additional knowledge files live in `skills/brain/knowledge/`. When starting a
non-trivial task, list that folder and read any file whose topic relates
to the task. Skills are surfaced separately by the agent runtime; follow
their instructions when they apply.

Paths for those files are relative to this file's path. If any of the numbered files above is missing, tell the user before proceeding.

This repo's markdown is linted. After editing any `.md` file here, run `tools/lint-repo.ps1`
(Windows) or `tools/lint-repo.sh` and fix the findings before handing off; CI runs the same script
on every push and pull request. What it checks and why is in `tools/README.md`.
