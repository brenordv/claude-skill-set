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

## Security

- **Don't expose error details at API boundaries.** Return generic, human-safe messages; log the details
  server-side. Exception text and internal descriptions hand an attacker a map of the system.
- **No machine-identifying details in the diff.** Absolute local paths, drive-letter paths, UNC shares,
  OS usernames, hostnames. Use the `machine-privacy.md` self-check patterns and judge hits against its
  carve-outs. On touched lines this is Critical and blocks approval.

## Prose (comments, docs, and other human-facing text)

- **Run the diff's prose against the `writing-style.md` hard bans.** Concrete greps over added/modified
  lines: the em-dash character, `, ensuring` / `, allowing` / `, making it` clause tails, "not just X,
  but Y", throat-clearing transitions (Moreover, Furthermore, Additionally, It's worth noting), and the
  AI vocabulary set (delve, leverage, robust, seamless, comprehensive, and the rest of the list in
  `writing-style.md`). A hard-ban violation on a touched line is at minimum Important.
- **Softer tells are Suggestions.** Tricolon flourishes, uniform sentence rhythm, and over-formatting in
  new docs get flagged as Suggestions, not demands.

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
