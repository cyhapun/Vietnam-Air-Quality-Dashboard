import requests
import pandas as pd
import time
import os
import glob
import numpy as np
import unicodedata
import re
import argparse
from datetime import date, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

START_DATE = "2025-01-01"
END_DATE = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
LOCATION_DIR = "../../data/location"
OUTPUT_DIR = "../../data/aqi" 

session = requests.Session()
retries = Retry(
    total=3,                # Chỉ thử lại tối đa 3 lần
    backoff_factor=2,       # Thời gian chờ sẽ là: 2s, 4s, 8s (tối đa chờ 14s cho 1 địa điểm lỗi)
    status_forcelist=[429, 500, 502, 503, 504]
)
session.mount("http://", HTTPAdapter(max_retries=retries))
session.mount("https://", HTTPAdapter(max_retries=retries))

# Time Skeleton
full_time_range = pd.date_range(start=START_DATE, end=END_DATE, freq="h")
FULL_TIME_STRINGS = full_time_range.strftime("%Y-%m-%dT%H:%M").tolist()

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
    """Hàm giúp xóa dấu tiếng Việt và ký tự đặc biệt"""
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[Đđ]', 'd', s)
    return s

def fetch_data(lat, lon, location_name):
    df_skeleton = pd.DataFrame({"time": FULL_TIME_STRINGS})
    try:
        air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        air_params = {
            "latitude": lat, "longitude": lon,
            "start_date": START_DATE, "end_date": END_DATE,
            "hourly": "us_aqi,pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
            "timezone": "Asia/Bangkok"
        }
        weather_url = "https://archive-api.open-meteo.com/v1/archive"
        weather_params = {
            "latitude": lat, "longitude": lon,
            "start_date": START_DATE, "end_date": END_DATE,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover",
            "timezone": "Asia/Bangkok"
        }

        r_air = session.get(air_url, params=air_params, timeout=30)
        r_weather = session.get(weather_url, params=weather_params, timeout=30)
        
        if r_air.status_code == 200 and r_weather.status_code == 200:
            df_air = pd.DataFrame(r_air.json()["hourly"])
            df_weather = pd.DataFrame(r_weather.json()["hourly"])
            
            df_merged = pd.merge(df_air, df_weather, on="time", how="inner")
            df_final = pd.merge(df_skeleton, df_merged, on="time", how="left")
        else:
            print(f"\nError: API failed cho {location_name} (Code: {r_air.status_code}|{r_weather.status_code}) -> Dùng dữ liệu trống")
            df_final = df_skeleton

    except Exception as e:
        print(f"\nError: Lỗi mạng tại {location_name}: {e} -> Dùng dữ liệu trống")
        df_final = df_skeleton

    return df_final

def process_and_save(df_raw, folder_name, province_name, unit_name, lat, lon):
    df = df_raw.copy()
    
    df["province"] = province_name
    df["location"] = unit_name
    df["lat"] = lat
    df["lon"] = lon

    if "us_aqi" not in df.columns:
        df["us_aqi"] = np.nan
        
    df["pollution_level"] = df["us_aqi"].apply(get_pollution_level)
    df["pollution_class"] = df["us_aqi"].apply(get_pollution_class)
    
    rename = {
        "time": "timestamp", 
        "temperature_2m": "temp", 
        "relative_humidity_2m": "humidity", 
        "precipitation": "rain",
        "wind_speed_10m": "wind_speed", 
        "wind_direction_10m": "wind_dir",
        "surface_pressure": "pressure", 
        "cloud_cover": "cloud",
        "carbon_monoxide": "co", 
        "nitrogen_dioxide": "no2", 
        "sulphur_dioxide": "so2",
        "ozone": "o3", 
        "us_aqi": "aqi"
    }
    df.rename(columns=rename, inplace=True)
    
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.month
    df["day"] = df["timestamp"].dt.day
    df["hour"] = df["timestamp"].dt.hour
    
    cols = [
        "timestamp", "year", "month", "day", "hour", 
        "province", "location", "lat", "lon", 
        "aqi", "pollution_level", "pollution_class", 
        "temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud", 
        "pm2_5", "pm10", "co", "no2", "o3", "so2"
    ]
    df = df[[c for c in cols if c in df.columns]]
    
    out_folder = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(out_folder, exist_ok=True)
    
    safe_unit_name = clean_filename(unit_name)
    out_file = os.path.join(out_folder, f"{safe_unit_name}.csv")
    
    df.to_csv(out_file, index=False, encoding="utf-8-sig")

