# Apple style

What makes output read as genuinely Apple rather than "generic minimal with more whitespace":
specific numbers and a philosophy of restraint. Two distinct registers share this file: app UI
(HIG, Liquid Glass era) and apple.com-style marketing pages. Mixed requests split cleanly:
marketing rules govern the page, HIG rules govern anything depicted as an app.

## Liquid Glass: the two-layer model

Every screen separates into:

1. A content layer: the actual content, opaque backgrounds, extending edge to edge and
   scrolling under everything.
2. A functional layer: controls and navigation (tab bars, toolbars, buttons) floating above
   on a glass material that refracts what is beneath and adapts to light/dark from the
   content under it.

Practical rules: bars are floating rounded or capsule islands, never full-width strips glued
to screen edges; content visibly scrolls beneath them; a scroll-edge effect (progressive
blur/fade) separates floating chrome from content instead of a hard hairline; glass is for
interactive chrome only, never for content-layer cards; symbols on glass stay monochrome,
with tint reserved for the one active or prominent element.

```css
.glass {
  background: rgba(255,255,255,.55);              /* dark mode: rgba(30,30,32,.55) */
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border-radius: 28px;                             /* capsule bars: 999px */
  box-shadow:
    0 8px 32px rgba(0,0,0,.08),                    /* soft lift */
    inset 0 1px 0 rgba(255,255,255,.55),           /* specular top edge */
    inset 0 0 0 .5px rgba(255,255,255,.25);        /* glass rim */
}
.glass--clear { background: rgba(255,255,255,.18); } /* over media; add a 35% black
                                                        dim layer when content is bright */
.scroll-edge {
  position: fixed; inset: 0 0 auto 0; height: 96px; pointer-events: none;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  mask-image: linear-gradient(to bottom, black 30%, transparent 100%);
}
```

Do not shove content down with `padding-top` under a floating bar; pad inside the scroller
with `env(safe-area-inset-*)` so content passes beneath the glass.

## Component feel

- **Buttons** are capsules or rounded rectangles, minimum 44px hit target. Press state dims
  to ~80% opacity plus `scale(0.97)`; never a ripple, never a hover lift with shadow. One
  prominent (filled, tinted) button per view; the rest are gray or plain. Labels are verbs.
- **Tint marks interactivity.** Anything tinted looks tappable, so never tint static
  decoration. One or two tinted elements per view, maximum.
- **Hierarchy comes from typography and background steps**, not boxes and borders: dramatic
  size/weight jumps, background levels (system, secondary, tertiary), hairlines at 8-30%
  opacity. Shadows only on genuinely floating things, soft and low-opacity.
- **Grouped lists** (settings style): 10px-radius groups inset 16px from the edges, rows at
  least 44px tall with 0.5px separators, 29px icon tiles, chevron for navigation, value text
  in secondary label color. Toggle: 51x31px pill, on-state green `#34c759`.
- **Sheets**: top radius 16-20px, a 36x5px grabber pill, scrim `rgba(0,0,0,.4)`, slide up
  over `--duration-slow` on `--ease-apple`, drag-to-dismiss mirrors the entrance downward. Cancel sits
  leading, Done trailing. Confirmation dialogs only for genuinely destructive, non-undoable
  actions.
- **Typography discipline**: body 17px (iOS register) or 13px (macOS-dense register);
  headlines several steps up, never one. Tracking tightens as size grows (see the tracking
  ramp in `design-tokens.md`). Emphasize with weight before size.

Font strategy: on Apple devices the system stack renders true SF
(`-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue",
Arial, sans-serif`). SF fonts are licensed for Apple-platform design only, so for client work
or non-Apple distribution recommend Inter with `font-feature-settings: "cv05", "cv11"` for
SF-like letterforms, and say why. Never embed SF font files in deliverables.

## Dark mode values

App UI: base `#000` with elevated surface steps in the `#1c1c1e` / `#2c2c2e` family; text
`#f5f5f7` family, never pure white; separators `rgba(84,84,88,.60)`; tint brightens
(`#0091ff` family). Dark mode dims backgrounds and brightens foregrounds; it never inverts,
and elevated surfaces step brighter, not darker.

## The apple.com marketing playbook

Page anatomy: a vertical stack of full-bleed sections alternating light (`#fff` / `#f5f5f7`)
and dark (`#000`), each section carrying exactly one feature, one hero visual, minimal copy.
Nav 44-48px, frosted (`rgba(251,251,253,0.8)` light / `rgba(22,22,23,0.8)` dark with
`backdrop-filter: saturate(180%) blur(20px)`), ~12px links, content max ~1024px; the floating
glass pill nav is the current-era alternative to the full-width strip. Footer: dense 12px
links on `#f5f5f7`.

Every feature section follows one copy formula:

```
[Eyebrow]   21-28px semibold, names the feature area
[Headline]  48-80px, weight 600-700, one short punchy claim
[Subhead]   19-21px, #86868b on light / #a1a1a6 on dark, 2-3 lines max
[Links]     "Learn more >" (#0066cc) and/or a pill CTA (#0071e3, hover #0077ed)
[Visual]    enormous, centered, often bleeding off-section
```

Voice: short declarative fragments ("Lightning fast. Lightyears ahead."). Superlatives are
earned by a spec, never stacked. No bullet-point feature lists in hero sections; one claim at
a time. Button labels in Title Case, body in sentence case, never mixed.

Signature moves, pick one or two per page, not all: gradient headline text
(`background-clip: text` on a black section), a scroll-scrubbed product sequence (pinned
section, scrub around 0.6, at most ~120 frames), sticky headline with scrolling visuals, a
bento grid of rounded cards (18-28px radius, mixed spans, one stat per card), device-frame
screenshot showcases (never raw floating UI), a horizontally snapping card rail.

Layout numbers: text blocks max 980-1024px; headline max ~800px; subhead max ~600px; section
padding 100-150px desktop / 60-80px mobile; centered by default, left-aligned only inside
cards and split layouts. Dark sections: background `#000`, text `#f5f5f7` (pure `#fff`
vibrates), secondary `#a1a1a6`, links `#2997ff`, cards `#1d1d1f` with an optional
`rgba(255,255,255,0.08)` hairline.

Marketing motion: reveals rise subtly (translateY around 28px, ~700ms, ease-out, no bounce)
and fire once. Whatever slides in from an edge dismisses back to that edge.

## What breaks the illusion

- Drop shadows on buttons or nav.
- More than one accent color.
- Grids of tiny icons with paragraph blurbs (SaaS template, not Apple).
- Desktop headlines under 40px.
- A busy hero: badge + headline + subhead + two buttons + trust logos + screenshot at once.
- Default `ease-in-out`, or bouncy springs on scroll reveals.
- Opaque full-width bars with content stopping above them (pre-glass look).
- Pure white text on black, or tinted static decoration.

## Quality bar

Before delivering Apple-styled work, check: could one more element be removed (usually yes;
do it); do bars float over content with a scroll-edge effect; is anything non-interactive
tinted; are hit targets at least 44px; do press states dim and scale rather than ripple; do
dark surfaces use the elevated-step values above; would a casual observer accept a screenshot
as an Apple app or an apple.com page. When a brand conflicts with strict Apple rules (a gold
hotel accent, say), keep the structure and restraint, swap only the tint, and say that is
what you did.
