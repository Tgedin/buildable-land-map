# MVP: Rooftop opportunity screener for Valencia

Status: draft, 2026-10-12. Built on the findings in `reports/Construction business model economics.md`; read its caveats first, many figures there are secondhand.

## Goal

Tell a promotor, an architect or a neighbours' community, for any building in Valencia: **how many homes could be added on top, what the project could bear for the air rights, and what blocks it.** Every number says whether it is verified, sourced or assumed, and anything unknown is withheld, never guessed.

The longer goal is cheaper, better housing. The route is to own the *front of the funnel* (which sites, what is feasible, who must agree) and partner for everything physical. No factory.

## Why this, and not another thing

1. **Where the money is.** Developers keep roughly 5x the contractor margin, but small projects carry the risk and the financing. Prefab ventures that built factories before they had approved sites (Katerra, Veev, L&G, Ilke, TopHat) failed. Survivors own the customer and the downstream income. A screener is the cheapest way to own the customer.
2. **Where the pain is.** Spain is short by an estimated 750,000 homes; industrialised building is 1-2% of the market. The gates are licensing, owner consent (three-fifths under LPH art. 17.4, read in the BOE consolidated text of 2026-10-05; unanimity is an open question for a lawyer) and capped-price housing.
3. **What we already have.** A buildable-land map (Phase 1), a rule engine with 17 Decreto 80/2023 rules, rule-checked dwelling generators and a screening of added homes (Phase 2). The MVP is mostly connecting them to money and risk.

## What the MVP does

For each parcel with room under the plan:

| Output | Source | Status |
|---|---|---|
| Added floors allowed | PGOU alignments, +1 offset | assumed (ADR 0004) |
| Homes that fit (1- and 2-bed) | rule-checked dwellings, area and free facade | computed |
| Residual value, 3 scenarios | `plan2cost.proforma` | assumed inputs, shown |
| Costs left out | structural reinforcement | named as excluded |
| Blocking risks | structure, owners' consent, protection, lift, fire | listed, not yet scored |

Current Ruzafa run (2026-10-12, after the floor-count and geometry corrections below). Two routes, 2-bed homes, residual as pessimistic / base / optimistic, before structural reinforcement:

| Route | Parcels that fit | Homes | Residual |
|---|---|---|---|
| Rooftop: 1-2 added floors up to the plan's height | 30 | 50 | -1.5 M / 2.5 M / 5.3 M EUR |
| Redevelopment: more than 2 added floors (assumed cap) | 6 | 27 | -0.9 M / 1.4 M / 3.0 M EUR |
| Penthouse (ático) | 31 of 140 eligible | 31 | -0.9 M / 1.5 M / 3.2 M EUR |

The rooftop thesis is the first and third rows: 81 two-bed homes on 57 parcels in Ruzafa, residual -2.5 M / 4.1 M / 8.5 M EUR (the two routes overlap on some parcels, where the ático comes after the floors). The second row is a different business (an old low building cannot carry five new floors). The 2-floor cap is an assumption, not a finding.

No parcel is positive in all three scenarios. Read it as "viable only if prices hold and costs stay low", not as a market size. The ático setback is applied to street-facing facades only, read from the outer edge of the blocks (the plan's own alignments are not used); parcels at the edge of the study area look like street fronts there, a small bias.

**Correction (2026-10-12):** reading the city's Normas Urbanísticas showed the plan's floor count already includes the ground floor (art. 5.33), so the earlier +1 offset overstated the room under the plan by about 3x (154 parcels / 38,880 m² became 65 / 12,237 m²). The first MVP numbers (90 parcels, 11.4 M EUR base) were built on that error. A second correction measured facade and plate on the tallest building part instead of the parcel outline: for 65 of 131 screened parcels the building was under 60% of the outline (one 'parcel' was a whole block of 4,749 m² with a 224 m² building). See ADR 0004.

A third correction (2026-10-12) reads the plan and the zone on the parcel's tallest building part instead of the whole parcel, so a low rear court cannot outvote the front building: room under the plan went from 12,237 to 13,195 m² (65 to 70 parcels), protected parcels from 246 to 270, and Ensanche parcels read as plan height 1 from 110 to 47.

The same plan (art. 6.19.5) allows a penthouse (*ático*) above the cornice, set back 4 m from street facades, in the Ensanche zone. That is the real rooftop route and is now screened (`plan2cost.feasibility.attic_*`): see the table above. Zone comes from the plan's Calificaciones layer (916 of 932 parcels are Ensanche).

**Residential only (2026-10-18).** The numbers above count residential buildings by Catastro use; 6 other-use parcels in Ruzafa (retail, office, industrial) fit homes but are listed apart. The first whole-city run showed why: 28% of the parcels and 47% of the homes were industrial, retail or office.

**Whole València (2026-10-18, ADR 0006).** 1,199 residential rooftop candidates, **2,529 two-bed homes**, residual **-79 M / 129 M / 269 M EUR** (pessimistic / base / optimistic, before structural reinforcement). A further 324 parcels would add 3+ floors (redevelopment) and 596 are not residential: both listed apart and not counted. 59% of the city's parcels have no usable plan height and are not screened. Still no parcel is positive in all three scenarios.

## How it is built (see ADR 0005)

- Deterministic core: rules, geometry, pro-forma. Tested, no AI in the number path.
- AI at the edges: reading plans and normative text (with a human check), proposing layouts, explaining results.
- Every figure carries a status (`plan2cost.claims`).

## Milestones

1. **Done:** claims ledger, pro-forma, residual per parcel in `screening.json`.
2. **Next:** show it in the map's parcel panel (range, status badges, excluded costs); rank the shortlist; export a one-page PDF/HTML report per building.
3. Risk scoring: owners' consent (**LPH read 2026-10-12**: new floors need 3/5 of owners and of quotas, art. 17.4; unanimity under arts. 5 and 17.6 is an open legal question, coded as a flag in `plan2cost.consent`), structure (needs an engineer; start with building age and floors as a flag), lift/stair, protection.
4. Sensitivity: which input flips the sign (price vs hard cost), shown to the user.
5. Real inputs: local quotes from a carpenter, a structural engineer's survey on one building, real sale comparables for Ruzafa. Each replaces an `assumed` with `sourced`.
6. Whole Valencia (M4 of Phase 1) so the shortlist covers the city.

## Kill criteria (decide before building more)

- If the base-case residual stays negative after real hard-cost quotes, the thesis is dead: stop and rethink.
- If no promotor, administrator or architect would pay for or use the shortlist after 5 conversations, the screener is a map, not a business.
- If owners' consent makes most candidates unreachable (to be tested with the lawyer), shift to single-owner buildings only.

## Not in the MVP

Factory or fabrication, financing, a design tool, legal advice, any claim of compliance or a permit.
