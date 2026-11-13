---
name: branch-review
description: >-
  Review all changes in the current branch compared to main/master.
  Covers correctness, security, performance, maintainability, and testing.
  Language-agnostic: detects languages in the diff and applies relevant
  standards. Use after completing work or before merging.
---

# Branch Review

> **Shared Knowledge**: This skill builds on `brain/knowledge/code-review.md`, `brain/knowledge/coding-general.md`, `brain/knowledge/writing-style.md`, and `brain/knowledge/machine-privacy.md`. Apply the first two when evaluating changes; writing-style applies both to prose in the diff (Step 4) and to the review write-up itself. All git inspection goes through the `git-ops` MCP per `brain/knowledge/git-readonly-operations.md`; never shell git. Stack detection and layer rules come from `brain/knowledge/github-pr-stacks.md`: a branch that is part of a PR stack is reviewed layer by layer, never as one flat diff.

## Purpose

Review the work done in the current branch by comparing it against the base branch (main/master). Produce actionable, prioritized feedback covering all changed files regardless of language.

## When to Use This Skill

- After completing implementation work, before handing off
- Before creating a pull request
- When asked to review current changes
- As a quality gate before merging

## Do Not Use This Skill When

- There are no changes to review (no diff)
- The user wants a full codebase audit (not scoped to branch changes)
- The task is writing code, not reviewing it

---

## Review Process

### Step 1: Scope the Review

1. **Stack check first.** Run `gh stack view --json` per `brain/knowledge/github-pr-stacks.md`.
   Exit 0 means the current branch is part of a PR stack: scope per layer as described below.
   Exit 2, or `gh`/the stack extension missing, means no stack: continue with the single-branch
   steps. Any other outcome follows the detection table in that file.
2. Identify the base branch (`main` or `master`) via `git_branch_list`
3. `git_log` with `ref: "<base>..HEAD"` to understand the commit narrative
4. `git_diff` for the change set: pass `fromRef: "<oldest-sha-from-step-2>^"` (the fork point as a
   revision expression) and `toRef: "HEAD"`, with `statOnly: true` first to see all changed files. If
   the branch contains merges from the base (fork point ambiguous), use `fromRef: "<base>"` instead and
   disclose in the review that base drift may appear in the diff.
5. Identify which languages/frameworks are present in the diff
6. **Retrieve prior reviews.** `vault_list` with `project: "code-reviews"` (pass it explicitly) and scan
   for earlier reviews of this repo or these files; `vault_get` close matches so recurring issues and prior
   verdicts inform this pass. Treat them as dated precedent, not current truth; re-verify against the diff.
   See `brain/knowledge/vault-operations.md` §"Artifact archives (pinned vault projects)".

**When the branch is part of a stack**, items 2-4 above are replaced by per-layer scoping: enumerate
the layers from the `gh stack view --json` output, and for each unmerged layer take `git_diff` with
`fromRef: "<branch-below>...<layer-branch>"` (three-dot; the bottom layer diffs against the trunk)
and `git_log` with `ref: "<branch-below>..<layer-branch>"`. Step 2 (language detection) through
Step 5 (feedback) then run once per layer, bottom-up, since upper layers depend on lower ones.
Findings and the assessment verdict are per layer (each layer is its own PR and merges on its own);
a finding about code a lower layer introduced belongs to that lower layer. Item 6 (prior reviews)
still runs once for the whole stack. Never run any `gh stack` command other than `view`, and never
create or restructure a stack (`github-pr-stacks.md` ⛔ Hard Rules).

### Step 2: Detect Language Context

Based on file extensions in the diff, apply the corresponding skill's standards:

| Extensions | Apply Standards From |
|------------|---------------------|
| `.ts`, `.tsx`, `.js`, `.jsx` | reactjs, nextjs, or angular (based on imports) |
| `.cs` that Unity compiles (the file sits under `Assets/` or `Packages/` of its nearest enclosing Unity root, the closest directory above the file that holds `Assets/`, `Packages/manifest.json`, and `ProjectSettings/`, which in a mono-repo can sit below the repo root; or the nearest `package.json` above the file has a `unity` field) | unity, plus csharp's Hard Rules with the Unity overrides the csharp skill names before rule 1 (rules 2, 4, 5, 19) |
| `.cs` (anything else) | csharp |
| `.py` | python |
| `.rs` | rust / rust-general |
| `.gd` | godot |
| `.cpp`, `.h` (with UE macros) | unreal-engine |
| `.sql` | postgres / azure-sql-server |
| `.sh`, `.bash` | linux-shell-scripting |
| `.ps1`, `.psm1` | windows-powershell-scripting |
| Mixed / other | coding-general.md only |

### Step 3: Review Each File

For every changed file, evaluate it across the review dimensions defined in `brain/knowledge/code-review.md` §2 (Correctness, Security, Performance, Maintainability, Testing), applying the language-specific standards routed in Step 2. Run each file against the concrete checklist in `brain/knowledge/review-heuristics.md`, and check the lessons vault (`vault_list` with `project: "lessons"`, topic tags from the diff) for any prior gotcha the change might reproduce.

