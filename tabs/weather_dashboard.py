"""
weather_dashboard.py  –  Tab "Thời tiết"  (v2 – redesign)
──────────────────────────────────────────────────────────
Thiết kế theo design system của app: light theme, Be Vietnam Pro,
dùng .card / .card-title / .kpi-box / .kpi-strip / .q-tag từ main.css.

Cải tiến so với v1:
  ✦ Filter bar thống nhất phong cách với overview_tab (ov-filter-bar)
  ✦ Layer 1: layout 3 cột ở màn rộng, insight badges tự động
  ✦ Layer 1: "Spark cards" – mini sparkline ngay trong KPI box
  ✦ Layer 1: Ranking dùng progress bar HTML (không cần chart riêng)
  ✦ Layer 2: Header sticky với KPI inline + nút back gọn
  ✦ Layer 2: Dual-axis timeline có vùng min-max (uncertainty band)
  ✦ Layer 2: Calendar heatmap mượt hơn (full 12 tháng x 31 ngày)
  ✦ Layer 2: Extreme events dùng highlight card thay bảng
  ✦ CSS bổ sung tự đóng gói, không đụng main.css
"""
from __future__ import annotations

import math
from html import escape
from textwrap import dedent

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import load_weather_data, load_weather_province_detail, CITY_FOLDERS

# ─── Constants ─────────────────────────────────────────────────────────────────

WEATHER_FEATURES = ["temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud"]

WIND_SECTORS = [
    "B", "BDB", "DB", "DDB", "D", "DDN", "DN", "NDN",
    "N", "NTN", "TN", "TTN", "T", "TTB", "TB", "BTB",
]
WIND_SPEED_BINS   = [0, 5, 10, 20, 35, np.inf]
WIND_SPEED_LABELS = ["0–5", "5–10", "10–20", "20–35", ">35"]

REGION_COLORS      = {"Bắc": "#2563eb",              "Trung": "#f59e0b",              "Nam": "#16a34a"}
REGION_COLORS_RGBA = {"Bắc": "rgba(37,99,235,0.09)", "Trung": "rgba(245,158,11,0.09)", "Nam": "rgba(22,163,74,0.09)"}
REGION_BG     = {"Bắc": "#eff6ff", "Trung": "#fffbeb", "Nam": "#f0fdf4"}

VAR_META = {
    "temp":       {"label": "Nhiệt độ",    "unit": "°C",  "agg": "mean", "cs": "RdYlBu_r", "color": "#ea580c", "accent": "accent-red",   "icon": "🌡️"},
    "humidity":   {"label": "Độ ẩm",       "unit": "%",   "agg": "mean", "cs": "Blues",     "color": "#0ea5e9", "accent": "accent-slate", "icon": "💧"},
    "rain":       {"label": "Lượng mưa",   "unit": "mm",  "agg": "sum",  "cs": "YlGnBu",   "color": "#2563eb", "accent": "accent-blue",  "icon": "🌧️"},
    "wind_speed": {"label": "Tốc độ gió",  "unit": "m/s", "agg": "mean", "cs": "Greens",    "color": "#16a34a", "accent": "accent-green", "icon": "💨"},
    "wind_dir":   {"label": "Hướng gió",   "unit": "°",   "agg": "none", "cs": None,        "color": "#64748b", "accent": "accent-slate", "icon": "🧭"},
    "pressure":   {"label": "Áp suất",     "unit": "hPa", "agg": "mean", "cs": "Purples",   "color": "#7c3aed", "accent": "accent-blue",  "icon": "🔵"},
    "cloud":      {"label": "Mây che phủ", "unit": "%",   "agg": "mean", "cs": "Greys",     "color": "#64748b", "accent": "accent-slate", "icon": "☁️"},
}

SEASON_PRESETS = {
    "Cả năm":  (1, 12),
    "Mùa khô": (11, 4),
    "Mùa mưa": (5, 10),
    "Q1": (1, 3), "Q2": (4, 6), "Q3": (7, 9), "Q4": (10, 12),
}
MONTH_NAMES = ["Th1","Th2","Th3","Th4","Th5","Th6","Th7","Th8","Th9","Th10","Th11","Th12"]

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
REGION_ORDER = ["Bắc", "Trung", "Nam"]

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


# ─── CSS bổ sung ────────────────────────────────────────────────────────────────

