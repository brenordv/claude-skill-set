## Git operations

There is a GitOps MCP server registered as `git-ops`. Its tools handle all read-only git inspection.
Each tool takes an absolute `cwd` and returns structured JSON, so don't `cd` into the repo first and
don't shell out to `git` for anything the tools below cover.

### ⛔ Hard Rules

1. **Never shell out to `git` for a read-only operation.** This binds in every context: the main
   conversation, subagents, review panels, and every workflow stage. One-liners included; "it's just
   a quick `git log`" is exactly the case this rule exists for.
2. **Precedence**: a skill, doc, or example that shows a shell `git` read command is a bug to flag,
   not permission. Fix it or report it; don't imitate it.
3. **A capability gap is not a fallback license.** When git-ops can't do what you need, follow the
   capability-gap protocol below. Silently reaching for shell git is never the answer.
4. Shell `git` remains acceptable **only for write operations** (`commit`, `add`, `push`, `checkout`,
   `reset`, `merge`, `rebase`, `tag`, `fetch`, `pull`, etc.), and only after checking your own, the
   user's, and the project's guidelines first. Standing rule of this skill set: never stage, never
   commit; leave both to the user.
5. **Exemption against over-application**: `git` inside shell scripts authored as deliverables for
   the user (the `linux-shell-scripting` templates, for example) is product code. The rule governs
   what the agent executes, not what it writes for others to run.

**Self-check**: before any Bash/PowerShell call whose command contains `git `, ask "is this a write
operation?" If it isn't, stop and use the MCP tool. The `block-vcs-writes` hook enforces the
stage/commit/stash ban at the tool-call layer when installed, but the rule binds first, in your
reasoning.

### Capability-gap protocol

Follow the shared protocol in `mcp-operations-protocol.md` (backlog project `git-ops-backlog`, name
prefix `gitops-gap`; ticket contents scrubbed repo-relative or as `<repo-root>`). git-ops specific:
**shell git for the missing capability is allowed only with the user's explicit approval**, and the
approval covers that one invocation, never a standing waiver. Inside an autonomous workflow there is
no such approval: work around the gap using only the available MCP tools (the no-shell-git rule
holds even when you can't ask), file the ticket, and note the limitation in the final report.

### Dispatch restatement (copy verbatim into every subagent prompt)

> Use the `git-ops` MCP tools for every read-only git operation; never shell out to `git` to inspect
> anything, even one-liners. If git-ops can't do what you need, don't fall back to shell git: report
> the gap and file a ticket in the `git-ops-backlog` vault project (recording the exact input used and
> the output received, scrubbed) per `brain/knowledge/git-readonly-operations.md`.

### Use these instead of shell `git`

| Instead of                                                              | Use                                                                                            |
|-------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| `git status`                                                            | `git_status`                                                                                   |
| `git diff`, `git diff --cached`, `git diff <a>..<b>`, `git diff <a>...<b>`, `git diff --stat` | `git_diff` (mode picked by params: `staged`, `fromRef`/`toRef`, `statOnly`; `fromRef` also takes a range `A..B` / `A...B`, where three-dot is the merge-base diff) |
| `git log ...`                                                           | `git_log` (filters: `author`, `since`, `until`, `grep`, `pickaxe`, `paths`, `ref`, `follow`, `maxCount`) |
| `git show <ref>`                                                        | `git_show`                                                                                     |
| `git blame <file>`                                                      | `git_blame` (supports `lineStart`/`lineEnd` and `ref`)                                         |
| `git grep <pattern>`                                                    | `git_grep` (set `fixedString: false` for regex)                                                |
| `git ls-files`                                                          | `git_ls_files`                                                                                 |
| `git branch`, `git branch -a`                                           | `git_branch_list` (set `includeRemote: true` for remotes)                                      |
| `git reflog`                                                            | `git_reflog`                                                                                   |
| `git stash list`                                                        | `git_stash_list`                                                                               |
| `git stash show stash@{N}`                                              | `git_stash_show` (pass `index`)                                                                |

### Usage notes

- Pass `cwd` as an absolute path. The server resolves the repo root itself; you don't need to be inside the repo or know its layout.
- Never `cd` and then run a git command for anything in the table above. The MCP call is the same regardless of the shell's current directory, and chaining `cd && git ...` defeats the point of having structured tools.
- The structured output saves a parse step and the error codes are machine-readable; that's why even one-liners go through the MCP.

### Reading the result envelope

Collection-returning tools wrap their payload in `{ results, count, filters_applied, truncated, repo_root, error }`.

- Check `error` first. If it's `null`, work with `results`. If not, branch on `error.code` (stable values like `RefNotFound`, `PathOutsideRepo`, `RejectedArgument`, `GitTimeout`, `PcreUnavailable`), not on the message text.
- `truncated: true` means git's output hit the 8 MB cap. Narrow the query (lower `maxCount`, restrict `paths`, tighten `since`/`until`) and call again rather than guessing what got cut.
- `GitTimeout` means the call ran past 30 s. Same fix: narrow the query.

### Common patterns

- "What changed?": `git_status` for the working tree, `git_diff` with `staged: true` for the index, `git_diff` with `fromRef`/`toRef` between commits.
- "Who wrote line N?": `git_blame` with `lineStart` and `lineEnd` both set to N.
- "When was this string added or removed?": `git_log` with `pickaxe: "<string>"`.
- "Find usages of X in the repo": `git_grep` with `pattern: "X"` (set `fixedString: false` if X is a regex). An empty `pattern`, or one that begins with `-`, is rejected (`RejectedArgument`, `param: "pattern"`); to match a leading-dash literal, use regex mode with the dash escaped, e.g. `pattern: "\\-flag", fixedString: false`. `git_grep` searches **tracked content only**; for untracked, ignored, or generated files, or dependency sources, use the text-search server per `brain/knowledge/text-search-operations.md`.
- "Find usages of X as of commit Y": `git_grep` with `pattern: "X"` and `ref: "Y"`.
- "What did commit X change?": `git_show` with `ref: "X"`.
- "What's on this branch that isn't on main?": `git_log` with `ref: "main..feature-branch"` (a two-dot range; each side is verified to a SHA before use, so an omitted side defaults to `HEAD`).
- "How does this branch differ from its fork point?": `git_diff` with `fromRef: "main...feature-branch"` (three-dot: the diff from the merge base of the two, not between the endpoints). A range must be the sole ref; don't also pass `toRef`.
