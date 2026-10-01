# Motion

How to make interfaces feel physical and alive. Curves, durations, and spring values live in
`design-tokens.md`; this file covers when to animate, how motion should behave, and the
recipes worth reusing. The distilled through-line, from Apple's fluid-interface work: motion
starts from the current on-screen value, inherits the user's velocity, projects momentum
forward, and can be grabbed and reversed at any instant.

## Should it animate at all

Gate every animation on frequency and purpose before choosing a tool:

| Frequency of the interaction | Animation budget |
|------------------------------|------------------|
| Constant (typing, keyboard nav, 100+ times a day) | none, or imperceptible |
| Frequent (open a menu, switch a tab) | fast and subtle, 150-250ms |
| Occasional (open a modal, expand a card) | full treatment, 250-400ms |
| Rare (onboarding, empty states, success moments) | expressive, this is where delight lives |

Name the purpose before writing it: feedback, orientation (where did this come from), state
change, or hierarchy. Decoration is not a purpose. If removing the animation loses no
information and no perceived quality, remove it.

## Tool ladder

Reach for the cheapest tool that does the job, in order:

1. CSS `transition` for state changes between two known states.
2. `@starting-style` for enter transitions from `display: none` (dialogs, popovers).
3. CSS `@keyframes` for multi-step, non-interactive sequences.
4. Web Animations API when JS needs to drive or compose timing.
5. A spring library (Motion / Framer Motion) for anything gesture-driven or interruptible.

Prefer transitions over keyframes for anything that can re-trigger rapidly: a transition
re-targets from the current value on interruption, a keyframe animation restarts from its
first frame.

## The feel rules

- **Respond on pointer-down, not on release.** Feedback that waits for `click` feels dead.
  Press states: `scale(0.97)` (or dim to 80% opacity for Apple-styled work), around 100ms.
- **Track 1:1 during a drag.** Content stays glued to the pointer, respecting the offset from
  where it was grabbed. Use Pointer Events with `setPointerCapture`, and keep a short
  position + timestamp history so release velocity is known.
- **Every animation is interruptible.** Never lock input during a transition. Animate from
  the presentation value (the live on-screen transform), never from the logical target, or
  interruption jumps. Springs do this by default.
- **Hand off velocity at release.** The animation continues at the finger's exact speed.
  Spring APIs that take absolute velocity get the raw px/s value; normalized APIs take
  `gestureVelocity / (target - current)`.
- **Project momentum to pick the target.** Do not snap to the nearest point from the release
  position; project where the flick was heading and snap to the point nearest that:

```js
// decelerationRate 0.998 for scroll-like feel, 0.99 for snappier
function project(velocity /* px/s */, decelerationRate = 0.998) {
  return (velocity / 1000) * decelerationRate / (1 - decelerationRate);
}
const target = nearestSnapPoint(current + project(releaseVelocity));
```

- **Rubber-band at boundaries.** Resist progressively past an edge instead of stopping hard:

```js
function rubberband(overshoot, dimension, constant = 0.55) {
  return (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));
}
```

- **Enter and exit along the same path.** A panel that slides in from the right dismisses to
  the right. Anchor popovers and menus to their trigger with `transform-origin` so they grow
  from the thing that opened them, and never enter with `scale(0)`; start around 0.95.
- **Decide commit vs cancel by velocity sign at release**, not by position. A drag past
  halfway moving back toward start is a cancel. A dismiss gesture with velocity above roughly
  0.11 px/ms commits regardless of distance.
- **Stagger group entrances** by 30-100ms per item, capped around 6-8 items; beyond that,
  batch the rest into one step.
- **Small blur crossfades sell morphs.** When content swaps inside a control (a label change,
  a number ticking), a 2px blur-out/blur-in over a short fade reads smoother than a plain
  opacity swap. Keep it discrete and under 20px of movement.
- **Clip-path is the precision tool** for reveals that must not distort content: inset
  reveals, tab highlight transitions, hold-to-confirm fills, comparison sliders. It
  composites like transform and does not trigger layout.

## Recipes

