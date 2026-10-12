"""Who must agree before floors are added to a Spanish residential building (Ley 49/1960, LPH).

Source: BOE-A-1960-10906, consolidated text downloaded 2026-10-05 (the PDF is kept in
`docs/sources/`). Each requirement quotes its clause. A person read and approved the extraction
(ADR 0005); this is a screening aid, not legal advice, and one question below needs a lawyer.

Open question, deliberately not decided here: art. 17.4 asks for three fifths, but art. 5 says
the share quotas are fixed "por acuerdo de todos los propietarios" and art. 17.6 asks for
unanimity for changes to the title or statutes that no other rule covers. Whether adding floors
(which creates new quotas) triggers unanimity depends on the building's title and on case law.
Until a lawyer says so, `UNANIMITY_RISK` stays a flag on every result.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Requirement:
    what: str
    needed: str  # in words, for people
    owners_share: float | None  # of the total number of owners; None when not a vote
    cuotas_share: float | None  # of the share quotas (cuotas de participación)
    clause: str
    quote: str  # verbatim from the BOE text, cut with "..."


NEW_FLOORS = Requirement(
    what="Build new floors on the building",
    needed="3/5 of all owners who also hold 3/5 of the share quotas",
    owners_share=0.6,
    cuotas_share=0.6,
    clause="LPH art. 17.4, third paragraph",
    quote=(
        "estarán sujetas al voto favorable de las tres quintas partes del total de los "
        "propietarios que, a su vez, representen las tres quintas partes de las cuotas de "
        "participación, [...] la construcción de nuevas plantas y cualquier otra alteración "
        "de la estructura o fábrica del edificio"
    ),
)

AFFECTED_OWNERS = Requirement(
    what="Owners whose flat or local is affected by the works",
    needed="their express consent, and a compensation agreed by the same majority",
    owners_share=None,
    cuotas_share=None,
    clause="LPH art. 10.3.b and art. 17.4, last paragraph",
    quote=(
        "En estos supuestos deberá constar el consentimiento de los titulares afectados y "
        "corresponderá a la Junta de Propietarios [...] la determinación de la indemnización "
        "por daños y perjuicios que corresponda."
    ),
)

ADMIN_AUTHORISATION = Requirement(
    what="Administrative authorisation",
    needed="the authorisation the planning law requires, after the owners' vote",
    owners_share=None,
    cuotas_share=None,
    clause="LPH art. 10.3.b",
    quote=(
        "Estarán sujetas al régimen de autorización administrativa que corresponda: [...] "
        "la construcción de nuevas plantas y cualquier otra alteración de la estructura o "
        "fábrica del edificio"
    ),
)

LIFT = Requirement(
    what="Install a lift (the easier part)",
    needed="a majority of owners who also hold a majority of the share quotas",
    owners_share=0.5,
    cuotas_share=0.5,
    clause="LPH art. 17.2",
    quote=(
        "el establecimiento de los servicios de ascensor, incluso cuando impliquen la "
        "modificación del título constitutivo, o de los estatutos, requerirá el voto favorable "
        "de la mayoría de los propietarios, que, a su vez, representen la mayoría de las cuotas "
        "de participación"
    ),
)

UNANIMITY_RISK = Requirement(
    what="Possible unanimity (NOT decided: ask a lawyer)",
    needed="all owners, if adding floors counts as a change to the title or statutes",
    owners_share=1.0,
    cuotas_share=1.0,
    clause="LPH art. 17.6 and art. 5, last paragraph",
    quote=(
        "Los acuerdos no regulados expresamente en este artículo, que impliquen la aprobación "
        "o modificación de las reglas contenidas en el título constitutivo de la propiedad "
        "horizontal o en los estatutos de la comunidad, requerirán para su validez la "
        "unanimidad del total de los propietarios"
    ),
)

REQUIREMENTS = (NEW_FLOORS, AFFECTED_OWNERS, ADMIN_AUTHORISATION, LIFT, UNANIMITY_RISK)


def owners_needed(n_owners: int, share: float = 0.6) -> int:
    """Smallest number of owners that reaches `share` of `n_owners` (rounded up).

    Three fifths is exact in integers: ceil(3n / 5). Other shares go through a small epsilon so
    that 0.5 of 10 stays 5 and not 6. `n_owners` counts owners, not flats: one person with
    three flats is one owner.
    """
    if n_owners < 1:
        raise ValueError("a building has at least one owner")
    if not 0 < share <= 1:
        raise ValueError("share must be in (0, 1]")
    if share == 0.6:
        return (3 * n_owners + 4) // 5
    needed = n_owners * share
    whole = int(needed)
    return whole if abs(needed - whole) < 1e-9 else whole + 1
