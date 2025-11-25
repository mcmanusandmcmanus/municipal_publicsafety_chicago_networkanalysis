# Municipal Public Safety – Chicago Network Analysis

Offline-first web app for exploratory analysis, spatial clustering, and social network analysis (SNA) on the Chicago crime extract. Built to be CJIS-safe: no external calls, CPU-only, pure Python stack.

## Quick start (local)
1) Place the CSV at `data/Crimes_-_2001_to_Present_20251124.csv` (or set `CRIME_CSV_PATH` to your secure location).
2) Install deps (prefer a virtualenv):
   ```bash
   pip install -r requirements.txt
   ```
3) Run the API:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4) Open `http://localhost:8000` for the summary dashboard, or use:
   - `/api/summary`
   - `/api/hotspots?crime_type=ROBBERY`
   - `/api/network?crime_type=ROBBERY`

## Stack (all offline-capable)
- FastAPI + Uvicorn (serving)
- Pandas / NumPy (data prep)
- scikit-learn (DBSCAN + BallTree haversine)
- NetworkX (centrality, components, Louvain)
- Statsmodels / Seaborn / Matplotlib (optional plotting)

## Render deployment
1) Push this repo with your data placement plan:
   - Best: mount a private dataset on Render (disk or env volume) and set `CRIME_CSV_PATH`.
   - Avoid checking large CJIS data into the public repo unless cleared by policy.
2) Create a new **Web Service** on Render, pick Python 3.10+.
3) Build command (optional, Render auto-installs): `pip install -r requirements.txt`
4) Start command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
5) Add environment variable: `CRIME_CSV_PATH=/path/on/render/disk/Crimes_-_2001_to_Present_20251124.csv`

## How it works
- Loads the CSV once on startup (cached).
- EDA summary: counts, date span, top primary types, arrest/domestic rates, monthly/hour/day-of-week breakdowns.
- Hotspots: DBSCAN in haversine space (default: 0.5 miles, min_samples=5) for a given `crime_type`.
- SNA: builds a spatiotemporal graph for a `crime_type` (default ROBBERY), connecting incidents within 0.5 miles and 3 days. Returns component summaries and top betweenness/degree nodes.
- Endpoints are read-only; no data leaves the server.

## Configuration
- `CRIME_CSV_PATH` – absolute or relative path to the CSV.
- `CRIME_TYPE_DEFAULT` – default crime type for homepage/hotspots/network (default: ROBBERY).
- To adjust proximity parameters, edit `Config` in `app/analysis.py` (spatial radius, temporal window, DBSCAN eps/min_samples).

## CJIS considerations
- All computations are local; no web requests or cloud APIs.
- Avoid emailing outputs; direct them to your secure network drive or keep on-host.
- If running in a shared environment, restrict file permissions on the CSV and logs.

## Testing smoke
With the CSV in place:
```bash
python - <<'PY'
from app.analysis import load_data, Config, build_spatiotemporal_graph
df = load_data("data/Crimes_-_2001_to_Present_20251124.csv")
cfg = Config()
G = build_spatiotemporal_graph(df, "ROBBERY", cfg)
print("rows", len(df), "nodes", G.number_of_nodes(), "edges", G.number_of_edges())
PY
```

## License
MIT (see LICENSE).
