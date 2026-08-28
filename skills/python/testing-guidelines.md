# Python Testing Guidelines

Framework-specific testing patterns for Python applications. These complement the general testing principles in `brain/knowledge/testing.md`.

## Framework

- **pytest** as the test framework (not unittest directly)

## Test Layout

Mirror the source package structure under a top-level `tests/` directory; never dump every test file flat at the `tests/` root. A test for `src/myapp/services/order.py` lives at `tests/services/test_order.py`, and you create the `services/` folder to hold it. This holds when you scaffold the suite yourself: a fresh, empty `tests/` is exactly where files pile up at the root by default, so build the mirrored folders as you add each file.

- Keep tests outside the application code (the "src layout"), in a top-level `tests/` next to `src/`, so the suite can run against the installed package. pytest recommends this layout for new projects (see [Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)).
- pytest discovers `test_*.py` (or `*_test.py`) files; keep the `test_` prefix on files and functions.
- **Mirroring gotcha (`__init__.py`):** test folders need no `__init__.py` by default, with one exception, and it is the one mirroring creates: two test files sharing a basename in different folders (`tests/orders/test_service.py` and `tests/users/test_service.py`) collide under pytest's default import mode. Add an empty `__init__.py` to each such test folder so pytest imports them as `tests.orders.test_service` and `tests.users.test_service` instead of clashing on `test_service`.

## Test Naming Convention

```
test_<behavior>_<scenario>_<expected>
```

Examples:
- `test_calculate_total_with_discount_returns_reduced_price`
- `test_create_user_duplicate_email_raises_conflict_error`
- `test_parse_config_missing_file_returns_default`

## Fixtures

Use `@pytest.fixture` for test data and setup:

```python
@pytest.fixture
def sample_user():
    return User(name="Alice", email="alice@example.com", role="admin")


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
```

## Parametrized Tests

Use `@pytest.mark.parametrize` for data-driven testing:

```python
@pytest.mark.parametrize("input_value,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
    ("already-UPPER", "ALREADY-UPPER"),
])
def test_to_uppercase_various_inputs_returns_uppercased(input_value, expected):
    assert to_uppercase(input_value) == expected
```

## Mocking

Use `mocker` (pytest-mock) or `unittest.mock`:

```python
def test_fetch_user_calls_api_with_correct_id(mocker):
    mock_get = mocker.patch("myapp.client.requests.get")
    mock_get.return_value.json.return_value = {"id": 1, "name": "Alice"}

    result = fetch_user(user_id=1)

    mock_get.assert_called_once_with("https://api.example.com/users/1")
    assert result.name == "Alice"
```

## Integration Tests

Mark integration tests for selective execution:

```python
@pytest.mark.integration
def test_database_migration_applies_cleanly(db_session):
    # Test that runs against a real (test) database
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
```

## Coverage

- Use `pytest-cov` for coverage measurement
- Aim for **>80% coverage** for critical modules
- Run: `pytest --cov=src --cov-report=term-missing`
- Focus coverage on business logic, not boilerplate

## New-code quality gate

`scripts/python_quality_gate.py` in this skill folder gates the lines a branch adds, diffing the
merge base against the working tree so uncommitted work is checked too. It runs a file-size check
and two tool-backed gates:

- A **file-size phase** grades new and cap-crossing production files against the per-language tiers
  in `brain/knowledge/coding-general.md` §3 (Python: warn at 800 lines, fail at the 1,500 cap). It
  keeps test files warn-only, folds in untracked `.py` files as new, and needs only git and the
  filesystem, so it runs first and reports even where pytest is absent. New files and pre-existing
  files a change pushes to the cap fail; an already-oversized file only warns, with a message to
  route new code into a new module. See `brain/knowledge/coding-general.md` §3 for the tiers and
  the split-don't-refactor policy.
- pytest with pytest-cov (`--cov --cov-report=lcov:...`) answers quantity: which added lines
  execute under tests. The script intersects the lcov output with the added lines and enforces a
  threshold, default 80% of new coverable lines.
- Cosmic Ray, scoped to the changed lines with `cr-filter-git`, answers quality: it mutates only
  the added code and fails when a mutant survives, meaning the code could be broken without any
  test noticing.

The threshold is a detection signal, and the coverage rule above holds: do not add tests purely to
move the number. A failing gate means "look at what is untested and decide", never "pad until
green".

The two halves run at different times. While iterating and at handoff, run only the coverage half
(`--skip-mutants`). The mutation half is opt-in and refuses a dirty tree, and a commit is the
user's action alone: never commit, stage, or stash to satisfy the gate. Once the coverage half
passes, ask the user whether they want the mutation phase and, if so, to commit the changes
themselves; only then run the gate without `--skip-mutants`.

One layout note: the gate's own unit tests sit next to it in `scripts/`, not in a mirrored
`tests/` tree (Hard Rule 4). That is deliberate: skill folders are self-contained distribution
units, the convention the Rust gate set.

### Install

The script is Python 3, standard library only. The two tool packages install into the target
project's environment:

```bash
pip install pytest-cov cosmic-ray
```

Version floors: pytest-cov >= 4.0 and coverage.py >= 6.3 (where lcov output arrived), and
Python >= 3.9 for Cosmic Ray. Cosmic Ray's Windows support is unverified; on Windows expect to
run it under WSL or verify locally first.

