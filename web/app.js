// Buildable Land Map — static client. Reads data/parcels.geojson + data/summary.json.
// No build step, no framework: one file you can read top to bottom.

const BASEMAP = "https://tiles.openfreemap.org/styles/positron"; // free, no API key
const ORTHO_TILES =
  "https://www.ign.es/wmts/pnoa-ma?request=GetTile&service=WMTS&version=1.0.0" +
  "&layer=OI.OrthoimageCoverage&style=default&format=image/jpeg" +
  "&tilematrixset=GoogleMapsCompatible&tilematrix={z}&tilerow={y}&tilecol={x}";
const FLOOR_H = 3; // metres, for the 3D extrusion only

// Colours for parcels the plan view sets aside, and the reason shown in the panel.
const CLASSES = {
  plan_gap: { label: "Room under the plan", color: null }, // coloured by floors, see RAMP
  at_limit: { label: "At or above the plan height", color: "#cfcac0" },
  protected: { label: "Protected by the plan", color: "#8da0cb" },
  public_use: { label: "Public use (not a target)", color: "#b9a7d6" },
  open: { label: "Open space in the plan", color: "#a8d5a2" },
  no_plan: { label: "No plan height found", color: "#e9e5db" },
};
const USES = {
  "1_residential": "Residential", "4_1_office": "Office", "4_2_retail": "Retail",
  "3_industrial": "Industrial", "4_3_publicServices": "Public services",
  "2_agriculture": "Agriculture",
};
const RAMP = ["#cfcac0", 1, "#f6b26b", 2, "#e8833a", 3, "#c2410c", 4, "#7c1d06"];

// "Rooftop candidates" view: three kinds of result, plus everything else muted. The three hues
// were checked for colour-blind separation; the panel also says the kind in words.
const CAND = {
  rooftop: { color: "#c2410c", label: "Rooftop addition (1–2 floors, up to the plan)" },
  attic: { color: "#0891b2", label: "Penthouse (ático) only" },
  redevelopment: { color: "#7c3aed", label: "Redevelopment (3+ floors: not a rooftop)" },
};
const CAND_REST = "#e4e0d6";
const SELECTED = "#111827";

const $ = (id) => document.getElementById(id);

const map = new maplibregl.Map({
  container: "map",
  style: BASEMAP,
  center: [-3.7, 40.42],
  zoom: 15,
  pitch: 45,
  hash: false,
});
map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");

let selected = null;
let summary = null;
let lookup = {}; // refcat -> feature properties
let screening = null; // optional: data/screening.json, from plan-to-cost
let view = "street"; // "plan" with plan columns, "candidates" when a screening is loaded

// Parcel colour for the current view. The selected parcel is always near-black.
function colorExpr() {
  const floors = (prop) => ["step", ["coalesce", ["get", prop], 0], ...RAMP];
  let base;
  if (view === "candidates")
    base = ["match", ["get", "cand"],
      ...Object.entries(CAND).flatMap(([k, c]) => [k, c.color]), CAND_REST];
  else if (view === "plan")
    base = ["match", ["get", "gap_class"],
      ...Object.entries(CLASSES).filter(([, c]) => c.color).flatMap(([k, c]) => [k, c.color]),
      floors("plan_gap_floors")];
  else base = floors("gap_floors");
  return ["case", ["boolean", ["feature-state", "selected"], false], SELECTED, base];
}

const card = (big, label, small = "") =>
  `<div><span>${big}</span><label>${label}</label>${small ? `<small>${small}</small>` : ""}</div>`;

