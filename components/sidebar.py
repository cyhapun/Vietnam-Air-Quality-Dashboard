import pandas as pd
import streamlit as st
from datetime import datetime

from services.data_loader import (
    load_province_detail_data,
    merge_overview_with_loaded_details,
)
from utils.helpers import (
    AQI_DEF,
    CITY_PALETTE,
    POLLS,
    UI_MODES,
    aqi_health_guidance,
    aqi_meta,
    fmt_delta,
    rank_rows_html,
    set_plot_theme,
    ui_mode_css,
)


PROVINCE_PLACEHOLDER = "Chọn tỉnh"
NAV_OVERVIEW = "overview"
NAV_PROVINCE_DETAIL = "province_detail"


def _extract_ward_options(detail_df: pd.DataFrame) -> list[str]:
    if detail_df is None or detail_df.empty:
        return []

    if "location" in detail_df.columns:
        wards = (
            detail_df["location"]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .unique()
            .tolist()
        )
        return sorted(wards)

    city_series = detail_df.get("city", pd.Series(dtype=str)).dropna().astype(str)
    wards = []
    for city in city_series.unique().tolist():
        if " - " in city:
            wards.append(city.split(" - ", 1)[1].strip())
    return sorted(set([w for w in wards if w]))


def _display_city_name(city_name: str, province: str | None = None) -> str:
    text = str(city_name).strip()
    if not text:
        return text
    if " - " in text:
        return text.split(" - ", 1)[1].strip()
    if province:
        prefix = f"{province} - "
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _normalize_selected_wards(selected: list[str], options: list[str]) -> list[str]:
    if not selected:
        return []

    normalized = [str(x).strip() for x in selected if str(x).strip()]
    return [x for x in normalized if x in options]


