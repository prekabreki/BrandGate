/**
 * Placeholder mark: a 3:1 band painted with the flow gradient.
 * Replace the inner element with the supplied SVG when it lands.
 * Never rotate, mirror, outline or shadow it.
 */
export function Mark({ width = 96 }: { width?: number }) {
  return (
    <div style={{ padding: width / 3 / 3 }}>
      <div
        className="hg-mark-flow"
        style={{ width, height: width / 3 }}
        role="img"
        aria-label="Handsel mark"
      />
    </div>
  );
}