function applyView() {
  if (map.getLayer("parcels-3d"))
    map.setPaintProperty("parcels-3d", "fill-extrusion-color", colorExpr());
  const chips = $("legend-classes");
  $("legend-ramp").hidden = view === "candidates";
  const dot = (color, text) => `<li><i style="background:${color}"></i>${text}</li>`;

  if (view === "candidates") {
    const t = candidateTotals(screening);
    const eur = t.eur;
    $("cards").innerHTML =
      card(fmt(t.parcels), "parcels where a rooftop addition fits") +
      card(fmt(t.homes), "two-bedroom homes on top") +
      card(kEur(eur.base), "most that could be paid for the air rights, base case",
        `range ${kEur(eur.pessimistic)} to ${kEur(eur.optimistic)}`);
    $("legend-title").textContent = "Rooftop candidates";
    const n = (k) => Object.values(screening.parcels).filter((p) => candidateClass(p) === k).length;
    chips.innerHTML =
      Object.entries(CAND).map(([k, c]) => dot(c.color, `${c.label} (${n(k)})`)).join("") +
      dot(CAND_REST, "Nothing fits, or not screened");
  } else if (view === "plan") {
    $("cards").innerHTML =
      card(fmt(summary.total_plan_gap_m2), "m² of room under the plan") +
      card(`${summary.n_parcels_with_plan_gap} / ${summary.n_parcels}`, "parcels with room under the plan");
    $("legend-title").textContent = "Room under the plan (floors)";
    chips.innerHTML = Object.entries(CLASSES).filter(([, c]) => c.color)
      .map(([k, c]) => dot(c.color, `${c.label}${summary.plan_by_class?.[k] != null ? ` (${summary.plan_by_class[k]})` : ""}`))
      .join("");
  } else {
    $("cards").innerHTML =
      card(fmt(summary.total_gap_m2), "m² missing floor area") +
      card(`${summary.n_parcels_with_gap} / ${summary.n_parcels}`, "parcels below street height");
    $("legend-title").textContent = "Missing floors vs. street";
    chips.innerHTML = "";
  }
  chips.hidden = !chips.innerHTML;
  // Street rows only make sense in the street view
  for (const id of ["d-dominant", "d-gapf", "d-gapm2"])
    $(id).previousElementSibling.hidden = $(id).hidden = view !== "street";
}

async function load() {
  const [summ, parcels] = await Promise.all([
    fetch(DATA + "summary.json").then((r) => r.json()),
    fetch(DATA + "parcels.geojson").then((r) => r.json()),
  ]);
  summary = summ;
  lookup = Object.fromEntries(parcels.features.map((f) => [f.properties.refcat, f.properties]));
  screening = await fetch(DATA + "screening.json").then((r) => (r.ok ? r.json() : null)).catch(() => null);
  if (summary.plan_by_class) view = "plan";
  if (screening) {
    view = "candidates";
    for (const f of parcels.features)
      f.properties.cand = candidateClass(screening.parcels[f.properties.refcat]);
  }
  $("seg-candidates").hidden = !screening;
  $("seg-plan").hidden = !summary.plan_by_class;
  $("view-toggle").hidden = !(screening || summary.plan_by_class);
  document.querySelector(`input[name="view"][value="${view}"]`).checked = true;
  renderSummary();
  renderScreeningNote();
  await new Promise((res) => (map.loaded() ? res() : map.once("load", res)));

  map.addSource("ortho", { type: "raster", tiles: [ORTHO_TILES], tileSize: 256,
    attribution: "PNOA © IGN" });
  map.addLayer({ id: "ortho", type: "raster", source: "ortho",
    layout: { visibility: "none" } });

  map.addSource("parcels", { type: "geojson", data: parcels, promoteId: "refcat" });
  map.addLayer({
    id: "parcels-3d",
    type: "fill-extrusion",
    source: "parcels",
    paint: {
      "fill-extrusion-height": ["*", ["coalesce", ["get", "floors"], 0], FLOOR_H],
      "fill-extrusion-color": colorExpr(),
      "fill-extrusion-opacity": 0.88,
    },
  });

  applyView();
  map.fitBounds(summary.bounds_wgs84, { padding: 40, duration: 0 });

  map.on("click", "parcels-3d", (e) => select(e.features[0]));
  map.on("mouseenter", "parcels-3d", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "parcels-3d", () => (map.getCanvas().style.cursor = ""));

  // Shareable parcel links: #rc=<refcat>
  const rc = new URLSearchParams(location.hash.slice(1)).get("rc");
  if (rc) {
    const f = parcels.features.find((x) => x.properties.refcat === rc);
    if (f) {
      select(f);
      const [minx, miny, maxx, maxy] = bbox(f.geometry);
      map.fitBounds([minx, miny, maxx, maxy], { padding: 200, maxZoom: 18, duration: 0 });
    }
  }
}