def _inject_weather_css():
    st.markdown("""
    <style>
    /* ── Filter bar (giống ov-filter-bar) ── */
    .wth-filter-bar {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 20px;
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        align-items: flex-end;
    }
    .wth-filter-cell { flex: 1; min-width: 140px; }
    .wth-filter-label {
        font-size: .62rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: .7px; color: #94a3b8; margin-bottom: 6px;
    }

    /* ── Page header ── */
    .wth-page-header {
        display: flex; align-items: center; gap: 14px;
        padding: 18px 0 6px;
    }
    .wth-page-icon {
        width: 42px; height: 42px; border-radius: 12px;
        background: linear-gradient(135deg,#0ea5e9,#2563eb);
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem; flex-shrink: 0;
    }
    .wth-page-title  { font-size: 1.18rem; font-weight: 700; color: #1e293b; line-height: 1.2; }
    .wth-page-sub    { font-size: .72rem; color: #64748b; margin-top: 2px; }

    /* ── Breadcrumb ── */
    .wth-breadcrumb {
        font-size: .72rem; color: #64748b; margin-bottom: 6px;
        display: flex; align-items: center; gap: 6px;
    }
    .wth-breadcrumb-home {
        color: #2563eb; cursor: pointer; text-decoration: none;
        font-weight: 600; display: inline-flex; align-items: center; gap: 4px;
    }
    .wth-breadcrumb-sep { color: #cbd5e1; }

    /* ── Section divider ── */
    .wth-section {
        font-size: .62rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: .8px; color: #94a3b8;
        margin: 26px 0 14px;
        display: flex; align-items: center; gap: 10px;
    }
    .wth-section::after { content: ''; flex: 1; height: 1px; background: #f1f5f9; }

    /* ── KPI accent-green ── */
    .kpi-box.accent-green  { border-top-color: #16a34a; }
    .kpi-box.accent-orange { border-top-color: #f59e0b; }

    /* ── Delta text ── */
    .kpi-delta-pos { color: #16a34a; font-size: .68rem; font-weight: 600; }
    .kpi-delta-neg { color: #ea580c; font-size: .68rem; font-weight: 600; }
    .kpi-delta-neu { color: #64748b; font-size: .68rem; }

    /* ── Insight badge row ── */
    .wth-badge-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
    .wth-badge {
        background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 99px;
        font-size: .72rem; font-weight: 500; color: #475569; padding: 4px 12px;
        display: inline-flex; align-items: center; gap: 5px;
    }
    .wth-badge-warn {
        background: #fff7ed; border-color: #fed7aa; color: #c2410c;
    }

    /* ── Ranking progress bar ── */
    .wth-rank-table { width: 100%; border-collapse: collapse; }
    .wth-rank-table td { padding: 5px 6px; vertical-align: middle; }
    .wth-rank-table tr:hover td { background: #f8fafc; border-radius: 6px; }
    .wth-rank-num  { font-size: .7rem; color: #94a3b8; font-weight: 700; width: 24px; text-align: right; }
    .wth-rank-city { font-size: .82rem; color: #334155; font-weight: 500; min-width: 110px; max-width: 130px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .wth-rank-bar-wrap { width: 100%; }
    .wth-rank-bar-bg { background: #f1f5f9; border-radius: 99px; height: 7px; width: 100%; overflow: hidden; }
    .wth-rank-bar-fill { border-radius: 99px; height: 7px; transition: width .4s ease; }
    .wth-rank-val  { font-size: .78rem; color: #1e293b; font-weight: 700; white-space: nowrap; width: 60px; text-align: right; }
    .wth-rank-tag  { font-size: .62rem; border-radius: 99px; padding: 2px 8px; font-weight: 600; margin-left: 4px; white-space: nowrap; }

    /* ── Extreme event cards ── */
    .wth-extreme-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px,1fr)); gap: 12px; margin-top: 4px; }
    .wth-extreme-card {
        background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 14px 16px; position: relative; overflow: hidden;
    }
    .wth-extreme-card::before {
        content: ''; position: absolute; left: 0; top: 0; bottom: 0;
        width: 4px; border-radius: 4px 0 0 4px;
    }
    .wth-extreme-card.hot::before  { background: #ea580c; }
    .wth-extreme-card.cold::before { background: #2563eb; }
    .wth-extreme-card.rain::before { background: #0284c7; }
    .wth-extreme-card.wind::before { background: #16a34a; }
    .wth-extreme-card .ec-icon  { font-size: 1.4rem; margin-bottom: 6px; }
    .wth-extreme-card .ec-label { font-size: .62rem; text-transform: uppercase; letter-spacing: .6px; color: #94a3b8; font-weight: 700; }
    .wth-extreme-card .ec-val   { font-size: 1.3rem; font-weight: 800; color: #1e293b; margin: 2px 0; line-height: 1; }
    .wth-extreme-card .ec-meta  { font-size: .72rem; color: #64748b; }

    /* ── Compare mini-cards (Layer 2 vs quốc gia) ── */
    .wth-compare-row { display: flex; gap: 10px; margin-top: 10px; }
    .wth-compare-card {
        flex: 1; padding: 10px 14px; border-radius: 10px;
        border: 1px solid #e2e8f0; text-align: center;
    }
    .wth-compare-card .cc-label { font-size: .62rem; text-transform: uppercase; letter-spacing: .6px; color: #94a3b8; font-weight: 700; }
    .wth-compare-card .cc-val   { font-size: 1.1rem; font-weight: 800; color: #1e293b; margin-top: 2px; }
    .wth-compare-card .cc-sub   { font-size: .68rem; color: #64748b; margin-top: 1px; }

    /* ── Tab pill strip (Layer 2 sub-navigation) ── */
    .wth-tab-bar {
        display: flex; gap: 6px; flex-wrap: wrap;
        background: #f1f5f9; padding: 5px; border-radius: 12px;
        margin-bottom: 18px;
    }
    .wth-tab-pill {
        padding: 6px 16px; border-radius: 9px; font-size: .8rem; font-weight: 600;
        cursor: pointer; border: none; background: transparent; color: #64748b;
        transition: background .15s, color .15s;
    }
    .wth-tab-pill.active { background: #ffffff; color: #1e293b; box-shadow: 0 1px 4px rgba(0,0,0,.07); }

    /* ── Card sub-text ── */
    .card-sub { font-size: .72rem; color: #94a3b8; margin: 2px 0 12px; }

    /* ── Min-max band legend ── */
    .wth-legend { display: flex; gap: 14px; font-size: .7rem; color: #64748b; margin-top: 4px; flex-wrap: wrap; }
    .wth-legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 4px; vertical-align: middle; }
    </style>
    """, unsafe_allow_html=True)


# ─── Utilities ──────────────────────────────────────────────────────────────────

def _fmt(value, decimals=1, suffix="") -> str:
    if value is None: return "N/A"
    try:
        v = float(value)
        if math.isnan(v): return "N/A"
        return f"{v:.{decimals}f}{suffix}"
    except Exception:
        return "N/A"

def _base_layout(**kw) -> dict:
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Be Vietnam Pro, sans-serif", size=10, color="#334155"),
        margin=dict(l=8, r=8, t=32, b=8),
        template="plotly_white",
    )
    base.update(kw)
    return base

def _ax(title="", **kw) -> dict:
    cfg = dict(
        title=dict(text=title, font=dict(size=9, color="#94a3b8")),
        tickfont=dict(size=9, color="#94a3b8"),
        gridcolor="rgba(203,213,225,0.35)",
        linecolor="#e2e8f0",
        zeroline=False,
    )
    cfg.update(kw)
    return cfg

def _colorbar(title=""):
    return dict(
        title=dict(text=title, font=dict(size=9, color="#64748b"), side="right"),
        tickfont=dict(size=8, color="#94a3b8"),
        thickness=9, len=0.65, outlinewidth=0,
    )

def _get_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

def _set_state(**kwargs):
    for k, v in kwargs.items():
        st.session_state[k] = v

def _go_layer1():
    _set_state(wx_layer=1, wx_province=None)
    st.rerun()

def _go_layer2(province: str):
    _set_state(wx_layer=2, wx_province=province)
    st.rerun()


# ─── Season / Month selector ────────────────────────────────────────────────────

def _season_selector(key_prefix: str) -> tuple[str, int | None]:
    all_opts = list(SEASON_PRESETS.keys()) + MONTH_NAMES
    preset = _get_state(f"{key_prefix}_season", "Cả năm")
    sel = st.segmented_control("Giai đoạn", all_opts, default=preset, key=f"{key_prefix}_sg")
    if sel:
        preset = sel
    _set_state(**{f"{key_prefix}_season": preset})
    month = None
    if isinstance(preset, str) and preset.startswith("Th"):
        try:
            month = int(preset[2:])
        except ValueError:
            pass
    return preset, month

