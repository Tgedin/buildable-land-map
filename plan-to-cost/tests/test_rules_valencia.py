import pytest
from conftest import make_dwelling, tweak_opening, tweak_space
from shapely.geometry import box

from plan2cost.plan import COMMON, Dwelling, Opening, OpeningKind, Space, Use
from plan2cost.rules import engine
from plan2cost.rules.engine import Status
from plan2cost.rules.valencia_d80 import rules

RULES = rules()


def run(d: Dwelling, rule_id: str):
    rule = next(r for r in RULES if r.id == rule_id)
    return rule.run(d)


def statuses(findings) -> set[Status]:
    return {f.status for f in findings}


# ---------------------------------------------------------------- the rule set itself


def test_every_numeric_parameter_appears_in_its_legal_quote():
    for r in RULES:
        assert engine.params_appear_in_quote(r) == [], f"{r.id}: number not in its quote"


def test_guard_catches_a_number_that_drifted_from_the_law():
    r = next(x for x in RULES if x.id == "VAL-D80-54.1")
    wrong = engine.Rule(r.id, r.title, r.source, {"min_area_m2": 36.0}, r.check)
    assert engine.params_appear_in_quote(wrong) == ["min_area_m2"]


def test_rule_ids_are_unique_and_sourced():
    ids = [r.id for r in RULES]
    assert len(ids) == len(set(ids))
    for r in RULES:
        assert r.source.quote.strip() and r.source.clause and r.source.document
        assert r.source.in_force_from == "2025-02-02"


def test_sample_dwelling_has_no_violation_in_the_checked_rules():
    report = engine.check(make_dwelling(), RULES)
    assert not report.by_status(Status.FAIL), [f.message for f in report.by_status(Status.FAIL)]
    assert not report.by_status(Status.NEEDS_REVIEW)
    assert report.verdict == "no_violation_found_in_checked_rules"


def test_report_never_says_complies():
    s = engine.check(make_dwelling(), RULES).summary()
    assert "complies" not in str(s) and "compliant" not in str(s)
    assert "VAL-D80-54.2" in s["partially_verified_rules"]  # still not fully modelled


# ---------------------------------------------------------------- art. 54: area


def test_min_area_fails_below_35():
    d = make_dwelling()
    small = Dwelling(
        "small",
        [Space("room", box(0, 0, 5, 6), frozenset({Use.ESTAR, Use.DORMITORIO_DOBLE}), 2.6)],
        [],
    )
    assert d.interior_area_m2 > 35
    f = run(small, "VAL-D80-54.1")[0]
    assert f.status is Status.FAIL and f.measured == pytest.approx(30.0) and f.required == 35


def test_exterior_spaces_do_not_count_as_useful_area():
    d = make_dwelling()
    assert d.interior_area_m2 == pytest.approx(8 * 9)  # the 6 m² terrace is excluded


# ---------------------------------------------------------------- art. 55: heights


def test_height_fails_below_minimum_and_review_when_unknown():
    d = tweak_space(make_dwelling(), "bed1", free_height_m=2.40)
    assert any(f.status is Status.FAIL for f in run(d, "VAL-D80-55.1"))
    d = tweak_space(make_dwelling(), "bed1", free_height_m=None)
    f = [x for x in run(d, "VAL-D80-55.1") if x.space_ids == ("bed1",)][0]
    assert f.status is Status.NEEDS_REVIEW  # unknown is never a pass


def test_open_plan_kitchen_takes_the_stricter_general_height():
    d = tweak_space(make_dwelling(), "living", free_height_m=2.40)  # fine for a kitchen alone
    assert any(f.status is Status.FAIL for f in run(d, "VAL-D80-55.1"))
    assert run(d, "VAL-D80-55.2")[0].status is Status.NOT_APPLICABLE  # no kitchen-only space


def test_circulation_and_bath_height_220():
    d = tweak_space(make_dwelling(), "corridor", free_height_m=2.10)
    fails = [f for f in run(d, "VAL-D80-55.3") if f.status is Status.FAIL]
    assert [f.space_ids for f in fails] == [("corridor",)]


# ---------------------------------------------------------------- art. 51: doors, corridors


def test_entrance_door_width():
    d = tweak_opening(make_dwelling(), "entrance", width_m=0.75)
    assert run(d, "VAL-D80-51.1.a")[0].status is Status.FAIL
    d = Dwelling("x", make_dwelling().spaces, [])
    assert run(d, "VAL-D80-51.1.a")[0].status is Status.NEEDS_REVIEW


