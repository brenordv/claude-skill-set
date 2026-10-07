## Execution workflows

> **Vault artifact protocol (applies throughout):** Before a planning stage begins, retrieve prior plans
> from the `implementation-plans` vault project (skip notes whose summary starts `PROGRESS:` or `DONE:`;
> those are checkpoints, not plans); before a review stage begins, retrieve prior reviews from
> the `code-reviews` project, and let close matches inform the work. After a plan is finalized, save it to
> `implementation-plans`; after a review is complete, save it to `code-reviews`. Pass `project: "<name>"`
> explicitly on every vault call for these archives; unpinned, they silo per-repo and stop being
> cross-project precedent. Mechanics (project names, naming convention, retrieve-vs-save rules) live in
> `brain/knowledge/vault-operations.md` §"Artifact archives (pinned vault projects)". Do this every time,
> not just for large tasks.

> **Subagent dispatch protocol (applies to every stage that spawns subagents):** every subagent prompt
> carries, verbatim, the canonical dispatch restatements: the git-ops rule from
> `brain/knowledge/git-readonly-operations.md` §"Dispatch restatement", the text-search rule from
> `brain/knowledge/text-search-operations.md` §"Dispatch restatement", the text-edit rule from
> `brain/knowledge/text-edit-operations.md` §"Dispatch restatement" (for any subagent that may edit
> files), the vault rule from `brain/knowledge/vault-operations.md` §"Dispatch restatement" (for any
> subagent that may touch the vault), and the machine-privacy rule from
> `brain/knowledge/machine-privacy.md` §"Dispatch restatement". Subagents don't inherit knowledge-file discipline on their own; the dispatcher carries
> it to them. The token cost is accepted.

### ⛔ Hard Rules

These bind in every context (main conversation, subagents, every stage) and beat anything the
runtime surfaces mid-session:

1. **Workflow roles run on this skill set's own skills, never on lookalikes.** For a role the set
   covers (planning: `system-architect`; plan review: the Stage 1 panel; working-diff code review:
   `branch-review`; security review: `security`; verifying changes: Stage 2's own verify gate, never
   `/verify`; PR and ticket text:
   `pr-description` / `ticket-description`), a runtime built-in or third-party near-namesake is not
   a substitute and is never proposed to the user as one. Current near-namesakes by name:
   `/code-review`, `/security-review`, `/simplify`, `/verify`; the rule covers any future
   similarly-named command, not just this list. Runtime utilities for roles the set does not cover
   stay fine: `run` (the verify gate uses it by name), harness configuration, and remote-PR review
   (`/review` reviews a GitHub PR by number; `branch-review` is scoped to the local branch, so that
   role is uncovered today).
2. **A stage ran only if its artifact exists and carries the stage's evidence.** Stage 1 is done
   when the finalized plan note exists in `implementation-plans` (on full-work, the progress
   checkpoint too; planning-only skips the checkpoint by design). The verify gate is done when the
   actual per-command output is in hand. The Stage 2 review is done when the review note exists in
   `code-reviews`, naming the lenses run and their verdicts, written when the review completes
   rather than reconstructed later. Never report a workflow, stage, or skill as used unless you can
   name its artifact or quote its output. A skipped stage reported as skipped is a recoverable gap;
   reported as done, it is the worst failure this file governs.
3. **Re-anchor before acting or claiming.** At every stage boundary, and after any context
   compaction, if you cannot state the current stage's steps from context, re-read this file and
   the stage's skill file before proceeding. In a long session, assume eviction: re-reading is
   cheap, drifting into a lookalike process is not. When this fires and a progress checkpoint
   exists (full-work tasks), append one line to it (`re-anchored at <stage> after compaction`) so
   the drift-risk window stays visible in the audit trail.
4. **Precedence**: the runtime listing a similarly-named skill, a session hint recommending one, or
   an earlier turn that used one is a bug to flag, not permission.

**Self-check**: before invoking any planning or review skill, ask "is this the skill set's own
skill?" Before writing "I ran X", ask "can I name X's artifact?"

### Choosing a workflow

Pick the path by the task in front of you, before starting:

- **Full-work**: a non-trivial coding task the user wants implemented end to end (a feature, a fix that
  changes behavior, work spanning multiple files or systems, or anything touching security, data, external
  interfaces, or migrations).
