import requests
import pandas as pd
import os
import glob
import numpy as np
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CẤU HÌNH ĐƯỜNG DẪN ---
base_dir = os.path.abspath(os.path.dirname(__file__))
HISTORICAL_DIR = os.path.join(base_dir, "..", "..", "data", "aqi")
FORECAST_DIR = os.path.join(base_dir, "..", "..", "data", "forecast")

BATCH_SIZE = 50

# Cấu hình Session chống lỗi mạng
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10))

# --- HÀM TIỆN ÍCH ---
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

import re
import unicodedata

def clean_filename(s):
    """Xóa dấu tiếng Việt và ký tự đặc biệt, chuẩn hóa thành slug."""
    s = str(s)
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[Đđ]', 'd', s)
    # Loại bỏ ký tự không phải chữ số hoặc khoảng trắng, thay khoảng trắng bằng gạch dưới
    s = re.sub(r'[^a-zA-Z0-9\s]', '', s).strip().lower()
    return re.sub(r'\s+', '_', s)

def extract_locations_from_history():
    """Quét thư mục historical để lấy danh sách tọa độ và thông tin tỉnh/trạm"""
    csv_files = glob.glob(os.path.join(HISTORICAL_DIR, "**", "*.csv"), recursive=True)
    locations = []
    
    print("📋 Đang lấy danh sách tọa độ từ thư mục data/aqi...")
    for file in csv_files:
        if "all.csv" in os.path.basename(file): continue
        try:
            df = pd.read_csv(file, nrows=1)
            if not df.empty and 'lat' in df.columns:
                locations.append({
                    "province": str(df["province"].iloc[0]),
                    "location": str(df["location"].iloc[0]),
                    "lat": str(df["lat"].iloc[0]),
                    "lon": str(df["lon"].iloc[0])
                })
        except:
            continue
    
    unique_locations = {f"{loc['lat']}_{loc['lon']}": loc for loc in locations}.values()
    return list(unique_locations)

def process_forecast_batch(batch_meta):
    if not batch_meta: return 0, 0
    
    lats = [m["lat"] for m in batch_meta]
    lons = [m["lon"] for m in batch_meta]
    
    params = {
        "latitude": ",".join(lats),
        "longitude": ",".join(lons),
        "timezone": "Asia/Bangkok",
        "forecast_days": 7  
    }
    
    weather_url = "https://api.open-meteo.com/v1/forecast"
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    
    weather_params = {**params, "hourly": "temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover"}
    air_params = {**params, "hourly": "us_aqi,pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"}

    try:
        r_weather = session.get(weather_url, params=weather_params, timeout=30)
        r_air = session.get(air_url, params=air_params, timeout=30)
        
        if r_weather.status_code != 200 or r_air.status_code != 200:
            return 0, len(batch_meta)

        data_weather = r_weather.json()
        data_air = r_air.json()

        if isinstance(data_weather, dict):
            data_weather = [data_weather]
            data_air = [data_air]

        updated_count = 0
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)

        for i, meta in enumerate(batch_meta):
            try:
                # 1. TẠO THƯ MỤC LƯU TRỮ THEO CẤU TRÚC: forecast/tinh_thanh/
                folder_name = clean_filename(meta["province"])
                out_folder = os.path.join(FORECAST_DIR, folder_name)
                os.makedirs(out_folder, exist_ok=True)
                
                # 2. XỬ LÝ DỮ LIỆU
                df_weather = pd.DataFrame(data_weather[i]["hourly"])
                df_air = pd.DataFrame(data_air[i]["hourly"])
                
                # Gộp chung dữ liệu thời tiết và AQI dựa trên cột 'time'
                df_merged = pd.merge(df_air, df_weather, on="time", how="inner")
                
                rename_map = {
                    "time": "timestamp", "temperature_2m": "temp", "relative_humidity_2m": "humidity", 
                    "precipitation": "rain", "wind_speed_10m": "wind_speed", "wind_direction_10m": "wind_dir",
                    "surface_pressure": "pressure", "cloud_cover": "cloud", "carbon_monoxide": "co", 
                    "nitrogen_dioxide": "no2", "sulphur_dioxide": "so2", "ozone": "o3", "us_aqi": "aqi"
                }
                df_merged.rename(columns=rename_map, inplace=True)
                
                # Bổ sung Meta Data
                df_merged["province"] = meta["province"]
                df_merged["location"] = meta["location"]
                df_merged["lat"] = float(meta["lat"])
                df_merged["lon"] = float(meta["lon"])
                
                df_merged["pollution_level"] = df_merged["aqi"].apply(get_pollution_level)
                df_merged["pollution_class"] = df_merged["aqi"].apply(get_pollution_class)

                # Chuyển đổi timestamp và LỌC BỎ QUÁ KHỨ
                df_merged["timestamp"] = pd.to_datetime(df_merged["timestamp"])
                df_merged = df_merged[df_merged["timestamp"] >= current_hour].copy()
                
                # Bổ sung cột thời gian chi tiết
                df_merged["year"] = df_merged["timestamp"].dt.year
                df_merged["month"] = df_merged["timestamp"].dt.month
                df_merged["day"] = df_merged["timestamp"].dt.day
                df_merged["hour"] = df_merged["timestamp"].dt.hour
                
                # Sắp xếp lại cột cho giống dữ liệu historical
                cols = [
                    "timestamp", "year", "month", "day", "hour", 
                    "province", "location", "lat", "lon", 
                    "aqi", "pollution_level", "pollution_class", 
                    "temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud", 
                    "pm2_5", "pm10", "co", "no2", "o3", "so2"
                ]
                df_merged = df_merged[[c for c in cols if c in df_merged.columns]]
                
                # 3. LƯU FILE THEO CẤU TRÚC: phuong_xa.csv
                safe_unit_name = clean_filename(meta["location"])
                out_file = os.path.join(out_folder, f"{safe_unit_name}.csv")

                df_merged.to_csv(out_file, index=False, encoding="utf-8-sig")
                
                updated_count += 1
            except Exception as e:
                print(f"❌ Lỗi ghi file cho trạm {meta['location']}: {e}")
                
        return updated_count, 0

    except Exception as e:
        print(f"🚨 Lỗi gọi API Batch Forecast: {e}")
        return 0, len(batch_meta)

def run_forecast_update():
    print(f"\n🌤️ BẮT ĐẦU CẬP NHẬT DỮ LIỆU DỰ BÁO TỔNG HỢP (FORECAST)...")
    locations = extract_locations_from_history()
    total_locs = len(locations)
    
    if total_locs == 0:
        print("⚠️ Không tìm thấy tọa độ nào từ thư mục dữ liệu cũ. Hãy chạy cào historical trước.")
        return

    print(f"📊 Tìm thấy {total_locs} trạm. Đang tải và gộp dự báo 7 ngày tới...")
    
    total_updated = 0
    total_errors = 0
    
    for i in range(0, total_locs, BATCH_SIZE):
        batch = locations[i : i + BATCH_SIZE]
        upd, err = process_forecast_batch(batch)
        total_updated += upd
        total_errors += err
        print(f"   ➤ Tiến độ: {min(i + BATCH_SIZE, total_locs)}/{total_locs} trạm...")

    print("-" * 50)
    print(f"✅ HOÀN TẤT CẬP NHẬT FORECAST!")
    print(f"📈 Lưu thành công: {total_updated} file (vào thư mục data/forecast/tinh_thanh/)")
    print(f"❌ Lỗi: {total_errors} file")
    print("-" * 50)

if __name__ == "__main__":
    run_forecast_update()