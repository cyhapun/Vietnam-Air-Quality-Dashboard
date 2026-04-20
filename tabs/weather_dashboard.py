"""
weather_dashboard.py  –  Tab "Thời tiết"  (v3 – insight-first redesign)
────────────────────────────────────────────────────────────────────────
Thay đổi so với v2:
  ✦ BỎ: Bản đồ bubble Layer 1 (khó đọc insight)
  ✦ BỎ: Bản đồ trạm quan trắc Layer 2 (thay bằng bar chart nội tỉnh)
  ✦ BỎ: Ranking progress bar (thay bằng Slope chart + Dot plot)
  ✦ THÊM Layer 1: Slope chart — tỉnh nào khắc nghiệt toàn diện?
  ✦ THÊM Layer 1: Dot plot — chỉ số nào phân hóa mạnh nhất?
  ✦ THÊM Layer 1: Scatter Độ ẩm vs Lượng mưa — correlation
  ✦ GIỮ: Trend 12 tháng, Boxplot vùng miền, Timeline L2,
          Calendar heatmap, Wind rose, Extreme events
"""
from __future__ import annotations

import math
from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import load_weather_data, load_weather_province_detail, CITY_FOLDERS
from tabs import weather_tab as wt

# ─── Constants ──────────────────────────────────────────────────────────────────

WEATHER_FEATURES = ["temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud"]

WIND_SECTORS = [
    "B", "BDB", "DB", "DDB", "D", "DDN", "DN", "NDN",
    "N", "NTN", "TN", "TTN", "T", "TTB", "TB", "BTB",
]
WIND_SPEED_BINS   = [0, 5, 10, 20, 35, np.inf]
WIND_SPEED_LABELS = ["0–5", "5–10", "10–20", "20–35", ">35"]

REGION_COLORS      = {"Bắc": "#2563eb",              "Trung": "#f59e0b",              "Nam": "#16a34a"}
REGION_COLORS_RGBA = {"Bắc": "rgba(37,99,235,0.12)", "Trung": "rgba(245,158,11,0.12)", "Nam": "rgba(22,163,74,0.12)"}
REGION_BG          = {"Bắc": "#eff6ff",               "Trung": "#fffbeb",               "Nam": "#f0fdf4"}

VAR_META = {
    "temp":       {"label": "Nhiệt độ",    "unit": "°C",  "agg": "mean", "cs": "RdYlBu_r", "color": "#ea580c", "accent": "accent-red",   "icon": "🌡️"},
    "humidity":   {"label": "Độ ẩm",       "unit": "%",   "agg": "mean", "cs": "Blues",     "color": "#0ea5e9", "accent": "accent-slate", "icon": "💧"},
    "rain":       {"label": "Lượng mưa",   "unit": "mm",  "agg": "sum",  "cs": "YlGnBu",   "color": "#2563eb", "accent": "accent-blue",  "icon": "🌧️"},
    "wind_speed": {"label": "Tốc độ gió",  "unit": "m/s", "agg": "mean", "cs": "Greens",    "color": "#16a34a", "accent": "accent-green", "icon": "💨"},
    "wind_dir":   {"label": "Hướng gió",   "unit": "°",   "agg": "none", "cs": None,        "color": "#64748b", "accent": "accent-slate", "icon": "🧭"},
    "pressure":   {"label": "Áp suất",     "unit": "hPa", "agg": "mean", "cs": "Purples",   "color": "#7c3aed", "accent": "accent-blue",  "icon": "🔵"},
    "cloud":      {"label": "Mây che phủ", "unit": "%",   "agg": "mean", "cs": "Greys",     "color": "#64748b", "accent": "accent-slate", "icon": "☁️"},
}

SLOPE_METRICS       = ["temp", "rain", "wind_speed", "humidity"]
SLOPE_METRIC_LABELS = ["Nhiệt độ", "Lượng mưa", "Tốc độ gió", "Độ ẩm"]

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


# ─── CSS ────────────────────────────────────────────────────────────────────────

def _inject_weather_css():
    st.markdown("""
    <style>
    .wth-filter-bar {
        background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px;
        padding:12px 16px; margin-bottom:20px;
        display:flex; flex-wrap:wrap; gap:16px; align-items:flex-end;
    }
    .wth-filter-label {
        font-size:.62rem; font-weight:700; text-transform:uppercase;
        letter-spacing:.7px; color:#94a3b8; margin-bottom:6px;
    }
    .wth-page-header { display:flex; align-items:center; gap:14px; padding:18px 0 6px; }
    .wth-page-icon {
        width:42px; height:42px; border-radius:12px;
        background:linear-gradient(135deg,#0ea5e9,#2563eb);
        display:flex; align-items:center; justify-content:center;
        font-size:1.3rem; flex-shrink:0;
    }
    .wth-page-title { font-size:1.18rem; font-weight:700; color:#1e293b; line-height:1.2; }
    .wth-page-sub   { font-size:.72rem; color:#64748b; margin-top:2px; }
    .wth-breadcrumb {
        font-size:.72rem; color:#64748b; margin-bottom:6px;
        display:flex; align-items:center; gap:6px;
    }
    .wth-breadcrumb-home {
        color:#2563eb; cursor:pointer; text-decoration:none;
        font-weight:600; display:inline-flex; align-items:center; gap:4px;
    }
    .wth-section {
        font-size:.62rem; font-weight:700; text-transform:uppercase;
        letter-spacing:.8px; color:#94a3b8; margin:26px 0 14px;
        display:flex; align-items:center; gap:10px;
    }
    .wth-section::after { content:''; flex:1; height:1px; background:#f1f5f9; }
    .kpi-box.accent-green  { border-top-color:#16a34a; }
    .kpi-box.accent-orange { border-top-color:#f59e0b; }
    .kpi-delta-pos { color:#16a34a; font-size:.68rem; font-weight:600; }
    .kpi-delta-neg { color:#ea580c; font-size:.68rem; font-weight:600; }
    .kpi-delta-neu { color:#64748b; font-size:.68rem; }
    .wth-badge-row { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:14px; }
    .wth-badge {
        background:#f1f5f9; border:1px solid #e2e8f0; border-radius:99px;
        font-size:.72rem; font-weight:500; color:#475569; padding:4px 12px;
        display:inline-flex; align-items:center; gap:5px;
    }
    .wth-extreme-grid {
        display:grid; grid-template-columns:repeat(auto-fill, minmax(200px,1fr));
        gap:12px; margin-top:4px;
    }
    .wth-extreme-card {
        background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px;
        padding:14px 16px; position:relative; overflow:hidden;
    }
    .wth-extreme-card::before {
        content:''; position:absolute; left:0; top:0; bottom:0;
        width:4px; border-radius:4px 0 0 4px;
    }
    .wth-extreme-card.hot::before  { background:#ea580c; }
    .wth-extreme-card.cold::before { background:#2563eb; }
    .wth-extreme-card.rain::before { background:#0284c7; }
    .wth-extreme-card.wind::before { background:#16a34a; }
    .wth-extreme-card .ec-icon  { font-size:1.4rem; margin-bottom:6px; }
    .wth-extreme-card .ec-label { font-size:.62rem; text-transform:uppercase; letter-spacing:.6px; color:#94a3b8; font-weight:700; }
    .wth-extreme-card .ec-val   { font-size:1.3rem; font-weight:800; color:#1e293b; margin:2px 0; line-height:1; }
    .wth-extreme-card .ec-meta  { font-size:.72rem; color:#64748b; }
    .wth-compare-row { display:flex; gap:10px; margin-top:10px; }
    .wth-compare-card { flex:1; padding:10px 14px; border-radius:10px; border:1px solid #e2e8f0; text-align:center; }
    .wth-compare-card .cc-label { font-size:.62rem; text-transform:uppercase; letter-spacing:.6px; color:#94a3b8; font-weight:700; }
    .wth-compare-card .cc-val   { font-size:1.1rem; font-weight:800; color:#1e293b; margin-top:2px; }
    .card-sub { font-size:.72rem; color:#94a3b8; margin:2px 0 12px; }
    .wth-insight-box {
        background:#f0fdf4; border:1px solid #bbf7d0; border-radius:9px;
        padding:8px 14px; font-size:.76rem; color:#166534; margin-top:8px;
        display:flex; align-items:flex-start; gap:6px;
    }
    
    /* ── Info Section Card (Premium Title) ── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .wx-info-card {
        background: linear-gradient(to right, #ffffff, #f8fbff);
        border: 1px solid #e2eaf3;
        border-left: 5px solid #0ea5e9;
        border-radius: 8px;
        padding: 1.3rem;
        margin-bottom: 0.4rem;
        display: flex;
        flex-direction: column;
        gap: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
        animation: fadeInUp 0.6s ease-out both;
        text-align: left;
    }
    .wx-info-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    .wx-info-badge {
        background: #e0f2fe;
        color: #0369a1;
        font-size: 0.85rem;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .wx-info-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
    }
    .wx-info-sub {
        font-size: 1rem;
        color: #64748b;
        line-height: 1.5;
        font-weight: 500;
        text-align: left;
    }
    </style>
    """, unsafe_allow_html=True)


