# Learned segmenter: results on CubiCasa5k

**Short version: a small U-Net trained on a laptop CPU in 56 minutes reads rooms well and walls decently, far ahead of the classical baseline.** On the 400 test plans: room-mask IoU **0.919** (baseline 0.514), wall-mask IoU **0.705** (baseline 0.431), and **99.3%** of plans have room IoU above 0.5 (baseline 66%). This is on Finnish plans only; it says nothing yet about Spanish ones.

## Comparison (test split, 400 plans, same metrics and frame)

| | Classical baseline (close_frac 0.02) | U-Net, 256 px |
|---|---|---|
| Rooms found (any) | 92.7% | 100% |
| Interior IoU, mean / median | 0.514 / 0.641 | **0.919 / 0.947** |
| Plans with interior IoU ≥ 0.5 | 66.0% | **99.3%** |
| Wall IoU, mean / median | 0.431 / 0.428 | **0.705 / 0.715** |
| Wall precision / recall | 0.471 / 0.865 | **0.741** / 0.935 |

| Style | n | wall IoU | interior IoU |
|---|---|---|---|
| high_quality_architectural | 270 | 0.683 | 0.906 |
| colorful | 67 | 0.751 | 0.943 |
| high_quality | 63 | 0.751 | 0.952 |

The weakest style is the same one the baseline struggled with (scanned plans with hatched walls), though it is now much closer to the others.

## Setup

- Data: CubiCasa5k, 4,200 train / 400 val / 400 test plans. **CC BY-NC-SA 4.0: the data and the trained weights stay out of git, and use in a paid product needs the licence checked.**
- Model: U-Net, 1.94M parameters, grayscale in, two masks out (walls, interior). Loss = BCE + Dice. AdamW with a one-cycle schedule (max lr 3e-3), batch 16, 25 epochs, flips/90° turns/mild contrast as augmentation, seed 0.
- Input: plans scaled so the longest side is 256 px and padded. Scoring upsamples the prediction back to the 1000 px frame the baseline is scored in, so the metrics are comparable.
- Checkpoint chosen on the validation split (epoch 22: val wall IoU 0.736, interior 0.936, pooled over pixels). The test split was scored **once**, with that checkpoint.
- Compute: 8 CPU threads with bf16, ~2.2 min/epoch, ~56 min in total. Run time and cost cuts are in the commit history.

## What this does and does not show

- ✅ A learned model handles hatched and double-line walls that defeat the rules, and separates rooms across doors.
- ⚠️ **Finnish residential plans, not Spanish.** Different conventions, scale conventions, languages and symbols. A good score here does not transfer automatically.
- ⚠️ Interior IoU is a good proxy for floor-area share, not an area error in m². Absolute quantities still need a scale (metres per pixel) from the user.
- ⚠️ Wall precision is 0.74: about a quarter of predicted wall pixels are not wall in the labels (the edges of thin walls at 256 px, and some furniture and text). Wall *length* from the mask will be better than wall *area*.
- ⚠️ Val numbers (pooled over pixels) and test numbers (mean over plans) are aggregated differently, so they should not be compared directly.
- ⚠️ One run, one seed: differences of a point or two between configurations are noise.

## Next experiments (on a GPU, one change at a time, chosen on validation)

Higher resolution (384 px) for thin walls; a wider network (width 32); longer training. Then test once on the best.

## Reproduce

```bash
python -m plan2cost.learn.data  --root data/cubicasa5k/extracted/cubicasa5k --out data/cache256 --size 256
python -m plan2cost.learn.train --cache data/cache256 --out results/unet256.pt --epochs 25 --batch 16 --lr 3e-3 --threads 8
python -m plan2cost.eval.cubicasa --root data/cubicasa5k/extracted/cubicasa5k --split test --model results/unet256.pt --model-size 256
```
