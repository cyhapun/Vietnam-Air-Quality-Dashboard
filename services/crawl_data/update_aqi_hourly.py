import requests
import pandas as pd
import os
import glob
import numpy as np
import time
from datetime import date, datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures
from tqdm import tqdm

# --- Cấu hình ---
base_dir = os.path.abspath(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(base_dir, "..", "..", "data", "aqi")
BATCH_SIZE = 50  # Giới hạn tối đa của Open-Meteo cho mỗi request

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cấu hình HTTP Session
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10))

def get_file_metadata(file_path):
    """Đọc nhanh thông tin file bằng cách chỉ lấy dòng cuối cùng"""
    try:
        df_tail = pd.read_csv(file_path).tail(1) 
        if df_tail.empty: return None
        
        last_ts = pd.to_datetime(df_tail["timestamp"]).iloc[0]
        
        # Đồng bộ múi giờ Asia/Bangkok
        now_bkk = pd.Timestamp.utcnow().tz_convert("Asia/Bangkok").tz_localize(None)
        current_hour = now_bkk.floor("h")
        
        if last_ts >= current_hour:
            return "UP_TO_DATE"
            
        return {
            "path": file_path,
            "lat": df_tail["lat"].iloc[-1],
            "lon": df_tail["lon"].iloc[-1],
            "last_ts": last_ts,
            "province": df_tail["province"].iloc[-1],
            "location": df_tail["location"].iloc[-1],
            "old_df": pd.read_csv(file_path) # Chỉ đọc full file khi chắc chắn cần update
        }
    except Exception:
        return None

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

def process_batch(batch_meta):
    """Xử lý một nhóm tọa độ"""
    if not batch_meta: return 0, 0
    
    # 1. Chuẩn bị thời gian và tham số Batch
    now_bkk = pd.Timestamp.utcnow().tz_convert("Asia/Bangkok").tz_localize(None)
    current_hour = now_bkk.floor("h")
    # Lùi lại chính xác 3 tháng theo giờ
    cutoff_hour = current_hour - pd.DateOffset(months=3) 
    
    lats = [str(m["lat"]) for m in batch_meta]
    lons = [str(m["lon"]) for m in batch_meta]
    
    min_ts = min([m["last_ts"] for m in batch_meta])
    # Đảm bảo không gọi API lấy dữ liệu cũ hơn 6 tháng (nếu file quá cũ)
    if min_ts < cutoff_hour:
        min_ts = cutoff_hour
        
    start_str = min_ts.strftime("%Y-%m-%d")
    today_str = current_hour.strftime("%Y-%m-%d")
    
    params = {
        "latitude": ",".join(lats),
        "longitude": ",".join(lons),
        "start_date": start_str,
        "end_date": today_str,
        "timezone": "Asia/Bangkok"
    }
    
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    weather_url = "https://archive-api.open-meteo.com/v1/archive"
    
    air_params = {**params, "hourly": "us_aqi,pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"}
    weather_params = {**params, "hourly": "temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover"}

    try:
        r_air = session.get(air_url, params=air_params, timeout=30)
        r_weather = session.get(weather_url, params=weather_params, timeout=30)
        
        if r_air.status_code != 200 or r_weather.status_code != 200:
            return 0, len(batch_meta)

        data_air = r_air.json()
        data_weather = r_weather.json()

        if isinstance(data_air, dict):
            data_air = [data_air]
            data_weather = [data_weather]

        updated_count = 0
        for i, meta in enumerate(batch_meta):
            try:
                # Trích xuất dữ liệu mới
                df_air = pd.DataFrame(data_air[i]["hourly"])
                df_weather = pd.DataFrame(data_weather[i]["hourly"])
                df_new = pd.merge(df_air, df_weather, on="time")

                rename_map = {
                    "time": "timestamp", "temperature_2m": "temp", "relative_humidity_2m": "humidity", 
                    "precipitation": "rain", "wind_speed_10m": "wind_speed", "wind_direction_10m": "wind_dir",
                    "surface_pressure": "pressure", "cloud_cover": "cloud", "carbon_monoxide": "co", 
                    "nitrogen_dioxide": "no2", "sulphur_dioxide": "so2", "ozone": "o3", "us_aqi": "aqi"
                }
                df_new.rename(columns=rename_map, inplace=True)
                
                df_new["province"] = meta["province"]
                df_new["location"] = meta["location"]
                df_new["lat"] = meta["lat"]
                df_new["lon"] = meta["lon"]
                df_new["pollution_level"] = df_new["aqi"].apply(get_pollution_level)
                df_new["pollution_class"] = df_new["aqi"].apply(get_pollution_class)
                
                df_new["timestamp"] = pd.to_datetime(df_new["timestamp"])
                df_new["year"] = df_new["timestamp"].dt.year
                df_new["month"] = df_new["timestamp"].dt.month
                df_new["day"] = df_new["timestamp"].dt.day
                df_new["hour"] = df_new["timestamp"].dt.hour
                
                # Lọc bỏ các giờ trong tương lai (đã có script forecast lo việc này)
                df_new = df_new[df_new["timestamp"] <= current_hour]
                
                # Gộp dữ liệu cũ và mới
                df_final = pd.concat([meta["old_df"], df_new], ignore_index=True)
                df_final["timestamp"] = pd.to_datetime(df_final["timestamp"])
                
                # -------------------------------------------------------------
                # BƯỚC CẮT TỈA: Xóa các bản ghi cũ hơn đúng 6 tháng (tính theo giờ)
                # -------------------------------------------------------------
                df_final = df_final[df_final["timestamp"] >= cutoff_hour]
                
                # Loại bỏ trùng lặp và sắp xếp lại
                df_final.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)
                df_final.sort_values("timestamp", inplace=True)

                # Lưu file
                df_final.to_csv(meta["path"], index=False, encoding="utf-8-sig")
                updated_count += 1
            except Exception as e:
                print(f"❌ Lỗi khi xử lý file {meta['path']}: {e}")
                
        return updated_count, 0

    except Exception as e:
        print(f"🚨 Lỗi kết nối API Batch: {e}")
        return 0, len(batch_meta)

