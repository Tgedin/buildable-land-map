"""The plan model: one dwelling as code, shared by the generator, the rules and the pricing.

Everything that produces or reads a plan (a generator, the vision model, a hand-drawn
sketch) fills this structure, and everything that judges it (the rule engine, the cost
estimator) reads it. Units are metres in a local frame.

It mirrors the vocabulary of the Valencian design decree (Decreto 80/2023, arts. 9, 52):
a *space* (recinto) hosts one or more *basic uses* (estar, comedor, cocina...), so an
open-plan living-dining-kitchen is one space with three uses.

Missing values are None, never 0: a free height of None means "unknown", which the rules
report as "needs review", not as a pass or a fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import shapely
from shapely.geometry import Polygon

EXTERIOR = "exterior"  # an opening to outside the building
COMMON = "common"  # an opening to the building's shared circulation (stair landing...)


class Use(StrEnum):
    ESTAR = "estar"  # living
    COMEDOR = "comedor"  # dining
    COCINA = "cocina"  # kitchen
    LAVADERO = "lavadero"  # laundry
    TENDEDERO = "tendedero"  # drying space
    DORMITORIO_SENCILLO = "dormitorio_sencillo"  # single bedroom
    DORMITORIO_DOBLE = "dormitorio_doble"  # double bedroom
    BANO = "bano"  # bathroom
    ASEO = "aseo"  # toilet (wc + basin)
    CIRCULACION = "circulacion"  # hall, corridor
    ALMACENAMIENTO = "almacenamiento"  # storage
    EXTERIOR = "exterior"  # terrace, balcony: not useful interior area


class OpeningKind(StrEnum):
    DOOR = "door"
    ENTRANCE_DOOR = "entrance_door"  # the dwelling's front door, to COMMON
    WINDOW = "window"  # to EXTERIOR


@dataclass(frozen=True)
class Space:
    id: str
    polygon: Polygon
    uses: frozenset[Use]
    free_height_m: float | None = None  # clear height; None = unknown
    is_corridor: bool = False  # a pasillo (elongated circulation), as opposed to a hall

    @property
    def area_m2(self) -> float:
        return float(self.polygon.area)

    @property
    def is_interior(self) -> bool:
        return Use.EXTERIOR not in self.uses


@dataclass(frozen=True)
class Opening:
    id: str
    kind: OpeningKind
    width_m: float
    height_m: float
    a: str  # space id
    b: str  # space id, EXTERIOR or COMMON


@dataclass
class Dwelling:
    id: str
    spaces: list[Space] = field(default_factory=list)
    openings: list[Opening] = field(default_factory=list)

    def space(self, space_id: str) -> Space:
        return next(s for s in self.spaces if s.id == space_id)

    def with_use(self, *uses: Use) -> list[Space]:
        return [s for s in self.spaces if s.uses & set(uses)]

    @property
    def interior_area_m2(self) -> float:
        """Useful interior area: every space that is not purely exterior."""
        return sum(s.area_m2 for s in self.spaces if s.is_interior)

    @property
    def n_double_bedrooms(self) -> int:
        return len(self.with_use(Use.DORMITORIO_DOBLE))

    @property
    def n_single_bedrooms(self) -> int:
        return len(self.with_use(Use.DORMITORIO_SENCILLO))

    @property
    def n_bedrooms(self) -> int:
        return self.n_double_bedrooms + self.n_single_bedrooms

    @property
    def occupants(self) -> int:
        """Art. 54.4: one person per single bedroom, two per double bedroom."""
        return self.n_single_bedrooms + 2 * self.n_double_bedrooms

    def doors(self) -> list[Opening]:
        return [o for o in self.openings if o.kind in (OpeningKind.DOOR, OpeningKind.ENTRANCE_DOOR)]

    def exterior_openings(self, space_id: str) -> list[Opening]:
        return [o for o in self.openings if EXTERIOR in (o.a, o.b) and space_id in (o.a, o.b)]

    def entrance_space(self) -> str | None:
        for o in self.openings:
            if o.kind is OpeningKind.ENTRANCE_DOOR:
                return o.a if o.b == COMMON else o.b
        return None

    def graph(self) -> dict[str, set[str]]:
        """Space-to-space connections through doors (windows do not connect spaces)."""
        ids = {s.id for s in self.spaces}
        g: dict[str, set[str]] = {i: set() for i in ids}
        for o in self.openings:
            if o.kind is OpeningKind.DOOR and o.a in ids and o.b in ids:
                g[o.a].add(o.b)
                g[o.b].add(o.a)
        return g

    def reachable_from(self, start: str, blocked: frozenset[str] = frozenset()) -> set[str]:
        g = self.graph()
        seen, stack = set(), [start]
        while stack:
            cur = stack.pop()
            if cur in seen or cur in blocked:
                continue
            seen.add(cur)
            stack.extend(g[cur] - seen)
        return seen


def rectangle_dims(polygon: Polygon, tol: float = 0.01) -> tuple[float, float] | None:
    """(short side, long side) if the polygon is a rectangle, else None.

    A rectangle's area equals that of its minimum rotated rectangle; anything else (an
    L-shaped corridor) has no single "width", so callers must send it to review.
    """
    mrr = polygon.minimum_rotated_rectangle
    if mrr.area == 0 or abs(polygon.area - mrr.area) / mrr.area > tol:
        return None
    xs, ys = mrr.exterior.coords.xy
    a = shapely.distance(shapely.points(xs[0], ys[0]), shapely.points(xs[1], ys[1]))
    b = shapely.distance(shapely.points(xs[1], ys[1]), shapely.points(xs[2], ys[2]))
    return (float(min(a, b)), float(max(a, b)))
