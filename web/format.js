// Text helpers shared by the map, the shortlist and the report. Plain JS, no build step.

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
function residualText(r) {
  if (!r) return "–";
  if (!r.eur) return `not computed (${r.withheld_reason})`;
  const left = r.excluded.length ? `; before ${r.excluded.join(", ")}` : "";
  return `${kEur(r.eur.pessimistic)} / ${kEur(r.eur.base)} / ${kEur(r.eur.optimistic)} ` +
    `(pessimistic / base / optimistic; inputs assumed${left})`;
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

// Base-case residual summed over the routes that have a number. A route with none is left out,
// not counted as 0.
function baseResidual(p) {
  const parts = [p.residual_2bed?.eur?.base, p.attic?.residual_2bed?.eur?.base];
  const known = parts.filter((v) => v !== null && v !== undefined);
  return known.length ? known.reduce((a, b) => a + b, 0) : null;
}
