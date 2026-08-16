# Changelog

## v4
- Added a Rust-specific quality check workflow test code coverage and also tests for mutants, helping imnprove code quality by deterministically checking if the tests are at least actually testing something.

## v3
- Hardened security by preventing the agent from using tools that would circumvent MCP tools designed to keep it in check (to avoid reading secret/sensitive files, or straying too far from the current code)
- Added a GitHub workflow that runs some checks and lints to make sure this repo is well maintained, without broken links between the files.

## v2
- Added new skill `deliverey-lead`, and included it in the `full-work`, and `planning-only workflows`.


## v1
- Initial Release