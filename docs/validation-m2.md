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

**Hypotheses, not yet verified by eye** (the Must says "inspected by hand", so this stays open until someone looks at each part on the PNOA aerial / street view):

- **Catastro tall, LiDAR ≈ 2–7 m (−5 to −8):** the building probably did not exist in 2015 (built after the flight; the two worst are parts 1 and 4 of the same parcel), or the roof points were not class 6.
- **Catastro 1 floor, LiDAR 17–25 m (+5 to +7):** probably a 1-floor part that sits under or beside a taller part, so the median of "roof" points inside its footprint picks up the taller building. Parts of one parcel can overlap or touch; this is a method limit.
- 5411701YJ2751A_part38 has a footprint of 8,952 m²: a large part, likely mixed heights inside one footprint, where a single median is a poor summary.

## Not done / open

- Hand inspection of the 10 cases above.
- Decision on `floor_height_m` (3.0 vs ~3.6).
- A newer LiDAR coverage would remove the 2015-vs-2026 mismatch; the CNIG 3rd-coverage point cloud could not be downloaded.
