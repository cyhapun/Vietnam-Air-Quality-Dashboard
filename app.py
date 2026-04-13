import streamlit as st

from components.footer import render_footer
from components.header import render_header
from components.overview import render_overview
from components.sidebar import render_sidebar
from services.data_loader import load_data
from tabs import overview_tab, location_tab, datetime_tab, atmos_tab, aqi_tab, weather_tab, interaction_tab
from utils.css import inject_css
from utils.loading import dashboard_loading
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
vietnam_svg_base64 = get_base64_image("components/vietnam.svg")
pm25_svg_base64 = get_base64_image("components/pm25.svg")
loader_icon_defs = [
    ("pm25", "PM2.5"),
    ("pm10", "PM10"),
    ("o3", "O3"),
    ("no2", "NO2"),
    ("so2", "SO2"),
    ("co", "CO"),
]
loader_icon_urls = []
loader_icon_labels = []
for icon_key, icon_label in loader_icon_defs:
    icon_b64 = get_base64_image(f"components/{icon_key}.svg")
    if icon_b64:
        loader_icon_urls.append(f"data:image/svg+xml;base64,{icon_b64}")
        loader_icon_labels.append(icon_label)

if loader_icon_urls:
    st.session_state["_loader_icon_urls"] = loader_icon_urls
    st.session_state["_loader_icon_labels"] = loader_icon_labels

if pm25_svg_base64:
    st.session_state["_loader_art_url"] = f"data:image/svg+xml;base64,{pm25_svg_base64}"
elif vietnam_svg_base64:
    st.session_state["_loader_art_url"] = (
        f"data:image/svg+xml;base64,{vietnam_svg_base64}"
    )
if logo_base64:
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="width:100%;height:100%;object-fit:contain;padding:2px;">'
else:
    logo_html = "🌿"


def _consume_header_actions():
    """Consume one-shot header actions from query params."""
    action = None
    use_modern_qp = hasattr(st, "query_params")

    if use_modern_qp:
        action = st.query_params.get("cb")
    else:
        qp = st.experimental_get_query_params()
        action = qp.get("cb", [None])[0]

    if action != "toggle":
        return

    st.session_state["colorblind_mode"] = not bool(
        st.session_state.get("colorblind_mode", False)
    )
    st.session_state["_header_toggle_loading"] = True

    if use_modern_qp:
        try:
            del st.query_params["cb"]
        except Exception:
            st.query_params.clear()
    else:
        st.experimental_set_query_params()


_consume_header_actions()

def render_tab_or_blank(tab_module, df):
    render_fn = getattr(tab_module, "render", None)
    if callable(render_fn):
        render_fn(df)


def render_dashboard():
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
            "vietnam_svg_base64": vietnam_svg_base64,
        }
    )

    st.session_state["dashboard_context"] = state

    render_header(state, logo_html)
    render_overview(state)

    tabs = st.tabs(
        [
            "Tổng quan",
            "Ví Trí",
            "Thời Gian",
            "Khí Tượng & Môi Trường",
            "AQI",
            "Thời tiết",
            "Tương tác",
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
    with tabs[4]:
        render_tab_or_blank(aqi_tab, state["df"])
    with tabs[5]:
        render_tab_or_blank(weather_tab, state["df"])
    with tabs[6]:
        render_tab_or_blank(interaction_tab, state["df"])

    render_footer()


is_first_boot = not st.session_state.get("_dashboard_boot_ready", False)
show_toggle_loader = bool(st.session_state.pop("_header_toggle_loading", False))

if is_first_boot:
    with dashboard_loading(
        "Đang tải dữ liệu dashboard...",
        hint="Chuẩn hóa dữ liệu AQI, PM2.5 và dựng bố cục ban đầu.",
        overlay=True,
        min_duration=1.0,
    ):
        render_dashboard()
    st.session_state["_dashboard_boot_ready"] = True
elif show_toggle_loader:
    with dashboard_loading(
        "Đang cập nhật chế độ mù màu...",
        hint="Đang áp dụng bảng màu mới và dựng lại dashboard.",
        overlay=True,
        min_duration=0.75,
    ):
        render_dashboard()
else:
    render_dashboard()
