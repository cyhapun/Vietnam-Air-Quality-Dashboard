import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as st_components
import re
import unicodedata
import html
import json
from services.data_loader import load_weather_data
from utils.helpers import val_meta


GEO_FEATURES = ["lat", "lon"]
WEATHER_FEATURES = ["temp", "humidity", "wind_speed", "rain"]

REGION6_PROVINCES = {
    "Trung du và Miền núi phía Bắc": [
        "Cao Bằng",
        "Tuyên Quang",
        "Lào Cai",
        "Thái Nguyên",
        "Phú Thọ",
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
        "Bắc Ninh",
    ],
    "Bắc Trung Bộ": [
        "Thanh Hóa",
        "Nghệ An",
        "Hà Tĩnh",
        "Quảng Trị",
        "TP. Huế",
    ],
    "Duyên hải Nam Trung Bộ và Tây Nguyên": [
        "TP. Đà Nẵng",
        "Quảng Ngãi",
        "Khánh Hòa",
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

REGION6_ORDER = [
    "Trung du và Miền núi phía Bắc",
    "Đồng bằng sông Hồng",
    "Bắc Trung Bộ",
    "Duyên hải Nam Trung Bộ và Tây Nguyên",
    "Đông Nam Bộ",
    "Đồng bằng sông Cửu Long",
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


def _normalize_token_interaction(value: str) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def _build_region_token_map_interaction() -> dict[str, str]:
    out = {}
    for region_name, provinces in REGION6_PROVINCES.items():
        for province in provinces:
            out[_normalize_token_interaction(province)] = region_name

    source_overrides = {
        "Cao Bằng": "Trung du và Miền núi phía Bắc",
        "Phú Thọ": "Trung du và Miền núi phía Bắc",
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
        "Bắc Ninh": "Đồng bằng sông Hồng",
        "Thanh Hóa": "Bắc Trung Bộ",
        "Nghệ An": "Bắc Trung Bộ",
        "Hà Tĩnh": "Bắc Trung Bộ",
        "Quảng Trị": "Bắc Trung Bộ",
        "Huế": "Bắc Trung Bộ",
        "Thừa Thiên Huế": "Bắc Trung Bộ",
        "Đà Nẵng": "Duyên hải Nam Trung Bộ và Tây Nguyên",
        "Quảng Ngãi": "Duyên hải Nam Trung Bộ và Tây Nguyên",
        "Khánh Hòa": "Duyên hải Nam Trung Bộ và Tây Nguyên",
        "Gia Lai": "Duyên hải Nam Trung Bộ và Tây Nguyên",
        "Đắk Lắk": "Duyên hải Nam Trung Bộ và Tây Nguyên",
        "Lâm Đồng": "Duyên hải Nam Trung Bộ và Tây Nguyên",
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
        out[_normalize_token_interaction(province_name)] = region_name
    return out


def _attach_region_interaction(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    p2r = _build_region_token_map_interaction()

    source_col = None
    if "province" in out.columns:
        source_col = "province"
    elif "city" in out.columns:
        source_col = "city"
    elif "location" in out.columns:
        source_col = "location"

    if source_col is None:
        out["province"] = "Không rõ"
        out["region_6"] = "Chưa xếp vùng"
        return out

    if "province" not in out.columns:
        out["province"] = out[source_col].astype(str)

    token = out[source_col].astype(str).map(_normalize_token_interaction)
    token = token.map(lambda t: PROVINCE_TOKEN_ALIAS.get(t, t))
    out["region_6"] = token.map(p2r).fillna("Chưa xếp vùng")
    return out


def get_base_layout():
    return {
        "template": "plotly_white",
        "font": dict(family="Inter, sans-serif", size=13),
        "legend_title_text": "",
    }


def _inject_interaction_filter_styles():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 0.5rem;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] {
            position: sticky;
            top: 0.65rem;
            z-index: 18;
            padding: 0 0 4px 0;
            align-items: center;
            justify-content: flex-start;
            gap: 10px;
            background: transparent;
            box-shadow: none;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] label {
            margin-bottom: 0.18rem !important;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] [data-testid="stWidgetLabel"] {
            margin-bottom: 0.1rem;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] > div {
            margin-bottom: 0.1rem;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] div[data-baseweb="select"] > div,
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] .stDateInput > div > div {
            height: 40px;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 120ms ease;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] div[data-baseweb="select"] > div:hover,
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] .stDateInput > div > div:hover {
            border-color: #9fc0df !important;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] div[data-baseweb="select"] > div:focus-within,
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] .stDateInput > div > div:focus-within {
            border-color: #2f7fc1 !important;
            box-shadow: 0 0 0 1px #2f7fc1 !important;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] .stSlider > div {
            padding-top: 0;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] .stSlider [data-testid="stTickBar"] {
            display: none;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] .stSlider [data-testid="stSliderThumbValue"] {
            font-size: 0.78rem;
            color: #1f3d5b;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] .stButton > button {
            border-radius: 8px;
            height: 40px;
            min-height: 40px;
            box-shadow: none;
            background: transparent;
            border: 1px solid #d3deea;
            color: #37556f;
            padding: 0.2rem 0.55rem;
        }
        .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] .stButton > button:hover {
            border-color: #9fc0df;
            color: #224764;
        }
        @media (max-width: 1100px) {
            .interaction-toolbar-anchor + div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
                row-gap: 8px;
            }
        }

        .interaction-rank-card {
            border: 1px solid #d9e3ef;
            border-radius: 14px;
            background: #f8fbff;
            padding: 12px 12px 10px 12px;
        }
        .interaction-rank-title {
            font-size: 15px;
            font-weight: 800;
            color: #1f2f46;
            margin: 0 2px 10px 2px;
        }
        .interaction-rank-sub {
            font-size: 12px;
            color: #68809b;
            margin: 0 2px 8px 2px;
        }
        .interaction-rank-head {
            display: grid;
            grid-template-columns: 1fr auto;
            font-size: 12px;
            color: #607a95;
            font-weight: 700;
            padding: 0 4px 7px 4px;
            border-bottom: 1px solid #e4ecf5;
            margin-bottom: 6px;
        }
        .interaction-rank-row {
            display: grid;
            grid-template-columns: 1fr auto;
            align-items: center;
            column-gap: 8px;
            padding: 8px 8px 7px 8px;
            border: 1px solid #e3ebf4;
            border-radius: 10px;
            background: #ffffff;
            margin-bottom: 7px;
            transition: border-color 120ms ease, transform 120ms ease;
        }
        .interaction-rank-row:hover {
            border-color: #c9d9ea;
            transform: translateY(-1px);
        }
        .interaction-rank-list {
            max-height: none;
            overflow-y: visible;
            padding-right: 2px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .interaction-rank-name {
            font-size: 13px;
            color: #243b55;
            font-weight: 700;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .interaction-rank-value {
            margin-bottom: 0;
            font-weight: 800;
            color: #136fca;
        }
        .interaction-rank-bar {
            grid-column: 1 / -1;
            height: 4px;
            border-radius: 999px;
            background: #e8f0fa;
            overflow: hidden;
            margin-top: 4px;
        }
        .interaction-rank-fill {
            height: 100%;
            background: linear-gradient(90deg, #2f8edc 0%, #1869c5 100%);
            border-radius: 999px;
        }

        .interaction-region-rank-card {
            border: 1px solid #d9e3ef;
            border-radius: 14px;
            background: #f8fbff;
            padding: 12px 12px 10px 12px;
            min-height: 380px;
            display: flex;
            flex-direction: column;
        }
        .interaction-region-rank-head {
            display: grid;
            grid-template-columns: 1fr 170px 74px;
            font-size: 12px;
            color: #607a95;
            font-weight: 700;
            padding: 0 4px 7px 4px;
            border-bottom: 1px solid #e4ecf5;
            margin-bottom: 8px;
            column-gap: 10px;
        }
        .interaction-region-rank-head span:nth-child(2) {
            justify-self: center;
        }
        .interaction-region-rank-head span:nth-child(3) {
            justify-self: end;
        }
        .interaction-region-rank-list {
            max-height: none;
            overflow-y: visible;
            padding-right: 2px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .interaction-region-rank-item {
            border: 1px solid #e3ebf4;
            border-radius: 10px;
            background: #ffffff;
            padding: 10px;
            margin-bottom: 0;
            transition: border-color 120ms ease, transform 120ms ease;
        }
        .interaction-region-rank-item:hover {
            border-color: #c9d9ea;
            transform: translateY(-1px);
        }
        .interaction-region-rank-top {
            border-color: #cddff2;
            background: linear-gradient(180deg, #ffffff 0%, #f4f9ff 100%);
        }
        .interaction-region-rank-row {
            display: grid;
            grid-template-columns: 24px 1fr 170px 74px;
            align-items: center;
            column-gap: 10px;
        }
        .interaction-region-rank-badge {
            min-width: 22px;
            height: 22px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 800;
            color: #1f4f7a;
            background: #eaf3fc;
            border: 1px solid #d2e3f4;
        }
        .interaction-region-rank-name {
            font-size: 13px;
            color: #243b55;
            font-weight: 700;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .interaction-region-rank-value {
            font-size: 15px;
            font-weight: 800;
            color: #145fae;
            letter-spacing: 0.1px;
            justify-self: end;
        }
        .interaction-region-rank-status {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 24px;
            border-radius: 7px;
            padding: 3px 10px;
            width: 170px;
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            justify-self: center;
            overflow: hidden;
            text-overflow: ellipsis;
            text-align: center;
        }
        .interaction-impact-titlebox {
            border: 1px solid #dce8f4;
            background: linear-gradient(135deg, #f8fbff 0%, #eef5fc 100%);
            border-radius: 12px;
            padding: 10px 12px;
            margin: 0 0 8px 0;
        }
        .interaction-impact-titlebox .t {
            font-size: 14px;
            font-weight: 800;
            color: #1f2f46;
        }
        .interaction-impact-titlebox .s {
            font-size: 11px;
            color: #67809b;
        }
        .interaction-heat-rank-scale {
            display: grid;
            grid-template-columns: 36px 1fr 36px;
            align-items: center;
            gap: 10px;
            margin-top: 2px;
            margin-bottom: 2px;
        }
        .interaction-heat-rank-end {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: 1px solid #c9dced;
            background: #e8f1fa;
            color: #184f7e;
            font-size: 18px;
            font-weight: 800;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }
        .interaction-heat-rank-mid {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .interaction-heat-rank-line {
            position: relative;
            height: 6px;
            border-radius: 999px;
            background: linear-gradient(90deg, #d7e6f4 0%, #8bb7e1 55%, #2f7fc1 100%);
        }
        .interaction-heat-rank-line::after {
            content: "";
            position: absolute;
            right: -1px;
            top: 50%;
            transform: translateY(-50%);
            width: 0;
            height: 0;
            border-top: 5px solid transparent;
            border-bottom: 5px solid transparent;
            border-left: 8px solid #2f7fc1;
        }
        .interaction-heat-rank-nums {
            display: flex;
            justify-content: space-between;
            color: #557492;
            font-size: 12px;
            font-weight: 700;
            padding: 0 2px;
        }

        .interaction-chart-title {
            font-size: 15px;
            font-weight: 800;
            color: #1f2f46;
            margin: 2px 0 10px 0;
            line-height: 1.35;
        }
        .interaction-chart-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 4px;
        }
        .interaction-chart-caption {
            font-size: 12px;
            color: #6f8298;
            margin: 0 0 8px 0;
        }
        .stSegmentedControl [role="radiogroup"] {
            font-size: 13px;
            font-weight: 600;
        }

        .interaction-flow-scale {
            display: grid;
            grid-template-columns: auto 1fr auto;
            align-items: center;
            gap: 10px;
            margin: -6px 6px 0 6px;
            opacity: 0.78;
            animation: interactionFadeIn 420ms ease-out;
            transition: opacity 140ms ease;
        }
        .interaction-flow-scale:hover {
            opacity: 0.96;
        }
        .interaction-flow-label {
            font-size: 13px;
            font-weight: 500;
            color: #74879a;
            line-height: 1;
            white-space: nowrap;
        }
        .interaction-flow-track {
            position: relative;
            height: 7px;
            border-radius: 999px;
            background: linear-gradient(90deg, #d3dbe5 0%, #9fc5ea 55%, #2f7fc1 100%);
        }
        .interaction-flow-track::after {
            content: "";
            position: absolute;
            right: -1px;
            top: 50%;
            transform: translateY(-50%);
            width: 0;
            height: 0;
            border-top: 6px solid transparent;
            border-bottom: 6px solid transparent;
            border-left: 9px solid #2f7fc1;
        }
        @keyframes interactionFadeIn {
            from {
                opacity: 0;
                transform: translateY(3px);
            }
            to {
                opacity: 0.78;
                transform: translateY(0);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_rank_table_html(rank_top: pd.DataFrame, rank_col: str, subtitle: str = "Top tỉnh có mức giảm mạnh theo bộ lọc hiện tại") -> str:
    if rank_top.empty:
        return "<div class='interaction-rank-card'><div class='interaction-rank-title'>Bảng xếp hạng tỉnh</div><div style='font-size:12px;color:#60758b;padding:6px 4px;'>Không có dữ liệu.</div></div>"

    max_val = max(float(rank_top[rank_col].max()), 0.0001)
    rows = []
    for idx, row in enumerate(rank_top.itertuples(index=False), start=1):
        province = html.escape(str(getattr(row, "province")))
        value = float(getattr(row, rank_col))
        width_pct = max(0.0, min(100.0, value / max_val * 100.0))
        rows.append(
            "<div class='interaction-rank-row'>"
            f"<div class='interaction-rank-name'>{idx}. {province}</div>"
            f"<div class='interaction-rank-value'>{value:.1f}%</div>"
            "<div class='interaction-rank-bar'>"
            f"<div class='interaction-rank-fill' style='width:{width_pct:.1f}%'></div>"
            "</div>"
            "</div>"
        )

    return (
        "<div class='interaction-rank-card'>"
        "<div class='interaction-rank-title'>Bảng xếp hạng tỉnh</div>"
        f"<div class='interaction-rank-sub'>{html.escape(subtitle)}</div>"
        "<div class='interaction-rank-head'><span>Tỉnh</span><span>%</span></div>"
        "<div class='interaction-rank-list'>" + "".join(rows) + "</div>" + "</div>"
    )


def _render_region_aqi_rank_html(
    rank_region: pd.DataFrame,
    name_col: str = "region_6",
    entity_label: str = "Vùng",
    title: str = "Xếp hạng AQI trung bình giữa các vùng",
):
    if rank_region.empty:
        return (
            "<div class='interaction-region-rank-card'>"
            f"<div class='interaction-rank-title'>{html.escape(title)}</div>"
            "<div style='font-size:12px;color:#60758b;padding:6px 4px;'>Không có dữ liệu.</div>"
            "</div>"
        )

    rows = []
    short_status_map = {
        "Không lành mạnh cho nhóm nhạy cảm": "Nhạy cảm",
        "Không khỏe mạnh": "Không khỏe mạnh",
        "Rất không tốt cho sức khỏe": "Rất không tốt",
        "Nguy hiểm": "Nguy hiểm",
        "Vừa phải": "Vừa phải",
        "Tốt": "Tốt",
    }
    for idx, row in enumerate(rank_region.itertuples(index=False), start=1):
        region_name = html.escape(str(getattr(row, name_col)))
        aqi_val = float(getattr(row, "aqi_mean"))
        status_lbl, status_clr = val_meta(aqi_val, "aqi")
        full_status = html.escape(str(status_lbl))
        status_lbl = html.escape(short_status_map.get(str(status_lbl), str(status_lbl)))
        top_class = " interaction-region-rank-top" if idx == 1 else ""
        rows.append(
            "<div class='interaction-region-rank-item" + top_class + "'>"
            "<div class='interaction-region-rank-row'>"
            f"<span class='interaction-region-rank-badge'>{idx}</span>"
            f"<div class='interaction-region-rank-name'>{region_name}</div>"
            f"<span class='interaction-region-rank-status' style='background:{status_clr};' title='{full_status}'>{status_lbl}</span>"
            f"<div class='interaction-region-rank-value'>{aqi_val:.1f}</div>"
            "</div>"
            "</div>"
        )

    return (
        "<div class='interaction-region-rank-card'>"
        f"<div class='interaction-rank-title'>{html.escape(title)}</div>"
        "<div class='interaction-rank-sub'>AQI càng cao thể hiện mức ô nhiễm không khí cao hơn</div>"
        f"<div class='interaction-region-rank-head'><span>{html.escape(entity_label)}</span><span>Trạng thái</span><span>AQI</span></div>"
        "<div class='interaction-region-rank-list'>"
        + "".join(rows)
        + "</div>"
        + "</div>"
    )


def _resolve_date_range(date_range, fallback_min, fallback_max):
    if isinstance(date_range, tuple):
        if len(date_range) == 2:
            start_date, end_date = date_range
        elif len(date_range) == 1:
            start_date = end_date = date_range[0]
        else:
            start_date, end_date = fallback_min, fallback_max
    else:
        start_date = end_date = date_range

    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def _render_flow_scale(left_label: str, right_label: str):
    st.markdown(
        f"""
        <div class="interaction-flow-scale">
            <div class="interaction-flow-label">{left_label}</div>
            <div class="interaction-flow-track"></div>
            <div class="interaction-flow-label" style="text-align:right;">{right_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _safe_reduction(base_val, compare_val):
    if pd.isna(base_val) or pd.isna(compare_val) or base_val == 0:
        return np.nan
    return (base_val - compare_val) / base_val * 100.0


def _prepare_interaction_source(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()

    out = _attach_region_interaction(frame.copy())
    if "timestamp" not in out.columns:
        return pd.DataFrame()

    if not pd.api.types.is_datetime64_any_dtype(out["timestamp"]):
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    return out.dropna(subset=["timestamp"])


@st.cache_data
def calc_wind_curve(df):
    work = df.copy()
    req_cols = ["wind_speed", "aqi", "pm2_5"]
    if any(c not in work.columns for c in req_cols):
        return pd.DataFrame()

    work = work.dropna(subset=req_cols)
    if len(work) < 20:
        return pd.DataFrame()

    try:
        work["wind_group_idx"] = pd.qcut(
            work["wind_speed"], q=6, labels=False, duplicates="drop"
        )
    except ValueError:
        return pd.DataFrame()

    work = work.dropna(subset=["wind_group_idx"])
    if work.empty:
        return pd.DataFrame()

    work["wind_group_idx"] = work["wind_group_idx"].astype(int)
    n_bins = int(work["wind_group_idx"].max()) + 1
    if n_bins < 3:
        return pd.DataFrame()

    labels = [f"Mức {i}" for i in range(1, n_bins + 1)]
    work["wind_group"] = work["wind_group_idx"].map(lambda i: labels[i])

    grouped = (
        work.groupby(["wind_group_idx", "wind_group"], observed=False)
        .agg(aqi=("aqi", "mean"), pm2_5=("pm2_5", "mean"), n=("aqi", "size"))
        .reset_index()
    )
    grouped["wind_group"] = pd.Categorical(
        grouped["wind_group"], categories=labels, ordered=True
    )
    grouped = grouped.sort_values("wind_group_idx").dropna(subset=["wind_group"])
    return grouped[["wind_group", "aqi", "pm2_5", "n"]]


@st.cache_data
def calc_rain_curve(df):
    work = df.copy()
    req_cols = ["rain", "aqi", "pm2_5"]
    if any(c not in work.columns for c in req_cols):
        return pd.DataFrame()

    work = work.dropna(subset=req_cols)
    if work.empty:
        return pd.DataFrame()

    try:
        work["rain_group_idx"] = pd.qcut(
            work["rain"], q=6, labels=False, duplicates="drop"
        )
    except ValueError:
        return pd.DataFrame()

    work = work.dropna(subset=["rain_group_idx"])
    if work.empty:
        return pd.DataFrame()

    work["rain_group_idx"] = work["rain_group_idx"].astype(int)
    n_bins = int(work["rain_group_idx"].max()) + 1
    if n_bins < 3:
        return pd.DataFrame()

    labels = [f"Mức {i}" for i in range(1, n_bins + 1)]
    work["rain_group"] = work["rain_group_idx"].map(lambda i: labels[i])

    grouped = (
        work.groupby(["rain_group_idx", "rain_group"], observed=False)
        .agg(aqi=("aqi", "mean"), pm2_5=("pm2_5", "mean"), n=("aqi", "size"))
        .reset_index()
    )
    grouped["rain_group"] = pd.Categorical(
        grouped["rain_group"], categories=labels, ordered=True
    )
    grouped = grouped.sort_values("rain_group_idx").dropna(subset=["rain_group"])
    return grouped[["rain_group", "aqi", "pm2_5", "n"]]


@st.cache_data
def calc_cleaning_overview(df):
    work = df.copy().dropna(subset=["aqi", "pm2_5", "wind_speed", "rain"])
    if len(work) < 30:
        return pd.DataFrame()

    wind_p25 = work["wind_speed"].quantile(0.25)
    wind_p75 = work["wind_speed"].quantile(0.75)

    low_wind = work[work["wind_speed"] <= wind_p25]
    high_wind = work[work["wind_speed"] >= wind_p75]
    no_rain = work[work["rain"] <= 0]
    rainy = work[work["rain"] > 0]

    rows = []
    for metric, label in [("aqi", "AQI"), ("pm2_5", "PM2.5")]:
        rows.append(
            {
                "metric": label,
                "wind_reduction_pct": _safe_reduction(
                    low_wind[metric].mean(), high_wind[metric].mean()
                ),
                "rain_reduction_pct": _safe_reduction(
                    no_rain[metric].mean(), rainy[metric].mean()
                ),
            }
        )
    return pd.DataFrame(rows)


@st.cache_data
def calc_province_cleaning_strength(df, min_samples):
    req_cols = ["province", "aqi", "pm2_5", "wind_speed", "rain"]
    if any(c not in df.columns for c in req_cols):
        return pd.DataFrame()

    out = []
    for province, g in df.groupby("province", observed=False):
        g = g.dropna(subset=["aqi", "pm2_5", "wind_speed", "rain"])
        if len(g) < min_samples:
            continue

        wind_p25 = g["wind_speed"].quantile(0.25)
        wind_p75 = g["wind_speed"].quantile(0.75)

        low_wind = g[g["wind_speed"] <= wind_p25]
        high_wind = g[g["wind_speed"] >= wind_p75]
        no_rain = g[g["rain"] <= 0]
        rainy = g[g["rain"] > 0]

        if (
            len(low_wind) < 5
            or len(high_wind) < 5
            or len(no_rain) < 5
            or len(rainy) < 5
        ):
            continue

        aqi_wind = _safe_reduction(low_wind["aqi"].mean(), high_wind["aqi"].mean())
        aqi_rain = _safe_reduction(no_rain["aqi"].mean(), rainy["aqi"].mean())
        pm25_wind = _safe_reduction(low_wind["pm2_5"].mean(), high_wind["pm2_5"].mean())
        pm25_rain = _safe_reduction(no_rain["pm2_5"].mean(), rainy["pm2_5"].mean())

        out.append(
            {
                "province": province,
                "aqi_wind_pct": aqi_wind,
                "aqi_rain_pct": aqi_rain,
                "aqi_cleaning_pct": np.nanmean([aqi_wind, aqi_rain]),
                "pm2_5_cleaning_pct": np.nanmean([pm25_wind, pm25_rain]),
                "overall_cleaning_pct": np.nanmean(
                    [aqi_wind, aqi_rain, pm25_wind, pm25_rain]
                ),
                "n_obs": len(g),
            }
        )

    if not out:
        return pd.DataFrame(
            columns=[
                "province",
                "aqi_wind_pct",
                "aqi_rain_pct",
                "aqi_cleaning_pct",
                "pm2_5_cleaning_pct",
                "overall_cleaning_pct",
                "n_obs",
            ]
        )

    res = pd.DataFrame(out)
    res = res.dropna(subset=["overall_cleaning_pct"])
    if res.empty:
        return pd.DataFrame(
            columns=[
                "province",
                "aqi_wind_pct",
                "aqi_rain_pct",
                "aqi_cleaning_pct",
                "pm2_5_cleaning_pct",
                "overall_cleaning_pct",
                "n_obs",
            ]
        )
    return res.sort_values("overall_cleaning_pct", ascending=False)


@st.cache_data
def calc_region_factor_impact(df, min_samples):
    req_cols = ["region_6", "aqi", *GEO_FEATURES, *WEATHER_FEATURES]
    if any(c not in df.columns for c in req_cols):
        return pd.DataFrame()

    out = []
    for region, g in df.groupby("region_6", observed=False):
        if region == "Chưa xếp vùng":
            continue

        for feature in [*GEO_FEATURES, *WEATHER_FEATURES]:
            g_sub = g[["aqi", feature]].dropna()
            if len(g_sub) < min_samples:
                continue
            corr = g_sub["aqi"].corr(g_sub[feature], method="spearman")
            out.append(
                {
                    "region_6": region,
                    "feature": feature,
                    "corr": corr,
                    "abs_corr": abs(corr),
                    "feature_type": (
                        "Địa lý" if feature in GEO_FEATURES else "Thời tiết"
                    ),
                    "n_obs": len(g_sub),
                }
            )

    return pd.DataFrame(out).dropna(subset=["corr"])


def render(df: pd.DataFrame):
    if df is None or df.empty:
        st.warning("Không có dữ liệu.")
        return

    base_work = _prepare_interaction_source(df)
    if base_work.empty:
        st.warning("Không có dữ liệu.")
        return

    st.markdown(
        '<div class="card" style="padding: 1.3rem; border-left: 5px solid #0ea5e9; background: linear-gradient(to right, #ffffff, #f8fbff); margin-bottom: 0.4rem;">'
        '<div style="font-size: 1.3rem; font-weight: 700; color: #1e293b; margin-bottom: 8px; display: flex; align-items: center; gap: 12px;">'
        '<span class="q-tag" style="font-size: 0.85rem; padding: 4px 10px; background: #e0f2fe; color: #0369a1; border-radius: 6px;">TƯƠNG TÁC</span>'
        "Phân tích tác động Thời tiết - Địa lý"
        "</div>"
        '<div style="font-size: 1rem; color: #64748b; line-height: 1.5;">Khám phá mối liên hệ giữa các yếu tố môi trường và vị trí địa lý đến chất lượng không khí.</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    _inject_interaction_filter_styles()

    if "interaction_region_select" not in st.session_state:
        st.session_state["interaction_region_select"] = "Tất cả"
    if "interaction_province_select" not in st.session_state:
        st.session_state["interaction_province_select"] = "Tất cả"
    if "interaction_time_range" not in st.session_state:
        st.session_state["interaction_time_range"] = "Năm 2025"
    if "interaction_rank_focus" not in st.session_state:
        st.session_state["interaction_rank_focus"] = "AQI"

    time_options = ["Năm 2025", "24h", "7 ngày", "30 ngày", "3 tháng"]
    if st.session_state.get("interaction_time_range") not in time_options:
        st.session_state["interaction_time_range"] = "Năm 2025"

    current_time_range = st.session_state["interaction_time_range"]
    if current_time_range == "Năm 2025":
        year_2025_df = load_weather_data()
        work = _prepare_interaction_source(year_2025_df)
        if work.empty:
            st.warning("Không tìm thấy dữ liệu trong nguồn aqi_year_2025.")
            return
    else:
        work = base_work

    available_regions = [
        r for r in REGION6_ORDER if r in work["region_6"].dropna().unique().tolist()
    ]

    # Keep a fixed minimum sample threshold after removing the slider from UI.
    min_samples = 60

    region_options = ["Tất cả", *available_regions]
    if st.session_state["interaction_region_select"] not in region_options:
        st.session_state["interaction_region_select"] = "Tất cả"

    selected_region = st.session_state["interaction_region_select"]
    region_scope = (
        work
        if selected_region == "Tất cả"
        else work[work["region_6"] == selected_region]
    )
    province_options = [
        "Tất cả",
        *sorted(region_scope["province"].dropna().unique().tolist()),
    ]
    if st.session_state["interaction_province_select"] not in province_options:
        st.session_state["interaction_province_select"] = "Tất cả"

    st.markdown(
        '<div class="interaction-toolbar-anchor"></div>', unsafe_allow_html=True
    )
    c1, c2, c3, c_spacer = st.columns([2.0, 0.9, 0.9, 4.0], gap="small")

    with c1:
        selected_region = st.selectbox(
            "Vùng",
            options=region_options,
            key="interaction_region_select",
        )

    region_scope = (
        work
        if selected_region == "Tất cả"
        else work[work["region_6"] == selected_region]
    )
    province_options = [
        "Tất cả",
        *sorted(region_scope["province"].dropna().unique().tolist()),
    ]
    if st.session_state["interaction_province_select"] not in province_options:
        st.session_state["interaction_province_select"] = "Tất cả"

    with c2:
        selected_province = st.selectbox(
            "Thành Phố / Tỉnh",
            options=province_options,
            key="interaction_province_select",
        )

    with c3:
        time_range = st.selectbox(
            "Thời gian",
            options=time_options,
            key="interaction_time_range",
        )
        if time_range != current_time_range:
            st.rerun()

        if time_range == "Năm 2025":
            start_ts = work["timestamp"].min()
            end_ts = work["timestamp"].max()
        else:
            delta_map = {
                "24h": pd.Timedelta(hours=24),
                "7 ngày": pd.Timedelta(days=7),
                "30 ngày": pd.Timedelta(days=30),
                "3 tháng": pd.Timedelta(days=90),
            }
            end_ts = work["timestamp"].max()
            start_ts = max(work["timestamp"].min(), end_ts - delta_map[time_range])

    with c_spacer:
        st.markdown("&nbsp;", unsafe_allow_html=True)

    selected_regions = (
        available_regions if selected_region == "Tất cả" else [selected_region]
    )
    all_provinces = sorted(region_scope["province"].dropna().unique().tolist())
    selected_provinces = (
        all_provinces if selected_province == "Tất cả" else [selected_province]
    )

    mask = (
        work["region_6"].isin(
            selected_regions if selected_regions else available_regions
        )
        & work["province"].isin(
            selected_provinces if selected_provinces else all_provinces
        )
        & (work["timestamp"] >= start_ts)
        & (work["timestamp"] <= end_ts)
    )
    f_df = work[mask].copy()

    if f_df.empty:
        st.warning("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
        return

    if "interaction_weather_chart" not in st.session_state:
        st.session_state["interaction_weather_chart"] = "Gió"

    # === TOP SECTION: Interactive heatmap (weather vs AQI) + region AQI ranking ===
    st.markdown("<br>", unsafe_allow_html=True)
    map_df = f_df[f_df["region_6"] != "Chưa xếp vùng"].copy()

    if map_df.empty:
        st.info("Không có dữ liệu để hiển thị.")
        return

    current_top_region = st.session_state.get("interaction_region_select", "Tất cả")
    is_single_region = current_top_region != "Tất cả"

    # Only weather/env features (not AQI itself) correlated against AQI
    weather_features = [
        "temp",
        "humidity",
        "rain",
        "wind_speed",
        "wind_dir",
        "pressure",
        "cloud",
    ]
    feature_labels_map = {
        "temp": "Nhiệt độ",
        "humidity": "Độ ẩm",
        "rain": "Lượng mưa",
        "wind_speed": "Tốc độ gió",
        "wind_dir": "Hướng gió",
        "pressure": "Áp suất",
        "cloud": "Mây",
    }
    avail_weather = [c for c in weather_features if c in map_df.columns]
    label_list = [feature_labels_map.get(c, c) for c in avail_weather]

    # --- Helper: compute 1-row correlation vector (each weather feature vs AQI) ---
    def compute_aqi_corr_row(df):
        if len(df) < 5 or "aqi" not in df.columns or not avail_weather:
            return None
        row = []
        for col in avail_weather:
            sub = df[["aqi", col]].dropna()
            if len(sub) < 5:
                row.append(None)
            else:
                v = sub["aqi"].corr(sub[col], method="spearman")
                row.append(None if pd.isna(v) else round(float(v), 4))
        return row  # list of len(avail_weather) values

    # --- Pre-compute: national + per-region + per-province ---
    corr_data = {"__all__": compute_aqi_corr_row(map_df)}
    for region_name, grp in map_df.groupby("region_6", observed=True):
        corr_data[region_name] = compute_aqi_corr_row(grp)
    for province_name, grp in map_df.groupby("province", observed=True):
        key = f"__prov__{province_name}"
        corr_data[key] = compute_aqi_corr_row(grp)

    short_status_map = {
        "Không lành mạnh cho nhóm nhạy cảm": "Nhạy cảm",
        "Không khỏe mạnh": "Không khỏe mạnh",
        "Rất không tốt cho sức khỏe": "Rất không tốt",
        "Nguy hiểm": "Nguy hiểm",
        "Vừa phải": "Vừa phải",
        "Tốt": "Tốt",
    }

    def _build_rank_rows(rank_df, name_col, key_prefix=""):
        rows_html = ""
        for idx, row in enumerate(rank_df.itertuples(index=False), start=1):
            entity_name = str(getattr(row, name_col))
            aqi_val = float(getattr(row, "aqi_mean"))
            status_lbl, status_clr = val_meta(aqi_val, "aqi")
            short_lbl = short_status_map.get(str(status_lbl), str(status_lbl))
            
            # Determine text color for better contrast
            # labels 'Tốt', 'Vừa phải', 'Không lành mạnh cho nhóm nhạy cảm' have light backgrounds
            text_clr = "#1e293b" if str(status_lbl) in ["Tốt", "Vừa phải", "Không lành mạnh cho nhóm nhạy cảm"] else "#ffffff"
            
            safe_name = html.escape(entity_name)
            safe_key = html.escape(f"{key_prefix}{entity_name}")
            top_class = " rrr-top" if idx == 1 else ""
            rows_html += (
                f"<div class='rrr-item{top_class}' data-region='{safe_key}'>"
                "<div class='rrr-row'>"
                f"<span class='rrr-badge'>{idx}</span>"
                f"<div class='rrr-name'>{safe_name}</div>"
                f"<span class='rrr-status' style='background:{status_clr}; color:{text_clr};'>{html.escape(short_lbl)}</span>"
                f"<div class='rrr-val'>{aqi_val:.1f}</div>"
                "</div>"
                "</div>"
            )
        return rows_html

    # Build region ranking - use FULL work df (unfiltered by region) so all regions appear
    all_regions_df = work[work["region_6"] != "Chưa xếp vùng"].copy()
    all_regions_df = all_regions_df[
        (all_regions_df["timestamp"] >= f_df["timestamp"].min())
        & (all_regions_df["timestamp"] <= f_df["timestamp"].max())
    ]
    # Recompute national corr from all_regions_df
    corr_data["__all__"] = compute_aqi_corr_row(all_regions_df)
    for region_name, grp in all_regions_df.groupby("region_6", observed=True):
        corr_data[region_name] = compute_aqi_corr_row(grp)

    _region_order_map = {r: i for i, r in enumerate(REGION6_ORDER)}
    rank_regions = (
        all_regions_df.groupby("region_6", as_index=False, observed=True)
        .agg(aqi_mean=("aqi", "mean"))
        .dropna(subset=["aqi_mean"])
    )
    rank_regions["_order"] = rank_regions["region_6"].map(_region_order_map).fillna(999)
    rank_regions = rank_regions.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)
    region_rows_html = _build_rank_rows(rank_regions, "region_6", key_prefix="")

    # Build province ranking (provinces within selected region, if filtered)
    if is_single_region:
        rank_provinces = (
            map_df.groupby("province", as_index=False, observed=True)
            .agg(aqi_mean=("aqi", "mean"), lat=("lat", "mean"))
            .dropna(subset=["aqi_mean"])
            .sort_values("lat", ascending=False)
            .reset_index(drop=True)
        )
        province_rows_html = _build_rank_rows(
            rank_provinces, "province", key_prefix="__prov__"
        )
        rank_title = html.escape(f"Các tỉnh trong vùng {current_top_region}")
        rank_col_label = "Tỉnh / Thành phố"
        initial_rows = province_rows_html
        initial_key = (
            f"__prov__{rank_provinces['province'].iloc[0]}"
            if not rank_provinces.empty
            else "__all__"
        )
        initial_subtitle = f"Phạm vi: <b>Vùng {html.escape(current_top_region)}</b>."
    else:
        rank_title = "Xếp hạng AQI theo vị trí địa lý"
        rank_col_label = "Vùng"
        initial_rows = region_rows_html
        initial_key = "__all__"
        initial_subtitle = "Phạm vi: <b>Toàn quốc</b>. Màu xanh giúp giảm ô nhiễm, màu đỏ làm tăng ô nhiễm."

    rank_item_count = int(
        len(rank_provinces) if is_single_region else len(rank_regions)
    )
    # Keep enough room for title/subheader and all rows without scroll or overflow.
    card_height_px = max(320, 116 + rank_item_count * 44)
    component_height_px = card_height_px + 24

    corr_json = json.dumps(corr_data, ensure_ascii=False)
    labels_json = json.dumps(label_list, ensure_ascii=False)
    initial_key_json = json.dumps(initial_key)
    initial_subtitle_json = json.dumps(initial_subtitle)

    component_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:'Inter','Segoe UI',sans-serif;}}
body{{background:transparent;overflow-x:hidden;}}
.wrapper{{display:flex;gap:18px;width:100%;padding:4px 0;align-items:stretch;}}
.heat-panel{{flex:1 1 0;max-width:50%;width:50%;min-width:0;display:flex;flex-direction:column;}}
.titlebox{{background:#f4f8fc;border-left:4px solid #3a7bd5;border-radius:8px;padding:10px 14px;margin-bottom:10px;flex-shrink:0;}}
.titlebox .t{{font-weight:700;font-size:13px;color:#1f2f46;margin-bottom:3px;}}
.titlebox .s{{font-size:11.5px;color:#607a95;line-height:1.4;}}
.titlebox .s b{{color:#145fae;}}
#heatmap-div{{width:100%;}}
.heat-card{{background:#fff;border:1px solid #dde8f2;border-radius:12px;padding:12px 14px;box-shadow:0 2px 8px rgba(60,100,160,.07);height:{card_height_px}px;display:flex;flex-direction:column;}}
.heatmap-wrap{{flex:1;display:flex;align-items:center;justify-content:center;border:1px solid #e7eff7;border-radius:10px;background:linear-gradient(96deg,#f8fbff 0%,#ffffff 46%,#f1f7fd 100%);padding:6px 8px;}}
.rank-panel{{flex:1 1 0;max-width:50%;width:50%;min-width:0;display:flex;flex-direction:column;}}
.rank-shell{{position:relative;display:flex;height:{card_height_px}px;align-items:stretch;padding-left:34px;}}
.nsb{{position:absolute;left:0;top:8px;bottom:8px;width:28px;display:flex;flex-direction:column;align-items:center;justify-content:space-between;padding:0;pointer-events:none;}}
.nsb-label{{font-size:14px;font-weight:800;color:#5c7895;line-height:1;white-space:nowrap;}}
.nsb-track{{position:relative;width:7px;flex:1;border-radius:999px;background:linear-gradient(180deg,#d3dbe5 0%,#9fc5ea 55%,#2f7fc1 100%);margin:8px 0;}}
.nsb-track::after{{content:'';position:absolute;left:50%;bottom:-1px;transform:translateX(-50%);width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:9px solid #2f7fc1;}}
.rcard{{background:#fff;border:1px solid #dde8f2;border-radius:12px;padding:12px 14px;box-shadow:0 2px 8px rgba(60,100,160,.07);height:100%;display:flex;flex-direction:column;flex:1;min-width:0;}}
.rtitle{{font-weight:700;font-size:15px;color:#1f2f46;margin-bottom:2px;}}
.rsub{{font-size:11.5px;color:#607a95;margin-bottom:8px;}}
.rhead{{display:grid;grid-template-columns:minmax(0,1fr) 86px 48px;column-gap:6px;align-items:center;font-size:11.5px;font-weight:700;color:#145fae;padding:3px 4px;border-bottom:1px solid #dde8f2;margin-bottom:2px;}}
.rhead .h1{{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}.rhead .h2{{text-align:center;}}.rhead .h3{{text-align:right;}}
.rlist{{display:flex;flex-direction:column;gap:1px;overflow:hidden;justify-content:flex-start;align-items:stretch;}}
.rrr-item{{border-radius:7px;padding:3px 2px;border:2px solid transparent;cursor:pointer;transition:all .18s ease;margin:0;}}
.rrr-item:hover,.rrr-item.active{{background:#eef5fc!important;border-color:#3a7bd5!important;box-shadow:0 2px 8px rgba(58,123,213,.15);}}
.rrr-top{{background:#f6f9fe;}}
.rrr-row{{display:grid;grid-template-columns:20px minmax(0,1fr) 86px 48px;column-gap:6px;align-items:center;}}
.rrr-badge{{min-width:22px;height:22px;border-radius:50%;background:#3a7bd5;color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
.rrr-name{{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12.5px;color:#1f2f46;font-weight:600;}}
.rrr-status{{display:inline-block;padding:2px 6px;border-radius:20px;font-size:10.5px;font-weight:700;min-width:0;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.rrr-val{{font-size:13px;font-weight:700;color:#145fae;text-align:right;white-space:nowrap;}}
@media (max-width: 1280px){{
    .wrapper{{flex-direction:column;gap:14px;}}
    .heat-panel,.rank-panel{{flex:1 1 100%;max-width:100%;}}
    .rank-shell{{height:auto;padding-left:0;}}
    .nsb{{position:static;width:100%;height:28px;flex-direction:row;justify-content:center;gap:8px;padding:0;margin-bottom:6px;}}
    .nsb-track{{width:100%;height:7px;flex:0 0 auto;margin:0;}}
    .nsb-track::after{{left:auto;right:-1px;bottom:50%;transform:translateY(50%);border-top:6px solid transparent;border-bottom:6px solid transparent;border-left:9px solid #2f7fc1;border-right:none;}}
    .heat-card,.rcard{{height:auto;min-height:340px;}}
}}
</style>
</head>
<body>
<div class="wrapper">
  <div class="heat-panel">
        <div class="heat-card">
            <div class="titlebox">
                <div class="t">Tương quan các yếu tố thời tiết với AQI</div>
                <div class="s" id="sub"></div>
            </div>
            <div class="heatmap-wrap">
                <div id="heatmap-div"></div>
            </div>
    </div>
  </div>
  <div class="rank-panel">
        <div class="rank-shell">
            <div class="nsb" aria-label="Thang địa lý Bắc tới Nam">
                <div class="nsb-label">Bắc</div>
                <div class="nsb-track"></div>
                <div class="nsb-label">Nam</div>
            </div>
            <div class="rcard">
                <div class="rtitle" id="rank-title">{rank_title}</div>
                <div class="rsub">AQI càng cao thể hiện mức ô nhiễm không khí cao hơn</div>
                <div class="rhead"><span class="h1">{rank_col_label}</span><span class="h2">Trạng thái</span><span class="h3">AQI</span></div>
                <div class="rlist" id="rlist">{initial_rows}</div>
            </div>
    </div>
  </div>
</div>
<script>
const CORR = {corr_json};
const LABELS = {labels_json};
const INITIAL_KEY = {initial_key_json};
const INITIAL_SUB = {initial_subtitle_json};

// row: 1D array of correlation values (1 per weather feature vs AQI)
function mkData(row){{
  const vals = row.map(v => v === null ? null : v);
    const labelVals = vals.map(v => v === null ? '' : Number(v).toFixed(2));
  return [{{
    type: 'heatmap',
    z: [vals],
        text: [labelVals],
    x: LABELS,
    y: ['AQI'],
                texttemplate: '%{{text}}',
                textfont: {{size: 12, color: '#1f2f46'}},
        colorscale: [
            [0.0, '#2f7fc1'],
            [0.5, '#d6dde8'],
            [1.0, '#d73027']
        ],
        reversescale: false,
    zmin: -1, zmax: 1,
        xgap: 4, ygap: 4,
    hovertemplate: '<b>%{{x}}</b><br>Tương quan với AQI: %{{z:.3f}}<extra></extra>',
        colorbar: {{title: '', thickness: 11, len: 0.82, y: 0.5}}
  }}];
}}
const layout = {{
    height: 176,
    margin: {{t: 6, r: 12, l: 12, b: 56}},
  plot_bgcolor: 'rgba(0,0,0,0)',
  paper_bgcolor: 'rgba(0,0,0,0)',
  xaxis: {{
    showgrid: false, side: 'bottom', automargin: true,
        tickangle: -30, tickfont: {{size: 11.5}}
  }},
  yaxis: {{
        showgrid: false,
        automargin: true,
        showticklabels: false,
        ticks: ''
  }},
    hoverlabel: {{
        bgcolor: 'rgba(255,255,255,0.92)',
        bordercolor: '#9fc4e6',
        font: {{size: 12, color: '#1f3b57'}}
    }},
    font: {{family: 'Inter,Segoe UI,sans-serif', size: 11, color: '#1f2f46'}}
}};
const cfg = {{displayModeBar: false, responsive: true}};

const sub = document.getElementById('sub');
sub.innerHTML = INITIAL_SUB;

const initialRow = CORR[INITIAL_KEY] || CORR['__all__'];
Plotly.newPlot('heatmap-div', mkData(initialRow), layout, cfg);

document.getElementById('rlist').addEventListener('mouseenter', function(e){{
  const item = e.target.closest('.rrr-item');
  if(!item) return;
  document.querySelectorAll('.rrr-item').forEach(el => el.classList.remove('active'));
  item.classList.add('active');
  const key = item.dataset.region;
  const name = item.querySelector('.rrr-name').textContent;
  const r = CORR[key];
  if(r){{
    Plotly.react('heatmap-div', mkData(r), layout, cfg);
    sub.innerHTML = 'Phạm vi: <b>'+name+'</b>. Màu xanh giúp giảm ô nhiễm, màu đỏ làm tăng ô nhiễm.';
  }}
}}, true);

document.getElementById('rlist').addEventListener('mouseleave', function(e){{
  const item = e.target.closest('.rrr-item');
  if(!item) return;
  item.classList.remove('active');
  const r = CORR[INITIAL_KEY] || CORR['__all__'];
  Plotly.react('heatmap-div', mkData(r), layout, cfg);
  sub.innerHTML = INITIAL_SUB;
}}, true);
</script>
</body></html>"""

    _component_slot = st.empty()
    with _component_slot:
        st_components.html(component_html, height=component_height_px, scrolling=False)

    # === BOTTOM SECTION: Wind/rain chart + province ranking ===
    st.markdown("<br>", unsafe_allow_html=True)

    col_table, col_chart = st.columns([3, 7], gap="medium")

    with col_chart:
        title_col, ctrl_weather = st.columns([4.9, 1.1], gap="small")

        with ctrl_weather:
            try:
                sel_raw = st.segmented_control(
                    "Loại biểu đồ",
                    options=["Gió", "Mưa"],
                    default=st.session_state["interaction_weather_chart"],
                    key="interaction_weather_chart_segmented",
                    label_visibility="collapsed",
                )
                weather_chart = (
                    sel_raw
                    if sel_raw is not None
                    else st.session_state["interaction_weather_chart"]
                )
            except AttributeError:
                weather_chart = st.radio(
                    "Loại biểu đồ",
                    ["Gió", "Mưa"],
                    index=(
                        0
                        if st.session_state["interaction_weather_chart"] == "Gió"
                        else 1
                    ),
                    horizontal=True,
                    key="interaction_weather_chart_radio",
                    label_visibility="collapsed",
                )

            if weather_chart != st.session_state["interaction_weather_chart"]:
                st.session_state["interaction_weather_chart"] = weather_chart
                st.rerun()

        with title_col:
            chart_title = (
                "AQI & PM2.5 theo cường độ gió"
                if st.session_state["interaction_weather_chart"] == "Gió"
                else "AQI & PM2.5 theo cường độ mưa"
            )
            st.markdown(
                f"<div class='interaction-chart-title'>{chart_title}</div>",
                unsafe_allow_html=True,
            )

        if st.session_state["interaction_weather_chart"] == "Gió":
            wind_curve = calc_wind_curve(f_df)
            if wind_curve.empty:
                st.info("Không đủ dữ liệu để phân tích theo nhóm gió.")
            else:
                wind_long = wind_curve.melt(
                    id_vars=["wind_group", "n"],
                    value_vars=["aqi", "pm2_5"],
                    var_name="metric",
                    value_name="value",
                )
                wind_long["metric"] = wind_long["metric"].replace(
                    {"aqi": "AQI", "pm2_5": "PM2.5"}
                )
                fig_wind = px.line(
                    wind_long,
                    x="wind_group",
                    y="value",
                    color="metric",
                    markers=True,
                    height=360,
                )
                fig_wind.update_traces(
                    line_shape="spline",
                    line_smoothing=0.8,
                    line=dict(width=3),
                    marker=dict(size=6),
                    hovertemplate="%{y:.2f}<extra></extra>",
                )
                fig_wind.update_layout(
                    **get_base_layout(),
                    yaxis_title="",
                    xaxis_title="",
                    margin={"t": 20, "r": 18, "l": 10, "b": 38},
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(font=dict(size=12)),
                    hoverlabel=dict(
                        bgcolor="rgba(255,255,255,0.92)",
                        bordercolor="#c9d7e6",
                        font=dict(size=14, color="#1f3b57"),
                    ),
                    hovermode="closest",
                )
                fig_wind.update_xaxes(
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False,
                    showspikes=True,
                    spikecolor="#9eb9d4",
                    spikethickness=1,
                    spikedash="dot",
                )
                fig_wind.update_yaxes(
                    showspikes=True, spikecolor="#d1deeb", spikethickness=1
                )
                st.plotly_chart(
                    fig_wind,
                    width="stretch",
                    config={"displayModeBar": False},
                )
                _render_flow_scale("Gió yếu", "Gió mạnh")
        else:
            rain_curve = calc_rain_curve(f_df)
            if rain_curve.empty:
                st.info("Không đủ dữ liệu để phân tích theo nhóm mưa.")
            else:
                rain_long = rain_curve.melt(
                    id_vars=["rain_group", "n"],
                    value_vars=["aqi", "pm2_5"],
                    var_name="metric",
                    value_name="value",
                )
                rain_long["metric"] = rain_long["metric"].replace(
                    {"aqi": "AQI", "pm2_5": "PM2.5"}
                )
                fig_rain = px.line(
                    rain_long,
                    x="rain_group",
                    y="value",
                    color="metric",
                    markers=True,
                    height=360,
                )
                fig_rain.update_traces(
                    line_shape="spline",
                    line_smoothing=0.8,
                    line=dict(width=3),
                    marker=dict(size=6),
                    hovertemplate="%{y:.2f}<extra></extra>",
                )
                fig_rain.update_layout(
                    **get_base_layout(),
                    yaxis_title="",
                    xaxis_title="",
                    margin={"t": 20, "r": 18, "l": 10, "b": 38},
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(font=dict(size=12)),
                    hoverlabel=dict(
                        bgcolor="rgba(255,255,255,0.92)",
                        bordercolor="#c9d7e6",
                        font=dict(size=14, color="#1f3b57"),
                    ),
                    hovermode="closest",
                )
                fig_rain.update_xaxes(
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False,
                    showspikes=True,
                    spikecolor="#9eb9d4",
                    spikethickness=1,
                    spikedash="dot",
                )
                fig_rain.update_yaxes(
                    showspikes=True, spikecolor="#d1deeb", spikethickness=1
                )
                st.plotly_chart(
                    fig_rain,
                    width="stretch",
                    config={"displayModeBar": False},
                )
                _render_flow_scale("Mưa ít", "Mưa nhiều")

    with col_table:
        province_strength = calc_province_cleaning_strength(
            f_df, min_samples=min_samples
        )
        if province_strength.empty:
            st.info("Không đủ mẫu để xếp hạng.")
        else:
            current_weather = st.session_state.get("interaction_weather_chart", "Gió")
            if current_weather == "Gió":
                rank_col = "aqi_wind_pct"
                rank_subtitle = "Top tỉnh có AQI giảm mạnh nhất khi gió tăng"
            else:
                rank_col = "aqi_rain_pct"
                rank_subtitle = "Top tỉnh có AQI giảm mạnh nhất khi có mưa"

            rank_top = (
                province_strength.dropna(subset=[rank_col])
                .sort_values(rank_col, ascending=False)
                .head(5)
                .copy()
            )
            st.markdown(
                _render_rank_table_html(rank_top=rank_top, rank_col=rank_col, subtitle=rank_subtitle),
                unsafe_allow_html=True,
            )
