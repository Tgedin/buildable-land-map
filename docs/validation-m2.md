# M2: LiDAR vs Catastro floors, Ruzafa

LiDAR: ICV (Valencian cartographic institute) PNOA-derived cloud, **2015 flight**, 0.5 pts/m², sheets `724-4372` and `726-4372`. Catastro: fetched 2026-10-11. **The two sources are about 11 years apart.**

Method: `lidar_floors = round(lidar_height_m / 3.0)`, compared with `floors_above`, high-confidence parts with ≥ 1 floor.

## Result (n = 1,987 parts)

| Metric | Value |
|---|---|
| MAE (floors) | 0.94 |
| Bias (LiDAR − Catastro) | **+0.87 floors** |
| Exact | 25.6% |
| Within ±1 floor | 85.9% (target ≥ 80%: met) |
| High-confidence parts | 1,993 of 4,043 with a height (49%; target ≥ 80%: **missed**) |
| Median metres per floor | 3.61 (not 3.0) |

## What the numbers say

- **The bias is systematic, not noise.** Median metres per floor is 3.6 in the 4–7 floor range and 4.45 m for 1-floor parts. The `floor_height_m: 3.0` setting is too low for this area, and LiDAR roof height includes parapets, lift and stair housings, and tall ground floors. Not changed: we report the disagreement, we do not tune to it (M2 scope). Whether to set 3.6 is a decision for the owner.
- Excluding parts under 50 m² barely changes it (MAE 0.91, ±1 = 86.2%), so tiny sheds are not driving the result.
- Only 49% of parts reach high confidence. 3,064 of 5,057 parts have too few roof or ground points at 0.5 pts/m², mostly small parts.

## Worst 10 (parts ≥ 50 m²)

| Part | Catastro floors | LiDAR height | Error (floors) |
|---|---|---|---|
| 6212322YJ2761C_part1 | 9 | 2.3 m | −8 |
| 5911205YJ2751B_part4 | 1 | 24.8 m | +7 |
| 6212322YJ2761C_part4 | 8 | 1.8 m | −7 |
| 6116404YJ2761E_part1 | 5 | 34.2 m | +6 |
| 5411701YJ2751A_part38 | 1 | 19.7 m | +6 |
| 6312056YJ2761A_part18 | 8 | 7.2 m | −6 |
| 5913115YJ2751D_part1 | 1 | 17.6 m | +5 |
| 6116404YJ2761E_part2 | 1 | 18.1 m | +5 |
| 5714107YJ2751D_part1 | 6 | 3.1 m | −5 |
| 6115912YJ2761E_part16 | 7 | 5.4 m | −5 |

**Inspected on the current PNOA aerial photo** (`docs/evidence/m2-worst10.jpg`, red = Catastro part outline; 8 images, the other 2 are siblings of parts shown: `6212322YJ2761C_part4` next to part1, `6116404YJ2761E_part2` next to part1). The aerial is newer than the 2015 LiDAR, so a building built after 2015 would show as built here and not be visible as an error cause. I looked at them, but this is one reader's reading of one image each.

| Pattern | Parts | What the image shows | Verdict |
|---|---|---|---|
| **Small part in an inner courtyard / light well**, Catastro floors high, LiDAR low (−5 to −8) | `6212322…_part1` (and part4), `5714107…_part1`, `6115912…_part16`, `6312056…_part18` (narrow strip) | The outline sits on open or low ground inside the block, surrounded by tall roofs. LiDAR measures the courtyard level, Catastro records the floors of the building it belongs to. | Method limit: a part's footprint is not always its roof. Not a Catastro error. |
| **Non-residential volumes**, Catastro floors not comparable | `5411701…_part38` (Estación del Norte hall, 8,952 m²), `5913115…_part1` (church, 1 "floor", 17.6 m), `6116404…_part1` and part2 (round tower/dome of the church, 5 floors vs 34.2 m) | Large single-volume or monumental buildings. | Floors are not a meaningful unit here. These should be excluded from validation and flagged on the map. |
| **Thin sliver beside a tall building**, Catastro 1 floor, LiDAR 24.8 m (+7) | `5911205…_part4` | A narrow strip at the edge of a tall block, next to a park. The roof points are the neighbouring wall and roof. | Method limit: the 0.5 m inner buffer does not protect slivers this thin. |

Nothing in these 10 suggests Catastro is wrong. All 10 are explained by how the part geometry meets the point cloud, or by non-residential use. That is a result worth stating: **the worst disagreements are mostly measurement artefacts**, so the 86% within ±1 is, if anything, a conservative view of how often Catastro floors agree with reality.

Suggested follow-ups (not done, M2 scope is reporting): drop parts under ~30 m² or thinner than ~4 m from validation, and exclude non-residential `currentUse` once that field is parsed.

## Not done / open

- A second pair of eyes on the worst 10 (the inspection above was done by the assistant on the current aerial; the owner should re-check, ideally on 2015 imagery).
- Decision on `floor_height_m` (3.0 vs ~3.6).
- A newer LiDAR coverage would remove the 2015-vs-2026 mismatch; the CNIG 3rd-coverage point cloud could not be downloaded.
