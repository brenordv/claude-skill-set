---
name: visual-design
description: >-
  High-end visual design for web pages, UIs, and artifacts: premium / luxury /
  Apple-like aesthetics, design tokens, typography, color, layout, motion design,
  microinteractions, glassmorphism, landing pages and hero sections, plus preset
  font-and-color themes for slide decks, documents, reports, and dashboards. Use
  PROACTIVELY whenever the user asks for styling, theming, branding, color
  palettes, font pairings, a "premium"/"high-end"/"Apple-like" look, a landing or
  product page, animation polish, or wants an artifact to "look better" or "more
  professional", even without the words "design" or "theme". For charts and
  data-visualization color semantics, defer to the dataviz skill.
---

# Visual Design

> **Shared knowledge**: builds on `brain/knowledge/general-problem-solving.md` and
> `brain/knowledge/writing-style.md` for any prose it produces.

Design guidance that separates crafted work from template output. The core test, from
Apple's playbook: premium = restraint + intention + craft. Every pixel, animation, and color
is a deliberate choice you can defend; nothing is accidental and nothing is a default.

## When to use

- Building or restyling a web page, landing page, or app UI that should read as premium,
  luxury, high-end, or Apple-like.
- Motion design: microinteractions, gestures, transitions, scroll reveals, animation polish.
- Reviewing an interface for visual quality and proposing improvements.
- Theming an artifact (deck, document, report, HTML page) with a preset or custom theme.

Boundaries: charts, graphs, and dashboard data-viz semantics belong to the runtime `dataviz`
skill; this skill covers the page and chrome around them. Component architecture and code
correctness belong to the framework skills (`reactjs`, `nextjs`, `angular`); this skill owns
look, feel, motion, and theming, and they co-load cleanly. For claude.ai artifacts, the
runtime `artifact-design` skill calibrates how much design investment a request warrants;
this skill supplies the design system when that investment is warranted.

## Routing

| Task | Read |
|------|------|
| Any build work (always first) | `references/design-tokens.md` |
| Animation, gestures, transitions, scroll effects | `references/motion.md` |
| Apple-like app UI or apple.com-style marketing page | `references/apple-style.md` |
| Page composition: heroes, sections, layout, copy on the page | `references/page-design.md` |
| Quick artifact theming with preset themes | `references/artifact-theming.md` |

Mixed requests combine: an Apple-like landing page reads design-tokens + apple-style +
motion; a premium SaaS page reads design-tokens + page-design + motion.

## Decision priority stack

Apply to every design decision, in order:

1. Does it reduce cognitive load? Remove anything that adds complexity without value.
2. Does it guide the user? Every element directs attention intentionally.
3. Does it feel crafted? No defaults, no template aesthetics, nothing generic.
4. Does it perform? LCP within 2.5s, 60fps motion, no jank.
5. Is it accessible? WCAG 2.1 AA minimum, keyboard navigable.

A conflict resolves upward: accessibility and performance are floors, not trade-offs.

## ⛔ Hard Rules

These bind whenever this skill is active and beat any repository convention, existing
stylesheet pattern, or example found in the project being styled.

1. **Never animate layout-triggering properties** (`top`/`left`/`width`/`height`/
   `margin`/`padding`), and never continuously animate `filter` or `box-shadow`. Composited
   `transform` and `opacity` carry motion; `clip-path` and short discrete filter transitions
   (a blur crossfade, a glass materialize) are fine, continuous filter animation is not.
2. **Never the default `linear` keyword on state transitions** (enter/exit/hover/press).
   Linear is correct only for constant motion (marquees, spinners), hold or scrub progress
   where the gesture or timer supplies the pacing, and `linear()` spring approximations.
3. **`backdrop-filter` only on chrome and overlay layers** (fixed or sticky bars, modals,
   popovers, menus) plus sparing in-flow glass accents. Never on scrolling containers or
   large content areas, and never animate blur radius outside a brief enter/exit
   materialize.
4. **`prefers-reduced-motion` is honored in everything shipped**, and reveal-on-scroll
   content must be visible when JavaScript never runs: the hidden state is applied by
   script, not `opacity: 0` in the base stylesheet.
5. **Never lazy-load the LCP image; never scroll-jack native scrolling.**
6. **WCAG 2.1 AA contrast minimum**: 4.5:1 body text, 3:1 large text, on every surface
   including translucent ones.
7. **No AI-tell defaults**: no purple/indigo accents or purple-blue mesh/aurora gradients
   unless purple is genuinely the brand, no uniform border radius on everything, no "three
   of everything" symmetry, no identical font pairing across unrelated projects.
8. **No external font, CDN, or script hosts in artifact output** (the artifact CSP blocks
   them anyway). In project code, fonts are system-stack or self-hosted with a verified
   license, and motion libraries arrive via the package manager with pinned versions.

## Build workflow

1. **Direction first.** Identify the project's genre and personality, then pick the font
   pairing and palette from `references/design-tokens.md`. Never the same combination as the
   last project. Decide light/dark and the one accent.
2. **Structure.** Choose a hero variant and layout archetype (`references/page-design.md`),
   set the section rhythm (alternating tones, breathing sections), and lay out on the 8px
   grid with premium whitespace.
3. **Componentry.** Cards, buttons, and chrome follow the component patterns (double-bezel
   nesting, island buttons, hairlines over borders; or the Apple component-feel rules when
   the direction is Apple).
4. **Motion last, purposefully.** Gate every animation through `references/motion.md`
   (should it animate at all, then the cheapest tool), wire press states and reveals, and
   apply the reduced-motion handling.
5. **Verify** against the checklist below before handing off.

## Review mode

When asked to critique an interface: judge it against the Hard Rules, the decision stack,
and the banned-defaults list in `references/page-design.md`. Report the highest-impact
problems first (typically: typography defaults, missing hierarchy, uniform AI-tell styling,
janky or purposeless motion), each with the concrete fix, and offer to implement.

## Verification checklist

Before declaring design work complete:

- [ ] First viewport communicates quality instantly: clear focal point, professional
      typography, generous whitespace, one primary CTA.
- [ ] Hero uses a deliberate variant, not centered-text-over-gradient.
- [ ] Max 2-3 fonts, genre-appropriate pairing; fluid type scale; tracking tightens on
      large text.
- [ ] Colors follow 60-30-10 with 2-3 core colors; neutrals carry a slight warm or cool
      bias; contrast passes AA.
- [ ] Spacing sits on the 8px grid; section rhythm alternates; dense sections get breathing
      room.
- [ ] No animated layout properties, no continuous filter/box-shadow animation (Hard
      Rule 1); no default `linear` on state transitions (Hard Rule 2).
- [ ] No `backdrop-filter` on scrolling containers or large areas; no blur-radius animation
      outside a materialize (the mechanical parts of Hard Rule 3).
- [ ] Reduced motion handled; content visible without JS; LCP image eager (Hard Rules 4-5).
- [ ] No banned defaults: purple-gradient tells, uniform radius, three-of-everything,
      template-recognizable layout (Hard Rule 7). Passes the uniqueness test in
      `references/page-design.md`.
- [ ] Performance verified, not asserted: LCP/CLS via Lighthouse, INP and frame drops via
      the DevTools Performance panel or the web-vitals extension.
- [ ] Any prose written for the page follows `brain/knowledge/writing-style.md`.

Provenance: this skill was synthesized and rewritten from five community design skills; the
credits and licenses are recorded in the repository `CHANGELOG.md` entry that introduced it.
