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
   suite, per `coding-general.md` "before delivering"; use the `verify` skill to exercise the change
   end to end where it has a runtime surface. Fix every failure here, and a deprecation warning on a
   line the change touched counts as a failure, not noise (⛔ Hard Rules in `coding-general.md`).
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
work, the verify results (build and test status), and the review outcome.

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
  the verify gate, after the review verdict, and BEFORE any risky step (roughly: anything expected to
  touch more than ~5 files or run longer than a build). A checkpoint written only after success is
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
