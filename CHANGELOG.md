# Changelog

## v18
- New `state-machine-auditor` skill and `brain/knowledge/implicit-state-machines.md`. The
  knowledge file defines implicit state machines (behavior keyed to field, flag, or row values with
  no one place listing the states), ten detection signals S1-S10 (status fields written from
  several places, repeated switches, exclusive flags, nullable-as-state, temporal coupling,
  event-first handlers, UI-guarded transitions, persisted statuses advanced by several processes,
  history bookkeeping, and a flag added to make a symptom stop), the guards that keep a lone toggle
  from being flagged, the SCXML vocabulary for maps, a flaw catalog F1-F15 with default severities
  (security state is Critical by default), and a smallest-first fix ladder whose exhaustive-dispatch
  rung gives the per-language setup, including C# CS8509 as an error with CS8524 suppressed and no
  discard arm. Every external source it cites was opened and checked.
- The skill has two modes. Review mode takes a diff or a Stage 1 plan, traces every writer and
  reader of the state the change touches, and compares the transition table before and after.
  Audit mode sweeps a scope, maps each machine (states, transitions with `file:line`, guards,
  readers, a Mermaid diagram, uncovered states, flaws), and archives the map in the new pinned
  vault project `state-machine-maps`; a file in the audited repo is written only on request. Its
  Hard Rules keep it read-only and static, keep secret-shaped files out of every search, and keep
  values out of maps (names only, placeholders, a scrub scan before saving).
- branch-review Step 4 runs the auditor as a subagent when an added, modified, or deleted line
  touches state (triggers keyed to the signal ids, deletions and lone flags included), folds its
  findings in as `[State machine F<n>]`, and records a lens line in the Summary: ran, triggered but
  not run with the reason, or not triggered. Its "review the diff" principle names the auditor's
  Notes as the one exception. `task-workflows.md` routes plans with persisted multi-writer
  statuses, ordered lifecycles, or flag clusters to the auditor on the Stage 1 panel, and
  `review-heuristics.md` §Correctness gained three findings: a new state member until every reader
  handles it, an unguarded write to persisted state, and a flag added to stop a symptom.
- `vault-operations.md` and the README list the new archive; the README catalog lists the skill.

## v17
- Added three `coding-general.md` ⛔ Hard Rules. Hard Rule 9: a summary, docstring, or doc
  comment describes the unit it sits on and never names its callers, consumers, or the services
  that relay it; the "explain inline instead of pointing at docs" rules there and in csharp Hard
  Rule 10 now say the inline context goes at the code that acts on it. Hard Rule 10: a handled
  failure never ends on the success path. The failure propagates uncaught, or a catch throws or
  wraps with the original kept as the cause, returns a failure the caller's contract makes it
  handle, recovers for real, or reports at a boundary, with message-handler rules for hosts that
  redeliver and for Event Hubs triggers, which advance the checkpoint either way. Logging is never
  an ending, a failure is logged once, and §5's "At minimum, log them" and "return empty, not null"
  bullets are rewritten to match, as are the csharp style guide's empty-list bullet and the csharp
  §8 log-and-rethrow bullet. Hard Rule 11: a credential is attached by the client's configuration, never
  by its call surface or a URL, and an exposed one is flagged for rotation. Driven by three
  incidents: an Event Hub message model whose summary described the frontend and function around
  it; a Cosmos repository whose trailing `catch (CosmosException)` only logged, so the caller
  published success after a failed save and no test broke when throws were added; and a Refit
  refactor that moved an Azure Functions key from `?code=` to a per-call `[Header]` parameter
  instead of the client registration.
- `testing.md` gained a ⛔ Hard Rules block: every catch, except, or error arm a change adds is
  driven by a test whose assertion matches how the arm ends, and a coverage percentage never
  excuses an undriven arm. The language skills mirror the rules in their own blocks (csharp Hard
  Rule 17 for catch endings and Hard Rule 18 for Refit credentials, python Hard Rule 8, rust Hard
  Rule 6, each naming its language's swallow shapes), and each testing guide gained a "Failure
  paths" section. csharp §8 now says where each kind of credential attaches (a static key in
  `ConfigureHttpClient`, a rotating key in a transient `DelegatingHandler`, tokens from the repo's
  token provider) and how header-log redaction differs before and after .NET 9.