function renderSummary() {
  const s = summary;
  $("area-label").textContent = s.label;
  $("synthetic-banner").hidden = !s.synthetic;
  $("generated").textContent = `Updated ${s.generated_at.slice(0, 10)}.`;
  $("tab-map").href = withArea("index.html");
  $("tab-list").href = withArea("shortlist.html");
  $("tab-list").hidden = !screening;
}

function renderSensitivityNote() {
  const b = screening?.sensitivity?.per_m2_built?.base;
  const price = screening?.sensitivity?.inputs?.["sale price"]?.base;
  const hard = screening?.sensitivity?.inputs?.["hard cost"]?.base;
  if (!b) return;
  $("sens-note").hidden = false;
  $("sens-note").textContent =
    `What flips the answer: at base inputs each m² of new floor leaves ${fmt(b.residual_per_m2)} €. That reaches zero if ` +
    `the sale price falls from ${fmt(price)} to ${fmt(b.breakeven_sale_price)} €/m², or the hard cost rises from ` +
    `${fmt(hard)} to ${fmt(b.breakeven_hard_cost)} €/m². Structural reinforcement, a rooftop premium and any ` +
    `payment to the owners all have to fit inside that ${fmt(b.cost_budget_per_m2)} €/m². The inputs are assumed.`;
}

function renderScreeningNote() {
  if (!screening) return;
  renderSensitivityNote();
  const t = candidateTotals(screening);
  $("screen-note").hidden = false;
  $("screen-note").textContent =
    `Screening result: ${fmt(t.homes)} two-bedroom homes on ${fmt(t.parcels)} parcels, by adding 1–2 floors ` +
    `up to the city plan's height or a penthouse (ático) set back 4 m from the street. A further ` +
    `${fmt(t.redev)} parcels could add 3+ floors, which is redevelopment and is not counted. ` +
    `Limited by floor area and free facade only. Adding floors needs 3/5 of the owners holding 3/5 of the ` +
    `quotas (LPH art. 17.4); whether it needs unanimity is for a lawyer. Structure, the existing stair, ` +
    `fire safety and permits are not checked.`;
}

function screeningText(refcat) {
  const r = screening?.parcels?.[refcat];
  if (!r) return "–";
  const lim = (l) => (l === "facade" ? "limited by facade" : l === "area" ? "limited by area" : "");
  return `${fmt(r.homes_2bed)} two-bed ${lim(r.limit_2bed)} · ${fmt(r.homes_1bed)} one-bed ` +
    `(${fmt(r.added_floors)} added floor${r.added_floors > 1 ? "s" : ""}, ${fmt(r.free_facade_m)} m free facade)`;
}

const KIND_NO = {
  protected: "Protected by the plan: not a candidate.",
  public_use: "Public use: not a candidate.",
  open: "Open space in the plan: nothing can be built.",
  no_plan: "No plan height found: not screened.",
  at_limit: "Already at or above the plan's height: only a penthouse could fit, and none does here.",
};

// One sentence that answers "what is here?" before any table.
function verdictText(p, sp) {
  if (!sp) return KIND_NO[p.gap_class] ?? "Not screened.";
  const parts = [];
  if (sp.added_floors > 0 && sp.homes_2bed > 0)
    parts.push(`${fmt(sp.homes_2bed)} two-bed homes on ${fmt(sp.added_floors)} added floor${sp.added_floors > 1 ? "s" : ""}`);
  if (sp.attic?.homes_2bed > 0) parts.push(`${fmt(sp.attic.homes_2bed)} in a penthouse (ático)`);
  if (!parts.length) return "Screened, but no home fits (floor area or free facade too small).";
  const redev = candidateClass(sp) === "redevelopment"
    ? " This adds more floors than an existing building usually carries: treat it as redevelopment, not a rooftop." : "";
  return parts.join(" + ") + "." + redev;
}

