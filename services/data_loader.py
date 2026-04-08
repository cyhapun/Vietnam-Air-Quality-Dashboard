import os

import numpy as np
import pandas as pd
import streamlit as st

from utils.helpers import AQI_DEF


@st.cache_data
def load_data():
    import glob
    base = os.path.dirname(__file__)
    
    # Xác định thư mục data/aqi (hỗ trợ nhiều cấp độ chạy script)
    data_dir = os.path.join(base, "..", "data", "aqi")
    if not os.path.exists(data_dir):
        data_dir = os.path.join(base, "data", "aqi")
    if not os.path.exists(data_dir):
        data_dir = os.path.join(base, "aqi")
        
    if not os.path.exists(data_dir):
        st.error("Không tìm thấy thư mục 'data/aqi'")
        st.stop()

    # Tìm tất cả các file CSV trong các thư mục con
    all_files = glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)
    
    if not all_files:
        st.error(f"Không tìm thấy file CSV nào trong thư mục {data_dir}")
        st.stop()

    # Đọc và nối tất cả các tiến trình lại với nhau
    df_list = []
    for p in all_files:
        try:
            temp_df = pd.read_csv(p)
            if not temp_df.empty:
                df_list.append(temp_df)
        except Exception as e:
            print(f"Lỗi đọc file {p}: {e}")
            
    if not df_list:
        st.error("Không có file CSV nào chứa dữ liệu hợp lệ.")
        st.stop()
        
    df = pd.concat(df_list, ignore_index=True)
    
    # Tạo cột 'city' để tương thích với các phần còn lại của ứng dụng vốn dùng 'city' thay vì 'province'/'location'
    if "province" in df.columns and "location" in df.columns:
        df["city"] = df["province"] + " - " + df["location"]
    elif "province" in df.columns:
        df["city"] = df["province"]

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

