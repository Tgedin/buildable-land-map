# ADR 0004: Gap against the municipal plan (PGOU), with protection and use exclusions

- **Status:** accepted; offset corrected from 1 to 0 on 2026-10-12 (see Correction)
- **Date:** 2026-10-11

## Context

The neighbour heuristic (ADR 0003) still flags 280 of 932 Ruzafa parcels. It cannot know that a parcel is protected, that the plan forbids more height, or that it is a school. Valencia publishes its plan open (CC BY 4.0): "PGOU - Alineaciones", polygons with `altura` and protection codes. Catastro `BU.BUILDING` gives `currentUse`.

## Decision

1. Fetch the PGOU alignments for the area (`blm plan`) and classify each polygon: `floors` (numeric, or `B+n`), `open` (`0`), `protected` (`PROTEGIDO*`, or code AMB/PAR/INT/BRL), `unknown` (anything else, never guessed, never 0).
2. Match polygons to parcels by area share: protected if ≥ 50% under protected polygons; plan height = the numeric polygon covering most of the parcel, required to cover ≥ 50%.
3. `plan_gap_floors = max(0, allowed − floors)`, `plan_gap_m2 = main_footprint × plan_gap_floors`. Parcels that are protected, open space, public-services use (Catastro `4_3_publicServices`) or have no plan height get NaN and a `gap_class` saying why.
4. The neighbour comparison stays as a second view; the plan view is the default.

## Correction, 2026-10-12: the offset is 0, not 1

This ADR first assumed `altura` counts floors above the ground floor (offset 1). A later edit cited the Ensanche cornice formula as support. **That was a misreading.** The Normas Urbanísticas (València PGOU, text transcription from valencia.es) say:

- Art. 5.33: the height in number of floors is "el número de plantas por encima de la cota de referencia o de la rasante, **incluida la planta baja**".
- Art. 6.19.1: `Hc = 4,80 + 2,90 Np`, where `Np` is "el número de plantas a edificar sobre la baja (es decir el señalado en los planos menos uno)". So Plano C counts the ground floor.

Allowed floors = `altura` + 0. The default is now 0. What remains an assumption is that the layer's `altura` is the Plano C number. Two checks on Ruzafa do not contradict it: LiDAR heights of plan-4 and plan-5 parcels sit at the cornice heights for "includes the ground floor" (13.8 vs 13.5 m, 16.3 vs 16.4 m), while plan-6 parcels (22.3 m) fit the other reading better (n=19; the LiDAR height includes roof structures). Catastro floors exceed the plan number on most parcels (+1 or more on about 60%), which is expected for a district built mostly before the 1988 plan and for buildings with a penthouse.

Not modelled yet: art. 6.19.5 allows an *ático* above the cornice (set back at least 4 m from street facades, at most 3.20 m high, not on buildings of more than 8 floors including the ground floor, and not when fewer floors than the plan allows were built). That is the real legal route for a rooftop addition and is a separate screening from the floors gap.

Sensitivity of the gap to the offset (Ruzafa, non-protected, non-public parcels), computed before the correction:

| offset | parcels with plan gap | m² |
|---|---|---|
| 0 (now the default) | 65 | 12,240 |
| 1 (previous default) | 154 | 38,884 |
| 2 | 304 | 82,975 |

## Result before the correction (offset 1)

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