function select(f, scroll = true) {
  if (selected) map.setFeatureState({ source: "parcels", id: selected }, { selected: false });
  const p = f.properties;
  selected = p.refcat;
  map.setFeatureState({ source: "parcels", id: selected }, { selected: true });

  const sp = screening?.parcels?.[p.refcat];
  $("detail").hidden = false;
  $("d-refcat").textContent = p.refcat;
  $("d-verdict").textContent = screening ? verdictText(p, sp) : "";
  $("d-verdict").hidden = !screening;
  const range = sp && residualRange(sp);
  $("d-money").hidden = !range;
  if (range)
    $("d-money").innerHTML = `Could bear for the air rights: <b class="${range.base < 0 ? "neg" : "pos"}">${kEur(range.base)}</b> base case ` +
      `<span class="muted">(${kEur(range.pessimistic)} to ${kEur(range.optimistic)}; inputs assumed, before structural reinforcement)</span>`;
  $("d-floors").textContent = fmt(p.floors);
  $("d-screen").textContent = screeningText(p.refcat);
  $("d-report").hidden = !sp;
  if (sp) $("d-report").href = withArea(`report.html?ref=${p.refcat}`);
  $("d-resid").textContent = residualText(sp?.residual_2bed, true);
  $("d-attic").textContent = atticText(sp?.attic);
  $("d-attic-resid").textContent = sp?.attic?.residual_2bed ? residualText(sp.attic.residual_2bed, true) : "–";
  for (const id of ["d-screen", "d-resid", "d-attic", "d-attic-resid"])
    $(id).previousElementSibling.hidden = $(id).hidden = !screening;
  $("d-use").textContent = USES[p.current_use] ?? "–";
  $("d-class").textContent = CLASSES[p.gap_class]?.label ?? "–";
  $("d-plan").textContent =
    p.plan_allowed_floors == null ? "–" : `${fmt(p.plan_allowed_floors)} (plan altura ${fmt(p.plan_floors)})`;
  $("d-plangap").textContent = p.plan_gap_floors == null ? "–" : `${fmt(p.plan_gap_floors)} floors, ${fmt(p.plan_gap_m2, " m²")}`;
  for (const id of ["d-use", "d-class", "d-plan", "d-plangap"])
    $(id).previousElementSibling.hidden = $(id).hidden = !summary.plan_by_class;
  $("d-dominant").textContent = fmt(p.dominant_floors);
  $("d-gapf").textContent = fmt(p.gap_floors);
  $("d-gapm2").textContent = fmt(p.gap_m2, " m²");
  for (const id of ["d-dominant", "d-gapf", "d-gapm2"])
    $(id).previousElementSibling.hidden = $(id).hidden = view !== "street";
  $("d-lidar").textContent =
    p.lidar_height_m == null ? "–" : `${p.lidar_height_m.toFixed(1)} m (${p.lidar_confidence})`;
  $("d-catastro").href =
    "https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCListaBienes.aspx" +
    `?rc1=${p.refcat.slice(0, 7)}&rc2=${p.refcat.slice(7, 14)}`;
  history.replaceState(null, "", `#rc=${encodeURIComponent(p.refcat)}`);
  if (scroll) $("panel").scrollTo({ top: 0 }); // the answer is at the top: do not hunt for it
}

function deselect() {
  if (selected) map.setFeatureState({ source: "parcels", id: selected }, { selected: false });
  selected = null;
  $("detail").hidden = true;
  history.replaceState(null, "", location.pathname + location.search);
}

function bbox(geom) {
  const pts = geom.type === "Polygon" ? geom.coordinates.flat() : geom.coordinates.flat(2);
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

$("d-close").addEventListener("click", deselect);
document.addEventListener("keydown", (e) => e.key === "Escape" && selected && deselect());

$("d-share").addEventListener("click", async () => {
  await navigator.clipboard.writeText(location.href);
  $("d-share").textContent = "Copied";
  setTimeout(() => ($("d-share").textContent = "Copy link"), 1500);
});

document.querySelectorAll('input[name="view"]').forEach((r) =>
  r.addEventListener("change", (e) => {
    view = e.target.value;
    applyView();
    if (selected) select({ properties: lookup[selected] }, false); // rows depend on the view
  }));

$("toggle-ortho").addEventListener("change", (e) =>
  map.setLayoutProperty("ortho", "visibility", e.target.checked ? "visible" : "none"));

load().catch((err) => {
  console.error(err);
  $("area-label").textContent = "Could not load data/. Run `make sample` or `make run`.";
});
