# Housing AI Roadmap: 12 Months, 5 Deployed Systems

> **Goal:** Better, more beautiful housing that costs less relative to income.
> **Rule:** Every phase ships to **real users, on real data, in production**. A project that runs only on localhost doesn't count.
> **Career target:** FDE (Forward Deployed Engineer) or field presales in physical-world AI, within 12 months.
> **Constraints:** 5–10 h/week (~350 h total), AI-assisted coding, Master in Applied AI running in parallel, cloud credits available.

---

## 0. First Principles

### 0.1 Decompose the goal

```
Housing affordability = Price / Income

Price = Land + Hard costs + Soft costs + Time cost + Margin
        │      │            │            │           │
        │      │            │            │           └─ developer risk premium
        │      │            │            └─ financing interest during delays (permits, construction)
        │      │            └─ design, engineering, licensing, estimation errors
        │      └─ materials + labor (labor = productivity problem)
        └─ scarcity + poor information on what is buildable
```

### 0.2 Where software has leverage

| Cost driver | Root cause | Software lever | Phase |
|---|---|---|---|
| Land | Information asymmetry: nobody knows what is buildable or underused | Open-data analysis of parcels, heights, zoning | P1 |
| Hard costs: estimation | Manual takeoff, errors, contingency padding | Automated quantity takeoff + pricing | P2 |
| Soft costs + time: permits | Non-compliant designs cause review loops and months of delay | Automated code checking before submission | P3 |
| Hard costs: design | Bespoke designs block industrialization | Generative layouts on modular/prefab grids | P4 |
| Hard costs: labor | Poor visibility on site causes rework | Vision-based progress tracking | P5 |

### 0.3 Definition of "real"

Each phase is complete only when it meets all four conditions:

1. **Deployed:** A public URL or an installed tool, not a notebook.
2. **Used:** At least N real external users or a real partner (target per phase below).
3. **Measured:** A usage metric and an accuracy metric are tracked.
4. **Shown:** A public repo, a 3-minute demo video, and a write-up post.

### 0.4 Per-phase operating loop (FDE + presales muscle)

```
Discover ──► Build MVP ──► Deploy ──► Get users ──► Measure ──► Iterate ──► Publish
 5 user       2-3 wks       cloud      outreach      usage +      1 cycle    repo + video
 interviews                 URL                      accuracy                + post
```

**Discovery is mandatory.** Before building, run 5 short conversations with target users: architects, small developers, housing cooperatives, contractors, self-builders. This is your presales skill turned into product discovery.

---

## 1. Phase Overview

```
LAND ──────► COST ──────► COMPLIANCE ──────► DESIGN ──────► BUILD
 P1           P2            P3                 P4             P5
 Oct-Dec      Jan-Mar       Apr-May            Jun-Sep        stretch
 60h          80h           70h                100h (TFM)     optional
```

| Phase | System | Real user | Usage target | Master module |
|---|---|---|---|---|
| P1 | Buildable Land Map | Housing cooperatives, small developers, journalists, citizens | 100 users / 500 parcel lookups | M3 Mining & Viz |
| P2 | Plan-to-Cost Estimator | Small architecture studios, renovating homeowners | 5 studios using it on live projects | M6 Vision |
| P3 | CTE Compliance Checker | Architecture students, small studios | 1 school or 10 studios | M5 NLP/LLM, M9 XAI |
| P4 | Modular Layout Generator | One housing cooperative or developer with a real plot | 1 real plot studied end-to-end | M4 ML/Optimization, M10 TFM |
| P5 | Site Progress Monitor | One small contractor | 1 active site, 8 weeks of data | M6, M7 |

---

## 2. Phases

### P1: Buildable Land Map (Oct–Dec, ~60h)

**First principle:** Land is scarce partly because information about it is scarce. Make underused buildable capacity visible.

**How it works:**
```
Catastro (parcels, buildings, year, use) ─┐
IGN PNOA LiDAR (real heights)            ─┼─► PostGIS ──► buildable gap = allowed − existing volume
Zoning (municipal planning, where open)  ─┤                    │
INE Atlas de renta (income by area)      ─┘                    ▼
                                         affordability index = est. cost per m² × typical unit / median income
                                                               │
                                                               ▼
                                         public web map (MapLibre) + parcel detail page
```

