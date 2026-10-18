// Buildable Land: the workspace. A ranked list (left), the map (centre), an inspector (right).
// Static client: reads data/parcels.geojson, data/screening.json, data/summary.json.
// No build step, no framework: one file you can read top to bottom. Helpers are in format.js.

const BASEMAP = "https://tiles.openfreemap.org/styles/positron"; // free, no API key
const ORTHO_TILES =
  "https://www.ign.es/wmts/pnoa-ma?request=GetTile&service=WMTS&version=1.0.0" +
  "&layer=OI.OrthoimageCoverage&style=default&format=image/jpeg" +
  "&tilematrixset=GoogleMapsCompatible&tilematrix={z}&tilerow={y}&tilecol={x}";
const FLOOR_H = 3; // metres, for the 3D extrusion only
const PAGE = 200; // list rows rendered at a time

// Plan-view classes (what the plan sets aside). All colours come from tokens.css (ADR 0007).
const CLASSES = {
  plan_gap: { label: "Room under the plan", color: null }, // coloured by floors, see RAMP
  at_limit: { label: "At or above the plan height", color: token("--class-at-limit") },
  protected: { label: "Protected by the plan", color: token("--class-protected") },
  public_use: { label: "Public use (not a target)", color: token("--class-public-use") },
  open: { label: "Open space in the plan", color: token("--class-open") },
  no_plan: { label: "No plan height found", color: token("--class-no-plan") },
};
const USES = {
  "1_residential": "Residential", "4_1_office": "Office", "4_2_retail": "Retail",
  "3_industrial": "Industrial", "4_3_publicServices": "Public services",
  "2_agriculture": "Agriculture",
};
const RAMP = [token("--ramp-0"), 1, token("--ramp-1"), 2, token("--ramp-2"), 3, token("--ramp-3"), 4, token("--ramp-4")];

// Candidate kinds: three hues checked for colour-blind separation. The inspector also says it in words.
const CAND = {
  rooftop: { color: token("--data-rooftop"), label: "Rooftop addition", short: "Rooftop", long: "Rooftop addition (1–2 floors, up to the plan)" },
  attic: { color: token("--data-attic"), label: "Penthouse (ático)", short: "Ático", long: "Penthouse (ático) only" },
  redevelopment: { color: token("--data-redevelopment"), label: "Redevelopment", short: "Redevelop.", long: "Redevelopment (3+ floors: not a rooftop)" },
  other: { color: token("--data-other"), label: "Other use", short: "Other use", long: "Industrial, retail, office or unknown use: shown, not counted" },
};
const CAND_REST = token("--data-rest");
const SELECTED = token("--data-selected");

const $ = (id) => document.getElementById(id);
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const map = new maplibregl.Map({
  container: "map", style: BASEMAP, center: [-0.376, 39.462], zoom: 15, pitch: 40, hash: false,
});
map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");

// ---------------------------------------------------------------- state
let summary = null;
let screening = null; // optional: data/screening.json, from plan-to-cost
let lookup = {}; // refcat -> feature properties
let features = {}; // refcat -> feature
let view = "street"; // "candidates" with a screening, "plan" with plan columns
let selected = null;
let tab = "summary";
let enabled = new Set(["rooftop", "attic", "redevelopment"]); // shown by default; "other use" is opt-in
let rows = []; // candidate rows, best first
let shown = 0;

// ---------------------------------------------------------------- what is on the map
function colorExpr() {
  const floors = (prop) => ["step", ["coalesce", ["get", prop], 0], ...RAMP];
  let base;
  if (view === "candidates")
    base = ["match", ["get", "cand"],
      ...CAND_ORDER.filter((k) => enabled.has(k)).flatMap((k) => [k, CAND[k].color]), CAND_REST];
  else if (view === "plan")
    base = ["match", ["get", "gap_class"],
      ...Object.entries(CLASSES).filter(([, c]) => c.color).flatMap(([k, c]) => [k, c.color]),
      floors("plan_gap_floors")];
  else base = floors("gap_floors");
  // A parcel has several parts, so selection compares the refcat instead of using feature state
  // (only the main part: that is where an addition would go)
  return ["case", ["all", ["==", ["get", "refcat"], selected ?? ""], ["==", ["get", "main"], true]], SELECTED, base];
}

