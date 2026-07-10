---
name: rust
description: >-
  Write production-quality Rust code following industry best practices and
  idiomatic patterns. Use for any Rust coding task including applications,
  libraries, refactoring, debugging, or code review.
---

# Rust

## Instructions

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the language-specific guidance below.
> **Language-Specific Testing**: See `testing-guidelines.md` in this skill folder for framework-specific testing patterns.

### 1. Design Principles

**Rust-Specific:**
- Prefer borrowing over cloning; pass `&str` not `&String`, `&Path` not `&PathBuf`, `&[T]` not `&Vec<T>`
- Use enums, newtypes, and the type system to make illegal states unrepresentable
- Parse raw input into well-typed structures at the boundary, then pass typed data inward
- Follow the repo's conventions over personal preference (see `CONTRIBUTING.md`)

**Models & Project Setup:**
- `#[derive(Debug, Clone)]` on config structs; add `Copy`, `PartialEq`, `Eq` where appropriate
- Enums for discrete modes/states; `Option<T>` for optional fields
- New crates: use the current stable `edition` (e.g., `"2021"`); set `authors` and `repository` to match the project's conventions; add the crate to the root `Cargo.toml` workspace `members` list (if using workspaces)

### 2. Error Handling (anyhow required)

**Use `anyhow` as the sole error-handling crate.** Do not introduce `thiserror`, `eyre`, or other error libraries.

- All fallible functions return `anyhow::Result<T>`
- Attach context at every level with `.context("message")` or `.with_context(|| format!(...))`
- Propagate errors with `?`; never use `unwrap()` or `expect()` outside test code
- Use `anyhow::anyhow!("message")` or `anyhow::bail!("message")` for ad-hoc errors
- At the entrypoint: print the error to `stderr` with `eprintln!`, log with `error!`, and exit non-zero (if the workspace defines a shared error-exit helper, use it)
- For tools needing distinct exit codes, define a custom `AppError { message, exit_code }` struct (follow the workspace's existing pattern if one exists)

### 3. Code Style

- Use the repo's `rustfmt` and `clippy` defaults; never change them; fix all warnings
- `snake_case` for functions/variables/modules/files; `PascalCase` for types; `UPPER_SNAKE_CASE` for constants
- Group imports: `crate::`, external crates, `std::`; no glob imports in production code
- Doc comments (`///`) on all public items with `# Errors` / `# Panics` sections where applicable
- Comments explain "why", not "what"; no commented-out code
- Functions ~50 lines max; extract helpers when they grow
- `match` over `if let` chains for multiple variants; guard clauses for early returns

### 4. Performance

- Use `BufReader`/`BufWriter` for file I/O; source buffer sizes from the workspace's shared constants if it defines them
- Pre-allocate `Vec` capacity when size is known; use `Cow<'_, str>` to avoid unnecessary allocations
- Use `once_cell::sync::Lazy` (or `std::sync::LazyLock`) for expensive one-time inits like compiled regexes
- Profile before optimizing; add parallelism only as the need arises

### 5. Testing

- Unit tests: `#[cfg(test)] mod tests` at the bottom of each file; `use super::*`
- File-based tests: `tempfile::tempdir()` for temporary directories
- Follow Arrange-Act-Assert; use helper functions to build test fixtures
- Use `assert!(matches!(...))` for enum variant checks
- Test happy paths, error conditions, and meaningful boundary values
- Add tests where it makes sense; don't add them purely for coverage numbers

### 6. Forbidden

- `unsafe` code unless explicitly approved
- `unwrap()` / `expect()` in non-test code
- Error libraries other than `anyhow` (no `thiserror`, `eyre`, etc.)
- Changing `edition`, `rustfmt`, or `clippy` settings

### 7. Quality Validation

Run before completion:
```bash
cargo build -p <crate>
cargo clippy -p <crate> -- -D warnings
cargo test -p <crate>
cargo fmt -p <crate> -- --check
```

## When to Use This Skill

- Writing new Rust CLI tools, libraries, or crates
- Adding functionality to existing tools or shared crates
- Refactoring, debugging, or reviewing Rust code
- Any Rust task where production-quality, idiomatic code is expected
