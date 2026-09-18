/**
 * The Handsel mark: six pie slices in a 3:1 band, the flow running through them.
 *
 * Both files come from brand/logo via scripts/tokens-to-tailwind.py, so this is the
 * shipped mark and not a redraw of it. The first build painted a plain gradient band
 * as a stand-in, which is the one thing a brand-consistency tool cannot do in its own
 * header. Aspect comes from --hg-mark-aspect, generated out of tokens.json.
 *
 * Day and night are separate files, so both render and CSS picks between them. That
 * keeps the choice out of React state: no prop to thread and nothing to mismatch on
 * hydration. Never rotate, mirror, outline or shadow it (mark.04).
 */
export function Mark({ width = 96 }: { width?: number }) {
  const height = `calc(${width}px / var(--hg-mark-aspect))`;
  // Clear space is a third of the mark's height on every side (mark.02).
  const pad = `calc(${height} / 3)`;

  return (
    <div style={{ padding: pad }}>
      <div style={{ width, height }} role="img" aria-label="Handsel mark">
        <img
          src="/brand/slice-mark.svg"
          alt=""
          className="block h-full w-full dark:hidden"
          draggable={false}
        />
        <img
          src="/brand/slice-mark-night.svg"
          alt=""
          className="hidden h-full w-full dark:block"
          draggable={false}
        />
      </div>
    </div>
  );
}
