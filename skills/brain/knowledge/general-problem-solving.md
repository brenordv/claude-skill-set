# General Problem-Solving Guideline

This guideline defines how AI should approach any coding or engineering task. Follow this process before starting implementation work.

---

## 1. Understand the Problem

Before touching any code:

- **Clarify the ask**: What exactly is the user requesting? If ambiguous, ask clarifying questions.
- **Identify the scope**: What files, modules, or systems are involved?
- **Understand the context**: Why is this being done? What business or technical problem does it solve?
- **Check constraints**: Are there performance targets, compatibility requirements, or deadlines?
- **Read before writing**: Review the relevant code, understand existing patterns, and identify dependencies.
- **Route before touching code**: name the skill for the language or framework the task touches and
  the knowledge file for its topic (`testing.md` for anything that adds or changes a test,
  `security.md` for auth or input handling, `database.md` for schema or queries), and read them now,
  before the first edit. Size doesn't gate this: "add some tests" routes to the language skill plus
  `testing.md` exactly as a feature would (`task-workflows.md` ⛔ Hard Rules item 5).

**If anything is unclear, ask the user before proceeding.**

---

## 2. Plan the Approach

Once the problem is understood:

- **Think through the solution**: Consider 2-3 approaches mentally. Choose the simplest one that fully solves the problem.
- **A stated reason is the acceptance criterion**: when the ask gives a reason ("for security", "to
  cut latency"), the reason decides which way of doing the named step counts as done. Compare the
  ways at the named step's footprint: the same component, no new service, infrastructure,
  dependency, or another team's surface. Keep the mechanism the user named and do it in its
  strongest form at that footprint. When costs are comparable, the way that serves the reason best
  wins, and for a security reason the weaker way at similar cost needs a stated justification. A
  stronger, different mechanism goes in the report as a follow-up, never substituted. Name the way
  chosen and the one rejected in the report. Example: asked to move a function key from the query
  string to the `x-functions-key` header for security, set the header once on the client
  registration rather than as a per-call header parameter, and tell the user to rotate the key,
  since its earlier calls carried it in URLs, which server logs capture.
- **Consider architecture**: For non-trivial tasks, consider calling the `system-architect` skill to get a design perspective, especially for:
  - New features that affect multiple systems
  - Changes to data models or APIs
  - Integration with external services
  - Scalability or performance concerns
- **Consider security**: For tasks involving user input, authentication, data access, or external APIs, consider calling the `security` skill to review the approach for vulnerabilities.
- **Identify what to test**: Before writing code, define:
  - What constitutes "working correctly" (acceptance criteria)
  - Which happy paths to verify
  - Which error paths to cover
  - Which edge cases matter
  - Which existing tests the change is expected to make stale, each with the behavior change that
    does it, or "none expected". Any other test that goes red later is a regression until
    diagnosed (`testing.md` ⛔ Hard Rule 2). The list is a prediction, not an allowlist: a test it
    missed can still be stale, on the same ground as the ones it named.
- **Break into steps**: Decompose the work into small, verifiable increments.

### Back external assumptions with an official source

Every claim your plan leans on about how an *external* technology behaves (a library's API or conventions, a framework's
defaults, a service's requirements, limits, or performance characteristics) must be backed by a link to that 
technology's **official, version-current documentation**. Both of these need a citation before they go in a plan:

- "React Query's `useMutation` has built-in conventions around X."
- "We send X and Y from the frontend because Azure Cosmos needs them to query this efficiently."

- **Official only.** Vendor or project docs, the API reference, the source repository, or a formal spec. Not blog posts, forum answers, or a model's own recollection.
- **Verify, never fabricate.** Actually open the page (`WebFetch`/`WebSearch`) and confirm it resolves *and* states what you claim. A plausible-looking URL you did not read is worse than no citation: a hallucinated source turns a guess into a false certainty.
- **Version-current.** The doc must match the version in play; if the project pins an older version whose behavior differs, cite that version and call out the difference.
- **Internal behavior is the exception.** Claims about *this* codebase are backed by reading the actual code, not a URL. The link rule is for third-party and external systems.

If you cannot find an official source for an assumption, say so and mark it unverified rather than presenting it as fact.

---

## 3. Execute

With a plan in hand:

- **Work incrementally**: Complete one step at a time. Verify each step before moving to the next.
- **Follow the knowledge guidelines**: Apply the relevant shared knowledge (coding-general, testing, security, etc.).
- **Use the right skill**: the language or framework skill was read in §1, before the first edit;
  apply it throughout, including the reference file it names for the work (`testing-guidelines.md`
  for tests). Consulting it after a correction is not the same as having loaded it.
- **A guideline's example is not an order**: when a rule names a mechanism (`TimeProvider` for code
  that reads the clock), check what the code already offers first. If the method already takes the
  value as a parameter, pass the parameter; adding the named mechanism beside it is the oversized
  mechanism `coding-general.md` ⛔ Hard Rule 6 bans.
- **Keep changes minimal**: Solve only what was asked. Resist scope creep. Minimal governs what you
  touch outside the goal, never how well a stated goal is met (§2).
- **Write tests alongside code**: Don't defer testing until the end.

### A deliberate change is the source of truth

When the user changes behavior on purpose, or the plan alters it by design, that change is the source of truth for the rest of the task. Whatever contradicts it is now stale and conforms to it, not the reverse.

- **Never revert or weaken a deliberate change to make a test pass.** A test asserting the old behavior went stale the moment the behavior changed by design. Update it to assert the new behavior, or delete it when that behavior is gone. Rolling back the change, relaxing a validation, or loosening production code to turn a test green throws away the intent the user just expressed. A red test that asserts exactly the behavior the user changed means the test is wrong, not the code. That holds only for that test: see "A red test is evidence until diagnosed" below.
- **Old, legacy, or ported code is precedent, not an oracle.** "The previous version accepted null here" or "this diverges from the API we ported" does not override a change made on purpose. Don't argue that a deliberate change will break in production by diffing it against the code it was written to replace. The user changed it knowingly.
- **Keep the blast radius exact.** Tightening one field's validation must not relax, or even touch, the validation on any other field. A change that makes one property stricter must never make an unrelated property more lenient. Fix what the change targets, nothing around it.
- **If a failing test looks like it caught a real regression** the change did not intend, fix the regression, or raise it with the user when the fix isn't clear. Don't silently revert, and don't delete a test that might be flagging a genuine bug.

### A red test is evidence until diagnosed

The rule above has a mirror, and it guards the tests. An agent under pressure to finish will call
any test in its way "stale", then delete it, skip it, or loosen its assertion until the suite is
green. That is the same defect as weakening production code, pointed the other way.

- **"Stale" needs a ground.** A test is stale only when you can quote the sentence that changed
  the behavior it asserts: one the user wrote, or a plan sentence that names the change and
  traces to the ask. No quote, no stale test.
- **Diagnose before touching.** Every red test gets one of four dispositions (the code is wrong,
  stale, defective, not caused by this change), each with its ground. The full rule is
  `testing.md` ⛔ Hard Rule 2.
- **Run the suite before the first edit.** That baseline is the only evidence for "it was already
  failing".
- **Every change to an existing test is recorded** in the test-change ledger as it happens
  (`testing.md` ⛔ Hard Rule 3), and the review rebuilds that list from the diff.
- **Red is a legal ending.** When a test can't be made green without weakening it, stop and
  report it red, by name, with what you tried. Green by any route is never the goal.

---

## 4. Verify

After implementation:

- **Run tests**: Execute the project's test suite, with the same command as the baseline run. A test that fails only because it asserts behavior this change intentionally altered is a stale test to update, not a reason to undo the change (see §3, "A deliberate change is the source of truth"). Any other red test is evidence to diagnose, never something to delete, skip, or loosen (see §3, "A red test is evidence until diagnosed").
- **Check against the plan**: Does the implementation match the testing plan from step 2?
- **Run formatters and linters**: Fix any style issues.
- **Review your own work**: Read through the changes. Does anything look wrong, fragile, or unclear?

---

## 5. Report

Before handing off to the user:

- **Summarize what was done**: Brief description of the changes and their purpose.
- **List skills and knowledge files used**: Report the skill files and knowledge files actually read for the task (e.g., "Used: csharp (SKILL.md, testing-guidelines.md), brain/knowledge/testing.md, security"). Code written in a language whose skill is missing from this list is the gap it looks like.
- **Report test changes**: The test-change ledger, or `Test changes: none`, with the baseline and final test figures (`testing.md` ⛔ Hard Rule 3). Every test still red is named.
- **Report caveats**: Any limitations, trade-offs, assumptions, or potential issues the user should be aware of.
- **Suggest follow-ups**: If there's related work that was out of scope but worth considering.

---

## When to Call Other Skills

| Situation | Skill to Consult |
|-----------|-----------------|
| New feature affecting architecture | `system-architect` |
| Security-sensitive changes | `security` |
| Database schema changes | Relevant database skill |
| Game feature design | `game-developer` |
| Code review after implementation | `branch-review` |

---

## Anti-Patterns

- **Jumping straight to code** without understanding the problem.
- **Skipping the language skill or a topical knowledge file** because the task looked small, then
  filling the gap with habit.
- **Applying a guideline's named mechanism literally** to code that already meets the rule's intent
  through a parameter or an existing hook.
- **Over-planning** for a trivial task; match planning effort to complexity. Checking is not
  planning: the verify gate and the diff's review run whatever the task's size
  (`task-workflows.md`, "The diff decides whether a review runs").
- **Ignoring existing patterns** in the codebase.
- **Not testing**: every change should be verifiable.
- **Silent completion**: always communicate what was done and any risks.
- **Reverting or weakening a deliberate change** to satisfy a stale test, instead of updating the test.
- **Deleting, skipping, or loosening a red test** to get a green suite, or calling it stale with no
  sentence from the user to quote.
