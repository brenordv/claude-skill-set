# C# Style Guidelines

These rules reflect the `.editorconfig` and formatting conventions for C# projects. Follow them strictly; they take precedence over all other guidance when in conflict.

---

## 1. Formatting

- **Obey `.editorconfig` without exceptions.** It is the ultimate authority on style.
- Match the surrounding code style exactly.
- Use file-scoped namespaces when the repo does; keep usings outside namespaces.
- Always use braces, even for single-line blocks.
- Never use `#region` / `#endregion`, unless creating a `#region Test Helpers` at the end of test files.
- When chaining methods, place each method on a new line:
  ```csharp
  products.Where(p => p.IsActive)
          .Select(p => p.Price)
          .ToList();
  ```
- Only one public class/record/enum/struct per file, **no exceptions**. A repo that bundles several types per file does not license you to do the same; new types always get their own file (Hard Rule 1 in `SKILL.md`).
- When the constructor only assigns arguments to private fields, use the Primary Constructor.
- Organize code to improve readability and reduce nesting.

---

## 2. LINQ Usage

- LINQ Query syntax is **forbidden**. Only LINQ Methods are allowed (`Where`, `Select`, `GroupBy`, etc.).
- This reduces complexity and improves readability.

---

## 3. Object Initialization

- Whenever possible, use collection initialization instead of `new {}` statements.
- When instantiating an object and setting properties right after, use object initializer: do it all at once.

---

## 4. Immutability, Types & Magic Values

- When creating a class that will only hold data, prefer `record` over `class`.
- **Default every property to `init`** (or get-only/`readonly`). Reach for `set` only when post-construction mutation is a genuine requirement of the flow; mutable-by-default is a defect, not a style choice (Hard Rule 4). This binds new properties only: in a class full of `set` properties, add yours with `init` and leave the existing ones untouched (Hard Rule 11: no scope creep).
- **Depend on interfaces, not concrete types** (Hard Rule 5). Constructor dependencies and public members are typed as the abstraction (`IUserService`), not the implementation. Same for collections: prefer the narrowest interface that fits the usage: a property only populated during deserialization and then read is `IReadOnlyList<T>`, not `IList<T>` or `List<T>`. It states intent and blocks accidental mutation at call sites.
- **Declare a local `const` when you can** (Hard Rule 7). If the value is a compile-time constant (string, numeric, bool, enum) and never reassigned, it's `const`, not `var`. Follow the constant naming convention (PascalCase).
- Implement nullable only when necessary.
- Nullable reference types must be **disabled** in all projects.
- Do not use `dynamic` type. If it's the absolute only option, explain to the user and ask for insights.
- **Never add useless default values** (Hard Rule 6). A string property receiving `string.Empty` as a default is useless: validations against it use `string.IsNullOrWhiteSpace`, which fails for both `string.Empty` and `null`. The same applies to defaulting to `0`, `false`, or `new()` "just in case". Add a default only when it is a real, meaningful domain default; otherwise leave it unset. The same holds for fallback expressions, not just initializers: `value ?? string.Empty` is the same useless default whenever every consumer downstream treats `null` and `""` alike. Fall back to `null`, or don't coalesce at all, unless the empty string is a distinct, meaningful value.
- **No magic values or magic behavior** (Hard Rule 9). Never design a flow that only works because some part of the system silently initializes a value to its default. Magic behavior always comes back to bite.
- **Enums: every member gets an explicit value, and numbering starts at 1.** That way `0` (the CLR default for an unassigned enum) always means "bug: this was never set" and gets caught instead of silently behaving like a valid member:
  ```csharp
  // Good: default(OrderStatus) is 0, which maps to no member, a bug that surfaces
  public enum OrderStatus
  {
      Pending = 1,
      Shipped = 2,
      Delivered = 3,
  }

  // Bad: an uninitialized value silently means Pending
  public enum OrderStatus
  {
      Pending,
      Shipped,
      Delivered,
  }
  ```

---

