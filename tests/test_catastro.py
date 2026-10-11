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
