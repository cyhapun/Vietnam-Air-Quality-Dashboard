import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import re
import unicodedata
import html
from utils.helpers import val_meta


GEO_FEATURES = ["lat", "lon"]
WEATHER_FEATURES = ["temp", "humidity", "wind_speed", "rain"]

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
    "Tây Nguyên": ["Gia Lai", "Đắk Lắk", "Lâm Đồng"],
    "Đông Nam Bộ": ["TP. Hồ Chí Minh", "Đồng Nai", "Tây Ninh"],
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
    for region_name, provinces in REGION7_PROVINCES.items():
        for province in provinces:
            out[_normalize_token_interaction(province)] = region_name

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
        out["region_7"] = "Chưa xếp vùng"
        return out

    if "province" not in out.columns:
        out["province"] = out[source_col].astype(str)

    token = out[source_col].astype(str).map(_normalize_token_interaction)
    token = token.map(lambda t: PROVINCE_TOKEN_ALIAS.get(t, t))
    out["region_7"] = token.map(p2r).fillna("Chưa xếp vùng")
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


def _render_rank_table_html(rank_top: pd.DataFrame, rank_col: str) -> str:
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
        "<div class='interaction-rank-sub'>Top tỉnh có mức giảm mạnh theo bộ lọc hiện tại</div>"
        "<div class='interaction-rank-head'><span>Tỉnh</span><span>%</span></div>"
        "<div class='interaction-rank-list'>" + "".join(rows) + "</div>" + "</div>"
    )


def _render_region_aqi_rank_html(
    rank_region: pd.DataFrame,
    name_col: str = "region_7",
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
    for province, g in df.groupby("province"):
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
                "aqi_cleaning_pct",
                "pm2_5_cleaning_pct",
                "overall_cleaning_pct",
                "n_obs",
            ]
        )
    return res.sort_values("overall_cleaning_pct", ascending=False)


