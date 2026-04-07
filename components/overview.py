import streamlit as st
import textwrap


def render_overview(state):
    globals().update(state)
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