function applyView() {
  if (map.getLayer("parcels-3d"))
    map.setPaintProperty("parcels-3d", "fill-extrusion-color", colorExpr());
  for (const b of $("view-switch").querySelectorAll("button"))
    b.setAttribute("aria-pressed", String(b.dataset.view === view));

  const dot = (color, text) => `<li><i style="background:${color}"></i>${text}</li>`;
  const chips = $("legend-classes");
  $("legend-ramp").hidden = view === "candidates";
  if (view === "candidates") {
    $("legend-title").textContent = "Rooftop candidates";
    const n = (k) => Object.values(screening.parcels).filter((p) => candidateClass(p) === k).length;
    chips.innerHTML = CAND_ORDER.map((k) => dot(CAND[k].color, `${CAND[k].long} · ${fmt(n(k))}`)).join("") +
      dot(CAND_REST, "Nothing fits, or not screened");
  } else if (view === "plan") {
    $("legend-title").textContent = "Room under the plan (floors)";
    chips.innerHTML = Object.entries(CLASSES).filter(([, c]) => c.color)
      .map(([k, c]) => dot(c.color, `${c.label}${summary.plan_by_class?.[k] != null ? ` · ${fmt(summary.plan_by_class[k])}` : ""}`)).join("");
  } else {
    $("legend-title").textContent = "Missing floors vs. the street";
    chips.innerHTML = "";
  }
  chips.hidden = !chips.innerHTML;
}

// ---------------------------------------------------------------- the ranked list (left)
function buildRows() {
  rows = [];
  for (const [ref, p] of Object.entries(screening.parcels)) {
    const cls = candidateClass(p);
    if (!cls) continue;
    const range = rangeOf(routesOf(p, cls));
    rows.push({ ref, p, cls, range, base: range?.base ?? -Infinity });
  }
  rows.sort((a, b) => CAND_ORDER.indexOf(a.cls) - CAND_ORDER.indexOf(b.cls) || b.base - a.base);
}

function renderKpis() {
  if (!screening) {
    const s = summary;
    $("kpis").innerHTML = `<div class="kpi"><b>${fmt(s.n_parcels_with_plan_gap ?? s.n_parcels_with_gap)}</b><small>parcels with room</small></div>` +
      `<div class="kpi"><b>${fmt(s.total_plan_gap_m2 ?? s.total_gap_m2)}</b><small>m² of room</small></div>`;
    return;
  }
  const t = candidateTotals(screening);
  $("kpis").innerHTML =
    `<div class="kpi"><b>${fmt(t.parcels)}</b><small>rooftop candidates</small></div>` +
    `<div class="kpi"><b>${fmt(t.homes)}</b><small>two-bed homes on top</small></div>` +
    `<div class="kpi"><b>${kEur(t.eur.base)}</b><small>air-rights capacity, base · ${prov("assumed")}<br>${kEur(t.eur.pessimistic)} to ${kEur(t.eur.optimistic)}</small></div>`;
}

function renderFilters() {
  $("filters").innerHTML = CAND_ORDER.map((k) => {
    const n = rows.filter((r) => r.cls === k).length;
    return `<button type="button" class="chip-btn" data-kind="${k}" aria-pressed="${enabled.has(k)}"><i style="background:${CAND[k].color}"></i>${CAND[k].short} <span class="fig muted">${fmt(n)}</span></button>`;
  }).join("");
}

function visibleRows() { return rows.filter((r) => enabled.has(r.cls)); }

