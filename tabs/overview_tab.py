import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import base64
import os


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
<<<<<<< HEAD
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
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": True},
    )
    st.markdown("</div>", unsafe_allow_html=True)
=======
        st.plotly_chart(
            fig_map, width="stretch", config={"displayModeBar": False}
        )
        st.markdown("</div>", unsafe_allow_html=True)
>>>>>>> feature/datetime

    rank_now = city_geo.sort_values("aqi", ascending=False).head(8).copy()
    rank_clean = city_geo.sort_values("aqi", ascending=True).head(8).copy()

    def _aqi_badge(val):
        _, badge_col = aqi_meta(float(val))
        badge_text = "#ffffff" if float(val) >= 151 else "#0f172a"
        return badge_col, badge_text

<<<<<<< HEAD
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
=======
        top_tbl = pd.DataFrame(
            {"Thành phố AQI cao": top_city.index, "AQI TB": top_city.values}
        )
        st.dataframe(top_tbl, width="stretch", hide_index=True)
        best_txt = " · ".join([f"{c} ({v:.1f})" for c, v in low_city.items()])
        st.markdown(
            f'<div class="card-sub" style="margin-top:6px"><strong>Khu vực sạch hơn:</strong> {best_txt}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    cO3, cO4 = st.columns([1.55, 2.45], gap="small")
    with cO3:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Cơ cấu mức AQI</div>',
            unsafe_allow_html=True,
        )
        band_dist = (
            df["aqi_lbl"]
            .value_counts(normalize=True)
            .reindex([x[2] for x in AQI_DEF])
            .fillna(0)
            * 100
        )
        fig_dn = go.Figure(
            go.Pie(
                labels=band_dist.index,
                values=band_dist.round(2),
                hole=0.56,
                marker=dict(
                    colors=[x[3] for x in AQI_DEF], line=dict(width=1, color="#fff")
                ),
                textinfo="label+percent",
                textfont=dict(size=9),
                hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            )
        )
        ml(fig_dn, h=265, margin=dict(l=4, r=4, t=14, b=2), showlegend=False)
        st.plotly_chart(
            fig_dn, width="stretch", config={"displayModeBar": False}
        )
        st.markdown("</div>", unsafe_allow_html=True)
>>>>>>> feature/datetime

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
                    use_container_width=True,
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
            fig_dn, use_container_width=True, config={"displayModeBar": False}
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
