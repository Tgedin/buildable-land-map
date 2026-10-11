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
