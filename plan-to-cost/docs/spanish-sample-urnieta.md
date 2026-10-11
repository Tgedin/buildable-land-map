# First test on a real Spanish plan (one sheet, Urnieta VPO)

**Short version: the model, trained only on Finnish plans, finds the wall network and room interiors of a Spanish public-housing floor plan it has never seen, but it also marks the title block and margins as "interior", and its area changes by about ±5% with the input size. One sheet is an anecdote, not a validation.**

## The sample

- Official Basque Government document: *Proyecto básico*, 25 VPO dwellings, parcel UD1.2, Urnieta (Gipuzkoa), sheet A154 "Planta primera", July 2022. A1 sheet, scale 1:50, five dwelling types (A.1 to E.1) around a central core.
- Source: `https://www.euskadi.eus/contenidos/noticia/insc_25_urnieta_vs/eu_def/adjuntos/8-LEHENENGO-SOLAIRUA-PLANTA-PRIMERA.pdf`
- **Reuse terms not checked.** It is used here only for a private test; the PDF and renders are not committed (`data/` is ignored).
- Ground truth available: the sheet prints each type's useful interior area: A.1 61.68, B.1 74.83, C.1 74.49, D.1 77.21, E.1 63.15 m² (sum **351.36 m²**). Corridor, stair/lift core, patio and terraces are not printed.

## Method

PDF rendered at 72 dpi (1 px = 1 pt = 0.3528 mm of paper = **0.01764 m** at 1:50). Grayscale into the U-Net trained on CubiCasa5k (`results/unet256.pt`), at three input sizes. Interior counted only inside the building outline (a hand-chosen crop: the model has no notion of where the building ends).

## Results

| Input size | Interior inside the outline |
|---|---|
| 384 px | 429 m² |
| 640 px | 392 m² |
| 896 px | 415 m² |

Compared with 351.4 m² of printed dwelling area **plus roughly 40-60 m² of corridor, core and patio that I estimated by eye** (about 25 m² corridor, 19 m² core, a patio of ~11 m²): 392-429 m² is in the right range. That is a plausibility check, not an accuracy measurement: the common-area figure is my rough estimate.

Scale check: the sheet draws turning circles labelled 2.50 m and 3.00 m. Circle detection found diameters of 145-147 px; a 2.50 m circle should be 142 px at 1:50, so the scale is consistent to about 3%. Not rigorous (the detector also picks up door swings).

## What went wrong

1. **False interior outside the building.** The title block, legend table and margins are painted as rooms. The model needs the building region from outside: a user-drawn rectangle or a detected plot outline.
2. **Sensitive to input size** (±5% here). The model saw walls ~3 px wide in training; on an A1 sheet the right size depends on how thick walls are drawn. Needs tiling or a multi-scale rule.
3. **No doors, windows or room types.** Quantities in units (doors, windows) cannot be counted yet.
4. **Per-dwelling area was not measured**: that needs the dwelling outlines, which this test did not extract. The check above is for the whole floor only.

## What this does and does not show

- ✅ A model trained on Finnish scans transfers, at least roughly, to a clean Spanish CAD plan of a different style and size.
- ❌ It does not show accuracy: there is one sheet, the reference total has an estimated part, and the crop was chosen by hand.
- Next test that would mean something: several Spanish plans, with dwelling outlines drawn so each printed area can be compared one to one.
