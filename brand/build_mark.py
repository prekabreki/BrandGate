"""Build the Handsel mark procedurally: six pie slices, one gradient flowing through them.

The mark is geometry plus a gradient, nothing else, so it is generated rather than drawn.
Geometry was measured off lookdev/brand_lookdev_01.psd (six 'Triangle 1' shapes,
193 x 189 px each, pitch 209, stagger 104.5 / 40). Everything downstream, the guide
sheet, the takes, the future anime.js ident, reads the same numbers from tokens.json.

Run from the repo root:  python brand/build_mark.py
Writes brand/logo/*.svg and refreshes the geometry block in brand/tokens.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGO = HERE / "logo"
TOKENS = HERE / "tokens.json"

# --- geometry (native units, one slice = radius 189) -----------------------
R = 189.0            # apex to arc
HALF_DEG = 31.0      # half the apex angle
PITCH = 209.0        # horizontal distance between same-orientation slices
STAGGER_X = 104.5    # up-slices sit half a pitch to the right
STAGGER_Y = 40.0     # and 40 lower
ROUND = 22.0         # stroke width used to round the corners (same paint as the fill)
SEAM = 9.0           # visible gap between neighbouring slices after rounding; 6 vanished below 120 px
# Adjacent straight edges are parallel and 13.5 units apart in the measured layout.
# The rounding stroke grows each shape by ROUND/2, so every edge is drawn inset by
# this much and the stroke brings it back out, leaving exactly SEAM between them.
EDGE_GAP = 13.5
INSET = (SEAM + ROUND - EDGE_GAP) / 2.0


def sector_path(cx: float, cy: float, down: bool) -> str:
    """A pie slice. `down` = apex at the bottom, arc on top.

    The nominal sector has its apex at the circle centre C and radius R. The drawn
    shape is that sector with both straight edges and the arc moved inward by INSET,
    so the corner-rounding stroke restores the nominal silhouette.
    """
    a = math.radians(HALF_DEG)
    sign = 1.0 if down else -1.0
    cxn, cyn = cx, cy + sign * R / 2.0              # nominal apex = circle centre
    r = R - INSET                                   # inset arc radius
    # Inset apex sits INSET / sin(a) further along the axis, away from the arc side.
    ax, ay = cxn, cyn - sign * INSET / math.sin(a)
    pts = []
    for side in (-1.0, 1.0):
        # Unit direction of the inset edge, parallel to the nominal edge.
        ux, uy = side * math.sin(a), -sign * math.cos(a)
        # Solve |A + t u - C| = r for t > 0.
        dx, dy = ax - cxn, ay - cyn
        b = 2 * (dx * ux + dy * uy)
        c = dx * dx + dy * dy - r * r
        t = (-b + math.sqrt(b * b - 4 * c)) / 2.0
        pts.append((ax + t * ux, ay + t * uy))
    p1, p2 = pts
    sweep = 1 if down else 0
    return (f"M {ax:.2f} {ay:.2f} L {p1[0]:.2f} {p1[1]:.2f} "
            f"A {r:.2f} {r:.2f} 0 0 {sweep} {p2[0]:.2f} {p2[1]:.2f} Z")


def slices() -> list[tuple[float, float, bool]]:
    out = []
    for i in range(3):
        out.append((i * PITCH, 0.0, True))                      # down
        out.append((i * PITCH + STAGGER_X, STAGGER_Y, False))   # up
    return out


def bbox() -> tuple[float, float, float, float]:
    a = math.radians(HALF_DEG)
    half_w = R * math.sin(a)
    xs = [cx for cx, _, _ in slices()]
    ys = [cy for _, cy, _ in slices()]
    pad = ROUND / 2.0
    return (min(xs) - half_w - pad, min(ys) - R / 2.0 - pad,
            max(xs) + half_w + pad, max(ys) + R / 2.0 + pad)


# --- paint ----------------------------------------------------------------
FLOW_STOPS = [  # left to right, the one gradient the whole brand shares
    (0.00, "#1E1A5C"),  # deep indigo, almost ink
    (0.28, "#4B3BE8"),  # indigo, Direction A primary
    (0.50, "#7A4FE0"),  # violet, the seam
    (0.74, "#B44C9E"),  # magenta, Direction A secondary
    (1.00, "#D9628A"),  # rose, the only warmth
]


def silhouette(paint: str, shapes=None) -> str:
    shapes = slices() if shapes is None else shapes
    return "".join(f'<path d="{sector_path(cx, cy, down)}" fill="{paint}" stroke="{paint}" '
                   f'stroke-width="{ROUND}" stroke-linejoin="round"/>' for cx, cy, down in shapes)


def svg(paints: list[str], defs: str = "", background: str | None = None) -> str:
    """The first paint is the silhouette itself. Any further paints are semi-transparent
    overlays, drawn as a rect through a mask of that silhouette. Drawing them as
    fill-plus-stroke paths instead doubles the alpha where stroke overlaps fill and
    leaves a visible rim along every seam."""
    x0, y0, x1, y1 = bbox()
    w, h = x1 - x0, y1 - y0
    body = []
    if background:
        body.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{background}"/>')
    body.append(silhouette(paints[0]))
    mask = ""
    if len(paints) > 1:
        mask = f'<mask id="sil" maskUnits="userSpaceOnUse" x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}">{silhouette("#fff")}</mask>'
        for paint in paints[1:]:
            body.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{paint}" mask="url(#sil)"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" '
            f'width="{w:.0f}" height="{h:.0f}">\n<defs>{defs}{mask}</defs>\n' + "\n".join(body) + "\n</svg>\n")


def flow_defs() -> str:
    """The flow: a left-to-right ramp, plus two soft radial washes that give it the
    diagonal warmth of the raster in the PSD (lemon high right, sky low left)."""
    x0, y0, x1, y1 = bbox()
    stops = "".join(f'<stop offset="{o:.2f}" stop-color="{c}"/>' for o, c in FLOW_STOPS)
    return (
        f'<linearGradient id="flow" gradientUnits="userSpaceOnUse" x1="{x0:.1f}" y1="0" x2="{x1:.1f}" y2="0">{stops}</linearGradient>'
        f'<radialGradient id="warm" gradientUnits="userSpaceOnUse" cx="{x1 - 60:.1f}" cy="{y0 + 20:.1f}" r="{(x1 - x0) * 0.55:.1f}">'
        f'<stop offset="0" stop-color="#F078BE" stop-opacity="0.55"/><stop offset="0.5" stop-color="#F078BE" stop-opacity="0.15"/><stop offset="1" stop-color="#F078BE" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="cool" gradientUnits="userSpaceOnUse" cx="{x0 + 200:.1f}" cy="{y1 - 20:.1f}" r="{(x1 - x0) * 0.42:.1f}">'
        f'<stop offset="0" stop-color="#56A4F8" stop-opacity="0.55"/><stop offset="1" stop-color="#56A4F8" stop-opacity="0"/></radialGradient>'
    )


FLOW_PAINTS = ["url(#flow)", "url(#warm)", "url(#cool)"]

# On night grounds the flow's deep start disappears into the black. Direction A2
# already answered this with a lifted pair, indigo 6C56FF to pink EC56A8, so the
# night variant of the mark uses those.
FLOW_STOPS_NIGHT = [
    (0.00, "#6C56FF"),
    (0.45, "#8E63FF"),
    (0.75, "#C25CCB"),
    (1.00, "#EC56A8"),
]


def flow_defs_for(stops, x0, x1, y0, y1, gid="flow"):
    """A flow spanning exactly x0..x1, with the two washes scaled to that span."""
    st = "".join(f'<stop offset="{o:.2f}" stop-color="{c}"/>' for o, c in stops)
    w = x1 - x0
    return (
        f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{x0:.1f}" y1="0" x2="{x1:.1f}" y2="0">{st}</linearGradient>'
        f'<radialGradient id="warm" gradientUnits="userSpaceOnUse" cx="{x1 - w*0.08:.1f}" cy="{y0 + (y1-y0)*0.1:.1f}" r="{w*0.55:.1f}">'
        f'<stop offset="0" stop-color="#F078BE" stop-opacity="0.5"/><stop offset="0.5" stop-color="#F078BE" stop-opacity="0.15"/><stop offset="1" stop-color="#F078BE" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="cool" gradientUnits="userSpaceOnUse" cx="{x0 + w*0.27:.1f}" cy="{y1 - (y1-y0)*0.1:.1f}" r="{w*0.42:.1f}">'
        f'<stop offset="0" stop-color="#56A4F8" stop-opacity="0.45"/><stop offset="1" stop-color="#56A4F8" stop-opacity="0"/></radialGradient>'
    )


def main() -> None:
    LOGO.mkdir(exist_ok=True)
    x0, y0, x1, y1 = bbox()
    (LOGO / "slice-mark.svg").write_text(svg(FLOW_PAINTS, flow_defs()), encoding="utf-8")
    (LOGO / "slice-mark-night.svg").write_text(
        svg(FLOW_PAINTS, flow_defs_for(FLOW_STOPS_NIGHT, x0, x1, y0, y1)), encoding="utf-8")
    (LOGO / "slice-mark-ink.svg").write_text(svg(["#111114"]), encoding="utf-8")
    (LOGO / "slice-mark-white.svg").write_text(svg(["#FFFFFF"]), encoding="utf-8")
    (LOGO / "slice-mark-blank.svg").write_text(svg(["#E5E5E5"]), encoding="utf-8")

    # One slice on its own: the avatar and favicon unit. The whole flow runs across
    # this one slice, so it never inherits only the dark end of the band.
    single = [(0.0, 0.0, True)]
    a = math.radians(HALF_DEG)
    hw = R * math.sin(a) + ROUND / 2
    for name, stops in (("slice-one.svg", FLOW_STOPS), ("slice-one-night.svg", FLOW_STOPS_NIGHT)):
        one = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-110 -110 220 220" width="220" height="220">'
               f'<defs>{flow_defs_for(stops, -hw, hw, -R/2 - ROUND/2, R/2 + ROUND/2)}'
               f'<mask id="one" maskUnits="userSpaceOnUse" x="-110" y="-110" width="220" height="220">{silhouette("#fff", single)}</mask></defs>'
               + silhouette(FLOW_PAINTS[0], single)
               + "".join(f'<rect x="-110" y="-110" width="220" height="220" fill="{p}" mask="url(#one)"/>' for p in FLOW_PAINTS[1:])
               + "</svg>" + chr(10))
        (LOGO / name).write_text(one, encoding="utf-8")

    tokens = json.loads(TOKENS.read_text(encoding="utf-8")) if TOKENS.exists() else {}
    x0, y0, x1, y1 = bbox()
    tokens["mark"] = {
        "radius": R, "half_angle_deg": HALF_DEG, "pitch": PITCH,
        "stagger": [STAGGER_X, STAGGER_Y], "corner_round": ROUND,
        "viewBox": [round(x0, 1), round(y0, 1), round(x1 - x0, 1), round(y1 - y0, 1)],
        "aspect": round((x1 - x0) / (y1 - y0), 3),
        "slices": [{"cx": cx, "cy": cy, "down": d} for cx, cy, d in slices()],
    }
    def css(stops):
        return "linear-gradient(90deg, " + ", ".join(f"{c} {o*100:.0f}%" for o, c in stops) + ")"
    tokens["mark"]["seam"] = SEAM
    tokens["mark"]["seam_note"] = "Gap between slices in band units; 1.2 px at the 96 px minimum width."
    # Both gradients live here so a rebuild never drops one the way the 09-14 seam change did.
    tokens["gradient"] = {
        "flow": {"angle_deg": 90, "stops": [{"offset": o, "color": c} for o, c in FLOW_STOPS], "css": css(FLOW_STOPS)},
        "css": css(FLOW_STOPS),
        "flow_night": {"stops": [{"offset": o, "color": c} for o, c in FLOW_STOPS_NIGHT], "css": css(FLOW_STOPS_NIGHT)},
    }
    TOKENS.write_text(json.dumps(tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", sorted(p.name for p in LOGO.glob("*.svg")), "viewBox", tokens["mark"]["viewBox"])


if __name__ == "__main__":
    main()
