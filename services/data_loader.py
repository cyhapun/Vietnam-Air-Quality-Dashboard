import glob
import os
import re
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

from utils.helpers import AQI_DEF


PREFERRED_COLUMNS = [
    "timestamp",
    "city",
    "province",
    "location",
    "lat",
    "lon",
    "aqi",
    "temp",
    "humidity",
    "rain",
    "wind_speed",
    "pm2_5",
    "pm10",
    "o3",
    "no2",
    "so2",
    "co",
]

NUMERIC_COLUMNS = [
    "lat",
    "lon",
    "aqi",
    "temp",
    "humidity",
    "rain",
    "wind_speed",
    "pm2_5",
    "pm10",
    "o3",
    "no2",
    "so2",
    "co",
]


def _resolve_first_existing_path(candidates: list[str]) -> str | None:
    for path in candidates:
        norm = os.path.normpath(path)
        if os.path.exists(norm):
            return norm
    return None


def _resolve_all_csv(base_dir: str) -> str | None:
    return _resolve_first_existing_path(
        [
            os.path.join(base_dir, "..", "data", "vietnam_air_quality.csv"),
            os.path.join(base_dir, "data", "vietnam_air_quality.csv"),
            os.path.join(base_dir, "vietnam_air_quality.csv"),
        ]
    )


def _resolve_aqi_dir(base_dir: str) -> str | None:
    return _resolve_first_existing_path(
        [
            os.path.join(base_dir, "..", "data", "aqi"),
            os.path.join(base_dir, "data", "aqi"),
            os.path.join(base_dir, "aqi"),
        ]
    )


def _resolve_location_dir(base_dir: str) -> str | None:
    return _resolve_first_existing_path(
        [
            os.path.join(base_dir, "..", "data", "location"),
            os.path.join(base_dir, "data", "location"),
            os.path.join(base_dir, "location"),
        ]
    )


def _safe_read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, usecols=lambda c: c in PREFERRED_COLUMNS, low_memory=False)


def _normalize_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _build_city_column(df: pd.DataFrame) -> pd.DataFrame:
    if "city" not in df.columns:
        if "province" in df.columns and "location" in df.columns:
            df["city"] = df["province"] + " - " + df["location"]
        elif "province" in df.columns:
            df["city"] = df["province"]
    return df


def _postprocess_df(df: pd.DataFrame) -> pd.DataFrame:
    df = _build_city_column(df)
    if "city" not in df.columns:
        st.error("Thiếu cột 'city' trong dữ liệu đầu vào.")
        st.stop()

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    if "timestamp" not in df.columns:
        st.error("Thiếu cột 'timestamp' trong dữ liệu đầu vào.")
        st.stop()

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df[df["timestamp"].notna()].copy()

    df["date_ts"] = df["timestamp"].dt.normalize()
    df["date"] = df["date_ts"].dt.date
    df["month"] = df["timestamp"].dt.month
    df["hour"] = df["timestamp"].dt.hour
    df["dow"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["dow"] >= 5
    df["is_raining"] = df["rain"] > 0

    aqi_labels = [x[2] for x in AQI_DEF]
    df["aqi_lbl"] = pd.cut(
        df["aqi"],
        bins=[-np.inf, 50, 100, 150, 200, 300, np.inf],
        labels=aqi_labels,
        include_lowest=True,
    ).fillna("Nguy hại")
    df["band"] = df["aqi_lbl"]

    slot_labels = ["Đêm (0–6h)", "Sáng (6–12h)", "Chiều (12–18h)", "Tối (18–24h)"]
    df["time_slot"] = pd.cut(
        df["hour"],
        bins=[-1, 5, 11, 17, 24],
        labels=slot_labels,
    ).fillna(slot_labels[-1])

    df["wind_bin"] = pd.cut(
        df["wind_speed"],
        bins=[0, 5, 10, 20, 200],
        labels=["0–5", "5–10", "10–20", ">20"],
        include_lowest=True,
    )
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def _province_name_slug_map() -> dict[str, str]:
    base = os.path.dirname(__file__)
    location_dir = _resolve_location_dir(base)
    if not location_dir:
        return {}

    mapping: dict[str, str] = {}
    for csv_path in glob.glob(os.path.join(location_dir, "*.csv")):
        slug = os.path.splitext(os.path.basename(csv_path))[0]
        try:
            sample = pd.read_csv(csv_path, nrows=1)
            if not sample.empty and "Tỉnh/Thành" in sample.columns:
                province_name = str(sample.iloc[0]["Tỉnh/Thành"]).strip()
                mapping[province_name] = slug
                mapping[_normalize_name(province_name)] = slug
        except Exception:
            continue
    return mapping


@st.cache_data(ttl=3600, show_spinner=False)
def list_detail_provinces() -> list[str]:
    base = os.path.dirname(__file__)
    location_dir = _resolve_location_dir(base)
    if location_dir:
        names: list[str] = []
        for csv_path in glob.glob(os.path.join(location_dir, "*.csv")):
            try:
                sample = pd.read_csv(csv_path, nrows=1)
                if not sample.empty and "Tỉnh/Thành" in sample.columns:
                    names.append(str(sample.iloc[0]["Tỉnh/Thành"]).strip())
            except Exception:
                continue
        if names:
            return sorted(set(names))

    # Fallback from folder names if location mapping is unavailable.
    aqi_dir = _resolve_aqi_dir(base)
    if not aqi_dir:
        return []
    return sorted(
        {
            os.path.basename(p).replace("_", " ").title()
            for p in glob.glob(os.path.join(aqi_dir, "*"))
            if os.path.isdir(p)
        }
    )


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    base = os.path.dirname(__file__)
    all_csv = _resolve_all_csv(base)
    if all_csv:
        df = _safe_read_csv(all_csv)
        return _postprocess_df(df)

    # Fallback for environments where all.csv is missing.
    data_dir = _resolve_aqi_dir(base)
    if not data_dir:
        st.error("Không tìm thấy nguồn dữ liệu all.csv hoặc thư mục data/aqi")
        st.stop()

    all_files = glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)
    if not all_files:
        st.error(f"Không tìm thấy file CSV nào trong thư mục {data_dir}")
        st.stop()

    df_list = []
    for p in all_files:
        try:
            temp_df = _safe_read_csv(p)
            if not temp_df.empty:
                df_list.append(temp_df)
        except Exception as e:
            print(f"Lỗi đọc file {p}: {e}")

    if not df_list:
        st.error("Không có file CSV nào chứa dữ liệu hợp lệ.")
        st.stop()

    return _postprocess_df(pd.concat(df_list, ignore_index=True))


