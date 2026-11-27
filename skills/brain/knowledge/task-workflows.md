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
   checkpoint too; planning-only skips the checkpoint by design). The verify gate is done when
   each command's row is in the verify record (the command, its exit status, the tool's own
   summary line), written when the command ran; "tests pass" with no row behind it is a claim,
   not a result. The Stage 2 review is done when the review note exists in
   `code-reviews`, naming the lenses run and their verdicts and carrying the reviewer's own
   re-run of the gate, written when the review completes rather than reconstructed later. Never report a workflow, stage, or skill as used unless you can
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
5. **The path decides whether the plan panel runs, never what loads and never whether the diff
   is reviewed.** `branch-review` runs on every diff that isn't proven all prose ("Choosing a
   workflow" below); the diff decides that, not the path and not the task's size. On every path,
   lightweight included, two reads precede the first edit: the skill for the language or framework being
   touched (its `SKILL.md` plus the reference file it names for the work at hand,
   `testing-guidelines.md` for anything that adds or changes a test) and the knowledge file for
   the task's topic (`brain/knowledge/testing.md` for test work, `brain/knowledge/security.md`
   for auth or input handling, `brain/knowledge/database.md` for schema or queries). Task size
   picks the path; it never decides whether the rules for the task's language and topic apply.
   "Add some tests" is a C# task and a testing task however small the diff, and "it looked small,
   so I went straight to the diff" is the exact rationalization this rule exists to block. A
   handoff for code written without naming the skill file that was read is a violation on its
   face.

**Self-check**: before invoking any planning or review skill, ask "is this the skill set's own
skill?" Before writing "I ran X", ask "can I name X's artifact, or its row in the verify record?"
Before skipping the review, ask "is every changed path a prose file no tool or agent loads as
instructions or configuration, with no hunk changing a command the reader is told to run?"
Before the first edit, ask "which
skill file and which knowledge file did I read for this task?" If the answer is none, stop and read
them.

### Choosing a workflow

Pick the path by the task in front of you, before starting:

- **Full-work**: a non-trivial coding task the user wants implemented end to end (a feature, a fix that
  changes behavior, work spanning multiple files or systems, or anything touching security, data, external
  interfaces, or migrations).
- **Planning-only**: the user wants a plan, design, or decision without implementation, or explicitly asks
  to plan.
- **Lightweight path**: a small, low-risk, mechanical change: a one-liner, a typo or copy fix, a config
  tweak, a doc edit, a rename. Skip the Stage 1 panel entirely: make the change, run the verify gate (below),
  and give it one focused self-review. Don't spin up system-architect, security, or observability for this.
  The language skill and the topic's knowledge file are not on that skip list: they load on this path
  as on every other (⛔ Hard Rules item 5). Neither is `branch-review`: see "The diff decides
  whether a review runs" below. Neither is the baseline: run each gate command the task will run
  once before the first edit, and put the baseline, the verify record, the test-change ledger
  (or `Test changes: none`), and the suppression list (or `Suppressions: none`) in the handoff,
  since this path has no checkpoint. A ledger entry
  whose disposition is `stale` or `defective` means the change touches behavior: escalate to
  full-work and carry the baseline and the entries already made into its checkpoint
  (`brain/knowledge/testing.md` ⛔ Hard Rules 2 and 3).
- **Neither**: a read-only question or a conversational answer runs no workflow.

If a task looks lightweight but the change turns out to touch behavior, security, or multiple systems,
stop and escalate to full-work rather than pushing a large change through the light path.

**The diff decides whether a review runs.** Whether a task is small is the agent's own judgment,
made before the rules that would say otherwise are read, so that judgment never decides whether a
second reader sees the change. Review is the default and the skip has to be proven:
`branch-review` is skipped only when every changed path (untracked and deleted files and both
sides of a rename included, read from `git_status` and the diff) is a prose file that no tool or
agent loads as instructions or configuration, and no hunk changes a command the reader is told
to run. Everything else gets the review, however small:

- any code file, even for a comment-only, copy-only, or formatting-only change (a directive that
  silences a check is a comment);
