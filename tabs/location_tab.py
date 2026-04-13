import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import re
import unicodedata


REGION7_PROVINCES = {
    "Trung du và Miền núi phía Bắc": [
        "Tuyên Quang",
        "Lào Cai",
        "Thái Nguyên",
        "Phú Thọ",
        "Bắc Ninh",
        "Lạng Sơn",
        "Điện Biên",
        "Sơn La",
        "Lai Châu",
    ],
    "Đồng bằng sông Hồng": [
        "Hà Nội",
        "TP. Hải Phòng",
        "Hưng Yên",
        "Ninh Bình",
        "Quảng Ninh",
    ],
    "Bắc Trung Bộ": [
        "Thanh Hóa",
        "Nghệ An",
        "Hà Tĩnh",
        "Quảng Trị",
        "TP. Huế",
    ],
    "Duyên hải Nam Trung Bộ": [
        "TP. Đà Nẵng",
        "Quảng Ngãi",
        "Khánh Hòa",
        "Bình Thuận",
    ],
    "Tây Nguyên": [
        "Gia Lai",
        "Đắk Lắk",
        "Lâm Đồng",
    ],
    "Đông Nam Bộ": [
        "TP. Hồ Chí Minh",
        "Đồng Nai",
        "Tây Ninh",
    ],
    "Đồng bằng sông Cửu Long": [
        "Đồng Tháp",
        "Vĩnh Long",
        "TP. Cần Thơ",
        "Cà Mau",
        "An Giang",
    ],
}

REGION7_ORDER = [
    "Trung du và Miền núi phía Bắc",
    "Đồng bằng sông Hồng",
    "Bắc Trung Bộ",
    "Duyên hải Nam Trung Bộ",
    "Tây Nguyên",
    "Đông Nam Bộ",
    "Đồng bằng sông Cửu Long",
]

REGION_COLOR = {
    "Trung du và Miền núi phía Bắc": "#0ea5e9",
    "Đồng bằng sông Hồng": "#0284c7",
    "Bắc Trung Bộ": "#2563eb",
    "Duyên hải Nam Trung Bộ": "#06b6d4",
    "Tây Nguyên": "#14b8a6",
    "Đông Nam Bộ": "#4f46e5",
    "Đồng bằng sông Cửu Long": "#6366f1",
}

DESC_COOL_PALETTE = [
    "#1e3a8a",
    "#1d4ed8",
    "#2563eb",
    "#0284c7",
    "#0891b2",
    "#0ea5e9",
    "#22d3ee",
    "#67e8f9",
    "#a5f3fc",
    "#cffafe",
]

PROVINCE_TOKEN_ALIAS = {
    "hue": "thuathienhue",
    "thienhue": "thuathienhue",
    "tthue": "thuathienhue",
    "hochiminh": "tphochiminh",
    "thanhphohochiminh": "tphochiminh",
    "tphcm": "tphochiminh",
    "hcm": "tphochiminh",
    "hochiminhcity": "tphochiminh",
}


