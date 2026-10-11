import cv2
import numpy as np
import pytest

from plan2cost.eval import cubicasa as cc
from plan2cost.vision import walls

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
<g class="Model"><g class="Floorplan">
 <g id="Wall" class="Wall External">
  <polygon points="40,40 360,40 360,52 40,52"/>
  <g class="Window"><polygon points="100,40 140,40 140,52 100,52"/></g>
 </g>
 <g class="Space Bedroom"><polygon points="52,52 200,52 200,250 52,250"/></g>
 <g class="Space Outdoor"><polygon points="250,100 350,100 350,200 250,200"/></g>
</g></g></svg>"""


def test_label_masks_walls_interior_and_outdoor(tmp_path):
    svg = tmp_path / "model.svg"
    svg.write_text(SVG)
    wall, interior = cc.label_masks(svg, work_dim=400)  # 1 label unit = 1 px
    assert wall[45, 60]
    assert wall.sum() == 321 * 13  # fillPoly includes both edge pixels
    assert interior[150, 100]  # bedroom
    assert not interior[150, 300]  # outdoor space is not interior
    assert wall.shape == (300, 400)


def test_nested_window_polygon_is_not_counted_as_wall(tmp_path):
    svg = tmp_path / "model.svg"
    # a window polygon far from the wall, nested in the Wall group: if it were parsed as a
    # wall, the wall area would grow
    svg.write_text(
        SVG.replace(
            '<polygon points="100,40 140,40 140,52 100,52"/>',
            '<polygon points="100,200 140,200 140,240 100,240"/>',
        )
    )
    wall, _ = cc.label_masks(svg, work_dim=400)
    assert wall.sum() == 321 * 13
    assert not wall[220, 120]


def test_wall_ratio_none_without_interior():
    assert cc.wall_ratio(np.zeros((5, 5), bool), 0) is None


def test_load_split_strips_slashes(tmp_path):
    (tmp_path / "test.txt").write_text("/high_quality/12/\n/colorful/7/\n")
    plans = cc.load_split(tmp_path, "test")
    assert plans == [tmp_path / "high_quality/12", tmp_path / "colorful/7"]


def test_summarize_empty_is_explicit():
    assert cc.summarize([]) == {"n_plans": 0}


def test_summarize_counts_and_errors():
    rows = [
        {"id": "a", "style": "s", "detected": True, "wall_ratio_rel_error": 0.1},
        {"id": "b", "style": "s", "detected": True, "wall_ratio_rel_error": -0.6},
        {"id": "c", "style": "s", "detected": False, "wall_ratio_rel_error": None},
    ]
    s = cc.summarize(rows)
    assert s["n_plans"] == 3 and s["n_with_ratio"] == 2
    assert s["detected_share"] == pytest.approx(0.667, abs=0.001)
    assert s["share_within_20pct"] == 0.5


def test_close_frac_merges_parallel_lines_into_a_wall():
    img = np.full((300, 400), 255, np.uint8)
    cv2.line(img, (50, 100), (350, 100), 0, 1)  # a wall drawn as two thin parallel lines
    cv2.line(img, (50, 112), (350, 112), 0, 1)
    assert walls.wall_mask(img).sum() == 0  # thin strokes are dropped without closing
    assert walls.wall_mask(img, close_frac=0.08)[106, 200]  # merged into one thick wall


def test_evaluate_plan_end_to_end_on_a_synthetic_plan(tmp_path):
    plan = tmp_path / "high_quality" / "1"
    plan.mkdir(parents=True)
    img = np.full((300, 400, 3), 255, np.uint8)
    cv2.rectangle(img, (40, 40), (360, 260), (0, 0, 0), 12)
    cv2.imwrite(str(plan / "F1_scaled.png"), img)
    (plan / "model.svg").write_text(
        SVG.replace(
            '<polygon points="52,52 200,52 200,250 52,250"/>',
            '<polygon points="46,46 354,46 354,254 46,254"/>',
        )
    )
    r = cc.evaluate_plan(plan, close_frac=0.0)
    assert r["detected"] is True and r["style"] == "high_quality" and r["id"] == "1"
    assert r["pred_wall_ratio"] is not None and r["gt_wall_ratio"] is not None
