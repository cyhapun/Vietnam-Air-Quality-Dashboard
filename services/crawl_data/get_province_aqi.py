import polars as pl
from pathlib import Path
from tqdm import tqdm 

# Cấu hình đường dẫn linh hoạt hơn
BASE_DIR = Path(__file__).resolve().parent.parent.parent # Trỏ về thư mục gốc dự án
ROOT_DIR = BASE_DIR / "data" / "aqi"

# 1. Định nghĩa danh sách cột mục tiêu và kiểu dữ liệu chuẩn
TARGET_SCHEMA = {
    "timestamp": pl.String,
    "year": pl.Int64,
    "month": pl.Int64,
    "day": pl.Int64,
    "hour": pl.Int64,
    "province": pl.String,
    "lat": pl.Float64,
    "lon": pl.Float64,
    "aqi": pl.Float64,
    "pollution_level": pl.String,
    "pollution_class": pl.Float64,
    "temp": pl.Float64,
    "humidity": pl.Float64,
    "rain": pl.Float64,
    "wind_speed": pl.Float64,
    "wind_dir": pl.Float64,
    "pressure": pl.Float64,
    "cloud": pl.Float64,
    "pm2_5": pl.Float64,
    "pm10": pl.Float64,
    "co": pl.Float64,
    "no2": pl.Float64,
    "o3": pl.Float64,
    "so2": pl.Float64
}

def clean_and_format_lf(file_path):
    """Hàm này đảm bảo mọi file CSV trả về đúng 1 schema duy nhất"""
    actual_columns = pl.read_csv(file_path, n_rows=0).columns
    rename_dict = {c: c.strip() for c in actual_columns if c.strip() in TARGET_SCHEMA}
    
    lf = pl.scan_csv(file_path, infer_schema_length=0)
    lf = lf.rename(rename_dict)
    
    # --- Lấy schema một lần duy nhất ---
    current_columns = lf.collect_schema().names() 
    
    # Chỉ chọn các cột có trong TARGET_SCHEMA
    existing_cols = [c for c in TARGET_SCHEMA.keys() if c in current_columns]
    lf = lf.select(existing_cols)
    
    # Ép kiểu và thêm các cột còn thiếu
    expressions = []
    for col_name, dtype in TARGET_SCHEMA.items():
        if col_name in current_columns:
            expressions.append(pl.col(col_name).cast(dtype, strict=False))
        else:
            expressions.append(pl.lit(None).cast(dtype).alias(col_name))
            
    return lf.with_columns(expressions).select(list(TARGET_SCHEMA.keys()))

def run_province_aggregation():
    if not ROOT_DIR.exists():
        print(f"⚠️ Thư mục không tồn tại: {ROOT_DIR}")
        return

    provinces = [d for d in ROOT_DIR.iterdir() if d.is_dir()]
    tqdm.write(f"\nTỔNG HỢP DỮ LIỆU CHO CÁC TỈNH/THÀNH:")

    # Thanh tiến trình chính: Duyệt qua các tỉnh
    for province_path in tqdm(provinces, desc="Tổng hợp dữ liệu", unit="tỉnh"):
        csv_files = [f for f in province_path.glob("*.csv") if f.name != 'all.csv']
        if not csv_files: continue

        lazy_frames = []
        
        # Thanh tiến trình phụ: Duyệt file trong tỉnh (leave=False giúp thanh này tự biến mất khi xong)
        for file in tqdm(csv_files, desc=f"Đang đọc: {province_path.name}", unit="file", leave=False):
            try:
                clean_lf = clean_and_format_lf(file)
                lazy_frames.append(clean_lf)
            except Exception:
                # Bỏ qua in lỗi để không làm vỡ giao diện tqdm
                pass 

        if not lazy_frames: continue

        # Gộp dữ liệu
        combined_df = pl.concat(lazy_frames)

        group_cols = ["timestamp", "year", "month", "day", "hour", "province"]
        mean_cols = ["lat", "lon", "aqi", "temp", "humidity", "rain", "wind_speed", "wind_dir", "pressure", "cloud", "pm2_5", "pm10", "co", "no2", "o3", "so2"]
        mode_cols = ["pollution_level", "pollution_class"]

        result = (
            combined_df
            .group_by(group_cols)
            .agg([
                *[pl.col(c).mean().alias(c) for c in mean_cols],
                *[pl.col(c).mode().first().alias(c) for c in mode_cols]
            ])
            .sort(['year', 'month', 'day', 'hour'])
        )

        # Lưu file
        output_file = province_path / "all.csv"
        result.collect().write_csv(output_file)

if __name__ == "__main__":
    run_province_aggregation()