def test_interior_door_width_and_height():
    d = tweak_opening(make_dwelling(), "d_bath", width_m=0.65)
    assert [f.space_ids for f in run(d, "VAL-D80-51.1.b") if f.status is Status.FAIL] == [
        ("corridor",)
    ]
    d = tweak_opening(make_dwelling(), "d_bed1", height_m=1.95)
    assert any(f.status is Status.FAIL for f in run(d, "VAL-D80-51.1.c"))


def test_large_exterior_opening():
    d = make_dwelling()
    assert run(d, "VAL-D80-51.1.d")[0].status is Status.PASS  # 1.60 x 1.40 living window
    small = Dwelling(
        "x", d.spaces, [Opening("w", OpeningKind.WINDOW, 0.80, 1.00, "living", "exterior")]
    )
    assert run(small, "VAL-D80-51.1.d")[0].status is Status.FAIL


def test_corridor_width():
    d = tweak_space(make_dwelling(), "corridor", polygon=box(0, 4.0, 8, 4.80))  # 0.80 wide
    f = run(d, "VAL-D80-51.2.a")[0]
    assert f.status is Status.FAIL and f.measured == pytest.approx(0.80)


def test_non_rectangular_corridor_goes_to_review():
    from shapely.geometry import Polygon

    l_shape = Polygon([(0, 4), (8, 4), (8, 5), (1, 5), (1, 7), (0, 7)])
    d = tweak_space(make_dwelling(), "corridor", polygon=l_shape)
    assert run(d, "VAL-D80-51.2.a")[0].status is Status.NEEDS_REVIEW


def test_long_corridor_needs_turning_space_review():
    d = tweak_space(make_dwelling(), "corridor", polygon=box(0, 4.0, 11, 4.95))
    f = run(d, "VAL-D80-51.2.b")[0]
    assert f.status is Status.NEEDS_REVIEW
    assert run(make_dwelling(), "VAL-D80-51.2.b")[0].status is Status.NOT_APPLICABLE


# ---------------------------------------------------------------- composition and relations


def test_missing_basic_spaces_are_named():
    d = make_dwelling()
    no_laundry = tweak_space(d, "bath", uses=frozenset({Use.BANO}))
    f = run(no_laundry, "VAL-D80-9.3")[0]
    assert f.status is Status.FAIL and "lavadero" in f.message
    assert run(d, "VAL-D80-9.3")[0].status is Status.PASS


def test_double_bedroom_required():
    d = tweak_space(make_dwelling(), "bed1", uses=frozenset({Use.DORMITORIO_SENCILLO}))
    assert run(d, "VAL-D80-52.3")[0].status is Status.FAIL


def test_three_bedrooms_need_a_second_bathroom():
    d = make_dwelling()
    three = Dwelling(
        "three",
        [*d.spaces, Space("bed3", box(8, 4.95, 10, 9), frozenset({Use.DORMITORIO_SENCILLO}), 2.6)],
        d.openings,
    )
    assert three.n_bedrooms == 3
    assert run(three, "VAL-D80-52.4")[0].status is Status.FAIL
    assert run(d, "VAL-D80-52.4")[0].status is Status.PASS


def test_a_room_reachable_only_through_the_bath_fails():
    d = make_dwelling()
    extra = Space("store", box(5.6, 4.95, 8, 9), frozenset({Use.ALMACENAMIENTO}), 2.6)
    # bed2 -> store only through the bath: remove d_bed2 link, add bath -> bed2
    spaces = [s for s in d.spaces if s.id != "bed2"] + [
        Space("bed2", box(5.6, 4.95, 8, 9), frozenset({Use.DORMITORIO_SENCILLO}), 2.6)
    ]
    openings = [o for o in d.openings if o.id != "d_bed2"] + [
        Opening("d_bath_bed2", OpeningKind.DOOR, 0.80, 2.05, "bath", "bed2")
    ]
    trapped = Dwelling("trapped", spaces, openings)
    f = run(trapped, "VAL-D80-53.1.c")[0]
    assert f.status is Status.FAIL and f.space_ids == ("bed2",)
    assert run(d, "VAL-D80-53.1.c")[0].status is Status.PASS
    del extra


def test_passage_rule_needs_an_entrance():
    d = make_dwelling()
    no_entrance = Dwelling("x", d.spaces, [o for o in d.openings if o.b != COMMON])
    assert run(no_entrance, "VAL-D80-53.1.c")[0].status is Status.NEEDS_REVIEW


def test_living_and_bedrooms_need_a_window_to_the_exterior():
    d = make_dwelling()
    no_window = Dwelling("x", d.spaces, [o for o in d.openings if o.id != "w_bed2"])
    fails = [f for f in run(no_window, "VAL-D80-10.4") if f.status is Status.FAIL]
    assert [f.space_ids for f in fails] == [("bed2",)]


