# Cross-Project Lessons (vault)

A persistent, cross-project knowledge base lives in the `vault` MCP server under the **pinned namespace `project: "lessons"`**.
Always pass `project: "lessons"` explicitly on every lesson read and write; never let it default to the working-directory namespace, or lessons get siloed per-project and defeat the purpose.

## Before planning: ALWAYS read first

Before producing any plan, strategy, design, or architectural decision, query the vault for relevant prior lessons:

1. `vault_list` with `project: "lessons"` and either a `query` (keywords from the task) or concept `tags`. Pull the topic, not the tech: for a Python test task, search `tags: ["testing"]`, not `["pytest"]`.
2. **Triage on summaries first.** `vault_list` returns names, summaries, and `parent` links; scan those and only `vault_get` the handful that look directly applicable. Don't fetch everything that matched.
3. **Follow the hierarchy when you land on one.** `vault_get` returns the note's `parent` and active `children`. A child may be the tech-specific application you actually need; a parent may state the general principle a child is just one instance of. Read the family, not just the node.
4. Factor relevant lessons into the plan.

Do the lookup silently. **Disclose any lesson that materially shaped your answer**: changed the approach, ruled out an option, or contradicted what you would otherwise have done. "Materially" is the test, not "when convenient."

**If a lesson conflicts with what you were about to do:**

- In the common case, follow the lesson and say so.
- If you genuinely believe the lesson is outdated or wrong given current information, surface the conflict to the user and propose an update. Never silently ignore a lesson; never blindly follow one you have specific reason to doubt.

## When to write: capture lessons automatically

Save a lesson, without being asked, whenever:

- The user **corrects** you (a wrong assumption, a rejected approach, a "no, do it this way").
- You hit a **gotcha** that cost real time and would recur on other projects.
- The user states a **durable preference** about how they want work done.
- You discover a **non-obvious principle** worth reusing elsewhere.

**Filter test (a lesson must pass both):**

1. **Durable.** Would still apply six months from now on a different project.
2. **Non-obvious.** A competent practitioner wouldn't already do this by default.

If it fails either, skip the save. A correction like "use 4 spaces" is real but fails non-obviousness; a one-off project quirk is real but fails durability.

Do NOT save: project-specific trivia already recorded in that repo's code, `CLAUDE.md`, or git history, or one-off facts that only matter to the current conversation.

Before saving, `vault_list project: "lessons"` and check for an existing lesson on the same idea. Pick the right write based on what's actually changing:

- **Metadata only: the summary or tags need to be sharper, or the parent link needs to change.** Use `vault_set_meta`. No `content` resend, no new version. This is the cheap way to keep discovery working as you learn what surfaces well in retrieval. Use it freely.
- **Body change confined to one heading's section.** Use `vault_edit_section` with that heading: it replaces just that section as a new version and leaves the rest byte-for-byte intact. Cheaper and safer than resending the whole body.
- **Body changes across the note (new insight, clarified Why/How, corrected Origin).** Read `current_version`, then `vault_save` with that `base_version`, restating `format: markdown` and the summary (save replaces both). On a `conflict`, the error carries the current version and a diff of what changed underneath you; fold that in instead of overwriting it.
- **Related but distinct: a tech-specific application of an existing general lesson.** Save it as a **child** of the general lesson by passing `parent: "<general-lesson-name>"` on `vault_save`. Don't duplicate the principle; let the child carry the specifics and the parent stay general.

## How to write: generalize, then tag for retrieval

**State the lesson at the most general level that's still true.** Put the principle in the summary and body; relegate tech-specific origin and application to a **child** note. A lesson learned via xUnit about test isolation is a *testing* lesson, not a C# lesson.

If a lesson is genuinely tech-specific and generalizing it would require mental gymnastics that make little sense, **keep the content specific but still tag a concept**. An Azure Functions cold-start workaround stays Azure-specific in its body, but tags as `performance` + `azure`, never `azure` alone. The content can be specific; the tagging must always include a concept layer so the lesson is discoverable cross-stack.

### Splitting with parent/child

