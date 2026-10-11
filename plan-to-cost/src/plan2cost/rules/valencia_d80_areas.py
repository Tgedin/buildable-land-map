# ruff: noqa: E501  (finding messages are kept on one line each)
"""Rules from Tables 7 and 8 of Decreto 80/2023: minimum areas and inscribed figures.

Table 7 gives, per kind of room and number of occupants, the minimum useful area; Table 8 the
free circles and furniture rectangles that must fit. The numbers live in
`valencia_d80_tables` (with the quoted table text); this module only applies them.
"""

from __future__ import annotations

import shapely
from shapely.geometry import Polygon

from plan2cost.plan import Dwelling, Space, Use, rectangle_dims
from plan2cost.rules import valencia_d80_tables as T
from plan2cost.rules.engine import Finding, Status

R54 = "VAL-D80-54.2"
R56 = "VAL-D80-56"
_NON_ROOM = {Use.CIRCULACION, Use.ALMACENAMIENTO, Use.TENDEDERO, Use.EXTERIOR}
_BEDROOMS = {Use.DORMITORIO_DOBLE, Use.DORMITORIO_SENCILLO}
_LIVING_ROWS = {
    frozenset({Use.ESTAR}): "estar",
    frozenset({Use.COMEDOR}): "comedor",
    frozenset({Use.COCINA}): "cocina",
    frozenset({Use.COCINA, Use.COMEDOR}): "cocina_comedor",
    frozenset({Use.ESTAR, Use.COMEDOR}): "estar_comedor",
    frozenset({Use.ESTAR, Use.COMEDOR, Use.COCINA}): "estar_comedor_cocina",
}


def occupant_column(occupants: int) -> int:
    """Index of the table 7 column for this number of occupants."""
    for i, cap in enumerate(T.TABLE7_OCCUPANTS[:-1]):
        if occupants <= cap:
            return i
    return len(T.TABLE7_OCCUPANTS) - 1


def _row(name: str, col: int) -> float | None:
    return T.TABLE_7[name][col]


def _principal_bedroom(d: Dwelling) -> str | None:
    doubles = [s for s in d.with_use(Use.DORMITORIO_DOBLE)]
    return max(doubles, key=lambda s: s.area_m2).id if doubles else None


def _bath_ids_by_size(d: Dwelling) -> list[str]:
    return [s.id for s in sorted(d.with_use(Use.BANO), key=lambda s: -s.area_m2)]


def required_area(space: Space, d: Dwelling, col: int) -> tuple[float | None, str] | None:
    """(minimum area, why) for this space, (None, why) if not allowed, None if no requirement."""
    uses = set(space.uses) - _NON_ROOM
    if not uses:
        return None
    parts: list[tuple[float, str]] = []
    laundry = Use.LAVADERO in uses
    host_for_laundry = bool(uses & {Use.COCINA, Use.BANO, Use.ASEO})
    uses.discard(Use.LAVADERO)

    bedroom = uses & _BEDROOMS
    living = frozenset(uses & {Use.ESTAR, Use.COMEDOR, Use.COCINA})
    if bedroom and living == {Use.ESTAR, Use.COMEDOR, Use.COCINA}:
        v = _row("dormitorio_estar_comedor_cocina", col)
        if v is None:
            return None, "a bedroom-living-dining-kitchen space is only allowed for 2 occupants"
        parts.append((v, "dormitorio-estar-comedor-cocina"))
        living, bedroom = frozenset(), set()
    if bedroom:
        if Use.DORMITORIO_SENCILLO in bedroom:
            parts.append((_row("dormitorio_sencillo", col), "dormitorio sencillo"))
        elif space.id == _principal_bedroom(d):
            parts.append((_row("dormitorio_doble_principal", col), "dormitorio doble principal"))
        else:
            parts.append((_row("dormitorio_doble", col), "dormitorio doble"))
    if living:
        row = _LIVING_ROWS.get(living)
        if row:
            parts.append((_row(row, col), row.replace("_", "-")))
        else:  # art. 54.3: a combination not in the table is the sum of its parts
            for use in sorted(living):
                parts.append((_row(_LIVING_ROWS[frozenset({use})], col), str(use)))
    if Use.BANO in uses:
        first = _bath_ids_by_size(d)[0] == space.id
        parts.append((_row("bano", col) if first else T.OTHER_BATH_MIN_M2, "baño"))
    elif Use.ASEO in uses:
        parts.append((_row("aseo", col), "aseo"))
    if laundry:
        if host_for_laundry:
            parts.append((T.INTEGRATED_LAUNDRY_EXTRA_M2, "lavadero integrado (+1 m²)"))
        else:
            parts.append((_row("lavadero", col), "lavadero"))
    if not parts:
        return None
    total = sum(v for v, _ in parts if v is not None)
    return total, " + ".join(w for _, w in parts)