### Running the gate

Run it from anywhere inside the target repo, with the project's own interpreter (the venv's), so
the coverage run and the mutants' test runs see the project's dependencies. `<skill-set>` is the
folder this skill set lives in, the one holding `skills/`:

```bash
python <skill-set>/skills/python/scripts/python_quality_gate.py
```

The base ref defaults to `origin/HEAD`, then `main`, then `master`; `--base <ref>` overrides it.
`--skip-mutants` runs only the coverage gate (the file-size phase always runs), for quick
iteration. `--cov-threshold <pct>` and the repeatable `--exclude <glob>` adjust the coverage policy
(`tests/` paths, `test_*.py`, `*_test.py`, and `conftest.py` are excluded by default); `--exclude`
also drops a file from the file-size gate, the escape hatch for a legitimately long generated file
(the gate's own `*_quality_gate.py` scripts are already size-exempt).
Coverage sources come from the target
repo's own coverage configuration: the gate runs bare `--cov`, the pytest-cov-documented route, so
a repo that needs narrowing sets its sources in `.coveragerc` or `pyproject.toml`. A repo whose
producer invocation differs entirely uses `--lcov-file <path>` instead. For the mutation phase,
`--module-path <path>` (default `src`) names the package Cosmic Ray mutates, `--test-command
<cmd>` (default: the launching interpreter with `-m pytest`) is what it runs per mutant, and
`--timeout <seconds>` (default 300) caps each mutant's test run so an infinite-loop mutant cannot
hang the gate.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | all gates pass |
| 2 | coverage gate failed |
| 3 | mutation gate failed |
| 4 | file-size gate failed (a new or cap-crossing production file hit the 1,500-line cap) |
| 64 | usage error |
| 70 | an underlying tool ran and failed: red baseline suite, failed pipeline step, unparseable rate |
| 78 | environment not ready: tool missing, not a git repo, dirty tree, module-path mismatch |

All phases run and report before the process exits; when several fail the precedence is 2
(coverage) > 3 (mutation) > 4 (file size). Codes 2, 3, and 4 mean the new code is undertested or
oversized; 70 means the build or suite is broken. A CI consumer should keep those remediation
paths separate.

### Runtime and caveats

- Mutation testing runs the test suite once per mutant: minutes, not seconds, even scoped to the
  diff. Iterate with `--skip-mutants`; the full gate waits for the user's opt-in and commit.
- The gate refuses to start the mutation phase on a dirty tree (exit 78): Cosmic Ray mutates
  source on disk during exec, so an interrupted run leaves a mutant indistinguishable from your
  uncommitted work. The clean tree comes from the user committing (the workflow above), or run
  `--skip-mutants`. After any interrupted mutation run, inspect `git diff` before trusting the
  working tree.
- Mutation scope is the resolved merge-base commit, passed to Cosmic Ray's git filter; the
  filter's own diff accepts any committish (verified against cosmic-ray 8.7.0 source), so upstream
  drift on the base branch cannot pull unrelated lines into scope.
- The verdict is the survival rate `cr-rate` prints, not its exit code: cosmic-ray 8.7.0 treats
  `--fail-over 0` as unset (a falsy-zero check in the tool), so the gate parses the printed rate
  and fails on anything above zero. Unparseable output is a tool failure, never a pass.
- Cosmic Ray only mutates files under `--module-path`, and its rate arithmetic scores an
  all-skipped session as zero survival. The gate refuses up front when none of the changed
  in-scope files lie under the module path (a false pass otherwise) and warns when only some do.
  This step does not work on Windows due to Cosmic Ray's lack of support on Windows. So we should 
  always skip this step when running on a Windows machine. 
- A changed `.py` file with no coverage record at all counts as fully uncovered rather than being
  dropped from the ratio: that shape usually means the suite never imports the module, or the
  coverage sources do not include it. 
- A deadlocked test suite hangs the coverage phase; only the mutation phase has the per-mutant
  timeout.
- Untracked files are invisible to `git diff` and so to both gates. The preflight warning names
  them; making them visible takes a git write (a commit, or `git add -N <file>`), which is the
  user's to run, so ask them first.
- Child-process output streams to stderr raw and unsanitized, by design; only the script's own
  report on stdout strips control sequences from echoed source lines.
- On failure the temp directory (lcov output, the generated Cosmic Ray config, the session
  database) is retained and its path printed. Delete it freely once inspected; CI runners should
  clean these up between runs.

### Trust boundary

Running the gate imports and runs the target repo's code: test collection, fixtures, and the
suite itself all execute on your machine, and the repo under test produces the very data the gate
judges it by. The gate's checks defend against careless code, not hostile code. Point it only at
a repo you would run `pytest` in; for untrusted code, use an isolated environment.

## Test Data

- Use realistic test data that resembles production values
- Avoid magic numbers/strings without explanation
- Use factories or fixtures for complex object creation

## Key Principles

- Test behavior, not implementation details
- Each test should test one thing and have a clear assertion
- Keep tests independent -- no shared mutable state between tests
- Use `tmp_path` fixture for file system tests
- Use `monkeypatch` for environment variables and configuration
