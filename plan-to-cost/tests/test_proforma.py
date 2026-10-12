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


def test_sensitivity_breakeven_is_where_the_residual_is_zero():
    from plan2cost.proforma import sensitivity

    sens = sensitivity(simple())["base"]  # net 2,000; profit 10%; cost 1,000
    assert sens.residual_per_m2 == 800.0
    # price at which 10% profit and 1,000 cost leave nothing: 1,000 / 0.9 net, x 1.1 VAT
    assert sens.breakeven_sale_price == pytest.approx(1000 / 0.9 * 1.1, abs=1)
    assert sens.breakeven_hard_cost == pytest.approx(2000 * 0.9, abs=1)
    assert sens.cost_budget_per_m2 == 800.0


def test_breakeven_values_really_zero_the_residual():
    from plan2cost.proforma import sensitivity

    a = simple()
    sens = sensitivity(a)["base"]
    at_price = replace(a, sale_price_per_m2=flat("price", sens.breakeven_sale_price))
    at_cost = replace(a, hard_cost_per_m2=flat("hard", sens.breakeven_hard_cost))
    assert abs(residual_value(100.0, 1.0, at_price).residual_per_m2["base"]) <= 1
    assert abs(residual_value(100.0, 1.0, at_cost).residual_per_m2["base"]) <= 1


def test_a_loss_has_no_cost_budget_and_costs_hurt_prices_help():
    from plan2cost.proforma import sensitivity

    sens = sensitivity()  # defaults: the pessimistic case loses money
    assert sens["pessimistic"].residual_per_m2 < 0
    assert sens["pessimistic"].cost_budget_per_m2 == 0.0  # never negative: no room for extras
    e = sens["base"].effect_of_10pct
    assert e["sale price"] > 0 and e["hard cost"] < 0 and e["required profit"] < 0


def test_sensitivity_is_withheld_when_an_input_is_unknown():
    from plan2cost.proforma import sensitivity

    missing = replace(
        DEFAULTS, hard_cost_per_m2=Assumption("hard", "x", None, 1.0, 1.0, ASSUMED, "")
    )
    assert sensitivity(missing) is None
