"""Screening: how many homes could be added on a parcel, limited by area and by daylight.

This is a first filter, not a design. For each added floor it asks two questions:

    area      how many dwellings fit in the floor plate once a stair/lift core is taken out?
    facade    how many dwellings get their windows on the parcel's free facade?
              (a wall shared with a neighbour is a party wall and cannot have windows)

and takes the smaller number. The dwelling used as the unit is a real generated plan that
the rule engine finds no violation in (Decreto 80/2023, with nothing left to review): the
smallest "clean" one of each bedroom count and typology, so the count is "how many such flats
fit", never an invented average.

What it does NOT check is listed in NOT_CHECKED and travels with every result. In particular
this is a screening of *added floors on an existing building*; structure, the existing stair,
lifts, fire safety, accessibility of common areas, owners' consent and permits decide whether
any of it can actually be built.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from plan2cost.generate.explore import (
    Candidate,
    explore,
    explore_single_aspect,
    frange,
    ranked,
)

NOT_CHECKED = (
    "structure of the existing building and its capacity for extra floors",
    "whether the existing stair can be extended, and lift requirements",
    "fire safety (DB-SI), accessibility of common areas (DB-SUA 9), energy (DB-HE), acoustics",
    "owners' consent (propiedad horizontal), permits, party-wall and neighbour-light conditions",
    "urban parameters other than the plan's height (occupation, setbacks, courtyards)",
    "only Decreto 80/2023 arts. 9-10 and 51-56 are applied to the dwelling",
    "ático: every free facade is set back 4 m (the street side is not known), the 3.20 m "
    "height limit and a pitched roof are not modelled, and whether the existing roof can host it",
)


@dataclass(frozen=True)
class Assumptions:
    """Numbers that are assumed, not derived. Change them and the result changes."""

    net_to_gross: float = 0.85  # useful area / floor area; the plans have no wall thickness
    core_m2: float = 18.0  # stair, landing and lift per floor
    party_tol_m: float = 0.35  # an edge this close to a neighbour is a party wall
    min_patio_m2: float = 30.0  # an inner hole smaller than this is a light well, not a facade
    attic_setback_m: float = (
        4.0  # PGOU art. 6.19.5: the ático is set back this far from street facades
    )


@dataclass(frozen=True)
class Profile:
    """The unit of account: one generated, rule-checked dwelling."""

    n_bedrooms: int
    typology: str
    useful_m2: float
    facade_needed_m: float
    depth_m: float
    width_m: float


@dataclass(frozen=True)
class Screening:
    n_bedrooms: int
    homes: int
    homes_per_floor: int
    added_floors: int
    limit: str  # the smaller cap: "area", "facade", or "both" if equal; "none" without a profile
    area_cap: int
    facade_cap: int
    useful_m2_total: float
    profile: Profile | None
    not_checked: tuple[str, ...] = field(default=NOT_CHECKED)


def _outline_parts(poly: Polygon | MultiPolygon, min_patio_m2: float):
    """The boundary lines that count as facade candidates: the outside, and large inner holes."""
    polys = [poly] if isinstance(poly, Polygon) else list(poly.geoms)
    lines = []
    for p in polys:
        lines.append(p.exterior)
        lines.extend(ring for ring in p.interiors if Polygon(ring).area >= min_patio_m2)
    return lines


def _free_facade_lines(
    poly: Polygon | MultiPolygon,
    neighbours: list[Polygon | MultiPolygon],
    a: Assumptions,
):
    """The parcel's boundary that is not a party wall (and not a small light well)."""
    lines = unary_union(_outline_parts(poly, a.min_patio_m2))
    near = [n for n in neighbours if n.distance(poly) <= 2 * a.party_tol_m]
    if near:
        lines = lines.difference(unary_union(near).buffer(a.party_tol_m))
    return lines


def free_facade_m(
    poly: Polygon | MultiPolygon,
    neighbours: list[Polygon | MultiPolygon],
    a: Assumptions = Assumptions(),  # noqa: B008
) -> float:
    """Length of the parcel's boundary that is not a party wall (and not a small light well)."""
    return float(_free_facade_lines(poly, neighbours, a).length)


