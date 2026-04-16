from textwrap import dedent
from html import escape
import re
import unicodedata
import uuid

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import list_detail_provinces, load_province_detail


WEATHER_FEATURES = [
    "temp",
    "humidity",
    "rain",
    "wind_speed",
    "wind_dir",
    "pressure",
    "cloud",
]

WIND_SECTORS = [
    "B", "BDB", "DB", "DDB", "D", "DDN", "DN", "NDN",
    "N", "NTN", "TN", "TTN", "T", "TTB", "TB", "BTB",
]
WIND_SPEED_BINS = [0, 5, 10, 20, 35, np.inf]
WIND_SPEED_LABELS = ["0-5", "5-10", "10-20", "20-35", ">35"]
WEEKDAY_VI = {
    "Mon": "Thứ 2", "Tue": "Thứ 3", "Wed": "Thứ 4",
    "Thu": "Thứ 5", "Fri": "Thứ 6", "Sat": "Thứ 7", "Sun": "CN",
}


def _html(content: str) -> str:
    return dedent(content).strip()


def _fmt_num(value, decimals=1, suffix=""):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}{suffix}"


def _wind_dir_label(deg):
    if deg is None or pd.isna(deg):
        return "N/A"
    idx = int(((float(deg) % 360) + 11.25) // 22.5) % 16
    return WIND_SECTORS[idx]


def _condition_from_weather(rain, cloud):
    rain = 0.0 if rain is None or pd.isna(rain) else float(rain)
    cloud = 0.0 if cloud is None or pd.isna(cloud) else float(cloud)
    if rain < 0.05:
        rain = 0.0
    if rain >= 8:
        return "Mưa lớn"
    if rain >= 2:
        return "Mưa vừa"
    if rain > 0:
        return "Mưa nhẹ"
    if cloud >= 85:
        return "Nhiều mây"
    if cloud >= 55:
        return "Có mây"
    if cloud >= 20:
        return "Ít mây"
    return "Trời quang"


def _condition_token(condition: str) -> str:
    if condition.startswith("Mưa"):
        return "RAIN"
    if condition in {"Nhiều mây", "Có mây", "Ít mây"}:
        return "CLOUD"
    return "SUN"


def _svg_icon_markup(token: str, size: int = 40, inline: bool = False) -> str:
    """Return weather SVG markup directly to avoid data-URI render issues."""
    icon_map = {
        "SUN": (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
            "<circle cx='24' cy='24' r='10' fill='#FFCA28'/>"
            "<g stroke='#FFB300' stroke-width='3' stroke-linecap='round'>"
            "<line x1='24' y1='4' x2='24' y2='10'/>"
            "<line x1='24' y1='38' x2='24' y2='44'/>"
            "<line x1='4' y1='24' x2='10' y2='24'/>"
            "<line x1='38' y1='24' x2='44' y2='24'/>"
            "<line x1='9.4' y1='9.4' x2='13.7' y2='13.7'/>"
            "<line x1='34.3' y1='34.3' x2='38.6' y2='38.6'/>"
            "<line x1='38.6' y1='9.4' x2='34.3' y2='13.7'/>"
            "<line x1='9.4' y1='38.6' x2='13.7' y2='34.3'/>"
            "</g></svg>"
        ),
        "CLOUD": (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
            "<circle cx='24' cy='20' r='8' fill='#FFCA28'/>"
            "<g stroke='#FFB300' stroke-width='2' stroke-linecap='round'>"
            "<line x1='24' y1='6' x2='24' y2='9'/>"
            "<line x1='14' y1='10' x2='16.1' y2='12.1'/>"
            "<line x1='34' y1='10' x2='31.9' y2='12.1'/>"
            "</g>"
            "<path d='M12 32 a8 8 0 0 1 0-16 10 10 0 0 1 20 0 6 6 0 0 1 0 16Z' fill='#90CAF9'/>"
            "<path d='M14 32 a6 6 0 0 1 0-12 8 8 0 0 1 16 0 4 4 0 0 1 0 12Z' fill='#BBDEFB'/>"
            "</svg>"
        ),
        "RAIN": (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
            "<path d='M10 26 a10 10 0 0 1 2-20 12 12 0 0 1 24 2 8 8 0 0 1 0 18Z' fill='#90CAF9'/>"
            "<path d='M12 26 a8 8 0 0 1 1.5-15.5 10 10 0 0 1 20 1.5 6 6 0 0 1 0 14Z' fill='#BBDEFB'/>"
            "<g stroke='#29B6F6' stroke-width='2.5' stroke-linecap='round'>"
            "<line x1='16' y1='32' x2='14' y2='38'/>"
            "<line x1='24' y1='32' x2='22' y2='38'/>"
            "<line x1='32' y1='32' x2='30' y2='38'/>"
            "</g></svg>"
        ),
    }
    svg = icon_map.get(token, icon_map["SUN"])
    style = f"width:{size}px;height:{size}px;"
    if inline:
        style += "vertical-align:-3px;margin-right:4px;display:inline-block;"
    else:
        style += "display:block;"
    return svg.replace("<svg ", f"<svg style='{style}' ", 1)


def _condition_img(condition: str, size: int = 40) -> str:
    token = _condition_token(condition)
    return _svg_icon_markup(token, size=size, inline=False)


def _condition_svg_inline(condition: str, size: int = 16) -> str:
    token = _condition_token(condition)
    return _svg_icon_markup(token, size=size, inline=True)


def _weekday_vi(ts: pd.Timestamp) -> str:
    key = ts.strftime("%a")
    return WEEKDAY_VI.get(key, key)


def _heat_index_c(temp_c, humidity):
    if temp_c is None or humidity is None or pd.isna(temp_c) or pd.isna(humidity):
        return np.nan
    temp_c = float(temp_c)
    humidity = float(humidity)
    if temp_c < 27 or humidity < 40:
        return temp_c
    temp_f = temp_c * 9 / 5 + 32
    hi_f = (
        -42.379 + 2.04901523 * temp_f + 10.14333127 * humidity
        - 0.22475541 * temp_f * humidity - 6.83783e-3 * temp_f**2
        - 5.481717e-2 * humidity**2 + 1.22874e-3 * temp_f**2 * humidity
        + 8.5282e-4 * temp_f * humidity**2 - 1.99e-6 * temp_f**2 * humidity**2
    )
    return (hi_f - 32) * 5 / 9


def _wind_chill_c(temp_c, wind_kmh):
    if temp_c is None or wind_kmh is None or pd.isna(temp_c) or pd.isna(wind_kmh):
        return np.nan
    temp_c = float(temp_c)
    wind_kmh = float(wind_kmh)
    if temp_c > 10 or wind_kmh <= 4.8:
        return temp_c
    return 13.12 + 0.6215 * temp_c - 11.37 * (wind_kmh**0.16) + 0.3965 * temp_c * (wind_kmh**0.16)


def _feels_like_c(temp_c, humidity, wind_speed):
    if temp_c is None or pd.isna(temp_c):
        return np.nan
    temp_c = float(temp_c)
    heat = _heat_index_c(temp_c, humidity)
    chill = _wind_chill_c(temp_c, wind_speed)
    if temp_c >= 27 and not pd.isna(heat):
        return heat
    if temp_c <= 10 and not pd.isna(chill):
        return chill
    return temp_c


def _fallback_ml(fig, h=None, **kwargs):
    base = dict(
        margin=dict(l=8, r=8, t=24, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=10, color="#334155"),
    )
    if h is not None:
        base["height"] = h
    base.update(kwargs)
    fig.update_layout(**base)
    return fig


def _fallback_ax(title=""):
    cfg = dict(
        tickfont=dict(color="#64748b", size=9),
        gridcolor="rgba(0,0,0,0.05)",
        linecolor="#dbe7f2",
        zeroline=False,
    )
    if title:
        cfg["title"] = dict(text=title, font=dict(size=9, color="#64748b"))
    return cfg


def _get_plot_helpers(ctx):
    ml_fn = ctx.get("ml") if callable(ctx.get("ml")) else _fallback_ml
    ax_fn = ctx.get("ax") if callable(ctx.get("ax")) else _fallback_ax
    return ml_fn, ax_fn


# ─── CSS ─────────────────────────────────────────────────────────────────────

def _inject_weather_css():
    st.markdown(
        _html("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        /* ── Reset & base ── */
        .wx-root { font-family: 'Inter', sans-serif; }

        /* ── HERO BANNER (top blue card) ── */
        .wx-hero {
            position: relative;
            overflow: hidden;
            border-radius: 20px;
            background: linear-gradient(160deg, #1565C0 0%, #1976D2 30%, #42A5F5 70%, #81D4FA 100%);
            padding: 20px 22px 24px;
            margin-bottom: 14px;
            box-shadow: 0 8px 32px rgba(21, 101, 192, 0.30);
            color: #fff;
        }
        .wx-hero::before {
            content: '';
            position: absolute;
            inset: 0;
            background:
                radial-gradient(200px 80px at 80% 10%, rgba(255,255,255,0.18) 0%, transparent 70%),
                radial-gradient(100px 50px at 15% 80%, rgba(255,255,255,0.10) 0%, transparent 70%);
            pointer-events: none;
        }
        /* Stable bottom fade instead of decorative bump (better on mobile) */
        .wx-hero::after {
            content: '';
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            height: 52px;
            background: linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(2, 18, 40, 0.24) 100%);
            pointer-events: none;
        }
        .wx-hero-inner { position: relative; z-index: 2; }

        /* breadcrumb */
        .wx-breadcrumb {
            font-size: 0.72rem;
            font-weight: 600;
            color: rgba(255,255,255,0.80);
            margin-bottom: 10px;
            letter-spacing: 0.2px;
        }
        .wx-breadcrumb a { color: rgba(255,255,255,0.80); text-decoration: none; }
        .wx-breadcrumb a:hover { color: #fff; }

        /* AQI | Weather toggle pill */
        .wx-nav-pills {
            display: inline-flex;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.25);
            margin-bottom: 14px;
        }
        .wx-nav-pill {
            padding: 6px 16px;
            font-size: 0.80rem;
            font-weight: 700;
            color: rgba(255,255,255,0.75);
            background: rgba(255,255,255,0.12);
            cursor: default;
        }
        .wx-nav-pill.active {
            background: rgba(255,255,255,0.28);
            color: #fff;
        }

        /* Main grid: left=temp info, right=hourly strip */
        .wx-hero-grid {
            display: grid;
            grid-template-columns: 1.4fr 1fr;
            gap: 18px;
            align-items: start;
            padding-bottom: 8px;
        }

        /* Big temperature display */
        .wx-title-row { display: flex; align-items: flex-end; gap: 10px; margin-bottom: 2px; }
        .wx-city-name {
            font-size: 1.05rem;
            font-weight: 700;
            color: rgba(255,255,255,0.95);
            margin-bottom: 4px;
        }
        .wx-temp-big {
            font-size: 3.8rem;
            font-weight: 900;
            line-height: 1;
            color: #fff;
            letter-spacing: -2px;
        }
        .wx-temp-unit { font-size: 1.4rem; font-weight: 700; color: rgba(255,255,255,0.80); margin-bottom: 8px; }
        .wx-cond-text {
            font-size: 1.05rem;
            font-weight: 700;
            color: rgba(255,255,255,0.95);
            margin: 6px 0 4px;
        }
        .wx-hilow {
            font-size: 0.82rem;
            color: rgba(255,255,255,0.80);
            margin-bottom: 8px;
        }

        /* Mini stat pills below temperature */
        .wx-stat-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
        .wx-stat-pill {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(255,255,255,0.18);
            border: 1px solid rgba(255,255,255,0.22);
            border-radius: 20px;
            padding: 4px 10px;
            font-size: 0.74rem;
            font-weight: 600;
            color: #fff;
        }
        .wx-stat-pill svg { flex-shrink: 0; }

        /* ── HOURLY STRIP (right panel in hero) ── */
        .wx-hour-panel {
            background: rgba(10, 30, 60, 0.45);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 16px;
            padding: 12px;
        }
        .wx-hour-tabs {
            display: flex;
            gap: 6px;
            margin-bottom: 10px;
        }
        .wx-hour-tab {
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 0.73rem;
            font-weight: 700;
            background: rgba(255,255,255,0.12);
            color: rgba(255,255,255,0.65);
            border: 1px solid transparent;
        }
        .wx-hour-tab.active {
            background: rgba(255,255,255,0.28);
            color: #fff;
            border-color: rgba(255,255,255,0.30);
        }
        .wx-hour-strip {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 6px;
        }
        .wx-hour-item {
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 10px;
            padding: 7px 4px;
            text-align: center;
        }
        .wx-hour-item.now { background: rgba(255,255,255,0.24); border-color: rgba(255,255,255,0.35); }
        .wx-hour-time  { font-size: 0.60rem; color: rgba(255,255,255,0.70); font-weight: 700; }
        .wx-hour-temp  { font-size: 0.88rem; font-weight: 800; color: #fff; margin-top: 4px; }
        .wx-hour-rain  { font-size: 0.58rem; color: #90CAF9; margin-top: 2px; }
        .wx-hour-note  { font-size: 0.65rem; color: rgba(255,255,255,0.50); margin-top: 8px; }

        /* ── PARAMS SECTION ── */
        .wx-section-wrap { margin-bottom: 14px; }
        .wx-section-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 12px;
            padding-left: 2px;
            letter-spacing: 0.2px;
        }
        .wx-block-head {
            margin-bottom: 10px;
            border-left: 4px solid #38bdf8;
            padding-left: 10px;
        }
        .wx-block-title {
            font-size: 1.04rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
        }
        .wx-block-sub {
            font-size: 0.72rem;
            color: #64748b;
            margin-top: 4px;
        }

        /* 2-row grid: top row 3 cols, bottom row 3 cols */
        .wx-params-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }

        /* Base card – teal/slate gradient like AQI.in */
        .wx-pcard {
            border-radius: 16px;
            background: linear-gradient(145deg, #2d6a8a 0%, #1e4f6b 100%);
            border: 1px solid rgba(255,255,255,0.12);
            padding: 15px 16px;
            box-shadow: 0 4px 16px rgba(15,40,60,0.18);
            min-height: 118px;
            position: relative;
            overflow: hidden;
            color: #f0f8ff;
            transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
        }
        .wx-pcard::before {
            content:''; position:absolute; inset:0;
            background: radial-gradient(120px 60px at 80% 10%, rgba(255,255,255,0.08) 0%, transparent 70%);
            pointer-events:none;
        }
        .wx-pcard:hover {
            transform: translateY(-3px);
            border-color: rgba(186,230,253,0.45);
            box-shadow: 0 14px 28px rgba(8, 32, 52, 0.34), 0 0 0 1px rgba(186,230,253,0.18) inset;
        }
        /* UV card – green gradient */
        .wx-pcard.uv {
            background: linear-gradient(145deg, #4caf50 0%, #2e7d32 100%);
        }
        /* Cloud card – slate with clouds art */
        .wx-pcard.cloud-card {
            background: linear-gradient(145deg, #3a7ca5 0%, #1c5a80 100%);
        }

        .wx-pcard-label {
            font-size: 0.64rem;
            text-transform: uppercase;
            letter-spacing: 0.9px;
            color: rgba(180,220,255,0.85);
            font-weight: 700;
            margin-bottom: 5px;
        }
        .wx-pcard-value {
            font-size: 1.65rem;
            font-weight: 900;
            color: #fff;
            line-height: 1;
        }
        .wx-pcard-value-sm { font-size: 1rem; font-weight: 700; color: rgba(255,255,255,0.75); }
        .wx-pcard-sub {
            font-size: 0.68rem;
            color: rgba(180,220,255,0.80);
            margin-top: 5px;
            line-height: 1.4;
        }

        /* ── COMPASS widget ── */
        .wx-compass-wrap {
            display: flex; align-items: center; gap: 12px; height: 100%;
        }
        .wx-compass-svg { flex-shrink: 0; }
        .wx-compass-svg svg { width: 84px; height: 84px; }
        .wx-compass-info {}
        .wx-compass-deg { font-size: 1.6rem; font-weight: 900; color:#fff; line-height:1; }
        .wx-compass-dir { font-size: 1.0rem; font-weight: 700; color:rgba(180,220,255,0.9); }
        .wx-compass-sub { font-size: 0.68rem; color:rgba(180,220,255,0.7); margin-top:3px; }

        /* ── WIND SPEED (turbine icon) ── */
        .wx-wind-wrap { display:flex; align-items:center; gap:12px; }
        .wx-wind-icon { flex-shrink:0; }
        .wx-wind-icon svg { width: 72px; height: 88px; }
        .wx-turbine-svg { overflow: visible; }
        .wx-turbine-rotor {
            transform-origin: 35px 48px;
            transform-box: view-box;
            animation: wx-turbine-spin var(--wx-spin, 2.4s) linear infinite;
        }
        .wx-wind-icon:hover .wx-turbine-rotor {
            animation-duration: calc(var(--wx-spin, 2.4s) * 0.68);
        }
        @keyframes wx-turbine-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        /* Cloud-cover banner animation (horizontal flow across full card) */
        .wx-cloud-banner {
            height: 78px;
            margin: -6px -2px 8px;
            border-radius: 12px;
            overflow: hidden;
            background: linear-gradient(180deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.02) 100%);
            border: 1px solid rgba(255,255,255,0.10);
        }
        .wx-cloud-cover-svg {
            width: 100%;
            height: 100%;
            display: block;
        }
        .wx-cloud-track {
            will-change: transform;
        }
        .wx-cloud-track-1 {
            animation: wx-cloud-horiz-1 12s linear infinite;
        }
        .wx-cloud-track-2 {
            animation: wx-cloud-horiz-2 16s linear infinite;
            opacity: 0.82;
        }
        .wx-cloud-track-3 {
            animation: wx-cloud-horiz-3 20s linear infinite;
            opacity: 0.70;
        }

        /* Rain icon animation */
        .wx-rain-svg { overflow: visible; }
        .wx-rain-sun {
            animation: wx-sun-pulse 2.8s ease-in-out infinite;
            transform-origin: 46px 14px;
            transform-box: fill-box;
        }
        .wx-rain-cloud {
            animation: wx-cloud-float 2.2s ease-in-out infinite;
            transform-origin: center;
        }
        .wx-rain-drop {
            animation: wx-rain-fall 1.25s linear infinite;
        }
        .wx-rain-drop.d2 { animation-delay: 0.25s; }
        .wx-rain-drop.d3 { animation-delay: 0.5s; }

        /* UV marker subtle pulse */
        .wx-uv-thumb {
            animation: wx-uv-pulse 2.2s ease-in-out infinite;
        }

        @keyframes wx-cloud-horiz-1 {
            0%   { transform: translateX(-170px); }
            100% { transform: translateX(170px); }
        }
        @keyframes wx-cloud-horiz-2 {
            0%   { transform: translateX(120px); }
            100% { transform: translateX(-210px); }
        }
        @keyframes wx-cloud-horiz-3 {
            0%   { transform: translateX(-260px); }
            100% { transform: translateX(120px); }
        }
        @keyframes wx-cloud-float {
            0%   { transform: translateY(1px) translateX(0px); }
            50%  { transform: translateY(-4px) translateX(1.5px); }
            100% { transform: translateY(1px) translateX(0px); }
        }
        @keyframes wx-rain-fall {
            0%   { transform: translateY(-1px); opacity: 0.2; }
            45%  { opacity: 0.95; }
            100% { transform: translateY(7px); opacity: 0.12; }
        }
        @keyframes wx-sun-pulse {
            0%   { transform: scale(1); opacity: 0.86; }
            50%  { transform: scale(1.08); opacity: 1; }
            100% { transform: scale(1); opacity: 0.86; }
        }
        @keyframes wx-uv-pulse {
            0%   { box-shadow: 0 1px 4px rgba(0,0,0,0.25); }
            50%  { box-shadow: 0 0 0 6px rgba(255,255,255,0.22), 0 2px 8px rgba(0,0,0,0.32); }
            100% { box-shadow: 0 1px 4px rgba(0,0,0,0.25); }
        }

        @media (prefers-reduced-motion: reduce) {
            .wx-turbine-rotor,
            .wx-cloud-track,
            .wx-rain-sun,
            .wx-rain-cloud,
            .wx-rain-drop,
            .wx-uv-thumb {
                animation: none !important;
            }
        }

        /* ── CLOUD / VISIBILITY card ── */
        .wx-cloud-metrics {
            display:flex;
            align-items:stretch;
            gap: 10px;
            margin-top: 2px;
            padding-top: 7px;
            border-top: 1px solid rgba(255,255,255,0.12);
        }
        .wx-cloud-metric { flex: 1; }
        .wx-cloud-metric.right { text-align: right; }
        .wx-cloud-divider { width:1px; background:rgba(255,255,255,0.15); align-self:stretch; margin:0 2px; }

        /* ── RAIN card ── */
        .wx-rain-wrap { display:flex; align-items:center; gap:10px; }
        .wx-rain-wrap svg { width: 72px; height: 72px; }

        /* ── PRESSURE gauge ── */
        .wx-gauge-wrap { display:flex; align-items:center; gap:10px; }
        .wx-gauge-svg  { flex-shrink:0; }
        .wx-gauge-info {}

        /* Pressure bar (bottom of card) */
        .wx-pressure-track {
            margin-top: 8px; height: 6px; border-radius: 99px;
            background: linear-gradient(90deg, #22c55e 0%, #facc15 40%, #f97316 65%, #ef4444 100%);
            position: relative;
        }
        .wx-pressure-thumb {
            position: absolute; top: -5px;
            width: 16px; height: 16px; border-radius: 50%;
            background: #fff; border: 2.5px solid #ef4444;
            transform: translateX(-50%);
            box-shadow: 0 1px 5px rgba(0,0,0,0.3);
        }

        /* ── UV bar ── */
        .wx-uv-bar-wrap { margin-top: 10px; }
        .wx-uv-track {
            height: 8px; border-radius: 99px;
            background: linear-gradient(90deg,
                #43a047 0%, #c0ca33 22%, #fdd835 38%,
                #fb8c00 55%, #e53935 72%, #8e24aa 100%);
            position: relative;
        }
        .wx-uv-thumb {
            position: absolute; top: -4px;
            width: 16px; height: 16px; border-radius: 50%;
            background: #fff; border: 2.5px solid #fff;
            transform: translateX(-50%);
            box-shadow: 0 2px 6px rgba(0,0,0,0.35);
        }
        .wx-uv-labels {
            display:flex; justify-content:space-between;
            font-size:0.55rem; color:rgba(255,255,255,0.65);
            margin-top:3px; font-weight:600;
        }

        /* ── 10-DAY FORECAST ── */
        .wx-forecast-card {
            background: #fff;
            border: 1px solid #e2eaf3;
            border-radius: 18px;
            padding: 16px;
            margin-bottom: 14px;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
        }
        .wx-fc-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .wx-fc-title { font-size: 1.05rem; font-weight: 800; color: #0f172a; }
        .wx-fc-link  { font-size: 0.74rem; color: #3b82f6; font-weight: 600; text-decoration: none; }
        .wx-fc-note {
            margin-top: 10px;
            font-size: 0.72rem;
            color: #64748b;
        }

        /* Shared dark tone (same direction as monthly calendar section) */
        .wx-month-tone {
            background: linear-gradient(155deg, #10243c 0%, #1a3553 60%, #1f3f61 100%) !important;
            border: 1px solid rgba(148, 163, 184, 0.24) !important;
            box-shadow: 0 8px 26px rgba(15, 23, 42, 0.22);
            color: #e2e8f0 !important;
        }
        .wx-month-tone .wx-fc-title,
        .wx-month-tone .wx-switch-pane-title,
        .wx-month-tone .wx-block-title,
        .wx-month-tone .wx-kpi-v {
            color: #f8fafc !important;
        }
        .wx-month-tone .wx-fc-link,
        .wx-month-tone .wx-block-sub,
        .wx-month-tone .wx-kpi-k {
            color: #cbd5e1 !important;
        }
        .wx-month-tone .wx-block-head {
            border-left-color: #60a5fa;
        }

        /* Horizontal scroll strip */
        .wx-fc-strip {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding-bottom: 4px;
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
        }
        .wx-fc-strip::-webkit-scrollbar { height: 4px; }
        .wx-fc-strip::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 2px; }

        .wx-day-link {
            text-decoration: none;
            color: inherit;
            display: block;
            flex: 0 0 auto;
        }
        .wx-day-link:hover { text-decoration: none; }

        .wx-day-chip {
            flex: 0 0 auto;
            min-width: 86px;
            border-radius: 14px;
            border: 1.5px solid #e2eaf3;
            background: #f8faff;
            padding: 12px 10px;
            text-align: center;
            transition: all 0.18s;
        }
        .wx-day-chip:hover { border-color: #93c5fd; background: #eff6ff; }
        .wx-day-chip.today {
            background: linear-gradient(150deg, #1976D2, #42A5F5);
            border-color: #1976D2;
            box-shadow: 0 4px 14px rgba(25, 118, 210, 0.30);
        }
        .wx-day-label {
            font-size: 0.70rem;
            font-weight: 700;
            color: #64748b;
            margin-bottom: 8px;
        }
        .wx-day-chip.today .wx-day-label { color: rgba(255,255,255,0.80); }
        .wx-day-icon { margin: 0 auto 6px; display: flex; justify-content: center; }
        .wx-day-temps {
            font-size: 0.82rem;
            font-weight: 800;
            color: #0f172a;
        }
        .wx-day-chip.today .wx-day-temps { color: #fff; }
        .wx-day-humi {
            font-size: 0.62rem;
            color: #94a3b8;
            margin-top: 3px;
        }
        .wx-day-chip.today .wx-day-humi { color: rgba(255,255,255,0.70); }

        /* ── HOURLY DETAIL TABLE ── */
        .wx-hourly-card {
            background: #fff;
            border: 1px solid #e2eaf3;
            border-radius: 18px;
            padding: 16px;
            margin-bottom: 14px;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
            overflow-x: auto;
        }
        .wx-hourly-card.wx-month-tone {
            background: linear-gradient(155deg, #10243c 0%, #1a3553 60%, #1f3f61 100%) !important;
            border: 1px solid rgba(148, 163, 184, 0.24) !important;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03);
        }
        .wx-htable {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
        }
        .wx-htable thead th {
            font-size: 0.64rem;
            text-transform: uppercase;
            letter-spacing: 0.7px;
            color: #94a3b8;
            font-weight: 700;
            padding: 8px 10px;
            border-bottom: 1px solid #f1f5f9;
            text-align: left;
            white-space: nowrap;
        }
        .wx-htable tbody tr { border-bottom: 1px solid #f8fafc; }
        .wx-htable tbody tr:hover { background: #f8faff; }
        .wx-htable tbody td {
            padding: 9px 10px;
            color: #0f172a;
            font-weight: 500;
            white-space: nowrap;
        }
        .wx-hourly-card.wx-month-tone .wx-htable thead th {
            color: #cbd5e1;
            border-bottom: 1px solid rgba(148, 163, 184, 0.35);
        }
        .wx-hourly-card.wx-month-tone .wx-htable tbody td {
            color: #e2e8f0;
        }
        .wx-hourly-card.wx-month-tone .wx-htable tbody tr {
            border-bottom: 1px solid rgba(148, 163, 184, 0.18);
        }
        .wx-hourly-card.wx-month-tone .wx-htable tbody tr:hover {
            background: rgba(148, 163, 184, 0.12);
        }
        .wx-htable-cond { display: flex; align-items: center; gap: 5px; }
        .wx-temp-pill,
        .wx-rain-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 64px;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.2px;
        }
        .wx-temp-pill.na,
        .wx-rain-pill.na {
            background: #e2e8f0;
            color: #475569;
        }
        .wx-aqi-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 44px;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.2px;
        }

        /* ── MONTHLY CALENDAR PANEL ── */
        .wx-month-shell {
            display: grid;
            grid-template-columns: 2.3fr 1fr;
            gap: 14px;
            margin-bottom: 14px;
        }
        .wx-month-left,
        .wx-month-right {
            background: linear-gradient(155deg, #10243c 0%, #1a3553 60%, #1f3f61 100%);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 18px;
            box-shadow: 0 8px 26px rgba(15, 23, 42, 0.22);
            color: #e2e8f0;
        }
        .wx-month-left {
            padding: 14px;
        }
        .wx-month-weekdays {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
            margin-bottom: 8px;
        }
        .wx-month-weekdays div {
            font-size: 0.78rem;
            color: #cbd5e1;
            text-align: left;
            font-weight: 700;
            padding-left: 2px;
        }
        .wx-month-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
        }
        .wx-cal-cell {
            min-height: 104px;
            border: 1px solid rgba(148, 163, 184, 0.15);
            border-radius: 12px;
            padding: 8px 8px 6px;
            background: rgba(15, 35, 60, 0.52);
            position: relative;
        }
        .wx-cal-cell.empty {
            background: rgba(255, 255, 255, 0.02);
            border-color: rgba(148, 163, 184, 0.07);
        }
        .wx-cal-cell.active {
            background: linear-gradient(150deg, rgba(59,130,246,0.52), rgba(37,99,235,0.44));
            border-color: rgba(147, 197, 253, 0.68);
            box-shadow: inset 0 0 0 1px rgba(191, 219, 254, 0.35);
        }
        .wx-cal-badge {
            position: absolute;
            top: 6px;
            right: 7px;
            font-size: 0.60rem;
            font-weight: 800;
            color: #f8fafc;
            background: rgba(59, 130, 246, 0.85);
            border-radius: 999px;
            padding: 1px 7px;
        }
        .wx-cal-day {
            font-size: 0.88rem;
            color: #cbd5e1;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .wx-cal-icon {
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 4px;
        }
        .wx-cal-temp {
            font-size: 1.24rem;
            line-height: 1;
            font-weight: 800;
            color: #f8fafc;
            text-align: center;
        }
        .wx-cal-temp-min {
            font-size: 0.86rem;
            color: #bfdbfe;
            text-align: center;
            margin-top: 2px;
            font-weight: 700;
        }
        .wx-cal-no-data {
            font-size: 0.74rem;
            color: #64748b;
            margin-top: 18px;
            text-align: center;
            font-weight: 700;
        }

        .wx-month-right {
            padding: 16px;
            display: flex;
            flex-direction: column;
        }
        .wx-month-title {
            font-size: 1.07rem;
            line-height: 1.35;
            font-weight: 800;
            color: #f8fafc;
            text-align: center;
            margin-bottom: 10px;
        }
        .wx-month-pie {
            width: 152px;
            height: 152px;
            margin: 0 auto 14px;
            border-radius: 50%;
            overflow: visible;
        }
        .wx-month-pie-svg {
            width: 100%;
            height: 100%;
            display: block;
            overflow: visible;
        }
        .wx-month-pie-slice {
            stroke: rgba(226, 232, 240, 0.78);
            stroke-width: 1.1;
            cursor: pointer;
            transition: transform 0.16s ease, filter 0.16s ease, opacity 0.16s ease;
            transform-origin: 80px 80px;
        }
        .wx-month-pie-slice:hover {
            transform: scale(1.045);
            opacity: 0.95;
            filter: drop-shadow(0 0 6px rgba(15, 23, 42, 0.50));
        }
        .wx-month-legend-title {
            font-size: 0.93rem;
            font-weight: 800;
            color: #e2e8f0;
            margin-bottom: 8px;
        }
        .wx-month-legend-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.86rem;
            color: #e2e8f0;
            padding: 6px 0;
            border-bottom: 1px dashed rgba(148, 163, 184, 0.25);
            font-weight: 700;
        }
        .wx-month-legend-item b {
            min-width: 34px;
            text-align: center;
            border-radius: 8px;
            padding: 2px 6px;
            color: #f8fafc;
            background: rgba(71, 85, 105, 0.80);
        }
        .wx-month-note {
            margin-top: 10px;
            font-size: 0.78rem;
            line-height: 1.5;
            color: #cbd5e1;
        }

        .wx-kpi-strip {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 12px;
        }
        .wx-kpi-card {
            background: linear-gradient(160deg, #ffffff 0%, #f8fbff 100%);
            border: 1px solid #dbe7f2;
            border-radius: 12px;
            padding: 10px 12px;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
        }
        .wx-kpi-k {
            font-size: 0.64rem;
            text-transform: uppercase;
            letter-spacing: 0.7px;
            color: #64748b;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .wx-kpi-v {
            font-size: 1.08rem;
            color: #0f172a;
            font-weight: 800;
        }
        .wx-kpi-strip-month .wx-kpi-card {
            background: linear-gradient(155deg, rgba(16, 36, 60, 0.92) 0%, rgba(26, 53, 83, 0.92) 60%, rgba(31, 63, 97, 0.92) 100%);
            border: 1px solid rgba(148, 163, 184, 0.20);
            box-shadow: none;
        }
        .wx-kpi-strip-month .wx-kpi-k {
            color: #cbd5e1;
        }
        .wx-kpi-strip-month .wx-kpi-v {
            color: #f8fafc;
        }

        /* ── DARK CHART CARD ── */
        .wx-dark-card {
            background: #0f172a;
            border-radius: 18px;
            padding: 14px;
            margin-bottom: 14px;
            box-shadow: 0 4px 20px rgba(15, 23, 42, 0.20);
        }
        .wx-dark-card-title {
            font-size: 0.88rem;
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 10px;
        }

        /* ── ADVANCED ANALYSIS CARD ── */
        .wx-analysis-card {
            background: #fff;
            border: 1px solid #e2eaf3;
            border-radius: 18px;
            padding: 16px;
            margin-bottom: 14px;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
        }
        .wx-analysis-title { font-size: 1.05rem; font-weight: 800; color: #0f172a; margin-bottom: 3px; }
        .wx-analysis-sub   { font-size: 0.72rem; color: #64748b; margin-bottom: 10px; }

        /* ── RESPONSIVE ── */
        @media (max-width: 1100px) {
            .wx-hero-grid { grid-template-columns: 1fr; }
            .wx-params-grid { grid-template-columns: repeat(2, 1fr); }
            .wx-month-shell { grid-template-columns: 1fr; }
            .wx-kpi-strip { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 680px) {
            .wx-params-grid { grid-template-columns: 1fr; }
            .wx-hour-strip { grid-template-columns: repeat(3, 1fr); }
            .wx-temp-big { font-size: 3rem; }
            .wx-cal-cell { min-height: 86px; padding: 6px 6px 5px; }
            .wx-cal-temp { font-size: 1rem; }
            .wx-cal-temp-min { font-size: 0.74rem; }
            .wx-kpi-strip { grid-template-columns: 1fr; }
        }
        </style>
        """),
        unsafe_allow_html=True,
    )


# ─── Data helpers ─────────────────────────────────────────────────────────────

def _build_hourly_frame(city_df):
    numeric_cols = [c for c in WEATHER_FEATURES if c in city_df.columns]
    if not numeric_cols:
        return pd.DataFrame()
    hourly = (
        city_df.set_index("timestamp")[numeric_cols]
        .resample("1h")
        .mean(numeric_only=True)
        .reset_index()
    )
    return hourly.dropna(how="all", subset=numeric_cols)


def _build_daily_frame(city_df):
    agg_spec = {
        "temp_max": ("temp", "max"),
        "temp_min": ("temp", "min"),
        "temp_avg": ("temp", "mean"),
        "humidity": ("humidity", "mean"),
        "rain": ("rain", "sum"),
        "wind_speed": ("wind_speed", "mean"),
        "wind_dir": ("wind_dir", "mean"),
        "pressure": ("pressure", "mean"),
        "cloud": ("cloud", "mean"),
    }

    available_agg = {
        out_col: (src_col, agg_fn)
        for out_col, (src_col, agg_fn) in agg_spec.items()
        if src_col in city_df.columns
    }
    if not available_agg:
        return pd.DataFrame()

    daily = (
        city_df.set_index("timestamp")
        .resample("1D")
        .agg(**available_agg)
        .dropna(how="all")
        .reset_index()
    )

    # Ensure downstream render logic can rely on these columns existing.
    for out_col in agg_spec:
        if out_col not in daily.columns:
            daily[out_col] = np.nan

    if daily.empty:
        return daily
    daily["condition"] = daily.apply(
        lambda r: _condition_from_weather(r.get("rain", np.nan), r.get("cloud", np.nan)),
        axis=1,
    )
    return daily


# ─── HTML Builders ────────────────────────────────────────────────────────────

def _hourly_strip_html(hourly_df, count=6):
    if hourly_df.empty:
        return ""
    rows = list(hourly_df.tail(count).itertuples(index=False))
    parts = []
    for i, row in enumerate(rows):
        cls = "wx-hour-item now" if i == len(rows) - 1 else "wx-hour-item"
        temp = _fmt_num(getattr(row, "temp", np.nan), 0)
        rain = getattr(row, "rain", np.nan)
        rain_txt = f"{_fmt_num(rain, 1)} mm" if not pd.isna(rain) and float(rain) > 0 else "0%"
        time_str = row.timestamp.strftime("%H:%M") if hasattr(row.timestamp, "strftime") else str(row.timestamp)[:5]
        parts.append(
            f"<div class='{cls}'>"
            f"<div class='wx-hour-time'>{time_str}</div>"
            f"<div class='wx-hour-temp'>{temp}°</div>"
            f"<div class='wx-hour-rain'>{rain_txt}</div>"
            "</div>"
        )
    return "".join(parts)


def _ten_day_chips_html(daily_df, selected_day=None, anchor_day=None):
    if daily_df.empty:
        return ""
    selected_norm = pd.to_datetime(selected_day).normalize() if selected_day is not None else None
    anchor_norm = pd.to_datetime(anchor_day).normalize() if anchor_day is not None else None
    cards = []
    for row in daily_df.itertuples(index=False):
        cond = getattr(row, "condition", "Trời quang")
        icon = _condition_img(cond, size=28)
        row_day = pd.to_datetime(row.timestamp).normalize()
        is_selected = selected_norm is not None and row_day == selected_norm
        cls = "wx-day-chip today" if is_selected else "wx-day-chip"
        if anchor_norm is not None and row_day == anchor_norm:
            label = "Hôm nay"
        else:
            label = _weekday_vi(row.timestamp)
        t_max = _fmt_num(getattr(row, "temp_max", np.nan), 0)
        t_min = _fmt_num(getattr(row, "temp_min", np.nan), 0)
        humi = _fmt_num(getattr(row, "humidity", np.nan), 0)
        cards.append(
            f"<div class='{cls}'>"
            f"<div class='wx-day-label'>{label}</div>"
            f"<div class='wx-day-icon'>{icon}</div>"
            f"<div class='wx-day-temps'>{t_max}° / {t_min}°</div>"
            f"<div class='wx-day-humi'>💧{humi}%</div>"
            "</div>"
        )
    return "".join(cards)


def _condition_emoji(condition: str) -> str:
    token = _condition_token(condition)
    if token == "RAIN":
        return "🌧️"
    if token == "CLOUD":
        return "☁️"
    return "☀️"


def _forecast_hourly_switch_html(forecast_df, day_groups, anchor_day=None, switch_key=None):
    """Build client-side interactive forecast cards + hourly detail panes (no rerun, no scroll jump)."""
    if forecast_df.empty:
        return ""

    anchor_norm = pd.to_datetime(anchor_day).normalize() if anchor_day is not None else None
    key_seed = switch_key or f"{pd.to_datetime(forecast_df.iloc[0]['timestamp']):%Y%m%d}-{len(forecast_df)}"
    prefix = f"wxswitch-{abs(hash(key_seed)) % 100000000}-{uuid.uuid4().hex[:6]}"

    radios = []
    cards = []
    panes = []
    rules = []

    for idx, row in enumerate(forecast_df.itertuples(index=False)):
        row_ts = pd.to_datetime(row.timestamp)
        row_day = row_ts.normalize()
        day_key = row_day.strftime("%Y-%m-%d")
        input_id = f"{prefix}-{idx}"

        label_day = "Hôm nay" if (anchor_norm is not None and row_day == anchor_norm) else _weekday_vi(row_ts)
        cond = getattr(row, "condition", "Trời quang")
        icon = _condition_img(cond, size=24)
        t_max = _fmt_num(getattr(row, "temp_max", np.nan), 0)
        t_min = _fmt_num(getattr(row, "temp_min", np.nan), 0)
        humi = _fmt_num(getattr(row, "humidity", np.nan), 0)

        pane_df = day_groups.get(day_key, pd.DataFrame()) if isinstance(day_groups, dict) else pd.DataFrame()
        table_markup = _hourly_table_html(pane_df, 24) if not pane_df.empty else "<div class='wx-pcard-sub'>Không có dữ liệu theo giờ cho ngày này.</div>"

        checked = " checked" if idx == 0 else ""
        radios.append(f"<input class='wx-switch-radio' type='radio' name='{prefix}' id='{input_id}'{checked}>")

        cards.append(
            f"<label class='wx-switch-card' for='{input_id}'>"
            f"<div class='wx-day-chip'>"
            f"<div class='wx-day-label'>{label_day}</div>"
            f"<div class='wx-day-icon'>{icon}</div>"
            f"<div class='wx-day-temps'>{t_max}° / {t_min}°</div>"
            f"<div class='wx-day-humi'>💧{humi}%</div>"
            "</div>"
            "</label>"
        )

        panes.append(
            f"<div class='wx-switch-pane wx-pane-{idx}'>"
            f"<div class='wx-switch-pane-title'>Chi tiết theo giờ ({row_ts:%d/%m/%Y})</div>"
            f"<div class='wx-hourly-card wx-hourly-card-inline wx-month-tone'>{table_markup}</div>"
            "</div>"
        )

        rules.append(
            f"#{input_id}:checked ~ .wx-switch-strip label[for='{input_id}'] .wx-day-chip"
            "{background:linear-gradient(150deg,#1976D2,#42A5F5);border-color:#1976D2;box-shadow:0 4px 14px rgba(25,118,210,.30);}"
        )
        rules.append(
            f"#{input_id}:checked ~ .wx-switch-strip label[for='{input_id}'] .wx-day-label"
            "{color:rgba(255,255,255,.82);}"
        )
        rules.append(
            f"#{input_id}:checked ~ .wx-switch-strip label[for='{input_id}'] .wx-day-temps"
            "{color:#fff;}"
        )
        rules.append(
            f"#{input_id}:checked ~ .wx-switch-strip label[for='{input_id}'] .wx-day-humi"
            "{color:rgba(255,255,255,.72);}"
        )
        rules.append(f"#{input_id}:checked ~ .wx-switch-details .wx-pane-{idx}" + "{display:block;}")

    return (
        "<style>"
        ".wx-switch-radio{position:absolute;left:-9999px;width:1px;height:1px;opacity:0;}"
        ".wx-switch-strip{display:flex;gap:8px;overflow-x:auto;padding:0 2px 4px;}"
        ".wx-switch-card{display:block;flex:0 0 auto;text-decoration:none;color:inherit;cursor:pointer;}"
        ".wx-switch-card:hover{text-decoration:none;}"
        ".wx-switch-details{margin-top:8px;}"
        ".wx-switch-details .wx-switch-pane{display:none;}"
        ".wx-switch-pane-title{font-size:.76rem;font-weight:700;color:#334155;margin:4px 0 8px;}"
        ".wx-hourly-card-inline{margin:0;padding:10px 12px;border-radius:14px;}"
        + "".join(rules)
        + "</style>"
        + "<div class='wx-forecast-card wx-forecast-shell wx-month-tone'>"
        + "<div class='wx-fc-header'>"
        + "<div class='wx-fc-title'>Dự báo 10 ngày</div>"
        + "<span class='wx-fc-link'>Chọn một ngày để xem chi tiết theo giờ</span>"
        + "</div>"
        + "<div class='wx-switch-wrap'>"
        + "".join(radios)
        + "<div class='wx-fc-strip wx-switch-strip'>"
        + "".join(cards)
        + "</div>"
        + "<div class='wx-switch-details'>"
        + "".join(panes)
        + "</div>"
        + "</div>"
        + "</div>"
    )


def _hourly_table_html(hourly_df, rows=24):
    if hourly_df.empty:
        return ""
    sub = hourly_df.tail(rows)
    header = (
        "<table class='wx-htable'><thead><tr>"
        "<th>Giờ</th><th>Tình trạng</th><th>🌡 Nhiệt độ</th>"
        "<th>💧 Độ ẩm</th><th>🌬 Gió (km/h)</th><th>☁ Mây</th><th>🌧 Mưa</th>"
        "</tr></thead><tbody>"
    )
    rows_html = []
    for row in sub.itertuples(index=False):
        ts = row.timestamp
        time_str = ts.strftime("%H:%M") if hasattr(ts, "strftime") else str(ts)[:5]
        rain = getattr(row, "rain", np.nan)
        cloud = getattr(row, "cloud", np.nan)
        cond = _condition_from_weather(rain, cloud)
        icon = _condition_svg_inline(cond, 14)
        temp_pill = _temp_pill_html(getattr(row, "temp", np.nan))
        rain_pill = _rain_pill_html(rain)
        rows_html.append(
            f"<tr>"
            f"<td>{time_str}</td>"
            f"<td><div class='wx-htable-cond'>{icon}{cond}</div></td>"
            f"<td>{temp_pill}</td>"
            f"<td>{_fmt_num(getattr(row,'humidity',np.nan),0)}%</td>"
            f"<td>{_fmt_num(getattr(row,'wind_speed',np.nan),1)}</td>"
            f"<td>{_fmt_num(cloud,0)}%</td>"
            f"<td>{rain_pill}</td>"
            "</tr>"
        )
    return header + "".join(rows_html) + "</tbody></table>"


def _temp_pill_html(temp) -> str:
    if temp is None or pd.isna(temp):
        return "<span class='wx-temp-pill na'>N/A</span>"

    value = float(temp)
    if value >= 35:
        bg, fg = "#ef4444", "#fff1f2"
    elif value >= 30:
        bg, fg = "#fb923c", "#fff7ed"
    elif value >= 25:
        bg, fg = "#facc15", "#422006"
    elif value >= 20:
        bg, fg = "#38bdf8", "#082f49"
    else:
        bg, fg = "#60a5fa", "#eff6ff"
    return f"<span class='wx-temp-pill' style='background:{bg};color:{fg};'>{value:.1f}°C</span>"


def _rain_pill_html(rain) -> str:
    if rain is None or pd.isna(rain):
        return "<span class='wx-rain-pill na'>N/A</span>"

    value = float(rain)
    if value >= 10:
        bg, fg = "#0369a1", "#e0f2fe"
    elif value >= 3:
        bg, fg = "#0ea5e9", "#eff6ff"
    elif value > 0:
        bg, fg = "#7dd3fc", "#0c4a6e"
    else:
        bg, fg = "#e2e8f0", "#334155"
    return f"<span class='wx-rain-pill' style='background:{bg};color:{fg};'>{value:.1f} mm</span>"


def _normalize_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _resolve_detail_province_name(city_name: str) -> str | None:
    if not city_name:
        return None
    provinces = list_detail_provinces()
    if not provinces:
        return None
    if city_name in provinces:
        return city_name

    target_norm = _normalize_name(city_name)
    for province in provinces:
        if _normalize_name(province) == target_norm:
            return province
    return None


def _load_anchor_location_rows(city_name: str, anchor_day: pd.Timestamp) -> pd.DataFrame:
    resolved_name = _resolve_detail_province_name(city_name)
    if resolved_name is None:
        return pd.DataFrame()

    anchor_day = pd.to_datetime(anchor_day).normalize()
    day_iso = anchor_day.strftime("%Y-%m-%d")
    try:
        detail_df = load_province_detail(resolved_name, start_date=day_iso, end_date=day_iso)
    except Exception:
        return pd.DataFrame()
    except BaseException as exc:
        # Optional detail data must not stop the whole weather tab render.
        if exc.__class__.__name__ == "StopException":
            return pd.DataFrame()
        raise

    if detail_df.empty or "timestamp" not in detail_df.columns or "location" not in detail_df.columns:
        return pd.DataFrame()

    frame = detail_df.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "location"])
    frame = frame[frame["timestamp"].dt.normalize() == anchor_day]
    if frame.empty:
        return frame

    frame["location"] = frame["location"].astype(str).str.strip()
    frame = frame[(frame["location"] != "") & (frame["location"].str.lower() != "nan")]
    return frame


def _circular_mean_deg(values: pd.Series) -> float:
    valid = pd.to_numeric(values, errors="coerce").dropna()
    if valid.empty:
        return np.nan
    radians = np.deg2rad(valid.to_numpy(dtype=float) % 360)
    sin_avg = np.sin(radians).mean()
    cos_avg = np.cos(radians).mean()
    if np.isclose(sin_avg, 0.0) and np.isclose(cos_avg, 0.0):
        return np.nan
    return float((np.rad2deg(np.arctan2(sin_avg, cos_avg)) + 360.0) % 360.0)


def _build_location_day_summary(detail_rows: pd.DataFrame) -> pd.DataFrame:
    if detail_rows.empty or "location" not in detail_rows.columns:
        return pd.DataFrame()

    frame = detail_rows.copy()
    required_numeric_cols = [
        "temp",
        "humidity",
        "rain",
        "wind_speed",
        "pressure",
        "cloud",
        "aqi",
        "wind_dir",
    ]
    for col in required_numeric_cols:
        if col not in frame.columns:
            frame[col] = np.nan

    grouped = frame.groupby("location", dropna=True, observed=False)
    summary = grouped.agg(
        temp_avg=("temp", "mean"),
        temp_max=("temp", "max"),
        temp_min=("temp", "min"),
        humidity=("humidity", "mean"),
        rain=("rain", "sum"),
        wind_speed=("wind_speed", "mean"),
        pressure=("pressure", "mean"),
        cloud=("cloud", "mean"),
        aqi=("aqi", "mean"),
    )
    summary["sample_count"] = grouped.size()
    summary["wind_dir"] = grouped["wind_dir"].apply(_circular_mean_deg)
    summary = summary.reset_index()
    summary["condition"] = summary.apply(
        lambda row: _condition_from_weather(row.get("rain", np.nan), row.get("cloud", np.nan)),
        axis=1,
    )
    return summary


def _aqi_badge_html(aqi_value) -> str:
    if aqi_value is None or pd.isna(aqi_value):
        return "<span class='wx-aqi-badge' style='background:#cbd5e1;color:#334155;'>N/A</span>"

    aqi = float(aqi_value)
    if aqi <= 50:
        bg, fg = "#22c55e", "#f0fdf4"
    elif aqi <= 100:
        bg, fg = "#facc15", "#422006"
    elif aqi <= 150:
        bg, fg = "#fb923c", "#431407"
    elif aqi <= 200:
        bg, fg = "#ef4444", "#fff1f2"
    elif aqi <= 300:
        bg, fg = "#a855f7", "#faf5ff"
    else:
        bg, fg = "#7f1d1d", "#fee2e2"

    return f"<span class='wx-aqi-badge' style='background:{bg};color:{fg};'>{int(round(aqi))}</span>"


def _aqi_level_meta(aqi_value: float) -> tuple[str, str, str, str]:
    if aqi_value <= 50:
        return (
            "Tốt",
            "#22c55e",
            "#f0fdf4",
            "Chất lượng không khí tốt, không ảnh hưởng tới sức khỏe.",
        )
    if aqi_value <= 100:
        return (
            "Vừa phải",
            "#facc15",
            "#422006",
            "Chất lượng không khí ở mức chấp nhận được, nhóm nhạy cảm cần theo dõi thêm.",
        )
    if aqi_value <= 150:
        return (
            "Không lành mạnh cho nhóm nhạy cảm",
            "#fb923c",
            "#431407",
            "Nhóm nhạy cảm có thể bị ảnh hưởng, nên hạn chế hoạt động ngoài trời kéo dài.",
        )
    if aqi_value <= 200:
        return (
            "Không khỏe mạnh",
            "#ef4444",
            "#fff1f2",
            "Mọi người bắt đầu chịu ảnh hưởng sức khỏe, nhóm nhạy cảm bị ảnh hưởng rõ hơn.",
        )
    if aqi_value <= 300:
        return (
            "Rất không tốt cho sức khỏe",
            "#a855f7",
            "#faf5ff",
            "Cảnh báo sức khỏe: giảm mạnh hoạt động ngoài trời và tăng biện pháp bảo hộ.",
        )
    return (
        "Nguy hiểm",
        "#7f1d1d",
        "#fee2e2",
        "Cảnh báo khẩn cấp: toàn bộ dân số có thể bị ảnh hưởng nghiêm trọng.",
    )


def _location_detail_table_html(location_df: pd.DataFrame, max_rows: int = 120) -> str:
    if location_df.empty:
        return ""

    sub = location_df.head(max_rows)
    header = (
        "<div class='wx-hourly-card wx-month-tone'>"
        "<table class='wx-htable'><thead><tr>"
        "<th>Địa điểm</th><th>Tình trạng</th><th>🌡 Nhiệt độ</th>"
        "<th>💧 Độ ẩm</th><th>🌬 Gió</th><th>☁ Mây</th><th>🌧 Mưa</th><th>AQI</th><th>Mẫu</th>"
        "</tr></thead><tbody>"
    )

    rows_html = []
    for row in sub.itertuples(index=False):
        location = escape(str(getattr(row, "location", "N/A")))
        condition = str(getattr(row, "condition", "Trời quang"))
        cond_icon = _condition_svg_inline(condition, 14)
        temp_avg = _fmt_num(getattr(row, "temp_avg", np.nan), 1)
        temp_max = _fmt_num(getattr(row, "temp_max", np.nan), 0)
        temp_min = _fmt_num(getattr(row, "temp_min", np.nan), 0)
        humidity = _fmt_num(getattr(row, "humidity", np.nan), 0)
        wind_speed = _fmt_num(getattr(row, "wind_speed", np.nan), 1)
        wind_dir = _wind_dir_label(getattr(row, "wind_dir", np.nan))
        cloud = _fmt_num(getattr(row, "cloud", np.nan), 0)
        rain = _fmt_num(getattr(row, "rain", np.nan), 1)
        sample_count = _fmt_num(getattr(row, "sample_count", np.nan), 0)
        aqi_badge = _aqi_badge_html(getattr(row, "aqi", np.nan))

        rows_html.append(
            "<tr>"
            f"<td><b>{location}</b></td>"
            f"<td><div class='wx-htable-cond'>{cond_icon}{condition}</div></td>"
            f"<td><b>{temp_avg}°C</b> <span style='color:#cbd5e1;font-size:0.68rem;'>({temp_max}° / {temp_min}°)</span></td>"
            f"<td>{humidity}%</td>"
            f"<td>{wind_speed} km/h · {wind_dir}</td>"
            f"<td>{cloud}%</td>"
            f"<td>{rain} mm</td>"
            f"<td>{aqi_badge}</td>"
            f"<td>{sample_count}</td>"
            "</tr>"
        )

    return header + "".join(rows_html) + "</tbody></table></div>"


def _detail_kpi_strip_html(total_locations: int, temp_avg_text: str, humidity_avg_text: str, rain_sum_text: str) -> str:
    return _html(
        f"""
        <div class='wx-kpi-strip wx-kpi-strip-month'>
            <div class='wx-kpi-card'>
                <div class='wx-kpi-k'>Số địa điểm</div>
                <div class='wx-kpi-v'>{total_locations:,}</div>
            </div>
            <div class='wx-kpi-card'>
                <div class='wx-kpi-k'>Nhiệt độ TB</div>
                <div class='wx-kpi-v'>{temp_avg_text}</div>
            </div>
            <div class='wx-kpi-card'>
                <div class='wx-kpi-k'>Độ ẩm TB</div>
                <div class='wx-kpi-v'>{humidity_avg_text}</div>
            </div>
            <div class='wx-kpi-card'>
                <div class='wx-kpi-k'>Mưa cộng dồn</div>
                <div class='wx-kpi-v'>{rain_sum_text}</div>
            </div>
        </div>
        """
    )


def _pie_point(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    rad = np.deg2rad(deg - 90)
    return (cx + r * np.cos(rad), cy + r * np.sin(rad))


def _pie_slice_path(cx: float, cy: float, r: float, start_deg: float, end_deg: float) -> str:
    x1, y1 = _pie_point(cx, cy, r, start_deg)
    x2, y2 = _pie_point(cx, cy, r, end_deg)
    large_arc = 1 if (end_deg - start_deg) > 180 else 0
    return (
        f"M {cx:.3f} {cy:.3f} "
        f"L {x1:.3f} {y1:.3f} "
        f"A {r:.3f} {r:.3f} 0 {large_arc} 1 {x2:.3f} {y2:.3f} Z"
    )


def _month_pie_svg_html(sunny_days: int, cloudy_days: int, rainy_days: int) -> str:
    segments = [
        ("Nắng", int(sunny_days), "#fb923c"),
        ("Có mây", int(cloudy_days), "#93c5fd"),
        ("Mưa", int(rainy_days), "#3b82f6"),
    ]
    total = sum(v for _, v, _ in segments)

    if total <= 0:
        return (
            "<svg class='wx-month-pie-svg' viewBox='0 0 160 160' role='img' aria-label='Chưa có dữ liệu'>"
            "<circle cx='80' cy='80' r='72' fill='rgba(71,85,105,0.60)' "
            "stroke='rgba(226,232,240,0.78)' stroke-width='1.1'>"
            "<title>Chưa có dữ liệu</title></circle></svg>"
        )

    start = 0.0
    paths = []
    for label, value, color in segments:
        if value <= 0:
            continue
        sweep = 360.0 * value / total
        end = start + sweep
        path_d = _pie_slice_path(80.0, 80.0, 72.0, start, end)
        pct = value / total * 100.0
        title = f"{label}: {value} ngày ({pct:.1f}%)"
        paths.append(
            f"<path class='wx-month-pie-slice' d='{path_d}' fill='{color}'>"
            f"<title>{escape(title)}</title>"
            "</path>"
        )
        start = end

    return (
        "<svg class='wx-month-pie-svg' viewBox='0 0 160 160' role='img' aria-label='Phân bố thời tiết theo tháng'>"
        + "".join(paths)
        + "<circle cx='80' cy='80' r='72' fill='none' stroke='rgba(226,232,240,0.78)' stroke-width='1.1'/>"
        + "</svg>"
    )


def _monthly_calendar_section_html(daily_df: pd.DataFrame, anchor_day: pd.Timestamp, city_name: str):
    if daily_df.empty or "timestamp" not in daily_df.columns:
        return ""

    month_anchor = pd.to_datetime(anchor_day).normalize()
    month_start = month_anchor.replace(day=1)
    month_end = (month_start + pd.offsets.MonthEnd(0)).normalize()
    days_in_month = int(month_end.day)

    month_df = daily_df.copy()
    month_df["timestamp"] = pd.to_datetime(month_df["timestamp"], errors="coerce")
    month_df = month_df.dropna(subset=["timestamp"])
    month_df = month_df[
        (month_df["timestamp"] >= month_start) & (month_df["timestamp"] <= month_end)
    ].sort_values("timestamp")

    if month_df.empty:
        return ""

    day_map: dict[int, object] = {}
    for row in month_df.itertuples(index=False):
        day_map[int(pd.to_datetime(row.timestamp).day)] = row

    weekday_labels = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"]
    start_blank = int((month_start.dayofweek + 1) % 7)
    cells: list[str] = []

    for _ in range(start_blank):
        cells.append("<div class='wx-cal-cell empty'></div>")

    for day in range(1, days_in_month + 1):
        row = day_map.get(day)
        is_anchor = (
            month_anchor.day == day
            and month_anchor.month == month_start.month
            and month_anchor.year == month_start.year
        )
        cls = "wx-cal-cell active" if is_anchor else "wx-cal-cell"

        if row is None:
            body = f"<div class='wx-cal-day'>{day}</div><div class='wx-cal-no-data'>--</div>"
        else:
            cond = str(getattr(row, "condition", "Trời quang"))
            icon = _condition_img(cond, size=26)
            t_max = _fmt_num(getattr(row, "temp_max", np.nan), 0)
            t_min = _fmt_num(getattr(row, "temp_min", np.nan), 0)
            body = (
                f"<div class='wx-cal-day'>{day}</div>"
                f"<div class='wx-cal-icon'>{icon}</div>"
                f"<div class='wx-cal-temp'>{t_max}°</div>"
                f"<div class='wx-cal-temp-min'>{t_min}°</div>"
            )

        badge = "<div class='wx-cal-badge'>Hôm nay</div>" if is_anchor else ""
        cells.append(f"<div class='{cls}'>{badge}{body}</div>")

    while len(cells) % 7 != 0:
        cells.append("<div class='wx-cal-cell empty'></div>")

    tokens = month_df["condition"].fillna("Trời quang").map(_condition_token)
    sunny_days = int((tokens == "SUN").sum())
    cloudy_days = int((tokens == "CLOUD").sum())
    rainy_days = int((tokens == "RAIN").sum())
    observed_days = int(month_df["timestamp"].dt.normalize().nunique())
    month_pie_svg = _month_pie_svg_html(sunny_days, cloudy_days, rainy_days)

    html = _html(f"""
    <div class='wx-month-shell'>
      <div class='wx-month-left'>
        <div class='wx-month-weekdays'>
          {''.join([f"<div>{label}</div>" for label in weekday_labels])}
        </div>
        <div class='wx-month-grid'>
          {''.join(cells)}
        </div>
      </div>

      <div class='wx-month-right'>
        <div class='wx-month-title'>Tháng {month_start.month}<br>Trung Bình Hàng Tháng</div>
        <div class='wx-month-pie'>{month_pie_svg}</div>
        <div class='wx-month-legend-title'>Số ngày</div>
        <div class='wx-month-legend-item'><span>🌤 Nắng</span><b>{sunny_days}</b></div>
        <div class='wx-month-legend-item'><span>☁ Có mây</span><b>{cloudy_days}</b></div>
        <div class='wx-month-legend-item'><span>🌧 Mưa</span><b>{rainy_days}</b></div>
        <div class='wx-month-note'>Trung bình thời tiết tháng {month_start.month} tại {escape(str(city_name))}: có dữ liệu {observed_days}/{days_in_month} ngày.</div>
      </div>
    </div>
    """)
    return html


def _compass_svg(deg_raw) -> str:
    """SVG compass rose with a rotating needle pointing to wind direction."""
    try:
        deg = float(deg_raw) % 360
    except (TypeError, ValueError):
        deg = 0.0

    # needle tip (from center outward)
    import math
    r = deg * math.pi / 180
    cx, cy = 44, 44
    nx = cx + 30 * math.sin(r)
    ny = cy - 30 * math.cos(r)
    # opposite tail
    tx = cx - 12 * math.sin(r)
    ty = cy + 12 * math.cos(r)

    ticks = "".join(
        f"<line x1='{44+38*math.sin(i*math.pi/8):.1f}' y1='{44-38*math.cos(i*math.pi/8):.1f}' "
        f"x2='{44+42*math.sin(i*math.pi/8):.1f}' y2='{44-42*math.cos(i*math.pi/8):.1f}' "
        f"stroke='rgba(150,200,230,0.4)' stroke-width='{'1.5' if i%4==0 else '0.8'}'/>"
        for i in range(16)
    )
    return (
        "<svg width='88' height='88' viewBox='0 0 88 88' xmlns='http://www.w3.org/2000/svg'>"
        "<circle cx='44' cy='44' r='42' fill='rgba(10,30,50,0.55)' stroke='rgba(100,160,200,0.35)' stroke-width='1.5'/>"
        + ticks +
        "<text x='44' y='11' text-anchor='middle' fill='#ef4444' font-size='9' font-weight='800' font-family='Inter'>N</text>"
        "<text x='44' y='82' text-anchor='middle' fill='rgba(180,220,255,0.8)' font-size='9' font-weight='700' font-family='Inter'>S</text>"
        "<text x='9' y='47' text-anchor='middle' fill='rgba(180,220,255,0.8)' font-size='9' font-weight='700' font-family='Inter'>W</text>"
        "<text x='79' y='47' text-anchor='middle' fill='rgba(180,220,255,0.8)' font-size='9' font-weight='700' font-family='Inter'>E</text>"
        "<circle cx='44' cy='44' r='28' fill='rgba(20,50,75,0.70)' stroke='rgba(100,160,200,0.20)' stroke-width='1'/>"
        f"<polygon points='{nx:.1f},{ny:.1f} {cx+5*math.sin(r+1.5):.1f},{cy-5*math.cos(r+1.5):.1f} "
        f"{tx:.1f},{ty:.1f} {cx+5*math.sin(r-1.5):.1f},{cy-5*math.cos(r-1.5):.1f}' fill='#ef4444'/>"
        f"<polygon points='{tx:.1f},{ty:.1f} {cx+4*math.sin(r+1.5):.1f},{cy-4*math.cos(r+1.5):.1f} "
        f"{cx:.1f},{cy:.1f} {cx+4*math.sin(r-1.5):.1f},{cy-4*math.cos(r-1.5):.1f}' fill='#60a5fa'/>"
        "<circle cx='44' cy='44' r='4' fill='#fff' stroke='#334155' stroke-width='1'/>"
        "</svg>"
    )


def _turbine_svg(wind_speed_kmh=np.nan) -> str:
    """Wind turbine SVG with animated rotor; stronger wind spins faster."""
    if wind_speed_kmh is None or pd.isna(wind_speed_kmh):
        spin_seconds = 2.6
    else:
        speed = float(np.clip(wind_speed_kmh, 0, 60))
        # Map 0–60 km/h to ~3.2s -> 1.2s per rotation.
        spin_seconds = 3.2 - (speed / 60.0) * 2.0

    return (
        f"<svg class='wx-turbine-svg' style='--wx-spin:{spin_seconds:.2f}s;' width='70' height='90' viewBox='0 0 70 90' xmlns='http://www.w3.org/2000/svg'>"
        # pole
        "<rect x='32' y='48' width='6' height='38' rx='3' fill='rgba(180,220,255,0.50)'/>"
        # rotor
        "<g class='wx-turbine-rotor'>"
        # blade 1 (top)
        "<ellipse cx='35' cy='26' rx='4' ry='20' fill='rgba(200,230,255,0.70)' transform='rotate(-15 35 48)'/>"
        # blade 2 (bottom-right)
        "<ellipse cx='35' cy='26' rx='4' ry='20' fill='rgba(200,230,255,0.70)' transform='rotate(105 35 48)'/>"
        # blade 3 (bottom-left)
        "<ellipse cx='35' cy='26' rx='4' ry='20' fill='rgba(200,230,255,0.70)' transform='rotate(225 35 48)'/>"
        "</g>"
        # hub
        "<circle cx='35' cy='48' r='5' fill='rgba(220,240,255,0.86)'/>"
        "</svg>"
    )


def _pressure_gauge_svg(pressure_val) -> str:
    """Arc gauge SVG mimicking AQI.in speedometer for pressure."""
    import math
    try:
        val = float(pressure_val)
    except (TypeError, ValueError):
        val = 1013.0
    # Map 970–1040 → -220° to 40° arc (260° sweep)
    pct = (val - 970) / 70
    pct = max(0.0, min(1.0, pct))
    # Arc: starts at 220° (bottom-left), sweeps 260° clockwise
    start_deg = 220
    sweep = 260
    needle_deg = start_deg + pct * sweep

    cx, cy, r = 50, 54, 40

    def arc_pt(deg, radius=r):
        rad = deg * math.pi / 180
        return cx + radius * math.cos(rad), cy + radius * math.sin(rad)

    # background arc (full 260°)
    def arc_path(cx, cy, r, start, end):
        s = start * math.pi / 180
        e = end * math.pi / 180
        x1, y1 = cx + r * math.cos(s), cy + r * math.sin(s)
        x2, y2 = cx + r * math.cos(e), cy + r * math.sin(e)
        large = 1 if (end - start) > 180 else 0
        return f"M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f}"

    bg_path = arc_path(cx, cy, r, start_deg, start_deg + sweep)
    # colored fill arc
    fill_end = start_deg + pct * sweep
    fill_path = arc_path(cx, cy, r, start_deg, fill_end) if pct > 0.01 else None

    # needle
    nr = needle_deg * math.pi / 180
    nx = cx + 32 * math.cos(nr)
    ny = cy + 32 * math.sin(nr)

    # tick labels (every ~65°)
    ticks = []
    for i, lbl in enumerate(["970", "983", "1000", "1020", "1040"]):
        td = (start_deg + i * 65) * math.pi / 180
        tx = cx + 50 * math.cos(td)
        ty = cy + 50 * math.sin(td)
        ticks.append(f"<text x='{tx:.0f}' y='{ty:.0f}' text-anchor='middle' "
                     f"fill='rgba(180,220,255,0.60)' font-size='6' font-family='Inter'>{lbl}</text>")

    svg = (
        f"<svg width='100' height='90' viewBox='0 0 100 90' xmlns='http://www.w3.org/2000/svg'>"
        f"<path d='{bg_path}' fill='none' stroke='rgba(100,150,200,0.25)' stroke-width='6' stroke-linecap='round'/>"
    )
    if fill_path:
        svg += f"<path d='{fill_path}' fill='none' stroke='#ef4444' stroke-width='6' stroke-linecap='round'/>"
    svg += "".join(ticks)
    svg += (
        f"<line x1='{cx}' y1='{cy}' x2='{nx:.1f}' y2='{ny:.1f}' "
        f"stroke='#ef4444' stroke-width='2.5' stroke-linecap='round'/>"
        f"<circle cx='{cx}' cy='{cy}' r='5' fill='#e2e8f0' stroke='#334155' stroke-width='1.2'/>"
        f"</svg>"
    )
    return svg


def _cloud_svg() -> str:
    """Cloud-cover banner with horizontally moving cloud bands."""
    return (
        "<div class='wx-cloud-banner'>"
        "<svg class='wx-cloud-cover-svg' viewBox='0 0 360 90' preserveAspectRatio='none' xmlns='http://www.w3.org/2000/svg'>"
        "<g class='wx-cloud-track wx-cloud-track-1' fill='rgba(240,248,255,0.88)'>"
        "<ellipse cx='24' cy='30' rx='20' ry='12'/>"
        "<ellipse cx='42' cy='24' rx='22' ry='14'/>"
        "<ellipse cx='62' cy='30' rx='20' ry='12'/>"
        "<ellipse cx='176' cy='34' rx='28' ry='16'/>"
        "<ellipse cx='202' cy='28' rx='30' ry='18'/>"
        "<ellipse cx='232' cy='34' rx='24' ry='15'/>"
        "<ellipse cx='316' cy='26' rx='20' ry='12'/>"
        "<ellipse cx='334' cy='21' rx='22' ry='14'/>"
        "<ellipse cx='352' cy='26' rx='18' ry='11'/>"
        "</g>"
        "<g class='wx-cloud-track wx-cloud-track-2' fill='rgba(214,230,247,0.82)'>"
        "<ellipse cx='88' cy='48' rx='24' ry='14'/>"
        "<ellipse cx='112' cy='42' rx='26' ry='16'/>"
        "<ellipse cx='140' cy='48' rx='22' ry='13'/>"
        "<ellipse cx='254' cy='52' rx='20' ry='12'/>"
        "<ellipse cx='272' cy='46' rx='22' ry='13'/>"
        "<ellipse cx='294' cy='52' rx='18' ry='11'/>"
        "<ellipse cx='16' cy='56' rx='16' ry='10'/>"
        "<ellipse cx='30' cy='52' rx='17' ry='10'/>"
        "<ellipse cx='46' cy='56' rx='14' ry='9'/>"
        "</g>"
        "<g class='wx-cloud-track wx-cloud-track-3' fill='rgba(196,218,238,0.72)'>"
        "<ellipse cx='148' cy='64' rx='18' ry='10'/>"
        "<ellipse cx='164' cy='60' rx='20' ry='12'/>"
        "<ellipse cx='184' cy='64' rx='16' ry='9'/>"
        "<ellipse cx='304' cy='66' rx='16' ry='9'/>"
        "<ellipse cx='318' cy='62' rx='18' ry='10'/>"
        "<ellipse cx='336' cy='66' rx='14' ry='8'/>"
        "</g>"
        "</svg>"
        "</div>"
    )


def _rain_svg() -> str:
    """Rain icon with cloud + drops."""
    return (
        "<svg class='wx-rain-svg' width='64' height='64' viewBox='0 0 64 64' xmlns='http://www.w3.org/2000/svg'>"
        "<g class='wx-rain-sun'>"
        # sun peek
        "<circle cx='46' cy='14' r='10' fill='#FFCA28' opacity='0.9'/>"
        "<g stroke='#FFB300' stroke-width='2' stroke-linecap='round' opacity='0.8'>"
        "<line x1='46' y1='2' x2='46' y2='5'/><line x1='58' y1='14' x2='55' y2='14'/>"
        "<line x1='54.5' y1='5.5' x2='52.4' y2='7.6'/>"
        "</g>"
        "</g>"
        "<g class='wx-rain-cloud'>"
        # cloud
        "<path d='M10 38 a12 12 0 0 1 2-24 14 14 0 0 1 27 3 10 10 0 0 1 0 21Z' fill='#90CAF9'/>"
        "<path d='M12 38 a10 10 0 0 1 1.5-19 12 12 0 0 1 23 2.5 8 8 0 0 1 0 16.5Z' fill='#BBDEFB'/>"
        "</g>"
        # raindrops
        "<g stroke='#29B6F6' stroke-width='2.2' stroke-linecap='round'>"
        "<line class='wx-rain-drop d1' x1='18' y1='44' x2='15' y2='52'/>"
        "<line class='wx-rain-drop d2' x1='28' y1='44' x2='25' y2='52'/>"
        "<line class='wx-rain-drop d3' x1='38' y1='44' x2='35' y2='52'/>"
        "</g>"
        "</svg>"
    )


def _params_section_html(latest, scope_df):
    wind_deg = latest.get("wind_dir", np.nan)
    wind_dir_text = _wind_dir_label(wind_deg)
    wind_now = latest.get("wind_speed", np.nan)
    gust_ms = scope_df["wind_speed"].quantile(0.9) / 3.6 if "wind_speed" in scope_df.columns else np.nan
    gust_kmh = gust_ms * 3.6 if not pd.isna(gust_ms) else np.nan
    cloud_now = latest.get("cloud", np.nan)
    rain_now = latest.get("rain", np.nan)
    humidity_now = latest.get("humidity", np.nan)
    pressure_now = latest.get("pressure", np.nan)

    visibility_km = np.nan
    if not pd.isna(cloud_now):
        visibility_km = np.clip(11 - float(cloud_now) * 0.08, 2, 11)

    rain_chance = (
        (scope_df["rain"].fillna(0) > 0).mean() * 100 if "rain" in scope_df.columns else np.nan
    )

    # Pressure bar thumb %
    p_pct = 50.0
    if not pd.isna(pressure_now):
        p_pct = float(np.clip((pressure_now - 980) / 50 * 100, 0, 100))

    # UV (estimated from cloud cover)
    uv_val = np.nan
    if not pd.isna(cloud_now):
        uv_val = float(np.clip(10 * (1 - float(cloud_now) / 100), 0, 11))
    uv_safe = uv_val if not pd.isna(uv_val) else 0.0
    uv_pct = float(np.clip(uv_safe / 11 * 100, 0, 100))
    uv_label = (
        "Thấp" if uv_safe < 3 else
        "Trung bình" if uv_safe < 6 else
        "Cao" if uv_safe < 8 else
        "Rất cao"
    )

    # Build widgets
    compass = _compass_svg(wind_deg if not pd.isna(wind_deg) else 0)
    turbine = _turbine_svg(wind_now)
    gauge = _pressure_gauge_svg(pressure_now if not pd.isna(pressure_now) else 1013)
    cloud_art = _cloud_svg()
    rain_art = _rain_svg()

    wind_deg_str = _fmt_num(wind_deg, 0)
    gust_ms_str = _fmt_num(gust_ms, 1)
    cloud_str = _fmt_num(cloud_now, 0)
    vis_str = _fmt_num(visibility_km, 0)
    rain_str = _fmt_num(rain_now, 1)
    pressure_str = _fmt_num(pressure_now, 0)
    uv_str = _fmt_num(uv_val, 1)

    cards = []
    cards.append(
        "<div class='wx-pcard' style='padding:12px 14px;'>"
        "<div class='wx-compass-wrap'>"
        f"<div class='wx-compass-svg'>{compass}</div>"
        "<div class='wx-compass-info'>"
        "<div class='wx-pcard-label'>Hướng</div>"
        f"<div class='wx-compass-deg'>{wind_deg_str}° {wind_dir_text}</div>"
        f"<div class='wx-compass-sub'>Tốc độ: <b style='color:#fff'>{_fmt_num(wind_now,1)} km/h</b></div>"
        "</div></div></div>"
    )
    cards.append(
        "<div class='wx-pcard' style='padding:12px 14px;'>"
        "<div class='wx-wind-wrap'>"
        f"<div class='wx-wind-icon'>{turbine}</div>"
        "<div><div class='wx-pcard-label'>Tốc Độ Gió Giật</div>"
        f"<div class='wx-pcard-value'>{gust_ms_str} <span class='wx-pcard-value-sm'>m/s</span></div>"
        f"<div class='wx-pcard-sub'>≈ {_fmt_num(gust_kmh,1)} km/h<br>P90 trong khung đang xem</div>"
        "</div></div></div>"
    )
    cards.append(
        "<div class='wx-pcard cloud-card' style='padding:12px 14px;'>"
        f"{cloud_art}"
        "<div class='wx-cloud-metrics'>"
        "<div class='wx-cloud-metric'><div class='wx-pcard-label'>Mây Che Phủ</div>"
        f"<div class='wx-pcard-value'>{cloud_str} <span class='wx-pcard-value-sm'>%</span></div></div>"
        "<div class='wx-cloud-divider'></div>"
        "<div class='wx-cloud-metric right'><div class='wx-pcard-label'>Tầm Nhìn</div>"
        f"<div class='wx-pcard-value'>{vis_str} <span class='wx-pcard-value-sm'>km</span></div></div>"
        "</div></div>"
    )
    cards.append(
        "<div class='wx-pcard' style='padding:12px 14px;'>"
        "<div class='wx-rain-wrap'>"
        f"<div>{rain_art}</div>"
        "<div><div class='wx-pcard-label'>Lượng Mưa</div>"
        f"<div class='wx-pcard-value'>{rain_str} <span class='wx-pcard-value-sm'>mm</span></div>"
        f"<div class='wx-pcard-sub'>Xác suất mưa hiện tại là {rain_str}mm.</div>"
        "</div></div></div>"
    )
    cards.append(
        "<div class='wx-pcard' style='padding:12px 14px;'>"
        "<div class='wx-gauge-wrap'>"
        f"<div class='wx-gauge-svg'>{gauge}</div>"
        "<div class='wx-gauge-info'><div class='wx-pcard-label'>Áp Suất</div>"
        f"<div class='wx-pcard-value'>{pressure_str} <span class='wx-pcard-value-sm'>mb</span></div></div></div>"
        f"<div class='wx-pressure-track' style='margin-top:6px;'><span class='wx-pressure-thumb' style='left:{p_pct:.1f}%'></span></div>"
        f"<div class='wx-pcard-sub' style='margin-top:7px;'>Mức áp suất hiện tại là {pressure_str}mb.</div>"
        "</div>"
    )
    cards.append(
        "<div class='wx-pcard uv' style='padding:14px 16px;'>"
        "<div class='wx-pcard-label' style='color:rgba(210,255,210,0.85);'>Chỉ Số UV</div>"
        f"<div class='wx-pcard-value'>{uv_str} <span style='font-size:1rem;font-weight:700;color:rgba(210,255,200,0.9);'>{uv_label}</span></div>"
        "<div class='wx-uv-bar-wrap'><div class='wx-uv-track'>"
        f"<span class='wx-uv-thumb' style='left:{uv_pct:.1f}%;'></span>"
        "</div><div class='wx-uv-labels'><span>Thấp</span><span>TB</span><span>Cao</span><span>Rất cao</span><span>Cực cao</span></div></div>"
        f"<div class='wx-pcard-sub' style='color:rgba(210,255,210,0.80);margin-top:6px;'>Chỉ số UV hiện tại là {uv_str}, hãy xem xét các khuyến nghị cho điều này!</div>"
        "</div>"
    )

    return (
        "<div class='wx-section-wrap'>"
        "<div class='wx-section-title'>Các thông số thời tiết tại khu vực</div>"
        "<div class='wx-params-grid'>"
        + "".join(cards)
        + "</div></div>"
    )


# ─── Charts ───────────────────────────────────────────────────────────────────

def _plot_hourly_temp(hourly_df, ml_fn, ax_fn):
    sub = hourly_df.tail(24).copy()
    if sub.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["timestamp"], y=sub["temp"],
        mode="lines", name="Nhiệt độ",
        line=dict(color="#ef4444", width=2.5, shape="spline", smoothing=0.9),
        fill="tozeroy", fillcolor="rgba(239,68,68,.18)",
        hovertemplate="%{x|%H:%M %d/%m}<br>Nhiệt độ: %{y:.1f}°C<extra></extra>",
    ))
    if "humidity" in sub.columns:
        fig.add_trace(go.Scatter(
            x=sub["timestamp"], y=sub["humidity"],
            mode="lines", name="Độ ẩm",
            line=dict(color="#93c5fd", width=1.6),
            yaxis="y2",
            hovertemplate="%{x|%H:%M %d/%m}<br>Độ ẩm: %{y:.0f}%<extra></extra>",
        ))
    fig.add_hline(
        y=35,
        line_dash="dash",
        line_color="rgba(251,113,133,0.92)",
        annotation_text="Ngưỡng nóng 35°C",
        annotation_position="top left",
        annotation_font=dict(color="#fecdd3", size=10),
    )
    y1 = ax_fn("Nhiệt độ (°C)")
    y1.update({"tickfont": {"color": "#fecaca", "size": 9}, "gridcolor": "rgba(148,163,184,0.22)"})
    y2 = ax_fn("Độ ẩm (%)")
    y2.update({"overlaying": "y", "side": "right", "showgrid": False, "tickfont": {"color": "#bfdbfe", "size": 9}})
    xaxis_cfg = ax_fn("Giờ")
    xaxis_cfg.update({"tickformat": "%Hh", "tickfont": {"color": "#cbd5e1", "size": 9}, "gridcolor": "rgba(148,163,184,0.14)"})
    ml_fn(fig, h=300,
        xaxis=xaxis_cfg,
        yaxis=y1, yaxis2=y2,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", size=10, family="Inter"),
        legend=dict(orientation="h", x=0, y=1.12, bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0")),
        hovermode="x unified",
    )
    return fig


def _plot_daily_forecast(daily_df, ml_fn, ax_fn):
    sub = daily_df.tail(10).copy()
    if sub.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["timestamp"], y=sub["temp_max"],
        mode="lines+markers", name="Cao",
        line=dict(color="#f97316", width=2.4), marker=dict(size=6),
        hovertemplate="%{x|%d/%m}<br>Cao: %{y:.1f}°C<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=sub["timestamp"], y=sub["temp_min"],
        mode="lines+markers", name="Thấp",
        line=dict(color="#38bdf8", width=2.0), marker=dict(size=5),
        fill="tonexty", fillcolor="rgba(56,189,248,.15)",
        hovertemplate="%{x|%d/%m}<br>Thấp: %{y:.1f}°C<extra></extra>",
    ))
    if "rain" in sub.columns:
        fig.add_trace(go.Bar(
            x=sub["timestamp"], y=sub["rain"], yaxis="y2", name="Mưa",
            marker=dict(color="rgba(14,165,233,.30)", line=dict(color="#0284c7", width=1)),
            hovertemplate="%{x|%d/%m}<br>Mưa: %{y:.1f} mm<extra></extra>",
        ))
    fig.add_hline(
        y=35,
        line_dash="dot",
        line_color="rgba(239,68,68,0.7)",
        annotation_text="35°C",
        annotation_position="top left",
        annotation_font=dict(color="#ef4444", size=10),
    )
    ml_fn(fig, h=300,
        xaxis=dict(**ax_fn("Ngày"), tickformat="%d/%m", tickfont=dict(color="#cbd5e1", size=9), gridcolor="rgba(148,163,184,0.14)"),
        yaxis=dict(**ax_fn("Nhiệt độ (°C)"), tickfont=dict(color="#fecaca", size=9), gridcolor="rgba(148,163,184,0.22)"),
        yaxis2=dict(**ax_fn("Mưa (mm)"), overlaying="y", side="right", showgrid=False, rangemode="tozero", tickfont=dict(color="#bfdbfe", size=9)),
        legend=dict(orientation="h", x=0, y=1.12, bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0")),
        barmode="overlay",
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", size=10, family="Inter"),
    )
    return fig


def _plot_wind_rose(hourly_df, ml_fn):
    if hourly_df is None or hourly_df.empty:
        return None
    if "wind_speed" not in hourly_df.columns or "wind_dir" not in hourly_df.columns:
        return None
    valid = hourly_df.dropna(subset=["wind_speed", "wind_dir"]).copy()
    if valid.empty:
        return None
    sector_idx = (((valid["wind_dir"] % 360) + 11.25) // 22.5).astype(int) % 16
    valid["sector"] = sector_idx.map(dict(enumerate(WIND_SECTORS)))
    valid["speed_band"] = pd.cut(
        valid["wind_speed"], bins=WIND_SPEED_BINS,
        labels=WIND_SPEED_LABELS, include_lowest=True, right=False,
    )
    pivot = (
        valid.groupby(["sector", "speed_band"], observed=False)
        .size().unstack(fill_value=0)
        .reindex(index=WIND_SECTORS, columns=WIND_SPEED_LABELS, fill_value=0)
    )
    colors = ["#bae6fd", "#7dd3fc", "#38bdf8", "#0ea5e9", "#0369a1"]
    fig = go.Figure()
    for band, color in zip(WIND_SPEED_LABELS, colors):
        fig.add_trace(go.Barpolar(
            r=pivot[band].values, theta=WIND_SECTORS, name=f"{band} km/h",
            marker_color=color, marker_line_color="rgba(255,255,255,0.75)",
            marker_line_width=0.7, opacity=0.94,
            hovertemplate="Hướng %{theta}<br>Tần suất: %{r} giờ<extra></extra>",
        ))
    ml_fn(fig, h=340,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(showticklabels=True, ticks="", gridcolor="rgba(0,0,0,0.08)", tickfont=dict(color="#475569", size=9)),
            angularaxis=dict(direction="clockwise", rotation=90, gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#334155", size=9)),
        ),
        legend=dict(orientation="h", x=0, y=1.1, bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
    )
    return fig


def _plot_pressure_cloud(hourly_df, ml_fn, ax_fn):
    if hourly_df is None or hourly_df.empty:
        return None
    if "pressure" not in hourly_df.columns or "cloud" not in hourly_df.columns:
        return None
    valid = hourly_df.dropna(subset=["pressure", "cloud"]).copy()
    if valid.empty:
        return None
    rain_size = valid["rain"].fillna(0).clip(lower=0) if "rain" in valid.columns else 0
    marker_size = 6 + np.clip(rain_size * 2.6, 0, 20)
    fig = go.Figure(go.Scatter(
        x=valid["pressure"], y=valid["cloud"], mode="markers",
        marker=dict(
            size=marker_size, color=valid["temp"] if "temp" in valid.columns else "#3b82f6",
            colorscale="RdYlBu_r", showscale=True,
            colorbar=dict(title="°C", thickness=10),
            line=dict(width=0.8, color="rgba(15,23,42,0.20)"), opacity=0.82,
        ),
        customdata=np.stack([
            valid.index.map(lambda i: ""),
            valid["rain"].fillna(0) if "rain" in valid.columns else np.zeros(len(valid)),
        ], axis=1),
        hovertemplate="Áp suất: %{x:.1f} hPa<br>Mây: %{y:.0f}%<extra></extra>",
    ))

    x_mid = float(valid["pressure"].median())
    y_mid = 50.0
    x_min = float(valid["pressure"].min())
    x_max = float(valid["pressure"].max())

    fig.add_vline(x=x_mid, line_dash="dot", line_color="rgba(51,65,85,0.45)")
    fig.add_hline(y=y_mid, line_dash="dot", line_color="rgba(51,65,85,0.45)")

    x_left = x_min + (x_mid - x_min) * 0.18 if x_mid > x_min else x_min
    x_right = x_mid + (x_max - x_mid) * 0.18 if x_max > x_mid else x_max
    y_low = 14
    y_high = 86
    annotations = [
        (x_left, y_high, "Áp thấp • Mây cao"),
        (x_right, y_high, "Áp cao • Mây cao"),
        (x_left, y_low, "Áp thấp • Trời quang"),
        (x_right, y_low, "Áp cao • Trời quang"),
    ]
    for x_val, y_val, label in annotations:
        fig.add_annotation(
            x=x_val,
            y=y_val,
            text=label,
            showarrow=False,
            font=dict(size=9, color="#334155"),
            bgcolor="rgba(255,255,255,0.72)",
            bordercolor="rgba(148,163,184,0.40)",
            borderpad=3,
        )

    ml_fn(fig, h=340,
        xaxis=dict(**ax_fn("Áp suất (hPa)")),
        yaxis=dict(**ax_fn("Mây (%)"), range=[0, 100]),
        hovermode="closest",
    )
    return fig


def _weather_metric_meta(metric_key: str) -> dict:
    mapping = {
        "temp": {"label": "Nhiệt độ", "unit": "°C", "color": "#ef4444"},
        "humidity": {"label": "Độ ẩm", "unit": "%", "color": "#0ea5e9"},
        "rain": {"label": "Mưa", "unit": "mm", "color": "#2563eb"},
        "wind_speed": {"label": "Gió", "unit": "km/h", "color": "#10b981"},
        "pressure": {"label": "Áp suất", "unit": "hPa", "color": "#8b5cf6"},
        "cloud": {"label": "Mây", "unit": "%", "color": "#64748b"},
    }
    return mapping.get(metric_key, {"label": metric_key, "unit": "", "color": "#0ea5e9"})


def _plot_weather_metric(metric_df, metric_key, chart_type, ml_fn, ax_fn):
    if metric_df is None or metric_df.empty or metric_key not in metric_df.columns:
        return None

    sub = metric_df.dropna(subset=[metric_key]).copy()
    if sub.empty:
        return None

    meta = _weather_metric_meta(metric_key)
    label = meta["label"]
    unit = meta["unit"]
    color = meta["color"]

    fig = go.Figure()
    if chart_type == "Cột (Bar)":
        fig.add_trace(
            go.Bar(
                x=sub["timestamp"],
                y=sub[metric_key],
                marker=dict(color=color, line=dict(width=0.5, color="#ffffff")),
                opacity=0.9,
                hovertemplate=f"%{{x|%H:%M %d/%m}}<br>{label}: %{{y:.1f}} {unit}<extra></extra>",
                name=label,
            )
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=sub["timestamp"],
                y=sub[metric_key],
                mode="lines+markers",
                line=dict(color=color, width=2.6, shape="spline", smoothing=0.9),
                marker=dict(size=5),
                fill="tozeroy",
                fillcolor="rgba(14,165,233,0.10)" if metric_key != "temp" else "rgba(239,68,68,0.12)",
                hovertemplate=f"%{{x|%H:%M %d/%m}}<br>{label}: %{{y:.1f}} {unit}<extra></extra>",
                name=label,
            )
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        height=400,
        showlegend=False,
        hovermode="x unified",
        font=dict(family="'Be Vietnam Pro', sans-serif", size=12, color="#475569"),
    )
    return fig


def _plot_weather_radar(df: pd.DataFrame, title: str) -> go.Figure:
    """Create a normalized Radar (Spider) chart for a multi-dimensional weather profile."""
    if df.empty:
        return None

    # Define metrics and their normalization ranges [min, max]
    metrics_config = {
        "temp": {"label": "Nhiệt độ (°C)", "range": [10, 45]},
        "humidity": {"label": "Độ ẩm (%)", "range": [0, 100]},
        "wind_speed": {"label": "Gió (km/h)", "range": [0, 60]},
        "cloud": {"label": "Mây (%)", "range": [0, 100]},
        "rain": {"label": "Mưa (mm)", "range": [0, 30]},
        "pressure": {"label": "Áp suất", "range": [990, 1030]},
    }

    categories = [cfg["label"] for cfg in metrics_config.values()]
    values = []
    raw_values = []

    for key, cfg in metrics_config.items():
        if key in df.columns:
            raw_val = df[key].mean()
            raw_values.append(raw_val)
            min_v, max_v = cfg["range"]
            norm_val = max(0, min(100, (raw_val - min_v) / (max_v - min_v) * 100))
            values.append(norm_val)
        else:
            values.append(0)
            raw_values.append(np.nan)

    # Close the loop
    categories.append(categories[0])
    values.append(values[0])
    raw_values.append(raw_values[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself', name='Hiện tại',
        line=dict(color='#3b82f6', width=2),
        fillcolor='rgba(59, 130, 246, 0.25)',
        hoverinfo='text',
        text=[f"{v:.1f}" if not pd.isna(v) else "N/A" for v in raw_values]
    ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(248, 250, 252, 0.5)",
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="rgba(148, 163, 184, 0.2)"),
            angularaxis=dict(gridcolor="rgba(148, 163, 184, 0.2)", linecolor="rgba(148, 163, 184, 0.2)", tickfont=dict(size=11, color="#475569"))
        ),
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=60, r=60, t=40, b=40), height=450,
        showlegend=False,
        title=dict(text=f"Cấu trúc thời tiết: {title}", font=dict(size=14, color="#0f172a", weight=700), x=0.5, y=0.98)
    )
    return fig


def _render_mode_switch(options, key, prefix):
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = options[0]
    cols = st.columns(len(options), gap="small")
    for idx, opt in enumerate(options):
        if cols[idx].button(
            opt, key=f"{prefix}_{idx}",
            type="primary" if st.session_state[key] == opt else "secondary",
            width="stretch",
        ):
            st.session_state[key] = opt
    return st.session_state[key]


# ─── Main render ──────────────────────────────────────────────────────────────

def render(df: pd.DataFrame):
    ctx = st.session_state.get("dashboard_context", {})
    ml_fn, ax_fn = _get_plot_helpers(ctx)
    _inject_weather_css()

    if df is None or df.empty:
        st.warning("Không có dữ liệu thời tiết.")
        return
    if "city" not in df.columns or "timestamp" not in df.columns:
        st.warning("Thiếu cột city/timestamp.")
        return

    weather_df = df.copy()
    weather_df["timestamp"] = pd.to_datetime(weather_df["timestamp"], errors="coerce")
    weather_df = weather_df.dropna(subset=["timestamp", "city"])
    for col in WEATHER_FEATURES:
        if col in weather_df.columns:
            weather_df[col] = pd.to_numeric(weather_df[col], errors="coerce")

    cities = sorted(weather_df["city"].astype(str).unique().tolist())
    if not cities:
        st.warning("Không tìm thấy khu vực.")
        return

    if "weather_city" not in st.session_state or st.session_state.weather_city not in cities:
        preferred = None
        sel = ctx.get("sel") if isinstance(ctx, dict) else None
        if isinstance(sel, list) and sel:
            preferred = sel[0]
        st.session_state.weather_city = preferred if preferred in cities else cities[0]

    if "weather_scope" not in st.session_state:
        st.session_state.weather_scope = "72h"
    if "weather_chart_type" not in st.session_state:
        st.session_state.weather_chart_type = "Đường (Spline)"
    if "weather_metric_key" not in st.session_state:
        st.session_state.weather_metric_key = "temp"
    if "weather_location_scope" not in st.session_state:
        st.session_state.weather_location_scope = ""

    # ── TOP CONTROLS ──
    c_top1, c_top2, c_top3 = st.columns([1.5, 1.5, 2], gap="small")
    with c_top1:
        selected_city = st.selectbox("Khu vực", options=cities, key="weather_city",
                                     help="Chọn khu vực xem thời tiết.")

    # We need city_df_all to get valid date range for the date picker
    city_df_all = weather_df[weather_df["city"] == selected_city].sort_values("timestamp").copy()
    day_series_all = pd.to_datetime(city_df_all["timestamp"]).dt.normalize()
    min_day = day_series_all.min().date()
    max_day = day_series_all.max().date()
    default_anchor = day_series_all.iloc[max(0, len(day_series_all) - 10)].date()

    if "weather_anchor_picker" not in st.session_state:
        st.session_state["weather_anchor_picker"] = default_anchor
    if (st.session_state["weather_anchor_picker"] < min_day or st.session_state["weather_anchor_picker"] > max_day):
        st.session_state["weather_anchor_picker"] = default_anchor

    with c_top2:
        anchor_pick = st.date_input(
            "Ngày mốc dự báo",
            min_value=min_day,
            max_value=max_day,
            key="weather_anchor_picker",
            help="Chọn ngày khởi đầu để xem chi tiết và dự báo."
        )

    # Variables for the lower controls (moved from above)
    location_options = [f"Tổng quan ({selected_city})"]
    if "location" in city_df_all.columns:
        locs = sorted(city_df_all["location"].dropna().astype(str).unique().tolist())
        location_options += locs

    if "weather_location_scope" not in st.session_state:
        st.session_state.weather_location_scope = location_options[0]
    if "weather_chart_type" not in st.session_state:
        st.session_state.weather_chart_type = "Đường (Spline)"
    if "weather_scope" not in st.session_state:
        st.session_state.weather_scope = "72h"
    if "weather_metric_key" not in st.session_state:
        st.session_state.weather_metric_key = "temp"

    # Final dataset for display (initially matching session state)
    city_df = city_df_all.copy()
    cur_loc = st.session_state.get("weather_location_scope", location_options[0])
    if cur_loc != f"Tổng quan ({selected_city})" and "location" in city_df.columns:
        if cur_loc in location_options:
            city_df = city_df[city_df["location"].astype(str) == str(cur_loc)].copy()

    if city_df.empty:
        st.warning("Khu vực này được chọn chưa có dữ liệu chi tiết.")
        return

    cache_sig = (
        selected_city,
        str(cur_loc),
        int(len(city_df)),
        str(city_df["timestamp"].min()),
        str(city_df["timestamp"].max()),
    )
    if st.session_state.get("weather_city_cache_sig") != cache_sig:
        hourly_df = _build_hourly_frame(city_df)
        daily_df = _build_daily_frame(city_df).sort_values("timestamp").reset_index(drop=True)
        day_groups = {}
        if not hourly_df.empty:
            grouped_src = hourly_df.copy()
            grouped_src["day_key"] = grouped_src["timestamp"].dt.strftime("%Y-%m-%d")
            for day_key, group in grouped_src.groupby("day_key", sort=True, observed=False):
                day_groups[day_key] = group.drop(columns=["day_key"]).reset_index(drop=True)
        st.session_state["weather_city_cache_sig"] = cache_sig
        st.session_state["weather_city_cache"] = {
            "hourly_df": hourly_df,
            "daily_df": daily_df,
            "day_groups": day_groups,
        }
    else:
        cached = st.session_state.get("weather_city_cache", {})
        hourly_df = cached.get("hourly_df", pd.DataFrame())
        daily_df = cached.get("daily_df", pd.DataFrame())
        day_groups = cached.get("day_groups", {})

    if hourly_df.empty:
        st.warning("Không đủ dữ liệu theo giờ.")
        return

    # scope_df for current view
    cur_scope_label = st.session_state.get("weather_scope", "72h")
    hours_map = {"24h": 24, "72h": 72, "7 ngày": 24 * 7, "30 ngày": 24 * 30}
    scope_hours = hours_map.get(cur_scope_label, 72)
    end_ts = hourly_df["timestamp"].max()
    start_ts = end_ts - pd.Timedelta(hours=scope_hours - 1)
    scope_df = hourly_df[hourly_df["timestamp"] >= start_ts].copy()

    anchor_day = pd.Timestamp(anchor_pick).normalize()
    day_series = pd.to_datetime(daily_df["timestamp"]).dt.normalize()
    forecast_df = daily_df[day_series >= anchor_day].head(10).copy()
    if forecast_df.empty:
        forecast_df = daily_df.tail(10).copy()
        if not forecast_df.empty:
            anchor_day = pd.to_datetime(forecast_df.iloc[0]["timestamp"]).normalize()

    end_day = pd.to_datetime(forecast_df.iloc[-1]["timestamp"]).normalize()
    day_keys = [pd.to_datetime(ts).strftime("%Y-%m-%d") for ts in forecast_df["timestamp"]]
    anchor_day_key = day_keys[0]

    anchor_day_df = day_groups.get(anchor_day_key)
    if anchor_day_df is None or anchor_day_df.empty:
        anchor_day_df = scope_df.tail(24).copy()
    else:
        anchor_day_df = anchor_day_df.copy()

    base_day_df = anchor_day_df

    latest = base_day_df.iloc[-1]
    latest_ts = pd.to_datetime(latest["timestamp"])
    cond_now = _condition_from_weather(latest.get("rain", np.nan), latest.get("cloud", np.nan))
    feels_like = _feels_like_c(
        latest.get("temp", np.nan), latest.get("humidity", np.nan), latest.get("wind_speed", np.nan)
    )

    day_high = base_day_df["temp"].max() if "temp" in base_day_df.columns else np.nan
    day_low  = base_day_df["temp"].min() if "temp" in base_day_df.columns else np.nan
    rain_chance = (base_day_df["rain"].fillna(0) > 0).mean() * 100 if "rain" in base_day_df.columns else np.nan

    big_icon = _condition_img(cond_now, size=64)

    # ── HERO CARD ──────────────────────────────────────────────────────────────
    st.markdown(_html(f"""
    <div class='wx-hero'>
      <div class='wx-hero-inner'>
        <div class='wx-breadcrumb'>
          Thời tiết &gt; Việt Nam &gt; {selected_city}
        </div>
        <div class='wx-nav-pills'>
          <span class='wx-nav-pill'>AQI</span>
          <span class='wx-nav-pill active'>Thời tiết</span>
        </div>
        <div class='wx-hero-grid'>
          <!-- Left: Current conditions -->
          <div>
                        <div class='wx-city-name'>{selected_city} – Điều kiện thời tiết ngày mốc {anchor_day:%d/%m/%Y}</div>
            <div class='wx-title-row'>
              {big_icon}
              <div>
                <div class='wx-temp-big'>{_fmt_num(latest.get("temp", np.nan), 0)}</div>
                <div class='wx-temp-unit'>°C</div>
              </div>
            </div>
            <div class='wx-cond-text'>{cond_now}</div>
            <div class='wx-hilow'>Cao {_fmt_num(day_high,0)}° / Thấp {_fmt_num(day_low,0)}°</div>
            <div class='wx-stat-row'>
              <span class='wx-stat-pill'>
                <svg width='12' height='12' viewBox='0 0 20 20' fill='none'><path d='M10 3C10 3 4 9 4 13a6 6 0 0 0 12 0c0-4-6-10-6-10Z' stroke='#93c5fd' stroke-width='2'/></svg>
                Ẩm {_fmt_num(latest.get("humidity",np.nan),0)}%
              </span>
              <span class='wx-stat-pill'>
                <svg width='12' height='12' viewBox='0 0 20 20' fill='none'><circle cx='10' cy='10' r='6' stroke='#fca5a5' stroke-width='2'/><path d='M10 10V6' stroke='#fca5a5' stroke-width='2' stroke-linecap='round'/></svg>
                Cảm giác {_fmt_num(feels_like,1)}°C
              </span>
              <span class='wx-stat-pill'>
                <svg width='12' height='12' viewBox='0 0 20 20' fill='none'><path d='M3 10h14M13 6l4 4-4 4' stroke='#86efac' stroke-width='2' stroke-linecap='round'/></svg>
                Mưa {_fmt_num(rain_chance,0)}%
              </span>
              <span class='wx-stat-pill'>
                🕐 {latest_ts:%H:%M, %d/%m/%Y}
              </span>
            </div>
          </div>
          <!-- Right: Hourly strip -->
          <div class='wx-hour-panel'>
            <div class='wx-hour-tabs'>
              <span class='wx-hour-tab active'>Hàng giờ</span>
              <span class='wx-hour-tab'>Hàng ngày</span>
            </div>
            <div class='wx-hour-strip'>
                            {_hourly_strip_html(base_day_df, 6)}
            </div>
            <div class='wx-hour-note'>Xu hướng theo khu vực đang chọn.</div>
          </div>
        </div>
      </div>
    </div>
    """), unsafe_allow_html=True)

    # ── PARAMS SECTION ──────────────────────────────────────────────────────────
    st.markdown(_params_section_html(latest, base_day_df), unsafe_allow_html=True)

    # ── 10-DAY FORECAST ─────────────────────────────────────────────────────────
    st.markdown(
        _forecast_hourly_switch_html(
            forecast_df,
            day_groups=day_groups,
            anchor_day=anchor_day,
            switch_key=f"{selected_city}|{anchor_day_key}",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='wx-fc-note'>Dải dự báo: {anchor_day:%d/%m/%Y} → {end_day:%d/%m/%Y}. Nhấn vào card ngày để xem dữ liệu giờ tương ứng.</div>",
        unsafe_allow_html=True,
    )

    month_panel_html = _monthly_calendar_section_html(daily_df, anchor_day, selected_city)
    if month_panel_html:
        st.markdown(month_panel_html, unsafe_allow_html=True)

    detail_rows = _load_anchor_location_rows(selected_city, anchor_day)
    detail_summary = _build_location_day_summary(detail_rows)

    st.markdown(_html(f"""
    <div class='wx-analysis-card wx-month-tone'>
            <div class='wx-block-head'>
                <div class='wx-block-title'>Chi tiết theo địa điểm trong tỉnh</div>
                <div class='wx-block-sub'>Ngày mốc {anchor_day:%d/%m/%Y} tại {selected_city}. Nguồn: dữ liệu chi tiết data/aqi.</div>
            </div>
    </div>
    """), unsafe_allow_html=True)

    if detail_summary.empty:
        st.info(
            f"Chưa có dữ liệu chi tiết theo địa điểm cho {selected_city} vào ngày mốc {anchor_day:%d/%m/%Y}."
        )
    else:
        temp_avg_text = _fmt_num(detail_summary["temp_avg"].mean(), 1)
        temp_avg_text = f"{temp_avg_text}°C" if temp_avg_text != "N/A" else "N/A"
        humidity_avg_text = _fmt_num(detail_summary["humidity"].mean(), 0)
        humidity_avg_text = f"{humidity_avg_text}%" if humidity_avg_text != "N/A" else "N/A"
        rain_sum_text = _fmt_num(detail_summary["rain"].sum(), 1)
        rain_sum_text = f"{rain_sum_text} mm" if rain_sum_text != "N/A" else "N/A"

        st.markdown(
            _detail_kpi_strip_html(
                len(detail_summary),
                temp_avg_text,
                humidity_avg_text,
                rain_sum_text,
            ),
            unsafe_allow_html=True,
        )

        st.markdown(_location_detail_table_html(detail_summary, max_rows=10), unsafe_allow_html=True)
        if len(detail_summary) > 10:
            st.caption(
                f"Đang hiển thị 10/{len(detail_summary)} địa điểm đầu tiên (sắp theo AQI giảm dần)."
            )

    # ── CHART CONTROLS (Moved here) ──
    st.markdown('<hr style="margin: 2rem 0 1rem 0; border-color: rgba(148,163,184,0.2);">', unsafe_allow_html=True)
    
    # Place secondary controls right above charts
    cc1, cc2, cc3, cc4 = st.columns([1.5, 1.2, 1.0, 1.0], gap="small")
    
    with cc1:
        # Re-verify curate scope options
        cur_scope_opt = st.session_state.get("weather_location_scope", location_options[0])
        if cur_scope_opt not in location_options:
            cur_scope_opt = location_options[0]
        selected_location = st.selectbox(
            "Đơn vị (Huyện/Xã/Phường)",
            options=location_options,
            index=location_options.index(cur_scope_opt),
            key="weather_location_scope",
        )
    
    with cc2:
        try:
            chart_opts = [":material/show_chart:", ":material/bar_chart:", ":material/track_changes:"]
            mapping = {
                ":material/show_chart:": "Đường (Spline)",
                ":material/bar_chart:": "Cột (Bar)",
                ":material/track_changes:": "Mạng nhện (Radar)"
            }
            rev_mapping = {v: k for k, v in mapping.items()}
            
            cur_type = st.session_state.get("weather_chart_type", "Đường (Spline)")
            default_icon = rev_mapping.get(cur_type, ":material/show_chart:")
            
            raw_sel = st.segmented_control("Loại biểu đồ", options=chart_opts, default=default_icon, key="weather_chart_seg")
            chart_type = mapping.get(raw_sel, cur_type)
        except AttributeError:
            chart_type = st.radio(
                "Loại biểu đồ", ["Đường (Spline)", "Cột (Bar)", "Mạng nhện (Radar)"],
                index=["Đường (Spline)", "Cột (Bar)", "Mạng nhện (Radar)"].index(st.session_state.get("weather_chart_type", "Đường (Spline)")),
                horizontal=True, key="weather_chart_radio",
            )
        st.session_state["weather_chart_type"] = chart_type

    with cc3:
        scope_label = st.selectbox("Khung thời gian",
                                   options=["24h", "72h", "7 ngày", "30 ngày"],
                                   key="weather_scope")
    with cc4:
        metric_opts = ["temp", "humidity", "rain", "wind_speed", "pressure", "cloud"]
        metric_fmt = {
            "temp": "Nhiệt độ", "humidity": "Độ ẩm", "rain": "Mưa",
            "wind_speed": "Gió", "pressure": "Áp suất", "cloud": "Mây",
        }
        metric_cur = st.session_state.get("weather_metric_key", "temp")
        
        # Disable parameter selection if Radar is active
        is_radar = (chart_type == "Mạng nhện (Radar)")
        metric_key = st.selectbox(
            "Thông số", options=metric_opts,
            index=metric_opts.index(metric_cur) if metric_cur in metric_opts else 0,
            format_func=lambda x: metric_fmt.get(x, x),
            key="weather_metric_select",
            disabled=is_radar,
            help="Tự động hiển thị tất cả thông số khi ở chế độ Mạng nhện." if is_radar else None
        )
        st.session_state["weather_metric_key"] = metric_key

    # Re-calculate scope_df based on new scope_label
    hours_map = {"24h": 24, "72h": 72, "7 ngày": 24 * 7, "30 ngày": 24 * 30}
    scope_hours = hours_map.get(scope_label, 72)
    end_ts = hourly_df["timestamp"].max()
    start_ts = end_ts - pd.Timedelta(hours=scope_hours - 1)
    scope_df = hourly_df[hourly_df["timestamp"] >= start_ts].copy()

    metric_meta = _weather_metric_meta(metric_key)
    metric_label = metric_meta["label"]
    metric_unit = metric_meta["unit"]

    def _weather_level(value: float) -> tuple[str, str, str, str]:
        if metric_key == "temp":
            if value >= 35:
                return ("Nắng nóng", "#ef4444", "#fff1f2", "Nhiệt độ cao, nên hạn chế ra ngoài vào khung giờ nắng gắt.")
            if value >= 30:
                return ("Nóng", "#fb923c", "#fff7ed", "Trời khá nóng, cần bổ sung nước và theo dõi thể trạng.")
            if value >= 20:
                return ("Dễ chịu", "#22c55e", "#f0fdf4", "Mức nhiệt độ tương đối dễ chịu cho phần lớn hoạt động ngoài trời.")
            return ("Mát", "#38bdf8", "#ecfeff", "Nhiệt độ thấp, nên giữ ấm nếu hoạt động ngoài trời kéo dài.")
        if metric_key == "humidity":
            if value >= 85:
                return ("Ẩm cao", "#0ea5e9", "#eff6ff", "Độ ẩm cao có thể gây oi bức, cần không gian thông thoáng.")
            if value >= 40:
                return ("Ổn định", "#22c55e", "#f0fdf4", "Độ ẩm nằm trong vùng tương đối dễ chịu.")
            return ("Khô", "#f59e0b", "#fffbeb", "Không khí khô, nên bổ sung nước và dưỡng ẩm.")
        if metric_key == "rain":
            if value >= 10:
                return ("Mưa lớn", "#1d4ed8", "#eff6ff", "Có khả năng mưa mạnh, chú ý an toàn khi di chuyển.")
            if value > 0:
                return ("Có mưa", "#0ea5e9", "#ecfeff", "Có mưa rải rác, nên chuẩn bị áo mưa/ô.")
            return ("Khô ráo", "#22c55e", "#f0fdf4", "Thời tiết khô ráo, thuận lợi cho hoạt động ngoài trời.")
        if metric_key == "wind_speed":
            if value >= 30:
                return ("Gió mạnh", "#0f766e", "#f0fdfa", "Gió mạnh, cần thận trọng với hoạt động ngoài trời.")
            if value >= 15:
                return ("Có gió", "#14b8a6", "#f0fdfa", "Điều kiện gió trung bình, tương đối ổn định.")
            return ("Gió nhẹ", "#22c55e", "#f0fdf4", "Gió nhẹ, điều kiện thời tiết ổn định.")
        if metric_key == "pressure":
            if value < 1000:
                return ("Áp thấp", "#f97316", "#fff7ed", "Áp suất thấp, thời tiết có thể biến động.")
            if value > 1020:
                return ("Áp cao", "#22c55e", "#f0fdf4", "Áp suất cao, xu hướng thời tiết khá ổn định.")
            return ("Ổn định", "#0ea5e9", "#eff6ff", "Áp suất trong ngưỡng ổn định.")
        if value >= 80:
            return ("Nhiều mây", "#64748b", "#f8fafc", "Mây che phủ cao, khả năng nắng giảm đáng kể.")
        if value >= 40:
            return ("Có mây", "#94a3b8", "#f8fafc", "Mây che phủ trung bình.")
        return ("Ít mây", "#22c55e", "#f0fdf4", "Trời khá quang, thuận lợi cho hoạt động ngoài trời.")

    if is_radar:
        hist_source = scope_df.dropna(subset=["timestamp"]).copy()
    else:
        hist_source = scope_df.dropna(subset=["timestamp", metric_key]).copy() if metric_key in scope_df.columns else pd.DataFrame()

    if not hist_source.empty:
        val_min = float(hist_source[metric_key].min())
        val_max = float(hist_source[metric_key].max())
        row_min = hist_source.loc[hist_source[metric_key].idxmin()]
        row_max = hist_source.loc[hist_source[metric_key].idxmax()]
        lbl_min, clr_min, _, _ = _weather_level(val_min)
        lbl_max, clr_max, _, _ = _weather_level(val_max)
        str_min_time = pd.to_datetime(row_min["timestamp"]).strftime("%H:%M, %d/%m/%Y")
        str_max_time = pd.to_datetime(row_max["timestamp"]).strftime("%H:%M, %d/%m/%Y")

        st.markdown('<hr style="margin: 1.5rem 0 1rem 0; border-color: rgba(148,163,184,0.15);">', unsafe_allow_html=True)
        cChart, cRank = st.columns([2.8, 1.2], gap="large")
        cT1, cT2 = cChart.columns([1.4, 1], gap="small")

        with cT1:
            st.markdown(
                f"""
                <div>
                    <div style="color:#64748b; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:2px;">Dữ liệu thời tiết lịch sử</div>
                    <div style="font-size:22px; font-family:'Be Vietnam Pro',sans-serif; font-weight:700; color:#0f172a; margin-bottom:4px;">Biểu đồ {metric_label}</div>
                    <div style="color:#334155; font-size:14px; font-weight:500;">{escape(str(selected_location))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with cT2:
            st.markdown(
                f"""
                <div style="display:flex; justify-content: flex-end; gap: 12px; align-items:center; height:100%;">
                    <div style="background:{clr_min}1F; border: 1.5px solid {clr_min}66; padding: 10px 14px; border-radius: 10px; display:flex; flex-direction:column; min-width:140px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
                            <span style="font-size:22px; font-weight:700; color:{clr_min}; line-height:1;">{val_min:.1f}{metric_unit}</span>
                            <span style="font-size:11px; padding:2px 6px; background:{clr_min}; color:#fff; border-radius:4px; font-weight:600;">{lbl_min}</span>
                        </div>
                        <div style="color:#64748b; font-size:11px; display:flex; align-items:center;"><span style="margin-right:4px;">↓ Tối thiểu</span></div>
                        <div style="color:#94a3b8; font-size:10px; font-weight:500;">lúc {str_min_time}</div>
                    </div>
                    <div style="background:{clr_max}1F; border: 1.5px solid {clr_max}66; padding: 10px 14px; border-radius: 10px; display:flex; flex-direction:column; min-width:140px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
                            <span style="font-size:22px; font-weight:700; color:{clr_max}; line-height:1;">{val_max:.1f}{metric_unit}</span>
                            <span style="font-size:11px; padding:2px 6px; background:{clr_max}; color:#fff; border-radius:4px; font-weight:600;">{lbl_max}</span>
                        </div>
                        <div style="color:#64748b; font-size:11px; display:flex; align-items:center;"><span style="margin-right:4px;">↑ Tối đa</span></div>
                        <div style="color:#94a3b8; font-size:10px; font-weight:500;">lúc {str_max_time}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with cChart:
            if chart_type == "Mạng nhện (Radar)":
                radar_fig = _plot_weather_radar(hist_source, escape(str(selected_location)))
                if radar_fig:
                    st.plotly_chart(radar_fig, use_container_width=True, config={"displayModeBar": False})
            else:
                metric_chart = _plot_weather_metric(hist_source[["timestamp", metric_key]].copy(), metric_key, chart_type, ml_fn, ax_fn)
                if metric_chart is not None:
                    st.plotly_chart(metric_chart, use_container_width=True, config={"displayModeBar": False})

        with cRank:
            st.markdown(
                f"<div style=\"font-size:16px; font-family:'Be Vietnam Pro',sans-serif; font-weight:700; color:#0f172a; margin-bottom:12px;\">Top 8 {metric_label} ({scope_label})</div>",
                unsafe_allow_html=True,
            )

            top_list_html = f"""
            <div style="display:flex; font-size:12px; font-weight:600; color:#64748b; padding-bottom: 10px; border-bottom: 2px solid rgba(148,163,184,0.1); margin-bottom: 12px; text-transform:uppercase;">
                <div style="flex:4;">Địa điểm</div>
                <div style="flex:3; text-align:center;">Trạng thái</div>
                <div style="flex:2; text-align:right;">{metric_label}</div>
            </div>
            """

            if "location" in city_df_all.columns:
                rank_df = city_df_all[
                    (city_df_all["timestamp"] >= start_ts)
                    & (city_df_all["timestamp"] <= end_ts)
                ].copy()
                rank_df = rank_df.dropna(subset=["location", metric_key]) if metric_key in rank_df.columns else pd.DataFrame()
            else:
                rank_df = pd.DataFrame()

            detail_metric_col = "temp_avg" if metric_key == "temp" else metric_key
            use_detail_fallback = rank_df.empty and (not detail_summary.empty) and (detail_metric_col in detail_summary.columns)

            if use_detail_fallback:
                top_df = (
                    detail_summary.dropna(subset=["location", detail_metric_col])
                    .sort_values(detail_metric_col, ascending=False)
                    .head(8)
                    .copy()
                )
                top_df = top_df.rename(columns={detail_metric_col: "metric_value"})
            elif not rank_df.empty:
                top_df = (
                    rank_df.groupby("location", as_index=False, observed=False)[metric_key]
                    .mean()
                    .sort_values(metric_key, ascending=False)
                    .head(8)
                    .rename(columns={metric_key: "metric_value"})
                )
            else:
                top_df = pd.DataFrame()

            if not top_df.empty:
                for row in top_df.itertuples(index=False):
                    loc_name = str(row.location)
                    val = float(getattr(row, "metric_value"))
                    lbl, clr, _, _ = _weather_level(val)
                    top_list_html += (
                        "<div style='display:flex; align-items:center; background-color: rgba(248,250,252,0.6); padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(148,163,184,0.15);'>"
                        f"<div style='flex:4; font-size:13px; font-weight:600; color:#1e293b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-right:8px;' title='{escape(loc_name)}'>{escape(loc_name)}</div>"
                        f"<div style='flex:3; display:flex; justify-content:center;'><span style='background-color: {clr}; color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight:600; white-space:nowrap;'>{lbl}</span></div>"
                        f"<div style='flex:2; text-align:right; font-size:15px; font-weight:700; color:#0f172a;'>{val:.1f}{metric_unit}</div>"
                        "</div>"
                    )
                if use_detail_fallback:
                    top_list_html += (
                        f"<div style='margin-top:6px;color:#64748b;font-size:11px;font-style:italic;'>"
                        f"* Top 8 lấy từ dữ liệu địa điểm của ngày mốc {anchor_day:%d/%m/%Y} do chưa đủ dữ liệu theo giờ trong khung {scope_label}."
                        "</div>"
                    )
            else:
                top_list_html += "<div style='color:#64748b; font-size:13px; font-style:italic; text-align:center; padding: 20px 0;'>Không có dữ liệu theo địa điểm trong khung thời gian này</div>"

            st.markdown(top_list_html, unsafe_allow_html=True)

    # ── WEATHER FORECAST STYLE (lower part) ───────────────────────────────────

    metric_source = city_df.dropna(subset=["timestamp", metric_key]).copy() if metric_key in city_df.columns else pd.DataFrame()
    if metric_source.empty:
        st.info(f"Chưa có dữ liệu {metric_label.lower()} cho khu vực đã chọn.")
    else:
        metric_source["timestamp"] = pd.to_datetime(metric_source["timestamp"], errors="coerce")
        metric_source = metric_source.dropna(subset=["timestamp"])

        hourly_metric = (
            metric_source.set_index("timestamp")[[metric_key]]
            .resample("1h")
            .mean()
            .dropna()
            .reset_index()
        )
        hourly_view = hourly_metric.tail(24).copy()

        if metric_key == "temp" and "temp_avg" in forecast_df.columns:
            daily_view = forecast_df[["timestamp", "temp_avg"]].rename(columns={"temp_avg": "value"}).dropna().tail(4).copy()
        elif metric_key in forecast_df.columns:
            daily_view = forecast_df[["timestamp", metric_key]].rename(columns={metric_key: "value"}).dropna().tail(4).copy()
        else:
            daily_view = (
                metric_source.set_index("timestamp")[[metric_key]]
                .resample("1D")
                .mean()
                .dropna()
                .reset_index()
                .rename(columns={metric_key: "value"})
                .tail(4)
                .copy()
            )

        if hourly_view.empty or daily_view.empty:
            st.info("Chưa đủ dữ liệu để dựng phần dự báo theo giờ/hằng ngày.")
        else:
            scope_name = selected_location if selected_location != f"Tổng quan ({selected_city})" else selected_city

            hour_items = []
            for i, row in enumerate(hourly_view.itertuples(index=False)):
                ts = pd.to_datetime(row.timestamp)
                val = float(getattr(row, metric_key))
                level, col_bg, col_fg, _ = _weather_level(val)
                hour_label = "Bây giờ" if i == len(hourly_view) - 1 else ts.strftime("%H:%M")
                day_label = ts.strftime("Th %w") if ts.weekday() != 6 else "CN"
                hour_items.append(
                    f"<div style='min-width:76px;text-align:center;'>"
                    f"<div style='font-size:11px;color:#64748b;font-weight:700;'>{day_label}</div>"
                    f"<div style='font-size:12px;color:#64748b;margin:4px 0 8px;'>{hour_label}</div>"
                    f"<div style='display:inline-block;background:{col_bg};color:{col_fg};padding:4px 10px;border-radius:7px;font-size:14px;font-weight:800;'>{val:.0f}{metric_unit}</div>"
                    f"<div style='font-size:10px;color:#64748b;margin-top:5px;'>{level}</div>"
                    "</div>"
                )

            st.markdown(
                f"""
                <div class='wx-analysis-card'>
                    <div style='font-size:34px;font-weight:800;color:#0f172a;line-height:1.0;'>Dự báo {metric_label} theo giờ</div>
                    <div style='margin-top:6px;color:#64748b;font-size:14px;'>Khu vực: <b style='color:#334155'>{escape(str(scope_name))}</b></div>
                    <div style='margin-top:14px;display:flex;overflow-x:auto;gap:12px;padding-bottom:8px;'>
                        {''.join(hour_items)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c_daily, c_advice = st.columns([1.6, 1.0], gap="small")
            with c_daily:
                rows = []
                for idx, row in enumerate(daily_view.itertuples(index=False)):
                    d = pd.to_datetime(row.timestamp)
                    val = float(row.value)
                    label, col_bg, col_fg, _ = _weather_level(val)
                    day_name = "Hôm nay" if idx == len(daily_view) - 1 else _weekday_vi(d)
                    row_bg = "#ffffff" if idx % 2 == 0 else "#f8fafc"
                    rows.append(
                        f"<div style='display:flex;align-items:center;padding:12px 16px;background:{row_bg};border-bottom:1px solid #eef2f7;'>"
                        f"<div style='width:90px;font-weight:700;color:#334155;'>{day_name}</div>"
                        f"<div style='width:86px;'><span style='display:inline-block;background:{col_bg};color:{col_fg};padding:4px 12px;border-radius:7px;font-weight:800;'>{val:.0f}{metric_unit}</span></div>"
                        f"<div style='flex:1;color:#334155;font-weight:600;'>{label}</div>"
                        f"<div style='width:100px;text-align:right;color:#64748b;font-size:12px;'>{d.strftime('%d/%m/%Y')}</div>"
                        "</div>"
                    )

                st.markdown(
                    f"""
                    <div class='wx-analysis-card' style='padding:0;overflow:hidden;'>
                        <div style='padding:14px 16px 10px;'>
                            <div style='font-size:36px;font-weight:800;color:#0f172a;line-height:1.0;'>Dự báo {metric_label} hằng ngày</div>
                            <div style='margin-top:4px;color:#64748b;'>Dự báo tại {escape(str(scope_name))} trong {len(daily_view)} ngày tới</div>
                        </div>
                        {''.join(rows)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c_advice:
                avg_val = float(daily_view["value"].mean())
                advice_label, advice_bg, advice_fg, advice_desc = _weather_level(avg_val)
                st.markdown(
                    f"""
                    <div class='wx-analysis-card' style='border:1.5px solid {advice_bg};background:{advice_fg}10;'>
                        <div style='font-size:26px;font-weight:800;color:{advice_bg};line-height:1.1;'>KHUYẾN CÁO THỜI TIẾT</div>
                        <div style='margin-top:14px;display:flex;align-items:center;gap:10px;'>
                            <div style='width:12px;height:12px;border-radius:50%;background:{advice_bg};'></div>
                            <div style='font-size:40px;font-weight:900;color:#0f172a;line-height:1.0;'>{advice_label}</div>
                        </div>
                        <div style='margin-top:14px;color:#334155;font-size:15px;line-height:1.55;font-weight:500;'>
                            {advice_desc}
                        </div>
                        <div style='margin-top:16px;padding-top:10px;border-top:1px dashed {advice_bg};font-size:12px;color:#64748b;font-style:italic;'>
                            * Khuyến cáo dựa trên giá trị trung bình phần dự báo theo thông số đã chọn.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # Data coverage footer
    coverage_cols = [c for c in WEATHER_FEATURES if c in city_df.columns]
    if coverage_cols:
        coverage = (city_df[coverage_cols].notna().mean() * 100).sort_values(ascending=False)
        coverage_text = " | ".join([f"{k}: {v:.1f}%" for k, v in coverage.items()])
        st.caption(f"Độ phủ dữ liệu: {coverage_text}")