## 5. Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Public types and members | PascalCase | `GetUserById` |
| Locals and parameters | camelCase | `userId` |
| Interfaces | Prefix with `I` | `IUserService` |
| Attributes | Suffix with `Attribute` | `RequiredAttribute` |
| Enums (singular) | PascalCase | `UserStatus` |
| [Flags] enums (plural) | PascalCase | `Permissions` |
| Private instance fields | `_camelCase` | `_userRepository` |
| Private static fields | `s_camelCase` | `s_instance` |
| Private static readonly | PascalCase | `DefaultTimeout` |
| Type parameters | Prefix with `T` | `TModel`, `TRequest` |
| Async methods | Suffix with `Async` | `GetUserAsync` |
| Constants | PascalCase | `MaxRetryCount` |

### Naming Rules

- Avoid consecutive underscores in identifiers.
- Avoid obscure abbreviations; prefer clear, descriptive names.
- Avoid single-letter names except for tight, obvious loop counters.
- Use `@`-prefixed identifiers only for interop with reserved keywords.
- Respect naming conventions from `.editorconfig` and existing code.
- Always prefer `var` over explicit types. The type is already visible from the right-hand side or IDE tooling.

---

## 6. Code Organization

- Classes holding extension methods live inside an `Extensions` folder.
- Code projects live under `src/`, test projects under `src/tests/`.
- Declare fields and properties before methods, so the class's data is visible before its behavior.
- Organize code to improve readability and reduce nesting.

---

## 7. Nullable Handling

- When dealing with nullable types, prefer safe guarding and asserting you have all you need early, instead of multiple null-coalescing checks during execution.
- **Check strings with `string.IsNullOrWhiteSpace`, never `string.IsNullOrEmpty`** (Hard Rule 8). A whitespace-only string is almost never a meaningful value; `IsNullOrEmpty` lets `"   "` slip through as valid. Use `IsNullOrEmpty` only when whitespace-only is explicitly documented as valid for that field.
- When a method returning a list fails, return empty list, not `null`.
- Prefer `is null` / `is not null` over `== null` / `!= null` for null checks: idiomatic and clearer in chains.
- Don't use `?.` on a value the surrounding control flow already guarantees non-null (e.g. inside `if (error != null)`). It implies a null case that can't happen. Use direct member access.
- Since nullable reference types are disabled project-wide, don't annotate reference types with `?` (e.g. `string?`); a reference type is already nullable, so it's just noise. The canonical `.editorconfig` enforces this as a build error (`dotnet_diagnostic.CS8632.severity = error`): a stray `?` annotation fails the build instead of slipping through.

---

## 8. Modern Syntax & Qualifications

- Use pattern matching combinators (`is`, `and`, `or`, `not`) over boolean operators when checking a single variable against multiple values or ranges:
  ```csharp
  // Good
  ex.Status is >= 500 or 429

  // Bad
  ex.Status >= 500 || ex.Status == 429
  ```
- Use property patterns when testing two or more properties on the same object:
  ```csharp
  // Good
  return payment is { IsPaid: true, InstallmentMissed: false };

  // Bad
  return payment.IsPaid && !payment.InstallmentMissed;
  ```
- Don't emit redundant no-op conversions. Calling `ToUniversalTime()` on a value a prior guard already
  proved is `DateTimeKind.Utc` implies it might not be UTC; rely on the guarantee, or consolidate all
  `DateTimeKind` handling into one place.
- Never use fully-qualified type names inline. Add a `using` directive and reference the short name:
  ```csharp
  // Good (with `using Azure;` at the top)
  new PredicateBuilder().Handle<RequestFailedException>(...)

  // Bad
  new PredicateBuilder().Handle<Azure.RequestFailedException>(...)
  ```
- Make methods `static` when they do not access instance state.
- Prefer `var` over explicit types in all cases.

---

## 9. Precedence Order

If rules conflict, the order of precedence is:
0. **Hard Rules (⛔ section in `SKILL.md`): above everything, including repository conventions.** A repo that violates a Hard Rule never licenses new code to violate it.
1. Repository conventions and `.editorconfig`
2. Local file patterns
3. This style guide
4. Skill-level guidance
