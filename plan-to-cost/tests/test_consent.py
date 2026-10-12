import pytest

from plan2cost.consent import NEW_FLOORS, REQUIREMENTS, UNANIMITY_RISK, owners_needed


@pytest.mark.parametrize("n, need", [(1, 1), (3, 2), (4, 3), (5, 3), (10, 6), (11, 7), (20, 12)])
def test_three_fifths_rounds_up(n, need):
    assert owners_needed(n) == need


def test_a_simple_majority_of_ten_is_five_not_six():
    assert owners_needed(10, 0.5) == 5
    assert owners_needed(11, 0.5) == 6


def test_bad_input_is_refused():
    with pytest.raises(ValueError):
        owners_needed(0)
    with pytest.raises(ValueError):
        owners_needed(5, 1.5)


def test_new_floors_need_three_fifths_of_owners_and_of_quotas():
    assert (NEW_FLOORS.owners_share, NEW_FLOORS.cuotas_share) == (0.6, 0.6)


def test_every_requirement_quotes_its_clause():
    for r in REQUIREMENTS:
        assert r.clause.startswith("LPH art.") and len(r.quote) > 40


def test_unanimity_is_flagged_as_undecided():
    assert "NOT decided" in UNANIMITY_RISK.what
