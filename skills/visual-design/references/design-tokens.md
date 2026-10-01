# Design tokens

The canonical value set for the visual-design skill. Every numeric value (easing curves,
durations, springs, spacing, radii, shadows, palettes) is defined once, here. The other
references use these token names and never restate the numbers, so a retune happens in one file.

## Easing and duration

```css
:root {
  --ease-out-expo:  cubic-bezier(0.16, 1, 0.3, 1);   /* reveals, entrances */
  --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);   /* general UI state changes */
  --ease-apple:     cubic-bezier(0.28, 0.11, 0.32, 1); /* Apple-flavored work */

  --duration-fast: 150ms;   /* hovers, toggles, small controls */
  --duration-base: 250ms;   /* most UI transitions */
  --duration-slow: 350ms;   /* sheets, modals, larger surfaces */
  --duration-reveal: 600ms; /* scroll-entrance of content blocks */
}
```

The sources this skill distills disagree on curves; these three are the canon. Rules that
follow from them:

- Reveals and entrances use `--ease-out-expo`. UI feedback uses `--ease-out-quart`.
  Apple-styled pages use `--ease-apple` throughout (0.3 to 0.4s).
- Exits are faster than entries and stay ease-out. There is no ease-in exit token on purpose:
  a slow-starting exit reads as lag.
- UI transitions live in the 150 to 500ms band. Under 100ms reads as a glitch; over 500ms
  reads as delay. Scroll reveals may run 500 to 800ms because they are content entrances,
  not feedback.
- The `linear` keyword is reserved for constant motion (marquee, spinners), hold or scrub
  progress where the gesture supplies the pacing, and `linear()` spring approximations.

## Springs

Named presets (Framer Motion / Motion values):

| Preset | Config | Use |
|--------|--------|-----|
| gentle | `stiffness: 120, damping: 20` | large surfaces settling |
| snappy | `stiffness: 300, damping: 24` | small controls, toggles |
| apple | `stiffness: 340, damping: 30` | Apple-styled interactive elements |

Apple's designer-facing spring parameters, for tools that take damping ratio + response:

| Interaction | Damping ratio | Response (s) |
|-------------|---------------|--------------|
| Move / reposition | 1.0 | 0.4 |
| Rotation | 0.8 | 0.4 |
| Drawer / sheet | 0.8 | 0.3 |

Default to damping 1.0 (no overshoot). Add bounce (damping around 0.8, or `bounce: 0.2`)
only when the gesture itself carried momentum: a flick, a throw, a drag release. Overshoot on
a menu that faded in feels wrong; overshoot on a card you flicked feels right.

## Typography

```css
:root {
  /* Fluid scale, Major Third (1.250) */
  --text-xs:   clamp(0.7rem, 0.65rem + 0.2vw, 0.8rem);
  --text-sm:   clamp(0.8rem, 0.76rem + 0.2vw, 0.9rem);
  --text-base: clamp(1rem, 0.95rem + 0.25vw, 1.125rem);
  --text-lg:   clamp(1.125rem, 1.05rem + 0.35vw, 1.406rem);
  --text-xl:   clamp(1.406rem, 1.3rem + 0.5vw, 1.758rem);
  --text-2xl:  clamp(1.758rem, 1.55rem + 0.95vw, 2.197rem);
  --text-3xl:  clamp(2.197rem, 1.85rem + 1.5vw, 2.747rem);
  --text-4xl:  clamp(2.747rem, 2.2rem + 2.5vw, 3.433rem);
  --text-5xl:  clamp(3.433rem, 2.5rem + 4vw, 4.768rem); /* display step, larger jump on purpose */
}
```

| Level | Desktop | Mobile | Line height | Tracking |
|-------|---------|--------|-------------|----------|
| H1 | 48-64px | 32-40px | 1.1-1.15 | -0.02em |
| H2 | 36-48px | 28-32px | 1.2-1.3 | -0.01em |
| H3 | 28-32px | 22-26px | 1.2-1.4 | 0 |
| Body | 16-18px | 16px | 1.5-1.8 | 0 |
| Uppercase labels | 10-12px | same | 1 | 0.05-0.15em |

Tracking is size-specific, never one value for all sizes: tighten as text grows (around
-0.003em at 17px, -0.015em at 48px, -0.022em at 80px and up), keep body near 0, open up small
uppercase labels. Line height moves inversely with size. Build hierarchy from weight + size +
leading as a set, and prefer dramatic weight contrast (300 vs 700) over the timid 400 vs 600
default. Reading width: 50 to 75 characters (`max-width: 70ch`). Maximum 2-3 fonts per
project, 1 heading + 1 body is the ideal.

## Font pairings by genre

Pick by the project's genre, or an adjacent one. Never default to the same pairing for every
project; identical font choices across unrelated projects are a recognizable generated-site
tell.

