# Skill authoring: writing rules that stick

How to write and maintain the instruction files in this repo so their rules survive contact with real
sessions. Distilled from two rounds of "the rule was written down and still got ignored" (the csharp
Hard Rules, then the writing-style em-dash ban). A rule stated once is not a rule enforced.

## The five failure modes

Audit all five whenever a rule "didn't stick"; usually more than one is present.

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

Why these bite: agents weight concrete examples and nearby directives over distant prose, precedence
heuristics resolve conflicts against the absolute rule unless the hierarchy is explicit, and a rule
outside the context window constrains nothing.

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
