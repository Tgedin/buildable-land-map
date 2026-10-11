"""Turn measured quantities into a priced estimate, withholding what cannot be trusted.

Each quantity (e.g. 42.5 m² of partition wall) is mapped to a BC3 price code. A line is
priced only if the mapping exists, the code is in the price base, the units agree, the
price exists and the detection confidence is high enough. Every other line is kept, with
a status saying why, and left out of the total: a missing price is not 0 €, and a low
confidence plan reading must go back to a human instead of becoming a wrong number.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from plan2cost.bc3 import PriceBase

PRICED = "priced"
NEEDS_REVIEW = {"unmapped", "unknown_code", "unit_mismatch", "no_price", "low_confidence"}


@dataclass(frozen=True)
class Quantity:
    key: str  # what was measured, e.g. "partition_wall"
    amount: float
    unit: str  # "m2", "m", "ud"
    confidence: float = 1.0  # 0..1; 1.0 for amounts a person typed in


@dataclass(frozen=True)
class LineItem:
    key: str
    amount: float
    unit: str
    status: str  # PRICED or one of NEEDS_REVIEW
    code: str | None = None
    summary: str | None = None
    unit_price: float | None = None
    cost: float | None = None  # None unless status == PRICED


@dataclass
class Estimate:
    items: list[LineItem] = field(default_factory=list)
    built_area_m2: float | None = None

    @property
    def total(self) -> float:
        """Sum of the priced lines only. Read it together with `complete`."""
        return round(sum(i.cost for i in self.items if i.cost is not None), 2)

    @property
    def needs_review(self) -> list[LineItem]:
        return [i for i in self.items if i.status in NEEDS_REVIEW]

    @property
    def complete(self) -> bool:
        return bool(self.items) and not self.needs_review

    @property
    def cost_per_m2(self) -> float | None:
        """Only given for a complete estimate: a partial total / m² would look too cheap."""
        if not self.complete or not self.built_area_m2:
            return None
        return round(self.total / self.built_area_m2, 2)


def _norm_unit(unit: str) -> str:
    return unit.strip().lower().replace("²", "2").replace("m^2", "m2")


def price_line(
    q: Quantity, mapping: dict[str, str], base: PriceBase, min_confidence: float
) -> LineItem:
    def item(status: str, **kw) -> LineItem:
        return LineItem(q.key, q.amount, q.unit, status, **kw)

    code = mapping.get(q.key)
    if code is None:
        return item("unmapped")
    concept = base.get(code)
    if concept is None:
        return item("unknown_code", code=code)
    shown = {"code": code, "summary": concept.summary, "unit_price": concept.price}
    if _norm_unit(concept.unit) != _norm_unit(q.unit):
        return item("unit_mismatch", **shown)
    if concept.price is None:
        return item("no_price", **shown)
    if q.confidence < min_confidence:
        return item("low_confidence", **shown)
    return item(PRICED, cost=round(q.amount * concept.price, 2), **shown)


def estimate(
    quantities: list[Quantity],
    mapping: dict[str, str],
    base: PriceBase,
    min_confidence: float = 0.6,
    built_area_m2: float | None = None,
) -> Estimate:
    items = [price_line(q, mapping, base, min_confidence) for q in quantities]
    return Estimate(items=items, built_area_m2=built_area_m2)
