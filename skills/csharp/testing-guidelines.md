# C# Testing Guidelines

Framework-specific testing patterns for C#/.NET applications. These complement the general testing principles in `brain/knowledge/testing.md`.

## Framework & Assertions

- **xUnit** as the test framework
- Use native `Assert` methods (Assert.Equal, Assert.True, Assert.Throws, etc.)

## ⛔ Banned Libraries: Moq & FluentAssertions

**Never use Moq or FluentAssertions. No exceptions, ever.**

- If the repo already uses them, that changes nothing: do not add a single new usage. Write new tests with native xUnit `Assert` and hand-rolled test doubles. Leave existing tests alone unless asked to migrate them.
- Instead of Moq, write a small fake/stub class implementing the interface (see the `BuildSut` example below). Fakes are a few lines, debuggable, and don't hide behavior behind setup expressions.
- Instead of FluentAssertions, use the native `Assert` equivalent (`result.Should().Be(x)` → `Assert.Equal(x, result)`).

## Comments in Tests

Every test body carries all three AAA markers (`// Arrange`, `// Act`, `// Assert`) and no other comment. The markers are required, not optional: a test written with none of them is as wrong as one with an explanatory comment. They are also the **only** comments allowed. Never add comments explaining what the test is doing or why: the test name states the scenario and expectation, and the test body must be simple enough to read without narration. If a test feels like it needs an explanatory comment, that's a signal to simplify the test, not to comment it.

## Test Structure

### AAA Pattern with Capitalized Comments

```csharp
[Fact]
public void CalculateTotal_WithDiscount_ReturnsReducedPrice()
{
    // Arrange
    var order = BuildSut();
    order.AddItem(new OrderItem("Widget", 100m));

    // Act
    var total = order.CalculateTotal(discountPercent: 10);

    // Assert
    Assert.Equal(90m, total);
}
```

All three markers appear in every test, capitalized, with a space between the comment slashes and the word (`// Arrange`, `// Act`, `// Assert`). A test that omits them is not following this pattern, regardless of how clean the body looks.

### Exception Assertions

The deferred-action local is `var`, never an explicit delegate type (Hard Rule 13). The compiler
infers the lambda's natural delegate type (C# 10+), so `Func<Task> act = ...` and `Action act = ...`
spell out what `var` already carries, and repos full of explicit types don't change that for new code:

```csharp
[Fact]
public async Task UpdateDocument_WithArchivedDocument_ThrowsDocumentArchivedException()
{
    // Arrange
    var sut = BuildSut();
    var document = MockDataGenerators.ArchivedDocument();

    // Act
    var act = () => sut.UpdateDocumentAsync(document, CancellationToken.None);

    // Assert
    await Assert.ThrowsAsync<DocumentArchivedException>(act);
}
```

### Test Naming Convention

```
{Method}_{Action}_{ExpectedResult}
```

Examples:
- `GetUser_WithValidId_ReturnsUser`
- `CreateOrder_WithEmptyCart_ThrowsInvalidOperationException`
- `CalculateShipping_InternationalAddress_AppliesInternationalRate`

### Test File Naming

- Same as the tested file + `Tests.cs`
- Example: `OrderService.cs` -> `OrderServiceTests.cs`

## Data-Driven Tests

### [Theory] with TheoryData<T>

```csharp
[Theory]
[MemberData(nameof(TheoryDataGenerator.ValidEmailAddresses), MemberType = typeof(TheoryDataGenerator))]
public void Validate_ValidEmail_ReturnsTrue(string email)
{
    // Arrange
    var validator = BuildSut();

    // Act
    var result = validator.Validate(email);

    // Assert
    Assert.True(result);
}
```

### TheoryDataGenerator Class

```csharp
public static class TheoryDataGenerator
{
    public static TheoryData<string> ValidEmailAddresses => new()
    {
        "user@example.com",
        "first.last@domain.org",
        "user+tag@example.co.uk",
    };
}
```

- If no `TheoryDataGenerator` or `MockDataGenerators` class exists in the test project, place generators under the `#region Test Helpers` region at the end of the test file.

## Realistic Test Data

- Use **Faker** (Bogus library) in `MockDataGenerators` for generating realistic test data
- Hardcoded test values used more than once should be extracted to a `const` with a meaningful name

```csharp
private const string ValidCustomerEmail = "testcustomer@example.com";
private const decimal StandardShippingRate = 5.99m;
```

### Dates & Times

Test dates derive from the clock, relative to now (Hard Rule 14). A hard-coded calendar date
changes scenario as real time passes: what was "issued last month" when the test was written is
"issued years ago" later, and the test quietly stops covering what its name claims.

```csharp
// Good: stays "30 days old" no matter when the suite runs
var issuedAt = DateTime.UtcNow.AddDays(-30);

// Bad: rots; the scenario this exercises drifts further into the past every day
var issuedAt = new DateTime(2024, 1, 15);
```

When the code under test reads the clock itself, inject the time (`TimeProvider` or the repo's
clock abstraction) and fake it in the test; asserting against the real `DateTime.UtcNow` from both
sides is a race. A fixed literal date is right only when that exact value is the behavior under
test (a leap-day boundary, the precise input from a regression); extract it to a `static readonly`
field whose name states the reason:

```csharp
private static readonly DateTime LeapDayBoundary = new(2024, 2, 29);
```

## Test Helpers

Place helper methods, fakes, and data generators at the bottom of the test file within a region. Dependencies are satisfied with hand-rolled fakes implementing the interfaces (never Moq):

```csharp
#region Test Helpers

private static OrderService BuildSut(IOrderRepository repository = null)
{
    return new OrderService(
        repository ?? new FakeOrderRepository(),
        NullLogger<OrderService>.Instance);
}

private sealed class FakeOrderRepository : IOrderRepository
{
    public List<Order> SavedOrders { get; } = new();

    public Task SaveAsync(Order order, CancellationToken cancellationToken)
    {
        SavedOrders.Add(order);
        return Task.CompletedTask;
    }
}

#endregion
```

Fakes stay minimal: implement only what the tests exercise, expose captured state through simple properties, and let the test assert on that state with native `Assert`. For `ILogger<T>`, use `NullLogger<T>.Instance` unless log output is the behavior under test.

## Project Structure

- Mirror the production folder structure in `*.Tests` projects; never flatten every test file into the project root (Hard Rule 11).
- Example: `src/MyApp.Domain/Services/OrderService.cs` -> `tests/MyApp.Domain.Tests/Services/OrderServiceTests.cs`
- This holds when you scaffold the test project yourself. An empty project has no folders to copy, which is exactly when files end up at the root by default; create the mirrored folders (`Services/`, and so on) as you add each test file instead.

## Coverage & Quality

- Target **90%+** code coverage (but consider ROI -- don't test trivial getters/setters)
- Always run `dotnet test` before handoff to verify all tests pass
- Every new feature or bug fix must include corresponding tests