- `general-problem-solving.md` §2: a stated reason is the acceptance criterion. Options are
  compared at the named step's footprint, the named mechanism is kept and done in its strongest
  form, and a stronger different mechanism goes in the report as a follow-up. `scope-discipline.md`
  counts that stronger form as in scope, and both minimal-change bullets say minimal limits what
  you touch, never how well a stated goal is met. `security.md` covers credentials at client
  configuration, rotation after exposure, and least privilege.
- Review side: `review-heuristics.md` gained findings for log-and-fall-through catches (Critical
  when the caller reports success or the catch sits in a security decision), undriven arms,
  credentials in signatures or URLs, real credential values in source or logs (Critical),
  interface-only credential tests, and summaries that describe their surroundings, plus a carve-out
  letting a test assert the request its own registration code produces. branch-review Step 4
  carries the matching items, including a stated-reason check that applies only when the task gave
  one.
- Fixed samples that taught a failure read as success: the Event Hubs C# send error handling,
  buffered-producer failure handler, and processor consumer, plus the checkpoint key rule, which
  claimed a skipped checkpoint redelivers; the Java and TypeScript batch re-adds that ignored
  `tryAdd`'s result and the Rust add that ignored `try_add_event_data`'s bool; Java's empty transient `processError` branch; the Cosmos ETag, Java,
  TypeScript bulk, and Python service samples; both Angular state-management patterns; and the
  SAST scanner, which reported a failed Semgrep ruleset as a clean scan, with CI steps that hid
  scanner crashes behind `|| true`.
- `skills/python/SKILL.md` pointed reviews at the runtime's `code-review` skill, which
  `task-workflows.md` Hard Rule 1 bans; it now names `branch-review`.

## v16
- Aligned the MCP knowledge files with mcp-toolset v23. `git-readonly-operations.md` maps
  `git grep -c` to `countOnly`, pathspec wildcards and exclusions to `globs` and `excludePaths`, and
  `git log --all` and `-P` to `allRefs` and `perlRegex`. It says a wildcard in `paths` is now
  `RejectedArgument` (an empty success on older builds), `grep: "A|B"` matches nothing without
  `perlRegex`, how to page `git_file_at_ref` with `maxBytes` and `next_byte_offset`, where
  `old_mode` and `new_mode` show a mode change, and which pinned behaviors (filter drivers compared
  raw, dirty submodules unlisted, `log.follow` ignored, no lazy fetch in a partial clone) are
  expected results rather than gaps. `text-search-operations.md` covers `count_only` and
  `total_match_count` (v1.5.0) and case-insensitive ignore-file names and the unlistable-directory
  `InternalError` (v1.8.0). `text-edit-operations.md` covers the unlistable-directory failure
  (v1.9.0) and `OperationBudgetExceeded` writing nothing when the budget runs out after selection
  (v1.10.0). `vault-operations.md` is unchanged: file-vault changed only its logging and its git
  lookup for project inference, and none of the file's guidance depends on either.
- `install-reference.md` registers the `skill-stats-cli` hook on `UserPromptExpansion` (matcher
  `.*`, the skills the user types) as well as `PostToolUse` (matcher `Skill`, the skills the model
  invokes), with the 10 s timeout the CLI README now documents, and says why `skill-stats-cli`
  1.1.0 is a precondition for the new entry: 1.0.0 exits 2 on a failure, which blocks the prompt
  on that event. Step 4 checks each entry with a before-and-after `usage_summary` pair and reads a
  stuck count from `ingest-errors.log`; the update flow adds the missing entry to a
  `PostToolUse`-only registration after the binary swap.
