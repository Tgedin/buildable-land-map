# ADR 0004: Screening of added homes by area and free facade

- **Status:** accepted
- **Date:** 2026-10-11

## Context

The map says which parcels have room under the plan (extra floors allowed). The next question for a cooperative or small developer is "how many homes could that be?". A design needs structure, services, fire safety and an architect; a first filter only needs to tell which parcels are worth a second look, and why the others are not.

## Decision

For each parcel with room under the plan, per added floor, take the smaller of two caps:

- **Area:** `floor((plate − core) / gross dwelling area)`, with the plate = the existing main body's footprint, the core a stair/lift allowance, and gross = useful area / a net-to-gross ratio.
- **Facade:** `floor(free facade / facade the dwelling needs)`. Free facade is the parcel boundary that is not a party wall (an edge within 0.35 m of a neighbour) and not a small light well (an inner hole under 30 m²).

The dwelling used as the unit is the smallest generated plan, per bedroom count and typology (double-aspect, single-aspect), for which the Decreto 80/2023 rule engine finds no violation *and* leaves nothing to review. The best typology per parcel wins.

## Result (Ruzafa, 154 parcels with room under the plan)

| | 2-bedroom | 1-bedroom |
|---|---|---|
| Parcels that can host at least one added home | 90 | 108 |
| Added homes in total | 213 | 348 |

Unit sizes found: 1 bedroom 40 m² (double-aspect, 10 m of facade) or 45 m² (single-aspect, 6.25 m); 2 bedrooms 54 m² (15.5 m) or 63 m² (9.25 m); 3 bedrooms 78 m² (single-aspect, 12.25 m).

## Assumptions (not derived; in `Assumptions`)

Net-to-gross 0.85, core 18 m² per floor, party-wall tolerance 0.35 m, light-well threshold 30 m². Changing them changes the result; a test checks that they do.

## What it does not check

Structure and the capacity of the existing building for extra floors; whether the stair can be extended and lift requirements; fire safety, accessibility of common areas, energy and acoustics; owners' consent, permits and neighbour-light conditions; urban parameters other than the plan's height; any rule other than arts. 9-10 and 51-56 of Decreto 80/2023. The list ships inside every output file and is shown on the map.

## Consequences

✅ A transparent, rule-grounded way to rank parcels and to say why one gets zero (area, or facade).
⚠️ It is a screening of added floors on an existing building. It is not a design, not a permit, and not a statement that any of it can be built. The facade proxy is crude: it does not know which edges are street or courtyard, how deep the plot is, or whether a flat can be laid out within the real plate shape.
⚠️ The first-pass unit is the smallest legal flat, which is not what people want to buy; a mix, and cost, come next.

## Revisit when

An architect reviewing a few real parcels disagrees with the numbers, or a real layout fit (placing the flats inside the parcel outline) replaces the facade proxy.

## Addendum, 2026-10-12: the ático route

The València Normas Urbanísticas (art. 6.19.5) allow an *ático* above the cornice in the Ensanche zone. The screening now has a second route next to "build up to the plan's height":

- **Eligible** if the parcel's zone is `ENS` (from the plan's *Calificaciones* layer), the plan allows at most 8 floors including the ground floor, and the building has no more floors than the plan assigns (the text bars an ático when fewer floors than assigned were built; a building already above the plan may have one). Anything else gets a reason, never a guess.
- **Plate** = the building footprint minus a 4 m band along the street-facing facades (see Street facades below).
- **One floor**, then the same homes screening and residual as the floors route. A parcel can have both routes; the ático then comes after the floors reach the plan.

Not modelled: the 3.20 m height limit of the ático, pitched roofs, whether the existing roof and structure can host it, and `enrase de cornisas` (art. 6.19.3).

Ruzafa result: 130 parcels eligible, 30 fit 2-bed homes (31 homes; 60 one-bed), residual about -0.9 M EUR pessimistic, 1.5 M EUR base, 3.2 M EUR optimistic, before structural reinforcement. No parcel is positive in all three scenarios. Earlier versions gave 152 parcels / 2.6 M EUR base (included plan-height-1 parcels), 25 / 1.4 M (setback on the parcel outline) and 7 / 0.3 M (every free facade set back, street and back yard not told apart).

**Street facades.** Art. 6.19.5 asks for the setback from facades onto a street or public space only. The street front is read from the outer boundary of the union of all parcels (`public_edge`): parcels tile the blocks, so that boundary is where they meet a street or square, and a facade within 1.5 m of it faces the street. Back yards and party lines are inside the blocks. This does not use the plan's own alignments, and parcels cut by the study-area border look like street fronts there.

**Geometry.** Facade length and the ático setback are measured on the tallest building part (`main_part_geometries`, from `parts_lidar.parquet`), not on the parcel outline: a parcel can be a whole block with a small tall building on it. Each result says what it was `measured_on`; without the parts file the outline is used.

**Known weakness found while testing the shortlist.** A parcel is matched to the plan polygon covering most of the *parcel*, not of the *building*. A tall front building with a large low rear court can therefore be read as "plan height 1". 110 Ensanche parcels in Ruzafa have a plan height of 1, most of them probably this case. The ático route excludes plan height 1 (reason `plan_ground_floor_only`), but the right fix is to match the plan to the building footprint; the same mix-up can distort the plan gap in m² (ADR 0004, plan heights).

**Rooftop or redevelopment.** The floors route can ask for more floors than an existing structure carries (a 2-floor building in a 7-floor plan "adds 5"). Results with more than `max_rooftop_floors` (2, assumed, no source) are labelled `redevelopment`. Ruzafa: 32 rooftop parcels (57 two-bed homes, residual 2.9 M EUR base) against 7 redevelopment parcels (42 homes, 2.2 M EUR base).
