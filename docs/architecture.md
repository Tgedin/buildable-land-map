# Architecture

## Principle: compute offline, serve static

```
OFFLINE (laptop or GitHub Actions)                 ONLINE (static, $0)
config/area.yaml ─► blm run ─► web/data/*.json ──► GitHub Pages ─► browser (MapLibre)
```

| Decision | Why | Revisit when |
|---|---|---|
| Static site, no backend | $0, never sleeps, no ops, nothing to secure | Users need live queries (custom rules, uploads) |
| GeoJSON output | Readable, debuggable, no tooling | File > 10 MB → PMTiles (M4) |
| GeoParquet intermediates | Fast, typed, keeps CRS | — |
| Python stdlib XML for GML | Transparent, testable, no GDAL driver surprises | Never, unless performance requires it |
| Grid index for LiDAR | O(points + buildings) instead of O(points × buildings) | Millions of buildings → PDAL/COPC |
| One config file | One knob per area, reproducible runs | Multi-city → one file per city |

## Data model

**Building part** (Catastro `BuildingPart`, one row per part)

| Column | Type | Source |
|---|---|---|
| `part_id` | str | `inspireId/localId`, e.g. `1234501VK4713S_part1` |
| `refcat` | str(14) | first 14 chars of `part_id` |
| `floors_above` / `floors_below` | int? | `numberOfFloorsAbove/BelowGround` |
| `footprint_m2` | float | geometry area (UTM, metres) |
| `lidar_height_m` | float? | `lidar.building_heights` |
| `lidar_confidence` | high / low | enough roof + ground points |

**Parcel** (one row per `refcat`): `floors` (max of parts), `existing_m2` (Σ footprint × floors), `dominant_floors`, `gap_floors`, `gap_m2`.

## Failure modes

| Failure | Handling |
|---|---|
| WFS > 5,000 features in a tile | Tile split in four, recursively (max depth 4) |
| WFS network error | 3 retries with backoff |
| WFS `ExceptionReport` | `WfsError` with the service message |
| Part crossing two tiles | Deduplicated by `part_id` |
| Too few LiDAR points | Height kept, `lidar_confidence = low`, excluded from validation |
| Isolated parcel (< 3 neighbours) | No gap computed (`NaN`), not zero |
| NaN in output | Converted to `null` (NaN is invalid JSON) |
