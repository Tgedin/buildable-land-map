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
