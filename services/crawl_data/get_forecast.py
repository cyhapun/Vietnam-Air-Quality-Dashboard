import requests
import pandas as pd
import polars as pl
import os
import glob
import numpy as np
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import unicodedata
from pathlib import Path
from tqdm import tqdm  
import subprocess


base_dir = os.path.abspath(os.path.dirname(__file__))
HISTORICAL_DIR = os.path.join(base_dir, "..", "..", "data", "aqi")
FORECAST_DIR = os.path.join(base_dir, "..", "..", "data", "forecast")

BATCH_SIZE = 50


session = requests.Session()
retries = Retry(total=5, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10))


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

    s = re.sub(r'[^a-zA-Z0-9\s]', '', s).strip().lower()
    return re.sub(r'\s+', '_', s)

def get_last_historical_timestamp(province, location):

    prov_slug = clean_filename(province)
    loc_slug = clean_filename(location)
    file_path = os.path.join(HISTORICAL_DIR, prov_slug, f"{loc_slug}.parquet")
    
    if os.path.exists(file_path):
        try:

            last_line = subprocess.check_output(['tail', '-n', '1', file_path], stderr=subprocess.DEVNULL).decode('utf-8').strip()
            if last_line:
                last_ts_str = last_line.split(',')[0]
                return pd.to_datetime(last_ts_str)
        except Exception:
            pass
            

    return datetime.now().replace(minute=0, second=0, microsecond=0)

def extract_locations_from_history():

    csv_files = glob.glob(os.path.join(HISTORICAL_DIR, "**", "*.parquet"), recursive=True)
    locations = []
    
    print("Dang lay danh sach toa do tu thu muc data/aqi...")

    for file in tqdm(csv_files, desc="Đang quét file", unit="file"):
        if "all.parquet" in os.path.basename(file): continue
        try:
            df = pd.read_parquet(file).head(1)
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
        "past_days": 2,
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

        for i, meta in enumerate(batch_meta):
            try:

                folder_name = clean_filename(meta["province"])
                out_folder = os.path.join(FORECAST_DIR, folder_name)
                os.makedirs(out_folder, exist_ok=True)
                

                df_weather = pd.DataFrame(data_weather[i]["hourly"])
                df_air = pd.DataFrame(data_air[i]["hourly"])
                

                df_merged = pd.merge(df_air, df_weather, on="time", how="right")
                
                rename_map = {
                    "time": "timestamp", "temperature_2m": "temp", "relative_humidity_2m": "humidity", 
                    "precipitation": "rain", "wind_speed_10m": "wind_speed", "wind_direction_10m": "wind_dir",
                    "surface_pressure": "pressure", "cloud_cover": "cloud", "carbon_monoxide": "co", 
                    "nitrogen_dioxide": "no2", "sulphur_dioxide": "so2", "ozone": "o3", "us_aqi": "aqi"
                }
                df_merged.rename(columns=rename_map, inplace=True)
                

                df_merged["province"] = meta["province"]
                df_merged["location"] = meta["location"]
                df_merged["lat"] = float(meta["lat"])
                df_merged["lon"] = float(meta["lon"])
                


                weather_cols = ["temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud"]
                poll_cols = ["aqi", "pm2_5", "pm10", "co", "no2", "o3", "so2"]
                

                df_merged[weather_cols] = df_merged[weather_cols].interpolate(method='linear', limit_direction='both')
                

                df_merged[poll_cols] = df_merged[poll_cols].interpolate(method='linear', limit_area='inside')
                

                df_merged["pollution_level"] = df_merged["aqi"].apply(get_pollution_level)
                df_merged["pollution_class"] = df_merged["aqi"].apply(get_pollution_class)


                df_merged["timestamp"] = pd.to_datetime(df_merged["timestamp"])
                

                last_ts = get_last_historical_timestamp(meta["province"], meta["location"])
                

                df_merged = df_merged[df_merged["timestamp"] > last_ts].copy()
                

                df_merged["year"] = df_merged["timestamp"].dt.year
                df_merged["month"] = df_merged["timestamp"].dt.month
                df_merged["day"] = df_merged["timestamp"].dt.day
                df_merged["hour"] = df_merged["timestamp"].dt.hour
                

                cols = [
                    "timestamp", "year", "month", "day", "hour", 
                    "province", "location", "lat", "lon", 
                    "aqi", "pollution_level", "pollution_class", 
                    "temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud", 
                    "pm2_5", "pm10", "co", "no2", "o3", "so2"
                ]
                df_merged = df_merged[[c for c in cols if c in df_merged.columns]]
                

                safe_unit_name = clean_filename(meta["location"])
                out_file = os.path.join(out_folder, f"{safe_unit_name}.parquet")

                df_merged.to_parquet(out_file, index=False)
                
                updated_count += 1
            except Exception as e:

                tqdm.write(f"Loi ghi file cho tram {meta['location']}: {e}")
                
        return updated_count, 0

    except Exception as e:
        tqdm.write(f"Loi goi API Batch Forecast: {e}")
        return 0, len(batch_meta)

