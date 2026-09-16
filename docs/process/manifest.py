"""The record of every review round on BrandGate #22, in order. Append, never edit."""

V3 = [("v3, seed 2000", "hero-ground_turbo_2000_"), ("v3, seed 2001", "hero-ground_turbo_2001_")]
TARGET = {"title": "Target", "frames": [("v7, seed 6002", "hero-ground_turbo_6002_")]}

ENTRIES = [
    {
        "slug": "2026-09-16-01-v4-watercolour", "short": "v4 sheet", "date": "2026-09-16",
        "title": "hero-ground v4 beside v3",
        "lede": "The v4 prompt (lighter, paper dominant, a bleed not orbs, no black) after the 09-15 review "
                "of the shipped grounds: too blobby, too much black, saturation too high. Forty frames were "
                "on the labelling page beside their v3 seed-mates; the first pairs are kept here.",
        "sections": [
            {"title": "v4 beside v3", "text": "Left v4, right v3, same row, same seed offset.",
             "frames": [("v4, seed 3000", "hero-ground_turbo_3000_"), V3[0],
                        ("v4, seed 3001", "hero-ground_turbo_3001_"), V3[1],
                        ("v4, seed 3002", "hero-ground_turbo_3002_"), ("v3, seed 2002", "hero-ground_turbo_2002_")]},
        ],
        "verdict": "Before labelling: they are all very diffuse watercolour-esque images. Not a bad effect but a big "
                   "departure from v3. A version between v3 and v4 is probably closer: the excellent colour blending "
                   "and texture from the watercolour with the more defined shapes (but not too defined) of v3, and a "
                   "saturation level between v3 and v4. No labels were recorded.",
    },
    {
        "slug": "2026-09-16-02-v5-midpoint", "short": "v5 preview", "date": "2026-09-16",
        "title": "v5, the midpoint",
        "lede": "Two frames of v5 (watercolour blending, v3's readable masses at half their definition, saturation "
                "between the two) shown before the batch finished, with v4 and v3 seed-mates for reference.",
        "sections": [
            {"title": "v5", "frames": [("v5, seed 4000", "hero-ground_turbo_4000_"), ("v5, seed 4001", "hero-ground_turbo_4001_")]},
            {"title": "v4 and v3 for reference",
             "frames": [("v4, seed 3000", "hero-ground_turbo_3000_"), ("v4, seed 3001", "hero-ground_turbo_3001_")] + V3},
        ],
        "verdict": "This is way too watercolour heavy, we need to aim for a modern looking webpage. Mesh gradients "
                   "with interesting grain basically. The batch was stopped at two frames.",
    },
    {
        "slug": "2026-09-16-03-v6-mesh", "short": "v6 preview", "date": "2026-09-16",
        "title": "v6, a mesh gradient",
        "lede": "No watercolour language left in the prompt: a digital mesh gradient with grain as the only texture.",
        "sections": [
            {"title": "v6", "frames": [("v6, seed 5000", "hero-ground_turbo_5000_"), ("v6, seed 5001", "hero-ground_turbo_5001_")]},
            {"title": "v3 for reference", "frames": V3},
        ],
        "verdict": "v6 looks muddy. seed 5001 is slightly better. Also asked, as a question not a direction: is "
                   "ComfyUI the wrong tool for these, should a mesh gradient generator come first and the model add "
                   "grain and artifacts on top? Worth a spike.",
    },
    {
        "slug": "2026-09-16-04-two-routes", "short": "two routes", "date": "2026-09-16",
        "title": "two routes to the ground",
        "lede": "Route A: a procedural mesh from the brand's flow stops, blended in OKLab, grain on top, no model. "
                "Route B: prompt v7, clean, luminous, no grey, with the 5001 diagonal sweep named.",
        "sections": [
            {"title": "A. Procedural mesh, first spike",
             "text": "Five control points, one per token stop, on a diagonal sweep. Blended in OKLab so no seam passes through grey.",
             "frames": [("mesh, seed 1", "mesh_1_v0.3_g0.03"), ("mesh, seed 2", "mesh_2_v0.3_g0.03"), ("mesh, seed 3", "mesh_3_v0.3_g0.03"),
                        ("the very first attempt, linear-light blend: everything averaged to lavender", "mesh_1_v0.55_g0.035")]},
            {"title": "B. v7, model only",
             "frames": [("v7, seed 6000", "hero-ground_turbo_6000_"), ("v7, seed 6001", "hero-ground_turbo_6001_"), ("v7, seed 6002", "hero-ground_turbo_6002_")]},
            {"title": "C. v6 5001 for reference", "frames": [("v6, seed 5001", "hero-ground_turbo_5001_")]},
        ],
        "verdict": "v7 seed 6002 is my favourite. Procedural mesh lacks colour depth and they have a dark line going "
                   "through them diagonally. Might be worth taking another shot at procedural mesh and try to match "
                   "the saturation and hues of v7?",
    },
    {
        "slug": "2026-09-16-05-band-a2", "short": "band A2", "date": "2026-09-16",
        "title": "procedural band, second shot",
        "lede": "No control-point blobs, so no seam: one flow of colour along the top with eight stops sampled from "
                "6002 itself, fading down into paper along a curved edge, blended in OKLab.",
        "sections": [
            TARGET,
            {"title": "A2, long fade", "frames": [(f"band A2, seed {i}", f"band_v7_{i}_c1.0_s0.6") for i in (1, 2, 3)]},
            {"title": "A2, shorter fade", "frames": [(f"band A2 short, seed {i}", f"band_v7_{i}_c1.0") for i in (1, 2)]},
            {"title": "The brand tokens instead",
             "text": "The tokens.json flow stops at 1.25x chroma. The token indigo is bluer and hotter than anything in 6002.",
             "frames": [("band, token stops", "band_brand_1_c1.25")]},
        ],
        "verdict": "A2 is much closer but still v7 is better. I think it might also have to do with the length of "
                   "the falloff. V7 has a very nice and long gradual falloff while the bands have a tighter falloff.",
    },
    {
        "slug": "2026-09-16-06-band-a3", "short": "band A3", "date": "2026-09-16",
        "title": "procedural band, third shot",
        "lede": "The vertical chroma falloff was read off 6002 at five columns and the band fitted to it: colour holds "
                "to a third of the way down at the left, decays over half the frame, paper keeps a tenth of the colour.",
        "sections": [
            TARGET,
            {"title": "A3", "frames": [(f"band A3, seed {i}", f"band_v7_{i}_c1.0_s0.55_fit") for i in (1, 2, 3)]},
        ],
        "verdict": "The edges are wobbly, so instead of the two big waves of v7 we have 3-4 waves. In A3 the purple "
                   "is overpowering, there is a large solid blob of purple.",
    },
    {
        "slug": "2026-09-16-07-band-a4", "short": "band A4", "date": "2026-09-16",
        "title": "procedural band, fourth shot",
        "lede": "One long edge wave. Lightness lifts from the very top as 6002's does (measured), while chroma holds "
                "to the edge, so the indigo no longer sits as one solid block.",
        "sections": [
            TARGET,
            {"title": "A4", "frames": [(f"band A4, seed {i}", f"band_v7_{i}_c1.0_s0.55_fit2") for i in (1, 2, 3)]},
        ],
        "verdict": "Better but now the wave amplitude is too low and the seam between white and the gradient is too "
                   "visible. It really should be a very gradual (and eventually film grained) falloff.",
    },
    {
        "slug": "2026-09-16-08-band-a5", "short": "band A5", "date": "2026-09-16",
        "title": "procedural band, fifth shot",
        "lede": "The hold-then-ramp replaced by a gaussian tail with no corner. Chroma lets go later than lightness so "
                "the fade stays a colour. Grain peaks across the falloff. Wave amplitude tripled. One overshoot in "
                "between (the fade ran the whole frame) is kept here too.",
        "sections": [
            TARGET,
            {"title": "A5", "frames": [(f"band A5, seed {i}", f"band_v7_{i}_c1.0_s0.5_fit5") for i in (1, 2, 3)]},
            {"title": "The overshoot, not shown at the time",
             "text": "Softness 0.75: no paper left and the wave vanished inside the tail.",
             "frames": [("overshoot, seed 2", "band_v7_2_c1.0_s0.75_fit3")]},
        ],
        "verdict": "A5 has reached v7.",
    },
    {
        "slug": "2026-09-16-09-composed", "short": "composed", "date": "2026-09-16",
        "title": "the surfaces on the mesh ground",
        "lede": "Every surface recomposed on the procedural ground (seed 2), with hero-ground@6 seed 5000, "
                "the frame called muddy, as the refused candidate beside each. The templates' paper veil "
                "is gone from the top of the ground and kept at the foot for the type; under the old veil "
                "the mesh read at mean chroma 23 where the bare ground scored 38. Gate verdicts in the captions.",
        "sections": [
            {"title": "Hero", "text": "Accepted ground: pass 0.95. Composed: gradient.03 fails by a hair, darks at chroma 56.1 against a bar of 55.5 that was set on a 1.6-unit gap. Refused: fail, the wash is dull.",
             "frames": [("hero on the mesh ground, 1600 by 900", "surfaces/hero/accepted/hero.png"),
                        ("hero on the refused ground (v6 5000)", "surfaces/hero/rejected/hero.png")]},
            {"title": "Cards", "text": "Square pass 0.97, story pass 1.00, link card fails gradient.03 the same hair (55.8).",
             "frames": [("square", "surfaces/social/accepted/square.png"), ("square, refused ground", "surfaces/social/rejected/square.png"),
                        ("story", "surfaces/social/accepted/story.png"), ("story, refused ground", "surfaces/social/rejected/story.png"),
                        ("link card", "surfaces/social/accepted/og.png"), ("link card, refused ground", "surfaces/social/rejected/og.png")]},
            {"title": "Print", "text": "A4, the band shows the right seven tenths of the ground as before. Fails only on the contrast check reading the mark as text at 4.2:1, the frozen #21 fault.",
             "frames": [("one-pager", "surfaces/print/accepted/onepager.png"), ("one-pager, refused ground", "surfaces/print/rejected/onepager.png")]},
        ],
        "verdict": "",
    },
]
