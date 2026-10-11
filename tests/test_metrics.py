import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from blm import lidar, metrics, synthetic
from blm.config import LidarConfig, MetricsConfig


def _row_of_parcels(floors: list[int]) -> gpd.GeoDataFrame:
    recs = [
        {
            "part_id": f"P{i:013d}_part1",
            "refcat": f"P{i:013d}",
            "floors_above": f,
            "geometry": box(i * 10, 0, i * 10 + 9.5, 10),
        }
        for i, f in enumerate(floors)
    ]
    gdf = gpd.GeoDataFrame(recs, geometry="geometry", crs="EPSG:25830")
    gdf["footprint_m2"] = gdf.geometry.area
    return gdf


def test_low_building_in_tall_street_has_gap():
    parts = _row_of_parcels([6, 6, 6, 1, 6, 6, 6])
    parcels = metrics.buildable_gap(metrics.aggregate_parcels(parts), MetricsConfig())
    low = parcels[parcels["refcat"] == "P0000000000003"].iloc[0]
    assert low["dominant_floors"] == 6
    assert low["gap_floors"] == 5
    assert low["gap_m2"] == pytest.approx(95 * 5, rel=0.01)


def test_building_at_street_height_has_no_gap():
    parts = _row_of_parcels([5, 5, 5, 5, 5])
    parcels = metrics.buildable_gap(metrics.aggregate_parcels(parts), MetricsConfig())
    assert (parcels["gap_m2"] == 0).all()


def test_isolated_parcel_gets_no_gap():
    parts = _row_of_parcels([1])
    parcels = metrics.buildable_gap(metrics.aggregate_parcels(parts), MetricsConfig())
    assert parcels["dominant_floors"].isna().all()
    assert parcels["gap_m2"].isna().all() or (parcels["gap_m2"].fillna(0) == 0).all()


def test_multi_part_parcel_sums_existing_area():
    parts = _row_of_parcels([4, 2])
    parts["refcat"] = "SAME0000000000"
    parcels = metrics.aggregate_parcels(parts)
    assert len(parcels) == 1
    assert parcels.iloc[0]["floors"] == 4
    assert parcels.iloc[0]["existing_m2"] == pytest.approx(95 * 4 + 95 * 2, rel=0.01)


def test_lidar_validation_on_synthetic_truth():
    parts = synthetic.make_parts(blocks=(2, 2))
    parts = lidar.building_heights(parts, synthetic.make_point_cloud(parts), LidarConfig())
    v = metrics.validate_lidar(parts, MetricsConfig(floor_height_m=3.0))
    assert v["n"] == len(parts)
    assert v["share_within_1"] == 1.0


def test_low_annex_in_courtyard_is_not_a_gap():
    """A 6-floor body with a 1-floor rear annex is at street height: no gap."""
    body = {"part_id": "A_part1", "refcat": "A", "floors_above": 6, "geometry": box(0, 0, 9.5, 10)}
    annex = {
        "part_id": "A_part2",
        "refcat": "A",
        "floors_above": 1,
        "geometry": box(0, 10, 9.5, 20),
    }
    others = _row_of_parcels([6, 6, 6, 6])
    others["geometry"] = others.geometry.translate(yoff=-30)
    parts = gpd.GeoDataFrame([body, annex], geometry="geometry", crs="EPSG:25830")
    parts["footprint_m2"] = parts.geometry.area
    parts = gpd.GeoDataFrame(
        pd.concat([parts, others], ignore_index=True), geometry="geometry", crs="EPSG:25830"
    )
    parcels = metrics.buildable_gap(metrics.aggregate_parcels(parts), MetricsConfig())
    row = parcels[parcels["refcat"] == "A"].iloc[0]
    assert row["main_footprint_m2"] == pytest.approx(95)
    assert row["gap_m2"] == 0