@st.cache_data(ttl=1800)
def load_province_detail(
    province_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    base = os.path.dirname(__file__)
    aqi_dir = _resolve_aqi_dir(base)
    if not aqi_dir:
        st.error("Không tìm thấy thư mục data/aqi để tải dữ liệu chi tiết tỉnh.")
        st.stop()

    if not province_name or not str(province_name).strip():
        st.error("Tên tỉnh/thành không hợp lệ.")
        st.stop()

    province_name = str(province_name).strip()
    mapping = _province_name_slug_map()
    slug = mapping.get(province_name) or mapping.get(_normalize_name(province_name))
    if not slug:
        st.error(f"Không map được tỉnh/thành '{province_name}' sang thư mục dữ liệu.")
        st.stop()

    province_dir = os.path.join(aqi_dir, slug)
    if not os.path.exists(province_dir):
        st.error(f"Không tìm thấy thư mục dữ liệu chi tiết cho {province_name} ({slug}).")
        st.stop()

    files = glob.glob(os.path.join(province_dir, "*.csv"))
    if not files:
        st.error(f"Không có dữ liệu chi tiết cho {province_name}.")
        st.stop()

    start_ts = pd.to_datetime(start_date, errors="coerce") if start_date else pd.NaT
    end_ts = pd.to_datetime(end_date, errors="coerce") if end_date else pd.NaT
    has_time_filter = pd.notna(start_ts) and pd.notna(end_ts)
    if has_time_filter and end_ts < start_ts:
        start_ts, end_ts = end_ts, start_ts

    df_list = []
    for p in files:
        try:
            temp_df = _safe_read_csv(p)
            if has_time_filter and "timestamp" in temp_df.columns:
                ts = pd.to_datetime(temp_df["timestamp"], errors="coerce")
                end_exclusive = end_ts + pd.Timedelta(days=1)
                temp_df = temp_df[(ts >= start_ts) & (ts < end_exclusive)]
            if not temp_df.empty:
                df_list.append(temp_df)
        except Exception as e:
            print(f"Lỗi đọc file {p}: {e}")

    if not df_list:
        st.error(f"Dữ liệu chi tiết của {province_name} không hợp lệ.")
        st.stop()

    return _postprocess_df(pd.concat(df_list, ignore_index=True))

@st.cache_data(show_spinner=False)
def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")