def calculate_province_all():

    print("\nDang tong hop du lieu (all.csv) cho tung tinh/thanh...")
    
    root_path = Path(FORECAST_DIR)
    if not root_path.exists():
        return

    provinces = [d for d in root_path.iterdir() if d.is_dir()]
    
    for province_path in tqdm(provinces, desc="Tổng hợp All.parquet", unit="tỉnh"):
        csv_files = [f for f in province_path.glob("*.parquet") if f.name != 'all.parquet']
        if not csv_files: continue

        lazy_frames = []
        for file in csv_files:
            try:

                lf = pl.scan_parquet(file)
                lf = lf.with_columns([
                    pl.col("timestamp").cast(pl.String),
                    pl.col("year").cast(pl.Int64),
                    pl.col("month").cast(pl.Int64),
                    pl.col("day").cast(pl.Int64),
                    pl.col("hour").cast(pl.Int64),
                    pl.col("province").cast(pl.String),
                    pl.col("lat").cast(pl.Float64, strict=False),
                    pl.col("lon").cast(pl.Float64, strict=False),
                    pl.col("aqi").cast(pl.Float64, strict=False),
                    pl.col("temp").cast(pl.Float64, strict=False),
                    pl.col("humidity").cast(pl.Float64, strict=False),
                    pl.col("rain").cast(pl.Float64, strict=False),
                    pl.col("wind_speed").cast(pl.Float64, strict=False),
                    pl.col("wind_dir").cast(pl.Float64, strict=False),
                    pl.col("pressure").cast(pl.Float64, strict=False),
                    pl.col("cloud").cast(pl.Float64, strict=False),
                    pl.col("pm2_5").cast(pl.Float64, strict=False),
                    pl.col("pm10").cast(pl.Float64, strict=False),
                    pl.col("co").cast(pl.Float64, strict=False),
                    pl.col("no2").cast(pl.Float64, strict=False),
                    pl.col("o3").cast(pl.Float64, strict=False),
                    pl.col("so2").cast(pl.Float64, strict=False),
                    pl.col("pollution_level").cast(pl.String),
                    pl.col("pollution_class").cast(pl.Float64, strict=False)
                ])
                lazy_frames.append(lf)
            except Exception as e:
                tqdm.write(f"Bo qua file loi {file.name}: {e}")

        if not lazy_frames: continue

        combined_df = pl.concat(lazy_frames)

        group_cols = ["timestamp", "year", "month", "day", "hour", "province"]
        mean_cols = ["lat", "lon", "aqi", "temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud", "pm2_5", "pm10", "co", "no2", "o3", "so2"]


        result = (
            combined_df
            .group_by(group_cols)
            .agg([
                *[pl.col(c).mean().alias(c) for c in mean_cols if c in combined_df.collect_schema().names()],
                *[pl.col(c).mode().first().alias(c) for c in mode_cols if c in combined_df.collect_schema().names()]
            ])
            .sort(['year', 'month', 'day', 'hour'])
        )

        output_file = province_path / "all.parquet"
        result.collect().write_parquet(output_file)

def run_forecast_update():
    print(f"\nBAT DAU CAP NHAT DU LIEU DU BAO TONG HOP (FORECAST)...")
    locations = extract_locations_from_history()
    total_locs = len(locations)
    
    if total_locs == 0:
        print("Khong tim thay toa do nao tu thu muc du lieu cu. Hay chay cao historical truoc.")
        return

    print(f"Tim thay {total_locs} tram. Dang tai va gop du bao 7 ngay toi...")
    
    total_updated = 0
    total_errors = 0
    

    for i in tqdm(range(0, total_locs, BATCH_SIZE), desc="Đang gọi API", unit="batch"):
        batch = locations[i : i + BATCH_SIZE]
        upd, err = process_forecast_batch(batch)
        total_updated += upd
        total_errors += err
        

        time.sleep(4)

    print("-" * 50)
    print(f"HOAN TAT CAP NHAT FORECAST!")
    print(f"📈 Lưu thành công: {total_updated} file (vào thư mục data/forecast/tinh_thanh/)")
    print(f"Loi: {total_errors} file")
    print("-" * 50)
    

    calculate_province_all()
    print("Qua trinh chay hoan tat!")

if __name__ == "__main__":
    run_forecast_update()