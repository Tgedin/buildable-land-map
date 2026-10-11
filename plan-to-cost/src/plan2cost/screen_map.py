"""Run the screening over the Buildable Land Map's parcels and write web/data/screening.json.

Reads `parcels.parquet` (made by `blm build`, with the plan columns) and, for every parcel the
map marks as having room under the plan (`gap_class == "plan_gap"`), asks how many 1- and
2-bedroom homes could be added on the extra floors. The result is a screening, not a design:
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

from plan2cost.feasibility import NOT_CHECKED, Assumptions, free_facade_m, screen


def run(parcels, assumptions: Assumptions = Assumptions()) -> dict:  # noqa: B008
    """`parcels` is a GeoDataFrame in a metric CRS with the columns `blm build` writes."""
    candidates = parcels[parcels["gap_class"] == "plan_gap"]
    tree = parcels.sindex
    out: dict[str, dict] = {}
    for _, row in candidates.iterrows():
        geom = row.geometry
        idx = tree.query(geom.buffer(2 * assumptions.party_tol_m))
        near = [parcels.geometry.iloc[i] for i in idx if parcels["refcat"].iloc[i] != row["refcat"]]
        facade = free_facade_m(geom, near, assumptions)
        floors = int(row["plan_gap_floors"])
        plate = float(row["main_footprint_m2"])
        result = {
            "plate_m2": round(plate, 1),
            "free_facade_m": round(facade, 1),
            "added_floors": floors,
        }
        for n in (1, 2):
            s = screen(plate, facade, floors, n, assumptions)
            result[f"homes_{n}bed"] = s.homes
            result[f"limit_{n}bed"] = s.limit
            if s.profile:
                result[f"unit_{n}bed"] = {
                    "typology": s.profile.typology,
                    "useful_m2": round(s.profile.useful_m2, 1),
                    "facade_m": round(s.profile.facade_needed_m, 2),
                }
        out[row["refcat"]] = result
    return out


def summarize(per_parcel: dict) -> dict:
    n = len(per_parcel)
    return {
        "parcels_screened": n,
        "parcels_with_homes_1bed": sum(1 for v in per_parcel.values() if v["homes_1bed"] > 0),
        "parcels_with_homes_2bed": sum(1 for v in per_parcel.values() if v["homes_2bed"] > 0),
        "total_homes_1bed": sum(v["homes_1bed"] for v in per_parcel.values()),
        "total_homes_2bed": sum(v["homes_2bed"] for v in per_parcel.values()),
        "limited_by_facade_2bed": sum(
            1 for v in per_parcel.values() if v["limit_2bed"] == "facade"
        ),
        "limited_by_area_2bed": sum(1 for v in per_parcel.values() if v["limit_2bed"] == "area"),
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
        "summary": summarize(per_parcel),
        "parcels": per_parcel,
    }
    a.out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
