import json
import math
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from blm import planning
from blm.config import AreaConfig, PlanningConfig

FIXTURE = Path(__file__).parent / "fixtures" / "pgou_alignments_sample.geojson"


@pytest.mark.parametrize(
    ("altura", "protec", "kind", "floors"),
    [
        ("6", " ", "floors", 6),
        ("B+5", None, "floors", 5),
        ("<=6", "", "floors", 6),
        ("0", "", "open", math.nan),
        ("PROTEGIDO", "AMB", "protected", math.nan),
        ("PROTEGIDO?", "", "protected", math.nan),
        ("7", "PAR", "protected", math.nan),  # protection code wins over a number
        ("-+-", "", "unknown", math.nan),
        ("6(B+1)", "", "unknown", math.nan),  # ambiguous text is never guessed
        (None, None, "unknown", math.nan),
        (math.nan, math.nan, "unknown", math.nan),  # null cells arrive as NaN floats
    ],
)
def test_parse_altura(altura, protec, kind, floors):
    a = planning.parse_altura(altura, protec)
    assert a.kind == kind
    assert (math.isnan(a.floors) and math.isnan(floors)) or a.floors == floors


def _alignments(rows):
    gdf = gpd.GeoDataFrame(
        [{"altura": a, "protec": p, "geometry": g} for a, p, g in rows],
        geometry="geometry",
        crs="EPSG:25830",
    )
    return planning.classify_alignments(gdf)


def _parcels(boxes):
    gdf = gpd.GeoDataFrame(
        [{"refcat": f"R{i}", "geometry": b} for i, b in enumerate(boxes)],
        geometry="geometry",
        crs="EPSG:25830",
    )
    gdf["footprint_m2"] = gdf.geometry.area
    return gdf


def test_match_parcels_statuses_and_allowed_floors():
    parcels = _parcels(
        [box(0, 0, 10, 10), box(20, 0, 30, 10), box(40, 0, 50, 10), box(60, 0, 70, 10)]
    )
    al = _alignments(
        [
            ("5", " ", box(-1, -1, 11, 11)),  # R0 fully under a 5-floor polygon
            ("PROTEGIDO", "AMB", box(19, -1, 31, 11)),  # R1 protected
            ("0", " ", box(39, -1, 51, 11)),  # R2 open space
            # R3: no polygon at all
        ]
    )
    out = planning.match_parcels(parcels, al, PlanningConfig(ground_floor_offset=1)).set_index(
        "refcat"
    )
    assert out.loc["R0", "plan_status"] == "floors"
    assert out.loc["R0", "plan_floors"] == 5
    assert out.loc["R0", "plan_allowed_floors"] == 6
    assert out.loc["R1", "plan_status"] == "protected"
    assert math.isnan(out.loc["R1", "plan_allowed_floors"])
    assert out.loc["R2", "plan_status"] == "open"
    assert out.loc["R3", "plan_status"] == "unknown"  # missing is unknown, not 0 floors
    assert math.isnan(out.loc["R3", "plan_floors"])


def test_match_parcels_uses_dominant_height_by_area():
    parcels = _parcels([box(0, 0, 10, 10)])
    al = _alignments([("4", " ", box(0, 0, 7, 10)), ("8", " ", box(7, 0, 10, 10))])
    out = planning.match_parcels(parcels, al, PlanningConfig())
    assert out.iloc[0]["plan_floors"] == 4  # 70% of the parcel, not the tallest


def test_ground_floor_offset_is_configurable():
    parcels = _parcels([box(0, 0, 10, 10)])
    al = _alignments([("5", " ", box(0, 0, 10, 10))])
    out = planning.match_parcels(parcels, al, PlanningConfig(ground_floor_offset=0))
    assert out.iloc[0]["plan_allowed_floors"] == 5


def test_classify_real_fixture():
    raw = gpd.read_file(FIXTURE)
    out = planning.classify_alignments(raw)
    assert set(out["kind"]) == {"floors", "protected"}
    assert out.loc[out["kind"] == "floors", "plan_floors"].notna().all()


