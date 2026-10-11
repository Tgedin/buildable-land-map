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