- any structured file: JSON, YAML, TOML, XML, resource and translation files;
- generated files and lockfiles, and a rename, deletion, or mode change of a non-prose file;
- any file an agent or tool loads as instructions or configuration, whatever its extension: skill
  files, `CLAUDE.md`, agent rules, prompt templates, hook and MCP settings;
- a documentation hunk that changes a command the reader is told to run.

"Can't tell" means review. On a lightweight task the review is dispatched as a subagent with the
user's prompt, the declared path, the verify record (baseline rows included), the test-change
ledger, and the suppression list written into the dispatch prompt, since there is no checkpoint
to point at; blocking findings are
fixed and re-reviewed as in Stage 2. When the review is skipped, the handoff lists the changed
files so the skip can be checked at a glance.

Whatever the choice, the final handoff names the path that ran (full-work, lightweight, planning-only,
or none) and the skill and knowledge files read for it. The path goes in one line:
`Path: <path>; review: ran | skipped, all changed files prose: <list> | not run: suite red | n/a; path check: clean | <fact> | n/a`.
A report with no plan note is legitimate only under a declared non-full-work path. One with no
review note is legitimate only when that line shows a proven all-prose diff, the red exit of
Stage 2, or a planning-only task, which has no diff (⛔ Hard Rules item 2). A report
of code written with no skill file named shows the Hard Rules item 5 gap in plain sight.

### Full-work workflow

Run autonomously end to end. Do not pause for approval between stages, do not ask whether to proceed once
the workflow has started, and do not narrate each skill handoff. Only return to the user when the workflow
completes, when a loop cap is hit with unresolved issues (see issue handling below), when the
suite can't go green without weakening a test (the red exit in Stage 2), or when the only way
past a security rule's finding is to silence it (`coding-general.md` ⛔ Hard Rule 13).

#### Stage 1: Plan & review

1. `[skill: system-architect]`: analyse the user prompt and produce a plan. The plan names the
   existing tests the change is expected to make stale, each with the behavior change that does
   it, or says "none expected" (`brain/knowledge/general-problem-solving.md` §2).

2. **Independent review panel (run in parallel).** The following are independent lenses on the *same* plan;
   none is an input to another. Dispatch them concurrently (e.g. as parallel subagents) rather than chaining
   them. Each reads the plan and returns findings (the `delivery-lead` lens also reads the original user
   prompt, its ground truth):
   - `[skill: <appropriate programming language/framework skill>]`: technical review with in-depth
     knowledge of the relevant language(s).
   - `[skill: security]`: review as a security professional against a stated threat model. The
     review opens with the model, and every finding carries its attacker, entry point,
     precondition, asset, and rating (`brain/knowledge/security.md` ⛔ Hard Rules).
   - `[skill: observability-engineer]`: recommend a reasonable level of observability to add.
   - `[skill: delivery-lead]`: scope-discipline review. Checks the plan against the *original user prompt*
     for scope creep, gold-plating, speculative generality, and work solving problems the ask never raised.
     This is the panel's one lens that argues for less; the others all pull toward adding. Give it the
     user's original prompt verbatim, since that prompt, not the plan, is its ground truth. See
     `brain/knowledge/scope-discipline.md`.
   - **Domain routing (principle, not a fixed list):** add any domain or framework skill whose area the
     plan actually touches, so it can weigh in before the stage completes. Examples: `postgres`,
     `azure-sql-server`, `azure-cosmos`, `azure-eventhub`, `nosql-database`, `angular`, `reactjs`, `nextjs`,
     `godot`, `unity`, `unreal-engine`, `game-developer`, `linux-shell-scripting`, `linux-troubleshooting`,
     and `state-machine-auditor` when the plan adds or changes a persisted status advanced by several
     handlers or services, an ordered lifecycle, or flags on one owner. Include every subject that
     applies, not just the first match, and route by what the plan does rather than by this list
     staying current.

