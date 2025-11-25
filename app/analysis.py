"""
Local analytics utilities for the public safety web app.

All logic runs offline on CPU and expects a local CSV at CRIME_CSV_PATH or
data/Crimes_-_2001_to_Present_20251124.csv.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import networkx as nx
from sklearn.cluster import DBSCAN
from sklearn.neighbors import BallTree


@dataclass
class Config:
    spatial_radius_miles: float = 0.5
    temporal_days: int = 3
    dbscan_eps_miles: float = 0.5
    dbscan_min_samples: int = 5


def load_data(path: str) -> pd.DataFrame:
    """Load the dataset, parse dates, and drop rows without coordinates."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found at {path}")

    df = pd.read_csv(path, low_memory=False)
    # Prefer explicit CPD format; fall back to auto if needed.
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
    if df["Date"].isna().any():
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date", "Latitude", "Longitude"])

    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.to_period("M")
    df["Dow"] = df["Date"].dt.day_name()
    df["Hour"] = df["Date"].dt.hour
    return df


def overall_summary(df: pd.DataFrame) -> Dict:
    top_types = df["Primary Type"].value_counts().head(7)
    return {
        "rows": int(len(df)),
        "unique_primary_types": int(df["Primary Type"].nunique()),
        "date_min": str(df["Date"].min().date()),
        "date_max": str(df["Date"].max().date()),
        "arrest_rate": float(df["Arrest"].mean()),
        "domestic_rate": float(df["Domestic"].mean()),
        "top_primary_types": {str(k): int(v) for k, v in top_types.to_dict().items()},
    }


def temporal_profiles(df: pd.DataFrame) -> Dict:
    monthly = df.groupby("Month").size().sort_index().tail(12)
    hourly = df.groupby("Hour").size().sort_index()
    dow = df.groupby("Dow").size().sort_values(ascending=False)
    return {
        "monthly_tail": {str(k): int(v) for k, v in monthly.astype(int).to_dict().items()},
        "hourly": {int(k): int(v) for k, v in hourly.astype(int).to_dict().items()},
        "dow": {str(k): int(v) for k, v in dow.astype(int).to_dict().items()},
    }


def dbscan_hotspots(df: pd.DataFrame, crime_type: str, cfg: Config) -> Tuple[pd.DataFrame, pd.DataFrame]:
    subset = df[df["Primary Type"] == crime_type].copy()
    if subset.empty:
        return subset.assign(cluster=-1), pd.DataFrame()

    coords = np.deg2rad(subset[["Latitude", "Longitude"]].values)
    eps_rad = cfg.dbscan_eps_miles / 3959
    model = DBSCAN(eps=eps_rad, min_samples=cfg.dbscan_min_samples, metric="haversine")
    labels = model.fit_predict(coords)
    subset["cluster"] = labels

    agg_rows = []
    for cid, group in subset[subset["cluster"] >= 0].groupby("cluster"):
        agg_rows.append(
            {
                "cluster": int(cid),
                "size": int(len(group)),
                "date_min": str(group["Date"].min().date()),
                "date_max": str(group["Date"].max().date()),
                "lat_center": float(group["Latitude"].mean()),
                "lon_center": float(group["Longitude"].mean()),
            }
        )
    clusters = pd.DataFrame(agg_rows).sort_values(by="size", ascending=False)
    return subset, clusters


def build_spatiotemporal_graph(df: pd.DataFrame, crime_type: str, cfg: Config) -> nx.Graph:
    subset = df[df["Primary Type"] == crime_type].copy()
    subset = subset.reset_index(drop=True)
    if subset.empty:
        return nx.Graph()

    coords_rad = np.deg2rad(subset[["Latitude", "Longitude"]].values)
    tree = BallTree(coords_rad, metric="haversine")
    radius = cfg.spatial_radius_miles / 3959
    neighbors, distances = tree.query_radius(coords_rad, r=radius, return_distance=True, sort_results=True)

    G = nx.Graph()
    for _, row in subset.iterrows():
        G.add_node(
            row["Case Number"],
            date=row["Date"],
            lat=row["Latitude"],
            lon=row["Longitude"],
            block=row["Block"],
            description=row["Description"],
            arrest=bool(row["Arrest"]),
        )

    for i, (idxs, dists) in enumerate(zip(neighbors, distances)):
        case_a = subset.iloc[i]
        for j, dist in zip(idxs, dists):
            if i >= j:
                continue
            case_b = subset.iloc[j]
            dt_days = abs((case_a["Date"] - case_b["Date"]).days)
            if dt_days <= cfg.temporal_days:
                G.add_edge(
                    case_a["Case Number"],
                    case_b["Case Number"],
                    distance_miles=dist * 3959,
                    time_diff_days=dt_days,
                    weight=1 / (dt_days if dt_days > 0 else 1),
                )
    return G


def component_summary(G: nx.Graph) -> List[Dict]:
    comps = list(nx.connected_components(G))
    rows = []
    for comp in comps:
        sub = G.subgraph(comp)
        lats = [d["lat"] for _, d in sub.nodes(data=True)]
        lons = [d["lon"] for _, d in sub.nodes(data=True)]
        dates = [d["date"] for _, d in sub.nodes(data=True)]
        arrests = [d["arrest"] for _, d in sub.nodes(data=True)]
        rows.append(
            {
                "size": int(sub.number_of_nodes()),
                "edges": int(sub.number_of_edges()),
                "date_min": str(min(dates).date()),
                "date_max": str(max(dates).date()),
                "lat_center": float(np.mean(lats)),
                "lon_center": float(np.mean(lons)),
                "arrest_rate": float(np.mean(arrests)),
            }
        )
    rows = sorted(rows, key=lambda r: r["size"], reverse=True)
    return rows


def centrality(G: nx.Graph) -> List[Dict]:
    if G.number_of_nodes() == 0:
        return []
    deg = dict(G.degree())
    betw = nx.betweenness_centrality(G)
    return [
        {
            "case_number": node,
            "degree": int(deg[node]),
            "betweenness": float(betw[node]),
            "block": str(G.nodes[node].get("block")),
            "date": str(G.nodes[node].get("date").date()),
            "description": str(G.nodes[node].get("description")),
        }
        for node in G.nodes
    ]