def _adjacent_to_circulation(d: Dwelling, space: Space) -> bool:
    return any(
        o.polygon.intersection(space.polygon).length > 0
        for o in d.spaces
        if Use.CIRCULACION in o.uses and o.id != space.id
    )


def table_7(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    if d.occupants == 0:
        return [
            Finding(
                R54,
                Status.NEEDS_REVIEW,
                "no bedroom is marked, so the number of occupants (and the table 7 column) is undefined",
            )
        ]
    col = occupant_column(d.occupants)
    label = f"{d.occupants} occupant(s), column {'≥9' if col == 4 else T.TABLE7_OCCUPANTS[col]}"
    out: list[Finding] = []
    for s in d.spaces:
        req = required_area(s, d, col)
        if req is None:
            continue
        need, why = req
        if need is None:
            out.append(Finding(R54, Status.FAIL, f"{s.id}: {why}", s.area_m2, None, (s.id,)))
            continue
        if s.area_m2 >= need - 1e-9:
            status, note = Status.PASS, ""
        elif (
            s.uses & _BEDROOMS
            and s.area_m2 >= need * (1 - T.BEDROOM_CIRCULATION_REDUCTION) - 1e-9
            and _adjacent_to_circulation(d, s)
        ):
            status = Status.NEEDS_REVIEW
            note = (
                " (note 1: up to 20% less is possible next to circulation if the conditions hold)"
            )
        else:
            status, note = Status.FAIL, ""
        out.append(
            Finding(
                R54,
                status,
                f"{s.id} ({why}, {label}): {s.area_m2:.2f} m² vs minimum {need:g} m²{note}",
                s.area_m2,
                need,
                (s.id,),
            )
        )
    return out or [Finding(R54, Status.NOT_APPLICABLE, "no room with a table 7 requirement")]


# ---------------------------------------------------------------- table 8: inscribed figures


def inscribed_diameter(poly: Polygon) -> float:
    """Diameter of the largest circle that fits inside the polygon."""
    return 2.0 * float(shapely.maximum_inscribed_circle(poly, tolerance=0.01).length)


def fits_rectangle(poly: Polygon, rect: tuple[float, float]) -> bool | None:
    """True/False for rectangular rooms; None when the shape needs a human (not a rectangle)."""
    dims = rectangle_dims(poly)
    if dims is None:
        return None
    short, long = dims
    return short >= min(rect) - 1e-9 and long >= max(rect) - 1e-9


def _any_fits(poly: Polygon, rects) -> bool | None:
    results = [fits_rectangle(poly, r) for r in rects]
    if any(r is True for r in results):
        return True
    return None if any(r is None for r in results) else False


def figures(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    out: list[Finding] = []
    circle = T.FREE_CIRCLE_DIAMETER_M

    def circle_finding(s: Space, kind: str) -> Finding:
        diam = inscribed_diameter(s.polygon)
        ok = diam >= circle - 1e-9
        return Finding(
            R56,
            Status.PASS if ok else Status.FAIL,
            f"{s.id} ({kind}): free circle Ø{diam:.2f} m vs Ø{circle:.2f} m",
            diam,
            circle,
            (s.id,),
        )

    for s in d.spaces:
        if (
            s.uses & {Use.ESTAR, Use.COMEDOR, Use.COCINA, Use.LAVADERO}
            and Use.EXTERIOR not in s.uses
        ):
            out.append(circle_finding(s, "free figure"))

    doubles = d.with_use(Use.DORMITORIO_DOBLE)
    if doubles:
        best = max(doubles, key=inscribed_diameter_of_space)
        out.append(circle_finding(best, "free figure, best double bedroom (note 2)"))
    baths = d.with_use(Use.BANO)
    if baths:
        best = max(baths, key=inscribed_diameter_of_space)
        out.append(circle_finding(best, "free figure, best bathroom (note 3)"))

    main_id = _principal_bedroom(d)
    for s in d.spaces:
        if Use.DORMITORIO_SENCILLO in s.uses:
            out.append(_rect_finding(s, "single bedroom 2,00 x 2,00", [T.BEDROOM_SINGLE_RECT]))
        elif Use.DORMITORIO_DOBLE in s.uses:
            if s.id == main_id:
                out.append(_rect_finding(s, "main bedroom 2,60 x 2,60", [T.BEDROOM_MAIN_RECT]))
            else:
                out.append(
                    _rect_finding(
                        s, "double bedroom 2,00 x 2,60 or 4,10 x 1,80", T.BEDROOM_DOUBLE_RECTS
                    )
                )
        if Use.ESTAR in s.uses:
            out.append(_rect_finding(s, "living 2,50 x 3,00 or 2,80 x 2,80", T.STAR_RECTS))
        if Use.COMEDOR in s.uses:
            diam = inscribed_diameter(s.polygon)
            if diam >= T.DINING_CIRCLE_DIAMETER_M - 1e-9:
                out.append(
                    Finding(
                        R56,
                        Status.PASS,
                        f"{s.id}: dining circle Ø{diam:.2f} m",
                        diam,
                        T.DINING_CIRCLE_DIAMETER_M,
                        (s.id,),
                    )
                )
            else:
                alt = fits_rectangle(s.polygon, T.DINING_RECT)
                combined = len(s.uses - _NON_ROOM) > 1
                dims = rectangle_dims(s.polygon)
                side_ok = dims is not None and dims[0] >= T.DINING_RECT_MIN_SIDE_M - 1e-9
                if alt and combined and side_ok:
                    out.append(
                        Finding(
                            R56,
                            Status.PASS,
                            f"{s.id}: dining 2,30 x 3,00 (combined space, short side ≥ 2,50 m, note 4)",
                            space_ids=(s.id,),
                        )
                    )
                elif alt is None:
                    out.append(
                        Finding(
                            R56,
                            Status.NEEDS_REVIEW,
                            f"{s.id}: not rectangular, dining figure needs review",
                            space_ids=(s.id,),
                        )
                    )
                else:
                    out.append(
                        Finding(
                            R56,
                            Status.FAIL,
                            f"{s.id}: neither a Ø2,50 m circle nor the allowed 2,30 x 3,00 rectangle fits",
                            diam,
                            T.DINING_CIRCLE_DIAMETER_M,
                            (s.id,),
                        )
                    )
    return out or [Finding(R56, Status.NOT_APPLICABLE, "no room with a table 8 figure")]


def inscribed_diameter_of_space(s: Space) -> float:
    return inscribed_diameter(s.polygon)


def _rect_finding(s: Space, what: str, rects) -> Finding:
    ok = _any_fits(s.polygon, rects)
    if ok is None:
        return Finding(
            R56,
            Status.NEEDS_REVIEW,
            f"{s.id}: not rectangular, {what} needs review",
            space_ids=(s.id,),
        )
    return Finding(
        R56,
        Status.PASS if ok else Status.FAIL,
        f"{s.id}: {what} {'fits' if ok else 'does not fit'}",
        space_ids=(s.id,),
    )