**Stack:** Python, GeoPandas, PDAL (LiDAR), PostGIS, FastAPI, MapLibre GL, deployed on your cloud.

**Real deployment:**
- Start with **one city**, not all of Spain.
- Public URL, shareable parcel links.
- Distribution: housing cooperative networks, local urbanism forums, LinkedIn, local press (data stories).

**Done criteria:**
- [ ] 1 city fully processed, refreshed by a scheduled job
- [ ] LiDAR heights vs Catastro floors validated on 50 sample buildings (error % reported)
- [ ] 100 unique users, analytics in place
- [ ] Write-up: "X m² of unused buildable volume in [city]"

**FDE skills:** Geospatial ETL, messy government data, scheduled pipelines, public deployment.

**Edge cases:** Zoning data is often published only as PDFs or isn't open at all. Start with a simplified rule (current height vs dominant height of the block) and state the limitation explicitly.

---

### P2: Plan-to-Cost Estimator (Jan–Mar, ~80h)

**First principle:** Estimation is manual, so it's slow and padded with contingency. Faster, cheaper estimates mean more design iterations and less risk premium.

**How it works:**
```
Floor plan (PDF/image) ──► vision model: walls, rooms, doors, windows
                       ──► vectorize + scale detection
                       ──► quantities (m² floor, m wall, units of openings)
                       ──► map to BC3 price items (FIEBDC public price base)
                       ──► cost breakdown + cost/m² + editable line items
```

**Stack:** Segmentation model fine-tuned on CubiCasa5k, OpenCV, an LLM for mapping quantities to price items, a BC3 parser, FastAPI + simple web UI.

**Real deployment:**
- Web app where users upload a plan and get an editable estimate.
- **Human-in-the-loop:** The user corrects detected elements, and every correction is logged as training data.
- Recruit 5 small studios or renovation clients from discovery interviews.

**Done criteria:**
- [ ] Detection accuracy reported on a held-out set and on 10 real Spanish plans
- [ ] Estimate vs real budget compared on at least 3 real projects (error %)
- [ ] 5 studios used it on live work
- [ ] Correction-feedback loop stored in the database

**FDE skills:** Vision on messy documents, HITL design, measuring against ground truth from the customer.

**Edge cases:** Hand-drawn or low-resolution plans fail. Add a confidence threshold that falls back to manual input instead of returning a wrong number.

---

### P3: CTE Compliance Checker (Apr–May, ~70h)

**First principle:** Permit delays are a time cost financed at interest. Every review loop caused by non-compliance adds months. Catch issues before submission.

**How it works:**
```
CTE text (DB-SUA, DB-SI, DB-HS) ──► LLM extracts rules ──► human-reviewed rule library (YAML/Python checks)
                                                                   │
Design (IFC model, or P2 output) ──────────────────────────────────┤
                                                                   ▼
                                       check engine ──► report: pass / fail / needs review
                                                         + cited clause + explanation
```

**Stack:** IfcOpenShell, an LLM with structured outputs for rule extraction, a deterministic rule engine (the LLM never makes the final pass/fail decision), report generation.

**Real deployment:**
- Target a small, high-value rule set first: accessibility (DB-SUA) and fire egress distances (DB-SI).
- Partner with one architecture school (students submit projects) or 10 studios.

**Done criteria:**
- [ ] 20+ rules implemented, each with unit tests from real cases
- [ ] Precision and recall measured against an architect's manual review on 10 projects
- [ ] Every result cites the exact CTE clause (explainability, M9)
- [ ] Used by the partner on real submissions

**FDE skills:** LLM + deterministic hybrid systems, explainability, regulated domains.

**Edge cases:** Rules that require interpretation (e.g. "practicable" spaces). Flag these as `needs review` and never auto-pass them.

---

### P4: Modular Layout Generator (Jun–Sep, ~100h, TFM core)

**First principle:** Bespoke design blocks industrialization. Repeating standard components on a modular grid reduces cost, and good proportion and light make the result beautiful, not cheap-looking.

