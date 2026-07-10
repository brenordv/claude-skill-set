---
name: theme-factory
description: >-
  Apply professional font and color themes to any artifact: slide decks,
  documents, reports, HTML pages, dashboards, or diagrams. Use PROACTIVELY
  whenever the user asks for styling, theming, branding, color palettes,
  font pairings, or wants an artifact to "look better" or "more professional",
  even if they don't say the word "theme". Contains 10 complete built-in
  themes plus a workflow for generating custom ones.
---

# Theme Factory

A fully self-contained theme system. All theme specifications live in this
file; there are no external PDFs, images, or theme directories to read.

## Workflow

1. **If the user already named a theme** (or their request clearly implies
   one), skip selection and apply it directly.
2. **If the user needs to choose**, present the options. Prefer generating a
   live preview (see *Generating a Preview* below) over describing themes in
   text. Ask which theme to apply and wait for confirmation.
3. **Apply the theme** using the specs below, following the *Application
   Rules*.
4. **If nothing fits**, create a custom theme (see *Custom Themes*).

## Theme Specifications

Each palette lists color name, hex, and role. Fonts are given as
Header / Body. All fonts are system fonts (DejaVu, FreeSans/FreeSerif
families) bundled in document-generation environments, so slide decks,
Word docs, and PDFs render correctly without downloading fonts.

**Dark themes** (dark background, light text): Ocean Depths, Tech
Innovation, Midnight Galaxy. All others are light themes.

| # | Theme | Palette | Fonts (Header / Body) | Best Used For |
|---|-------|---------|----------------------|---------------|
| 1 | **Ocean Depths** *(dark)* | Deep Navy `#1a2332` bg · Teal `#2d8b8b` accent · Seafoam `#a8dadc` light accent · Cream `#f1faee` text | DejaVu Sans Bold / DejaVu Sans | Corporate presentations, financial reports, consulting decks, trust-building content |
| 2 | **Sunset Boulevard** | Burnt Orange `#e76f51` primary accent · Coral `#f4a261` secondary accent · Warm Sand `#e9c46a` highlights/bg · Deep Purple `#264653` dark contrast/text | DejaVu Serif Bold / DejaVu Sans | Creative pitches, marketing, lifestyle brands, event promos, inspirational content |
| 3 | **Forest Canopy** | Forest Green `#2d4a2b` primary · Sage `#7d8471` muted accent · Olive `#a4ac86` light accent · Ivory `#faf9f6` bg/text | FreeSerif Bold / FreeSans | Environmental and sustainability content, outdoor brands, wellness, organic products |
| 4 | **Modern Minimalist** | Charcoal `#36454f` primary · Slate Gray `#708090` accent · Light Gray `#d3d3d3` bg/dividers · White `#ffffff` text/bg | DejaVu Sans Bold / DejaVu Sans | Tech presentations, architecture portfolios, design showcases, data visualization |
| 5 | **Golden Hour** | Mustard `#f4a900` bold accent · Terracotta `#c1666b` warm secondary · Warm Beige `#d4b896` neutral bg · Chocolate `#4a403a` text/anchors | FreeSans Bold / FreeSans | Restaurants, hospitality, fall campaigns, cozy lifestyle, artisan products |
| 6 | **Arctic Frost** | Ice Blue `#d4e4f7` light bg/highlights · Steel Blue `#4a6fa5` primary accent · Silver `#c0c0c0` metallic accents · Crisp White `#fafafa` bg/text | DejaVu Sans Bold / DejaVu Sans | Healthcare, technology solutions, winter sports, clean tech, pharma |
| 7 | **Desert Rose** | Dusty Rose `#d4a5a5` soft primary · Clay `#b87d6d` earthy accent · Sand `#e8d5c4` warm neutral bg · Deep Burgundy `#5d2e46` rich dark contrast | FreeSans Bold / FreeSans | Fashion, beauty brands, weddings, interior design, boutique businesses |
| 8 | **Tech Innovation** *(dark)* | Electric Blue `#0066ff` vibrant accent · Neon Cyan `#00ffff` bright highlight · Dark Gray `#1e1e1e` bg · White `#ffffff` text/contrast | DejaVu Sans Bold / DejaVu Sans | Tech startups, software launches, AI/ML, innovation showcases, digital transformation |
| 9 | **Botanical Garden** | Fern Green `#4a7c59` rich natural primary · Marigold `#f9a620` bright floral accent · Terracotta `#b7472a` earthy warm tone · Cream `#f5f3ed` soft neutral bg | DejaVu Serif Bold / DejaVu Sans | Garden centers, food, farm-to-table, botanical brands, natural products |
| 10 | **Midnight Galaxy** *(dark)* | Deep Purple `#2b1e3e` dark base/bg · Cosmic Blue `#4a4e8f` mystical mid-tone · Lavender `#a490c2` soft accent · Silver `#e6e6fa` highlights/text | FreeSans Bold / FreeSans | Entertainment, gaming, nightlife venues, luxury brands, creative agencies |

## Application Rules

1. Respect each color's stated role: background colors stay as surfaces,
   accents stay as accents. Distribute roughly 60% dominant surface / 30%
   secondary / 10% accent.
2. On dark themes, all body text uses the theme's light color; never place
   dark palette colors as text on the dark background.
3. Verify WCAG 2.1 AA contrast (4.5:1 body text, 3:1 large text). If a
   combination fails, darken/lighten the foreground rather than swapping
   roles. Note: Neon Cyan (`#00ffff`) and Silver tones are highlight-only,
   too low-contrast for body text on light surfaces.
4. Header font for headings and display text only; body font for everything
   else, including tables, captions, and labels.
5. Apply the theme consistently across the entire artifact: every slide,
   page, or section. Derive tints/shades of the palette for charts and
   tables rather than introducing new hues.
6. For slide decks and HTML, define the palette once as variables (CSS
   custom properties or a theme constant) and reference the variables
   everywhere.
7. For HTML artifacts rendered in a browser, use web-safe equivalents:
   DejaVu Sans → `Verdana, 'DejaVu Sans', sans-serif`; DejaVu Serif /
   FreeSerif → `Georgia, 'DejaVu Serif', serif`; FreeSans →
   `Helvetica, Arial, sans-serif`.

## Generating a Preview

When the user needs to see options before choosing, generate a single HTML
artifact showing swatch cards: one card per candidate theme (all 10, or a
shortlist filtered by the user's context, using the "Best Used For" column).
Each card shows:

- Theme name set in its header font, on its background color
- A one-line sample sentence in its body font and text color
- Four color chips with name and hex labels

Keep it lightweight: plain HTML/CSS with the web-safe font stacks above,
no JS frameworks, no external assets. This replaces any static showcase
file; generate it fresh, on demand, only when selection is actually needed.

## Custom Themes

If no built-in theme fits:

1. Gather intent: mood, audience, industry, any brand colors, light vs dark.
2. Compose a theme in the same format as the table above: four colors with
   named roles, a header/body font pairing from the bundled font families,
   and a "best used for" line.
3. Name it in the same style (two evocative words describing the palette).
4. Show a preview card (same format as above) for confirmation, then apply.
5. If the user likes it, offer to add it to this file's table so it becomes
   a permanent part of the theme library.
