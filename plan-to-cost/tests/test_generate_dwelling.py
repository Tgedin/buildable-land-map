import pytest

from plan2cost.generate.dwelling import DwellingParams, generate
from plan2cost.plan import Use
from plan2cost.rules import engine
from plan2cost.rules.engine import Status
from plan2cost.rules.valencia_d80 import rules

RULES = rules()


def fails(d):
    return {f.rule_id for f in engine.check(d, RULES).by_status(Status.FAIL)}


def test_default_two_bedroom_flat_has_no_violation():
    d = generate(DwellingParams(8.0, 9.0))
    assert d is not None and d.n_bedrooms == 2
    assert fails(d) == set()
    assert d.interior_area_m2 == pytest.approx(72.0)  # spaces tile the footprint exactly


def test_spaces_tile_the_footprint_without_overlap():
    d = generate(DwellingParams(12.5, 9.5, n_bedrooms=3, closed_kitchen=True))
    interior = [s for s in d.spaces if s.is_interior]
    union = interior[0].polygon
    for s in interior[1:]:
        assert union.intersection(s.polygon).area == pytest.approx(0.0, abs=1e-9)
        union = union.union(s.polygon)
    assert union.area == pytest.approx(12.5 * 9.5)


def test_three_bedrooms_get_two_bathrooms_and_pass_the_rules():
    d = generate(DwellingParams(12.5, 9.0, n_bedrooms=3))
    assert d is not None and len(d.with_use(Use.BANO)) == 2
    assert fails(d) == set()


def test_closed_kitchen_variant_passes():
    d = generate(DwellingParams(9.0, 9.0, closed_kitchen=True))
    assert d is not None and d.with_use(Use.COCINA)[0].id == "kitchen"
    assert fails(d) == set()


@pytest.mark.parametrize(
    "params",
    [
        DwellingParams(5.0, 9.0),  # too narrow for two bedrooms and a bath
        DwellingParams(10.5, 9.0, n_bedrooms=3),  # three bedrooms and two baths need ~11.9 m
        DwellingParams(8.0, 5.0),  # too shallow for three bands
        DwellingParams(8.0, 9.0, n_bedrooms=4),
        DwellingParams(8.0, 9.0, n_bedrooms=0),
    ],
)
def test_impossible_parameters_return_none_not_a_broken_plan(params):
    assert generate(params) is None


def test_the_rules_catch_what_the_generator_is_told_to_get_wrong():
    assert "VAL-D80-51.2.a" in fails(generate(DwellingParams(8.0, 9.0, corridor_w_m=0.85)))
    assert "VAL-D80-51.1.b" in fails(generate(DwellingParams(8.0, 9.0, door_w_m=0.65)))
    assert "VAL-D80-55.1" in fails(generate(DwellingParams(8.0, 9.0, ceiling_m=2.40)))
    assert "VAL-D80-54.1" in fails(
        generate(DwellingParams(5.0, 6.9, n_bedrooms=1, day_depth_m=3.0))
    )


def test_one_bedroom_flat_can_be_small_but_legal():
    d = generate(DwellingParams(6.0, 7.0, n_bedrooms=1, day_depth_m=3.2, corridor_w_m=0.95))
    assert d is not None and d.interior_area_m2 >= 35
    assert fails(d) == set()
