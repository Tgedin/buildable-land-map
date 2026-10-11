# Working notes for AI assistants

Project: Plan-to-Cost Estimator (Phase 2 of the Housing AI roadmap, see ../docs/roadmap.md).

## Rules

- `make check` must pass before any commit.
- Every new function in `src/plan2cost/` gets a test.
- Never commit real client plans, budgets or licensed price bases (`data/` is gitignored).
- Missing values are `None`/`NaN`, never `0`. An unpriced item and a free item are different facts.
- A number we cannot stand behind is withheld and reported as `needs review`, never guessed.
- No AI attribution lines in commits or PRs.
- Explain non-obvious choices in a docstring or an ADR (`docs/decisions/`).

## The owner learns by reading

Prefer small, readable diffs over clever ones, and explain *why* in commit messages.
