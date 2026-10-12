"""A deterministic pro-forma for added floors: what could a developer pay for the air rights?

For homes added on top of an existing building there is no land to buy. What the project can
bear is the *residual*: sale revenue minus building cost, soft costs and the developer's
required profit. That residual is the most that could be offered to the owners' community for
the right to build, before the project stops making sense.

    net revenue = built m² x sale price / (1 + VAT)
    cost        = built m² x hard cost x (1 + soft-cost share)        [+ reinforcement if known]
    residual    = net revenue - required profit (a share of net revenue) - cost

It is computed for three scenarios (pessimistic, base, optimistic), because the inputs are
judgements and the sign of the answer often depends on them. Nothing here is a forecast.

Costs with no usable source (structural reinforcement of the existing building) are *excluded
and named* in `Proforma.excluded`, never priced at 0: the residual is then "before
reinforcement", and the screen must say so (ADR 0005).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from plan2cost.claims import ASSUMED, SCENARIOS, SOURCED, Assumption


@dataclass(frozen=True)
class ProformaAssumptions:
    sale_price_per_m2: Assumption  # EUR per built m², VAT included
    vat_rate: Assumption
    hard_cost_per_m2: Assumption  # EUR per built m², contractor price
    soft_cost_share: Assumption  # fees, licences, taxes, financing, as a share of hard cost
    developer_margin: Assumption  # required profit, as a share of net revenue
    reinforcement_per_m2: Assumption  # structure of the existing building; unknown today

    @property
    def required(self) -> tuple[Assumption, ...]:
        return (
            self.sale_price_per_m2,
            self.vat_rate,
            self.hard_cost_per_m2,
            self.soft_cost_share,
            self.developer_margin,
        )


# Pessimistic means "worst for the developer": low price, high cost, high margin.
DEFAULTS = ProformaAssumptions(
    sale_price_per_m2=Assumption(
        "sale price",
        "EUR/built m2 incl. VAT",
        3000.0,
        3400.0,
        3800.0,
        ASSUMED,
        "Range around Idealista's Valencia city resale average (3,378 EUR/m2, May 2026). "
        "The new-build premium and the Ruzafa premium are not verified.",
    ),
    vat_rate=Assumption(
        "VAT on new housing",
        "share",
        0.10,
        0.10,
        0.10,
        SOURCED,
        "10% on new housing in Spain (research report, Construction business model economics).",
    ),
    hard_cost_per_m2=Assumption(
        "hard cost",
        "EUR/built m2",
        1900.0,
        1400.0,
        1131.0,
        ASSUMED,
        "Optimistic = contractor price 1,131 EUR/m2 for the Valencian Community, 2026 (UPV/IVE "
        "report, advocacy author). The rooftop premium for access, crane and tie-in is assumed: "
        "no Spanish rooftop cost per m2 was found.",
    ),
    soft_cost_share=Assumption(
        "soft costs",
        "share of hard cost",
        0.40,
        0.32,
        0.25,
        ASSUMED,
        "Base derived from the Valencia protected-housing cost stack (Feb 2025): fees, licences, "
        "taxes and financing are about 32% of construction cost. Range assumed.",
    ),
    developer_margin=Assumption(
        "required profit",
        "share of net revenue",
        0.20,
        0.15,
        0.12,
        ASSUMED,
        "Listed Spanish developers show 22-27% gross and 6-8% net margins (2025), cyclical "
        "highs. A small project carries more risk per euro, so a profit share is assumed.",
    ),
    reinforcement_per_m2=Assumption(
        "structural reinforcement",
        "EUR/built m2",
        None,
        None,
        None,
        ASSUMED,
        "No source found for Spanish reinforcement costs or the load margin of 1960s-80s "
        "buildings. Needs an engineer's survey per building.",
    ),
)


@dataclass(frozen=True)
class Proforma:
    built_m2: float | None
    residual_eur: dict[str, float] | None  # by scenario; None when withheld
    residual_per_m2: dict[str, float] | None
    excluded: tuple[str, ...] = field(default=())  # cost lines left out because unknown
    withheld_reason: str | None = None

    @property
    def positive_in_all_scenarios(self) -> bool | None:
        if self.residual_eur is None:
            return None
        return all(v > 0 for v in self.residual_eur.values())


def _withheld(reason: str, built_m2: float | None = None) -> Proforma:
    return Proforma(built_m2, None, None, (), reason)


def residual_value(
    useful_m2: float | None,
    net_to_gross: float,
    a: ProformaAssumptions = DEFAULTS,
) -> Proforma:
    """Residual value of `useful_m2` of new homes, by scenario, or a withheld result."""
    if useful_m2 is None or useful_m2 != useful_m2 or useful_m2 <= 0:
        return _withheld("no homes to price")
    if not 0 < net_to_gross <= 1:
        raise ValueError("net_to_gross must be in (0, 1]")
    unknown = [x.name for x in a.required if not x.known]
    if unknown:
        return _withheld("missing inputs: " + ", ".join(unknown))

    built = useful_m2 / net_to_gross
    include_reinforcement = a.reinforcement_per_m2.known
    excluded = () if include_reinforcement else (a.reinforcement_per_m2.name,)

    residual: dict[str, float] = {}
    for s in SCENARIOS:
        revenue = built * a.sale_price_per_m2.value(s) / (1 + a.vat_rate.value(s))
        cost = built * a.hard_cost_per_m2.value(s) * (1 + a.soft_cost_share.value(s))
        if include_reinforcement:
            cost += built * a.reinforcement_per_m2.value(s)
        residual[s] = round(revenue * (1 - a.developer_margin.value(s)) - cost, 0)
    per_m2 = {s: round(v / built, 0) for s, v in residual.items()}
    return Proforma(round(built, 1), residual, per_m2, excluded)
