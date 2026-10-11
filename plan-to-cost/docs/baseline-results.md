# Plan-reading baseline: results on CubiCasa5k

**Short version: the classical baseline reads rooms moderately well and walls poorly.** On the 400-plan test split, its room (interior) mask overlaps the labels with a mean IoU of **0.51** (66% of plans at IoU ≥ 0.5). Its wall mask has IoU **0.43**: it finds most wall pixels (recall 0.87) but marks many non-wall pixels as wall too (precision 0.47). It is a floor for a learned model to beat, not something to price from.

> **Correction.** An earlier version of this file reported a "+35% shape error" measured with a scale-free proxy, because I believed the SVG labels were not aligned with the images. That was my mistake: I had tested only scaling conventions, while the dataset's loader uses the SVG coordinates directly as pixel positions in `F1_scaled.png`. With the right mapping the labels line up (checked by overlay). The old numbers and the closing setting chosen from them (0.10) were wrong and are discarded. See ADR 0002.

## What was measured

- Data: CubiCasa5k test split, 400 plans (270 `high_quality_architectural`, 67 `colorful`, 63 `high_quality`), Finnish residential plans. **CC BY-NC-SA 4.0: never committed, and a model trained on it may not be usable commercially without checking the terms.**
- Method: `vision/walls.py` (dark strokes, thin ones dropped, optional closing to merge parallel lines) -> `vision/rooms.py` (enclosed free space).
- Metrics: pixel IoU, precision and recall of the wall mask; IoU of the interior mask (rooms = class `Space` except `Outdoor`). Image and labels are scaled together to a 1000 px longest side.
- `close_frac` was chosen on the validation split (first 150 plans) and the test split was run once.

## Results (test split, 400 plans, close_frac 0.02)

| | Value |
|---|---|
| Plans with an enclosed room found | 92.7% |
| Wall IoU (mean / median) | 0.431 / 0.428 |
| Wall precision / recall (mean) | 0.471 / 0.865 |
| Interior IoU (mean / median) | **0.514 / 0.641** |
| Plans with interior IoU ≥ 0.5 | **66.0%** |

| Style | n | wall IoU | interior IoU |
|---|---|---|---|
| high_quality_architectural | 270 | 0.387 | 0.556 |
| colorful | 67 | 0.517 | 0.471 |
| high_quality | 63 | 0.531 | 0.378 |

Without closing (`close_frac 0`): rooms found in only 24.7% of plans, interior IoU 0.043, wall IoU 0.349 (wall precision 0.65, recall 0.41).

### How the setting was chosen (validation, first 150 plans)

| close_frac | detected | wall IoU | wall precision | wall recall | interior IoU | interior IoU ≥ 0.5 |
|---|---|---|---|---|---|---|
| 0 | 18.0% | 0.193 | 0.547 | 0.228 | 0.036 | 4.0% |
| 0.01 | 87.3% | 0.410 | 0.508 | 0.712 | 0.352 | 40.0% |
| **0.02** | 98.0% | 0.378 | 0.410 | 0.860 | 0.534 | 65.3% |
| 0.04 | 100% | 0.291 | 0.300 | 0.930 | 0.539 | 63.3% |
| 0.07 | 100% | 0.219 | 0.222 | 0.964 | 0.465 | 48.0% |
| 0.10 | 97.3% | 0.182 | 0.183 | 0.977 | 0.352 | 26.0% |

Interior IoU peaks at 0.02-0.04; I took 0.02 because it ties on rooms and has clearly better wall overlap. Larger values merge more and more non-wall pixels into wall (precision falls to 0.18), which is the opposite of what the earlier flawed measure suggested.

## Why it is wrong where it is wrong (4 plans looked at, not systematic)

Many CubiCasa5k plans draw a wall as **two thin parallel lines or hatching**, not a solid bar. Without closing those are discarded and rooms never close. Closing merges them but also merges furniture outlines, text and door arcs into wall: that is the low precision. Door openings are never closed, so rooms joined by a doorway can leak into the outside.

## Caveats

1. Finnish plans, not Spanish: different drawing conventions and scales. Nothing here transfers automatically.
2. No scale detection: absolute m² and metres need a scale from the user.
3. Interior IoU is a good proxy for floor area share but not an area error in m².
4. Failure inspection was on 4 plans only.

## What a learned model needs to fix

Read double-line and hatched walls as walls, ignore text and furniture, and separate rooms across door openings. The dataset has wall and room masks to train on, now known to be aligned. The real accuracy claim still needs Spanish plans with measured areas.

## Reproduce

```bash
# data: Zenodo record 2613548 (md5 0ce0b203d1e3c125b51087b219bd23b9), extract to data/cubicasa5k/extracted/
python -m plan2cost.eval.cubicasa --root data/cubicasa5k/extracted/cubicasa5k --split test --close-frac 0.02
```
