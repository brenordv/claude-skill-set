---
name: csharp
description: >-
  Production-quality C# development following .NET best practices.
  Covers formatting, naming, async patterns, error handling, logging,
  dependency injection, testing (xUnit), and Web API conventions.
  Use for any C# coding task.
---

# C# Skill

## Instructions

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the language-specific guidance below.
> **Language-Specific Testing**: See `testing-guidelines.md` in this skill folder for framework-specific testing patterns.
> **Style & Formatting**: See `style-guidelines.md` in this skill folder for C# formatting, naming, and `.editorconfig` rules.

### ⛔ Hard Rules: Non-Negotiable

These bind every line of C# you add or modify. They are the ONE exception to "the repository is the
source of truth": when the repo itself violates one of them, the rule still wins for the code you
write. Leave existing violations in untouched code alone (never mass-refactor), but nothing new may
break these. Re-read this list before writing code, and walk it again at handoff (§18).

1. **One public type per file.** Never declare two public classes/records/enums/structs in the same file, even when neighboring files in the repo do.
2. **Never use Moq or FluentAssertions. Ever.** Not one new usage, even in a repo already full of them. Assert with native xUnit `Assert`; replace mocking with small hand-rolled fakes/stubs that implement the interface.
3. **No comments in test bodies except `// Arrange` / `// Act` / `// Assert`.** The test name and plainly written test code must carry the meaning on their own. If a test seems to need an explanatory comment, the test is too clever; rewrite it instead.
4. **`init` over `set`.** Every property defaults to `init` (or get-only/`readonly`). Use `set` only when post-construction mutation is a genuine requirement of the flow.
5. **Depend on interfaces, not concrete types.** Constructor dependencies, public members, and collection-typed properties use the narrowest fitting abstraction (`IUserService`, `IReadOnlyList<T>`), not the concrete class, and not `List<T>` where an interface fits.
6. **No useless default values.** Never initialize a property or field to `string.Empty`, `0`, `false`, or `new()` "just in case". Add a default only when it is a real, meaningful domain default.
7. **`const` over `var` for locals when possible.** A local whose value is a compile-time constant and is never reassigned is declared `const`.
8. **`string.IsNullOrWhiteSpace`, never `string.IsNullOrEmpty`**, unless whitespace-only is explicitly documented as a valid value for that field.
9. **No magic values or magic behavior.** Every enum member gets an explicit value and numbering starts at 1, so `0`/`default` always means "bug: never assigned". Never rely on an implicit default (enum, config value, parameter) to make a flow work.
10. **Never point at separate documentation.** Code, XML docs, comments, READMEs, and summaries must not reference ADRs, design docs, wikis, or tickets. Briefly explain the relevant decision inline instead; documentation does not ship with the code.
11. **Hard Rules apply to YOUR code only; never expand the task's scope to enforce them.** If a class is full of `set` properties, the property you add uses `init` and the existing ones stay untouched. If the test project uses FluentAssertions or Moq, your new tests use native `Assert` and hand-rolled fakes while the existing tests stay as they are. Fixing pre-existing violations is a separate task: mention them in your handoff summary and move on.

### 1. Prime Directives

- Treat the repository as the source of truth; match existing patterns and structure, **except where a Hard Rule above says otherwise. Hard Rules always win over repo conventions.**
- Follow `.editorconfig` strictly, even when other guidance conflicts. The canonical `.editorconfig` lives in this skill's folder; it must be used and never modified. If the project does not have one, copy it there from the skill folder.
- Prefer design patterns already present in the repo; do not introduce new ones unless required.
- Any new code should always follow the prime directives, be testable, and have well-thought-out unit tests.

### 2. Formatting, Style & Naming

Cut to summary; see `style-guidelines.md` for the full formatting, naming, and `.editorconfig` rules.

- Obey `.editorconfig` without exceptions and match the surrounding code style; use file-scoped namespaces with usings outside the namespace.
- Prefer `var`; use records for data-only types, `init`/`readonly` properties, object/collection initializers, and Primary Constructors where they apply.
- Always use braces; only one public type per file; place each chained LINQ method on its own line.
- Follow C# naming conventions: PascalCase types/members, camelCase locals/parameters, `_camelCase` instance fields, `s_camelCase` static fields, `Async` suffix on async methods, `I`/`Attribute`/`T` prefixes.

### 3. Language & Runtime Practices