Scroll reveal, no-JS-safe: the hidden state is applied by the script, so content stays
visible when JS never runs.

```js
const io = new IntersectionObserver((entries) => {
  for (const e of entries) if (e.isIntersecting) {
    e.target.classList.add('is-visible');
    io.unobserve(e.target);
  }
}, { rootMargin: '0px 0px -10% 0px' });

document.querySelectorAll('[data-reveal]').forEach((el, i) => {
  el.classList.add('will-reveal');           /* hidden state added here, not in base CSS */
  el.style.setProperty('--index', i);
  io.observe(el);
});
```

```css
.will-reveal {
  opacity: 0; transform: translateY(28px);
  transition: opacity var(--duration-reveal) var(--ease-out-expo),
              transform var(--duration-reveal) var(--ease-out-expo);
  transition-delay: calc(var(--index) * 60ms);
}
.will-reveal.is-visible { opacity: 1; transform: none; }
```

Entry from `display: none` (dialogs, popovers). `transition-behavior: allow-discrete` is
required or the display flip skips the transition:

```css
dialog[open] {
  opacity: 1; transform: translateY(0);
  transition: opacity var(--duration-base) var(--ease-out-quart),
              transform var(--duration-base) var(--ease-out-quart),
              display var(--duration-base) allow-discrete,
              overlay var(--duration-base) allow-discrete;
}
@starting-style {
  dialog[open] { opacity: 0; transform: translateY(8px); }
}
```

Browser support, verified against MDN: `@starting-style` is Baseline (newly available since
August 2024), safe with the understanding that older browsers simply skip the entrance
(https://developer.mozilla.org/en-US/docs/Web/CSS/@starting-style). Scroll-driven animations
(`animation-timeline: scroll()` / `view()`) are NOT Baseline; treat them strictly as
progressive enhancement layered over the IntersectionObserver recipe above
(https://developer.mozilla.org/en-US/docs/Web/CSS/animation-timeline).

Tooltip skip-delay: the first tooltip in a group waits (400-700ms); while one is open,
siblings show instantly on hover. One shared timer per group, not per trigger.

## Performance

- Animate `transform` and `opacity`; `clip-path` and short discrete `filter` transitions are
  acceptable. Never animate layout properties (`top/left/width/height/margin/padding`) and
  never continuously animate `filter` or `box-shadow`; transition a pre-rendered shadow
  layer's opacity instead.
- Never drive reveals from a `scroll` event listener; it forces continuous main-thread work.
  IntersectionObserver or a scroll-linked library does the same job off the hot path.
- `will-change: transform` only on elements about to animate, removed after; blanket
  `will-change` wastes GPU memory.
- The CSS-variable trap: animating a custom property on `:root` forces style recalculation
  on everything that inherits it. Animate the property on the element that uses it.
- JS-library caution: some Motion/Framer Motion versions run `x`/`y` shorthand animations on
  the main thread via rAF rather than compositing them, so they stutter under load where a
  CSS transform would not. When a JS-driven transform stutters, test the same motion as a CSS
  transition before blaming the design; prefer CSS or WAAPI for simple transforms.
- Frame budget: 16.7ms at 60Hz, 8.3ms at 120Hz. Test on real mid-range hardware, and review
  motion frame-by-frame (slow it 10x) to catch what full speed hides.

## Reduced motion and accessibility

Respect three independent signals:

- `prefers-reduced-motion: reduce`: replace slides, springs, and parallax with short opacity
  cross-fades or static swaps. Keep the state change visible; reduced motion means gentler,
  not gone.
- `prefers-reduced-transparency: reduce`: raise translucent surfaces to near-solid and drop
  the blur.
- `prefers-contrast: more`: near-solid backgrounds with a defined contrasting border.

```css
@media (prefers-reduced-motion: reduce) {
  .will-reveal { opacity: 1; transform: none; transition: none; }
}
```

Also avoid: full-viewport moving backgrounds, slow loops near one cycle per 5 seconds, and
abrupt dark/light brightness jumps (ease theme changes). JS-driven scroll effects get killed
under reduced motion, not merely shortened.
