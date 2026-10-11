import pytest

from plan2cost.generate.single_aspect import SingleAspectParams, generate_single_aspect
from plan2cost.plan import COMMON, EXTERIOR, Use
from plan2cost.rules import engine
from plan2cost.rules.engine import Status
from plan2cost.rules.valencia_d80 import rules

RULES = rules()


def fails(d):
    return {f.rule_id for f in engine.check(d, RULES).by_status(Status.FAIL)}


def test_spaces_tile_the_footprint():
    p = SingleAspectParams(11.5)
    d = generate_single_aspect(p)
    assert d is not None and d.n_bedrooms == 2
    assert d.interior_area_m2 == pytest.approx(11.5 * p.depth_m)


def test_all_windows_are_on_one_facade_and_the_entrance_is_opposite():
    d = generate_single_aspect(SingleAspectParams(11.5))
    wins = [o for o in d.openings if EXTERIOR in (o.a, o.b)]
    for o in wins:
        assert d.space(o.a).polygon.bounds[1] == 0.0  # every window room touches y = 0
    entrance = next(o for o in d.openings if COMMON in (o.a, o.b))
    assert d.space(entrance.a).polygon.bounds[3] == pytest.approx(SingleAspectParams(11.5).depth_m)


def test_a_wide_enough_flat_has_no_violation():
    d = generate_single_aspect(SingleAspectParams(12.0, 2, facade_depth_m=5.0))
    assert d is not None and fails(d) == set(), fails(d)


def test_three_bedrooms_get_two_bathrooms():
    d = generate_single_aspect(SingleAspectParams(14.0, 3, facade_depth_m=5.0))
    assert d is not None and len(d.with_use(Use.BANO)) == 2
    assert "VAL-D80-52.4" not in fails(d)


def test_too_narrow_a_facade_returns_none():
    assert generate_single_aspect(SingleAspectParams(8.0, 2)) is None  # living would be 2.0 m wide
    assert generate_single_aspect(SingleAspectParams(12.0, 4)) is None


def test_the_rules_catch_a_living_room_that_is_too_small():
    d = generate_single_aspect(SingleAspectParams(9.5, 2, facade_depth_m=4.0))
    assert d is not None and "VAL-D80-54.2" in fails(d)  # living far below the table 7 minimum


def test_circulation_is_connected_from_the_entrance_to_every_room():
    d = generate_single_aspect(SingleAspectParams(12.0, 2, facade_depth_m=5.0))
    reach = d.reachable_from(d.entrance_space())
    assert {s.id for s in d.spaces if s.is_interior} <= reach


def test_deep_living_room_runs_the_full_depth_and_the_flat_still_tiles():
    p = SingleAspectParams(10.5, 2, facade_depth_m=4.2, deep_living=True)
    d = generate_single_aspect(p)
    assert d is not None
    assert d.interior_area_m2 == pytest.approx(p.width_m * p.depth_m)
    assert d.space("living").polygon.bounds[3] == pytest.approx(p.depth_m)  # full depth
    assert d.space("bed1").polygon.bounds[3] == pytest.approx(p.facade_depth_m)  # facade band only


def test_deep_living_flat_is_connected_and_judged_by_the_same_rules():
    d = generate_single_aspect(SingleAspectParams(11.0, 2, facade_depth_m=4.2, deep_living=True))
    assert d is not None
    assert {s.id for s in d.spaces if s.is_interior} <= d.reachable_from(d.entrance_space())
    assert fails(d) <= {"VAL-D80-54.2", "VAL-D80-56"}  # only room sizes can still fail