def test_gap_uses_main_body_footprint_only():
    """5-floor body + 1-floor annex on a 7-floor street: 2 extra floors over the body."""
    body = {"part_id": "A_part1", "refcat": "A", "floors_above": 5, "geometry": box(0, 0, 9.5, 10)}
    annex = {
        "part_id": "A_part2",
        "refcat": "A",
        "floors_above": 1,
        "geometry": box(0, 10, 9.5, 20),
    }
    others = _row_of_parcels([7, 7, 7, 7])
    others["geometry"] = others.geometry.translate(yoff=-30)
    parts = gpd.GeoDataFrame([body, annex], geometry="geometry", crs="EPSG:25830")
    parts["footprint_m2"] = parts.geometry.area
    parts = gpd.GeoDataFrame(
        pd.concat([parts, others], ignore_index=True), geometry="geometry", crs="EPSG:25830"
    )
    parcels = metrics.buildable_gap(metrics.aggregate_parcels(parts), MetricsConfig())
    row = parcels[parcels["refcat"] == "A"].iloc[0]
    assert row["gap_floors"] == 2
    assert row["gap_m2"] == pytest.approx(95 * 2)


def _planned(rows):
    """rows: (status, allowed_floors, floors, use) -> parcels as match_parcels would return."""
    recs = [
        {
            "refcat": f"P{i}",
            "plan_status": st,
            "plan_allowed_floors": al,
            "floors": fl,
            "main_footprint_m2": 100.0,
            "current_use": use,
            "geometry": box(i * 10, 0, i * 10 + 9, 10),
        }
        for i, (st, al, fl, use) in enumerate(rows)
    ]
    return gpd.GeoDataFrame(recs, geometry="geometry", crs="EPSG:25830")


def test_plan_gap_classes_and_area():
    nan = float("nan")
    out = metrics.plan_gap(
        _planned(
            [
                ("floors", 6.0, 4, "1_residential"),  # 2 floors below the plan
                ("floors", 6.0, 7, "1_residential"),  # above the plan: at the limit
                ("protected", nan, 3, "1_residential"),
                ("open", nan, 1, "1_residential"),
                ("unknown", nan, 2, "1_residential"),
                ("floors", 8.0, 1, "4_3_publicServices"),  # a school under a tall plan
            ]
        )
    ).set_index("refcat")
    assert out["gap_class"].to_dict() == {
        "P0": "plan_gap",
        "P1": "at_limit",
        "P2": "protected",
        "P3": "open",
        "P4": "no_plan",
        "P5": "public_use",
    }
    assert out.loc["P0", "plan_gap_floors"] == 2
    assert out.loc["P0", "plan_gap_m2"] == 200
    assert out.loc["P1", "plan_gap_floors"] == 0  # computed, and zero
    # Not computed is NaN, never 0.
    assert out[["plan_gap_floors", "plan_gap_m2"]].loc[["P2", "P3", "P4", "P5"]].isna().all().all()


def test_plan_gap_unknown_use_is_not_excluded():
    out = metrics.plan_gap(_planned([("floors", 6.0, 3, None)]))
    assert out.iloc[0]["gap_class"] == "plan_gap"  # missing use must not hide a parcel


def test_summarize_reports_plan_classes():
    parcels = metrics.plan_gap(
        _planned([("floors", 6.0, 4, "1_residential"), ("open", None, 1, None)])
    )
    parcels["gap_m2"] = 0.0
    parcels["existing_m2"] = 0.0
    s = metrics.summarize(parcels, {"n": 0})
    assert s["plan_by_class"] == {"plan_gap": 1, "open": 1}
    assert s["total_plan_gap_m2"] == 200
    assert s["n_parcels_with_plan_gap"] == 1


def test_aggregate_keeps_current_use():
    parts = _row_of_parcels([4])
    parts["current_use"] = "1_residential"
    assert metrics.aggregate_parcels(parts).iloc[0]["current_use"] == "1_residential"
