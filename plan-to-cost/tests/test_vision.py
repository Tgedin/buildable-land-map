import cv2
import numpy as np
import pytest

from plan2cost.vision import quantities, rooms, walls


def _plan() -> np.ndarray:
    """White 300x400 image: 12 px thick outer walls and one inner wall -> two rooms."""
    img = np.full((300, 400, 3), 255, np.uint8)
    cv2.rectangle(img, (40, 40), (360, 260), (0, 0, 0), 12)
    cv2.line(img, (200, 40), (200, 260), (0, 0, 0), 12)
    cv2.line(img, (60, 120), (160, 120), (0, 0, 0), 1)  # thin line: a dimension, not a wall
    cv2.putText(img, "12", (80, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)  # text
    return img


def test_wall_mask_keeps_thick_strokes_and_drops_thin_ones():
    m = walls.wall_mask(walls.to_gray(_plan()))
    assert m[40, 100] and m[150, 200]  # outer wall and inner wall
    assert not m[120, 100]  # the thin line
    assert not m[200, 90]  # the text


def test_find_two_rooms_and_not_the_outside():
    m = walls.wall_mask(walls.to_gray(_plan()))
    found = rooms.find_rooms(m)
    assert len(found) == 2
    xs = sorted(r.centroid[0] for r in found)
    assert xs[0] < 200 < xs[1]


def test_interior_area_matches_geometry():
    found = rooms.find_rooms(walls.wall_mask(walls.to_gray(_plan())))
    inner = (360 - 40 - 12) * (260 - 40 - 12) - 12 * (260 - 40 - 12)  # minus the inner wall
    assert rooms.interior_area_px(found) == pytest.approx(inner, rel=0.05)


def test_open_plan_with_a_gap_has_no_room():
    img = np.full((300, 400, 3), 255, np.uint8)
    cv2.rectangle(img, (40, 40), (360, 260), (0, 0, 0), 12)
    cv2.line(img, (200, 40), (200, 60), (255, 255, 255), 14)  # hole in the outer wall
    cv2.rectangle(img, (190, 30), (210, 70), (255, 255, 255), -1)
    assert rooms.find_rooms(walls.wall_mask(walls.to_gray(img))) == []


def test_to_gray_handles_gray_and_alpha():
    g = np.full((10, 10), 7, np.uint8)
    assert walls.to_gray(g) is g
    rgba = np.zeros((4, 4, 4), np.uint8)  # fully transparent -> white
    assert (walls.to_gray(rgba) == 255).all()


def test_quantities_scale_with_metres_per_pixel():
    m = walls.wall_mask(walls.to_gray(_plan()))
    found = rooms.find_rooms(m)
    q1 = {x.key: x for x in quantities.quantities_from_plan(m, found, 0.01)}
    q2 = {x.key: x for x in quantities.quantities_from_plan(m, found, 0.02)}
    assert q2["floor_area"].amount == pytest.approx(4 * q1["floor_area"].amount, rel=0.01)
    assert q2["wall_length"].amount == pytest.approx(2 * q1["wall_length"].amount, rel=0.01)
    assert q1["floor_area"].unit == "m2" and q1["wall_length"].unit == "m"


def test_wall_length_is_about_the_centreline():
    m = walls.wall_mask(walls.to_gray(_plan()))
    expected = 2 * (320 + 220) + 220  # outer rectangle centre-line + inner wall
    assert quantities.wall_length_px(m) == pytest.approx(expected, rel=0.08)


def test_scale_must_be_positive():
    with pytest.raises(ValueError):
        quantities.quantities_from_plan(np.zeros((5, 5), bool), [], 0)


def test_interior_mask_matches_find_rooms():
    m = walls.wall_mask(walls.to_gray(_plan()))
    mask = rooms.interior_mask(m)
    assert mask.sum() == rooms.interior_area_px(rooms.find_rooms(m))
    assert not mask[150, 200]  # on the inner wall
    assert mask[150, 100] and mask[150, 300]  # both rooms
    assert not mask[5, 5]  # outside
