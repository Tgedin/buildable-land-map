# ADR 0001: Static-first architecture

- **Status:** accepted
- **Date:** 2026-10-11

## Context

The phase must be deployed and used by real people at ~€0. Free managed databases (e.g. Supabase free tier) pause after a week of inactivity, which breaks a public map that gets sporadic traffic. The data changes slowly (Catastro twice a year via ATOM, LiDAR every few years).

## Decision

Compute everything offline with a Python CLI. Publish static files (`web/data/*.json`) and a MapLibre page on GitHub Pages. No server, no database in production.

## Consequences

- ✅ €0, nothing sleeps, nothing to secure or patch.
- ✅ Every published number is reproducible from `config/area.yaml` + a commit.
- ⚠️ No live queries. Users can't change the rules on the fly.
- ⚠️ GeoJSON size grows with area → switch to PMTiles when > 10 MB (M4).

## Revisit when

A user need requires server-side computation (custom zoning rules, uploads, accounts).
