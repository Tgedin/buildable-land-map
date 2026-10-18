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


def test_attic_plate_is_set_back_from_free_facades_only():
    from plan2cost.feasibility import attic_plate_m2

    lot = box(0, 0, 10, 20)
    party = [box(-10, 0, 0, 20), box(10, 0, 20, 20)]  # both long sides are party walls
    # free: the two 10 m ends. A 4 m setback at each end leaves 10 x 12 m = 120 m² of 200 m²
    assert attic_plate_m2(lot, party, 200.0) == pytest.approx(120.0, abs=8.0)
    # detached: 4 m all round leaves 2 x 12 = 24 m²
    assert attic_plate_m2(lot, [], 200.0) == pytest.approx(24.0, abs=1.0)


def test_attic_plate_scales_with_the_built_footprint():
    from plan2cost.feasibility import attic_plate_m2

    lot = box(0, 0, 10, 20)
    full = attic_plate_m2(lot, [], 200.0)
    assert attic_plate_m2(lot, [], 100.0) == pytest.approx(full / 2)  # half the parcel is yard


@pytest.mark.parametrize(
    ("zone", "klass", "plan", "floors", "ok", "why"),
    [
        ("ENS", "at_limit", 5.0, 5.0, True, "eligible"),
        ("ENS", "plan_gap", 6.0, 4.0, True, "eligible"),  # must first reach the plan's 6
        ("ENS", "at_limit", 8.0, 8.0, True, "eligible"),
        ("ENS", "at_limit", 9.0, 9.0, False, "plan_over_8_floors"),
        ("ENS", "at_limit", 1.0, 1.0, False, "plan_ground_floor_only"),  # block interior
        ("ENS", "at_limit", 5.0, 7.0, False, "already_above_plan"),  # may have an ático already
        ("ENS", "protected", None, 5.0, False, "no_buildable_plan_height"),
        ("ENS", "public_use", 5.0, 5.0, False, "no_buildable_plan_height"),
        ("RV", "at_limit", 5.0, 5.0, False, "not_ensanche"),
        (None, "at_limit", 5.0, 5.0, False, "zone_unknown"),  # never guessed
        ("ENS", "at_limit", 5.0, None, False, "floors_unknown"),
        ("ENS", "at_limit", None, 5.0, False, "floors_unknown"),
    ],
)
def test_attic_eligibility_follows_art_6_19_5(zone, klass, plan, floors, ok, why):
    from plan2cost.feasibility import attic_eligibility

    assert attic_eligibility(zone, klass, plan, floors) == (ok, why)


def _block():
    """Two 10 x 20 m rows back to back: a block 20 x 20 m, streets all round."""
    front = box(0, 0, 20, 10)  # south row
    back = box(0, 10, 20, 20)  # north row
    return front, back


def test_public_edge_is_the_outer_boundary_of_the_block_only():
    from plan2cost.feasibility import public_edge

    front, back = _block()
    edge = public_edge([front, back])
    assert edge.length == pytest.approx(80.0, abs=0.5)  # the block's perimeter
    assert not edge.intersects(Polygon([(2, 9.9), (18, 9.9), (18, 10.1), (2, 10.1)]))  # party line


def test_public_edge_closes_sliver_gaps_between_neighbours():
    from plan2cost.feasibility import public_edge

    a, b = box(0, 0, 10, 20), box(10.2, 0, 20, 20)  # a 20 cm gap between the two parcels
    assert public_edge([a, b]).length == pytest.approx(80.0, abs=1.0)  # no inner edge from the gap


def test_street_facade_leaves_out_the_back_yard():
    from plan2cost.feasibility import public_edge, street_facade_m

    # three parcels in a row (a block 30 x 30): the middle one has a street front and a
    # back that meets a fourth parcel behind it, so only the front is on the street
    mid = box(10, 0, 20, 20)
    parcels = [box(0, 0, 10, 20), mid, box(20, 0, 30, 20), box(0, 20, 30, 30)]
    edge = public_edge(parcels)
    neighbours = [p for p in parcels if p is not mid]
    assert street_facade_m(mid, neighbours, edge) == pytest.approx(10.0, abs=1.0)  # the front only


def test_attic_setback_with_an_edge_only_applies_to_street_facades():
    from plan2cost.feasibility import attic_plate_m2, public_edge

    # a deep parcel (10 x 30 m) between two neighbours; the building (10 x 15 m) stands at the
    # street front (y = 0) and its rear faces the parcel's own yard
    left, right = box(-10, 0, 0, 30), box(10, 0, 20, 30)
    parcel, building = box(0, 0, 10, 30), box(0, 0, 10, 15)
    edge = public_edge([left, parcel, right])
    # every free facade set back (front 4 m and rear 4 m): 10 x 7 m
    assert attic_plate_m2(building, [left, right], 150.0) == pytest.approx(70.0, abs=2.0)
    # only the street facade set back: 10 x 11 m, the rear faces a yard and keeps its area
    street_only = attic_plate_m2(building, [left, right], 150.0, edge=edge)
    assert street_only == pytest.approx(110.0, abs=2.0)


def test_a_big_floor_plate_needs_more_than_one_stair_core():
    a = Assumptions(net_to_gross=0.85, core_m2=18.0, plate_per_core_m2=600.0)
    one = screen(500.0, 400.0, 1, 2, a)  # one core: 500 m² plate
    big = screen(3000.0, 4000.0, 1, 2, a)  # five cores
    gross = big.profile.useful_m2 / a.net_to_gross
    assert big.area_cap == int((3000.0 - 5 * 18.0) // gross)  # five cores taken out, not one
    assert one.area_cap == int((500.0 - 18.0) // gross)
    # the same plate with a single core would have fitted more homes: the assumption has a cost
    single = Assumptions(net_to_gross=0.85, core_m2=18.0, plate_per_core_m2=1e9)
    assert screen(3000.0, 4000.0, 1, 2, single).area_cap >= big.area_cap
