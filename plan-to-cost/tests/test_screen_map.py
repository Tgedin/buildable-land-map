import geopandas as gpd
import pytest
from shapely.geometry import box

from plan2cost import screen_map


def _parcels() -> gpd.GeoDataFrame:
    """Three lots in a row between party walls (10 x 20 m) and one detached lot."""
    rows = []
    for i in range(3):
        rows.append(
            {
                "refcat": f"ROW{i}",
                "geometry": box(i * 10, 0, (i + 1) * 10, 20),
                "main_footprint_m2": 200.0,
                "plan_gap_floors": 2.0,
                "gap_class": "plan_gap" if i == 1 else "at_limit",
            }
        )
    rows.append(
        {
            "refcat": "FAR",
            "geometry": box(100, 0, 112, 25),
            "main_footprint_m2": 300.0,
            "plan_gap_floors": 1.0,
            "gap_class": "plan_gap",
        }
    )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:25830")


def test_only_parcels_with_room_under_the_plan_are_screened():
    out = screen_map.run(_parcels())
    assert set(out) == {"ROW1", "FAR"}  # ROW0 and ROW2 are at the plan limit


def test_party_walls_between_neighbours_limit_the_facade():
    out = screen_map.run(_parcels())
    middle, detached = out["ROW1"], out["FAR"]
    assert middle["free_facade_m"] == pytest.approx(20.0, abs=1.5)  # only the two short ends
    assert detached["free_facade_m"] > middle["free_facade_m"]  # all four sides


def test_result_carries_the_unit_and_the_limit():
    row = screen_map.run(_parcels())["ROW1"]
    assert row["added_floors"] == 2 and row["plate_m2"] == 200.0
    assert row["homes_2bed"] == 2 * (
        row["homes_2bed"] // 2
    )  # a whole number per floor, times 2 floors
    assert row["limit_2bed"] in {"area", "facade", "both"}
    assert row["unit_2bed"]["useful_m2"] > 35


def test_summary_adds_up():
    out = screen_map.run(_parcels())
    s = screen_map.summarize(out)
    assert s["parcels_screened"] == 2
    assert s["total_homes_2bed"] == sum(v["homes_2bed"] for v in out.values())
    assert (
        s["parcels_with_homes_1bed"] >= s["parcels_with_homes_2bed"]
    )  # a 1-bed fits wherever a 2-bed does


def test_each_screened_parcel_gets_a_residual_that_names_what_it_leaves_out():
    row = screen_map.run(_parcels())["FAR"]
    r = row["residual_2bed"]
    assert r["eur"] is not None and set(r["eur"]) == {"pessimistic", "base", "optimistic"}
    assert r["excluded"] == ["structural reinforcement"]  # unknown cost is named, not priced at 0


def _ensanche_parcels() -> gpd.GeoDataFrame:
    """A detached 20 x 30 m block at its plan limit (5 floors) and one over the limit."""
    rows = [
        {
            "refcat": "LIMIT",
            "geometry": box(0, 0, 20, 30),
            "main_footprint_m2": 600.0,
            "plan_gap_floors": 0.0,
            "gap_class": "at_limit",
            "zone": "ENS",
            "plan_floors": 5.0,
            "floors": 5.0,
        },
        {
            "refcat": "OVER",
            "geometry": box(100, 0, 120, 30),
            "main_footprint_m2": 600.0,
            "plan_gap_floors": 0.0,
            "gap_class": "at_limit",
            "zone": "ENS",
            "plan_floors": 5.0,
            "floors": 7.0,
        },
    ]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:25830")


def test_a_building_at_its_plan_limit_is_screened_for_an_attic_only():
    out = screen_map.run(_ensanche_parcels())
    assert set(out) == {"LIMIT"}  # OVER is above the plan: no attic assumed, no floors gap
    row = out["LIMIT"]
    assert row["added_floors"] == 0 and row["homes_2bed"] == 0  # no floors route
    attic = row["attic"]
    assert 0 < attic["plate_m2"] < row["plate_m2"]  # the setback takes area away
    assert attic["homes_2bed"] >= 1
    assert attic["residual_2bed"]["excluded"] == ["structural reinforcement"]


def test_parcels_without_a_zone_column_get_no_attic_and_say_why():
    out = screen_map.run(_parcels())
    assert out["ROW1"]["attic"] == {"eligible": False, "reason": "zone_unknown"}


def test_summary_counts_the_two_routes_separately():
    summary = screen_map.summarize(screen_map.run(_ensanche_parcels()))
    assert summary["parcels_screened"] == 0  # nothing in the floors route
    assert summary["attic_parcels"] == 1
    assert summary["attic_total_homes_2bed"] >= 1


