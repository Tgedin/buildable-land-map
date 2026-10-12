"""A number with its provenance: the unit of account for everything the product shows.

Every figure that reaches a user is either computed from rule-checked inputs or comes from an
`Assumption`. An assumption says where it came from and how far to trust it, so the screen can
show "assumed" next to a price instead of a bare euro amount (ADR 0005).

Statuses:
    verified  checked against a primary source (law text, filing, official statistic)
    sourced   taken from a secondary source we have read but not verified at the origin
    assumed   our own estimate; no source found. Change it and the result changes
"""

from __future__ import annotations

from dataclasses import dataclass

VERIFIED = "verified"
SOURCED = "sourced"
ASSUMED = "assumed"
STATUSES = (VERIFIED, SOURCED, ASSUMED)

# Order matters: results are reported in this order, worst case first.
SCENARIOS = ("pessimistic", "base", "optimistic")


@dataclass(frozen=True)
class Assumption:
    """An input that is a judgement, with one value per scenario.

    A value of `None` means unknown, not zero: whatever depends on it is excluded from the
    result and named there, never silently priced at 0.
    """

    name: str
    unit: str
    pessimistic: float | None
    base: float | None
    optimistic: float | None
    status: str
    source: str

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {self.status!r}")

    def value(self, scenario: str) -> float | None:
        if scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {SCENARIOS}, got {scenario!r}")
        return getattr(self, scenario)

    @property
    def known(self) -> bool:
        return all(self.value(s) is not None for s in SCENARIOS)
