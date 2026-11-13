# General Coding Best Practices

These guidelines apply to all coding skills regardless of language or framework. They define the quality bar for production code.

---

## ⛔ Hard Rules: Non-Negotiable

These bind every line of code you add or modify, in every language, and they beat repository
conventions: an existing duplicate or an existing deprecated call in the repo is precedent, not
permission. The scope boundary cuts both ways: leave pre-existing violations in untouched code
alone (mention them in the handoff; never mass-refactor), but nothing new may break these.
Re-read this list before writing code and walk it again at handoff (§10).

1. **Search before you write.** Before adding any function, class, helper, mapping, or constant,
   search the repo for an existing implementation: the domain terms, the names you'd expect
   it to have, and the sibling modules where it would live (native search tools or `git_grep` /
   text-search, never shell grep; see §12). If something close exists, reuse or
   extend it; if you deliberately don't, name it in the handoff summary and say why. Writing a
   new helper without having searched first is a defect even when no duplicate turns out to exist.
2. **No deprecated or obsolete APIs.** Never add a call to an API that is deprecated or obsolete
   in the version this project pins. An API you know only from memory is an unverified
   assumption: before using one you haven't seen working in this repo, confirm it is current for
   the pinned version in the official docs. This is the codegen-time extension of
   `general-problem-solving.md` §"Back external assumptions with an official source". Every
   deprecation warning the compiler, linter, or build emits on a line you touched is a blocking
   failure to fix before handoff, not noise to scroll past.
3. **No change-narration comments.** A comment describes the code as it now stands: a constraint,
   an invariant, a domain fact the code can't show. It never describes the change that produced
   it: not the bug it fixes, the request or review finding that prompted it, the behavior it
   replaces, and never an argument that the new version is correct. "Why, not what" (§6) means the
   why of the code, never the why of the edit. The test: a comment that only makes sense to a
   reader who knows the previous version, the task, or the conversation is narration; delete it
   and put that story in the handoff summary or commit message. This bites hardest when fixing
   code: the urge to annotate the fix at the fix site is exactly the pattern banned here.
