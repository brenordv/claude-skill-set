# Page design

Composition rules for premium pages: heroes, section flow, layout archetypes, component
patterns, and the tells that make a page read as generated. Numeric tokens (spacing, radii,
shadows, type scale) live in `design-tokens.md`.

## The first viewport

Users judge a site in about 50 milliseconds, and that judgment transfers to the product. The
first viewport must carry: a clear focal point (top-left or center-left entry, not
dead-center), professional typography, generous whitespace, the value proposition, one
primary CTA, and one trust signal. Visual weight splits roughly 60/40 across the fold; a
50/50 mirror feels static.

Hero variants; rotate across projects, never the same layout twice:

| Pattern | Layout | Best for |
|---------|--------|----------|
| Split | text left (55-60%), media right | SaaS, apps, tools |
| Asymmetric | headline offset left, visual bleeds past the right edge | creative, agencies |
| Full-bleed media | video/image fills the viewport, text over a scrim | automotive, luxury, travel |
| Editorial | large serif headline (80-120px), minimal subtext, no hero image | fashion, brands |
| Product spotlight | product image dominant (65%+), tight caption beside it | e-commerce, hardware |
| Dashboard | angled screenshot or device mockup, headline above or beside | dev tools, analytics |

The default centered-headline-over-gradient hero is the one variant that is never acceptable.

## Section flow

A premium page reads as one continuous narrative, not a stack of isolated blocks.

- One idea per section, one action. If a section carries two messages, split it.
- Alternate background tones every one or two sections (light, off-white, dark); never three
  consecutive sections on the same background. Alternate media sides too: image-left follows
  image-right.
- Follow every content-dense section with a breathing element: a single pulled quote, one
  large stat, a full-width image, or a minimal CTA bar.
- Transition techniques, two or three per page: a background tone shift, an element
  overlapping the section boundary (negative margin 40-80px), a shared accent thread, a
  full-bleed break.
- Landing-page order that works: hero, social proof (grayscale logo bar attached to the
  hero), problem, solution, features (alternating sides), testimonials with real names and
  numbers, how-it-works, pricing (anchored high to low, one highlighted), FAQ, final CTA,
  footer.

## Layout archetypes

Pick one deliberately per project; vary across projects.

- **Asymmetric bento**: a masonry-like grid of varied card spans (a wide 2-row card beside
  stacked small ones). Collapses to a single column with generous vertical gaps below 768px.
- **Z-axis cascade**: overlapping card stacks with slight rotations (-2 to 3 degrees) and
  depth differences. Below 768px, remove rotations and overlaps entirely; overlapping
  elements collide with touch targets.
- **Editorial split**: massive typography on one half, scrollable or staggered interactive
  content on the other. Collapses to a full-width vertical stack, type block first.

Universal mobile override: below 768px everything falls back to full width with modest
padding, and full-height sections use `min-h-[100dvh]`, never `h-screen`, to avoid the iOS
Safari viewport jump.

## Component patterns

- **Double-bezel nesting**: premium cards sit in a thin outer shell (a subtle background,
  hairline ring, small padding, large radius) with an inner core whose radius is calculated
  concentrically (`rounded-[calc(2rem-0.375rem)]` style), like a glass plate in a machined
  tray. This one move separates "template with nice fonts" from crafted hardware feel.
- **Island buttons**: primary CTAs are full pills with generous padding; a trailing arrow
  never sits naked next to the label, it gets its own small circular wrapper flush with the
  button's inner edge, which translates diagonally a few pixels on hover.
- **Eyebrow tags**: major headings are preceded by a microscopic pill badge (10px uppercase,
  wide tracking).
- **Hairlines over borders**: 1px solid gray borders read as bootstrap; use low-opacity
  hairlines (`black/5`, `white/10`) and background steps.

## Copy on the page

Copy is part of the visual hierarchy; keep only what layout needs:

- Hero headlines 6-9 words; one supporting paragraph of 2-3 sentences; one CTA per section
  (a single competing action measurably outperforms several).
- Specific beats vague: "Deploys in 38 seconds" over "Lightning-fast deployment"; concrete
  numbers are what premium copy looks like.
- CTA labels are action-specific ("Start building", "See pricing") and match what happens
  next. Secondary CTAs take ghost/outline style and never compete with the primary.

## What the best ship

Condensed brand techniques worth stealing:

| Brand | Signature technique |
|-------|--------------------|
| Apple | one feature per scroll section; scroll-scrubbed image sequences; see `apple-style.md` |
| Stripe | tiny custom WebGL gradient (~10KB) instead of a heavy library; four animation tiers by importance |
| Linear | LCH color system: 3 inputs generate the whole palette; 80/100/120px section rhythm |
| Vercel | 10-step tiered color scales (1-3 backgrounds, 4-6 borders, 7-8 contrast, 9-10 text) on a 4px grid |
| Tesla | full-bleed media heroes with scrim text overlays |
| Aesop | warm neutrals, serif authority, hairline rules instead of cards |

Universal: 2-3 colors, roughly 40:60 content-to-space, one idea per viewport, editorial tone
over commercial, motion under 500ms on compositor properties.

## Banned defaults and generated-page tells

Instant fails, no exceptions:

- Fonts: Arial/system-default headings on a premium brief; the same pairing on every project.
- Purple/indigo accents (`#6366F1` family) and purple-blue mesh/aurora gradients as defaults.
  The one exception: purple genuinely is the client's brand color; then use it confidently.
- The centered-headline-over-gradient hero; edge-to-edge sticky navbars glued to the top.
- Uniform border radius everywhere; identical same-size card grids; "three of everything"
  (3 features, 3 testimonials, 3 tiers); perfect center alignment on every block.
- Zero-chroma neutral grays; timid 400/600 weight contrast.
- Generic aspirational headlines ("Build the future of X", "Your all-in-one platform").
- Harsh dark drop shadows; generic 1px solid gray borders; thick-stroke default icon sets
  (prefer thin precise lines, 1.5-2px stroke).
- Scroll-jacking; entrance animations over 800ms; every element sliding in identically.

The uniqueness test: placed beside five generated sites, would this one blend in? If yes,
change the font pairing, the accent, the hero layout, or the radius strategy, and add one
unexpected element per page (an oversized number, a giant pulled quote, an asymmetric break).

## Performance guardrails

- `backdrop-filter` only on chrome and overlay layers (fixed/sticky bars, modals, popovers,
  menus); never on scrolling containers or large content areas; never animate blur radius
  outside a brief enter/exit materialize.
- Noise/grain overlays only as fixed, `pointer-events-none` pseudo-elements at very low
  opacity, never attached to scrolling containers.
- Z-index discipline: reserve layers for systemic chrome (nav, modal, overlay, tooltip); no
  arbitrary `z-[9999]`.
- Images: AVIF/WebP with fallbacks, responsive `srcset`, explicit width/height (prevents
  CLS), `loading="lazy"` below the fold only. The LCP image loads eager with
  `fetchpriority="high"`, never lazy.
- Fonts: WOFF2 only, preload the critical faces.
- Budgets: LCP at or under 2.5s, INP at or under 200ms, CLS at or under 0.1, animations at
  60fps. Verify, don't assert: LCP/CLS in a Lighthouse run, INP and frame drops in the
  DevTools Performance panel or the web-vitals extension.
