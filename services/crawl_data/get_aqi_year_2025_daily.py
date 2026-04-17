import requests
import pandas as pd
import time
import os
import glob
import numpy as np
import re
import argparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# Cố định dải thời gian: Toàn bộ năm 2025
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"

LOCATION_DIR = "./data/location"
OUTPUT_DIR = "./data/aqi_daily_2025"
BATCH_SIZE = 20

session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504]
)
session.mount("http://", HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10))
session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10))

# Time Skeleton - Theo ngày
full_time_range = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
FULL_TIME_STRINGS = full_time_range.strftime("%Y-%m-%d").tolist()

def get_pollution_level(aqi):
    if pd.isna(aqi): return "Unknown"
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Moderate"
    elif aqi <= 150: return "Unhealthy for Sensitive Groups"
    elif aqi <= 200: return "Unhealthy"
    elif aqi <= 300: return "Very Unhealthy"
    else: return "Hazardous"

def get_pollution_class(aqi):
    if pd.isna(aqi): return np.nan
    if aqi <= 50: return 0
    elif aqi <= 100: return 1
    elif aqi <= 150: return 2
    elif aqi <= 200: return 3
    elif aqi <= 300: return 4
    else: return 5

def clean_filename(s):
    s = str(s)
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[Đđ]', 'd', s)
    s = re.sub(r'[^a-zA-Z0-9\s_]', '', s).strip().lower()
    return re.sub(r'\s+', '_', s)

def process_and_save_batch(batch_targets):
    if not batch_targets: return
    
    lats = [t["lat"] for t in batch_targets]
    lons = [t["lon"] for t in batch_targets]

    # Cập nhật tham số API sang HOURLY cho Air Quality theo đúng document Open-Meteo
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    air_params = {
        "latitude": ",".join(lats),
        "longitude": ",".join(lons),
        "start_date": START_DATE, 
        "end_date": END_DATE,
        "hourly": "us_aqi,pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
        "timezone": "Asia/Bangkok"
    }
    
    # API Archive của Weather hỗ trợ biến DAILY
    weather_url = "https://archive-api.open-meteo.com/v1/archive"
    weather_params = {
        "latitude": ",".join(lats),
        "longitude": ",".join(lons),
        "start_date": START_DATE, 
        "end_date": END_DATE,
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum,surface_pressure_mean,wind_speed_10m_max,wind_direction_10m_dominant,cloud_cover_mean",
        "timezone": "Asia/Bangkok"
    }

    try:
        r_air = session.get(air_url, params=air_params, timeout=30)
        r_weather = session.get(weather_url, params=weather_params, timeout=30)
        
        if r_air.status_code != 200 or r_weather.status_code != 200:
            tqdm.write(f"🚨 Lỗi API (Air: {r_air.status_code}, Weather: {r_weather.status_code})")
            return

        data_air = r_air.json()
        data_weather = r_weather.json()

        # Handle TH chỉ gọi 1 trạm (Open-Meteo trả về dict thay vì list)
        if isinstance(data_air, dict) and "hourly" in data_air:
            data_air = [data_air]
            data_weather = [data_weather]

        df_skeleton = pd.DataFrame({"time": FULL_TIME_STRINGS})

        for i, target in enumerate(batch_targets):
            try:
                # 1. Đọc thẳng dữ liệu Weather vì đã ở định dạng "daily"
                df_weather = pd.DataFrame(data_weather[i]["daily"])
                
                # 2. Xử lý dữ liệu Air Quality từ "hourly" -> "daily"
                df_air_hourly = pd.DataFrame(data_air[i]["hourly"])
                df_air_hourly["time"] = pd.to_datetime(df_air_hourly["time"])
                
                # Tạo cột date (chuỗi YYYY-MM-DD) để groupby
                df_air_hourly["date"] = df_air_hourly["time"].dt.strftime("%Y-%m-%d")
                
                # Group theo ngày và tính trung bình (mean)
                df_air_daily = df_air_hourly.groupby("date").mean(numeric_only=True).reset_index()
                df_air_daily.rename(columns={"date": "time"}, inplace=True)
                
                # 3. Merge hai bộ dữ liệu daily
                df_merged = pd.merge(df_air_daily, df_weather, on="time", how="inner")
                df_final = pd.merge(df_skeleton, df_merged, on="time", how="left")
                
                df_final["province"] = target["province"]
                df_final["location"] = target["location"]
                df_final["lat"] = float(target["lat"])
                df_final["lon"] = float(target["lon"])

                if "us_aqi" not in df_final.columns:
                    df_final["us_aqi"] = np.nan
                    
                df_final["pollution_level"] = df_final["us_aqi"].apply(get_pollution_level)
                df_final["pollution_class"] = df_final["us_aqi"].apply(get_pollution_class)
                
                # Cập nhật tên từ điển rename do Air Quality không còn chữ _mean ở đuôi
                rename = {
                    "time": "timestamp", 
                    "temperature_2m_mean": "temp", 
                    "relative_humidity_2m_mean": "humidity", 
                    "precipitation_sum": "rain", 
                    "wind_speed_10m_max": "wind_speed", 
                    "wind_direction_10m_dominant": "wind_dir",
                    "surface_pressure_mean": "pressure", 
                    "cloud_cover_mean": "cloud", 
                    "carbon_monoxide": "co", 
                    "nitrogen_dioxide": "no2", 
                    "sulphur_dioxide": "so2", 
                    "ozone": "o3", 
                    "us_aqi": "aqi",
                    "pm2_5": "pm2_5",
                    "pm10": "pm10"
                }
                df_final.rename(columns=rename, inplace=True)
                
                # Trích xuất thời gian
                df_final["timestamp"] = pd.to_datetime(df_final["timestamp"])
                df_final["year"] = df_final["timestamp"].dt.year
                df_final["month"] = df_final["timestamp"].dt.month
                df_final["day"] = df_final["timestamp"].dt.day
                
                cols = [
                    "timestamp", "year", "month", "day", 
                    "province", "location", "lat", "lon", 
                    "aqi", "pollution_level", "pollution_class", 
                    "temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud", 
                    "pm2_5", "pm10", "co", "no2", "o3", "so2"
                ]
                df_final = df_final[[c for c in cols if c in df_final.columns]]
                
                df_final.to_parquet(target["out_file"], index=False)

            except Exception as e:
                tqdm.write(f"❌ Lỗi ghi file cho trạm {target['location']}: {e}")

    except Exception as e:
        tqdm.write(f"🚨 Lỗi gọi API Batch: {e}")

