from pathlib import Path

import pytest

from blm import catastro

FIXTURE = Path(__file__).parent / "fixtures" / "buildingparts_sample.gml"


def test_tiles_cover_bbox_without_exceeding_size():
    bbox = (0, 0, 1250, 600)
    tiles = catastro.tile_bbox(bbox, 500)
    assert len(tiles) == 3 * 2
    assert all((t[2] - t[0]) <= 500 and (t[3] - t[1]) <= 500 for t in tiles)
    area = sum((t[2] - t[0]) * (t[3] - t[1]) for t in tiles)
    assert area == pytest.approx(1250 * 600)


def test_tiles_respect_service_area_limit():
    tiles = catastro.tile_bbox((0, 0, 5000, 5000), 500)
    assert max((t[2] - t[0]) * (t[3] - t[1]) for t in tiles) <= 4_000_000  # 4 km²


def test_parse_building_parts():
    parsed = catastro.parse_building_parts(FIXTURE.read_bytes())
    assert parsed.n_features == 2
    p1, p2 = parsed.records
    assert p1["refcat"] == "1234501VK4713S"
    assert p1["floors_above"] == 6
    assert p1["floors_below"] == 1
    assert len(p1["geometry"].interiors) == 1  # courtyard kept as a hole
    assert p1["geometry"].area == pytest.approx(14 * 16 - 4 * 4)
    assert p2["floors_below"] is None  # xsi:nil handled


def test_exception_report_raises():
    xml = b"""<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1">
      <ows:Exception><ows:ExceptionText>Bbox too large</ows:ExceptionText></ows:Exception>
    </ows:ExceptionReport>"""
    with pytest.raises(catastro.WfsError, match="Bbox too large"):
        catastro.parse_building_parts(xml)


def test_load_from_files_dedupes(tmp_path):
    gdf = catastro.load_from_files([FIXTURE, FIXTURE], "EPSG:25830")
    assert len(gdf) == 2
    assert gdf.crs.to_epsg() == 25830
    assert {"footprint_m2", "refcat", "floors_above"} <= set(gdf.columns)


REAL_FIXTURE = Path(__file__).parent / "fixtures" / "ruzafa_real_sample.gml"


def test_real_catastro_response_parses():
    """A real 30 x 30 m WFS response from Ruzafa: guards against schema drift."""
    parsed = catastro.parse_building_parts(REAL_FIXTURE.read_bytes())
    assert parsed.n_features == 28
    assert all(r["refcat"] and r["geometry"] is not None for r in parsed.records)
    floors = [r["floors_above"] for r in parsed.records]
    assert all(f is not None for f in floors)  # M1 target: floors_above present
    assert max(floors) >= 5  # Eixample blocks are tall


BUILDINGS_FIXTURE = Path(__file__).parent / "fixtures" / "ruzafa_real_buildings_sample.gml"


def test_parse_building_uses_real_response():
    parsed = catastro.parse_building_uses(BUILDINGS_FIXTURE.read_bytes())
    assert parsed.n_features >= 1
    uses = {r["refcat"]: r["current_use"] for r in parsed.records}
    assert "1_residential" in uses.values()
    assert all(len(k) == 14 for k in uses)


def test_parse_building_uses_missing_use_is_none():
    xml = b"""<root xmlns:bu-ext2d="x" xmlns:base="y"><bu-ext2d:Building>
      <base:localId>5915207YJ2751F</base:localId></bu-ext2d:Building></root>"""
    (rec,) = catastro.parse_building_uses(xml).records
    assert rec == {"refcat": "5915207YJ2751F", "current_use": None}


def test_building_uses_exception_report_raises():
    xml = b"""<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1">
      <ows:Exception><ows:ExceptionText>boom</ows:ExceptionText></ows:Exception>
    </ows:ExceptionReport>"""
    with pytest.raises(catastro.WfsError, match="boom"):
        catastro.parse_building_uses(xml)


def test_fetch_building_uses_maps_refcat_to_use(monkeypatch):
    from blm.config import AreaConfig

    monkeypatch.setattr(catastro, "_get", lambda *a, **k: BUILDINGS_FIXTURE.read_bytes())
    cfg = AreaConfig(name="t", label="t", epsg=25830, bbox=(0, 0, 400, 400))
    uses = catastro.fetch_building_uses(cfg)  # 1 tile; the same fixture is just deduplicated
    assert uses["5915207YJ2751F"] == "1_residential"


def test_fetch_building_uses_tiles_and_dedupes(monkeypatch):
    from blm.config import AreaConfig

    xml = BUILDINGS_FIXTURE.read_bytes()
    calls = []

    def fake_get(session, b, cfg, typename="x"):
        calls.append(typename)
        return xml

    monkeypatch.setattr(catastro, "_get", fake_get)
    cfg = AreaConfig(name="t", label="t", epsg=25830, bbox=(0, 0, 1000, 500))  # 2 tiles
    uses = catastro.fetch_building_uses(cfg)
    assert calls == ["BU.BUILDING", "BU.BUILDING"]
    assert "1_residential" in uses.values()  # same buildings in both tiles, deduped by refcat