# ─── Utilities ───────────────────────────────────────────────────────────────────

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
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Be Vietnam Pro, sans-serif", size=10, color="#334155"),
        margin=dict(l=8, r=8, t=32, b=8), template="plotly_white",
    )
    base.update(kw)
    return base

def _ax(title="", **kw) -> dict:
    cfg = dict(
        title=dict(text=title, font=dict(size=9, color="#94a3b8")),
        tickfont=dict(size=9, color="#94a3b8"),
        gridcolor="rgba(203,213,225,0.35)", linecolor="#e2e8f0", zeroline=False,
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
    """Safely retrieves a value from the Streamlit session state, returning a default if missing."""
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

def _set_state(**kwargs):
    """Updates one or more values in the Streamlit session state."""
    for k, v in kwargs.items():
        st.session_state[k] = v

def _go_layer1():
    """Triggers navigation to the Layer 1 (National Overview) view."""
    _set_state(wx_layer=1, wx_layer2_city=None)
    st.rerun()

def _go_layer2(province: str):
    """Triggers navigation to the Layer 2 (Province Detail) view for a specific province."""
    _set_state(wx_layer=2, wx_layer2_city=province)
    st.rerun()


# ─── Season selector ────────────────────────────────────────────────────────────

def _season_selector(key_prefix: str) -> tuple[str, int | None]:
    """
    Renders a season/month selector UI and returns the selected preset and specific month (if applicable).
    """
    categories = {
        "📊 Tổng quát": ["Cả năm", "Mùa khô", "Mùa mưa"],
        "🕒 Theo Quý":  ["Q1", "Q2", "Q3", "Q4"],
        "📅 Theo Tháng": MONTH_NAMES,
    }
    current_preset = _get_state(f"{key_prefix}_season", "Cả năm")
    current_cat_idx = 0
    for i, (cat, opts) in enumerate(categories.items()):
        if current_preset in opts:
            current_cat_idx = i
            break
    c1, c2 = st.columns([0.7, 2.3], gap="small")
    with c1:
        cat_sel = st.selectbox("Loại", list(categories.keys()), index=current_cat_idx,
                               key=f"{key_prefix}_cat_sel", label_visibility="collapsed")
    with c2:
        opts = categories[cat_sel]
        default_val = current_preset if current_preset in opts else opts[0]
        sel = st.segmented_control("Giai đoạn", opts, default=default_val,
                                   key=f"{key_prefix}_sg", selection_mode="single",
                                   label_visibility="collapsed")
    if sel and sel != current_preset:
        _set_state(**{f"{key_prefix}_season": sel})
        st.rerun()
    preset = sel if sel else current_preset
    month = None
    if isinstance(preset, str) and preset.startswith("Th"):
        try:
            month = int(preset[2:])
        except ValueError:
            pass
    return preset, month

def _filter_by_season(df: pd.DataFrame, preset: str, month: int | None = None) -> pd.DataFrame:
    """Filters a DataFrame based on the selected season or month preset."""
    if "timestamp" not in df.columns:
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
    """Aggregates weather data to a monthly resolution."""
    if df.empty or "timestamp" not in df.columns:
        return pd.DataFrame()
    src = df.copy()
    src["month"] = pd.to_datetime(src["timestamp"]).dt.month
    agg = {c: (c, "mean") for c in ["temp","humidity","pressure","cloud","wind_speed"] if c in src.columns}
    if "rain" in src.columns:
        agg["rain"] = ("rain", "sum")
    return src.groupby(["city","month"], observed=True).agg(**agg).reset_index() if agg else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def _agg_annual(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates weather data to an annual resolution, grouped by region and province."""
    if df.empty or "city" not in df.columns:
        return pd.DataFrame()
    src = df.copy()
    agg = {c: (c, "mean") for c in ["temp","humidity","pressure","cloud","wind_speed"] if c in src.columns}
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
        coords.append({"city": city, "lat": lat, "lon": lon})
    result = result.merge(pd.DataFrame(coords), on="city", how="left")
    for col in ["temp","humidity","rain","wind_speed"]:
        if col in result.columns:
            result[f"{col}_rank"] = result[col].rank(ascending=False, method="min").astype("Int64")
    return result


# ─── Card / KPI helpers ──────────────────────────────────────────────────────────

def _card_open(tag: str, title: str, sub: str = ""):
    """Renders the opening HTML tags and header for a dashboard card."""
    sub_html = f"<div class='card-sub'>{escape(sub)}</div>" if sub else ""
    st.markdown(
        f"<div class='card'>"
        f"<div class='card-title'><span class='q-tag'>{tag}</span>{escape(title)}</div>"
        f"{sub_html}", unsafe_allow_html=True,
    )

def _card_close():
    """Renders the closing HTML tags for a dashboard card."""
    st.markdown("</div>", unsafe_allow_html=True)

def _kpi_html(label, value, unit, accent, sub="") -> str:
    """Generates the HTML markup for a KPI metric box."""
    sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
    return (
        f"<div class='kpi-box {accent}'>"
        f"<div class='kpi-lbl'>{escape(label)}</div>"
        f"<div class='kpi-val'>{escape(value)} <span class='u'>{escape(unit)}</span></div>"
        f"{sub_html}</div>"
    )

def _kpi_row(cards: list[str]):
    """Renders a responsive row of KPI cards using CSS flexbox."""
    st.markdown(
        f"<div class='kpi-strip' style='grid-template-columns:repeat({len(cards)},1fr)'>"
        + "".join(cards) + "</div>", unsafe_allow_html=True,
    )

def _info_card_html(badge: str, title: str, sub: str) -> str:
    html = f"""
    <div class='wx-info-card'>
        <div class='wx-info-header'>
            <span class='wx-info-badge'>{badge}</span>
            <div class='wx-info-title'>{title}</div>
        </div>
        <div class='wx-info-sub'>{sub}</div>
    </div>
    """
    return html.strip().replace("\n", "").replace("    ", "")

def _section(title: str, subtitle: str = ""):
    """Renders a section header as a premium info card."""
    badge = "PHÂN TÍCH"
    # Basic icon extraction
    icons = ["🌡️", "🌧️", "💨", "🧭", "🔵", "☁️", "📊", "📍", "🗺️", "🏅"]
    clean_title = title
    for icon in icons:
        if icon in title:
            badge = icon
            clean_title = title.replace(icon, "").strip()
            break
            
    st.markdown(_info_card_html(badge, clean_title, subtitle), unsafe_allow_html=True)

def _insight_box(text: str):
    """Renders an insight text box."""
    st.markdown(
        f"<div class='wth-insight-box'>💡 {text}</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CHART: SLOPE CHART — tỉnh nào khắc nghiệt toàn diện?
# ═══════════════════════════════════════════════════════════════════════════════

def _render_slope_chart(annual: pd.DataFrame):
    """
    Renders a custom slope/bump chart comparing the rank of top provinces across different meteorological metrics.
    """
    avail_metrics = [m for m in SLOPE_METRICS if m in annual.columns]
    avail_labels  = [SLOPE_METRIC_LABELS[SLOPE_METRICS.index(m)] for m in avail_metrics]
    if len(avail_metrics) < 2:
        st.info("Không đủ chỉ số để vẽ slope chart.")
        return

    annual = annual.copy()
    annual["region"] = annual["city"].map(PROVINCE_REGION).fillna("Khác")

    # Calculate rank for each metric (rank 1 = highest value)
    for m in avail_metrics:
        annual[f"{m}_rank"] = annual[m].rank(ascending=False, method="min").astype("Int64")

    n_total = len(annual)

    # Get top N provinces: only top 5 to reduce clutter
    TOP_K = 5
    top_candidates: set[str] = set()
    for m in avail_metrics:
        top_candidates |= set(annual.nsmallest(TOP_K, f"{m}_rank")["city"].tolist())
    top_df = annual[annual["city"].isin(top_candidates)].copy()

    fig = go.Figure()

    for _, row in top_df.iterrows():
        city   = str(row["city"])
        reg    = str(row["region"])
        color  = REGION_COLORS.get(reg, "#94a3b8")
        ranks  = [int(row[f"{m}_rank"]) for m in avail_metrics]
        # Highlight the province with the lowest total rank (most extreme)
        total_rank = sum(ranks)
        is_top     = total_rank == min(
            sum(int(r[f"{m}_rank"]) for m in avail_metrics)
            for _, r in top_df.iterrows()
        )
        # Draw a glow line underneath if it is a top province to make it stand out
        if is_top:
            fig.add_trace(go.Scatter(
                x=avail_labels, y=ranks, mode="lines",
                line=dict(color=color, width=10, shape="spline"),
                opacity=0.15, showlegend=False, hoverinfo="skip"
            ))

        fig.add_trace(go.Scatter(
            x=avail_labels, y=ranks, mode="lines+markers",
            name=city,
            line=dict(color=color, width=5 if is_top else 1.5, shape="spline"),
            marker=dict(size=10 if is_top else 5, color=color,
                        line=dict(width=1.5, color="#ffffff")),
            opacity=1.0 if is_top else 0.35, # Increased from 0.2 to 0.35 for better visibility
            customdata=[[city, reg, ranks[i], n_total] for i in range(len(avail_metrics))],
            hovertemplate=(
                "<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                "Hạng: %{y}/%{customdata[3]}<br>"
                "Chỉ số: %{x}<extra></extra>"
            ),
        ))

    # Annotation for the most extreme province (e.g. Quang Tri) as a focal point
    best_city_row = top_df.loc[
        top_df[[f"{m}_rank" for m in avail_metrics]].sum(axis=1).idxmin()
    ]
    best_name = str(best_city_row["city"])
    best_reg  = str(best_city_row["region"])
    best_last_rank = int(best_city_row[f"{avail_metrics[-1]}_rank"])
    fig.add_annotation(
        x=avail_labels[-1], y=best_last_rank,
        text=f"  {best_name}",
        showarrow=False, xanchor="left",
        font=dict(size=11, color=REGION_COLORS.get(best_reg, "#334155"), weight="bold"),
    )

    fig.update_layout(
        **_base_layout(height=340, margin=dict(l=10, r=90, t=20, b=10)),
        yaxis=dict(
            **_ax("Thứ hạng (1 = cao nhất)"),
            autorange="reversed",
            tickvals=list(range(1, min(TOP_K + 2, n_total + 1))),
        ),
        xaxis=_ax(),
        showlegend=False,
        hovermode="closest",
    )

    # Region Legend
    for reg, clr in REGION_COLORS.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(size=8, color=clr),
            name=reg, showlegend=True,
        ))
    fig.update_layout(
        showlegend=False, # Hide province legend to reduce clutter
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Auto insight
    total_ranks = top_df[[f"{m}_rank" for m in avail_metrics]].sum(axis=1)
    best_idx    = total_ranks.idxmin()
    best_row    = top_df.loc[best_idx]
    ranks_str   = " · ".join(
        f"{lbl} #{int(best_row[f'{m}_rank'])}"
        for m, lbl in zip(avail_metrics, avail_labels)
    )
    _insight_box(
        f"<b>{escape(str(best_row['city']))}</b> ({escape(str(best_row['region']))}) "
        f"khắc nghiệt toàn diện nhất — {ranks_str}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CHART: DOT PLOT — chỉ số nào phân hóa mạnh nhất giữa các tỉnh?
# ═══════════════════════════════════════════════════════════════════════════════

def _render_dot_plot(annual: pd.DataFrame, reg_filter: str = "Tất cả"):
    """
    Renders a dot plot to show the dispersion and outliers of meteorological metrics across provinces.
    """
    avail_metrics = [m for m in SLOPE_METRICS if m in annual.columns]
    avail_labels  = [SLOPE_METRIC_LABELS[SLOPE_METRICS.index(m)] for m in avail_metrics]
    if not avail_metrics:
        st.info("Không đủ dữ liệu.")
        return

    df = annual.copy()
    df["region"] = df["city"].map(PROVINCE_REGION).fillna("Khác")

    if reg_filter != "Tất cả":
        df = df[df["region"] == reg_filter]
    if df.empty:
        st.info("Không có dữ liệu cho vùng này.")
        return

    fig = go.Figure()

    coeff_of_var: dict[str, float] = {}

    for yi, (m, lbl) in enumerate(zip(avail_metrics, avail_labels)):
        vals = df[m].dropna()
        if vals.empty:
            continue
        mn, mx  = vals.min(), vals.max()
        span    = mx - mn if mx != mn else 1.0
        mean    = vals.mean()
        cv      = (vals.std() / mean * 100) if mean != 0 else 0
        coeff_of_var[lbl] = cv

        norm_vals = (df[m] - mn) / span * 100
        norm_mean = (mean - mn) / span * 100

        # Dots per province
        for _, row in df.iterrows():
            if pd.isna(row[m]): continue
            nv  = (row[m] - mn) / span * 100
            reg = str(row["region"])
            clr = REGION_COLORS.get(reg, "#94a3b8")
            # Determine outlier: outside 1.5 IQR
            q1, q3  = vals.quantile(0.25), vals.quantile(0.75)
            iqr     = q3 - q1
            is_out  = row[m] < q1 - 1.5*iqr or row[m] > q3 + 1.5*iqr
            fig.add_trace(go.Scatter(
                x=[nv], y=[yi],
                mode="markers",
                marker=dict(
                    size=9 if is_out else 6,
                    color=clr,
                    opacity=1.0 if is_out else 0.6,
                    symbol="diamond" if is_out else "circle",
                    line=dict(width=1.5 if is_out else 0, color=clr),
                ),
                showlegend=False,
                customdata=[[str(row["city"]), reg, row[m], lbl,
                             VAR_META.get(m, {}).get("unit",""),
                             "outlier" if is_out else ""]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                    "%{customdata[3]}: %{customdata[2]:.1f} %{customdata[4]}<br>"
                    "%{customdata[5]}<extra></extra>"
                ),
            ))

        # Mean marker (black diamond)
        fig.add_trace(go.Scatter(
            x=[norm_mean], y=[yi],
            mode="markers",
            marker=dict(size=10, color="#1e293b", symbol="diamond",
                        line=dict(width=0)),
            showlegend=True if yi == 0 else False,
            name="Trung bình nhóm",
            hovertemplate=f"Trung bình {lbl}: {mean:.1f} {VAR_META.get(m,{}).get('unit','')}<extra></extra>",
        ))

        # CV annotation on the right
        fig.add_annotation(
            x=105, y=yi,
            text=f"CV={cv:.0f}%",
            showarrow=False, xanchor="left",
            font=dict(size=9, color="#94a3b8"),
        )

    fig.update_layout(
        **_base_layout(height=max(220, len(avail_metrics) * 70), margin=dict(l=10, r=70, t=10, b=10)),
        xaxis=dict(
            **_ax("Giá trị chuẩn hóa trong nhóm (%)"),
            range=[-5, 115],
            tickvals=[0, 25, 50, 75, 100],
            ticktext=["Min", "25%", "Median", "75%", "Max"],
        ),
        yaxis=dict(
            **_ax(),
            tickvals=list(range(len(avail_labels))),
            ticktext=avail_labels,
        ),
        legend=dict(orientation="h", x=0, y=1.08, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
        hovermode="closest",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Auto insight: highest CV metric = strongest dispersion
    if coeff_of_var:
        most_unequal = max(coeff_of_var, key=coeff_of_var.get)
        _insight_box(
            f"<b>{most_unequal}</b> phân hóa mạnh nhất giữa các tỉnh "
            f"(CV={coeff_of_var[most_unequal]:.0f}%) — "
            f"chỉ số này tạo ra bất bình đẳng khí hậu lớn nhất."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CHART: MULTIVARIATE — Nhiệt độ, Độ ẩm có kéo theo mưa không?
# ═══════════════════════════════════════════════════════════════════════════════

def _render_multivariate_rain_analysis(annual: pd.DataFrame):
    """
    Renders a multivariate bubble chart and correlation heatmap to analyze the relationship between temperature, humidity, and rainfall.
    """
    cols = ["temp", "humidity", "rain"]
    if not all(c in annual.columns for c in cols):
        st.info("Không đủ dữ liệu (Nhiệt độ, Độ ẩm, Lượng mưa) để phân tích tương quan.")
        return

    df = annual.dropna(subset=cols).copy()
    if df.empty: return

    # 1. Calculate Pearson correlation
    corr = df[cols].corr()
    r_tr = corr.loc["temp", "rain"]
    r_hr = corr.loc["humidity", "rain"]

    c1, c2 = st.columns([2.5, 1], gap="medium")

    with c1:
        # Bubble Chart
        fig = go.Figure()
        # Calculate sizeref so bubbles are not too large
        max_rain = df["rain"].max()
        sizeref = 2.0 * max_rain / (40**2) if max_rain > 0 else 1

        for reg in REGION_ORDER + ["Khác"]:
            sub = df[df["city"].map(PROVINCE_REGION).fillna("Khác") == reg]
            if sub.empty: continue
            fig.add_trace(go.Scatter(
                x=sub["temp"], y=sub["humidity"], mode="markers",
                name=reg,
                marker=dict(
                    size=sub["rain"], sizemode='area', sizeref=sizeref, sizemin=4,
                    color=REGION_COLORS.get(reg, "#94a3b8"), opacity=0.85, # Increased from 0.7 to 0.85
                    line=dict(width=1, color="#ffffff")
                ),
                customdata=list(zip(sub["city"], sub["rain"])),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Nhiệt độ: %{x:.1f}°C<br>"
                    "Độ ẩm: %{y:.1f}%<br>"
                    "Lượng mưa: %{customdata[1]:.0f} mm<extra></extra>"
                )
            ))

        fig.update_layout(
            **_base_layout(height=380, margin=dict(l=10, r=10, t=20, b=10)),
            xaxis=_ax("Nhiệt độ trung bình (°C)"),
            yaxis=_ax("Độ ẩm trung bình (%)"),
            legend=dict(orientation="h", x=0, y=1.08, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
            hovermode="closest"
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        # Mini heatmap showing correlation coefficients
        st.markdown("<div style='font-size:0.62rem; font-weight:700; color:#94a3b8; text-align:center; margin-bottom:8px'>HỆ SỐ TƯƠNG QUAN (r)</div>", unsafe_allow_html=True)
        
        fig_corr = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=["Nhiệt độ", "Độ ẩm", "Mưa"],
            y=["Nhiệt độ", "Độ ẩm", "Mưa"],
            colorscale='RdBu_r', zmin=-1, zmax=1,
            text=corr.values.round(2), texttemplate="%{text}",
            showscale=False
        ))
        fig_corr.update_layout(
            **_base_layout(height=240, margin=dict(l=40, r=10, t=10, b=10)),
            xaxis=dict(side="bottom", tickfont=dict(size=8)),
            yaxis=dict(tickfont=dict(size=8))
        )
        st.plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": False})

        # Brief explanation of r
        st.markdown(
            f"<div style='font-size:0.68rem; color:#64748b; line-height:1.4'>"
            f"• r &gt; 0: Đồng biến (cùng tăng)<br>"
            f"• r &lt; 0: Nghịch biến<br>"
            f"• |r| &gt; 0.5: Tương quan mạnh"
            f"</div>", unsafe_allow_html=True
        )

    # 3. Answer User's question directly with Auto-Insight
    def get_relation(r):
        if r > 0.3: return "tăng rõ rệt"
        if r > 0.1: return "có xu hướng tăng nhẹ"
        if r < -0.3: return "giảm rõ rệt"
        return "không có liên hệ rõ ràng"

    msg = (f"Câu trả lời: Khi <b>Nhiệt độ</b> tăng, lượng mưa {get_relation(r_tr)} (r={r_tr:.2f}). "
           f"Khi <b>Độ ẩm</b> tăng, lượng mưa {get_relation(r_hr)} (r={r_hr:.2f}).")
    
    if r_tr > 0.2 and r_hr > 0.2:
        msg += " <br>=> <b>Kết luận:</b> Nhiệt độ và Độ ẩm cao thường là 'ngòi nổ' kéo theo lượng mưa lớn tại Việt Nam."
    else:
        msg += " <br>=> <b>Kết luận:</b> Mưa phụ thuộc vào nhiều yếu tố khác (như gió/áp suất) chứ không chỉ riêng nhiệt độ/độ ẩm."

    _insight_box(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 – TỔNG QUAN TOÀN QUỐC
# ═══════════════════════════════════════════════════════════════════════════════

def _render_layer1(df: pd.DataFrame):
    """
    Renders Layer 1 of the weather dashboard: the National Overview.
    Includes high-level KPIs, spatial maps, and macro-level analysis charts.
    """
    # Header with switch to Forecast mode button on the right
    c_head, c_nav = st.columns([4, 1.2], gap="small")
    with c_head:
        st.markdown(
            "<div class='wth-page-header'>"
            "<div class='wth-page-icon'>🌤</div>"
            "<div>"
            "<div class='wth-page-title'>Thời tiết Toàn quốc</div>"
            "<div class='wth-page-sub'>Dữ liệu quan trắc khí tượng Việt Nam · Phân tích theo giai đoạn và vùng miền</div>"
            "</div></div>", unsafe_allow_html=True,
        )
    with c_nav:
        st.markdown("<div style='margin-top:16px'>", unsafe_allow_html=True)
        if st.button("← Quay lại Dự báo", type="secondary", key="back_to_forecast_head", use_container_width=True):
            st.session_state["wx_view_mode"] = "forecast"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Filter bar ───────────────────────────────────────────────────────────────
    st.markdown("<div class='wth-filter-bar'>", unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([1.8, 1.2, 1.0], gap="small")
    with fc1:
        st.markdown("<div class='wth-filter-label'>Giai đoạn phân tích</div>", unsafe_allow_html=True)
        preset, month = _season_selector("l1")
    with fc2:
        st.markdown("<div class='wth-filter-label'>Chỉ số hiển thị</div>", unsafe_allow_html=True)
        var_opts = [v for v in ["temp","humidity","rain","wind_speed"] if v in df.columns]
        cur_var  = _get_state("l1_var", var_opts[0] if var_opts else "temp")
        if cur_var not in var_opts: cur_var = var_opts[0]
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
        for col, icon, label in [("temp","🌡️","Nóng nhất"), ("rain","🌧️","Mưa nhiều nhất"), ("wind_speed","💨","Gió mạnh nhất")]:
            if col in annual.columns and not annual[col].isna().all():
                city = annual.loc[annual[col].idxmax(), "city"]
                badges.append(f"{icon} {label}: <b>{escape(str(city))}</b>")
        if not monthly.empty and "temp" in monthly.columns:
            nat_mon = monthly.groupby("month")["temp"].mean()
            if not nat_mon.empty:
                badges.append(f"📅 Tháng nóng nhất: <b>Tháng {int(nat_mon.idxmax())}</b>")
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

    # ── Section A: Xu hướng + Boxplot ───────────────────────────────────────────
    _section("CHU KỲ KHÍ HẬU & PHÂN BỐ VÙNG MIỀN")
    col_trend, col_box = st.columns([1.35, 1], gap="large")

    with col_trend:
        _card_open(
            "Xu hướng", f"{meta.get('label','')} theo tháng · Toàn quốc",
            "Đường = chỉ số đã chọn · Cột mờ = lượng mưa · ★ = đỉnh cao nhất"
        )
        if not monthly.empty:
            agg_fns = {c: (c, "sum" if c == "rain" else "mean")
                       for c in ["temp","humidity","rain","wind_speed"] if c in monthly.columns}
            nat_mon = monthly.groupby("month", observed=True).agg(**agg_fns).reset_index() if agg_fns else pd.DataFrame()
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
                    **_base_layout(height=230),
                    yaxis=_ax(f"{meta.get('label','')} ({meta.get('unit','')})"),
                    yaxis2=dict(**_ax(f"{m2_meta.get('label','')} ({m2_meta.get('unit','')})"),
                                overlaying="y", side="right", showgrid=False),
                    legend=dict(orientation="h", x=0, y=1.1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                    hovermode="x unified", bargap=0.3,
                )
                st.plotly_chart(fig_t, use_container_width=True, config={"displayModeBar": False})

                if cur_var in nat_mon.columns:
                    m_hi  = int(nat_mon.loc[nat_mon[cur_var].idxmax(), "month"])
                    m_lo  = int(nat_mon.loc[nat_mon[cur_var].idxmin(), "month"])
                    st.markdown(
                        f"<div style='display:flex;gap:8px;margin-top:6px'>"
                        f"<div style='flex:1;background:#fff7ed;border:1px solid #fed7aa;padding:8px 12px;border-radius:9px'>"
                        f"<div class='kpi-lbl'>Đỉnh cao nhất</div>"
                        f"<div style='font-size:.95rem;font-weight:800;color:#ea580c'>"
                        f"Tháng {m_hi} · {_fmt(nat_mon[cur_var].max(),1)} {escape(meta.get('unit',''))}</div></div>"
                        f"<div style='flex:1;background:#eff6ff;border:1px solid #bfdbfe;padding:8px 12px;border-radius:9px'>"
                        f"<div class='kpi-lbl'>Đáy thấp nhất</div>"
                        f"<div style='font-size:.95rem;font-weight:800;color:#2563eb'>"
                        f"Tháng {m_lo} · {_fmt(nat_mon[cur_var].min(),1)} {escape(meta.get('unit',''))}</div></div>"
                        f"</div>", unsafe_allow_html=True,
                    )
        else:
            st.info("Không đủ dữ liệu xu hướng.")
        _card_close()

    with col_box:
        _card_open(
            "Vùng miền", f"{meta.get('label','')} · Bắc – Trung – Nam",
            "Hộp = Q1–Q3 · Đường giữa = median · Điểm = từng tỉnh (hover xem tên)"
        )
        if not annual.empty and cur_var in annual.columns:
            annual_box = annual.copy()
            annual_box["region"] = annual_box["city"].map(PROVINCE_REGION).fillna("Khác")
            fig_box = go.Figure()
            for reg in REGION_ORDER:
                sub = annual_box[annual_box["region"] == reg]
                d   = sub[cur_var].dropna()
                if d.empty: continue
                fig_box.add_trace(go.Box(
                    y=d, name=reg,
                    boxpoints="all", jitter=0.4, pointpos=-1.6,
                    marker=dict(size=6, color=REGION_COLORS.get(reg,"#94a3b8"), opacity=0.7),
                    line=dict(color=REGION_COLORS.get(reg,"#94a3b8"), width=2),
                    fillcolor=REGION_COLORS_RGBA.get(reg, "rgba(148,163,184,0.12)"),
                    # Tooltip bao gồm tên tỉnh
                    customdata=sub[["city","region",cur_var]].dropna().values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                        f"{meta.get('label','')}: %{{customdata[2]:.1f}} {meta.get('unit','')}"
                        "<extra></extra>"
                    ),
                ))
            fig_box.update_layout(
                **_base_layout(height=290, margin=dict(l=8, r=8, t=8, b=8)),
                yaxis=_ax(meta.get("unit","")), xaxis=_ax(), showlegend=False,
            )
            st.plotly_chart(fig_box, use_container_width=True, config={"displayModeBar": False})

            # Auto insight: vùng có độ phân tán lớn nhất
            region_iqr = {}
            for reg in REGION_ORDER:
                d = annual_box[annual_box["region"] == reg][cur_var].dropna()
                if len(d) >= 3:
                    region_iqr[reg] = float(d.quantile(0.75) - d.quantile(0.25))
            if region_iqr:
                most_varied = max(region_iqr, key=region_iqr.get)
                _insight_box(
                    f"Miền <b>{most_varied}</b> có {meta.get('label','')} phân tán nhất nội vùng "
                    f"(IQR = {region_iqr[most_varied]:.1f} {meta.get('unit','')}) — "
                    f"các tỉnh trong vùng rất khác nhau."
                )
        _card_close()

        # Nút Dự báo đã được chuyển lên Header

    # ── Section B: Slope chart + Dot plot ───────────────────────────────────────
    _section("XẾP HẠNG & PHÂN HÓA TỈNH THÀNH")

    col_slope, col_dot = st.columns([1.2, 1], gap="large")

    with col_slope:
        _card_open(
            "Slope chart", "Tỉnh nào khắc nghiệt toàn diện?",
            "Đường nằm cao xuyên suốt = khắc nghiệt nhiều chỉ số · Hover xem thứ hạng",
        )
        if not annual.empty:
            _render_slope_chart(annual)
        _card_close()

    with col_dot:
        _card_open(
            "Dot plot", "Chỉ số nào phân hóa mạnh nhất?",
            "Khoảng trải rộng = phân hóa lớn · Hình thoi = trung bình · ◆ = outlier",
        )
        if not annual.empty:
            reg_opts = ["Tất cả"] + REGION_ORDER
            reg_dot  = st.radio("Lọc vùng:", reg_opts, horizontal=True, key="l1_dot_reg")
            _render_dot_plot(annual, reg_filter=reg_dot)
        _card_close()

    # ── Section C: Phân tích đa biến (Nhiệt độ + Độ ẩm -> Mưa) ───────────────────
    _section("TƯƠNG QUAN NHIỆT ĐỘ, ĐỘ ẨM & LƯỢNG MƯA")
    _card_open(
        "Multivariate Analysis", "Nhiệt độ & Độ ẩm tăng có kéo theo mưa không?",
        "Bong bóng lớn = mưa nhiều · X: Nhiệt độ · Y: Độ ẩm · Màu: Vùng miền",
    )
    if not annual.empty:
        _render_multivariate_rain_analysis(annual)
    _card_close()


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2 – CHI TIẾT TỈNH
# ═══════════════════════════════════════════════════════════════════════════════

def _render_layer2(df: pd.DataFrame):
    """
    Renders Layer 2 of the weather dashboard: Province Detail View.
    Displays localized weather KPIs, 24-hour trends, and seasonal distribution for a specific province.
    """
    province = _get_state("wx_province", None)
    if not province:
        _go_layer1(); return

    c_bc, c_back = st.columns([6, 1], gap="small")
    with c_bc:
        st.markdown(
            f"<div class='wth-breadcrumb'>"
            f"<span class='wth-breadcrumb-home'>🏠 Toàn quốc</span>"
            f"<span style='color:#cbd5e1;margin:0 4px'>/</span>"
            f"<span style='color:#1e293b;font-weight:600'>{escape(province)}</span>"
            f"</div>", unsafe_allow_html=True,
        )
    with c_back:
        if st.button("← Quay lại", key="l2_back", use_container_width=True):
            _go_layer1()

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
        f"<div><div class='wth-page-title'>{escape(province)}{region_badge}</div>"
        f"<div class='wth-page-sub'>Phân tích khí tượng chi tiết từ trạm quan trắc địa phương</div>"
        f"</div></div>", unsafe_allow_html=True,
    )

    # Filter bar
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
    meta    = VAR_META.get(pv, {})

    nat_annual = _agg_annual(filtered)
    nat_avg    = nat_annual.mean(numeric_only=True) if not nat_annual.empty else pd.Series(dtype=float)

    def _delta_sub(col, prov_val):
        nat = nat_avg.get(col)
        if nat is None or pd.isna(nat) or pd.isna(prov_val): return ""
        diff = prov_val - nat
        sign = "+" if diff > 0 else ""
        cls  = "kpi-delta-pos" if diff < 0 else "kpi-delta-neg"
        return f"<span class='{cls}'>{sign}{_fmt(diff,1)} vs toàn quốc</span>"

    # KPI strip
    kpis = []
    for col, lbl, unit, acc in [("temp","Nhiệt độ TB","°C","accent-red"),
                                  ("humidity","Độ ẩm TB","%","accent-slate"),
                                  ("wind_speed","Gió cực đại","m/s","accent-green"),
                                  ("pressure","Áp suất TB","hPa","accent-blue")]:
        if col not in prov_df.columns: continue
        v = prov_df[col].max() if col == "wind_speed" else prov_df[col].mean()
        kpis.append(_kpi_html(lbl, _fmt(v,1), unit, acc, _delta_sub(col, v)))
    if "rain" in prov_df.columns:
        kpis.append(_kpi_html("Tổng mưa", _fmt(prov_df["rain"].sum(),0), "mm", "accent-blue"))
    if kpis:
        _kpi_row(kpis)

    # ── Section 1: Timeline ──────────────────────────────────────────────────────
    _section("DIỄN BIẾN THỜI GIAN", "Theo dõi biến động nhiệt độ và lượng mưa qua các mốc thời gian")
    _card_open("Timeline", "Nhiệt độ & Lượng mưa hàng ngày",
               "Đường cam = nhiệt độ · Vùng mờ = biên độ min–max · Cột xanh = lượng mưa")

    if "month" in prov_df.columns and "day" in prov_df.columns:
        spec = {}
        if "temp" in prov_df.columns:
            spec.update({"temp_mean": ("temp","mean"), "temp_min": ("temp","min"), "temp_max": ("temp","max")})
        if "rain"     in prov_df.columns: spec["rain"]     = ("rain","sum")
        if "humidity" in prov_df.columns: spec["humidity"] = ("humidity","mean")

        if spec:
            daily = prov_df.groupby(["month","day"], observed=True).agg(**spec).reset_index()
            daily["ts"] = (pd.to_datetime("2025-01-01")
                           + pd.to_timedelta((daily["month"]-1)*30 + daily["day"]-1, unit="D"))
            fig_tl = go.Figure()
            if "rain" in daily.columns:
                fig_tl.add_trace(go.Bar(
                    x=daily["ts"], y=daily["rain"], name="Lượng mưa",
                    marker=dict(color="#2563eb", opacity=0.25, line=dict(width=0)),
                    yaxis="y2",
                    hovertemplate="%{x|%d/%m}<br>Mưa: %{y:.1f} mm<extra></extra>",
                ))
            if "temp_min" in daily.columns and "temp_max" in daily.columns:
                ts_rev = daily["ts"].iloc[::-1].tolist()
                fig_tl.add_trace(go.Scatter(
                    x=daily["ts"].tolist() + ts_rev,
                    y=daily["temp_max"].tolist() + daily["temp_min"].iloc[::-1].tolist(),
                    fill="toself", fillcolor="rgba(234,88,12,0.07)",
                    line=dict(width=0), name="Biên độ nhiệt",
                    hoverinfo="skip",
                ))
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
            st.plotly_chart(fig_tl, use_container_width=True, config={"displayModeBar": False})
    _card_close()

    # ── Section 2: Heatmap ───────────────────────────────────────────────────────
    _card_open("Heatmap", "Biến thiên chỉ số theo ngày trong năm",
               "Trục Y = tháng · Trục X = ngày · Màu theo giá trị · Hover xem chi tiết")

    hm_col1, _ = st.columns([2, 5], gap="small")
    with hm_col1:
        hm_var = st.selectbox(
            "Biến:", [v for v in ["temp","rain","humidity","wind_speed"] if v in prov_df.columns],
            format_func=lambda x: f"{VAR_META[x]['icon']} {VAR_META[x]['label']}",
            key="l2_hm_var", label_visibility="collapsed",
        )

    if "month" in prov_df.columns and "day" in prov_df.columns and hm_var in prov_df.columns:
        pivot = (prov_df.groupby(["month","day"])[hm_var]
                 .agg("sum" if hm_var == "rain" else "mean")
                 .reset_index()
                 .pivot(index="month", columns="day", values=hm_var))
        pivot   = pivot.reindex(index=range(1,13), columns=range(1,32))
        hm_meta = VAR_META[hm_var]
        fig_hm  = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[str(d) for d in pivot.columns],
            y=[MONTH_NAMES[m-1] for m in pivot.index],
            colorscale=hm_meta.get("cs","RdYlBu_r") or "RdYlBu_r",
            colorbar=_colorbar(hm_meta["unit"]),
            zsmooth="best",
            hovertemplate=f"Tháng %{{y}}, Ngày %{{x}}<br>{hm_meta['label']}: %{{z:.1f}} {hm_meta['unit']}<extra></extra>",
        ))
        fig_hm.update_layout(
            **_base_layout(height=310, margin=dict(l=36, r=20, t=8, b=10)),
            xaxis=_ax("Ngày", tickmode="linear", dtick=5),
            yaxis=dict(**_ax(), autorange="reversed"),
        )
        st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})
    _card_close()

    # ── Section 3: Bar chart nội tỉnh + Wind rose ────────────────────────────────
    _section("PHÂN BỔ TRẠM QUAN TRẮC & HƯỚNG GIÓ", "So sánh dữ liệu giữa các trạm địa phương và phân tích hướng gió chủ đạo")
    col_loc, col_wr = st.columns([1.1, 1], gap="large")

    with col_loc:
        _card_open("Trạm quan trắc", "So sánh các trạm trong tỉnh",
                   "Hover xem giá trị · Màu theo vùng · Sắp xếp tăng dần")
        has_loc = "location" in prov_df.columns and prov_df["location"].nunique() > 1
        if has_loc:
            loc_agg = {c: (c,"sum" if c=="rain" else "mean")
                       for c in ["temp","rain","humidity","wind_speed"] if c in prov_df.columns}
            loc_sum = prov_df.groupby("location", observed=True).agg(**loc_agg).reset_index()
            map_v_opts = [v for v in ["temp","rain","humidity","wind_speed"] if v in loc_sum.columns]
            if map_v_opts:
                map_v = st.radio("Chỉ số:", map_v_opts,
                                 format_func=lambda x: f"{VAR_META[x]['icon']} {VAR_META[x]['label']}",
                                 horizontal=True, key="l2_locbar_v")
                mv  = VAR_META[map_v]
                ls  = loc_sum.dropna(subset=[map_v]).sort_values(map_v, ascending=True)
                clr = REGION_COLORS.get(region, mv["color"])
                fig_lb = go.Figure(go.Bar(
                    y=ls["location"], x=ls[map_v], orientation="h",
                    marker=dict(color=clr, opacity=0.75, line=dict(width=0)),
                    hovertemplate=f"%{{y}}<br>{mv['label']}: %{{x:.1f}} {mv['unit']}<extra></extra>",
                ))
                # Đường trung bình
                mean_val = ls[map_v].mean()
                fig_lb.add_vline(x=mean_val, line=dict(color="#94a3b8", width=1.5, dash="dot"),
                                 annotation_text=f"TB: {mean_val:.1f}",
                                 annotation_font_size=9, annotation_font_color="#94a3b8")
                fig_lb.update_layout(
                    **_base_layout(height=max(280, len(ls)*28), margin=dict(l=120, r=10, t=8, b=10)),
                    xaxis=_ax(f"{mv['label']} ({mv['unit']})"),
                    yaxis=_ax(),
                )
                st.plotly_chart(fig_lb, use_container_width=True, config={"displayModeBar": False})

                # Auto insight: trạm outlier
                if len(ls) >= 3:
                    top_station = ls.iloc[-1]
                    bot_station = ls.iloc[0]
                    diff = top_station[map_v] - bot_station[map_v]
                    _insight_box(
                        f"Chênh lệch giữa trạm cao nhất "
                        f"(<b>{escape(str(top_station['location']))}</b>) và thấp nhất "
                        f"(<b>{escape(str(bot_station['location']))}</b>): "
                        f"<b>{diff:.1f} {mv['unit']}</b> — "
                        f"{'đáng kể, địa hình ảnh hưởng lớn.' if diff > mv.get('threshold', diff) else 'khá đồng đều.'}"
                    )
        else:
            st.info("Tỉnh này chỉ có một trạm quan trắc.")
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
                st.plotly_chart(fig_wr, use_container_width=True, config={"displayModeBar": False})

                # Auto insight: hướng gió thống trị
                dominant_sector = piv_wr.sum(axis=1).idxmax()
                dominant_speed  = piv_wr.loc[dominant_sector].idxmax()
                _insight_box(
                    f"Hướng gió thống trị: <b>{dominant_sector}</b> · "
                    f"Tốc độ phổ biến nhất: <b>{dominant_speed} m/s</b>"
                )
            else:
                st.info("Không đủ dữ liệu hướng gió.")
        else:
            st.info("Không có cột wind_dir.")
        _card_close()

    # ── Section 4: Extreme events ────────────────────────────────────────────────
    _section("SỰ KIỆN CỰC ĐOAN", "Tổng hợp các giá trị kỷ lục được ghi nhận trong giai đoạn phân tích")
    _card_open("Extremes", "Ghi nhận cực trị trong giai đoạn phân tích",
               "Dữ liệu từ tất cả trạm quan trắc trong tỉnh")

    prov_cp       = prov_df.copy()
    prov_cp["_date"] = pd.to_datetime(prov_cp["timestamp"]).dt.date
    prov_cp["_loc"]  = prov_cp["location"].astype(str) if "location" in prov_cp.columns else province

    extreme_cards = []
    if "temp" in prov_cp.columns and not prov_cp["temp"].isna().all():
        r = prov_cp.loc[prov_cp["temp"].idxmax()]
        extreme_cards.append({"type":"hot",  "icon":"🌡️", "label":"NÓNG NHẤT",     "val":f"{_fmt(r['temp'],1)}°C",         "meta":f"{r['_loc']} · {r['_date']}"})
        r = prov_cp.loc[prov_cp["temp"].idxmin()]
        extreme_cards.append({"type":"cold", "icon":"❄️",  "label":"LẠNH NHẤT",     "val":f"{_fmt(r['temp'],1)}°C",         "meta":f"{r['_loc']} · {r['_date']}"})
    if "rain" in prov_cp.columns and not prov_cp["rain"].isna().all():
        dr = prov_cp.groupby(["_date","_loc"], observed=True)["rain"].sum().reset_index()
        if not dr.empty:
            r = dr.loc[dr["rain"].idxmax()]
            extreme_cards.append({"type":"rain", "icon":"🌧️", "label":"MƯA LỚN NHẤT",  "val":f"{_fmt(r['rain'],0)} mm",        "meta":f"{r['_loc']} · {r['_date']}"})
    if "wind_speed" in prov_cp.columns and not prov_cp["wind_speed"].isna().all():
        r = prov_cp.loc[prov_cp["wind_speed"].idxmax()]
        extreme_cards.append({"type":"wind", "icon":"💨", "label":"GIÓ MẠNH NHẤT",  "val":f"{_fmt(r['wind_speed'],1)} m/s", "meta":f"{r['_loc']} · {r['_date']}"})

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
    """
    Main entry point for the Weather Dashboard Tab.
    Initializes CSS, reads global context, and routes to either Layer 1 (National) or Layer 2 (Province Detail).
    """
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

    if "wx_view_mode" not in st.session_state:
        st.session_state["wx_view_mode"] = "forecast"

    # Chế độ Dự báo (Weather Tab)
    if st.session_state["wx_view_mode"] == "forecast":
        wt.render(global_df, show_analysis_button=True)
        return

    # ── Tab Header Card (Description) ──
    st.markdown(
        _info_card_html(
            "PHÂN TÍCH", 
            "Phân tích Chuỗi thời gian & Xu hướng Khí tượng", 
            "Khám phá dữ liệu lịch sử, tương quan các chỉ số và nhận diện các kịch bản thời tiết cực đoan."
        ),
        unsafe_allow_html=True
    )

    layer    = _get_state("wx_layer",    1)
    province = _get_state("wx_province", None)

    if layer == 2 and province:
        _render_layer2(df)
    else:
        _render_layer1(df)
