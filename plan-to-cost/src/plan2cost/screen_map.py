"""Run the screening over the Buildable Land Map's parcels and write web/data/screening.json.

Reads `parcels.parquet` (made by `blm build`, with the plan and zone columns) and asks, for
every parcel with room under the plan (`gap_class == "plan_gap"`) or that can take an ático,
how many 1- and 2-bedroom homes could be added. The result is a screening, not a design:
read `not_checked` in the output before quoting any number.

    python -m plan2cost.screen_map --parcels data/processed/ruzafa-valencia/parcels.parquet \\
        --out web/data/screening.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from plan2cost.consent import REQUIREMENTS
from plan2cost.feasibility import (
    NOT_CHECKED,
    Assumptions,
    attic_eligibility,
    attic_plate_m2,
    free_facade_m,
    screen,
)
from plan2cost.proforma import DEFAULTS, residual_value, sensitivity


def _homes(plate: float, facade: float, floors: int, assumptions: Assumptions) -> dict:
    """Homes, limit, unit and residual value for 1- and 2-bedroom flats on `floors` new floors."""
    out: dict = {}
    for n in (1, 2):
        s = screen(plate, facade, floors, n, assumptions)
        out[f"homes_{n}bed"] = s.homes
        out[f"limit_{n}bed"] = s.limit
        if s.profile:
            out[f"unit_{n}bed"] = {
                "typology": s.profile.typology,
                "useful_m2": round(s.profile.useful_m2, 1),
                "facade_m": round(s.profile.facade_needed_m, 2),
            }
        p = residual_value(s.useful_m2_total, assumptions.net_to_gross)
        out[f"residual_{n}bed"] = {
            "eur": p.residual_eur,  # by scenario, None when withheld
            "excluded": list(p.excluded),
            "withheld_reason": p.withheld_reason,
        }
    return out


def _num(row, key):
    v = row.get(key)
    return None if v is None or v != v else float(v)


def run(parcels, assumptions: Assumptions = Assumptions()) -> dict:  # noqa: B008
    """`parcels` is a GeoDataFrame in a metric CRS with the columns `blm build` writes.

    Two routes are screened. `floors`: parcels the map marks `plan_gap` (room under the plan's
    height), at the top level of each result. `attic`: parcels that can take an ático above the
    cornice (art. 6.19.5), under the `attic` key. A parcel can have either or both.
    """
    tree = parcels.sindex
    out: dict[str, dict] = {}
    for _, row in parcels.iterrows():
        floors_route = row["gap_class"] == "plan_gap"
        eligible, reason = attic_eligibility(
            row.get("zone"), row["gap_class"], _num(row, "plan_floors"), _num(row, "floors")
        )
        if not (floors_route or eligible):
            continue
        geom = row.geometry
        idx = tree.query(geom.buffer(2 * assumptions.party_tol_m))
        near = [parcels.geometry.iloc[i] for i in idx if parcels["refcat"].iloc[i] != row["refcat"]]
        facade = free_facade_m(geom, near, assumptions)
        footprint = float(row["main_footprint_m2"])
        added = int(row["plan_gap_floors"]) if floors_route else 0
        result = {
            "plate_m2": round(footprint, 1),
            "free_facade_m": round(facade, 1),
            "added_floors": added,
            **_homes(footprint, facade, added, assumptions),
        }
        if eligible:
            plate = attic_plate_m2(geom, near, footprint, assumptions)
            result["attic"] = {
                "plate_m2": round(plate, 1),
                "free_facade_m": round(facade, 1),  # the setback line runs parallel to it
                **_homes(plate, facade, 1, assumptions),
            }
        else:
            result["attic"] = {"eligible": False, "reason": reason}
        out[row["refcat"]] = result
    return out


def summarize(per_parcel: dict) -> dict:
    floors = {k: v for k, v in per_parcel.items() if v["added_floors"] > 0}
    attic = {k: v["attic"] for k, v in per_parcel.items() if "homes_2bed" in v["attic"]}
    return {
        "parcels_screened": len(floors),
        "parcels_with_homes_1bed": sum(1 for v in floors.values() if v["homes_1bed"] > 0),
        "parcels_with_homes_2bed": sum(1 for v in floors.values() if v["homes_2bed"] > 0),
        "total_homes_1bed": sum(v["homes_1bed"] for v in floors.values()),
        "total_homes_2bed": sum(v["homes_2bed"] for v in floors.values()),
        "limited_by_facade_2bed": sum(1 for v in floors.values() if v["limit_2bed"] == "facade"),
        "limited_by_area_2bed": sum(1 for v in floors.values() if v["limit_2bed"] == "area"),
        "attic_parcels": len(attic),
        "attic_parcels_with_homes_2bed": sum(1 for v in attic.values() if v["homes_2bed"] > 0),
        "attic_total_homes_1bed": sum(v["homes_1bed"] for v in attic.values()),
        "attic_total_homes_2bed": sum(v["homes_2bed"] for v in attic.values()),
    }


def main(argv: list[str] | None = None) -> None:
    import geopandas as gpd  # only this command needs it

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--parcels", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)

    assumptions = Assumptions()
    per_parcel = run(gpd.read_parquet(a.parcels), assumptions)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": "screening",
        "meaning": (
            "Homes that could be added on the extra floors the plan allows, limited by floor "
            "area and by free facade. A first filter, not a design and not a permit."
        ),
        "assumptions": asdict(assumptions),
        "not_checked": list(NOT_CHECKED),
        "consent": [asdict(r) for r in REQUIREMENTS],
        "sensitivity": {
            "per_m2_built": {k: asdict(v) for k, v in (sensitivity() or {}).items()},
            "inputs": {
                x.name: {
                    "unit": x.unit,
                    "pessimistic": x.pessimistic,
                    "base": x.base,
                    "optimistic": x.optimistic,
                    "status": x.status,
                    "source": x.source,
                }
                for x in (*DEFAULTS.required, DEFAULTS.reinforcement_per_m2)
            },
        },
        "summary": summarize(per_parcel),
        "parcels": per_parcel,
    }
    a.out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
