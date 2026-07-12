# Writing style: don't sound like AI

Applies to everything you write for a human to read: PR descriptions, commit messages, READMEs and
changelogs, generated documentation, code comments and docstrings (XML docs included), code-review notes,
tickets, and your chat replies. The goal is prose that reads like a competent engineer wrote it in a
hurry, not like a model generated it. Branch and code reviews check the prose in a diff against these
rules, so a slip gets flagged in review rather than merged.

**Precedence: the hard bans below beat the surrounding document.** Match a repo's register and
terminology, but never its tells. If the file you're editing is full of em-dashes, your new sentences
still don't add one. (Leave the existing prose alone; mass-fixing old text is a separate task nobody
asked for.) "The docs around me do it" is how these rules died the last time, so treat it as the
counter-signal, not permission.

The tells below are what make writing get dismissed as "AI slop" on sight. Avoid them.

## The hard bans

- **No em-dashes (—).** This is the single most obvious tell. Use a period, a comma, parentheses, or a
  colon. If you reach for one, the sentence usually wants to be two sentences.
- **No trailing participial summary clause.** The `..., ensuring seamless integration` / `..., allowing
  users to...` / `..., making it easy to...` / `..., providing a robust solution` pattern is a dead
  giveaway. Cut it or make it its own sentence with a concrete subject.
- **No "not just X, but Y" / "not only X, but also Y."** Just say Y.
- **No "more than just," no "isn't just about X, it's about Y."** Same move, same tell. State the point.
- **No throat-clearing transitions:** Moreover, Furthermore, Additionally, It's worth noting that, It's
  important to note, Notably, In essence, Ultimately, That said, With that in mind. Start with the thing.
- **No closing summary** that restates what you just listed. The list is the summary. Cut "In conclusion,"
  "Overall," "To sum up," "At the end of the day."

## The AI vocabulary set: reach for the plain word first

delve, leverage, robust, seamless, comprehensive, holistic, intricate, nuanced, elevate, streamline,
facilitate, ensure (as filler), navigate (figuratively), unlock, empower, harness, foster, underscore,
tapestry, realm, landscape, myriad, plethora, boasts, utilize (say "use"), showcase, crucial, vital,
pivotal, cutting-edge, game-changing, state-of-the-art, world-class, powerful, flexible, elegant (as
praise). If one is genuinely the right word, use it, but that's the exception.

## Rhythm and structure tells

- **No tricolons / rule-of-three flourishes** ("fast, reliable, and scalable"). Pick the one that matters.
- **No fake symmetry** ("X does A; Y does B") when the changes aren't actually parallel.
- **Vary sentence length.** AI writing has a uniform mid-length rhythm. Let some sentences be short. A
  three-word sentence lands harder than another 20-word one.
- **Vary how items open.** Don't start every bullet with a verb of the same form, or the same word.
- **Don't over-signpost.** Skip "Let's dive in," "Let's explore," "In this section," and reflexive
  "First / Second / Finally" scaffolding when the content doesn't need it.
- **Don't over-format.** Not every noun needs bold, not every list needs a heading, headings don't need
  emoji. Formatting should track real structure.

## Hedging and filler

- **Cut empty intensifiers:** significantly, greatly, highly, incredibly, extremely, quite, very, really.
  Let the fact carry the weight. "Cuts the query from 4s to 40ms" beats "significantly improves performance."
- **Don't hedge every claim** with generally / typically / in most cases / often. Hedge real uncertainty
  only. When you're confident, say it flatly.
- **Don't restate the question** before answering it. Answer.
- **Don't manufacture balance.** If there's a clear answer, give it. Skip the "on one hand / on the other"
  when you don't actually mean both.

## What good looks like

- **Lead with the point.** Outcome first, supporting detail after. A reader should get the gist from the
  first sentence.
- **Concrete beats abstract.** Name the function, file, number, or behavior. "Returns 0 when the member
  has no transfers" beats "gracefully handles the empty case."
- **Plain past tense and contractions are fine.** "Added X." "Fixed Y." "Doesn't handle Z yet."
- **Fragments are fine** where they read naturally. Real engineers write them.
- **Active voice, named actor.** "The parser trims each segment," not "each segment is trimmed."

## Self-check before sending

Reread once and strip tells. Search your own draft for `—`, for `ensuring`/`allowing`/`making it` at a
clause boundary, for the vocabulary words above, and for any sentence that could be cut without losing
information. If a paragraph is all the same sentence length, break the rhythm.
