import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render(df):
    ctx = st.session_state.get("dashboard_context")
    if ctx is None:
        st.error("Thiếu ngữ cảnh dashboard.")
        st.stop()
    globals().update(ctx)
    cO1, cO2 = st.columns([2.2, 1.2], gap="small")

    with cO1:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Bản đồ AQI theo khu vực</div><div class="card-sub">Kích thước điểm = PM2.5 trung bình · Màu điểm = AQI trung bình</div>',
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
        ).fillna("Nguy hại")
        city_geo["marker_size"] = (city_geo["pm2_5"].clip(lower=8) * 0.7).clip(
            lower=8, upper=28
        )

        fig_map = go.Figure(
            go.Scattermapbox(
                lat=city_geo["lat"],
                lon=city_geo["lon"],
                mode="markers+text",
                text=city_geo["city"],
                textposition="top center",
                textfont=dict(size=9, color="#334155"),
                marker=dict(
                    size=city_geo["marker_size"],
                    color=city_geo["aqi"],
                    colorscale=[
                        [0.0, "#14b8a6"],
                        [0.35, "#0ea5e9"],
                        [0.55, "#f59e0b"],
                        [0.75, "#f97316"],
                        [1.0, "#ef4444"],
                    ],
                    cmin=0,
                    cmax=max(200, city_geo["aqi"].max() + 10),
                    opacity=0.84,
                    colorbar=dict(
                        title="AQI", thickness=10, tickfont=dict(size=8), x=1.01
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
            fig_map, use_container_width=True, config={"displayModeBar": False}
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with cO2:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Tổng quan nhanh</div>',
            unsafe_allow_html=True,
        )
        top_city = city_aqi_mean.head(5).round(1)
        low_city = city_aqi_mean.sort_values(ascending=True).head(3).round(1)
        top_who = sorted(who_exceed.items(), key=lambda x: x[1], reverse=True)[:3]
        top_who_txt = " · ".join([f"{POLLS[k]['label']}: {v}%" for k, v in top_who])

        st.markdown(
            f'<div class="kpi-box accent-blue" style="margin-bottom:8px"><div class="kpi-lbl">AQI trung bình</div><div class="kpi-val" style="color:{_col}">{avg_aqi}</div><div class="kpi-sub">{_lbl}</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="kpi-box accent-amber" style="margin-bottom:8px"><div class="kpi-lbl">PM2.5 trung bình</div><div class="kpi-val">{avg_pm25} <span class="u">µg/m³</span></div><div class="kpi-sub">% giờ nguy hiểm: {dangerp}%</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="kpi-box accent-slate"><div class="kpi-lbl">Vượt ngưỡng WHO</div><div class="kpi-sub" style="font-size:.67rem;color:#334155">{top_who_txt}</div></div>',
            unsafe_allow_html=True,
        )

        top_tbl = pd.DataFrame(
            {"Thành phố AQI cao": top_city.index, "AQI TB": top_city.values}
        )
        st.dataframe(top_tbl, use_container_width=True, hide_index=True)
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
            fig_dn, use_container_width=True, config={"displayModeBar": False}
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with cO4:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Xu hướng AQI và PM2.5 theo ngày</div><div class="card-sub">Đặt hai tín hiệu cạnh nhau để đọc nhanh biến động thời gian</div>',
            unsafe_allow_html=True,
        )
        daily_o = (
            df.groupby("date")[["aqi", "pm2_5"]]
            .mean()
            .reset_index()
            .sort_values("date")
        )
        fig_ov = go.Figure()
        fig_ov.add_trace(
            go.Scatter(
                x=daily_o["date"],
                y=daily_o["aqi"].round(1),
                mode="lines",
                name="AQI",
                line=dict(color="#0ea5e9", width=2.4),
                hovertemplate="%{x}<br>AQI: %{y:.1f}<extra></extra>",
            )
        )
        fig_ov.add_trace(
            go.Scatter(
                x=daily_o["date"],
                y=daily_o["pm2_5"].round(1),
                mode="lines",
                name="PM2.5",
                line=dict(color="#f59e0b", width=2),
                yaxis="y2",
                hovertemplate="%{x}<br>PM2.5: %{y:.1f} µg/m³<extra></extra>",
            )
        )
        ml(
            fig_ov,
            h=265,
            xaxis=dict(**ax()),
            yaxis=dict(**ax("AQI")),
            yaxis2=dict(
                title=dict(text="PM2.5", font=dict(size=9, color="#b45309")),
                overlaying="y",
                side="right",
                tickfont=dict(size=9, color="#b45309"),
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
            fig_ov, use_container_width=True, config={"displayModeBar": False}
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
