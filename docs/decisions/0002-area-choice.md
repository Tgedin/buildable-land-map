# ADR 0002: Area choice, Ruzafa (Valencia)

- **Status:** accepted
- **Date:** 2026-10-11

## Context

M1 needs one neighborhood of ~0.5 km² with open data and people we can reach.

- **Data openness:** Valencia is in the national Catastro WFS (unlike Navarra and País Vasco) and in UTM zone 30N (EPSG:25830), so the config needs no CRS changes. PNOA LiDAR covers it (needed for M2).
- **Size:** bbox `[725450, 4370950, 726250, 4371650]`, 800 × 700 m = 0.56 km². The fetch takes 4 tiles and ~1 min, 5,057 building parts, 932 parcels.
- **Personal access to users:** chosen by the owner, who can reach cooperatives, architects and neighbours in Ruzafa for the M3 discovery conversations. This is the reason it was picked, and I cannot verify it from the data.
- **Urban form:** a dense Eixample-style grid with fairly uniform heights (median 6 floors). The "compare with neighbours" heuristic works best here.

## Decision

Use Ruzafa as the Phase 1 area. Bbox is centred on the Mercat de Russafa.

## Consequences

✅ Real data on day one; short fetch; a tight area users recognise.
⚠️ The gap is a neighbour heuristic. In Ruzafa the biggest "gaps" come from large low-rise parcels (likely facilities, markets, industrial or protected buildings), not from lots that could really be built on. M3 must state this on the map.
⚠️ Single-city results may not generalise to the M4 city scale.

## Revisit when

Discovery conversations show the users who matter are elsewhere, or the heuristic gap in Ruzafa turns out to be mostly unbuildable.
