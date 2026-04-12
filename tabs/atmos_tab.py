import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import list_detail_provinces, load_province_detail


def _safe_update_layout(fig, h=330):
    ctx = st.session_state.get("dashboard_context") or {}
    ml_fn = ctx.get("ml")
    if callable(ml_fn):
        ml_fn(fig, h=h)
    else:
        fig.update_layout(
            height=h,
            margin=dict(l=6, r=6, t=20, b=6),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Be Vietnam Pro", size=10, color="#334155"),
        )


def render(df):
    ctx = st.session_state.get("dashboard_context")
    if ctx is None:
        st.error("Thiếu ngữ cảnh dashboard.")
        st.stop()
    globals().update(ctx)

    province_options = ["Toàn quốc (all.csv)"] + list_detail_provinces()
    if "tab4_province" not in st.session_state:
        st.session_state.tab4_province = province_options[0]
    if st.session_state.tab4_province not in province_options:
        st.session_state.tab4_province = province_options[0]

    st.markdown(
        '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>Khí tượng & môi trường theo tỉnh</div><div class="card-sub">Mặc định hiển thị dữ liệu all.csv; khi chọn tỉnh sẽ tải dữ liệu chi tiết phường/xã của tỉnh đó.</div>',
        unsafe_allow_html=True,
    )
    selected_province = st.selectbox(
        "Chọn tỉnh/thành để xem chi tiết",
        options=province_options,
        key="tab4_province",
    )
    top_station_n = st.slider(
        "Số điểm quan trắc hiển thị (Top AQI)",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
        key="tab4_top_station_n",
        help="Giảm số lượng điểm để tăng tốc hiển thị khi dữ liệu lớn.",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if selected_province == "Toàn quốc (all.csv)":
        detail_df = df
        scope_text = "Toàn quốc (all.csv)"
    else:
        start_arg = str(ctx["s_d"]) if "s_d" in ctx else None
        end_arg = str(ctx["e_d"]) if "e_d" in ctx else None
        with st.spinner(f"Đang tải dữ liệu chi tiết của {selected_province}..."):
            detail_df = load_province_detail(selected_province, start_arg, end_arg)
        scope_text = selected_province

    if detail_df.empty:
        st.warning("Không có dữ liệu để hiển thị cho phạm vi đang chọn.")
        return

    loc_col = "location" if "location" in detail_df.columns else "city"
    if loc_col not in detail_df.columns:
        st.warning("Dữ liệu chi tiết không có cột vị trí để hiển thị.")
        return

    calc_cols = [
        loc_col,
        "aqi",
        "pm2_5",
        "wind_speed",
        "timestamp",
        "is_raining",
        "wind_bin",
    ]
    calc_df = detail_df[calc_cols].dropna(subset=[loc_col])
    stations = calc_df[loc_col].astype(str)
    st.caption(
        f"Phạm vi: {scope_text} · {len(calc_df):,} bản ghi · {stations.nunique():,} điểm quan trắc"
    )

    summary_df = (
        calc_df.groupby(loc_col)
        .agg(
            aqi=("aqi", "mean"),
            pm2_5=("pm2_5", "mean"),
            wind_speed=("wind_speed", "mean"),
            samples=("aqi", "size"),
            latest=("timestamp", "max"),
        )
        .round({"aqi": 1, "pm2_5": 1, "wind_speed": 1})
        .sort_values("aqi", ascending=False)
    )
    station_rank = summary_df.head(top_station_n).index.tolist()

    c1, c2 = st.columns(2, gap="small")

    with c1:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>PM2.5 theo tốc độ gió (chi tiết)</div><div class="card-sub">Hiển thị top điểm quan trắc có AQI trung bình cao.</div>',
            unsafe_allow_html=True,
        )
        wc = (
            calc_df[calc_df[loc_col].isin(station_rank)]
            .groupby([loc_col, "wind_bin"])["pm2_5"]
            .mean()
            .reset_index()
            .dropna()
        )

        fig_w = go.Figure()
        color_pool = [
            "#0284c7",
            "#0ea5e9",
            "#14b8a6",
            "#22c55e",
            "#f59e0b",
            "#f97316",
            "#ef4444",
            "#6366f1",
            "#8b5cf6",
            "#0f766e",
        ]
        clr_map = {name: color_pool[i % len(color_pool)] for i, name in enumerate(station_rank)}

        for station in station_rank:
            sub = wc[wc[loc_col] == station]
            if sub.empty:
                continue
            fig_w.add_trace(
                go.Scatter(
                    x=sub["wind_bin"].astype(str),
                    y=sub["pm2_5"].round(2),
                    name=station,
                    mode="lines+markers",
                    line=dict(color=clr_map[station], width=2),
                    marker=dict(size=6, color=clr_map[station]),
                    hovertemplate=f"<b>{station}</b><br>Gió %{{x}}: PM2.5 %{{y:.1f}} µg/m³<extra></extra>",
                )
            )

        _safe_update_layout(fig_w, h=340)
        fig_w.update_xaxes(
            categoryorder="array",
            categoryarray=["0–5", "5–10", "10–20", ">20"],
            title_text="Tốc độ gió (km/h)",
        )
        fig_w.update_yaxes(title_text="PM2.5 (µg/m³)")
        st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>Hiệu quả mưa rửa không khí</div><div class="card-sub">Giá trị dương: mưa giúp giảm PM2.5 so với lúc không mưa.</div>',
            unsafe_allow_html=True,
        )
        rr = (
            calc_df.groupby([loc_col, "is_raining"])["pm2_5"]
            .mean()
            .unstack()
            .rename(columns={False: "no_rain", True: "rain"})
            .dropna()
        )

        if rr.empty:
            st.info("Không đủ dữ liệu mưa/không mưa để so sánh.")
        else:
            rr["drop"] = ((rr["no_rain"] - rr["rain"]) / rr["no_rain"] * 100).replace(
                [np.inf, -np.inf], np.nan
            )
            rr = rr.dropna(subset=["drop"])
            rr = rr.sort_values("drop", ascending=False).head(top_station_n + 5).reset_index()
            rr["clr"] = rr["drop"].apply(lambda x: "#16a34a" if x > 0 else "#dc2626")

            fig_rr = go.Figure(
                go.Bar(
                    x=rr["drop"].round(1),
                    y=rr[loc_col],
                    orientation="h",
                    marker_color=rr["clr"],
                    text=rr["drop"].round(1).map(lambda x: f"{x:+.1f}%"),
                    textposition="outside",
                    hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
                )
            )
            fig_rr.add_vline(x=0, line_color="#cbd5e1", line_width=1)
            _safe_update_layout(fig_rr, h=340)
            fig_rr.update_xaxes(title_text="% thay đổi PM2.5 khi mưa")
            fig_rr.update_yaxes(title_text="Điểm quan trắc")
            st.plotly_chart(
                fig_rr, use_container_width=True, config={"displayModeBar": False}
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>Bảng chi tiết điểm quan trắc</div>',
        unsafe_allow_html=True,
    )
    rank_df = summary_df.reset_index()
    rank_df = rank_df.rename(
        columns={
            loc_col: "Điểm quan trắc",
            "aqi": "AQI TB",
            "pm2_5": "PM2.5 TB",
            "wind_speed": "Gió TB (km/h)",
            "samples": "Số mẫu",
            "latest": "Quan trắc gần nhất",
        }
    )
    st.dataframe(rank_df.head(30), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


# def render(df):
#     ctx = st.session_state.get("dashboard_context")
#     if ctx is None:
#         st.error("Thiếu ngữ cảnh dashboard.")
#         st.stop()
#     globals().update(ctx)
#     cW1, cW2 = st.columns(2, gap="small")

#     with cW1:
#         st.markdown(
#             '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>PM2.5 theo tốc độ gió</div><div class="card-sub">Đường dốc xuống = gió làm giảm bụi mịn hiệu quả</div>',
#             unsafe_allow_html=True,
#         )
#         wc = (
#             df_city.groupby(["city", "wind_bin"])["pm2_5"].mean().reset_index().dropna()
#         )
#         fig_w = go.Figure()
#         for city in sorted(wc["city"].unique()):
#             sub = wc[wc["city"] == city]
#             fig_w.add_trace(
#                 go.Scatter(
#                     x=sub["wind_bin"].astype(str),
#                     y=sub["pm2_5"].round(2),
#                     name=city,
#                     mode="lines+markers",
#                     line=dict(color=CITY_CLR.get(city, "#2563eb"), width=2),
#                     marker=dict(
#                         size=6,
#                         color=CITY_CLR.get(city, "#2563eb"),
#                         line=dict(width=1.5, color="#fff"),
#                     ),
#                     hovertemplate=f"<b>{city}</b> gió %{{x}}: %{{y:.1f}}<extra></extra>",
#                 )
#             )
#         ml(
#             fig_w,
#             h=330,
#             xaxis=dict(
#                 categoryorder="array",
#                 categoryarray=["0–5", "5–10", "10–20", ">20"],
#                 tickfont=TF,
#                 gridcolor=GC,
#                 linecolor=LC,
#                 title=dict(
#                     text="Tốc độ gió (km/h)", font=dict(size=9, color="#64748b")
#                 ),
#             ),
#             yaxis=dict(**ax("PM2.5 µg/m³")),
#             legend=dict(
#                 bgcolor="rgba(0,0,0,0)",
#                 font_size=9,
#                 orientation="v",
#                 yanchor="top",
#                 y=1,
#                 xanchor="left",
#                 x=1.01,
#             ),
#         )
#         st.plotly_chart(
#             fig_w, use_container_width=True, config={"displayModeBar": False}
#         )
#         st.markdown("</div>", unsafe_allow_html=True)

#     with cW2:
#         st.markdown(
#             '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>Hiệu quả rửa không khí khi mưa</div><div class="card-sub">Xanh = mưa giảm bụi · Đỏ = mưa không hiệu quả</div>',
#             unsafe_allow_html=True,
#         )
#         rr = (
#             df_city.groupby(["city", "is_raining"])["pm2_5"]
#             .mean()
#             .unstack()
#             .rename(columns={False: "no_rain", True: "rain"})
#             .dropna()
#         )
#         rr["drop"] = ((rr["no_rain"] - rr["rain"]) / rr["no_rain"] * 100).round(1)
#         rr = rr.sort_values("drop", ascending=True).reset_index()
#         rr["clr"] = rr["drop"].apply(lambda x: "#16a34a" if x > 0 else "#dc2626")
#         fig_rr = go.Figure(
#             go.Bar(
#                 x=rr["drop"],
#                 y=rr["city"],
#                 orientation="h",
#                 marker_color=rr["clr"],
#                 text=rr["drop"].apply(lambda x: f"{x:+.1f}%"),
#                 textposition="outside",
#                 textfont=dict(size=9, color="#334155"),
#                 hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
#             )
#         )
#         fig_rr.add_vline(x=0, line_color="#e2e8f0", line_width=1)
#         ml(
#             fig_rr,
#             h=330,
#             xaxis=dict(**ax("% thay đổi PM2.5 khi mưa")),
#             yaxis=dict(
#                 tickfont=dict(color="#334155", size=9), gridcolor=GC, linecolor=LC
#             ),
#         )
#         st.plotly_chart(
#             fig_rr, use_container_width=True, config={"displayModeBar": False}
#         )
#         st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # TAB 5 — Q5 & Q6
