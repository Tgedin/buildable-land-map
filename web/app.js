// Buildable Land Map — static client. Reads data/parcels.geojson + data/summary.json.
// No build step, no framework: one file you can read top to bottom.

const BASEMAP = "https://tiles.openfreemap.org/styles/positron"; // free, no API key
const ORTHO_TILES =
  "https://www.ign.es/wmts/pnoa-ma?request=GetTile&service=WMTS&version=1.0.0" +
  "&layer=OI.OrthoimageCoverage&style=default&format=image/jpeg" +
  "&tilematrixset=GoogleMapsCompatible&tilematrix={z}&tilerow={y}&tilecol={x}";
const FLOOR_H = 3; // metres, for the 3D extrusion only

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

async function load() {
  const [summary, parcels] = await Promise.all([
    fetch("data/summary.json").then((r) => r.json()),
    fetch("data/parcels.geojson").then((r) => r.json()),
  ]);
  renderSummary(summary);
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
      "fill-extrusion-color": [
        "case",
        ["boolean", ["feature-state", "selected"], false], "#1d4ed8",
        ["step", ["coalesce", ["get", "gap_floors"], 0],
          "#cfcac0", 1, "#f6b26b", 2, "#e8833a", 3, "#c2410c", 4, "#7c1d06"],
      ],
      "fill-extrusion-opacity": 0.88,
    },
  });

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

function renderSummary(s) {
  $("area-label").textContent = s.label;
  $("synthetic-banner").hidden = !s.synthetic;
  $("stat-gap").textContent = fmt(s.total_gap_m2);
  $("stat-parcels").textContent = `${s.n_parcels_with_gap} / ${s.n_parcels}`;
  $("generated").textContent = `Updated ${s.generated_at.slice(0, 10)}.`;
}

function select(f) {
  if (selected) map.setFeatureState({ source: "parcels", id: selected }, { selected: false });
  const p = f.properties;
  selected = p.refcat;
  map.setFeatureState({ source: "parcels", id: selected }, { selected: true });

  $("detail").hidden = false;
  $("d-refcat").textContent = p.refcat;
  $("d-floors").textContent = fmt(p.floors);
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

$("toggle-ortho").addEventListener("change", (e) =>
  map.setLayoutProperty("ortho", "visibility", e.target.checked ? "visible" : "none"));

load().catch((err) => {
  console.error(err);
  $("area-label").textContent = "Could not load data/. Run `make sample` or `make run`.";
});
