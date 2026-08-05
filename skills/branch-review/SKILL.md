---
name: branch-review
description: >-
  Review all changes in the current branch compared to main/master.
  Covers correctness, security, performance, maintainability, and testing.
  Language-agnostic: detects languages in the diff and applies relevant
  standards. Use after completing work or before merging.
---

# Branch Review

> **Shared Knowledge**: This skill builds on `brain/knowledge/code-review.md`, `brain/knowledge/coding-general.md`, `brain/knowledge/writing-style.md`, and `brain/knowledge/machine-privacy.md`. Apply the first two when evaluating changes; writing-style applies both to prose in the diff (Step 4) and to the review write-up itself. All git inspection goes through the `git-ops` MCP per `brain/knowledge/git-readonly-operations.md`; never shell git.

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

1. Identify the base branch (`main` or `master`) via `git_branch_list`
2. `git_log` with `ref: "<base>..HEAD"` to understand the commit narrative
3. `git_diff` for the change set: pass `fromRef: "<oldest-sha-from-step-2>^"` (the fork point as a
   revision expression) and `toRef: "HEAD"`, with `statOnly: true` first to see all changed files. If
   the branch contains merges from the base (fork point ambiguous), use `fromRef: "<base>"` instead and
   disclose in the review that base drift may appear in the diff.
4. Identify which languages/frameworks are present in the diff
5. **Retrieve prior reviews.** `vault_list` with `project: "code-reviews"` (pass it explicitly) and scan
   for earlier reviews of this repo or these files; `vault_get` close matches so recurring issues and prior
   verdicts inform this pass. Treat them as dated precedent, not current truth; re-verify against the diff.
   See `brain/knowledge/vault-operations.md` §"Artifact archives (pinned vault projects)".

### Step 2: Detect Language Context

Based on file extensions in the diff, apply the corresponding skill's standards:

| Extensions | Apply Standards From |
|------------|---------------------|
| `.ts`, `.tsx`, `.js`, `.jsx` | reactjs, nextjs, or angular (based on imports) |
| `.cs` | csharp |
| `.py` | python |
| `.rs` | rust / rust-general |
| `.gd` | godot |
| `.cpp`, `.h` (with UE macros) | unreal-engine |
| `.sql` | postgres / azure-sql-server |
| `.sh`, `.bash` | linux-shell-scripting |
| Mixed / other | coding-general.md only |

### Step 3: Review Each File

For every changed file, evaluate it across the review dimensions defined in `brain/knowledge/code-review.md` §2 (Correctness, Security, Performance, Maintainability, Testing), applying the language-specific standards routed in Step 2. Run each file against the concrete checklist in `brain/knowledge/review-heuristics.md`, and check `brain/gotchas/` for any prior gotcha the change might reproduce.

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
- [ ] **No change-narration comments.** Every comment the diff adds or edits describes the current
  code, not the edit: nothing referencing the fix, the request, the old behavior, or the task that
  produced it. Concrete tells in `brain/knowledge/review-heuristics.md` §Prose;
  `coding-general.md` ⛔ Hard Rule 3. At minimum Important on touched lines.
- [ ] **No deprecated APIs.** No added call is deprecated or obsolete in the version the project
  pins, and build/linter output shows no new deprecation warnings from the diff. See
  `brain/knowledge/review-heuristics.md` §Correctness.
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

### Step 5: Produce Feedback

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
- [ ] Error paths are tested

## Notes
[Any observations about dead code spotted, architectural concerns for future, etc.]
```

---

## Severity Classification

Classify findings by severity and map to the overall outcome (Approved / Changes Requested / Rejected) per `brain/knowledge/code-review.md` §3 (Review Outcomes) and §4 (Feedback Structure): Critical (must fix before merge), Important (should fix), Suggestion (optional).

---

## Review Principles

- **Review the diff, not the whole file**: Focus on what changed. Don't flag pre-existing issues unless they're security-critical.
- **One concern per finding**: Keep feedback atomic and addressable.
- **Provide fixes, not just problems**: Show what "better" looks like.
- **Respect existing patterns**: Don't suggest rewrites that contradict the project's conventions, except where a language skill marks a rule as a Hard Rule; those beat project conventions and must be flagged.
- **Acknowledge good work**: Call out well-crafted solutions.
- **Context matters**: A quick fix has different standards than a new feature.
