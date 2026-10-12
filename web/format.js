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
  n === null || n === undefined ? "–"
    : `${Math.round(n).toLocaleString("es-ES", { useGrouping: "always" })}${unit}`;

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

// The routes a candidate row stands for: the floors route (up to the plan's height) only where it
// is a rooftop, plus the ático. A redevelopment row stands for its floors route. Totals, list rows
// and the inspector all use this, so they cannot disagree.
function routesOf(p, cls = candidateClass(p)) {
  const up = p.added_floors > 0 && p.homes_2bed > 0 ? p : null;
  const at = p.attic?.homes_2bed > 0 ? p.attic : null;
  if (cls === "redevelopment") return up ? [up] : [];
  return [p.kind === "rooftop" ? up : null, at].filter(Boolean);
}

// {pessimistic, base, optimistic} summed over routes, or null when none has a number.
function rangeOf(routes) {
  const out = {};
  for (const k of ["pessimistic", "base", "optimistic"]) {
    const parts = routes.map((r) => r.residual_2bed?.eur?.[k]).filter((v) => v != null);
    if (!parts.length) return null;
    out[k] = parts.reduce((a, b) => a + b, 0);
  }
  return out;
}

// Totals for the rooftop candidates, the same on the list and the map. Redevelopment is counted
// apart, never added in.
function candidateTotals(screening) {
  const t = { parcels: 0, homes: 0, eur: { pessimistic: 0, base: 0, optimistic: 0 }, redev: 0 };
  for (const p of Object.values(screening.parcels)) {
    const cls = candidateClass(p);
    if (cls === "redevelopment") t.redev++;
    if (cls !== "rooftop" && cls !== "attic") continue;
    t.parcels++;
    const routes = routesOf(p, cls);
    for (const r of routes) t.homes += r.homes_2bed;
    const range = rangeOf(routes);
    if (range) for (const k of Object.keys(t.eur)) t.eur[k] += range[k];
  }
  return t;
}

// ---------------------------------------------------------------- shared interface pieces

// Provenance: how far to trust a number (the claims ledger of ADR 0005, made visible). It is
// shown next to every figure that rests on an input, so honesty is a feature of the screen.
const PROV = {
  verified: "Checked against a primary source",
  sourced: "From a source we read, not verified at its origin",
  assumed: "Our own estimate: no source found",
};
const prov = (status) => `<span class="prov prov-${status}" title="${PROV[status]}">${status}</span>`;

// A range bar: pessimistic to optimistic on a scale shared by the rows being compared, a tick at
// the base case, a line at zero. Red where the range loses money, green where it earns. Values
// outside the scale are clipped to the edge, never wrapped.
function rangeBar(r, lo, hi, w = 104, h = 14) {
  if (!r) return `<span class="muted">–</span>`;
  const x = (v) => Math.max(0, Math.min(w, ((v - lo) / (hi - lo)) * w));
  const z = x(0), a = x(r.pessimistic), b = x(r.optimistic), m = x(r.base);
  const neg = a < z ? `<rect x="${a}" y="4" width="${Math.min(b, z) - a}" height="6" rx="1" class="rb-neg"/>` : "";
  const pos = b > z ? `<rect x="${Math.max(a, z)}" y="4" width="${b - Math.max(a, z)}" height="6" rx="1" class="rb-pos"/>` : "";
  const label = `${kEur(r.pessimistic)} pessimistic, ${kEur(r.base)} base, ${kEur(r.optimistic)} optimistic`;
  return `<svg class="rb" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${label}">` +
    `<line x1="0" x2="${w}" y1="${h / 2}" y2="${h / 2}" class="rb-track"/>${neg}${pos}` +
    `<line x1="${z}" x2="${z}" y1="0" y2="${h}" class="rb-zero"/>` +
    `<rect x="${m - 1}" y="1" width="2" height="${h - 2}" rx="1" class="rb-base"/></svg>`;
}

// The product mark: a building with a new floor on top.
const LOGO = `<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true"><rect x="3" y="9" width="14" height="9" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.6"/><rect x="5.5" y="3" width="9" height="4.5" rx="1" fill="var(--accent)"/></svg>`;

// The top bar, the same on every page. `active` is the page being shown.
function topbar(active, areaLabel = "") {
  const link = (id, href, text) =>
    `<a href="${withArea(href)}"${active === id ? ' aria-current="page"' : ""}>${text}</a>`;
  return `<header class="topbar">
    <a class="brand" href="${withArea("index.html")}">${LOGO}<span>Buildable Land</span><small>${areaLabel}</small></a>
    <form class="search" role="search" id="search-form">
      <input id="search" type="search" placeholder="Find a parcel by cadastral reference" aria-label="Find a parcel by cadastral reference" autocomplete="off" spellcheck="false" />
      <kbd>/</kbd>
    </form>
    <nav class="topnav" aria-label="Pages">
      ${link("map", "index.html", "Map")}
      ${link("table", "shortlist.html", "Table")}
      ${link("method", "method.html", "Method")}
    </nav>
  </header>`;
}

// On pages other than the map, the search box opens the map on that parcel.
function wireSearchToMap() {
  const form = document.getElementById("search-form");
  if (!form) return;
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = document.getElementById("search").value.trim().toUpperCase();
    if (/^[0-9A-Z]{7,20}$/.test(q)) location.href = `${withArea("index.html")}#rc=${q}`;
  });
}
