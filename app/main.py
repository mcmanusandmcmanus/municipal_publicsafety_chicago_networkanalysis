from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from string import Template

from .analysis import (
    Config,
    load_data,
    overall_summary,
    temporal_profiles,
    dbscan_hotspots,
    build_spatiotemporal_graph,
    component_summary,
    centrality,
)


CSV_PATH = os.getenv("CRIME_CSV_PATH", "data/Crimes_-_2001_to_Present_20251124.csv")
CRIME_TYPE_DEFAULT = os.getenv("CRIME_TYPE_DEFAULT", "ROBBERY")

app = FastAPI(
    title="Chicago Public Safety Network Analysis",
    description="Offline-friendly EDA + SNA web API.",
    version="0.1.0",
)

# Optional: enable CORS for public frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def _load_and_cache() -> Dict[str, Any]:
    cfg = Config()
    df = load_data(CSV_PATH)
    summary = overall_summary(df)
    temporal = temporal_profiles(df)

    # DBSCAN hotspots (default crime type)
    _, hotspots = dbscan_hotspots(df, CRIME_TYPE_DEFAULT, cfg)

    # Spatiotemporal SNA (default crime type)
    G = build_spatiotemporal_graph(df, CRIME_TYPE_DEFAULT, cfg)
    components = component_summary(G)
    cent = centrality(G)
    cent_top = sorted(cent, key=lambda r: r["betweenness"], reverse=True)[:15]

    return {
        "df": df,
        "cfg": cfg,
        "summary": summary,
        "temporal": temporal,
        "hotspots": hotspots,
        "graph": G,
        "components": components,
        "centrality_top": cent_top,
    }


def _require_data():
    try:
        return _load_and_cache()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/summary")
def api_summary():
    data = _require_data()
    return {"summary": data["summary"], "temporal": data["temporal"]}


@app.get("/api/hotspots")
def api_hotspots(crime_type: str = CRIME_TYPE_DEFAULT):
    data = _require_data()
    df: pd.DataFrame = data["df"]
    subset, clusters = dbscan_hotspots(df, crime_type, data["cfg"])
    clusters = clusters.to_dict(orient="records")
    return {"crime_type": crime_type, "cluster_count": len(clusters), "clusters": clusters}


@app.get("/api/network")
def api_network(crime_type: str = CRIME_TYPE_DEFAULT):
    data = _require_data()
    df: pd.DataFrame = data["df"]
    cfg = data["cfg"]

    G = build_spatiotemporal_graph(df, crime_type, cfg)
    comps = component_summary(G)
    cent = centrality(G)
    cent_top = sorted(cent, key=lambda r: r["betweenness"], reverse=True)[:15]
    return {
        "crime_type": crime_type,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "avg_degree": 0 if G.number_of_nodes() == 0 else 2 * G.number_of_edges() / G.number_of_nodes(),
        "components": comps[:10],
        "centrality_top": cent_top,
    }


