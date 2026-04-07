import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os
from datetime import datetime
import base64
import textwrap

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return None

logo_base64 = get_base64_image("data/hcmus_logo.png")
if logo_base64:
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="width:100%;height:100%;object-fit:contain;padding:2px;">'
else:
    logo_html = "🌿"

# ═══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════
st.set_page_config(layout="wide", page_title="Vietnam AQI Dashboard",
                   page_icon="data/hcmus_logo.png", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700&display=swap');
:root {
    --pri-900: #102844;
    --pri-800: #173a5e;
    --pri-700: #1f4f7d;
    --pri-500: #0ea5e9;
    --pri-300: #7dd3fc;
    --acc-500: #f59e0b;
    --acc-600: #ea580c;
    --bg-050: #f5f9fc;
    --ink-700: #334155;
    --ink-500: #64748b;
    --line-200: #dbe7f2;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] { font-family: 'Be Vietnam Pro', sans-serif !important; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding: 3.1rem 0 0 !important; max-width: 100% !important; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

/* ═══════════════════════════════════
   SIDEBAR REDESIGN
═══════════════════════════════════ */

/* Sidebar container */
[data-testid="stSidebar"] {
    background: var(--pri-900) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    padding: 0 !important;
    min-width: 270px !important;
    max-width: 270px !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
    background: var(--pri-900) !important;
}

/* Sidebar scrollbar */
[data-testid="stSidebar"] ::-webkit-scrollbar { width: 3px; }
[data-testid="stSidebar"] ::-webkit-scrollbar-track { background: transparent; }
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }

/* Hide default Streamlit labels inside sidebar */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stDateInput label,
[data-testid="stSidebar"] .stSlider label {
    display: none !important;
}

/* Sidebar multiselect chips */
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
    background: rgba(14,165,233,0.24) !important;
    border: 1px solid rgba(14,165,233,0.48) !important;
    border-radius: 4px !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] span {
    color: #bfdbfe !important;
    font-size: 11px !important;
}

/* Multiselect input box */
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"]:hover {
    border-color: rgba(14,165,233,0.6) !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] input {
    color: #e2e8f0 !important;
    font-family: 'Be Vietnam Pro', sans-serif !important;
    font-size: 12px !important;
}

/* Date input */
[data-testid="stSidebar"] .stDateInput input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'Be Vietnam Pro', sans-serif !important;
    font-size: 12px !important;
    padding: 8px 10px !important;
}
[data-testid="stSidebar"] .stDateInput input:focus {
    border-color: rgba(14,165,233,0.7) !important;
    box-shadow: 0 0 0 2px rgba(14,165,233,0.15) !important;
}

/* Dropdown popover (city list) */
[data-testid="stSidebar"] [data-baseweb="popover"] {
    background: var(--pri-800) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-baseweb="menu"] li {
    color: #cbd5e1 !important;
    font-size: 12px !important;
    font-family: 'Be Vietnam Pro', sans-serif !important;
}
[data-testid="stSidebar"] [data-baseweb="menu"] li:hover {
    background: rgba(14,165,233,0.2) !important;
}

/* Warning text */
[data-testid="stSidebar"] .stWarning {
    background: rgba(217,119,6,0.15) !important;
    border: 1px solid rgba(217,119,6,0.3) !important;
    border-radius: 8px !important;
    color: #fcd34d !important;
    font-size: 12px !important;
}

