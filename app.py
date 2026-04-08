import streamlit as st

from components.footer import render_footer
from components.header import render_header
from components.overview import render_overview
from components.sidebar import render_sidebar
from services.data_loader import load_data
from tabs import overview_tab, location_tab, datetime_tab, atmos_tab
from utils.css import inject_css
from utils.helpers import (
    AQI_DEF,
    CITY_PALETTE,
    GC,
    LC,
    POLLS,
    SLOT_CLR,
    TF,
    aqi_health_guidance,
    aqi_meta,
    ax,
    band_lbl,
    chart_h,
    fmt_delta,
    get_base64_image,
    hex_rgba,
    ml,
    rank_rows_html,
)


st.set_page_config(
    layout="wide",
    page_title="Vietnam AQI Dashboard",
    page_icon="data/hcmus_logo.png",
    initial_sidebar_state="expanded",
)

inject_css("styles/main.css")

logo_base64 = get_base64_image("data/hcmus_logo.png")
if logo_base64:
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="width:100%;height:100%;object-fit:contain;padding:2px;">'
else:
    logo_html = "🌿"

with st.spinner("Đang tải dữ liệu..."):
    DF = load_data()

state = render_sidebar(DF)
state.update(
    {
        "AQI_DEF": AQI_DEF,
        "POLLS": POLLS,
        "CITY_PALETTE": CITY_PALETTE,
        "SLOT_CLR": SLOT_CLR,
        "GC": GC,
        "LC": LC,
        "TF": TF,
        "aqi_meta": aqi_meta,
        "band_lbl": band_lbl,
        "aqi_health_guidance": aqi_health_guidance,
        "rank_rows_html": rank_rows_html,
        "hex_rgba": hex_rgba,
        "ml": ml,
        "ax": ax,
        "chart_h": chart_h,
        "fmt_delta": fmt_delta,
    }
)

st.session_state["dashboard_context"] = state

render_header(state, logo_html)
render_overview(state)


def render_tab_or_blank(tab_module, df):
    render_fn = getattr(tab_module, "render", None)
    if callable(render_fn):
        render_fn(df)


tabs = st.tabs(
    [
        "Tổng quan",
        "Vị Trí",
        "Thời Gian",
        "Khí Tượng & Môi Trường",
    ]
)

with tabs[0]:
    render_tab_or_blank(overview_tab, state["df"])
with tabs[1]:
    render_tab_or_blank(location_tab, state["df"])
with tabs[2]:
    render_tab_or_blank(datetime_tab, state["df"])
with tabs[3]:
    render_tab_or_blank(atmos_tab, state["df"])

render_footer()
