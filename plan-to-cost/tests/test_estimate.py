from pathlib import Path

import pytest

from plan2cost import bc3, estimate
from plan2cost.estimate import Quantity

BASE = bc3.load_bc3(Path(__file__).parent / "fixtures" / "sample.bc3")
MAP = {"partition_wall": "EFS010", "paint": "EPT010", "door": "CARP010", "x": "NOPRICE"}


def _by_key(est):
    return {i.key: i for i in est.items}


def test_priced_lines_and_total():
    est = estimate.estimate(
        [Quantity("partition_wall", 10, "m2"), Quantity("door", 3, "ud")], MAP, BASE
    )
    items = _by_key(est)
    assert items["partition_wall"].cost == pytest.approx(185.0)
    assert items["door"].cost == pytest.approx(360.0)
    assert est.total == pytest.approx(545.0)
    assert est.complete


def test_unmapped_unknown_and_unpriced_are_flagged_not_zero():
    est = estimate.estimate(
        [
            Quantity("window", 4, "ud"),  # nothing maps it
            Quantity("paint", 5, "m2"),
            Quantity("ghost", 1, "ud"),
            Quantity("x", 2, "m"),  # concept has no price
        ],
        {**MAP, "ghost": "DOES_NOT_EXIST"},
        BASE,
    )
    items = _by_key(est)
    assert items["window"].status == "unmapped" and items["window"].cost is None
    assert items["ghost"].status == "unknown_code"
    assert items["x"].status == "no_price" and items["x"].cost is None
    assert est.total == pytest.approx(21.5)  # only the paint
    assert not est.complete
    assert len(est.needs_review) == 3


def test_unit_mismatch_is_not_priced():
    est = estimate.estimate([Quantity("partition_wall", 10, "ud")], MAP, BASE)
    assert est.items[0].status == "unit_mismatch"
    assert est.total == 0 and not est.complete  # total 0 here means "nothing priced"


def test_unit_spelling_is_normalised():
    est = estimate.estimate([Quantity("paint", 2, "m²")], MAP, BASE)
    assert est.items[0].status == "priced"


def test_low_confidence_goes_back_to_a_human():
    est = estimate.estimate(
        [Quantity("partition_wall", 10, "m2", confidence=0.4)], MAP, BASE, min_confidence=0.6
    )
    assert est.items[0].status == "low_confidence"
    assert est.items[0].cost is None
    assert est.items[0].unit_price == 18.5  # shown so the reviewer sees what would apply


def test_cost_per_m2_only_when_complete():
    full = estimate.estimate([Quantity("paint", 10, "m2")], MAP, BASE, built_area_m2=50)
    assert full.cost_per_m2 == pytest.approx(0.86)
    partial = estimate.estimate(
        [Quantity("paint", 10, "m2"), Quantity("window", 1, "ud")], MAP, BASE, built_area_m2=50
    )
    assert partial.cost_per_m2 is None


def test_empty_estimate_is_not_complete():
    est = estimate.estimate([], MAP, BASE)
    assert not est.complete and est.cost_per_m2 is None
