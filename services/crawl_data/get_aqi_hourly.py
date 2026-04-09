import requests
import pandas as pd
import os
import glob
import numpy as np
from datetime import date
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures
from tqdm import tqdm  # Thêm thư viện này để tạo progress bar 1 dòng

# Cấu hình đường dẫn cố định
base_dir = os.path.abspath(os.path.dirname(__file__))

OUTPUT_DIR = os.path.join(base_dir, "..", "..", "data", "aqi")
if not os.path.exists(OUTPUT_DIR):
    raise FileNotFoundError(f"🚨Không thể tìm thấy thư mục: {OUTPUT_DIR}")

# Cấu hình HTTP Session (Tối ưu cho Đa luồng)
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("http://", HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))

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

def fetch_and_merge(file_path, today_str):
    """Trả về trạng thái: 'SKIPPED', 'UPDATED', hoặc 'ERROR'"""
    try:
        from datetime import datetime
        
        df_old = pd.read_csv(file_path)
        if df_old.empty: return "ERROR"

        df_old["timestamp"] = pd.to_datetime(df_old["timestamp"])

        lat = df_old["lat"].iloc[-1]
        lon = df_old["lon"].iloc[-1]
        location_name = df_old["location"].iloc[-1]
        province_name = df_old["province"].iloc[-1]
        
        latest_ts = df_old["timestamp"].max()
        start_date = latest_ts.strftime("%Y-%m-%d")

        now = datetime.now()
        # Chốt chặn thời gian: Cùng ngày và cùng giờ -> Bỏ qua
        if latest_ts.date() == now.date() and latest_ts.hour == now.hour:
            return "SKIPPED"

        # Fetch API
        full_time_range = pd.date_range(start=start_date, end=today_str, freq="h")
        full_time_strings = full_time_range.strftime("%Y-%m-%dT%H:%M").tolist()
        df_skeleton = pd.DataFrame({"time": full_time_strings})

        air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        weather_url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": start_date, "end_date": today_str,
            "timezone": "Asia/Bangkok"
        }
        
        air_params = {**params, "hourly": "us_aqi,pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"}
        weather_params = {**params, "hourly": "temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover"}

        r_air = session.get(air_url, params=air_params, timeout=15)
        r_weather = session.get(weather_url, params=weather_params, timeout=15)
        
        if r_air.status_code == 200 and r_weather.status_code == 200:
            df_air = pd.DataFrame(r_air.json()["hourly"])
            df_weather = pd.DataFrame(r_weather.json()["hourly"])
            df_merged = pd.merge(df_air, df_weather, on="time", how="inner")
            df_new = pd.merge(df_skeleton, df_merged, on="time", how="left")
        else:
            return "ERROR"

        # Tiền xử lý
        df_new["province"] = province_name
        df_new["location"] = location_name
        df_new["lat"] = lat
        df_new["lon"] = lon
        if "us_aqi" not in df_new.columns: df_new["us_aqi"] = np.nan
        df_new["pollution_level"] = df_new["us_aqi"].apply(get_pollution_level)
        df_new["pollution_class"] = df_new["us_aqi"].apply(get_pollution_class)
        
        rename = {
            "time": "timestamp", "temperature_2m": "temp", "relative_humidity_2m": "humidity", 
            "precipitation": "rain", "wind_speed_10m": "wind_speed", "wind_direction_10m": "wind_dir",
            "surface_pressure": "pressure", "cloud_cover": "cloud", "carbon_monoxide": "co", 
            "nitrogen_dioxide": "no2", "sulphur_dioxide": "so2", "ozone": "o3", "us_aqi": "aqi"
        }
        df_new.rename(columns=rename, inplace=True)
        
        df_new["timestamp"] = pd.to_datetime(df_new["timestamp"])
        df_new["year"] = df_new["timestamp"].dt.year
        df_new["month"] = df_new["timestamp"].dt.month
        df_new["day"] = df_new["timestamp"].dt.day
        df_new["hour"] = df_new["timestamp"].dt.hour

        cols = ["timestamp", "year", "month", "day", "hour", "province", "location", "lat", "lon", 
                "aqi", "pollution_level", "pollution_class", "temp", "humidity", "rain", 
                "wind_speed", "wind_dir", "pressure", "cloud", "pm2_5", "pm10", "co", "no2", "o3", "so2"]
        df_new = df_new[[c for c in cols if c in df_new.columns]]

        # Gộp và lưu
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
        df_combined["timestamp"] = pd.to_datetime(df_combined["timestamp"])
        df_combined.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)
        df_combined.sort_values(by="timestamp", inplace=True)

        df_combined.to_csv(file_path, index=False, encoding="utf-8-sig")
        return "UPDATED"

    except Exception as e:
        # Chỉ lưu lại lỗi dạng chuỗi, không in trực tiếp để tránh nát Progress Bar
        return f"ERROR: {e}"

def run_hourly_update():
    """Hàm chạy update ngầm có Tracking Progress cực kỳ gọn nhẹ cho Terminal"""
    if not os.path.exists(OUTPUT_DIR):
        print("🚨 Thư mục data/aqi không tồn tại.")
        return

    csv_files = glob.glob(os.path.join(OUTPUT_DIR, "**", "*.csv"), recursive=True)
    total_files = len(csv_files)
    if total_files == 0: 
        return

    today_str = date.today().strftime("%Y-%m-%d")
    print(f"\n⏳ Bắt đầu quét {total_files} đơn vị hành chính để cập nhật (Đang chạy ngầm)...")
    
    # Biến đếm thống kê
    stats = {"UPDATED": 0, "SKIPPED": 0, "ERROR": 0}
    error_logs = []

    # Chạy đa luồng
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_and_merge, fp, today_str): fp for fp in csv_files}
        
        completed_count = 0
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            completed_count += 1
            
            if res == "UPDATED":
                stats["UPDATED"] += 1
            elif res == "SKIPPED":
                stats["SKIPPED"] += 1
            else:
                stats["ERROR"] += 1
                error_logs.append(res)
            
            # LOG GỌN NHẸ: Chỉ in ra màn hình mỗi khi quét xong 100 file hoặc khi đã xong file cuối cùng
            if completed_count % 100 == 0 or completed_count == total_files:
                print(f"   ➤ Đã quét: {completed_count}/{total_files} file...")

    # Tổng kết gọn gàng trên 1 dòng
    print(f"✅ Hoàn tất quá trình Hourly Update!")
    print(f"📊 Thống kê: [ 🔄 Cập nhật thêm: {stats['UPDATED']} | ⏭️ Đã Up-to-date: {stats['SKIPPED']} | ❌ Lỗi: {stats['ERROR']} ]\n")
    
    # In lỗi nếu có để dễ fix
    if error_logs:
        print(f"⚠️ Chi tiết 3 lỗi đầu tiên: {error_logs[:3]}")
        
if __name__ == "__main__":
    run_hourly_update()