def render_sidebar(DF):
    province_options = sorted(DF["province"].dropna().unique().tolist())
    province_select_options = [PROVINCE_PLACEHOLDER, *province_options]

    if "selected_province" not in st.session_state:
        st.session_state.selected_province = None

    if (
        "overview_selected_province_ui" not in st.session_state
        or st.session_state.overview_selected_province_ui not in province_select_options
    ):
        st.session_state.overview_selected_province_ui = PROVINCE_PLACEHOLDER

    if st.session_state.selected_province not in province_options:
        st.session_state.selected_province = None

    if "loaded_province_details" not in st.session_state:
        st.session_state.loaded_province_details = {}
    if "nav_mode" not in st.session_state:
        st.session_state.nav_mode = NAV_OVERVIEW
    if st.session_state.nav_mode not in [NAV_OVERVIEW, NAV_PROVINCE_DETAIL]:
        st.session_state.nav_mode = NAV_OVERVIEW
    if "selected_wards" not in st.session_state:
        st.session_state.selected_wards = []
    if "selected_wards_custom_ui" not in st.session_state:
        st.session_state.selected_wards_custom_ui = []
    if "ward_select_mode" not in st.session_state:
        st.session_state.ward_select_mode = "all"
    if "ward_select_all_checkbox" not in st.session_state:
        st.session_state.ward_select_all_checkbox = True
    if "ui_mode" not in st.session_state:
        st.session_state.ui_mode = UI_MODES[0]
    if "reduce_motion" not in st.session_state:
        st.session_state.reduce_motion = False

    nav_mode = st.session_state.nav_mode
    requested_province = st.session_state.get("selected_province")

    if nav_mode == NAV_PROVINCE_DETAIL and not requested_province:
        st.session_state.nav_mode = NAV_OVERVIEW
        st.session_state.selected_wards = []
        st.session_state.selected_wards_custom_ui = []
        st.session_state.ward_select_mode = "all"
        st.session_state.ward_select_all_checkbox = True
        nav_mode = NAV_OVERVIEW

    st.sidebar.markdown(
        """
        <style>
        .sidebar-dashboard-top {
            border-radius: 18px;
            padding: 12px;
            margin: 0 0 12px 0;
            background: linear-gradient(155deg, #f7fbff 0%, #e7f1ff 100%);
            border: 1px solid #cbdff9;
            box-shadow: 0 8px 18px rgba(15, 76, 129, 0.08);
        }
        .sidebar-dashboard-title {
            margin: 0 0 9px 0;
            color: #18334e;
            font-size: 1.16rem;
            font-weight: 800;
            letter-spacing: 0.2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        f"""
        <div class='sidebar-dashboard-top'>
            <p class='sidebar-dashboard-title'>Bảng Điều Khiển</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    set_plot_theme(st.session_state.ui_mode)
    st.markdown(
        ui_mode_css(st.session_state.ui_mode, st.session_state.reduce_motion),
        unsafe_allow_html=True,
    )

    if nav_mode == NAV_OVERVIEW:
        st.sidebar.markdown(
            "<div class='sidebar-section-title'>Điều hướng dữ liệu</div>",
            unsafe_allow_html=True,
        )
        selected_overview = st.sidebar.selectbox(
            "Chọn tỉnh",
            options=province_select_options,
            key="overview_selected_province_ui",
            help="Chọn tỉnh để nạp dữ liệu xã/phường của tỉnh đó.",
        )
        if selected_overview in province_options:
            st.session_state.selected_province = selected_overview
            requested_province = selected_overview
            st.session_state.nav_mode = NAV_PROVINCE_DETAIL
            nav_mode = NAV_PROVINCE_DETAIL
            st.session_state.selected_wards = []
            st.session_state.selected_wards_custom_ui = []
            st.session_state.ward_select_mode = "all"
            st.session_state.ward_select_all_checkbox = True
        else:
            st.session_state.selected_province = None
    if nav_mode == NAV_PROVINCE_DETAIL and requested_province:
        cached_detail = st.session_state.loaded_province_details.get(requested_province)
        need_load_detail = (
            requested_province not in st.session_state.loaded_province_details
            or not isinstance(cached_detail, pd.DataFrame)
            or cached_detail.empty
        )
        if need_load_detail:
            with st.spinner(f"Đang tải chi tiết {requested_province}..."):
                st.session_state.loaded_province_details[requested_province] = (
                    load_province_detail_data(requested_province)
                )

    merged_df = merge_overview_with_loaded_details(
        DF,
        st.session_state.loaded_province_details,
    )

    if nav_mode == NAV_PROVINCE_DETAIL and requested_province:
        # In detail mode, lock all downstream filtering to the selected province only.
        active_df = merged_df[merged_df["province"] == requested_province].copy()
    else:
        active_df = DF

    all_cities = sorted(active_df["city"].unique())
    mn_date = active_df["timestamp"].min().date()
    mx_date = active_df["timestamp"].max().date()

    if "selected_cities" not in st.session_state:
        st.session_state.selected_cities = all_cities

    if "date_range" not in st.session_state:
        st.session_state.date_range = [mn_date, mx_date]

    loaded_provinces = sorted(
        [
            p
            for p, d in st.session_state.loaded_province_details.items()
            if isinstance(d, pd.DataFrame) and not d.empty
        ]
    )
    if nav_mode == NAV_OVERVIEW and loaded_provinces:
        st.sidebar.caption(f"Đã tải chi tiết: {len(loaded_provinces)} tỉnh")

    if nav_mode == NAV_PROVINCE_DETAIL and requested_province:
        p1, p2 = st.sidebar.columns([2.6, 1.4])
        with p1:
            st.markdown(f"**{requested_province}**")
        with p2:
            if st.button("Quay lại", use_container_width=True, key="btn_back_overview"):
                st.session_state.nav_mode = NAV_OVERVIEW
                st.session_state.selected_province = None
                st.session_state.overview_selected_province_ui = PROVINCE_PLACEHOLDER
                st.session_state.selected_wards = []
                st.session_state.selected_wards_custom_ui = []
                st.session_state.ward_select_mode = "all"
                st.session_state.ward_select_all_checkbox = True
                st.session_state.selected_cities = []
                st.rerun()

        detail_df = st.session_state.loaded_province_details.get(
            requested_province, pd.DataFrame()
        )
        ward_options = _extract_ward_options(detail_df)
        st.session_state.selected_wards = [
            w for w in st.session_state.selected_wards if w in ward_options
        ]
        st.session_state.selected_wards_custom_ui = [
            w for w in st.session_state.selected_wards_custom_ui if w in ward_options
        ]

        if st.session_state.ward_select_mode not in ["all", "custom"]:
            st.session_state.ward_select_mode = (
                "custom" if st.session_state.selected_wards else "all"
            )

        if st.session_state.ward_select_mode == "custom":
            st.session_state.selected_wards = _normalize_selected_wards(
                st.session_state.selected_wards_custom_ui,
                ward_options,
            )

            if ward_options and len(st.session_state.selected_wards) >= len(
                ward_options
            ):
                st.session_state.ward_select_mode = "all"
                st.session_state.selected_wards = []
                st.session_state.selected_wards_custom_ui = []
                st.session_state.ward_select_all_checkbox = True

        selected_wards_effective = _normalize_selected_wards(
            st.session_state.selected_wards,
            ward_options,
        )
        total_wards = len(ward_options)

        if st.session_state.ward_select_mode == "all" or not selected_wards_effective:
            ward_counter_text = "Tất cả"
        else:
            ward_counter_text = f"{len(selected_wards_effective)}/{total_wards}"

        st.sidebar.markdown(
            f"""
            <div style='display:flex;justify-content:space-between;align-items:center;margin:6px 0 4px;'>
                <div class='sidebar-section-title' style='margin:0;'>Xã/Phường</div>
                <span style='font-size:.72rem;font-weight:700;color:#0f4c81;background:rgba(14,165,233,.12);border:1px solid rgba(14,165,233,.35);padding:2px 8px;border-radius:999px;'>
                    {ward_counter_text}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        select_all_checked = st.sidebar.checkbox(
            f"Tất cả xã/phường ({total_wards})",
            key="ward_select_all_checkbox",
            disabled=(total_wards == 0),
        )

        ward_mode = "all" if select_all_checked else "custom"
        st.session_state.ward_select_mode = ward_mode

        if ward_mode == "all":
            st.session_state.selected_wards = []
            st.session_state.selected_wards_custom_ui = []
            selected_wards_effective = []
        else:
            selected_wards_raw = st.sidebar.multiselect(
                "Danh sách xã/phường",
                options=ward_options,
                key="selected_wards_custom_ui",
                label_visibility="collapsed",
            )
            selected_wards_effective = _normalize_selected_wards(
                selected_wards_raw,
                ward_options,
            )
            st.session_state.selected_wards = selected_wards_effective

        province_scope_df = active_df
        if selected_wards_effective:
            if "location" in province_scope_df.columns:
                province_scope_df = province_scope_df[
                    province_scope_df["location"]
                    .fillna("")
                    .astype(str)
                    .isin(selected_wards_effective)
                ]
            else:
                province_scope_df = province_scope_df[
                    province_scope_df["city"]
                    .astype(str)
                    .apply(
                        lambda x: (" - " in x)
                        and (x.split(" - ", 1)[1] in selected_wards_effective)
                    )
                ]

        selected_cities = sorted(province_scope_df["city"].dropna().unique().tolist())
        st.session_state.selected_cities = selected_cities

        selected_count = len(selected_cities)
        preview_names = selected_cities[:3]
        preview_chips = "".join(
            [
                f"<span class='mini-city-chip'>{_display_city_name(c, requested_province)}</span>"
                for c in preview_names
            ]
        )
        if selected_count > 3:
            preview_chips += (
                f"<span class='mini-city-chip'>+{selected_count - 3} khu vực</span>"
            )

        st.sidebar.markdown(
            f"""
            <div class='sidebar-selection-summary sidebar-selection-summary-soft'>
                <div class='summary-count summary-count-soft'>Đang xem {selected_count} khu vực thuộc {requested_province}</div>
                <div>{preview_chips if preview_chips else "<span style='font-size:0.76rem;color:#64748b;'>Không có khu vực phù hợp</span>"}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            "<div class='sidebar-section-title'>Lọc khu vực</div>",
            unsafe_allow_html=True,
        )
        st.session_state.selected_wards = []
        st.session_state.selected_wards_custom_ui = []
        st.session_state.ward_select_mode = "all"
        st.session_state.ward_select_all_checkbox = True
        st.session_state.selected_cities = [
            c for c in st.session_state.selected_cities if c in all_cities
        ]
        if not st.session_state.selected_cities:
            st.session_state.selected_cities = all_cities

        st.sidebar.markdown(
            "<div class='sidebar-inline-label'>Lọc nhanh:</div>",
            unsafe_allow_html=True,
        )
        btn1, btn2, btn3 = st.sidebar.columns([1.0, 1.0, 1.0])
        with btn1:
            if st.button("Tất cả", use_container_width=True, key="btn_all_cities"):
                st.session_state.selected_cities = all_cities
        with btn2:
            if st.button("AQI cao", use_container_width=True, key="btn_hotspot"):
                top_cities = (
                    active_df.groupby("city")["aqi"]
                    .mean()
                    .sort_values(ascending=False)
                    .head(min(8, len(all_cities)))
                    .index.tolist()
                )
                st.session_state.selected_cities = top_cities
        with btn3:
            if st.button("×", use_container_width=True, key="btn_clear_cities"):
                st.session_state.selected_cities = []

        selected_count = len(st.session_state.selected_cities)
        preview_names = st.session_state.selected_cities[:3]
        preview_chips = "".join(
            [f"<span class='mini-city-chip'>{c}</span>" for c in preview_names]
        )
        if selected_count > 3:
            preview_chips += (
                f"<span class='mini-city-chip'>+{selected_count - 3} khu vực</span>"
            )

        st.sidebar.markdown(
            "<div class='sidebar-hint' style='margin-top:4px;margin-bottom:4px;'>Đang xem:</div>",
            unsafe_allow_html=True,
        )
        st.sidebar.markdown(
            f"""
            <div class='sidebar-selection-summary'>
                <div class='summary-count'>{selected_count} khu vực</div>
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

    if selected_cities:
        city_scope_df = active_df[active_df["city"].isin(selected_cities)]
    elif nav_mode == NAV_PROVINCE_DETAIL and requested_province:
        city_scope_df = active_df[active_df["province"] == requested_province]
    else:
        city_scope_df = active_df

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
        if st.button("30N", use_container_width=True, key="date_30d"):
            st.session_state.date_range = [
                max(min_date, max_date - pd.Timedelta(days=29)),
                max_date,
            ]
    with t2:
        if st.button("90N", use_container_width=True, key="date_90d"):
            st.session_state.date_range = [
                max(min_date, max_date - pd.Timedelta(days=89)),
                max_date,
            ]
    with t3:
        if st.button("YTD", use_container_width=True, key="date_ytd"):
            start_of_year = datetime(max_date.year, 1, 1).date()
            st.session_state.date_range = [max(min_date, start_of_year), max_date]
    with t4:
        if st.button("Full", use_container_width=True, key="date_full"):
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

    aqi_opts = [b[2] for b in AQI_DEF]
    sel_bands = aqi_opts

    if not sel and nav_mode == NAV_PROVINCE_DETAIL and requested_province:
        sel = sorted(
            active_df.loc[active_df["province"] == requested_province, "city"]
            .dropna()
            .unique()
            .tolist()
        )

    if not sel:
        st.warning("Vui lòng chọn ít nhất 1 khu vực để hiển thị.")
        st.stop()

    # Fixed cap after removing sidebar density control.
    city_cap = min(18, max(1, len(sel)))

    # ── FILTER DATA ──
    df = active_df[
        active_df["city"].isin(sel)
        & active_df["band"].isin(sel_bands)
        & (active_df["date_ts"] >= start_date_ts)
        & (active_df["date_ts"] <= end_date_ts)
    ].copy()

    if nav_mode == NAV_PROVINCE_DETAIL and requested_province and "city" in df.columns:
        # Keep internal selection keys unchanged; only simplify names for UI rendering.
        df["city"] = (
            df["city"]
            .astype(str)
            .apply(lambda c: _display_city_name(c, requested_province))
        )

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

    loaded_detail_rows = sum(
        len(d)
        for d in st.session_state.loaded_province_details.values()
        if isinstance(d, pd.DataFrame)
    )

    # ═══════════════════════════════════════════════════════════════════
    return locals()
