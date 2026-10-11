"""A parametric dwelling: a flat between party walls, with a facade on each long side.

Plan (x runs along the facade, y into the building; south facade at y = 0):

    y = depth    +--------+--------+----+--------+   north facade: bedrooms and bath
                 | bed 1  | bed 2  |bath| (store)|
    y = c_top    +--------+--------+----+--------+
                 |            corridor    ->  entrance door at x = 0 (to the stair landing)
    y = d_day    +----------------------+--------+
                 |  living-dining(-kitchen)       |   south facade: day zone
    y = 0        +--------------------------------+   terrace (tendedero) outside, to the south

The generator only decides geometry and defaults. It does NOT check the rules: callers run
`rules.engine.check`, so the same rules judge a generated plan and a drawn one. Parameters
that would make the layout impossible return None instead of a broken plan.
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import box

from plan2cost.plan import COMMON, EXTERIOR, Dwelling, Opening, OpeningKind, Space, Use

U = Use
O = OpeningKind  # noqa: E741

MAIN_BEDROOM_W = 3.3  # double bedroom width along the facade (a design default, not a rule)
OTHER_BEDROOM_W = 2.7
BATH_MIN_W = 1.6
BATH_MAX_W = 2.4


@dataclass(frozen=True)
class DwellingParams:
    width_m: float  # along the facade
    depth_m: float  # between the two facades
    n_bedrooms: int = 2  # 1 to 3; the first is a double bedroom, the others single
    day_depth_m: float = 4.0  # depth of the living zone
    corridor_w_m: float = 1.0
    closed_kitchen: bool = False  # separate kitchen room instead of open plan
    ceiling_m: float = 2.60
    door_w_m: float = 0.80
    entrance_w_m: float = 0.90
    door_h_m: float = 2.05


def generate(p: DwellingParams) -> Dwelling | None:
    """The dwelling for these parameters, or None if the layout does not fit."""
    if not 1 <= p.n_bedrooms <= 3:
        return None
    night_depth = p.depth_m - p.day_depth_m - p.corridor_w_m
    if night_depth < 2.4 or p.day_depth_m < 2.4:
        return None

    n_baths = 2 if p.n_bedrooms >= 3 else 1
    bed_widths = [MAIN_BEDROOM_W] + [OTHER_BEDROOM_W] * (p.n_bedrooms - 1)
    spare = p.width_m - sum(bed_widths)
    if spare < BATH_MIN_W * n_baths:
        return None
    bath_w = min(spare / n_baths, BATH_MAX_W)
    store_w = spare - bath_w * n_baths

    y0, y1 = p.day_depth_m, p.day_depth_m + p.corridor_w_m  # corridor band
    h = p.ceiling_m
    spaces: list[Space] = []
    openings: list[Opening] = []

    def door(oid: str, a: str, b: str, width: float | None = None) -> None:
        openings.append(Opening(oid, O.DOOR, width or p.door_w_m, p.door_h_m, a, b))

    def window(oid: str, space: str, width: float) -> None:
        openings.append(Opening(oid, O.WINDOW, width, 1.40, space, EXTERIOR))

    # corridor and entrance
    spaces.append(
        Space("corridor", box(0, y0, p.width_m, y1), frozenset({U.CIRCULACION}), 2.40, True)
    )
    openings.append(
        Opening("entrance", O.ENTRANCE_DOOR, p.entrance_w_m, p.door_h_m, "corridor", COMMON)
    )

    # day zone
    if p.closed_kitchen:
        kw = 2.6
        spaces.append(
            Space("living", box(0, 0, p.width_m - kw, y0), frozenset({U.ESTAR, U.COMEDOR}), h)
        )
        spaces.append(
            Space(
                "kitchen",
                box(p.width_m - kw, 0, p.width_m, y0),
                frozenset({U.COCINA, U.LAVADERO}),
                h,
            )
        )
        door("d_living", "corridor", "living")
        door("d_kitchen", "corridor", "kitchen")
        window("w_kitchen", "kitchen", 1.2)
        window("w_living", "living", min(max(0.25 * (p.width_m - kw), 1.4), 2.4))
        laundry_in_bath = False
    else:
        spaces.append(
            Space("living", box(0, 0, p.width_m, y0), frozenset({U.ESTAR, U.COMEDOR, U.COCINA}), h)
        )
        door("d_living", "corridor", "living")
        window("w_living", "living", min(max(0.25 * p.width_m, 1.6), 2.6))
        laundry_in_bath = True
    spaces.append(
        Space("terrace", box(0, -1.8, 3.0, 0), frozenset({U.EXTERIOR, U.TENDEDERO}), None)
    )
    door("d_terrace", "living", "terrace", 0.90)

    # night zone, left to right: bedrooms, bath(s), store
    x = 0.0
    for i, w in enumerate(bed_widths, start=1):
        use = U.DORMITORIO_DOBLE if i == 1 else U.DORMITORIO_SENCILLO
        spaces.append(Space(f"bed{i}", box(x, y1, x + w, p.depth_m), frozenset({use}), h))
        door(f"d_bed{i}", "corridor", f"bed{i}")
        window(f"w_bed{i}", f"bed{i}", 1.2)
        x += w
    for i in range(1, n_baths + 1):
        uses = {U.BANO} | ({U.LAVADERO} if laundry_in_bath and i == 1 else set())
        spaces.append(Space(f"bath{i}", box(x, y1, x + bath_w, p.depth_m), frozenset(uses), 2.40))
        door(f"d_bath{i}", "corridor", f"bath{i}")
        x += bath_w
    if store_w > 0.5:
        spaces.append(
            Space("store", box(x, y1, p.width_m, p.depth_m), frozenset({U.ALMACENAMIENTO}), h)
        )
        door("d_store", "corridor", "store")

    return Dwelling(f"gen-{p.width_m:g}x{p.depth_m:g}-{p.n_bedrooms}b", spaces, openings)
