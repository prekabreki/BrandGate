# site/checks

Full-page captures of `site/index.html`, the evidence for #14's "renders correctly at 1280
and 420 wide with no horizontal scroll".

- `1280.jpg`, `420.jpg`: regenerated 2026-09-18 after the tools showcase landed.
- JPEG, not PNG: once the page wash was fixed the whole page carries film grain, which PNG
  cannot compress. The pair was 18 MB as PNG and is under 2 MB as JPEG, for an artifact
  nothing measures pixels on.
- Both are captured with a viewport as tall as the page (`chrome-devtools-axi emulate
  --viewport '420x11820x1,mobile'`), which is how the committed pair has always been made.
  That stretches the 88vh hero, so read these for clipping and overflow, not for the hero.
  Chrome will not lay a window out narrower than 500 CSS px, so 420 must be emulated, never
  a window size: `lookdev/render.py` refuses anything under 500 and says so.
- Horizontal overflow is checked separately, at the real viewport rather than a tall one:
  `document.documentElement.scrollWidth` against `clientWidth` at 420, 1280 and 1920.
  All three equal, 2026-09-18.
