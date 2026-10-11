# ADR 0002: Evaluate with scale-free measures, not pixel IoU

- **Status:** accepted
- **Date:** 2026-10-11

## Context

The obvious way to score a wall detector is pixel IoU against the labels. In CubiCasa5k the SVG labels are not aligned with the images: on 60 test plans, four conventions (stretch, isotropic by width, by height, by the smaller ratio) each put only ~9-10% of labelled wall pixels on dark pixels. The label coordinate frame does not map onto the image by scaling alone.

## Decision

Compare quantities that do not depend on the pixel frame: whether a room is found, and wall length / sqrt(interior area), computed independently from the labels and from the prediction. Choose any tunable setting on the validation split and run the test split once.

## Consequences

✅ Measures the plan's shape, not the annotation offset.
⚠️ Weak: it can be matched by accident and says nothing about absolute area. It is a smoke test for the baseline, not the accuracy claim for the product.
⚠️ The real accuracy claim needs real Spanish plans with measured areas (roadmap P2 done-criteria).

## Revisit when

A per-plan alignment of labels to images is available, or real plans with known areas arrive: then measure area and length error directly.
