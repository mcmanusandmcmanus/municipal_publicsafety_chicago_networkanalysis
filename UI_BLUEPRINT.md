# UI Blueprint (Inspiration)

Purpose: capture an operator-friendly UI concept (dashboard + network view) inspired by the provided mock, while keeping CJIS-safe constraints (no external tiles/CDNs if prohibited).

Key sections
- Sidebar: navigation (Dashboard, Network Graph), status indicator, version tag.
- Header: dataset record count, crime-type selector (ALL, ROBBERY, THEFT, ASSAULT, BURGLARY, MOTOR VEHICLE THEFT, WEAPONS VIOLATION).
- KPIs: total incidents, arrest rate, domestic rate, hotspot count.
- Hotspot map: leaflet-style map showing DBSCAN clusters (color/size by count).
- Charts: hourly volume bar, monthly trend line (last 24 months).
- Network view: linkage analysis card showing nodes/edges/components; map with edges/nodes; list of active series.

Offline/CJIS adaptations
- Replace external CDNs (Tailwind, Chart.js, Leaflet) with locally bundled assets or pure canvas SVG as done in the current homepage (no external calls).
- If maps are required, use self-hosted tiles/GeoJSON overlays; avoid third-party tile servers unless approved.
- Fonts: prefer system-safe stack to avoid fetching from Google Fonts.

Data bindings to existing API
- Record count, arrest/domestic: `/api/summary`.
- Hourly/monthly charts: `/api/summary` (hourly_counts, monthly_counts).
- Hotspots: `/api/hotspots?crime_type=...` → plot circles colored by count thresholds.
- Network: `/api/network?crime_type=...` → nodes/edges, components count, largest component size.

UX notes
- Default view: Dashboard with KPIs, hotspots map, charts.
- Network view: warn if “ALL” selected; default to ROBBERY to avoid overload.
- Auto-resize maps on tab switch; show loading states when fetching.

Next steps (if building this UI)
- Bundle a lightweight CSS (e.g., vanilla or a tiny utility file) and a local chart helper to keep CJIS-safe.
- Add a local tile/shape overlay for maps (e.g., precinct/beat GeoJSON).
- Keep CORS restricted to known origins; no external telemetry.
