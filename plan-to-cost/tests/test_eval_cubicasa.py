import cv2
import numpy as np
import pytest

from plan2cost.eval import cubicasa as cc
from plan2cost.vision import walls

# The SVG's own width/height (here 999 x 888) deliberately differ from the image (400 x 300):
# polygons are pixel coordinates of the image and must NOT be scaled by those attributes.
SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="999" height="888">
<g class="Model"><g class="Floorplan">
 <g id="Wall" class="Wall External">
  <polygon points="40,40 360,40 360,52 40,52"/>
  <g class="Window"><polygon points="100,200 140,200 140,240 100,240"/></g>
 </g>
 <g class="Space Bedroom"><polygon points="52,52 200,52 200,250 52,250"/></g>
 <g class="Space Outdoor"><polygon points="250,100 350,100 350,200 250,200"/></g>
</g></g></svg>"""


def test_label_masks_use_pixel_coordinates_unscaled(tmp_path):
    svg = tmp_path / "model.svg"
    svg.write_text(SVG)
    wall, interior = cc.label_masks(svg, (300, 400))
    assert wall[45, 60] and wall.sum() == 321 * 13  # fillPoly includes both edge pixels
    assert interior[150, 100]  # bedroom
    assert not interior[150, 300]  # outdoor space is not interior
    assert wall.shape == (300, 400)


def test_nested_window_polygon_is_not_counted_as_wall(tmp_path):
    svg = tmp_path / "model.svg"
    svg.write_text(SVG)
    wall, _ = cc.label_masks(svg, (300, 400))
    assert not wall[220, 120]  # the window polygon is a child of the Wall group, not a wall


def test_label_masks_follow_the_image_scale(tmp_path):
    svg = tmp_path / "model.svg"
    svg.write_text(SVG)
    half, _ = cc.label_masks(svg, (150, 200), scale=0.5)
    assert half[22, 30]  # (60, 45) at full size
    assert half.sum() == pytest.approx(321 * 13 / 4, rel=0.1)


def test_overlap_metrics():
    a = np.zeros((10, 10), bool)
    b = np.zeros((10, 10), bool)
    a[:5] = True
    b[:, :5] = True  # 25 px overlap, 50 + 50 - 25 = 75 union
    m = cc.overlap(a, b)
    assert m["iou"] == pytest.approx(25 / 75)
    assert m["precision"] == pytest.approx(0.5) and m["recall"] == pytest.approx(0.5)


def test_overlap_empty_masks_are_zero_not_nan():
    z = np.zeros((4, 4), bool)
    assert cc.overlap(z, z) == {"iou": 0.0, "precision": 0.0, "recall": 0.0}


def test_load_split_strips_slashes(tmp_path):
    (tmp_path / "test.txt").write_text("/high_quality/12/\n/colorful/7/\n")
    plans = cc.load_split(tmp_path, "test")
    assert plans == [tmp_path / "high_quality/12", tmp_path / "colorful/7"]


def test_summarize_empty_is_explicit():
    assert cc.summarize([]) == {"n_plans": 0}


def test_summarize_means_and_by_style():
    base = {"style": "s", "wall_precision": 0.5, "wall_recall": 0.5}
    rows = [
        {**base, "id": "a", "detected": True, "wall_iou": 0.4, "interior_iou": 0.8},
        {**base, "id": "b", "detected": False, "wall_iou": 0.2, "interior_iou": 0.0},
    ]
    s = cc.summarize(rows)
    assert s["n_plans"] == 2 and s["detected_share"] == 0.5
    assert s["wall_iou_mean"] == pytest.approx(0.3)
    assert s["interior_iou_ge_0.5_share"] == 0.5
    assert s["by_style"]["s"]["n"] == 2


def test_close_frac_merges_parallel_lines_into_a_wall():
    img = np.full((300, 400), 255, np.uint8)
    cv2.line(img, (50, 100), (350, 100), 0, 1)  # a wall drawn as two thin parallel lines
    cv2.line(img, (50, 112), (350, 112), 0, 1)
    assert walls.wall_mask(img).sum() == 0  # thin strokes are dropped without closing
    assert walls.wall_mask(img, close_frac=0.08)[106, 200]  # merged into one thick wall


def test_evaluate_plan_scores_a_perfect_synthetic_plan(tmp_path):
    plan = tmp_path / "high_quality" / "1"
    plan.mkdir(parents=True)
    img = np.full((300, 400, 3), 255, np.uint8)
    cv2.rectangle(img, (40, 40), (360, 260), (0, 0, 0), 12)
    cv2.imwrite(str(plan / "F1_scaled.png"), img)
    # cv2 centres a 12 px stroke on the line, so the wall ring spans 34..46 and 354..366 / 254..266
    (plan / "model.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
        '<g class="Wall"><polygon points="34,34 366,34 366,46 34,46"/>'
        '<polygon points="34,254 366,254 366,266 34,266"/>'
        '<polygon points="34,34 46,34 46,266 34,266"/>'
        '<polygon points="354,34 366,34 366,266 354,266"/></g>'
        '<g class="Space Bedroom"><polygon points="46,46 354,46 354,254 46,254"/></g></svg>'
    )
    r = cc.evaluate_plan(plan, work_dim=400)
    assert r["id"] == "1" and r["style"] == "high_quality" and r["detected"] is True
    assert r["interior_iou"] > 0.9
    assert r["wall_iou"] > 0.7