### Step 4: Check Cross-Cutting Concerns

- [ ] No unrelated changes mixed in (minimal diff principle)
- [ ] No dead code introduced without justification
- [ ] No secrets, credentials, or PII in the diff
- [ ] Consistent style with the rest of the codebase
- [ ] Dependencies added are justified and pinned
- [ ] **Hard Rules hold on every added/modified line: the language-agnostic ⛔ block in
  `brain/knowledge/coding-general.md` (no re-implemented logic without an acknowledged reason, no
  deprecated/obsolete APIs) plus the routed language skill's. Open that skill and walk its ⛔ Hard Rules
  block item by item against the changed lines rather than gesturing at it.** These override repo
  conventions: "the codebase already does it" is not a pass. Each violation is at minimum an Important
  finding. The scope boundary cuts both ways: pre-existing violations in untouched code are a Note at
  most, never a demand to refactor; and conversely, a diff that DID refactor untouched code to satisfy a
  Hard Rule is itself a scope-creep finding.
- [ ] **No duplicated logic.** The diff doesn't re-implement something the repo already has: search
  for the distinctive tokens of each new helper, mapper, or validator (`git_grep` or the native
  search tools, never shell grep) per
  `brain/knowledge/review-heuristics.md` §Maintainability. An unacknowledged near-duplicate is at
  minimum Important.
- [ ] **No oversized mechanism.** No added mechanism exists only to serve cases the ask never named:
  an accumulator array, registry, or config-driven loop gating a small fixed set where an if/else or
  a direct call is shorter and clearer is at minimum Important on touched lines
  (`brain/knowledge/coding-general.md` ⛔ Hard Rule 6; concrete tells in
  `brain/knowledge/review-heuristics.md` §Maintainability). A clock abstraction injected beside a
  parameter that already carries the instant is the same finding
  (`brain/knowledge/review-heuristics.md` §Testing).
- [ ] **No change-narration comments.** Every comment the diff adds or edits describes the current
  code, not the edit: nothing referencing the fix, the request, the old behavior, or the task that
  produced it. Concrete tells in `brain/knowledge/review-heuristics.md` §Prose;
  `coding-general.md` ⛔ Hard Rule 3. At minimum Important on touched lines.
- [ ] **No deprecated APIs.** No added call is deprecated or obsolete in the version the project
  pins, and build/linter output shows no new deprecation warnings from the diff. See
  `brain/knowledge/review-heuristics.md` §Correctness.
- [ ] **No unprompted version bump.** A version field changes in the diff (manifest `version`,
  `<Version>` in a csproj, a VERSION file, `__version__`) only when the task was a release the user
  asked for. On a project with no release yet (no release tag, registry publication, or live
  deployment) the version never moves; the first release ships from the initial value.
  `coding-general.md` ⛔ Hard Rule 5. At minimum Important.
- [ ] **Prose passes `writing-style.md`.** Check every added/modified comment, docstring, doc file, and
  markdown block in the diff against the hard bans; the Prose section of
  `brain/knowledge/review-heuristics.md` has the concrete greps. A hard-ban violation on a touched line
  is at minimum an Important finding; on untouched lines it's a Note, never a refactor demand.
- [ ] **No machine-identifying details (blocking).** Run the `machine-privacy.md` self-check over the
  diff. Any absolute local path, OS username, or hostname on an added/modified line is a Critical
  finding, and the overall outcome cannot be APPROVED while one exists. On unchanged context lines it's
  Important: report it, don't deadlock the branch on it. Judge hits against the file's "Not a violation"
  carve-outs (OS-fixed paths, assessed-target details) before flagging.
- [ ] **No deliberate change reverted or weakened to pass a test.** If the diff loosened a validation,
  reintroduced a useless default, or rolled back an intentional tightening so an existing test passes,
  that is a Critical finding: the stale test should change, not the production code. Also flag a
  validation relaxation that spilled onto fields the change did not target. See
  `brain/knowledge/review-heuristics.md` §Correctness.
- [ ] **Summaries describe their own unit.** No added summary, docstring, or doc comment names who
  calls or consumes the unit, or the services and queues it travels through
  (`brain/knowledge/coding-general.md` ⛔ Hard Rule 9; `brain/knowledge/review-heuristics.md`
  §Architecture). At minimum Important on touched lines.
- [ ] **No handled failure ends on the success path, and every new arm is driven.** Each catch,
  except, or error arm the diff adds ends in one of `brain/knowledge/coding-general.md` ⛔ Hard
  Rule 10's endings and has a test that makes the dependency fail that way
  (`brain/knowledge/testing.md` ⛔ Hard Rule 1). A log-and-fall-through arm is at minimum
  Important, Critical when the caller then reports success or the arm sits in a security decision;
  an undriven arm is at minimum Important (`brain/knowledge/review-heuristics.md` §Correctness and
  §Testing).
