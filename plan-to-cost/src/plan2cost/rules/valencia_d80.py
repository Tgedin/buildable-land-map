# ruff: noqa: E501  (legal quotes and review notes are kept unbroken so they can be diffed against the source)
"""Decreto 80/2023 (Comunitat Valenciana): design and quality norms for dwellings, new build.

Source text: full decree as published in the DOGV of 2 June 2023, read from the Civil
Mercantil database copy (NCL013201) and cross-checked with the INAP copy. Entry into force
was moved by Decreto 202/2023 to "veinte meses" after publication, i.e. 2 February 2025.

KNOWN GAPS (do not paper over them):
- Tables 7 (minimum area per space by occupants) and 8 (inscribable figures) are not in the
  text copies we could read. Rules that need them return NEEDS_REVIEW, never a guessed value.
- A further amending decree was put to public consultation in July 2024; its outcome was
  not established. Re-check the consolidated text before relying on this set.
- Only Title III (new construction) is implemented. Existing buildings and interventions
  (Titles I and II) have different, more flexible rules.

Each Rule quotes its clause verbatim. `rules.engine.params_appear_in_quote` is tested over
the whole set so a number in the code cannot differ from the number in the law.
"""

from __future__ import annotations

from plan2cost.plan import (
    COMMON,
    EXTERIOR,
    Dwelling,
    OpeningKind,
    Use,
    rectangle_dims,
)
from plan2cost.rules.engine import Finding, Rule, Source, Status

DOC = "Decreto 80/2023, de 26 de mayo, del Consell (Comunitat Valenciana)"
IN_FORCE = "2025-02-02"  # 20 months after 2023-06-02 (Decreto 202/2023, disposición final segunda)
RETRIEVED = "civil-mercantil.com NCL013201 / NCL013283, read 2026-10-11; verify against the DOGV"


def _src(clause: str, quote: str) -> Source:
    return Source(DOC, clause, quote, IN_FORCE, RETRIEVED)


def _f(rule_id, status, message, measured=None, required=None, spaces=()) -> Finding:
    return Finding(rule_id, status, message, measured, required, tuple(spaces))


def _na(rule_id: str, why: str) -> list[Finding]:
    return [_f(rule_id, Status.NOT_APPLICABLE, why)]


# ------------------------------------------------------------------ art. 54: areas


