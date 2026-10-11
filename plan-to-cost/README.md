# Plan-to-Cost Estimator

Phase 2 of the [Housing AI roadmap](../docs/roadmap.md): a floor plan in, an editable priced estimate out.

> Status: **a working toolkit with narrow, honestly-stated coverage.** Plans are code, rules are code, results say what they do not check. Read [docs/rule-sources.md](docs/rule-sources.md) before trusting any output.

```
Parcel (Phase 1 map: footprint, allowed floors, party walls)
        │                                    existing plan image ─► vision U-Net (reads walls, rooms)
        ▼                                                │
Generator (code: parameters -> plan) ─────────────┐      │
                                                  ▼      ▼
                                         Plan model: spaces, uses, openings, heights
                                                  │
              ┌───────────────────────────────────┼──────────────────────────┐
              ▼                                   ▼                          ▼
   Rule engine: Decreto 80/2023          Quantities ─► BC3 prices      Screening: homes that fit
   (each rule quotes its clause;         (parser done; mapping         by area and free facade
   violation / needs review / none)       by hand so far)              (shown on the map)
```

## What exists

- `plan2cost.plan`: the plan model (a dwelling as spaces hosting basic uses, openings, clear heights). Unknown is `None`, never zero.
- `plan2cost.rules`: a deterministic rule engine and 17 rules from Decreto 80/2023 (Comunitat Valenciana, new dwellings), including tables 7 and 8, each quoting its clause. Verdicts are `violation_found`, `needs_review` or `no_violation_found_in_checked_rules`: never "complies". See [rule-sources.md](docs/rule-sources.md) and [ADR 0003](docs/decisions/0003-rules-as-code.md).
- `plan2cost.generate`: two parametric dwelling generators (double-aspect, single-aspect) and a search that keeps the plans the engine does not reject. `python -m plan2cost.generate.explore --bedrooms 2`.
- `plan2cost.feasibility` and `screen_map`: how many homes could be added on a parcel, limited by floor area and free facade ([ADR 0004](docs/decisions/0004-screening.md)). Written to `web/data/screening.json` and shown in the map's parcel panel.
- `plan2cost.vision`, `learn`, `eval`: a classical baseline and a CPU-trained U-Net that read walls and rooms from images (room IoU 0.92, wall IoU 0.71 on CubiCasa5k, Finnish plans only: [model results](docs/model-results.md)).
- `plan2cost.bc3`, `estimate`, `quantify`: price-base parser (runs on a real 59k-concept base), quantities from the plan model, and an estimator that withholds what it cannot trust (ADR 0001).

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
