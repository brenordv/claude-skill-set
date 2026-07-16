# General Coding Best Practices

These guidelines apply to all coding skills regardless of language or framework. They define the quality bar for production code.

---

## 1. Core Principles

### SOLID

- **Single Responsibility**: Each class/function has one clear purpose. If you cannot describe what it does in one sentence without "and", split it.
- **Open/Closed**: Code should be open for extension, closed for modification. Favor composition and polymorphism over editing existing logic.
- **Liskov Substitution**: Subtypes must be substitutable for their base types without breaking behavior.
- **Interface Segregation**: Clients should not be forced to depend on methods they do not use. Keep interfaces small and focused.
- **Dependency Inversion**: High-level modules depend on abstractions, not concretions. This also applies to data types: use the most appropriate abstraction for the use case.

### DRY (Don't Repeat Yourself)

- Extract repeated logic into reusable functions, methods, or shared utilities.
- When you see the same pattern three or more times, refactor.
- But don't over-abstract: three similar lines are better than a premature abstraction that obscures intent.

### YAGNI (You Aren't Gonna Need It)

- Implement only what is required right now.
- Do not add speculative abstractions, feature flags, or extensibility points for hypothetical future needs.
- You can always add complexity later; removing it is much harder.

### KISS (Keep It Simple, Stupid)

- Favor simplicity and clarity over cleverness.
- Readability is more important than being clever or terse.
- If a colleague cannot understand your code in 30 seconds, simplify it.

### Clean Code & Anti-Over-Engineering

- **Think before coding**: Pause and reason about the problem. Understand the full picture before touching code. This prevents both duplication and over-engineering.
- **Readability over cleverness**: Always. A clear 10-line solution beats a clever 3-line one that requires a comment to explain.
- **Avoid premature abstraction**: Don't create helpers, utilities, or frameworks for things that only happen once. Wait until you see the pattern repeat.
- **Avoid over-engineering**: The right amount of complexity is what the task actually requires. No speculative abstractions, but no half-finished implementations either.
- **Avoid code duplication through thoughtfulness**: Before writing new code, check if similar logic already exists. If it does, reuse or extend it. If you're about to write similar code in multiple places, extract it once.
- **Minimal changes**: Solve the problem asked. Don't add features, refactor surrounding code, or make "improvements" beyond what was requested.
- **Contain the blast radius**: A change that tightens or fixes one thing must not loosen or alter anything unrelated. Making one field's validation stricter must never make another field's more lenient. Keep a change's effect scoped to exactly what it targets.
- **A deliberate change outranks stale tests and legacy code**: When behavior changes on purpose, conform failing tests and old assumptions to it; never revert it, relax a validation, or weaken code to satisfy a test or to match the code it replaced. Full statement in `general-problem-solving.md` §3.

### Modern Language Features & Hygiene

- **Use the latest stable language syntax**: When the language offers a cleaner, more expressive way to write something (pattern matching, destructuring, collection expressions, etc.), prefer it over the older equivalent.
- **Use imports, not fully-qualified names**: Always add an import/using directive and reference types by their short name. Never inline fully-qualified type names (e.g., `Namespace.TypeName`) when an import would suffice.
- **Make functions/methods static when possible**: If a method does not access instance state, mark it as static. This communicates intent, avoids accidental coupling, and can enable compiler optimizations.
- **Keep dependencies current**: Before delivering work, verify that project dependencies (packages, libraries) are on the latest stable version. Outdated dependencies are a source of bugs, security vulnerabilities, and missing improvements.
- **Remove unnecessary imports/usings**: Do not leave behind unused import statements. Run the language's formatter or linter to clean them up.

---

## 2. Planning Before Coding

Before writing any code:

1. **Understand the requirements**: What problem are we solving? What are the constraints?
2. **Review existing patterns**: Match the codebase's conventions. Do not introduce new patterns unless required.
3. **Identify dependencies**: What does this code interact with?
4. **Consider edge cases**: But keep it grounded. Extreme edge cases are only worth handling if explicitly requested.
5. **Plan your approach**: Break the problem into small, testable steps.
6. **Remember Lessons learned**: Look into the `brain/gotchas` folder for any relevant problemas we already faced and learned how to fix.

---

## 3. Code Organization

### Functions & Methods

- Keep functions short and focused (~50 lines max).
- Limit parameters to 5 or fewer. If more are needed, evaluate whether the function does too much or group them into a well-named data structure.
- Use guard clauses for early returns to reduce nesting.
- Extract complex conditionals into named helper functions.

### Classes & Modules

- Keep classes small and focused on a single responsibility.
- Favor composition over deep inheritance chains.
- Prefer interfaces/abstractions to concretions.
- Organize code logically by domain/feature, not by technical type.

### File Organization

- One primary public type per file (exceptions: tightly coupled small types).
- Group related functionality together.
- Match the project's existing structure before inventing a new one.

