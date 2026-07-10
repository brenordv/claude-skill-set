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

### 1. Code Style & Standards

**PEP 8 Compliance:**
- 4 spaces for indentation (never tabs)
- Maximum line length: 88 characters (Black formatter standard)
- Two blank lines between top-level definitions
- Imports: standard library, third-party, local (separated by blank lines)

**Naming Conventions:**
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `UPPER_CASE` for constants

**Type Hints:**
```python
from typing import Dict, List, Optional, Union

def process_data(
    items: List[str],
    config: Dict[str, int],
    timeout: Optional[float] = None
) -> Dict[str, Union[int, str]]:
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

Use **pytest** with the Arrange-Act-Assert structure. Test happy paths, error conditions, and boundary values; aim for >80% coverage on critical modules. See `testing-guidelines.md` in this skill folder for fixtures, parametrization, mocking, and coverage detail.

### 5. Quality Validation & Completion Checklist

Run these checks before marking work complete:

- [ ] Code formatted: `black .` and `isort .`
- [ ] Type checking clean: `mypy src/`
- [ ] No linting errors: `flake8 src/` and `pylint src/`
- [ ] No security warnings: `bandit -r src/`
- [ ] Tests pass with coverage (>=80% for critical paths): `pytest --cov=src --cov-report=term-missing`
- [ ] Documentation complete (docstrings)
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
