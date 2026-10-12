# ADR 0004: Gap against the municipal plan (PGOU), with protection and use exclusions

- **Status:** accepted, with one unverified assumption (below)
- **Date:** 2026-10-11

## Context

The neighbour heuristic (ADR 0003) still flags 280 of 932 Ruzafa parcels. It cannot know that a parcel is protected, that the plan forbids more height, or that it is a school. Valencia publishes its plan open (CC BY 4.0): "PGOU - Alineaciones", polygons with `altura` and protection codes. Catastro `BU.BUILDING` gives `currentUse`.

## Decision

1. Fetch the PGOU alignments for the area (`blm plan`) and classify each polygon: `floors` (numeric, or `B+n`), `open` (`0`), `protected` (`PROTEGIDO*`, or code AMB/PAR/INT/BRL), `unknown` (anything else, never guessed, never 0).
2. Match polygons to parcels by area share: protected if ≥ 50% under protected polygons; plan height = the numeric polygon covering most of the parcel, required to cover ≥ 50%.
3. `plan_gap_floors = max(0, allowed − floors)`, `plan_gap_m2 = main_footprint × plan_gap_floors`. Parcels that are protected, open space, public-services use (Catastro `4_3_publicServices`) or have no plan height get NaN and a `gap_class` saying why.
4. The neighbour comparison stays as a second view; the plan view is the default.

## The assumption (not verified)

Allowed floors = `altura` + 1 (`ground_floor_offset` in config), i.e. `altura` counts floors above the ground floor. Evidence is empirical (Catastro floors are usually `altura` + 1 or + 2) plus one indirect clue from the plan text: for the Ensanche zone, which covers Ruzafa, the cornice height is 4.80 m + 2.90 m per plan floor (art. 6.19.1). A 4.80 m base is roughly one tall ground floor, so `altura` counts floors above the ground floor, which supports an offset of 1. **Art. 5.33 (how floors are counted) has still not been read**, so this stays unverified. The result is sensitive to it (Ruzafa, non-protected, non-public parcels):

| offset | parcels with plan gap | m² |
|---|---|---|
| 0 | 65 | 12,240 |
| 1 (default) | 154 | 38,884 |
| 2 | 304 | 82,975 |

## Result (offset 1)

| Class | Parcels |
|---|---|
| at_limit | 518 |
| protected | 246 |
| plan_gap | 154 |
| public_use | 7 |
| no_plan | 6 |
| open | 1 |

Plan gap 38,880 m² vs 167,826 m² for the neighbour heuristic: about 77% of the neighbour "gap" disappears once protection, plan limits and public use are applied.

## Consequences

✅ The map answers "what could be added under the plan", not "what is lower than the neighbours".
✅ Every excluded parcel says why.
⚠️ The offset assumption moves the total by 3× either way. Must be shown on the map until verified.
⚠️ Some large 1-floor parcels with plan `altura` 1 get a 1-floor gap only because of the +1 offset; they are probably facilities zones.
⚠️ The PGOU layer was last edited recently but the plan itself is old; recent modifications may be missing. Heights here are the plan's, not a building permit.
⚠️ Alignment polygons describe building lines, so using the whole main footprint over-counts where only part of the parcel is buildable.

## Revisit when

The PGOU normative text is read and the offset confirmed, or a user shows a parcel where the plan view is clearly wrong.
