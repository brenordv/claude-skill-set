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

### ⛔ Hard Rules: Non-Negotiable

These bind every line of Rust you add or modify. They are the ONE exception to "follow the repo's
conventions": when the repo itself violates one of them, the rule still wins for the code you write.
Leave existing violations in untouched code alone (never mass-refactor), but nothing new may break
these. Softer conflicts between repo patterns and this skill go to the user per
`brain/knowledge/coding-general.md` §2, "When the repo and the guidelines disagree". Re-read this
list before writing code, and walk it again at handoff (§8).

1. **`anyhow` for binaries and applications, `thiserror` for library crates, nothing else.**
   Application code returns `anyhow::Result<T>` with `.context(...)` attached at every level. A
   library crate consumed by others exposes typed errors via `thiserror` instead, because `anyhow`
   erases the type callers need to match on; the consuming binary converts at its boundary with `?`
   and `.context(...)`. No `eyre`, no hand-rolled error enums where `thiserror` fits, and never
   both patterns mixed inside one crate.
2. **No `unwrap()` or `expect()` outside test code, even in a repo sprinkled with them.** Errors
   propagate with `?`. A case you believe impossible still gets handled explicitly, with the
   reasoning stated where it's handled, never panicked through.
3. **`tracing` is the logging crate.** `tracing` + `tracing-subscriber` (subscriber initialized at
   the binary entry point only), never `log`, `env_logger`, or `println!`/`eprintln!` diagnostics
   in library code. Events carry structured fields (`info!(user_id = %id, "queued transfer")`),
   not values interpolated into the message string, and async or hot-path fns that deserve span
   context get `#[instrument]`.
4. **The four gates run clean before handoff, warnings as errors:** `cargo fmt --all -- --check`,
   `cargo clippy --all-targets --all-features -- -D warnings`, `cargo build`, `cargo test`. Never
   silence a lint to get there: an `#[allow(...)]` without a stated, site-specific reason is a
   violation, not a fix.
5. **File size: split new code into a new module; never mass-refactor an existing file for size.** A
   `.rs` file you create, or a pre-existing one your change grows across 1,500 lines (the hard cap;
   the warn tier starts at 700), goes into a new cohesive module instead of sailing past the cap. The
   per-language tier table is in `brain/knowledge/coding-general.md` §3 (File size). This binds your
   code only: a file already over the cap stays untouched for size; route your addition into a new
   module and name the oversized file in the handoff. The count is production lines: the trailing
   `#[cfg(test)] mod tests` block is subtracted, so co-located unit tests never push a file over a
   tier, and test-only files (`tests/`, `*_tests.rs`) are warn-only. The new-code quality gate (§8)
   enforces the cap.

### 1. Design Principles

**Rust-Specific:**
- Prefer borrowing over cloning; pass `&str` not `&String`, `&Path` not `&PathBuf`, `&[T]` not `&Vec<T>`
- Use enums, newtypes, and the type system to make illegal states unrepresentable
- Parse raw input into well-typed structures at the boundary, then pass typed data inward
- Follow the repo's conventions over personal preference (see `CONTRIBUTING.md`), **except where a
  ⛔ Hard Rule above says otherwise; Hard Rules beat repo conventions.** A softer conflict between
  a repo pattern and this skill's guidance goes to the user, not to whichever side you prefer

**Models & Project Setup:**
- `#[derive(Debug, Clone)]` on config structs; add `Copy`, `PartialEq`, `Eq` where appropriate
- Enums for discrete modes/states; `Option<T>` for optional fields
- New crates: use `edition = "2021"` (the standing default for these projects for now); set `authors` and `repository` to match the project's conventions; add the crate to the root `Cargo.toml` workspace `members` list (if using workspaces)
- Pin the lint policy in the repo with a `[workspace.lints]` (or per-crate `[lints]`) table in `Cargo.toml` and `lints.workspace = true` in member crates, so the clippy bar travels with the project instead of living in anyone's head
- When you are the one creating that lint-policy table (not when a crate merely joins an existing workspace), add `[workspace.lints.clippy] too_many_lines = "warn"`. The lint is allow-by-default (pedantic), and under Hard Rule 4's `-D warnings` a `"warn"` entry becomes a hard error, so a function past clippy's `too-many-lines-threshold` (kept at the default 100, consistent with the ~50-line function guidance in §4) stops the gate. A function that is legitimately long escapes with `#[allow(clippy::too_many_lines)]` plus a one-line site-specific reason, the same sanctioned-exception shape as Hard Rule 4. If the same table also enables a lint group (for example `pedantic = "warn"`), give the group `priority = -1` so the individual `too_many_lines` level still wins. This is a per-function guard; whole-file size is enforced by Hard Rule 5 and the new-code gate, since no file-level clippy lint exists.

### 2. Error Handling (anyhow for binaries, thiserror for libraries)

**Applications use `anyhow`; library crates consumed by others use `thiserror`** (Hard Rule 1). No
other error library, and never both patterns mixed inside one crate.

In application/binary code:

