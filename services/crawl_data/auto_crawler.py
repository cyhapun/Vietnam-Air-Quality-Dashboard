import time
from datetime import datetime
import schedule # pip install schedule
from Midterm.services.crawl_data.update_aqi_hourly import run_hourly_update

def job():
    now = datetime.now()
    print(f"\n[{now.strftime('%H:%M:%S')}] 🚀 Bắt đầu chu kỳ quét dữ liệu Hourly...")
    
    # Gọi hàm cập nhật từ file crawler của bạn
    run_hourly_update()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💤 Hoàn tất! Đang ngủ chờ đến chu kỳ tiếp theo...")

def main():
    print("🤖 TRỢ LÝ CRAWL DỮ LIỆU AQI REAL-TIME ĐÃ KHỞI ĐỘNG")
    
    # 1. Khởi động thì chạy ngay lập tức 1 lần cho nóng
    job()
    
    # 2. Lập lịch tự động chạy vào phút thứ 05 của MỖI GIỜ (ví dụ: 14:05, 15:05...)
    # (Tránh chạy đúng 00 để đợi Open-Meteo cập nhật data ổn định)
    schedule.every().hour.at(":01").do(job)
    
    print("\n⏰ Đã cài đặt lịch: Sẽ tự động chạy vào phút thứ 01 của mỗi giờ.")
    
    # 3. Vòng lặp vô tận giữ cho chương trình luôn sống
    while True:
        schedule.run_pending()
        time.sleep(30) # Ngủ 30s rồi kiểm tra lịch 1 lần cho nhẹ CPU

if __name__ == "__main__":
    main()