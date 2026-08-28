# Changelog

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