def _normalize_token(value: str) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def _build_region_token_map() -> dict[str, str]:
    out = {}
    for region_name, provinces in REGION7_PROVINCES.items():
        for province in provinces:
            out[_normalize_token(province)] = region_name

    # Bổ sung ánh xạ từ tên tỉnh/thành trong dữ liệu hiện tại sang taxonomy vùng mới.
    source_overrides = {
        "Cao Bằng": "Trung du và Miền núi phía Bắc",
        "Phú Thọ": "Trung du và Miền núi phía Bắc",
        "Bắc Ninh": "Trung du và Miền núi phía Bắc",
        "Lạng Sơn": "Trung du và Miền núi phía Bắc",
        "Điện Biên": "Trung du và Miền núi phía Bắc",
        "Sơn La": "Trung du và Miền núi phía Bắc",
        "Lai Châu": "Trung du và Miền núi phía Bắc",
        "Thái Nguyên": "Trung du và Miền núi phía Bắc",
        "Lào Cai": "Trung du và Miền núi phía Bắc",
        "Tuyên Quang": "Trung du và Miền núi phía Bắc",
        "Hà Nội": "Đồng bằng sông Hồng",
        "Hải Phòng": "Đồng bằng sông Hồng",
        "Hưng Yên": "Đồng bằng sông Hồng",
        "Ninh Bình": "Đồng bằng sông Hồng",
        "Quảng Ninh": "Đồng bằng sông Hồng",
        "Thanh Hóa": "Bắc Trung Bộ",
        "Nghệ An": "Bắc Trung Bộ",
        "Hà Tĩnh": "Bắc Trung Bộ",
        "Quảng Trị": "Bắc Trung Bộ",
        "Huế": "Bắc Trung Bộ",
        "Thừa Thiên Huế": "Bắc Trung Bộ",
        "Đà Nẵng": "Duyên hải Nam Trung Bộ",
        "Quảng Ngãi": "Duyên hải Nam Trung Bộ",
        "Khánh Hòa": "Duyên hải Nam Trung Bộ",
        "Bình Thuận": "Duyên hải Nam Trung Bộ",
        "Gia Lai": "Tây Nguyên",
        "Đắk Lắk": "Tây Nguyên",
        "Lâm Đồng": "Tây Nguyên",
        "TP. Hồ Chí Minh": "Đông Nam Bộ",
        "Hồ Chí Minh": "Đông Nam Bộ",
        "Đồng Nai": "Đông Nam Bộ",
        "Tây Ninh": "Đông Nam Bộ",
        "An Giang": "Đồng bằng sông Cửu Long",
        "Cà Mau": "Đồng bằng sông Cửu Long",
        "Cần Thơ": "Đồng bằng sông Cửu Long",
        "Vĩnh Long": "Đồng bằng sông Cửu Long",
        "Đồng Tháp": "Đồng bằng sông Cửu Long",
    }

    for province_name, region_name in source_overrides.items():
        out[_normalize_token(province_name)] = region_name

    return out


