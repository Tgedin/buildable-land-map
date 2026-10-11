"""Measure a dwelling: the quantities a cost estimate (or a quick judgement) needs.

Everything is read off the plan model, so the same numbers come out for a generated plan and
for one read from an image. Heights come from each space's own free height; a space with an
unknown height makes `partition_area_m2` None rather than a number built on a guess.
"""

from __future__ import annotations

from dataclasses import dataclass

from plan2cost.plan import Dwelling, OpeningKind, Use


@dataclass(frozen=True)
class Measures:
    interior_area_m2: float
    circulation_area_m2: float
    partition_length_m: float  # shared walls between interior spaces, counted once
    partition_area_m2: (
        float | None
    )  # length x height, minus door openings; None if a height is unknown
    n_doors: int
    n_windows: int

    @property
    def circulation_share(self) -> float:
        return self.circulation_area_m2 / self.interior_area_m2 if self.interior_area_m2 else 0.0


def partition_length_m(d: Dwelling) -> float:
    """Total length of walls shared between two interior spaces (each wall counted once)."""
    interior = [s for s in d.spaces if s.is_interior]
    total = 0.0
    for i, a in enumerate(interior):
        for b in interior[i + 1 :]:
            total += a.polygon.intersection(b.polygon).length
    return total


def _partition_area(d: Dwelling) -> float | None:
    interior = [s for s in d.spaces if s.is_interior]
    area = 0.0
    for i, a in enumerate(interior):
        for b in interior[i + 1 :]:
            shared = a.polygon.intersection(b.polygon).length
            if shared == 0:
                continue
            if a.free_height_m is None or b.free_height_m is None:
                return None
            area += shared * min(a.free_height_m, b.free_height_m)
    in_walls = sum(
        o.width_m * o.height_m
        for o in d.doors()
        if o.a in {s.id for s in interior} and o.b in {s.id for s in interior}
    )
    return area - in_walls


def measure(d: Dwelling) -> Measures:
    circulation = sum(s.area_m2 for s in d.spaces if s.uses == {Use.CIRCULACION})
    return Measures(
        interior_area_m2=d.interior_area_m2,
        circulation_area_m2=circulation,
        partition_length_m=partition_length_m(d),
        partition_area_m2=_partition_area(d),
        n_doors=len(
            [o for o in d.openings if o.kind in (OpeningKind.DOOR, OpeningKind.ENTRANCE_DOOR)]
        ),
        n_windows=len([o for o in d.openings if o.kind is OpeningKind.WINDOW]),
    )
