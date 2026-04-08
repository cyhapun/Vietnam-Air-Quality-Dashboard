import requests
import pandas as pd
import time
import os
import numpy as np
from datetime import date, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

START_DATE = "2025-01-01"
END_DATE = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
LOCATION_FILE = "data/raw/vietnam_locations.csv"
OUTPUT_FILE = "data/raw/vietnam_air_quality.csv"

session = requests.Session()
retries = Retry(total=10, backoff_factor=10, status_forcelist=[429, 500, 502, 503, 504])
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

def fetch_data(city_info):
    city_name = city_info["name"]
    lat = city_info["lat"]
    lon = city_info["lon"]
    
    # Empty skeleton dataframe
    df_skeleton = pd.DataFrame({"time": FULL_TIME_STRINGS})
    
    try:
        air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        air_params = {
            "latitude": lat, "longitude": lon,
            "start_date": START_DATE, "end_date": END_DATE,
            "hourly": "us_aqi,pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
            "timezone": "Asia/Bangkok"
        }
        
        # Weather API
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
            
            # Merge API data
            df_merged = pd.merge(df_air, df_weather, on="time", how="inner")
            # Left join with skeleton
            df_final = pd.merge(df_skeleton, df_merged, on="time", how="left")
        else:
            print(f"\nError: API failed for {city_name} (Code: {r_air.status_code}|{r_weather.status_code}) -> Using empty data")
            df_final = df_skeleton

    except Exception as e:
        print(f"\nError: Network issue for {city_name}: {e} -> Using empty data")
        df_final = df_skeleton

    df_final["city"] = city_name
    df_final["lat"] = lat
    df_final["lon"] = lon
    return df_final

def main():
    if not os.path.exists(LOCATION_FILE):
        print(f"Error: File '{LOCATION_FILE}' not found. Please run the coordinate generation step first.")
        return

    locations = pd.read_csv(LOCATION_FILE).to_dict("records")
    all_data = []

    print(f"Starting data crawl for {len(locations)} cities")
    print(f"Time range: {START_DATE} to {END_DATE}")
    
    for city in tqdm(locations, desc="Crawling Data", unit="city"):
        df = fetch_data(city)
        all_data.append(df)
        time.sleep(10.0)

    if all_data:
        print("Processing and merging data...")
        final_df = pd.concat(all_data, ignore_index=True)
        final_df.sort_values(by=["time", "city"], inplace=True)
        
        print("Calculating pollution labels...")
        final_df["pollution_level"] = final_df["us_aqi"].apply(get_pollution_level)
        final_df["pollution_class"] = final_df["us_aqi"].apply(get_pollution_class)
        
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
        final_df.rename(columns=rename, inplace=True)
        
        cols = [
            "timestamp", "city", "lat", "lon", 
            "aqi", "pollution_level", "pollution_class", 
            "temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud", 
            "pm2_5", "pm10", "co", "no2", "o3", "so2"
        ]
        
        final_df = final_df[[c for c in cols if c in final_df.columns]]
        
        final_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print("-" * 40)
        print(f"Done! Data saved to: {OUTPUT_FILE}")
        print(f"Total rows: {len(final_df):,}")
        print(final_df.head())

if __name__ == "__main__":
    main() 