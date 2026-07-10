## Git operations

There is a GitOps MCP server registered as `git-ops`. Use its tools for all read-only git inspections.
Each tool takes an absolute `cwd` and returns structured JSON, so don't `cd` into the repo first and don't shell
out to `git` for anything the tools below already cover.

### Use these instead of shell `git`

| Instead of                                                              | Use                                                                                            |
|-------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| `git status`                                                            | `git_status`                                                                                   |
| `git diff`, `git diff --cached`, `git diff <a>..<b>`, `git diff --stat` | `git_diff` (mode picked by params: `staged`, `fromRef`/`toRef`, `statOnly`)                    |
| `git log ...`                                                           | `git_log` (filters: `author`, `since`, `until`, `grep`, `pickaxe`, `paths`, `ref`, `follow`, `maxCount`) |
| `git show <ref>`                                                        | `git_show`                                                                                     |
| `git blame <file>`                                                      | `git_blame` (supports `lineStart`/`lineEnd` and `ref`)                                         |
| `git grep <pattern>`                                                    | `git_grep` (set `fixedString: false` for regex)                                                |
| `git ls-files`                                                          | `git_ls_files`                                                                                 |
| `git branch`, `git branch -a`                                           | `git_branch_list` (set `includeRemote: true` for remotes)                                      |
| `git reflog`                                                            | `git_reflog`                                                                                   |
| `git stash list`                                                        | `git_stash_list`                                                                               |
| `git stash show stash@{N}`                                              | `git_stash_show` (pass `index`)                                                                |

### Rules

- Pass `cwd` as an absolute path. The server resolves the repo root itself; you don't need to be inside the repo or know its layout.
- Never `cd` and then run a git command for anything in the table above. The MCP call is the same regardless of the shell's current directory, and chaining `cd && git ...` defeats the point of having structured tools.
- Don't shell out to `git` via bash for any read-only operation the table covers, even for one-liners. The structured output saves a parse step and the error codes are machine-readable.
- Bash `git` is only acceptable for write operations (`commit`, `add`, `push`, `checkout`, `reset`, `merge`, `rebase`, `tag`, `fetch`, `pull`, etc.), since this server is read-only by design. -- However, check yours, the users, and the projects guidelines first before using any of the git write-operations commands.

### Reading the result envelope

Collection-returning tools wrap their payload in `{ results, count, filters_applied, truncated, repo_root, error }`.

- Check `error` first. If it's `null`, work with `results`. If not, branch on `error.code` (stable values like `RefNotFound`, `PathOutsideRepo`, `RejectedArgument`, `GitTimeout`, `PcreUnavailable`), not on the message text.
- `truncated: true` means git's output hit the 8 MB cap. Narrow the query (lower `maxCount`, restrict `paths`, tighten `since`/`until`) and call again rather than guessing what got cut.
- `GitTimeout` means the call ran past 30 s. Same fix: narrow the query.

### Common patterns

- "What changed?": `git_status` for the working tree, `git_diff` with `staged: true` for the index, `git_diff` with `fromRef`/`toRef` between commits.
- "Who wrote line N?": `git_blame` with `lineStart` and `lineEnd` both set to N.
- "When was this string added or removed?": `git_log` with `pickaxe: "<string>"`.
- "Find usages of X in the repo": `git_grep` with `pattern: "X"` (set `fixedString: false` if X is a regex).
- "Find usages of X as of commit Y": `git_grep` with `pattern: "X"` and `ref: "Y"`.
- "What did commit X change?": `git_show` with `ref: "X"`.
- "What's on this branch that isn't on main?": `git_log` with `ref: "main..feature-branch"` style ref expression (verified via `rev-parse` before use).
