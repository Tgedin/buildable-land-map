// Helpers shared by the map, the shortlist and the report. Plain JS, no build step.

// A design token (tokens.css) as authored. The map needs plain sRGB strings, so the data colours
// are hex there; do not read a Radix step directly, it can be a display-p3 value.
const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// Which data folder to read: data/ (default) or data/<area>/ for ?area=<slug>. The slug is
// checked so the query string cannot point a fetch somewhere else.
const AREA = (() => {
  const a = new URLSearchParams(location.search).get("area");
  return a && /^[a-z0-9-]+$/.test(a) ? a : null;
})();
const DATA = AREA ? `data/${AREA}/` : "data/";
const withArea = (href) => (AREA ? `${href}${href.includes("?") ? "&" : "?"}area=${AREA}` : href);

const fmt = (n, unit = "") =>
  n === null || n === undefined ? "–" : `${Math.round(n).toLocaleString("es-ES")}${unit}`;

// Thousands of euros (millions from 1 M), with a real minus sign: −71k €, 14,7 M €.
// es-ES does not group four-digit numbers, so "7040k" would read badly next to "14.692k".
const kEur = (v) => {
  const a = Math.abs(v), sign = v < 0 ? "−" : "";
  return a >= 1e6 ? `${sign}${(a / 1e6).toLocaleString("es-ES", { maximumFractionDigits: 1 })} M €`
                  : `${sign}${fmt(Math.round(a / 1000))}k €`;
};

// Residual value of the added homes: the most a developer could pay owners for the right to
// build. Three scenarios, because the sign depends on prices and costs that are assumed.
function residualText(r, short = false) {
  if (!r) return "–";
  if (!r.eur) return `not computed (${r.withheld_reason})`;
  const range = `${kEur(r.eur.pessimistic)} / ${kEur(r.eur.base)} / ${kEur(r.eur.optimistic)}`;
  if (short) return range; // the caveats are stated once, next to the headline figure
  const left = r.excluded.length ? `; before ${r.excluded.join(", ")}` : "";
  return `${range} (pessimistic / base / optimistic; inputs assumed${left})`;
}

const ATTIC_NO = {
  not_ensanche: "not in the Ensanche zone",
  zone_unknown: "zone not known",
  no_buildable_plan_height: "protected, public use or no plan height",
  floors_unknown: "floor count unknown",
  plan_ground_floor_only: "plan allows only a ground floor here (block interior)",
  plan_over_8_floors: "plan allows more than 8 floors (no ático above 8)",
  already_above_plan: "already above the plan's floors",
};

// Penthouse (ático) allowed above the cornice by PGOU art. 6.19.5, set back 4 m from the facades.
function atticText(a) {
  if (!a) return "–";
  if (a.eligible === false) return `not eligible: ${ATTIC_NO[a.reason] ?? a.reason}`;
  return `${fmt(a.homes_2bed)} two-bed · ${fmt(a.homes_1bed)} one-bed ` +
    `(one floor of ${fmt(a.plate_m2)} m² after the 4 m setback)`;
}

// Residual summed over the routes that have a number, per scenario: {pessimistic, base,
// optimistic}, or null when no route has one. A route with none is left out, not counted as 0.
function residualRange(p) {
  const out = {};
  for (const k of ["pessimistic", "base", "optimistic"]) {
    const parts = [p.residual_2bed?.eur?.[k], p.attic?.residual_2bed?.eur?.[k]].filter((v) => v != null);
    if (!parts.length) return null;
    out[k] = parts.reduce((a, b) => a + b, 0);
  }
  return out;
}

const baseResidual = (p) => residualRange(p)?.base ?? null;

// Which kind of result a screened parcel has, if any. Rooftop wins over ático, which wins over
// redevelopment, because that is the order of how much the thesis cares.
function candidateClass(p) {
  if (!p) return null;
  const up = p.added_floors > 0 && p.homes_2bed > 0;
  if (up && p.kind === "rooftop") return "rooftop";
  if (p.attic?.homes_2bed > 0) return "attic";
  if (up) return "redevelopment";
  return null;
}

// Totals for the rooftop candidates, the same on the map and on the shortlist: the floors route
// only where it is a rooftop, plus every ático. Redevelopment is counted apart, never added in.
function candidateTotals(screening) {
  const t = { parcels: 0, homes: 0, eur: { pessimistic: 0, base: 0, optimistic: 0 }, redev: 0 };
  for (const p of Object.values(screening.parcels)) {
    const cls = candidateClass(p);
    if (cls === "redevelopment") t.redev++;
    if (cls !== "rooftop" && cls !== "attic") continue;
    t.parcels++;
    const routes = [];
    if (p.kind === "rooftop" && p.added_floors > 0 && p.homes_2bed > 0) routes.push(p);
    if (p.attic?.homes_2bed > 0) routes.push(p.attic);
    for (const r of routes) {
      t.homes += r.homes_2bed;
      for (const k of Object.keys(t.eur)) t.eur[k] += r.residual_2bed?.eur?.[k] ?? 0;
    }
  }
  return t;
}