def attic_plate_m2(
    poly: Polygon | MultiPolygon,
    neighbours: list[Polygon | MultiPolygon],
    footprint_m2: float,
    a: Assumptions = Assumptions(),  # noqa: B008
) -> float:
    """Floor area of an ático: the building footprint minus a band along the free facades.

    PGOU art. 6.19.5 sets the ático back at least `attic_setback_m` from the facades onto a public
    street or space. We cannot tell a street facade from a back-yard one here, so every free
    facade is set back: conservative, it under-counts where the back is not a street. The
    parcel's share left after the setback is applied to the building footprint, because the
    parcel outline includes unbuilt yards.
    """
    if poly.area <= 0:
        return 0.0
    band = _free_facade_lines(poly, neighbours, a).buffer(a.attic_setback_m)
    return float(footprint_m2 * poly.difference(band).area / poly.area)


ATTIC_ZONE = "ENS"  # Ensanche: the zone art. 6.19 of the Normas applies to
ATTIC_MAX_FLOORS = 8  # "áticos excepto en edificios de más de ocho plantas (incluida la baja)"
ATTIC_CLASSES = ("plan_gap", "at_limit")  # not protected, public, open or without plan height


def attic_eligibility(
    zone: str | None, gap_class: str | None, plan_floors: float | None, floors: float | None
) -> tuple[bool, str]:
    """Can this parcel take an ático under art. 6.19.5? Returns (eligible, reason).

    Conditions taken from the text: Ensanche zone; at most 8 floors including the ground floor;
    no ático when fewer floors were built than the plan assigns, so the building must first
    reach the plan's floor count. A building already above the plan is not assumed to be able
    to add one: it may have an ático already, or be out of the plan.
    """
    nan = float("nan")
    plan_floors = nan if plan_floors is None else plan_floors
    floors = nan if floors is None else floors
    if zone != ATTIC_ZONE:
        return False, "not_ensanche" if zone else "zone_unknown"
    if gap_class not in ATTIC_CLASSES:
        return False, "no_buildable_plan_height"
    if plan_floors != plan_floors or floors != floors:
        return False, "floors_unknown"
    if plan_floors > ATTIC_MAX_FLOORS:
        return False, "plan_over_8_floors"
    if floors > plan_floors:
        return False, "already_above_plan"
    return True, "eligible"


@cache
def best_profile(n_bedrooms: int, typology: str) -> Profile | None:
    """Smallest clean dwelling of this size and typology that the rules do not reject."""
    if typology == "single-aspect":
        cands, _ = explore_single_aspect(n_bedrooms, frange(5.5, 16.0, 0.25))
    else:
        cands, _ = explore(n_bedrooms, frange(4.5, 14.0, 0.25), frange(6.0, 11.0, 0.5))
    clean = ranked(cands, clean_only=True)
    if not clean:
        return None
    c: Candidate = min(clean, key=lambda c: (round(c.area, 2), c.facade_needed_m))
    return Profile(n_bedrooms, c.typology, c.area, c.facade_needed_m, c.depth_m, c.params.width_m)


def screen(
    plate_m2: float,
    free_facade: float,
    added_floors: int,
    n_bedrooms: int,
    a: Assumptions = Assumptions(),  # noqa: B008
) -> Screening:
    """Best result over the typologies for dwellings with `n_bedrooms` bedrooms."""
    best: Screening | None = None
    for typology in ("single-aspect", "double-aspect"):
        profile = best_profile(n_bedrooms, typology)
        if profile is None or added_floors <= 0:
            continue
        gross = profile.useful_m2 / a.net_to_gross
        area_cap = max(0, int((plate_m2 - a.core_m2) // gross))
        facade_cap = int(free_facade // profile.facade_needed_m)
        per_floor = min(area_cap, facade_cap)
        limit = "area" if area_cap < facade_cap else "facade" if facade_cap < area_cap else "both"
        s = Screening(
            n_bedrooms=n_bedrooms,
            homes=per_floor * added_floors,
            homes_per_floor=per_floor,
            added_floors=added_floors,
            limit=limit,
            area_cap=area_cap,
            facade_cap=facade_cap,
            useful_m2_total=round(per_floor * added_floors * profile.useful_m2, 1),
            profile=profile,
        )
        if best is None or (s.homes, -profile.useful_m2) > (best.homes, -best.profile.useful_m2):
            best = s
    return best or Screening(n_bedrooms, 0, 0, added_floors, "none", 0, 0, 0.0, None)
