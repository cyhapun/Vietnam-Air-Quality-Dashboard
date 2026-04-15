import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
from pathlib import Path

# --- CẤU HÌNH ---
DATA_DIR = "./data"
AQI_DIR = os.path.join(DATA_DIR, "aqi")
FORECAST_DIR = os.path.join(DATA_DIR, "forecast")
LOCATION_DIR = os.path.join(DATA_DIR, "location")

# Mốc thời gian kỳ vọng (Hardcoded dựa trên khảo sát thực tế)
HISTORICAL_START = "2026-01-14 20:00:00"
HISTORICAL_END = "2026-04-14 20:00:00"
EXPECTED_ROWS = 2161  # 90 ngày * 24h + 1 (Header)
FORECAST_START_EXPECTED = "2026-04-14 21:00:00"

def get_expected_units():
    """Đọc thư mục location để lấy số lượng đơn vị duy nhất kỳ vọng mỗi tỉnh."""
    expected = {}
    if not os.path.exists(LOCATION_DIR):
        return expected
    
    def clean_slug(s):
        s = str(s)
        import re
        s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
        s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
        s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
        s = re.sub(r'[ìíịỉĩ]', 'i', s)
        s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
        s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
        s = re.sub(r'[Đđ]', 'd', s)
        s = re.sub(r'[^a-zA-Z0-9\s]', '', s).strip().lower()
        return re.sub(r'\s+', '_', s)

    for file in os.listdir(LOCATION_DIR):
        if file.endswith(".csv"):
            province = file.replace(".csv", "")
            try:
                # Đọc với utf-8-sig và lấy số lượng trạm duy nhất sau khi slugify
                df = pd.read_csv(os.path.join(LOCATION_DIR, file), encoding='utf-8-sig')
                unit_col = 'Tên đơn vị' if 'Tên đơn vị' in df.columns else df.columns[1]
                slugs = df[unit_col].apply(clean_slug)
                expected[province] = slugs.nunique()
            except:
                expected[province] = 0
    return expected

def validate():
    print("🔍 BẮT ĐẦU KIỂM TRA DỮ LIỆU TOÀN DIỆN...")
    results = []
    expected_units = get_expected_units()
    all_provinces = sorted(expected_units.keys())
    
    failures = []

    # 1. Kiểm tra đủ 34 tỉnh
    existing_aqi_provinces = set(os.listdir(AQI_DIR)) if os.path.exists(AQI_DIR) else set()
    existing_fc_provinces = set(os.listdir(FORECAST_DIR)) if os.path.exists(FORECAST_DIR) else set()
    
    # Duyệt qua từng tỉnh
    for idx, prov in enumerate(all_provinces, 1):
        prov_data = {
            "stt": idx,
            "province": prov,
            "aqi_units_exp": expected_units[prov],
            "aqi_units_act": 0,
            "fc_units_act": 0,
            "time_range_ok": "✅",
            "missing_data_ok": "✅",
            "continuity_ok": "✅",
            "status": "✅ PASS"
        }
        
        # Check folders exist
        if prov not in existing_aqi_provinces or prov not in existing_fc_provinces:
            prov_data["status"] = "❌ MISSING FOLDER"
            results.append(prov_data)
            continue
            
        aqi_path = os.path.join(AQI_DIR, prov)
        fc_path = os.path.join(FORECAST_DIR, prov)
        
        # Check Unit counts
        aqi_files = [f for f in os.listdir(aqi_path) if f.endswith(".csv") and f != "all.csv"]
        fc_files = [f for f in os.listdir(fc_path) if f.endswith(".csv") and f != "all.csv"]
        prov_data["aqi_units_act"] = len(aqi_files)
        prov_data["fc_units_act"] = len(fc_files)
        
        if prov_data["aqi_units_act"] != prov_data["aqi_units_exp"]:
            prov_data["status"] = "⚠️ UNIT MISMATCH"
            failures.append(f"[{prov}] Unit mismatch: Exp {prov_data['aqi_units_exp']}, Got {prov_data['aqi_units_act']}")

        # Duyệt sâu vào các file để check nội dung (Sample check for performance)
        all_aqi_ok = True
        all_missing_ok = True
        all_continuity_ok = True
        
        # Lấy file all.csv làm đại diện cho range time và continuity
        all_csv_aqi = os.path.join(aqi_path, "all.csv")
        all_csv_fc = os.path.join(fc_path, "all.csv")
        
        if os.path.exists(all_csv_aqi) and os.path.exists(all_csv_fc):
            try:
                df_aqi = pd.read_csv(all_csv_aqi)
                df_fc = pd.read_csv(all_csv_fc)
                
                # Check 3: Range Time AQI
                actual_start = str(df_aqi.iloc[0]['timestamp'])
                actual_end = str(df_aqi.iloc[-1]['timestamp'])
                if actual_start != HISTORICAL_START or actual_end != HISTORICAL_END:
                    all_aqi_ok = False
                    failures.append(f"[{prov}] AQI Range Error: {actual_start} -> {actual_end}")
                
                # Check 5: Continuity
                fc_start = str(df_fc.iloc[0]['timestamp'])
                if fc_start != FORECAST_START_EXPECTED:
                    all_continuity_ok = False
                    failures.append(f"[{prov}] Continuity Error: FC starts at {fc_start}, expected {FORECAST_START_EXPECTED}")
                
                # Check 4: Missing Data (Thực hiện trên all.csv của AQI trước)
                pollutant_cols = ["aqi", "pm2_5", "temp", "humidity", "rain"]
                cols_to_check = [c for c in pollutant_cols if c in df_aqi.columns]
                if df_aqi[cols_to_check].isnull().values.any():
                    all_missing_ok = False
                    failures.append(f"[{prov}] Missing data detected in all.csv")
                    
            except Exception as e:
                prov_data["status"] = "❌ READ ERROR"
                failures.append(f"[{prov}] Error: {e}")

        prov_data["time_range_ok"] = "✅" if all_aqi_ok else "❌"
        prov_data["missing_data_ok"] = "✅" if all_missing_ok else "❌"
        prov_data["continuity_ok"] = "✅" if all_continuity_ok else "❌"
        
        if not (all_aqi_ok and all_missing_ok and all_continuity_ok):
            prov_data["status"] = "❌ FAIL"

        results.append(prov_data)

    # In kết quả dạng bảng
    print("\n" + "="*80)
    print(f"{'STT':<4} | {'Tỉnh/Thành':<15} | {'Exp':<4} | {'AQI':<4} | {'FC':<4} | {'Time':<4} | {'Miss':<4} | {'Cont':<4} | {'Status'}")
    print("-" * 80)
    for r in results:
        print(f"{r['stt']:<4} | {r['province']:<15} | {r['aqi_units_exp']:<4} | {r['aqi_units_act']:<4} | {r['fc_units_act']:<4} | {r['time_range_ok']:<4} | {r['missing_data_ok']:<4} | {r['continuity_ok']:<4} | {r['status']}")
    print("="*80)

    if failures:
        print("\n🚩 CHI TIẾT CÁC LỖI TÌM THẤY:")
        for f in failures[:20]: # Show top 20
            print(f" - {f}")
        if len(failures) > 20:
            print(f" ... và {len(failures)-20} lỗi khác.")
    else:
        print("\n🎉 TUYỆT VỜI! Mọi dữ liệu đều nhất quán và đầy đủ.")

if __name__ == "__main__":
    validate()
