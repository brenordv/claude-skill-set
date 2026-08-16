# Rust Testing Guidelines

Framework-specific testing patterns for Rust projects. These complement the general testing principles in `brain/knowledge/testing.md`.

## Unit Tests

Place unit tests at the bottom of each source file:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_config_valid_toml_returns_config() {
        let input = r#"
            [server]
            port = 8080
        "#;

        let config = parse_config(input).unwrap();

        assert_eq!(config.server.port, 8080);
    }
}
```

## Integration Tests

Integration tests exercise the crate through its public API only, the way an external caller would. They live in a top-level `tests/` directory next to `src/`.

- Each file directly under `tests/` compiles as its own separate crate, and cargo lists it separately in the test output. No `#[cfg(test)]` is needed; cargo only builds `tests/` under `cargo test`.
- They reach only your public API. Anything private stays covered by the in-file `#[cfg(test)]` unit tests above.
- Shared helper code goes in `tests/common/mod.rs`, not `tests/common.rs`. The `mod.rs` form tells cargo `common` is a helper module, not a test crate, so it stays out of the test output. Pull it in with `mod common;` and call `common::setup()`.
- Files in subdirectories of `tests/` are not compiled as separate test crates. Only files placed directly in `tests/` become test binaries.
- Integration tests need something to import. A binary-only crate (just `src/main.rs`, no `src/lib.rs`) exposes nothing, so keep the logic in `lib.rs` and let `main.rs` stay a thin shell; both unit and integration tests can then reach it.

Reference: The Rust Programming Language, ch. 11.3 ["Test Organization"](https://doc.rust-lang.org/book/ch11-03-test-organization.html).

### No mirrored test tree

Do not build a separate test project that mirrors `src/`'s folder layout (the C# and pytest convention). It does not fit Rust: unit tests already sit in-file next to the code, and integration tests are organized by the public behavior they exercise, not by the internal module that implements it. Mirroring `src/foo/bar.rs` into `tests/foo/bar.rs` also breaks discovery, since a file inside a `tests/` subdirectory is not compiled as a test crate.

## File-Based Tests

Use `tempfile::tempdir()` for tests that interact with the filesystem:

```rust
#[test]
fn write_output_creates_file_with_content() {
    let dir = tempfile::tempdir().unwrap();
    let file_path = dir.path().join("output.txt");

    write_output(&file_path, "hello").unwrap();

    let content = std::fs::read_to_string(&file_path).unwrap();
    assert_eq!(content, "hello");
}
```

## Test Fixtures

Use helper functions to build test data:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    fn sample_user() -> User {
        User {
            id: 1,
            name: "Alice".to_string(),
            email: "alice@example.com".to_string(),
            active: true,
        }
    }

    #[test]
    fn deactivate_user_sets_active_false() {
        let mut user = sample_user();

        user.deactivate();

        assert!(!user.active);
    }
}
```

## Enum Variant Assertions

Use `assert!(matches!(...))` for checking enum variants:

```rust
#[test]
fn parse_invalid_input_returns_error() {
    let result = parse_command("invalid gibberish");

    assert!(matches!(result, Err(ParseError::UnknownCommand(_))));
}