def test_laundry_inside_the_bathroom_is_a_bathroom_for_height():
    d = make_dwelling()  # the bath hosts the laundry and is 2.40 m: fine as a bathroom
    assert not [f for f in run(d, "VAL-D80-55.1") if f.space_ids == ("bath",)]
    assert all(f.status is Status.PASS for f in run(d, "VAL-D80-55.3") if f.space_ids == ("bath",))


def test_a_laundry_room_on_its_own_needs_the_general_height():
    d = make_dwelling()
    laundry = Space("laundry", box(8, 4.95, 9.5, 7), frozenset({Use.LAVADERO}), 2.40)
    d2 = Dwelling("x", [*d.spaces, laundry], d.openings)
    fails = [f for f in run(d2, "VAL-D80-55.1") if f.status is Status.FAIL]
    assert [f.space_ids for f in fails] == [("laundry",)]


# ------------------------------------------------------- table 7 (areas) and table 8 (figures)


def test_table_7_quote_and_data_agree():
    """The table exists twice (quoted rows and data): they must not disagree."""
    import re

    from plan2cost.rules import valencia_d80_tables as T

    labels = {
        "Dormitorio doble principal": "dormitorio_doble_principal",
        "Resto de dormitorios dobles": "dormitorio_doble",
        "Dormitorio sencillo": "dormitorio_sencillo",
        "Cocina-comedor": "cocina_comedor",
        "Cocina": "cocina",
        "Comedor": "comedor",
        "Estar-comedor-cocina": "estar_comedor_cocina",
        "Estar-comedor": "estar_comedor",
        "Estar": "estar",
        "Dormitorio-estar-comedor-cocina": "dormitorio_estar_comedor_cocina",
        "Baño": "bano",
        "Aseo": "aseo",
        "Lavadero": "lavadero",
    }
    seen = set()
    for line in T.TABLE_7_QUOTE.splitlines():
        m = re.match(r"^([^:(]+?)(?: \(\d\))*:\s*(.+)$", line)
        if not m or m.group(1) not in labels:
            continue
        key = labels[m.group(1)]
        cells = [None if c == "–" else float(c) for c in m.group(2).split()]
        if len(cells) == 1:
            cells = cells * 5  # a merged cell spans every occupant column
        assert tuple(cells) == tuple(T.TABLE_7[key]), key
        seen.add(key)
    assert seen == set(T.TABLE_7)


def test_params_must_match_whole_numbers_in_the_quote():
    r = next(x for x in RULES if x.id == "VAL-D80-54.1")
    odd = engine.Rule(
        r.id, r.title, engine.Source("d", "c", "mínima de 36 m².", "", ""), {"x": 6.0}, r.check
    )
    assert engine.params_appear_in_quote(odd) == ["x"]  # 6 is inside 36 but is not 6


def test_occupant_columns():
    from plan2cost.rules.valencia_d80_areas import occupant_column

    assert [occupant_column(n) for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 12)] == [
        0,
        0,
        1,
        1,
        2,
        2,
        3,
        3,
        4,
        4,
    ]


def table7(d):
    return run(d, "VAL-D80-54.2")


def test_sample_meets_table_7():
    # 3 occupants -> column 4: living-dining-kitchen 22 m², main bedroom 10, single 6,
    # bath 4 (+1 m² for the laundry)
    assert all(f.status is Status.PASS for f in table7(make_dwelling()))


def test_main_bedroom_below_10_m2_fails():
    d = tweak_space(make_dwelling(), "bed1", polygon=box(0, 4.95, 2.6, 7.95))  # 7.8 m², < 80% of 10
    fails = [f for f in table7(d) if f.status is Status.FAIL]
    assert [f.space_ids for f in fails] == [("bed1",)] and fails[0].required == 10
    # 9 m² is within the 20% of note 1 and the room opens onto the corridor: a person decides
    d = tweak_space(make_dwelling(), "bed1", polygon=box(0, 4.95, 3.0, 7.95))
    assert [f.status for f in table7(d) if f.space_ids == ("bed1",)] == [Status.NEEDS_REVIEW]


