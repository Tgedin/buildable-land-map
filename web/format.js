// Helpers shared by the map, the shortlist and the report. Plain JS, no build step.

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
