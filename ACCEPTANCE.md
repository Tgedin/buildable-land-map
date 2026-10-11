# Phase 1: Acceptance Criteria

**Phase goal:** Make underused buildable floor area visible, parcel by parcel, for one Spanish city, and get it used by real people.

**Budget:** ~60 h, Oct–Dec 2026.

**How to read this file:**

- **Must** criteria are the gate. A milestone is done when every *Must* box is ticked.
- **Target** criteria are aims. Missing a target is fine if the gap is written down in the milestone's *Notes*. Write it down, don't hide it.
- **Evidence** is where someone else can verify the claim: a link, a file or a number.

```
M0 Scaffold ─► M1 First real map ─► M2 LiDAR validated ─► M3 Gap + first users ─► M4 City scale
   done          wk 1–2 (~10h)        wk 3–5 (~15h)         wk 6–8 (~15h)          wk 9–11 (~15h)
```

---

## M0: Scaffold ✅

**Goal:** A clean repo where the whole pipeline runs end to end, with no real data needed yet.

| | Criterion | Evidence |
|---|---|---|
| Must | ☑ `make check` passes (lint + 16 tests) | CI badge |
| Must | ☑ `make sample && make serve` shows a 3D map of synthetic parcels | `web/data/summary.json` has `synthetic: true` |
| Must | ☑ Every pipeline step is a CLI command with a single config file | `config/area.yaml`, `blm --help` |
| Must | ☑ Raw/interim data can't be committed by accident | `.gitignore` |

---

## M1: First real map

**Goal:** Real Catastro buildings for one neighborhood, on a public URL.

| | Criterion | Evidence |
|---|---|---|
| Must | ☑ Area chosen and justified in `docs/decisions/0002-area-choice.md` (data openness, size, personal access to users) | ADR file |
| Must | ☑ `make run` from a clean clone produces `web/data/` for the real area | commit of `web/data/` |
| Must | ☑ Map live on GitHub Pages, and the `synthetic` banner is gone | public URL in README |
| Must | ☑ At least 1 real Catastro WFS response saved as a test fixture (small) | `tests/fixtures/` |
| Target | ☑ ≥ 95% of building parts have `floors_above` | `summary.json` / Notes |
| Target | ☐ Map usable on a phone (loads, clickable, readable) | screenshot |
| Target | ☑ Fetch for the neighborhood finishes in < 5 min | log line |

**Out of scope:** LiDAR, analytics, city scale.

**Notes:**
- Ruzafa, 0.56 km²: 5,057 parts, 932 parcels. Fetch took ~58 s. 100% of parts have `floors_above` (42 of them are 0: patios and sheds, a real zero, not a missing value).
- Fixture: `tests/fixtures/ruzafa_real_sample.gml` (real, 30 × 30 m, 28 parts).
- Surprise: the heuristic reports 687,618 m² of "gap" on 1.49M m² existing, with 811 of 932 parcels flagged. The largest come from big 1-3 floor parcels (probably facilities or industrial). Not courtyards: excluding floor-0 parts barely changes the total. Cause found later: 1-floor rear annexes in courtyards (1,854 parts have 1 floor). Fixed in ADR 0003: 280 parcels, 167,826 m². Footer limitation text is already on the map.
- Live: https://tgedin.github.io/buildable-land-map/ . Still open: phone screenshot (Target).

---

## M2: LiDAR heights validated

**Goal:** Measured heights from PNOA LiDAR, with an honest accuracy number.

| | Criterion | Evidence |
|---|---|---|
| Must | ☐ LiDAR tiles for the area downloaded and processed with `make heights` | log + `parts_lidar.parquet` |
| Must | ☐ Validation reported on ≥ 50 buildings: MAE in floors, share exact, share within ±1 | `summary.json → lidar_validation` |
| Must | ☐ Worst 10 disagreements inspected by hand and explained (e.g. attic, terrace, wrong class, recent works) | `docs/validation-m2.md` |
| Must | ☐ One debug drill done (see `docs/debug-drills.md`) | drill log |
| Target | ☐ ≥ 80% of parts have `lidar_confidence = high` | `summary.json` |
| Target | ☐ ≥ 80% of validated parts within ±1 floor | `summary.json` |

**Out of scope:** Correcting Catastro. Disagreements are reported, not fixed.

**Notes:**
- _(LiDAR flight year vs Catastro date matters: new buildings may be missing from one source)_

---

## M3: Buildable gap + first real users

**Goal:** The map answers a real question for real people, and you can prove they used it.

| | Criterion | Evidence |
|---|---|---|
| Must | ☐ 5 discovery conversations done and logged (cooperatives, small developers, architects, journalists) | `docs/discovery/` (no personal data, just role + learnings) |
| Must | ☐ At least 1 change to the map driven by a discovery conversation | commit message references the note |
| Must | ☐ Analytics live (privacy-friendly, no cookies) | GoatCounter dashboard |
| Must | ☐ Limitation stated clearly on the map: heuristic, not zoning | footer text |
| Must | ☐ Write-up #1 published: "X m² of missing floor area in [area]", with method + limits | post link |
| Target | ☐ 25 unique visitors from outside your own network | analytics |
| Target | ☐ 3-min demo video | link |

**Out of scope:** Real zoning (PGOU) parsing. Note which data would be needed for it.

**Notes:**

---

## M4: City scale + scheduled refresh

**Goal:** The whole city, refreshed automatically, at the usage target from the roadmap.

| | Criterion | Evidence |
|---|---|---|
| Must | ☐ Whole city processed (Catastro + LiDAR) | `summary.json` |
| Must | ☐ Scheduled GitHub Action refreshes Catastro data monthly and redeploys | workflow file + run history |
| Must | ☐ If `parcels.geojson` > 10 MB, switch to PMTiles (vector tiles in one static file) | ADR + file size |
| Must | ☐ README shows monthly cost (target: €0) | README |
| Target | ☐ 100 unique users / 500 parcel lookups (roadmap target) | analytics |
| Target | ☐ Map loads in < 3 s on a mid-range phone | Lighthouse report |

**Out of scope:** Multiple cities.

**Notes:**

---

## Next (Phase 1.5, only if time remains)

- **Affordability index:** INE *Atlas de distribución de renta de los hogares* by census section → cost per m² × typical unit ÷ median income.
- **Zoning:** One municipality's PGOU max heights, where published as open data, to replace the heuristic in that zone.

---

## Definition of "real" (from the roadmap)

Phase 1 is complete only when it is **Deployed** (M1) · **Measured** (M2) · **Used** (M3–M4) · **Shown** (write-up + video + public repo).
