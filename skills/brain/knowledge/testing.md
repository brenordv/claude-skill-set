# Testing Best Practices

These guidelines apply to all coding and game development skills regardless of language or framework. They define the quality bar for test code.

---

## 1. Testing Philosophy

- **Tests are first-class code**: Maintain them with the same standards as production code.
- **Test behavior, not implementation**: Tests should verify *what* the code does, not *how* it does it internally.
- **Tests enable refactoring**: Good tests give you confidence to change code without fear.
- **Test at the right level**: Unit tests for logic, integration tests for connections, E2E for critical flows.
- **Tests serve the intended behavior, not the reverse**: When a change deliberately alters behavior, the tests that asserted the old behavior are stale. Update or delete them; never revert the change or weaken the code to keep an obsolete test green. A test is not a veto over an intentional change (see `general-problem-solving.md` §3).

---

## 2. Test Structure: Arrange-Act-Assert (AAA)

Every test follows three phases:

1. **Arrange**: Set up the test data, dependencies, and preconditions.
2. **Act**: Execute the behavior being tested (one action per test).
3. **Assert**: Verify the expected outcome.

```
// Arrange
[set up inputs and dependencies]

// Act
[call the method/function under test]

// Assert
[verify the result matches expectations]
```

Keep each section clearly separated. One logical assertion per test (multiple `assert` calls for the same logical verification are fine).

---

## 3. What to Test

### Always Test

- **Happy path**: The normal, expected behavior.
- **Error conditions**: What happens when things go wrong (invalid input, failures).
- **Boundary values**: Edge cases at the limits (empty collections, zero, max values, off-by-one).

### Test Judiciously

- **Edge cases within reason**: Don't test extreme scenarios unless explicitly needed.
- **Integration points**: Where your code talks to external systems.
- **Complex business logic**: Where bugs would have the highest impact.

### Don't Test

- **Framework/library internals**: Trust that they work.
- **Simple getters/setters**: Unless they contain logic.
- **Private methods directly**: Test them through their public interface.

---

## 4. Test Quality

### Independence

- Tests must not depend on each other or share mutable state.
- Each test sets up its own preconditions and cleans up after itself.
- Tests should pass in any order and in isolation.

### Determinism

- No test should fail randomly (flaky tests erode trust).
- Mock time, random values, and external services.
- Avoid dependencies on system state (file system, network, environment).
- **Hard-coded calendar dates rot.** Arrangement data that means "recent", "last month", or
  "expired" derives from the current clock (offsets from now) or the test's fake clock, never a
  literal like `2024-01-15`: the literal ages, and the test quietly stops covering the scenario its
  name claims. Reserve a fixed date for when that exact value is the behavior under test (a
  boundary, a regression's input), extracted to a named constant that states the reason.

### Readability

- **Descriptive test names**: The name should explain what behavior is being verified and the expected outcome.
- **Minimal setup**: Only set up what the specific test needs.
- **Avoid logic in tests**: No conditionals, loops, or complex calculations in test code.
- **Use fixtures/helpers**: Extract common setup to reduce duplication without obscuring intent.
- **No explanatory comments in tests**: A test must be simple and clear enough that a reader figures out what is being tested from the name and the code alone. Comments narrating what the test does ("create a user with an expired token", "verify the discount was applied") are banned; if a test needs them, simplify the test instead. The only permitted comments are structural phase markers where the stack's convention uses them (e.g. `// Arrange` / `// Act` / `// Assert`).

### Speed

- Unit tests should be fast (milliseconds each).
- Isolate slow tests (I/O, network) into integration test suites.
- Fast feedback loop enables running tests frequently.

---

## 5. Test Naming

Tests should be named to clearly communicate:
- What is being tested (method/behavior)
- Under what conditions (scenario)
- What is expected (outcome)

Good patterns:
- `test_calculate_discount_applies_10_percent_for_premium_users`
- `CalculateDiscount_PremiumUser_Returns10PercentOff`
- `should return empty list when no items match filter`

Bad patterns:
- `test1`, `testMethod`, `testItWorks`

---

## 6. Mocking & Test Doubles

- **Mock external dependencies**: Database, HTTP, file system, third-party APIs.
- **Don't mock what you own**: Prefer testing through the real implementation for internal code.
- **Minimal mocking**: Only mock what's necessary for the test. Over-mocking makes tests brittle.
- **Verify interactions sparingly**: Prefer verifying outputs over verifying that specific methods were called.

---

## 7. Test Coverage

- **Aim for meaningful coverage**: 80%+ for critical business logic paths.
- **Coverage is a guide, not a goal**: 100% coverage with bad tests is worse than 80% with good tests.
- **Focus on paths with highest risk**: Complex logic, security-sensitive code, data integrity.
- **Don't test purely for coverage numbers**: Every test should verify meaningful behavior.

---

## 8. Parametrized / Data-Driven Tests

When multiple test cases share the same logic but differ in input/output:
- Use parametrized tests (pytest.mark.parametrize, [Theory], test.each, etc.).
- Group related test data logically.
- Avoid creating nearly-identical tests that differ only in data.

---

## 9. Test Organization

- **Mirror production structure**: Test files map to source files.
- **Separate test helpers**: Fixtures, factories, and builders in dedicated locations.
- **Group by behavior**: Tests for the same feature/method grouped in the same describe/class.
- **Run frequently**: Integrate into development workflow and CI/CD.

---

## 10. Integration & E2E Tests

- **Integration tests** verify components work together (database queries, API calls).
- **E2E tests** verify critical user journeys through the full stack.
- **Use realistic data**: But anonymized/synthetic, never production data.
- **Stable selectors**: Use semantic locators (role, label) over implementation details (CSS class, test ID).
- **Test the happy path and critical error paths**: Don't E2E-test every edge case.

---

## 11. Anti-Patterns

| Anti-Pattern | Problem | Better Approach |
|---|---|---|
| Testing implementation details | Tests break on refactoring | Test behavior/outputs |
| Shared mutable state between tests | Order-dependent failures | Independent test setup |
| Giant test methods | Hard to diagnose failures | One assertion per test |
| Copy-paste test code | Maintenance nightmare | Extract helpers/fixtures |
| Testing only the happy path | Bugs hide in error paths | Test errors and edges |
| Comments narrating the test | Signals the test is too complex to read | Simplify until name + code speak for themselves |
| Slow test suites | Developers skip running them | Isolate slow tests |
| No tests at all | Refactoring is terrifying | Start with critical paths |
| Reverting code to satisfy a stale test | Locks in behavior the change meant to replace | Update or delete the test to match the intended behavior |
