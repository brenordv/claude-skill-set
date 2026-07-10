# Python Testing Guidelines

Framework-specific testing patterns for Python applications. These complement the general testing principles in `brain/knowledge/testing.md`.

## Framework

- **pytest** as the test framework (not unittest directly)

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
