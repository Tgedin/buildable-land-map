# Data sources (Phase 2)

## Price base: Junta de Extremadura, Base de Precios de la Construcción 2025

- Page: <https://www.juntaex.es/w/base-construccion-2025> (official, free download, `.bc3` plus Presto and PDF tables).
- File: `BCEXTREM25_V.1.bc3`, 17.7 MB, FIEBDC-3/2020, Windows-1252 with one stray `0x81` byte.
- Loads in 0.3 s: 59,473 concepts (6,024 chapters), 28,933 decompositions, 22,986 texts.
- **Licence: the page states none.** So the file is NOT committed. Download it into `plan-to-cost/data/extremadura2025/` (gitignored) yourself.
- It is a **regional** base (Extremadura prices). Fine for developing and testing the parser and mapping, wrong for pricing a Valencia project: for that, use the IVE (Valencia) base once its terms are checked.

Plain word search is not enough: "solado baldosa cerámica" finds nothing in this base, so mapping quantities to price items needs more than keyword search (LLM suggestion with human review, later).
