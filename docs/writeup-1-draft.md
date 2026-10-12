# DRAFT: write-up #1 (not published)

Numbers are from the repository on 2026-10-12, Ruzafa only. They will be redone for the whole city when that run lands. Everything below is a screening, not a design, a valuation or a permit.

**Working title:** From 168,000 m² to 12,000 m²: what the city plan does to a "missing floors" map of Ruzafa

## The question
Housing is expensive partly because it is hard to see what could be built. Spanish public data can show how a building compares with its street. This map started there, for one neighbourhood, Ruzafa in València (0.56 km², 932 parcels). It now asks a sharper question: **on which buildings could homes be added on top, how many, and what could that project pay for the air rights?**

## The first number, and why it was wrong
Compare each building with the median height of the parcels within 50 m, and 280 of 932 parcels sit below their street: about **167,826 m²** of "missing" floor area. It is a tempting headline and it is mostly not buildable. Schools, markets, a railway station and protected buildings all look like gaps.

Replace the neighbours with the city plan (PGOU heights, protection, Catastro use) and only **65 parcels** have room, **12,237 m²**. 246 parcels are protected, 607 are already at the plan's height, 7 are public uses.

I did not get there directly. My first plan-based answer was **154 parcels and 38,880 m²**, three times too high. I had assumed the plan's height field counts floors *above* the ground floor. The plan's own norms say the opposite: art. 5.33 defines the number of floors as "incluida la planta baja". I had even misread a formula in the same text as supporting my assumption. Reading the clause fixed it. The lesson is boring and true: read the rule before you model it.

## What actually fits
Two legal routes, using real rule-checked dwellings (Decreto 80/2023) as the unit, limited by floor area and by free facade:

| Route | Parcels | Two-bed homes |
|---|---|---|
| Add 1 or 2 floors up to the plan's height | 32 | 57 |
| Penthouse above the cornice (norms art. 6.19.5), set back 4 m from the street | 30 | 31 |

Together: 58 parcels and about **88 two-bedroom homes**. A further 7 parcels could add three or more floors; an old building rarely carries that, so I call it redevelopment and do not count it. (The cap of two floors is my assumption.)

## What it could pay
Net sale revenue minus building cost and the developer's required profit leaves a *residual*: the most the homes could pay the owners for the right to build. Because the inputs are judgements, it is shown for three scenarios:

**about 4.4 M € in the base case, from −2.7 M € (pessimistic) to 9.2 M € (optimistic)**, before structural reinforcement.

Per m² of new floor, the base case leaves about 779 €. That reaches zero if the sale price falls about 30% (3,400 to 2,392 €/m²) or the hard cost rises about 42% (1,400 to 1,990 €/m²). **No parcel is positive in all three scenarios.** The prices, costs and profit are assumed and labelled as such: I did not run interviews or collect quotes, because the cost of a rooftop job varies too much between carpenters, buildings and months to be one number.

## What stands in the way
- **Structure.** Whether the existing building can carry more floors decides the project, and there is no source in the numbers for it. It needs an engineer per building.
- **Owners.** Adding floors needs three fifths of the owners holding three fifths of the quotas (Ley de Propiedad Horizontal, art. 17.4), the consent of those affected and a compensation. Whether it triggers unanimity, because it creates new quotas (arts. 5 and 17.6), I could not settle from the text. That is a question for a lawyer, and it decides how many of these buildings are reachable.

## How good the inputs are
Catastro floors were checked against a 2015 LiDAR cloud: 86% of 1,987 parts are within one floor, with a systematic +0.9 floor bias because roofs include parapets and lift housings (3.6 m per floor, not 3.0). The worst disagreements were measurement artefacts, not Catastro errors (`docs/validation-m2.md`). Catastro and LiDAR are 11 years apart here.

## Known weaknesses
A parcel is matched to the plan polygon covering most of the parcel, not of the building, so a tall front building with a low rear court can be misread. The street side of a facade is read from the outer edge of the blocks. The plan layer is the published one; recent modifications may be missing.

## What I learned from users
No conversations yet, so this section is empty on purpose. It will be written after real people have used the map, not before.

## Link
https://tgedin.github.io/buildable-land-map/ · every number carries its status (verified, sourced or assumed) and the method page lists what is not checked. Code, decisions and data sources are in the repo.
