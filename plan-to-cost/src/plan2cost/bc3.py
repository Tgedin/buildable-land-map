"""Read a BC3 (FIEBDC-3) price base: concepts (~C), decompositions (~D) and texts (~T).

BC3 is the Spanish construction price-base exchange format. A file is a list of records,
each starting with `~` and a letter, with fields separated by `|` and sub-fields by `\\`:

    ~C|CODE|UNIT|SUMMARY|PRICE1\\PRICE2|DATE|TYPE|     a concept (a unit price, a chapter…)
    ~D|PARENT|CHILD\\FACTOR\\YIELD\\CHILD\\FACTOR\\YIELD|  what a concept is made of
    ~T|CODE|long text|

Codes ending in `#` are chapters, `##` the root. We drop the marker and keep `is_chapter`.
Only the first price is read: later ones are alternative price columns (e.g. by year).
A price that is missing or unreadable stays None, never 0.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Concept:
    code: str
    unit: str
    summary: str
    price: float | None
    kind: str | None  # raw BC3 type field (0 none, 1 labour, 2 machinery, 3 material…)
    is_chapter: bool = False


@dataclass(frozen=True)
class Component:
    code: str
    factor: float | None
    yield_: float | None


@dataclass
class PriceBase:
    concepts: dict[str, Concept] = field(default_factory=dict)
    components: dict[str, list[Component]] = field(default_factory=dict)
    texts: dict[str, str] = field(default_factory=dict)

    def get(self, code: str) -> Concept | None:
        return self.concepts.get(code)

    def search(self, query: str, unit: str | None = None, limit: int = 10) -> list[Concept]:
        """Concepts whose summary contains every word of `query` (accent/case-insensitive)."""
        words = _norm(query).split()
        if not words:
            return []
        hits = [
            c
            for c in self.concepts.values()
            if not c.is_chapter
            and all(w in _norm(c.summary) for w in words)
            and (unit is None or _norm(c.unit) == _norm(unit))
        ]
        return sorted(hits, key=lambda c: (len(c.summary), c.code))[:limit]


def _norm(text: str) -> str:
    stripped = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in stripped if unicodedata.category(ch) != "Mn")


def _float(text: str) -> float | None:
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None


def _clean_code(raw: str) -> tuple[str, bool]:
    code = raw.strip()
    return code.rstrip("#"), code.endswith("#")


def parse_bc3(text: str) -> PriceBase:
    base = PriceBase()
    for chunk in text.replace("\r", "").split("~")[1:]:
        kind, _, rest = chunk.partition("|")
        fields = rest.split("|")
        if kind == "C" and len(fields) >= 3:
            code, is_chapter = _clean_code(fields[0])
            if not code:
                continue
            prices = fields[3].split("\\") if len(fields) > 3 else []
            base.concepts[code] = Concept(
                code=code,
                unit=fields[1].strip(),
                summary=fields[2].strip(),
                price=_float(prices[0]) if prices else None,
                kind=fields[5].strip() if len(fields) > 5 and fields[5].strip() else None,
                is_chapter=is_chapter,
            )
        elif kind == "D" and len(fields) >= 2:
            parent, _ = _clean_code(fields[0])
            parts = fields[1].split("\\")
            base.components[parent] = [
                Component(
                    _clean_code(parts[i])[0],
                    _float(parts[i + 1]) if i + 1 < len(parts) else None,
                    _float(parts[i + 2]) if i + 2 < len(parts) else None,
                )
                for i in range(0, len(parts) - 2, 3)
                if parts[i].strip()
            ]
        elif kind == "T" and len(fields) >= 2:
            base.texts[_clean_code(fields[0])[0]] = fields[1].strip()
    return base


def load_bc3(path: Path) -> PriceBase:
    """Read a .bc3 file. BC3 is normally Windows-1252, but some tools write UTF-8.

    UTF-8 is tried first on purpose: cp1252 accepts almost any bytes, so it would silently
    turn a UTF-8 file into mojibake, whereas strict UTF-8 rejects real cp1252 accents.
    The last resort replaces undefined bytes instead of failing: a real 17 MB base (Junta de
    Extremadura 2025) contains a stray 0x81 that strict cp1252 refuses, and one bad character
    in a description must not stop the whole price base from loading.
    """
    raw = path.read_bytes()
    try:
        return parse_bc3(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return parse_bc3(raw.decode("cp1252", errors="replace"))