---

## 4. Naming

- **Be descriptive**: Names should reveal intent without needing comments.
- **Avoid abbreviations**: Use `calculateTotalPrice` not `calcTP`.
- **Avoid single-letter names**: Except for tight, obvious loop counters (`i`, `j`).
- **Follow the language's conventions**: snake_case, PascalCase, camelCase (whatever the ecosystem dictates).
- **Be consistent**: Match the naming patterns already in the codebase.

---

## 5. Error Handling

- **Use specific exceptions/errors**: Never catch or throw generic exceptions when a specific one exists.
- **Provide meaningful error messages**: Include context: what failed, what was the input, why it matters.
- **Never swallow errors silently**: At minimum, log them. Prefer surfacing to the user.
- **Validate inputs early**: Guard at system boundaries (user input, external APIs). Fail fast with clear messages.
- **Use resource management patterns**: Context managers, try-with-resources, `using`, RAII (whatever the language provides).
- **When a method returning a collection fails, return empty, not null**: Unless null carries distinct semantic meaning.

---

## 6. Code Clarity

- **Comments explain "why", not "what"**: The code itself should be readable enough to explain "what."
- **Comment and doc prose follows `writing-style.md`**: the hard bans (em-dashes first among them) bind
  inside code comments, docstrings, and documentation exactly as they do in chat and PR prose.
- **No commented-out code**: Use version control for history.
- **Remove dead code you introduced**: If code you wrote becomes unused during the task, delete it. However, do not remove pre-existing dead code unrelated to your change; that increases diff scope. Instead, point it out to the user.
- **Document new code**: Add summaries/docstrings to new methods and classes so added code is properly documented.
- **Avoid magic numbers**: Extract to named constants.
- **Keep nesting shallow**: Use early returns and extraction to keep code flat.
- **Never reference separate documentation from code; explain inline instead**: Code comments, docstrings, READMEs, and summaries must never point at ADRs, design docs, wikis, planning docs, or tickets ("see ADR-012", "as described in the architecture document"). Those artifacts don't ship with the code and rot independently of it. When the reader needs that context, briefly explain the relevant decision or constraint in one or two sentences right there, in place of the pointer. This applies to every artifact you write: source files, XML docs/docstrings, READMEs, and handoff summaries.

---

## 7. Performance Mindset

- **Profile before optimizing**: Never optimize without evidence of a bottleneck.
- **Choose appropriate data structures**: Sets for membership, maps for lookup, queues for FIFO.
- **Avoid unnecessary allocations in hot paths**: Reuse, pool, pre-allocate when measured data warrants it.
- **Prefer parallel fetching over sequential**: When making independent calls (I/O, network), run them concurrently.
- **Cache expensive computations**: But only when the cost is proven and the cache invalidation strategy is clear.

---

## 8. Security Basics

- **Never trust user input**: Validate and sanitize at system boundaries.
- **Use parameterized queries**: Never concatenate user input into queries or commands.
- **Never hardcode secrets**: Use environment variables, vaults, or secret managers.
- **Never log sensitive data**: Passwords, tokens, PII must never appear in logs.
- **Apply least privilege**: Grant only the permissions needed.

---

## 9. Version Control Hygiene

- **Minimal diffs**: Change only what is necessary. Avoid scope creep.
- **Never commit secrets**: .env, credentials, API keys stay out of version control.
- **Never run git write commands**: no `git commit`, and no staging either (`git add`, `git stash`),
  even to "snapshot a baseline". Leave the working tree exactly as your file edits made it; the user
  manages git and commits when ready. To inspect state, use the read-only git-ops MCP tools.
- **Follow existing commit conventions**: Match the repo's style.

---

## 10. Handoff Discipline

Before delivering work:

1. Run the project's formatter and linters; fix all issues.
2. Ensure new code is covered by tests.
3. Run the test suite; confirm nothing is broken.
4. Summarize the change, its rationale, and any caveats or warnings.
5. Report which skills/tools were used.

## 11. Interacting with git
1. When interacting with git, use the specialized MCP (Read and apply the instructions here: `./git-readonly-operations.md`)
2. You are forbidden from using git commands that generate/persist changes, like `commit`, or `push`.

## 12. Shell & Tooling Hygiene

- **Never rewrite source files through a shell text pipeline** (piping file content through string
  replacement and writing it back). Shell string handling is encoding-lossy: Windows PowerShell 5.1
  reads BOM-less UTF-8 as ANSI and writes UTF-16, silently mojibaking every non-ASCII character in the
  file, not just the edited part. Use a real file-edit tool or a script with explicit encoding.
- **Run every command you publish in docs once before writing it down.** Shell quirks (PowerShell 5.1
  mangling native stderr on redirection, quoting differences between shells) make plausible-looking
  commands produce garbage. A documented command that was never executed is a guess.