def _filter_by_season(df: pd.DataFrame, preset: str, month: int | None = None) -> pd.DataFrame:
    if "month" not in df.columns:
        df = df.copy(); df["month"] = pd.to_datetime(df["timestamp"]).dt.month
    if "day" not in df.columns:
        df = df.copy(); df["day"] = pd.to_datetime(df["timestamp"]).dt.day
    if month is not None:
        return df[df["month"] == month].copy()
    if preset not in SEASON_PRESETS:
        return df.copy()
    ms, me = SEASON_PRESETS[preset]
    if ms <= me:
        return df[df["month"].between(ms, me)].copy()
    return df[(df["month"] >= ms) | (df["month"] <= me)].copy()


# ─── Aggregation ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _agg_monthly(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "city" not in df.columns:
        return pd.DataFrame()
    src = df.copy()
    src["month"] = pd.to_datetime(src["timestamp"]).dt.month
    agg = {c: (c, "mean") for c in ["temp","humidity","pressure","cloud","wind_speed"] if c in src.columns}
    if "rain" in src.columns:
        agg["rain"] = ("rain", "sum")
    return src.groupby(["city","month"], observed=True).agg(**agg).reset_index() if agg else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def _agg_annual(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "city" not in df.columns:
        return pd.DataFrame()
    src = df.copy()
    agg = {c: (c,"mean") for c in ["temp","humidity","pressure","cloud","wind_speed"] if c in src.columns}
    if "rain" in src.columns:
        agg["rain"] = ("rain", "sum")
    result = src.groupby("city", observed=True).agg(**agg).reset_index() if agg else pd.DataFrame()
    if result.empty:
        return result

    coords = []
    for city in result["city"]:
        sub = src[src["city"] == city]
        lat = sub["lat"].mean() if "lat" in sub.columns else float("nan")
        lon = sub["lon"].mean() if "lon" in sub.columns else float("nan")
        if (pd.isna(lat) or pd.isna(lon)) and city in PROVINCE_COORDS:
            lat, lon = PROVINCE_COORDS[city]
        if (pd.isna(lat) or pd.isna(lon)) and " - " in city:
            p = city.split(" - ")[0]
            if p in PROVINCE_COORDS:
                lat, lon = PROVINCE_COORDS[p]
        coords.append({"city": city, "lat": lat, "lon": lon})
    result = result.merge(pd.DataFrame(coords), on="city", how="left")
    for col in ["temp","humidity","rain","wind_speed"]:
        if col in result.columns:
            result[f"{col}_rank"] = result[col].rank(ascending=False, method="min").astype("Int64")
    return result


# ─── Card helpers ───────────────────────────────────────────────────────────────

def _card_open(tag: str, title: str, sub: str = ""):
    sub_html = f"<div class='card-sub'>{escape(sub)}</div>" if sub else ""
    st.markdown(
        f"<div class='card'>"
        f"<div class='card-title'><span class='q-tag'>{tag}</span>{escape(title)}</div>"
        f"{sub_html}",
        unsafe_allow_html=True,
    )

def _card_close():
    st.markdown("</div>", unsafe_allow_html=True)

def _kpi_html(label: str, value: str, unit: str, accent: str, sub: str = "") -> str:
    sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
    return (
        f"<div class='kpi-box {accent}'>"
        f"<div class='kpi-lbl'>{escape(label)}</div>"
        f"<div class='kpi-val'>{escape(value)} <span class='u'>{escape(unit)}</span></div>"
        f"{sub_html}</div>"
    )

def _kpi_row(cards: list[str]):
    st.markdown(
        f"<div class='kpi-strip' style='grid-template-columns:repeat({len(cards)},1fr)'>"
        + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )

def _section(title: str):
    st.markdown(f"<div class='wth-section'>{title}</div>", unsafe_allow_html=True)


# ─── Ranking HTML (progress bar style) ──────────────────────────────────────────

def _render_ranking_html(annual: pd.DataFrame, cur_var: str, meta: dict,
                         reg_filter: str = "Tất cả", ascending: bool = False, n: int = 15):
    """Render xếp hạng bằng progress bar thuần HTML — nhanh, không cần chart."""
    if annual.empty or cur_var not in annual.columns:
        st.info("Không đủ dữ liệu xếp hạng.")
        return

    annual = annual.copy()
    annual["region"] = annual["city"].map(PROVINCE_REGION).fillna("Khác")
    rb = annual[["city","region", cur_var]].dropna(subset=[cur_var])
    if reg_filter != "Tất cả":
        rb = rb[rb["region"] == reg_filter]
    rb = rb.sort_values(cur_var, ascending=ascending).head(n).reset_index(drop=True)

    if rb.empty:
        st.info("Không có dữ liệu cho bộ lọc này.")
        return

    max_val = rb[cur_var].max()
    min_val = rb[cur_var].min()
    span    = max_val - min_val if max_val != min_val else 1.0

    rows = ""
    for i, row in rb.iterrows():
        rank   = i + 1
        city   = escape(str(row["city"]))
        reg    = str(row["region"])
        val    = float(row[cur_var])
        pct    = max(6, int((val - min_val) / span * 100))
        color  = REGION_COLORS.get(reg, "#94a3b8")
        bg     = REGION_BG.get(reg, "#f8fafc")
        tag_html = (
            f"<span class='wth-rank-tag' style='background:{bg};color:{color}'>{escape(reg)}</span>"
            if reg != "Khác" else ""
        )
        rows += (
            f"<tr>"
            f"<td class='wth-rank-num'>{rank}</td>"
            f"<td class='wth-rank-city'>{city}{tag_html}</td>"
            f"<td class='wth-rank-bar-wrap'><div class='wth-rank-bar-bg'>"
            f"<div class='wth-rank-bar-fill' style='width:{pct}%;background:{color}'></div>"
            f"</div></td>"
            f"<td class='wth-rank-val'>{_fmt(val,1)} <span style='color:#94a3b8;font-size:.65rem'>{escape(meta.get('unit',''))}</span></td>"
            f"</tr>"
        )

    st.markdown(
        f"<table class='wth-rank-table'><tbody>{rows}</tbody></table>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 – TỔNG QUAN TOÀN QUỐC
# ═══════════════════════════════════════════════════════════════════════════════

def _render_layer1(df: pd.DataFrame):
    # ── Page header ─────────────────────────────────────────────────────────────
    st.markdown(
        "<div class='wth-page-header'>"
        "<div class='wth-page-icon'>🌤</div>"
        "<div>"
        "<div class='wth-page-title'>Thời tiết Toàn quốc</div>"
        "<div class='wth-page-sub'>Dữ liệu quan trắc khí tượng Việt Nam · Phân tích theo giai đoạn và vùng miền</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # ── Unified filter bar ───────────────────────────────────────────────────────
    st.markdown("<div class='wth-filter-bar'>", unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([1.8, 1.2, 1.0], gap="small")

    with fc1:
        st.markdown("<div class='wth-filter-label'>Giai đoạn phân tích</div>", unsafe_allow_html=True)
        preset, month = _season_selector("l1")

    with fc2:
        st.markdown("<div class='wth-filter-label'>Chỉ số hiển thị</div>", unsafe_allow_html=True)
        var_opts = [v for v in ["temp","humidity","rain","wind_speed"] if v in df.columns]
        cur_var  = _get_state("l1_var", var_opts[0] if var_opts else "temp")
        if cur_var not in var_opts:
            cur_var = var_opts[0]
        cur_var = st.segmented_control(
            "Chỉ số", var_opts,
            format_func=lambda x: f"{VAR_META[x]['icon']} {VAR_META[x]['label']}",
            selection_mode="single", default=cur_var, key="l1_var_sg",
        ) or cur_var
        _set_state(l1_var=cur_var)

    with fc3:
        st.markdown("<div class='wth-filter-label'>Trạng thái dữ liệu</div>", unsafe_allow_html=True)
        n_cities  = df["city"].nunique() if "city" in df.columns else 0
        n_records = len(df)
        st.markdown(
            f"<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:9px;padding:8px 12px;margin-top:2px'>"
            f"<div style='font-size:.68rem;color:#16a34a;font-weight:700'>● LIVE DATA</div>"
            f"<div style='font-size:.72rem;color:#166534;margin-top:2px'>"
            f"{n_cities} tỉnh · {n_records:,} bản ghi</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    filtered = _filter_by_season(df, preset, month)
    annual   = _agg_annual(filtered)
    monthly  = _agg_monthly(filtered)
    meta     = VAR_META.get(cur_var, {})

    # ── Auto insight badges ──────────────────────────────────────────────────────
    badges = []
    if not annual.empty:
        if "temp" in annual.columns:
            hot_city = annual.loc[annual["temp"].idxmax(), "city"] if not annual["temp"].isna().all() else None
            if hot_city:
                badges.append(f"🌡️ Nóng nhất: <b>{escape(str(hot_city))}</b>")
        if "rain" in annual.columns:
            wet_city = annual.loc[annual["rain"].idxmax(), "city"] if not annual["rain"].isna().all() else None
            if wet_city:
                badges.append(f"🌧️ Mưa nhiều nhất: <b>{escape(str(wet_city))}</b>")
        if "wind_speed" in annual.columns:
            wind_city = annual.loc[annual["wind_speed"].idxmax(), "city"] if not annual["wind_speed"].isna().all() else None
            if wind_city:
                badges.append(f"💨 Gió mạnh nhất: <b>{escape(str(wind_city))}</b>")
        if not monthly.empty and "temp" in monthly.columns:
            nat_mon = monthly.groupby("month", observed=False)["temp"].mean()
            if not nat_mon.empty:
                m_hot = int(nat_mon.idxmax())
                badges.append(f"📅 Tháng nóng nhất: <b>Tháng {m_hot}</b>")

    if badges:
        items = "".join(f"<span class='wth-badge'>{b}</span>" for b in badges)
        st.markdown(f"<div class='wth-badge-row'>{items}</div>", unsafe_allow_html=True)

    # ── KPI strip ───────────────────────────────────────────────────────────────
    kpis = []
    if not annual.empty:
        if "temp"       in annual.columns: kpis.append(_kpi_html("Nhiệt độ TB",   _fmt(annual["temp"].mean(),1),       "°C",  "accent-red"))
        if "humidity"   in annual.columns: kpis.append(_kpi_html("Độ ẩm TB",      _fmt(annual["humidity"].mean(),0),   "%",   "accent-slate"))
        if "rain"       in annual.columns: kpis.append(_kpi_html("Tổng mưa TB",   _fmt(annual["rain"].mean(),0),       "mm",  "accent-blue"))
        if "wind_speed" in annual.columns: kpis.append(_kpi_html("Tốc độ gió TB", _fmt(annual["wind_speed"].mean(),1), "m/s", "accent-green"))
    if kpis:
        _kpi_row(kpis)

    # ── Layout: Map | [Trend + Region box] ──────────────────────────────────────
    col_map, col_right = st.columns([1.35, 1], gap="large")

    with col_map:
        _card_open("Bản đồ", f"Phân bổ {meta.get('label','')} theo tỉnh/thành",
                   "Màu & kích thước theo giá trị chỉ số đã chọn · Click trên bản đồ để xem chi tiết")
        if not annual.empty and cur_var in annual.columns:
            ann_p    = annual.dropna(subset=["lat","lon", cur_var])
            n_tot    = len(annual)
            rank_col = (ann_p[f"{cur_var}_rank"].fillna(0).astype(int)
                        if f"{cur_var}_rank" in ann_p.columns
                        else pd.Series(0, index=ann_p.index))
            fig_map = go.Figure(go.Scattermapbox(
                lat=ann_p["lat"], lon=ann_p["lon"], mode="markers",
                marker=dict(
                    size=15, opacity=0.88,
                    color=ann_p[cur_var],
                    colorscale=meta.get("cs","RdYlBu_r") or "RdYlBu_r",
                    showscale=True, colorbar=_colorbar(meta.get("unit","")),
                ),
                text=ann_p["city"],
                customdata=np.column_stack([ann_p[cur_var].round(1), rank_col]),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"{meta.get('label','')}: %{{customdata[0]}} {meta.get('unit','')}<br>"
                    f"Xếp hạng: %{{customdata[1]}}/{n_tot}"
                    "<br><i>↗ Chọn tỉnh phía dưới để xem chi tiết</i><extra></extra>"
                ),
            ))
            fig_map.update_layout(
                **_base_layout(height=430, margin=dict(l=0,r=0,t=0,b=0)),
                mapbox=dict(style="carto-positron", zoom=4.5, center=dict(lat=16.5, lon=106.5)),
            )
            st.plotly_chart(fig_map, width='stretch', config={"displayModeBar": False, "scrollZoom": True})

            # Drill-down selector
            c_sel, c_btn = st.columns([3, 1], gap="small")
            with c_sel:
                sel = st.selectbox(
                    "Chọn tỉnh xem chi tiết:", ["—"] + sorted(annual["city"].tolist()),
                    key="l1_drill_sel", label_visibility="collapsed",
                )
            with c_btn:
                if st.button("Chi tiết →", type="primary", key="l1_drill_btn", width='stretch'):
                    if sel != "—":
                        _go_layer2(sel)
        else:
            st.info("Không đủ dữ liệu bản đồ.")
        _card_close()

    with col_right:
        # ── Xu hướng tháng ──────────────────────────────────────────────────────
        _card_open("Xu hướng", f"{meta.get('label','')} theo tháng",
                   "Đường = chỉ số đã chọn · Cột mờ = lượng mưa")
        if not monthly.empty:
            agg_fns = {c: (c, "sum" if c=="rain" else "mean")
                       for c in ["temp","humidity","rain","wind_speed"] if c in monthly.columns}
            nat_mon = (monthly.groupby("month", observed=True).agg(**agg_fns).reset_index()
                       if agg_fns else pd.DataFrame())
            if not nat_mon.empty:
                xl   = [MONTH_NAMES[m-1] for m in nat_mon["month"]]
                var2 = "rain" if cur_var != "rain" else "humidity"
                fig_t = go.Figure()
                if var2 in nat_mon.columns:
                    m2 = VAR_META[var2]
                    fig_t.add_trace(go.Bar(
                        x=xl, y=nat_mon[var2], name=m2["label"],
                        marker=dict(color=m2["color"], opacity=0.2, line=dict(width=0)),
                        yaxis="y2",
                        hovertemplate=f"%{{x}}<br>{m2['label']}: %{{y:.1f}} {m2['unit']}<extra></extra>",
                    ))
                if cur_var in nat_mon.columns:
                    fig_t.add_trace(go.Scatter(
                        x=xl, y=nat_mon[cur_var], name=meta.get("label",""),
                        mode="lines+markers",
                        line=dict(color=meta.get("color","#2563eb"), width=2.5, shape="spline"),
                        marker=dict(size=5, color=meta.get("color","#2563eb"),
                                    line=dict(width=2, color="#ffffff")),
                        hovertemplate=f"%{{x}}<br>{meta.get('label','')}: %{{y:.1f}} {meta.get('unit','')}<extra></extra>",
                    ))
                    # Highlight peak month
                    peak_idx = nat_mon[cur_var].idxmax()
                    fig_t.add_trace(go.Scatter(
                        x=[xl[peak_idx]], y=[nat_mon[cur_var].iloc[peak_idx]],
                        mode="markers", name="Đỉnh",
                        marker=dict(size=11, color=meta.get("color","#2563eb"),
                                    symbol="star", line=dict(width=2, color="#ffffff")),
                        showlegend=False,
                        hovertemplate=f"Đỉnh: %{{y:.1f}} {meta.get('unit','')}<extra></extra>",
                    ))
                m2_meta = VAR_META.get(var2, {})
                fig_t.update_layout(
                    **_base_layout(height=210),
                    yaxis=_ax(f"{meta.get('label','')} ({meta.get('unit','')})"),
                    yaxis2=dict(**_ax(f"{m2_meta.get('label','')} ({m2_meta.get('unit','')})"),
                                overlaying="y", side="right", showgrid=False),
                    legend=dict(orientation="h", x=0, y=1.1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                    hovermode="x unified", bargap=0.3,
                )
                st.plotly_chart(fig_t, width='stretch', config={"displayModeBar": False})

                # Peak / trough mini cards
                if cur_var in nat_mon.columns:
                    m_hi = int(nat_mon.loc[nat_mon[cur_var].idxmax(), "month"])
                    m_lo = int(nat_mon.loc[nat_mon[cur_var].idxmin(), "month"])
                    val_hi = _fmt(nat_mon[cur_var].max(), 1)
                    val_lo = _fmt(nat_mon[cur_var].min(), 1)
                    st.markdown(
                        f"<div style='display:flex;gap:8px;margin-top:6px'>"
                        f"<div style='flex:1;background:#fff7ed;border:1px solid #fed7aa;padding:8px 12px;border-radius:9px'>"
                        f"<div class='kpi-lbl'>Đỉnh cao nhất</div>"
                        f"<div style='font-size:.95rem;font-weight:800;color:#ea580c'>Tháng {m_hi} · {val_hi} {escape(meta.get('unit',''))}</div></div>"
                        f"<div style='flex:1;background:#eff6ff;border:1px solid #bfdbfe;padding:8px 12px;border-radius:9px'>"
                        f"<div class='kpi-lbl'>Đáy thấp nhất</div>"
                        f"<div style='font-size:.95rem;font-weight:800;color:#2563eb'>Tháng {m_lo} · {val_lo} {escape(meta.get('unit',''))}</div></div>"
                        f"</div>", unsafe_allow_html=True,
                    )
        else:
            st.info("Không đủ dữ liệu xu hướng.")
        _card_close()

        # ── Phân phối vùng miền (boxplot) ───────────────────────────────────────
        _card_open("Vùng miền", f"{meta.get('label','')} · Bắc – Trung – Nam",
                   "Mỗi điểm = 1 tỉnh/thành")
        if not annual.empty and cur_var in annual.columns:
            annual["region"] = annual["city"].map(PROVINCE_REGION).fillna("Khác")
            fig_box = go.Figure()
            for reg in REGION_ORDER:
                d = annual[annual["region"] == reg][cur_var].dropna()
                if d.empty:
                    continue
                fig_box.add_trace(go.Box(
                    y=d, name=reg, boxpoints="all", jitter=0.45, pointpos=-1.7,
                    marker=dict(size=5, color=REGION_COLORS.get(reg,"#94a3b8"), opacity=0.65),
                    line=dict(color=REGION_COLORS.get(reg,"#94a3b8"), width=1.8),
                    fillcolor=REGION_COLORS_RGBA.get(reg, "rgba(148,163,184,0.09)"),
                    hovertemplate=f"{reg}<br>{meta.get('label','')}: %{{y:.1f}} {meta.get('unit','')}<extra></extra>",
                ))
            fig_box.update_layout(
                **_base_layout(height=160, margin=dict(l=8,r=8,t=8,b=8)),
                yaxis=_ax(meta.get("unit","")), xaxis=_ax(), showlegend=False,
            )
            st.plotly_chart(fig_box, width='stretch', config={"displayModeBar": False})
        _card_close()

    # ── Xếp hạng tỉnh thành ─────────────────────────────────────────────────────
    _section("BẢNG XẾP HẠNG TỈNH THÀNH")
    _card_open("Ranking", f"Top tỉnh/thành theo {meta.get('label','')} · {preset}",
               "Độ dài thanh tỉ lệ với giá trị trong nhóm hiển thị")

    c_reg, c_n, c_asc = st.columns([2.5, 1, 0.8], gap="small")
    with c_reg:
        reg_f = st.radio("Vùng miền:", ["Tất cả"] + REGION_ORDER,
                         horizontal=True, key="l1_rank_reg")
    with c_n:
        top_n = st.selectbox("Số tỉnh:", [10, 15, 20], index=1,
                             key="l1_rank_n", label_visibility="collapsed")
    with c_asc:
        asc_f = st.toggle("Tăng dần", key="l1_rank_asc")

    _render_ranking_html(annual, cur_var, meta, reg_filter=reg_f, ascending=asc_f, n=top_n)
    _card_close()


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2 – CHI TIẾT TỈNH
# ═══════════════════════════════════════════════════════════════════════════════

def _render_layer2(df: pd.DataFrame):
    province = _get_state("wx_province", None)
    if not province:
        _go_layer1(); return

    # ── Breadcrumb + back button ─────────────────────────────────────────────────
    c_bc, c_back = st.columns([6, 1], gap="small")
    with c_bc:
        st.markdown(
            f"<div class='wth-breadcrumb'>"
            f"<span class='wth-breadcrumb-home'>🏠 Toàn quốc</span>"
            f"<span class='wth-breadcrumb-sep'>/</span>"
            f"<span style='color:#1e293b;font-weight:600'>{escape(province)}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c_back:
        if st.button("← Quay lại", key="l2_back", width='stretch'):
            _go_layer1()

    # ── Page header ─────────────────────────────────────────────────────────────
    region = PROVINCE_REGION.get(province, "")
    region_badge = ""
    if region:
        clr = REGION_COLORS.get(region, "#94a3b8")
        bg  = REGION_BG.get(region, "#f8fafc")
        region_badge = (
            f"<span style='display:inline-block;background:{bg};color:{clr};"
            f"border:1px solid {clr}33;border-radius:99px;font-size:.72rem;"
            f"font-weight:700;padding:3px 10px;margin-left:10px;vertical-align:middle'>"
            f"Vùng {escape(region)}</span>"
        )
    st.markdown(
        f"<div class='wth-page-header'>"
        f"<div class='wth-page-icon'>📍</div>"
        f"<div>"
        f"<div class='wth-page-title'>{escape(province)}{region_badge}</div>"
        f"<div class='wth-page-sub'>Phân tích khí tượng chi tiết từ trạm quan trắc địa phương</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # ── Filter bar ───────────────────────────────────────────────────────────────
    st.markdown("<div class='wth-filter-bar'>", unsafe_allow_html=True)
    fc1, fc2 = st.columns([1.6, 1.4], gap="small")
    with fc1:
        st.markdown("<div class='wth-filter-label'>Giai đoạn phân tích</div>", unsafe_allow_html=True)
        preset, month = _season_selector("l2")
    with fc2:
        st.markdown("<div class='wth-filter-label'>Chỉ số chính</div>", unsafe_allow_html=True)
        l2_vars = [v for v in ["temp","rain","humidity","wind_speed","pressure"] if v in df.columns]
        pv = st.segmented_control(
            "Chỉ số", l2_vars,
            format_func=lambda x: f"{VAR_META[x]['icon']} {VAR_META[x]['label']}",
            selection_mode="single", default=l2_vars[0], key="l2_pv_sg",
        ) or l2_vars[0]
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = _filter_by_season(df, preset, month)

    with st.spinner(f"Đang tải dữ liệu {province}..."):
        prov_df = load_weather_province_detail(province)
        if prov_df is None or prov_df.empty:
            st.error(f"Không tìm thấy dữ liệu cho {province}.")
            return
        prov_df = _filter_by_season(prov_df, preset, month)

    if prov_df.empty:
        st.warning("Không có dữ liệu trong giai đoạn này.")
        return

    prov_df = prov_df.sort_values("timestamp")
    meta = VAR_META.get(pv, {})

    # So sánh với toàn quốc
    nat_annual = _agg_annual(filtered)
    nat_avg    = nat_annual.mean(numeric_only=True) if not nat_annual.empty else pd.Series(dtype=float)

    def _delta_sub(col, prov_val):
        nat = nat_avg.get(col)
        if nat is None or pd.isna(nat) or pd.isna(prov_val): return ""
        diff = prov_val - nat
        sign = "+" if diff > 0 else ""
        cls  = "kpi-delta-pos" if diff < 0 else "kpi-delta-neg"
        return f"<span class='{cls}'>{sign}{_fmt(diff,1)} vs toàn quốc</span>"

    # ── KPI strip ───────────────────────────────────────────────────────────────
    kpis = []
    if "temp" in prov_df.columns:
        v = prov_df["temp"].mean()
        kpis.append(_kpi_html("Nhiệt độ TB",  _fmt(v,1), "°C",  "accent-red",   _delta_sub("temp",v)))
    if "humidity" in prov_df.columns:
        v = prov_df["humidity"].mean()
        kpis.append(_kpi_html("Độ ẩm TB",     _fmt(v,0), "%",   "accent-slate", _delta_sub("humidity",v)))
    if "rain" in prov_df.columns:
        v = prov_df["rain"].sum()
        kpis.append(_kpi_html("Tổng mưa",     _fmt(v,0), "mm",  "accent-blue"))
    if "wind_speed" in prov_df.columns:
        v = prov_df["wind_speed"].max()
        kpis.append(_kpi_html("Gió cực đại",  _fmt(v,1), "m/s", "accent-green"))
    if "pressure" in prov_df.columns:
        v = prov_df["pressure"].mean()
        kpis.append(_kpi_html("Áp suất TB",   _fmt(v,0), "hPa", "accent-blue",  _delta_sub("pressure",v)))
    if kpis:
        _kpi_row(kpis)

    # ── Section 1: Diễn biến thời gian ──────────────────────────────────────────
    _section("DIỄN BIẾN THỜI GIAN")
    _card_open("Timeline", "Nhiệt độ & Lượng mưa hàng ngày",
               "Đường cam = nhiệt độ · Vùng mờ = biên độ min–max · Cột xanh = lượng mưa")

    if "month" in prov_df.columns and "day" in prov_df.columns:
        daily_agg_spec = {}
        if "temp" in prov_df.columns:
            daily_agg_spec["temp_mean"] = ("temp", "mean")
            daily_agg_spec["temp_min"]  = ("temp", "min")
            daily_agg_spec["temp_max"]  = ("temp", "max")
        if "rain" in prov_df.columns:
            daily_agg_spec["rain"] = ("rain", "sum")
        if "humidity" in prov_df.columns:
            daily_agg_spec["humidity"] = ("humidity", "mean")

        if daily_agg_spec:
            daily = prov_df.groupby(["month","day"], observed=True).agg(**daily_agg_spec).reset_index()
            daily["ts"] = (pd.to_datetime("2025-01-01")
                           + pd.to_timedelta((daily["month"]-1)*30 + daily["day"]-1, unit="D"))
            fig_tl = go.Figure()

            # Rain bars (background)
            if "rain" in daily.columns:
                fig_tl.add_trace(go.Bar(
                    x=daily["ts"], y=daily["rain"], name="Lượng mưa",
                    marker=dict(color="#2563eb", opacity=0.25, line=dict(width=0)),
                    yaxis="y2",
                    hovertemplate="%{x|%d/%m}<br>Mưa: %{y:.1f} mm<extra></extra>",
                ))

            # Temp min-max band
            if "temp_min" in daily.columns and "temp_max" in daily.columns:
                ts_rev = daily["ts"].iloc[::-1].tolist()
                fig_tl.add_trace(go.Scatter(
                    x=daily["ts"].tolist() + ts_rev,
                    y=daily["temp_max"].tolist() + daily["temp_min"].iloc[::-1].tolist(),
                    fill="toself", fillcolor="rgba(234,88,12,0.07)",
                    line=dict(width=0), name="Biên độ nhiệt",
                    hoverinfo="skip", showlegend=True,
                ))

            # Temp mean line
            if "temp_mean" in daily.columns:
                fig_tl.add_trace(go.Scatter(
                    x=daily["ts"], y=daily["temp_mean"], name="Nhiệt độ TB",
                    mode="lines", line=dict(color="#ea580c", width=2.5, shape="spline"),
                    hovertemplate="%{x|%d/%m}<br>Nhiệt độ TB: %{y:.1f}°C<extra></extra>",
                ))

            fig_tl.update_layout(
                **_base_layout(height=270),
                yaxis=_ax("Nhiệt độ (°C)"),
                yaxis2=dict(**_ax("Mưa (mm)"), overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", x=0, y=1.09, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                hovermode="x unified", bargap=0.05,
            )
            st.plotly_chart(fig_tl, width='stretch', config={"displayModeBar": False})
    _card_close()

    # ── Section 2: Heatmap Calendar ──────────────────────────────────────────────
    _card_open("Heatmap", "Biến thiên chỉ số theo ngày trong năm",
               "Trục Y = tháng · Trục X = ngày · Màu theo giá trị")

    hm_col1, hm_col2 = st.columns([2, 5], gap="small")
    with hm_col1:
        hm_var = st.selectbox(
            "Biến:", [v for v in ["temp","rain","humidity","wind_speed"] if v in prov_df.columns],
            format_func=lambda x: f"{VAR_META[x]['icon']} {VAR_META[x]['label']}",
            key="l2_hm_var", label_visibility="collapsed",
        )

    if "month" in prov_df.columns and "day" in prov_df.columns and hm_var in prov_df.columns:
        pivot = (prov_df.groupby(["month","day"], observed=False)[hm_var]
                 .agg("sum" if hm_var == "rain" else "mean")
                 .reset_index()
                 .pivot(index="month", columns="day", values=hm_var))
        # Ensure full 12-month × 31-day grid
        pivot = pivot.reindex(index=range(1,13), columns=range(1,32))
        hm_meta = VAR_META[hm_var]
        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[str(d) for d in pivot.columns],
            y=[MONTH_NAMES[m-1] for m in pivot.index],
            colorscale=hm_meta.get("cs","RdYlBu_r") or "RdYlBu_r",
            colorbar=_colorbar(hm_meta["unit"]),
            zsmooth="best",
            hovertemplate=f"Tháng %{{y}}, Ngày %{{x}}<br>{hm_meta['label']}: %{{z:.1f}} {hm_meta['unit']}<extra></extra>",
        ))
        fig_hm.update_layout(
            **_base_layout(height=310, margin=dict(l=36,r=20,t=8,b=10)),
            xaxis=_ax("Ngày", tickmode="linear", dtick=5),
            yaxis=dict(**_ax(), autorange="reversed"),
        )
        st.plotly_chart(fig_hm, width='stretch', config={"displayModeBar": False})
    _card_close()

    # ── Section 3: Bản đồ trạm + Hoa gió ────────────────────────────────────────
    _section("PHÂN BỔ TRẠM QUAN TRẮC & HƯỚNG GIÓ")
    col_loc, col_wr = st.columns([1.1, 1], gap="large")

    with col_loc:
        _card_open("Bản đồ trạm", "Vị trí trạm quan trắc",
                   "Màu sắc theo giá trị chỉ số đã chọn")
        has_loc    = "location" in prov_df.columns and prov_df["location"].nunique() > 1
        has_coords = "lat" in prov_df.columns and "lon" in prov_df.columns

        loc_agg = {c: (c,"sum" if c=="rain" else "mean")
                   for c in ["temp","rain","humidity","wind_speed","lat","lon"] if c in prov_df.columns}
        loc_sum = (prov_df.groupby("location", observed=True).agg(**loc_agg).reset_index()
                   if has_loc and loc_agg else pd.DataFrame())

        map_v = None
        if has_loc:
            opts = [v for v in ["temp","rain"] if v in prov_df.columns]
            if opts:
                map_v = st.radio("Màu theo:", opts,
                                 format_func=lambda x: VAR_META[x]["label"],
                                 horizontal=True, key="l2_locmap_v")

        if map_v and not loc_sum.empty and has_coords and map_v in loc_sum.columns:
            lp  = loc_sum.dropna(subset=["lat","lon", map_v])
            mv  = VAR_META[map_v]
            fig_lm = go.Figure(go.Scattermapbox(
                lat=lp["lat"], lon=lp["lon"], mode="markers+text",
                marker=dict(
                    size=14, color=lp[map_v], opacity=0.88,
                    colorscale=mv.get("cs","RdYlBu_r") or "RdYlBu_r",
                    showscale=True, colorbar=_colorbar(mv["unit"]),
                ),
                text=lp["location"],
                textposition="top right",
                textfont=dict(size=9, color="#334155"),
                hovertemplate=f"<b>%{{text}}</b><br>{mv['label']}: %{{marker.color:.1f}} {mv['unit']}<extra></extra>",
            ))
            fig_lm.update_layout(
                **_base_layout(height=320, margin=dict(l=0,r=0,t=0,b=0)),
                mapbox=dict(style="carto-positron", zoom=7,
                            center=dict(lat=float(lp["lat"].mean()), lon=float(lp["lon"].mean()))),
            )
            st.plotly_chart(fig_lm, width='stretch', config={"displayModeBar": False, "scrollZoom": True})
        elif map_v and not loc_sum.empty and map_v in loc_sum.columns:
            ls = loc_sum.dropna(subset=[map_v]).sort_values(map_v, ascending=True).tail(15)
            mv = VAR_META[map_v]
            fig_fb = go.Figure(go.Bar(
                y=ls["location"], x=ls[map_v], orientation="h",
                marker=dict(color=mv["color"], opacity=0.75, line=dict(width=0)),
                hovertemplate=f"%{{y}}<br>{mv['label']}: %{{x:.1f}} {mv['unit']}<extra></extra>",
            ))
            fig_fb.update_layout(
                **_base_layout(height=max(290, len(ls)*22), margin=dict(l=150,r=10,t=8,b=10)),
                xaxis=_ax(f"{mv['label']} ({mv['unit']})"), yaxis=_ax(),
            )
            st.plotly_chart(fig_fb, width='stretch', config={"displayModeBar": False})
        else:
            st.info("Không có dữ liệu theo địa điểm.")
        _card_close()

    with col_wr:
        _card_open("Hoa gió", "Phân bổ hướng & tốc độ gió",
                   "Độ dài cánh = tần suất · Màu sắc = tốc độ gió (m/s)")
        if "wind_dir" in prov_df.columns and "wind_speed" in prov_df.columns:
            wr_valid = prov_df.dropna(subset=["wind_speed","wind_dir"]).copy()
            if not wr_valid.empty:
                si = (((wr_valid["wind_dir"] % 360) + 11.25) // 22.5).astype(int) % 16
                wr_valid["sector"]  = si.map(dict(enumerate(WIND_SECTORS)))
                wr_valid["spd_bin"] = pd.cut(wr_valid["wind_speed"], bins=WIND_SPEED_BINS,
                                              labels=WIND_SPEED_LABELS, include_lowest=True, right=False)
                piv_wr = (wr_valid.groupby(["sector","spd_bin"], observed=False)
                          .size().unstack(fill_value=0)
                          .reindex(index=WIND_SECTORS, columns=WIND_SPEED_LABELS, fill_value=0))
                wr_palette = ["#dbeafe","#93c5fd","#3b82f6","#1d4ed8","#1e3a8a"]
                fig_wr = go.Figure()
                for band, clr in zip(WIND_SPEED_LABELS, wr_palette):
                    fig_wr.add_trace(go.Barpolar(
                        r=piv_wr[band].values, theta=WIND_SECTORS, name=f"{band} m/s",
                        marker_color=clr, marker_line_color="rgba(255,255,255,0.8)",
                        marker_line_width=0.5, opacity=0.9,
                        hovertemplate="Hướng %{theta}<br>Tần suất: %{r}<extra></extra>",
                    ))
                fig_wr.update_layout(
                    **_base_layout(height=320),
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(showticklabels=True, ticks="",
                                        gridcolor="rgba(203,213,225,0.5)",
                                        tickfont=dict(size=7, color="#94a3b8")),
                        angularaxis=dict(direction="clockwise", rotation=90,
                                         gridcolor="rgba(203,213,225,0.3)",
                                         tickfont=dict(size=9, color="#64748b")),
                    ),
                    legend=dict(orientation="h", x=0.05, y=-0.12,
                                font=dict(size=8, color="#64748b"), bgcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig_wr, width='stretch', config={"displayModeBar": False})
            else:
                st.info("Không đủ dữ liệu hướng gió.")
        else:
            st.info("Không có cột wind_dir.")
        _card_close()

    # ── Section 4: Sự kiện cực đoan (card grid) ──────────────────────────────────
    _section("SỰ KIỆN CỰC ĐOAN")
    _card_open("Extremes", "Ghi nhận cực trị trong giai đoạn phân tích",
               "Dữ liệu từ tất cả trạm quan trắc trong tỉnh")

    prov_cp = prov_df.copy()
    prov_cp["_date"] = pd.to_datetime(prov_cp["timestamp"]).dt.date
    prov_cp["_loc"]  = prov_cp["location"].astype(str) if "location" in prov_cp.columns else province

    extreme_cards = []
    if "temp" in prov_cp.columns and not prov_cp["temp"].isna().all():
        r = prov_cp.loc[prov_cp["temp"].idxmax()]
        extreme_cards.append({
            "type": "hot", "icon": "🌡️", "label": "NÓNG NHẤT",
            "val": f"{_fmt(r['temp'],1)}°C", "meta": f"{r['_loc']} · {r['_date']}"
        })
        r = prov_cp.loc[prov_cp["temp"].idxmin()]
        extreme_cards.append({
            "type": "cold", "icon": "❄️", "label": "LẠNH NHẤT",
            "val": f"{_fmt(r['temp'],1)}°C", "meta": f"{r['_loc']} · {r['_date']}"
        })
    if "rain" in prov_cp.columns and not prov_cp["rain"].isna().all():
        dr = prov_cp.groupby(["_date","_loc"], observed=True)["rain"].sum().reset_index()
        if not dr.empty:
            r = dr.loc[dr["rain"].idxmax()]
            extreme_cards.append({
                "type": "rain", "icon": "🌧️", "label": "MƯA LỚN NHẤT",
                "val": f"{_fmt(r['rain'],0)} mm", "meta": f"{r['_loc']} · {r['_date']}"
            })
    if "wind_speed" in prov_cp.columns and not prov_cp["wind_speed"].isna().all():
        r = prov_cp.loc[prov_cp["wind_speed"].idxmax()]
        extreme_cards.append({
            "type": "wind", "icon": "💨", "label": "GIÓ MẠNH NHẤT",
            "val": f"{_fmt(r['wind_speed'],1)} m/s", "meta": f"{r['_loc']} · {r['_date']}"
        })

    if extreme_cards:
        cards_html = "".join(
            f"<div class='wth-extreme-card {c['type']}'>"
            f"<div class='ec-icon'>{c['icon']}</div>"
            f"<div class='ec-label'>{escape(c['label'])}</div>"
            f"<div class='ec-val'>{escape(c['val'])}</div>"
            f"<div class='ec-meta'>{escape(c['meta'])}</div>"
            f"</div>"
            for c in extreme_cards
        )
        st.markdown(f"<div class='wth-extreme-grid'>{cards_html}</div>", unsafe_allow_html=True)
    else:
        st.info("Không có dữ liệu cực trị.")

    _card_close()
    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def render(global_df: pd.DataFrame):
    _inject_weather_css()

    with st.spinner("Đang tải dữ liệu thời tiết..."):
        df = load_weather_data()

    if df is None or df.empty:
        st.warning("Không có dữ liệu thời tiết.")
        return
    if "city" not in df.columns or "timestamp" not in df.columns:
        st.warning("Dữ liệu thiếu cột city/timestamp.")
        return

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp","city"])
    for col in WEATHER_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "month" not in df.columns: df["month"] = df["timestamp"].dt.month
    if "day"   not in df.columns: df["day"]   = df["timestamp"].dt.day

    layer    = _get_state("wx_layer",    1)
    province = _get_state("wx_province", None)

    if layer == 2 and province:
        _render_layer2(df)
    else:
        _render_layer1(df)