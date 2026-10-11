import geopandas as gpd
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
