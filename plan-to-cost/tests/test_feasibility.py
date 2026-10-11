import pytest
from shapely.geometry import Polygon, box

from plan2cost import feasibility as F
from plan2cost.feasibility import Assumptions, best_profile, free_facade_m, screen


def test_party_walls_do_not_count_as_facade():
    lot = box(0, 0, 10, 20)  # 10 m frontage, 20 m deep
    neighbours = [box(-10, 0, 0, 20), box(10, 0, 20, 20)]  # both long sides are party walls
    # free: the two short ends (10 + 10 m), minus a little at each corner next to a neighbour
    assert free_facade_m(lot, neighbours) == pytest.approx(20.0, abs=1.5)
    assert free_facade_m(lot, []) == pytest.approx(60.0)  # a detached lot: all four sides


def test_a_neighbour_far_away_is_ignored():
    lot = box(0, 0, 10, 20)
    assert free_facade_m(lot, [box(50, 0, 60, 20)]) == pytest.approx(60.0)


def test_small_light_wells_are_not_facade_but_large_courtyards_are():
    small = Polygon(box(0, 0, 20, 20).exterior.coords, [box(8, 8, 11, 11).exterior.coords])  # 9 m²
    large = Polygon(
        box(0, 0, 20, 20).exterior.coords, [box(5, 5, 15, 15).exterior.coords]
    )  # 100 m²
    assert free_facade_m(small, []) == pytest.approx(80.0)
    assert free_facade_m(large, []) == pytest.approx(80.0 + 40.0)


def test_profiles_are_real_rule_checked_dwellings():
    p = best_profile(2, "single-aspect")
    assert p is not None and p.n_bedrooms == 2 and p.typology == "single-aspect"
    assert p.useful_m2 > 35 and p.facade_needed_m == p.width_m  # one facade
    d = best_profile(2, "double-aspect")
    assert d is not None and d.facade_needed_m == pytest.approx(2 * d.width_m)  # two facades
    assert best_profile(3, "double-aspect") is None  # none found without a review item


def test_screening_takes_the_smaller_of_area_and_facade():
    # plenty of area, little facade: facade limits
    s = screen(plate_m2=400, free_facade=10.0, added_floors=1, n_bedrooms=2)
    assert s.limit == "facade" and s.homes_per_floor == s.facade_cap == 1
    # plenty of facade, little area: area limits
    s = screen(plate_m2=60, free_facade=60.0, added_floors=1, n_bedrooms=1)
    assert s.limit == "area" and s.homes_per_floor == s.area_cap


def test_homes_scale_with_added_floors_and_zero_floors_means_none():
    one = screen(300, 30, 1, 2)
    three = screen(300, 30, 3, 2)
    assert three.homes == 3 * one.homes and one.homes > 0
    assert screen(300, 30, 0, 2).homes == 0


def test_a_plate_smaller_than_the_core_gives_nothing():
    s = screen(plate_m2=15, free_facade=30, added_floors=2, n_bedrooms=1)
    assert s.homes == 0 and s.area_cap == 0 and s.limit == "area"


def test_assumptions_change_the_answer_and_are_reported():
    base = screen(200, 40, 1, 2)
    tight = screen(200, 40, 1, 2, Assumptions(net_to_gross=0.70, core_m2=30.0))
    assert tight.homes <= base.homes
    assert base.not_checked and "structure" in base.not_checked[0]  # the caveats always travel


def test_nothing_checked_beyond_the_dwelling_is_hidden():
    s = screen(200, 40, 1, 2)
    text = " ".join(s.not_checked)
    for word in ("structure", "fire", "consent", "lift"):
        assert word in text


def test_module_exports_the_caveat_list():
    assert len(F.NOT_CHECKED) >= 5