function renderList(reset = true) {
  const list = visibleRows();
  if (reset) { $("list").innerHTML = ""; shown = 0; }
  // One scale for the whole list, from the 5th percentile of the worst cases to the 95th of the best
  const lows = list.map((r) => r.range?.pessimistic).filter((v) => v != null).sort((a, b) => a - b);
  const highs = list.map((r) => r.range?.optimistic).filter((v) => v != null).sort((a, b) => a - b);
  const lo = Math.min(lows[Math.floor(lows.length * 0.05)] ?? -1, -1);
  const hi = Math.max(highs[Math.floor(highs.length * 0.95)] ?? 1, 1);
  const html = list.slice(shown, shown + PAGE).map(({ ref, p, cls, range }) => {
    const homes = routesOf(p, cls).map((r) => r.homes_2bed).join(" + ");
    const q = lookup[ref] ?? {};
    return `<li class="row" role="option" tabindex="-1" data-ref="${ref}" aria-selected="${ref === selected}">` +
      `<span class="dot" style="background:${CAND[cls].color}"></span>` +
      `<div><span class="ref fig">${ref}</span><span class="sub">${fmt(q.floors)}→${fmt(q.plan_floors)} floors · ${homes} homes</span></div>` +
      `<div><div class="eur fig ${range && range.base < 0 ? "neg" : ""}">${range ? kEur(range.base) : "–"}</div>${rangeBar(range, lo, hi, 96, 12)}</div></li>`;
  }).join("");
  $("list").insertAdjacentHTML("beforeend", html);
  shown = Math.min(shown + PAGE, list.length);
  $("list").querySelector(".list-more")?.remove();
  if (shown < list.length)
    $("list").insertAdjacentHTML("beforeend", `<li class="list-more"><button class="btn" type="button">Show ${fmt(Math.min(PAGE, list.length - shown))} more of ${fmt(list.length - shown)}</button></li>`);
  if (!list.length) $("list").innerHTML = `<li class="row"><span></span><span class="muted">No parcels of these kinds.</span></li>`;
  const t = candidateTotals(screening);
  $("rail-foot").innerHTML = `Residential buildings only. Listed apart and not counted: ${fmt(t.redev)} redevelopment (3+ floors) and ${fmt(t.other)} of other use. ` +
    `Generated ${screening.generated_at.slice(0, 10)} from Catastro, PNOA LiDAR and the city plan. A screening, not a design, valuation or permit. <a href="${withArea("method.html")}">Method and limits</a>.`;
}

// ---------------------------------------------------------------- the inspector (right)
const KIND_NO = {
  protected: "Protected by the plan: not a candidate.",
  public_use: "Public use: not a candidate.",
  open: "Open space in the plan: nothing can be built.",
  no_plan: "No plan height found: not screened.",
  at_limit: "Already at or above the plan's height; a penthouse would be the only option and none fits.",
};

function verdictText(p, sp) {
  if (!sp) return KIND_NO[p.gap_class] ?? "Not screened.";
  const parts = [];
  if (sp.added_floors > 0 && sp.homes_2bed > 0)
    parts.push(`${fmt(sp.homes_2bed)} two-bed homes on ${fmt(sp.added_floors)} added floor${sp.added_floors > 1 ? "s" : ""}`);
  if (sp.attic?.homes_2bed > 0) parts.push(`${fmt(sp.attic.homes_2bed)} in a penthouse (ático)`);
  if (!parts.length) return "Screened, but no home fits: floor area or free facade is too small.";
  const kind = candidateClass(sp);
  const redev = kind === "redevelopment"
    ? " This adds more floors than an existing building usually carries: redevelopment, not a rooftop."
    : kind === "other"
      ? ` Catastro use is ${(USES[sp.use] ?? "unknown").toLowerCase()}, not residential: not counted as a rooftop candidate.`
      : "";
  return parts.join(" and ") + "." + redev;
}

const inputValue = (i, v) => (v == null ? "?" : i.unit.includes("share") ? `${Math.round(v * 100)}%` : fmt(v));

