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
#     cG1, cG2 = st.columns([1.15, 1.85], gap="small")

#     with cG1:
#         st.markdown(
#             '<div class="card"><div class="card-title"><span class="q-tag">Q2</span>AQI trung bình theo thành phố</div>',
#             unsafe_allow_html=True,
#         )
#         ca = (
#             df_city.groupby("city")["aqi"]
#             .mean()
#             .sort_values(ascending=True)
#             .reset_index()
#         )
#         ca["clr"] = ca["aqi"].apply(lambda x: aqi_meta(x)[1])
#         fig_ca = go.Figure(
#             go.Bar(
#                 x=ca["aqi"].round(1),
#                 y=ca["city"],
#                 orientation="h",
#                 marker_color=ca["clr"],
#                 text=ca["aqi"].round(1),
#                 textposition="outside",
#                 textfont=dict(size=9, color="#334155"),
#                 hovertemplate="%{y}: AQI %{x:.0f}<extra></extra>",
#             )
#         )
#         ml(
#             fig_ca,
#             h=chart_h(len(ca), min_h=280, row_h=20, max_h=580),
#             xaxis=dict(**ax("AQI")),
#             yaxis=dict(
#                 tickfont=dict(color="#334155", size=9), gridcolor=GC, linecolor=LC
#             ),
#         )
#         st.plotly_chart(
#             fig_ca, use_container_width=True, config={"displayModeBar": False}
#         )
#         st.markdown("</div>", unsafe_allow_html=True)

#     with cG2:
#         st.markdown(
#             '<div class="card"><div class="card-title"><span class="q-tag">Q2</span>Nhiệt độ × Độ ẩm → AQI</div><div class="card-sub">Kích thước bong bóng = PM2.5</div>',
#             unsafe_allow_html=True,
#         )
#         sc2 = (
#             df_city.groupby("city")
#             .agg(
#                 temp=("temp", "mean"),
#                 humidity=("humidity", "mean"),
#                 aqi=("aqi", "mean"),
#                 pm2_5=("pm2_5", "mean"),
#             )
#             .reset_index()
#         )
#         fig_bb = go.Figure()
#         for _, row in sc2.iterrows():
#             clr = CITY_CLR.get(row["city"], "#2563eb")
#             fig_bb.add_trace(
#                 go.Scatter(
#                     x=[round(row["temp"], 1)],
#                     y=[round(row["humidity"], 1)],
#                     mode="markers+text",
#                     marker=dict(
#                         size=max(10, row["pm2_5"] * 0.85),
#                         color=clr,
#                         opacity=0.8,
#                         line=dict(width=1.5, color="#fff"),
#                     ),
#                     text=[row["city"]],
#                     textposition="top center",
#                     textfont=dict(size=8, color="#334155"),
#                     showlegend=False,
#                     hovertemplate=(
#                         f"<b>{row['city']}</b><br>Nhiệt độ: {row['temp']:.1f}°C<br>"
#                         f"Độ ẩm: {row['humidity']:.1f}%<br>AQI: {row['aqi']:.0f}<br>"
#                         f"PM2.5: {row['pm2_5']:.1f}<extra></extra>"
#                     ),
#                 )
#             )
#         ml(
#             fig_bb,
#             h=chart_h(len(ca), min_h=280, row_h=20, max_h=580),
#             xaxis=dict(**ax("Nhiệt độ (°C)")),
#             yaxis=dict(**ax("Độ ẩm (%)")),
#         )
#         st.plotly_chart(
#             fig_bb, use_container_width=True, config={"displayModeBar": False}
#         )
#         st.markdown("</div>", unsafe_allow_html=True)

#     st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
#     st.markdown(
#         '<div class="card"><div class="card-title"><span class="q-tag">Q2</span>Phân phối mức AQI theo thành phố</div>',
#         unsafe_allow_html=True,
#     )
#     lc = df_city.groupby(["city", "aqi_lbl"]).size().reset_index(name="n")
#     lc["pct"] = (lc["n"] / lc.groupby("city")["n"].transform("sum") * 100).round(1)
#     lclr = {
#         "Tốt": "#16a34a",
#         "Trung bình": "#d97706",
#         "Kém": "#ea580c",
#         "Xấu": "#dc2626",
#         "Rất xấu": "#9333ea",
#         "Nguy hại": "#7f1d1d",
#     }
#     fig_lv = go.Figure()
#     for lv in ["Tốt", "Trung bình", "Kém", "Xấu", "Rất xấu", "Nguy hại"]:
#         sub = lc[lc["aqi_lbl"] == lv]
#         if sub.empty:
#             continue
#         fig_lv.add_trace(
#             go.Bar(
#                 name=lv,
#                 x=sub["city"],
#                 y=sub["pct"],
#                 marker_color=lclr[lv],
#                 hovertemplate=f"<b>%{{x}}</b> {lv}: %{{y:.1f}}%<extra></extra>",
#             )
#         )
#     ml(
#         fig_lv,
#         h=chart_h(len(ca), min_h=340, row_h=18, max_h=620),
#         barmode="stack",
#         xaxis=dict(
#             tickfont=dict(color="#334155", size=9),
#             tickangle=-25,
#             gridcolor=GC,
#             linecolor=LC,
#         ),
#         yaxis=dict(**ax("%"), range=[0, 105]),
#         legend=dict(
#             bgcolor="rgba(0,0,0,0)",
#             font_size=8,
#             orientation="h",
#             yanchor="bottom",
#             y=1.02,
#             xanchor="left",
#             x=0,
#         ),
#     )
#     st.plotly_chart(fig_lv, use_container_width=True, config={"displayModeBar": False})
#     st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # TAB 4 — Q3
