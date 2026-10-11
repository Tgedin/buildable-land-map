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

const $ = (id) => document.getElementById(id);
const fmt = (n, unit = "") =>
  n === null || n === undefined ? "–" : `${Math.round(n).toLocaleString("es-ES")}${unit}`;

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
let screening = null; // optional: data/screening.json, from plan-to-cost
let view = "street"; // "plan" when the data has plan columns

// Parcel colour for the current view. The selected parcel is always blue.
function colorExpr() {
  const floors = (prop) => ["step", ["coalesce", ["get", prop], 0], ...RAMP];
  const base =
    view === "plan"
      ? ["match", ["get", "gap_class"],
          ...Object.entries(CLASSES).filter(([, c]) => c.color).flatMap(([k, c]) => [k, c.color]),
          floors("plan_gap_floors")]
      : floors("gap_floors");
  return ["case", ["boolean", ["feature-state", "selected"], false], "#1d4ed8", base];
}

function applyView() {
  if (map.getLayer("parcels-3d"))
    map.setPaintProperty("parcels-3d", "fill-extrusion-color", colorExpr());
  const plan = view === "plan";
  $("stat-gap").textContent = fmt(plan ? summary.total_plan_gap_m2 : summary.total_gap_m2);
  $("stat-gap-label").textContent = plan
    ? "m² of room under the plan" : "m² missing floor area";
  $("stat-parcels").textContent =
    `${plan ? summary.n_parcels_with_plan_gap : summary.n_parcels_with_gap} / ${summary.n_parcels}`;
  $("stat-parcels-label").textContent = plan
    ? "parcels with room under the plan" : "parcels below street height";
  $("legend-title").textContent = plan ? "Room under the plan (floors)" : "Missing floors vs. street";
  const chips = $("legend-classes");
  chips.hidden = !plan;
  chips.innerHTML = Object.entries(CLASSES)
    .filter(([, c]) => c.color)
    .map(([k, c]) => `<li><i style="background:${c.color}"></i>${c.label}` +
      `${summary.plan_by_class?.[k] != null ? ` (${summary.plan_by_class[k]})` : ""}</li>`)
    .join("");
}

async function load() {
  const [summ, parcels] = await Promise.all([
    fetch("data/summary.json").then((r) => r.json()),
    fetch("data/parcels.geojson").then((r) => r.json()),
  ]);
  summary = summ;
  screening = await fetch("data/screening.json").then((r) => (r.ok ? r.json() : null)).catch(() => null);
  if (summary.plan_by_class) {
    view = "plan";
    $("view-toggle").hidden = false;
  }
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
}

function renderScreeningNote() {
  if (!screening) return;
  const s = screening.summary;
  $("screen-note").hidden = false;
  $("screen-note").textContent =
    `Screening: up to ${fmt(s.total_homes_2bed)} two-bedroom homes (or ${fmt(s.total_homes_1bed)} ` +
    `one-bedroom) could be added on ${fmt(s.parcels_with_homes_1bed)} parcels. A first filter limited ` +
    `by floor area and free facade; structure, lifts, fire safety, owners' consent and permits are not checked.`;
}

function screeningText(refcat) {
  const r = screening?.parcels?.[refcat];
  if (!r) return "–";
  const lim = (l) => (l === "facade" ? "limited by facade" : l === "area" ? "limited by area" : "");
  return `${fmt(r.homes_2bed)} two-bed ${lim(r.limit_2bed)} · ${fmt(r.homes_1bed)} one-bed ` +
    `(${fmt(r.added_floors)} added floor${r.added_floors > 1 ? "s" : ""}, ${fmt(r.free_facade_m)} m free facade)`;
}

function select(f) {
  if (selected) map.setFeatureState({ source: "parcels", id: selected }, { selected: false });
  const p = f.properties;
  selected = p.refcat;
  map.setFeatureState({ source: "parcels", id: selected }, { selected: true });

  $("detail").hidden = false;
  $("d-refcat").textContent = p.refcat;
  $("d-floors").textContent = fmt(p.floors);
  $("d-screen").textContent = screeningText(p.refcat);
  $("d-screen").previousElementSibling.hidden = $("d-screen").hidden = !screening;
  $("d-use").textContent = USES[p.current_use] ?? "–";
  $("d-class").textContent = CLASSES[p.gap_class]?.label ?? "–";
  $("d-plan").textContent =
    p.plan_allowed_floors == null ? "–" : `${fmt(p.plan_allowed_floors)} (plan altura ${fmt(p.plan_floors)} + 1)`;
  $("d-plangap").textContent = p.plan_gap_floors == null ? "–" : `${fmt(p.plan_gap_floors)} floors, ${fmt(p.plan_gap_m2, " m²")}`;
  for (const id of ["d-use", "d-class", "d-plan", "d-plangap"])
    $(id).previousElementSibling.hidden = $(id).hidden = !summary.plan_by_class;
  $("d-dominant").textContent = fmt(p.dominant_floors);
  $("d-gapf").textContent = fmt(p.gap_floors);
  $("d-gapm2").textContent = fmt(p.gap_m2, " m²");
  $("d-lidar").textContent =
    p.lidar_height_m == null ? "–" : `${p.lidar_height_m.toFixed(1)} m (${p.lidar_confidence})`;
  $("d-catastro").href =
    "https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCListaBienes.aspx" +
    `?rc1=${p.refcat.slice(0, 7)}&rc2=${p.refcat.slice(7, 14)}`;
  history.replaceState(null, "", `#rc=${encodeURIComponent(p.refcat)}`);
}

function bbox(geom) {
  const pts = geom.type === "Polygon" ? geom.coordinates.flat() : geom.coordinates.flat(2);
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

$("d-share").addEventListener("click", async () => {
  await navigator.clipboard.writeText(location.href);
  $("d-share").textContent = "Copied";
  setTimeout(() => ($("d-share").textContent = "Copy link"), 1500);
});

document.querySelectorAll('input[name="view"]').forEach((r) =>
  r.addEventListener("change", (e) => { view = e.target.value; applyView(); }));

$("toggle-ortho").addEventListener("change", (e) =>
  map.setLayoutProperty("ortho", "visibility", e.target.checked ? "visible" : "none"));

load().catch((err) => {
  console.error(err);
  $("area-label").textContent = "Could not load data/. Run `make sample` or `make run`.";
});
