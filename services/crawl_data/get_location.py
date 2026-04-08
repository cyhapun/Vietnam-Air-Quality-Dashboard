import requests
import pandas as pd
from io import StringIO
from geopy.geocoders import OpenCage
import time
import re
import os

# Tạo thư mục lưu trữ
save_dir = "../../data/location"
os.makedirs(save_dir, exist_ok=True)

def format_filename(province_name):
    """Giữ nguyên tiếng Việt có dấu cho tên file"""
    return f"{province_name.replace(' ', '_')}.csv"

sources = [
    {"province": "Lâm Đồng", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tra-cuu-ma-xa-phuong-lam-dong-sau-sap-nhap-tu-0172025-chi-tiet-xem-bang-ma-so-don-vi-hanh-chinh-xa--225800.html"},
    {"province": "Đà Nẵng", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tra-cuu-ma-xa-phuong-cua-tp-da-nang-sau-sap-nhap-2025-ra-sao-bang-ma-so-don-vi-hanh-chinh-xa-phuong-330007-228096.html"},
    {"province": "Cao Bằng", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tra-cuu-ma-xa-phuong-cua-cao-bang-sau-sap-nhap-2025-ra-sao-bang-ma-so-don-vi-hanh-chinh-xa-phuong-t-203526-229657.html"},
    {"province": "Quảng Ngãi", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tra-cuu-ma-xa-phuong-quang-ngai-sau-sap-nhap-tu-0172025-chi-tiet-xem-bang-ma-so-don-vi-hanh-chinh-x-224865.html"},
    {"province": "Gia Lai", "url": "https://thuvienphapluat.vn/phap-luat/tra-cuu-ma-so-don-vi-hanh-chinh-135-xa-phuong-tinh-gia-lai-bang-tra-cuu-ma-so-don-vi-hanh-chinh-tin-133660-219453.html"},
    {"province": "Khánh Hòa", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tra-cuu-ma-xa-phuong-dac-khu-tinh-khanh-hoa-sau-sap-nhap-tu-172025-ma-tinh-xa-phuong-dac-khu-tinh-k-226467.html"},
    {"province": "Đắk Lắk", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tra-cuu-ma-xa-phuong-cua-tinh-dak-lak-sau-sap-nhap-2025-bang-ma-so-don-vi-hanh-chinh-xa-phuong-tinh-678665-228383.html"}
]

headers = {'User-Agent': 'Mozilla/5.0'}
geolocator = OpenCage("YOUR_API_KEY") 
prefix_pattern = r'^(?i)(Phường|Xã|Thị trấn|Đặc khu)\s+'
total_saved = 0

print("BẮT ĐẦU TRÍCH XUẤT DỮ LIỆU")

for item in sources:
    province = item["province"]
    print(f"\nĐang xử lý: {province}")
    
    wards_set = set()
    try:
        response = requests.get(item["url"], headers=headers, timeout=15)
        response.encoding = 'utf-8'
        tables = pd.read_html(StringIO(response.text))
        
        for df_table in tables:
            target_col = -1
            
            for idx, col in enumerate(df_table.columns):
                if 'tên đơn vị hành chính' in str(col).lower(): target_col = idx; break
            
            if target_col == -1 and not df_table.empty:
                for idx, val in enumerate(df_table.iloc[0].astype(str).str.lower()):
                    if 'tên đơn vị hành chính' in val: target_col = idx; break

            if target_col != -1:
                for w in df_table.iloc[:, target_col].dropna().tolist():
                    w = str(w).strip()
                    if len(w) > 4 and 'tên đơn vị' not in w.lower(): wards_set.add(w.title())
                break
    except Exception as e:
        print(f"Lỗi quét web: {e}")
        continue

    if not wards_set:
        continue

    results, failed = [], []
    
    for place in sorted(list(wards_set)):
        try:
            loc = geolocator.geocode(f"{place}, {province}, Vietnam", timeout=10)
            if not loc:
                if re.match(prefix_pattern, place):
                    loc = geolocator.geocode(f"{re.sub(prefix_pattern, '', place).strip()}, {province}, Vietnam", timeout=10)
                else:
                    for pfx in ["Xã", "Phường", "Thị trấn"]:
                        loc = geolocator.geocode(f"{pfx} {place}, {province}, Vietnam", timeout=10)
                        if loc: break

            if loc:
                results.append({"Tỉnh/Thành": province, "Tên đơn vị": place, "Vĩ độ": loc.latitude, "Kinh độ": loc.longitude})
            else:
                failed.append(place)
            time.sleep(1) 
        except Exception:
            failed.append(place)
            time.sleep(1.5)

    if results:
        path = os.path.join(save_dir, format_filename(province))
        pd.DataFrame(results).to_csv(path, index=False, encoding="utf-8-sig")
        total_saved += 1
        print(f"Đã lưu {path} ({len(results)} dòng)")
        
    if failed:
        print(f"Thất bại: {', '.join(failed)}")

print(f"\nHOÀN TẤT! Đã tạo {total_saved} file.")