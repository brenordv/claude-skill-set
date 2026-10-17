# Skill authoring: writing rules that stick

How to write and maintain the instruction files in this repo so their rules survive contact with real
sessions. Distilled from three rounds of "the rule was written down and still got ignored" (the csharp
Hard Rules, the writing-style em-dash ban, then a test task that skipped the testing files because it
looked small). A rule stated once is not a rule enforced.

## The seven failure modes

Audit all seven whenever a rule "didn't stick"; usually more than one is present.

1. **Buried in a reference file** the agent only skims ("see style-guidelines.md for details"). The
   rule exists but never enters context.
2. **Outranked by "match the repo".** Any "respect existing patterns" directive legitimizes every
   violation the corpus already contains, because the corpus was usually written before the rule.
   Absolute rules must say explicitly that they beat repo conventions.
3. **Contradicted by the docs' own examples.** One sample using a banned library or pattern teaches
   more than the sentence banning it. A testing guide banned Moq while its `BuildSut` example used
   `.Object`; the writing-style file banned em-dashes while carrying them in its own headings.
4. **No verification hook.** Rules stated only as prose, never as an item-by-item walk at handoff and
   in the review skill, don't get checked.
5. **Never loaded at all.** "Read these N files at session start" gets triaged, so a rule living only
   in a startup-read file is absent exactly when output is generated.
6. **Gated by a size judgment.** A trigger phrased as "for non-trivial tasks", or left to the agent's
   sense of proportion, is skipped whenever the task looks small, and "small" gets decided before
   the rules that would say otherwise are read. A C# "add some tests" task went straight to the
   diff with neither the csharp skill nor `testing.md` loaded because it looked too small to route;
   the fixed dates and invented ids that followed were exactly what those files ban.
7. **Executed literally.** A rule that names its example mechanism ("inject `TimeProvider`") gets
   applied as an order over code that already met the intent another way. In the same incident the
   agent read the rule after the correction, reached for the named mechanism, and added an
   abstraction beside a `day` parameter the test could simply have passed.

Why these bite: agents weight concrete examples and nearby directives over distant prose, precedence
heuristics resolve conflicts against the absolute rule unless the hierarchy is explicit, a rule
outside the context window constrains nothing, and a rule whose trigger depends on a judgment the
agent makes before reading it gets skipped by that judgment.

## The structural fix (apply all four parts)

When adding a non-negotiable or repairing one that regressed:

1. **Hard Rules block**: put it in a ⛔ Hard Rules block at the top of the entry file the agent always
   reads for that domain, not only in a reference file.
2. **Precedence override**: state in the block that these rules beat repository conventions, and amend
   any "match the repo" or precedence list nearby to say so.
3. **Clean examples**: audit every example in the skill and its references for the banned pattern;
   purge counter-examples. Leave no sample demonstrating what the text forbids.
4. **Verification hooks**: add the rule to the skill's handoff self-check AND to the review side
   (`branch-review`, `review-heuristics.md`) so violations get caught twice.

For failure mode 5, one more move: mirror the one or two highest-signal bans into the config that is
always in context (CLAUDE.md), and keep the full rule file as the detail layer. Don't mirror
everything; the always-loaded file stays short or it stops being read too.

For failure mode 6, write triggers as topics, never proportions: "any task that adds or changes a
test reads `testing.md`", not "non-trivial tasks read the relevant files". Size picks the workflow
path; it never decides whether a domain's rules apply, and the rule should say so in those words.

For failure mode 7, state the intent first and mark the mechanism as one way to meet it, then name
the check that comes before it ("read the signature; if the instant is already a parameter, pass
it"). An example that could be mistaken for a mandate needs the sentence that says it isn't.

## Maintenance notes

- A "didn't stick" report is a structural bug, not a wording bug. Adding one more sentence to the same
  file has never fixed it.
- When restructuring a file that carries rules, preserve its existing safeguards (write-operation
  caveats, user-specific bans); a rewrite that drops one silently relaxes it.
- New guidance must pass its own bar: run the writing-style self-check and the machine-privacy
  self-check on skill prose before finalizing.
- When a vault lesson gets promoted into this repo, purge the lesson afterward and sweep for
  references to its name; a pointer to a purged lesson is a dead link the next reader can't follow.
  This file is the standing home of the principle; it carries everything the lesson did.
