import requests
import pandas as pd
from io import StringIO
from geopy.geocoders import OpenCage
import time
import re
import os

print("Khởi tạo hệ thống lấy dữ liệu tổng hợp theo từng Tỉnh/Thành...")

# Các hàm hỗ trợ để xử lý định dạng tên file
def remove_vietnamese_accents(s):
    """Hàm giúp xóa dấu tiếng Việt và ký tự đặc biệt"""
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[Đđ]', 'd', s)
    return s

def format_filename(province_name):
    """Chuyển đổi tên tỉnh thành định dạng tên file csv chuẩn"""
    name = remove_vietnamese_accents(province_name.lower())
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    return f"{name}.csv"

# Kiểm tra và tạo thư mục lưu trữ dữ liệu nếu chưa có
os.makedirs("../../data/location", exist_ok=True)

# Danh sách các nguồn dữ liệu cần thu thập
sources = [
    {"province": "Quảng Trị", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tra-cuu-ma-xa-phuong-quang-tri-sau-sap-nhap-tu-0172025-chi-tiet-xem-bang-ma-don-vi-hanh-chinh-xa-ph-228563.html"},
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}

geolocator = OpenCage("463ebb9169564a7bab4caea9311901d0")
extracted_data_by_province = {}

# Bước đầu tiên Thực hiện quét dữ liệu từ các trang web
print("\nBắt đầu phần 1: Trích xuất thông tin từ website")

for idx, item in enumerate(sources):
    province = item["province"]
    url = item["url"]
    print(f"Đang lấy thông tin phường/xã của tỉnh/thành {province}")
    
    extracted_data_by_province[province] = set()
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        tables = pd.read_html(StringIO(response.text))
        target_keywords = ['tên đơn vị hành chính']
        
        for df_table in tables:
            target_col_idx = -1
            for col_idx, col_name in enumerate(df_table.columns):
                col_str = str(col_name).lower()
                if any(kw in col_str for kw in target_keywords):
                    target_col_idx = col_idx
                    break
            
            if target_col_idx == -1 and not df_table.empty:
                first_row = df_table.iloc[0].astype(str).str.lower()
                for col_idx, cell_val in enumerate(first_row):
                    if any(kw in cell_val for kw in target_keywords):
                        target_col_idx = col_idx
                        break

            if target_col_idx != -1:
                wards_raw = df_table.iloc[:, target_col_idx].dropna().tolist()
                for w in wards_raw:
                    w = str(w).strip()
                    if len(w) > 4 and not any(kw in w.lower() for kw in target_keywords):
                        extracted_data_by_province[province].add(w.title()) 
                break

    except Exception as e:
        print(f"Gặp lỗi khi quét dữ liệu tỉnh {province} chi tiết {e}")

# Bước tiếp theo Tìm tọa độ địa lý và xuất ra file
print("\nBắt đầu phần 2: Tìm kiếm tọa độ và lưu file")

prefix_pattern = r'^(?i)(Phường|Xã|Thị trấn|Đặc khu)\s+'
total_saved_files = 0

for province, wards in extracted_data_by_province.items():
    ward_list = sorted(list(wards))
    if not ward_list:
        print(f"Bỏ qua tỉnh {province} vì không tìm thấy dữ liệu")
        continue
        
    print(f"\nĐang xử lý khu vực {province.upper()} với {len(ward_list)} đơn vị")
    
    # Khởi tạo danh sách kết quả riêng cho từng tỉnh
    province_results = [] 
    failed_wards = []
    
    for place in ward_list:
        try:
            search_query = f"{place}, {province}, Vietnam"
            location = geolocator.geocode(search_query, timeout=10)
            
            if not location:
                has_prefix = re.match(prefix_pattern, place)
                if has_prefix:
                    simple_name = re.sub(prefix_pattern, '', place).strip()
                    location = geolocator.geocode(f"{simple_name}, {province}, Vietnam", timeout=10)
                else:
                    for prefix in ["Xã", "Phường", "Thị trấn"]:
                        location = geolocator.geocode(f"{prefix} {place}, {province}, Vietnam", timeout=10)
                        if location:
                            break

            if location:
                print(f"Tìm thấy '{place}' tại tọa độ ({location.latitude}, {location.longitude})")
                province_results.append({
                    "Tỉnh/Thành": province,
                    "Tên đơn vị": place,
                    "Vĩ độ": location.latitude,
                    "Kinh độ": location.longitude
                })
            else:
                print(f"Không tìm thấy tọa độ cho {place}")
                failed_wards.append(place)
                
            time.sleep(1) 
            
        except Exception as e:
            print(f"Lỗi kết nối khi xử lý {place} chi tiết {e}")
            failed_wards.append(place)
            time.sleep(1.5)

    # Thực hiện lưu kết quả ngay khi xử lý xong mỗi tỉnh
    if province_results:
        df_province = pd.DataFrame(province_results)
        df_province = df_province[['Tỉnh/Thành', 'Tên đơn vị', 'Vĩ độ', 'Kinh độ']]
        
        # Tạo tên file theo quy chuẩn đã định nghĩa
        file_name = format_filename(province)
        file_path = f"../../data/location/{file_name}"
        
        df_province.to_csv(file_path, index=False, encoding="utf-8-sig")
        total_saved_files += 1
        print(f"Đã lưu thành công file {file_path} với {len(province_results)} dòng dữ liệu")
    
    # Liệt kê các đơn vị không tìm được tọa độ
    if failed_wards:
        print(f"Các đơn vị chưa lấy được dữ liệu trong tỉnh này")
        for fw in failed_wards:
            print(f"Thiếu thông tin của {fw}")
    print("Hoàn tất xử lý đơn vị hành chính của tỉnh")

print(f"\nQuá trình hoàn tất Đã tạo được {total_saved_files} file trong thư mục data")