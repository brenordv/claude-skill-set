# Changelog

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