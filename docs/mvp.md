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
| Rooftop: 1-2 added floors up to the plan's height | 32 | 57 | -1.8 M / 2.9 M / 6.0 M EUR |
| Redevelopment: more than 2 added floors (assumed cap) | 7 | 42 | -1.3 M / 2.2 M / 4.6 M EUR |
| Penthouse (ático) | 7 of 130 eligible | 7 | -0.2 M / 0.3 M / 0.7 M EUR |

The rooftop thesis is the first and third rows: about 60 homes in Ruzafa. The second row is a different business (an old low building cannot carry five new floors). The 2-floor cap is an assumption, not a finding.

No parcel is positive in all three scenarios. Read it as "viable only if prices hold and costs stay low", not as a market size. The ático result is small mostly because every free facade is set back 4 m (street and back yard are not told apart): it is a lower bound, not an estimate.

**Correction (2026-10-12):** reading the city's Normas Urbanísticas showed the plan's floor count already includes the ground floor (art. 5.33), so the earlier +1 offset overstated the room under the plan by about 3x (154 parcels / 38,880 m² became 65 / 12,237 m²). The first MVP numbers (90 parcels, 11.4 M EUR base) were built on that error. A second correction measured facade and plate on the tallest building part instead of the parcel outline: for 65 of 131 screened parcels the building was under 60% of the outline (one 'parcel' was a whole block of 4,749 m² with a 224 m² building). See ADR 0004.

The same plan (art. 6.19.5) allows a penthouse (*ático*) above the cornice, set back 4 m from street facades, in the Ensanche zone. That is the real rooftop route and is now screened (`plan2cost.feasibility.attic_*`): see the table above. Zone comes from the plan's Calificaciones layer (916 of 932 parcels are Ensanche).

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
