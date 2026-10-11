"""Search the generator's parameters and keep what the rules do not reject.

For each combination the dwelling is generated and checked by the rule engine. A candidate is
kept only if no rule FAILS. Candidates still carry their `needs_review` findings: a candidate
is "no violation found in the checked rules", never "compliant".

This is a search over a small design space of one dwelling type, so "smallest" means smallest
within this typology (fixed room widths, one layout) and the implemented rules. It is not "the
legal minimum": rules not yet implemented, and design choices outside this layout, move it.
"""

from __future__ import annotations

import argparse
import itertools
from dataclasses import dataclass

from plan2cost.generate.dwelling import DwellingParams, generate
from plan2cost.plan import Dwelling
from plan2cost.quantify import Measures, measure
from plan2cost.rules import engine
from plan2cost.rules.engine import Report, Status
from plan2cost.rules.valencia_d80 import rules


@dataclass(frozen=True)
class Candidate:
    params: DwellingParams
    dwelling: Dwelling
    report: Report
    measures: Measures

    @property
    def area(self) -> float:
        return self.measures.interior_area_m2

    @property
    def review_items(self) -> int:
        return len(self.report.by_status(Status.NEEDS_REVIEW))

    @property
    def clean(self) -> bool:
        """Nothing is left to a person's judgement: every checked rule passes or does not apply."""
        return self.review_items == 0


def frange(start: float, stop: float, step: float) -> list[float]:
    n = int(round((stop - start) / step))
    return [round(start + i * step, 6) for i in range(n + 1)]


def explore(
    n_bedrooms: int,
    widths: list[float],
    depths: list[float],
    corridor_widths: list[float] = (0.9, 1.0, 1.1),
    day_depths: list[float] = (3.0, 3.5, 4.0, 4.5),
    closed_kitchen: tuple[bool, ...] = (False, True),
) -> tuple[list[Candidate], int]:
    """(candidates with no FAIL, number of parameter combinations that produced a plan)."""
    rule_set = rules()
    kept, tried = [], 0
    for w, d, c, dd, k in itertools.product(
        widths, depths, corridor_widths, day_depths, closed_kitchen
    ):
        params = DwellingParams(w, d, n_bedrooms, dd, c, k)
        dwelling = generate(params)
        if dwelling is None:
            continue
        tried += 1
        report = engine.check(dwelling, rule_set)
        if not report.by_status(Status.FAIL):
            kept.append(Candidate(params, dwelling, report, measure(dwelling)))
    return kept, tried


def ranked(cands: list[Candidate], clean_only: bool = False) -> list[Candidate]:
    """Smallest useful area first, then least circulation, then least partition wall.

    clean_only drops candidates that rely on a `needs_review` judgement (for example the 20%
    bedroom reduction of table 7, note 1, whose conditions are not checked).
    """
    pool = [c for c in cands if c.clean] if clean_only else cands
    return sorted(
        pool,
        key=lambda c: (
            round(c.area, 2),
            round(c.measures.circulation_share, 3),
            c.measures.partition_length_m,
        ),
    )


def _line(c: Candidate) -> str:
    p, m = c.params, c.measures
    kitchen = "closed" if p.closed_kitchen else "open"
    return (
        f"  {c.area:6.2f} m²  {p.width_m:g} x {p.depth_m:g} m  corridor {p.corridor_w_m:g} m  "
        f"{kitchen} kitchen  circulation {m.circulation_share:4.0%}  "
        f"partitions {m.partition_length_m:5.1f} m  review items {c.review_items}"
    )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Smallest dwellings the implemented rules do not reject"
    )
    ap.add_argument("--bedrooms", type=int, default=2)
    ap.add_argument("--top", type=int, default=3)
    a = ap.parse_args(argv)
    cands, tried = explore(a.bedrooms, frange(4.5, 14.0, 0.25), frange(6.0, 11.0, 0.25))
    clean = ranked(cands, clean_only=True)
    print(
        f"{a.bedrooms} bedroom(s): {tried} plans generated, {len(cands)} with no violation, "
        f"{len(clean)} with nothing left to a person's judgement"
    )
    print("(Decreto 80/2023 arts. 9-10 and 51-56 with tables 7 and 8; no other rules applied.)")
    print("Smallest with nothing left to review:")
    for c in clean[: a.top]:
        print(_line(c))
    loose = ranked(cands)
    if loose and (not clean or loose[0].area < clean[0].area):
        print(
            "Smallest if the review items (e.g. table 7 note 1, 20% bedroom reduction) are accepted:"
        )
        print(_line(loose[0]))


if __name__ == "__main__":
    main()