def main():
    parser = argparse.ArgumentParser(description="Script crawl dữ liệu AQI cho các tỉnh/thành")
    parser.add_argument(
        '--provinces', 
        nargs='*', 
        help="Danh sách tên các file tỉnh/thành cần chạy, không có đuôi .csv (vd: --provinces ha_noi ho_chi_minh). Nếu không truyền sẽ chạy tất cả."
    )
    args = parser.parse_args()

    if not os.path.exists(LOCATION_DIR):
        print(f"Lỗi: Không tìm thấy thư mục '{LOCATION_DIR}'.")
        return
        
    csv_files = glob.glob(os.path.join(LOCATION_DIR, "*.csv"))
    
    if args.provinces:
        selected_files = [f"{p.lower().replace('.csv', '')}.csv" for p in args.provinces]
        csv_files = [f for f in csv_files if os.path.basename(f).lower() in selected_files]
        if not csv_files:
            print(f"Lỗi: Không tìm thấy file dữ liệu nào khớp với danh sách chỉ định: {args.provinces}")
            return
            
    if not csv_files:
        print(f"Lỗi: Không tìm thấy file CSV nào trong '{LOCATION_DIR}'.")
        return

    print(f"Phát hiện {len(csv_files)} file tỉnh/thành. Bắt đầu crawl dữ liệu...")
    
    for file_path in csv_files:
        folder_name = clean_filename(os.path.splitext(os.path.basename(file_path))[0])
        out_folder = os.path.join(OUTPUT_DIR, folder_name)
        
        try:
            df_locations = pd.read_csv(file_path)
            total_units = len(df_locations)
            
            # BỎ QUA CẢ TỈNH/THÀNH NẾU ĐÃ ĐỦ SỐ LƯỢNG FILE
            if os.path.exists(out_folder):
                existing_files = glob.glob(os.path.join(out_folder, "*.csv"))
                if len(existing_files) >= total_units:
                    print(f"\n[BỎ QUA] '{folder_name}' - Đã hoàn thành ({len(existing_files)}/{total_units} file).")
                    continue
            else:
                os.makedirs(out_folder, exist_ok=True)

            print(f"\n[{folder_name}] Đang xử lý {total_units} đơn vị hành chính...")
            
            for _, row in tqdm(df_locations.iterrows(), total=total_units, unit="đơn vị"):
                province_name = row["Tỉnh/Thành"]
                unit_name = row["Tên đơn vị"]
                lat = row["Vĩ độ"]
                lon = row["Kinh độ"]
                
                # BỎ QUA XÃ/PHƯỜNG CỤ THỂ NẾU FILE ĐÃ TỒN TẠI (Resume)
                safe_unit_name = clean_filename(unit_name)
                out_file = os.path.join(out_folder, f"{safe_unit_name}.csv")
                
                if os.path.exists(out_file):
                    continue # Bỏ qua vòng lặp này, nhảy sang xã/phường tiếp theo
                
                # Fetch dữ liệu
                df_raw = fetch_data(lat, lon, unit_name)
                process_and_save(df_raw, folder_name, province_name, unit_name, lat, lon)
                
                time.sleep(0.1) 
                
        except Exception as e:
            print(f"Lỗi khi đọc hoặc xử lý file {file_path}: {e}")

    print("\n" + "="*40)
    print(f"Hoàn thành toàn bộ quá trình! Dữ liệu được lưu tại thư mục: '{OUTPUT_DIR}'")

if __name__ == "__main__":
    main()