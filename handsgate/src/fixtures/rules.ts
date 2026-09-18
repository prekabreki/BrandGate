/*
 * GENERATED FILE. Do not edit.
 *
 * Written by handsgate/scripts/rules-to-fixtures.py from brand/rules.json, which
 * the gate scores against. Every sentence below is the designer's, not a paraphrase:
 * the build that paraphrased them was wrong about the mark's clear space and invented
 * a motif rule outright. Change brand/rules.md, rebuild rules.json, run the script.
 */

import type { Rule } from "./types";


export const rules: Rule[] = [
  // Mark
  {
    id: "mark.01",
    section: "Mark",
    prose: "Six pie slices in a 3:1 band, alternating apex down and apex up, the geometry in `tokens.json` under `mark`.",
    check: "band",
  },
  {
    id: null,
    section: "Mark",
    prose: "One gradient flows through all six left to right, deep indigo to rose.",
    check: "manual",
  },
  {
    id: null,
    section: "Mark",
    prose: "Solid variants are ink on light ground and white on dark ground.",
    check: "manual",
  },
  {
    id: null,
    section: "Mark",
    prose: "On night the gradient mark uses the lifted night flow, indigo 6C56FF to pink EC56A8; the paper flow starts too deep to read on black.",
    check: "manual",
  },
  {
    id: "mark.05",
    section: "Mark",
    prose: "A lone slice always carries the whole flow across its own width, never a cut of the band.",
    check: "band",
  },
  {
    id: null,
    section: "Mark",
    prose: "Clear space is one slice radius on every side.",
    check: "manual",
  },
  {
    id: "mark.07",
    section: "Mark",
    prose: "Minimum width is 96 px on screen. The seam between slices is 9 units of the 739 unit band, which is 1.2 px at that size; below it, use the lone slice.",
    check: "band",
  },
  {
    id: "mark.08",
    section: "Mark",
    prose: "The mark is never rotated, mirrored, outlined, or shown with a drop shadow.",
    check: "band",
  },
  {
    id: null,
    section: "Mark",
    prose: "A single slice may stand alone as the avatar or favicon unit.",
    check: "manual",
  },
  {
    id: null,
    section: "Mark",
    prose: "Type beside the mark sets its left edge on the first slice's lowest point, the lower corner of the leftmost slice: 108.3 of the mark's 739 units in from its left edge, 14.65% of its width. The wordmark, headline and tagline share that line. Type never aligns to the mark's left edge.",
    check: "manual",
  },

  // Colour
  {
    id: "colour.01",
    section: "Colour",
    prose: "Grounds are paper `#FAFAF8`, mist `#ECEAF6`, or night `#0D0B18`.",
    check: "palette",
  },
  {
    id: "colour.02",
    section: "Colour",
    prose: "Text is ink `#111114` on light grounds and white on night. Secondary text is graphite `#4A4A55`.",
    check: "contrast",
  },
  {
    id: "colour.03",
    section: "Colour",
    prose: "Indigo `#4B3BE8` is the one flat accent: links, the primary button, a chip border. Magenta is never a flat accent.",
    check: "palette",
  },
  {
    id: "colour.04",
    section: "Colour",
    prose: "No gradient stop is ever used as text.",
    check: "contrast",
  },

  // Gradient
  {
    id: null,
    section: "Gradient",
    prose: "There is one gradient, the flow, and it runs left to right on every surface.",
    check: "manual",
  },
  {
    id: null,
    section: "Gradient",
    prose: "The flow appears on the mark, on display type, and as a ground wash. Nothing else carries it.",
    check: "manual",
  },
  {
    id: "gradient.03",
    section: "Gradient",
    prose: "As a ground it is softened: blurred orbs over paper or night, indigo at the left and magenta warming to rose at the right, bleeding into one another, with a paper veil and film grain over that. No other colour enters the wash. Never the raw ramp.",
    check: "wash",
  },
  {
    id: null,
    section: "Gradient",
    prose: "Display type takes the text variant, which starts from ink so the first word reads as text before it turns.",
    check: "manual",
  },

  // Surface
  {
    id: null,
    section: "Surface",
    prose: "Where there is depth, cards are glass: white at 52 percent, backdrop blur, a one pixel inset specular, the Direction A shadow stack.",
    check: "manual",
  },
  {
    id: null,
    section: "Surface",
    prose: "Where the surface must survive as a flat PNG, cards are paper with a hairline border and no shadow.",
    check: "manual",
  },
  {
    id: null,
    section: "Surface",
    prose: "Film grain at 38 percent overlay on every ground with a wash. None on flat surfaces.",
    check: "manual",
  },

  // Type
  {
    id: null,
    section: "Type",
    prose: "Display is Archivo 800, tracking -0.045 em, line height 0.9, two lines or fewer.",
    check: "manual",
  },
  {
    id: null,
    section: "Type",
    prose: "The wordmark is Handsel in Archivo 800, title case, in the text gradient or in ink.",
    check: "manual",
  },
  {
    id: "type.03",
    section: "Type",
    prose: "Body is Archivo 400 at 17 px, line height 1.5, under 75 characters a line.",
    check: "contrast",
  },
  {
    id: null,
    section: "Type",
    prose: "IBM Plex Mono 400 carries labels, code and data, at 10 to 13 px with 0.14 em tracking when set in caps.",
    check: "manual",
  },

  // Motif
  {
    id: "motif.01",
    section: "Motif",
    prose: "The slice is the only motif. No other geometric shape is used decoratively.",
    check: "motif",
  },
  {
    id: "motif.02",
    section: "Motif",
    prose: "One gesture per surface: the mark, or gradient type, or a slice field. Not two.",
    check: "motif",
  },

  // Motion
  {
    id: null,
    section: "Motion",
    prose: "One orchestrated entrance per surface, a rise of 14 px over 900 ms on a soft curve, staggered by 120 ms.",
    check: "manual",
  },
  {
    id: null,
    section: "Motion",
    prose: "Ground orbs drift for 26 to 38 seconds, alternate, and never faster.",
    check: "manual",
  },
  {
    id: null,
    section: "Motion",
    prose: "Nothing else moves without a user action.",
    check: "manual",
  },

];

export const ruleSections = ["Mark", "Colour", "Gradient", "Surface", "Type", "Motif", "Motion"];
