# Plan-reading baseline: results on CubiCasa5k

**Short version: the classical baseline is not usable for pricing.** It finds *some* enclosed rooms in almost every plan (98.5%), but its measure of plan shape is off by a median of **+35%**, and only **29%** of plans are within 20%. It is a floor for a learned model to beat, not a product.

## What was measured

- Data: CubiCasa5k test split, 400 plans (270 `high_quality_architectural`, 67 `colorful`, 63 `high_quality`), Finnish residential plans. **CC BY-NC-SA 4.0: never committed, and a model trained on it may not be usable commercially without checking the terms.**
- Method: `vision/walls.py` (dark thick strokes, optional closing to merge parallel lines) -> `vision/rooms.py` (enclosed free space) -> `vision/quantities.py`.
- Measures (ADR 0002 explains why these and not pixel IoU):
  - **detected**: at least one enclosed room found.
  - **wall ratio**: wall centre-line length / sqrt(interior area), compared with the same ratio computed from the SVG labels. Dimensionless, so independent of scale and pixel frame.

## Results

### Test split (400 plans), `close_frac` chosen on the validation split

| | close_frac 0.10 (chosen) | close_frac 0 (no closing) |
|---|---|---|
| Rooms detected | 98.5% | 24.7% |
| Wall ratio, median abs. error | **35.3%** | 542.6% |
| Within 20% | **28.8%** | 2.0% |
| Within 50% | **62.2%** | 6.1% |
| Median signed error | +35.3% (overestimates wall per area) | +542.6% |

Per style, detection at 0.10: colorful 100%, high_quality 98.4%, high_quality_architectural 98.1%.

### How the setting was chosen (validation split, first 120 plans)

| close_frac | detected | median abs. error | within 20% | within 50% |
|---|---|---|---|---|
| 0 | 18.3% | 728% | 4.5% | 9.1% |
| 0.01 | 89.2% | 207% | 0.9% | 8.4% |
| 0.02 | 98.3% | 107% | 0.8% | 12.7% |
| 0.03 | 99.2% | 83% | 0.8% | 14.3% |
| 0.05 | 100% | 66% | 3.3% | 25.8% |
| 0.07 | 100% | 52% | 5.0% | 47.5% |
| **0.10** | 97.5% | 37.5% | 19.7% | 65.8% |
| 0.14 | 86.7% | 21.7% | 48.1% | 75.0% |

I stopped at 0.10 deliberately. The error keeps shrinking at 0.14, but detection falls to 87% and the setting is large enough (14% of the image) to fill small real rooms and turn them into wall, which can make the ratio look right by accident. 0.10 is the largest value that still finds rooms in at least 95% of plans. The test split was run once with that value.

## Why it fails (looked at on 4 plans, not systematically)

Many CubiCasa5k plans are scans where a wall is drawn as **two thin parallel lines or hatching**, not a solid black bar. A "thick dark stroke" detector throws those away. Closing merges them, at the price of also merging furniture, text and door arcs into wall, which is where the positive bias comes from. Door openings are never closed, so rooms joined by a doorway read as one.

## Caveats (important)

1. **Labels are not pixel-aligned with the images.** On 60 test plans, every simple scaling convention put only ~10% of labelled wall pixels on dark pixels. So pixel overlap (IoU) could not be used, and these results say nothing about absolute areas.
2. **The wall ratio is a weak proxy.** It can be satisfied by accident (see the 0.14 row). A good score on it would not prove good area or length estimates.
3. **"Detected" is a low bar.** It means an enclosed region exists, not that it is a real room.
4. **Not Spanish plans.** Different drawing conventions, languages and scales. Nothing here transfers automatically to your real plans.
5. **No scale detection.** Absolute quantities need metres per pixel from the user.
6. Failure inspection was on 4 plans only.

## What a learned model needs to fix

- Read walls drawn as double lines and hatching (segmentation, e.g. a model trained on CubiCasa5k, which has wall masks).
- Close door openings so rooms separate.
- Separate text, furniture and dimension lines from structure.
- Be evaluated on Spanish plans with real measured areas, which only you can provide.

## Reproduce

```bash
# data: Zenodo record 2613548 (md5 0ce0b203d1e3c125b51087b219bd23b9), extract to data/cubicasa5k/extracted/
python -m plan2cost.eval.cubicasa --root data/cubicasa5k/extracted/cubicasa5k --split test --close-frac 0.10
```