function panelSummary(p, sp, cls) {
  const routes = sp ? routesOf(sp, cls ?? candidateClass(sp)) : [];
  const range = routes.length ? rangeOf(routes) : null;
  const homes = routes.reduce((t, r) => t + r.homes_2bed, 0);
  const lo = range ? Math.min(range.pessimistic, 0) * 1.15 : 0;
  const hi = range ? Math.max(range.optimistic, 0) * 1.15 : 1;
  let html = "";
  if (range) {
    html += `<div class="big"><div><b>${fmt(homes)}</b><small>two-bed homes</small></div>` +
      `<div><b class="${range.base < 0 ? "neg" : ""}">${kEur(range.base)}</b><small>base case · ${prov("assumed")}</small></div></div>` +
      `<div class="range-block"><div class="overline">What the homes could pay for the air rights</div>` +
      `${rangeBar(range, lo, hi, 340, 20)}<div class="axis fig"><span>${kEur(range.pessimistic)}</span><span>${kEur(range.base)}</span><span>${kEur(range.optimistic)}</span></div>` +
      `<div class="axis"><span>pessimistic</span><span>base</span><span>optimistic</span></div></div>` +
      `<p class="note">Before structural reinforcement, which has no source yet. It is the shared pot for reinforcement, any rooftop premium and the payment to the owners.</p>`;
  }
  html += `<div><div class="overline" style="margin-bottom:var(--size-2)">Today and the plan</div><dl class="facts">` +
    `<dt>Floors today (Catastro)</dt><dd>${fmt(p.floors)}</dd>` +
    `<dt>Plan height, ground floor included</dt><dd>${p.plan_floors == null ? "–" : fmt(p.plan_floors)}</dd>` +
    `<dt>Room under the plan</dt><dd>${p.plan_gap_floors == null ? "–" : `${fmt(p.plan_gap_floors)} floors · ${fmt(p.plan_gap_m2, " m²")}`}</dd>` +
    `<dt>Measured height (LiDAR)</dt><dd>${p.lidar_height_m == null ? "–" : `${p.lidar_height_m.toFixed(1)} m · ${p.lidar_confidence}`}</dd>` +
    `<dt>Use (Catastro)</dt><dd>${USES[p.current_use] ?? "–"}</dd>` +
    `<dt>Status in the plan</dt><dd>${CLASSES[p.gap_class]?.label ?? "–"}</dd></dl></div>`;
  if (sp) {
    const row = (name, r) => r && r.homes_2bed != null && !(r === sp && !(sp.added_floors > 0))
      ? `<tr><td>${name}</td><td>${fmt(r.homes_2bed)}</td><td>${fmt(r.homes_1bed)}</td><td>${r.residual_2bed?.eur ? kEur(r.residual_2bed.eur.base) : "–"}</td></tr>` : "";
    const up = row("Up to the plan's height", sp);
    const at = sp.attic?.homes_2bed != null ? row("Penthouse (ático)", sp.attic) : "";
    if (up || at)
      html += `<div><div class="overline" style="margin-bottom:var(--size-2)">Routes</div><table class="mini"><thead><tr><th>Route</th><th>2-bed</th><th>1-bed</th><th>Base</th></tr></thead><tbody>${up}${at}</tbody></table></div>`;
  }
  return html;
}

function panelEconomics(sp) {
  if (!sp) return `<p class="note">Not screened, so there is no economics. ${esc(KIND_NO[(lookup[selected] ?? {}).gap_class] ?? "")}</p>`;
  const sens = screening.sensitivity;
  const b = sens.per_m2_built.base;
  const scen = (r) => r?.eur
    ? ["pessimistic", "base", "optimistic"].map((k) => `<td class="${r.eur[k] < 0 ? "neg" : ""}">${kEur(r.eur[k])}</td>`).join("")
    : `<td colspan="3" class="muted">not computed</td>`;
  const table = (name, r) => r ? `<tr><td>${name}</td>${scen(r.residual_2bed)}</tr>` : "";
  let html = `<div><div class="overline" style="margin-bottom:var(--size-2)">Residual by route, 2-bed homes</div>` +
    `<table class="mini"><thead><tr><th>Route</th><th>Pess.</th><th>Base</th><th>Opt.</th></tr></thead><tbody>` +
    `${sp.added_floors > 0 ? table("Up to the plan's height", sp) : ""}${sp.attic?.homes_2bed != null ? table("Penthouse (ático)", sp.attic) : ""}</tbody></table></div>`;
  html += `<div class="range-block"><div class="overline">What flips the answer, per m² of new floor</div>` +
    `<p style="margin:var(--size-2) 0 0">At base inputs each m² leaves <b class="fig">${fmt(b.residual_per_m2)} €</b>. It reaches zero if the sale price falls ` +
    `<span class="fig">${fmt(sens.inputs["sale price"].base)} → ${fmt(b.breakeven_sale_price)} €/m²</span>, or the hard cost rises ` +
    `<span class="fig">${fmt(sens.inputs["hard cost"].base)} → ${fmt(b.breakeven_hard_cost)} €/m²</span>. Reinforcement, a rooftop premium and any payment to the owners must fit in that ${fmt(b.cost_budget_per_m2)} €/m².</p></div>`;
  const inputs = Object.entries(sens.inputs).map(([name, i]) =>
    `<div class="input"><div class="input-top"><b>${esc(name)}</b>${prov(i.status)}</div>` +
    `<div class="fig input-vals">${inputValue(i, i.pessimistic)} / ${inputValue(i, i.base)} / ${inputValue(i, i.optimistic)} <span class="muted">${esc(i.unit)}</span></div>` +
    `<div class="note">${esc(i.source)}</div></div>`).join("");
  html += `<div><div class="overline" style="margin-bottom:var(--size-2)">Inputs, pessimistic / base / optimistic</div>${inputs}</div>`;
  return html;
}

