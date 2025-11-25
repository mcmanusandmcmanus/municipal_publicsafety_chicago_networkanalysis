# Prompts & Guidance (Training Module)

Use these prompts and guardrails when interacting with or extending the app.

**Prompts to Gather Insight**
- “Summarize current crime volume, date span, and top primary types from the loaded CSV.”
- “List DBSCAN hotspots for ROBBERY (or other crime types) with cluster size, centroid, and date span.”
- “Describe the largest spatiotemporal network components (0.5 mi / 3-day) and top betweenness nodes.”
- “Highlight beats/areas with high arrests versus low arrests for the selected crime type.”
- “Refresh caches after loading a new CSV and report any schema or date parsing issues.”

**Operational Guidance**
- Always set `CRIME_CSV_PATH` to the secured local CSV; never fetch data from the internet.
- Keep analytics offline: scikit-learn (DBSCAN/BallTree), NetworkX (centrality/components), Pandas/NumPy; no external tiles/APIs.
- Use `uvicorn app.main:app --host 0.0.0.0 --port 8000` for local runs; limit CORS origins in production.
- Default SNA params: 0.5-mile spatial radius, 3-day temporal window; adjust in `Config` (app/analysis.py) if needed.
- If performance becomes an issue, precompute per-crime-type caches on startup instead of per-request recomputation.

**Perceived Mission**
- Provide a CJIS-compliant, public-facing view of crime patterns that accelerates situational awareness, surfaces hotspots and low-arrest pockets, and supports rapid, community-safety interventions without exposing raw data externally.