def test_living_dining_kitchen_minimum_grows_with_occupants():
    d = make_dwelling()  # 32 m² living
    extra = [
        Space(
            f"bed{i}", box(8 + 2 * i, 4.95, 10 + 2 * i, 9), frozenset({Use.DORMITORIO_DOBLE}), 2.6
        )
        for i in (3, 4)
    ]
    three_beds = Dwelling("x", [*d.spaces, *extra], d.openings)
    # double (2) + single (1) + two more doubles (4) = 7 occupants -> column 8: 28 m², 32 passes
    assert three_beds.occupants == 7
    living = [f for f in table7(three_beds) if f.space_ids == ("living",)][0]
    assert living.required == 28 and living.status is Status.PASS
    small = tweak_space(three_beds, "living", polygon=box(0, 0, 6.5, 4.0))  # 26 m²
    living = [f for f in table7(small) if f.space_ids == ("living",)][0]
    assert living.status is Status.FAIL


def test_second_bathroom_needs_only_3_m2_and_laundry_adds_1():
    d = make_dwelling()
    two_baths = Dwelling(
        "x",
        [*d.spaces, Space("bath2", box(8, 4.95, 10.0, 6.45), frozenset({Use.BANO}), 2.4)],
        d.openings,
    )
    f = {x.space_ids[0]: x for x in table7(two_baths) if x.space_ids}
    assert f["bath"].required == 4 + 1  # largest bath: 4 m², plus 1 m² for the integrated laundry
    assert f["bath2"].required == 3 and f["bath2"].status is Status.PASS  # 3.0 m²


def test_studio_only_allowed_for_two_occupants():
    studio = Dwelling(
        "studio",
        [
            Space(
                "room",
                box(0, 0, 6, 5),
                frozenset({Use.DORMITORIO_DOBLE, Use.ESTAR, Use.COMEDOR, Use.COCINA}),
                2.6,
            )
        ],
        [],
    )
    assert table7(studio)[0].status is Status.PASS  # 30 m² >= 29, 2 occupants
    small = tweak_space(studio, "room", polygon=box(0, 0, 5, 5))  # 25 m² < 29
    assert table7(small)[0].status is Status.FAIL


def test_bedroom_next_to_circulation_within_20_percent_goes_to_review_not_fail():
    d = tweak_space(
        make_dwelling(), "bed2", polygon=box(5.6, 4.95, 7.6, 7.4)
    )  # 4.9 m², single needs 6
    f = [x for x in table7(d) if x.space_ids == ("bed2",)][0]
    assert f.status is Status.NEEDS_REVIEW and "note 1" in f.message  # 4.9 >= 4.8 (80% of 6)
    d = tweak_space(make_dwelling(), "bed2", polygon=box(5.6, 4.95, 7.6, 7.0))  # 4.1 m² < 80% of 6
    assert [x for x in table7(d) if x.space_ids == ("bed2",)][0].status is Status.FAIL


def test_no_bedroom_means_occupants_unknown_so_review():
    d = make_dwelling()
    none = Dwelling(
        "x",
        [s for s in d.spaces if not s.uses & {Use.DORMITORIO_DOBLE, Use.DORMITORIO_SENCILLO}],
        [],
    )
    assert table7(none)[0].status is Status.NEEDS_REVIEW


def fig(d):
    return run(d, "VAL-D80-56")


def test_sample_meets_table_8_figures():
    assert all(f.status is Status.PASS for f in fig(make_dwelling())), [
        f.message for f in fig(make_dwelling()) if f.status is not Status.PASS
    ]


def test_free_circle_fails_in_a_too_narrow_bathroom():
    d = tweak_space(make_dwelling(), "bath", polygon=box(3.6, 4.95, 4.6, 9))  # 1.0 m wide
    assert any(f.status is Status.FAIL and "bath" in f.message for f in fig(d))


def test_main_bedroom_needs_a_2_60_square():
    d = tweak_space(make_dwelling(), "bed1", polygon=box(0, 4.95, 2.4, 9))  # 2.4 m wide
    assert any(f.status is Status.FAIL and "main bedroom" in f.message for f in fig(d))


def test_dining_rectangle_alternative_only_in_a_combined_space_with_2_50_short_side():
    d = make_dwelling()  # combined 8 x 4 living: a circle of 2.5 fits easily
    assert any("dining circle" in f.message and f.status is Status.PASS for f in fig(d))
    narrow = tweak_space(
        d, "living", polygon=box(0, 0, 8, 2.4)
    )  # 2.4 m: no circle, short side < 2.50
    assert any(f.status is Status.FAIL for f in fig(narrow))


def test_non_rectangular_bedroom_figure_needs_review():
    from shapely.geometry import Polygon

    l_shape = Polygon([(0, 4.95), (3.6, 4.95), (3.6, 9), (1.5, 9), (1.5, 7), (0, 7)])
    d = tweak_space(make_dwelling(), "bed1", polygon=l_shape)
    assert any(f.status is Status.NEEDS_REVIEW and "main bedroom" in f.message for f in fig(d))