class _FakeSession:
    """Counts calls and returns a canned response."""

    def __init__(self, content: bytes):
        self.content, self.calls = content, 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1

        class R:
            content = self.content

            def raise_for_status(self):
                pass

        return R()


def _cfg(monkeypatch, tmp_path):
    from blm.config import AreaConfig

    monkeypatch.setattr(AreaConfig, "raw_dir", property(lambda self: tmp_path))
    return AreaConfig(name="t", label="t", epsg=25830, bbox=(0, 0, 10, 10))


def test_a_tile_is_fetched_once_and_then_read_from_disk(monkeypatch, tmp_path):
    cfg = _cfg(monkeypatch, tmp_path)
    session = _FakeSession(FIXTURE.read_bytes())
    first = catastro._get(session, (0, 0, 500, 500), cfg)
    second = catastro._get(session, (0, 0, 500, 500), cfg)
    assert first == second and session.calls == 1  # the second call never reached the service
    assert catastro._get(session, (500, 0, 1000, 500), cfg) and session.calls == 2  # a new tile


def test_an_error_body_is_not_cached(monkeypatch, tmp_path):
    cfg = _cfg(monkeypatch, tmp_path)
    err = b'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"/>'
    session = _FakeSession(err)
    catastro._get(session, (0, 0, 500, 500), cfg)
    catastro._get(session, (0, 0, 500, 500), cfg)
    assert session.calls == 2  # asked again: a failure must not look like data
    assert not list(tmp_path.rglob("*.xml"))


def test_parallel_fetch_gives_the_same_parts_as_a_single_worker(monkeypatch, tmp_path):
    from dataclasses import replace

    cfg = _cfg(monkeypatch, tmp_path)
    cfg = replace(cfg, bbox=(0, 0, 1500, 1000))  # 6 tiles of 500 m
    monkeypatch.setattr(catastro, "_get", lambda session, b, c, typename=None: FIXTURE.read_bytes())

    def parts(workers):
        c = replace(cfg, catastro=replace(cfg.catastro, workers=workers))
        return catastro.fetch_building_parts(c)

    one, four = parts(1), parts(4)
    assert sorted(one["part_id"]) == sorted(four["part_id"])
    assert len(one) == 2  # the same two fixture parts in every tile are deduplicated by part_id


def test_a_tile_with_no_buildings_is_an_empty_result_not_an_error():
    xml = b"""<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1">
      <ows:Exception><ows:ExceptionText>No records founded for BBOX</ows:ExceptionText>
      </ows:Exception></ows:ExceptionReport>"""
    for parse in (catastro.parse_building_parts, catastro.parse_building_uses):
        parsed = parse(xml)
        assert parsed.records == [] and parsed.n_features == 0


def test_the_empty_answer_is_cached_so_a_restart_does_not_ask_again(monkeypatch, tmp_path):
    cfg = _cfg(monkeypatch, tmp_path)
    empty = (
        b'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception>'
        b"<ows:ExceptionText>No records founded for BBOX</ows:ExceptionText>"
        b"</ows:Exception></ows:ExceptionReport>"
    )
    session = _FakeSession(empty)
    catastro._get(session, (0, 0, 500, 500), cfg)
    catastro._get(session, (0, 0, 500, 500), cfg)
    assert session.calls == 1


def test_a_busy_server_is_retried_with_growing_waits(monkeypatch, tmp_path):
    import requests

    from blm.config import CatastroConfig

    cfg = _cfg(monkeypatch, tmp_path)
    from dataclasses import replace

    cfg = replace(cfg, catastro=CatastroConfig(retries=4, retry_wait_s=3))
    waits = []
    monkeypatch.setattr(catastro.time, "sleep", waits.append)

    class Flaky:
        calls = 0

        def get(self, url, params=None, timeout=None):
            Flaky.calls += 1
            if Flaky.calls < 3:
                raise requests.ReadTimeout("slow")

            class R:
                content = FIXTURE.read_bytes()

                def raise_for_status(self):
                    pass

            return R()

    out = catastro._get(Flaky(), (0, 0, 500, 500), cfg)
    assert out and Flaky.calls == 3 and waits == [3, 6]  # waited 3 s, then 6 s, then it worked


def test_giving_up_names_how_many_tries(monkeypatch, tmp_path):
    from dataclasses import replace

    import requests

    from blm.config import CatastroConfig

    cfg = replace(_cfg(monkeypatch, tmp_path), catastro=CatastroConfig(retries=2, retry_wait_s=0))
    monkeypatch.setattr(catastro.time, "sleep", lambda s: None)

    class Down:
        def get(self, *a, **k):
            raise requests.ConnectionError("down")

    import pytest

    with pytest.raises(catastro.WfsError, match="failed 2 times"):
        catastro._get(Down(), (0, 0, 500, 500), cfg)
