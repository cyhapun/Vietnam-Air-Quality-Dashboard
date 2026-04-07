import os

import numpy as np
import pandas as pd
import streamlit as st

from utils.helpers import AQI_DEF


@st.cache_data
def load_data():
    base = os.path.dirname(__file__)
    for p in [
        os.path.join(base, "..", "data", "vietnam_air_quality.csv"),
        os.path.join(base, "data", "vietnam_air_quality.csv"),
        os.path.join(base, "vietnam_air_quality.csv"),
    ]:
        if os.path.exists(p):
            df = pd.read_csv(p)
            break
    else:
        st.error("Không tìm thấy file vietnam_air_quality.csv")
        st.stop()

    df["timestamp"]  = pd.to_datetime(df["timestamp"], errors="coerce")
    df["date_ts"]    = df["timestamp"].dt.normalize()
    df["date"]       = df["date_ts"].dt.date
    df["month"]      = df["timestamp"].dt.month
    df["hour"]       = df["timestamp"].dt.hour
    df["dow"]        = df["timestamp"].dt.dayofweek
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

@st.cache_data(show_spinner=False)
def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")