4. **New code respects the file-size tiers; never mass-refactor to hit them.** The per-language tier
   table in §3 (File Organization) sets a warn threshold and a hard cap per language (Python warn 800,
   C#/Rust warn 700; cap 1,500 for all three, comparisons inclusive). A file you create, or a
   pre-existing file your change grows across the cap, must not sail past it: split the new code into a
   new cohesive module on a real boundary. New code that pushes a file past "worth reviewing" is the
   signal to split, not to keep piling on. This binds your code only, per the scope boundary above: an
   already-oversized file you had to touch is never yours to refactor for size. Route your addition
   into a new module and name the oversized file in the handoff. Test code is exempt from the hard cap.
   The new-code quality gate enforces this on new and cap-crossing production files.
5. **A version number moves only as a release act, never as a side effect of other work.** Don't
   bump a project version (`version` in Cargo.toml, package.json, or pyproject.toml, `<Version>` in
   a csproj, a VERSION file, `__version__`) while doing feature or fix work. On a project that has
   never been released (no release tag, nothing on a registry, no live deployment), the version
   keeps its initial value however many changes land, so the first release ships as 1.0.0 or the
   scaffold's 0.1.0, not an accumulated 1.4.9 that no consumer ever saw. A history of per-change
   bumps in the repo is precedent, not permission. Once the project is live, bump only when the
   user asks for a release or the repo's release process calls for it in the task at hand; the
   increment then follows that process.
6. **Match the mechanism to the cases in front of you.** When the inputs are a known, small, fixed
   set, handle them directly: an if/else, a literal, a direct call. A mechanism whose only
   justification is absorbing future additions nobody named (an accumulator array of settings, a
   registry or config-driven loop, an abstraction seam with one implementation) is a defect even
   when it works. The test: if deleting the mechanism and writing the cases directly makes the code
   shorter and clearer, the mechanism is the finding. The canonical shape: a deploy script builds
   an `EXTRA_SETTINGS=()` array conditionally and expands it later, for exactly two settings; the
   right-sized version passes the two values inside the `if` directly. Scalability
   justifies the mechanism only when the ask names the growth. A helper extracted for testability
   or clarity is not this defect; the defect is the helper whose only argument is future callers.
   The same test applies when a guideline names the mechanism. `TimeProvider` is the shape for
   code that must read the clock itself; when the method under test already takes the instant as
   a parameter, the test passes the parameter, a real-clock fallback on it that no production
   caller uses gets removed, and no clock abstraction is added. A guideline's example illustrates
   its intent; it is never an order to add that mechanism to code that already meets the intent
   another way.
7. **Acquiring and running software is the machine owner's act, never yours.** When a tool the
   task needs is missing or the wrong version or build, stop, report it, hand the user the exact
   install command, and proceed only on their explicit yes. Never fetch and execute anything new:
   an installer, a release binary or archive, a script piped to a shell. A global tool install
   (`dotnet tool install -g`, `cargo install`, `npm install -g`, winget, brew) is the same act
   even though nothing is downloaded by hand. "It's the official release artifact", "it only went
   to a temp directory", and "it unblocks the task" are rationalizations, not consent, and
   announcing the install while performing it is still a violation. Fine without asking: tools
   already installed that the task implies (the project's compiler, linter, build tool), and the
   project's own dependency manager restoring or adding packages inside the project's manifest
   and local environment. A documented install flow the user invoked by name
   (`install-reference.md`) is consent for exactly the steps it defines.
8. **Read the routed skill and the topic's knowledge file before the first edit.** The skill for
   the language or framework being touched (its `SKILL.md` and the reference file it names for the
   work: `testing-guidelines.md` for any test, `style-guidelines.md` where formatting is the task)
   and the knowledge file for the task's topic (`testing.md` for tests, `security.md` for auth or
   input handling, `database.md` for schema or queries) are read before any code is written,
   whatever the task's size or workflow path. A test written from habit because "add some tests"
   looked too small to route is the defect this rule names: the habits those files replace (fixed
   calendar dates, invented literal ids, a mocking library the skill bans) are exactly what shows
   up when they're skipped. Reading them after a correction doesn't count as having loaded them.
9. **Documentation describes the unit it sits on, never the system around it.** A summary,
   docstring, or doc comment says what the unit is or does: for a type, what it represents, what
   its members mean, and its constraints and invariants; for a method, its behavior, inputs,
   outputs, and what it throws. It never says who produces, consumes, or calls the unit, which
   services, queues, or functions relay it, or how it is deployed. Naming what the unit itself
   calls or binds to is describing it: a publisher names the hub it sends to, a trigger function
   names the queue it reads. The check: would the summary still be true if a different caller used
   the unit, or it travelled by another route? If not, it describes usage, and that context belongs
   at the code that does the wiring. A message model that a frontend publishes to a queue a
   function reads gets a summary about the message, and nothing about the frontend or the
   function. A repo full of such summaries is precedent, not permission.
10. **A handled failure never ends on the success path.** A caller must never mistake a failure
    for success. Every catch, except, or error arm ends in exactly one of these:
    - **Not catching.** When nothing at this level can do one of the endings below, let the
      failure propagate. A catch that adds nothing is noise.
    - **Throw.** Rethrow, or wrap in the repo's domain error with context the caller lacks, keeping
      the original as the cause (inner exception, `raise ... from e`, `.context(...)`).
    - **Return a failure the caller's contract makes it handle.** A result type, or a sentinel the
      signature or its doc comment documents: null or None for not-found, Rust `Ok(None)` in a
      `Result<Option<T>>`.
    - **Recover for real.** A retry that succeeded, a fallback that produces a correct value.
    - **Report at a boundary.** A request handler returns an error response (generic to the
      caller, details in server logs); a UI handler shows an error state; a job or CLI exits
      non-zero. A message or event handler rethrows to end a delivery only where its host
      redelivers until success or dead-letters (a Service Bus or Storage queue trigger does).
      Where the host moves past the message whether or not the handler throws (a stream that
      checkpoints its position), the handler rethrows on earlier attempts where the host has a
      bounded retry policy, or retries in code where it doesn't, and on the last attempt parks the
      message somewhere recoverable instead of throwing and logs at error so an alert can fire.
      Where the SDK says not to throw from the handler, the handler parks the message and logs at
      error. If the park fails too, the handler logs at critical with the message's position so it
      can be recovered, and keeps the host from moving past the message where the host allows it.
      The host's skill has the mechanics (`azure-eventhub/SKILL.md` for Event Hubs triggers and
      the processor).

    Logging is never an ending on its own. Log a failure once, where the context is: a catch that
    throws or wraps logs only data the boundary can't see, or carries it in the wrapped error, and
    the boundary or the error-handling middleware logs the rest. Three catches are exempt. An SDK
    error-notification callback whose library owns recovery (an Event Hubs processor's error
    handler) ends in a log or an alert. Best-effort work whose failure can't change the result
    (cleanup, telemetry other than a required audit record, cache warm-up) logs at warning level,
    naming the skipped work and its identifier (item id, cache key) with the error attached, and a
    comment at the catch says it is best-effort. A handler whose park failed, on a host that moves
    past the message whether or not it throws, ends in the critical log above. Cancellation is not
    a failure: catch it only where the stop was requested, and never let a broad catch or a retry
    loop absorb it. The shape that regresses lets an unexpected error end normally: a broad catch
    of an SDK's base error type, after the specific handlers or as one catch that checks the
    status, or a catch-all error arm. Let that error propagate or wrap it with context instead
    (csharp Hard Rule 17 and python Hard Rule 8 show it in C# and Python). The test half is
    `testing.md` ⛔ Hard Rule 1: every arm you add is driven by a test.
11. **A credential is attached by the client's configuration, never by its call surface.** A
    static key (an API key, function key, or subscription key) is set where the client is built,
    as a default header or the SDK client's credential argument, from configuration backed by a
    secret store, never a committed settings file. A token that expires or varies per user or
    tenant comes from an auth handler on the client's pipeline. Neither is ever a parameter of the
    client's call methods, and neither goes in a URL or query string: a credential in a URL lands
    in web logs, browser history, and Referer headers even over HTTPS
    ([OWASP](https://community.owasp.org/vulnerabilities/Information_exposure_through_query_strings_in_url)).
    When a service issues the credential as a URL (a SAS or presigned URL, a webhook URL), the
    whole URL is the secret: loaded from a secret store, never logged. A credential that already
    reached a URL, a log, or source control is exposed; rotating it is the owner's act, and the
    handoff says so. A test of credential handling asserts on the outgoing request, never on an
    interface signature. The C# mechanisms are in `csharp/SKILL.md` §8.
12. **State you add joins its machine on purpose.** A change that adds a state value, adds a flag
    or field to an owner that already holds a status or other flags, or writes a persisted status
    must leave the owner unable to reach a combination nobody designed. A lone toggle that
    combines with nothing (`isOpen` on a modal) is outside this rule; state that gates access
    never is. A status field or column the change adds has no default that names a real state:
    new rows take theirs from the transition that creates them, and existing rows one derived
    from their data or a named never-assigned state, which every reader handles and which a
    transition leaves (a backfill, or the next writer that can derive the real state) unless the
    row is closed. First find every writer and reader of a value, flag, or field the change adds
    (the Hard Rule 1 search, aimed at the field). Then:
    - **Every reader handles every state, and the default fails closed.** Dispatch is a switch,
      match, or if/else-if chain over two or more states, or a grouping predicate (`IsTerminal`)
      written once on the state's type. Dispatch the change writes is exhaustive where the
      language can check it, so a missed state is reported at every reader that misses it, and no
      arm treats "everything else" as one state. The only default allowed fails when reached (it
      throws, or returns a failure the caller must handle, Hard Rule 10), so an out-of-type value
      (a newer server, an old row) fails closed; a type-only check or a debug-only assert is not
      that default. A one-state test (`status == Paid`) is not dispatch and keeps its `else`, but
      a new state its `else` would mishandle joins it. Per-language setup: rung 2 of
      `implicit-state-machines.md` §"Making it explicit" and the language skill's Hard Rules.
    - **Readers the change reaches get the new case, and nothing more.** An existing dispatch the
      checker can't verify (a switch statement, a discard or `_` arm, a catch-all `else`) keeps
      its form, gets the case, and is named in the handoff as compile-unchecked. Existing flags
      and persisted or wire-format fields are not converted; a cluster of them goes in the handoff.
    - **A flag or field the change adds joins the state it depends on.** A boolean that can't be
      true beside another, or that only means something in some states, becomes a value of the
      status. Data valid in only some states lives in that state's variant where the language
      has sum types, set and cleared by the transitions in and out.
    - **A persisted status moves only from the state the writer expects.** The write names it
      (`UPDATE ... SET status = @next WHERE id = @id AND status = @expected`) and checks the row
      count; a concurrency token the store checks (an ORM version, an `If-Match` ETag), on a row
      whose state the code checked after reading it, meets the same intent, and a failed check,
      the code's or the store's, ends as zero rows does. Zero rows is a rejected transition: it
      stops the transition and every effect after it, is never a silent return, and is recorded
      with the expected and actual state, the trigger, and the correlation id. A message or
      webhook handler acknowledges it only as a duplicate or late delivery and otherwise hands it
      back per Hard Rule 10; a caller that required the transition gets it reported per
      Hard Rule 10 (a 409 at a request boundary). A webhook is signature-checked
      before anything else and deduplicated by event id, and a handler that dedupes on an event
      or message id records it in the transaction that applies the event. An effect that follows
      the write commits with it, as a write in the same transaction or an outbox row that write
      inserts.
      How to tell duplicate, late, and early deliveries apart and end each, how work before the
      write is deduped and effects after it commit, how outbox rows drain, what a machine that
      can return to the expected state needs, and when a single writer may check the state in
      code are in `implicit-state-machines.md` §"Persisted transitions and deliveries".
    - **A persisted in-flight state has a way out** when the process dies mid-transition: a
      reaper that acts on a timeout measured from the row's latest claim (the entered-at timestamp
      the transition writes, or the claim time a takeover writes), and whose reclaim fences the
      worker it took the row from, with a bounded retry, counted at each claim, that ends in a
      failed state that is final or has its own exit, which resets the attempt count but never
      reuses an attempt id. An outbox row is one, and its dead state has its own exit. Work that
      may already have reached a receiver never ends final: the last retry parks it for a lookup.
      The reclaim fence, the park, and the drain contract are in the same section.
    - **State that gates access fails closed**: verified, approved, active, locked, revoked, MFA,
      sessions, one-time tokens, and reset or checkout steps. Every path that authenticates or
      authorizes the principal is one of its readers, whether it reads the field yet or not. A
      check names the states that allow, so a new, unknown, default, or zero value denies; an
      existing check the change reaches that names a denying state (`status == Locked`) gets the
      new state beside it when that state must deny, and either way its deny-by-name shape goes
      in the handoff; request input never binds to the field; each step checks the step before
      it on the server; a one-time token expires and is consumed by the conditional write above,
      and zero rows denies the request, never acknowledges it or returns what the first consume
      granted. `implicit-state-machines.md` F14 has the rest.

    The shape this rule exists for is the flag added to make a symptom stop: a late `shipped`
    webhook moves a cancelled order back to `Shipped`, and the patch adds
    `if (order.WasCancelled) return;`, a second copy of the status that every other writer
    ignores. The fix is the conditional write `WHERE status = 'Paid'`, which rejects the late event
    at the one place the order changes state and records the rejection. Fix the transition that
    produced the bad state, not the symptom downstream, and stop at the smallest fix that closes
    it (Hard Rule 6): no State pattern, state-machine library, or typestate API the cases don't
    demand. Game code keeps the explicit machines `coding-gamedev.md` §3 prescribes. Tests drive
    each transition the change adds, one the machine must reject, and an effect that fails after
    the commit with the message redelivered.

---

## 1. Core Principles

### SOLID

- **Single Responsibility**: Each class/function has one clear purpose. If you cannot describe what it does in one sentence without "and", split it.
- **Open/Closed**: Code should be open for extension, closed for modification. Favor composition and polymorphism over editing existing logic. Design an extension point when a requirement exists for it; pre-building seams for futures nobody named is the defect ⛔ Hard Rule 6 bans.
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
- **Avoid over-engineering**: The right amount of complexity is what the task actually requires. No speculative abstractions, but no half-finished implementations either. The mechanism-sizing test is ⛔ Hard Rule 6.
- **Avoid code duplication through thoughtfulness**: Before writing new code, check if similar logic already exists. If it does, reuse or extend it. If you're about to write similar code in multiple places, extract it once. The pre-write search is mandatory, not aspirational: ⛔ Hard Rule 1.
- **Minimal changes**: Solve the problem asked. Don't add features, refactor surrounding code, or make "improvements" beyond what was requested. Minimal limits what you touch beyond the goal, never how well you meet a goal the user stated: when the ask gives a reason, `general-problem-solving.md` §2 decides which way of doing the step counts as done.
- **Contain the blast radius**: A change that tightens or fixes one thing must not loosen or alter anything unrelated. Making one field's validation stricter must never make another field's more lenient. Keep a change's effect scoped to exactly what it targets.
- **A deliberate change outranks stale tests and legacy code**: When behavior changes on purpose, conform failing tests and old assumptions to it; never revert it, relax a validation, or weaken code to satisfy a test or to match the code it replaced. Full statement in `general-problem-solving.md` §3.

### Modern Language Features & Hygiene

- **Use the latest stable language syntax**: When the language offers a cleaner, more expressive way to write something (pattern matching, destructuring, collection expressions, etc.), prefer it over the older equivalent. And never the withdrawn one: deprecated/obsolete APIs are banned outright (⛔ Hard Rule 2).
- **Use imports, not fully-qualified names**: Always add an import/using directive and reference types by their short name. Never inline fully-qualified type names (e.g., `Namespace.TypeName`) when an import would suffice.
- **Make functions/methods static when possible**: If a method does not access instance state, mark it as static. This communicates intent, avoids accidental coupling, and can enable compiler optimizations.
- **Keep dependencies current**: Before delivering work, verify that project dependencies (packages, libraries) are on the latest stable version. Outdated dependencies are a source of bugs, security vulnerabilities, and missing improvements.
- **Remove unnecessary imports/usings**: Do not leave behind unused import statements. Run the language's formatter or linter to clean them up.

---

## 2. Planning Before Coding

Before writing any code:

1. **Load the routed guidance**: the language skill's `SKILL.md` and the reference file it names for this work (`testing-guidelines.md` for tests), plus the knowledge file for the task's topic (`testing.md` for any test work). This happens before step 2 and whatever the task's size (⛔ Hard Rule 8).
2. **Understand the requirements**: What problem are we solving? What are the constraints?
3. **Review existing patterns**: Match the codebase's conventions. Do not introduce new patterns unless required. When an existing convention contradicts this skill set's guidance, the conflict goes to the user (next subsection).
4. **Identify dependencies**: What does this code interact with?
5. **Consider edge cases**: But keep it grounded. Extreme edge cases are only worth handling if explicitly requested.
6. **Plan your approach**: Break the problem into small, testable steps.
7. **Remember Lessons learned**: Query the lessons vault (`vault_list` with `project: "lessons"`, topic tags from the task) for problems already faced and how they were fixed, per `general-remembering-lessons.md`.

### When the repo and the guidelines disagree

"Match the repo" and "use the modern pattern" collide whenever a codebase carries legacy
conventions this skill set has since moved past. Who wins is not yours to decide:

- **A Hard Rule ends the question.** Hard Rules (this file's ⛔ block and the routed language
  skill's) beat repository conventions. No ask needed; the rule wins.
- **Anything below a Hard Rule goes to the user.** When the repo's established pattern and a
  skill or knowledge recommendation point opposite ways on code you are about to write, don't
  silently side with either. Sometimes the user wants consistency with the repo; sometimes the
  repo is legacy and they want the modern pattern on new code. The code can't tell you which, so
  ask: name the pattern, show the repo's way and the guideline's way (one line each), and give
  your recommendation. Batch every conflict you've spotted into a single question instead of
  interrupting per finding.
- **One answer per pattern per task.** The user's choice holds for the rest of the task; don't
  re-ask per file. If the answer sounds durable ("in this repo, always the modern way"), suggest
  recording it in the project's CLAUDE.md, or capture it per the lesson protocol when it
  generalizes beyond the repo.
- **When you can't ask** (an autonomous workflow stage, a subagent), follow the repo's pattern
  for consistency and flag the conflict prominently in the handoff so the user can overturn it.

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

### File size

Files grow until they stop being readable. These per-language tiers mark where size stops being
normal and starts being worth a second look. They apply to files you create or grow, and are the
detail behind ⛔ Hard Rule 4; they are not a mandate to refactor existing files.

| Language | Very common | Still normal | Worth reviewing | Often too large |
| -------- | ----------: | -----------: | --------------: | --------------: |
| Python   |     200-500 |      500-800 |       800-1,200 |          1,500+ |
| C#       |     150-400 |      400-700 |       700-1,000 |          1,500+ |
| Rust     |     150-400 |      400-700 |       700-1,000 |          1,500+ |

- The warn threshold is the start of "worth reviewing" (Python 800, C# and Rust 700); the hard cap
  is 1,500 for all three. Comparisons are inclusive: a 1,500-line file is at the cap.
- New code that would push a file past "worth reviewing" goes into a new cohesive module, split on a
  real domain boundary rather than an arbitrary line count.
- An existing file already over a tier is not yours to mass-refactor for size (⛔ Hard Rule 4, and
  the blast-radius rule in §1). Route your new code into a new module and name the oversized file in
  the handoff so the owner can decide.
- The numbers cover the three languages named. For others (TypeScript, GDScript, C++, ...), the same
  instinct applies; there is no hard cap, so use judgment.
- The new-code quality gate in each language skill (`scripts/*_quality_gate.py`) enforces the cap on
  new and cap-crossing production files, warns earlier, and leaves test files warn-only.

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
- **Never swallow errors**: every catch ends in one of ⛔ Hard Rule 10's endings; logging alone is not one.
- **Validate inputs early**: Guard at system boundaries (user input, external APIs). Fail fast with clear messages.
- **Use resource management patterns**: Context managers, try-with-resources, `using`, RAII (whatever the language provides).
- **When a method returning a collection finds nothing, return empty, not null**: Unless null carries distinct semantic meaning. A failure is never an empty collection (⛔ Hard Rule 10).

---

## 6. Code Clarity

- **Comments explain "why", not "what"**: The code itself should be readable enough to explain "what."
  The "why" is the why of the *code* (a constraint, an invariant, a non-obvious domain fact), never the
  why of the change you just made. Narrating the edit (the fix, the request, the old behavior) in a
  comment is banned outright: ⛔ Hard Rule 3.
- **Comment and doc prose follows `writing-style.md`**: the hard bans (em-dashes first among them) bind
  inside code comments, docstrings, and documentation exactly as they do in chat and PR prose.
- **No commented-out code**: Use version control for history.
- **Remove dead code you introduced**: If code you wrote becomes unused during the task, delete it. However, do not remove pre-existing dead code unrelated to your change; that increases diff scope. Instead, point it out to the user.
- **Document new code**: Add summaries/docstrings to new methods and classes so added code is properly documented. Each describes the unit itself, never its callers or the route it travels (⛔ Hard Rule 9).
- **Avoid magic numbers**: Extract to named constants.
- **Keep nesting shallow**: Use early returns and extraction to keep code flat.
- **Never reference separate documentation from code; explain inline instead**: Code comments, docstrings, READMEs, and summaries must never point at ADRs, design docs, wikis, planning docs, or tickets ("see ADR-012", "as described in the architecture document"). Those artifacts don't ship with the code and rot independently of it. When the reader needs that context, briefly explain the relevant decision or constraint in one or two sentences right there, in place of the pointer. "Right there" means the code that acts on the decision, never the summary of a type that code merely uses (⛔ Hard Rule 9). This applies to every artifact you write: source files, XML docs/docstrings, READMEs, and handoff summaries.

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
- **Credentials attach at client configuration**: never as call arguments and never in URLs (⛔ Hard Rule 11).

---

## 9. Version Control Hygiene

- **Minimal diffs**: Change only what is necessary. Avoid scope creep.
- **Never commit secrets**: .env, credentials, API keys stay out of version control.
- **Never run git write commands**: no `git commit`, and no staging either (`git add`, `git stash`),
  even to "snapshot a baseline". Leave the working tree exactly as your file edits made it; the user
  manages git and commits when ready. To inspect state, use the read-only git-ops MCP tools. The
  `block-vcs-writes` hook enforces this at the tool layer when installed; the rule binds regardless.
- **Version fields are release acts**: a change to a project version accompanies a release the user
  asked for, never ordinary feature or fix work, and never lands before the project's first release
  (⛔ Hard Rule 5).
- **Follow existing commit conventions**: Match the repo's style.

---

## 10. Handoff Discipline

Before delivering work:

1. Run the project's formatter and linters; fix all issues.
2. Walk the ⛔ Hard Rules block at the top of this file: the build/linter output shows zero new
   deprecation warnings on lines you touched, and the pre-write reuse search happened. Name any
   near-duplicate you deliberately did not reuse in the summary, with the reason. Confirm the diff
   touches no version field unless the task was a release the user asked for (Hard Rule 5). Any
   mechanism added for cases that don't exist yet gets named and justified in the summary, or
   removed (Hard Rule 6). Confirm nothing newly fetched was executed and no tool was installed
   mid-task without the user's explicit yes; a tool gap you hit goes in the summary with the
   suggested install command (Hard Rule 7). Name the skill files and knowledge files read for
   the task; if a language's code changed and its skill file isn't on that list, the handoff
   isn't ready (Hard Rule 8). Every summary the diff adds describes its own unit (Hard Rule 9).
   List each catch the diff adds with its ending and the test that drives it; an uncovered catch
   line blocks the handoff whatever the coverage percentage (Hard Rule 10). No credential sits in a
   call signature or a URL, and one that was exposed is flagged for rotation (Hard Rule 11). For
   each state value, flag, or persisted status write the diff adds, name its readers and how each
   handles it, the guard on each write and what its rejected path records, and, for state that
   gates access, every path that grants on it (Hard Rule 12). For each transition a message,
   webhook, or outbox relay drives, name its delivery guarantee (at least once or at most once,
   deduped or not) and the repeat that remains, such as a receiver that can't dedupe or a send
   that timed out after the receiver took it, and any receiver with no lookup for a parked row
   (Hard Rule 12). When the ask stated a reason, name
   the way chosen and the one rejected (`general-problem-solving.md` §2). Then reread every
   comment the diff adds or edits: any that narrates the change rather than the current code gets
   deleted here, its story moved to the summary (Hard Rule 3).
3. Ensure new code is covered by tests.
4. Run the test suite; confirm nothing is broken.
5. Summarize the change, its rationale, and any caveats or warnings.
6. Report which skill files and knowledge files were read and which tools were used; the list is
   the evidence that the routing in Hard Rule 8 happened.

## 11. Interacting with git
1. When interacting with git, use the specialized MCP (Read and apply the instructions here: `./git-readonly-operations.md`)
2. You are forbidden from using git commands that generate/persist changes, like `commit`, or `push`.

## 12. Shell & Tooling Hygiene

- **Never rewrite source files through a shell text pipeline** (piping file content through string
  replacement and writing it back). Shell string handling is encoding-lossy: Windows PowerShell 5.1
  reads BOM-less UTF-8 as ANSI and writes UTF-16, silently mojibaking every non-ASCII character in the
  file, not just the edited part. Use a real file-edit tool; bulk mechanical edits (multi-file replace,
  whitespace/line-ending normalization) go through the text-edit MCP per `./text-edit-operations.md`.
- **Never shell out for read-only text probing** (`grep`/`rg`, `find`, `cat`, `head`, `tail`,
  `Select-String`, `Get-Content` used to locate or inspect file content). Use the runtime's native
  file tools or the text-search MCP per `./text-search-operations.md`.
- **Run every command you publish in docs once before writing it down.** Shell quirks (PowerShell 5.1
  mangling native stderr on redirection, quoting differences between shells) make plausible-looking
  commands produce garbage. A documented command that was never executed is a guess.
- **Never fetch and run software to unblock yourself.** A tool that is missing or the wrong version
  mid-task is a blocker to report with the exact install command for the user, never something to
  fix by downloading a release or installer and executing it (⛔ Hard Rule 7).