When a lesson grows past one principle, split rather than stuff. The server nudges you here too: a write
result carrying a `hint` field means the note crossed the size threshold. Treat that as the trigger for
this section, not as noise to ignore.

Split like this:

- The **parent** carries the general, language-agnostic principle (`name: lesson-<concept-slug>`).
- Each **child** carries one tech-specific application or origin (`name: lesson-<concept>-<stack>`), linked via `parent` at save time.

This works because `vault_get` returns both directions of the link, so reading either end surfaces the rest. Keep parents lean: if the parent's body would just enumerate the children, let the children speak for themselves and keep the parent to the principle.

To retro-link an existing top-level lesson under a new parent, use `vault_set_meta` with `parent: "<name>"`: no rewrite, no new version. To detach, pass `clear_parent: true`. Self-links and cycles are rejected. Purging a parent orphans its children (they become top-level) rather than cascading, so reorganizing is safe.

### Fields

- **name**: `lesson-<kebab-slug>` (e.g. `lesson-test-isolation-shared-state`)
- **summary**: one line, language-agnostic statement of the principle.
- **format**: `markdown`
- **parent** (optional): name of a more-general lesson this one specializes.
- **content** template:

```
## Lesson
<the general principle, phrased so it transfers across languages/stacks>

**Why:** <the reasoning, so future-you can judge when it applies>
**How to apply:** <concrete actionable guidance>
**Origin:** <what happened (the correction/gotcha) and on which stack>
```

### Tagging convention (layered, never tag-lock)

Apply tags in three layers; **always include layers 1 and 2**, add layer 3 only as extra:

1. **Kind** (always): one of `correction`, `gotcha`, `preference`, `principle`, `workflow`.
2. **Concept** (always, language-agnostic): the transferable topic: `testing`, `error-handling`, `concurrency`, `api-design`, `security`, `performance`, `logging`, `git`, `naming`, `dependency-mgmt`, `data-modeling`, `ci`.
3. **Tech** (optional, additive): `rust`, `csharp`, `python`, `xunit`, `azure`, etc.; only ever *in addition* to a concept tag, never as the sole handle.

Rule of thumb: if the only tag that fits is a tech tag, you haven't identified the concept yet: the concept exists, find it.

When retrieval fails to surface a lesson you know exists, the tags or summary are the bug; fix them with `vault_set_meta` immediately. No new version, no friction; treat discovery hygiene as cheap.

### Example of a well-formed lesson family

Parent (general principle):

```
name: lesson-test-isolation-shared-state
summary: Tests that share mutable global state can't run in parallel and produce flaky failures under load.
tags: [gotcha, testing, concurrency]
content:
## Lesson
When test cases share mutable global state (singletons, static caches, env vars,
fixed on-disk paths), they cannot reliably run in parallel; failures often surface
as intermittent timeouts or order-dependent assertions.

**Why:** Parallel runners assume per-test independence; shared mutable state breaks
that assumption invisibly until concurrency goes up.
**How to apply:** Default new tests to no shared mutable state; for unavoidable
shared resources, gate with a per-test fixture or mark the suite serial.
```

Child (xUnit-specific application, linked via `parent`):

```
name: lesson-test-isolation-shared-state-xunit
parent: lesson-test-isolation-shared-state
summary: In xUnit, group classes that share state under one [Collection] to force serial execution.
tags: [gotcha, testing, concurrency, xunit]
content:
## Lesson
xUnit runs test classes in parallel by default but tests within one class serially.
Group classes that touch the same mutable resource under [Collection("Name")];
that collection runs serially even if other collections run in parallel.

**Why:** The default parallelism is per-class; without a Collection, two classes
touching the same static cache race.
**How to apply:** Co-locate classes sharing a resource under one [Collection]; for
truly isolated tests, leave the default and assert no statics are mutated.
**Origin:** Intermittent CI failures on project X: a static cache mutated by two
test classes flaked only under the parallel runner.
```

The pattern: the parent states the principle generally and is discoverable from any stack; the child gives the concrete recipe for one stack and inherits discoverability via the link. Tech tags appear only on the child.