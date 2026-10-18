# ADR 0006: Whole-city València: candidates on the web, residential only, local street edge

- **Status:** accepted
- **Date:** 2026-10-18

## Context

Phase 1's M4 asks for the whole city. The first full run (urban area, about 11 x 18.5 km: 814 Catastro tiles, 60 LiDAR sheets, 75,786 parcels, 324,064 building parts) exposed what Ruzafa never did, and forced four decisions.

## What the run took

| Step | Time | Note |
|---|---|---|
| Catastro parts + use (cached per tile) | about 1.5 h | the use pass timed out at 60 s; retries are now configurable, with a 120 s timeout |
| LiDAR heights (153 M points) | 1.5 min | 263,654 parts; 127,794 buildings validated: mean error 0.64 floors, 91.7% within one floor |
| Build | 25 s | |
| Screening | 1.5 min | after the change below; before it, more than 12 min without finishing |
| Disk | 2.2 GB LiDAR, 1.3 GB Catastro responses, 0.3 GB derived | none of it is committed |

## Decisions

1. **The web shows candidates only.** The full dataset (15 MB of parcels, 213 MB processed) stays in `data/processed`. `blm candidates` exports only the parcels the screening found a home on, with their building parts: 2,761 parcels, 7,334 parts, 8.4 MB of JSON, **about 0.7 MB compressed** on GitHub Pages. Each file is under the 10 MB threshold that triggers PMTiles in ADR 0001, so PMTiles is not needed; revisit if the load-time target (M4: under 3 s on a mid-range phone) fails. Pages read `?area=<slug>` to choose `data/<slug>/`.
2. **The street edge is local.** Whether a facade faces the street depends only on the parcels within a few metres, so each candidate builds its own small edge from its neighbours. The global version (the union of every parcel) is identical on Ruzafa (141 of 141 parcels the same) but did not finish on the city: unioning 75,786 buffered parcels is too slow, and each use buffered the whole edge.
3. **The headline counts residential buildings only.** Of 1,663 parcels that fit homes, only 1,199 (72%) were residential by Catastro use; 362 were industrial, 79 retail and 14 office, and they carried 47% of the homes. Those have no community of owners to vote on new floors (LPH art. 17.4) and housing may not be allowed in their zone, which is not checked. They stay on the map and the list as "Other use", counted apart, hidden by default. Unknown use is not residential.
4. **Large plates get more than one core.** One stair core per 600 m² of floor plate (assumed), because a 7,000 m² plate with a single 18 m² core is not a building.

## What the city data does not give

- **59% of parcels (44,616 of 75,786) have no usable plan height.** The plan's alignments layer covers only part of the city, and some polygons say another planning instrument governs ("PPARCIAL", "NORMATIVA"). They are not screened, never guessed. 14,799 parcels are in the Ensanche zone, where the rooftop thesis applies.
- The plan layer has non-height numbers in its height field ("3833", "2650406"): a height above 20 floors is read as unknown. Protection tags written in that field ("PROT_1h", "BIC_M", "BRL_MIL") are read as protected.
- The monthly refresh workflow still covers Ruzafa only. A city refresh takes about 1.5 h of fetching and is run by hand.

## Result (2026-10-18, two-bed homes, residual pessimistic / base / optimistic, before structural reinforcement)

1,199 residential rooftop candidates, **2,529 two-bed homes**, **-79 M / 129 M / 269 M EUR**. Listed apart and not counted: 324 redevelopment parcels (3+ added floors) and 596 of other use. No parcel is positive in all three scenarios.

## Consequences

✅ The whole city loads in about 1.5 s locally and is small over the wire; the same pages serve any area.
✅ Every number still carries its status and its limits.
⚠️ 8.4 MB of JSON is parsed at load; if the phone target fails, split the files or move to PMTiles.
⚠️ Large single-owner plates still rank high; the ranking is by capacity, not by likelihood.
⚠️ The residential filter trusts Catastro's use field, which is per building, not per floor: a building with shops on the ground floor and homes above is "residential" only if Catastro says so.

## Revisit when

The load-time target is measured, the plan layer's coverage is understood (which instruments govern the 59%), or a city refresh is automated.