| Genre | Heading | Body | Best for |
|-------|---------|------|----------|
| Elegant editorial | Playfair Display | Inter | fashion, wine, luxury goods |
| Refined luxury | Cormorant Garamond | DM Sans | jewelry, hospitality, spa |
| Modern warmth | DM Serif Display | DM Sans | food, lifestyle, wellness |
| Clean tech | Inter (600-700) | Inter (400) | SaaS, developer tools |
| Bold authority | Space Grotesk | Inter | fintech, enterprise, B2B |
| Swiss minimal | Neue Montreal / Geist Sans | system UI stack | portfolios, agencies |
| Editorial modern | Sora | Source Serif 4 | magazines, blogs, media |
| Playful premium | Cabinet Grotesk | General Sans | consumer apps, startups |
| Dark luxury | Bebas Neue (caps only) | Manrope | automotive, nightlife, audio |
| Classic authority | EB Garamond | Lato | legal, finance, education |

Sourcing rules:

- Default to the system stack or self-hosted open-license faces (WOFF2, preloaded,
  `font-display: swap` for headings). Verify the license before embedding any commercial
  face; several in the table (Neue Montreal, Cabinet Grotesk, General Sans) ship under
  commercial or Fontshare terms, and Apple's SF fonts are licensed for Apple-platform work
  only (see the font strategy note in `apple-style.md`).
- In artifact output, never reference external font, CDN, or script hosts; the artifact CSP
  blocks them. In project code, motion libraries come in via the package manager with pinned
  versions, never script tags.

## Spacing and layout

```css
:root {
  /* 8px grid */
  --space-1: 0.25rem; --space-2: 0.5rem;  --space-3: 0.75rem; --space-4: 1rem;
  --space-6: 1.5rem;  --space-8: 2rem;    --space-12: 3rem;   --space-16: 4rem;
  --space-24: 6rem;   --space-32: 8rem;   --space-40: 10rem;

  /* Fluid section padding */
  --section-sm: clamp(3rem, 6vw, 5rem);
  --section-md: clamp(5rem, 10vw, 7.5rem);
  --section-lg: clamp(7.5rem, 14vw, 12.5rem);

  --container-lg: 1024px; --container-xl: 1200px; --container-text: 70ch;
  --grid-gap: clamp(1rem, 2vw, 2rem);
}
```

Every dimension sits on the 8px grid. Section padding: 80-120px desktop / 60-80px mobile for
standard content, 120-200px for heroes. Content-to-whitespace ratio around 40:60 for a
premium feel. Headings take 1.5-2x more space above than below.

## Radius and shadows

```css
:root {
  --radius-sm: 4px;   /* tags, badges */
  --radius-md: 8px;   /* cards */
  --radius-lg: 12px;  /* containers */
  --radius-xl: 16px;  /* modals, large panels */
  --radius-2xl: 24px; /* feature cards, bento tiles */
  --radius-full: 9999px; /* pills, avatars */

  /* Layered, never a single plain-black shadow */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.1);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05);
  --shadow-dreamy: 0 2px 4px rgba(0,0,0,0.07), 0 8px 16px rgba(0,0,0,0.07),
                   0 16px 32px rgba(0,0,0,0.07), 0 32px 64px rgba(0,0,0,0.07);
}
```

Vary radius by element role; uniform 12-16px on everything is a generated-site tell. Sharp
(0px) edges on some elements give editorial authority. Tint shadows toward the surface hue
instead of pure black when the palette is warm.

## Palettes

Five premium starting points; pick by brand personality, never the same one every time.

| Palette | Surfaces | Text | Accent | Best for |
|---------|----------|------|--------|----------|
| Warm premium | `#F9F6F4` / `#F5F0E6`, white cards | `#2F2F2F` / `#998B7E` | gold `#D4AF37` | luxury goods, hospitality, beauty |
| Cool tech (light) | `#FAFAFA` / `#F5F5F5`, white cards | `#171717` / `#525252` | `#0066FF` | SaaS, developer tools, fintech |
| Cool tech (dark) | `#0A0A0F` / `#141414`, `#1A1A1A` cards | `#EDEDED` / `#A0A0A0` | `#3B82F6` | same, dark contexts |
| Bold dark | `#0A0A0A` / `#111111`, `#1A1A1A` cards, 1px `#222222` borders, no shadows | `#F5F5F5` / `#888888` | `#FF3B30` or white | automotive, audio, gaming |
| Minimal editorial | white / `#F7F7F5`, no card backgrounds, 1px `#E0E0E0` hairlines | `#1A1A1A` / `#666666` | `#1A1A1A` + warm `#C5A572` | architecture, editorial, portfolio |

Color rules: 60% dominant surface, 30% secondary, 10% accent; 2-3 core colors maximum; muted
and desaturated over vivid; give every neutral a slight warm or cool bias, because zero-chroma
grays read as emotionally dead defaults.

Dark mode for standard product UI: avoid pure `#000` backgrounds (use `#121212` to
`#1A1A1A`), never pure white text (`#E0E0E0` range), replace shadows with lighter surface
steps (`#1E1E1E`, `#242424`, `#2C2C2C`), desaturate accents. The Bold dark and Cool tech
dark palettes above are standalone dark page designs and deliberately sit below that floor.
Apple-styled work is the other exception: marketing dark sections use true `#000` with
`#f5f5f7` text, and HIG app dark mode uses a `#000` base with elevated surface steps; those
exact values live in `apple-style.md`.