- All fallible functions return `anyhow::Result<T>`
- Attach context at every level with `.context("message")` or `.with_context(|| format!(...))`
- Propagate errors with `?`; never use `unwrap()` or `expect()` outside test code (Hard Rule 2)
- Use `anyhow::anyhow!("message")` or `anyhow::bail!("message")` for ad-hoc errors
- At the entrypoint: print the error to `stderr` with `eprintln!`, log with `error!`, and exit non-zero (if the workspace defines a shared error-exit helper, use it)
- For tools needing distinct exit codes, define a custom `AppError { message, exit_code }` struct (follow the workspace's existing pattern if one exists)

In a library crate:

- Define one error enum per module or domain with `#[derive(thiserror::Error, Debug)]`, a `#[error("...")]` message per variant, and `#[from]` where a source error maps one-to-one
- Return `Result<T, YourError>` from the public API; let binaries wrap it into `anyhow` at their boundary with `?` and `.context(...)`
- Keep variants meaningful to the caller (what they can match on and react to), not one variant per internal call site

### 3. Logging (tracing required)

`tracing` is the logging crate; never `log`, `env_logger`, or `println!` diagnostics (Hard Rule 3).

- Initialize `tracing-subscriber` once, at the binary entry point; libraries only emit events, never install a subscriber
- Structured fields over interpolation: `info!(user_id = %id, order_count, "queued transfers")`, never `info!("queued {count} transfers for {id}")`; fields survive as queryable data, interpolated strings don't
- `#[instrument]` on async fns and hot paths that deserve span context (skip trivial helpers); `#[instrument(skip(large_arg))]` to keep noisy arguments out
- Levels: `error!` for failures someone must look at, `warn!` for degraded-but-continuing, `info!` for meaningful flow milestones, `debug!`/`trace!` for diagnosis; don't narrate every step at `info!`
- Log at the site that has the context; don't double-log an error at every level of the propagation chain (`.context(...)` already carries the story upward)

### 4. Code Style

- Use the repo's `rustfmt` and `clippy` defaults; never change an existing project's settings; fix all warnings. Setting the lint policy on a new crate or workspace you are creating is the one sanctioned exception (§1), including the `too_many_lines` pin
- `snake_case` for functions/variables/modules/files; `PascalCase` for types; `UPPER_SNAKE_CASE` for constants
- Group imports: `crate::`, external crates, `std::`; no glob imports in production code
- Doc comments (`///`) on all public items with `# Errors` / `# Panics` sections where applicable
- Comments explain "why", not "what"; the code's why, never the edit's (no comments narrating the
  fix, the request, or the old behavior; `brain/knowledge/coding-general.md` ⛔ Hard Rule 3); no
  commented-out code
- Functions ~50 lines max; extract helpers when they grow
- `match` over `if let` chains for multiple variants; guard clauses for early returns

### 5. Performance

- Use `BufReader`/`BufWriter` for file I/O; source buffer sizes from the workspace's shared constants if it defines them
- Pre-allocate `Vec` capacity when size is known; use `Cow<'_, str>` to avoid unnecessary allocations
- Use `std::sync::LazyLock` (stable since Rust 1.80) for expensive one-time inits like compiled regexes; reach for `once_cell` only in a repo pinned below 1.80
- Profile before optimizing; add parallelism only as the need arises

### 6. Testing

- Unit tests: `#[cfg(test)] mod tests` at the bottom of each file; `use super::*`
- When a co-located `#[cfg(test)] mod tests` grows large, move it into a sibling `tests.rs` submodule file (`#[cfg(test)] mod tests;` in the source file, the tests in the adjacent `tests.rs`) rather than letting it inflate the source. Private items still reach it through the module boundary. The size gate already subtracts the trailing test module from the production count, so co-located tests never fail the gate; this split is about keeping the source file readable, and it is distinct from the integration-test `tests/` dir
- Integration tests: separate crates in a top-level `tests/` dir, exercising the public API; shared helpers go in `tests/common/mod.rs`. Do not mirror `src/`'s folder layout into a separate test tree (that is a C#/pytest convention, not Rust's). See `testing-guidelines.md`.
- File-based tests: `tempfile::tempdir()` for temporary directories
- Follow Arrange-Act-Assert; use helper functions to build test fixtures
- Use `assert!(matches!(...))` for enum variant checks
- Test happy paths, error conditions, and meaningful boundary values
- Add tests where it makes sense; don't add them purely for coverage numbers
- New-code quality gate: `scripts/rust_quality_gate.py --skip-mutants` checks diff coverage before handoff; the mutation half is opt-in and runs only after the user has committed the work themselves and asked for it; see `testing-guidelines.md` §"New-code quality gate"

### 7. Forbidden

- `unsafe` code unless explicitly approved
- `unwrap()` / `expect()` in non-test code (Hard Rule 2)
- Error libraries other than `anyhow` in binaries and `thiserror` in libraries; no `eyre` and friends (Hard Rule 1)
- `log`, `env_logger`, or `println!`/`eprintln!` diagnostics where `tracing` belongs (Hard Rule 3; the entrypoint's final error print is the exception)
- Changing `edition`, `rustfmt`, or `clippy` settings in an existing project (setting the lint policy when you create a new crate or workspace is the one sanctioned exception, §1)

### 8. Quality Validation

Before completion:

1. **Walk the ⛔ Hard Rules block at the top item by item against your diff**: error crates match the
   crate kind, no new `unwrap()`/`expect()`, events use structured fields. Verify by looking, not by
   assuming.
2. Run the four gates; all clean, warnings as errors:
```bash
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo build
cargo test
```
In a large workspace, scope with `-p <crate>` while iterating, but the full unscoped run happens at
least once before handoff.

3. Run the coverage half of the new-code quality gate where the toolchain is available
   (`scripts/rust_quality_gate.py --skip-mutants`; see §6 and `testing-guidelines.md`). Its file-size
   check (Hard Rule 5) exits 4 when a new or cap-crossing production file hits the 1,500-line cap; the
   fix is to split the new code into a new module, never to mass-refactor an existing oversized one.
   The size phase runs on git and the filesystem alone, so it reports even where cargo is absent, and
   it subtracts the trailing `#[cfg(test)]` block from the count.

## When to Use This Skill

- Writing new Rust CLI tools, libraries, or crates
- Adding functionality to existing tools or shared crates
- Refactoring, debugging, or reviewing Rust code
- Any Rust task where production-quality, idiomatic code is expected
