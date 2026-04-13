import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import base64
import os
import textwrap


def _safe_pm25_mean(df):
    if "pm2_5" not in df.columns:
        return 0.0
    val = df["pm2_5"].mean()
    return 0.0 if pd.isna(val) else float(val)


def _build_scope_metrics(df, state):
    _aqi_meta = state["aqi_meta"]
    _aqi_health_guidance = state["aqi_health_guidance"]
    _fmt_delta = state["fmt_delta"]
    city_col = "province" if "province" in df.columns else "city"
    city_aqi_mean = (
        df.groupby(city_col)["aqi"].mean().sort_values(ascending=False)
        if city_col in df.columns
        else pd.Series(dtype=float)
    )
    avg_aqi = int(df["aqi"].mean()) if not df["aqi"].dropna().empty else 0
    avg_pm25 = round(_safe_pm25_mean(df), 1)
    dangerp = round((df["aqi"] > 150).mean() * 100, 1) if len(df) else 0.0
    worst = city_aqi_mean.index[0] if not city_aqi_mean.empty else "N/A"
    days = max(1, (df["date_ts"].max() - df["date_ts"].min()).days + 1)
    cig_n = round(avg_pm25 / 22.0 * days, 1)
    _lbl, _col = _aqi_meta(avg_aqi)
    health_hd, _, _ = _aqi_health_guidance(avg_aqi)
    who_pm25_multi = round(max(avg_pm25, 0.1) / 5.0, 1)
    latest_obs = df["timestamp"].max()

    daily_trend = df.groupby("date")[["aqi", "pm2_5"]].mean().sort_index()
    if len(daily_trend) >= 2:
        aqi_1d_text, aqi_1d_color = _fmt_delta(
            daily_trend["aqi"].iloc[-1], daily_trend["aqi"].iloc[-2]
        )
        pm_1d_text, pm_1d_color = _fmt_delta(
            daily_trend["pm2_5"].iloc[-1], daily_trend["pm2_5"].iloc[-2], " µg"
        )
    else:
        aqi_1d_text, aqi_1d_color = _fmt_delta(0, None)
        pm_1d_text, pm_1d_color = _fmt_delta(0, None)

    if len(daily_trend) >= 14:
        curr_7d = daily_trend.tail(7).mean()
        prev_7d = daily_trend.iloc[-14:-7].mean()
        aqi_7d_text, aqi_7d_color = _fmt_delta(curr_7d["aqi"], prev_7d["aqi"])
        pm_7d_text, pm_7d_color = _fmt_delta(curr_7d["pm2_5"], prev_7d["pm2_5"], " µg")
    else:
        aqi_7d_text, aqi_7d_color = _fmt_delta(0, None)
        pm_7d_text, pm_7d_color = _fmt_delta(0, None)

    rank_up_line = "Chưa đủ dữ liệu để so sánh thứ hạng ngày gần nhất."
    rank_down_line = ""
    if len(daily_trend) >= 2 and city_col in df.columns:
        last_date = daily_trend.index[-1]
        prev_date = daily_trend.index[-2]
        city_day = df.groupby(["date", city_col])["aqi"].mean().reset_index()
        now_rank = (
            city_day[city_day["date"] == last_date]
            .sort_values("aqi", ascending=False)[city_col]
            .tolist()
        )
        prv_rank = (
            city_day[city_day["date"] == prev_date]
            .sort_values("aqi", ascending=False)[city_col]
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

    derived_state = dict(state)
    derived_state.update(
        {
            "avg_aqi": avg_aqi,
            "avg_pm25": avg_pm25,
            "dangerp": dangerp,
            "worst": worst,
            "days": days,
            "cig_n": cig_n,
            "_lbl": _lbl,
            "_col": _col,
            "health_hd": health_hd,
            "who_pm25_multi": who_pm25_multi,
            "latest_obs": latest_obs,
            "aqi_1d_text": aqi_1d_text,
            "aqi_1d_color": aqi_1d_color,
            "pm_1d_text": pm_1d_text,
            "pm_1d_color": pm_1d_color,
            "aqi_7d_text": aqi_7d_text,
            "aqi_7d_color": aqi_7d_color,
            "pm_7d_text": pm_7d_text,
            "pm_7d_color": pm_7d_color,
            "rank_up_line": rank_up_line,
            "rank_down_line": rank_down_line,
            "sel": sorted(df[city_col].dropna().unique().tolist()) if city_col in df.columns else [],
            "df": df,
            "plot_city_limit": len(city_aqi_mean),
            "city_priority": city_aqi_mean.index.tolist(),
            "is_city_trimmed": False,
        }
    )
    return derived_state


def render_overview(state, df_override=None, scope_label="Việt Nam"):
    if df_override is not None and not df_override.empty:
        local_state = _build_scope_metrics(df_override, state)
    else:
        local_state = state
    globals().update(local_state)
    AQI_DEF = local_state["AQI_DEF"]
    _col = local_state["_col"]
    avg_aqi = local_state["avg_aqi"]
    _lbl = local_state["_lbl"]
    avg_pm25 = local_state["avg_pm25"]
    cig_n = local_state["cig_n"]
    days = local_state["days"]
    worst = local_state["worst"]
    dangerp = local_state["dangerp"]
    aqi_1d_color = local_state["aqi_1d_color"]
    aqi_1d_text = local_state["aqi_1d_text"]
    pm_1d_color = local_state["pm_1d_color"]
    pm_1d_text = local_state["pm_1d_text"]
    aqi_7d_color = local_state["aqi_7d_color"]
    aqi_7d_text = local_state["aqi_7d_text"]
    pm_7d_color = local_state["pm_7d_color"]
    pm_7d_text = local_state["pm_7d_text"]
    rank_up_line = local_state["rank_up_line"]
    rank_down_line = local_state["rank_down_line"]
    health_hd = local_state["health_hd"]
    latest_obs = local_state["latest_obs"]
    who_pm25_multi = local_state["who_pm25_multi"]
    sel = local_state["sel"]
    df = local_state["df"]
    is_city_trimmed = local_state["is_city_trimmed"]
    plot_city_limit = local_state["plot_city_limit"]
    city_priority = local_state["city_priority"]
    vietnam_svg_base64 = local_state.get("vietnam_svg_base64", "")
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    hero_bg_html = ""
    if vietnam_svg_base64:
        hero_bg_html = (
            "<div class='iq-hero-vn-bg' "
            f"style=\"background-image:url('data:image/svg+xml;base64,{vietnam_svg_base64}')\"></div>"
        )

    st.markdown(f"""
    <div class="kpi-strip">
      <div class="kpi-box accent-blue">
        <div class="kpi-lbl">AQI phạm vi chọn</div>
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

    aqi_reference = [(lo, hi, label) for lo, hi, label, _ in AQI_DEF]
    pm25_warning_map = {
        "Tốt": "Không có cảnh báo đáng kể.",
        "Vừa phải": "Nhóm nhạy cảm nên giảm vận động ngoài trời.",
        "Không lành mạnh cho các nhóm nhạy cảm": "Nhóm nhạy cảm tránh hoạt động ngoài trời kéo dài.",
        "Không khỏe mạnh": "Hạn chế ra ngoài, ưu tiên khẩu trang lọc bụi mịn.",
        "Rất không tốt cho sức khỏe": "Tránh hoạt động gắng sức ngoài trời.",
        "Nguy hiểm": "Mọi người nên hạn chế tối đa hoạt động ngoài trời.",
    }
    current_band = next(
        (item for item in aqi_reference if item[0] <= avg_aqi <= item[1]),
        aqi_reference[-1],
    )
    current_pm_warning = pm25_warning_map.get(
        current_band[2], "Theo dõi AQI theo thời gian thực."
    )
    action_line = (
        "Ưu tiên hoạt động trong nhà giờ cao điểm ô nhiễm."
        if dangerp >= 20
        else "Có thể sinh hoạt bình thường, vẫn nên theo dõi AQI theo giờ."
    )

    insight_block_html = textwrap.dedent(
        f"""
    <div class="aqi-insight-wrap in-hero">
        <div class="aqi-insight-grid">
            <div class="aqi-insight-card">
                <div class="aqi-insight-kicker">Mức hiện tại</div>
                <div class="aqi-insight-main">AQI {avg_aqi} · {current_band[2]}</div>
                <div class="aqi-insight-sub">{health_hd}</div>
            </div>
            <div class="aqi-insight-card">
                <div class="aqi-insight-kicker">Cảnh báo PM2.5</div>
                <div class="aqi-insight-main">Khuyến nghị ưu tiên</div>
                <div class="aqi-insight-sub">{current_pm_warning}</div>
            </div>
            <div class="aqi-insight-card">
                <div class="aqi-insight-kicker">Insight vận hành</div>
                <div class="aqi-insight-main">Theo dõi theo giờ</div>
                <div class="aqi-insight-sub">{action_line}</div>
            </div>
        </div>
    </div>
    """
    )

    latest_obs_text = (
        latest_obs.strftime("%H:%M · %d/%m/%Y") if pd.notna(latest_obs) else "N/A"
    )
    iqair_hybrid_html = (
        f"<div class='iq-wrap'>"
        f"<div class='iq-live-head'>"
        f"<div class='iq-title'>Live AQI Vietnam · IQAir Hybrid</div>"
        f"<div class='iq-meta'>Cập nhật gần nhất: {latest_obs_text} · Dữ liệu từ bộ cảm biến nội bộ</div>"
        f"</div>"
        f"<div class='iq-card iq-card-hero'>"
        f"{hero_bg_html}"
        f"<div class='iq-hero-content'>"
        f"<div class='iq-hero-kicker'>Chất lượng không khí tại {scope_label}</div>"
        f"<div class='iq-hero-row'>"
        f"<div class='iq-hero-aqi' style='color:{_col}'>{avg_aqi}</div>"
        f"<div class='iq-hero-status'>{_lbl}</div>"
        f"</div>"
        f"<div class='iq-hero-sub'>PM2.5 trung bình hiện tại: <strong>{avg_pm25} µg/m³</strong></div>"
        f"<div class='iq-hero-sub'>Nồng độ PM2.5 đang cao gấp <strong>{who_pm25_multi} lần</strong> mức hướng dẫn năm của WHO (5 µg/m³).</div>"
        f"<div class='iq-chip-row'>"
        f"<span class='iq-chip'>{len(sel)} khu vực</span>"
        f"<span class='iq-chip'>{len(df):,} bản ghi</span>"
        f"<span class='iq-chip'>{dangerp}% giờ AQI > 150</span>"
        f"</div>"
        f"{insight_block_html}"
        f"</div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(iqair_hybrid_html, unsafe_allow_html=True)

    if is_city_trimmed:
        st.caption(
            f"Hiển thị Top {plot_city_limit}/{len(city_priority)} khu vực theo AQI trung bình cho các biểu đồ theo thành phố để giữ bố cục gọn."
        )


def render(df):
    ctx = st.session_state.get("dashboard_context")
    if ctx is None:
        st.error("Thiếu ngữ cảnh dashboard.")
        st.stop()
    globals().update(ctx)
    st.markdown(
        '<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Bản đồ AQI theo khu vực</div><div class="card-sub">Màu sắc biểu diễn AQI trung bình, kích thước điểm phản ánh PM2.5.</div>',
        unsafe_allow_html=True,
    )
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
    ).fillna(AQI_DEF[-1][2])
    city_geo["marker_size"] = (city_geo["pm2_5"].clip(lower=8) * 0.7).clip(
        lower=8, upper=28
    )
    aqi_cap = AQI_DEF[-1][1]
    # Build a smooth AQI gradient by interpolating between AQI_DEF color anchors.
    def _hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _mix_color(c1, c2, t):
        r1, g1, b1 = _hex_to_rgb(c1)
        r2, g2, b2 = _hex_to_rgb(c2)
        return _rgb_to_hex(
            (
                int(r1 + (r2 - r1) * t),
                int(g1 + (g2 - g1) * t),
                int(b1 + (b2 - b1) * t),
            )
        )

    color_stops = [(0, AQI_DEF[0][3])] + [(hi, col) for _, hi, _, col in AQI_DEF]
    aqi_colorscale = []
    smooth_steps = 4
    for i in range(len(color_stops) - 1):
        v1, c1 = color_stops[i]
        v2, c2 = color_stops[i + 1]
        for s in range(smooth_steps):
            t = s / smooth_steps
            v = v1 + (v2 - v1) * t
            aqi_colorscale.append([v / aqi_cap, _mix_color(c1, c2, t)])
    aqi_colorscale.append([1.0, AQI_DEF[-1][3]])

    fig_map = go.Figure(
        go.Scattermapbox(
            lat=city_geo["lat"],
            lon=city_geo["lon"],
            mode="markers",
            text=city_geo["city"],
            marker=dict(
                size=city_geo["marker_size"],
                color=city_geo["aqi"],
                colorscale=aqi_colorscale,
                cmin=0,
                cmax=aqi_cap,
                opacity=0.84,
                colorbar=dict(
                    title="AQI",
                    thickness=10,
                    tickfont=dict(size=8),
                    tickvals=[(lo + hi) / 2 for lo, hi, _, _ in AQI_DEF],
                    ticktext=[
                        f"{lo}-{hi}: {lbl}" if hi < AQI_DEF[-1][1] else f"{lo}+: {lbl}"
                        for lo, hi, lbl, _ in AQI_DEF
                    ],
                    x=1.01,
                ),
            ),
            customdata=np.stack(
                [city_geo["aqi_lbl"], city_geo["pm2_5"].round(1), city_geo["n"]],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "AQI TB: %{marker.color:.1f} (%{customdata[0]})<br>"
                "PM2.5 TB: %{customdata[1]} µg/m³<br>"
                "Số quan trắc: %{customdata[2]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig_map.update_layout(
        mapbox=dict(
            style="carto-positron",
            center=dict(
                lat=float(city_geo["lat"].mean()), lon=float(city_geo["lon"].mean())
            ),
            zoom=4.5,
        ),
        margin=dict(l=2, r=2, t=6, b=2),
        height=430,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Be Vietnam Pro", size=10, color="#334155"),
    )
    st.plotly_chart(
        fig_map,
        width="stretch",
        config={"displayModeBar": False, "scrollZoom": True},
    )
    st.markdown("</div>", unsafe_allow_html=True)

    rank_now = city_geo.sort_values("aqi", ascending=False).head(8).copy()
    rank_clean = city_geo.sort_values("aqi", ascending=True).head(8).copy()

    def _aqi_badge(val):
        _, badge_col = aqi_meta(float(val))
        badge_text = "#ffffff" if float(val) >= 151 else "#0f172a"
        return badge_col, badge_text

    def _rows_html(rank_df):
        rows = []
        for idx, row in enumerate(rank_df.itertuples(index=False), start=1):
            badge_col, badge_text = _aqi_badge(row.aqi)
            highlight_cls = " ov-live-row-top" if idx == 1 else ""
            rows.append(
                f"<div class='ov-live-row{highlight_cls}'>"
                f"<div class='ov-live-col ov-live-no'>{idx}</div>"
                f"<div class='ov-live-col ov-live-city'><span class='ov-flag-icon'>★</span> {row.city}</div>"
                f"<div class='ov-live-col ov-live-aqi'><span class='ov-aqi-pill' style='background:{badge_col};color:{badge_text}'>{row.aqi:.0f}</span></div>"
                "</div>"
            )
        return "".join(rows)


    year_city = (
        df.assign(year=df["timestamp"].dt.year)
        .groupby(["year", "city"], as_index=False)["aqi"]
        .mean()
        .dropna()
    )
    target_year = 2025

    def _year_stat(target_year, polluted=True):
        if target_year is None:
            return "N/A", "Chưa có dữ liệu", np.nan
        ydf = year_city[year_city["year"] == target_year]
        if ydf.empty:
            return str(target_year), "Chưa có dữ liệu", np.nan
        row = ydf.sort_values("aqi", ascending=not polluted).iloc[0]
        return str(int(target_year)), str(row["city"]), float(row["aqi"])

    now_hot_year, now_hot_city, now_hot_val = _year_stat(target_year, polluted=True)
    now_clean_year, now_clean_city, now_clean_val = _year_stat(
        target_year, polluted=False
    )

    def _badge_html(v):
        if pd.isna(v):
            return "<span class='ov-aqi-pill ov-aqi-pill-na'>N/A</span>"
        bg, tx = _aqi_badge(v)
        return f"<span class='ov-aqi-pill' style='background:{bg};color:{tx}'>{v:.0f}</span>"

    rank_left, rank_right = st.columns(2, gap="small")
    with rank_left:
        st.markdown(
            f"""
            <div class="ov-live-card">
                <div class="ov-live-head">Xếp hạng trực tiếp thành phố ô nhiễm nhất</div>
                <div class="ov-live-sub">Xếp hạng thành phố ô nhiễm nhất tại Việt Nam theo thời gian thực</div>
                <div class="ov-live-table-head">
                    <div>#</div><div>Thành phố</div><div>AQI Mỹ</div>
                </div>
                {_rows_html(rank_now)}
                <div class="ov-year-cell ov-year-hot">
                    <div class="ov-year-title">{now_hot_year} thành phố ô nhiễm nhất tại Việt Nam</div>
                    <div class="ov-year-row">
                        <div class="ov-year-city">{now_hot_city}</div>
                        {_badge_html(now_hot_val)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with rank_right:
        st.markdown(
            f"""
            <div class="ov-live-card">
                <div class="ov-live-head">Xếp hạng trực tiếp thành phố sạch nhất</div>
                <div class="ov-live-sub">Xếp hạng thành phố sạch nhất tại Việt Nam theo thời gian thực</div>
                <div class="ov-live-table-head">
                    <div>#</div><div>Thành phố</div><div>AQI Mỹ</div>
                </div>
                {_rows_html(rank_clean)}
                <div class="ov-year-cell ov-year-clean">
                    <div class="ov-year-title">{now_clean_year} thành phố sạch nhất tại Việt Nam</div>
                    <div class="ov-year-row">
                        <div class="ov-year-city">{now_clean_city}</div>
                        {_badge_html(now_clean_val)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    cO3, cO4 = st.columns([2.5, 1.5], gap="small")
    with cO3:
        period_labels = {"Ngày": "D", "Tuần": "W", "Tháng": "ME"}
        if "ov_trend_period" not in st.session_state:
            st.session_state["ov_trend_period"] = "Ngày"
        st.markdown(
            '<div class="card trend-card"><div class="card-title"><span class="q-tag">Overview</span>Xu hướng AQI và PM2.5</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="pill-group-wrap">', unsafe_allow_html=True)
        pill_cols = st.columns([1, 1, 1, 3])
        for idx, label in enumerate(period_labels):
            is_active = st.session_state["ov_trend_period"] == label
            with pill_cols[idx]:
                if st.button(
                    label,
                    key=f"ov_p_{label}",
                    type="primary" if is_active else "secondary",
                    width="stretch",
                ):
                    st.session_state["ov_trend_period"] = label
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        freq = period_labels[st.session_state["ov_trend_period"]]
        trend_data = (
            df.set_index("timestamp")[["aqi", "pm2_5"]]
            .resample(freq)
            .mean()
            .dropna()
            .reset_index()
        )
        aqi_line_color = "#0ea5e9"
        pm25_line_color = "#f97316"
        fig_ov = go.Figure()
        fig_ov.add_trace(
            go.Scatter(
                x=trend_data["timestamp"],
                y=trend_data["aqi"].round(1),
                mode="lines",
                name="AQI",
                line=dict(color=aqi_line_color, width=2.4),
                fill="tozeroy",
                fillcolor="rgba(14,165,233,0.08)",
                hovertemplate="%{x}<br>AQI: %{y:.1f}<extra></extra>",
            )
        )
        fig_ov.add_trace(
            go.Scatter(
                x=trend_data["timestamp"],
                y=trend_data["pm2_5"].round(1),
                mode="lines",
                name="PM2.5",
                line=dict(color=pm25_line_color, width=2),
                yaxis="y2",
                hovertemplate="%{x}<br>PM2.5: %{y:.1f} µg/m³<extra></extra>",
            )
        )
        ml(
            fig_ov,
            h=310,
            xaxis=dict(**ax()),
            yaxis=dict(**ax("AQI")),
            yaxis2=dict(
                title=dict(text="PM2.5", font=dict(size=9, color=pm25_line_color)),
                overlaying="y",
                side="right",
                tickfont=dict(size=9, color=pm25_line_color),
                showgrid=False,
            ),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font_size=9,
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
        )
        st.plotly_chart(
            fig_ov, width="stretch", config={"displayModeBar": False}
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with cO4:
        st.markdown(
            '<div class="card donut-card"><div class="card-title"><span class="q-tag">Overview</span>Cơ cấu mức AQI</div><div class="card-sub">Phân bố tỷ trọng các mức chất lượng không khí.</div>',
            unsafe_allow_html=True,
        )
        band_dist = (
            df["aqi_lbl"]
            .value_counts(normalize=True)
            .reindex([x[2] for x in AQI_DEF])
            .fillna(0)
            * 100
        )
        dominant_idx = band_dist.values.argmax()
        dominant_label = band_dist.index[dominant_idx]
        dominant_pct = band_dist.values[dominant_idx]
        dominant_color = AQI_DEF[dominant_idx][3]
        pull_vals = [0.04] * len(band_dist)
        pull_vals[dominant_idx] = 0.10
        fig_dn = go.Figure(
            go.Pie(
                labels=band_dist.index,
                values=band_dist.round(2),
                hole=0.55,
                pull=pull_vals,
                marker=dict(
                    colors=[x[3] for x in AQI_DEF],
                    line=dict(width=2.5, color="#ffffff"),
                ),
                textinfo="percent",
                textfont=dict(size=14, color="#ffffff", family="Be Vietnam Pro"),
                textposition="inside",
                insidetextorientation="horizontal",
                hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
                direction="clockwise",
                sort=False,
                rotation=90,
            )
        )
        fig_dn.update_layout(
            annotations=[
                dict(
                    text=f"<b style='font-size:1.6rem;color:{dominant_color}'>{dominant_pct:.0f}%</b>"
                    f"<br><span style='font-size:.72rem;color:#64748b'>{dominant_label}</span>",
                    x=0.5,
                    y=0.5,
                    font_size=12,
                    showarrow=False,
                )
            ]
        )
        ml(fig_dn, h=310, margin=dict(l=10, r=10, t=14, b=10), showlegend=False)
        st.plotly_chart(
            fig_dn, width="stretch", config={"displayModeBar": False}
        )
        legend_items = "".join(
            f"<span class='donut-legend-item'><span class='donut-legend-dot' style='background:{c}'></span>{lbl}</span>"
            for _, _, lbl, c in AQI_DEF
        )
        st.markdown(
            f"<div class='donut-legend'>{legend_items}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    pollutant_meta = {
        "pm2_5": {
            "title": "Vật chất hạt mịn",
            "subtitle": "(PM2.5)",
            "icon_file": "pm25.svg",
        },
        "pm10": {
            "title": "Vật chất hạt mịn",
            "subtitle": "(PM10)",
            "icon_file": "pm10.svg",
        },
        "co": {"title": "Carbon monoxide", "subtitle": "(CO)", "icon_file": "co.svg"},
        "so2": {
            "title": "Lưu huỳnh dioxide",
            "subtitle": "(SO2)",
            "icon_file": "so2.svg",
        },
        "no2": {
            "title": "Nitrogen dioxide",
            "subtitle": "(NO2)",
            "icon_file": "no2.svg",
        },
        "o3": {"title": "Ozon", "subtitle": "(O3)", "icon_file": "o3.svg"},
    }

    def _svg_data_uri(file_name):
        svg_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "components", file_name)
        )
        try:
            with open(svg_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/svg+xml;base64,{encoded}"
        except Exception:
            return ""

    available_polls = [k for k in pollutant_meta if k in df.columns]
    if available_polls:
        st.markdown(
            "<div class='card pollutant-card-wrap' style='margin-top:10px'><div class='card-title'><span class='q-tag'>Insights</span>Chỉ số chất ô nhiễm theo thành phần</div>",
            unsafe_allow_html=True,
        )
        ordered = ["pm2_5", "pm10", "co", "so2", "no2", "o3"]
        card_html = []
        for poll_key in ordered:
            if poll_key not in available_polls:
                continue
            meta = pollutant_meta[poll_key]
            series = df[poll_key].dropna()
            if series.empty:
                continue
            current_val = round(series.mean(), 1)
            unit = POLLS[poll_key]["unit"] if poll_key in POLLS else ""
            icon_uri = _svg_data_uri(meta["icon_file"])
            icon_block = (
                f"<img src='{icon_uri}' class='pollutant-icon' alt='{meta['title']}'/>"
                if icon_uri
                else "<div class='pollutant-icon pollutant-icon-fallback'></div>"
            )
            card_html.append(
                (
                    "<div class='pollutant-mini-card'>"
                    f"<div class='pollutant-mini-left'>{icon_block}</div>"
                    "<div class='pollutant-mini-mid'>"
                    f"<div class='pollutant-mini-title'>{meta['title']}</div>"
                    f"<div class='pollutant-mini-sub'>{meta['subtitle']}</div>"
                    "</div>"
                    "<div class='pollutant-mini-right'>"
                    f"<div class='pollutant-mini-value'>{current_val:g}</div>"
                    f"<div class='pollutant-mini-unit'>{unit}</div>"
                    "</div>"
                    "<div class='pollutant-mini-arrow'>›</div>"
                    "</div>"
                )
            )
        st.markdown(
            f"<div class='pollutant-mini-grid'>{''.join(card_html)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
