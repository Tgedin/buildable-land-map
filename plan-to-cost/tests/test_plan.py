import pytest
from conftest import make_dwelling
from shapely.geometry import Polygon, box

from plan2cost.plan import Space, Use, rectangle_dims


def test_occupants_follow_art_54_4():
    d = make_dwelling()  # one double + one single bedroom
    assert d.n_bedrooms == 2 and d.occupants == 3


def test_graph_connects_through_doors_only():
    d = make_dwelling()
    g = d.graph()
    assert g["corridor"] >= {"living", "bed1", "bed2", "bath"}
    assert "bed1" not in g["bed2"]  # windows and shared walls do not connect rooms
    assert d.reachable_from("corridor") == {s.id for s in d.spaces if s.id != "terrace"}


def test_blocked_spaces_cut_the_graph():
    d = make_dwelling()
    assert "bath" not in d.reachable_from("corridor", blocked=frozenset({"bath"}))


def test_entrance_space():
    assert make_dwelling().entrance_space() == "corridor"


def test_rectangle_dims_and_non_rectangles():
    assert rectangle_dims(box(0, 0, 8, 0.95)) == pytest.approx((0.95, 8.0))
    assert rectangle_dims(Polygon([(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (0, 3)])) is None
    assert rectangle_dims(box(0, 0, 3, 5)) == pytest.approx((3.0, 5.0))


def test_exterior_space_is_not_interior():
    s = Space("t", box(0, 0, 1, 1), frozenset({Use.EXTERIOR, Use.TENDEDERO}))
    assert not s.is_interior
    assert Space("r", box(0, 0, 1, 1), frozenset({Use.ESTAR})).is_interior
