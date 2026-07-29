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

## Key Principles

- Keep `#[cfg(test)] mod tests` at the bottom of the file, after all production code
- Always `use super::*` to bring parent module items into test scope
- Prefer `unwrap()` in tests -- panics give clear failure messages
- Use `assert_eq!` for value comparisons (better error messages than `assert!`)
- Use `assert!(matches!(...))` for enum/pattern checks
- Name tests descriptively: `<function>_<scenario>_<expected_behavior>`
