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
