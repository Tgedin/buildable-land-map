import pytest

from plan2cost.claims import ASSUMED, SCENARIOS, Assumption


def test_value_by_scenario():
    a = Assumption("price", "EUR", 1.0, 2.0, 3.0, ASSUMED, "test")
    assert [a.value(s) for s in SCENARIOS] == [1.0, 2.0, 3.0]
    with pytest.raises(ValueError):
        a.value("typical")


def test_status_must_be_known():
    with pytest.raises(ValueError):
        Assumption("price", "EUR", 1.0, 2.0, 3.0, "trust me", "test")


def test_unknown_is_none_and_not_known():
    a = Assumption("reinforcement", "EUR", None, None, None, ASSUMED, "no source")
    assert not a.known
    assert Assumption("x", "EUR", 1.0, 1.0, 1.0, ASSUMED, "").known
    assert not Assumption("x", "EUR", 1.0, None, 1.0, ASSUMED, "").known