/* ── HEADER ── */
.hdr {
    background: var(--pri-800);
    padding: 12px 24px;
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
}
.hdr-left { display: flex; align-items: center; gap: 14px; }
.hdr-logo {
    width: 48px; height: 48px;
    background: rgba(255,255,255,0.12);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    border: 1px solid rgba(255,255,255,0.2);
}
.hdr-school { font-size: 0.62rem; color: #93afc9; line-height: 1.5; }
.hdr-title  { font-size: 1.05rem; font-weight: 700; color: #ffffff; line-height: 1.3; }
.hdr-sub    { font-size: 0.65rem; color: #7da4c0; margin-top: 2px; }
.hdr-right  { display: flex; align-items: center; gap: 20px; flex-shrink: 0; }
.hdr-stat   { text-align: right; }
.hdr-stat-val { font-size: 1.1rem; font-weight: 700; color: #ffffff; line-height: 1; }
.hdr-stat-lbl { font-size: 0.6rem; color: #7da4c0; margin-top: 3px; text-transform: uppercase; letter-spacing: .5px; }
.hdr-badge {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 8px; padding: 8px 18px; text-align: center;
}
.hdr-badge-val { font-size: 1.6rem; font-weight: 800; line-height: 1; }
.hdr-badge-lbl { font-size: 0.6rem; color: #93afc9; text-transform: uppercase; letter-spacing: .5px; }

/* ── MAIN ── */
.main-wrap { padding: 12px 16px; background: #f8fafc; }

/* ── KPI STRIP ── */
.kpi-strip { display: grid; grid-template-columns: repeat(5,1fr); gap: 10px; margin-bottom: 12px; }
.kpi-box {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-top: 3px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 14px;
}
.kpi-box.accent-blue  { border-top-color: #2563eb; }
.kpi-box.accent-amber { border-top-color: #f59e0b; }
.kpi-box.accent-red   { border-top-color: #ea580c; }
.kpi-box.accent-slate { border-top-color: #0ea5e9; }
.kpi-lbl { font-size: .63rem; font-weight: 600; text-transform: uppercase; letter-spacing: .7px; color: #64748b; margin-bottom: 5px; }
.kpi-val { font-size: 1.5rem; font-weight: 700; color: #1e293b; line-height: 1; }
.kpi-val .u { font-size: .72rem; font-weight: 400; color: #64748b; }
.kpi-sub { font-size: .62rem; color: #94a3b8; margin-top: 4px; }

/* ── CARD ── */
.card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px 10px; height: 100%; }
.card-title { font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .7px; color: #334155; margin-bottom: 4px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px; }
.card-sub { font-size: .62rem; color: #64748b; margin-bottom: 6px; line-height: 1.4; }
.card { transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08); border-color: #bfdbfe; }
.q-tag {
    display: inline-block;
    background: #e0f2fe; color: #0369a1;
    font-size: .58rem; font-weight: 700; letter-spacing: .8px;
    text-transform: uppercase; padding: 1px 6px; border-radius: 4px; margin-right: 4px;
}

/* ── POLLUTANT MINI GRID ── */
.poll-mini-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 6px; margin-bottom: 8px; }
.poll-mini {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
    padding: 7px 8px; text-align: center;
}
.pm-rank { font-size: .6rem; font-weight: 700; color: #94a3b8; margin-bottom: 2px; }
.pm-name { font-size: .62rem; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: .5px; }
.pm-val  { font-size: 1.05rem; font-weight: 700; line-height: 1.3; color: #1e293b; }

/* ── WHO BAR ── */
.who-row { display: flex; align-items: center; gap: 6px; margin-top: 5px; }
.who-lbl { font-size: .62rem; color: #334155; font-weight: 600; width: 34px; }
.who-bar-bg { flex: 1; height: 5px; background: #f1f5f9; border-radius: 3px; overflow: hidden; }
.who-bar-fg { height: 100%; border-radius: 3px; }
.who-pct { font-size: .62rem; font-weight: 700; width: 34px; text-align: right; }

/* ── INSIGHT ROW ── */
.ins-row { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; margin-top: 12px; }
.ins-item {
    background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;
    padding: 12px 14px; border-left: 3px solid;
}
.ins-item.ins-red    { border-left-color: #dc2626; }
.ins-item.ins-amber  { border-left-color: #f59e0b; }
.ins-item.ins-blue   { border-left-color: #0ea5e9; }
.ins-tag { font-size: .6rem; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; margin-bottom: 5px; }
.ins-tag.t-red   { color: #dc2626; }
.ins-tag.t-amber { color: #b45309; }
.ins-tag.t-blue  { color: #0369a1; }
.ins-body { font-size: .78rem; color: #1e293b; line-height: 1.55; }
.ins-foot { font-size: .65rem; color: #64748b; margin-top: 5px; padding-top: 5px; border-top: 1px solid #f1f5f9; }

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; background: #f8fafc; border-bottom: 1px solid #e2e8f0; padding: 0 8px;
}
.stTabs [data-baseweb="tab"] {
    height: 34px; font-size: .72rem; font-weight: 600; color: #475569;
    border-radius: 0; padding: 0 16px; background: transparent !important;
    border-bottom: 2px solid transparent;
}
.stTabs [aria-selected="true"] { color: #1e3a5f !important; border-bottom: 2px solid #1e3a5f !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 12px 0 0 !important; }

/* ── FOOTER ── */
.ftr { background: var(--pri-800); padding: 8px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; }
.ftr-txt { font-size: .63rem; color: #7da4c0; }
.ftr-grp { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.ftr-member { background: rgba(255,255,255,.08); border-radius: 4px; padding: 2px 8px; font-size: .6rem; color: #93afc9; }
.ftr-marquee {
    width: min(760px, 100%);
    overflow: hidden;
    position: relative;
    border-radius: 6px;
}
.ftr-track {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    width: max-content;
    will-change: transform;
    animation: ftr-scroll 24s linear infinite;
}
.ftr-track:hover { animation-play-state: paused; }
@keyframes ftr-scroll {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
@media (max-width: 980px) {
    .ftr { padding: 8px 12px; }
    .ftr-txt { width: 100%; }
    .ftr-marquee { width: 100%; }
}

/* ════════════════════════════════
   SIDEBAR CUSTOM COMPONENTS
════════════════════════════════ */
.sb-header {
    background: linear-gradient(135deg, var(--pri-800) 0%, var(--pri-900) 100%);
    padding: 20px 18px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}
.sb-logo-row {
    display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
}
.sb-logo-circle {
    width: 36px; height: 36px;
    background: rgba(14,165,233,0.2);
    border: 1px solid rgba(14,165,233,0.4);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0;
}
.sb-title { font-size: .8rem; font-weight: 700; color: #f1f5f9; line-height: 1.3; }
.sb-subtitle { font-size: .6rem; color: #64748b; margin-top: 2px; letter-spacing: .3px; }
.sb-stats-row {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 8px; margin-top: 4px;
}
.sb-stat-box {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 8px 10px;
    text-align: center;
}
.sb-stat-num { font-size: 1.2rem; font-weight: 700; color: #ffffff; line-height: 1; }
.sb-stat-lbl { font-size: .56rem; color: #64748b; text-transform: uppercase; letter-spacing: .6px; margin-top: 3px; }

.sb-section {
    padding: 14px 18px 0;
}
.sb-section-hd {
    display: flex; align-items: center; gap: 7px;
    margin-bottom: 10px;
}
.sb-section-dot {
    width: 3px; height: 14px;
    background: var(--pri-500); border-radius: 2px; flex-shrink: 0;
}
.sb-section-lbl {
    font-size: .6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .9px; color: #64748b;
}
.sb-section-badge {
    margin-left: auto;
    background: rgba(14,165,233,0.2);
    border: 1px solid rgba(14,165,233,0.35);
    border-radius: 10px; padding: 1px 7px;
    font-size: .58rem; font-weight: 700; color: #93c5fd;
}

.sb-date-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
.sb-date-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 8px 10px; cursor: pointer;
    transition: border-color .2s, background .2s;
}
.sb-date-card:hover { background: rgba(255,255,255,0.07); border-color: rgba(37,99,235,0.5); }
.sb-date-mini { font-size: .55rem; color: #64748b; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 2px; }
.sb-date-val { font-size: .78rem; font-weight: 600; color: #e2e8f0; }

.sb-quick-pills { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 4px; }
.sb-pill {
    font-size: .6rem; font-weight: 600; padding: 4px 9px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(255,255,255,0.04);
    color: #94a3b8; cursor: pointer; transition: all .18s;
    font-family: 'Be Vietnam Pro', sans-serif;
    letter-spacing: .2px;
}
.sb-pill:hover { border-color: rgba(14,165,233,0.45); color: #bae6fd; background: rgba(14,165,233,0.12); }
.sb-pill.active { background: #0284c7; border-color: #0284c7; color: #ffffff; }

.sb-divider {
    height: 1px; margin: 14px 18px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08) 30%, rgba(255,255,255,0.08) 70%, transparent);
}

.sb-city-search-wrap { position: relative; margin-bottom: 8px; }
.sb-city-search-icon {
    position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
    width: 13px; height: 13px; color: #475569; pointer-events: none;
}
.sb-city-search {
    width: 100%;
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    padding: 7px 10px 7px 28px !important;
    font-family: 'Be Vietnam Pro', sans-serif !important;
    font-size: 12px !important;
    color: #e2e8f0 !important;
    outline: none;
    transition: border-color .2s;
}
.sb-city-search:focus { border-color: rgba(37,99,235,0.6) !important; }
.sb-city-search::placeholder { color: #475569; }

.sb-city-actions { display: flex; gap: 5px; margin-bottom: 8px; }
.sb-city-act {
    font-family: 'Be Vietnam Pro', sans-serif;
    font-size: .58rem; font-weight: 600; letter-spacing: .3px;
    padding: 4px 9px; border-radius: 5px;
    border: 1px solid rgba(255,255,255,0.1);
    background: transparent; color: #64748b;
    cursor: pointer; transition: all .15s;
    text-transform: uppercase;
}
.sb-city-act:hover { background: rgba(255,255,255,0.06); color: #94a3b8; }

.sb-footer {
    padding: 14px 18px 18px;
    border-top: 1px solid rgba(255,255,255,0.06);
    margin-top: 6px;
}
.sb-apply-btn {
    width: 100%;
    background: linear-gradient(135deg, #0ea5e9, #0284c7);
    border: none; border-radius: 9px;
    padding: 11px 0;
    font-family: 'Be Vietnam Pro', sans-serif;
    font-size: .72rem; font-weight: 700;
    color: #ffffff; cursor: pointer;
    letter-spacing: .5px; text-transform: uppercase;
    transition: all .2s;
    box-shadow: 0 4px 14px rgba(14,165,233,0.28);
}
.sb-apply-btn:hover { background: linear-gradient(135deg, #0284c7, #0369a1); box-shadow: 0 6px 20px rgba(14,165,233,0.4); }
.sb-reset-btn {
    width: 100%; margin-top: 6px;
    background: transparent;
    border: 1px solid rgba(255,255,255,0.1); border-radius: 9px;
    padding: 8px 0;
    font-family: 'Be Vietnam Pro', sans-serif;
    font-size: .65rem; font-weight: 600;
    color: #64748b; cursor: pointer;
    letter-spacing: .3px;
    transition: all .2s;
}
.sb-reset-btn:hover { border-color: rgba(255,255,255,0.2); color: #94a3b8; }

.sb-aqi-band-row { display: flex; gap: 4px; margin-bottom: 10px; }
.sb-aqi-band {
    flex: 1; padding: 5px 2px; border-radius: 6px;
    text-align: center; cursor: pointer;
    font-size: .55rem; font-weight: 700;
    letter-spacing: .3px; text-transform: uppercase;
    transition: opacity .15s, transform .1s;
    border: 1px solid transparent;
}
.sb-aqi-band:hover { transform: translateY(-1px); }
.sb-aqi-band.dim { opacity: 0.25; }

.sb-info-strip {
    background: rgba(14,165,233,0.09);
    border: 1px solid rgba(14,165,233,0.2);
    border-radius: 8px; padding: 8px 10px;
    margin: 10px 18px 0;
    display: flex; gap: 8px; align-items: flex-start;
}
.sb-info-icon { font-size: 13px; flex-shrink: 0; margin-top: 1px; }
.sb-info-txt { font-size: .6rem; color: #7da4c0; line-height: 1.5; }

.sb-filter-card {
    margin: 10px 18px 0;
    background: rgba(14,165,233,0.09);
    border: 1px solid rgba(14,165,233,0.24);
    border-radius: 10px;
    padding: 9px 10px;
}
.sb-filter-title {
    font-size: .58rem;
    font-weight: 700;
    color: #bae6fd;
    text-transform: uppercase;
    letter-spacing: .6px;
    margin-bottom: 4px;
}
.sb-filter-line {
    font-size: .61rem;
    color: #c7d9ea;
    line-height: 1.45;
}

.sb-chip-wrap { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
.sb-chip {
    display: inline-flex;
    align-items: center;
    height: 20px;
    padding: 0 8px;
    border-radius: 999px;
    background: rgba(14,165,233,0.18);
    border: 1px solid rgba(14,165,233,0.36);
    color: #dbeafe;
    font-size: .58rem;
    font-weight: 700;
}

[data-testid="stSidebar"] .stButton > button {
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.14);
    background: rgba(255,255,255,0.05);
    color: #dbeafe;
    font-size: .67rem;
    font-weight: 700;
    min-height: 34px;
}
[data-testid="stSidebar"] .stButton > button:hover {
    border-color: rgba(125, 211, 252, 0.55);
    color: #e0f2fe;
}
[data-testid="stSidebar"] .stExpander {
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    background: rgba(255,255,255,0.03);
}
[data-testid="stSidebar"] .stExpander summary {
    font-size: .72rem;
    color: #cbd5e1;
    font-weight: 700;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
    display: none;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] > div {
    min-height: 38px;
    max-height: 38px;
    overflow: hidden;
    padding-right: 28px;
}

/* ── IQAIR-HYBRID STRIP ── */
.iq-wrap {
    background: linear-gradient(120deg, #f7fbff 0%, #fffaf0 55%, #fff5f5 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 12px;
}
.iq-live-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;
    flex-wrap: wrap;
}
.iq-title {
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .8px;
    text-transform: uppercase;
    color: #0f172a;
}
.iq-meta {
    font-size: .62rem;
    color: #475569;
}
.iq-grid {
    display: grid;
    grid-template-columns: 1.2fr 1fr 1fr;
    gap: 10px;
}
.iq-card {
    background: rgba(255,255,255,0.92);
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px;
}
.iq-card-hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #0c4a6e 100%);
    border-color: rgba(255,255,255,0.2);
}
.iq-hero-kicker {
    font-size: .58rem;
    letter-spacing: .7px;
    text-transform: uppercase;
    color: #93c5fd;
    font-weight: 700;
}
.iq-hero-row {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin: 5px 0 2px;
}
.iq-hero-aqi {
    font-size: 2.05rem;
    font-weight: 800;
    line-height: 1;
}
.iq-hero-status {
    font-size: .72rem;
    font-weight: 700;
    color: #e2e8f0;
}
.iq-hero-sub {
    font-size: .64rem;
    color: #cbd5e1;
    line-height: 1.5;
}
.iq-chip-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 8px;
}
.iq-chip {
    border: 1px solid rgba(255,255,255,0.2);
    background: rgba(255,255,255,0.08);
    border-radius: 999px;
    padding: 2px 8px;
    font-size: .58rem;
    color: #e2e8f0;
    font-weight: 700;
}
.iq-card-title {
    font-size: .63rem;
    font-weight: 800;
    color: #334155;
    letter-spacing: .6px;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.iq-rank-row {
    display: grid;
    grid-template-columns: 22px 1fr auto;
    gap: 8px;
    align-items: center;
    border-bottom: 1px dashed #e2e8f0;
    padding: 6px 0;
}
.iq-rank-row:last-child { border-bottom: none; padding-bottom: 1px; }
.iq-rank-no {
    width: 22px;
    height: 22px;
    border-radius: 999px;
    background: #0f172a;
    color: #ffffff;
    font-size: .58rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
}
.iq-rank-city {
    font-size: .69rem;
    color: #1e293b;
    font-weight: 600;
}
.iq-rank-aqi {
    font-size: .7rem;
    font-weight: 800;
}
.iq-rank-pm {
    font-size: .56rem;
    color: #64748b;
}
.iq-health-box {
    margin-top: 8px;
    border-left: 3px solid;
    border-radius: 7px;
    padding: 6px 8px;
    background: rgba(255,255,255,0.08);
}
.iq-health-hd {
    font-size: .62rem;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 2px;
}
.iq-health-tx {
    font-size: .6rem;
    color: #cbd5e1;
    line-height: 1.45;
}
.trend-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1.2fr;
    gap: 10px;
    margin-bottom: 12px;
}
.trend-card {
    background: #ffffff;
    border: 1px solid #dbe7f2;
    border-radius: 10px;
    padding: 10px 11px;
}
.trend-kicker {
    font-size: .58rem;
    letter-spacing: .7px;
    text-transform: uppercase;
    color: #64748b;
    font-weight: 700;
    margin-bottom: 4px;
}
.trend-main {
    font-size: 1.15rem;
    font-weight: 800;
    line-height: 1.15;
}
.trend-sub {
    margin-top: 3px;
    font-size: .63rem;
    color: #64748b;
}
.trend-rank-line {
    font-size: .66rem;
    color: #334155;
    line-height: 1.45;
    margin-top: 3px;
}
@media (max-width: 1100px) {
    .iq-grid { grid-template-columns: 1fr; }
    .trend-grid { grid-template-columns: 1fr; }
}

/* ════════════════════════════════
   SIDEBAR WHITE MODE + COLLAPSE FIX
════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
    box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.05), 0 12px 28px rgba(15, 23, 42, 0.06) !important;
    transition: min-width .2s ease, max-width .2s ease, width .2s ease !important;
}
section[data-testid="stSidebar"] > div:first-child {
    background: #ffffff !important;
}
section[data-testid="stSidebar"][aria-expanded="true"] {
    min-width: 290px !important;
    max-width: 290px !important;
}
section[data-testid="stSidebar"][aria-expanded="false"] {
    min-width: 0 !important;
    max-width: 0 !important;
    width: 0 !important;
    border-right: 0 !important;
    box-shadow: none !important;
    overflow: hidden !important;
}
section[data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
    min-width: 0 !important;
    max-width: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
}
[data-testid="stSidebarCollapsedControl"] {
    border: 1px solid #dbe3ee !important;
    border-radius: 10px !important;
    background: #ffffff !important;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.1) !important;
}

[data-testid="stSidebar"] ::-webkit-scrollbar-track { background: #f8fafc !important; }
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background: #cbd5e1 !important; }

[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"],
[data-testid="stSidebar"] .stDateInput input,
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
    background: #ffffff !important;
    border: 1px solid #dbe3ee !important;
    color: #0f172a !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] input,
[data-testid="stSidebar"] .stDateInput input {
    color: #0f172a !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"]:hover,
[data-testid="stSidebar"] .stDateInput input:hover {
    border-color: #93c5fd !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
    background: #eff6ff !important;
    border: 1px solid #bfdbfe !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] span {
    color: #1d4ed8 !important;
}
[data-testid="stSidebar"] [data-baseweb="popover"],
[data-testid="stSidebar"] [data-baseweb="menu"] {
    background: #ffffff !important;
    border: 1px solid #dbe3ee !important;
}
[data-testid="stSidebar"] [data-baseweb="menu"] li {
    color: #1e293b !important;
}
[data-testid="stSidebar"] [data-baseweb="menu"] li:hover {
    background: #f1f5f9 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #ffffff !important;
    border: 1px solid #dbe3ee !important;
    color: #334155 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    border-color: #93c5fd !important;
    color: #1e40af !important;
    background: #f8fbff !important;
}
[data-testid="stSidebar"] .stExpander {
    background: #ffffff !important;
    border: 1px solid #dbe3ee !important;
}
[data-testid="stSidebar"] .stExpander summary {
    color: #334155 !important;
}

.sb-header {
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
    border-bottom: 1px solid #e2e8f0 !important;
}
.sb-logo-circle {
    background: #eff6ff !important;
    border: 1px solid #bfdbfe !important;
}
.sb-title { color: #0f172a !important; }
.sb-subtitle { color: #64748b !important; }
.sb-stat-box {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
}
.sb-stat-num { color: #0f172a !important; }
.sb-stat-lbl { color: #64748b !important; }
.sb-section-lbl { color: #475569 !important; }
.sb-divider {
    background: linear-gradient(90deg, transparent, rgba(148,163,184,0.28) 30%, rgba(148,163,184,0.28) 70%, transparent) !important;
}
.sb-filter-card {
    background: #f8fbff !important;
    border: 1px solid #dbeafe !important;
}
.sb-filter-title { color: #1d4ed8 !important; }
.sb-filter-line { color: #334155 !important; }
.sb-chip {
    background: #eff6ff !important;
    border: 1px solid #bfdbfe !important;
    color: #1e40af !important;
}
.sb-info-strip {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
}
.sb-info-txt { color: #334155 !important; }

/* Sidebar classes from requested template - premium override */
[data-testid="stSidebar"] .sidebar-header-card {
    background:
        radial-gradient(120px 70px at 100% -5%, rgba(14,165,233,.16), transparent 70%),
        linear-gradient(160deg, #ffffff 0%, #f7fbff 65%, #f3f8ff 100%);
    border: 1px solid #d7e4f1;
    border-radius: 16px;
    padding: 12px;
    margin-bottom: 12px;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}
[data-testid="stSidebar"] .sidebar-header-title {
    margin: 0;
    font-size: 1rem;
    letter-spacing: .3px;
    color: #0f2940;
    font-weight: 800;
}
[data-testid="stSidebar"] .sidebar-header-sub {
    margin: 4px 0 10px;
    font-size: .76rem;
    color: #4f6b86;
    line-height: 1.45;
}
[data-testid="stSidebar"] .sidebar-hero-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}
[data-testid="stSidebar"] .hero-pill {
    border: 1px solid #d7e8f7;
    background: #ffffff;
    border-radius: 12px;
    padding: 6px 8px;
    text-align: center;
}
[data-testid="stSidebar"] .hero-pill span {
    display: block;
    color: #0b4f86;
    font-size: .95rem;
    line-height: 1.1;
    font-weight: 800;
}
[data-testid="stSidebar"] .hero-pill small {
    display: block;
    margin-top: 2px;
    color: #607b96;
    font-size: .62rem;
    text-transform: uppercase;
    letter-spacing: .6px;
    font-weight: 700;
}
[data-testid="stSidebar"] .sidebar-section-title {
    font-size: .76rem;
    text-transform: uppercase;
    letter-spacing: .75px;
    color: #355673;
    font-weight: 800;
    margin: 10px 0 6px;
    padding-left: 10px;
    position: relative;
}
[data-testid="stSidebar"] .sidebar-section-title::before {
    content: "";
    position: absolute;
    left: 0;
    top: 2px;
    width: 4px;
    height: 14px;
    border-radius: 3px;
    background: linear-gradient(180deg, #0ea5e9, #2563eb);
}
[data-testid="stSidebar"] .sidebar-selection-summary {
    background: #ffffff;
    border: 1px solid #d7e4f1;
    border-radius: 12px;
    padding: 9px 10px 7px 10px;
    margin-top: 4px;
    margin-bottom: 8px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.85);
}
[data-testid="stSidebar"] .summary-count {
    font-size: .74rem;
    color: #3f5f7c;
    margin-bottom: 6px;
    font-weight: 700;
}
[data-testid="stSidebar"] .mini-city-chip {
    display: inline-block;
    margin-right: 5px;
    margin-bottom: 5px;
    padding: 2px 8px;
    font-size: .66rem;
    border-radius: 999px;
    border: 1px solid #c5dcf2;
    color: #0b4f86;
    background: #eef6fd;
    font-weight: 700;
}
[data-testid="stSidebar"] .sidebar-hint {
    font-size: .72rem;
    color: #4c6a86;
    margin-top: 2px;
    margin-bottom: 4px;
}

[data-testid="stSidebar"] .stButton > button {
    border-radius: 10px !important;
    border: 1px solid #c7dbef !important;
    background: linear-gradient(180deg, #ffffff 0%, #f5faff 100%) !important;
    color: #18466f !important;
    font-weight: 700 !important;
    min-height: 38px !important;
    transition: all .18s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    border-color: #88bee8 !important;
    color: #0b5b9a !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.12) !important;
    transform: translateY(-1px);
}
[data-testid="stSidebar"] .stExpander {
    border: 1px solid #d7e4f1 !important;
    border-radius: 12px !important;
    background: #ffffff !important;
}
[data-testid="stSidebar"] .stExpander summary {
    color: #0f4f82 !important;
    font-size: .8rem !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"],
[data-testid="stSidebar"] .stDateInput > div > div {
    border-radius: 10px !important;
    border: 1px solid #d3e2f0 !important;
    background: #ffffff !important;
}
[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] > div > div:nth-child(1) {
    background: #dbeafe !important;
}
[data-testid="stSidebar"] .stSlider [role="slider"] {
    box-shadow: 0 0 0 3px rgba(14,165,233,.15) !important;
    border: 1px solid #7dd3fc !important;
}
[data-testid="stSidebar"] [data-testid="stNotificationContentSuccess"] {
    border: 1px solid #c9e7d6 !important;
    background: #f0fdf4 !important;
    color: #166534 !important;
    border-radius: 10px !important;
}

@media (max-width: 1100px) {
    section[data-testid="stSidebar"][aria-expanded="true"] {
        min-width: 100% !important;
        max-width: 100% !important;
    }
}

/* ════════════════════════════════
   MODERN VISUAL REFRESH
   Inspired by IQAir clarity + Linear density + Stripe depth
════════════════════════════════ */
:root {
    --ux-bg-0: #f3f7fb;
    --ux-bg-1: #eef4ff;
    --ux-bg-2: #fffdf8;
    --ux-card: rgba(255,255,255,0.88);
    --ux-card-solid: #ffffff;
    --ux-border: rgba(148, 163, 184, 0.24);
    --ux-border-soft: rgba(148, 163, 184, 0.18);
    --ux-ink: #0f172a;
    --ux-sub: #5b7089;
    --ux-pri: #0ea5e9;
    --ux-pri-deep: #0369a1;
    --ux-warm: #f59e0b;
    --ux-shadow: 0 18px 42px rgba(15, 23, 42, 0.09);
}

.stApp {
    background:
        radial-gradient(1200px 420px at 8% -10%, rgba(14,165,233,0.18), transparent 65%),
        radial-gradient(920px 380px at 92% 3%, rgba(245,158,11,0.14), transparent 62%),
        linear-gradient(180deg, var(--ux-bg-1) 0%, var(--ux-bg-0) 45%, #f8fbff 100%) !important;
}

.block-container {
    padding-top: 2.2rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

.hdr {
    position: sticky;
    top: 0;
    z-index: 20;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.5);
    background:
        linear-gradient(140deg, rgba(11,37,64,0.9) 0%, rgba(17,58,93,0.88) 60%, rgba(12,79,134,0.82) 100%) !important;
    box-shadow: 0 16px 40px rgba(2, 6, 23, 0.22);
    backdrop-filter: blur(7px);
    -webkit-backdrop-filter: blur(7px);
    margin-bottom: 10px;
}

.hdr-title {
    font-size: 1.15rem;
    letter-spacing: .1px;
}

.hdr-sub,
.hdr-school,
.hdr-stat-lbl,
.hdr-badge-lbl {
    color: #b7cce0 !important;
}

.main-wrap {
    background: transparent !important;
    padding: 4px 4px 10px;
}

.kpi-strip {
    gap: 12px;
}

.kpi-box,
.trend-card,
.card,
.iq-wrap,
.ins-item {
    background: var(--ux-card) !important;
    border: 1px solid var(--ux-border) !important;
    box-shadow: var(--ux-shadow);
}

.kpi-box,
.trend-card,
.card,
.ins-item {
    position: relative;
    overflow: hidden;
}

.kpi-box::before,
.trend-card::before,
.card::before,
.ins-item::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(125deg, rgba(14,165,233,0.055), transparent 46%, rgba(245,158,11,0.045));
    pointer-events: none;
}

.card-title {
    color: var(--ux-ink);
    font-size: .72rem;
}

.card-sub,
.kpi-sub,
.trend-sub,
.iq-meta,
.ins-foot {
    color: var(--ux-sub) !important;
}

.kpi-lbl,
.trend-kicker,
.ins-tag {
    letter-spacing: .82px;
}

.kpi-val,
.trend-main,
.iq-hero-aqi {
    color: var(--ux-ink);
    text-shadow: 0 1px 0 rgba(255,255,255,0.45);
}

.iq-wrap {
    border-radius: 14px;
    background:
        radial-gradient(130px 80px at 6% -8%, rgba(14,165,233,0.12), transparent 70%),
        radial-gradient(190px 88px at 100% 0%, rgba(245,158,11,0.11), transparent 72%),
        var(--ux-card) !important;
}

.iq-card {
    border: 1px solid var(--ux-border-soft);
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.07);
}

.iq-card-hero {
    background: linear-gradient(138deg, #0f172a 0%, #102d49 54%, #0b5b9a 100%) !important;
    border-color: rgba(255,255,255,0.2) !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 0 !important;
    gap: 10px;
    padding: 2px 0 8px !important;
}

.stTabs [data-baseweb="tab"] {
    height: 36px;
    border-radius: 999px;
    padding: 0 16px;
    border: 1px solid var(--ux-border-soft);
    background: rgba(255,255,255,0.58) !important;
    color: #35516d;
    font-size: .7rem;
    font-weight: 700;
    transition: all .2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    border-color: rgba(14,165,233,0.38);
    color: #0f4f82;
    transform: translateY(-1px);
}

.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    border-color: transparent !important;
    background: linear-gradient(140deg, #0ea5e9 0%, #2563eb 100%) !important;
    box-shadow: 0 9px 20px rgba(37, 99, 235, 0.26);
}

section[data-testid="stSidebar"] {
    border-right: 1px solid rgba(148,163,184,0.22) !important;
    background:
        radial-gradient(180px 86px at 100% -2%, rgba(14,165,233,.1), transparent 74%),
        linear-gradient(180deg, #ffffff 0%, #f8fbff 56%, #f5f9ff 100%) !important;
}

[data-testid="stSidebar"] .sidebar-header-card,
[data-testid="stSidebar"] .sidebar-selection-summary,
[data-testid="stSidebar"] .stExpander {
    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.06) !important;
}

[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"],
[data-testid="stSidebar"] .stDateInput > div > div {
    min-height: 37px !important;
    border-radius: 11px !important;
}

[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(180deg, #ffffff 0%, #f4f9ff 100%) !important;
}

.ftr {
    border-radius: 12px;
    margin-top: 12px;
    background: linear-gradient(140deg, rgba(11,37,64,0.96) 0%, rgba(14,57,89,0.94) 55%, rgba(9,80,124,0.9) 100%) !important;
    border: 1px solid rgba(148,163,184,0.18);
    box-shadow: 0 16px 34px rgba(2, 6, 23, 0.18);
}

.ftr-member {
    background: rgba(255,255,255,.12);
    border: 1px solid rgba(255,255,255,.2);
}

@keyframes riseIn {
    from {
        opacity: 0;
        transform: translateY(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.kpi-box,
.trend-card,
.iq-wrap,
.card,
.ins-item {
    animation: riseIn .45s ease both;
}

.kpi-box:nth-child(2) { animation-delay: .04s; }
.kpi-box:nth-child(3) { animation-delay: .08s; }
.kpi-box:nth-child(4) { animation-delay: .12s; }
.kpi-box:nth-child(5) { animation-delay: .16s; }

@media (max-width: 1200px) {
    .hdr {
        position: static;
    }
    .kpi-strip {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 780px) {
    .kpi-strip {
        grid-template-columns: 1fr;
    }
    .trend-grid,
    .ins-row,
    .iq-grid {
        grid-template-columns: 1fr !important;
    }
    .hdr {
        padding: 10px 12px;
        border-radius: 10px;
    }
    .hdr-right {
        width: 100%;
        justify-content: space-between;
        gap: 10px;
    }
    .hdr-badge {
        padding: 6px 10px;
    }
}

</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# HELPERS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════
AQI_DEF = [
    (0,   50,  "Tốt",        "#14b8a6"),
    (51,  100, "Trung bình", "#0ea5e9"),
    (101, 150, "Kém",        "#f59e0b"),
    (151, 200, "Xấu",        "#f97316"),
    (201, 300, "Rất xấu",    "#ef4444"),
    (301, 500, "Nguy hại",   "#b91c1c"),
]

def aqi_meta(v):
    for lo, hi, lbl, col in AQI_DEF:
        if v <= hi: return lbl, col
    return "Nguy hại", "#b91c1c"

def band_lbl(v):
    for lo, hi, l, _ in AQI_DEF:
        if lo <= v <= hi: return l
    return "Nguy hại"

def aqi_health_guidance(v):
    if v <= 50:
        return "Không khí tốt", "Nhóm nhạy cảm có thể sinh hoạt ngoài trời bình thường.", "#22c55e"
    if v <= 100:
        return "Mức trung bình", "Người có bệnh hô hấp nên giảm hoạt động kéo dài ngoài trời.", "#0ea5e9"
    if v <= 150:
        return "Bắt đầu ảnh hưởng", "Trẻ em, người già và người có bệnh nền nên hạn chế ra ngoài giờ cao điểm.", "#f59e0b"
    if v <= 200:
        return "Không tốt cho sức khỏe", "Nên đeo khẩu trang lọc bụi mịn và giảm vận động mạnh ngoài trời.", "#f97316"
    return "Rất xấu", "Ưu tiên ở trong nhà, đóng cửa và dùng máy lọc nếu có.", "#ef4444"

def rank_rows_html(rank_df):
    rows = []
    for i, row in enumerate(rank_df.itertuples(index=False), start=1):
        lbl, clr = aqi_meta(row.aqi)
        rows.append(
            f"<div class='iq-rank-row'>"
            f"<div class='iq-rank-no'>{i}</div>"
            f"<div><div class='iq-rank-city'>{row.city}</div><div class='iq-rank-pm'>PM2.5: {row.pm2_5:.1f} µg/m³</div></div>"
            f"<div class='iq-rank-aqi' style='color:{clr}'>{row.aqi:.0f}</div>"
            f"</div>"
        )
    return "".join(rows)

def hex_rgba(h, a=0.12):
    h = h.lstrip("#"); r,g,b = int(h[:2],16), int(h[2:4],16), int(h[4:],16)
    return f"rgba({r},{g},{b},{a})"

CITY_PALETTE = [
    "#0284c7", "#0ea5e9", "#06b6d4", "#0891b2", "#0369a1",
    "#2563eb", "#3b82f6", "#14b8a6", "#0f766e", "#22c55e",
    "#f59e0b", "#f97316", "#ef4444", "#b45309", "#1d4ed8",
]

POLLS = {
    "pm2_5": dict(label="PM2.5", unit="µg/m³", who=15,   color="#ef4444", desc="Bụi mịn < 2.5µm"),
    "pm10":  dict(label="PM10",  unit="µg/m³", who=45,   color="#f97316", desc="Bụi thô < 10µm"),
    "o3":    dict(label="O₃",    unit="µg/m³", who=100,  color="#0ea5e9", desc="Ozone mặt đất"),
    "no2":   dict(label="NO₂",   unit="µg/m³", who=25,   color="#14b8a6", desc="Khí thải giao thông"),
    "co":    dict(label="CO",    unit="µg/m³", who=4000, color="#0369a1", desc="Đốt cháy không hoàn toàn"),
    "so2":   dict(label="SO₂",   unit="µg/m³", who=40,   color="#f59e0b", desc="Công nghiệp & nhiệt điện"),
}

SLOT_CLR = {
    "Sáng (6–12h)":  "#0284c7",
    "Chiều (12–18h)":"#f59e0b",
    "Tối (18–24h)":  "#0369a1",
    "Đêm (0–6h)":    "#94a3b8",
}

PT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Be Vietnam Pro", color="#334155", size=10),
    margin=dict(l=4, r=4, t=24, b=4),
)
GC = "rgba(0,0,0,0.04)"
LC = "#e2e8f0"
TF = dict(color="#64748b", size=9)

def ml(fig, h=None, **kw):
    cfg = {**PT, **({"height": h} if h else {}), **kw}
    fig.update_layout(**cfg)
    return fig

def ax(title=""):
    r = dict(tickfont=TF, gridcolor=GC, linecolor=LC, zeroline=False)
    if title:
        r["title"] = dict(text=title, font=dict(size=9, color="#64748b"))
    return r

def chart_h(n_rows, min_h=260, row_h=24, max_h=560):
    return int(min(max_h, max(min_h, n_rows * row_h + 70)))

def fmt_delta(curr, prev, unit=""):
    if prev is None or pd.isna(prev):
        return "Không đủ dữ liệu", "#64748b"
    delta = curr - prev
    if abs(delta) < 0.05:
        return f"■ 0.0{unit}", "#64748b"
    arrow = "▲" if delta > 0 else "▼"
    color = "#dc2626" if delta > 0 else "#16a34a"
    return f"{arrow} {delta:+.1f}{unit}", color

UI_MODES = ["Premium Sky", "Bloomberg Pro", "Apple Clean"]

def set_plot_theme(mode: str):
    global PT, GC, LC, TF
    if mode == "Bloomberg Pro":
        PT = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Be Vietnam Pro", color="#334155", size=10),
            margin=dict(l=4, r=4, t=24, b=4),
        )
        GC = "rgba(51,65,85,0.09)"
        LC = "#cbd5e1"
        TF = dict(color="#475569", size=9)
    elif mode == "Apple Clean":
        PT = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Be Vietnam Pro", color="#1f2937", size=10),
            margin=dict(l=4, r=4, t=24, b=4),
        )
        GC = "rgba(148,163,184,0.15)"
        LC = "#e2e8f0"
        TF = dict(color="#64748b", size=9)
    else:
        PT = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Be Vietnam Pro", color="#334155", size=10),
            margin=dict(l=4, r=4, t=24, b=4),
        )
        GC = "rgba(0,0,0,0.04)"
        LC = "#e2e8f0"
        TF = dict(color="#64748b", size=9)

def ui_mode_css(mode: str, reduce_motion: bool) -> str:
    if mode == "Bloomberg Pro":
        css = """
        .stApp {
            background:
                linear-gradient(180deg, #eef2f7 0%, #f5f7fb 40%, #f8fafc 100%) !important;
        }
        .hdr {
            border-radius: 8px !important;
            background: linear-gradient(132deg, #0b1320 0%, #1e293b 55%, #1f3c5b 100%) !important;
            border: 1px solid rgba(148,163,184,0.35) !important;
            box-shadow: 0 14px 28px rgba(15, 23, 42, 0.22) !important;
        }
        .hdr-badge {
            border-color: rgba(251,191,36,0.46) !important;
            background: rgba(245,158,11,0.16) !important;
        }
        .kpi-box, .trend-card, .card, .ins-item, .iq-wrap {
            border-radius: 8px !important;
            border-color: #c7d3e2 !important;
            box-shadow: 0 8px 18px rgba(15,23,42,0.08) !important;
            background: rgba(255,255,255,0.96) !important;
        }
        .card:hover {
            transform: none !important;
            box-shadow: 0 10px 22px rgba(15,23,42,0.1) !important;
        }
        .stTabs [data-baseweb=\"tab\"] {
            border-radius: 6px !important;
            border: 1px solid #cbd5e1 !important;
            background: #f8fafc !important;
            color: #334155 !important;
        }
        .stTabs [aria-selected=\"true\"] {
            background: linear-gradient(150deg, #0f172a, #1e293b) !important;
            color: #f8fafc !important;
            border-color: #334155 !important;
            box-shadow: 0 6px 14px rgba(15,23,42,0.24) !important;
        }
        .ftr {
            border-radius: 8px !important;
            background: linear-gradient(140deg, #0f172a 0%, #1e293b 100%) !important;
        }
        section[data-testid=\"stSidebar\"] {
            background:
                linear-gradient(180deg, #ffffff 0%, #f3f6fa 100%) !important;
        }
        """
    elif mode == "Apple Clean":
        css = """
        .stApp {
            background:
                radial-gradient(900px 300px at 15% -10%, rgba(2,132,199,0.09), transparent 70%),
                radial-gradient(720px 260px at 95% 0%, rgba(14,165,233,0.08), transparent 65%),
                linear-gradient(180deg, #f8fbff 0%, #f4f8fd 55%, #f8fafc 100%) !important;
        }
        .hdr {
            background: rgba(255,255,255,0.8) !important;
            border: 1px solid rgba(148,163,184,0.25) !important;
            box-shadow: 0 16px 34px rgba(15, 23, 42, 0.1) !important;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }
        .hdr-school, .hdr-sub, .hdr-stat-lbl, .hdr-badge-lbl {
            color: #64748b !important;
        }
        .hdr-title, .hdr-stat-val {
            color: #0f172a !important;
        }
        .hdr-badge {
            background: #f8fafc !important;
            border: 1px solid #dbeafe !important;
        }
        .kpi-box, .trend-card, .card, .ins-item, .iq-wrap {
            border-radius: 16px !important;
            border-color: rgba(148,163,184,0.2) !important;
            box-shadow: 0 16px 34px rgba(15,23,42,0.08) !important;
            background: rgba(255,255,255,0.88) !important;
        }
        .stTabs [data-baseweb=\"tab\"] {
            border-radius: 999px !important;
            border: 1px solid #dbeafe !important;
            background: rgba(255,255,255,0.85) !important;
        }
        .stTabs [aria-selected=\"true\"] {
            background: linear-gradient(140deg, #0ea5e9 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            border-color: transparent !important;
        }
        section[data-testid=\"stSidebar\"] {
            background:
                linear-gradient(180deg, #ffffff 0%, #f8fbff 60%, #f5f8fd 100%) !important;
        }
        """
    else:
        css = """
        .stApp {
            background:
                radial-gradient(1200px 420px at 8% -10%, rgba(14,165,233,0.18), transparent 65%),
                radial-gradient(920px 380px at 92% 3%, rgba(245,158,11,0.14), transparent 62%),
                linear-gradient(180deg, #eef4ff 0%, #f3f7fb 45%, #f8fbff 100%) !important;
        }
        """

    if reduce_motion:
        css += """
        *, *::before, *::after {
            animation: none !important;
            transition: none !important;
            scroll-behavior: auto !important;
        }
        """

    return f"<style>{css}</style>"

# ═══════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════
@st.cache_data
def load_data():
    base = os.path.dirname(__file__)
    for p in [
        os.path.join(base, "..", "data", "vietnam_air_quality.csv"),
        os.path.join(base, "data", "vietnam_air_quality.csv"),
        os.path.join(base, "vietnam_air_quality.csv"),
    ]:
        if os.path.exists(p):
            df = pd.read_csv(p)
            break
    else:
        st.error("Không tìm thấy file vietnam_air_quality.csv")
        st.stop()

    df["timestamp"]  = pd.to_datetime(df["timestamp"], errors="coerce")
    df["date_ts"]    = df["timestamp"].dt.normalize()
    df["date"]       = df["date_ts"].dt.date
    df["month"]      = df["timestamp"].dt.month
    df["hour"]       = df["timestamp"].dt.hour
    df["dow"]        = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["dow"] >= 5
    df["is_raining"] = df["rain"] > 0

    aqi_labels = [x[2] for x in AQI_DEF]
    df["aqi_lbl"] = pd.cut(
        df["aqi"],
        bins=[-np.inf, 50, 100, 150, 200, 300, np.inf],
        labels=aqi_labels,
        include_lowest=True,
    ).fillna("Nguy hại")
    df["band"] = df["aqi_lbl"]

    slot_labels = ["Đêm (0–6h)", "Sáng (6–12h)", "Chiều (12–18h)", "Tối (18–24h)"]
    df["time_slot"] = pd.cut(
        df["hour"],
        bins=[-1, 5, 11, 17, 24],
        labels=slot_labels,
    ).fillna(slot_labels[-1])

    df["wind_bin"] = pd.cut(
        df["wind_speed"],
        bins=[0, 5, 10, 20, 200],
        labels=["0–5", "5–10", "10–20", ">20"],
        include_lowest=True,
    )
    return df

@st.cache_data(show_spinner=False)
def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")

with st.spinner("Đang tải dữ liệu..."):
    DF = load_data()

# ═══════════════════════════════════════════════════════════════════
# SIDEBAR — TEMPLATE-STYLE FILTER
# ═══════════════════════════════════════════════════════════════════
all_cities = sorted(DF["city"].unique())
mn_date = DF["timestamp"].min().date()
mx_date = DF["timestamp"].max().date()

if "selected_cities" not in st.session_state:
    st.session_state.selected_cities = all_cities
if "date_range" not in st.session_state:
    st.session_state.date_range = [mn_date, mx_date]
if "city_chart_limit" not in st.session_state:
    st.session_state.city_chart_limit = min(18, len(all_cities))
if "ui_mode" not in st.session_state:
    st.session_state.ui_mode = UI_MODES[0]
if "reduce_motion" not in st.session_state:
    st.session_state.reduce_motion = False

st.sidebar.markdown("<div class='sidebar-section-title'>Phong cách hiển thị</div>", unsafe_allow_html=True)
st.sidebar.selectbox(
    "Chọn phong cách",
    options=UI_MODES,
    key="ui_mode",
    label_visibility="collapsed",
)
st.sidebar.toggle(
    "Giảm hiệu ứng chuyển động",
    key="reduce_motion",
    help="Phù hợp khi trình chiếu lâu hoặc muốn giao diện tĩnh.",
)

set_plot_theme(st.session_state.ui_mode)
st.markdown(ui_mode_css(st.session_state.ui_mode, st.session_state.reduce_motion), unsafe_allow_html=True)

st.sidebar.markdown(
    f"""
    <div class='sidebar-header-card'>
        <p class='sidebar-header-title'>Bảng Điều Khiển</p>
        <p class='sidebar-header-sub'>Lọc nhanh dữ liệu theo khu vực và khung thời gian.</p>
        <div class='sidebar-hero-metrics'>
            <div class='hero-pill'>
                <span>{len(all_cities)}</span>
                <small>Khu vực</small>
            </div>
            <div class='hero-pill'>
                <span>{len(DF):,}</span>
                <small>Bản ghi</small>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("<div class='sidebar-section-title'>Khu vực quan trắc</div>", unsafe_allow_html=True)

btn1, btn2, btn3 = st.sidebar.columns(3)
with btn1:
    if st.button("Tất cả", use_container_width=True, key="btn_all_cities"):
        st.session_state.selected_cities = all_cities
with btn2:
    if st.button("AQI cao", use_container_width=True, key="btn_hotspot"):
        top_cities = (
            DF.groupby("city")["aqi"]
            .mean()
            .sort_values(ascending=False)
            .head(min(8, len(all_cities)))
            .index.tolist()
        )
        st.session_state.selected_cities = top_cities
with btn3:
    if st.button("Xóa", use_container_width=True, key="btn_clear_cities"):
        st.session_state.selected_cities = []

selected_count = len(st.session_state.selected_cities)
preview_names = st.session_state.selected_cities[:4]
preview_chips = "".join([f"<span class='mini-city-chip'>{c}</span>" for c in preview_names])
if selected_count > 4:
    preview_chips += f"<span class='mini-city-chip'>+{selected_count - 4} khu vực</span>"

st.sidebar.markdown(
    f"""
    <div class='sidebar-selection-summary'>
        <div class='summary-count'>Đã chọn {selected_count} khu vực</div>
        <div>{preview_chips if preview_chips else "<span style='font-size:0.76rem;color:#64748b;'>Chưa chọn khu vực nào</span>"}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar.expander(f"Chỉnh khu vực ({selected_count})", expanded=False):
    st.multiselect(
        "Danh sách khu vực",
        options=all_cities,
        key="selected_cities",
        label_visibility="collapsed",
        placeholder="Tìm và chọn khu vực...",
    )

selected_cities = st.session_state.selected_cities
sel = selected_cities

st.sidebar.markdown(
    "<p class='sidebar-hint'>Gợi ý: bấm Chỉnh khu vực để cập nhật danh sách nhanh.</p>",
    unsafe_allow_html=True,
)

if selected_cities:
    city_scope_df = DF[DF["city"].isin(selected_cities)]
else:
    city_scope_df = DF

min_date = city_scope_df["timestamp"].min().date()
max_date = city_scope_df["timestamp"].max().date()

curr_start, curr_end = st.session_state.date_range
curr_start = min(max(curr_start, min_date), max_date)
curr_end = min(max(curr_end, min_date), max_date)
if curr_start > curr_end:
    curr_start, curr_end = min_date, max_date
st.session_state.date_range = [curr_start, curr_end]

st.sidebar.markdown("<div class='sidebar-section-title'>Khung thời gian</div>", unsafe_allow_html=True)
t1, t2, t3, t4 = st.sidebar.columns(4)
with t1:
    if st.button("30N", use_container_width=True, key="date_30d"):
        st.session_state.date_range = [max(min_date, max_date - pd.Timedelta(days=29)), max_date]
with t2:
    if st.button("90N", use_container_width=True, key="date_90d"):
        st.session_state.date_range = [max(min_date, max_date - pd.Timedelta(days=89)), max_date]
with t3:
    if st.button("YTD", use_container_width=True, key="date_ytd"):
        start_of_year = datetime(max_date.year, 1, 1).date()
        st.session_state.date_range = [max(min_date, start_of_year), max_date]
with t4:
    if st.button("Full", use_container_width=True, key="date_full"):
        st.session_state.date_range = [min_date, max_date]

dr = st.sidebar.date_input(
    "Chọn khoảng thời gian",
    value=st.session_state.date_range,
    min_value=min_date,
    max_value=max_date,
    key="date_range",
)
if isinstance(dr, (tuple, list)) and len(dr) == 2:
    s_d, e_d = dr
else:
    s_d, e_d = min_date, max_date
if s_d > e_d:
    s_d, e_d = e_d, s_d

start_date_ts = pd.Timestamp(s_d)
end_date_ts = pd.Timestamp(e_d)

side_df = DF[
    DF["city"].isin(selected_cities if selected_cities else all_cities)
    & (DF["date_ts"] >= start_date_ts)
    & (DF["date_ts"] <= end_date_ts)
]
st.sidebar.success(f"Dữ liệu đang xét: {len(side_df):,} bản ghi")

if not side_df.empty:
    side_avg_aqi = int(side_df["aqi"].mean())
    side_health_hd, side_health_tx, side_health_color = aqi_health_guidance(side_avg_aqi)
    st.sidebar.markdown(
        f"""
        <div class='sidebar-selection-summary'>
            <div class='summary-count'>Khuyến nghị sức khỏe theo AQI hiện tại</div>
            <div style='font-size:.84rem;font-weight:800;color:{side_health_color};margin-bottom:3px'>{side_health_hd} · AQI {side_avg_aqi}</div>
            <div style='font-size:.7rem;color:#4c6a86;line-height:1.5'>{side_health_tx}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

quality_cols = [
    c for c in ["aqi", "pm2_5", "pm10", "o3", "no2", "so2", "co", "temp", "humidity", "wind_speed", "rain"]
    if c in side_df.columns
]
if quality_cols and not side_df.empty:
    missing_rate = (side_df[quality_cols].isna().mean() * 100).sort_values(ascending=False)
    top_missing = missing_rate.head(3)
    missing_line = " · ".join([f"{k}: {v:.1f}%" for k, v in top_missing.items()])
    latest_side = side_df["timestamp"].max().strftime("%H:%M · %d/%m/%Y")
    st.sidebar.markdown(
        f"""
        <div class='sidebar-selection-summary'>
            <div class='summary-count'>Chất lượng dữ liệu</div>
            <div style='font-size:.68rem;color:#3f5f7c;line-height:1.45'>Cập nhật gần nhất: <strong>{latest_side}</strong></div>
            <div style='font-size:.68rem;color:#3f5f7c;line-height:1.45'>Tỷ lệ thiếu cao nhất: {missing_line}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

csv_name = f"vietnam_aqi_filtered_{s_d.strftime('%Y%m%d')}_{e_d.strftime('%Y%m%d')}.csv"
csv_bytes = to_csv_bytes(side_df)
st.sidebar.download_button(
    "Tải CSV theo bộ lọc hiện tại",
    data=csv_bytes,
    file_name=csv_name,
    mime="text/csv",
    use_container_width=True,
    help="Xuất toàn bộ dữ liệu sau khi lọc khu vực và thời gian.",
)

st.sidebar.markdown("<div class='sidebar-section-title'>Mật độ biểu đồ</div>", unsafe_allow_html=True)
city_cap_max = max(1, len(selected_cities) if selected_cities else len(all_cities))
city_cap_min = 1 if city_cap_max < 8 else 8
city_cap_default = min(max(st.session_state.city_chart_limit, city_cap_min), city_cap_max)
city_cap = st.sidebar.slider(
    "Số khu vực tối đa trên biểu đồ dài",
    min_value=city_cap_min,
    max_value=city_cap_max,
    value=city_cap_default,
    step=1,
    key="city_chart_limit",
    help="Giảm số khu vực để tránh biểu đồ quá cao khi chọn nhiều thành phố.",
)

aqi_opts = [b[2] for b in AQI_DEF]
sel_bands = aqi_opts

if not sel:
        st.warning("Vui lòng chọn ít nhất 1 khu vực để hiển thị.")
        st.stop()

# ── FILTER DATA ──
df = DF[
    DF["city"].isin(sel) &
    DF["band"].isin(sel_bands) &
    (DF["date_ts"] >= start_date_ts) &
    (DF["date_ts"] <= end_date_ts)
].copy()

days = max(1, (e_d - s_d).days + 1)
if df.empty:
    st.warning("Không có dữ liệu.")
    st.stop()

P_KEYS   = [k for k in POLLS if k in df.columns]
CITY_CLR = {c: CITY_PALETTE[i % len(CITY_PALETTE)] for i, c in enumerate(sorted(df["city"].unique()))}
city_aqi_mean = df.groupby("city")["aqi"].mean().sort_values(ascending=False)

avg_aqi   = int(df["aqi"].mean())
avg_pm25  = round(df["pm2_5"].mean(), 1)
dangerp   = round((df["aqi"] > 150).mean() * 100, 1)
worst     = city_aqi_mean.index[0]
cig_n     = round(avg_pm25 / 22.0 * days, 1)
_lbl, _col = aqi_meta(avg_aqi)
who_exceed = {k: round((df[k] > POLLS[k]["who"]).mean() * 100, 1) for k in P_KEYS}

latest_obs = df["timestamp"].max()
city_rank = (
    df.groupby("city")
    .agg(aqi=("aqi", "mean"), pm2_5=("pm2_5", "mean"))
    .round(1)
    .reset_index()
)
polluted_rank = city_rank.sort_values("aqi", ascending=False).head(6)
clean_rank = city_rank.sort_values("aqi", ascending=True).head(6)
who_pm25_multi = round(max(avg_pm25, 0.1) / 5.0, 1)
health_hd, health_tx, health_color = aqi_health_guidance(avg_aqi)
polluted_html = rank_rows_html(polluted_rank)
clean_html = rank_rows_html(clean_rank)

daily_trend = (
    df.groupby("date")[["aqi", "pm2_5"]]
    .mean()
    .sort_index()
)
if len(daily_trend) >= 2:
    aqi_1d_text, aqi_1d_color = fmt_delta(daily_trend["aqi"].iloc[-1], daily_trend["aqi"].iloc[-2])
    pm_1d_text, pm_1d_color = fmt_delta(daily_trend["pm2_5"].iloc[-1], daily_trend["pm2_5"].iloc[-2], " µg")
else:
    aqi_1d_text, aqi_1d_color = fmt_delta(0, None)
    pm_1d_text, pm_1d_color = fmt_delta(0, None)

if len(daily_trend) >= 14:
    curr_7d = daily_trend.tail(7).mean()
    prev_7d = daily_trend.iloc[-14:-7].mean()
    aqi_7d_text, aqi_7d_color = fmt_delta(curr_7d["aqi"], prev_7d["aqi"])
    pm_7d_text, pm_7d_color = fmt_delta(curr_7d["pm2_5"], prev_7d["pm2_5"], " µg")
else:
    aqi_7d_text, aqi_7d_color = fmt_delta(0, None)
    pm_7d_text, pm_7d_color = fmt_delta(0, None)

rank_up_line = "Chưa đủ dữ liệu để so sánh thứ hạng ngày gần nhất."
rank_down_line = ""
if len(daily_trend) >= 2:
    last_date = daily_trend.index[-1]
    prev_date = daily_trend.index[-2]
    city_day = df.groupby(["date", "city"])["aqi"].mean().reset_index()
    now_rank = city_day[city_day["date"] == last_date].sort_values("aqi", ascending=False)["city"].tolist()
    prv_rank = city_day[city_day["date"] == prev_date].sort_values("aqi", ascending=False)["city"].tolist()
    all_rank_cities = sorted(set(now_rank) | set(prv_rank))
    fallback_rank = len(all_rank_cities) + 1
    rank_now_map = {city: i + 1 for i, city in enumerate(now_rank)}
    rank_prev_map = {city: i + 1 for i, city in enumerate(prv_rank)}

    shift_rows = []
    for city in all_rank_cities:
        shift = rank_prev_map.get(city, fallback_rank) - rank_now_map.get(city, fallback_rank)
        if shift != 0:
            shift_rows.append((city, shift))

    up_moves = sorted([r for r in shift_rows if r[1] > 0], key=lambda x: x[1], reverse=True)[:2]
    down_moves = sorted([r for r in shift_rows if r[1] < 0], key=lambda x: x[1])[:2]
    if up_moves:
        rank_up_line = " · ".join([f"{c} (+{s})" for c, s in up_moves])
    if down_moves:
        rank_down_line = " · ".join([f"{c} ({s})" for c, s in down_moves])

city_priority = city_aqi_mean.index.tolist()
plot_city_limit = min(city_cap, len(city_priority))
plot_cities = city_priority[:plot_city_limit]
df_city = df[df["city"].isin(plot_cities)].copy()
is_city_trimmed = len(city_priority) > plot_city_limit

# ═══════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="hdr">
  <div class="hdr-left">
    <div class="hdr-logo">{logo_html}</div>
    <div>
      <div class="hdr-school">ĐẠI HỌC KHOA HỌC TỰ NHIÊN, ĐHQG–HCM &nbsp;·&nbsp; KHOA CNTT &nbsp;·&nbsp; Trực quan hóa Dữ liệu</div>
      <div class="hdr-title">Phân tích Chỉ số Chất lượng Không khí tại Việt Nam</div>
      <div class="hdr-sub">GVHD: Bùi Tiến Lên &nbsp;·&nbsp; Lớp CQ2023/24 &nbsp;·&nbsp; Nhóm 8 &nbsp;·&nbsp; TP.HCM – 2026</div>
    </div>
  </div>
  <div class="hdr-right">
    <div class="hdr-stat">
      <div class="hdr-stat-val">{len(sel)}</div>
      <div class="hdr-stat-lbl">Khu vực</div>
    </div>
    <div class="hdr-stat">
      <div class="hdr-stat-val">{len(df):,}</div>
      <div class="hdr-stat-lbl">Bản ghi</div>
    </div>
    <div class="hdr-stat">
      <div class="hdr-stat-val">{s_d.strftime('%d/%m/%y')} → {e_d.strftime('%d/%m/%y')}</div>
      <div class="hdr-stat-lbl">Thời gian</div>
    </div>
    <div class="hdr-badge">
      <div class="hdr-badge-val" style="color:{_col}">{avg_aqi}</div>
      <div class="hdr-badge-lbl">AQI · {_lbl}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# MAIN WRAP
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

# ── KPI STRIP ──
st.markdown(f"""
<div class="kpi-strip">
  <div class="kpi-box accent-blue">
    <div class="kpi-lbl">AQI tổng hợp</div>
    <div class="kpi-val" style="color:{_col}">{avg_aqi} <span class="u">{_lbl}</span></div>
    <div class="kpi-sub">WHO khuyến nghị AQI ≤ 50</div>
  </div>
  <div class="kpi-box accent-amber">
    <div class="kpi-lbl">PM2.5 trung bình</div>
    <div class="kpi-val">{avg_pm25} <span class="u">µg/m³</span></div>
    <div class="kpi-sub">Vượt ngưỡng WHO ({round(avg_pm25/15*100-100,0):.0f}% so với 15 µg)</div>
  </div>
  <div class="kpi-box accent-red">
    <div class="kpi-lbl">Tương đương thuốc lá</div>
    <div class="kpi-val">{cig_n} <span class="u">điếu</span></div>
    <div class="kpi-sub">trong {days} ngày · 22 µg/m³ = 1 điếu</div>
  </div>
  <div class="kpi-box accent-slate">
    <div class="kpi-lbl">Khu vực ô nhiễm nhất</div>
    <div class="kpi-val" style="font-size:1.1rem;padding-top:4px">{worst}</div>
    <div class="kpi-sub">AQI trung bình cao nhất</div>
  </div>
  <div class="kpi-box accent-red">
    <div class="kpi-lbl">Giờ AQI nguy hiểm</div>
    <div class="kpi-val">{dangerp} <span class="u">%</span></div>
    <div class="kpi-sub">AQI > 150 (Kém → Nguy hại)</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="trend-grid">
    <div class="trend-card">
        <div class="trend-kicker">Biến động 24 giờ</div>
        <div class="trend-main" style="color:{aqi_1d_color}">AQI: {aqi_1d_text}</div>
        <div class="trend-sub" style="color:{pm_1d_color}">PM2.5: {pm_1d_text}</div>
    </div>
    <div class="trend-card">
        <div class="trend-kicker">Biến động 7 ngày</div>
        <div class="trend-main" style="color:{aqi_7d_color}">AQI: {aqi_7d_text}</div>
        <div class="trend-sub" style="color:{pm_7d_color}">PM2.5: {pm_7d_text}</div>
    </div>
    <div class="trend-card">
        <div class="trend-kicker">Thay đổi thứ hạng ô nhiễm (so với ngày trước)</div>
        <div class="trend-rank-line"><strong>Leo hạng:</strong> {rank_up_line}</div>
        <div class="trend-rank-line"><strong>Hạ hạng:</strong> {rank_down_line if rank_down_line else "Không có biến động giảm rõ rệt."}</div>
    </div>
</div>
""", unsafe_allow_html=True)

iqair_hybrid_html = textwrap.dedent(f"""
<div class="iq-wrap">
<div class="iq-live-head">
<div class="iq-title">Live AQI Vietnam · IQAir Hybrid</div>
<div class="iq-meta">Cập nhật gần nhất: {latest_obs.strftime('%H:%M · %d/%m/%Y')} · Dữ liệu từ bộ cảm biến nội bộ</div>
</div>
<div class="iq-grid">
<div class="iq-card iq-card-hero">
<div class="iq-hero-kicker">Chất lượng không khí tại Việt Nam</div>
<div class="iq-hero-row">
<div class="iq-hero-aqi" style="color:{_col}">{avg_aqi}</div>
<div class="iq-hero-status">{_lbl}</div>
</div>
<div class="iq-hero-sub">PM2.5 trung bình hiện tại: <strong>{avg_pm25} µg/m³</strong></div>
<div class="iq-hero-sub">Nồng độ PM2.5 đang cao gấp <strong>{who_pm25_multi} lần</strong> mức hướng dẫn năm của WHO (5 µg/m³).</div>
<div class="iq-chip-row">
<span class="iq-chip">{len(sel)} khu vực</span>
<span class="iq-chip">{len(df):,} bản ghi</span>
<span class="iq-chip">{dangerp}% giờ AQI > 150</span>
</div>
<div class="iq-health-box" style="border-left-color:{health_color}">
<div class="iq-health-hd">Khuyến nghị sức khỏe: {health_hd}</div>
<div class="iq-health-tx">{health_tx}</div>
</div>
</div>
<div class="iq-card">
<div class="iq-card-title">Xếp hạng thành phố ô nhiễm nhất</div>
{polluted_html}
</div>
<div class="iq-card">
<div class="iq-card-title">Xếp hạng thành phố sạch hơn</div>
{clean_html}
</div>
</div>
</div>
""")
st.markdown(iqair_hybrid_html, unsafe_allow_html=True)

if is_city_trimmed:
    st.caption(
        f"Hiển thị Top {plot_city_limit}/{len(city_priority)} khu vực theo AQI trung bình cho các biểu đồ theo thành phố để giữ bố cục gọn."
    )

# ═══════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "🏠 Tổng quan",
    "📈 Q1 · Xu hướng thời gian",
    "🗺️  Q2 · Địa lý & Thời tiết",
    "💨 Q3 · Gió & Mưa",
    "🔬 Q4 · Tác nhân ô nhiễm",
    "📅 Q5&6 · Tần suất & Tuần",
])

# ══════════════════════════════════════════════
# TAB 0 — OVERVIEW
# ══════════════════════════════════════════════
with tabs[0]:
    cO1, cO2 = st.columns([2.2, 1.2], gap="small")

    with cO1:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Bản đồ AQI theo khu vực</div><div class="card-sub">Kích thước điểm = PM2.5 trung bình · Màu điểm = AQI trung bình</div>', unsafe_allow_html=True)
        city_geo = (
            df.groupby("city")
            .agg(
                lat=("lat", "mean"),
                lon=("lon", "mean"),
                aqi=("aqi", "mean"),
                pm2_5=("pm2_5", "mean"),
                n=("aqi", "size"),
            )
            .reset_index()
            .dropna(subset=["lat", "lon"])
        )
        city_geo["aqi_lbl"] = pd.cut(
            city_geo["aqi"],
            bins=[-np.inf, 50, 100, 150, 200, 300, np.inf],
            labels=[x[2] for x in AQI_DEF],
            include_lowest=True,
        ).fillna("Nguy hại")
        city_geo["marker_size"] = (city_geo["pm2_5"].clip(lower=8) * 0.7).clip(lower=8, upper=28)

        fig_map = go.Figure(go.Scattermapbox(
            lat=city_geo["lat"],
            lon=city_geo["lon"],
            mode="markers+text",
            text=city_geo["city"],
            textposition="top center",
            textfont=dict(size=9, color="#334155"),
            marker=dict(
                size=city_geo["marker_size"],
                color=city_geo["aqi"],
                colorscale=[
                    [0.0, "#14b8a6"],
                    [0.35, "#0ea5e9"],
                    [0.55, "#f59e0b"],
                    [0.75, "#f97316"],
                    [1.0, "#ef4444"],
                ],
                cmin=0,
                cmax=max(200, city_geo["aqi"].max() + 10),
                opacity=0.84,
                colorbar=dict(title="AQI", thickness=10, tickfont=dict(size=8), x=1.01),
            ),
            customdata=np.stack([city_geo["aqi_lbl"], city_geo["pm2_5"].round(1), city_geo["n"]], axis=-1),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "AQI TB: %{marker.color:.1f} (%{customdata[0]})<br>"
                "PM2.5 TB: %{customdata[1]} µg/m³<br>"
                "Số quan trắc: %{customdata[2]}<extra></extra>"
            ),
            showlegend=False,
        ))
        fig_map.update_layout(
            mapbox=dict(
                style="carto-positron",
                center=dict(lat=float(city_geo["lat"].mean()), lon=float(city_geo["lon"].mean())),
                zoom=4.5,
            ),
            margin=dict(l=2, r=2, t=6, b=2),
            height=430,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Be Vietnam Pro", size=10, color="#334155"),
        )
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cO2:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Tổng quan nhanh</div>', unsafe_allow_html=True)
        top_city = city_aqi_mean.head(5).round(1)
        low_city = city_aqi_mean.sort_values(ascending=True).head(3).round(1)
        top_who = sorted(who_exceed.items(), key=lambda x: x[1], reverse=True)[:3]
        top_who_txt = " · ".join([f"{POLLS[k]['label']}: {v}%" for k, v in top_who])

        st.markdown(
            f'<div class="kpi-box accent-blue" style="margin-bottom:8px"><div class="kpi-lbl">AQI trung bình</div><div class="kpi-val" style="color:{_col}">{avg_aqi}</div><div class="kpi-sub">{_lbl}</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="kpi-box accent-amber" style="margin-bottom:8px"><div class="kpi-lbl">PM2.5 trung bình</div><div class="kpi-val">{avg_pm25} <span class="u">µg/m³</span></div><div class="kpi-sub">% giờ nguy hiểm: {dangerp}%</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="kpi-box accent-slate"><div class="kpi-lbl">Vượt ngưỡng WHO</div><div class="kpi-sub" style="font-size:.67rem;color:#334155">{top_who_txt}</div></div>',
            unsafe_allow_html=True,
        )

        top_tbl = pd.DataFrame({"Thành phố AQI cao": top_city.index, "AQI TB": top_city.values})
        st.dataframe(top_tbl, use_container_width=True, hide_index=True)
        best_txt = " · ".join([f"{c} ({v:.1f})" for c, v in low_city.items()])
        st.markdown(f'<div class="card-sub" style="margin-top:6px"><strong>Khu vực sạch hơn:</strong> {best_txt}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    cO3, cO4 = st.columns([1.55, 2.45], gap="small")
    with cO3:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Cơ cấu mức AQI</div>', unsafe_allow_html=True)
        band_dist = df["aqi_lbl"].value_counts(normalize=True).reindex([x[2] for x in AQI_DEF]).fillna(0) * 100
        fig_dn = go.Figure(go.Pie(
            labels=band_dist.index,
            values=band_dist.round(2),
            hole=0.56,
            marker=dict(colors=[x[3] for x in AQI_DEF], line=dict(width=1, color="#fff")),
            textinfo="label+percent",
            textfont=dict(size=9),
            hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
        ))
        ml(fig_dn, h=265, margin=dict(l=4, r=4, t=14, b=2), showlegend=False)
        st.plotly_chart(fig_dn, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cO4:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Xu hướng AQI và PM2.5 theo ngày</div><div class="card-sub">Đặt hai tín hiệu cạnh nhau để đọc nhanh biến động thời gian</div>', unsafe_allow_html=True)
        daily_o = df.groupby("date")[["aqi", "pm2_5"]].mean().reset_index().sort_values("date")
        fig_ov = go.Figure()
        fig_ov.add_trace(go.Scatter(
            x=daily_o["date"],
            y=daily_o["aqi"].round(1),
            mode="lines",
            name="AQI",
            line=dict(color="#0ea5e9", width=2.4),
            hovertemplate="%{x}<br>AQI: %{y:.1f}<extra></extra>",
        ))
        fig_ov.add_trace(go.Scatter(
            x=daily_o["date"],
            y=daily_o["pm2_5"].round(1),
            mode="lines",
            name="PM2.5",
            line=dict(color="#f59e0b", width=2),
            yaxis="y2",
            hovertemplate="%{x}<br>PM2.5: %{y:.1f} µg/m³<extra></extra>",
        ))
        ml(
            fig_ov,
            h=265,
            xaxis=dict(**ax()),
            yaxis=dict(**ax("AQI")),
            yaxis2=dict(
                title=dict(text="PM2.5", font=dict(size=9, color="#b45309")),
                overlaying="y",
                side="right",
                tickfont=dict(size=9, color="#b45309"),
                showgrid=False,
            ),
            legend=dict(bgcolor="rgba(0,0,0,0)", font_size=9, orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig_ov, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 1 — Q4
# ══════════════════════════════════════════════
with tabs[4]:
    df_d = df[df["aqi"] > 100].copy()
    if df_d.empty:
        st.info("Không có dữ liệu AQI > 100.")
        st.stop()

    for k in P_KEYS:
        mu, sig = df_d[k].mean(), df_d[k].std()
        df_d[f"{k}_z"] = (df_d[k] - mu) / (sig + 1e-9)

    z_cols = [f"{k}_z" for k in P_KEYS]
    df_d["z_sum"] = df_d[z_cols].clip(lower=0).sum(axis=1).replace(0, np.nan)
    for k in P_KEYS:
        df_d[f"{k}_share"] = df_d[f"{k}_z"].clip(lower=0) / df_d["z_sum"] * 100

    # Build city-limited slice after derived share columns exist.
    df_d_city = df_d[df_d["city"].isin(plot_cities)].copy()
    if df_d_city.empty:
        df_d_city = df_d.copy()
    df_d_city_aqi_mean = df_d_city.groupby("city")["aqi"].mean().sort_values(ascending=False)

    overall = {k: df_d[f"{k}_share"].mean() for k in P_KEYS}
    rank    = sorted(overall, key=overall.get, reverse=True)
    bands_p = [b[2] for b in AQI_DEF if b[2] in df_d["band"].unique()]

    cA1, cA2, cA3, cA4 = st.columns([1, 1.35, 2.8, 2.2], gap="small")

    with cA1:
        st.markdown('<div class="card"><div class="card-title">AQI hiện tại</div>', unsafe_allow_html=True)
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number", value=avg_aqi,
            number=dict(font=dict(size=28, color=_col, family="Be Vietnam Pro")),
            gauge=dict(
                axis=dict(range=[0,300], tickwidth=1, tickcolor="#cbd5e1", tickfont=dict(size=8)),
                bar=dict(color=_col, thickness=0.22),
                bgcolor="white", borderwidth=0,
                steps=[
                    dict(range=[0,50],   color="#dcfce7"),
                    dict(range=[50,100], color="#fef9c3"),
                    dict(range=[100,150],color="#ffedd5"),
                    dict(range=[150,200],color="#fee2e2"),
                    dict(range=[200,300],color="#f3e8ff"),
                ],
            ),
        ))
        ml(fig_g, h=155, margin=dict(l=10,r=10,t=20,b=0))
        st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f'<div style="text-align:center;margin-top:-4px">'
            f'<span style="font-size:.95rem;font-weight:700;color:{_col}">{_lbl}</span><br>'
            f'<span style="font-size:.62rem;color:#64748b">PM2.5: {avg_pm25} µg/m³</span></div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with cA2:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q4</span>Xếp hạng chất ô nhiễm</div><div class="card-sub">% bất thường khi AQI > 100</div>', unsafe_allow_html=True)
        rank_icons = ["① ","② ","③ ","④ ","⑤ ","⑥ "]
        html_pm = '<div class="poll-mini-grid">'
        for i, k in enumerate(rank[:6]):
            cfg = POLLS[k]; pct = overall[k]
            html_pm += (
                f'<div class="poll-mini" style="border-top:2px solid {cfg["color"]}">'
                f'<div class="pm-rank">{rank_icons[i]}</div>'
                f'<div class="pm-name">{cfg["label"]}</div>'
                f'<div class="pm-val" style="color:{cfg["color"]}">{pct:.0f}'
                f'<span style="font-size:.6rem;color:#64748b">%</span></div>'
                f'</div>'
            )
        html_pm += '</div>'
        st.markdown(html_pm, unsafe_allow_html=True)
        st.markdown('<div style="margin-top:8px;font-size:.6rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">% giờ vượt ngưỡng WHO</div>', unsafe_allow_html=True)
        for k in rank[:4]:
            cfg = POLLS[k]; ex = who_exceed.get(k, 0); w = min(100, ex)
            st.markdown(
                f'<div class="who-row">'
                f'<span class="who-lbl">{cfg["label"]}</span>'
                f'<div class="who-bar-bg"><div class="who-bar-fg" style="width:{w}%;background:{cfg["color"]}"></div></div>'
                f'<span class="who-pct" style="color:{cfg["color"]}">{ex}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with cA3:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q4</span>Heatmap — % bất thường theo thành phố</div><div class="card-sub">Ô đậm = chất tăng bất thường mạnh · ● = thủ phạm chính</div>', unsafe_allow_html=True)
        city_sh = (
            df_d_city.groupby("city")[[f"{k}_share" for k in P_KEYS]]
            .mean()
            .rename(columns={f"{k}_share": POLLS[k]["label"] for k in P_KEYS})
        )
        cord    = df_d_city_aqi_mean.index
        city_sh = city_sh.reindex([c for c in cord if c in city_sh.index])
        poll_ord= [POLLS[k]["label"] for k in rank]
        city_sh = city_sh[[p for p in poll_ord if p in city_sh.columns]]
        z  = city_sh.values.round(1)
        xl = city_sh.columns.tolist()
        yl = city_sh.index.tolist()
        txt = []
        for row in z:
            mi = int(np.argmax(row))
            txt.append([f"●{v:.0f}" if j == mi else f"{v:.0f}" for j, v in enumerate(row)])
        fig_h = go.Figure(go.Heatmap(
            z=z, x=xl, y=yl,
            text=txt, texttemplate="%{text}", textfont=dict(size=9, color="#1e293b"),
            colorscale=[[0,"#f8fafc"],[0.35,"#bfdbfe"],[0.7,"#f97316"],[1,"#dc2626"]],
            showscale=True,
            colorbar=dict(thickness=8, len=0.6, tickfont=dict(size=8),
                          title=dict(text="%", font=dict(size=8)), outlinewidth=0),
            hovertemplate="<b>%{y}</b> · %{x}: %{z:.1f}%<extra></extra>",
        ))
        h_h = chart_h(len(yl), min_h=260, row_h=21, max_h=560)
        ml(fig_h, h=h_h)
        fig_h.update_xaxes(side="top", tickfont=TF, gridcolor="rgba(0,0,0,0)", linecolor=LC)
        fig_h.update_yaxes(tickfont=dict(color="#334155", size=9), gridcolor="rgba(0,0,0,0)", autorange="reversed", linecolor=LC)
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cA4:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q4</span>Cơ cấu & xu hướng theo mức AQI</div>', unsafe_allow_html=True)
        band_sh = (
            df_d.groupby("band")[[f"{k}_share" for k in P_KEYS]]
            .mean()
            .rename(columns={f"{k}_share": POLLS[k]["label"] for k in P_KEYS})
            .reindex(bands_p).fillna(0)
        )
        fig_st = go.Figure()
        for k in rank:
            lbl = POLLS[k]["label"]
            if lbl not in band_sh.columns: continue
            fig_st.add_trace(go.Bar(
                name=lbl, x=band_sh.index.tolist(), y=band_sh[lbl].round(1).tolist(),
                marker_color=POLLS[k]["color"],
                hovertemplate=f"<b>{lbl}</b> %{{x}}: %{{y:.1f}}%<extra></extra>"
            ))
        ml(fig_st, h=int(h_h*0.47), barmode="stack",
           xaxis=dict(**ax(), tickangle=-20),
           yaxis=dict(**ax(), range=[0,105]),
           legend=dict(bgcolor="rgba(0,0,0,0)", font_size=8, orientation="h",
                       yanchor="bottom", y=1.02, xanchor="left", x=0),
           bargap=0.2)
        st.plotly_chart(fig_st, use_container_width=True, config={"displayModeBar": False})

        band_z = (
            df_d.groupby("band")[[f"{k}_z" for k in P_KEYS]]
            .mean()
            .rename(columns={f"{k}_z": POLLS[k]["label"] for k in P_KEYS})
            .reindex(bands_p).fillna(0)
        )
        bz_n = (band_z - band_z.min()) / (band_z.max() - band_z.min() + 1e-9)
        fig_ln = go.Figure()
        for k in rank[:4]:
            lbl = POLLS[k]["label"]
            if lbl not in bz_n.columns: continue
            fig_ln.add_trace(go.Scatter(
                x=bands_p, y=bz_n[lbl].round(3).tolist(), name=lbl,
                mode="lines+markers",
                line=dict(color=POLLS[k]["color"], width=2),
                marker=dict(size=5, color=POLLS[k]["color"], line=dict(width=1.5, color="#fff")),
                hovertemplate=f"<b>{lbl}</b> %{{x}}: %{{y:.2f}}<extra></extra>"
            ))
        ml(fig_ln, h=int(h_h*0.47),
           xaxis=dict(**ax(), tickangle=-20),
           yaxis=dict(**ax("Z chuẩn hóa")),
           legend=dict(bgcolor="rgba(0,0,0,0)", font_size=8, orientation="h",
                       yanchor="bottom", y=1.02, xanchor="left", x=0))
        st.plotly_chart(fig_ln, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Row B
    cB1, cB2, cB3, cB4, cB5 = st.columns([2.5,1,1,1,1], gap="small")
    with cB1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        top_k  = rank[0]; top_cfg = POLLS[top_k]
        st.markdown(f'<div class="card-title"><span class="q-tag">Q4</span>Scatter {top_cfg["label"]} ↔ AQI theo thành phố</div>', unsafe_allow_html=True)
        sdf = df_d_city[[top_k,"aqi","city"]].dropna().sample(min(4000, len(df_d_city)), random_state=9)
        fig_sc = go.Figure()
        for city in sorted(sdf["city"].unique()):
            sub = sdf[sdf["city"]==city]
            fig_sc.add_trace(go.Scattergl(
                x=sub[top_k].round(2), y=sub["aqi"].round(1),
                mode="markers", name=city,
                marker=dict(color=CITY_CLR.get(city,"#2563eb"), size=4, opacity=0.5, line=dict(width=0)),
                hovertemplate=f"<b>{city}</b><br>{top_cfg['label']}: %{{x:.1f}}<br>AQI: %{{y:.0f}}<extra></extra>"
            ))
        fig_sc.add_vline(x=top_cfg["who"], line_dash="dot", line_color="rgba(217,119,6,.5)", line_width=1.5,
                         annotation_text=f"WHO {top_cfg['who']}", annotation_font_size=8,
                         annotation_font_color="#d97706", annotation_position="top right")
        fig_sc.add_hline(y=150, line_dash="dot", line_color="rgba(220,38,38,.5)", line_width=1.5,
                         annotation_text="AQI 150", annotation_font_size=8,
                         annotation_font_color="#dc2626", annotation_position="right")
        ml(fig_sc, h=220,
           xaxis=dict(**ax(f"{top_cfg['label']} ({top_cfg['unit']})")),
           yaxis=dict(**ax("AQI")),
           legend=dict(bgcolor="rgba(0,0,0,0)", font_size=8, orientation="v",
                       yanchor="top", y=1, xanchor="left", x=1.01))
        st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    top4   = df_d_city_aqi_mean.head(4).index.tolist()
    z_mean = (
        df_d_city[df_d_city["city"].isin(top4)]
        .groupby("city")[[f"{k}_z" for k in P_KEYS]].mean()
        .rename(columns={f"{k}_z": POLLS[k]["label"] for k in P_KEYS})
        .clip(lower=0)
    )
    z_n   = (z_mean / (z_mean.max() + 1e-9)).fillna(0)
    theta = z_n.columns.tolist()

    for i, (col_obj, city) in enumerate(zip([cB2,cB3,cB4,cB5], top4)):
        if city not in z_n.index: continue
        vals = z_n.loc[city].tolist(); vc = vals+[vals[0]]; tc = theta+[theta[0]]
        clr  = CITY_CLR.get(city, "#2563eb")
        aqit = df_d_city_aqi_mean.get(city, np.nan)
        main_p = z_mean.loc[city].idxmax() if city in z_mean.index else "—"
        fig_r = go.Figure(go.Scatterpolar(
            r=vc, theta=tc, fill="toself",
            fillcolor=hex_rgba(clr, 0.1),
            line=dict(color=clr, width=2),
            hovertemplate="<b>%{theta}</b>: %{r:.2f}<extra></extra>"
        ))
        fig_r.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Be Vietnam Pro", color="#334155", size=8),
            margin=dict(l=10,r=10,t=42,b=10), height=220,
            title=dict(
                text=f"<b style='color:{clr}'>{city}</b><br><span style='font-size:8px;color:#64748b'>AQI {aqit:.0f} · {main_p}</span>",
                x=0.5, xanchor="center", font=dict(size=10, color="#1e293b")
            ),
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0,1], showticklabels=False, gridcolor=GC, linecolor=LC),
                angularaxis=dict(tickfont=dict(size=8, color="#475569"), gridcolor=GC, linecolor=LC)
            )
        )
        with col_obj:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

    top1_cfg = POLLS[rank[0]]; top1_pct = overall[rank[0]]
    dom = city_sh.idxmax(axis=1) if not city_sh.empty else pd.Series()
    alt = dom[dom != top1_cfg["label"]]
    if not alt.empty:
        c2n, pl2 = alt.index[0], alt.iloc[0]
        pk2  = next((k for k in P_KEYS if POLLS[k]["label"]==pl2), None)
        pc2  = POLLS[pk2]["color"] if pk2 else "#d97706"
        pp2  = city_sh.loc[c2n, pl2] if pl2 in city_sh.columns else 0
        ins2 = f'Tại <b>{c2n}</b>, <span style="color:{pc2};font-weight:600">{pl2}</span> chiếm <b>{pp2:.1f}%</b> — khác xu hướng chung.'
        ins2f= "Kiểm tra nguồn phát thải đặc thù: công nghiệp, giao thông, địa hình."
    else:
        ins2 = "Tất cả khu vực có cơ cấu ô nhiễm tương đồng."; ins2f = ""

    if len(band_sh) >= 2:
        delta = band_sh.iloc[-1] - band_sh.iloc[0]; rl = delta.idxmax()
        rk    = next((k for k in P_KEYS if POLLS[k]["label"]==rl), None)
        rc    = POLLS[rk]["color"] if rk else "#2563eb"; rd = delta.max()
        ins3  = f'<span style="color:{rc};font-weight:600">{rl}</span> tăng <b>{rd:.1f} điểm %</b> khi AQI leo từ "{bands_p[0]}" → "{bands_p[-1]}".'
        ins3f = f"Theo dõi {rl} như chỉ báo sớm — khi tăng bất thường, AQI sắp vào vùng nguy hiểm."
    else:
        ins3 = "Cần thêm dữ liệu đa mức AQI."; ins3f = ""

    st.markdown(f"""
    <div class="ins-row">
      <div class="ins-item ins-red">
        <div class="ins-tag t-red">Thủ phạm số 1 toàn vùng</div>
        <div class="ins-body">
          <span style="color:{top1_cfg['color']};font-weight:700;font-size:1rem">{top1_cfg['label']}</span>
          chiếm trung bình <b>{top1_pct:.1f}%</b> mức bất thường khi AQI > 100.
        </div>
        <div class="ins-foot">{top1_cfg['desc']} · WHO limit: {top1_cfg['who']} {top1_cfg['unit']}</div>
      </div>
      <div class="ins-item ins-amber">
        <div class="ins-tag t-amber">Khu vực khác biệt</div>
        <div class="ins-body">{ins2}</div>
        <div class="ins-foot">{ins2f}</div>
      </div>
      <div class="ins-item ins-blue">
        <div class="ins-tag t-blue">Chỉ báo sớm</div>
        <div class="ins-body">{ins3}</div>
        <div class="ins-foot">{ins3f}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 2 — Q1
# ══════════════════════════════════════════════
with tabs[1]:
    cT1, cT2 = st.columns([1.7, 1.1], gap="small")

    with cT1:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q1</span>PM2.5 theo tháng & thời điểm</div><div class="card-sub">T10–T3 (mùa khô) PM2.5 thường cao hơn T4–T9 (mùa mưa)</div>', unsafe_allow_html=True)
        ms = df.groupby(["month","time_slot"])["pm2_5"].mean().reset_index()
        fig_ms = go.Figure()
        for slot, clr in SLOT_CLR.items():
            sub = ms[ms["time_slot"]==slot]
            fig_ms.add_trace(go.Scatter(
                x=sub["month"], y=sub["pm2_5"].round(2), name=slot,
                mode="lines+markers",
                line=dict(color=clr, width=2),
                marker=dict(size=5, color=clr, line=dict(width=1.5, color="#fff")),
                hovertemplate=f"<b>{slot}</b> T%{{x}}: %{{y:.1f}} µg/m³<extra></extra>"
            ))
        fig_ms.add_hline(y=15, line_dash="dot", line_color="rgba(220,38,38,.4)", line_width=1,
                         annotation_text="WHO 15µg", annotation_font_size=8, annotation_font_color="#dc2626")
        ml(fig_ms, h=290,
           xaxis=dict(tickmode="array", tickvals=list(range(1,13)),
                      ticktext=[f"T{m}" for m in range(1,13)], tickfont=TF, gridcolor=GC, linecolor=LC),
           yaxis=dict(**ax("PM2.5 µg/m³")),
           legend=dict(bgcolor="rgba(0,0,0,0)", font_size=9, orientation="h",
                       yanchor="bottom", y=1.02, xanchor="left", x=0))
        st.plotly_chart(fig_ms, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cT2:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q1</span>Nhịp AQI 24 giờ</div><div class="card-sub">Màu theo mức AQI · Đỉnh sáng sớm & chiều tối</div>', unsafe_allow_html=True)
        hr = df.groupby("hour")["aqi"].mean().reset_index()
        fig_hr = go.Figure(go.Bar(
            x=hr["hour"], y=hr["aqi"].round(1),
            marker_color=[aqi_meta(v)[1] for v in hr["aqi"]],
            hovertemplate="Giờ %{x}h: AQI %{y:.0f}<extra></extra>"
        ))
        ml(fig_hr, h=290,
           xaxis=dict(**ax("Giờ"), dtick=3),
           yaxis=dict(**ax("AQI")))
        st.plotly_chart(fig_hr, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q1</span>AQI hàng ngày — Rolling 7 ngày</div><div class="card-sub">Xám = từng ngày · Đỏ = trung bình trượt 7 ngày</div>', unsafe_allow_html=True)
    daily = df.groupby("date")["aqi"].mean().reset_index().sort_values("date")
    daily["r7"] = daily["aqi"].rolling(7, min_periods=1).mean()
    fig_day = go.Figure()
    for lo, hi, l, c in AQI_DEF:
        fig_day.add_hrect(y0=lo, y1=min(hi,310), fillcolor=c, opacity=0.04, line_width=0)
    fig_day.add_trace(go.Scatter(
        x=daily["date"], y=daily["aqi"].round(1), name="Hàng ngày",
        mode="lines", line=dict(color="#cbd5e1", width=1)
    ))
    fig_day.add_trace(go.Scatter(
        x=daily["date"], y=daily["r7"].round(1), name="TB 7 ngày",
        mode="lines", line=dict(color="#dc2626", width=2.5)
    ))
    ml(fig_day, h=310,
       xaxis=dict(**ax()),
       yaxis=dict(**ax("AQI")),
       legend=dict(bgcolor="rgba(0,0,0,0)", font_size=9, orientation="h",
                   yanchor="bottom", y=1.02, xanchor="left", x=0))
    st.plotly_chart(fig_day, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 3 — Q2
# ══════════════════════════════════════════════
with tabs[2]:
    cG1, cG2 = st.columns([1.15, 1.85], gap="small")

    with cG1:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q2</span>AQI trung bình theo thành phố</div>', unsafe_allow_html=True)
        ca = df_city.groupby("city")["aqi"].mean().sort_values(ascending=True).reset_index()
        ca["clr"] = ca["aqi"].apply(lambda x: aqi_meta(x)[1])
        fig_ca = go.Figure(go.Bar(
            x=ca["aqi"].round(1), y=ca["city"], orientation="h",
            marker_color=ca["clr"],
            text=ca["aqi"].round(1), textposition="outside",
            textfont=dict(size=9, color="#334155"),
            hovertemplate="%{y}: AQI %{x:.0f}<extra></extra>"
        ))
        ml(fig_ca, h=chart_h(len(ca), min_h=280, row_h=20, max_h=580),
           xaxis=dict(**ax("AQI")),
           yaxis=dict(tickfont=dict(color="#334155", size=9), gridcolor=GC, linecolor=LC))
        st.plotly_chart(fig_ca, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cG2:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q2</span>Nhiệt độ × Độ ẩm → AQI</div><div class="card-sub">Kích thước bong bóng = PM2.5</div>', unsafe_allow_html=True)
        sc2 = df_city.groupby("city").agg(
            temp=("temp","mean"), humidity=("humidity","mean"),
            aqi=("aqi","mean"), pm2_5=("pm2_5","mean")
        ).reset_index()
        fig_bb = go.Figure()
        for _, row in sc2.iterrows():
            clr = CITY_CLR.get(row["city"], "#2563eb")
            fig_bb.add_trace(go.Scatter(
                x=[round(row["temp"],1)], y=[round(row["humidity"],1)],
                mode="markers+text",
                marker=dict(size=max(10, row["pm2_5"]*0.85), color=clr, opacity=0.8,
                            line=dict(width=1.5, color="#fff")),
                text=[row["city"]], textposition="top center",
                textfont=dict(size=8, color="#334155"),
                showlegend=False,
                hovertemplate=(
                    f"<b>{row['city']}</b><br>Nhiệt độ: {row['temp']:.1f}°C<br>"
                    f"Độ ẩm: {row['humidity']:.1f}%<br>AQI: {row['aqi']:.0f}<br>"
                    f"PM2.5: {row['pm2_5']:.1f}<extra></extra>"
                )
            ))
        ml(fig_bb, h=chart_h(len(ca), min_h=280, row_h=20, max_h=580),
           xaxis=dict(**ax("Nhiệt độ (°C)")),
           yaxis=dict(**ax("Độ ẩm (%)")))
        st.plotly_chart(fig_bb, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q2</span>Phân phối mức AQI theo thành phố</div>', unsafe_allow_html=True)
    lc = df_city.groupby(["city","aqi_lbl"]).size().reset_index(name="n")
    lc["pct"] = (lc["n"] / lc.groupby("city")["n"].transform("sum") * 100).round(1)
    lclr = {
        "Tốt":       "#16a34a",
        "Trung bình":"#d97706",
        "Kém":       "#ea580c",
        "Xấu":       "#dc2626",
        "Rất xấu":  "#9333ea",
        "Nguy hại":  "#7f1d1d",
    }
    fig_lv = go.Figure()
    for lv in ["Tốt","Trung bình","Kém","Xấu","Rất xấu","Nguy hại"]:
        sub = lc[lc["aqi_lbl"]==lv]
        if sub.empty:
            continue
        fig_lv.add_trace(go.Bar(
            name=lv, x=sub["city"], y=sub["pct"],
            marker_color=lclr[lv],
            hovertemplate=f"<b>%{{x}}</b> {lv}: %{{y:.1f}}%<extra></extra>"
        ))
    ml(fig_lv, h=chart_h(len(ca), min_h=340, row_h=18, max_h=620), barmode="stack",
       xaxis=dict(tickfont=dict(color="#334155", size=9), tickangle=-25, gridcolor=GC, linecolor=LC),
       yaxis=dict(**ax("%"), range=[0,105]),
       legend=dict(bgcolor="rgba(0,0,0,0)", font_size=8, orientation="h",
                   yanchor="bottom", y=1.02, xanchor="left", x=0))
    st.plotly_chart(fig_lv, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 4 — Q3
# ══════════════════════════════════════════════
with tabs[3]:
    cW1, cW2 = st.columns(2, gap="small")

    with cW1:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q3</span>PM2.5 theo tốc độ gió</div><div class="card-sub">Đường dốc xuống = gió làm giảm bụi mịn hiệu quả</div>', unsafe_allow_html=True)
        wc = df_city.groupby(["city","wind_bin"])["pm2_5"].mean().reset_index().dropna()
        fig_w = go.Figure()
        for city in sorted(wc["city"].unique()):
            sub = wc[wc["city"]==city]
            fig_w.add_trace(go.Scatter(
                x=sub["wind_bin"].astype(str), y=sub["pm2_5"].round(2),
                name=city, mode="lines+markers",
                line=dict(color=CITY_CLR.get(city,"#2563eb"), width=2),
                marker=dict(size=6, color=CITY_CLR.get(city,"#2563eb"), line=dict(width=1.5, color="#fff")),
                hovertemplate=f"<b>{city}</b> gió %{{x}}: %{{y:.1f}}<extra></extra>"
            ))
        ml(fig_w, h=330,
           xaxis=dict(categoryorder="array", categoryarray=["0–5","5–10","10–20",">20"],
                      tickfont=TF, gridcolor=GC, linecolor=LC,
                      title=dict(text="Tốc độ gió (km/h)", font=dict(size=9, color="#64748b"))),
           yaxis=dict(**ax("PM2.5 µg/m³")),
           legend=dict(bgcolor="rgba(0,0,0,0)", font_size=9, orientation="v",
                       yanchor="top", y=1, xanchor="left", x=1.01))
        st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cW2:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q3</span>Hiệu quả rửa không khí khi mưa</div><div class="card-sub">Xanh = mưa giảm bụi · Đỏ = mưa không hiệu quả</div>', unsafe_allow_html=True)
        rr = (
            df_city.groupby(["city","is_raining"])["pm2_5"].mean()
            .unstack().rename(columns={False:"no_rain", True:"rain"}).dropna()
        )
        rr["drop"] = ((rr["no_rain"]-rr["rain"]) / rr["no_rain"] * 100).round(1)
        rr = rr.sort_values("drop", ascending=True).reset_index()
        rr["clr"] = rr["drop"].apply(lambda x: "#16a34a" if x > 0 else "#dc2626")
        fig_rr = go.Figure(go.Bar(
            x=rr["drop"], y=rr["city"], orientation="h",
            marker_color=rr["clr"],
            text=rr["drop"].apply(lambda x: f"{x:+.1f}%"),
            textposition="outside", textfont=dict(size=9, color="#334155"),
            hovertemplate="%{y}: %{x:+.1f}%<extra></extra>"
        ))
        fig_rr.add_vline(x=0, line_color="#e2e8f0", line_width=1)
        ml(fig_rr, h=330,
           xaxis=dict(**ax("% thay đổi PM2.5 khi mưa")),
           yaxis=dict(tickfont=dict(color="#334155", size=9), gridcolor=GC, linecolor=LC))
        st.plotly_chart(fig_rr, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 5 — Q5 & Q6
# ══════════════════════════════════════════════
with tabs[5]:
    cQ1, cQ2 = st.columns([1.35, 1.65], gap="small")

    with cQ1:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q5</span>% giờ AQI nguy hiểm (>150) theo thành phố</div>', unsafe_allow_html=True)
        dc = (
            df_city.assign(aqi_danger=df_city["aqi"] > 150)
            .groupby("city")["aqi_danger"]
            .mean()
            .mul(100)
            .sort_values(ascending=False)
            .round(1)
            .reset_index(name="pct")
        )
        dc["clr"]  = dc["pct"].apply(lambda x: "#dc2626" if x>20 else "#ea580c" if x>10 else "#d97706")
        fig_dc = go.Figure(go.Bar(
            x=dc["pct"], y=dc["city"], orientation="h",
            marker_color=dc["clr"],
            text=dc["pct"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside", textfont=dict(size=9, color="#334155"),
            hovertemplate="%{y}: %{x:.1f}% giờ AQI>150<extra></extra>"
        ))
        ml(fig_dc, h=chart_h(len(dc), min_h=300, row_h=20, max_h=580),
           xaxis=dict(**ax("% giờ quan trắc")),
           yaxis=dict(tickfont=dict(color="#334155", size=9), gridcolor=GC, linecolor=LC))
        st.plotly_chart(fig_dc, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cQ2:
        st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q6</span>PM2.5 — Ngày thường vs Cuối tuần</div>', unsafe_allow_html=True)
        wd = (
            df_city.groupby(["city","is_weekend"])["pm2_5"].mean()
            .unstack().fillna(0)
        )
        wd.columns = ["Ngày thường","Cuối tuần"]
        wd = wd.sort_values("Ngày thường", ascending=False).reset_index()
        fig_wd = go.Figure()
        for col, clr in [("Ngày thường","#2563eb"),("Cuối tuần","#16a34a")]:
            fig_wd.add_trace(go.Bar(
                name=col, x=wd["city"], y=wd[col].round(1),
                marker_color=clr,
                hovertemplate=f"<b>%{{x}}</b> {col}: %{{y:.1f}} µg/m³<extra></extra>"
            ))
        ml(fig_wd, h=chart_h(len(wd), min_h=300, row_h=20, max_h=580), barmode="group",
           xaxis=dict(tickfont=dict(color="#334155", size=9), tickangle=-30, gridcolor=GC, linecolor=LC),
           yaxis=dict(**ax("PM2.5 µg/m³")),
           legend=dict(bgcolor="rgba(0,0,0,0)", font_size=9, orientation="h",
                       yanchor="bottom", y=1.02, xanchor="left", x=0))
        st.plotly_chart(fig_wd, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-title"><span class="q-tag">Q6</span>PM2.5 theo thứ trong tuần</div>', unsafe_allow_html=True)
    DOW = {0:"T2",1:"T3",2:"T4",3:"T5",4:"T6",5:"T7",6:"CN"}
    dow = df.groupby("dow")["pm2_5"].mean().reset_index()
    dow["name"] = dow["dow"].map(DOW)
    dow["clr"]  = dow["dow"].apply(lambda x: "#16a34a" if x >= 5 else "#2563eb")
    fig_dw = go.Figure(go.Bar(
        x=dow["name"], y=dow["pm2_5"].round(1),
        marker_color=dow["clr"],
        text=dow["pm2_5"].round(1),
        textposition="outside", textfont=dict(size=9, color="#334155"),
        hovertemplate="%{x}: %{y:.1f} µg/m³<extra></extra>"
    ))
    ml(fig_dw, h=320,
       xaxis=dict(tickfont=dict(color="#334155", size=9), gridcolor=GC, linecolor=LC),
       yaxis=dict(**ax("PM2.5 µg/m³")))
    st.plotly_chart(fig_dw, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── FOOTER ──
members = [
        "23120283 · Phạm Quốc Khánh",
        "23120301 · Phạm Thành Nam",
        "23120318 · Trương Quang Phát",
        "23120329 · Châu Huỳnh Phúc",
        "23120334 · Huỳnh Tấn Phước",
]
member_chips = "".join([f'<span class="ftr-member">{m}</span>' for m in members])

st.markdown(f"""
<div class="ftr">
  <div class="ftr-txt">Vietnam AQI Analytics · ĐH Khoa học Tự nhiên TP.HCM · GVHD: Bùi Tiến Lên · {datetime.now().strftime('%d/%m/%Y')}</div>
    <div class="ftr-marquee">
        <div class="ftr-track">
            {member_chips}{member_chips}
        </div>
  </div>
</div>
""", unsafe_allow_html=True)