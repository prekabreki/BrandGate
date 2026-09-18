import type { Rule } from "./types";

export const rules: Rule[] = [
  // Mark
  {
    id: null,
    section: "Mark",
    prose: "The mark is six pie slices in a 3:1 band, alternating apex down and apex up.",
    check: "manual",
  },
  {
    id: null,
    section: "Mark",
    prose: "One flow gradient runs across all six slices, left to right.",
    check: "manual",
  },
  {
    id: "mark.02",
    section: "Mark",
    prose: "The mark keeps clear space of a third of its height on every side and sets no smaller than 96 px wide.",
    check: "manual",
  },
  {
    id: null,
    section: "Mark",
    prose: "The mark is never rotated, mirrored, outlined or shadowed.",
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
    prose:
      "Text is ink `#111114` on light grounds and white on night. Secondary text is graphite `#4A4A55`.",
    check: "contrast",
  },
  {
    id: "colour.03",
    section: "Colour",
    prose:
      "Indigo `#4B3BE8` is the one flat accent: links, the primary button, a chip border. Magenta is never a flat accent.",
    check: "palette",
  },
  {
    id: "colour.04",
    section: "Colour",
    prose: "No gradient stop is ever used as text.",
    check: "palette",
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
    prose:
      "The flow appears on the mark, on display type, and as a ground wash. Nothing else carries it.",
    check: "manual",
  },
  {
    id: "gradient.03",
    section: "Gradient",
    prose:
      "As a ground it is softened: blurred orbs over paper or night, indigo at the left and magenta warming to rose at the right, bleeding into one another, with a paper veil and film grain over that. No other colour enters the wash. Never the raw ramp.",
    check: "wash",
  },
  {
    id: null,
    section: "Gradient",
    prose:
      "Display type takes the text variant, which starts from ink so the first word reads as text before it turns.",
    check: "manual",
  },

  // Surface
  {
    id: null,
    section: "Surface",
    prose: "The ground is paper or night, always under the wash and the grain.",
    check: "manual",
  },
  {
    id: "surface.02",
    section: "Surface",
    prose: "A panel on the wash is glass: blurred, saturated, with a light inner edge.",
    check: "manual",
  },
  {
    id: null,
    section: "Surface",
    prose: "Radius is 22 px on glass panels and 6 px on inputs and chips. Nothing else.",
    check: "manual",
  },
  {
    id: null,
    section: "Surface",
    prose: "Film grain sits at 38 percent over the wash, never over an image.",
    check: "manual",
  },

  // Type
  {
    id: null,
    section: "Type",
    prose: "Display is Archivo 800, tracking -0.045em, line height 0.9, never more than two lines.",
    check: "manual",
  },
  {
    id: "type.03",
    section: "Type",
    prose: "Body is Archivo 400 at 17 px, line height 1.5, under 75 characters a line.",
    check: "band",
  },
  {
    id: null,
    section: "Type",
    prose: "Labels, data, code and rule ids set in IBM Plex Mono at 10 to 13 px.",
    check: "manual",
  },
  {
    id: null,
    section: "Type",
    prose: "Mono set in caps carries 0.14em tracking.",
    check: "manual",
  },

  // Motif
  {
    id: null,
    section: "Motif",
    prose: "The recurring motif is the band: a 3:1 strip carrying the flow.",
    check: "manual",
  },
  {
    id: null,
    section: "Motif",
    prose: "Strings are plain sentences in sentence case and present tense.",
    check: "manual",
  },
  {
    id: null,
    section: "Motif",
    prose: "No exclamation marks, no marketing adjectives, no emoji.",
    check: "manual",
  },

  // Motion
  {
    id: "motion.01",
    section: "Motion",
    prose: "Orbs drift over 26 to 38 seconds in alternating directions, and nothing moves faster.",
    check: "manual",
  },
  {
    id: "motion.02",
    section: "Motion",
    prose: "Panels rise 14 px over 900 ms on a soft ease, staggered 120 ms, once on load.",
    check: "manual",
  },
  {
    id: null,
    section: "Motion",
    prose: "Hover changes colour and nothing else.",
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