def run_hourly_update():
    print(f"🔍 Đang quét thư mục: {OUTPUT_DIR}")
    csv_files = glob.glob(os.path.join(OUTPUT_DIR, "**", "*.csv"), recursive=True)
    
    all_metadata = []
    skipped = 0
    
    print("📋 Đang kiểm tra trạng thái các file...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(tqdm(executor.map(get_file_metadata, csv_files), total=len(csv_files)))
    
    for res in results:
        if res == "UP_TO_DATE": skipped += 1
        elif res is not None: all_metadata.append(res)
    
    total_need_update = len(all_metadata)
    print(f"📊 Tổng cộng: {len(csv_files)} file | Đã mới: {skipped} | Cần cập nhật: {total_need_update}")

    if total_need_update == 0:
        print("✅ Tất cả dữ liệu đã được cập nhật mới nhất!")
        return

    total_updated = 0
    total_errors = 0
    
    print(f"🚀 Bắt đầu gọi API theo Batch (Size: {BATCH_SIZE})...")
    for i in range(0, total_need_update, BATCH_SIZE):
        batch = all_metadata[i : i + BATCH_SIZE]
        upd, err = process_batch(batch)
        total_updated += upd
        total_errors += err
        print(f"   ➤ Tiến độ: {min(i + BATCH_SIZE, total_need_update)}/{total_need_update} trạm...")
        
        # Thêm độ trễ chống Rate Limit
        time.sleep(1.1)

    print("-" * 50)
    print(f"✅ HOÀN TẤT CẬP NHẬT!")
    print(f"📈 Thành công: {total_updated} file")
    print(f"⏭️ Bỏ qua: {skipped} file")
    print(f"❌ Lỗi: {total_errors} file")
    print("-" * 50)

if __name__ == "__main__":
    start_time = datetime.now()
    run_hourly_update()
    duration = datetime.now() - start_time
    print(f"⏱️ Tổng thời gian thực hiện: {duration}")