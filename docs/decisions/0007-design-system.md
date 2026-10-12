# ADR 0007: A token-based design system on Radix Colors and Open Props

- **Status:** accepted
- **Date:** 2026-10-12

## Context

The map, the shortlist and the report were styled page by page with raw hex colours, so they drifted (a "muted" grey differed between pages, the map's colours lived in JavaScript, and a status colour was reused for something else). The owner asked for the appearance to be built on a design system. Constraints from AGENTS.md: `web/` stays plain HTML, CSS and JS, with no build step.

## Decision

1. **Foundations, vendored unmodified (MIT) in `web/vendor/`:** Radix Colors 3.0.0 for colour scales, where every step has a job (1-2 backgrounds, 3-5 components, 6-8 borders, 9-10 solid fills, 11-12 text, so contrast is designed in), and Open Props 1.7.23 for space, type, radius and shadow scales. Vendored, not linked from a CDN: no build step and no third-party request at load.
2. **One semantic layer, `web/tokens.css`.** Pages and scripts use roles (`--surface-card`, `--text-muted`, `--accent`, `--positive`, `--data-rooftop`, ...), never a raw hex or a raw Radix step. A rebrand or a dark mode is a change in that file.
3. **Data colours are sRGB hex in the token file**, because Radix serves some colours as `display-p3` to wide-gamut screens and MapLibre cannot parse them in paint rules. Each hex names its Radix step in a comment, and `tests/test_web_tokens.py` checks that it equals the vendored step. The same test fails if a raw hex appears anywhere outside `tokens.css` and `vendor/`.
4. **Category colours were validated, not eyeballed.** Rooftop `orange-11`, penthouse `cyan-10`, redevelopment `violet-10` pass the colour-blind and contrast checks (CVD ΔE 15.2 worst case). The floors ramp is one hue from light to dark. Colour is never the only cue: the panel says the type in words.
5. **A living style guide**, `web/styleguide.html`, renders every token and component from the real stylesheet, so documentation cannot go stale.
6. The map's colours are read from the tokens at load (`token()` in `format.js`), so the map and the panel cannot disagree.

## Consequences

✅ One place decides how the product looks; the three pages agree by construction.
✅ Accessible contrast comes from the scale's step semantics, not from case-by-case checking.
✅ No build step, no CDN.
⚠️ Dark mode is not shipped. The tokens are ready for it (Radix has dark scales), but the basemap is light and would need a dark style; until then the panel stays light.
⚠️ `tokens.css` uses `@import`, so the 11 small vendor files load in a chain. Fine on HTTP/2 static hosting; concatenate them if load time ever matters (M4 target: map in under 3 s on a mid-range phone).
⚠️ The sRGB hex duplication is deliberate and guarded by a test, but it is still a duplication.

## Revisit when

A dark basemap is wanted, a second brand is needed, or the style guide shows a component that no page uses.
