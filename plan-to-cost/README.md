# Plan-to-Cost Estimator

Phase 2 of the [Housing AI roadmap](../docs/roadmap.md): a floor plan in, an editable priced estimate out.

> Status: **core + a measured baseline.** BC3 parser and quantities-to-cost are tested (and the parser runs on a real 59k-concept price base). A classical plan-reading baseline exists and was measured on CubiCasa5k: **not usable for pricing** (median shape error +35%, [results](docs/baseline-results.md)). Nothing is validated on real Spanish plans or budgets yet.

```
Floor plan (PDF/image) ─► vision: walls, rooms                      [classical baseline, weak]
                       ─► quantities (m² floor, m wall, units)    [input type exists: Quantity]
                       ─► map to BC3 price items                  [dict mapping; LLM suggestion later]
                       ─► priced estimate + review list           [done, tested]
```

## What exists

- `plan2cost.bc3`: parse FIEBDC-3 price bases (concepts, decompositions, texts), search by summary.
- `plan2cost.estimate`: price quantities against a base. Lines that cannot be trusted (unmapped, unit mismatch, no price, low detection confidence) are listed under `needs_review` and excluded from the total. `cost_per_m2` is only given for a complete estimate.

## Train on a free GPU

[Open the notebook in Colab](https://colab.research.google.com/github/Tgedin/buildable-land-map/blob/main/plan-to-cost/notebooks/train_on_colab.ipynb): downloads CubiCasa5k, trains the U-Net and scores it on the test split. The GPU path has not been run on a GPU yet.

## Rule that shapes the design

A number we cannot stand behind is withheld, not guessed (ADR 0001).

## Data

Price bases and plans are not committed (`data/` is ignored): they can be licensed or carry client data. The test fixture `tests/fixtures/sample.bc3` is synthetic and says so.

## Dev

```bash
uv venv .venv && . .venv/bin/activate && make setup && make check
```
