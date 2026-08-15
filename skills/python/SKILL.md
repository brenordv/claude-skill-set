---
name: python
description: >-
  Write production-quality Python code following PEP 8, type safety, and
  comprehensive testing standards. Use for any Python coding task including
  new features, refactoring, debugging, or building complete applications.
---

# Python

## Instructions

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the language-specific guidance below.
> **Language-Specific Testing**: See `testing-guidelines.md` in this skill folder for framework-specific testing patterns.

### ⛔ Hard Rules: Non-Negotiable

These bind every line of Python you add or modify. They are the ONE exception to "match the
repository's conventions": when the repo itself violates one of them, the rule still wins for the
code you write. Leave existing violations in untouched code alone (never mass-refactor), but nothing
new may break these. Softer conflicts between repo patterns and this skill go to the user per
`brain/knowledge/coding-general.md` §2, "When the repo and the guidelines disagree". Re-read this
list before writing code, and walk it again at handoff (§5).

1. **The toolchain is ruff, ruff format, and mypy, and all of it runs green before handoff.**
   `ruff check`, `ruff format --check`, `mypy`, and `pytest` clean on the code you touched, even in
   a repo configured for black/isort/flake8/pylint (run those too if the repo's CI does; they don't
   replace this gate). Never silence a finding to get there: a `# noqa` or `# type: ignore` without
   a specific rule code and a real reason is a violation, not a fix.
2. **Type hints on every function signature you write**, parameters and return type, public or
   private, in modern syntax: `list[str]`, `dict[str, int]`, `X | None`. Never import `List`,
   `Dict`, `Optional`, or `Union` from `typing` for new code unless the project pins a Python
   version that still needs them (below 3.10).
3. **Docstrings on every public module, class, and function** (Google or NumPy style, matching the
   repo's), with `Args:`, `Returns:`, and `Raises:` where they apply.
4. **Test files mirror the source package layout under `tests/`; never flatten them to the root.**
   A test for `src/app/services/orders.py` lives at `tests/services/test_orders.py`, and you create
   the folders as you add each file. Scaffolding the suite yourself is not an exception: an empty
   `tests/` directory is exactly where files end up dumped at the root.
5. **Pickle-format model and data files are untrusted code, not data.** `torch.load`,
   `joblib.load`, and fairseq-style checkpoints execute arbitrary code at load time: load only from
   trusted sources, prefer safetensors, and pass `weights_only=True` where the call supports it.

### 1. Code Style & Standards

**PEP 8 Compliance:**
- 4 spaces for indentation (never tabs)
- Maximum line length: 88 characters (the ruff format default)
- Two blank lines between top-level definitions
- Imports: standard library, third-party, local (separated by blank lines; `ruff check` enforces the ordering via its isort rules)

**Naming Conventions:**
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `UPPER_CASE` for constants

**Type Hints** (modern syntax; Hard Rule 2):
```python
def process_data(
    items: list[str],
    config: dict[str, int],
    timeout: float | None = None,
) -> dict[str, int | str]:
    """Process items according to configuration."""
    ...
```

**Documentation:**
- Use Google or NumPy style docstrings
- Document all public APIs (classes, functions, modules)
- Include: purpose, parameters (`Args:`), return values (`Returns:`), exceptions (`Raises:`), and an example where useful

### 2. Implementation Guidelines

**Error Handling:**
```python
# Use specific exceptions
raise ValueError(f"Invalid user_id: {user_id}")

# Provide context in error messages
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed for user {user_id}: {e}")
    raise
```

**Resource Management:**
```python
# Use context managers (built-in, or @contextlib.contextmanager for custom resources)
with open(file_path) as f:
    data = f.read()
```

**Common Utilities:**
If the project has shared utility libraries (retry, logging, caching helpers), prefer them over reimplementing common patterns.

**ML model files:**
Weight files in pickle-based formats (`torch.load`, `joblib.load`, fairseq checkpoints) execute
arbitrary code at load time. Treat them as untrusted code, not data: load only from trusted sources,
prefer safetensors, and pass `weights_only=True` to `torch.load` where the call supports it.

### 3. Performance

**Caching:**
```python
from functools import cache, lru_cache

@cache  # For functions with hashable arguments
def fibonacci(n: int) -> int:
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

@lru_cache(maxsize=128)  # For size-limited cache
def expensive_computation(param: str) -> dict:
    ...
```

**Efficient Data Structures:**
- Use generators for large datasets: `(x for x in range(1000000))`
- Choose appropriate collections: `set` for membership, `deque` for queues
- Use `collections.defaultdict` and `collections.Counter` where appropriate

**Profiling Critical Code:**
- Profile with `cProfile` + `pstats` (sort by `'cumulative'`) before optimizing.

### 4. Testing

Use **pytest** with the Arrange-Act-Assert structure. Test happy paths, error conditions, and boundary values; aim for >80% coverage on critical modules. Test files mirror the source package layout under a top-level `tests/` directory and are never dumped flat at the `tests/` root, even in a suite you created yourself. See `testing-guidelines.md` in this skill folder for the test layout, fixtures, parametrization, mocking, and coverage detail.

### 5. Quality Validation & Completion Checklist

Run these checks before marking work complete:

- [ ] **Walk the ⛔ Hard Rules block at the top item by item against your diff.** These are the rules that regress; verify them by looking, not by assuming.
- [ ] No lint errors: `ruff check .` (ruff carries the flake8, isort, pylint-style, and bandit-style rule sets)
- [ ] Formatting clean: `ruff format --check .` (run `ruff format .` to fix)
- [ ] Type checking clean: `mypy src/`
- [ ] Tests pass with coverage (>=80% for critical paths): `pytest --cov=src --cov-report=term-missing`
- [ ] Test files mirror the source package layout under `tests/`, not dumped flat at the root (Hard Rule 4)
- [ ] Documentation complete (docstrings on every public API; Hard Rule 3)
- [ ] Performance profiled if applicable
- [ ] Code reviewed (use `code-review` skill)
- [ ] Summarize the changes to the user, alongside any problems and caveats you can see with the new code.

## When to Use This Skill

- Writing new Python modules, classes, or functions
- Refactoring existing Python code
- Debugging Python applications
- Setting up Python project structure
- Creating API endpoints, CLI tools, or python packages
- Building data processing pipelines
- Implementing algorithms or business logic

## Related Skills

- `code-review`: For reviewing the current diff after implementation
- `branch-review`: For reviewing all changes in the branch before merging
