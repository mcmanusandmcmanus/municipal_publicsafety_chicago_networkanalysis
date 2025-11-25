# CrimeAnalyzer Engine (Training Notes)

Purpose: Describe the mission-critical analytics in the upgraded `CrimeAnalyzer` class so operators and developers know how to run, tune, and prompt it.

Key capabilities
- Load: memory-optimized CSV ingest with dtype narrowing and chunked parsing; drops rows missing Date/Lat/Lon; precomputes hour features and radian coords for BallTree/DBSCAN.
- Summary: total incidents, date span, top primary types, arrest/domestic rates, hourly and monthly counts (tail 24 months).
- Hotspots: haversine DBSCAN (eps miles configurable) on full data or sampled (cap 500k by default), returns cluster size and centroid; parallel via `n_jobs=-1`.
- Network: spatiotemporal graph for a given crime type using BallTree neighbors within 0.5 miles and 3 days; caps nodes (default 20k) for UI; returns top 10 components with node metadata and centrality.
- Caching: per-crime-type network cache to avoid recomputation; optional DBSCAN sampling cap; data window selectable (`LOAD_YEARS_BACK` if desired).

Production defaults (Intel Ultra 7 / 32GB)
- `NETWORK_NODE_LIMIT=20000` to keep JSON payloads responsive.
- `DBSCAN_SAMPLE_LIMIT=500000` to retain detail without UI lag.
- `SPATIAL_RADIUS_MILES=0.5`, `TEMPORAL_WINDOW_DAYS=3`, `DBSCAN_EPS_MILES=0.2`, `DBSCAN_MIN_SAMPLES=5`.
- `CRIME_CSV_PATH` env var points to the secured CSV (fallback: `data/Crimes_2022_2025.csv`).

Prompts for operators
- “Load the dataset and report summary stats and memory footprint.”
- “Run hotspots for ROBBERY (or ALL) with current eps/min_samples; list top clusters.”
- “Build the network for ROBBERY and summarize components, edge count, largest CC size.”
- “Adjust node cap/eps/radius/time window and rerun hotspots/network to compare sensitivity.”
- “Refresh caches after new CSV load and surface any date parsing or schema issues.”

Mission alignment
- Keep analytics CJIS-safe (offline, no external calls), highlight spatial/temporal clusters and low-arrest pockets, and surface bridging events to support faster, safer interventions.
