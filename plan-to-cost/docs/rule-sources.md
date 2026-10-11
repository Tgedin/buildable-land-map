# Rule sources: what the rules come from, and what is not established

Read this before trusting any result of the rule engine. A rule is only as good as its source, and several gaps below are real.

## Decreto 80/2023 (Comunitat Valenciana), new-construction dwellings

Implemented in `src/plan2cost/rules/valencia_d80.py` (15 rules, each quoting its clause verbatim).

| | |
|---|---|
| Document | Decreto 80/2023, de 26 de mayo, del Consell, por el que se aprueban las normas de diseño y calidad en edificios de vivienda. DOGV núm. 9609, 2 June 2023 |
| Text used | Full decree from the Civil Mercantil database copy (ref. NCL013201, 33 pages), cross-checked with the INAP copy. Read 2026-10-11 |
| In force | **2 February 2025**: Decreto 202/2023 (DOGV 23 Nov 2023, ref. NCL013283), final provision 2.ª, sets entry into force "a los veinte meses de su publicación" (2 June 2023 + 20 months). Some websites give 2 Dec 2023 or 2 Oct 2025; neither is supported by the amending text |
| Replaces | Decreto 151/2009 and the Orden of 7 Dec 2009 |
| Scope implemented | Title III (new construction): arts. 9.3, 10.4, 51, 52, 53.1.c, 54, 55 |

### Known gaps

1. **Tables 7 and 8 are missing.** Table 7 (minimum area per space by occupants) and table 8 (inscribable figures) are not in either text copy. Rules that need them return `needs_review`; nothing is guessed.
2. **No official gazette PDF.** I could not retrieve the DOGV PDF itself (the site loads its content with JavaScript). The copies used are reputable legal databases, but a human should confirm clause wording, and the tables, against the DOGV.
3. **Later amendment pending.** A further amending decree was put to public consultation (DOGV 9884, 3 July 2024). Its outcome was not established. Re-check the consolidated text before relying on this set.
4. **Interpretations.** Marked in the code and in each rule's `not_verified` field. Example: a bathroom that also hosts the laundry (art. 53.2) is held to the bathroom height (2,20 m), not the general 2,50 m.
5. **Titles I and II** (existing buildings, interventions) have different, more flexible rules and are not implemented.

## CTE DB-SUA (Safety of use and accessibility), national

Source file: `https://www.codigotecnico.org/pdf/Documentos/SUA/DBSUA.pdf`, consolidated text through Real Decreto 450/2022 (file dated May 2023, 47 pages). The official page mentions newer versions with ministry comments (July 2024). **No rules implemented yet.**

## How a rule is held to its source

- Each `Rule` has the clause's exact words in `source.quote`.
- A test (`params_appear_in_quote`) checks that every numeric parameter in the code appears in that quote, written the Spanish way (`0,90`, `35`). A typo in a number fails the build.
- `not_verified` states what the code does not check of the clause, and the report lists every partially verified rule.
- The engine never says a design "complies". Verdicts are `violation_found`, `needs_review`, or `no_violation_found_in_checked_rules`.
- A language model may help *draft* rules from text, but a person reviews them, and the decision is always made by this deterministic code.