def _min_total_area(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    area, need = d.interior_area_m2, p["min_area_m2"]
    ok = area >= need - 1e-9
    return [
        _f(
            "VAL-D80-54.1",
            Status.PASS if ok else Status.FAIL,
            f"useful interior area {area:.2f} m² vs minimum {need:g} m²",
            area,
            need,
        )
    ]


def _table_7(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    return [
        _f(
            "VAL-D80-54.2",
            Status.NEEDS_REVIEW,
            f"minimum area per space for {d.occupants} occupants comes from table 7, which is "
            "not available in the text we could read; check it against the official DOGV",
        )
    ]


# ------------------------------------------------------------------ art. 55: heights

# INTERPRETATION (flagged in the rules' not_verified notes): art. 55 names three groups.
# A laundry may sit inside a bathroom or kitchen (art. 53.2), and such a space is read as the
# bathroom or kitchen it is; a laundry room on its own falls under the general 2,50 m.
_GENERAL_USES = {
    Use.ESTAR,
    Use.COMEDOR,
    Use.DORMITORIO_SENCILLO,
    Use.DORMITORIO_DOBLE,
    Use.ALMACENAMIENTO,
}
_CIRCULATION_USES = {Use.CIRCULACION, Use.BANO, Use.ASEO}


def _height_check(rule_id: str, label: str, spaces, need: float) -> list[Finding]:
    out = []
    for s in spaces:
        if s.free_height_m is None:
            out.append(
                _f(
                    rule_id,
                    Status.NEEDS_REVIEW,
                    f"{s.id}: free height not given",
                    None,
                    need,
                    [s.id],
                )
            )
            continue
        ok = s.free_height_m >= need - 1e-9
        out.append(
            _f(
                rule_id,
                Status.PASS if ok else Status.FAIL,
                f"{s.id} ({label}): free height {s.free_height_m:.2f} m vs minimum {need:.2f} m",
                s.free_height_m,
                need,
                [s.id],
            )
        )
    return out or _na(rule_id, f"no {label} space")


def _height_general(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    spaces = [s for s in d.spaces if s.uses & _GENERAL_USES or s.uses == {Use.LAVADERO}]
    return _height_check("VAL-D80-55.1", "general", spaces, p["min_height_m"])


def _height_kitchen(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    spaces = [s for s in d.spaces if Use.COCINA in s.uses and not s.uses & _GENERAL_USES]
    return _height_check("VAL-D80-55.2", "kitchen", spaces, p["min_height_m"])


def _height_circulation(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    spaces = [
        s
        for s in d.spaces
        if s.uses <= _CIRCULATION_USES | {Use.LAVADERO} and s.uses & _CIRCULATION_USES
    ]
    return _height_check("VAL-D80-55.3", "circulation/bath", spaces, p["min_height_m"])


# ------------------------------------------------------------------ art. 51: circulation


def _entrance_door(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    doors = [o for o in d.openings if o.kind is OpeningKind.ENTRANCE_DOOR]
    if not doors:
        return [_f("VAL-D80-51.1.a", Status.NEEDS_REVIEW, "no entrance door in the plan")]
    return [
        _f(
            "VAL-D80-51.1.a",
            Status.PASS if o.width_m >= p["min_width_m"] - 1e-9 else Status.FAIL,
            f"{o.id}: clear width {o.width_m:.2f} m vs minimum {p['min_width_m']:.2f} m",
            o.width_m,
            p["min_width_m"],
            [o.a],
        )
        for o in doors
    ]


def _interior_doors(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    doors = [o for o in d.openings if o.kind is OpeningKind.DOOR]
    return [
        _f(
            "VAL-D80-51.1.b",
            Status.PASS if o.width_m >= p["min_width_m"] - 1e-9 else Status.FAIL,
            f"{o.id}: clear width {o.width_m:.2f} m vs minimum {p['min_width_m']:.2f} m",
            o.width_m,
            p["min_width_m"],
            [o.a],
        )
        for o in doors
    ] or _na("VAL-D80-51.1.b", "no interior doors")


def _door_height(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    return [
        _f(
            "VAL-D80-51.1.c",
            Status.PASS if o.height_m >= p["min_height_m"] - 1e-9 else Status.FAIL,
            f"{o.id}: clear height {o.height_m:.2f} m vs minimum {p['min_height_m']:.2f} m",
            o.height_m,
            p["min_height_m"],
            [o.a],
        )
        for o in d.doors()
    ] or _na("VAL-D80-51.1.c", "no doors")


def _exterior_opening(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    cands = [
        o
        for o in d.openings
        if EXTERIOR in (o.a, o.b)
        and o.width_m >= p["min_width_m"] - 1e-9
        and o.width_m * o.height_m >= p["min_area_m2"] - 1e-9
    ]
    if cands:
        return [
            _f(
                "VAL-D80-51.1.d",
                Status.PASS,
                f"{cands[0].id}: {cands[0].width_m:.2f} m wide, "
                f"{cands[0].width_m * cands[0].height_m:.2f} m²",
            )
        ]
    return [
        _f(
            "VAL-D80-51.1.d",
            Status.FAIL,
            f"no opening to the exterior at least {p['min_width_m']:.2f} m wide and "
            f"{p['min_area_m2']:.2f} m²",
        )
    ]


def _corridor_width(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    out = []
    for s in (s for s in d.spaces if s.is_corridor):
        dims = rectangle_dims(s.polygon)
        if dims is None:
            out.append(
                _f(
                    "VAL-D80-51.2.a",
                    Status.NEEDS_REVIEW,
                    f"{s.id}: not rectangular, width needs review",
                    None,
                    p["min_width_m"],
                    [s.id],
                )
            )
            continue
        width = dims[0]
        out.append(
            _f(
                "VAL-D80-51.2.a",
                Status.PASS if width >= p["min_width_m"] - 1e-9 else Status.FAIL,
                f"{s.id}: width {width:.2f} m vs minimum {p['min_width_m']:.2f} m",
                width,
                p["min_width_m"],
                [s.id],
            )
        )
    return out or _na("VAL-D80-51.2.a", "no corridor flagged in the plan")


def _corridor_turning(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    out = []
    for s in (s for s in d.spaces if s.is_corridor):
        dims = rectangle_dims(s.polygon)
        length = dims[1] if dims else None
        if length is None or length > p["long_corridor_m"]:
            out.append(
                _f(
                    "VAL-D80-51.2.b",
                    Status.NEEDS_REVIEW,
                    f"{s.id}: longer than {p['long_corridor_m']:.2f} m (or not rectangular): "
                    f"check a free {p['turning_diameter_m']:.2f} m turning circle at the end",
                    length,
                    p["long_corridor_m"],
                    [s.id],
                )
            )
    return out or _na("VAL-D80-51.2.b", "no corridor longer than 10 m")


# ------------------------------------------------------------------ arts. 9, 10, 52, 53: composition


def _composition(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    needed = {
        "estar": {Use.ESTAR},
        "comedor": {Use.COMEDOR},
        "cocina": {Use.COCINA},
        "lavadero": {Use.LAVADERO},
        "tendedero": {Use.TENDEDERO},
        "dormitorio": {Use.DORMITORIO_SENCILLO, Use.DORMITORIO_DOBLE},
        "baño": {Use.BANO},
    }
    missing = [name for name, uses in needed.items() if not d.with_use(*uses)]
    if missing:
        return [_f("VAL-D80-9.3", Status.FAIL, "missing basic spaces: " + ", ".join(missing))]
    return [_f("VAL-D80-9.3", Status.PASS, "all required basic spaces are present")]


def _double_bedroom(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    ok = d.n_double_bedrooms >= 1
    return [
        _f(
            "VAL-D80-52.3",
            Status.PASS if ok else Status.FAIL,
            f"{d.n_double_bedrooms} double bedroom(s); one is required",
            float(d.n_double_bedrooms),
            1.0,
        )
    ]


def _bathrooms(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    need = 2 if d.n_bedrooms >= 3 else 1  # "tres o más dormitorios": a second bathroom
    have = len(d.with_use(Use.BANO))
    return [
        _f(
            "VAL-D80-52.4",
            Status.PASS if have >= need else Status.FAIL,
            f"{have} bathroom(s) for {d.n_bedrooms} bedroom(s); {need} required",
            float(have),
            float(need),
        )
    ]


def _bath_not_only_passage(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    start = d.entrance_space()
    if start is None:
        return [_f("VAL-D80-53.1.c", Status.NEEDS_REVIEW, "no entrance, cannot trace circulation")]
    sanitary = frozenset(s.id for s in d.with_use(Use.BANO, Use.ASEO))
    if not sanitary:
        return _na("VAL-D80-53.1.c", "no bathroom or toilet")
    all_ids = {s.id for s in d.spaces if s.is_interior}
    reach_all = d.reachable_from(start)
    reach_without = d.reachable_from(start, blocked=sanitary)
    cut = sorted((all_ids & reach_all) - reach_without - sanitary)
    if cut:
        return [
            _f(
                "VAL-D80-53.1.c",
                Status.FAIL,
                "a bathroom or toilet is the only way to reach: " + ", ".join(cut),
                spaces=cut,
            )
        ]
    return [
        _f("VAL-D80-53.1.c", Status.PASS, "no space depends on a bathroom or toilet for access")
    ]


def _exterior_windows(d: Dwelling, p: dict[str, float]) -> list[Finding]:
    spaces = d.with_use(
        Use.ESTAR, Use.COMEDOR, Use.COCINA, Use.DORMITORIO_SENCILLO, Use.DORMITORIO_DOBLE
    )
    out = []
    for s in spaces:
        wins = [o for o in d.exterior_openings(s.id) if o.kind is OpeningKind.WINDOW]
        out.append(
            _f(
                "VAL-D80-10.4",
                Status.PASS if wins else Status.FAIL,
                f"{s.id}: {len(wins)} window(s) to the exterior",
                spaces=[s.id],
            )
        )
    return out or _na("VAL-D80-10.4", "no living, dining, kitchen or bedroom space")


# ------------------------------------------------------------------ the rule set


def rules() -> list[Rule]:
    return [
        Rule(
            "VAL-D80-9.3",
            "Basic spaces every dwelling must have",
            _src(
                "art. 9.3",
                "Toda vivienda deberá disponer como mínimo los siguientes espacios básicos: "
                "estar, comedor, cocina, lavadero, tendedero, dormitorio, baño y, en su caso, aseo.",
            ),
            {},
            _composition,
            "Only that each use exists somewhere; lavadero and tendedero conditions (art. 53.2-3) are not checked.",
        ),
        Rule(
            "VAL-D80-10.4",
            "Living, dining, kitchen and bedrooms need exterior openings",
            _src(
                "art. 10.4",
                "Se considera que los espacios de estar, comedor, cocina y dormitorio han de "
                "disponer de huecos exteriores del edificio, practicables y con la superficie y "
                "posición que permitan la percepción visual del exterior, además de la "
                "iluminación y ventilación natural.",
            ),
            {},
            _exterior_windows,
            "Only that a window to the exterior exists; operability, size and position (arts. 48-50) are not checked.",
        ),
        Rule(
            "VAL-D80-51.1.a",
            "Dwelling entrance door width",
            _src(
                "art. 51.1.a",
                "El acceso a la vivienda, desde los espacios comunes de circulación del edificio "
                "o desde el exterior, será a través de una puerta de anchura libre de paso mayor "
                "o igual que 0,80 m, medida en el marco y aportada por no más de una hoja.",
            ),
            {"min_width_m": 0.80},
            _entrance_door,
            "Whether the width comes from a single leaf is not modelled.",
        ),
        Rule(
            "VAL-D80-51.1.b",
            "Interior door width",
            _src(
                "art. 51.1.b",
                "Las puertas de paso tendrán una anchura libre de paso mayor o igual que 0,70 m "
                "medida en el marco y aportada por no más de una hoja, salvo aquellas reguladas "
                "por la normativa vigente en materia de accesibilidad.",
            ),
            {"min_width_m": 0.70},
            _interior_doors,
            "Accessibility exceptions and single-leaf width are not modelled.",
        ),
        Rule(
            "VAL-D80-51.1.c",
            "Door clear height",
            _src(
                "art. 51.1.c",
                "La altura libre mínima del hueco en todas las puertas será de 2,00 m.",
            ),
            {"min_height_m": 2.00},
            _door_height,
        ),
        Rule(
            "VAL-D80-51.1.d",
            "At least one large opening to the exterior",
            _src(
                "art. 51.1.d",
                "Cada vivienda tendrá al menos un hueco al exterior del edificio con una anchura "
                "libre de paso mayor o igual que 0,90 m y superficie mayor o igual que 1,50 m².",
            ),
            {"min_width_m": 0.90, "min_area_m2": 1.50},
            _exterior_opening,
        ),
        Rule(
            "VAL-D80-51.2.a",
            "Corridor width",
            _src(
                "art. 51.2.a",
                "Los pasillos tendrán una anchura libre de paso mayor o igual que 0,90 m, "
                "permitiéndose estrechamientos puntuales de anchura 0,80 m, de longitud 0,50 m y "
                "con separación 0,65 m a huecos de paso o a cambios de dirección.",
            ),
            {"min_width_m": 0.90},
            _corridor_width,
            "Only spaces flagged as corridors are measured, and only if rectangular; local narrowings are not modelled.",
        ),
        Rule(
            "VAL-D80-51.2.b",
            "Turning space at the end of long corridors",
            _src(
                "art. 51.2.b",
                "Existirán espacios para giro de al menos 1,20 m de diámetro libres de "
                "obstáculos al fondo de pasillos de más de 10,00 m.",
            ),
            {"turning_diameter_m": 1.20, "long_corridor_m": 10.00},
            _corridor_turning,
            "The turning circle itself is not tested: long corridors are sent to review.",
        ),
        Rule(
            "VAL-D80-52.3",
            "A main double bedroom",
            _src(
                "art. 52.3",
                "Todas las viviendas contarán con un dormitorio doble principal, aunque no se "
                "materialice físicamente su compartimentación de acuerdo con lo previsto en el "
                "artículo 53.1.a de este Título.",
            ),
            {},
            _double_bedroom,
        ),
        Rule(
            "VAL-D80-52.4",
            "Bathrooms",
            _src(
                "art. 52.4",
                "Todas las viviendas deberán disponer de espacio para la higiene personal con la "
                "dotación correspondiente a baño. Las viviendas de tres o más dormitorios "
                "contarán con un espacio adicional para la higiene personal con la dotación "
                "correspondiente a baño.",
            ),
            {},
            _bathrooms,
            "Fixtures (the 'dotación' of a bathroom) are not modelled: a space with the bathroom use counts.",
        ),
        Rule(
            "VAL-D80-53.1.c",
            "A bathroom or toilet is not the only way into another room",
            _src(
                "art. 53.1.c",
                "El baño y el aseo no serán paso único para acceder a otra habitación o recinto.",
            ),
            {},
            _bath_not_only_passage,
        ),
        Rule(
            "VAL-D80-54.1",
            "Minimum useful interior area",
            _src(
                "art. 54.1",
                "La superficie útil interior mínima total de la vivienda será de 35 m².",
            ),
            {"min_area_m2": 35.0},
            _min_total_area,
        ),
        Rule(
            "VAL-D80-54.2",
            "Minimum area per space by occupants (table 7)",
            _src(
                "art. 54.2",
                "En función del número de ocupantes de la vivienda, los recintos que la componen "
                "contarán con la superficie mínima que se indica en la tabla 7. En estas "
                "superficies mínimas no se incluye el espacio para almacenamiento.",
            ),
            {},
            _table_7,
            "Table 7 is missing from the text we could read: always sent to review.",
        ),
        Rule(
            "VAL-D80-55.1",
            "Free height, general",
            _src(
                "art. 55.1",
                "En la vivienda la altura libre mínima será de 2,50 m, admitiéndose descuelgues "
                "hasta 2,20 m, con ocupación en planta de cada recinto de hasta el 10 % de su "
                "superficie útil.",
            ),
            {"min_height_m": 2.50},
            _height_general,
            "A single free height per space: the allowed 2,20 m drops over 10% of the area are not modelled. A laundry inside a bathroom or kitchen is read as that bathroom or kitchen (interpretation).",
        ),
        Rule(
            "VAL-D80-55.2",
            "Free height, kitchens",
            _src(
                "art. 55.2",
                "En cocinas, la altura libre mínima será de 2,35 m, admitiéndose descuelgues "
                "hasta 2,20 m, con ocupación en planta de hasta el 30 % de su superficie útil.",
            ),
            {"min_height_m": 2.35},
            _height_kitchen,
            "A single free height per space: the allowed 2,20 m drops over 30% of the area are not modelled. A laundry inside the kitchen is read as the kitchen (interpretation).",
        ),
        Rule(
            "VAL-D80-55.3",
            "Free height, circulation, bathrooms and toilets",
            _src(
                "art. 55.3",
                "En espacios de circulación, baños, aseos, la altura libre mínima será de 2,20 m.",
            ),
            {"min_height_m": 2.20},
            _height_circulation,
            "A bathroom that also hosts the laundry is read as a bathroom (interpretation, art. 53.2).",
        ),
    ]


__all__ = ["rules", "COMMON"]
