# Scope Discipline

Concrete, checkable patterns for keeping planned work aimed at what was actually asked. These sit under
the review dimensions in `code-review.md` the way `review-heuristics.md` does, but at a different altitude:
`review-heuristics.md` asks whether the code is correct and clean; this file asks whether the work *should
exist at all* and whether there is *more of it than the ask justified*. The `delivery-lead` skill is the
primary reader. `system-architect` can run it as a self-check while drafting, and `branch-review` can apply
it to a finished diff.

The rule under all of it: measure against the original prompt, not the plan. The plan is one person's
interpretation of the ask, and interpretation is where scope quietly grows. Keep the user's own words as
the yardstick.

---

## The ground check

Before flagging anything, write the ask in one line: what did the user request, and what did they say
"done" looks like? Every item below is measured against that line. If a piece of the plan traces back to
nothing in it, that piece needs a reason to exist, and "while we're in here" is not one.

## Speculative generality (YAGNI)

Abstraction or flexibility built for a future the prompt never named.

- An interface, plugin point, strategy, or factory where one concrete implementation was asked for.
- Config knobs, feature flags, or parameters no requirement drives.
- "Make it generic / reusable / pluggable" when a single caller exists.
- Data models carrying fields for use cases not in the ask.

The fix is almost always the same: build the one case asked for, and record the extension point as a future
option instead of building it now.

## Gold-plating (over-delivery)

Work that runs past the acceptance criteria.

- Handling inputs the system will never receive.
- Error handling for conditions that cannot arise in the described flow.
- Refactoring or "improving" a path the ask did not touch.
- States, formats, or options nobody requested.

## Solving a problem we don't have

Effort spent on a problem the ask never raised, most often performance or scale.

- Performance work with no stated target and no evidence of a bottleneck.
- Caching, pooling, or batching something called rarely.
- Scale design (sharding, queues, horizontal anything) for load nobody projected.
- Retry, backoff, or circuit-breaker machinery around a call not shown to fail.

Premature optimization and premature resilience are one mistake in two hats: complexity added against a
hypothetical.

## Interpretation drift

The plan's deliverable is quietly bigger than the request.

- Nouns in the plan that never appear in the prompt: new endpoints, tables, services, screens.
- The plan solves a general category when the ask named one instance.
- "The user probably also wants..." reasoning with nothing in the ask behind it.

When drift is real, cut the plan back to the ask, or surface the added scope to the user as an explicit
decision. Don't smuggle it in.

## Panel-inflation drift

The plan grew because another review lens asked for more, not because the ask needed it. In a panel where
security, observability, and the language lens all pull toward adding, this is the common failure.

- A hardening, logging, or structural addition whose only justification is another lens's finding.
- Layers of requirement stacked on a feature the prompt mentioned in passing.

Resolve it with the tiebreak below: challenge the feature, not the addition.

## Rebuild versus reuse (at plan altitude)

The plan proposes building what the repo or its ecosystem already provides. `branch-review` catches this in
the diff; catching it in the plan is cheaper, before a line is written.

- A new helper, mapper, validator, or client for a capability the codebase already has.
- Re-implementing what an already-present library covers.

Search the repo for the capability before the plan commits to building it (`git_grep`, the text-search MCP,
or the native search tools; never shell grep).

## Wrong process altitude

The work is being handled at the wrong weight.

- A one-line, low-risk change routed through the full-work pipeline and accreting design it does not need.
  That is over-process; drop it to the lightweight path.
- Something touching data, security, or multiple systems pushed down the lightweight path. That is
  under-process; escalate per `task-workflows.md`.

---

## What is NOT scope creep

Scope discipline is not an excuse to cut corners. The following are in scope even when the user did not
spell them out, and flagging them as creep is the failure mode to avoid:

- Correctness and edge-case handling the described flow can actually hit.
- Security controls a feature genuinely requires: authn/authz, input validation, secret handling.
- Data-safety and integrity for data the feature touches.
- Tests for the code being written.
- The project's standing conventions and Hard Rules.

If cutting something would ship a real correctness, security, or data risk, it is not gold-plating. Leave it.

## The tiebreak

When a scope-cut collides with an additive lens, correctness, security, and data-safety outrank the cut.
Don't ship unsafe to stay lean. But the cut has one legal counter-move: challenge the *feature that
requires* the addition, not the addition itself. If the feature a hardening finding protects was never in
the ask, cutting the feature resolves both at once, and the hardening leaves with it. Settle the scope
question before a revision cycle is spent hardening something that should not exist.

## Severity

- **Blocking**: speculative complexity or unrequested scope that would ship real, lasting cost, such as a
  whole abstraction, service, or feature past the ask. The plan is trimmed before it proceeds.
- **Suggestion**: minor gold-plating or a small over-delivery, cheap to leave or trim. Note it; don't gate
  on it.
- **Deferred by design**: an extension point worth recording for the user as a future option, deliberately
  not built now.
