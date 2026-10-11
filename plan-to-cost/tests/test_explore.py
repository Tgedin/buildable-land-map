import pytest

from plan2cost.generate.dwelling import DwellingParams, generate
from plan2cost.generate.explore import explore, frange, ranked
from plan2cost.quantify import measure, partition_length_m
from plan2cost.rules.engine import Status


def test_frange_is_inclusive_and_free_of_float_noise():
    assert frange(4.0, 5.0, 0.25) == [4.0, 4.25, 4.5, 4.75, 5.0]


def test_explore_keeps_only_plans_without_a_violation():
    cands, tried = explore(2, frange(7.0, 9.0, 1.0), frange(8.0, 10.0, 1.0))
    assert tried >= len(cands) > 0
    for c in cands:
        assert not c.report.by_status(Status.FAIL)
        assert c.area >= 35.0


def test_candidates_are_never_called_compliant_and_list_partial_rules():
    cands, _ = explore(
        2, [8.0], [9.0], corridor_widths=(1.0,), day_depths=(4.0,), closed_kitchen=(False,)
    )
    summary = cands[0].report.summary()
    assert "compliant" not in str(summary) and "complies" not in str(summary)
    assert summary["verdict"] == "no_violation_found_in_checked_rules"
    assert summary["partially_verified_rules"]  # what the code does not check is always listed


def test_ranking_puts_the_smallest_area_first():
    cands, _ = explore(2, frange(7.0, 10.0, 0.5), frange(8.0, 10.0, 0.5))
    areas = [c.area for c in ranked(cands)]
    assert areas == sorted(areas)


def test_explore_finds_nothing_when_the_space_is_too_small():
    cands, tried = explore(3, [6.0], [6.0])
    assert cands == [] and tried == 0


def test_measures_of_the_default_flat():
    m = measure(generate(DwellingParams(8.0, 9.0)))
    assert m.interior_area_m2 == pytest.approx(72.0)
    assert m.circulation_area_m2 == pytest.approx(8.0 * 1.0)
    assert m.circulation_share == pytest.approx(8 / 72)
    assert m.n_doors == 6 and m.n_windows == 3  # entrance + living + 2 beds + bath + terrace door
    assert m.partition_area_m2 is not None and m.partition_area_m2 > 0


def test_partition_length_counts_each_shared_wall_once():
    d = generate(DwellingParams(8.0, 9.0))
    # corridor|living 8.0, corridor|night band 8.0 (3.3 + 2.7 + 2.0), bed1|bed2 4.0, bed2|bath 4.0
    assert partition_length_m(d) == pytest.approx(24.0)


def test_unknown_height_makes_the_partition_area_unknown_not_zero():
    from dataclasses import replace

    d = generate(DwellingParams(8.0, 9.0))
    d = replace(
        d, spaces=[replace(s, free_height_m=None) if s.id == "bed1" else s for s in d.spaces]
    )
    assert measure(d).partition_area_m2 is None


def test_clean_only_drops_candidates_that_depend_on_a_review():
    cands, _ = explore(2, frange(7.5, 9.0, 0.25), frange(6.0, 9.0, 0.25))
    assert any(not c.clean for c in cands) and any(c.clean for c in cands)
    clean = ranked(cands, clean_only=True)
    assert clean and all(c.review_items == 0 for c in clean)
    assert ranked(cands)[0].area <= clean[0].area  # the loose minimum is never larger
