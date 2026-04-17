from __future__ import annotations

import math
import re
import unicodedata
import uuid
from html import escape
from textwrap import dedent

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from services.data_loader import load_weather_data, load_weather_province_detail, CITY_FOLDERS

# ─── Constants ────────────────────────────────────────────────────────────────

WEATHER_FEATURES = ["temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud"]

WIND_SECTORS = [
    "B", "BDB", "DB", "DDB", "D", "DDN", "DN", "NDN",
    "N", "NTN", "TN", "TTN", "T", "TTB", "TB", "BTB",
]
WIND_SPEED_BINS   = [0, 5, 10, 20, 35, np.inf]
WIND_SPEED_LABELS = ["0–5", "5–10", "10–20", "20–35", ">35"]

VAR_META = {
    "temp":       {"label": "Nhiệt độ",      "unit": "°C",   "agg": "mean", "cs": "RdYlBu_r", "color": "#ef4444"},
    "humidity":   {"label": "Độ ẩm",         "unit": "%",    "agg": "mean", "cs": "Blues",     "color": "#0ea5e9"},
    "rain":       {"label": "Lượng mưa",      "unit": "mm",   "agg": "sum",  "cs": "Blues",     "color": "#2563eb"},
    "wind_speed": {"label": "Tốc độ gió",    "unit": "m/s",  "agg": "mean", "cs": "Greens",    "color": "#10b981"},
    "wind_dir":   {"label": "Hướng gió",     "unit": "°",    "agg": "none", "cs": None,        "color": "#64748b"},
    "pressure":   {"label": "Áp suất",        "unit": "hPa",  "agg": "mean", "cs": "Purples",   "color": "#8b5cf6"},
    "cloud":      {"label": "Độ che phủ mây","unit": "%",    "agg": "mean", "cs": "Greys",     "color": "#94a3b8"},
}

# Seasonal presets (month ranges, inclusive)
SEASON_PRESETS = {
    "Cả năm 2025":   (1, 12),
    "Mùa khô":       (11, 4),   # wraps around
    "Mùa mưa":       (5, 10),
    "Q1":            (1, 3),
    "Q2":            (4, 6),
    "Q3":            (7, 9),
    "Q4":            (10, 12),
}
MONTH_NAMES = ["Th1","Th2","Th3","Th4","Th5","Th6","Th7","Th8","Th9","Th10","Th11","Th12"]

# Region mapping for province ordering (Bắc → Trung → Nam)
PROVINCE_REGION = {
    "Cao Bằng": "Bắc", "Tuyên Quang": "Bắc", "Lào Cai": "Bắc", "Thái Nguyên": "Bắc",
    "Phú Thọ": "Bắc", "Lạng Sơn": "Bắc", "Điện Biên": "Bắc", "Sơn La": "Bắc",
    "Lai Châu": "Bắc", "Hà Nội": "Bắc", "Hải Phòng": "Bắc", "TP. Hải Phòng": "Bắc",
    "Hưng Yên": "Bắc", "Ninh Bình": "Bắc", "Quảng Ninh": "Bắc", "Bắc Ninh": "Bắc",
    "Thanh Hóa": "Trung", "Nghệ An": "Trung", "Hà Tĩnh": "Trung",
    "Quảng Trị": "Trung", "Huế": "Trung", "TP. Huế": "Trung",
    "Đà Nẵng": "Trung", "TP. Đà Nẵng": "Trung", "Quảng Ngãi": "Trung",
    "Khánh Hòa": "Trung", "Gia Lai": "Trung", "Đắk Lắk": "Trung", "Lâm Đồng": "Trung",
    "TP. Hồ Chí Minh": "Nam", "Hồ Chí Minh": "Nam", "Đồng Nai": "Nam", "Tây Ninh": "Nam",
    "Đồng Tháp": "Nam", "Vĩnh Long": "Nam", "TP. Cần Thơ": "Nam", "Cần Thơ": "Nam",
    "Cà Mau": "Nam", "An Giang": "Nam",
}

# Centroids for map fallback
PROVINCE_COORDS = {
    "An Giang": (10.52, 105.12), "Bắc Giang": (21.27, 106.19), "Bắc Ninh": (21.14, 106.06),
    "Bình Dương": (11.16, 106.67), "Cà Mau": (9.18, 105.15), "Cần Thơ": (10.03, 105.78),
    "TP. Cần Thơ": (10.03, 105.78), "Cao Bằng": (22.66, 106.25), "Đà Nẵng": (16.05, 108.20),
    "TP. Đà Nẵng": (16.05, 108.20), "Đắk Lắk": (12.71, 108.22), "Điện Biên": (21.39, 103.01),
    "Đồng Nai": (10.95, 106.82), "Đồng Tháp": (10.45, 105.63), "Gia Lai": (13.98, 108.00),
    "Hà Nội": (21.02, 105.85), "TP. Hà Nội": (21.02, 105.85), "Hà Tĩnh": (18.33, 105.90),
    "Hải Phòng": (20.84, 106.68), "TP. Hải Phòng": (20.84, 106.68), "Hồ Chí Minh": (10.82, 106.62),
    "TP. Hồ Chí Minh": (10.82, 106.62), "Huế": (16.46, 107.59), "TP. Huế": (16.46, 107.59),
    "Hưng Yên": (20.65, 106.05), "Khánh Hòa": (12.24, 109.19), "Lai Châu": (22.39, 103.46),
    "Lâm Đồng": (11.94, 108.44), "Lạng Sơn": (21.85, 106.76), "Lào Cai": (22.48, 103.97),
    "Nghệ An": (18.67, 105.68), "Ninh Bình": (20.25, 105.97), "Phú Thọ": (21.32, 105.39),
    "Quảng Bình": (17.47, 106.62), "Quảng Ngãi": (15.12, 108.80), "Quảng Ninh": (20.94, 107.07),
    "Quảng Trị": (16.81, 107.10), "Sơn La": (21.32, 103.91), "Tây Ninh": (11.31, 106.10),
    "Thái Nguyên": (21.59, 105.84), "Thanh Hóa": (19.80, 105.77), "Tuyên Quang": (21.82, 105.21),
    "Vĩnh Long": (10.25, 105.97),
}
REGION_ORDER = ["Bắc", "Trung", "Nam"]

PLOTLY_TEMPLATE = "plotly_white"
_FONT = "Inter, sans-serif"


# ─── Small utilities ──────────────────────────────────────────────────────────

def _h(content: str) -> str:
    return dedent(content).strip()


def _fmt(value, decimals=1, suffix="") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    try:
        v = float(value)
        if math.isnan(v):
            return "N/A"
        return f"{v:.{decimals}f}{suffix}"
    except Exception:
        return "N/A"


def _normalize_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _wind_dir_label(deg) -> str:
    try:
        idx = int(((float(deg) % 360) + 11.25) // 22.5) % 16
        return WIND_SECTORS[idx]
    except Exception:
        return "N/A"


def _base_layout(**kw) -> dict:
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", size=11, color="#334155"),
        margin=dict(l=10, r=10, t=36, b=10),
        template=PLOTLY_TEMPLATE,
    )
    base.update(kw)
    return base


def _ax_cfg(title="", **kw) -> dict:
    cfg = dict(
        title=dict(text=title, font=dict(size=10, color="#64748b")),
        tickfont=dict(size=9, color="#64748b"),
        gridcolor="rgba(0,0,0,0.05)",
        linecolor="#dbe7f2",
        zeroline=False,
    )
    cfg.update(kw)
    return cfg


# ─── Season filter helper ─────────────────────────────────────────────────────

def _filter_by_season(df: pd.DataFrame, preset: str, month: int | None = None) -> pd.DataFrame:
    """Return rows matching the chosen season preset or explicit month."""
    if "month" not in df.columns:
        df = df.copy()
        df["month"] = pd.to_datetime(df["timestamp"]).dt.month
    if month is not None:
        return df[df["month"] == month].copy()
    if preset not in SEASON_PRESETS:
        return df.copy()
    m_start, m_end = SEASON_PRESETS[preset]
    if m_start <= m_end:
        return df[df["month"].between(m_start, m_end)].copy()
    # wraps (e.g. Nov–Apr)
    return df[(df["month"] >= m_start) | (df["month"] <= m_end)].copy()


# ─── Pre-aggregation helpers (Layer 1 — never pass raw hourly data) ──────────

@st.cache_data(ttl=3600, show_spinner=False)
def _agg_province_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """City × Month aggregated frame for Layer-1 charts."""
    if df.empty or "city" not in df.columns:
        return pd.DataFrame()
    src = df.copy()
    src["month"] = pd.to_datetime(src["timestamp"]).dt.month
    agg: dict = {}
    for col in ["temp", "humidity", "pressure", "cloud", "wind_speed"]:
        if col in src.columns:
            agg[col] = (col, "mean")
    if "rain" in src.columns:
        agg["rain"] = ("rain", "sum")
    if not agg:
        return pd.DataFrame()
    return src.groupby(["city", "month"], observed=True).agg(**agg).reset_index()


