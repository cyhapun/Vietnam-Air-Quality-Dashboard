import streamlit as st
import threading
import time

from services.crawl_data.update_aqi_hourly import run_hourly_update
from services.crawl_data.get_province_aqi import run_province_aggregation
from services.crawl_data.get_forecast import run_forecast_update
import argparse

from components.header import render_header
from components.sidebar import build_state
from components.navigation import render_navigation
from services.data_loader import load_data
from tabs import overview_tab, aqi_tab, weather_dashboard, interaction_tab
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


def start_crawler_thread(mode="realtime"):
    """
    Background thread function to schedule data crawling.
    Executes a continuous loop based on the selected mode.
    """
    time.sleep(20)
    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] 🤖 Crawler ({mode}) đang chạy ngầm...")
            
            # Cập nhật dữ liệu hiện tại (áp dụng cho 'realtime' và 'current')
            if mode in ["realtime", "current"]:
                # Step 1: Crawl new data for each station (Batch API)
                run_hourly_update()
                time.sleep(15)

                # Step 2: Recalculate representative values (Mean/Mode) for each province/city
                run_province_aggregation()
                time.sleep(15)

            # Cập nhật dữ liệu dự báo (áp dụng cho 'realtime' và 'forecast')
            if mode in ["realtime", "forecast"]:
                # Step 3: Update Forecast data for the future
                run_forecast_update()

            print(f"Đã hoàn tất cập nhật dữ liệu cho chế độ: {mode}!")
        except Exception as e:
            print(f"❌ Lỗi crawler: {e}")

        # Sleep for 1 hour (3610 seconds) then run again
        time.sleep(3610)


@st.cache_resource
def initialize_background_tasks(mode):
    """
    Initializes and starts the background crawler thread with the specified mode.
    """
    # Truyền args=(mode,) vào thread để start_crawler_thread nhận được tham số
    thread = threading.Thread(target=start_crawler_thread, args=(mode,), daemon=True)
    thread.start()
    return "Crawler started"


# Use the cache decorator to ensure this thread is INITIALIZED ONLY ONCE
# even when Streamlit reruns (due to user interactions on the web)
@st.cache_resource
def initialize_background_tasks():
    """
    Initializes and starts the background crawler thread.
    Cached by Streamlit to prevent multiple thread spawns across app reruns.
    """
    thread = threading.Thread(target=start_crawler_thread, daemon=True)
    thread.start()
    return "Crawler started"


parser = argparse.ArgumentParser(description="Tùy chọn cho Vietnam AQI Dashboard")
parser.add_argument(
    "mode",
    nargs="?",
    choices=["realtime", "current", "forecast"],
    help="Chế độ crawler chạy ngầm: 'realtime' (cập nhật tất cả), 'current' (chỉ hiện tại), 'forecast' (chỉ dự báo)",
)

args, unknown = parser.parse_known_args()

if args.mode in ["realtime", "current", "forecast"]:
    initialize_background_tasks(args.mode)
    print(f"Đang bật chế độ crawler ngầm: {args.mode.upper()}.")
else:
    print(
        "Không sử dụng chế độ chạy ngầm. Thêm 'realtime', 'current', hoặc 'forecast' sau tên file khi chạy để bật."
    )