@app.get("/", response_class=HTMLResponse)
def home():
    data = _require_data()
    summary = data["summary"]
    temporal = data["temporal"]
    hotspots = data["hotspots"].head(5).to_dict(orient="records") if not data["hotspots"].empty else []
    comps = data["components"][:5]
    cent = data["centrality_top"]

    def bulletize(items):
        return "".join(f"<li>{item}</li>" for item in items)

    hotspots_html = bulletize(
        [
            f"Cluster {h['cluster']}: size {h['size']} ({h['date_min']} to {h['date_max']}) @ ({h['lat_center']:.5f}, {h['lon_center']:.5f})"
            for h in hotspots
        ]
    )
    comps_html = bulletize(
        [
            f"Size {c['size']} | {c['date_min']} to {c['date_max']} | arrest rate {c['arrest_rate']:.3f} | center ({c['lat_center']:.5f}, {c['lon_center']:.5f})"
            for c in comps
        ]
    )
    cent_html = bulletize(
        [
            f"{n['case_number']} deg {n['degree']} betw {n['betweenness']:.3f} | {n['date']} | {n['block']}"
            for n in cent
        ]
    )

    html_template = Template("""
    <html>
    <head>
        <title>Chicago Public Safety Network Analysis</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 24px; background: #f6f7fb; color: #1f2937; }
            h1, h2 { color: #111827; }
            .card { background: white; padding: 16px; border-radius: 10px; margin-bottom: 18px; box-shadow: 0 4px 10px rgba(0,0,0,0.06); }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
            code { background: #eef2ff; padding: 2px 6px; border-radius: 4px; }
            footer { margin-top: 24px; font-size: 0.9em; color: #6b7280; }
            canvas { width: 100%; max-width: 700px; height: 240px; }
            .chart-row { display: flex; flex-wrap: wrap; gap: 16px; }
            .chart-card { flex: 1 1 320px; }
        </style>
    </head>
    <body>
        <h1>Chicago Public Safety Network Analysis</h1>
        <div class="card">
            <h2>Dataset</h2>
            <p>$rows rows | $unique_types primary types | $date_min to $date_max</p>
            <p>Arrest rate: $arrest_rate | Domestic rate: $domestic_rate</p>
            <p>Top types: $top_types</p>
            <p>CRIME_CSV_PATH = <code>$csv_path</code></p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Hotspots (DBSCAN, $crime_type)</h3>
                <ul>$hotspots</ul>
            </div>
            <div class="card">
                <h3>Network Components ($crime_type)</h3>
                <ul>$components</ul>
            </div>
            <div class="card">
                <h3>Top Centrality ($crime_type)</h3>
                <ul>$centrality</ul>
            </div>
        </div>

        <div class="card">
            <h2>Visuals</h2>
            <div class="chart-row">
                <div class="chart-card">
                    <h4>Top Primary Types</h4>
                    <canvas id="chart-types"></canvas>
                </div>
                <div class="chart-card">
                    <h4>Crimes by Hour</h4>
                    <canvas id="chart-hour"></canvas>
                </div>
                <div class="chart-card">
                    <h4>Crimes by Day of Week</h4>
                    <canvas id="chart-dow"></canvas>
                </div>
                <div class="chart-card">
                    <h4>Monthly (last 12)</h4>
                    <canvas id="chart-month"></canvas>
                </div>
            </div>
        </div>

        <footer>
            API endpoints: <code>/api/summary</code> | <code>/api/hotspots</code> | <code>/api/network</code> | Health: <code>/health</code>.
            All computations run locally (no external calls). Adjust env var CRIME_CSV_PATH to point to your secured CSV.
        </footer>
        <script>
            async function fetchJSON(url) {
                const r = await fetch(url);
                if (!r.ok) throw new Error('Request failed ' + url);
                return r.json();
            }
            function drawBar(canvasId, labels, values, color='#2563eb') {
                const c = document.getElementById(canvasId);
                if (!c) return;
                const ctx = c.getContext('2d');
                const w = c.width = c.clientWidth;
                const h = c.height = c.clientHeight;
                const max = Math.max(...values, 1);
                const barW = w / labels.length;
                ctx.clearRect(0,0,w,h);
                ctx.fillStyle = color;
                ctx.font = '11px Arial';
                ctx.textAlign = 'center';
                labels.forEach((lab, i) => {
                    const val = values[i];
                    const barH = (val / max) * (h - 40);
                    const x = i * barW + barW * 0.1;
                    const bw = barW * 0.8;
                    ctx.fillRect(x, h - barH - 20, bw, barH);
                    ctx.fillStyle = '#111827';
                    ctx.fillText(val, x + bw/2, h - barH - 25);
                    ctx.save();
                    ctx.translate(x + bw/2, h - 5);
                    ctx.rotate(-Math.PI/4);
                    ctx.fillText(lab, 0, 0);
                    ctx.restore();
                    ctx.fillStyle = color;
                });
            }
            (async () => {
                try {
                    const summary = await fetchJSON('/api/summary');
                    const topTypes = summary.summary.top_primary_types;
                    const hourly = summary.temporal.hourly;
                    const dow = summary.temporal.dow;
                    const monthly = summary.temporal.monthly_tail;

                    const typeLabels = Object.keys(topTypes);
                    const typeVals = Object.values(topTypes);
                    drawBar('chart-types', typeLabels, typeVals, '#2563eb');

                    const hourLabels = Object.keys(hourly).map(k => k.toString());
                    const hourVals = Object.values(hourly);
                    drawBar('chart-hour', hourLabels, hourVals, '#16a34a');

                    const dowLabels = Object.keys(dow);
                    const dowVals = Object.values(dow);
                    drawBar('chart-dow', dowLabels, dowVals, '#f97316');

                    const monthLabels = Object.keys(monthly);
                    const monthVals = Object.values(monthly);
                    drawBar('chart-month', monthLabels, monthVals, '#6366f1');
                } catch (e) {
                    console.error(e);
                }
            })();
        </script>
    </body>
    </html>
    """)

    html = html_template.safe_substitute(
        rows=f"{summary['rows']:,}",
        unique_types=summary["unique_primary_types"],
        date_min=summary["date_min"],
        date_max=summary["date_max"],
        arrest_rate=f"{summary['arrest_rate']:.3f}",
        domestic_rate=f"{summary['domestic_rate']:.3f}",
        top_types=summary["top_primary_types"],
        csv_path=CSV_PATH,
        crime_type=CRIME_TYPE_DEFAULT,
        hotspots=hotspots_html,
        components=comps_html,
        centrality=cent_html,
    )
    return HTMLResponse(content=html)
