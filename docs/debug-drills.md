# Debug drills

FDE interviews test whether you can read and fix code without an assistant. Once per milestone, run one drill: **no AI, 45 min timebox**, then log it below.

## How

1. Start from a green `make check`.
2. Ask someone (or a fresh AI chat, without showing it the fix) to apply one breaking change from the list. Or pick one yourself and forget which line you touched.
3. Find and fix it using only tests, logs, `print`, `pdb` and reading code.

## Bug bank

| # | Break | Symptom to diagnose |
|---|---|---|
| 1 | Swap x/y in `catastro._ring` | Buildings appear in the ocean / wrong country |
| 2 | Remove `.to_crs(4326)` in `export.py` | Map is empty, test catches lat/lon range |
| 3 | `side="right"` → `"left"` in `GridIndex.query` | Some buildings get no LiDAR points |
| 4 | Drop `keep = src != nbr` in `metrics.buildable_gap` | Each parcel counts itself as a neighbour; gaps shrink |
| 5 | Use `max` instead of `median` for roof z | Heights inflated by chimneys / noise |
| 6 | `tile_size_m: 3000` in config | Real WFS starts failing (area limit) |
| 7 | Remove `replace({np.nan: None})` in export | Browser JSON parse error |

## Log

| Date | Bug # | Time to fix | What helped | What I learned |
|---|---|---|---|---|
| | | | | |