def main():
    parser = argparse.ArgumentParser(description="Script crawl dữ liệu AQI theo ngày cho năm 2025")
    parser.add_argument(
        '--provinces', 
        nargs='*', 
        help="Danh sách tên các file tỉnh/thành cần chạy, không có đuôi .parquet (vd: --provinces ha_noi ho_chi_minh)."
    )
    args = parser.parse_args()

    if not os.path.exists(LOCATION_DIR):
        print(f"Lỗi: Không tìm thấy thư mục '{LOCATION_DIR}'.")
        return
        
    csv_files = glob.glob(os.path.join(LOCATION_DIR, "*.parquet"))
    
    if args.provinces:
        selected_files = [f"{p.lower().replace('.parquet', '')}.parquet" for p in args.provinces]
        csv_files = [f for f in csv_files if os.path.basename(f).lower() in selected_files]
        if not csv_files:
            print(f"Lỗi: Không tìm thấy file dữ liệu nào khớp với danh sách chỉ định: {args.provinces}")
            return
            
    if not csv_files:
        print(f"Lỗi: Không tìm thấy file Parquet nào trong '{LOCATION_DIR}'.")
        return

    print(f"Phát hiện {len(csv_files)} file tỉnh/thành. Bắt đầu lấy dữ liệu năm 2025 ...")
    
    for file_path in csv_files:
        folder_name = clean_filename(os.path.splitext(os.path.basename(file_path))[0])
        out_folder = os.path.join(OUTPUT_DIR, folder_name)
        
        try:
            df_locations = pd.read_parquet(file_path)
            total_units = len(df_locations)
            os.makedirs(out_folder, exist_ok=True)
            
            targets_to_fetch = []
            for _, row in df_locations.iterrows():
                unit_name = row["Tên đơn vị"]
                safe_unit_name = clean_filename(unit_name)
                out_file = os.path.join(out_folder, f"{safe_unit_name}.parquet")
                
                if not os.path.exists(out_file):
                    targets_to_fetch.append({
                        "province": row["Tỉnh/Thành"],
                        "location": unit_name,
                        "lat": str(row["Vĩ độ"]),
                        "lon": str(row["Kinh độ"]),
                        "out_file": out_file
                    })

            if not targets_to_fetch:
                print(f"\n[BỎ QUA] '{folder_name}' - Đã hoàn thành ({total_units}/{total_units} file).")
                continue

            print(f"\n[{folder_name}] Đang xử lý {len(targets_to_fetch)} đơn vị hành chính còn thiếu...")
            
            for i in tqdm(range(0, len(targets_to_fetch), BATCH_SIZE), desc="Đang Fetch (Batch)", unit="batch"):
                batch = targets_to_fetch[i : i + BATCH_SIZE]
                process_and_save_batch(batch)
                
                time.sleep(1.5) 
                
        except Exception as e:
            print(f"Lỗi khi đọc hoặc xử lý file {file_path}: {e}")

    print("\n" + "="*50)
    print(f"✅ Hoàn thành toàn bộ quá trình! Dữ liệu được lưu tại thư mục: '{OUTPUT_DIR}'")

if __name__ == "__main__":
    main()