- **Planning-only**: the user wants a plan, design, or decision without implementation, or explicitly asks
  to plan.
- **Lightweight path**: a small, low-risk, mechanical change: a one-liner, a typo or copy fix, a config
  tweak, a doc edit, a rename. Skip the review panel entirely: make the change, run the verify gate (below),
  and give it one focused self-review. Don't spin up system-architect, security, or observability for this.
- **Neither**: a read-only question or a conversational answer runs no workflow.

If a task looks lightweight but the change turns out to touch behavior, security, or multiple systems,
stop and escalate to full-work rather than pushing a large change through the light path.

Whatever the choice, the final handoff names the path that ran (full-work, lightweight, planning-only,
or none), so a report with no vault artifacts is legitimate only under a declared non-full-work path
(⛔ Hard Rules item 2).

### Full-work workflow

Run autonomously end to end. Do not pause for approval between stages, do not ask whether to proceed once
the workflow has started, and do not narrate each skill handoff. Only return to the user when the workflow
completes or when a loop cap is hit with unresolved issues (see issue handling below).

#### Stage 1: Plan & review

1. `[skill: system-architect]`: analyse the user prompt and produce a plan.

2. **Independent review panel (run in parallel).** The following are independent lenses on the *same* plan;
   none is an input to another. Dispatch them concurrently (e.g. as parallel subagents) rather than chaining
   them. Each reads the plan and returns findings (the `delivery-lead` lens also reads the original user
   prompt, its ground truth):
   - `[skill: <appropriate programming language/framework skill>]`: technical review with in-depth
     knowledge of the relevant language(s).
   - `[skill: security]`: review as a security professional.
   - `[skill: observability-engineer]`: recommend a reasonable level of observability to add.
   - `[skill: delivery-lead]`: scope-discipline review. Checks the plan against the *original user prompt*
     for scope creep, gold-plating, speculative generality, and work solving problems the ask never raised.
     This is the panel's one lens that argues for less; the others all pull toward adding. Give it the
     user's original prompt verbatim, since that prompt, not the plan, is its ground truth. See
     `brain/knowledge/scope-discipline.md`.
   - **Domain routing (principle, not a fixed list):** add any domain or framework skill whose area the
     plan actually touches, so it can weigh in before the stage completes. Examples: `postgres`,
     `azure-sql-server`, `azure-cosmos`, `azure-eventhub`, `nosql-database`, `angular`, `reactjs`, `nextjs`,
     `godot`, `unity`, `unreal-engine`, `game-developer`, `linux-shell-scripting`, `linux-troubleshooting`.
     Include every subject that applies, not just the first match, and route by what the plan does rather
     than by this list staying current.

3. **Consolidate.** Merge the panel's findings, de-duplicate overlaps, and classify each as **blocking**
   (a correctness, security, data, or design flaw that must be resolved) or **suggestion** (an optional
   improvement). Every reviewer treats an assumption about external/third-party behavior that lacks a
   working link to official, version-current docs as a **blocking** finding: the plan cites its
   external-behavior claims and the citations resolve, or it does not pass. See
   `brain/knowledge/general-problem-solving.md` §"Back external assumptions with an official source".

   **Scope-vs-hardening tiebreak.** When the `delivery-lead`'s scope-trimming collides with an additive
   lens (security, observability, a language rule), correctness, security, and data-safety findings
   outrank the trim: don't ship unsafe to stay lean. But the delivery-lead's legal counter is to challenge
   the *feature that requires* the addition rather than the addition itself. If the feature a hardening
   finding protects was never in the ask, cutting the feature resolves both at once and the hardening
   leaves with it. Settle that scope question before spending a revision cycle hardening something that
   shouldn't exist. See `brain/knowledge/scope-discipline.md` §"The tiebreak".

**Issue handling (Stage 1):**
- **Blocking findings** → hand control back to `[skill: system-architect]` to revise the plan. Then
  re-review only the perspective(s) whose concern the revision touched, plus a quick consistency check that
  the change didn't break another lens's assumption. Do **not** re-run the whole panel from the top.
- **Suggestions** → fold the worthwhile ones into the plan directly; no revision cycle needed. Note any you
  deliberately skip and why.
- **Cap:** limit revision to 3 cycles. If blocking issues remain after the 3rd, stop and hand the user a
  real decision point: the specific unresolved disagreement, the revisions already tried, and the trade-off
  at stake.

