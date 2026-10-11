# ADR 0001: Withhold a number rather than guess it

- **Status:** accepted
- **Date:** 2026-10-11

## Context

An estimate that looks complete but hides a failed plan reading or a missing price is worse than no estimate: the user trusts it. The roadmap says low-confidence readings must fall back to manual input.

## Decision

Every line has a status. Only `priced` lines contribute to the total. Unmapped, unknown-code, unit-mismatch, no-price and low-confidence lines stay in the output with their reason, cost `None`. `cost_per_m2` is `None` unless every line is priced.

## Consequences

✅ The user always sees what is missing, and can fix it (the correction loop is the training data later).
⚠️ Estimates look "incomplete" more often at first. That is the honest state.

## Revisit when

Measured error on real projects shows a lower confidence threshold is safe.