- Use modern C# syntax: pattern matching (`is null`, `is not null`), pattern matching combinators (`is`, `and`, `or`, `not`), `using var`, target-typed `new()`, and collection expressions. (See `style-guidelines.md` for combinator and fully-qualified-name examples.)
- Pass `CancellationToken` through call chains when available.
- Use `ValueTask<T>` only for hot paths that frequently complete synchronously.
- If the validation is complex (more than a single check) or done in multiple places, follow the logic below:
    - If the validation is only useful for that specific class/service, create a private validation method.
    - If the validation depends on a single variable, and is generic enough to be used on the whole system, create a validation method in the most appropriate custom exception, following patterns like `ArgumentException.ThrowIfNullOrWhiteSpace`.
    - Otherwise, create an extension method, based on the most appropriate variable involved in the validation, adding unit tests to make sure the validation works.

### 4. Forbidden

- `dynamic` type. If that's the absolute only option, stop, explain to the user what is going on and your reasoning to think this is the only option, and ask the user for insights.
- Reflection: it drastically reduces code readability and creates "magical" behavior in the code.
- LINQ Query syntax: only LINQ Methods (`Where`, `Select`, `GroupBy`, etc.) are allowed.
- `#region` / `#endregion`, except a `Test Helpers` region at the end of test files.
- `ConfigureAwait`: async code should be awaited by using `await`.
- Enabling nullable reference types: they must stay disabled in all projects.

### 5. Exceptions & Error Handling

- Discover the repository's base exception type and use it for custom exceptions.
- If no base exception exists, introduce a domain-appropriate base and inherit from it.
- Avoid throwing or catching `Exception`; catch specific exceptions and recover when possible.
- If the repo provides error helpers (for example, `LogAndProcessError`), use them consistently.

### 6. Serialization

- If the repository has `Newtonsoft.Json`, then use it as a source of truth, and avoid using other packages. Otherwise, use `System.Text.Json`.

### 7. Logging

- Always use structured logging with message templates and named placeholders.
- Never use string interpolation inside log messages.
- Use logging scopes when available to enrich context.
- Log messages should be concise but meaningful. Indicating which step of the flow failed, and include available data to facilitate debugging.
- When adding a nullable variable to the log message template, include braces around it, to facilitate the visualization of null/empty variables. Example: `User Name: [{UserName}]`.
- Avoid making the code too verbose by adding too much `LogInformation` entries. Add them when they provide meaningful insights to the flow.
- Check if there's an Error Handling Middleware that logs the errors and avoids double-logging an exception.
    - If the method where the error happened has more details to include in the log message, create an error log with the relevant data.
- Avoid generic error log messages. (I.E: `An error has happened: {ExceptionMessage}`); The error messages must be meaningful and provide insights on what happened.

### 8. Refit External Calls (Default Pattern)

- Define Refit interfaces under the API clients area and use Refit attributes for routes, bodies, and parameters.
- Register all Refit clients in a single extension method, and wire them in `Program.cs` via `RegisterRefitClients`.
    - If the repository already have an initialization method with a different name, use that instead.
- Always configure each client with `BaseAddress` from configuration and reuse the shared `ConfigureRefitClient` policy setup.
- Use client-credentials authentication via the existing profiles when calling external services.
    - If the repository has a dedicated authentication package already installed, use it consistently.
    - Otherwise, create an extension method to configure authentication in a centralized place.
- Apply the standard retry policies: unauthorized retry plus transient HTTP error policy.
- Configure request timeouts and shared message handlers centrally when the repo provides them.
- Prefer typed `ApiResponse<T>` when you need to access the body/content returned; If all you need is the status codes and headers, use `IApiResponse` instead.
- Always validate responses with custom methods in the repository, if available. Otherwise, use `EnsureSuccessStatusCode`.
- Log failures with structured logging and rethrow a domain-appropriate exception.

### 9. Global Error Handling

When an Error Handling Middleware is present:
- Use single error-handling middleware to capture exceptions and return `ProblemDetails` (dotnet native).
    - Do not include technical details in production. For production only a meaningful error message should be returned.
    - In case of doubt of which environment is being targeted, assume it is production.
- Check `HttpResponse.HasStarted` before writing any error response.
- Map known exception types to consistent status codes and titles.
- Log errors with structured context (method, path, client identifiers) before responding.

### 10. Configuration Validation

- Validate configuration at startup with Options `Validate` + `ValidateOnStart`.
- Use reusable validation helpers and clear failure messages.
- Fail fast on invalid configuration; do not defer config errors to runtime.
- All variables read from settings files (`appsettings.json`, `local.settings.json`, etc.) must be validating during startup, as soon as possible, and if missing/invalid,
  follow the repositories pattern to propagate a meaningful error message that will make it clear what is wrong.
- If the repository doesn't have a pattern, throw a domain-appropriate exception instead.

