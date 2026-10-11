# ADR 0002: Label frame and evaluation (corrected)

- **Status:** accepted, **supersedes the first version of this ADR, which was wrong**
- **Date:** 2026-10-11

## What the first version said, and why it was wrong

It claimed the CubiCasa5k SVG labels are not aligned with the images, and chose scale-free measures instead of pixel IoU. The claim came from testing four *scaling* conventions (stretch to the image size, isotropic by width, by height, by the smaller ratio); each put only ~10% of labelled wall pixels on dark pixels. I took that as proof of misalignment. It was a wrong test twice over: none of the conventions was the right one, and "dark pixel" is a poor check for walls drawn as hatching.

## Evidence for the correct mapping

The dataset's own loader (`floortrans/loaders/house.py`, CubiCasa5k repo) allocates the label grid from the image shape and uses the SVG polygon coordinates directly as pixel indices: no scaling, no offset, and the SVG `width`/`height` attributes are never read. An overlay of the wall polygons on `F1_scaled.png` with identity mapping lines up with the walls.

## Decision

Label polygons are pixel coordinates of `F1_scaled.png`. Image and labels are resized together by one factor. Evaluation is pixel IoU / precision / recall of the wall mask and IoU of the interior mask. Any tunable setting is chosen on the validation split; the test split is run once.

## Consequences

✅ A proper segmentation metric, and valid training labels.
⚠️ The first set of baseline results and the setting derived from them (0.10) were discarded; `docs/baseline-results.md` states the correction.
⚠️ Lesson recorded: check a convention against the source (loader code, an overlay) before building an evaluation on top of it.

## Revisit when

Real Spanish plans with measured areas exist: then measure area and length error in m² directly.