@st.cache_data
def calc_region_factor_impact(df, min_samples):
    req_cols = ["region_7", "aqi", *GEO_FEATURES, *WEATHER_FEATURES]
    if any(c not in df.columns for c in req_cols):
        return pd.DataFrame()

    out = []
    for region, g in df.groupby("region_7"):
        if region == "Chưa xếp vùng":
            continue

        for feature in [*GEO_FEATURES, *WEATHER_FEATURES]:
            g_sub = g[["aqi", feature]].dropna()
            if len(g_sub) < min_samples:
                continue
            corr = g_sub["aqi"].corr(g_sub[feature], method="spearman")
            out.append(
                {
                    "region_7": region,
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

    work = _attach_region_interaction(df.copy())
    if not pd.api.types.is_datetime64_any_dtype(work["timestamp"]):
        work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce")
    work = work.dropna(subset=["timestamp"])

    st.markdown(
        '<div class="card" style="padding: 0.85rem 1rem; margin-bottom: 0.35rem;">'
        '<div class="card-title" style="margin-bottom: 4px;"><span class="q-tag">Tương tác</span>Phân tích tác động thời tiết - địa lý đến AQI/PM2.5</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    _inject_interaction_filter_styles()

    available_regions = [
        r for r in REGION7_ORDER if r in work["region_7"].dropna().unique().tolist()
    ]

    if "interaction_region_select" not in st.session_state:
        st.session_state["interaction_region_select"] = "Tất cả"
    if "interaction_province_select" not in st.session_state:
        st.session_state["interaction_province_select"] = "Tất cả"
    if "interaction_time_range" not in st.session_state:
        st.session_state["interaction_time_range"] = "3 tháng"
    if "interaction_rank_focus" not in st.session_state:
        st.session_state["interaction_rank_focus"] = "AQI"

    # Keep a fixed minimum sample threshold after removing the slider from UI.
    min_samples = 60

    region_options = ["Tất cả", *available_regions]
    if st.session_state["interaction_region_select"] not in region_options:
        st.session_state["interaction_region_select"] = "Tất cả"

    selected_region = st.session_state["interaction_region_select"]
    region_scope = (
        work
        if selected_region == "Tất cả"
        else work[work["region_7"] == selected_region]
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
    c1, c2, c3, c_spacer = st.columns([1.4, 0.8, 0.8, 4.0], gap="small")

    with c1:
        selected_region = st.selectbox(
            "Vùng",
            options=region_options,
            key="interaction_region_select",
        )

    region_scope = (
        work
        if selected_region == "Tất cả"
        else work[work["region_7"] == selected_region]
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
        time_options = ["24h", "7 ngày", "30 ngày", "3 tháng"]
        if st.session_state.get("interaction_time_range") not in time_options:
            st.session_state["interaction_time_range"] = "3 tháng"
        time_range = st.selectbox(
            "Thời gian",
            options=time_options,
            key="interaction_time_range",
        )
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
        work["region_7"].isin(
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

    # Q1: Wind / rain cleaning effect (single chart with controls at top-right)
    if "interaction_weather_chart" not in st.session_state:
        st.session_state["interaction_weather_chart"] = "Gió"

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

        rank_focus = st.session_state.get("interaction_rank_focus", "AQI")

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
                    use_container_width=True,
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
                    use_container_width=True,
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
            if rank_focus == "AQI":
                rank_col = "aqi_cleaning_pct"
            else:
                rank_col = "pm2_5_cleaning_pct"

            rank_top = (
                province_strength.sort_values(rank_col, ascending=False).head(5).copy()
            )
            st.markdown(
                _render_rank_table_html(rank_top=rank_top, rank_col=rank_col),
                unsafe_allow_html=True,
            )

    feature_label_map = {
        "temp": "Nhiệt độ",
        "humidity": "Độ ẩm",
        "wind_speed": "Tốc độ gió",
        "rain": "Lượng mưa",
    }
    min_unit_samples = max(15, min_samples // 3)

    if selected_region == "Tất cả":
        compare_col = "region_7"
        compare_label = "Vùng"
        compare_title = "Xếp hạng AQI trung bình giữa các vùng"
        compare_scope = f_df[f_df["region_7"] != "Chưa xếp vùng"].copy()
    else:
        compare_col = "province"
        compare_label = "Tỉnh"
        compare_title = f"Xếp hạng AQI trung bình các tỉnh trong {selected_region}"
        compare_scope = f_df.copy()

    rank_region = (
        compare_scope.groupby(compare_col, as_index=False)
        .agg(aqi_mean=("aqi", "mean"), n_obs=("aqi", "size"))
        .sort_values("aqi_mean", ascending=False)
    )
    if rank_region.empty or rank_region[compare_col].nunique() < 2:
        st.info("Không đủ dữ liệu để so sánh AQI theo phạm vi hiện tại.")
        return

    impact_rows = []
    for unit_name, g in compare_scope.groupby(compare_col):
        for feature_key in feature_label_map.keys():
            sub = g[["aqi", feature_key]].dropna()
            if len(sub) < min_unit_samples:
                continue
            corr = sub["aqi"].corr(sub[feature_key], method="spearman")
            if pd.isna(corr):
                continue
            impact_rows.append(
                {
                    "unit_name": unit_name,
                    "feature": feature_key,
                    "feature_label": feature_label_map[feature_key],
                    "corr": float(corr),
                }
            )

    impact_df = pd.DataFrame(impact_rows)
    if impact_df.empty:
        st.info("Không đủ dữ liệu yếu tố thời tiết để phân tích theo phạm vi hiện tại.")
        return

    ranked_units = rank_region[compare_col].astype(str).tolist()
    rank_idx_map = {name: idx + 1 for idx, name in enumerate(ranked_units)}
    region_display_map = {name: str(rank_idx_map[name]) for name in ranked_units}

    impact_left, impact_right = st.columns([1, 1], gap="medium")

    with impact_left:
        st.markdown(
            """
            <div class='interaction-impact-titlebox'>
                <div class='t'>Tương quan AQI với yếu tố thời tiết theo phạm vi đã chọn</div>
                <div class='s'>Mức độ tương quan: Màu xanh giúp giảm ô nhiễm, màu đỏ làm tăng ô nhiễm.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        feature_order = ["Nhiệt độ", "Độ ẩm", "Tốc độ gió", "Lượng mưa"]
        heat_df = impact_df.pivot_table(
            index="feature_label", columns="unit_name", values="corr", aggfunc="mean"
        )
        heat_df = heat_df.reindex(index=feature_order)
        heat_df = heat_df[[c for c in ranked_units if c in heat_df.columns]]
        heat_df = heat_df.rename(columns=region_display_map)

        fig_heat = px.imshow(
            heat_df,
            aspect="auto",
            zmin=-1,
            zmax=1,
            color_continuous_scale=[
                [0.0, "#2f7fc1"],
                [0.5, "#f4f7fb"],
                [1.0, "#e46a3a"],
            ],
            labels={"x": "", "y": "", "color": "Tương quan"},
            height=380,
        )
        fig_heat.update_traces(
            hovertemplate="Vùng: %{x}<br>Yếu tố: %{y}<br>Tương quan: %{z:.3f}<extra></extra>"
        )
        fig_heat.update_layout(
            **get_base_layout(),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin={"t": 8, "r": 10, "l": 10, "b": 32},
            coloraxis_colorbar=dict(title="Spearman"),
            hoverlabel=dict(
                bgcolor="rgba(255,255,255,0.94)",
                bordercolor="#c9d7e6",
                font=dict(size=12, color="#1f3b57"),
            ),
        )
        fig_heat.update_xaxes(showticklabels=False, side="bottom")
        fig_heat.update_yaxes(showgrid=False)
        st.plotly_chart(
            fig_heat, use_container_width=True, config={"displayModeBar": False}
        )

        ordered_rank_labels = []
        for col in heat_df.columns.astype(str).tolist():
            try:
                ordered_rank_labels.append(int(col))
            except ValueError:
                continue
        ordered_rank_labels = sorted(set(ordered_rank_labels))
        if ordered_rank_labels:
            min_rank = ordered_rank_labels[0]
            max_rank = ordered_rank_labels[-1]
            inner_nums = "".join([f"<span>{n}</span>" for n in ordered_rank_labels])
        else:
            min_rank = 1
            max_rank = 1
            inner_nums = "<span>1</span>"

        st.markdown(
            (
                "<div class='interaction-heat-rank-scale'>"
                f"<span class='interaction-heat-rank-end'>{min_rank}</span>"
                "<div class='interaction-heat-rank-mid'>"
                "<div class='interaction-heat-rank-line'></div>"
                f"<div class='interaction-heat-rank-nums'>{inner_nums}</div>"
                "</div>"
                f"<span class='interaction-heat-rank-end'>{max_rank}</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    with impact_right:
        st.markdown(
            _render_region_aqi_rank_html(
                rank_region,
                name_col=compare_col,
                entity_label=compare_label,
                title=compare_title,
            ),
            unsafe_allow_html=True,
        )

    return
