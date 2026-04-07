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
#     cT1, cT2 = st.columns([1.7, 1.1], gap="small")

#     with cT1:
#         st.markdown(
#             '<div class="card"><div class="card-title"><span class="q-tag">Q1</span>PM2.5 theo tháng & thời điểm</div><div class="card-sub">T10–T3 (mùa khô) PM2.5 thường cao hơn T4–T9 (mùa mưa)</div>',
#             unsafe_allow_html=True,
#         )
#         ms = df.groupby(["month", "time_slot"])["pm2_5"].mean().reset_index()
#         fig_ms = go.Figure()
#         for slot, clr in SLOT_CLR.items():
#             sub = ms[ms["time_slot"] == slot]
#             fig_ms.add_trace(
#                 go.Scatter(
#                     x=sub["month"],
#                     y=sub["pm2_5"].round(2),
#                     name=slot,
#                     mode="lines+markers",
#                     line=dict(color=clr, width=2),
#                     marker=dict(size=5, color=clr, line=dict(width=1.5, color="#fff")),
#                     hovertemplate=f"<b>{slot}</b> T%{{x}}: %{{y:.1f}} µg/m³<extra></extra>",
#                 )
#             )
#         fig_ms.add_hline(
#             y=15,
#             line_dash="dot",
#             line_color="rgba(220,38,38,.4)",
#             line_width=1,
#             annotation_text="WHO 15µg",
#             annotation_font_size=8,
#             annotation_font_color="#dc2626",
#         )
#         ml(
#             fig_ms,
#             h=290,
#             xaxis=dict(
#                 tickmode="array",
#                 tickvals=list(range(1, 13)),
#                 ticktext=[f"T{m}" for m in range(1, 13)],
#                 tickfont=TF,
#                 gridcolor=GC,
#                 linecolor=LC,
#             ),
#             yaxis=dict(**ax("PM2.5 µg/m³")),
#             legend=dict(
#                 bgcolor="rgba(0,0,0,0)",
#                 font_size=9,
#                 orientation="h",
#                 yanchor="bottom",
#                 y=1.02,
#                 xanchor="left",
#                 x=0,
#             ),
#         )
#         st.plotly_chart(
#             fig_ms, use_container_width=True, config={"displayModeBar": False}
#         )
#         st.markdown("</div>", unsafe_allow_html=True)

#     with cT2:
#         st.markdown(
#             '<div class="card"><div class="card-title"><span class="q-tag">Q1</span>Nhịp AQI 24 giờ</div><div class="card-sub">Màu theo mức AQI · Đỉnh sáng sớm & chiều tối</div>',
#             unsafe_allow_html=True,
#         )
#         hr = df.groupby("hour")["aqi"].mean().reset_index()
#         fig_hr = go.Figure(
#             go.Bar(
#                 x=hr["hour"],
#                 y=hr["aqi"].round(1),
#                 marker_color=[aqi_meta(v)[1] for v in hr["aqi"]],
#                 hovertemplate="Giờ %{x}h: AQI %{y:.0f}<extra></extra>",
#             )
#         )
#         ml(fig_hr, h=290, xaxis=dict(**ax("Giờ"), dtick=3), yaxis=dict(**ax("AQI")))
#         st.plotly_chart(
#             fig_hr, use_container_width=True, config={"displayModeBar": False}
#         )
#         st.markdown("</div>", unsafe_allow_html=True)

#     st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
#     st.markdown(
#         '<div class="card"><div class="card-title"><span class="q-tag">Q1</span>AQI hàng ngày — Rolling 7 ngày</div><div class="card-sub">Xám = từng ngày · Đỏ = trung bình trượt 7 ngày</div>',
#         unsafe_allow_html=True,
#     )
#     daily = df.groupby("date")["aqi"].mean().reset_index().sort_values("date")
#     daily["r7"] = daily["aqi"].rolling(7, min_periods=1).mean()
#     fig_day = go.Figure()
#     for lo, hi, l, c in AQI_DEF:
#         fig_day.add_hrect(
#             y0=lo, y1=min(hi, 310), fillcolor=c, opacity=0.04, line_width=0
#         )
#     fig_day.add_trace(
#         go.Scatter(
#             x=daily["date"],
#             y=daily["aqi"].round(1),
#             name="Hàng ngày",
#             mode="lines",
#             line=dict(color="#cbd5e1", width=1),
#         )
#     )
#     fig_day.add_trace(
#         go.Scatter(
#             x=daily["date"],
#             y=daily["r7"].round(1),
#             name="TB 7 ngày",
#             mode="lines",
#             line=dict(color="#dc2626", width=2.5),
#         )
#     )
#     ml(
#         fig_day,
#         h=310,
#         xaxis=dict(**ax()),
#         yaxis=dict(**ax("AQI")),
#         legend=dict(
#             bgcolor="rgba(0,0,0,0)",
#             font_size=9,
#             orientation="h",
#             yanchor="bottom",
#             y=1.02,
#             xanchor="left",
#             x=0,
#         ),
#     )
#     st.plotly_chart(fig_day, use_container_width=True, config={"displayModeBar": False})
#     st.markdown("</div>", unsafe_allow_html=True)
