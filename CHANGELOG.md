# Changelog

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