- `route-to-text-tools` (`.sh` and `.ps1`): the redirect hints name `files_only` and `count_only`
  for `grep -l` and `-c`, and `countOnly`, `globs`, `allRefs`, and `perlRegex` for git, so a denied
  `git grep foo -- '*.cs'` lands on `globs` instead of a `paths` entry the server rejects. Two new
  `tools/hook-cases.tsv` rows pin that text in both implementations (86 cases to 88).

## v15
- Aligned the MCP knowledge files with mcp-toolset v22. `git-readonly-operations.md` maps
  `git show <ref>:<path>` to the new `git_file_at_ref` and `git ls-files --stage` to `git_ls_files`
  with `stage: true` (git-ops v2.2.0), notes that `git_show` now rejects a `<rev>:<path>` ref, and
  says the secret-file ban is the only guard on `git_file_at_ref`, since git-ops has no denylist.
  `text-search-operations.md` covers tier specificity beating directory depth (v1.4.4), the
  `build/**` `include_ignored` example and the pre-v1.4.5 short-or-empty `truncated: true` result
  on scoped selections (v1.4.5), and `PatternInvalid` for an uncompilable glob plus the
  `InternalError` cases (v1.4.2, v1.4.6). `text-edit-operations.md` covers the `ignore_file`
  refusal and undo skip (v1.4.0), `truncated` and `skipped_symlinks` on sweeps (v1.5.0, and
  Hard Rule 4's dry-run review now checks `truncated`), the unreadable-ignore-file `InternalError`,
  writable agent config inside the base root, and corrects the denylisted-`paths` note: those files
  are dropped without a report, not refused.
- `security-hardening.md`: `mcp__skill-stats` joins the suggested `allow` list, and the notes show
  how to make agent config unwritable to `text-edit` with `MCP_TEXTEDIT_EXTRA_DENY`.
  `install-reference.md` asks about that opt-out during `text-edit` configuration.
- `install-reference.md` now installs `skill-stats` with its `skill-stats-cli` hook. Before, the
  hook was left to the CLI's README, which ground rule 3 forbids the installing agent from acting
  on, so the store was never created and the `usage_summary` smoke call failed Step 4 with
  `StoreUnavailable`, blocking the manifest. The new "The skill-stats hook" section carries the
  `PostToolUse` registration per OS (`cmd.exe /c` on Windows, which doesn't start a bare `.exe`),
  Step 4 runs one skill before checking `total_records`, and the manifest records `hookPath`.
- `route-to-text-tools` (`.sh` and `.ps1`) and the `hooks/README.md` table: the git-ops redirect
  hint now sends `git show <ref>:<path>` to `git_file_at_ref` and `git ls-files --stage` to
  `git_ls_files` with `stage: true`, so a denied shell call lands on a tool that accepts it.

## v14
- Added `task-workflows.md` ⛔ Hard Rule 5: the workflow path decides how much review runs, never
  what loads. On every path, lightweight included, the skill for the language being touched (its
  `SKILL.md` plus the reference file it names for the work, `testing-guidelines.md` for tests) and
  the knowledge file for the task's topic (`testing.md` for test work) are read before the first
  edit, and the handoff names them. Mirrored as item 9 of the repo CLAUDE.md always-in-context
  block, and the "non-trivial task" gate on reading topical knowledge files there is gone: the
  trigger is the topic, never the size. Wired into `coding-general.md` as ⛔ Hard Rule 8 (plus a
  §2 planning step and the §10 handoff walk), `general-problem-solving.md` §1, §3, §5, and its
  anti-patterns, the lightweight-path and handoff text in `task-workflows.md`, the csharp skill's
  testing preamble, and the README. Driven by a C# "add some tests" task that went straight to the
  diff with neither the csharp skill nor `testing.md` loaded because it looked small, then filled
  the gap with fixed calendar dates and invented literal ids, both of which those files ban.
- Extended `coding-general.md` ⛔ Hard Rule 6 (and CLAUDE.md item 7) to mechanisms a guideline
  names by example: `TimeProvider` is the shape for code that must read the clock itself; when the
  method under test already takes the instant as a parameter, the test passes it, an unused
  real-clock fallback on that parameter is removed, and no clock is injected. The csharp Hard
  Rule 14 and the Dates & Times section of its testing guide now say to read the signature first
  (with a good/bad pair), `testing.md` §Determinism and its anti-pattern table carry the
  language-agnostic form, and a `review-heuristics.md` §Testing bullet plus the `branch-review`
  Step 4 mechanism item catch it in review. Same incident: after the correction, the agent read
  the guide, applied the `TimeProvider` line literally, and added an abstraction beside a `day`
  parameter the test could have passed.
- `general-remembering-lessons.md`: a correction that reveals an existing rule went unapplied is a
  lesson about routing, since the rule is already written. Don't save a per-repo memory restating
  it; name the trigger that failed (skill never loaded, reference file skipped for size, example
  mechanism applied literally) and save that, or fix the trigger when the skill set is the repo at
  hand.
- `skill-authoring.md` gains failure modes 6 (a rule gated by a size judgment) and 7 (a rule
  executed literally) with their structural fixes: write triggers as topics, never proportions, and
  state a rule's intent before its example mechanism, with the check that precedes it.
- Added a seventh hook, `compact-test-output` (`PostToolUse` on `Bash|PowerShell`, `.ps1` and
  `.sh`): it rewrites test-runner output through `hookSpecificOutput.updatedToolOutput` before the
  model reads it. A passing `dotnet test`, `pytest` (default or `-q`), `cargo test`, jest, or
  vitest run collapses to its summary line(s); a run carrying failure indicators keeps every unrecognized line
  and drops only positively identified noise; anything else passes through untouched. The
  replacement is never larger than the original, so Claude Code's Bash output window stays the only
  size limit, and `#keep-output` on the command skips the hook. Documented in `hooks/README.md`,
  `install-reference.md`, and the README.
- The hook harness grew a `rewrite` verdict and an optional sixth TSV field (the payload's
  `tool_response`), plus the `@CTO_FILLER@` and `@LONG_LINE@` placeholders; rewrite rows match
  their signature against the decoded `updatedToolOutput`, never raw stdout. `tools/hook-cases.tsv`
  goes from 60 to 86 rows.
- `skills/csharp/testing-guidelines.md` gains an xUnit v3 / Microsoft.Testing.Platform section:
  how to detect the engine, the `dotnet test` MTP forms, exit codes 5 and 8, the xUnit v3 filter
  switches, coverage through `Microsoft.Testing.Extensions.CodeCoverage` or `coverlet.MTP`, and the
  package guidance from xunit.net (`coverlet.collector` has no role under MTP;
  `Microsoft.NET.Test.Sdk` stays optional and recommended). SKILL.md §15 carries the same note.

## v13
- Updated Azure Cosmos DB skill.

## v12
- Added a ⛔ Hard Rules block to `task-workflows.md` binding every workflow stage to this skill
  set's own skills: Claude Code's bundled near-namesakes (`/code-review`, `/security-review`,
  `/simplify`, `/verify`) are never substitutes for `branch-review`, `security`, and the Stage 1
  panel, while `/review` stays out of the ban (remote-PR review is a role the set doesn't cover)
  and so do utilities like `run`. A stage now counts as run only when its vault artifact exists and
  carries the stage's evidence, the completion handoff names the workflow path, the exact vault
  note names, and the per-command verify results, and a re-anchor rule makes the agent re-read the
  workflow file at stage boundaries or after compaction whenever it can't quote the current
  stage's steps (appending a line to the progress checkpoint when one exists). Driven by two
  incidents: an agent proposing the bundled code-review over branch-review, and a long session
  claiming workflow compliance it couldn't evidence.
- Mirrored the two highest-signal rules into the repo CLAUDE.md always-in-context block (items 6
  and 7), per the `skill-authoring.md` failure-mode-5 playbook. The hoist works because CLAUDE.md
  reloads from disk after compaction, verified against the Claude Code prompt-caching docs; the
  knowledge files it points to are exactly what long sessions evict.
- Added `coding-general.md` ⛔ Hard Rule 6: match the mechanism to the cases in front of you. An
  accumulator array, registry, or config-driven loop whose only justification is future additions
  nobody named is a defect even when it works; the test is whether deleting the mechanism and
  writing the cases directly reads shorter and clearer, with an exemption for extractions made for
  testability or clarity. Wired into §1 (an Open/Closed boundary sentence and an over-engineering
  cross-reference), the §10 handoff walk, a new `review-heuristics.md` §Maintainability heuristic
  plus a boundary qualifier on the extract-reusable-logic bullet there, a `branch-review` Step 4
  checklist item, and a README general-rules bullet. Driven by a deploy script that gated two
  settings behind a conditionally-built settings array where an if/else was the right size.
- Documented the `skillOverrides` per-skill states in a new README workflow-fidelity paragraph,
  with a ready-to-paste block hiding the overlapping bundled skills (`off` for the duplicates,
  `user-invocable-only` where a manual fallback is worth keeping) and its caveats: per-machine
  config the repo documents but does not apply, merge rather than replace, bundled names vary by
  Claude Code version. The same paragraph records the decision against an orchestrator agent (a
  subagent can't observe or intercept the main conversation; the named-artifact ledger does the
  supervising) and states plainly that the Hard Rules are doc rules while the hooks,
  `skillOverrides`, and the hook-fed skill-stats record are the mechanical and audit layers.
- Added `coding-general.md` ⛔ Hard Rule 7: acquiring and running software is the machine owner's
  act. A tool that is missing or the wrong version or build is reported with the exact install
  command for the user, never self-fixed by downloading a release binary, installer, or script
  and executing it, and global tool installs (`dotnet tool install -g`, `cargo install`,
  `npm install -g`, winget, brew) count as the same act. Still in bounds: tools already installed
  that the task implies, the project's own dependency manager inside its manifest and local
  environment, and a documented install flow the user invoked by name (`install-reference.md`).
  Wired into the §10 handoff walk, a §12 tooling-hygiene bullet, the Stage 2 verify gate in
  `task-workflows.md`, a new item 8 in the repo CLAUDE.md always-in-context block, a README
  general-rules bullet, and user's-act clarifiers on the install sections of the rust and csharp
  testing guides. Promoted from the vault lesson written when an agent fetched and executed the
  official dart-sass release zip mid-task to fix a version mismatch, in a session where installs
  were explicitly the user's call; the lesson was purged after promotion per the
  `skill-authoring.md` protocol.

## v11
- Replaced `theme-factory` with `skills/visual-design/`, a consolidated high-end design skill:
  an entry file with eight design Hard Rules (composited-property motion, no default `linear`
  on state transitions, blur confined to chrome/overlays, reduced-motion plus no-JS visibility,
  LCP and scroll-jack bans, AA contrast, anti-AI-tell defaults, no external hosts in artifact
  output) and five references covering canonical design tokens, motion physics and recipes,
  Apple HIG/Liquid Glass plus the apple.com marketing playbook, premium page composition, and
  the artifact-theming content carried over intact from theme-factory (same 10 themes and
  triggers, so nothing users relied on is lost; theme-factory had zero recorded invocations).
  A `review-heuristics.md` Frontend & Motion bullet backs Hard Rules 1 and 4 on the review
  side, and the README skill table row was swapped.

## v10
- Added `install-reference.md`, an agent-followable checklist for setting up the skill set on a new
  machine: deploy mode, hook and tools selection, MCP servers fetched from pinned repo slugs
  (release download or source build), `claude mcp add --scope user` registration, per-server smoke
  checks plus a hook-harness re-run against the installed copies, and a machine-local manifest
  (`~/.claude/skill-set-install.json`) that records what went where so a later session can update
  the install instead of re-deriving it. Ground rules bound the installing agent: timestamped
  settings backups with additive-only merges, fetched READMEs treated as data rather than
  instructions, no secrets in the manifest, and the manifest written only after verification
  passes. The root README points to it from "Using it" and "MCP dependencies".
- Relaxed the Rust skill's error-handling Hard Rule: `anyhow` now also covers library crates
  internal to their workspace, with `thiserror` reserved for libraries published for external
  consumers. An internal lib whose callers start matching on failure modes is the stated trigger to
  move it to `thiserror`. §2 (Error Handling) and §7 (Forbidden) in `skills/rust/SKILL.md` and the
  README's Rust summary carry the same split.
- Added `coding-general.md` ⛔ Hard Rule 5: a project version moves only as a release act, never as
  a side effect of other work, and never before the first release; an unpublished project keeps its
  initial version however many changes land. Wired into the handoff walk (§10) and §9 Version
  Control Hygiene, plus the review side: a `branch-review` checklist item and a
  `review-heuristics.md` §Infrastructure heuristic, both flagging an unprompted bump as at minimum
  Important. The README's general-rules summary carries the one-line version.
- Added `skills/python/SKILL.md` ⛔ Hard Rule 7: every toolchain command runs through the project's
  environment manager, detected from the lockfile (`uv run`, `poetry run`, `pipenv run`, or the
  venv's `python -m`), never a `.venv` binary called by path or a global install. Wired into the §5
  checklist, the pytest and install commands in `testing-guidelines.md`, and the README's Python
  summary.
- `block-secrets` now catches `tee` and input redirection: `echo KEY=x | tee .env` and `sort < .env`
  passed before because the read/exfil construct list had neither `tee` nor `<`. Both scripts
  updated in sync, the deny message reworded to "reads, writes, or copies" (case-table signatures
  updated to match), four new rows in `tools/hook-cases.tsv`, and the hooks README extended.
- Refreshed `writing-style.md` against the current revision of Wikipedia's signs-of-AI-writing
  field guide: straight quotes/apostrophes rule (curly forms are a documented tell), the
  thematic-break (`---`) tell, vague-association chains ("associated with", "linked to"),
  era-rotated vocabulary (nestled, groundbreaking, participial "emphasizing"/"highlighting"),
  knowledge-cutoff disclaimers and collaborative "we" as chat residue in durable artifacts, and
  citation hygiene (cite content, not coverage; strip `utm_source` params). The self-check list
  grew the same tells.
- Added `warn-writing-tells`, a sixth hook pair (`PostToolUse`, matcher `Write|Edit`): warns when
  the text a write just added carries an em-dash or a curly quote/apostrophe, scanning only the
  written payload (`content`/`new_string`) so tells already present in an edited file never nag.
  The markdown lint enforces the em-dash ban inside this repo only; the hook extends the backstop
  to every repo on the machine. Five rows in the shared case table (banned characters spelled as
  JSON `\u` escapes to keep it ASCII), full section in `hooks/README.md`, hook counts updated
  across both READMEs and the harness headers.
- Documented the file-vault v3.3.0 retrieval surface in `vault-operations.md` and
  `general-remembering-lessons.md`: all-terms-then-ranked-fallback query semantics with
  `query_mode` and the 16-term cap, `vault_list` pagination (`limit`, `count`, `truncated`,
  `cursor`; fallback results cap without a cursor), and the new body-only `vault_search`
  (case-insensitive substring terms, capped snippets, `skipped`), which replaces the
  list-everything-then-`vault_get`-one-by-one retrieval pattern the old server forced.

## v9
- Updated the MCP knowledge files for toolset v16, which ported the pre-run argument-shape validation
  `text-search` gained in v15 to the remaining servers. `git-readonly-operations.md` (git-ops v2.1.0)
  and `text-edit-operations.md` (text-edit v1.3.0) now document the `InvalidArgument` shape rejection
  in their envelope sections, and `vault-operations.md` (file-vault v3.2.0) gained the matching
  `invalid_argument` rule. Each notes the behavior change (an unknown argument name is now rejected
  instead of silently ignored) and that a shape rejection is a caller error, never a capability-gap
  ticket.
- Consistency pass over the v8 additions. `quality-gates.md` caught up with the three-phase gate
  contract: it now documents the file-size phase, exit code 4, and the 2 > 3 > 4 precedence it was
  missing. The root README's hooks section now lists all five hooks (it said four, all `PreToolUse`,
  while `warn-file-size` registers under `PostToolUse` and needs git), and its repo-lint section and
  layout tree mention the hook test harness. CI's gate-suite job was renamed `python-tests` to
  `gate-tests` to match what it runs; anything pinning the old name as a required check needs the new
  one.

## v8
- Added `tools/test-hooks.ps1`, a Windows PowerShell 5.1 behavior harness that runs the five `.ps1` hooks the way they ship. The case table moved out of the bash harness into `tools/hook-cases.tsv`, shared by both harnesses, so a behavior divergence inside a hook pair fails one platform's CI job. Two new regression rows pin the `warn-file-size` secret-skip anchoring that a review had caught broken on the Windows side while every existing check stayed green. Wired into the CI Windows job next to the `.ps1` parse check.
- Added a threshold-sync layer to `tools/test-hooks.sh`: the file-size warn thresholds and size constants declared in five scripts (both `warn-file-size` hooks and the three `*_quality_gate.py` gates) are extracted and cross-compared, so a hand-sync miss fails the harness instead of drifting silently.
- CI's gate-suite job now runs the python and csharp unit suites alongside rust, one step each. The v6 entry claimed all three were wired in; only rust was.

## v7
- Updated `skills\brain\knowledge\text-search-operations.md` to account for the latest version of the `text-search` skill.

## v6
- Added new-code quality gates for C# and Python alongside the Rust one: `skills/csharp/scripts/csharp_quality_gate.py` (diff coverage via `dotnet test` with the coverlet collector's lcov output, mutation via Stryker.NET `--since`) and `skills/python/scripts/python_quality_gate.py` (diff coverage via pytest-cov lcov, mutation via Cosmic Ray with `cr-filter-git`). Same CLI shape and exit codes as the Rust gate. Documented in each skill's testing-guidelines.md and wired both scripts' unit tests into CI. A cross-language overview (install steps, exit codes, skill wiring) lives in `quality-gates.md` at the repo root. In the agent workflow the mutation half of every gate is opt-in: an agent runs the coverage half (`--skip-mutants`) and never commits; the mutation phase runs only after the user commits the work themselves and asks for it, and the scripts' preflight messages route every git write (commit, `git add -N`) to the user.

## v5
- Fixed a parsing bug in the four bash `PreToolUse` hooks. Their deny messages were built with a heredoc inside command substitution, which parses on bash 5.2 but not on the bash 3.2 that ships with macOS: an apostrophe in the message body mis-lexes there and the script fails to load. Three of the four hooks broke on macOS while every Linux CI runner parsed the same source without complaint. Rewrote the nine message blocks to read each heredoc without command substitution.
- Added `tools/test-hooks.sh`, a bash harness that syntax-checks the hooks, guards against the command-substitution heredoc pattern returning, and runs each hook against a table of JSON payloads on stdin. Wired it into CI on Ubuntu (bash 5.2) and macOS (bash 3.2, the shipping interpreter), added a PowerShell parse check for the `.ps1` hooks, and pinned `*.sh` to LF via `.gitattributes`.
- Fixed a second macOS bash 3.2 bug the new harness caught on its first CI run: `route-to-text-tools` split compound commands like `build && grep ...` with a control-character-sentinel here-string that misbehaves on bash 3.2, so the trailing probe slipped through unrouted. Reworked its statement splitter to the newline-based `while read` loop that `block-vcs-writes` already uses, which behaves identically on bash 5.2.

## v4
- Added a Rust-specific quality check workflow test code coverage and also tests for mutants, helping imnprove code quality by deterministically checking if the tests are at least actually testing something.

## v3
- Hardened security by preventing the agent from using tools that would circumvent MCP tools designed to keep it in check (to avoid reading secret/sensitive files, or straying too far from the current code)
- Added a GitHub workflow that runs some checks and lints to make sure this repo is well maintained, without broken links between the files.

## v2
- Added new skill `deliverey-lead`, and included it in the `full-work`, and `planning-only workflows`.


## v1
- Initial Release