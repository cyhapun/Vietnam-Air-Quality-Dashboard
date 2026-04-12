import pandas as pd
import streamlit as st
from datetime import datetime

from services.data_loader import to_csv_bytes
from utils.helpers import (
    AQI_DEF,
    CITY_PALETTE,
    POLLS,
    UI_MODES,
    aqi_health_guidance,
    aqi_meta,
    apply_colorblind,
    fmt_delta,
    rank_rows_html,
    set_plot_theme,
    ui_mode_css,
)


def render_sidebar(DF):
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

    st.sidebar.markdown(
        "<div class='sidebar-section-title'>Phong cách hiển thị</div>",
        unsafe_allow_html=True,
    )
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
    st.sidebar.toggle(
        "Chế độ mù màu",
        key="colorblind_mode",
        help="Chuyển sang bảng màu thân thiện với người mù màu (Okabe-Ito).",
    )

    apply_colorblind(st.session_state.get("colorblind_mode", False))
    set_plot_theme(st.session_state.ui_mode)
    st.markdown(
        ui_mode_css(st.session_state.ui_mode, st.session_state.reduce_motion),
        unsafe_allow_html=True,
    )

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

    st.sidebar.markdown(
        "<div class='sidebar-section-title'>Khu vực quan trắc</div>",
        unsafe_allow_html=True,
    )

    btn1, btn2, btn3 = st.sidebar.columns(3)
    with btn1:
        if st.button("Tất cả", width="stretch", key="btn_all_cities"):
            st.session_state.selected_cities = all_cities
    with btn2:
        if st.button("AQI cao", width="stretch", key="btn_hotspot"):
            top_cities = (
                DF.groupby("city")["aqi"]
                .mean()
                .sort_values(ascending=False)
                .head(min(8, len(all_cities)))
                .index.tolist()
            )
            st.session_state.selected_cities = top_cities
    with btn3:
        if st.button("Xóa", width="stretch", key="btn_clear_cities"):
            st.session_state.selected_cities = []

    selected_count = len(st.session_state.selected_cities)
    preview_names = st.session_state.selected_cities[:4]
    preview_chips = "".join(
        [f"<span class='mini-city-chip'>{c}</span>" for c in preview_names]
    )
    if selected_count > 4:
        preview_chips += (
            f"<span class='mini-city-chip'>+{selected_count - 4} khu vực</span>"
        )

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

    st.sidebar.markdown(
        "<div class='sidebar-section-title'>Khung thời gian</div>",
        unsafe_allow_html=True,
    )
    t1, t2, t3, t4 = st.sidebar.columns(4)
    with t1:
        if st.button("30N", width="stretch", key="date_30d"):
            st.session_state.date_range = [
                max(min_date, max_date - pd.Timedelta(days=29)),
                max_date,
            ]
    with t2:
        if st.button("90N", width="stretch", key="date_90d"):
            st.session_state.date_range = [
                max(min_date, max_date - pd.Timedelta(days=89)),
                max_date,
            ]
    with t3:
        if st.button("YTD", width="stretch", key="date_ytd"):
            start_of_year = datetime(max_date.year, 1, 1).date()
            st.session_state.date_range = [max(min_date, start_of_year), max_date]
    with t4:
        if st.button("Full", width="stretch", key="date_full"):
            st.session_state.date_range = [min_date, max_date]

    dr = st.sidebar.date_input(
        "Chọn khoảng thời gian",
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
    st.sidebar.success(
        f"Dữ liệu đang xét: {len(side_df):,}/{len(DF):,} bản ghi (sau lọc/tổng)"
    )

    if not side_df.empty:
        side_avg_aqi = int(side_df["aqi"].mean())
        side_health_hd, side_health_tx, side_health_color = aqi_health_guidance(
            side_avg_aqi
        )
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
        c
        for c in [
            "aqi",
            "pm2_5",
            "pm10",
            "o3",
            "no2",
            "so2",
            "co",
            "temp",
            "humidity",
            "wind_speed",
            "rain",
        ]
        if c in side_df.columns
    ]
    if quality_cols and not side_df.empty:
        missing_rate = (side_df[quality_cols].isna().mean() * 100).sort_values(
            ascending=False
        )
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

    csv_name = (
        f"vietnam_aqi_filtered_{s_d.strftime('%Y%m%d')}_{e_d.strftime('%Y%m%d')}.csv"
    )
    csv_bytes = to_csv_bytes(side_df)
    st.sidebar.download_button(
        "Tải CSV theo bộ lọc hiện tại",
        data=csv_bytes,
        file_name=csv_name,
        mime="text/csv",
        width="stretch",
        help="Xuất toàn bộ dữ liệu sau khi lọc khu vực và thời gian.",
    )

    st.sidebar.markdown(
        "<div class='sidebar-section-title'>Mật độ biểu đồ</div>",
        unsafe_allow_html=True,
    )
    city_cap_max = max(1, len(selected_cities) if selected_cities else len(all_cities))
    city_cap_min = 1 if city_cap_max < 8 else 8
    city_cap_default = min(
        max(st.session_state.city_chart_limit, city_cap_min), city_cap_max
    )
    st.session_state.city_chart_limit = city_cap_default
    city_cap = st.sidebar.slider(
        "Số khu vực tối đa trên biểu đồ dài",
        min_value=city_cap_min,
        max_value=city_cap_max,
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
        DF["city"].isin(sel)
        & DF["band"].isin(sel_bands)
        & (DF["date_ts"] >= start_date_ts)
        & (DF["date_ts"] <= end_date_ts)
    ].copy()

    days = max(1, (e_d - s_d).days + 1)
    if df.empty:
        st.warning("Không có dữ liệu.")
        st.stop()

    P_KEYS = [k for k in POLLS if k in df.columns]
    CITY_CLR = {
        c: CITY_PALETTE[i % len(CITY_PALETTE)]
        for i, c in enumerate(sorted(df["city"].unique()))
    }
    city_aqi_mean = df.groupby("city")["aqi"].mean().sort_values(ascending=False)

    avg_aqi = int(df["aqi"].mean())
    avg_pm25 = round(df["pm2_5"].mean(), 1)
    dangerp = round((df["aqi"] > 150).mean() * 100, 1)
    worst = city_aqi_mean.index[0]
    cig_n = round(avg_pm25 / 22.0 * days, 1)
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

    daily_trend = df.groupby("date")[["aqi", "pm2_5"]].mean().sort_index()
    if len(daily_trend) >= 2:
        aqi_1d_text, aqi_1d_color = fmt_delta(
            daily_trend["aqi"].iloc[-1], daily_trend["aqi"].iloc[-2]
        )
        pm_1d_text, pm_1d_color = fmt_delta(
            daily_trend["pm2_5"].iloc[-1], daily_trend["pm2_5"].iloc[-2], " µg"
        )
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
        now_rank = (
            city_day[city_day["date"] == last_date]
            .sort_values("aqi", ascending=False)["city"]
            .tolist()
        )
        prv_rank = (
            city_day[city_day["date"] == prev_date]
            .sort_values("aqi", ascending=False)["city"]
            .tolist()
        )
        all_rank_cities = sorted(set(now_rank) | set(prv_rank))
        fallback_rank = len(all_rank_cities) + 1
        rank_now_map = {city: i + 1 for i, city in enumerate(now_rank)}
        rank_prev_map = {city: i + 1 for i, city in enumerate(prv_rank)}

        shift_rows = []
        for city in all_rank_cities:
            shift = rank_prev_map.get(city, fallback_rank) - rank_now_map.get(
                city, fallback_rank
            )
            if shift != 0:
                shift_rows.append((city, shift))

        up_moves = sorted(
            [r for r in shift_rows if r[1] > 0], key=lambda x: x[1], reverse=True
        )[:2]
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
    return locals()