def _attach_region(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    p2r = _build_region_token_map()

    source_col = None
    if "province" in out.columns:
        source_col = "province"
    elif "city" in out.columns:
        source_col = "city"
    elif "location" in out.columns:
        source_col = "location"

    if source_col is None:
        out["province"] = "Không rõ"
        out["region_7"] = "Chưa xếp vùng"
        return out

    if "province" not in out.columns:
        out["province"] = out[source_col].astype(str)

    token = out[source_col].astype(str).map(_normalize_token)
    token = token.map(lambda t: PROVINCE_TOKEN_ALIAS.get(t, t))
    out["region_7"] = token.map(p2r).fillna("Chưa xếp vùng")
    return out


def _summary_by_region(frame: pd.DataFrame) -> pd.DataFrame:
    s = (
        frame.groupby("region_7")
        .agg(aqi=("aqi", "mean"), pm2_5=("pm2_5", "mean"), n=("aqi", "size"))
        .reset_index()
    )
    s = (
        s.set_index("region_7")
        .reindex(REGION7_ORDER)
        .dropna(subset=["aqi"], how="all")
        .reset_index()
    )
    return s


def _summary_by_province(frame: pd.DataFrame) -> pd.DataFrame:
    s = (
        frame.groupby(["region_7", "province"])
        .agg(aqi=("aqi", "mean"), pm2_5=("pm2_5", "mean"), n=("aqi", "size"))
        .reset_index()
    )
    return s


def _render_region_filter_boxes(options: list[str], state_key: str) -> str:
    selected = st.session_state.get(state_key, options[0])
    # st.markdown(
    #     "<div class='card-sub' style='margin-top:6px'>7 vùng địa lý</div>",
    #     unsafe_allow_html=True,
    # )

    cols = st.columns(len(options), gap="small")
    for i, option in enumerate(options):
        is_active = option == selected
        label = f"✓ {option}" if is_active else option
        clicked = cols[i].button(
            label,
            key=f"{state_key}_btn_{i}",
            width="stretch",
            type="primary" if is_active else "secondary",
        )
        if clicked and not is_active:
            st.session_state[state_key] = option

    return st.session_state.get(state_key, options[0])


def _inject_location_styles():
    st.markdown(
        """
        <style>
        .stApp, .stMarkdown, .stCaption, .stText, p, span, label, div {
            font-size: 14px;
        }
        div.stButton > button {
            height: 72px !important;
            min-height: 72px !important;
            max-height: 72px !important;
            border-radius: 10px !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            justify-content: center !important;
            text-align: center !important;
            line-height: 1.25 !important;
            padding: 0 8px !important;
        }
        div.stButton > button[kind="primary"],
        div.stButton > button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%) !important;
            color: #ffffff !important;
            border: 1px solid #1e3a8a !important;
            box-shadow: 0 8px 20px rgba(30, 58, 138, 0.25) !important;
        }
        div.stButton > button[kind="secondary"],
        div.stButton > button[data-testid="baseButton-secondary"] {
            background: #f8fbff !important;
            color: #334155 !important;
            border: 1px solid #bfdbfe !important;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.08) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _cycle_palette(size: int, palette: list[str]) -> list[str]:
    if size <= 0:
        return []
    return [palette[i % len(palette)] for i in range(size)]


def _rank_desc_colors(size: int) -> list[str]:
    if size <= 0:
        return []
    if size <= len(DESC_COOL_PALETTE):
        return DESC_COOL_PALETTE[:size]
    return _cycle_palette(size, DESC_COOL_PALETTE)


@st.cache_data(show_spinner=False)
def compute_who_stats(df_raw: pd.DataFrame) -> pd.DataFrame:
    who_df = df_raw.copy()
    who_thresholds = {
        "pm2_5": 15,
        "o3": 100,
        "no2": 25,
    }

    for col, threshold in who_thresholds.items():
        who_df[f"{col}_exceed"] = (who_df[col] > threshold).astype(int)

    return (
        who_df.groupby("climate_zone")
        .agg(
            pm25_who=("pm2_5_exceed", lambda x: round(x.mean() * 100, 1)),
            o3_who=("o3_exceed", lambda x: round(x.mean() * 100, 1)),
            no2_who=("no2_exceed", lambda x: round(x.mean() * 100, 1)),
            temp=("temp", "mean"),
            humidity=("humidity", "mean"),
            aqi=("aqi", "mean"),
        )
        .reset_index()
    )


@st.cache_data(show_spinner=False)
def compute_who_stats_by_province(df_raw: pd.DataFrame) -> pd.DataFrame:
    who_df = df_raw.copy()
    who_thresholds = {
        "pm2_5": 15,
        "o3": 100,
        "no2": 25,
    }

    for col, threshold in who_thresholds.items():
        who_df[f"{col}_exceed"] = (who_df[col] > threshold).astype(int)

    return (
        who_df.groupby("province")
        .agg(
            pm25_who=("pm2_5_exceed", lambda x: round(x.mean() * 100, 1)),
            o3_who=("o3_exceed", lambda x: round(x.mean() * 100, 1)),
            no2_who=("no2_exceed", lambda x: round(x.mean() * 100, 1)),
            temp=("temp", "mean"),
            humidity=("humidity", "mean"),
            aqi=("aqi", "mean"),
        )
        .reset_index()
    )


def render(df: pd.DataFrame):
    ctx = st.session_state.get("dashboard_context")
    if ctx is None:
        st.error("Thiếu ngữ cảnh dashboard.")
        st.stop()

    ml = ctx.get("ml")
    ax = ctx.get("ax")

    if df is None or df.empty:
        st.info("Không có dữ liệu để hiển thị tab vị trí.")
        return

    _inject_location_styles()

    work = _attach_region(df)
    region_summary = _summary_by_region(work)
    province_summary = _summary_by_province(work)

    available_regions = [
        r for r in REGION7_ORDER if r in region_summary["region_7"].tolist()
    ]
    filter_options = ["Tất cả vùng", *available_regions]

    key = "location_tab_region_filter"
    if key not in st.session_state or st.session_state[key] not in filter_options:
        st.session_state[key] = "Tất cả vùng"

    selected_region = _render_region_filter_boxes(filter_options, key)
    selected_zone = selected_region
    color_discrete_map = {
        zone: REGION_COLOR.get(zone, "#64748b") for zone in available_regions
    }

    if selected_region == "Tất cả vùng":
        chart_df = region_summary.sort_values("aqi", ascending=False).copy()
        x_col = "region_7"
        bar_colors = _rank_desc_colors(len(chart_df))
    else:
        chart_df = province_summary[
            province_summary["region_7"] == selected_region
        ].copy()
        x_col = "province"
        chart_df = chart_df.sort_values("aqi", ascending=False)
        bar_colors = _rank_desc_colors(len(chart_df))

    bar_colors_pm = bar_colors

    if chart_df.empty:
        st.info("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
        return

    c1, c2 = st.columns([1, 1], gap="small")

    with c1:
        fig_aqi = go.Figure(
            go.Bar(
                x=chart_df[x_col],
                y=chart_df["aqi"].round(1),
                marker_color=bar_colors,
                marker_line_width=1,
                marker_line_color="rgba(15,23,42,0.12)",
                opacity=0.82,
                text=chart_df["aqi"].round(1),
                texttemplate="<b>%{text}</b>",
                textposition="outside",
                textfont=dict(size=14, color="#0f172a"),
                customdata=np.stack([chart_df["n"]], axis=-1),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "AQI trung bình: %{y:.1f}<br>"
                    "Số quan trắc: %{customdata[0]}<extra></extra>"
                ),
            )
        )
        if ml and ax:
            ml(
                fig_aqi,
                h=500,
                bargap=0.25,
                margin=dict(l=60, r=40, t=60, b=120),
                title=dict(
                    text="<b>Chỉ số AQI trung bình</b>", x=0.01, font=dict(size=18)
                ),
                xaxis={
                    **ax(""),
                    "tickangle": -35,
                    "tickfont": dict(size=13, color="#475569"),
                },
                yaxis={
                    **ax("AQI"),
                    "tickfont": dict(size=13, color="#475569"),
                    "title": dict(
                        text="<b>AQI</b>", font=dict(size=15, color="#334155")
                    ),
                },
                showlegend=False,
            )
        else:
            fig_aqi.update_layout(
                height=500,
                bargap=0.25,
                margin=dict(l=60, r=40, t=60, b=120),
                title=dict(
                    text="<b>Chỉ số AQI trung bình</b>", x=0.01, font=dict(size=18)
                ),
                xaxis=dict(tickangle=-35, tickfont=dict(size=13)),
                yaxis=dict(
                    tickfont=dict(size=13),
                    title=dict(text="<b>AQI</b>", font=dict(size=15)),
                ),
                showlegend=False,
            )
        st.plotly_chart(fig_aqi, width="stretch", config={"displayModeBar": False})

    with c2:
        fig_pm = go.Figure(
            go.Bar(
                x=chart_df[x_col],
                y=chart_df["pm2_5"].round(1),
                marker_color=bar_colors_pm,
                marker_line_width=1,
                marker_line_color="rgba(15,23,42,0.12)",
                opacity=0.86,
                text=chart_df["pm2_5"].round(1),
                texttemplate="<b>%{text}</b>",
                textposition="outside",
                textfont=dict(size=14, color="#0f172a"),
                customdata=np.stack([chart_df["n"]], axis=-1),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "PM2.5 trung bình: %{y:.1f} µg/m3<br>"
                    "Số quan trắc: %{customdata[0]}<extra></extra>"
                ),
            )
        )
        if ml and ax:
            ml(
                fig_pm,
                h=500,
                bargap=0.25,
                margin=dict(l=60, r=40, t=60, b=120),
                title=dict(
                    text="<b>Nồng độ PM2.5 trung bình</b>", x=0.01, font=dict(size=18)
                ),
                xaxis={
                    **ax(""),
                    "tickangle": -35,
                    "tickfont": dict(size=13, color="#475569"),
                },
                yaxis={
                    **ax("PM2.5 (µg/m3)"),
                    "tickfont": dict(size=13, color="#475569"),
                    "title": dict(
                        text="<b>PM2.5 (µg/m3)</b>",
                        font=dict(size=15, color="#334155"),
                    ),
                },
                showlegend=False,
            )
        else:
            fig_pm.update_layout(
                height=500,
                bargap=0.25,
                margin=dict(l=60, r=40, t=60, b=120),
                title=dict(
                    text="<b>Nồng độ PM2.5 trung bình</b>", x=0.01, font=dict(size=18)
                ),
                xaxis=dict(tickangle=-35, tickfont=dict(size=13)),
                yaxis=dict(
                    tickfont=dict(size=13),
                    title=dict(text="<b>PM2.5 (µg/m3)</b>", font=dict(size=15)),
                ),
                showlegend=False,
            )
        st.plotly_chart(fig_pm, width="stretch", config={"displayModeBar": False})

    req_cols = ["pm2_5", "o3", "no2", "temp", "humidity", "aqi", "region_7"]
    if all(col in work.columns for col in req_cols):
        df_raw = work.copy()
        df_raw["climate_zone"] = df_raw["region_7"]
        who_by_zone = compute_who_stats(df_raw)

        aqi_by_zone = who_by_zone[["climate_zone", "aqi"]].copy()
        zone_order = (
            aqi_by_zone.sort_values("aqi", ascending=False)["climate_zone"]
            .dropna()
            .tolist()
        )
        who_by_zone["climate_zone"] = pd.Categorical(
            who_by_zone["climate_zone"], categories=zone_order, ordered=True
        )
        who_by_zone = who_by_zone.sort_values("climate_zone")

        if selected_zone != "Tất cả vùng":
            province_input = df_raw[df_raw["climate_zone"] == selected_zone].copy()
            who_filtered = compute_who_stats_by_province(province_input)
            who_filtered = who_filtered.sort_values("aqi", ascending=False)
            x_who_col = "province"
            who_title = f"<b>% giờ vượt ngưỡng WHO theo tỉnh - {selected_zone}</b>"
        else:
            who_filtered = who_by_zone.copy()
            x_who_col = "climate_zone"
            who_title = "<b>% giờ vượt ngưỡng WHO theo vùng</b>"

        if not who_filtered.empty:
            c3, c4 = st.columns([1, 1], gap="small")

            with c3:
                fig_who = go.Figure()
                custom = np.stack(
                    [
                        who_filtered["pm25_who"],
                        who_filtered["o3_who"],
                        who_filtered["no2_who"],
                    ],
                    axis=-1,
                )
                hovertemplate = (
                    "<b>%{x}</b><br>"
                    "PM2.5: %{customdata[0]}%<br>"
                    "O₃: %{customdata[1]}%<br>"
                    "NO₂: %{customdata[2]}%<extra></extra>"
                )

                fig_who.add_trace(
                    go.Bar(
                        x=who_filtered[x_who_col],
                        y=who_filtered["pm25_who"],
                        name="PM2.5",
                        marker=dict(
                            color=[
                                color_discrete_map.get(str(z), "#0284c7")
                                for z in who_filtered[x_who_col]
                            ]
                        ),
                        customdata=custom,
                        hovertemplate=hovertemplate,
                    )
                )
                fig_who.add_trace(
                    go.Bar(
                        x=who_filtered[x_who_col],
                        y=who_filtered["o3_who"],
                        name="O₃",
                        marker=dict(color="#1D9E75", pattern=dict(shape="/")),
                        customdata=custom,
                        hovertemplate=hovertemplate,
                    )
                )
                fig_who.add_trace(
                    go.Bar(
                        x=who_filtered[x_who_col],
                        y=who_filtered["no2_who"],
                        name="NO₂",
                        marker=dict(color="#EF9F27", pattern=dict(shape="\\")),
                        customdata=custom,
                        hovertemplate=hovertemplate,
                    )
                )
                fig_who.add_hline(
                    y=100,
                    line_dash="dash",
                    line_color="#E24B4A",
                    line_width=1.5,
                    annotation_text="Ngưỡng 100% WHO",
                    annotation_position="top left",
                    annotation_font=dict(size=11, color="#E24B4A"),
                )

                if ml and ax:
                    ml(
                        fig_who,
                        h=440,
                        bargap=0.3,
                        barmode="stack",
                        margin=dict(l=60, r=40, t=80, b=140),
                        title=dict(
                            text=who_title,
                            x=0.01,
                            font=dict(size=16),
                        ),
                        xaxis={
                            **ax(""),
                            "tickangle": -30,
                            "tickfont": dict(size=13, color="#475569"),
                        },
                        yaxis={
                            **ax("% giờ vượt ngưỡng"),
                            "tickfont": dict(size=13, color="#475569"),
                        },
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=0.98,
                            xanchor="right",
                            x=0.99,
                            bgcolor="rgba(255,255,255,0.75)",
                            bordercolor="rgba(148,163,184,0.35)",
                            borderwidth=1,
                            font=dict(size=12),
                        ),
                    )
                else:
                    fig_who.update_layout(
                        height=440,
                        bargap=0.3,
                        barmode="stack",
                        margin=dict(l=60, r=40, t=80, b=140),
                        title=dict(text=who_title, x=0.01, font=dict(size=16)),
                        xaxis=dict(tickangle=-30, tickfont=dict(size=13)),
                        yaxis=dict(title="% giờ vượt ngưỡng", tickfont=dict(size=13)),
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=0.98,
                            xanchor="right",
                            x=0.99,
                            bgcolor="rgba(255,255,255,0.75)",
                            bordercolor="rgba(148,163,184,0.35)",
                            borderwidth=1,
                        ),
                    )
                st.plotly_chart(
                    fig_who,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            with c4:
                fig_met = go.Figure()
                all_points = who_by_zone.copy()
                all_points["temp"] = all_points["temp"].round(1)
                all_points["humidity"] = all_points["humidity"].round(1)
                all_points["aqi"] = all_points["aqi"].round(1)

                x_min = float(all_points["temp"].min()) - 1
                x_max = float(all_points["temp"].max()) + 1
                y_min = float(all_points["humidity"].min()) - 2
                y_max = float(all_points["humidity"].max()) + 2

                for _, row in all_points.iterrows():
                    zone = str(row["climate_zone"])
                    is_focus = (selected_zone == "Tất cả vùng") or (
                        zone == selected_zone
                    )
                    base_size = max(10, float(row["aqi"]) / 4)
                    marker_size = (
                        base_size * 1.5
                        if (selected_zone != "Tất cả vùng" and is_focus)
                        else base_size
                    )
                    marker_opacity = 1.0 if is_focus else 0.15
                    clr = color_discrete_map.get(zone, "#0284c7")

                    fig_met.add_trace(
                        go.Scatter(
                            x=[row["temp"]],
                            y=[row["humidity"]],
                            mode="markers",
                            name=zone,
                            marker=dict(
                                size=marker_size,
                                color=clr,
                                line=dict(width=1, color="#ffffff"),
                                opacity=marker_opacity,
                            ),
                            hovertemplate=(
                                f"<b>{zone}</b><br>"
                                f"Nhiệt độ: {row['temp']:.1f}°C<br>"
                                f"Độ ẩm: {row['humidity']:.1f}%<br>"
                                f"AQI: {row['aqi']:.1f}<extra></extra>"
                            ),
                            showlegend=True,
                        )
                    )

                temp_median = float(all_points["temp"].median())
                for _, row in all_points.iterrows():
                    zone = str(row["climate_zone"])
                    xpos = "right" if float(row["temp"]) < temp_median else "left"
                    fig_met.add_annotation(
                        x=float(row["temp"]),
                        y=float(row["humidity"]),
                        text=zone,
                        showarrow=False,
                        xanchor=xpos,
                        xshift=12 if xpos == "right" else -12,
                        yshift=10,
                        font=dict(size=11, color="#334155"),
                    )

                if ml and ax:
                    ml(
                        fig_met,
                        h=440,
                        margin=dict(l=60, r=40, t=60, b=140),
                        title=dict(
                            text="<b>Nhiệt độ & độ ẩm trung bình</b>",
                            x=0.01,
                            font=dict(size=18),
                        ),
                        xaxis={
                            **ax("Nhiệt độ TB (°C)"),
                            "tickfont": dict(size=13, color="#475569"),
                            "range": [x_min, x_max],
                        },
                        yaxis={
                            **ax("Độ ẩm TB (%)"),
                            "tickfont": dict(size=13, color="#475569"),
                            "range": [y_min, y_max],
                        },
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.22,
                            xanchor="left",
                            x=0,
                            bgcolor="rgba(0,0,0,0)",
                            font=dict(size=11),
                            entrywidth=220,
                            entrywidthmode="pixels",
                        ),
                    )
                else:
                    fig_met.update_layout(
                        height=440,
                        margin=dict(l=60, r=40, t=60, b=140),
                        title=dict(
                            text="<b>Nhiệt độ & độ ẩm trung bình</b>",
                            x=0.01,
                            font=dict(size=18),
                        ),
                        xaxis=dict(
                            title="Nhiệt độ TB (°C)",
                            tickfont=dict(size=13),
                            range=[x_min, x_max],
                        ),
                        yaxis=dict(
                            title="Độ ẩm TB (%)",
                            tickfont=dict(size=13),
                            range=[y_min, y_max],
                        ),
                        legend=dict(
                            orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0
                        ),
                    )
                st.plotly_chart(
                    fig_met, width="stretch", config={"displayModeBar": False}
                )