3. **Consolidate.** Merge the panel's findings, de-duplicate overlaps, and classify each as **blocking**
   (a correctness, data, or design flaw, or an in-model security finding rated blocking, that must
   be resolved) or **suggestion** (an optional improvement). Every reviewer treats an assumption about external/third-party behavior that lacks a
   working link to official, version-current docs as a **blocking** finding: the plan cites its
   external-behavior claims and the citations resolve, or it does not pass. See
   `brain/knowledge/general-problem-solving.md` §"Back external assumptions with an official source".
   Security findings are classified by `brain/knowledge/security.md` ⛔ Hard Rules: one blocks only
   when it is inside the threat model and meets Hard Rule 6. A high-impact, low-likelihood finding
   starts no revision cycle; it is recorded with its fix-or-accept question and raised at handoff.
   The stated threat model, each out-of-model concern with its precondition, and each accepted risk
   with its reason are recorded in the plan's notes.

   **Scope-vs-hardening tiebreak.** When the `delivery-lead`'s scope-trimming collides with an additive
   lens (security, observability, a language rule), correctness, data-safety, and in-model security
   findings outrank the trim: don't ship unsafe to stay lean. But the delivery-lead's legal counter is to challenge
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

1. `[skill: <appropriate programming language skill>]`: execute the approved plan. Before the
   first edit, run each gate command the task will run (format check, lint, build or typecheck,
   tests) once and record the baseline in the progress checkpoint's "Verify" section, one row
   per command in the verify record's shape (step 2), labeled `baseline`. "That warning was
   already there" and "that test was already failing" are claimable only from these rows. For
   the test suite the row holds the
   exact command, the runner's own summary figures (total, passed, failed, skipped or ignored,
   and any other bucket it prints), and the name of every failing and skipped test, capped at 20
   with "and N more". Parametrized cases count as the runner counts them; the comparison is
   baseline against final within this task. When it can't run, its baseline row is `not run: <reason>`; a build broken
   before the first edit is the baseline state, recorded as such. As tests change, write each
   test-change ledger entry to the checkpoint's "Test changes" section at the moment the test is
   touched (`brain/knowledge/testing.md` ⛔ Hard Rules 2 and 3), and each suppression to its
   "Suppressions" section at the moment it is added (`coding-general.md` ⛔ Hard Rule 13).

2. **Verify gate (mandatory before review).** Run the formatter/linter, the build/typecheck, and the test
   suite, per `coding-general.md` "before delivering". Write the verify record as each command
   runs, one row per command, labeled `final`, in the checkpoint's "Verify" section:
   - the kind: format check, lint, build or typecheck, tests, end-to-end;
   - the command as typed, environment-manager prefix included, with paths repo-relative and any
     secret value replaced by its variable name (`machine-privacy.md`);
   - the result: the exit status and the tool's own last summary line, or `(no output)`. On a
     failure, add the failing identifiers (test names, or rule id and file), capped at 20 with
     "and N more". Never a log.

   A command that didn't run is `not run: <reason>`, and a gate the project doesn't have is
   `n/a: <reason>`, so "no linter exists" never reads the same as "skipped". The format row
   records the check form the language skill names; if a write form ran, the row says so. A
   `final` row holds the latest run only, and any edit after that run makes it stale: the command
   runs again. The tests row uses the baseline's command, or the difference is a test-change
   ledger entry. Then, when the change has a runtime surface (an
   endpoint, a CLI, a UI), exercise it end to end: use the runtime's `run` skill if one is listed (in
   Claude Code it launches and drives the project's app); if no such skill exists in the runtime, run
   the app or entry point directly and confirm the changed behavior with your own eyes. Fix every
   failure here, and a deprecation warning on a
   line the change touched counts as a failure, not noise (⛔ Hard Rules in `coding-general.md`).
   Fixed means fixed in the code: a finding silenced with a suppression, a config change, or a
   swallowed exit status is not fixed (`coding-general.md` ⛔ Hard Rule 13).
   A tool this gate needs that is missing or the wrong build is itself a blocker: report it with
   the exact install command for the user, never self-fix it by downloading a binary or
   installing a tool (`coding-general.md` ⛔ Hard Rule 7).
   **Do not proceed to review with a build failure, lint error, or deprecation warning that is
   new relative to the baseline, or a test that is red relative to it**: reviewing unrun code
   reviews a guess. A finding the baseline already had, in code the change doesn't touch, is
   left alone and reported, like a baseline-red test (`coding-general.md` ⛔ Hard Rule 13). A test that was
   already red in the baseline, or is red for a named environmental reason, doesn't block the
   review; it is left untouched and reported red by name. With no baseline, every red test without
   a named environmental reason counts as red relative to it. Run the suite with the baseline's command; the totals are a tripwire
   (three tests deleted and five added still reads as a gain), and the diff is the proof.
   **"Fix" never means revert:**
   when a test fails because it encodes behavior this change intentionally altered, the test is stale, so
   update it, or remove it when that behavior is gone. Never roll back the deliberate change, relax a validation, or weaken production code
   to turn a test green (see `general-problem-solving.md` §3, "A deliberate change is the source of truth").
   **"Fix" never means weaken the test either:** a red test is diagnosed before it is touched, and
   "stale" needs a quoted sentence as its ground. A test the plan didn't predict as stale is
   a regression until diagnosed. Deleting it, skipping it, loosening its assertion, rewriting its
   expected value to the actual output, or narrowing the test command are moves that go in the
   ledger with a disposition and a ground, or don't happen (`brain/knowledge/testing.md` ⛔ Hard
   Rules 2 and 3). **Red is a legal ending:** when a test red relative to the baseline can't be
   made green without weakening it, stop. Return to the user with `tests: RED (<n> failed)`, each
   red test's name and file, the diagnosis reached, what was tried, and "review not run: suite
   red"; write the same to the checkpoint first.

