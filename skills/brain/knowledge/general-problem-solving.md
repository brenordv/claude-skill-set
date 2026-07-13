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

**If anything is unclear, ask the user before proceeding.**

---

## 2. Plan the Approach

Once the problem is understood:

- **Think through the solution**: Consider 2-3 approaches mentally. Choose the simplest one that fully solves the problem.
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
- **Use the right skill**: If the task involves a specific language/framework, use its dedicated skill.
- **Keep changes minimal**: Solve only what was asked. Resist scope creep.
- **Write tests alongside code**: Don't defer testing until the end.

---

## 4. Verify

After implementation:

- **Run tests**: Execute the project's test suite. Ensure nothing is broken.
- **Check against the plan**: Does the implementation match the testing plan from step 2?
- **Run formatters and linters**: Fix any style issues.
- **Review your own work**: Read through the changes. Does anything look wrong, fragile, or unclear?

---

## 5. Report

Before handing off to the user:

- **Summarize what was done**: Brief description of the changes and their purpose.
- **List skills used**: Report which skills contributed to the solution (e.g., "Used: python, security, system-architect").
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
| Code review after implementation | `python-code-review` (or equivalent) |

---

## Anti-Patterns

- **Jumping straight to code** without understanding the problem.
- **Over-planning** for a trivial task; match effort to complexity.
- **Ignoring existing patterns** in the codebase.
- **Not testing**: every change should be verifiable.
- **Silent completion**: always communicate what was done and any risks.
