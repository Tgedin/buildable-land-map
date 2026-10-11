from pathlib import Path

from plan2cost import bc3

SAMPLE = Path(__file__).parent / "fixtures" / "sample.bc3"


def test_parse_concepts_and_chapters():
    base = bc3.load_bc3(SAMPLE)
    wall = base.get("EFS010")
    assert wall.unit == "m2"
    assert wall.price == 18.5  # decimal comma, first price only
    assert wall.is_chapter is False
    assert base.get("CAP01").is_chapter is True  # '#' marker dropped, flag kept
    assert base.get("ROOT") is not None


def test_missing_price_is_none_not_zero():
    assert bc3.load_bc3(SAMPLE).get("NOPRICE").price is None


def test_decomposition_and_text():
    base = bc3.load_bc3(SAMPLE)
    assert [c.code for c in base.components["CAP01"]] == ["EFS010", "EPT010", "EFP020"]
    assert base.components["CAP01"][0].factor == 1
    assert "recibido con mortero" in base.texts["EFS010"]


def test_search_ignores_accents_case_and_chapters():
    base = bc3.load_bc3(SAMPLE)
    assert [c.code for c in base.search("ALBAÑILERIA")] == []  # a chapter, not a unit price
    assert [c.code for c in base.search("pintura plastica")] == ["EPT010"]
    assert [c.code for c in base.search("solado", unit="M2")] == ["EFP020"]
    assert base.search("") == []


def test_cp1252_file_is_decoded(tmp_path):
    p = tmp_path / "x.bc3"
    p.write_bytes("~C|A1|m2|Albañilería|1.0||0|\n".encode("cp1252"))
    assert bc3.load_bc3(p).get("A1").summary == "Albañilería"


def test_utf8_file_is_not_turned_into_mojibake(tmp_path):
    p = tmp_path / "u.bc3"
    p.write_bytes("~C|A1|m2|Albañilería|1.0||0|\n".encode())
    assert bc3.load_bc3(p).get("A1").summary == "Albañilería"
