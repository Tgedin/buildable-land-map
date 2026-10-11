"""A single-aspect dwelling: every habitable room on one facade, entrance on the opposite side.

Typical of narrow lots between party walls, where daylight comes only from the street (or a
courtyard) at one end. Plan (x along the facade, y into the building; facade at y = 0):

    y = depth       +--hall--+-bath-+-store-+     rear band: hall (front door to the landing),
                    |        |      |      |     bathrooms, store
    y = d_f + c     +--------+------+------+
                    |          corridor    |     corridor, doors to every room
    y = d_f         +--------+------+------+
                    | living | bed1 | bed2 |     facade band: living-dining-kitchen and bedrooms
    y = 0           +--------+------+------+     facade (windows), terrace outside

As in `dwelling.py`, the generator decides geometry only and the rule engine judges the result.
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import box

from plan2cost.generate.dwelling import MAIN_BEDROOM_W, OTHER_BEDROOM_W
from plan2cost.plan import COMMON, EXTERIOR, Dwelling, Opening, OpeningKind, Space, Use

U = Use
O = OpeningKind  # noqa: E741

HALL_W = 1.3
BATH_MIN_W = 1.7
BATH_MAX_W = 2.4


@dataclass(frozen=True)
class SingleAspectParams:
    width_m: float  # facade length
    n_bedrooms: int = 2
    facade_depth_m: float = 4.5  # depth of the living and bedroom band
    corridor_w_m: float = 1.0
    rear_depth_m: float = 2.4  # depth of the hall / bathrooms band
    ceiling_m: float = 2.60
    door_w_m: float = 0.80
    entrance_w_m: float = 0.90
    door_h_m: float = 2.05
    # True: the living room runs the full depth of the flat and the corridor serves only the
    # bedrooms and bathrooms beside it, which wastes much less area than a full-width corridor.
    deep_living: bool = False

    @property
    def depth_m(self) -> float:
        return self.facade_depth_m + self.corridor_w_m + self.rear_depth_m


def generate_single_aspect(p: SingleAspectParams) -> Dwelling | None:
    """The dwelling for these parameters, or None if the layout does not fit."""
    if not 1 <= p.n_bedrooms <= 3 or p.facade_depth_m < 2.6 or p.rear_depth_m < 1.8:
        return None
    n_baths = 2 if p.n_bedrooms >= 3 else 1
    bed_widths = [MAIN_BEDROOM_W] + [OTHER_BEDROOM_W] * (p.n_bedrooms - 1)
    living_w = p.width_m - sum(bed_widths)
    if living_w < 2.8:
        return None
    d_f, c, depth, h = p.facade_depth_m, p.corridor_w_m, p.depth_m, p.ceiling_m
    x0 = living_w if p.deep_living else 0.0  # where the corridor and rear band start
    rear_w = p.width_m - x0 - HALL_W
    if rear_w < BATH_MIN_W * n_baths:
        return None
    bath_w = min(rear_w / n_baths, BATH_MAX_W)
    store_w = rear_w - bath_w * n_baths

    spaces: list[Space] = []
    openings: list[Opening] = []

    def door(oid: str, a: str, b: str, width: float | None = None) -> None:
        openings.append(Opening(oid, O.DOOR, width or p.door_w_m, p.door_h_m, a, b))

    # living room: facade band only, or the full depth of the flat
    living_depth = depth if p.deep_living else d_f
    spaces.append(
        Space(
            "living",
            box(0, 0, living_w, living_depth),
            frozenset({U.ESTAR, U.COMEDOR, U.COCINA}),
            h,
        )
    )
    win_w = min(max(0.35 * living_w, 1.4), 2.4)
    openings.append(Opening("w_living", O.WINDOW, win_w, 1.40, "living", EXTERIOR))
    door("d_living", "corridor", "living")
    x = living_w
    for i, w in enumerate(bed_widths, start=1):
        use = U.DORMITORIO_DOBLE if i == 1 else U.DORMITORIO_SENCILLO
        spaces.append(Space(f"bed{i}", box(x, 0, x + w, d_f), frozenset({use}), h))
        openings.append(Opening(f"w_bed{i}", O.WINDOW, 1.2, 1.40, f"bed{i}", EXTERIOR))
        door(f"d_bed{i}", "corridor", f"bed{i}")
        x += w
    terrace_w = min(3.0, living_w)
    spaces.append(
        Space("terrace", box(0, -1.8, terrace_w, 0), frozenset({U.EXTERIOR, U.TENDEDERO}), None)
    )
    door("d_terrace", "living", "terrace", 0.90)

    # corridor
    spaces.append(
        Space("corridor", box(x0, d_f, p.width_m, d_f + c), frozenset({U.CIRCULACION}), 2.40, True)
    )

    # rear band: hall at the landing, bathrooms, store
    spaces.append(
        Space("hall", box(x0, d_f + c, x0 + HALL_W, depth), frozenset({U.CIRCULACION}), 2.40)
    )
    openings.append(
        Opening("entrance", O.ENTRANCE_DOOR, p.entrance_w_m, p.door_h_m, "hall", COMMON)
    )
    door("d_hall", "hall", "corridor", 0.90)
    x = x0 + HALL_W
    for i in range(1, n_baths + 1):
        uses = {U.BANO} | ({U.LAVADERO} if i == 1 else set())
        spaces.append(Space(f"bath{i}", box(x, d_f + c, x + bath_w, depth), frozenset(uses), 2.40))
        door(f"d_bath{i}", "corridor", f"bath{i}")
        x += bath_w
    if store_w > 0.6:
        spaces.append(
            Space("store", box(x, d_f + c, p.width_m, depth), frozenset({U.ALMACENAMIENTO}), h)
        )
        door("d_store", "corridor", "store")

    return Dwelling(f"sa-{p.width_m:g}x{depth:g}-{p.n_bedrooms}b", spaces, openings)
