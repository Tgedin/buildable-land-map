# ADR 0005: AI proposes and perceives; deterministic code decides; every number has a status

- **Status:** accepted
- **Date:** 2026-10-12

## Context

The product is going to cover more ground (screening, economics, risk, reports) and AI can do much of the reading and drafting. In housing a wrong number does real damage: a refused permit, a project that loses money. We need a rule for where AI is allowed to sit.

## Decision

1. **AI is used for perception and proposal.** Reading plan images and normative text, drafting rules from a clause (quoted, then approved by a person), proposing layouts and massing, explaining results, drafting reports.
2. **Numbers and verdicts come from deterministic code.** Rule checks, geometry, quantities, prices and the pro-forma are plain, tested functions. An AI step never writes a figure that reaches a user.
3. **Generate and test.** Any generator, learned or not, sits behind the rule engine, which already rejects candidates (ADR 0003).
4. **Every figure has a status** (`plan2cost.claims`): `verified`, `sourced` or `assumed`. Unknown is `None` and is excluded and named, never 0 (ADR 0001).
5. **Rules drafted by an AI are code only after a human approves them**, with the quoted clause attached.

## Consequences

✅ A reader can see what to trust and what to check.
✅ The deterministic core is testable and reproducible.
⚠️ A human approval step for drafted rules costs time; it is the point.
⚠️ Beauty and quality cannot be verified like a rule. They will be shown as labelled proxies (daylight, ventilation, proportions), never pass/fail.

## Revisit when

An AI step is proposed for anything that outputs a number or verdict, or a status turns out to be too coarse for what users need.
