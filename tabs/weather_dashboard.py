"""
weather_dashboard.py  –  Tab "Thời tiết"
Thiết kế theo design system của app: light theme, Be Vietnam Pro,
dùng .card / .card-title / .kpi-box / .kpi-strip / .q-tag từ main.css.

Cấu trúc 2 tầng:
  Layer 1 – Tổng quan toàn quốc  (bản đồ + xu hướng tháng + xếp hạng tỉnh)
  Layer 2 – Chi tiết tỉnh         (timeline + heatmap + bản đồ trạm + hoa gió + cực trị)
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

# Màu vùng miền – palette nhẹ phù hợp light theme
REGION_COLORS = {"Bắc": "#2563eb", "Trung": "#f59e0b", "Nam": "#16a34a"}

VAR_META = {
    "temp":       {"label": "Nhiệt độ",    "unit": "°C",  "agg": "mean", "cs": "RdYlBu_r", "color": "#ea580c", "accent": "accent-red"},
    "humidity":   {"label": "Độ ẩm",       "unit": "%",   "agg": "mean", "cs": "Blues",     "color": "#0ea5e9", "accent": "accent-slate"},
    "rain":       {"label": "Lượng mưa",   "unit": "mm",  "agg": "sum",  "cs": "YlGnBu",   "color": "#2563eb", "accent": "accent-blue"},
    "wind_speed": {"label": "Tốc độ gió",  "unit": "m/s", "agg": "mean", "cs": "Greens",    "color": "#16a34a", "accent": "accent-green"},
    "wind_dir":   {"label": "Hướng gió",   "unit": "°",   "agg": "none", "cs": None,        "color": "#64748b", "accent": "accent-slate"},
    "pressure":   {"label": "Áp suất",     "unit": "hPa", "agg": "mean", "cs": "Purples",   "color": "#7c3aed", "accent": "accent-blue"},
    "cloud":      {"label": "Mây che phủ", "unit": "%",   "agg": "mean", "cs": "Greys",     "color": "#64748b", "accent": "accent-slate"},
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


# ─── CSS bổ sung (chỉ định nghĩa class không có trong main.css) ────────────────

def _inject_weather_css():
    st.markdown("""
    <style>
    /* Breadcrumb */
    .wth-breadcrumb {
        font-size: .72rem; color: #64748b; margin-bottom: 4px;
        display: flex; align-items: center; gap: 6px;
    }
    .wth-breadcrumb a { color: #2563eb; cursor: pointer; text-decoration: none; font-weight: 600; }
    .wth-breadcrumb-sep { color: #cbd5e1; }

    /* Page title strip */
    .wth-page-title {
        font-size: 1.15rem; font-weight: 700; color: #1e293b;
        margin-bottom: 2px;
    }
    .wth-page-sub {
        font-size: .72rem; color: #64748b; margin-bottom: 20px;
    }

    /* Section divider */
    .wth-section {
        font-size: .65rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: .8px; color: #94a3b8;
        margin: 28px 0 12px 0;
        display: flex; align-items: center; gap: 10px;
    }
    .wth-section::after {
        content: ''; flex: 1; height: 1px; background: #f1f5f9;
    }

    /* KPI accent-green (không có trong main.css) */
    .kpi-box.accent-green { border-top-color: #16a34a; }

    /* Delta sub text */
    .kpi-delta-pos { color: #16a34a; font-size: .7rem; font-weight: 600; }
    .kpi-delta-neg { color: #ea580c; font-size: .7rem; font-weight: 600; }
    .kpi-delta-neu { color: #64748b; font-size: .7rem; }

    /* Insight badge strip */
    .wth-badge-row {
        display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;
    }
    .wth-badge {
        background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 99px;
        font-size: .72rem; font-weight: 500; color: #475569;
        padding: 4px 12px;
    }

    /* Extreme events table */
    .wth-extr-table { width: 100%; border-collapse: collapse; font-size: .82rem; }
    .wth-extr-table th {
        color: #64748b; font-size: .65rem; font-weight: 700;
        letter-spacing: .6px; text-transform: uppercase;
        padding: 7px 12px; text-align: left;
        border-bottom: 1px solid #f1f5f9;
    }
    .wth-extr-table td { padding: 10px 12px; color: #334155; border-bottom: 1px solid #f8fafc; }
    .wth-extr-table tr:last-child td { border-bottom: none; }
    .wth-extr-table tr:hover td { background: #f8fafc; }

    /* Filter bar (season selector) */
    .wth-filter-bar {
        background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 10px 14px; margin-bottom: 16px;
    }
    .wth-filter-label {
        font-size: .65rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: .6px; color: #64748b; margin-bottom: 6px;
    }
    </style>
    """, unsafe_allow_html=True)


# ─── Utilities ─────────────────────────────────────────────────────────────────

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
        gridcolor="rgba(203,213,225,0.4)",
        linecolor="#e2e8f0",
        zeroline=False,
    )
    cfg.update(kw)
    return cfg

def _colorbar(title=""):
    """Plotly colorbar dict – dùng `title` dict thay vì `titlefont` (deprecated)."""
    return dict(
        title=dict(text=title, font=dict(size=9, color="#64748b"), side="right"),
        tickfont=dict(size=8, color="#94a3b8"),
        thickness=9,
        len=0.65,
        outlinewidth=0,
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

def _season_selector(key_prefix: str) -> tuple[str, int | None]:
    all_opts = list(SEASON_PRESETS.keys()) + MONTH_NAMES
    preset = _get_state(f"{key_prefix}_season", "Cả năm")
    sel = st.segmented_control("Giai đoạn", all_opts, default=preset, key=f"{key_prefix}_sg")
    if sel: preset = sel
    _set_state(**{f"{key_prefix}_season": preset})
    month = None
    if isinstance(preset, str) and preset.startswith("Th"):
        try: month = int(preset[2:])
        except ValueError: pass
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


# ─── Aggregation ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _agg_monthly(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "city" not in df.columns: return pd.DataFrame()
    src = df.copy()
    src["month"] = pd.to_datetime(src["timestamp"]).dt.month
    agg = {c: (c, "mean") for c in ["temp","humidity","pressure","cloud","wind_speed"] if c in src.columns}
    if "rain" in src.columns: agg["rain"] = ("rain","sum")
    return src.groupby(["city","month"], observed=True).agg(**agg).reset_index() if agg else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def _agg_annual(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "city" not in df.columns: return pd.DataFrame()
    src = df.copy()
    agg = {c: (c,"mean") for c in ["temp","humidity","pressure","cloud","wind_speed"] if c in src.columns}
    if "rain" in src.columns: agg["rain"] = ("rain","sum")
    result = src.groupby("city", observed=True).agg(**agg).reset_index() if agg else pd.DataFrame()
    if result.empty: return result

    coords = []
    for city in result["city"]:
        sub = src[src["city"] == city]
        lat = sub["lat"].mean() if "lat" in sub.columns else float("nan")
        lon = sub["lon"].mean() if "lon" in sub.columns else float("nan")
        if (pd.isna(lat) or pd.isna(lon)) and city in PROVINCE_COORDS:
            lat, lon = PROVINCE_COORDS[city]
        if (pd.isna(lat) or pd.isna(lon)) and " - " in city:
            p = city.split(" - ")[0]
            if p in PROVINCE_COORDS: lat, lon = PROVINCE_COORDS[p]
        coords.append({"city": city, "lat": lat, "lon": lon})
    result = result.merge(pd.DataFrame(coords), on="city", how="left")
    for col in ["temp","humidity","rain","wind_speed"]:
        if col in result.columns:
            result[f"{col}_rank"] = result[col].rank(ascending=False, method="min").astype("Int64")
    return result


# ─── Card helpers ───────────────────────────────────────────────────────────────

def _card_open(tag: str, title: str, sub: str = ""):
    sub_html = f"<div class='card-sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"<div class='card'>"
        f"<div class='card-title'><span class='q-tag'>{tag}</span>{title}</div>"
        f"{sub_html}",
        unsafe_allow_html=True,
    )

def _card_close():
    st.markdown("</div>", unsafe_allow_html=True)

def _kpi_html(label: str, value: str, unit: str, accent: str, sub: str = "") -> str:
    sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
    return (
        f"<div class='kpi-box {accent}'>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"<div class='kpi-val'>{value} <span class='u'>{unit}</span></div>"
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


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 – TỔNG QUAN TOÀN QUỐC
# ═══════════════════════════════════════════════════════════════════════════════

def _render_layer1(df: pd.DataFrame):
    st.markdown("<div class='wth-page-title'>🌤 Thời tiết Toàn quốc</div>", unsafe_allow_html=True)
    st.markdown("<div class='wth-page-sub'>Dữ liệu quan trắc Việt Nam 2025 · Chọn chỉ số và giai đoạn để phân tích</div>", unsafe_allow_html=True)

    # ── Controls ────────────────────────────────────────────────────────────────
    c_season, c_var = st.columns([1.6, 1], gap="large")
    with c_season:
        preset, month = _season_selector("l1")
    with c_var:
        var_opts = [v for v in ["temp","humidity","rain","wind_speed"] if v in df.columns]
        cur_var  = _get_state("l1_var", var_opts[0] if var_opts else "temp")
        if cur_var not in var_opts: cur_var = var_opts[0]
        cur_var = st.segmented_control(
            "Chỉ số", var_opts,
            format_func=lambda x: VAR_META[x]["label"],
            selection_mode="single", default=cur_var, key="l1_var_sg",
        ) or cur_var
        _set_state(l1_var=cur_var)

    filtered = _filter_by_season(df, preset, month)
    annual   = _agg_annual(filtered)
    monthly  = _agg_monthly(filtered)
    meta     = VAR_META.get(cur_var, {})

    # ── KPI Strip ───────────────────────────────────────────────────────────────
    kpis = []
    if not annual.empty:
        if "temp"       in annual.columns: kpis.append(_kpi_html("Nhiệt độ TB",  _fmt(annual["temp"].mean(),1),       "°C",  "accent-red"))
        if "humidity"   in annual.columns: kpis.append(_kpi_html("Độ ẩm TB",     _fmt(annual["humidity"].mean(),0),   "%",   "accent-slate"))
        if "rain"       in annual.columns: kpis.append(_kpi_html("Tổng mưa",     _fmt(annual["rain"].sum(),0),        "mm",  "accent-blue"))
        if "wind_speed" in annual.columns: kpis.append(_kpi_html("Tốc độ gió TB",_fmt(annual["wind_speed"].mean(),1),"m/s", "accent-green"))
    if kpis: _kpi_row(kpis)

    # ── Bản đồ + Xu hướng tháng ─────────────────────────────────────────────────
    col_map, col_trend = st.columns([1.35, 1], gap="large")

    with col_map:
        _card_open("Bản đồ", f"Phân bổ {meta.get('label','')} theo tỉnh/thành",
                   "Kích thước & màu sắc theo giá trị chỉ số đã chọn")
        if not annual.empty and cur_var in annual.columns:
            ann_p = annual.dropna(subset=["lat","lon", cur_var])
            n_tot = len(annual)
            rank_col = ann_p[f"{cur_var}_rank"].fillna(0).astype(int) if f"{cur_var}_rank" in ann_p.columns else pd.Series(0, index=ann_p.index)
            cb = _colorbar(meta.get("unit",""))
            fig_map = go.Figure(go.Scattermapbox(
                lat=ann_p["lat"], lon=ann_p["lon"], mode="markers",
                marker=dict(
                    size=14, opacity=0.88,
                    color=ann_p[cur_var],
                    colorscale=meta.get("cs","RdYlBu_r") or "RdYlBu_r",
                    showscale=True,
                    colorbar=cb,
                ),
                text=ann_p["city"],
                customdata=np.column_stack([ann_p[cur_var].round(1), rank_col]),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"{meta.get('label','')}: %{{customdata[0]}} {meta.get('unit','')}<br>"
                    f"Xếp hạng: %{{customdata[1]}}/{n_tot}<extra></extra>"
                ),
            ))
            fig_map.update_layout(
                **_base_layout(height=420, margin=dict(l=0,r=0,t=0,b=0)),
                mapbox=dict(style="carto-positron", zoom=4.5, center=dict(lat=16.5, lon=106.5)),
            )
            st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})

            c_sel, c_btn = st.columns([3,1], gap="small")
            with c_sel:
                sel = st.selectbox("Chọn tỉnh xem chi tiết:", ["—"] + sorted(annual["city"].tolist()),
                                   key="l1_drill_sel", label_visibility="collapsed")
            with c_btn:
                if st.button("Chi tiết →", type="primary", key="l1_drill_btn", use_container_width=True):
                    if sel != "—": _go_layer2(sel)
        else:
            st.info("Không đủ dữ liệu bản đồ.")
        _card_close()

    with col_trend:
        # Xu hướng tháng
        _card_open("Xu hướng", f"{meta.get('label','')} & Lượng mưa theo tháng",
                   "Đường = chỉ số đã chọn  ·  Cột = lượng mưa")
        if not monthly.empty:
            agg_fns = {c:(c,"sum" if c=="rain" else "mean") for c in ["temp","humidity","rain","wind_speed"] if c in monthly.columns}
            nat_mon = monthly.groupby("month", observed=True).agg(**agg_fns).reset_index() if agg_fns else pd.DataFrame()
            if not nat_mon.empty:
                xl    = [MONTH_NAMES[m-1] for m in nat_mon["month"]]
                var2  = "rain" if cur_var != "rain" else "humidity"
                fig_t = go.Figure()
                if var2 in nat_mon.columns:
                    m2 = VAR_META[var2]
                    fig_t.add_trace(go.Bar(
                        x=xl, y=nat_mon[var2], name=m2["label"],
                        marker=dict(color=m2["color"], opacity=0.25, line=dict(width=0)),
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
                m2_meta = VAR_META.get(var2, {})
                fig_t.update_layout(
                    **_base_layout(height=230),
                    yaxis=_ax(f"{meta.get('label','')} ({meta.get('unit','')})"),
                    yaxis2=dict(**_ax(f"{m2_meta.get('label','')} ({m2_meta.get('unit','')})"),
                                overlaying="y", side="right", showgrid=False),
                    legend=dict(orientation="h", x=0, y=1.08, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                    hovermode="x unified", bargap=0.25,
                )
                st.plotly_chart(fig_t, use_container_width=True, config={"displayModeBar": False})
                if cur_var in nat_mon.columns:
                    m_hi = int(nat_mon.loc[nat_mon[cur_var].idxmax(), "month"])
                    m_lo = int(nat_mon.loc[nat_mon[cur_var].idxmin(), "month"])
                    st.markdown(
                        f"<div style='display:flex;gap:8px;margin-top:8px'>"
                        f"<div style='flex:1;background:#fff7ed;border:1px solid #fed7aa;padding:8px 12px;border-radius:8px'>"
                        f"<div class='kpi-lbl'>Cao nhất</div>"
                        f"<div style='font-size:.95rem;font-weight:700;color:#ea580c'>Tháng {m_hi}</div></div>"
                        f"<div style='flex:1;background:#eff6ff;border:1px solid #bfdbfe;padding:8px 12px;border-radius:8px'>"
                        f"<div class='kpi-lbl'>Thấp nhất</div>"
                        f"<div style='font-size:.95rem;font-weight:700;color:#2563eb'>Tháng {m_lo}</div></div>"
                        f"</div>", unsafe_allow_html=True
                    )
        else:
            st.info("Không đủ dữ liệu xu hướng.")
        _card_close()

        # Phân phối vùng miền
        _card_open("Vùng miền", f"Phân bổ {meta.get('label','')} Bắc – Trung – Nam")
        if not annual.empty and cur_var in annual.columns:
            annual["region"] = annual["city"].map(PROVINCE_REGION).fillna("Khác")
            fig_box = go.Figure()
            for reg in REGION_ORDER:
                d = annual[annual["region"] == reg][cur_var].dropna()
                if d.empty: continue
                fig_box.add_trace(go.Box(
                    y=d, name=reg, boxpoints="all", jitter=0.4, pointpos=-1.6,
                    marker=dict(size=4, color=REGION_COLORS.get(reg,"#94a3b8"), opacity=0.6),
                    line=dict(color=REGION_COLORS.get(reg,"#94a3b8"), width=1.5),
                    hovertemplate=f"{reg}<br>{meta.get('label','')}: %{{y:.1f}} {meta.get('unit','')}<extra></extra>",
                ))
            fig_box.update_layout(
                **_base_layout(height=185, margin=dict(l=8,r=8,t=8,b=8)),
                yaxis=_ax(f"{meta.get('unit','')}"), xaxis=_ax(), showlegend=False,
            )
            st.plotly_chart(fig_box, use_container_width=True, config={"displayModeBar": False})
        _card_close()

    # ── Xếp hạng tỉnh thành ─────────────────────────────────────────────────────
    _section("XẾPHẠNG TỈNH THÀNH")
    _card_open("Ranking", f"Top tỉnh thành theo {meta.get('label','')} · {preset}")

    c_reg, c_asc = st.columns([3,1], gap="small")
    with c_reg:
        reg_f = st.radio("Vùng:", ["Tất cả"] + REGION_ORDER, horizontal=True, key="l1_rank_reg")
    with c_asc:
        asc_f = st.checkbox("Tăng dần", key="l1_rank_asc")

    if not annual.empty and cur_var in annual.columns:
        annual["region"] = annual["city"].map(PROVINCE_REGION).fillna("Khác")
        rb = annual[["city","region",cur_var]].dropna(subset=[cur_var])
        if reg_f != "Tất cả": rb = rb[rb["region"] == reg_f]
        rb = rb.sort_values(cur_var, ascending=asc_f).head(20)
        bar_clrs = [REGION_COLORS.get(r,"#94a3b8") for r in rb["region"]]
        fig_rank = go.Figure(go.Bar(
            y=rb["city"], x=rb[cur_var], orientation="h",
            marker=dict(color=bar_clrs, opacity=0.8, line=dict(width=0)),
            hovertemplate=f"%{{y}}<br>{meta.get('label','')}: %{{x:.1f}} {meta.get('unit','')}<extra></extra>",
        ))
        fig_rank.update_layout(
            **_base_layout(height=max(340, len(rb)*22), margin=dict(l=140,r=10,t=10,b=10)),
            xaxis=_ax(f"{meta.get('label','')} ({meta.get('unit','')})"),
            yaxis=_ax(autorange="reversed"), showlegend=False,
        )
        st.plotly_chart(fig_rank, use_container_width=True, config={"displayModeBar": False})
    _card_close()


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2 – CHI TIẾT TỈNH
# ═══════════════════════════════════════════════════════════════════════════════

def _render_layer2(df: pd.DataFrame):
    province = _get_state("wx_province", None)
    if not province:
        _go_layer1(); return

    # Breadcrumb
    st.markdown(
        f"<div class='wth-breadcrumb'>"
        f"<a id='wth-bc-home'>🏠 Toàn quốc</a>"
        f"<span class='wth-breadcrumb-sep'>/</span>"
        f"<span>{province}</span></div>",
        unsafe_allow_html=True,
    )
    if st.button("← Quay lại Toàn quốc", key="l2_back"):
        _go_layer1()

    st.markdown(f"<div class='wth-page-title'>📍 {province}</div>", unsafe_allow_html=True)
    st.markdown("<div class='wth-page-sub'>Phân tích khí tượng chi tiết từ trạm quan trắc địa phương</div>", unsafe_allow_html=True)

    # Controls
    c_var, c_season = st.columns([1, 1.6], gap="large")
    with c_var:
        l2_vars = [v for v in ["temp","rain","humidity","wind_speed","pressure"] if v in df.columns]
        pv = st.segmented_control("Chỉ số", l2_vars,
                                   format_func=lambda x: VAR_META[x]["label"],
                                   selection_mode="single", default=l2_vars[0], key="l2_pv_sg") or l2_vars[0]
    with c_season:
        preset, month = _season_selector("l2")

    filtered = _filter_by_season(df, preset, month)

    with st.spinner(f"Đang tải dữ liệu {province}..."):
        prov_df = load_weather_province_detail(province)
        if prov_df is None or prov_df.empty:
            st.error(f"Không tìm thấy dữ liệu cho {province}.")
            return
        prov_df = _filter_by_season(prov_df, preset, month)

    if prov_df.empty:
        st.warning("Không có dữ liệu trong giai đoạn này."); return

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

    # ── KPI Strip ───────────────────────────────────────────────────────────────
    kpis = []
    if "temp" in prov_df.columns:
        v = prov_df["temp"].mean()
        kpis.append(_kpi_html("Nhiệt độ TB", _fmt(v,1), "°C", "accent-red", _delta_sub("temp",v)))
    if "humidity" in prov_df.columns:
        v = prov_df["humidity"].mean()
        kpis.append(_kpi_html("Độ ẩm TB", _fmt(v,0), "%", "accent-slate", _delta_sub("humidity",v)))
    if "rain" in prov_df.columns:
        v = prov_df["rain"].sum()
        kpis.append(_kpi_html("Tổng mưa", _fmt(v,0), "mm", "accent-blue"))
    if "wind_speed" in prov_df.columns:
        v = prov_df["wind_speed"].max()
        kpis.append(_kpi_html("Gió cực đại", _fmt(v,1), "m/s", "accent-green"))
    if kpis: _kpi_row(kpis)

    # ── Timeline Nhiệt độ & Mưa ─────────────────────────────────────────────────
    _section("DIỄN BIẾN THỜI GIAN")
    _card_open("Timeline", "Nhiệt độ & Lượng mưa hàng ngày",
               "Đường đỏ = nhiệt độ  ·  Cột xanh = lượng mưa")

    if "month" in prov_df.columns and "day" in prov_df.columns:
        daily_agg = {c:(c,"sum" if c=="rain" else "mean")
                     for c in ["temp","rain","humidity"] if c in prov_df.columns}
        if daily_agg:
            daily = prov_df.groupby(["month","day"], observed=True).agg(**daily_agg).reset_index()
            daily["ts"] = (pd.to_datetime("2025-01-01")
                           + pd.to_timedelta((daily["month"]-1)*30 + daily["day"]-1, unit="D"))
            fig_tl = go.Figure()
            if "rain" in daily.columns:
                fig_tl.add_trace(go.Bar(
                    x=daily["ts"], y=daily["rain"], name="Lượng mưa",
                    marker=dict(color="#2563eb", opacity=0.3, line=dict(width=0)),
                    yaxis="y2",
                    hovertemplate="%{x|%d/%m}<br>Mưa: %{y:.1f} mm<extra></extra>",
                ))
            if "temp" in daily.columns:
                fig_tl.add_trace(go.Scatter(
                    x=daily["ts"], y=daily["temp"], name="Nhiệt độ",
                    mode="lines", line=dict(color="#ea580c", width=2, shape="spline"),
                    fill="tozeroy", fillcolor="rgba(234,88,12,0.05)",
                    hovertemplate="%{x|%d/%m}<br>Nhiệt độ: %{y:.1f}°C<extra></extra>",
                ))
            fig_tl.update_layout(
                **_base_layout(height=260),
                yaxis=_ax("Nhiệt độ (°C)"),
                yaxis2=dict(**_ax("Mưa (mm)"), overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", x=0, y=1.08, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                hovermode="x unified", bargap=0.1,
            )
            st.plotly_chart(fig_tl, use_container_width=True, config={"displayModeBar": False})
    _card_close()

    # ── Heatmap Calendar ────────────────────────────────────────────────────────
    _card_open("Heatmap", "Biến thiên chỉ số theo ngày trong năm", "Chọn biến để xem phân bổ")
    hm_var = st.selectbox(
        "Biến:", [v for v in ["temp","rain","humidity"] if v in prov_df.columns],
        format_func=lambda x: VAR_META[x]["label"], key="l2_hm_var", label_visibility="collapsed",
    )
    if "month" in prov_df.columns and "day" in prov_df.columns and hm_var in prov_df.columns:
        pivot = (prov_df.groupby(["month","day"])[hm_var]
                 .agg("sum" if hm_var == "rain" else "mean")
                 .reset_index()
                 .pivot(index="month", columns="day", values=hm_var))
        hm_meta = VAR_META[hm_var]
        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[str(d) for d in pivot.columns],
            y=[MONTH_NAMES[m-1] for m in pivot.index],
            colorscale=hm_meta.get("cs","RdYlBu_r") or "RdYlBu_r",
            colorbar=_colorbar(hm_meta["unit"]),
            hovertemplate=f"Tháng %{{y}}, Ngày %{{x}}<br>{hm_meta['label']}: %{{z:.1f}} {hm_meta['unit']}<extra></extra>",
        ))
        fig_hm.update_layout(
            **_base_layout(height=300, margin=dict(l=36,r=20,t=8,b=10)),
            xaxis=_ax("Ngày", tickmode="linear", dtick=5),
            yaxis=dict(**_ax(), autorange="reversed"),
        )
        st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})
    _card_close()

    # ── Bản đồ trạm + Hoa gió ───────────────────────────────────────────────────
    _section("PHÂN BỔ ĐỊA ĐIỂM & HƯỚNG GIÓ")
    col_loc, col_wr = st.columns([1.1, 1], gap="large")

    with col_loc:
        _card_open("Bản đồ", "Bản đồ trạm quan trắc", "Màu theo chỉ số đã chọn")
        has_loc    = "location" in prov_df.columns and prov_df["location"].nunique() > 1
        has_coords = "lat" in prov_df.columns and "lon" in prov_df.columns

        loc_agg = {c:(c,"sum" if c=="rain" else "mean")
                   for c in ["temp","rain","humidity","wind_speed","lat","lon"] if c in prov_df.columns}
        loc_sum = (prov_df.groupby("location", observed=True).agg(**loc_agg).reset_index()
                   if has_loc and loc_agg else pd.DataFrame())

        map_v = st.radio("Màu theo:", [v for v in ["temp","rain"] if v in prov_df.columns],
                          format_func=lambda x: VAR_META[x]["label"],
                          horizontal=True, key="l2_locmap_v") if has_loc else None

        if map_v and not loc_sum.empty and has_coords and map_v in loc_sum.columns:
            lp  = loc_sum.dropna(subset=["lat","lon", map_v])
            mv  = VAR_META[map_v]
            fig_lm = go.Figure(go.Scattermapbox(
                lat=lp["lat"], lon=lp["lon"], mode="markers",
                marker=dict(
                    size=13, color=lp[map_v], opacity=0.88,
                    colorscale=mv.get("cs","RdYlBu_r") or "RdYlBu_r",
                    showscale=True, colorbar=_colorbar(mv["unit"]),
                ),
                text=lp["location"],
                hovertemplate=f"<b>%{{text}}</b><br>{mv['label']}: %{{marker.color:.1f}} {mv['unit']}<extra></extra>",
            ))
            fig_lm.update_layout(
                **_base_layout(height=330, margin=dict(l=0,r=0,t=0,b=0)),
                mapbox=dict(style="carto-positron", zoom=7,
                            center=dict(lat=float(lp["lat"].mean()), lon=float(lp["lon"].mean()))),
            )
            st.plotly_chart(fig_lm, use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})
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
            st.plotly_chart(fig_fb, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Không có dữ liệu theo địa điểm.")
        _card_close()

    with col_wr:
        _card_open("Hoa gió", "Phân bổ hướng & tốc độ gió", "Độ dài cánh = tần suất xuất hiện")
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
                # Palette nhẹ phù hợp light theme
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
                    **_base_layout(height=330),
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(showticklabels=True, ticks="",
                                        gridcolor="rgba(203,213,225,0.5)",
                                        tickfont=dict(size=7, color="#94a3b8")),
                        angularaxis=dict(direction="clockwise", rotation=90,
                                         gridcolor="rgba(203,213,225,0.3)",
                                         tickfont=dict(size=9, color="#64748b")),
                    ),
                    legend=dict(orientation="h", x=0.05, y=-0.1,
                                font=dict(size=8, color="#64748b"), bgcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig_wr, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Không đủ dữ liệu hướng gió.")
        else:
            st.info("Không có cột wind_dir.")
        _card_close()

    # ── Sự kiện cực đoan ────────────────────────────────────────────────────────
    _section("SỰ KIỆN CỰC ĐOAN")
    _card_open("Extreme", "Ghi nhận cực trị trong giai đoạn phân tích")

    prov_df = prov_df.copy()
    prov_df["_date"] = pd.to_datetime(prov_df["timestamp"]).dt.date
    prov_df["_loc"]  = prov_df["location"].astype(str) if "location" in prov_df.columns else province
    extremes = []
    if "temp" in prov_df.columns:
        r = prov_df.loc[prov_df["temp"].idxmax()]
        extremes.append({"Loại": "🌡 Nóng nhất",    "Địa điểm": str(r["_loc"]), "Ngày": str(r["_date"]), "Giá trị": f"{_fmt(r['temp'],1)} °C"})
        r = prov_df.loc[prov_df["temp"].idxmin()]
        extremes.append({"Loại": "❄️ Lạnh nhất",    "Địa điểm": str(r["_loc"]), "Ngày": str(r["_date"]), "Giá trị": f"{_fmt(r['temp'],1)} °C"})
    if "rain" in prov_df.columns:
        dr = prov_df.groupby(["_date","_loc"], observed=True)["rain"].sum().reset_index()
        if not dr.empty:
            r = dr.loc[dr["rain"].idxmax()]
            extremes.append({"Loại": "🌧 Mưa lớn nhất", "Địa điểm": str(r["_loc"]), "Ngày": str(r["_date"]), "Giá trị": f"{_fmt(r['rain'],0)} mm"})
    if "wind_speed" in prov_df.columns:
        r = prov_df.loc[prov_df["wind_speed"].idxmax()]
        extremes.append({"Loại": "💨 Gió mạnh nhất", "Địa điểm": str(r["_loc"]), "Ngày": str(r["_date"]), "Giá trị": f"{_fmt(r['wind_speed'],1)} m/s"})

    if extremes:
        rows = "".join(
            f"<tr>"
            f"<td><b>{escape(e['Loại'])}</b></td>"
            f"<td>{escape(e['Địa điểm'])}</td>"
            f"<td style='color:#94a3b8'>{escape(e['Ngày'])}</td>"
            f"<td><b style='color:#1e293b'>{escape(e['Giá trị'])}</b></td>"
            f"</tr>"
            for e in extremes
        )
        st.markdown(
            f"<table class='wth-extr-table'>"
            "<thead><tr><th>Loại</th><th>Địa điểm</th><th>Ngày</th><th>Giá trị</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>",
            unsafe_allow_html=True,
        )
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
        st.warning("Không có dữ liệu thời tiết."); return
    if "city" not in df.columns or "timestamp" not in df.columns:
        st.warning("Dữ liệu thiếu cột city/timestamp."); return

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