function panelRules() {
  if (!screening) return `<p class="note">No screening loaded.</p>`;
  const consent = screening.consent.map((c) => {
    const flag = c.what.includes("NOT decided");
    return `<details class="q"><summary><span><b>${esc(c.what)}</b><br>${esc(c.needed)}</span><span>${flag ? '<span class="tag">for a lawyer</span>' : ""}</span></summary>` +
      `<blockquote>${esc(c.quote)}<br><i>${esc(c.clause)}</i></blockquote></details>`;
  }).join("");
  return `<div><div class="overline" style="margin-bottom:var(--size-2)">Who must agree (Ley de Propiedad Horizontal)</div>${consent}</div>` +
    `<div class="warn">Whether adding floors needs unanimity is not decided here. It depends on the building's title and on case law.</div>` +
    `<div><div class="overline" style="margin-bottom:var(--size-2)">Not checked</div><ul class="note" style="padding-left:var(--size-4);margin:0">` +
    `${screening.not_checked.map((t) => `<li>${esc(t)}</li>`).join("")}</ul></div>`;
}

function panelSources(p) {
  const rc = p.refcat;
  return `<div><div class="overline" style="margin-bottom:var(--size-2)">Where each number comes from</div><dl class="facts">` +
    `<dt>Floors, use, footprint</dt><dd>Catastro INSPIRE</dd>` +
    `<dt>Heights</dt><dd>PNOA LiDAR · ${p.lidar_confidence ?? "–"}</dd>` +
    `<dt>Plan height and zone</dt><dd>València PGOU</dd>` +
    `<dt>Consent rules</dt><dd>Ley 49/1960</dd>` +
    `<dt>Prices and costs</dt><dd>assumed</dd></dl></div>` +
    `<p class="note">The plan's own text: floors count the ground floor (art. 5.33); a penthouse is allowed above the cornice, set back 4 m from the street (art. 6.19.5). Method and limits are on the <a href="${withArea("method.html")}">Method</a> page.</p>` +
    `<div style="display:flex;gap:var(--size-2);flex-wrap:wrap"><a class="btn" target="_blank" rel="noopener" href="https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCListaBienes.aspx?rc1=${rc.slice(0, 7)}&rc2=${rc.slice(7, 14)}">Open in Catastro ↗</a>` +
    `<button class="btn" type="button" id="copy-link">Copy link</button></div>`;
}

const TABS = [["summary", "Summary"], ["economics", "Economics"], ["rules", "Rules"], ["sources", "Sources"]];

function renderInspector() {
  if (!selected) return;
  const p = lookup[selected];
  const sp = screening?.parcels?.[selected];
  const cls = sp ? candidateClass(sp) : null;
  const type = cls ? `<span class="insp-type"><i style="background:${CAND[cls].color}"></i>${CAND[cls].label}</span>`
    : `<span class="insp-type">${CLASSES[p.gap_class]?.label ?? ""}</span>`;
  const body = { summary: () => panelSummary(p, sp, cls), economics: () => panelEconomics(sp), rules: panelRules, sources: () => panelSources(p) }[tab]();
  $("inspector").hidden = false;
  $("inspector").innerHTML =
    `<div class="insp-head"><div class="insp-title"><div><h2>${selected}</h2>${type}</div>` +
    `<button class="icon-btn" id="insp-close" type="button" aria-label="Close (Esc)">×</button></div>` +
    `${screening ? `<p class="verdict">${esc(verdictText(p, sp))}</p>` : ""}</div>` +
    `<div class="tabs" role="tablist">${TABS.map(([k, t]) => `<button role="tab" type="button" data-tab="${k}" aria-selected="${k === tab}">${t}</button>`).join("")}</div>` +
    `<div class="panel" role="tabpanel">${body}</div>` +
    `<div class="insp-foot">${sp ? `<a class="btn primary" target="_blank" rel="noopener" href="${withArea(`report.html?ref=${selected}`)}">One-page report →</a>` : ""}` +
    `<button class="btn" type="button" id="copy-link-foot">Copy link</button></div>`;
  $("inspector").scrollTop = 0;
}

