import math
from dataclasses import replace

import pytest

from plan2cost.claims import ASSUMED, Assumption
from plan2cost.proforma import DEFAULTS, residual_value


def flat(name, v):
    return Assumption(name, "x", v, v, v, ASSUMED, "test")


def simple(**over):
    """Round numbers: price 2,200 incl. 10% VAT -> 2,000 net; cost 1,000 x 1.0; profit 10%."""
    base = replace(
        DEFAULTS,
        sale_price_per_m2=flat("price", 2200.0),
        vat_rate=flat("vat", 0.10),
        hard_cost_per_m2=flat("hard", 1000.0),
        soft_cost_share=flat("soft", 0.0),
        developer_margin=flat("margin", 0.10),
    )
    return replace(base, **over)


def test_residual_is_revenue_minus_profit_minus_cost():
    r = residual_value(85.0, 0.85, simple())  # 100 built m²
    assert r.built_m2 == 100.0
    # net revenue 200,000; profit 20,000; cost 100,000
    assert r.residual_eur["base"] == 80_000.0
    assert r.residual_per_m2["base"] == 800.0


def test_unknown_reinforcement_is_excluded_and_named_not_priced_at_zero():
    r = residual_value(85.0, 0.85, simple())
    assert r.excluded == ("structural reinforcement",)
    known = simple(reinforcement_per_m2=flat("structural reinforcement", 200.0))
    r2 = residual_value(85.0, 0.85, known)
    assert r2.excluded == ()
    assert r2.residual_eur["base"] == 80_000.0 - 100 * 200.0  # 100 built m² x 200 EUR


def test_scenarios_are_ordered_worst_to_best_with_the_defaults():
    r = residual_value(500.0, 0.85)
    e = r.residual_eur
    assert e["pessimistic"] < e["base"] < e["optimistic"]


def test_defaults_do_not_hide_that_the_pessimistic_case_loses_money():
    r = residual_value(500.0, 0.85)
    assert r.residual_eur["pessimistic"] < 0
    assert r.positive_in_all_scenarios is False


@pytest.mark.parametrize("useful", [None, 0.0, -5.0, math.nan])
def test_no_homes_means_withheld_not_zero(useful):
    r = residual_value(useful, 0.85)
    assert r.residual_eur is None and r.withheld_reason
    assert r.positive_in_all_scenarios is None


def test_a_missing_required_input_withholds_the_result():
    missing = replace(
        DEFAULTS, hard_cost_per_m2=Assumption("hard", "x", None, 1.0, 1.0, ASSUMED, "")
    )
    r = residual_value(100.0, 0.85, missing)
    assert r.residual_eur is None
    assert "hard" in r.withheld_reason


def test_net_to_gross_must_be_a_share():
    with pytest.raises(ValueError):
        residual_value(100.0, 0.0)
    with pytest.raises(ValueError):
        residual_value(100.0, 1.2)
