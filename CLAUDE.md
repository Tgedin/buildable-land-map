# Working notes for AI assistants

Project: Buildable Land Map (Phase 1 of docs/roadmap.md). Milestones and gates: ACCEPTANCE.md.

## Rules

- `make check` must pass before any commit.
- Every new function in `src/blm/` gets a test. Use `blm.synthetic` for known-truth data.
- Never commit anything under `data/raw`, `data/interim` or `data/processed`.
- Coordinates: UTM metres (EPSG from config) everywhere in Python; WGS84 only in `export.py` and `web/`.
- Missing values are `NaN`/`None`, never `0`. Zero floors and unknown floors are different facts.
- Keep `web/` framework-free: plain HTML/CSS/JS, no build step.
- Explain non-obvious choices in a docstring or an ADR (`docs/decisions/`).

## The owner learns by reading

The repo owner is building FDE skills. Prefer small, readable diffs over clever ones, and explain *why* in commit messages.
