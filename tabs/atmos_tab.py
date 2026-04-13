import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import list_detail_provinces, load_province_detail
from utils.helpers import AQI_DEF


WIND_BIN_ORDER = ["0–5", "5–10", "10–20", ">20"]
STATION_MODE_OPTIONS = ["Ô nhiễm cao", "Không khí tốt"]
TREND_PERIODS = {"Ngày": "D", "Tuần": "W", "Tháng": "ME"}
COLOR_POOL = [
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


def _fallback_ml(fig, h=None, **kwargs):
    base = dict(
        margin=dict(l=6, r=6, t=20, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Be Vietnam Pro", size=10, color="#334155"),
    )
    if h is not None:
        base["height"] = h
    base.update(kwargs)
    fig.update_layout(**base)
    return fig


def _fallback_ax(title=""):
    cfg = dict(
        tickfont=dict(color="#64748b", size=9),
        gridcolor="rgba(0,0,0,0.04)",
        linecolor="#e2e8f0",
        zeroline=False,
    )
    if title:
        cfg["title"] = dict(text=title, font=dict(size=9, color="#64748b"))
    return cfg


def _fallback_chart_h(n_rows, min_h=260, row_h=24, max_h=560):
    return int(min(max_h, max(min_h, n_rows * row_h + 70)))


def _get_plot_helpers(ctx):
    ml_fn = ctx.get("ml") if callable(ctx.get("ml")) else _fallback_ml
    ax_fn = ctx.get("ax") if callable(ctx.get("ax")) else _fallback_ax
    chart_h_fn = (
        ctx.get("chart_h") if callable(ctx.get("chart_h")) else _fallback_chart_h
    )
    return ml_fn, ax_fn, chart_h_fn


def _render_button_group(options, state_key, prefix):
    if state_key not in st.session_state or st.session_state[state_key] not in options:
        st.session_state[state_key] = options[0]

    cols = st.columns(len(options), gap="small")
    selected = st.session_state[state_key]

    for idx, opt in enumerate(options):
        is_active = opt == selected
        if cols[idx].button(
            opt,
            key=f"{prefix}_{idx}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            st.session_state[state_key] = opt

    return st.session_state[state_key]


def _prepare_detail_frame(detail_df, loc_col):
    wanted = [
        loc_col,
        "aqi",
        "pm2_5",
        "wind_speed",
        "timestamp",
        "is_raining",
        "wind_bin",
        "aqi_lbl",
        "rain",
    ]
    cols = [c for c in wanted if c in detail_df.columns]
    calc_df = detail_df[cols].copy()

    calc_df[loc_col] = calc_df[loc_col].astype(str).str.strip()
    calc_df = calc_df[calc_df[loc_col] != ""]

    for c in ["aqi", "pm2_5", "wind_speed", "rain"]:
        if c in calc_df.columns:
            calc_df[c] = pd.to_numeric(calc_df[c], errors="coerce")

    calc_df["timestamp"] = pd.to_datetime(calc_df["timestamp"], errors="coerce")
    calc_df = calc_df.dropna(
        subset=[loc_col, "aqi", "pm2_5", "wind_speed", "timestamp"]
    )

    if "is_raining" not in calc_df.columns:
        if "rain" in calc_df.columns:
            calc_df["is_raining"] = calc_df["rain"].fillna(0) > 0
        else:
            calc_df["is_raining"] = False
    else:
        calc_df["is_raining"] = calc_df["is_raining"].fillna(False).astype(bool)

    if "wind_bin" not in calc_df.columns:
        calc_df["wind_bin"] = pd.cut(
            calc_df["wind_speed"],
            bins=[0, 5, 10, 20, 200],
            labels=WIND_BIN_ORDER,
            include_lowest=True,
        )
    else:
        normalized = calc_df["wind_bin"].astype(str)
        normalized = normalized.where(normalized.isin(WIND_BIN_ORDER))
        calc_df["wind_bin"] = pd.Categorical(
            normalized,
            categories=WIND_BIN_ORDER,
            ordered=True,
        )

    if "aqi_lbl" not in calc_df.columns:
        labels = [x[2] for x in AQI_DEF]
        calc_df["aqi_lbl"] = pd.cut(
            calc_df["aqi"],
            bins=[-np.inf, 50, 100, 150, 200, 300, np.inf],
            labels=labels,
            include_lowest=True,
        ).fillna(labels[-1])

    calc_df["date"] = calc_df["timestamp"].dt.date
    return calc_df


def _rain_effect_by_station(calc_df, loc_col):
    rr = (
        calc_df.groupby([loc_col, "is_raining"])["pm2_5"]
        .mean()
        .unstack()
        .rename(columns={False: "dry", True: "rain"})
        .dropna()
    )
    if rr.empty:
        return rr
    rr["rain_drop_pct"] = (
        (rr["dry"] - rr["rain"]) / rr["dry"] * 100
    ).replace([np.inf, -np.inf], np.nan)
    rr = rr.dropna(subset=["rain_drop_pct"])
    return rr


def _fmt_na(value, fmt="{:.1f}"):
    if pd.isna(value):
        return "N/A"
    return fmt.format(value)


def render(df):
    ctx = st.session_state.get("dashboard_context")
    if ctx is None:
        st.error("Thiếu ngữ cảnh dashboard.")
        st.stop()
    globals().update(ctx)

    ml_fn, ax_fn, chart_h_fn = _get_plot_helpers(ctx)

    province_options = ["Toàn quốc (all.csv)"] + list_detail_provinces()
    if "tab4_province" not in st.session_state:
        st.session_state.tab4_province = province_options[0]
    if st.session_state.tab4_province not in province_options:
        st.session_state.tab4_province = province_options[0]

    st.markdown(
        '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>Khí tượng & môi trường theo tỉnh</div><div class="card-sub">Đồng bộ theo phong cách tab mới: có chế độ xếp hạng điểm, xu hướng theo chu kỳ và bảng chi tiết cho từng điểm quan trắc.</div>',
        unsafe_allow_html=True,
    )
    c_ctrl1, c_ctrl2 = st.columns([2.1, 1.0], gap="small")
    with c_ctrl1:
        selected_province = st.selectbox(
            "Chọn tỉnh/thành để xem chi tiết",
            options=province_options,
            key="tab4_province",
        )
    with c_ctrl2:
        top_station_n = st.slider(
            "Số điểm quan trắc hiển thị",
            min_value=5,
            max_value=20,
            value=10,
            step=1,
            key="tab4_top_station_n",
            help="Giảm số lượng điểm để tăng tốc hiển thị khi dữ liệu lớn.",
        )

    st.markdown(
        '<div class="card-sub" style="margin-top:4px">Chế độ xếp hạng điểm quan trắc</div>',
        unsafe_allow_html=True,
    )
    station_mode = _render_button_group(
        STATION_MODE_OPTIONS,
        "tab4_station_mode",
        "tab4_station_mode_btn",
    )
    st.markdown(
        '<div class="card-sub" style="margin-top:8px">Chu kỳ xu hướng</div>',
        unsafe_allow_html=True,
    )
    trend_period = _render_button_group(
        list(TREND_PERIODS.keys()),
        "tab4_trend_period",
        "tab4_trend_period_btn",
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

    calc_df = _prepare_detail_frame(detail_df, loc_col)
    if calc_df.empty:
        st.warning("Dữ liệu sau chuẩn hóa không đủ để phân tích.")
        return

    summary_df = (
        calc_df.groupby(loc_col)
        .agg(
            aqi=("aqi", "mean"),
            pm2_5=("pm2_5", "mean"),
            wind_speed=("wind_speed", "mean"),
            samples=("aqi", "size"),
            latest=("timestamp", "max"),
        )
        .sort_values("aqi", ascending=False)
    )

    rain_effect_df = _rain_effect_by_station(calc_df, loc_col)
    if not rain_effect_df.empty:
        summary_df = summary_df.join(rain_effect_df[["rain_drop_pct"]], how="left")
    else:
        summary_df["rain_drop_pct"] = np.nan

    rank_ascending = station_mode == "Không khí tốt"
    ranked_summary = summary_df.sort_values("aqi", ascending=rank_ascending)
    station_rank = ranked_summary.head(top_station_n).index.tolist()

    total_records = len(calc_df)
    station_count = summary_df.shape[0]
    avg_aqi = calc_df["aqi"].mean()
    avg_pm = calc_df["pm2_5"].mean()
    median_rain_drop = summary_df["rain_drop_pct"].median(skipna=True)
    focus_station = ranked_summary.index[0]
    focus_aqi = ranked_summary.iloc[0]["aqi"]

    st.caption(
        f"Phạm vi: {scope_text} · {total_records:,} bản ghi · {station_count:,} điểm quan trắc"
    )

    k1, k2, k3, k4 = st.columns(4, gap="small")
    with k1:
        st.markdown(
            f'<div class="kpi-box accent-blue"><div class="kpi-lbl">AQI trung bình</div><div class="kpi-val">{avg_aqi:.1f}</div><div class="kpi-sub">Điểm nổi bật: {focus_station}</div></div>',
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f'<div class="kpi-box accent-amber"><div class="kpi-lbl">PM2.5 trung bình</div><div class="kpi-val">{avg_pm:.1f} <span class="u">µg/m³</span></div><div class="kpi-sub">Theo {trend_period.lower()}</div></div>',
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f'<div class="kpi-box accent-slate"><div class="kpi-lbl">Số điểm quan trắc</div><div class="kpi-val">{station_count}</div><div class="kpi-sub">Top hiển thị: {top_station_n}</div></div>',
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f'<div class="kpi-box accent-red"><div class="kpi-lbl">Hiệu quả mưa (median)</div><div class="kpi-val">{_fmt_na(median_rain_drop, "{:+.1f}%")}</div><div class="kpi-sub">{station_mode}: AQI {focus_aqi:.1f}</div></div>',
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2, gap="small")

    with c1:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>PM2.5 theo tốc độ gió</div><div class="card-sub">Đường biểu diễn theo nhóm gió cho các điểm quan trắc được xếp hạng.</div>',
            unsafe_allow_html=True,
        )
        wc = (
            calc_df[calc_df[loc_col].isin(station_rank)]
            .groupby([loc_col, "wind_bin"], observed=False)["pm2_5"]
            .mean()
            .reset_index()
            .dropna(subset=["wind_bin", "pm2_5"])
        )

        fig_w = go.Figure()
        color_map = {
            name: COLOR_POOL[i % len(COLOR_POOL)] for i, name in enumerate(station_rank)
        }
        for station in station_rank:
            sub = wc[wc[loc_col] == station].sort_values("wind_bin")
            if sub.empty:
                continue
            fig_w.add_trace(
                go.Scatter(
                    x=sub["wind_bin"].astype(str),
                    y=sub["pm2_5"].round(2),
                    name=station,
                    mode="lines+markers",
                    line=dict(color=color_map[station], width=2),
                    marker=dict(size=6, color=color_map[station]),
                    hovertemplate=f"<b>{station}</b><br>Gió %{{x}}: PM2.5 %{{y:.1f}} µg/m³<extra></extra>",
                )
            )

        xaxis_cfg = dict(
            **ax_fn("Tốc độ gió (km/h)"),
            categoryorder="array",
            categoryarray=WIND_BIN_ORDER,
        )
        yaxis_cfg = dict(**ax_fn("PM2.5 (µg/m³)"))
        ml_fn(
            fig_w,
            h=chart_h_fn(len(station_rank), min_h=300, row_h=10, max_h=460),
            xaxis=xaxis_cfg,
            yaxis=yaxis_cfg,
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font_size=9,
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.01,
            ),
        )
        st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>Hiệu quả mưa rửa không khí</div><div class="card-sub">Giá trị dương nghĩa là PM2.5 giảm khi mưa.</div>',
            unsafe_allow_html=True,
        )
        rain_view = summary_df.loc[station_rank, ["rain_drop_pct"]].dropna()

        if rain_view.empty:
            st.info("Không đủ dữ liệu mưa/không mưa để so sánh trong nhóm đang chọn.")
        else:
            rain_view = rain_view.sort_values("rain_drop_pct", ascending=False).reset_index()
            rain_view["clr"] = rain_view["rain_drop_pct"].apply(
                lambda x: "#16a34a" if x > 0 else "#dc2626"
            )

            fig_rr = go.Figure(
                go.Bar(
                    x=rain_view["rain_drop_pct"].round(1),
                    y=rain_view[loc_col],
                    orientation="h",
                    marker_color=rain_view["clr"],
                    text=rain_view["rain_drop_pct"].map(lambda x: f"{x:+.1f}%"),
                    textposition="outside",
                    hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
                )
            )
            fig_rr.add_vline(x=0, line_color="#cbd5e1", line_width=1)
            ml_fn(
                fig_rr,
                h=chart_h_fn(len(rain_view), min_h=300, row_h=16, max_h=460),
                xaxis=dict(**ax_fn("% thay đổi PM2.5 khi mưa")),
                yaxis=dict(
                    tickfont=dict(color="#334155", size=9),
                    gridcolor="rgba(0,0,0,0.04)",
                    linecolor="#e2e8f0",
                ),
            )
            st.plotly_chart(
                fig_rr,
                use_container_width=True,
                config={"displayModeBar": False},
            )
        st.markdown("</div>", unsafe_allow_html=True)

    c3, c4 = st.columns([2.2, 1.2], gap="small")

    with c3:
        st.markdown(
            '<div class="card trend-card"><div class="card-title"><span class="q-tag">Q3</span>Xu hướng AQI và PM2.5</div><div class="card-sub">Chu kỳ tổng hợp lấy theo lựa chọn ở đầu tab.</div>',
            unsafe_allow_html=True,
        )
        freq = TREND_PERIODS.get(trend_period, "D")
        trend_df = (
            calc_df.set_index("timestamp")[["aqi", "pm2_5"]]
            .resample(freq)
            .mean()
            .dropna()
            .reset_index()
        )
        if trend_df.empty:
            st.info("Không đủ dữ liệu để dựng xu hướng theo chu kỳ đã chọn.")
        else:
            fig_tr = go.Figure()
            fig_tr.add_trace(
                go.Scatter(
                    x=trend_df["timestamp"],
                    y=trend_df["aqi"].round(1),
                    mode="lines",
                    name="AQI",
                    line=dict(color="#0ea5e9", width=2.3),
                    hovertemplate="%{x|%d/%m/%Y}<br>AQI: %{y:.1f}<extra></extra>",
                )
            )
            fig_tr.add_trace(
                go.Scatter(
                    x=trend_df["timestamp"],
                    y=trend_df["pm2_5"].round(1),
                    mode="lines",
                    name="PM2.5",
                    yaxis="y2",
                    line=dict(color="#f59e0b", width=2),
                    hovertemplate="%{x|%d/%m/%Y}<br>PM2.5: %{y:.1f} µg/m³<extra></extra>",
                )
            )
            ml_fn(
                fig_tr,
                h=300,
                xaxis=dict(**ax_fn()),
                yaxis=dict(**ax_fn("AQI")),
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
            st.plotly_chart(fig_tr, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with c4:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>Cơ cấu mức AQI</div><div class="card-sub">Phân bố mức chất lượng không khí trong phạm vi đang xét.</div>',
            unsafe_allow_html=True,
        )
        band_order = [x[2] for x in AQI_DEF]
        band_dist = (
            calc_df["aqi_lbl"].value_counts(normalize=True).reindex(band_order).fillna(0) * 100
        )
        fig_dn = go.Figure(
            go.Pie(
                labels=band_dist.index,
                values=band_dist.round(2),
                hole=0.55,
                marker=dict(
                    colors=[x[3] for x in AQI_DEF],
                    line=dict(width=1, color="#fff"),
                ),
                textinfo="label+percent",
                textfont=dict(size=9),
                hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            )
        )
        ml_fn(fig_dn, h=300, margin=dict(l=4, r=4, t=12, b=2), showlegend=False)
        st.plotly_chart(fig_dn, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="card"><div class="card-title"><span class="q-tag">Q3</span>Bảng chi tiết điểm quan trắc</div>',
        unsafe_allow_html=True,
    )
    table_df = ranked_summary.reset_index().rename(
        columns={
            loc_col: "Điểm quan trắc",
            "aqi": "AQI TB",
            "pm2_5": "PM2.5 TB",
            "wind_speed": "Gió TB (km/h)",
            "samples": "Số mẫu",
            "latest": "Quan trắc gần nhất",
            "rain_drop_pct": "Hiệu quả mưa (%)",
        }
    )
    table_df["Quan trắc gần nhất"] = pd.to_datetime(
        table_df["Quan trắc gần nhất"], errors="coerce"
    ).dt.strftime("%d/%m/%Y %H:%M")
    for c in ["AQI TB", "PM2.5 TB", "Gió TB (km/h)", "Hiệu quả mưa (%)"]:
        if c in table_df.columns:
            table_df[c] = table_df[c].round(1)

    st.dataframe(table_df.head(40), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
