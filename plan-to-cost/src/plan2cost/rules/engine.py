"""The rule engine. Deterministic: the same plan and rules always give the same report.

A rule never returns "compliant". Each rule returns findings with one of four statuses:
PASS, FAIL, NEEDS_REVIEW (the plan lacks the data, or the rule needs a human judgement),
NOT_APPLICABLE. The report's verdict is deliberately cautious: it can say a violation was
found, or that none was found in what was checked, never that the design "complies".

Every rule carries the legal quote it implements. A test checks that each numeric
parameter appears in that quote, so a number cannot drift away from the law it came from.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from plan2cost.plan import Dwelling


class Status(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class Source:
    document: str  # e.g. "Decreto 80/2023 (Comunitat Valenciana)"
    clause: str  # e.g. "art. 54.1"
    quote: str  # verbatim text of the clause
    in_force_from: str  # ISO date, or "" when not established
    retrieved: str  # where and when the text was obtained


@dataclass(frozen=True)
class Finding:
    rule_id: str
    status: Status
    message: str
    measured: float | None = None
    required: float | None = None
    space_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    source: Source
    params: dict[str, float]
    check: Callable[[Dwelling, dict[str, float]], list[Finding]]
    # What the code does NOT verify of the clause (empty = the whole clause is checked).
    not_verified: str = ""

    def run(self, dwelling: Dwelling) -> list[Finding]:
        return self.check(dwelling, self.params)


@dataclass
class Report:
    dwelling_id: str
    findings: list[Finding] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)

    def by_status(self, status: Status) -> list[Finding]:
        return [f for f in self.findings if f.status is status]

    @property
    def verdict(self) -> str:
        if self.by_status(Status.FAIL):
            return "violation_found"
        if self.by_status(Status.NEEDS_REVIEW):
            return "needs_review"
        return "no_violation_found_in_checked_rules"

    @property
    def partially_verified(self) -> list[Rule]:
        return [r for r in self.rules if r.not_verified]

    def summary(self) -> dict:
        return {
            "dwelling": self.dwelling_id,
            "verdict": self.verdict,
            "rules_run": len(self.rules),
            "counts": {s.value: len(self.by_status(s)) for s in Status},
            "partially_verified_rules": [r.id for r in self.partially_verified],
        }


def check(dwelling: Dwelling, rules: list[Rule]) -> Report:
    report = Report(dwelling.id, rules=list(rules))
    for rule in rules:
        report.findings.extend(rule.run(dwelling))
    return report


def _spanish_forms(value: float) -> set[str]:
    """How a number is written in Spanish legal text: 35, 0,90, 2,5, 1,50 ..."""
    forms = {f"{value:g}", f"{value:.1f}", f"{value:.2f}"}
    return {f.replace(".", ",") for f in forms}


def params_appear_in_quote(rule: Rule) -> list[str]:
    """Parameters whose value does not appear in the rule's quote (empty = all good)."""
    missing = []
    for name, value in rule.params.items():
        if not any(form in rule.source.quote for form in _spanish_forms(value)):
            missing.append(name)
    return missing