// ---------------------------------------------------------------- selecting
function select(ref, { fly = false } = {}) {
  if (!lookup[ref]) return;
  selected = ref;
  applyView();
  renderInspector();
  history.replaceState(null, "", `#rc=${encodeURIComponent(ref)}`);
  for (const li of $("list").querySelectorAll(".row[data-ref]"))
    li.setAttribute("aria-selected", String(li.dataset.ref === ref));
  $("list").querySelector(`.row[data-ref="${ref}"]`)?.scrollIntoView({ block: "nearest" });
  if (window.innerWidth <= 900) window.scrollTo({ top: 0, behavior: "smooth" }); // the map is above the list
  if (fly && features[ref]) {
    const [minx, miny, maxx, maxy] = bbox(features[ref].geometry);
    const wide = window.innerWidth > 900;
    map.fitBounds([minx, miny, maxx, maxy], {
      padding: wide ? { top: 80, bottom: 80, left: 60, right: 460 } : 60, maxZoom: 18.5, duration: 700,
    });
  }
}

function deselect() {
  selected = null;
  applyView();
  $("inspector").hidden = true;
  for (const li of $("list").querySelectorAll('.row[aria-selected="true"]')) li.setAttribute("aria-selected", "false");
  history.replaceState(null, "", location.pathname + location.search);
}

function bbox(geom) {
  const pts = geom.type === "Polygon" ? geom.coordinates.flat() : geom.coordinates.flat(2);
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

// ---------------------------------------------------------------- loading
async function load() {
  const [summ, parcels] = await Promise.all([
    fetch(DATA + "summary.json").then((r) => r.json()),
    fetch(DATA + "parcels.geojson").then((r) => r.json()),
  ]);
  summary = summ;
  screening = await fetch(DATA + "screening.json").then((r) => (r.ok ? r.json() : null)).catch(() => null);
  for (const f of parcels.features) { lookup[f.properties.refcat] = f.properties; features[f.properties.refcat] = f; }
  if (summary.plan_by_class) view = "plan";
  if (screening) { view = "candidates"; buildRows(); }

  // The 3D layer draws building parts, each at its own height (a parcel outline would draw a small
  // tower on a big plot as a giant slab). Without parts.geojson it falls back to parcel outlines.
  const partsFC = await fetch(DATA + "parts.geojson").then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const layerFC = partsFC ?? parcels;
  for (const f of layerFC.features) {
    const ref = f.properties.refcat, q = lookup[ref] ?? {};
    f.properties.gap_class = q.gap_class;
    f.properties.plan_gap_floors = q.plan_gap_floors;
    f.properties.gap_floors = q.gap_floors;
    f.properties.floors = partsFC ? f.properties.floors_part : q.floors;
    if (!partsFC) f.properties.main = true; // an outline is its own main part
    // only the tallest part of a candidate is coloured: that is where the addition would go
    f.properties.cand = (partsFC ? f.properties.main : true) ? candidateClass(screening?.parcels[ref]) : null;
  }

  document.querySelector(".brand small").textContent = summary.label;
  $("synthetic-banner").hidden = !summary.synthetic;
  $("view-switch").innerHTML =
    (screening ? `<button type="button" data-view="candidates">Candidates</button>` : "") +
    (summary.plan_by_class ? `<button type="button" data-view="plan">City plan</button>` : "") +
    `<button type="button" data-view="street">Vs. street</button>`;
  renderKpis();
  if (screening) { renderFilters(); renderList(); }
  else { $("filters").hidden = true; $("rail").querySelector(".list-head").hidden = true; }

  await new Promise((res) => (map.loaded() ? res() : map.once("load", res)));
  map.addSource("ortho", { type: "raster", tiles: [ORTHO_TILES], tileSize: 256, attribution: "PNOA © IGN" });
  map.addLayer({ id: "ortho", type: "raster", source: "ortho", layout: { visibility: "none" } });
  map.addSource("parcels", { type: "geojson", data: layerFC });
  map.addLayer({
    id: "parcels-3d", type: "fill-extrusion", source: "parcels",
    paint: {
      "fill-extrusion-height": ["*", ["coalesce", ["get", "floors"], 0], FLOOR_H],
      "fill-extrusion-color": colorExpr(),
      "fill-extrusion-opacity": 0.9,
    },
  });
  applyView();
  map.fitBounds(summary.bounds_wgs84, { padding: { top: 70, bottom: 70, left: 40, right: 40 }, duration: 0 });

  map.on("click", "parcels-3d", (e) => select(e.features[0].properties.refcat));
  map.on("mouseenter", "parcels-3d", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "parcels-3d", () => (map.getCanvas().style.cursor = ""));

  // Shareable parcel links: #rc=<refcat>
  const rc = new URLSearchParams(location.hash.slice(1)).get("rc");
  if (rc && lookup[rc]) select(rc, { fly: true });
}

// ---------------------------------------------------------------- events
$("view-switch").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-view]");
  if (!b) return;
  view = b.dataset.view;
  applyView();
});

