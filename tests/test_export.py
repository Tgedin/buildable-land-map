import json

from blm import export, metrics, synthetic
from blm.config import MetricsConfig


def test_export_writes_valid_wgs84_geojson(tmp_path):
    parts = synthetic.make_parts(blocks=(1, 1))
    parcels = metrics.buildable_gap(metrics.aggregate_parcels(parts), MetricsConfig())
    summary = metrics.summarize(parcels, {"n": 0})

    gj_path, sum_path = export.export_web(parcels, summary, tmp_path, "Test", synthetic=True)
    gj = json.loads(gj_path.read_text())
    s = json.loads(sum_path.read_text())

    assert gj["type"] == "FeatureCollection"
    assert len(gj["features"]) == len(parcels)
    lon, lat = gj["features"][0]["geometry"]["coordinates"][0][0]
    assert -10 < lon < 5 and 35 < lat < 44  # inside Spain, so CRS was converted
    assert "NaN" not in gj_path.read_text()  # NaN is invalid JSON
    assert s["synthetic"] is True and s["n_parcels"] == len(parcels)


def test_export_candidates_keeps_only_the_listed_parcels(tmp_path):
    parts = synthetic.make_parts(blocks=(2, 2))
    parcels = metrics.buildable_gap(metrics.aggregate_parcels(parts), MetricsConfig())
    summary = metrics.summarize(parcels, {"n": 0})
    keep = set(parcels["refcat"].iloc[:2])

    gj_path, sum_path = export.export_candidates(parcels, keep, summary, tmp_path, "Test")
    gj = json.loads(gj_path.read_text())

    assert {f["properties"]["refcat"] for f in gj["features"]} == keep
    # the summary still describes every parcel, not only the exported ones
    assert json.loads(sum_path.read_text())["n_parcels"] == len(parcels) > len(keep)


def test_export_parts_keeps_each_parts_own_floors_and_marks_the_tallest():
    import geopandas as gpd
    from shapely.geometry import box

    parts = gpd.GeoDataFrame(
        {
            "refcat": ["A", "A", "A", "B"],
            "floors_above": [6, 6, 2, 3],
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
    import json
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        path = export.export_parts(parts, Path(d))
        feats = json.loads(path.read_text())["features"]
        assert "NaN" not in path.read_text()
        by = [
            (f["properties"]["refcat"], f["properties"]["floors_part"], f["properties"]["main"])
            for f in feats
        ]
        assert by == [("A", 6, True), ("A", 6, True), ("A", 2, False), ("B", 3, True)]

        only_b = json.loads(export.export_parts(parts, Path(d), refcats={"B"}).read_text())[
            "features"
        ]
        assert [f["properties"]["refcat"] for f in only_b] == ["B"]
