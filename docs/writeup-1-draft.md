# DRAFT: write-up #1 (not published; numbers are from the repo at commit time)

**Working title:** From 168,000 m² to 39,000 m²: what the plan does to a "missing floor area" map of Ruzafa

## The question
Land is expensive partly because it is hard to see what could be built. Spanish public data can show how a building compares with its street. This map does that for one neighbourhood, Ruzafa in Valencia (0.56 km², 932 parcels).

## The method (3 lines)
Catastro building parts give footprints and floors. For each parcel, the "street height" is the median floors of parcels within 50 m. The gap is the footprint of the building's tallest part times the missing floors. (ADR 0003 explains why courtyards are excluded.)

## The number
Against the neighbours, 280 of 932 parcels sit below their street: about 167,826 m² "missing". Against the municipal plan (PGOU heights, protection, Catastro use), only 154 parcels have room, about 38,880 m². 246 parcels are protected, 518 are already at the plan height. About three quarters of the first number was never buildable. **Caveat:** the plan view assumes the plan's `altura` excludes the ground floor; with other readings the total is 12,000 to 83,000 m².

## How good are the inputs
Catastro floors were checked against a 2015 LiDAR cloud: 86% of 1,987 parts are within one floor, with a systematic +0.9 floor bias because roofs include parapets and lift housings (3.6 m per floor, not 3.0). The worst disagreements were measurement artefacts, not Catastro errors. (`docs/validation-m2.md`)

## What this is not
Not zoning (PGOU). Schools, markets, churches, the railway station and protected buildings show up as gaps and are not buildable. Catastro and LiDAR are 11 years apart here.

## What I learned from users
_(fill in after the 5 conversations)_

## Link
https://tgedin.github.io/buildable-land-map/ · code and data sources in the repo.