- [ ] **Credentials attach at client configuration.** No credential in a call signature, URL, or
  query string (at minimum Important), and no real credential value in source or in a log
  (Critical) (`brain/knowledge/coding-general.md` ⛔ Hard Rule 11;
  `brain/knowledge/review-heuristics.md` §Security).
- [ ] **When the task stated a reason, the diff meets it.** For an ask like "move the key to a
  header for security", check the diff against the stated reason at the named step's footprint
  (`brain/knowledge/general-problem-solving.md` §2). Skip this item when the task gave no reason.
- [ ] **State changes checked against their machine.** Run the `state-machine-auditor` skill in
  review mode when an added, modified, or deleted line does any of these (signal ids from
  `brain/knowledge/implicit-state-machines.md`):
  - writes a status, state, phase, stage, step, or mode field, auth state included (`verified`,
    `approved`, `active`, `revoked`) (S1);
  - adds or removes a member of an enum or value set such a field holds (S1, F9);
  - adds or removes a guard, a `WHERE state =` clause, or a switch arm on such a field (S2, F4);
  - adds a boolean flag to a type or component, a lone flag included (S3, S10);
  - sets or clears a nullable field or timestamp that stands for a state (S4);
  - changes the order of lifecycle calls (S5);
  - touches a handler, job, or webhook that advances a persisted status (S8);
  - touches retry counters, attempt ids, leases, locks, or processed-id sets (S9).

  Dispatch it as a subagent. Invoke the skill through the Skill tool where the runtime allows;
  otherwise tell the subagent to read `state-machine-auditor/SKILL.md` and
  `brain/knowledge/implicit-state-machines.md` before anything else. Pass the diff refs from
  Step 1, the dispatch restatements `brain/knowledge/task-workflows.md` requires (git-ops,
  text-search, vault, machine-privacy), and the secret-file rule from
  `brain/knowledge/text-search-operations.md` ⛔ Hard Rules item 8. Fold its findings into this
  review at the severities it assigns, each tagged `[State machine F<n>]`, and record the lens line
  in the Summary. The trigger is what the diff touches, never its size; a flag added to make a
  symptom stop is the first case to check.

### Step 5: Produce Feedback

Consolidate the findings from Steps 3 and 4: de-duplicate overlapping ones, classify each per the
Severity Classification section below, and verify every `file:line` anchor actually points at the code
the finding quotes. Then emit the review using the Output Format below; the format block is the single
source of truth for the shape, so don't restate structure here.

### Step 6: Archive the Review

Once the review is complete, archive it: `vault_save` with `project: "code-reviews"` passed explicitly, the
full review as the body. Name, summary (carry the overall assessment), and tags follow
`brain/knowledge/vault-operations.md` §"Artifact archives (pinned vault projects)".

---

## Output Format

```markdown
# Branch Review

## Summary
[1-2 sentence overview of what the branch does]

**Files changed**: [count]
**Languages**: [detected languages]
**Overall assessment**: APPROVED | CHANGES REQUESTED | CONCERNS
**State-machine lens**: ran (<signal ids>), <n> machines, <m> findings | triggered (<signal ids>), not run: <reason> | not triggered

---

## Strengths
- [What was done well]

## Critical Issues (Must Fix)
1. **[Category]** `file:line`: [Issue description and why it matters]
   - **Fix**: [Specific suggestion]

## Important Issues (Should Fix)
1. **[Category]** `file:line`: [Issue description]
   - **Fix**: [Suggestion]

## Suggestions (Nice to Have)
1. `file:line`: [Improvement idea]

## Testing Assessment
- [ ] New code paths have test coverage
- [ ] Tests verify meaningful behavior
- [ ] Every new catch, except, or error arm is driven by a test asserting what the caller sees

## Notes
[Any observations about dead code spotted, architectural concerns for future, etc.]
```

For a stacked branch, open with a stack summary (the layers bottom-up, each with its branch, PR,
and verdict), then produce one full review block per layer in that order, titled with the layer's
branch and PR.

---

## Severity Classification

Classify findings by severity and map to the overall outcome (Approved / Changes Requested / Rejected) per `brain/knowledge/code-review.md` §3 (Review Outcomes) and §4 (Feedback Structure): Critical (must fix before merge), Important (should fix), Suggestion (optional).

---

## Review Principles

- **Review the diff, not the whole file**: Focus on what changed. Don't flag pre-existing issues unless they're security-critical. The one standing exception is the `state-machine-auditor` sanity pass, which reports pre-existing flaws in the machine a change touches as Notes.
- **One concern per finding**: Keep feedback atomic and addressable.
- **Provide fixes, not just problems**: Show what "better" looks like.
- **Respect existing patterns**: Don't suggest rewrites that contradict the project's conventions, except where a language skill marks a rule as a Hard Rule; those beat project conventions and must be flagged.
- **Acknowledge good work**: Call out well-crafted solutions.
- **Context matters**: A quick fix has different standards than a new feature.
