# Rule sources: what the rules come from, and what is not established

Read this before trusting any result of the rule engine. A rule is only as good as its source, and several gaps below are real.

## Decreto 80/2023 (Comunitat Valenciana), new-construction dwellings

Implemented in `src/plan2cost/rules/valencia_d80.py` (16 rules, each quoting its clause verbatim) with tables 7 and 8 in `valencia_d80_tables.py` and their application in `valencia_d80_areas.py`.

| | |
|---|---|
| Document | Decreto 80/2023, de 26 de mayo, del Consell, por el que se aprueban las normas de diseño y calidad en edificios de vivienda. DOGV núm. 9609, 2 June 2023 |
| Text used | Official DOGV PDF (tables), and the full decree from the Civil Mercantil database copy (NCL013201) and the INAP copy for clause wording. Read 2026-10-11 |
| In force | **2 February 2025**: Decreto 202/2023 (DOGV 23 Nov 2023, ref. NCL013283), final provision 2.ª, sets entry into force "a los veinte meses de su publicación" (2 June 2023 + 20 months). Some websites give 2 Dec 2023 or 2 Oct 2025; neither is supported by the amending text |
| Replaces | Decreto 151/2009 and the Orden of 7 Dec 2009 |
| Scope implemented | Title III (new construction): arts. 9.3, 10.4, 51, 52, 53.1.c, 54 (with table 7), 55, 56 (with table 8) |

### Official source of the tables

The official gazette PDF is `https://dogv.gva.es/datos/2023/06/02/pdf/2023_6094.pdf` (bilingual, 40 pages, DOGV 9609). The DOGV site hides this address behind JavaScript: it is found through `https://dogv.gva.es/dogv-portal/export/disposicion/387208/pdf`, which returns the file's path. **Tables 7 and 8 are in it** (pp. 34133-34135) and are implemented from it (`valencia_d80_tables.py`), checked against the page images. Note the official *Spanish* column contains stray Valencian words in the table footnotes ("aquesta", "aquest"); the quotes keep them as published.

### Known gaps

1. **Tables 9, 10 and 11** (kitchen appliance dimensions, bathroom and laundry fixtures) are not implemented, and neither is the kitchen counter figure of table 8. Fixtures are not modelled.
2. **Later amendment pending.** A further amending decree was put to public consultation (DOGV 9884, 3 July 2024). Its outcome was not established. Re-check the consolidated text before relying on this set.
3. **Transcription is mine.** The tables were read from the PDF and typed in twice (quote and data, compared by a test). A person should still compare them with the DOGV.
4. **Interpretations.** Marked in the code and in each rule's `not_verified` field. Example: a bathroom that also hosts the laundry (art. 53.2) is held to the bathroom height (2,20 m), not the general 2,50 m.
5. **Table 7 note 1** (up to 20% smaller bedrooms next to circulation) is only flagged for review: its conditions (a 1,80 m wide circulation zone with natural light) are not checked. Search results show these separately ("clean" versus review-dependent).
6. **Titles I and II** (existing buildings, interventions) have different, more flexible rules and are not implemented.

## CTE DB-SUA (Safety of use and accessibility), national

Source file: `https://www.codigotecnico.org/pdf/Documentos/SUA/DBSUA.pdf`, consolidated text through Real Decreto 450/2022 (file dated May 2023, 47 pages). The official page mentions newer versions with ministry comments (July 2024). **No rules implemented yet.**

## How a rule is held to its source

- Each `Rule` has the clause's exact words in `source.quote`.
- A test (`params_appear_in_quote`) checks that every numeric parameter in the code appears in that quote, written the Spanish way (`0,90`, `35`). A typo in a number fails the build.
- `not_verified` states what the code does not check of the clause, and the report lists every partially verified rule.
- The engine never says a design "complies". Verdicts are `violation_found`, `needs_review`, or `no_violation_found_in_checked_rules`.
- A language model may help *draft* rules from text, but a person reviews them, and the decision is always made by this deterministic code.
