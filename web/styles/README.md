# Design tokens

`tokens.dark.css` and `tokens.light.css` are the only place a color literal is allowed to be
declared. Every component consumes a `var(--token-name)`; `tests/tokens.test.ts` asserts no
component file contains a hardcoded color literal.

## `serious` is deliberately absent

anchor-spec.md §22.3 originally proposed a fourth status role between `warning` and `critical`.
Measured against `warning` (`#fab219`) it came out to normal-vision ΔE 13.6 — below the 15 floor a
full-color reader needs to reliably tell the pair apart. It was cut, not forgotten: three status
levels plus muted plus the accent cover every run/step state in the data model without asking a
reader to distinguish two oranges. Its absence here is a decision, not an omission — do not add it
back without re-running the same validation and clearing the floor.

## Why two files instead of one with a media query

§22.1 requires the light set to be *selected and validated* against its own surface, never an
automatic inversion of dark — light-mode gold, for instance, is pushed to olive (`#7a6300`)
specifically because a gold light enough for the dark panel is unreadable on a light one. A single
token computed by inversion would silently drift out of validation the next time dark is retouched.
