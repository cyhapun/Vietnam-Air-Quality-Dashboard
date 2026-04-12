import os
import glob
import re
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

from utils.helpers import AQI_DEF


def _resolve_aqi_data_dir() -> str:
    base = os.path.dirname(__file__)
    candidates = [
        os.path.join(base, "..", "data", "aqi"),
        os.path.join(base, "data", "aqi"),
        os.path.join(base, "aqi"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    st.error("Không tìm thấy thư mục 'data/aqi'")
    st.stop()


def _normalize_token(value: str) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def _resolve_province_dir(data_dir: str, province: str) -> str | None:
    direct = os.path.join(data_dir, province)
    if os.path.isdir(direct):
        return direct

    province_token = _normalize_token(province)
    if not province_token:
        return None

    for folder in glob.glob(os.path.join(data_dir, "*")):
        if not os.path.isdir(folder):
            continue
        folder_name = os.path.basename(folder)
        if _normalize_token(folder_name) == province_token:
            return folder
    return None


def _prepare_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()

    if "province" not in out.columns:
        out["province"] = "Không rõ tỉnh"
    out["province"] = out["province"].astype(str).str.strip()

    if "location" not in out.columns:
        out["location"] = pd.NA

    location_text = out["location"].fillna("").astype(str).str.strip()
    out["city"] = np.where(
        location_text == "",
        out["province"],
        out["province"] + " - " + location_text,
    )

    out["timestamp"] = pd.to_datetime(out.get("timestamp"), errors="coerce")
    out["date_ts"] = out["timestamp"].dt.normalize()
    out["date"] = out["date_ts"].dt.date
    out["month"] = out["timestamp"].dt.month
    out["hour"] = out["timestamp"].dt.hour
    out["dow"] = out["timestamp"].dt.dayofweek
    out["is_weekend"] = out["dow"] >= 5

    if "rain" not in out.columns:
        out["rain"] = 0
    out["is_raining"] = out["rain"].fillna(0) > 0

    if "aqi" not in out.columns:
        out["aqi"] = np.nan
    aqi_labels = [x[2] for x in AQI_DEF]
    out["aqi_lbl"] = pd.cut(
        out["aqi"],
        bins=[-np.inf, 50, 100, 150, 200, 300, np.inf],
        labels=aqi_labels,
        include_lowest=True,
    ).fillna("Nguy hại")
    out["band"] = out["aqi_lbl"]

    slot_labels = ["Đêm (0–6h)", "Sáng (6–12h)", "Chiều (12–18h)", "Tối (18–24h)"]
    out["time_slot"] = pd.cut(
        out["hour"],
        bins=[-1, 5, 11, 17, 24],
        labels=slot_labels,
    ).fillna(slot_labels[-1])

    if "wind_speed" not in out.columns:
        out["wind_speed"] = np.nan
    out["wind_bin"] = pd.cut(
        out["wind_speed"],
        bins=[0, 5, 10, 20, 200],
        labels=["0–5", "5–10", "10–20", ">20"],
        include_lowest=True,
    )

    return out


def _read_csv_files(paths: list[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        try:
            temp_df = pd.read_csv(p)
            if not temp_df.empty:
                frames.append(temp_df)
        except Exception as e:
            print(f"Lỗi đọc file {p}: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_province_overview_data() -> pd.DataFrame:
    data_dir = _resolve_aqi_data_dir()
    overview_files = glob.glob(os.path.join(data_dir, "*", "all.csv"))

    if not overview_files:
        st.error(f"Không tìm thấy file all.csv trong thư mục {data_dir}")
        st.stop()

    df = _read_csv_files(overview_files)
    if df.empty:
        st.error("Không có dữ liệu tổng quan hợp lệ từ all.csv.")
        st.stop()
    return _prepare_common_columns(df)


@st.cache_data(ttl=3600, show_spinner=False)
def load_province_detail_data(province: str) -> pd.DataFrame:
    if not province:
        return pd.DataFrame()

    data_dir = _resolve_aqi_data_dir()
    province_dir = _resolve_province_dir(data_dir, province)
    if not province_dir:
        return pd.DataFrame()

    detail_files = [
        p
        for p in glob.glob(os.path.join(province_dir, "*.csv"))
        if os.path.basename(p).lower() != "all.csv"
    ]
    if not detail_files:
        return pd.DataFrame()

    df = _read_csv_files(detail_files)
    if df.empty:
        return pd.DataFrame()
    return _prepare_common_columns(df)


def merge_overview_with_loaded_details(
    overview_df: pd.DataFrame,
    loaded_details: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    if not loaded_details:
        return overview_df

    detail_frames = [
        d for d in loaded_details.values() if d is not None and not d.empty
    ]
    if not detail_frames:
        return overview_df

    loaded_provinces = {
        province
        for province, d in loaded_details.items()
        if d is not None and not d.empty
    }
    base_df = overview_df[~overview_df["province"].isin(loaded_provinces)].copy()
    merged_df = pd.concat([base_df, *detail_frames], ignore_index=True, sort=False)
    return merged_df


@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    # Backward-compatible full load used by older code paths.
    data_dir = _resolve_aqi_data_dir()
    all_files = glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)
    if not all_files:
        st.error(f"Không tìm thấy file CSV nào trong thư mục {data_dir}")
        st.stop()

    df = _read_csv_files(all_files)
    if df.empty:
        st.error("Không có file CSV nào chứa dữ liệu hợp lệ.")
        st.stop()
    return _prepare_common_columns(df)


@st.cache_data(show_spinner=False)
def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")
