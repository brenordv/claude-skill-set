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
| `git log -P --grep=...`, `git log --all`                                | `git_log` with `perlRegex: true` / `allRefs: true` (server v2.4.0+; `allRefs` can't be combined with `ref`) |
| `git show <ref>`                                                        | `git_show`                                                                                     |
| `git show <ref>:<path>`                                                 | `git_file_at_ref` (server v2.2.0+; `path` and `ref` are separate arguments, `ref` defaults to `HEAD`; `lineStart`/`lineEnd`, `maxBytes`, and `byteOffset` slice and page it, v2.5.0+) |
| `git blame <file>`                                                      | `git_blame` (supports `lineStart`/`lineEnd` and `ref`)                                         |
| `git grep <pattern>`                                                    | `git_grep` (set `fixedString: false` for regex)                                                |
| `git grep -c <pattern>`                                                 | `git_grep` with `countOnly: true` (server v2.6.0+)                                             |
| `git grep <pattern> -- '*.cs' ':!docs'`                                 | `git_grep` with `globs: ["*.cs"]` and `excludePaths: ["docs"]` (server v2.3.0+)               |
| `git ls-files`, `git ls-files '*.json'`                                 | `git_ls_files` (wildcards in `globs`, exclusions in `excludePaths`, v2.3.0+)                   |
| `git ls-files --stage`                                                  | `git_ls_files` with `stage: true` (server v2.2.0+)                                             |
| `git branch`, `git branch -a`                                           | `git_branch_list` (set `includeRemote: true` for remotes)                                      |
| `git reflog`                                                            | `git_reflog`                                                                                   |
| `git stash list`                                                        | `git_stash_list`                                                                               |
| `git stash show stash@{N}`                                              | `git_stash_show` (pass `index`)                                                                |

### Usage notes

- Pass `cwd` as an absolute path. The server resolves the repo root itself; you don't need to be inside the repo or know its layout.
- **`paths` is literal; wildcards go in `globs`** (server v2.3.0+). A `paths` entry holding `*`, `?`,
  or a leading `:`, or an empty one, is `RejectedArgument` on every tool that takes `paths`. Only
  `git_grep` and `git_ls_files` take `globs` (git's pathspec wildcards, where `*` also matches `/`,
  so `*.cs` matches at any depth) and `excludePaths` (a path or wildcard to drop; a directory drops
  its subtree; given alone, it selects everything else). Older builds ran every pathspec literally,
  so a wildcard in `paths` returned an empty success that reads as "no matches" and isn't.
- **`git_log`'s `grep` and `author` are basic regular expressions**: `|` is a literal, so
  `grep: "A|B"` returns no commits. Pass `perlRegex: true` (server v2.4.0+) for alternation, `\d`,
  and the rest of PCRE; a git built without PCRE2 returns `PcreUnavailable`.
- **`git_file_at_ref` has no default size cap.** A large file, or one long line, can exceed the
  client's per-result limit. Pass `maxBytes` (server v2.5.0+) and page by passing the payload's
  `next_byte_offset` back as `byteOffset` with the same range and cap; `lineStart`/`lineEnd`
  (1-based, inclusive, both or neither) cut to a line range first, and `total_lines` says how far
  the file runs.
- `git_grep` `countOnly` counts matching lines per file, not occurrences, and `maxCount` alongside
  it is `RejectedArgument`.
- **The server pins some git behavior off on purpose**, so these results are expected, not gaps to
  ticket: a file under git-lfs, git-crypt, or another filter driver is compared as raw worktree
  bytes (v2.10.0+), so `git_status` can list it as modified when only its timestamp changed (in a
  repository the user trusts, a `git status` in their own shell refreshes that); a submodule with
  only uncommitted changes inside it is not listed (v2.10.0+); a `log.follow=true` in git config is
  ignored, so pass `follow: true` (v2.14.0+); and in a partial clone, a call that needs an object
  the clone never fetched fails with `GitCommandError` instead of fetching it (v2.17.0+; on some
  older gits, `git_grep` with `ref` leaves such a file out of its results instead). Report the last
  one to the user rather than working around it.
- Never `cd` and then run a git command for anything in the table above. The MCP call is the same regardless of the shell's current directory, and chaining `cd && git ...` defeats the point of having structured tools.
- The structured output saves a parse step and the error codes are machine-readable; that's why even one-liners go through the MCP.
- `git_file_at_ref` returns committed content as-is. git-ops has no secret denylist and no content
  scan, so the secret-file ban in `text-search-operations.md` ⛔ Hard Rules item 8 is the only guard:
  never point `path` at a file that looks like a secret, at any ref.

### Reading the result envelope

Collection-returning tools wrap their payload in `{ results, count, filters_applied, truncated, repo_root, error }`.

- Check `error` first. If it's `null`, work with `results`. If not, branch on `error.code` (stable values like `RefNotFound`, `PathNotFound`, `PathOutsideRepo`, `RejectedArgument`, `InvalidArgument`, `GitTimeout`, `GitCommandError`, `PcreUnavailable`), not on the message text.
- Argument-shape mistakes are rejected before the tool runs (server v2.1.0+), as `InvalidArgument`: an
  unknown argument name now fails the call instead of being silently ignored by the SDK, with
  `detail.unknown_arguments` naming each one (plus a `did_you_mean` when a schema name is close),
  `missing_required` (a `git_status` with no `cwd`, say), and the full `expected_arguments`. A known
  argument of the wrong JSON type reports the same code with the SDK's fixed generic text in
  `detail.sdk_error`. Correct the call from the detail and retry; this is a caller error, never a
  capability gap, so no `gitops-gap` ticket in those cases.
- `truncated: true` means git's output hit the 8 MB cap. Narrow the query (lower `maxCount`, restrict `paths`, tighten `since`/`until`) and call again rather than guessing what got cut. On `git_file_at_ref` it can also mean `maxBytes` cut the content; that one is paging, so continue from `next_byte_offset`.
- `GitTimeout` means the call ran past 30 s. Same fix: narrow the query.

### Common patterns

- "What changed?": `git_status` for the working tree, `git_diff` with `staged: true` for the index, `git_diff` with `fromRef`/`toRef` between commits.
- "Who wrote line N?": `git_blame` with `lineStart` and `lineEnd` both set to N.
- "When was this string added or removed?": `git_log` with `pickaxe: "<string>"`.
- "Find usages of X in the repo": `git_grep` with `pattern: "X"` (set `fixedString: false` if X is a regex). An empty `pattern`, or one that begins with `-`, is rejected (`RejectedArgument`, `param: "pattern"`); to match a leading-dash literal, use regex mode with the dash escaped, e.g. `pattern: "\\-flag", fixedString: false`. `git_grep` searches **tracked content only**; for untracked, ignored, or generated files, or dependency sources, use the text-search server per `brain/knowledge/text-search-operations.md`.
- "Find usages of X as of commit Y": `git_grep` with `pattern: "X"` and `ref: "Y"`.
- "Find X in C# files only, outside `docs/`": `git_grep` with `globs: ["*.cs"]` and
  `excludePaths: ["docs"]` (server v2.3.0+). `git_ls_files` takes the same two to list files.
- "How many lines match X in each file?": `git_grep` with `countOnly: true` (server v2.6.0+), one
  `{path, match_count}` per matching file instead of every line.
- "Which commits mention A or B, on any branch?": `git_log` with `grep: "A|B"`, `perlRegex: true`,
  and `allRefs: true` (server v2.4.0+).
- "Did this commit change a file's mode?": the `git_show` (or `git_diff`) file entry carries
  `old_mode` and `new_mode` (server v2.20.0+); a mode-only change is an entry with both and no hunks.
- "What did commit X change?": `git_show` with `ref: "X"`. A `<rev>:<path>` ref (`HEAD:README.md`)
  names a file, not a commit: server v2.2.0+ rejects it with `RejectedArgument` pointing at
  `git_file_at_ref`, and older builds returned an empty success (`commit: null`, `files: []`)
  that looks like "no changes" and isn't.
- "What did file F look like at commit X?", including a file deleted since: `git_file_at_ref` with
  `path: "F"` and `ref: "X"`. The result carries `content`, `mode`, `object_id`, and `size`; a
  binary blob comes back `is_binary: true` with `content: null`. A path missing at that ref is
  `PathNotFound`; a directory or the repo root is `RejectedArgument`. For one part of a long file,
  pass `lineStart`/`lineEnd` or page with `maxBytes` (server v2.5.0+).
- "Is this script committed as executable?": `git_ls_files` with `stage: true` and `paths` set to
  the script. Each entry is `{path, mode, object_id, stage}`; `100755` is executable, `100644` is
  not. Check this before telling the user to run `./script.sh`.
- "What's on this branch that isn't on main?": `git_log` with `ref: "main..feature-branch"` (a two-dot range; each side is verified to a SHA before use, so an omitted side defaults to `HEAD`).
- "How does this branch differ from its fork point?": `git_diff` with `fromRef: "main...feature-branch"` (three-dot: the diff from the merge base of the two, not between the endpoints). A range must be the sole ref; don't also pass `toRef`.
