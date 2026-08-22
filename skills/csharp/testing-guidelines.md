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

## New-code quality gate

`scripts/csharp_quality_gate.py` in this skill folder gates the lines a branch adds, diffing the
merge base against the working tree so uncommitted work is checked too. It wraps two tools, one
per question:

- `dotnet test` with the coverlet collector (`--collect:"XPlat Code Coverage;Format=lcov"`)
  answers quantity: which added lines execute under tests. The script intersects the lcov output
  with the added lines and enforces a threshold, default 90% of new coverable lines.
- Stryker.NET (`dotnet stryker --since:<merge-base>`) answers quality: it mutates only the changed
  code and fails when the scoped mutation score drops below 100, meaning the code could be broken
  without any test noticing.

The threshold is a detection signal, and this file's standing rule holds: do not add tests purely
to move the number. A failing gate means "look at what is untested and decide", never "pad until
green".

The two halves run at different times. While iterating and at handoff, run only the coverage half
(`--skip-mutants`). The mutation half is opt-in and wants committed work, and a commit is the
user's action alone: never commit, stage, or stash to satisfy the gate. Once the coverage half
passes, ask the user whether they want the mutation phase and, if so, to commit the changes
themselves; only then run the gate without `--skip-mutants`.

### Install

The script is Python 3, standard library only. The coverlet collector is already on every test
project per SKILL.md section 15 (`coverlet.collector` plus `Microsoft.NET.Test.Sdk`), so only
Stryker installs once per machine:

```bash
dotnet tool install -g dotnet-stryker
```

A repo-local install (`dotnet new tool-manifest` then `dotnet tool install dotnet-stryker`) works
too; the gate runs it as `dotnet stryker` either way. Stryker itself needs the .NET 10 runtime or
newer, whatever the target app targets.

### Running the gate

Run it from anywhere inside the target repo:

```bash
python <skill-set>/skills/csharp/scripts/csharp_quality_gate.py
```

The base ref defaults to `origin/HEAD`, then `main`, then `master`; `--base <ref>` overrides it.
`--skip-mutants` runs only the coverage gate, for quick iteration. `--cov-threshold <pct>` and the
repeatable `--exclude <glob>` adjust the coverage policy (test/tests/`*.Tests` path segments and
`*Tests.cs` / `*.Designer.cs` basenames are excluded by default, case-insensitively).
`--test-target <path>` is handed to `dotnet test` and defaults to `.`, which requires a project or
solution file at the repo root; point it at your solution or test project otherwise.
`--lcov-file <path>` consumes a pre-generated lcov file instead of running `dotnet test`.
`--stryker-dir <path>` is the directory the gate runs `dotnet stryker` from; Stryker requires the
test project directory. `--stryker-solution <path>` switches to full-solution mutation scope
instead: the gate runs Stryker from the solution file's directory with `--solution`, and the flag
cannot be combined with `--stryker-dir`.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | both gates pass |
| 2 | coverage gate failed (when both gates fail, both are reported and 2 wins) |
| 3 | mutation gate failed |
| 64 | usage error |
| 70 | an underlying tool ran and failed: broken build, failing test run, no completed report |
| 78 | environment not ready: tool missing, not a git repo, base ref unresolvable |

Codes 2 and 3 mean the new code is undertested; 70 means the build or suite is broken. A CI
consumer should keep those two remediation paths separate.

### Runtime and caveats

- Mutation testing runs a build plus a test run per mutant: minutes, not seconds, even scoped with
  `--since`. Iterate with `--skip-mutants`; the full gate waits for the user's opt-in and commit.
- The gate assumes the VSTest runner, the current `dotnet test` default; the coverlet collector is
  a VSTest data collector, so a repo switched to Microsoft.Testing.Platform via `global.json`
  needs the `--lcov-file` escape hatch.
- The collector writes `coverage.info` into a per-run subfolder of the results directory with
  absolute source paths; the gate finds it by lcov grammar, not by name, and normalizes the paths.
- A changed `.cs` file with no coverage record at all counts as fully uncovered rather than being
  dropped from the ratio: in .NET that shape usually means no test project references the file's
  project, so the collector never saw it. The one carve-out is files whose type declarations are
  all interfaces, enums, or delegates; they compile to no method bodies, emit no coverage record,
  and are reported as non-coverable instead. The carve-out keys on type declarations, not member
  bodies, so an interface file carrying C# 8 default or static member implementations inside an
  unreferenced project is still classified non-coverable; when such a file matters, reference its
  project from a test project so the collector instruments it.
- Stryker's `--since` documentation promises scoping to "code changes" without stating the
  granularity; treat it as at least file-level. Whether uncommitted working-tree changes are
  covered by `--since` is unverified, so the gate warns up front on a dirty tree: the mutation
  verdict is only trustworthy once the user has committed the work.
- A single Stryker run from one test project directory mutates only the production projects that
  test project references. On a branch that changes more than one project the gate warns and
  points at `--stryker-solution`, which analyzes the whole solution.
- The gate pins Stryker's thresholds on the command line (`--break-at 100` and friends); CLI
  values override a repo-local `stryker-config.json`.
- Mutation verdicts come from Stryker's exit code plus the presence of its JSON report under the
  gate's output directory (`reports/mutation-report.json` in current Stryker); the report is an
  existence signal, never parsed. Survivors are read from the cleartext output streamed above.
- Untracked files are invisible to `git diff` and so to both gates. The preflight warning names
  them; making them visible takes a git write (a commit, or `git add -N <file>`), which is the
  user's to run, so ask them first.
- Child-process output streams to stderr raw and unsanitized, by design; only the script's own
  report on stdout strips control sequences from echoed source lines.
- On failure the temp directory (test results, Stryker output) is retained and its path printed.
  Delete it freely once inspected; CI runners should clean these up between runs.

### Trust boundary

Running the gate builds and runs the target repo's code: MSBuild tasks, analyzers, and tests all
execute on your machine, and the repo under test produces the very data the gate judges it by.
The gate's checks defend against careless code, not hostile code. Point it only at a repo you
would run `dotnet test` in; for untrusted code, use an isolated environment.
