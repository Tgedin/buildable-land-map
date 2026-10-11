# Buildable Land Map

**Underused buildable floor area, parcel by parcel, from Spanish open data.**

Phase 1 of the [Housing AI roadmap](docs/roadmap.md). Goal: better housing that costs less relative to income. Land is expensive partly because information about what is buildable is scarce. This map makes it visible.

> Status: **M1 done, M2 done except the debug drill, plan-based gap added (ADR 0004)**. See [ACCEPTANCE.md](ACCEPTANCE.md).
> Live map: <https://tgedin.github.io/buildable-land-map/>

---

## How it works

```
Catastro WFS (BU.BUILDINGPART)        PNOA LiDAR (.laz, manual download)
  footprints + floors per part          ground (class 2) + building (class 6) points
            │                                      │
            ▼                                      ▼
   blm fetch ──► parts.parquet ──► blm heights ──► parts_lidar.parquet
   blm plan  ──► pgou.parquet (municipal plan heights + protection)
                                                   │
                                                   ▼
                                     blm build: parcels + buildable gap + validation
                                                   │
                                                   ▼
                              web/data/parcels.geojson + summary.json  (committed)
                                                   │
                                                   ▼
                              web/ (MapLibre, static) ──► GitHub Pages ($0, never sleeps)
```

**Gap against the plan (default view, Valencia):** `blm plan` downloads the municipal plan's height polygons (PGOU, CC BY 4.0). Room under the plan = allowed floors − Catastro floors, over the building's main footprint. Protected buildings, open space and public-services use are set aside, each with a reason on the map. The plan's `altura` is assumed to exclude the ground floor (+1); this is unverified and the total moves 3× either way (ADR 0004). Without a `planning:` section in `config/area.yaml`, only the neighbour view is built.

**Gap against the street (second view, a heuristic, not zoning):**

```
dominant_floors = median floors of neighbouring parcels within 50 m
gap_m2          = max(0, footprint × dominant_floors − Σ part_footprint × part_floors)
```

**LiDAR height:** median roof z (class 6, inside the footprint) − median ground z (class 2, 10 m ring). Medians are robust to chimneys, trees and misclassified points. Used to **validate** Catastro floors, not to replace them.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
make setup          # install + dev tools
make check          # lint + tests
make sample         # synthetic data -> web/data (offline)
make serve          # http://localhost:8000
```

Real data:

```bash
# 1. Edit config/area.yaml: name, label, bbox (ETRS89 UTM), epsg
# 2. (optional) Put PNOA LiDAR .laz tiles in data/raw/lidar/ (see docs/data-sources.md)
make run            # fetch -> heights -> build
make serve
git add web/data && git commit -m "data: <area> refresh" && git push   # deploys the map
```

## Repo map

```
config/area.yaml        the only knob: area, CRS, thresholds
src/blm/
  catastro.py           WFS tiling (4 km² / 5,000-feature limits), GML parsing
  lidar.py              LAZ reading, grid index, per-footprint heights
  planning.py           municipal plan (PGOU) heights, protection, parcel matching
  metrics.py            parcel aggregation, street gap, plan gap, LiDAR validation
  export.py             WGS84 GeoJSON + summary for the web
  synthetic.py          fake neighbourhood with known truth (tests + demo)
  cli.py                blm fetch | heights | build | run | sample
web/                    static map (index.html, app.js, style.css, data/)
plan-to-cost/           Phase 2/4 toolkit: plan model, cited rules, generators, screening of added homes (own package + tests)
tests/                  unit tests + small real/fixture data
docs/                   architecture, data sources, decisions (ADRs), drills
ACCEPTANCE.md           milestones M0–M4 with Must / Target criteria
```

## Data & licences

- Buildings: © Dirección General del Catastro, INSPIRE services. Licence: see the [Catastro INSPIRE page](https://www.catastro.hacienda.gob.es/webinspire/index.html).
- LiDAR: © IGN, PNOA LiDAR via the CNIG download centre (CC BY 4.0 for IGN data; check the tile's licence).
- Coverage: the national Catastro excludes Navarra and the Basque Country, which have their own cadastres.

## Running cost

| Item | Monthly |
|---|---|
| GitHub Pages hosting | €0 |
| Pipeline (monthly GitHub Actions run, ~6 min, public repo) | €0 |
| **Total** | **€0** |

## Limits (stated, not hidden)

- The gap is a **heuristic** against neighbours, not the municipal plan (PGOU). A parcel can show a gap and still be unbuildable (protected heritage, plan limits, open space).
- Catastro floors can lag reality; LiDAR flights happen every few years. M2 measures the disagreement.
