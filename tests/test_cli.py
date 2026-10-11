import json
from pathlib import Path

from blm import cli

FIXTURE = Path(__file__).parent / "fixtures" / "buildingparts_sample.gml"


def _config(tmp_path: Path) -> Path:
    cfg = tmp_path / "area.yaml"
    cfg.write_text(
        "name: test-area\nlabel: Test\nepsg: 25830\nbbox: [440290, 4473490, 440330, 4473530]\n"
    )
    return cfg


def test_fetch_from_files_then_build(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    import blm.config as config

    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    cfg = _config(tmp_path)

    cli.main(["--config", str(cfg), "fetch", "--from-files", str(FIXTURE)])
    cli.main(["--config", str(cfg), "build"])

    summary = json.loads((tmp_path / "web" / "data" / "summary.json").read_text())
    assert summary["n_parcels"] == 1
    assert summary["synthetic"] is False


def test_plan_command_saves_alignments(tmp_path, monkeypatch):
    import geopandas as gpd

    import blm.config as config
    from blm import planning

    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    cfg = tmp_path / "area.yaml"
    cfg.write_text(
        "name: test-area\nlabel: Test\nepsg: 25830\nbbox: [0, 0, 10, 10]\n"
        "planning:\n  alignments_url: https://example.test/MapServer/1\n"
    )
    fixture = Path(__file__).parent / "fixtures" / "pgou_alignments_sample.geojson"
    monkeypatch.setattr(
        planning,
        "fetch_alignments",
        lambda _cfg: planning.classify_alignments(gpd.read_file(fixture)),
    )
    cli.main(["--config", str(cfg), "plan"])
    saved = gpd.read_parquet(tmp_path / "data" / "interim" / "test-area" / "pgou.parquet")
    assert {"kind", "plan_floors"} <= set(saved.columns)