st.set_page_config(
    layout="wide",
    page_title="Vietnam AQI Dashboard",
    page_icon="data/hcmus_logo.png",
    initial_sidebar_state="collapsed",
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
    """
    Consume one-shot header actions from query parameters.
    Handles 'refresh' to clear cache and 'cb' to toggle colorblind mode.
    """
    use_modern_qp = hasattr(st, "query_params")

    if use_modern_qp:
        cb_val = st.query_params.get("cb")
        refresh_action = st.query_params.get("refresh")
    else:
        qp = st.experimental_get_query_params()
        cb_val = qp.get("cb", [None])[0]
        refresh_action = qp.get("refresh", [None])[0]

    # Handle Refresh
    if refresh_action == "1":
        st.cache_data.clear()
        if use_modern_qp:
            if "refresh" in st.query_params:
                del st.query_params["refresh"]
        else:
            qp = st.experimental_get_query_params()
            if "refresh" in qp:
                del qp["refresh"]
            st.experimental_set_query_params(**qp)
        st.rerun()

    if cb_val == "1":
        if not st.session_state.get("colorblind_mode", False):
            st.session_state["colorblind_mode"] = True
            st.session_state["_header_toggle_loading"] = True
    elif cb_val == "0":
        if st.session_state.get("colorblind_mode", True):
            st.session_state["colorblind_mode"] = False
            st.session_state["_header_toggle_loading"] = True
    elif cb_val == "toggle":
        st.session_state["colorblind_mode"] = not bool(st.session_state.get("colorblind_mode", False))
        st.session_state["_header_toggle_loading"] = True
        if use_modern_qp:
            st.query_params["cb"] = "1" if st.session_state["colorblind_mode"] else "0"
        else:
            qp = st.experimental_get_query_params()
            qp["cb"] = ["1" if st.session_state["colorblind_mode"] else "0"]
            st.experimental_set_query_params(**qp)


_consume_header_actions()


def render_tab_or_blank(tab_module, df):
    """
    Safely render a tab module if it has a 'render' function.

    Args:
        tab_module: The module representing the tab content.
        df: The main dataframe to pass to the render function.
    """
    render_fn = getattr(tab_module, "render", None)
    if callable(render_fn):
        render_fn(df)


def render_dashboard():
    """
    Main function to render the entire dashboard layout using three
    st.columns([1, 15]) rows (header / main). The left column of the
    main row hosts the hover navigation rail; tab content renders on the right.
    """
    DF = load_data()

    state = build_state(DF)
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

    active_tab = state.get("active_tab", "overview")

    # ── Row 1: Header ───────────────────────────
    hdr_left, hdr_right = st.columns([1, 15], gap="small")
    with hdr_right:
        render_header(state, logo_html)

    # ── Row 2: Navigation rail + tab content ────
    nav_col, content_col = st.columns([1, 15], gap="small")
    with nav_col:
        render_navigation(active_tab)

    with content_col:
        _render_tab_content(state, active_tab)


def _render_tab_content(state, active_tab):
    """Renders the currently active tab inside the main content column."""
    st.markdown('<div class="main-limit">', unsafe_allow_html=True)
    previous_active_tab = st.session_state.get("_last_active_tab")
    if active_tab == "interaction" and previous_active_tab != "interaction":
        st.session_state["interaction_time_range"] = "Năm 2025"
    st.session_state["_last_active_tab"] = active_tab

    if active_tab == "overview":
        overview_df = state["df"]
        province_col = "province" if "province" in overview_df.columns else "city"
        province_options = sorted(
            overview_df[province_col].dropna().astype(str).unique().tolist()
        )
        hcm_default = next(
            (
                p
                for p in province_options
                if "ho chi minh" in p.lower()
                or "hồ chí minh" in p.lower()
                or "tp hcm" in p.lower()
            ),
            province_options[0] if province_options else None,
        )
        if "overview_scope_mode" not in st.session_state:
            st.session_state["overview_scope_mode"] = "Cả nước"
        if "ov_time_range" not in st.session_state:
            st.session_state["ov_time_range"] = "24h"
        time_options = list(overview_tab.OV_TIMEFRAME_DELTAS.keys())
        if st.session_state["ov_time_range"] not in time_options:
            st.session_state["ov_time_range"] = "24h"

        c_filter_mode, c_filter_target, c_filter_time = st.columns(
            [1, 1.3, 0.8], gap="small"
        )
        with c_filter_mode:
            st.markdown(
                "<div class='ov-filter-label'>Phạm vi</div>", unsafe_allow_html=True
            )
            if "overview_scope_mode" not in st.session_state:
                st.session_state.overview_scope_mode = "Cả nước"

            b1, b2 = st.columns(2, gap="small")
            if b1.button(
                "Cả nước",
                type=(
                    "primary"
                    if st.session_state.overview_scope_mode == "Cả nước"
                    else "secondary"
                ),
                width="stretch",
            ):
                st.session_state.overview_scope_mode = "Cả nước"
                st.session_state["overview_scope_province"] = None
                st.rerun()
            if b2.button(
                "Theo Tỉnh thành",
                type=(
                    "primary"
                    if st.session_state.overview_scope_mode == "Theo Tỉnh thành"
                    else "secondary"
                ),
                width="stretch",
            ):
                st.session_state.overview_scope_mode = "Theo Tỉnh thành"
                if not st.session_state.get("overview_scope_province") and hcm_default:
                    st.session_state["overview_scope_province"] = hcm_default
                st.rerun()

            scope_mode = st.session_state.overview_scope_mode
        selected_scope_label = "Việt Nam"
        with c_filter_target:
            st.markdown(
                "<div class='ov-filter-label'>Khu vực cụ thể</div>",
                unsafe_allow_html=True,
            )
            if (
                scope_mode == "Theo Tỉnh thành"
                and not st.session_state.get("overview_scope_province")
                and hcm_default
            ):
                st.session_state["overview_scope_province"] = hcm_default

            cur_prov = st.session_state.get("overview_scope_province")
            if scope_mode == "Theo Tỉnh thành":
                if cur_prov in province_options:
                    sb_index = province_options.index(cur_prov)
                else:
                    sb_index = (
                        province_options.index(hcm_default)
                        if hcm_default in province_options
                        else 0
                    )
            else:
                sb_index = None

            selected_province = st.selectbox(
                "Chọn tỉnh/thành",
                options=province_options,
                index=sb_index,
                placeholder=(
                    "Vui lòng chọn tỉnh thành"
                    if scope_mode == "Theo Tỉnh thành"
                    else "Chỉ áp dụng khi chọn Theo Tỉnh thành"
                ),
                disabled=scope_mode != "Theo Tỉnh thành",
                label_visibility="collapsed",
            )

            if scope_mode == "Theo Tỉnh thành" and selected_province != cur_prov:
                st.session_state["overview_scope_province"] = selected_province
                st.rerun()
            if scope_mode == "Theo Tỉnh thành":
                if selected_province:
                    try:
                        from services.data_loader import (
                            load_province_detail,
                            _apply_aqi_labels,
                        )

                        s_arg = str(state["s_d"]) if "s_d" in state else None
                        e_arg = str(state["e_d"]) if "e_d" in state else None
                        with dashboard_loading(
                            "Đang tải dữ liệu chi tiết tỉnh/thành...",
                            hint=f"Chuẩn hóa chuỗi thời gian và phân lớp AQI cho {selected_province}.",
                            overlay=True,
                            min_duration=0.35,
                        ):
                            detail_raw = load_province_detail(
                                selected_province,
                                s_arg,
                                e_arg,
                                prefer_all_csv=False,
                            )
                        overview_df = _apply_aqi_labels(detail_raw.copy())
                    except Exception:
                        overview_df = overview_df[
                            overview_df[province_col] == selected_province
                        ].copy()
                    selected_scope_label = selected_province
                else:
                    overview_df = overview_df.iloc[0:0]
        with c_filter_time:
            st.markdown(
                "<div class='ov-filter-label'>Thời gian</div>", unsafe_allow_html=True
            )
            selected_time = st.selectbox(
                "Thời gian",
                options=time_options,
                index=time_options.index(st.session_state["ov_time_range"]),
                key="overview_time_range_select",
                label_visibility="collapsed",
            )
            if selected_time != st.session_state["ov_time_range"]:
                st.session_state["ov_time_range"] = selected_time
                st.rerun()

        if overview_df.empty:
            st.info("Không có dữ liệu cho phạm vi đã chọn.")
        else:
            overview_tab.render_overview(
                state, df_override=overview_df, scope_label=selected_scope_label
            )
            render_tab_or_blank(overview_tab, overview_df)
    elif active_tab == "aqi":
        render_tab_or_blank(aqi_tab, state["df"])
    elif active_tab == "weather":
        render_tab_or_blank(weather_dashboard, state["df"])
    elif active_tab == "interaction":
        render_tab_or_blank(interaction_tab, state["df"])
    else:
        render_tab_or_blank(overview_tab, state["df"])

    st.markdown("</div>", unsafe_allow_html=True)  # Close main-limit


def main():
    """
    Application entry point when run within Streamlit.
    Handles the initial loading screen and mode toggles before rendering the dashboard.
    """
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


if st.runtime.exists():
    main()
elif __name__ == "__main__":
    import os
    import sys
    from streamlit.web import cli as stcli

    if len(sys.argv) > 1:
        # Automatically insert Streamlit's '--' to support the command: python app.py realtime
        sys.argv = ["streamlit", "run", sys.argv[0], "--", *sys.argv[1:]]
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
    sys.exit(stcli.main())
