# ADR 0003: Gap counts the main body, not the whole footprint

- **Status:** accepted
- **Date:** 2026-10-11

## Context

v0 computed `gap = max(0, footprint × dominant_floors − Σ part footprint × floors)`. On real Ruzafa data it flagged 811 of 932 parcels and 687,618 m² of gap on 1.49M m² existing, which no one would believe.

Cause (checked, not guessed): the parcel footprint includes low rear parts (1,854 of 5,057 parts have 1 floor). In the Eixample these are ground-floor workshops filling inner courtyards, so v0 reported about five "missing floors" over every courtyard. Floor-0 parts were not the cause (excluding them changed the total by < 1%).

## Decision

`gap_floors = max(0, dominant_floors − floors)` where `floors` is the parcel's tallest part, and `gap_m2 = main_footprint_m2 × gap_floors`. `main_footprint_m2` is the footprint of the parts at the tallest height.

Result on Ruzafa: 280 of 932 parcels, 167,826 m² (was 811 and 687,618 m²).

## Consequences

✅ Gap reads as "add storeys to the building body", which is explainable to a user in one sentence.
✅ Courtyard annexes no longer count as under-use.
⚠️ Conservative: a parcel with a 6-floor front and a 5-floor wing gets the wing ignored. A parcel whose body is low because it is a school, market or protected building still shows a gap (the map footer says so).
⚠️ No ground truth yet. Validate with the M3 conversations before trusting the total.

## Revisit when

Users point at parcels where the gap is clearly wrong, or when the municipal plan (PGOU) is added and gives real allowed heights.
