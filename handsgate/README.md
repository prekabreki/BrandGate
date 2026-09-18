# Handsel Gate

The screen a brand team uses to review generated brand surfaces that the scoring gate
accepted or rejected. The tool is itself a Handsel surface: it is set in the brand type,
sits on the flow wash, and answers to the same rules it reviews.

It is a static React review tool. There is no login and no backend. Data comes from typed
fixtures under `src/fixtures/`, shaped the way the gate's own output is shaped, so the app
can later read the same JSON from disk.

Live build: https://handsel-gate.lovable.app

## Run it

    cd handsgate
    npm install
    npm run dev
    npm run build

## Brand values are generated, never typed here

    python scripts/tokens-to-tailwind.py   # brand/tokens.json -> src/brand/tokens.generated.css, plus the mark and the real renders
    python scripts/rules-to-fixtures.py    # brand/rules.json  -> src/fixtures/rules.ts

## Where things live

- `src/fixtures/surfaces.ts` — one entry per surface folder: the accepted candidate, the
  rejected candidate, and each candidate's full score.
- `src/fixtures/rules.ts` — generated. The brand rules as editable prose, grouped under
  Mark, Colour, Gradient, Surface, Type, Motif, Motion.
- `src/gate/rescore.ts` — the seam. It is a lookup, not a scorer: the real gate is the
  Python pipeline in `pipeline/`, which reads the same rules file. When the two are wired
  together, this function is where the pipeline plugs in.
- `src/brand/tokens.generated.css` — generated values. `src/brand/tokens.css` — the roles,
  the night theme and the surface recipes. `src/brand/glass.css` — one declaration, and the
  comment explaining why it cannot live with the others.

Editing a rule line in the right column calls `rescore` on blur and updates the centre
breakdown, so the rehearsed rule edits behave the way they will once the real pipeline answers.

## What Lovable produced, and what changed after export

Lovable built the whole app: TanStack Start, Tailwind v4 CSS-first, the three-panel layout,
the theme toggle, the rescore seam, and the rehearsed rule edit, which was exact on the first
build. Dropping `paper` from the grounds rule takes `colour.01` from 0.90 to 0.79 with the
reason changing to `#ECEAF6`; dropping `mist` too fails it at 0.71. That behaviour is
unchanged here. The review of that build is on issue #5.

What changed after the export, and why:

**The brand values became generated.** `tokens.css` held its own copy of the palette, the
gradients and the type stack. Now `tokens.generated.css` comes out of `brand/tokens.json`,
the same file the gate, the brand sheet and the one-pager read, so this app cannot drift from
the thing it reviews. `tokens.css` keeps only what a token file cannot hold: which token is
the ground in each theme, what night does, and the surface recipes.

**The rule prose became the brand's, not a paraphrase.** The build invented its rule text. It
read plausibly and it was wrong: it gave the mark a clear space of "a third of its height"
and invented a motif rule outright, with ids attached. `rules-to-fixtures.py` now writes the
panel from `brand/rules.json`, so every sentence shown is the one in `brand/rules.md`. Thirty
scoreable rules replaced twenty-four approximate ones.

**The drift plot became an empty state.** The left panel carried two figures captioned
"drift, last 24 runs" and "sameness, last 24 runs". Both were sine waves drawn in SVG. The
sameness figure is now the real one from `runs/sameness/plot.png`; drift says "specified, not
yet run", because it has not been run. A decorative curve captioned as a measurement is the
one defect that would actually matter on a tool about catching drift.

**The surface thumbnails became the surfaces.** The eight slots held soft SVG gradients under
the labels HERO, SOCIAL, PRINT and MOTION, beside those surfaces' real scores. They are now
the real renders out of `surfaces/`.

**The mark became the mark.** The header had a placeholder: a 3:1 band painted with the flow.
It is now `brand/logo/slice-mark.svg`, with a night variant, sized off `--hg-mark-aspect`.

**The glass was flat in every Chromium browser.** `.hg-glass` set `backdrop-filter`, and
`getComputedStyle` reported `none`. Tailwind v4 runs its own Lightning CSS pass targeting
Safari, so Lightning rewrote the declaration to `-webkit-backdrop-filter` and deleted the
standard property as redundant. Chrome 153 supports the standard property and not the
prefixed one, so every panel rendered as a flat white fill, in dev and in the build, with
nothing logged. Neither a `browserslist` nor `css.lightningcss.targets` in the Vite config
reaches that pass. The declaration now lives in `src/brand/glass.css`, which carries no
Tailwind at-rule and is linked separately, so it survives.

**The kit palette went.** A shadcn `:root` shipped beside the brand tokens: an oklch palette,
chart and sidebar scales, a `--radius` ramp, and a `body` set to system-font-on-white rather
than Archivo-on-paper. Only eight utilities referenced any of it, all in the 404 and error
screens, which now wear the brand. Deleting beat re-skinning: a kit palette left in place is
the off-brand surface waiting to turn up in the brand tool's own gallery.

**Lovable's own scaffolding came out.** `lovable-error-reporting.ts` reported errors to their
platform. `src/routes/api/public/handsgate-push.ts` was a one-off that pushed this source into
the BrandGate repo, guarded by a local token file; its own comment said it was safe to delete
after the push, and the push happened. The default metadata still said "Lovable App", author
"Lovable", `@Lovable`. The document title carried an em dash, which public copy here does not use.

`src/lib/error-capture.ts` and `src/lib/error-page.ts` stayed: those are TanStack Start's SSR
error handling, not Lovable's.

## Known

`npx vite preview` fails looking for `dist/server/server.js` while the build writes to
`.output/`. That is a preview-plugin mismatch in the Start and nitro pair, not this app. Use
`npm run dev`, or serve `.output/`.
