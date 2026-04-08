import requests
import pandas as pd
from io import StringIO
from geopy.geocoders import OpenCage
import time
import re
import os # Thêm thư viện os để quản lý thư mục

print("Khởi tạo hệ thống lấy dữ liệu tổng hợp theo từng Tỉnh/Thành...")

# --- HÀM HỖ TRỢ CHUYỂN ĐỔI TÊN FILE ---
def remove_vietnamese_accents(s):
    """Hàm xóa dấu tiếng Việt và chữ Đ"""
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[Đđ]', 'd', s)
    return s

def format_filename(province_name):
    """Chuyển 'Đà Nẵng' thành 'da_nang.csv'"""
    name = remove_vietnamese_accents(province_name.lower())
    name = re.sub(r'[^a-z0-9\s]', '', name) # Xóa các ký tự đặc biệt (dấu phẩy, ngoặc...)
    name = re.sub(r'\s+', '_', name.strip()) # Thay khoảng trắng bằng dấu gạch dưới
    return f"{name}.csv"

# Tạo thư mục data nếu chưa tồn tại
os.makedirs("../data", exist_ok=True)

# 1. KHAI BÁO DANH SÁCH URL
sources = [
    {"province": "Đà Nẵng", "url": "https://thuvienphapluat.vn/phap-luat-nha-dat/danh-sach-cac-xa-phuong-moi-tai-thanh-pho-da-nang-sau-khi-sap-nhap-tinh-bang-gia-dat-tai-thanh-pho--5140.html"},
    {"province": "Quảng Ngãi", "url": "https://thuvienphapluat.vn/phap-luat/danh-sach-96-xa-phuong-tinh-quang-ngai-moi-sau-sap-nhap-the-nao-viec-dat-ten-xa-phuong-sau-sap-nhap-302384-224103.html"},
    {"province": "Gia Lai", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tra-cuu-135-phuong-xa-gia-lai-chinh-thuc-sau-sap-nhap-tu-172025-toan-bo-danh-sach-phuong-xa-moi-gia-224001.html"},
    {"province": "Khánh Hòa", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/danh-sach-65-xa-phuong-dac-khu-moi-cua-tinh-khanh-hoa-tu-172025-sau-sap-nhap-khanh-hoa-ninh-thuan-c-223249.html"},
    {"province": "Lâm Đồng", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/bang-tra-cuu-day-du-124-xa-phuong-moi-tinh-lam-dong-sau-sap-nhap-chi-tiet-day-du-danh-sach-xa-phuon-159611-223978.html"},
    {"province": "Đắk Lắk", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/bang-tra-cuu-day-du-102-xa-phuong-moi-tinh-dak-lak-sau-sap-nhap-chi-tiet-day-du-danh-sach-xa-phuong-223979.html"},
    {"province": "Cao Bằng", "url": "https://thuvienphapluat.vn/ma-so-thue/phap-luat-thue/tra-cuu-ten-goi-moi-cac-xa-phuong-tinh-cao-bang-sau-sap-nhap-dvhc-2025-danh-sach-cac-thue-co-so-thu-254199-207850.html"}
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}


geolocator = OpenCage("a5a903a0c9b04cffb85bdf5492b3a4fd")
extracted_data_by_province = {}

# 2. VÒNG LẶP CÀO DỮ LIỆU TỪ WEB
print("\n" + "="*50)
print("PHẦN 1: TRÍCH XUẤT DỮ LIỆU TỪ WEBSITE")
print("="*50)

for idx, item in enumerate(sources):
    province = item["province"]
    url = item["url"]
    print(f"[{idx + 1}/{len(sources)}] Đang cào dữ liệu: {province}")
    
    extracted_data_by_province[province] = set()
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        tables = pd.read_html(StringIO(response.text))
        target_keywords = ['mới', 'sau sáp nhập', 'đổi tên', 'sau sắp xếp', 'thành lập']
        
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
        print(f"  -> Lỗi khi quét {province}: {e}")

# 3. ĐỐI CHIẾU TỌA ĐỘ VÀ LƯU THEO TỪNG TỈNH
print("\n" + "="*50)
print("PHẦN 2: LẤY TỌA ĐỘ & XUẤT FILE")
print("="*50)

prefix_pattern = r'^(?i)(Phường|Xã|Thị trấn|Đặc khu)\s+'
total_saved_files = 0

for province, wards in extracted_data_by_province.items():
    ward_list = sorted(list(wards))
    if not ward_list:
        print(f"\n[⏩ BỎ QUA] {province}: Không lấy được dữ liệu từ web.")
        continue
        
    print(f"\n📍 ĐANG XỬ LÝ: {province.upper()} ({len(ward_list)} đơn vị)")
    
    province_results = [] # Khởi tạo danh sách kết quả riêng cho tỉnh này
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
                print(f"  ✓ {place} -> ({location.latitude}, {location.longitude})")
                province_results.append({
                    "Tỉnh/Thành": province,
                    "Tên đơn vị": place,
                    "Vĩ độ": location.latitude,
                    "Kinh độ": location.longitude
                })
            else:
                print(f"  ✕ Thất bại: {place}")
                failed_wards.append(place)
                
            time.sleep(1) 
            
        except Exception as e:
            print(f"  ! Lỗi mạng/Timeout tại {place}: {e}")
            failed_wards.append(place)
            time.sleep(1.5)

    # 4. LƯU FILE NGAY SAU KHI XỬ LÝ XONG 1 TỈNH
    if province_results:
        df_province = pd.DataFrame(province_results)
        df_province = df_province[['Tỉnh/Thành', 'Tên đơn vị', 'Vĩ độ', 'Kinh độ']]
        
        # Tạo tên file chuẩn
        file_name = format_filename(province)
        file_path = f"../../data/location/{file_name}"
        
        df_province.to_csv(file_path, index=False, encoding="utf-8-sig")
        total_saved_files += 1
        print(f"  💾 ĐÃ LƯU FILE: {file_path} ({len(province_results)} dòng)")
    
    # BÁO CÁO THẤT BẠI
    if failed_wards:
        print(f"  > ⚠️ DANH SÁCH THẤT BẠI ({len(failed_wards)} đơn vị):")
        for fw in failed_wards:
            print(f"      - {fw}")
    print("-" * 40)

print(f"\n✅ HOÀN TẤT TOÀN BỘ! Đã tạo thành công {total_saved_files} file trong thư mục '../data/'.")