$("filters").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-kind]");
  if (!b) return;
  const k = b.dataset.kind;
  enabled.has(k) ? enabled.delete(k) : enabled.add(k);
  b.setAttribute("aria-pressed", String(enabled.has(k)));
  renderList();
  applyView();
});

$("list").addEventListener("click", (e) => {
  if (e.target.closest(".list-more")) return renderList(false);
  const li = e.target.closest(".row[data-ref]");
  if (li) select(li.dataset.ref, { fly: true });
});

$("inspector").addEventListener("click", async (e) => {
  const t = e.target.closest("[data-tab]");
  if (t) { tab = t.dataset.tab; return renderInspector(); }
  if (e.target.closest("#insp-close")) return deselect();
  const copy = e.target.closest("#copy-link, #copy-link-foot");
  if (copy) {
    await navigator.clipboard.writeText(location.href);
    const old = copy.textContent; copy.textContent = "Copied";
    setTimeout(() => (copy.textContent = old), 1500);
  }
});

$("toggle-ortho").addEventListener("change", (e) =>
  map.setLayoutProperty("ortho", "visibility", e.target.checked ? "visible" : "none"));

// Search by cadastral reference: Enter selects the first parcel that contains the text
$("search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $("search").value.trim().toUpperCase();
  if (q.length < 4) return;
  const hit = Object.keys(lookup).find((ref) => ref === q) ?? Object.keys(lookup).find((ref) => ref.includes(q));
  $("search").setCustomValidity(hit ? "" : "No parcel with that reference in this area");
  if (hit) select(hit, { fly: true }); else $("search").reportValidity();
});

// Keyboard: "/" finds, Esc closes, arrows (or j/k) walk the list
document.addEventListener("keydown", (e) => {
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName);
  if (e.key === "/" && !typing) { e.preventDefault(); $("search").focus(); }
  else if (e.key === "Escape") { if (typing) document.activeElement.blur(); else if (selected) deselect(); }
  else if (!typing && ["ArrowDown", "ArrowUp", "j", "k"].includes(e.key) && screening) {
    const refs = visibleRows().map((r) => r.ref);
    if (!refs.length) return;
    const i = refs.indexOf(selected);
    const next = e.key === "ArrowDown" || e.key === "j" ? Math.min(i + 1, refs.length - 1) : Math.max(i - 1, 0);
    e.preventDefault();
    select(refs[i === -1 ? 0 : next], { fly: true });
  }
});

load().catch((err) => {
  console.error(err);
  document.querySelector(".brand small").textContent = "Could not load data/. Run `make sample` or `make run`.";
});
