# Plan-to-Cost Estimator

Phase 2 of the [Housing AI roadmap](../docs/roadmap.md): a floor plan in, an editable priced estimate out.

> Status: **core only**. BC3 price-base parser and the quantities-to-cost step exist and are tested on a synthetic price base. Plan reading (vision) is not started. Nothing here is validated against real plans or budgets yet.

```
Floor plan (PDF/image) ─► vision: walls, rooms, doors, windows   [not started]
                       ─► quantities (m² floor, m wall, units)    [input type exists: Quantity]
                       ─► map to BC3 price items                  [dict mapping; LLM suggestion later]
                       ─► priced estimate + review list           [done, tested]
```

## What exists

- `plan2cost.bc3`: parse FIEBDC-3 price bases (concepts, decompositions, texts), search by summary.
- `plan2cost.estimate`: price quantities against a base. Lines that cannot be trusted (unmapped, unit mismatch, no price, low detection confidence) are listed under `needs_review` and excluded from the total. `cost_per_m2` is only given for a complete estimate.

## Rule that shapes the design

A number we cannot stand behind is withheld, not guessed (ADR 0001).

## Data

Price bases and plans are not committed (`data/` is ignored): they can be licensed or carry client data. The test fixture `tests/fixtures/sample.bc3` is synthetic and says so.

## Dev

```bash
uv venv .venv && . .venv/bin/activate && make setup && make check
```