def test_main_part_is_the_union_of_the_tallest_parts():
    parts = gpd.GeoDataFrame(
        {
            "refcat": ["A", "A", "A", "B"],
            "floors_above": [5, 5, 2, 3],
            "geometry": [
                box(0, 0, 10, 10),
                box(10, 0, 20, 10),
                box(20, 0, 30, 10),
                box(50, 0, 60, 10),
            ],
        },
        geometry="geometry",
        crs="EPSG:25830",
    )
    main = screen_map.main_part_geometries(parts)
    assert main["A"].area == pytest.approx(200.0)  # the two 5-floor parts, not the 2-floor one
    assert main["B"].area == pytest.approx(100.0)


def test_facade_is_measured_on_the_building_not_on_a_big_parcel_outline():
    # a 100 x 100 m parcel with a 10 x 20 m tall building in the middle
    parcels = gpd.GeoDataFrame(
        [
            {
                "refcat": "BIG",
                "geometry": box(0, 0, 100, 100),
                "main_footprint_m2": 200.0,
                "plan_gap_floors": 1.0,
                "gap_class": "plan_gap",
            }
        ],
        geometry="geometry",
        crs="EPSG:25830",
    )
    on_outline = screen_map.run(parcels)["BIG"]
    on_building = screen_map.run(parcels, main_parts={"BIG": box(45, 40, 55, 60)})["BIG"]
    assert on_outline["measured_on"] == "parcel_outline"
    assert on_building["measured_on"] == "main_part"
    assert on_outline["free_facade_m"] == pytest.approx(400.0)
    assert on_building["free_facade_m"] == pytest.approx(60.0)  # 10 + 20 + 10 + 20


def test_adding_more_floors_than_a_structure_can_carry_is_labelled_redevelopment():
    out = screen_map.run(_parcels())  # ROW1 may add 2 floors, FAR 1
    assert out["ROW1"]["kind"] == "rooftop" and out["FAR"]["kind"] == "rooftop"
    tall = _parcels()
    tall.loc[tall["refcat"] == "FAR", "plan_gap_floors"] = 5.0
    out = screen_map.run(tall)
    assert out["FAR"]["kind"] == "redevelopment"
    assert screen_map.summarize(out)["parcels_redevelopment"] == 1


def test_the_street_edge_is_local_so_distant_parcels_change_nothing():
    """A candidate's result must not depend on parcels far away (it is what lets a city scale)."""
    base = _ensanche_parcels()
    far = [
        {
            "refcat": f"FAR{i}",
            "geometry": box(5000 + i * 40, 0, 5030 + i * 40, 30),
            "main_footprint_m2": 800.0,
            "plan_gap_floors": 0.0,
            "gap_class": "protected",
            "zone": "ENS",
            "plan_floors": 5.0,
            "floors": 5.0,
        }
        for i in range(30)
    ]
    crowded = gpd.GeoDataFrame([*base.to_dict("records"), *far], geometry="geometry", crs=base.crs)
    alone = screen_map.run(base)["LIMIT"]["attic"]
    among = screen_map.run(crowded)["LIMIT"]["attic"]
    assert among == alone


def test_a_candidate_in_a_block_sees_its_own_street_front():
    # a 20 x 30 m detached block: all four sides are street, so the whole free facade is street
    block = _ensanche_parcels()
    attic = screen_map.run(block)["LIMIT"]["attic"]
    assert attic["street_facade_m"] == pytest.approx(attic["free_facade_m"], abs=2.0)


def test_with_homes_keeps_only_parcels_where_a_route_fits_a_home():
    results = {
        "FLOORS": {"homes_1bed": 0, "homes_2bed": 2, "attic": {"eligible": False, "reason": "x"}},
        "ATTIC": {"homes_1bed": 0, "homes_2bed": 0, "attic": {"homes_1bed": 1, "homes_2bed": 0}},
        "NOTHING": {"homes_1bed": 0, "homes_2bed": 0, "attic": {"homes_1bed": 0, "homes_2bed": 0}},
        "NOATTIC": {"homes_1bed": 0, "homes_2bed": 0, "attic": {"eligible": False, "reason": "x"}},
    }
    assert set(screen_map.with_homes(results)) == {"FLOORS", "ATTIC"}


def test_the_catastro_use_travels_with_the_result_and_unknown_stays_none():
    parcels = _parcels()
    parcels["current_use"] = ["1_residential", "3_industrial", None, "1_residential"]
    out = screen_map.run(parcels)
    assert out["ROW1"]["use"] == "3_industrial"
    assert out["FAR"]["use"] == "1_residential"
    parcels.loc[parcels["refcat"] == "FAR", "current_use"] = None
    assert screen_map.run(parcels)["FAR"]["use"] is None  # unknown is not residential