**How it works:**
```
Plot (from P1) + constraints (setbacks, orientation, unit mix, modular grid)
        │
        ▼
optimizer (constraint solver + evolutionary search)
  objectives: usable area ↑, sunlight hours ↑, unique components ↓, cost ↓
        │
        ▼
N candidate layouts ──► P3 compliance check ──► P2 cost model ──► affordability score
        │
        ▼
IFC export + comparison dashboard
```

**Stack:** Shapely, OR-Tools or a genetic algorithm, a sun-path library, IfcOpenShell, plus your P1–P3 services as APIs.

**Real deployment:**
- One real client: a housing cooperative (vivienda cooperativa / cesión de uso) or a small developer with an actual plot.
- Deliverable: a feasibility study they use in a real decision.

**Done criteria:**
- [ ] Full pipeline from plot to compliant, costed layouts in under 10 minutes
- [ ] Generated options reviewed by a licensed architect
- [ ] Used by the partner in a real go/no-go or design decision
- [ ] TFM written around it, including the AI Act / explainability chapter

**FDE skills:** System integration across services, optimization, delivering to a real client.

**Edge cases:** Irregular plots and complex zoning can make the search space explode. Restrict the scope to rectangular or near-rectangular plots in v1.

---

### P5 (Stretch): Site Progress Monitor

**First principle:** Rework and delays on site come from late detection. Weekly visual tracking catches deviations early.

**How it works:**
```
Weekly site photos (phone / 360 camera) ──► detection (elements, machinery, PPE)
                                        ──► compare to planned schedule
                                        ──► deviation report to site manager
```

**Stack:** YOLO-family detector fine-tuned on SODA/MOCS construction datasets plus your own labeled photos, a simple schedule model, an email or WhatsApp report.

**Real deployment:** One small contractor, one active site, 8 weeks. This is literally forward-deployed engineering: on site, with their workflow.

**Done criteria:**
- [ ] 8 weekly reports delivered
- [ ] Site manager feedback logged (useful / not useful per alert)
- [ ] Detection accuracy measured on their own photos

---

## 3. Cross-Cutting Practices

| Practice | Why | How |
|---|---|---|
| **Debug drill** | FDE interviews test reading and fixing code without AI | Once per phase: break something in your own code, fix it unaided, timeboxed |
| **Metrics first** | Shows engineering maturity | Define accuracy + usage metrics before writing code |
| **Customer FAQ** | Presales muscle | Per phase: data residency, security, failure modes, cost per run |
| **Build in public** | Portfolio > CV | 1 repo, tagged release per phase, 3-min video, 1 post |
| **Cost tracking** | Real deployments cost money | Monthly cloud cost per phase in the README |

---

## 4. Master Alignment

| Master module | Phase |
|---|---|
| M2 Programming & environments | P1 (setup, pipelines) |
| M3 Mining, analysis, visualization | P1 |
| M4 Machine learning | P4 (optimization) |
| M5 NLP & LLMs | P3 |
| M6 Computer vision | P2, P5 |
| M7–M8 Applications & use cases | P4, P5 |
| M9 Explainability & regulation | P3, TFM chapter |
| M10 TFM | P4 (integrating P1–P3) |

---

## 5. Risks

- **Scope creep:** P2 and P4 can absorb unlimited hours. Hard-cap each phase and ship what exists.
- **No users:** The biggest risk. That's why discovery comes before build, and why each phase is scoped to one city, one partner or one rule set.
- **Data access:** Zoning and municipal data vary by city. Pick the city for P1 based on data openness, not familiarity.
- **Niche market:** Construction tech hires fewer FDEs. The skills (geospatial, document vision, LLM + rules, on-site deployment) transfer to energy, manufacturing, logistics and defense AI.

---

## 6. End State (Oct 2027)

```
Portfolio:  4–5 deployed systems, real usage numbers, real partner testimonials
Story:      "I took a societal problem, decomposed it from first principles,
             and shipped AI systems that real people used to make real decisions."
Fit:        FDE (physical-world AI) · field presales · ConTech founding engineer
```

---

## 7. Immediate Next Actions

- [ ] Pick the P1 city (criterion: best open zoning + Catastro + LiDAR coverage)
- [ ] Book 5 discovery calls (cooperatives, small developers, architects)
- [ ] Create the repo + cloud project + budget alert
- [ ] Download one LiDAR tile + Catastro buildings for one neighborhood, then render the first map
