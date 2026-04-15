import streamlit as st
import threading
import time

from services.crawl_data.update_aqi_hourly import run_hourly_update 
from services.crawl_data.get_province_aqi import run_province_aggregation 
from services.crawl_data.get_forecast import run_forecast_update
import argparse

from components.footer import render_footer
from components.header import render_header
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

# Hàm chạy ngầm để lập lịch
def start_crawler_thread():
    time.sleep(20)
    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] 🤖 Crawler đang chạy ngầm...")
            # Bước 1: Cào dữ liệu mới cho từng trạm (Batch API)
            run_hourly_update()
            
            # Bước 2: Tính toán lại giá trị đại diện (Mean/Mode) cho từng tỉnh thành
            run_province_aggregation()

            # 3. Cập nhật dữ liệu Dự báo (Forecast tương lai)
            run_forecast_update()

            print("Đã hoàn tất cập nhật dữ liệu!")
        except Exception as e:
            print(f"❌ Lỗi crawler: {e}")
        
        # Ngủ 1 tiếng (3610 giây) rồi chạy tiếp (chừa 10s để API cập nhật dữ liệu tránh lỗi)
        time.sleep(3610) 

# Sử dụng decorator cache để đảm bảo thread này CHỈ KHỞI TẠO 1 LẦN 
# ngay cả khi Streamlit rerun (do user thao tác trên web)
@st.cache_resource
def initialize_background_tasks():
    thread = threading.Thread(target=start_crawler_thread, daemon=True)
    thread.start()
    return "Crawler started"

parser = argparse.ArgumentParser(description="Tùy chọn cho Vietnam AQI Dashboard")
parser.add_argument(
    "--real-time", 
    action="store_true", 
    help="Bật tính năng chạy ngầm crawler để cập nhật dữ liệu real-time"
)

# Sử dụng parse_known_args để bỏ qua các tham số mặc định của lệnh `streamlit run`
args, unknown = parser.parse_known_args()

# if args.real_time:
#     initialize_background_tasks()
#     print("Đang bật chế độ Real-time.")
# else:
#     print("Không sử dụng chế độ Real-time. Thêm cờ '--real-time' khi chạy để bật.")

print("⚠️ CHẾ ĐỘ CRAWL NGẦM ĐÃ ĐƯỢC TẠM TẮT ĐỂ TIỆN TEST. (Mở app.py để bỏ comment nếu cần)")

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

    active_tab = state.get("active_tab", "overview")

    if active_tab == "overview":
        overview_df = state["df"]
        province_col = "province" if "province" in overview_df.columns else "city"
        province_options = sorted(overview_df[province_col].dropna().astype(str).unique().tolist())
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

        c_filter_mode, c_filter_target, c_filter_time = st.columns([1.15, 1.45, 0.85], gap="small")
        with c_filter_mode:
            st.markdown("<div class='ov-filter-label'>Phạm vi</div>", unsafe_allow_html=True)
            if "overview_scope_mode" not in st.session_state:
                st.session_state.overview_scope_mode = "Cả nước"

            b1, b2 = st.columns(2, gap="small")
            if b1.button(
                "Cả nước",
                type="primary" if st.session_state.overview_scope_mode == "Cả nước" else "secondary",
                use_container_width=True,
            ):
                st.session_state.overview_scope_mode = "Cả nước"
                st.session_state["overview_scope_province"] = None
                st.rerun()
            if b2.button(
                "Theo tỉnh/thành",
                type="primary" if st.session_state.overview_scope_mode == "Theo tỉnh/thành" else "secondary",
                use_container_width=True,
            ):
                st.session_state.overview_scope_mode = "Theo tỉnh/thành"
                if not st.session_state.get("overview_scope_province") and hcm_default:
                    st.session_state["overview_scope_province"] = hcm_default
                st.rerun()

            scope_mode = st.session_state.overview_scope_mode
        selected_scope_label = "Việt Nam"
        with c_filter_target:
            st.markdown("<div class='ov-filter-label'>Khu vực cụ thể</div>", unsafe_allow_html=True)
            if (
                scope_mode == "Theo tỉnh/thành"
                and not st.session_state.get("overview_scope_province")
                and hcm_default
            ):
                st.session_state["overview_scope_province"] = hcm_default
            selected_province = st.selectbox(
                "Chọn tỉnh/thành",
                options=province_options,
                index=(
                    province_options.index(st.session_state["overview_scope_province"])
                    if st.session_state.get("overview_scope_province") in province_options
                    else (province_options.index(hcm_default) if hcm_default in province_options else None)
                ),
                key="overview_scope_province",
                placeholder=(
                    "Vui lòng chọn tỉnh thành"
                    if scope_mode == "Theo tỉnh/thành"
                    else "Chỉ áp dụng khi chọn Theo tỉnh/thành"
                ),
                disabled=scope_mode != "Theo tỉnh/thành",
                label_visibility="collapsed",
            )
            if scope_mode == "Theo tỉnh/thành":
                if selected_province:
                    try:
                        from services.data_loader import load_province_detail, _apply_aqi_labels
                        s_arg = str(state["s_d"]) if "s_d" in state else None
                        e_arg = str(state["e_d"]) if "e_d" in state else None
                        with dashboard_loading(
                            "Đang tải dữ liệu chi tiết tỉnh/thành...",
                            hint=f"Chuẩn hóa chuỗi thời gian và phân lớp AQI cho {selected_province}.",
                            overlay=False,
                            min_duration=0.35,
                        ):
                            detail_raw = load_province_detail(
                                selected_province,
                                s_arg,
                                e_arg,
                                prefer_all_csv=True,
                            )
                        overview_df = _apply_aqi_labels(detail_raw.copy())
                    except Exception:
                        overview_df = overview_df[overview_df[province_col] == selected_province].copy()
                    selected_scope_label = selected_province
                else:
                    overview_df = overview_df.iloc[0:0]
        with c_filter_time:
            st.markdown("<div class='ov-filter-label'>Thời gian</div>", unsafe_allow_html=True)
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
    elif active_tab == "location":
        render_tab_or_blank(location_tab, state["df"])
    elif active_tab == "datetime":
        render_tab_or_blank(datetime_tab, state["df"])
    elif active_tab == "atmos":
        render_tab_or_blank(atmos_tab, state["df"])
    elif active_tab == "aqi":
        render_tab_or_blank(aqi_tab, state["df"])
    elif active_tab == "weather":
        render_tab_or_blank(weather_tab, state["df"])
    elif active_tab == "interaction":
        render_tab_or_blank(interaction_tab, state["df"])
    else:
        render_tab_or_blank(overview_tab, state["df"])

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