@st.cache_data(ttl=3600, show_spinner=False)
def _agg_province_annual(df: pd.DataFrame) -> pd.DataFrame:
    """One row per city — annual summary."""
    if df.empty or "city" not in df.columns:
        return pd.DataFrame()
    src = df.copy()
    agg: dict = {}
    for col in ["temp", "humidity", "pressure", "cloud", "wind_speed"]:
        if col in src.columns:
            agg[col] = (col, "mean")
    if "rain" in src.columns:
        agg["rain"] = ("rain", "sum")
    if not agg:
        return pd.DataFrame()
    result = src.groupby("city", observed=True).agg(**agg).reset_index()
    # Add lat/lon centroids if available or from PROVINCE_COORDS fallback
    coords_list = []
    for city in result["city"]:
        # Try to get from data first
        subset = src[src["city"] == city]
        lat = subset["lat"].mean()
        lon = subset["lon"].mean()
        
        # Fallback to PROVINCE_COORDS if nan
        if (pd.isna(lat) or pd.isna(lon)) and city in PROVINCE_COORDS:
            lat, lon = PROVINCE_COORDS[city]
        
        # Secondary fallback if it's "Province - Location" format
        if (pd.isna(lat) or pd.isna(lon)) and " - " in city:
            prov = city.split(" - ")[0]
            if prov in PROVINCE_COORDS:
                lat, lon = PROVINCE_COORDS[prov]
        
        coords_list.append({"city": city, "lat": lat, "lon": lon})
    
    coords_df = pd.DataFrame(coords_list)
    result = result.merge(coords_df, on="city", how="left")

    # Rank each numeric col
    for col in ["temp", "humidity", "rain", "wind_speed", "pressure"]:
        if col in result.columns:
            result[f"{col}_rank"] = result[col].rank(ascending=False, method="min").astype("Int64")
    return result

def _agg_location_annual(df: pd.DataFrame) -> pd.DataFrame:
    """Location × Annual summary."""
    if df.empty or "location" not in df.columns:
        return pd.DataFrame()
    src = df.copy()
    agg: dict = {}
    for col in ["temp", "humidity", "pressure", "cloud", "wind_speed"]:
        if col in src.columns:
            agg[col] = (col, "mean")
    if "rain" in src.columns:
        agg["rain"] = ("rain", "sum")
    if "lat" in src.columns: agg["lat"] = ("lat", "mean")
    if "lon" in src.columns: agg["lon"] = ("lon", "mean")
    return src.groupby("location", observed=True).agg(**agg).reset_index()


# ─── CSS injection ────────────────────────────────────────────────────────────