On completion with no blocking issues, the finalized plan is saved to the vault (per the protocol above),
and the workflow proceeds directly to Stage 2 without pausing.

#### Stage 2: Execute, verify & review

1. `[skill: <appropriate programming language skill>]`: execute the approved plan.

2. **Verify gate (mandatory before review).** Run the formatter/linter, the build/typecheck, and the test
   suite, per `coding-general.md` "before delivering". Then, when the change has a runtime surface (an
   endpoint, a CLI, a UI), exercise it end to end: use the runtime's `run` skill if one is listed (in
   Claude Code it launches and drives the project's app); if no such skill exists in the runtime, run
   the app or entry point directly and confirm the changed behavior with your own eyes. Fix every
   failure here, and a deprecation warning on a
   line the change touched counts as a failure, not noise (⛔ Hard Rules in `coding-general.md`).
   A tool this gate needs that is missing or the wrong build is itself a blocker: report it with
   the exact install command for the user, never self-fix it by downloading a binary or
   installing a tool (`coding-general.md` ⛔ Hard Rule 7).
   **Do not proceed to review with a red build, failing tests, lint errors, or new deprecation
   warnings**: reviewing unrun code reviews a guess. **"Fix" never means revert:**
   when a test fails because it encodes behavior this change intentionally altered, the test is stale, so
   update or remove it. Never roll back the deliberate change, relax a validation, or weaken production code
   to turn a test green (see `general-problem-solving.md` §3, "A deliberate change is the source of truth").

3. `[skill: branch-review]`: review the work that was done.

**Issue handling (Stage 2):**
- **Blocking review findings** → hand back to the programming language skill to fix them, re-run the verify
  gate, then re-review the affected areas (not necessarily the whole diff again).
- **Suggestions** → apply the worthwhile ones; skip the rest.
- **Cap:** limit to 3 cycles. If blocking issues remain after the 3rd, stop and report the specific
  remaining issues with what was tried.

On completion, the review is saved to the vault, and the workflow returns to the user with a summary of the
work plus the compliance ledger: the workflow path that ran (full-work, lightweight, or planning-only), the
exact vault note names for the plan, the checkpoint, and the review, the per-command verify results (build,
lint, tests), and the review outcome. The ledger is what makes the report checkable: one `vault_get` on a
named note confirms a stage ran (⛔ Hard Rules item 2).

#### Progress checkpoints (crash recovery)

Every full-work task keeps a live checkpoint note in the vault so a crash, freeze, BSOD, or
token-exhaustion mid-task resumes cleanly instead of re-deriving state. Lightweight-path and
planning-only work skip this.

- **Create** right after the plan is archived: `vault_save` in `project: "implementation-plans"`,
  `parent`-linked to the plan note, name `<repo>--<scope>-progress--<YYYY-MM-DD>`, summary prefixed
  `PROGRESS:`. Tags: `progress`, `handoff`, the repo, plus a concept tag.
- **Content**: DONE / IN FLIGHT / NEXT as a checklist, current branch, a one-line uncommitted-state
  summary, verify-gate status. Repo-relative paths only, no machine-identifying details, secrets
  redacted; never paste raw `git_status` or diff output (see `machine-privacy.md`).
- **Update** with `vault_edit_section` (not full resaves): after each stage or phase completes, after
  the verify gate, after the review verdict, when the re-anchor rule fires (⛔ Hard Rules item 3), and
  BEFORE any risky step (roughly: anything expected to touch more than ~5 files or run longer than a
  build). A checkpoint written only after success is
  useless for the crash it was meant to survive.
- **Close**: when the workflow returns to the user, flip the summary prefix to `DONE:` via
  `vault_set_meta`.
- **Resume**: at the start of any full-work task, and whenever the user says "continue" or "pick up",
  `vault_list` `project: "implementation-plans"` for a `PROGRESS:` note on this repo first, and resume
  from it.

---

### Planning-only workflow

Run **Stage 1** of the full-work workflow exactly as described above: the parallel review panel, principled
domain routing, consolidation, and the severity-gated Stage 1 issue-handling loop. Do **not** run Stage 2.

When Stage 1 completes, return the finalized plan to the user. Do not begin implementation unless the user
explicitly approves and switches to the full-work workflow.
