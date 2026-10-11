import geopandas as gpd
import pytest
from shapely.geometry import box

from blm import lidar_sheets
from blm.config import AreaConfig, LidarConfig


def _index() -> gpd.GeoDataFrame:
    rows = [
        {"nom_laz": "a.laz", "link_laz": "https://x.test/a.laz", "geometry": box(0, 0, 2000, 2000)},
        {
            "nom_laz": "b.laz",
            "link_laz": "https://x.test/b.laz",
            "geometry": box(2000, 0, 4000, 2000),
        },
        {
            "nom_laz": "far.laz",
            "link_laz": "https://x.test/far.laz",
            "geometry": box(9000, 0, 11000, 2000),
        },
    ]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:25830")


def test_sheets_for_bbox_picks_only_touching_sheets():
    hit = lidar_sheets.sheets_for_bbox(_index(), (1500, 100, 2500, 900))  # crosses a | b
    assert [n for n, _ in hit] == ["a.laz", "b.laz"]


def test_sheets_for_bbox_none():
    assert lidar_sheets.sheets_for_bbox(_index(), (5000, 0, 6000, 100)) == []


class _Resp:
    def __init__(self, body: bytes = b"", payload=None):
        self._body, self._payload = body, payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload

    def iter_content(self, chunk_size):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _cfg(url="https://index.test/wfs"):
    return AreaConfig(
        name="t",
        label="t",
        epsg=25830,
        bbox=(1500, 100, 2500, 900),
        lidar=LidarConfig(sheet_index_url=url),
    )


def test_download_sheets_fetches_missing_and_keeps_existing(tmp_path, monkeypatch):
    feats = _index().__geo_interface__["features"]
    (tmp_path / "a.laz").write_bytes(b"already here")
    got = []

    def fake_get(url, **kw):
        if url == "https://index.test/wfs":
            return _Resp(payload={"features": feats})
        got.append(url)
        return _Resp(body=b"LAZDATA")

    monkeypatch.setattr(lidar_sheets.requests, "get", fake_get)
    paths = lidar_sheets.download_sheets(_cfg(), tmp_path)
    assert [p.name for p in paths] == ["a.laz", "b.laz"]
    assert got == ["https://x.test/b.laz"]  # a.laz was already there
    assert (tmp_path / "a.laz").read_bytes() == b"already here"
    assert (tmp_path / "b.laz").read_bytes() == b"LAZDATA"
    assert not list(tmp_path.glob("*.part"))


def test_download_requires_index_url(tmp_path):
    with pytest.raises(ValueError, match="sheet_index_url"):
        lidar_sheets.download_sheets(_cfg(url=None), tmp_path)
