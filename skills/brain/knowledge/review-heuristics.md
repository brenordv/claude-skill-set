# Review Heuristics

Concrete, checkable patterns to look for when reviewing or writing code. These sit under the dimensions in
`code-review.md` §2 and give them teeth. Language-agnostic unless noted; the C# examples illustrate a
general principle. Distilled from real review findings.

---

## Infrastructure & Configuration

- **Verify external resource names against the target system.** When a script or config references a
  secret, key vault entry, connection string, or env var by name, confirm the exact name exists. Similar
  names (`PRODUCT-ENGINE-...` vs `PRODUCTS-ENGINE-...`) coexist silently and read the wrong value. Flag any
  read from an external store with no evidence the key name was verified, and remove stale alternatives.
- **A tag-derived version pasted into a package manifest breaks on the `v` prefix.** Debian's
  `Version:` field must start with a digit (RPM's too, and RPM also forbids `-`), while release tags
  conventionally carry `v` (`v2.4.2`). Flag any workflow where all three hold: it builds a `.deb`/`.rpm`
  (calls `dpkg-deb`, writes `DEBIAN/control`, or has a `Version:` line in a heredoc); the version comes
  from `GITHUB_REF`, `github.ref_name`, or `git describe`; and nothing strips the prefix (`${TAG#v}` or
  equivalent, a no-op when the prefix is absent). Such a workflow passes every dry run and fails the
  first real release. Prefer sourcing the version from the package manifest over the tag; the manifest
  is already digit-first.

## Security

- **Don't expose error details at API boundaries.** Return generic, human-safe messages; log the details
  server-side. Exception text and internal descriptions hand an attacker a map of the system.
- **No machine-identifying details in the diff.** Absolute local paths, drive-letter paths, UNC shares,
  OS usernames, hostnames. Use the `machine-privacy.md` self-check patterns and judge hits against its
  carve-outs. On touched lines this is Critical and blocks approval.

## Prose (comments, docs, and other human-facing text)

- **A comment that narrates the change instead of describing the code is a finding.** Tells on
  added/modified comment lines: "fixed", "changed to", "now handles", "no longer", "previously",
  "was returning", "per the request/ticket/review", "to address", "as requested", "updated to". A
  valid comment states a constraint, invariant, or domain fact of the current code and would still
  make sense to a reader who never saw the old version or the task
  (`coding-general.md` ⛔ Hard Rule 3). At minimum Important on touched lines; the change story
  belongs in the commit message or PR text, not the source.
- **Run the diff's prose against the `writing-style.md` hard bans.** Concrete greps over added/modified
  lines: the em-dash character, `, ensuring` / `, allowing` / `, making it` clause tails, "not just X,
  but Y" and flat "not X, but Y" contrasts, copula dodges (`serves as`, `stands as`, `functions as`,
  `acts as`), significance inflation (`plays a crucial role`, `a testament to`, `underscores the`),
  throat-clearing transitions (Moreover, Furthermore, Additionally, It's worth noting), and the
  AI vocabulary set (delve, leverage, robust, seamless, comprehensive, and the rest of the list in
  `writing-style.md`). A hard-ban violation on a touched line is at minimum Important.
- **Commit messages and PR text get the summary-specific checks.** Virtue summaries ("improved clarity
  and readability"), compliance assurances ("ensured adherence to standards"), reflexive "while
  preserving existing behavior" tails, and chat voice ("I hope this helps," "let me know if") per
  `writing-style.md` §Commit messages.
- **Softer tells are Suggestions.** Tricolon flourishes, uniform sentence rhythm, synonym-cycling for one
  concept, `- **Label:** text` bullet lists, and over-formatting in new docs get flagged as Suggestions,
  not demands.

## API Design & HTTP Semantics

- **Use semantically correct status codes.** `408`/`504` for timeouts (client vs upstream), `502` when an
  upstream API errored, `204` for success-with-no-content. Returning `200` for an empty result or `500`
  for a known timeout conflates failure modes and stops clients reacting correctly.

## Observability

- **Attach correlation identifiers to logs.** Request ID, client/user ID, trace/correlation ID. Log lines
  without them can't be reconstructed across services in production.
- **Make log messages specific; don't log invariants.** `"Draw failed"` says nothing; `"Fortune wheel
  reward already used for {IndividualClientId}"` names the condition. And if a structured parameter is
  always the same value (it sits inside an `if` that already pins it), drop it or inline the literal.

## Maintainability

- **Logic added that already exists elsewhere in the repo is a finding.** Before approving a new
  helper, mapper, validator, or utility, search the repo for its distinctive tokens (`git_grep`,
  the native search tools, or text-search; never shell grep): name fragments,
  domain terms, a characteristic constant or format string. A near-duplicate the diff didn't reuse is
  at minimum Important, unless the handoff names it and justifies the divergence
  (`coding-general.md` ⛔ Hard Rule 1).
- **Extract reusable, dependency-free logic into an independently testable unit.** When a private method
  operates purely on its parameters (no services, no side effects) and the logic could be needed elsewhere,
  pull it out (in C#, an extension method on the parameter's type). It becomes testable without
  constructing the parent class and keeps handlers focused on orchestration.
- **Extract complex inline logic into a named method.** Multi-step pagination, filter assembly, and the
  like read better behind a descriptive name than inline. The caller reads as a narrative.
- **Avoid reflection for data mapping or filtering.** It hides the mapping rules from the call site. If
  unavoidable, isolate it in a documented, tested helper and verify the reflected property set is what you
  intend (`GetProperties()` returns all properties, not just serialization-annotated ones).
- **Opaque cross-references in comments are noise.** `// see §1.1`, `// per producer guide §3` require a
  document the reader may never find. State the reasoning inline in plain language.
- **Keep comments and docs in sync with the code.** A doc that says `body[surveyId]` while the parser
  splits on `:` creates an invisible rule that breaks silently. Flag any divergence between a documented
  contract and actual logic.

## Correctness

- **An added call to a deprecated or obsolete API is at minimum Important.** Judge against the
  version the project pins, not the latest release: deprecated means deprecated in the version
  actually in use. Build and linter output is the cheap detector; check it for deprecation warnings
  attributable to the diff, and flag any the author scrolled past
  (`coding-general.md` ⛔ Hard Rule 2).
- **A change reverted or weakened to pass a test is a defect, not a fix.** If the diff loosens a
  validation, reintroduces a useless default, or rolls back a deliberate tightening so an existing test
  goes green, flag it: the stale test should have been updated, not the production code weakened. Also
  flag a validation relaxation that leaked past its target onto unrelated fields.
- **Preserve null guards when extracting a method.** Inline code often inherits a null check from its
  surroundings; the extracted method receives the raw parameter and loses that guarantee. Guard at the top
  or document that the caller is responsible.
- **No `catch` that only rethrows.** `catch (X) { throw; }` is behaviourally identical to no catch; the
  comment inside is stripped at compile time. Put intent in a comment above the `try`.
- **Never rely on implicit ordering from an external API.** `FirstOrDefault()` on an upstream list assumes
  a sort order that's never contractually guaranteed. Request an explicit sort, or sort yourself before
  selecting, and document which ordering the logic depends on.
- **Guard every nullable step in a chain.** In `obj?.Prop1.Prop2`, if `Prop1` is non-null but `Prop2` is
  null, it still throws. `?.` only short-circuits on the receiver it's attached to. Each nullable hop needs
  its own guard.
- **Decide partial-failure semantics before writing a "fetch all pages" loop.** An exception mid-loop
  discards everything accumulated so far. Choose explicitly: is a partial result acceptable (catch and
  handle per page) or must the whole operation fail atomically? Document it.
- **Prefer total-count termination for paginated loops.** `lastPageCount == pageSize` over-fetches when the
  last page is exactly full and assumes a stable page size. If the API returns a total, loop on
  `fetched < total`.
- **Short-circuit before iterating an empty or null collection.** If a filter/list/map is empty or null,
  skip the loop and make the no-op explicit.
- **Make string case-sensitivity explicit.** Decide consciously per comparison and make it visible (a
  `StringComparison` argument, or explicit normalization). Implicit ordinal comparison is often unintended.
- **Trim segments when parsing external or user input.** Stray leading/trailing whitespace is a common
  source of silent mismatches.
- **Prefer split-and-check-length over `IndexOf`-plus-substring for delimited parsing.** `key.Split(':')`
  gives a clearly sized array. If the delimiter can appear in the value, design the format to be
  unambiguous (split on the first occurrence, or pick another delimiter).

## Testing

- **Don't test framework or DI wiring.** A test that resolves `IFooService` from the container tests the
  framework, not your code; a missing registration already fails at startup. Reserve tests for your logic.
- **New endpoints need HTTP-layer tests.** A new action must ship with tests covering routing,
  authorization, response shape, and error handling in the same change, not only service-layer tests.
- **Sibling tests for the same scenario must assert consistently.** If two tests cover equivalent states,
  they should check the same things unless the difference is intentional and documented. Asymmetric
  assertions silently under-test one branch.
- **A local spelling out a type the compiler could infer is a finding (C#: at minimum Important).**
  The recurring case is the deferred-action local: `Func<Task> act = () => ...` where
  `var act = () => ...` compiles (C# 10+ natural delegate types). csharp Hard Rule 13; the repo
  already writing explicit types is precedent, not permission.
- **A hard-coded calendar date in arrangement data is a finding.** `new DateTime(2024, 1, 15)` where
  the scenario is really "recent" or "expired" rots as real time passes and silently changes what the
  test covers. Expect clock-relative values (`DateTime.UtcNow.AddDays(-30)` or the language's
  equivalent) or an injected fake clock; accept a fixed literal only when that exact value is the
  behavior under test, and it's extracted to a field whose name says so (csharp Hard Rule 14; the
  principle is language-agnostic).

## Architecture

- **Defensive normalization for a downstream consumer belongs in the consumer.** If a transformation has no
  effect on the producer's own logic and exists only to keep a downstream service working, that service
  should own it. Producer-side workarounds create invisible cross-service coupling. Keep it only if the
  producer benefits too, and document why.
- **Don't leak other services' internals into code or comments.** Comments describing how a downstream
  system deduplicates, what envelope a receiver expects, or another service's terminology go stale and
  confuse anyone reading the producer alone. Describe *what you send*, not *why the receiver needs it*.
- **Adapter/facade layers translate upstream models to domain models.** A wrapper over an external API is
  an anti-corruption layer; its public interface exposes domain types, not the vendor's. Leaking
  `ThirdPartyProviderXxx` types ties every caller to the upstream schema. Map at the boundary.