### 11. Dependency Injection Organization

- Register services via extension methods grouped by concern (DI, AutoMapper, HTTP clients, etc.).
- Keep `Program.cs` minimal by delegating setup to these extensions.
- Choose explicit lifetimes (`Singleton`, `Scoped`, `Transient`) based on behavior.

### 12. Documentation Comments (Summary Required)

- Every new public class, interface, struct, record, and method must have XML documentation comments.
- Every new internal/private methods or classes should be documented unless the repo explicitly avoids it.
- Use `/// <summary>` on types and members; keep it concise and action-oriented.
- Use `<see cref="..."/>` when referencing other types or members in the summary.
- For orchestration methods, write a high-level overview in the orchestrator summary and put step detail in the called methods.
- Use `<param>` for every parameter and `<returns>` for non-`void` methods.
- Use `<exception cref="...">` for exceptions the method may throw and document the condition.
- Use `<remarks>` for important constraints or non-obvious behavior.
- Keep XML well-formed and place comments directly above the declaration (and above attributes).

### 13. Architecture & Design

- Create domain-specific folders for models, requests, responses, and constants when adding new domains.
- Prefer extension methods over helper classes; document extension methods with summaries.
- SQL data access uses Dapper, not hand-rolled ADO.NET command/reader code. EF Core only when an ORM is genuinely warranted, never as the default.

### 14. Testing

Use xUnit with native `Assert` methods and the AAA (Arrange, Act, Assert) pattern with capitalized `// Arrange` / `// Act` / `// Assert` comments, and **no other comments anywhere in a test** (Hard Rule 3). **Moq and FluentAssertions are banned outright** (Hard Rule 2), including in repos that already use them: new tests use native `Assert` and hand-rolled fakes. Before writing tests, understand the code and the flow it participates in, then plan happy path, sad/broken path, and grounded edge cases; avoid tests that differ only in test data. Test projects and files mirror the source with a `.Tests` / `Tests.cs` suffix, and coverage should stay at least 90% where ROI justifies it. See `testing-guidelines.md` for `[Theory]`/`TheoryData`, `Faker`/`MockDataGenerators`, `BuildSut` helpers, naming, and coverage detail.

### 15. NuGet packages

- Use the latest stable version of each package.
- Always use transient dependencies and avoid adding the same dependency on multiple projects, unless necessary.
    - On that note, pay attention to the repercussions of moving a package to a more central project, if it doesn't make sense, leave a note on the csproj file explaining why.
    - The only exception to this rule is the following packages: `coverlet.collector`, and `Microsoft.NET.Test.Sdk`. They need to be present on all test projects for the pipelines to work properly.

### 16. Web API Conventions (When Applicable)

- Controller actions return `IActionResult`.
- If the API is mature enough to contain an error handling middleware, controllers will orchestrate only; no business logic and no `try/catch`.
    - If no error handling middleware is found, then add a `try/catch` to the endpoint method in a consistent way with other existing endpoints.
- Validate early in controllers; return `400 Bad Request` as soon as possible.
- `GET` returns `200 OK` with data or `204 No Content` when empty.
- `POST` returns `201 Created` with data.
- Do not return status codes inside response bodies.

### 17. Analyzer & Tooling Expectations

- Respect analyzer severities configured in `.editorconfig`.
- All projects must use the latest stable version of `Roslynator.Analyzers`.

### 18. Quality Validation

Before handing off your work:
1. **Walk the Hard Rules list (⛔ section at the top) item by item against your diff.** For each rule, scan the changed lines and fix every violation. This step is mandatory even for small changes; these are the rules that keep regressing.
2. Run `dotnet format` and fix any reported problems.
3. Make sure the code is changed, and the new use-case is covered by unit tests. If there are no tests, create test coverage for it to improve repository maintainability.
4. Run `dotnet test` to make sure you didn't break anything.
5. Check that all NuGet packages are on the latest stable version. Run `dotnet list package --outdated` and update any that are behind.
6. Summarize the change to the user and report any problems, caveats, or warnings with the code change. In the summary, include the skills that were used to solve the request.

### 19. AI Guardrails

- Follow existing repository patterns before introducing new abstractions.
- If a rule conflicts, follow the order of precedence defined in `style-guidelines.md` (§9 Precedence Order), remembering that the Hard Rules at the top of this skill sit above that entire list.

## When to Use This Skill

- Writing new C# features, services, or Web APIs
- Refactoring, debugging, or reviewing C# code
- Adding or updating xUnit test coverage
- Any C# task where production-quality, idiomatic .NET code is expected
