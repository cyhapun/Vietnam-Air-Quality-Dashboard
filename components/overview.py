import streamlit as st
import textwrap
import pandas as pd


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

    # ── KPI STRIP ──
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


