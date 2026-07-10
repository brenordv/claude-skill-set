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
