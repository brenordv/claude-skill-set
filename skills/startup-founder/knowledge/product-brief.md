# Product brief

Turn a one-sentence idea into a structured brief the founder can act on. When the idea has not
been validated at all, say so and point at `idea-validation.md`; the brief still gets written.

Input needed: the idea, ideally with target user and stage. Where input is missing, assume and
state the assumption inline.

## Sections

**1. Problem statement.** The specific pain this solves, who feels it most, and what those people
do about it today.

**2. Target audience.** 2-3 thumbnail personas with enough specificity to be falsifiable: not
"small business owners" but "solo SaaS founders under $10K MRR who spend 8+ hours a week on manual
competitor tracking". For full persona work, use `personas.md`.

**3. Value proposition.** One sentence that passes the "so what?" test, in the form:
"[Product] helps [audience] [achieve outcome] by [mechanism], unlike [alternative] which
[limitation]."

**4. Core MVP features.** Exactly 5-7 features. For each: name, one-line description, and why
launch fails without it ("nice to have" disqualifies it from this list). Deep triage belongs to
`mvp-scope.md`.

**5. Success metrics.** 3-5 measurable KPIs with numeric targets for the first 90 days, leading
indicators included, never revenue alone. The full framework lives in `metrics.md`; the brief
carries just the headline numbers.

**6. Risks and assumptions.** The top 3 assumptions that must hold for the product to work, each
with a way to test it for under $500 and inside 2 weeks.

**7. Go-to-market snapshot.** The first 3 channels to try, a rough CAC range per channel (labeled
as an estimate), and one growth idea specific to this product. The full plan belongs to
`go-to-market.md`.

## Rules

- Format as clean markdown with headers and short bullets; the brief is a working document, not
  an essay.
- Every number is either grounded in something the user said or flagged as an assumption.
