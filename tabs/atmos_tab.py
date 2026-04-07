import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


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
