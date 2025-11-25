# Mission & Framework

**Purpose**
- Deliver a CJIS-safe, offline analytics service for Chicago public safety data, turning raw incidents into operational insights (hotspots, temporal patterns, and spatiotemporal networks) for faster, safer interventions.

**Analytical Framework**
- Ingest: load the local CSV via `CRIME_CSV_PATH`; parse dates (`%m/%d/%Y %I:%M:%S %p`); drop rows missing Date/Lat/Lon.
- EDA: compute volume, date span, top primary types, arrest/domestic rates, temporal profiles (hour, day-of-week, last-12 months).
- Hotspots: run haversine DBSCAN (default 0.5 miles, min_samples=5) per crime type; report cluster size, date span, centroid.
- SNA: build an undirected graph connecting incidents within 0.5 miles and 3 days; summarize components, arrest rates, and top central nodes.
- Caching: load-and-cache at startup to avoid repeat heavy computation; recompute only when the CSV changes or on restart.

**Operational Outcomes**
- Identify where and when incidents cluster, highlight low-arrest pockets, and surface bridging events to inform deployment and community safety actions.
- Provide a consumable API (`/api/summary`, `/api/hotspots`, `/api/network`) and a lightweight UI so partners can act without code changes.

**Run/Deploy**
- Local: `uvicorn app.main:app --host 0.0.0.0 --port 8000` with `CRIME_CSV_PATH` set to your secured CSV.
- Render: use `render.yaml`, set `CRIME_CSV_PATH` to the mounted dataset path, and keep CORS limited to allowed origins.

**Data Handling (CJIS-safe)**
- No external network calls; all analytics on local CPU/RAM.
- Do not email or expose raw CSV; store on approved secure drives and restrict API exposure to approved audiences.
- If regenerating, maintain the same schema and date format; rerun loaders to refresh caches.