#[test]
fn state_after_start_is_running() {
    let mut machine = StateMachine::new();

    machine.start();

    assert!(matches!(machine.state(), State::Running { .. }));
}
```

## What to Test

- **Happy paths**: the primary use case works correctly
- **Error conditions**: invalid input, missing files, network failures
- **Meaningful boundary values**: empty strings, zero, MAX values where relevant

Do **not** add tests purely for coverage numbers. Every test should validate meaningful behavior.

## Running Tests

Before handoff, always run:

```bash
cargo test -p <tool-name>
```

For workspace-wide checks:

```bash
cargo test --workspace
```

## New-code quality gate

`scripts/rust_quality_gate.py` in this skill folder gates the lines a branch adds, diffing the
merge base against the working tree so uncommitted work is checked too. It wraps two tools, one
per question:

- `cargo llvm-cov` answers quantity: which added lines execute under tests. The script intersects
  its lcov output with the added lines and enforces a threshold, default 80% of new coverable
  lines.
- `cargo mutants --in-diff` answers quality: it mutates only the added code and fails when a
  mutant survives, meaning the code could be broken without any test noticing.

The threshold is a detection signal, and this file's standing rule holds: do not add tests purely
to move the number. A failing gate means "look at what is untested and decide", never "pad until
green".

### Install

The script is Python 3, standard library only. The two cargo tools install once per machine:

```bash
cargo +stable install cargo-llvm-cov --locked
cargo install --locked cargo-mutants
```

`--locked` pins each tool's dependency tree, not its version: a CI job rerunning the install still
fetches the current release. Add `--version X.Y.Z` where reproducibility matters.

### Running the gate

Run it from anywhere inside the target repo:

```bash
python <skill-set>/skills/rust/scripts/rust_quality_gate.py
```

The base ref defaults to `origin/HEAD`, then `main`, then `master`; `--base <ref>` overrides it.
`--skip-mutants` runs only the coverage gate, for quick iteration. `--cov-threshold <pct>` and the
repeatable `--exclude <glob>` adjust the coverage policy (test files and `tests/` paths are
excluded by default). `--lcov-file <path>` consumes a pre-generated lcov file instead of running
`cargo llvm-cov` itself; that is the escape hatch for projects whose coverage needs a different
producer invocation (feature flags, nextest, and the like).

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | both gates pass |
| 2 | coverage gate failed (when both gates fail, both are reported and 2 wins) |
| 3 | mutation gate failed |
| 64 | usage error |
| 70 | an underlying tool ran and failed: broken build, red baseline suite, diff mismatch |
| 78 | environment not ready: tool missing, not a git repo, base ref unresolvable |

Codes 2 and 3 mean the new code is undertested; 70 means the build or suite is broken. A CI
consumer should keep those two remediation paths separate.

### Runtime and caveats

- Mutation testing runs a build plus a test run per mutant: minutes, not seconds, even scoped to
  the diff. Iterate with `--skip-mutants`; run the full gate before handoff.
- cargo-mutants enforces a per-mutant timeout. The coverage phase has no equivalent, so a
  deadlocked test suite hangs the coverage run.
- A diff touching only test code produces zero mutants; the script reports that as informational.
- Doctests do not count as coverage: cargo-llvm-cov's `--doctests` flag is nightly-only and the
  gate does not pass it. Code exercised only by doc examples reads as uncovered.
- Untracked files are invisible to `git diff` and so to both gates. The preflight warning names
  them; commit them or `git add -N <file>` first.
- In a workspace where a lib crate is tested through another member's integration tests, set
  `test_workspace = true` in the target repo's `.cargo/mutants.toml`. By default each mutant runs
  only the tests of the package being mutated
  ([cargo-mutants workspaces](https://mutants.rs/workspaces.html)), so those cross-crate tests
  would otherwise never get the chance to catch a mutant.
- Child-process output streams to stderr raw and unsanitized, by design; only the script's own
  report on stdout strips control sequences from echoed source lines.
- On failure the temp directory (diff files, lcov output, mutants output) is retained and its
  path printed. Delete it freely once inspected; CI runners should clean these up between runs.

### Trust boundary

Running the gate builds and runs the target repo's code: build scripts, proc macros, tests, and
repo-local cargo config all execute on your machine. Point it only at a repo you would run
`cargo test` in; for untrusted code, use an isolated environment (the cargo-mutants
[cautions chapter](https://mutants.rs/cautions.html) covers why).

## Key Principles

- Keep `#[cfg(test)] mod tests` at the bottom of the file, after all production code
- Always `use super::*` to bring parent module items into test scope
- Prefer `unwrap()` in tests -- panics give clear failure messages
- Use `assert_eq!` for value comparisons (better error messages than `assert!`)
- Use `assert!(matches!(...))` for enum/pattern checks
- Name tests descriptively: `<function>_<scenario>_<expected_behavior>`
