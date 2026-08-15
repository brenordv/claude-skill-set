# GitHub PR stacks (gh stack)

GitHub ships stacked pull requests through the official `gh stack` CLI extension
(`gh extension install github/gh-stack`; needs gh 2.90+). A stack is two or more PRs in the same
repository forming a dependency chain: the bottom PR targets the trunk (usually the default
branch) and each PR above targets the branch of the PR below it. Each PR shows only its own
layer's diff. Merging happens bottom-up, and when a mid-stack PR merges, the PRs above re-target
automatically. All branches live in one repository; cross-fork stacks are not supported.

Any skill that reviews branch changes or writes PR descriptions must find out whether the current
branch is part of a stack before doing anything else, and when it is, work layer by layer.

Official references:

- [About stacked pull requests](https://docs.github.com/en/pull-requests/get-started/about-stacked-prs)
- [Stacked pull requests CLI commands](https://docs.github.com/en/pull-requests/reference/stacked-prs-cli-commands)
- [Quickstart](https://docs.github.com/en/pull-requests/get-started/stacked-prs-quickstart)

## ⛔ Hard Rules

1. **Never create or mutate a stack.** Stack and layer creation is the user's responsibility,
   always. The only `gh stack` command you may run is `gh stack view`. Every other subcommand is
   banned: `init`, `add`, `submit`, `sync`, `rebase`, `push`, `merge`, `modify`, `unstack`,
   `link`, and the navigation commands (`checkout`, `switch`, `up`, `down`, `top`, `bottom`,
   `trunk`), which move the working tree and count as write operations. This holds even when the
   task is "get this PR opened": write the description, hand it over, and let the user submit.
2. **Detection runs before any branch review or PR description.** Skipping the check and
   reviewing a stacked branch as one flat diff produces findings about code that belongs to other
   layers' PRs. If the check was skipped, the output is wrong, not merely incomplete.
3. **`gh stack view --json` is a sanctioned shell probe.** `gh` is the GitHub CLI, not git, and
   the git-ops MCP has no stack capability, so running it does not break the no-shell-git rule.
   The exemption covers exactly this one read-only command; layer diffs, logs, and blame still go
   through git-ops as usual.

The `block-vcs-writes` hook denies every `gh stack` subcommand except `view` when installed; the
rules above bind regardless.

## Detection protocol

```shell
gh stack view --json
```

| Outcome | Meaning | What to do |
|---------|---------|------------|
| exit 0 | Current branch is part of a stack; stdout carries the stack as JSON | Work layer by layer (below) |
| exit 2 | Not part of a stack; nothing wrong | Normal single-branch flow |
| `gh` not found, or `stack` is an unknown command | CLI or extension absent | Assume no stack; normal flow |
| exit 6 | Branch belongs to more than one stack | Ask the user which stack before proceeding |
| any other non-zero | Something failed (generic error, API failure, lock, ...) | Fall back to the normal flow and tell the user the command failed, quoting its output |

The extension documents its exit codes (0 success, 1 generic error, 2 not in a stack, 3 rebase
conflict, 4 GitHub API failure, 5 invalid arguments, 6 disambiguation required, 7 rebase in
progress, 8 stack locked, 9 stacked PRs not enabled, 10 modify session interrupted) in the
[CLI reference](https://docs.github.com/en/pull-requests/reference/stacked-prs-cli-commands).
Non-interactive shells don't engage its pager; if a run ever hangs on one, set `PAGER=cat`.

## Reading the layers

The `--json` schema is not documented (checked August 2026), so read the fields from the actual
output instead of assuming names. Expect an ordered list of the stack's branches from bottom
(nearest the trunk) to top, with their linked PRs. If the output doesn't identify the trunk, get
the default branch from `git_branch_list` as usual.

A layer's change set is its branch diffed against the branch directly below it (the bottom layer
diffs against the trunk). Use git-ops: `git_diff` with `fromRef: "<branch-below>...<layer-branch>"`
(three-dot, merge-base form, so drift in the lower branch doesn't bleed in), and `git_log` with
`ref: "<branch-below>..<layer-branch>"` for that layer's commit narrative.

## Working layer by layer

- **Branch review**: review each unmerged layer as its own unit, bottom-up, since upper layers
  depend on lower ones. Findings and the assessment verdict are per layer (each layer is its own
  PR and merges on its own), topped by a short stack-level summary. A finding about code a lower
  layer introduced belongs to that lower layer, not to the layer whose diff happened to sit on
  top of it.
- **PR description**: one description per layer PR, generated from that layer's diff only. Never
  describe changes that live in a lower layer, however visible they are from the upper branch.
  Default to the layer the current branch is on; produce descriptions for other layers only when
  the user asks.
- **Scope questions go to the user.** When it's unclear which layers the user wants reviewed or
  described, ask rather than assuming the whole stack.