3. `[skill: branch-review]`: review the work that was done. Hand it the user's original prompt
   verbatim, the declared path, the progress checkpoint's note name (it holds the verify record
   with its baseline rows, the test-change ledger, and the suppression list), and the plan note's name with the
   version recorded when Stage 1 finalized. The review re-runs the verify record's commands
   itself and compares; it doesn't take the rows on trust.

**Issue handling (Stage 2):**
- **Blocking review findings** → hand back to the programming language skill to fix them, re-run the verify
  gate, then re-review the affected areas (not necessarily the whole diff again).
- **Suggestions** → apply the worthwhile ones; skip the rest.
- **Cap:** limit to 3 cycles. If blocking issues remain after the 3rd, stop and report the specific
  remaining issues with what was tried.

On completion, the review is saved to the vault, and the workflow returns to the user with a summary of the
work plus the compliance ledger: the `Path` line ("Choosing a workflow"), the
skill and knowledge files loaded for the work, the exact vault note names for the plan, the checkpoint,
and the review, one Verify block (the review's `Verify re-run` line verbatim, then each command
with its baseline and final result; where no review ran, the author's rows alone, which are then
the author's word only), the test-change ledger copied from the checkpoint (or
`Test changes: none`), the review's `Test integrity lens` line verbatim, the `Suppressions` line
with its entries (or `Suppressions: none`), every test still red by
name, and the review outcome. When the suite ended red and no review ran, the block opens with
`Verify re-run: not run: review not run, suite red`. The ledger is what makes the report checkable: one `vault_get` on a
named note confirms a stage ran (⛔ Hard Rules item 2).

#### Progress checkpoints (crash recovery)

Every full-work task keeps a live checkpoint note in the vault so a crash, freeze, BSOD, or
token-exhaustion mid-task resumes cleanly instead of re-deriving state. Lightweight-path and
planning-only work skip this; a lightweight task's records go in the handoff and, when its diff
gets a review, in the dispatch prompt.

- **Create** right after the plan is archived: `vault_save` in `project: "implementation-plans"`,
  `parent`-linked to the plan note, name `<repo>--<scope>-progress--<YYYY-MM-DD>`, summary prefixed
  `PROGRESS:`. Tags: `progress`, `handoff`, the repo, plus a concept tag.
- **Content**: DONE / IN FLIGHT / NEXT as a checklist, current branch, a one-line uncommitted-state
  summary, the plan note's version at Stage 1 finalization, a "Verify" section holding the verify
  record (`baseline` rows from Stage 2 step 1, `final` rows from the verify gate), a "Test
  changes" section holding the test-change ledger (`testing.md` ⛔ Hard Rule 3), and a
  "Suppressions" section (`coding-general.md` ⛔ Hard Rule 13), each `none` until it has an
  entry. Repo-relative paths only, no machine-identifying details, secrets
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
