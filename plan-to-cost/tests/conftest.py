"""A hand-built dwelling that satisfies every implemented rule, and helpers to break it."""

from dataclasses import replace

import pytest
from shapely.geometry import box

from plan2cost.plan import COMMON, EXTERIOR, Dwelling, Opening, OpeningKind, Space, Use

U = Use


def make_dwelling() -> Dwelling:
    """8.0 x 9.0 m flat: open living-kitchen south, corridor, two bedrooms and a bath north."""
    h = 2.60
    spaces = [
        Space("living", box(0, 0, 8, 4.0), frozenset({U.ESTAR, U.COMEDOR, U.COCINA}), h),
        Space("corridor", box(0, 4.0, 8, 4.95), frozenset({U.CIRCULACION}), 2.40, is_corridor=True),
        Space("bed1", box(0, 4.95, 3.6, 9), frozenset({U.DORMITORIO_DOBLE}), h),
        Space("bath", box(3.6, 4.95, 5.6, 9), frozenset({U.BANO, U.LAVADERO}), 2.40),
        Space("bed2", box(5.6, 4.95, 8, 9), frozenset({U.DORMITORIO_SENCILLO}), h),
        Space("terrace", box(0, -2.0, 3.0, 0), frozenset({U.EXTERIOR, U.TENDEDERO}), None),
    ]
    O = OpeningKind  # noqa: E741
    openings = [
        Opening("entrance", O.ENTRANCE_DOOR, 0.90, 2.05, "corridor", COMMON),
        Opening("d_living", O.DOOR, 0.80, 2.05, "corridor", "living"),
        Opening("d_bed1", O.DOOR, 0.80, 2.05, "corridor", "bed1"),
        Opening("d_bath", O.DOOR, 0.80, 2.05, "corridor", "bath"),
        Opening("d_bed2", O.DOOR, 0.80, 2.05, "corridor", "bed2"),
        Opening("w_living", O.WINDOW, 1.60, 1.40, "living", EXTERIOR),
        Opening("w_bed1", O.WINDOW, 1.20, 1.40, "bed1", EXTERIOR),
        Opening("w_bed2", O.WINDOW, 1.20, 1.40, "bed2", EXTERIOR),
    ]
    return Dwelling("sample", spaces, openings)


@pytest.fixture
def dwelling() -> Dwelling:
    return make_dwelling()


def tweak_space(d: Dwelling, space_id: str, **changes) -> Dwelling:
    return replace(d, spaces=[replace(s, **changes) if s.id == space_id else s for s in d.spaces])


def tweak_opening(d: Dwelling, opening_id: str, **changes) -> Dwelling:
    return replace(
        d, openings=[replace(o, **changes) if o.id == opening_id else o for o in d.openings]
    )
