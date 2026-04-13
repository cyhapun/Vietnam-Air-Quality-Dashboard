import streamlit as st
import textwrap


def render_overview(state):
    globals().update(state)
    vietnam_svg_base64 = state.get("vietnam_svg_base64", "")
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
        <div class="kpi-lbl">AQI cả nước</div>
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

    iqair_hybrid_html = (
        f"<div class='iq-wrap'>"
        f"<div class='iq-live-head'>"
        f"<div class='iq-title'>Live AQI Vietnam · IQAir Hybrid</div>"
        f"<div class='iq-meta'>Cập nhật gần nhất: {latest_obs.strftime('%H:%M · %d/%m/%Y')} · Dữ liệu từ bộ cảm biến nội bộ</div>"
        f"</div>"
        f"<div class='iq-card iq-card-hero'>"
        f"{hero_bg_html}"
        f"<div class='iq-hero-content'>"
        f"<div class='iq-hero-kicker'>Chất lượng không khí tại Việt Nam</div>"
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


