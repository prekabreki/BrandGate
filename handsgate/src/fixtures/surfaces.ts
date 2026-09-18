/*
 * The real renders, cut into public/surfaces by scripts/tokens-to-tailwind.py. These
 * slots used to hold hand-drawn SVG gradients: abstract shapes under the labels HERO,
 * SOCIAL, PRINT and MOTION, captioned with the real scores below. A picture of a
 * surface that was never made, sitting beside that surface's genuine verdict.
 */
const heroAccepted = "/surfaces/hero-accepted.jpg";
const heroRejected = "/surfaces/hero-rejected.jpg";
const motionAccepted = "/surfaces/motion-accepted.jpg";
const motionRejected = "/surfaces/motion-rejected.jpg";
const printAccepted = "/surfaces/print-accepted.jpg";
const printRejected = "/surfaces/print-rejected.jpg";
const socialAccepted = "/surfaces/social-accepted.jpg";
const socialRejected = "/surfaces/social-rejected.jpg";
import type { Surface } from "./types";

const thresholds = { on_brand_min: 0.75, novelty_min: 0.12 };

export const surfaces: Surface[] = [
  {
    id: "hero",
    accepted: {
      image: heroAccepted,
      score: {
        verdict: "pass",
        on_brand: 0.9662,
        novelty: 0.31,
        thresholds,
        failed_rules: [],
        breakdown: [
          {
            rule: "colour.01",
            check: "palette",
            score: 0.9,
            passed: true,
            reason: "the ground is #FAFAF8",
            detail: { ground: "#FAFAF8" },
          },
          {
            rule: "colour.02",
            check: "contrast",
            score: 1,
            passed: true,
            reason: "every text region clears 4.5:1 (worst 12.1:1)",
            detail: { worst_ratio: 12.1 },
          },
          {
            rule: "colour.03",
            check: "palette",
            score: 1,
            passed: true,
            reason: "the one flat accent is #4B3BE8",
            detail: { flat_accents: ["#4B3BE8"] },
          },
          {
            rule: "colour.04",
            check: "palette",
            score: 1,
            passed: true,
            reason: "no gradient stop is used as text",
            detail: { text_colours: ["#111114", "#4A4A55"] },
          },
          {
            rule: "gradient.03",
            check: "wash",
            score: 1,
            passed: true,
            reason: "soft wash: darks at chroma 56, edges 5.2, every stop present",
            detail: { dark_chroma: 56, edge_energy: 5.2, stops_present: 5 },
          },
          {
            rule: "type.03",
            check: "band",
            score: 0.96,
            passed: true,
            reason: "body sets at 17 px, line height 1.5, 68 characters a line",
            detail: { size_px: 17, measure: 68 },
          },
        ],
        not_applicable: [
          { rule: "mark.02", check: "manual", reason: "the mark is not present on this surface" },
          { rule: "motion.01", check: "manual", reason: "the surface is a still frame" },
        ],
      },
    },
    rejected: {
      image: heroRejected,
      score: {
        verdict: "fail",
        on_brand: 0.84,
        novelty: 0.44,
        thresholds,
        failed_rules: ["gradient.03", "colour.01"],
        breakdown: [
          {
            rule: "gradient.03",
            check: "wash",
            score: 0.891,
            passed: false,
            reason: "the wash is dull (mean chroma 27, a ground carries at least 30)",
            detail: { mean_chroma: 27, minimum: 30 },
          },
          {
            rule: "colour.01",
            check: "palette",
            score: 0.63,
            passed: false,
            reason: "the ground is #ECEAF6",
            detail: { ground: "#ECEAF6" },
          },
          {
            rule: "colour.03",
            check: "palette",
            score: 1,
            passed: true,
            reason: "the one flat accent is #4B3BE8",
            detail: { flat_accents: ["#4B3BE8"] },
          },
          {
            rule: "colour.04",
            check: "palette",
            score: 1,
            passed: true,
            reason: "no gradient stop is used as text",
            detail: { text_colours: ["#111114"] },
          },
          {
            rule: "type.03",
            check: "band",
            score: 0.88,
            passed: true,
            reason: "body sets at 17 px, line height 1.5, 79 characters a line",
            detail: { size_px: 17, measure: 79 },
          },
        ],
        not_applicable: [
          { rule: "mark.02", check: "manual", reason: "the mark is not present on this surface" },
        ],
      },
    },
  },
  {
    id: "social",
    accepted: {
      image: socialAccepted,
      score: {
        verdict: "pass",
        on_brand: 0.9214,
        novelty: 0.27,
        thresholds,
        failed_rules: [],
        breakdown: [
          {
            rule: "colour.01",
            check: "palette",
            score: 1,
            passed: true,
            reason: "the ground is #0D0B18",
            detail: { ground: "#0D0B18" },
          },
          {
            rule: "colour.02",
            check: "contrast",
            score: 0.94,
            passed: true,
            reason: "every text region clears 4.5:1 (worst 6.7:1)",
            detail: { worst_ratio: 6.7 },
          },
          {
            rule: "colour.03",
            check: "palette",
            score: 0.87,
            passed: true,
            reason: "the one flat accent is #4B3BE8",
            detail: { flat_accents: ["#4B3BE8"] },
          },
          {
            rule: "gradient.03",
            check: "wash",
            score: 0.93,
            passed: true,
            reason: "soft wash: darks at chroma 48, edges 6.1, every stop present",
            detail: { dark_chroma: 48, edge_energy: 6.1, stops_present: 5 },
          },
          {
            rule: "type.03",
            check: "band",
            score: 0.9,
            passed: true,
            reason: "body sets at 17 px, line height 1.5, 61 characters a line",
            detail: { size_px: 17, measure: 61 },
          },
        ],
        not_applicable: [
          { rule: "motion.01", check: "manual", reason: "the surface is a still frame" },
        ],
      },
    },
    rejected: {
      image: socialRejected,
      score: {
        verdict: "fail",
        on_brand: 0.7,
        novelty: 0.51,
        thresholds,
        failed_rules: ["colour.03", "colour.04"],
        breakdown: [
          {
            rule: "colour.03",
            check: "palette",
            score: 0.42,
            passed: false,
            reason: "magenta #B44C9E is set as a flat accent on the button",
            detail: { flat_accents: ["#B44C9E"] },
          },
          {
            rule: "colour.04",
            check: "palette",
            score: 0.55,
            passed: false,
            reason: "the headline is filled with rose #D9628A",
            detail: { text_colours: ["#D9628A"] },
          },
          {
            rule: "colour.01",
            check: "palette",
            score: 1,
            passed: true,
            reason: "the ground is #0D0B18",
            detail: { ground: "#0D0B18" },
          },
          {
            rule: "gradient.03",
            check: "wash",
            score: 0.86,
            passed: true,
            reason: "soft wash: darks at chroma 41, edges 6.8, every stop present",
            detail: { dark_chroma: 41, edge_energy: 6.8, stops_present: 5 },
          },
        ],
        not_applicable: [
          { rule: "motion.01", check: "manual", reason: "the surface is a still frame" },
        ],
      },
    },
  },
  {
    id: "print",
    accepted: {
      image: printAccepted,
      score: {
        verdict: "pass",
        on_brand: 1,
        novelty: 0.19,
        thresholds,
        failed_rules: [],
        breakdown: [
          {
            rule: "colour.01",
            check: "palette",
            score: 1,
            passed: true,
            reason: "the ground is #FAFAF8",
            detail: { ground: "#FAFAF8" },
          },
          {
            rule: "colour.02",
            check: "contrast",
            score: 1,
            passed: true,
            reason: "every text region clears 4.5:1 (worst 8.4:1)",
            detail: { worst_ratio: 8.4 },
          },
          {
            rule: "colour.03",
            check: "palette",
            score: 1,
            passed: true,
            reason: "the one flat accent is #4B3BE8",
            detail: { flat_accents: ["#4B3BE8"] },
          },
          {
            rule: "colour.04",
            check: "palette",
            score: 1,
            passed: true,
            reason: "no gradient stop is used as text",
            detail: { text_colours: ["#111114", "#4A4A55"] },
          },
          {
            rule: "type.03",
            check: "band",
            score: 1,
            passed: true,
            reason: "body sets at 17 px, line height 1.5, 66 characters a line",
            detail: { size_px: 17, measure: 66 },
          },
        ],
        not_applicable: [
          { rule: "motion.01", check: "manual", reason: "print does not move" },
          { rule: "surface.02", check: "manual", reason: "glass does not survive ink on paper" },
        ],
      },
    },
    rejected: {
      image: printRejected,
      score: {
        verdict: "fail",
        on_brand: 0.72,
        novelty: 0.38,
        thresholds,
        failed_rules: ["colour.02"],
        breakdown: [
          {
            rule: "colour.02",
            check: "contrast",
            score: 0.49,
            passed: false,
            reason: "the caption clears only 3.1:1 against the wash",
            detail: { worst_ratio: 3.1 },
          },
          {
            rule: "colour.01",
            check: "palette",
            score: 1,
            passed: true,
            reason: "the ground is #FAFAF8",
            detail: { ground: "#FAFAF8" },
          },
          {
            rule: "gradient.03",
            check: "wash",
            score: 0.81,
            passed: true,
            reason: "soft wash: darks at chroma 34, edges 7.4, every stop present",
            detail: { dark_chroma: 34, edge_energy: 7.4, stops_present: 5 },
          },
          {
            rule: "type.03",
            check: "band",
            score: 0.77,
            passed: true,
            reason: "body sets at 17 px, line height 1.5, 74 characters a line",
            detail: { size_px: 17, measure: 74 },
          },
        ],
        not_applicable: [{ rule: "motion.01", check: "manual", reason: "print does not move" }],
      },
    },
  },
  {
    id: "motion",
    accepted: {
      image: motionAccepted,
      score: {
        verdict: "pass",
        on_brand: 0.8843,
        novelty: 0.35,
        thresholds,
        failed_rules: [],
        breakdown: [
          {
            rule: "colour.01",
            check: "palette",
            score: 1,
            passed: true,
            reason: "the ground is #0D0B18",
            detail: { ground: "#0D0B18" },
          },
          {
            rule: "colour.03",
            check: "palette",
            score: 0.92,
            passed: true,
            reason: "the one flat accent is #4B3BE8",
            detail: { flat_accents: ["#4B3BE8"] },
          },
          {
            rule: "gradient.03",
            check: "wash",
            score: 0.88,
            passed: true,
            reason: "soft wash: darks at chroma 44, edges 5.9, every stop present",
            detail: { dark_chroma: 44, edge_energy: 5.9, stops_present: 4 },
          },
          {
            rule: "type.03",
            check: "band",
            score: 0.85,
            passed: true,
            reason: "body sets at 17 px, line height 1.5, 58 characters a line",
            detail: { size_px: 17, measure: 58 },
          },
        ],
        not_applicable: [
          { rule: "motion.02", check: "manual", reason: "orb drift is read by eye, not by the gate" },
        ],
      },
    },
    rejected: {
      image: motionRejected,
      score: {
        verdict: "fail",
        on_brand: 0.66,
        novelty: 0.62,
        thresholds,
        failed_rules: ["gradient.03"],
        breakdown: [
          {
            rule: "gradient.03",
            check: "wash",
            score: 0.52,
            passed: false,
            reason: "the raw ramp runs across the frame, unsoftened",
            detail: { edge_energy: 22.6, blur_px: 0 },
          },
          {
            rule: "colour.01",
            check: "palette",
            score: 1,
            passed: true,
            reason: "the ground is #0D0B18",
            detail: { ground: "#0D0B18" },
          },
          {
            rule: "colour.04",
            check: "palette",
            score: 1,
            passed: true,
            reason: "no gradient stop is used as text",
            detail: { text_colours: ["#FFFFFF"] },
          },
        ],
        not_applicable: [
          { rule: "motion.02", check: "manual", reason: "orb drift is read by eye, not by the gate" },
        ],
      },
    },
  },
];

export const surfaceById = (id: string) => surfaces.find((s) => s.id === id) ?? surfaces[0]!;