def test_fetch_alignments_pages_and_classifies(monkeypatch):
    body = json.loads(FIXTURE.read_text())
    calls = []

    class Resp:
        def __init__(self, payload):
            self._p = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._p

    def fake_get(url, params, timeout):
        calls.append(params["resultOffset"])
        if params["resultOffset"] == 0:
            first = {
                **body,
                "features": body["features"][:5],
                "properties": {"exceededTransferLimit": True},
            }
            return Resp(first)
        if params["resultOffset"] == 5:
            return Resp({**body, "features": body["features"][5:]})
        return Resp({**body, "features": []})  # past the end: an empty page ends the paging

    monkeypatch.setattr(planning.requests, "get", fake_get)
    cfg = AreaConfig(
        name="t",
        label="t",
        epsg=25830,
        bbox=(0, 0, 1, 1),
        planning=PlanningConfig(alignments_url="https://example.test/MapServer/1"),
    )
    out = planning.fetch_alignments(cfg)
    assert calls[:2] == [0, 5] and calls[-1] == len(body["features"])  # then one empty page
    assert len(out) == len(body["features"])
    assert "kind" in out.columns


def test_fetch_requires_url():
    cfg = AreaConfig(name="t", label="t", epsg=25830, bbox=(0, 0, 1, 1))
    with pytest.raises(ValueError, match="alignments_url"):
        planning.fetch_alignments(cfg)


def _parcels_for_zone():
    gdf = gpd.GeoDataFrame(
        {
            "refcat": ["IN", "SPLIT", "OUT"],
            "footprint_m2": [100.0, 100.0, 100.0],
            "geometry": [box(0, 0, 10, 10), box(20, 0, 30, 10), box(100, 0, 110, 10)],
        },
        geometry="geometry",
        crs="EPSG:25830",
    )
    return gdf


def test_match_zone_takes_the_zone_covering_most_of_the_parcel():
    zoning = gpd.GeoDataFrame(
        {"califi": ["ENS", "RV", "ENS"]},
        geometry=[box(-5, -5, 15, 15), box(18, -5, 26, 15), box(26, -5, 40, 15)],
        crs="EPSG:25830",
    )
    out = planning.match_zone(_parcels_for_zone(), zoning).set_index("refcat")
    assert out.loc["IN", "zone"] == "ENS"
    # SPLIT: 6 m of RV (60%) against 4 m of ENS (40%)
    assert out.loc["SPLIT", "zone"] == "RV"


def test_match_zone_is_none_when_no_zone_covers_half_or_any():
    zoning = gpd.GeoDataFrame(
        {"califi": ["ENS", "RV"]},
        geometry=[box(20, -5, 25, 15), box(25, -5, 30, 15)],  # 50% / 50% of SPLIT
        crs="EPSG:25830",
    )
    out = planning.match_zone(_parcels_for_zone(), zoning, min_share=0.6).set_index("refcat")
    assert out.loc["SPLIT", "zone"] is None  # neither zone reaches 60%: never guessed
    assert out.loc["OUT", "zone"] is None  # outside every polygon
    assert out.loc["IN", "zone"] is None


def test_paging_continues_until_an_empty_page(monkeypatch):
    """The server's page size is 2,000: a layer with 5 polygons and page size 2 needs 3 requests."""
    feats = [
        {
            "type": "Feature",
            "properties": {"califi": f"Z{i}"},
            "geometry": {"type": "Point", "coordinates": [i, i]},
        }
        for i in range(5)
    ]
    calls = []

    class R:
        def __init__(self, page):
            self.page = page

        def raise_for_status(self):
            pass

        def json(self):
            return {"features": self.page}  # no "more pages" flag at all

    def fake_get(url, params=None, timeout=None):
        calls.append(params["resultOffset"])
        return R(feats[params["resultOffset"] : params["resultOffset"] + 2])

    monkeypatch.setattr(planning.requests, "get", fake_get)
    cfg = AreaConfig(name="t", label="t", epsg=25830, bbox=(0, 0, 10, 10))
    out = planning._fetch_layer("http://x", "califi", cfg)
    assert len(out) == 5 and calls == [0, 2, 4, 5]