def _inject_css():
    st.markdown(
        _h("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        :root {
            --wx-navy: #0f172a;
            --wx-slate: #1e293b;
            --wx-blue: #38bdf8;
            --wx-sky: #0ea5e9;
            --wx-glass: rgba(255, 255, 255, 0.03);
            --wx-border: rgba(255, 255, 255, 0.08);
        }

        .stApp { font-family: 'Plus Jakarta Sans', sans-serif; }

        /* ── Modern Navigation ── */
        .wx-nav-container {
            display: flex; align-items: center; justify-content: space-between;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            padding: 24px 32px; border-radius: 24px; margin-bottom: 32px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.1);
            position: relative; overflow: hidden;
        }
        .wx-nav-container::after {
            content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: radial-gradient(circle, rgba(56,189,248,0.05) 0%, transparent 70%);
            pointer-events: none;
        }
        .wx-nav-info { display: flex; flex-direction: column; gap: 6px; z-index: 1; }
        .wx-nav-title { font-size: 1.6rem; font-weight: 800; color: #fff; letter-spacing: -0.02em; }
        .wx-nav-breadcrumb { display: flex; align-items: center; gap: 8px; color: rgba(255,255,255,0.5); font-size: 0.85rem; font-weight: 600; }
        .wx-nav-sep { color: rgba(255,255,255,0.2); }
        .wx-nav-active { color: #38bdf8; text-shadow: 0 0 20px rgba(56,189,248,0.4); }

        /* ── Section Titles ── */
        .wx-section-title {
            font-size: 1.4rem; font-weight: 800; color: #0f172a; margin: 40px 0 20px 0;
            display: flex; align-items: center; gap: 12px;
        }
        .wx-section-title::after {
            content: ''; flex: 1; height: 1px; background: linear-gradient(to right, #e2e8f0, transparent);
        }

        /* ── KPI Grid ── */
        .wx-kpi-card {
            background: #fff; border: 1px solid #f1f5f9; border-radius: 20px;
            padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative; overflow: hidden; height: 100%;
        }
        .wx-kpi-card:hover { transform: translateY(-6px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.05); border-color: #e2e8f0; }
        .wx-kpi-icon {
            position: absolute; top: -10px; right: -10px; width: 80px; height: 80px;
            background: radial-gradient(circle, rgba(56,189,248,0.08) 0%, transparent 70%);
            display: flex; align-items: center; justify-content: center; opacity: 0.6;
        }
        .wx-kpi-label { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
        .wx-kpi-value { font-size: 2rem; font-weight: 800; color: #0f172a; letter-spacing: -0.03em; display: flex; align-items: baseline; gap: 4px; }
        .wx-kpi-unit { font-size: 0.9rem; color: #94a3b8; font-weight: 600; }

        /* ── Chart & Content Cards ── */
        .wx-card {
            background: #fff; border: 1px solid #f1f5f9; border-radius: 24px;
            padding: 28px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
        }
        .wx-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
        .wx-card-title { font-size: 1.1rem; font-weight: 800; color: #1e293b; display: flex; align-items: center; gap: 12px; }
        .wx-card-title::before { content: ''; width: 5px; height: 20px; background: linear-gradient(to bottom, #38bdf8, #0ea5e9); border-radius: 10px; }

        /* Legacy support for wx3 */
        .wx3-chart-card { background: #fff; border: 1px solid #f1f5f9; border-radius: 24px; padding: 24px; margin-bottom: 24px; }
        .wx3-chart-title { font-size: 1rem; font-weight: 700; color: #1e293b; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
        .wx3-section-title { font-size: 1.2rem; font-weight: 800; color: #0f172a; margin: 32px 0 16px 0; }

        /* ── Hints & Labels ── */
        .wx-click-hint {
            font-size: 0.85rem; color: #64748b; font-weight: 500;
            display: flex; align-items: center; gap: 6px; margin-bottom: 12px;
        }
        .wx-click-hint::before { content: '👆'; }
        
        .wx-control-label {
            font-size: 0.75rem; font-weight: 700; color: #64748b;
            text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;
            display: flex; align-items: center; gap: 6px;
        }

        /* ── Insights ── */
        .wx-insight-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px; }
        .wx-insight-card {
            background: #f8fafc; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px;
            transition: all 0.2s ease;
        }
        .wx-insight-card:hover { background: #f1f5f9; border-color: #e2e8f0; }
        .wx-insight-label { font-size: 0.7rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.04em; }
        .wx-insight-value { font-size: 1.2rem; font-weight: 800; color: #0f172a; margin-top: 6px; }

        /* ── Tables ── */
        .wx-table-container { border-radius: 16px; overflow: hidden; border: 1px solid #f1f5f9; }
        .wx-extreme-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        .wx-extreme-table th { background: #f8fafc; padding: 12px 16px; text-align: left; color: #64748b; font-weight: 700; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em; border-bottom: 1px solid #f1f5f9; }
        .wx-extreme-table td { padding: 14px 16px; color: #1e293b; border-bottom: 1px solid #f8fafc; }
        .wx-extreme-table tr:last-child td { border-bottom: none; }
        .wx-extreme-table tr:hover { background: #f8fafc; }

        /* ── Custom Selectors ── */
        .stSelectbox [data-baseweb="select"] { border-radius: 12px !important; }
        .stButton button { border-radius: 12px !important; font-weight: 700 !important; }
        .stSegmentedControl [role="radiogroup"] { background: #f1f5f9; border-radius: 14px; padding: 4px; }
        </style>
        """),
        unsafe_allow_html=True,
    )


# ─── Navigation helpers ───────────────────────────────────────────────────────

def _get_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def _set_state(*args, **kwargs):
    if len(args) == 2:
        st.session_state[args[0]] = args[1]
    for k, v in kwargs.items():
        st.session_state[k] = v


def _go_layer1():
    _set_state(wx_layer=1, wx_province=None, wx_location=None)
    st.rerun()


def _go_layer2(province: str | None = None):
    _set_state(wx_layer=2, wx_province=province, wx_location=None)
    st.rerun()


def _go_layer3(province: str, location: str | None = None):
    _set_state(wx_layer=3, wx_province=province, wx_location=location)
    st.rerun()


def _render_nav(layer: int, province: str | None = None, location: str | None = None):
    # Modern SVG Icons
    icon_home = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>'
    
    titles = ["Toàn quốc", "So sánh Tỉnh thành", "Chi tiết Trạm đo"]
    bc_html = f"<div class='wx-nav-breadcrumb'>{icon_home} <span class='wx-nav-sep'>/</span> <span>Toàn quốc</span>"
    if layer >= 2:
        bc_html += f" <span class='wx-nav-sep'>/</span> <span>So sánh</span>"
    if layer >= 3:
        bc_html += f" <span class='wx-nav-sep'>/</span> <span class='wx-nav-active'>{province}</span>"
    bc_html += "</div>"

    nav_html = f"<div class='wx-nav-container'><div class='wx-nav-info'>{bc_html}<div class='wx-nav-title'>{titles[layer-1]}</div></div><div style='display:flex; gap:12px;'><button class='stButton' style='background:transparent; border:1px solid rgba(255,255,255,0.2); color:white; border-radius:8px; padding:6px 12px; font-size:12px; cursor:pointer;' onclick='window.location.reload()'>🔄 Làm mới</button></div></div>"
    st.markdown(nav_html, unsafe_allow_html=True)


def _icon(name: str) -> str:
    icons = {
        "temp": "<svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='#ef4444' stroke-width='2.5'><path d='M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z'/></svg>",
        "hum": "<svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='#0ea5e9' stroke-width='2.5'><path d='M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z'/></svg>",
        "rain": "<svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='#3b82f6' stroke-width='2.5'><path d='M4 14.89c0-2.9 1.93-5.45 4.73-6.2C10.01 6.04 12.34 5 15 5c3.31 0 6 2.69 6 6 0 .17-.01.33-.03.5A5 5 0 0 1 18 21h-5m-1 3v-3m-4 3v-3m8 3v-3'/></svg>",
        "wind": "<svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='#64748b' stroke-width='2.5'><path d='M17.7 7.7A2.5 2.5 0 1 1 20 11H3m14.7 5.3A2.5 2.5 0 1 0 20 13H10m-3 6a2.5 2.5 0 1 1-2.3 3.5H16'/></svg>",
        "map": "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.5'><polygon points='1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6'/><line x1='8' y1='2' x2='8' y2='18'/><line x1='16' y1='6' x2='16' y2='22'/></svg>",
        "chart": "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.5'><line x1='18' y1='20' x2='18' y2='10'/><line x1='12' y1='20' x2='12' y2='4'/><line x1='6' y1='20' x2='6' y2='14'/></svg>"
    }
    return icons.get(name, "")


def _kpi_html(label: str, value: str, unit: str = "", icon_svg: str = "") -> str:
    return f"<div class='wx-kpi-card'><div class='wx-kpi-icon'>{icon_svg}</div><div class='wx-kpi-label'>{label}</div><div class='wx-kpi-value'>{value}<span class='wx-kpi-unit'>{unit}</span></div></div>"


def _kpi_row(cards: list[str]):
    if not cards: return
    cols = st.columns(len(cards))
    for i, card in enumerate(cards):
        with cols[i]:
            st.markdown(card, unsafe_allow_html=True)


# ─── Season preset selector ───────────────────────────────────────────────────

def _season_selector(key_prefix: str) -> tuple[str, int | None]:
    """Single clean season/period selector. Returns (preset_name, month_or_None)."""
    all_opts = list(SEASON_PRESETS.keys()) + MONTH_NAMES
    preset = _get_state(f"{key_prefix}_season", "Cả năm 2025")
    if preset not in all_opts:
        preset = all_opts[0]

    sel = st.segmented_control(
        "Giai đoạn phân tích",
        all_opts,
        default=preset,
        key=f"{key_prefix}_season_seg",
    )
    if sel:
        preset = sel
    _set_state(f"{key_prefix}_season", preset)

    month = None
    if preset.startswith("Th") and len(preset) <= 4:
        try:
            month = int(preset[2:])
        except ValueError:
            pass
    return preset, month


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — NATIONAL OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

def _render_layer1(df: pd.DataFrame):
    _render_nav(1)
    
    preset, month = _season_selector("l1")
    filtered = _filter_by_season(df, preset, month)

    annual = _agg_province_annual(filtered)
    monthly_agg = _agg_province_monthly(filtered)

    # ── KPI Cards ──────────────────────────────────────────────────────────────
    kpi_cards = []
    if "temp" in annual.columns:
        nat_temp = annual["temp"].mean()
        kpi_cards.append(_kpi_html("Nhiệt độ TB", _fmt(nat_temp, 1), "°C", _icon("temp")))
    if "humidity" in annual.columns:
        nat_hum = annual["humidity"].mean()
        kpi_cards.append(_kpi_html("Độ ẩm TB", _fmt(nat_hum, 0), "%", _icon("hum")))
    if "rain" in annual.columns:
        nat_rain = annual["rain"].sum()
        kpi_cards.append(_kpi_html("Tổng mưa năm", _fmt(nat_rain, 0), " mm", _icon("rain")))
    if "wind_speed" in annual.columns:
        nat_wind = annual["wind_speed"].mean()
        kpi_cards.append(_kpi_html("Tốc độ gió TB", _fmt(nat_wind, 1), " m/s", _icon("wind")))
    if kpi_cards:
        _kpi_row(kpi_cards)

    # ── Variable selector ──────────────────────────────────────────────────────
    var_opts = [v for v in ["temp", "humidity", "rain", "wind_speed"] if v in annual.columns]
    var_labels = {v: VAR_META[v]["label"] for v in var_opts}
    cur_var = _get_state("l1_var", var_opts[0] if var_opts else "temp")
    if cur_var not in var_opts and var_opts:
        cur_var = var_opts[0]

    cur_var = st.segmented_control(
        "Chỉ số phân tích",
        var_opts,
        format_func=lambda x: var_labels[x],
        selection_mode="single",
        default=cur_var,
        key="l1_var_seg",
    )
    if not cur_var:
        cur_var = _get_state("l1_var", "temp")
    _set_state(l1_var=cur_var)

    var_meta = VAR_META.get(cur_var, {})
    var_label = var_meta.get("label", cur_var)
    var_unit  = var_meta.get("unit", "")
    var_cs    = var_meta.get("cs", "RdYlBu_r") or "RdYlBu_r"

    col_left, col_right = st.columns([1.3, 1], gap="large")

    # ── Chart 1 — Choropleth / Scatter Map ────────────────────────────────────
    with col_left:
        st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='wx-card-header'><div class='wx-card-title'>{_icon('map')} Bản đồ {var_label} theo tỉnh</div></div>", unsafe_allow_html=True)

        if not annual.empty and cur_var in annual.columns:
            has_coords = "lat" in annual.columns and "lon" in annual.columns

            if has_coords:
                ann_plot = annual.dropna(subset=["lat", "lon", cur_var]).copy()
                n_total = len(annual)
                ann_plot["rank_txt"] = ann_plot[f"{cur_var}_rank"].apply(
                    lambda r: f"Rank {int(r)}/{n_total}" if pd.notna(r) else ""
                ) if f"{cur_var}_rank" in ann_plot.columns else ""

                fig_map = go.Figure(go.Scattermapbox(
                    lat=ann_plot["lat"], lon=ann_plot["lon"],
                    mode="markers",
                    marker=dict(
                        size=16, opacity=0.90,
                        color=ann_plot[cur_var], colorscale=var_cs,
                        showscale=True,
                        colorbar=dict(title=var_unit, thickness=10, len=0.65),
                    ),
                    text=ann_plot["city"],
                    customdata=np.column_stack([
                        ann_plot[cur_var].round(1),
                        ann_plot["rank_txt"] if "rank_txt" in ann_plot else [""] * len(ann_plot),
                    ]),
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        f"{var_label}: %{{customdata[0]}} {var_unit}<br>"
                        "%{customdata[1]}<extra></extra>"
                    ),
                ))
                fig_map.update_layout(
                    **_base_layout(height=480, margin=dict(l=0, r=0, t=10, b=0)),
                    mapbox=dict(
                        style="carto-positron", zoom=4.5,
                        center=dict(lat=16.5, lon=106.5),
                    ),
                )
                st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})
            else:
                # Fallback: horizontal bar chart ranked by var
                ann_sorted = annual.dropna(subset=[cur_var]).sort_values(cur_var, ascending=True).tail(20)
                fig_bar = go.Figure(go.Bar(
                    y=ann_sorted["city"], x=ann_sorted[cur_var],
                    orientation="h",
                    marker=dict(color=ann_sorted[cur_var], colorscale=var_cs, line=dict(width=0)),
                    hovertemplate=f"%{{y}}<br>{var_label}: %{{x:.1f}} {var_unit}<extra></extra>",
                ))
                fig_bar.update_layout(**_base_layout(height=420, xaxis=_ax_cfg(f"{var_label} ({var_unit})"), yaxis=_ax_cfg()))
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

            # Province selector for drill-down
            st.markdown("<div class='wx-click-hint'>Chọn tỉnh bên dưới để xem phân tích chi tiết</div>", unsafe_allow_html=True)
            province_list = sorted(annual["city"].tolist())
            sel_prov = st.selectbox("Xem chi tiết tỉnh/thành:", ["— chọn tỉnh —"] + province_list, key="l1_province_sel")
            if sel_prov != "— chọn tỉnh —":
                if st.button(f"Phân tích chi tiết: {sel_prov}", key="l1_drill_btn", type="primary"):
                    _go_layer2(sel_prov)
        else:
            st.info("Không đủ dữ liệu cho bản đồ.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Chart 2 — Seasonal Line Chart ─────────────────────────────────────────
    with col_right:
        st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='wx-card-header'><div class='wx-card-title'>{_icon('chart')} Biến thiên theo mùa (toàn quốc)</div></div>", unsafe_allow_html=True)

        if not monthly_agg.empty:
            nat_monthly = monthly_agg.groupby("month", observed=True).agg(
                temp=("temp", "mean") if "temp" in monthly_agg.columns else ("month", "count"),
                rain=("rain", "sum") if "rain" in monthly_agg.columns else ("month", "count"),
                humidity=("humidity", "mean") if "humidity" in monthly_agg.columns else ("month", "count"),
            ).reset_index()

            fig_line = go.Figure()
            # Background wet-season shade (May–Oct)
            fig_line.add_vrect(x0=4.5, x1=10.5, fillcolor="rgba(235,245,251,0.6)", line_width=0,
                               annotation_text="Mùa mưa", annotation_position="top left",
                               annotation_font=dict(size=9, color="#0369a1"))
            # Dry season shade (Nov–Apr, split)
            fig_line.add_vrect(x0=0.5, x1=4.5, fillcolor="rgba(254,249,231,0.6)", line_width=0)
            fig_line.add_vrect(x0=10.5, x1=12.5, fillcolor="rgba(254,249,231,0.6)", line_width=0,
                               annotation_text="Mùa khô", annotation_position="top right",
                               annotation_font=dict(size=9, color="#92400e"))

            if "temp" in nat_monthly.columns:
                t_peak_idx = nat_monthly["temp"].idxmax()
                fig_line.add_trace(go.Scatter(
                    x=nat_monthly["month"], y=nat_monthly["temp"],
                    mode="lines+markers", name="Nhiệt độ TB (°C)",
                    line=dict(color="#ef4444", width=2.5, shape="spline"),
                    marker=dict(size=6),
                    hovertemplate="Tháng %{x}<br>Nhiệt độ: %{y:.1f}°C<extra></extra>",
                ))
                # Annotate peak
                fig_line.add_annotation(
                    x=nat_monthly.loc[t_peak_idx, "month"],
                    y=nat_monthly.loc[t_peak_idx, "temp"],
                    text=f"Đỉnh {nat_monthly.loc[t_peak_idx,'temp']:.1f}°C",
                    showarrow=True, arrowhead=2, arrowcolor="#ef4444",
                    font=dict(size=9, color="#ef4444"), bgcolor="rgba(255,255,255,0.85)",
                )

            if "humidity" in nat_monthly.columns:
                fig_line.add_trace(go.Scatter(
                    x=nat_monthly["month"], y=nat_monthly["humidity"],
                    mode="lines", name="Độ ẩm TB (%)",
                    line=dict(color="#0ea5e9", width=1.8, dash="dot"),
                    yaxis="y2",
                    hovertemplate="Tháng %{x}<br>Độ ẩm: %{y:.0f}%<extra></extra>",
                ))

            fig_line.update_layout(
                **_base_layout(
                    height=380,
                    xaxis=_ax_cfg("Tháng", tickvals=list(range(1, 13)), ticktext=MONTH_NAMES),
                    yaxis=_ax_cfg("Nhiệt độ (°C)"),
                    yaxis2=dict(**_ax_cfg("Độ ẩm (%)"), overlaying="y", side="right", showgrid=False),
                    legend=dict(orientation="h", x=0, y=1.1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                    hovermode="x unified",
                )
            )
            st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Không đủ dữ liệu theo tháng.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Chart 4 — Wind Rose ──────────────────────────────────────────────────
    # Chart 5 — Box / Violin (monthly distribution)
    col_wind, col_box = st.columns([1, 1], gap="large")

    with col_wind:
        st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
        st.markdown("<div class='wx-card-header'><div class='wx-card-title'>🌬 Hoa gió toàn quốc</div></div>", unsafe_allow_html=True)

        wind_src = filtered.dropna(subset=["wind_speed", "wind_dir"]) if "wind_dir" in filtered.columns else pd.DataFrame()
        if not wind_src.empty:
            sector_idx = (((wind_src["wind_dir"] % 360) + 11.25) // 22.5).astype(int) % 16
            wind_src = wind_src.copy()
            wind_src["sector"] = sector_idx.map(dict(enumerate(WIND_SECTORS)))
            wind_src["spd_bin"] = pd.cut(wind_src["wind_speed"], bins=WIND_SPEED_BINS,
                                          labels=WIND_SPEED_LABELS, include_lowest=True, right=False)
            pivot_wr = (
                wind_src.groupby(["sector", "spd_bin"], observed=False)
                .size().unstack(fill_value=0)
                .reindex(index=WIND_SECTORS, columns=WIND_SPEED_LABELS, fill_value=0)
            )
            colors_wr = ["#bae6fd", "#7dd3fc", "#38bdf8", "#0ea5e9", "#0369a1"]
            fig_wr = go.Figure()
            for band, clr in zip(WIND_SPEED_LABELS, colors_wr):
                fig_wr.add_trace(go.Barpolar(
                    r=pivot_wr[band].values, theta=WIND_SECTORS,
                    name=f"{band} m/s", marker_color=clr,
                    marker_line_color="rgba(255,255,255,0.7)", marker_line_width=0.6, opacity=0.93,
                    hovertemplate="Hướng %{theta}<br>Tần suất: %{r}<extra></extra>",
                ))
            fig_wr.update_layout(
                **_base_layout(height=340),
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(showticklabels=True, ticks="", gridcolor="rgba(0,0,0,0.08)", tickfont=dict(size=8)),
                    angularaxis=dict(direction="clockwise", rotation=90, gridcolor="rgba(0,0,0,0.06)", tickfont=dict(size=9)),
                ),
                legend=dict(orientation="h", x=0.3, y=-0.1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_wr, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Không có dữ liệu wind_dir để vẽ hoa gió.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_box:
        st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
        box_var = _get_state("l1_box_var", "temp")
        box_opts = [v for v in ["temp", "rain"] if v in filtered.columns]

        box_var_sel = st.segmented_control(
            "Phân phối theo tháng",
            box_opts,
            format_func=lambda x: VAR_META[x]["label"],
            selection_mode="single",
            default=box_var,
            key="l1_box_var_seg",
        )
        if box_var_sel:
            box_var = box_var_sel
            _set_state(l1_box_var=box_var)
        else:
            box_var = _get_state("l1_box_var", "temp")

        box_src = filtered.copy()
        box_src["month"] = pd.to_datetime(box_src["timestamp"]).dt.month
        # Pre-aggregate to monthly for performance
        box_agg = monthly_agg if not monthly_agg.empty else pd.DataFrame()
        if not box_agg.empty and box_var in box_agg.columns:
            fig_box = go.Figure()
            for m in range(1, 13):
                m_data = box_agg[box_agg["month"] == m][box_var].dropna()
                if m_data.empty:
                    continue
                fig_box.add_trace(go.Box(
                    y=m_data, name=MONTH_NAMES[m - 1],
                    marker_color=VAR_META[box_var]["color"],
                    marker=dict(size=3), line=dict(width=1.2),
                    boxmean=True,
                    hovertemplate=f"Tháng {m}<br>{VAR_META[box_var]['label']}: %{{y:.1f}}<extra></extra>",
                ))
            fig_box.update_layout(
                **_base_layout(height=300),
                yaxis=_ax_cfg(f"{VAR_META[box_var]['label']} ({VAR_META[box_var]['unit']})"),
                xaxis=_ax_cfg("Tháng"),
                showlegend=False,
            )
            st.plotly_chart(fig_box, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Không đủ dữ liệu box/violin.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Province Ranking Table ────────────────────────────────────────────────
    st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
    st.markdown("<div class='wx-card-header'><div class='wx-card-title'>🏆 Xếp hạng tỉnh thành</div></div>", unsafe_allow_html=True)

    if not annual.empty and cur_var in annual.columns:
        # Show Top 10 and Bottom 10 if there are many cities
        rank_df_full = annual[["city", cur_var]].dropna().sort_values(cur_var, ascending=False).reset_index(drop=True)
        rank_df_full.columns = ["Tỉnh/Thành", f"{var_label} ({var_unit})"]
        rank_df_full.index = rank_df_full.index + 1
        
        c_r1, c_r2 = st.columns([1, 1], gap="large")
        with c_r1:
            st.markdown("<div style='font-size:0.8rem;font-weight:700;margin-bottom:8px;'>🔝 Top 10 cao nhất</div>", unsafe_allow_html=True)
            st.dataframe(rank_df_full.head(10), use_container_width=True, height=380)
        with c_r2:
            st.markdown("<div style='font-size:0.8rem;font-weight:700;margin-bottom:8px;'>❄️ Top 10 thấp nhất</div>", unsafe_allow_html=True)
            st.dataframe(rank_df_full.tail(10), use_container_width=True, height=380)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📊 Xem toàn bộ xếp hạng (63 tỉnh thành)"):
            st.dataframe(rank_df_full, use_container_width=True, height=400)

        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("So sánh tỉnh thành chi tiết", key="l1_go_l2", type="primary"):
                _go_layer2()
        with c2:
            st.caption("Chọn một tỉnh trong bảng xếp hạng và nhấn 'Phân tích chi tiết' ở bản đồ để khám phá sâu hơn.")


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — PROVINCE COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════

def _render_layer2(df: pd.DataFrame, focus_province: str | None = None):
    province = _get_state("wx_province", focus_province)
    _render_nav(2, province)

    # ── Action Bar (Province & Time) ──
    st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
    
    col_p, col_v = st.columns([1, 1], gap="large")
    with col_p:
        st.markdown("<div class='wx-control-label'>🏙️ CHỌN TỈNH PHÂN TÍCH</div>", unsafe_allow_html=True)
        c_sel, c_btn = st.columns([3, 1])
        with c_sel:
            sel_province = st.selectbox("Tỉnh/Thành:", list(CITY_FOLDERS.keys()), 
                                        index=list(CITY_FOLDERS.keys()).index(province) if province in CITY_FOLDERS else 0,
                                        key="l2_prov_sel", label_visibility="collapsed")
            if sel_province != province:
                _set_state(wx_province=sel_province)
                province = sel_province
        with c_btn:
            if st.button("Khám phá", key="l2_go_l3", type="primary", use_container_width=True):
                _go_layer3(province)
    
    with col_v:
        l2_vars = [v for v in ["temp", "rain", "humidity", "wind_speed", "pressure"] if v in df.columns]
        l2_primary_var = st.segmented_control("Chỉ số so sánh", l2_vars,
                                              format_func=lambda x: VAR_META[x]["label"],
                                              selection_mode="single",
                                              default=l2_vars[0],
                                              key="l2_primary_var_seg")
        if not l2_primary_var: l2_primary_var = l2_vars[0]

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    preset, month = _season_selector("l2")
    st.markdown("</div>", unsafe_allow_html=True)
    filtered = _filter_by_season(df, preset, month)

    annual = _agg_province_annual(filtered)
    monthly_agg = _agg_province_monthly(filtered)

    # ── Chart 1 — Province × Month Heatmap ───────────────────────
    st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='wx-card-header'><div class='wx-card-title'>{_icon('chart')} Heatmap Tỉnh × Tháng</div></div>", unsafe_allow_html=True)

    hm2_var_opts = [v for v in ["temp", "rain", "humidity", "wind_speed"] if v in monthly_agg.columns]
    hm2_col1, hm2_col2 = st.columns([1, 1])
    with hm2_col1:
        sort_by = st.segmented_control("Sắp xếp:", ["Vùng miền", "Giá trị năm", "Tên A–Z"],
                            key="l2_sort_seg", default="Vùng miền")
    with hm2_col2:
        region_filter = st.selectbox("Lọc vùng:", ["Tất cả", "Bắc", "Trung", "Nam"], key="l2_region_filter")

    hm2_var = l2_primary_var

    if not monthly_agg.empty and hm2_var in monthly_agg.columns:
        prov_month = monthly_agg.groupby(["city", "month"], observed=True)[hm2_var].agg(
            "sum" if hm2_var == "rain" else "mean"
        ).reset_index()
        pivot2 = prov_month.pivot(index="city", columns="month", values=hm2_var).reindex(columns=range(1, 13))

        # Apply region filter
        if region_filter != "Tất cả":
            keep = [c for c in pivot2.index if PROVINCE_REGION.get(c, "Bắc") == region_filter]
            pivot2 = pivot2.loc[[c for c in keep if c in pivot2.index]]

        # Sort
        if sort_by == "Vùng miền":
            def _reg_key(city):
                reg = PROVINCE_REGION.get(city, "Nam")
                return (REGION_ORDER.index(reg) if reg in REGION_ORDER else 99, city)
            pivot2 = pivot2.loc[sorted(pivot2.index, key=_reg_key)]
        elif sort_by == "Giá trị năm":
            pivot2 = pivot2.loc[pivot2.mean(axis=1).sort_values(ascending=False).index]
        else:
            pivot2 = pivot2.sort_index()

        # Region boundary lines
        shapes, annots = [], []
        prev_reg = None
        for i, city in enumerate(pivot2.index):
            reg = PROVINCE_REGION.get(city, "Bắc")
            if sort_by == "Vùng miền" and reg != prev_reg:
                if i > 0:
                    shapes.append(dict(type="line", x0=-0.5, x1=11.5, y0=i - 0.5, y1=i - 0.5,
                                       line=dict(color="#ffffff", width=2)))
                prev_reg = reg

        cs2 = VAR_META[hm2_var].get("cs", "RdYlBu_r") or "RdYlBu_r"
        fig_hm2 = go.Figure(go.Heatmap(
            z=pivot2.values,
            x=[f"T{m}" for m in range(1, 13)],
            y=list(pivot2.index),
            colorscale=cs2,
            hovertemplate=f"Tỉnh: %{{y}}<br>Tháng: %{{x}}<br>{VAR_META[hm2_var]['label']}: %{{z:.1f}} {VAR_META[hm2_var]['unit']}<extra></extra>",
            colorbar=dict(title=VAR_META[hm2_var]["unit"], thickness=10, len=0.8),
        ))
        h2 = max(400, len(pivot2) * 20)
        fig_hm2.update_layout(
            **_base_layout(height=h2, shapes=shapes, margin=dict(l=130, r=10, t=20, b=10)),
            xaxis=_ax_cfg("Tháng"),
            yaxis=_ax_cfg("Tỉnh/Thành"),
        )
        st.plotly_chart(fig_hm2, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Không đủ dữ liệu heatmap tỉnh × tháng.")

    # ── Chart 2 — Ranking Bar + Chart 3 — Scatter ────────────────────────────
    col_rank, col_scatter = st.columns([1, 1], gap="large")

    with col_rank:
        st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='wx-card-header'><div class='wx-card-title'>{_icon('chart')} Xếp hạng tỉnh thành</div></div>", unsafe_allow_html=True)
        rank_reg = st.radio("Vùng:", ["Tất cả", "Bắc", "Trung", "Nam"], horizontal=True, key="l2_rank_reg")
        rank_var = l2_primary_var

        if not annual.empty and rank_var in annual.columns:
            rb_df = annual[["city", rank_var]].dropna().sort_values(rank_var, ascending=False).copy()
            if rank_reg != "Tất cả":
                rb_df = rb_df[rb_df["city"].map(lambda c: PROVINCE_REGION.get(c, "")) == rank_reg]
            
            n_show = min(15, len(rb_df))
            rb_plot = rb_df.head(n_show)
            
            # Color top 5 red/orange, bottom 5 blue (within the Top 15)
            colors_rb = []
            for i in range(len(rb_plot)):
                if i < 3: colors_rb.append("#ef4444")
                elif i >= len(rb_plot) - 3: colors_rb.append("#3b82f6")
                else: colors_rb.append("#94a3b8")

            fig_rb = go.Figure(go.Bar(
                y=rb_plot["city"], x=rb_plot[rank_var],
                orientation="h",
                marker=dict(color=colors_rb, line=dict(width=0)),
                hovertemplate=f"%{{y}}<br>{VAR_META[rank_var]['label']}: %{{x:.1f}} {VAR_META[rank_var]['unit']}<extra></extra>",
            ))
            fig_rb.update_layout(
                **_base_layout(height=450, margin=dict(l=120, r=10, t=20, b=10)),
                xaxis=_ax_cfg(f"{VAR_META[rank_var]['label']} ({VAR_META[rank_var]['unit']})"),
                yaxis=_ax_cfg(autorange="reversed"),
                showlegend=False,
            )
            st.plotly_chart(fig_rb, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_scatter:
        st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='wx-card-header'><div class='wx-card-title'>{_icon('chart')} Tương quan: Nhiệt độ & Độ ẩm (theo vùng)</div></div>", unsafe_allow_html=True)

        if not annual.empty and "temp" in annual.columns and "humidity" in annual.columns:
            sc_df = annual.dropna(subset=["temp", "humidity"]).copy()
            sc_df["region"] = sc_df["city"].map(lambda c: PROVINCE_REGION.get(c, "Nam"))
            region_colors = {"Bắc": "#3b82f6", "Trung": "#f97316", "Nam": "#ef4444"}
            sc_df["color"] = sc_df["region"].map(region_colors)

            fig_sc = go.Figure()
            for reg, grp in sc_df.groupby("region"):
                rain_col = grp["rain"] if "rain" in grp.columns else pd.Series(10, index=grp.index)
                fig_sc.add_trace(go.Scatter(
                    x=grp["humidity"], y=grp["temp"],
                    mode="markers",
                    name=reg,
                    marker=dict(
                        color=region_colors.get(reg, "#64748b"),
                        size=10, opacity=0.85,
                        line=dict(width=1, color="white"),
                    ),
                    text=grp["city"].str[:8],
                    textposition="top center",
                    textfont=dict(size=8),
                    customdata=np.column_stack([
                        grp["city"],
                        grp["humidity"].round(0),
                        rain_col.fillna(0).round(0) if "rain" in grp.columns else np.zeros(len(grp)),
                    ]),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Nhiệt độ: %{y:.1f}°C<br>"
                        "Độ ẩm: %{customdata[1]:.0f}%<br>"
                        "Mưa: %{customdata[2]:.0f} mm<extra></extra>"
                    ),
                ))
            fig_sc.update_layout(
                **_base_layout(height=420),
                xaxis=_ax_cfg("Độ ẩm TB (%)"),
                yaxis=_ax_cfg("Nhiệt độ TB (°C)"),
                legend=dict(orientation="h", x=0, y=1.1, font=dict(size=10)),
                hovermode="closest",
            )
            st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Chart 4 — 2-Province Comparison (collapsible) ────────────────────────
    with st.expander("📊 So sánh 2 tỉnh thành (Advanced)", expanded=False):
        provinces_list = sorted(annual["city"].tolist()) if not annual.empty else []
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            prov_a = st.selectbox("Tỉnh A:", provinces_list, key="l2_cmp_a",
                                  index=0 if provinces_list else 0)
        with c2:
            prov_b = st.selectbox("Tỉnh B:", provinces_list, key="l2_cmp_b",
                                  index=min(1, len(provinces_list) - 1))
        with c3:
            cmp_var = st.selectbox("Biến:", [v for v in ["temp", "humidity", "rain", "wind_speed"] if v in monthly_agg.columns],
                                   format_func=lambda x: VAR_META[x]["label"], key="l2_cmp_var")

        if not monthly_agg.empty and prov_a != prov_b and cmp_var in monthly_agg.columns:
            def _get_monthly(city, var):
                sub = monthly_agg[monthly_agg["city"] == city].sort_values("month")
                return sub.set_index("month")[var].reindex(range(1, 13))

            ser_a = _get_monthly(prov_a, cmp_var)
            ser_b = _get_monthly(prov_b, cmp_var)

            fig_cmp = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                                    subplot_titles=["Đường so sánh", "% Chênh lệch theo tháng"])
            fig_cmp.add_trace(go.Scatter(
                x=list(range(1, 13)), y=ser_a.values,
                name=prov_a, line=dict(color="#3b82f6", width=2.5),
                hovertemplate=f"{prov_a} Tháng %{{x}}: %{{y:.1f}}<extra></extra>",
            ), row=1, col=1)
            fig_cmp.add_trace(go.Scatter(
                x=list(range(1, 13)), y=ser_b.values,
                name=prov_b, line=dict(color="#ef4444", width=2.5),
                hovertemplate=f"{prov_b} Tháng %{{x}}: %{{y:.1f}}<extra></extra>",
            ), row=1, col=1)

            pct_diff = ((ser_a - ser_b) / ser_b.replace(0, np.nan) * 100).fillna(0)
            colors_diff = ["#3b82f6" if v >= 0 else "#ef4444" for v in pct_diff.values]
            fig_cmp.add_trace(go.Bar(
                x=list(range(1, 13)), y=pct_diff.values,
                name="% Chênh lệch", marker_color=colors_diff,
                hovertemplate="Tháng %{x}<br>Chênh lệch: %{y:.1f}%<extra></extra>",
            ), row=2, col=1)

            fig_cmp.update_layout(**_base_layout(height=480, showlegend=True,
                                                  legend=dict(orientation="h", x=0, y=1.05, font=dict(size=10)),
                                                  hovermode="x unified"))
            fig_cmp.update_xaxes(tickvals=list(range(1, 13)), ticktext=MONTH_NAMES)
            st.plotly_chart(fig_cmp, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — PROVINCE DETAIL
# ═══════════════════════════════════════════════════════════════════════════════

def _render_layer3(df: pd.DataFrame):
    province = _get_state("wx_province", None)
    if not province:
        st.warning("Chưa chọn tỉnh. Quay lại Toàn quốc.")
        if st.button("← Quay lại", key="l3_fallback_back"):
            _go_layer1()
        return

    _render_nav(3, province)
    
    # ── Layer 3 Shared Action Bar ──
    st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
    c_l3_v, c_l3_t = st.columns([1, 1], gap="large")
    
    with c_l3_v:
        l3_vars = [v for v in ["temp", "rain", "humidity", "wind_speed", "pressure"] if v in df.columns]
        l3_primary_var = st.segmented_control("Chỉ số phân tích", l3_vars,
                                              format_func=lambda x: VAR_META[x]["label"],
                                              selection_mode="single",
                                              default=l3_vars[0],
                                              key="l3_primary_var_seg")
        if not l3_primary_var: l3_primary_var = l3_vars[0]

    with c_l3_t:
        preset, month = _season_selector("l3")
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = _filter_by_season(df, preset, month)

    with st.spinner(f"Đang tải dữ liệu chi tiết {province}..."):
        prov_df = load_weather_province_detail(province)
        if prov_df.empty:
            st.error(f"Không tìm thấy dữ liệu chi tiết cho {province}.")
            return
        prov_df = _filter_by_season(prov_df, preset, month)

    if prov_df.empty:
        st.warning(f"Không tải được dữ liệu chi tiết cho {province}. Dùng dữ liệu toàn quốc.")
        # Fallback to national data filtered by city
        if "city" in df.columns:
            prov_df = df[df["city"].astype(str).str.contains(province[:6], case=False, na=False)].copy()
        if prov_df.empty:
            st.error("Không có dữ liệu.")
            return

    prov_df = prov_df.sort_values("timestamp")
    national_annual = _agg_province_annual(df)
    nat_avg = national_annual.mean(numeric_only=True) if not national_annual.empty else pd.Series(dtype=float)

    # ── KPI Cards ──────────────────────────────────────────────────────────────
    kpi_cards = []
    if "temp" in prov_df.columns:
        p_temp = prov_df["temp"].mean()
        kpi_cards.append(_kpi_html("Nhiệt độ TB", _fmt(p_temp, 1), "°C", _icon("temp")))
    if "humidity" in prov_df.columns:
        p_hum = prov_df["humidity"].mean()
        kpi_cards.append(_kpi_html("Độ ẩm TB", _fmt(p_hum, 0), "%", _icon("hum")))
    if "rain" in prov_df.columns:
        p_rain = prov_df["rain"].sum()
        kpi_cards.append(_kpi_html("Tổng mưa giai đoạn", _fmt(p_rain, 0), " mm", _icon("rain")))
    if "wind_speed" in prov_df.columns:
        p_wind = prov_df["wind_speed"].mean()
        kpi_cards.append(_kpi_html("Tốc độ gió TB", _fmt(p_wind, 1), " m/s", _icon("wind")))
    if kpi_cards:
        _kpi_row(kpi_cards)

    # ── Insights Grid ──
    t_max = prov_df["temp"].max() if "temp" in prov_df.columns else 0
    t_min = prov_df["temp"].min() if "temp" in prov_df.columns else 0
    r_sum = prov_df["rain"].sum() if "rain" in prov_df.columns else 0
    w_max = prov_df["wind_speed"].max() if "wind_speed" in prov_df.columns else 0
    
    # Comfort Score (Simplified)
    comfort = 100
    if "temp" in prov_df.columns and "humidity" in prov_df.columns:
        t_avg = prov_df["temp"].mean()
        h_mean = prov_df["humidity"].mean()
        comfort = 100 - abs(t_avg - 24) * 3 - (max(0, h_mean - 70) * 0.5)
        comfort = max(0, min(100, comfort))

    st.markdown("<div class='wx-insight-grid'>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class='wx-insight-card'>
            <div class='wx-insight-label'>🌡 BIÊN ĐỘ NHIỆT</div>
            <div class='wx-insight-value'>{_fmt(t_min, 1)}°C - {_fmt(t_max, 1)}°C</div>
        </div>
        <div class='wx-insight-card'>
            <div class='wx-insight-label'>😊 CHỈ SỐ THOẢI MÁI</div>
            <div class='wx-insight-value'>{int(comfort)}/100</div>
        </div>
        <div class='wx-insight-card'>
            <div class='wx-insight-label'>🌧 TỔNG MƯA</div>
            <div class='wx-insight-value'>{_fmt(r_sum, 0)} mm</div>
        </div>
        <div class='wx-insight-card'>
            <div class='wx-insight-label'>🌬 GIÓ MẠNH NHẤT</div>
            <div class='wx-insight-value'>{_fmt(w_max, 1)} m/s</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Station/Location Ranking (Layer 3) ──
    if "location" in prov_df.columns:
        valid_locs = prov_df.dropna(subset=["location"])
        if not valid_locs.empty:
            st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='wx-card-header'><div class='wx-card-title'>{_icon('chart')} Xếp hạng các phường/xã/trạm trong tỉnh</div></div>", unsafe_allow_html=True)
            
            l3_rank_var = _get_state("l3_rank_var", "temp")
            l3_rv_opts = [v for v in ["temp", "rain", "humidity", "wind_speed"] if v in valid_locs.columns]
            
            c_sel1, c_sel2 = st.columns([1, 3])
            with c_sel1:
                l3_rank_var = st.selectbox("Xếp hạng theo:", l3_rv_opts, 
                                           format_func=lambda x: VAR_META[x]["label"],
                                           key="l3_rank_var_sel")
            
            # Aggregation for locations
            agg_fn = "sum" if l3_rank_var == "rain" else "mean"
            l3_rank_df = valid_locs.groupby("location", observed=True)[l3_rank_var].agg(agg_fn).reset_index()
            l3_rank_df = l3_rank_df.sort_values(l3_rank_var, ascending=(l3_rank_var == "humidity")).reset_index(drop=True)
            l3_rank_df.columns = ["Phường/Xã/Trạm", f"{VAR_META[l3_rank_var]['label']} ({VAR_META[l3_rank_var]['unit']})"]
            l3_rank_df.index = l3_rank_df.index + 1
            
            st.dataframe(l3_rank_df, use_container_width=True, height=250)
            st.markdown("<br>", unsafe_allow_html=True)

    # ── Chart 1 — Ward/Location Scatter Map ───────────────────────────────────
    has_loc = "location" in prov_df.columns and prov_df["location"].nunique() > 1
    has_coords = "lat" in prov_df.columns and "lon" in prov_df.columns

    map_var = _get_state("l3_map_var", "temp")
    if has_loc:
        st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='wx-card-header'><div class='wx-card-title'>{_icon('map')} Bản đồ phân bổ trạm quan trắc</div></div>", unsafe_allow_html=True)
        mv_opts = [v for v in ["temp", "rain"] if v in prov_df.columns]
        mv_col1, mv_col2 = st.columns([4, 1])
        with mv_col2:
            map_var = st.radio("Biến:", mv_opts, format_func=lambda x: VAR_META[x]["label"],
                                key="l3_map_var_radio")
            _set_state(l3_map_var=map_var)

        loc_agg_dict: dict = {}
        for col in ["temp", "humidity", "rain", "wind_speed", "pressure", "cloud"]:
            if col not in prov_df.columns:
                continue
            fn = "sum" if col == "rain" else "mean"
            loc_agg_dict[col] = (col, fn)
        if "lat" in prov_df.columns:
            loc_agg_dict["lat"] = ("lat", "mean")
        if "lon" in prov_df.columns:
            loc_agg_dict["lon"] = ("lon", "mean")

        loc_summary = (
            prov_df.groupby("location", observed=True).agg(**loc_agg_dict).reset_index()
            if loc_agg_dict else pd.DataFrame()
        )

        with mv_col1:
            if not loc_summary.empty and has_coords and map_var in loc_summary.columns:
                loc_plot = loc_summary.dropna(subset=["lat", "lon", map_var])
                ws_size = (loc_plot["wind_speed"].fillna(5) / loc_plot["wind_speed"].max() * 18 + 6).clip(6, 24) if "wind_speed" in loc_plot.columns else 10

                fig_lmap = go.Figure(go.Scattermapbox(
                    lat=loc_plot["lat"], lon=loc_plot["lon"],
                    mode="markers",
                    marker=dict(
                        size=ws_size, opacity=0.9,
                        color=loc_plot[map_var],
                        colorscale=VAR_META[map_var].get("cs", "RdYlBu_r") or "RdYlBu_r",
                        showscale=True,
                        colorbar=dict(title=VAR_META[map_var]["unit"], thickness=10, len=0.65),
                    ),
                    text=loc_plot["location"],
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        f"{VAR_META[map_var]['label']}: %{{marker.color:.1f}} {VAR_META[map_var]['unit']}<extra></extra>"
                    ),
                ))
                fig_lmap.update_layout(
                    **_base_layout(height=380, margin=dict(l=0, r=0, t=10, b=0)),
                    mapbox=dict(
                        style="carto-positron", zoom=7,
                        center=dict(lat=float(loc_plot["lat"].mean()), lon=float(loc_plot["lon"].mean())),
                    ),
                )
                st.plotly_chart(fig_lmap, use_container_width=True, config={"displayModeBar": False})
            elif not loc_summary.empty and map_var in loc_summary.columns:
                # No coords — fallback horizontal bar
                ls_plot = loc_summary.dropna(subset=[map_var]).sort_values(map_var, ascending=True).tail(20)
                fig_fallback = go.Figure(go.Bar(
                    y=ls_plot["location"], x=ls_plot[map_var], orientation="h",
                    marker_color=VAR_META[map_var]["color"],
                    hovertemplate=f"%{{y}}<br>{VAR_META[map_var]['label']}: %{{x:.1f}}<extra></extra>",
                ))
                fig_fallback.update_layout(
                    **_base_layout(
                        height=max(320, len(ls_plot) * 22),
                        xaxis=_ax_cfg(VAR_META[map_var]['label']),
                        yaxis=_ax_cfg(),
                        margin=dict(l=150, r=10, t=20, b=10)
                    )
                )
                st.plotly_chart(fig_fallback, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 3 — Daily Timeline (Temp + Rain dual axis) ─────────────────────
    st.markdown("<div class='wx-section-title'>📅 Timeline hàng ngày (365 ngày)</div>", unsafe_allow_html=True)

    daily_agg_dict: dict = {}
    for col, fn in [("temp", "mean"), ("temp", "max"), ("temp", "min"), ("rain", "sum"),
                    ("humidity", "mean"), ("wind_speed", "mean")]:
        out = f"{col}_max" if fn == "max" else (f"{col}_min" if fn == "min" else (f"{col}_sum" if fn == "sum" else col))
        if col in prov_df.columns:
            daily_agg_dict[out] = (col, fn)

    daily_df = (
        prov_df.set_index("timestamp").resample("1D").agg(**daily_agg_dict).dropna(how="all").reset_index()
        if daily_agg_dict else pd.DataFrame()
    )

    if not daily_df.empty:
        fig_tl = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                               row_heights=[0.68, 0.32])
        if "temp" in daily_df.columns:
            fig_tl.add_trace(go.Scatter(
                x=daily_df["timestamp"], y=daily_df["temp"],
                mode="lines", name="Nhiệt độ TB",
                line=dict(color="#ef4444", width=1.8, shape="spline"),
                hovertemplate="%{x|%d/%m}<br>Nhiệt độ: %{y:.1f}°C<extra></extra>",
            ), row=1, col=1)
            if "temp_max" in daily_df.columns:
                fig_tl.add_trace(go.Scatter(
                    x=daily_df["timestamp"], y=daily_df["temp_max"],
                    mode="lines", name="Tmax",
                    line=dict(color="#fca5a5", width=1, dash="dot"),
                    hovertemplate="%{x|%d/%m}<br>Tmax: %{y:.1f}°C<extra></extra>",
                ), row=1, col=1)
            # Extreme heat markers (>38°C)
            if "temp_max" in daily_df.columns:
                hot = daily_df[daily_df["temp_max"] > 38]
                if not hot.empty:
                    fig_tl.add_trace(go.Scatter(
                        x=hot["timestamp"], y=hot["temp_max"],
                        mode="markers", name="🔴 Nóng cực đoan (>38°C)",
                        marker=dict(color="#dc2626", size=8, symbol="circle"),
                    ), row=1, col=1)

        if "rain_sum" in daily_df.columns or "rain" in daily_df.columns:
            rain_col = "rain_sum" if "rain_sum" in daily_df.columns else "rain"
            fig_tl.add_trace(go.Bar(
                x=daily_df["timestamp"], y=daily_df[rain_col],
                name="Lượng mưa (mm)",
                marker=dict(color="rgba(14,165,233,0.55)", line=dict(color="#0284c7", width=0.5)),
                hovertemplate="%{x|%d/%m}<br>Mưa: %{y:.1f} mm<extra></extra>",
            ), row=2, col=1)
            # Extreme rain markers (>100mm)
            heavy = daily_df[daily_df[rain_col] > 100]
            if not heavy.empty:
                fig_tl.add_trace(go.Scatter(
                    x=heavy["timestamp"], y=heavy[rain_col],
                    mode="markers", name="🔵 Mưa lớn (>100mm)",
                    marker=dict(color="#1d4ed8", size=8, symbol="diamond"),
                ), row=2, col=1)

        fig_tl.update_layout(
            **_base_layout(height=480, hovermode="x unified",
                           legend=dict(orientation="h", x=0, y=1.05, font=dict(size=9), bgcolor="rgba(0,0,0,0)")),
            xaxis2=_ax_cfg("Ngày"),
            yaxis=_ax_cfg("Nhiệt độ (°C)"),
            yaxis2=_ax_cfg("Mưa (mm)"),
            barmode="overlay",
        )
        st.plotly_chart(fig_tl, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 5 — Ward Ranking + Wind Rose ───────────────────────────────────
    col_wr2, col_ward = st.columns([1, 1], gap="medium")

    with col_wr2:
        st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='wx-card-header'><div class='wx-card-title'>{_icon('wind')} Hoa gió theo mùa</div></div>", unsafe_allow_html=True)

        wr_season = st.radio("Mùa:", ["Cả năm", "Mùa mưa (T5–T10)", "Mùa khô (T11–T4)", "Q1", "Q2", "Q3", "Q4"],
                              horizontal=True, key="l3_wr_season")
        wr_map = {
            "Cả năm": (1, 12), "Mùa mưa (T5–T10)": (5, 10), "Mùa khô (T11–T4)": None,
            "Q1": (1, 3), "Q2": (4, 6), "Q3": (7, 9), "Q4": (10, 12),
        }
        wr_src = prov_df.copy()
        if "wind_dir" in wr_src.columns:
            wr_src["month"] = pd.to_datetime(wr_src["timestamp"]).dt.month
            if wr_season == "Mùa khô (T11–T4)":
                wr_src = wr_src[(wr_src["month"] >= 11) | (wr_src["month"] <= 4)]
            elif wr_map.get(wr_season):
                ms, me = wr_map[wr_season]
                wr_src = wr_src[wr_src["month"].between(ms, me)]

            wr_valid = wr_src.dropna(subset=["wind_speed", "wind_dir"])
            if not wr_valid.empty:
                si = (((wr_valid["wind_dir"] % 360) + 11.25) // 22.5).astype(int) % 16
                wr_valid = wr_valid.copy()
                wr_valid["sector"] = si.map(dict(enumerate(WIND_SECTORS)))
                wr_valid["spd_bin"] = pd.cut(wr_valid["wind_speed"], bins=WIND_SPEED_BINS,
                                               labels=WIND_SPEED_LABELS, include_lowest=True, right=False)
                piv_wr = (
                    wr_valid.groupby(["sector", "spd_bin"], observed=False)
                    .size().unstack(fill_value=0)
                    .reindex(index=WIND_SECTORS, columns=WIND_SPEED_LABELS, fill_value=0)
                )
                clrs_wr = ["#bae6fd", "#7dd3fc", "#38bdf8", "#0ea5e9", "#0369a1"]
                fig_wr2 = go.Figure()
                for band, clr in zip(WIND_SPEED_LABELS, clrs_wr):
                    fig_wr2.add_trace(go.Barpolar(
                        r=piv_wr[band].values, theta=WIND_SECTORS, name=f"{band} m/s",
                        marker_color=clr, marker_line_color="rgba(255,255,255,0.7)",
                        marker_line_width=0.6, opacity=0.93,
                        hovertemplate="Hướng %{theta}<br>Tần suất: %{r}<extra></extra>",
                    ))
                fig_wr2.update_layout(
                    **_base_layout(height=340),
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(showticklabels=True, ticks="", gridcolor="rgba(0,0,0,0.08)", tickfont=dict(size=8)),
                        angularaxis=dict(direction="clockwise", rotation=90, gridcolor="rgba(0,0,0,0.06)", tickfont=dict(size=9)),
                    ),
                    legend=dict(orientation="h", x=0.2, y=-0.12, font=dict(size=9)),
                )
                st.plotly_chart(fig_wr2, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Không có dữ liệu wind_dir hợp lệ.")
        else:
            st.info("Không có cột wind_dir.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_ward:
        st.markdown("<div class='wx-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='wx-card-header'><div class='wx-card-title'>{_icon('chart')} Xếp hạng trạm/địa điểm</div></div>", unsafe_allow_html=True)

        if has_loc and not loc_summary.empty:
            ward_var = l3_primary_var
            ward_asc = st.checkbox("Sắp xếp tăng dần (mát/ít mưa nhất)", key="l3_ward_asc")

            # Limit Top 15
            ls_rank = loc_summary.dropna(subset=[ward_var]).sort_values(ward_var, ascending=ward_asc).head(15)
            wv_meta = VAR_META[ward_var]

            fig_ward = go.Figure(go.Bar(
                y=ls_rank["location"].str[:22], x=ls_rank[ward_var],
                orientation="h",
                marker=dict(
                    color=ls_rank[ward_var],
                    colorscale=wv_meta.get("cs", "RdYlBu_r") or "RdYlBu_r",
                    line=dict(width=0),
                ),
                hovertemplate=f"%{{y}}<br>{wv_meta['label']}: %{{x:.1f}} {wv_meta['unit']}<extra></extra>",
            ))
            fig_ward.update_layout(
                **_base_layout(
                    height=450,
                    xaxis=_ax_cfg(f"{wv_meta['label']} ({wv_meta['unit']})"),
                    yaxis=_ax_cfg(),
                    margin=dict(l=150, r=10, t=20, b=10),
                    showlegend=False,
                )
            )
            st.plotly_chart(fig_ward, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Không có dữ liệu theo địa điểm (location).")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Extreme Events Table ───────────────────────────────────────────────────
    st.markdown("<div class='wx-section-title'>⚠️ Sự kiện cực đoan</div>", unsafe_allow_html=True)
    prov_df["_date"] = pd.to_datetime(prov_df["timestamp"]).dt.date
    prov_df["_loc"]  = prov_df["location"].astype(str) if "location" in prov_df.columns else province

    extremes = []
    if "temp" in prov_df.columns:
        idx = prov_df["temp"].idxmax()
        r = prov_df.loc[idx]
        extremes.append({"Loại": "🌡 Nóng nhất", "Địa điểm": str(r["_loc"]), "Ngày": str(r["_date"]), "Giá trị": f"{_fmt(r['temp'], 1)} °C"})
        idx2 = prov_df["temp"].idxmin()
        r2 = prov_df.loc[idx2]
        extremes.append({"Loại": "❄ Lạnh nhất", "Địa điểm": str(r2["_loc"]), "Ngày": str(r2["_date"]), "Giá trị": f"{_fmt(r2['temp'], 1)} °C"})

    if "rain" in prov_df.columns:
        day_rain = prov_df.groupby(["_date", "_loc"], observed=True)["rain"].sum().reset_index()
        if not day_rain.empty:
            idx = day_rain["rain"].idxmax()
            r = day_rain.loc[idx]
            extremes.append({"Loại": "🌧 Mưa lớn nhất/ngày", "Địa điểm": str(r["_loc"]), "Ngày": str(r["_date"]), "Giá trị": f"{_fmt(r['rain'], 0)} mm"})

    if "wind_speed" in prov_df.columns:
        idx = prov_df["wind_speed"].idxmax()
        r = prov_df.loc[idx]
        extremes.append({"Loại": "💨 Gió mạnh nhất", "Địa điểm": str(r["_loc"]), "Ngày": str(r["_date"]), "Giá trị": f"{_fmt(r['wind_speed'], 1)} m/s"})

    if extremes:
        rows_html = "".join(
            f"<tr>"
            f"<td><b>{escape(e['Loại'])}</b></td>"
            f"<td>{escape(e['Địa điểm'])}</td>"
            f"<td>{escape(e['Ngày'])}</td>"
            f"<td><b style='color:#0f172a'>{escape(e['Giá trị'])}</b></td>"
            f"</tr>"
            for e in extremes
        )
        st.markdown(
            "<div class='wx-card'>"
            "<div class='wx-card-header'><div class='wx-card-title'>⚠️ Sự kiện cực đoan trong giai đoạn</div></div>"
            "<div class='wx-table-container'>"
            "<table class='wx-extreme-table'>"
            "<thead><tr><th>Loại</th><th>Địa điểm</th><th>Ngày</th><th>Giá trị</th></tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table></div></div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT — render(df)
# ═══════════════════════════════════════════════════════════════════════════════

def render(global_df: pd.DataFrame):
    """Main entry point called from the dashboard app."""
    _inject_css()

    # Load custom weather data instead of relying on global df
    with st.spinner("Đang tải dữ liệu thời tiết..."):
        df = load_weather_data()

    # ── Validate dataframe ────────────────────────────────────────────────────
    if df is None or df.empty:
        st.warning("Không có dữ liệu thời tiết.")
        return
    if "city" not in df.columns or "timestamp" not in df.columns:
        st.warning("Dữ liệu thiếu cột city/timestamp.")
        return

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "city"])
    for col in WEATHER_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "month" not in df.columns:
        df["month"] = df["timestamp"].dt.month

    # ── Session state initialisation ──────────────────────────────────────────
    layer    = _get_state("wx_layer",    1)
    province = _get_state("wx_province", None)

    # ── Routing ───────────────────────────────────────────────────────────────
    if layer == 3 and province:
        _render_layer3(df)
    elif layer == 2:
        _render_layer2(df, province)
    else:
        _render_layer1(df)
