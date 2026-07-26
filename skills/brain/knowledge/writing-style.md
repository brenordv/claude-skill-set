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

The tells below are what make writing get dismissed as "AI slop" on sight. Avoid them. Most are
documented with real examples in Wikipedia's field guide
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing); skim it when this
file feels abstract.

## The hard bans

- **No em-dashes (—).** This is the single most obvious tell. Use a period, a comma, parentheses, or a
  colon. If you reach for one, the sentence usually wants to be two sentences.
- **No trailing participial summary clause.** The `..., ensuring seamless integration` / `..., allowing
  users to...` / `..., making it easy to...` / `..., providing a robust solution` pattern is a dead
  giveaway. Cut it or make it its own sentence with a concrete subject.
- **No "not just X, but Y" / "not only X, but also Y."** Just say Y.
- **No "more than just," no "isn't just about X, it's about Y."** Same move, same tell. State the point.
- **No flat "not X, but Y" contrasts either.** "It's not a cache, it's a ledger"; "this isn't
  configuration, it's code." The strawman-then-reveal rhythm is a tell. Say what the thing is.
- **Don't dodge "is" and "has."** No "serves as," "stands as," "functions as," "acts as," "represents"
  where "is" would do; no "boasts," "features," "offers" where "has" would do; no "refers to" opening a
  definition. Studies measure a sharp post-2022 drop in plain "is"/"are"; it is one of the strongest
  documented AI signals. "The parser is the entry point," not "the parser serves as the entry point."
- **No significance inflation.** "Plays a crucial/key/vital role," "marks a significant shift," "a
  testament to," "underscores the importance of," "reflects broader trends," "sets the stage for." If
  something matters, give the fact that makes it matter; don't narrate its importance.
- **No throat-clearing transitions:** Moreover, Furthermore, Additionally, It's worth noting that, It's
  important to note, Notably, In essence, Ultimately, That said, With that in mind. Start with the thing.
- **No closing summary** that restates what you just listed. The list is the summary. Cut "In conclusion,"
  "Overall," "To sum up," "At the end of the day."

## The AI vocabulary set: reach for the plain word first

delve, leverage, robust, seamless, comprehensive, holistic, intricate, nuanced, elevate, streamline,
facilitate, ensure (as filler), enhance, navigate (figuratively), unlock, empower, harness, foster,
underscore, highlight (as a praise verb), tapestry, realm, landscape, myriad, plethora, boasts, utilize
(say "use"), showcase, crucial, vital, pivotal, key (as an adjective), meticulous, garner, bolster,
enduring, testament, interplay, vibrant, valuable (as filler praise), align with, cutting-edge,
game-changing, state-of-the-art, world-class, powerful, flexible, elegant (as praise). If one is
genuinely the right word, use it, but that's the exception.

Same family: stiff synonyms for plain verbs. Wrote, not authored; moved, not relocated; tried, not
attempted; died, not passed away. Plain verbs and plain is/has phrases are documented signs of *human*
writing; the stiff synonym is the tell.

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
- **Call the same thing by the same name.** Cycling synonyms for one concept ("the parser... the
  component... the module") is elegant variation, an AI tell driven by repetition penalties, and it's
  ambiguous in technical prose. Repeating the exact term is correct, not clumsy.
- **Plain bullets, sentence-case headings.** The `- **Label:** text` bullet list is the most
  recognizable AI formatting pattern; reserve it for items that genuinely have named parts. Write
  headings in sentence case ("Error handling"), not Title Case ("Error Handling").
- **No boilerplate "Challenges" or "Limitations and future work" scaffolding,** and no "Despite these
  challenges..." pivot back to optimism. If limitations matter, list them and stop.

## Hedging and filler

- **Cut empty intensifiers:** significantly, greatly, highly, incredibly, extremely, quite, very, really.
  Let the fact carry the weight. "Cuts the query from 4s to 40ms" beats "significantly improves performance."
- **Don't hedge every claim** with generally / typically / in most cases / often. Hedge real uncertainty
  only. When you're confident, say it flatly.
- **Don't restate the question** before answering it. Answer.
- **Don't manufacture balance.** If there's a clear answer, give it. Skip the "on one hand / on the other"
  when you don't actually mean both.
- **No vague authority.** "Widely considered best practice," "experts recommend," "industry standards
  suggest." Name the actual source, or make the claim in your own voice and own it.
- **Don't paper over unknowns.** "Details are limited" followed by "likely..." speculation is an AI
  signature. If you don't know, say you don't know and stop.

## Commit messages, PR descriptions, and summaries

The same tells show up compressed in commits, PR descriptions, and review write-ups; Wikipedia editors
spot AI edits from the edit summary alone. The equivalents here:

- **Name changes, not virtues.** "Split parse() into parseHeader() and parseBody()," not "improved
  clarity, flow, and readability." A summary that lists qualities instead of changes is the tell.
- **No compliance assurances.** "Ensured adherence to coding standards," "maintained consistency with
  the style guide." Cite a concrete rule only when it drove the change ("renamed per repo naming
  convention"); otherwise say nothing about compliance.
- **Don't inventory what you didn't touch.** The reflexive "...while preserving existing behavior" tail
  is a tell. Claim "no behavior change" only when that claim is the point of the commit and you verified
  it.
- **No chat voice in durable artifacts.** "I hope this helps," "let me know if," "would you like me
  to..." live in conversation only, never in a commit, PR, ticket, or doc.

## What good looks like

- **Lead with the point.** Outcome first, supporting detail after. A reader should get the gist from the
  first sentence.
- **Concrete beats abstract.** Name the function, file, number, or behavior. "Returns 0 when the member
  has no transfers" beats "gracefully handles the empty case." This is the principle behind every tell
  above: a model smooths rare, specific detail into statistically safe filler, so generic praise sitting
  where a specific fact should be reads as AI even when no banned word appears. Specificity is the one
  move no tell-list can flag.
- **Plain past tense and contractions are fine.** "Added X." "Fixed Y." "Doesn't handle Z yet."
- **Fragments are fine** where they read naturally. Real engineers write them.
- **Active voice, named actor.** "The parser trims each segment," not "each segment is trimmed."

## Self-check before sending

Reread once and strip tells. Search your own draft for `—`, for `ensuring`/`allowing`/`making it` at a
clause boundary, for `serves as`/`stands as`/`acts as`/`plays a`, for `not just` and `it's not`, for
`- **` label bullets, for `while preserving`, and for the vocabulary words above. Cut any sentence that
adds no information. If a paragraph is all the same sentence length, break the rhythm.
