# Phân tích Chỉ số Chất lượng Không khí tại Việt Nam

<div align="center">

<img src="https://img.shields.io/badge/PYTHON-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/STREAMLIT-1.55-ff4b4b?style=for-the-badge&logo=streamlit&logoColor=white" />
<img src="https://img.shields.io/badge/PLOTLY-6.6-2c97d1?style=for-the-badge&logo=plotly&logoColor=white" />
<img src="https://img.shields.io/badge/PANDAS-2.3-150458?style=for-the-badge&logo=pandas&logoColor=white" />
<img src="https://img.shields.io/badge/POLARS-1.12-CD792C?style=for-the-badge&logo=polars&logoColor=white" />

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://vietnam-air-quality-dashboard.streamlit.app/)

### Đồ án môn học: Trực quan hóa Dữ liệu
**Giảng viên hướng dẫn:** Bùi Tiến Lên  
**Khoa Công nghệ Thông tin — Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM**  
**Nhóm 8 · Lớp CQ2023/24 · Năm học 2025 - 2026**

---

</div>

## Mục Lục
1. [Giới thiệu & Thành viên](#1-giới-thiệu--thành-viên)
2. [Giới thiệu Dữ liệu](#2-giới-thiệu-dữ-liệu)
3. [Phân tích What-Why](#3-phân-tích-what-why)
4. [Thiết kế Dashboard (How)](#4-thiết-kế-dashboard-how)
5. [Thảo luận](#5-thảo-luận)
6. [Cài đặt & Chạy ứng dụng](#6-cài-đặt--chạy-ứng-dụng)
7. [Cấu trúc thư mục](#7-cấu-trúc-thư-mục)
8. [Thư viện phụ thuộc](#8-thư-viện-phụ-thuộc)

---

## 1. Giới thiệu & Thành viên

### 1.1 Tổng quan
Dashboard tương tác theo dõi và phân tích chất lượng không khí theo thời gian thực tại **34 tỉnh/thành Việt Nam**. Hệ thống thu thập dữ liệu AQI theo giờ, tính toán chỉ số ô nhiễm, dự báo xu hướng và cung cấp khuyến nghị sức khỏe trực tiếp trên giao diện web.

### 1.2 Thành viên nhóm (Nhóm 8)

| MSSV | Họ và Tên | Vai trò | Đóng góp |
|:---:|:---|:---|:---:|
| 23120283 | **Phạm Quốc Khánh** | Thành viên | 100% |
| 23120301 | **Phạm Thành Nam** | Thành viên | 100% |
| 23120318 | **Trương Quang Phát** | Thành viên | 100% |
| 23120329 | **Châu Huỳnh Phúc** | Nhóm trưởng | 100% |
| 23120334 | **Huỳnh Tấn Phước** | Thành viên | 100% |

---

## 2. Giới thiệu Dữ liệu

### 2.1 Nguồn dữ liệu
| Nguồn | Loại dữ liệu | Chi tiết |
|:---|:---|:---|
| **Thư viện Pháp luật** | Hành chính | Danh mục Phường/Xã tại 34 Tỉnh/Thành phố |
| **OpenStreetMap** | Tọa độ | Vĩ độ & Kinh độ chính xác của từng đơn vị |
| **Open-Meteo API** | AQI & Khí tượng | Chỉ số ô nhiễm (AQI, PM2.5...) và Thời tiết (Temp, Rain...) |

*Tất cả dữ liệu được xử lý và lưu trữ dưới định dạng **Parquet** để tối ưu hiệu năng.*

### 2.2 Phạm vi dữ liệu
Dữ liệu bao phủ diện rộng trên **34 tỉnh/thành phố** tại Việt Nam:
> An Giang, Bắc Ninh, Cà Mau, Cần Thơ, Cao Bằng, Đà Nẵng, Đắk Lắk, Điện Biên, Đồng Nai, Đồng Tháp, Gia Lai, Hà Nội, Hà Tĩnh, Hải Phòng, Thành phố Hồ Chí Minh, Huế, Hưng Yên, Khánh Hòa, Lai Châu, Lâm Đồng, Lạng Sơn, Lào Cai, Nghệ An, Ninh Bình, Phú Thọ, Quảng Ngãi, Quảng Ninh, Quảng Trị, Sơn La, Tây Ninh, Thái Nguyên, Thanh Hóa, Tuyên Quang, Vĩnh Long.

---

## 3. Phân tích What-Why

### 3.1 Phân tích biến số (Variable Types)

| Biến | Loại | Vai trò |
|:---|:---|:---|
| **timestamp** | Thời gian (datetime) | Trục thời gian chính |
| **city / province** | Phân loại (categorical) | Bộ lọc địa lý |
| **aqi** | Định lượng liên tục | Chỉ số tổng hợp chính |
| **pm2_5, pm10** | Định lượng liên tục | Chất ô nhiễm dạng hạt |
| **o3, no2, so2, co** | Định lượng liên tục | Chất ô nhiễm khí |
| **temperature, humidity** | Định lượng liên tục | Điều kiện khí tượng |
| **wind_speed, wind_dir** | Định lượng / Phân loại | Yếu tố khuếch tán ô nhiễm |
| **aqi_label** | Thứ tự (ordinal) | Phân loại mức độ: Tốt → Nguy hiểm |
| **time_slot** | Phân loại có thứ tự | Khung giờ trong ngày |
| **date, month, season** | Thời gian dẫn xuất | Phân tích theo mùa/tháng |

### 3.2 Câu hỏi phân tích (Tasks)
- **T1**: Bức tranh phân hóa chất lượng không khí giữa các vùng miền hiện nay như thế nào?
- **T2**: Tỉnh/thành nào đang ô nhiễm nhất/trong lành nhất trong 24h qua?
- **T3**: Chất lượng không khí có diễn biến theo chu kỳ mùa vụ hay không?
- **T4**: Bức tranh khí hậu Việt Nam có sự bất thường lớn về lượng mưa, nhiệt độ không?
- **T5**: Lượng mưa và nhiệt độ có phải là tác nhân gây ra những trận mưa xối xả không?
- **T6**: Mức độ ảnh hưởng của địa lý và thời tiết đến AQI khác nhau như thế nào?
- **T7**: Khi tốc độ gió tăng hoặc có mưa, nồng độ PM2.5 và AQI có giảm rõ rệt không?

---

## 4. Thiết kế Dashboard (How)

### 4.1 Bố cục tổng thể
Dashboard chia thành 4 tab điều hướng qua navigation rail bên trái, kết hợp header cố định chứa logo, thông tin nhóm, nút làm mới dữ liệu và chế độ mù màu.

### 4.2 Tab 1 — Tổng quan (Overview)
*Mục đích: Cung cấp cái nhìn nhanh về tình trạng chất lượng không khí hiện tại.*

| Thành phần | Mark | Channel | Insight |
|:---|:---|:---|:---|
| **Hero AQI Card** | Số (Text) | Màu sắc (chuẩn AQI), Kích thước font | Đọc ngay mức AQI tổng thể và phân loại |
| **Bản đồ bong bóng** | Point | Vị trí (lat/lon), Màu (AQI), Size (PM2.5) | Phân bố địa lý ô nhiễm, phát hiện vùng nóng |
| **Trend Grid** | Text + Icon | Màu xanh/đỏ cho delta, Icon mũi tên | So sánh biến động AQI và PM2.5 theo chu kỳ |
| **Pollutant Mini Cards** | Card + Bar | Màu border = mức độ, Giá trị số | Xem nhanh từng chất ô nhiễm và khuyến nghị |
| **Donut Chart** | Arc | Màu theo dải AQI, Góc = Tỷ lệ | Tỷ lệ thời điểm đạt từng mức chất lượng |

**Design Rationale**:
- **F-pattern reading**: Đặt Hero card ở trên cùng để người dùng nhìn thấy chỉ số quan trọng nhất ngay lập tức.
- **Dual encoding**: Sử dụng cả màu sắc và kích thước trên bản đồ để tăng khả năng phân biệt vùng ô nhiễm cao.
- **Color Standard**: Tuân thủ chuẩn mã màu AQI quốc tế (Xanh lá → Nâu).

### 4.3 Tab 2 — AQI (Phân tích chuyên sâu)
*Mục đích: Phân tích sâu chỉ số AQI theo chuỗi thời gian và so sánh đa tỉnh.*

| Thành phần | Mark | Channel | Insight |
|:---|:---|:---|:---|
| **Line chart** | Line | X (Thời gian), Y (AQI), Màu (Tỉnh/Thành) | Xu hướng AQI, phát hiện đỉnh ô nhiễm |
| **Bar chart ranking** | Bar | Độ dài (AQI trung bình), Màu (Mức độ) | Tỉnh nào ô nhiễm nhất trong kỳ chọn |
| **Heatmap** | Rect | X (Giờ), Y (Ngày), Màu (AQI) | Khung giờ và ngày ô nhiễm nhất trong tuần |
| **Histogram** | Bar | X (Dải AQI), Y (Tần suất) | Phân phối tổng thể — lệch phải = thường xuyên ô nhiễm |

**Design Rationale**: Line chart đa tỉnh dùng bảng màu phân biệt để so sánh dễ dàng. Heatmap giúp khám phá pattern theo thời điểm mà line chart đơn lẻ khó thể hiện.

### 4.4 Tab 3 — Thời tiết (Weather)
*Mục đích: Phân tích mối quan hệ giữa điều kiện khí tượng và chất lượng không khí.*

| Thành phần | Mark | Channel | Insight |
|:---|:---|:---|:---|
| **Scatter plot** | Point | X (Biến thời tiết), Y (AQI), Màu (Mức AQI) | Tương quan nhiệt độ/độ ẩm với ô nhiễm |
| **Line chart kép** | Line | Trục Y trái (AQI), Trục Y phải (Weather) | So sánh đồng thời biến động khí tượng và AQI |
| **Wind rose chart** | Polar bar | Góc (Hướng gió), Bán kính (Tần suất) | Hướng gió chính gây phân tán/tích tụ ô nhiễm |
| **KPI cards** | Text + Icon | Màu ngưỡng cảnh báo | Tóm tắt điều kiện thời tiết hiện tại |

**Design Rationale**: Dual-axis chart giúp thấy ngay nghịch tương quan (ví dụ: độ ẩm cao/mưa → AQI giảm). Wind rose dùng polar encoding phù hợp tự nhiên với hướng gió.

### 4.5 Tab 4 — Tương tác (Interaction)
*Mục đích: Cho phép người dùng tự khám phá dữ liệu theo nhiều chiều.*

| Thành phần | Mark | Channel | Insight |
|:---|:---|:---|:---|
| **Biểu đồ so sánh** | Line / Bar | Màu (Tỉnh), X (Thời gian) | So sánh trực tiếp AQI giữa các địa phương |
| **Scatter matrix** | Point | Vị trí, Màu sắc | Phát hiện tương quan chéo giữa các chất ô nhiễm |
| **Bộ lọc (Filters)** | Control | Dropdown, Slider | Lọc linh hoạt theo tỉnh, thời gian, loại ô nhiễm |
| **Forecast chart** | Line + Area | X (Tương lai), Vùng bóng (Confidence) | Dự báo AQI 24h tới kèm khoảng tin cậy |

**Design Rationale**: Cho phép thực hiện **Exploratory Analysis** (khám phá tự do). Forecast area chart dùng vùng bóng mờ để thể hiện mức độ bất định của dự báo.

---

## 5. Thảo luận

### 5.1 Khó khăn gặp phải
- **Dữ liệu không đều**: Một số tỉnh/thành thiếu trạm quan trắc, dẫn đến chuỗi thời gian bị gián đoạn. Nhóm xử lý bằng cách suy diễn từ khu vực lân cận hoặc lọc bỏ các kỳ thiếu thông tin nghiêm trọng.
- **Hiệu năng với dữ liệu lớn**: Việc tải dữ liệu 34 tỉnh với hàng nghìn bản ghi mỗi tỉnh gây độ trễ. Giải quyết bằng cách sử dụng `@st.cache_data`, lưu trữ định dạng **Parquet/NPZ** và áp dụng cơ chế *Lazy Loading* theo từng Tab.
- **Đồng bộ Crawler ngầm**: Background thread trong Streamlit dễ bị khởi tạo lại nhiều lần khi ứng dụng rerun. Nhóm xử lý bằng `@st.cache_resource` để quản lý vòng đời thread crawler duy nhất.
- **Responsive Layout**: Streamlit có hạn chế về layout tùy chỉnh. Nhóm đã thực hiện *Inject CSS* để tinh chỉnh giao diện, đảm bảo tính thẩm mỹ và chuyên nghiệp.

### 5.2 Hạn chế & Hướng phát triển
| Hạn chế | Hướng phát triển |
|:---|:---|
| Dữ liệu phụ thuộc API bên thứ 3 | Xây dựng pipeline thu thập trực tiếp từ Cục Môi trường Việt Nam |
| Mô hình dự báo còn đơn giản | Tích hợp Deep Learning (LSTM/RNN) để tăng độ chính xác dự báo dài hạn |
| Chưa có hệ thống thông báo | Phát triển tính năng gửi cảnh báo AQI qua Email/Telegram khi vượt ngưỡng |

---

## 6. Cài đặt & Chạy ứng dụng

### Yêu cầu
- Python 3.10+
- pip

### Cài đặt
```bash
# 1. Clone repository
git clone https://github.com/cyhapun/Vietnam-Air-Quality-Dashboard.git
cd Vietnam-Air-Quality-Dashboard

# 2. Tạo virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Cài đặt thư viện
pip install -r requirements.txt
```

### Chạy ứng dụng
```bash
# Chế độ xem (không thu thập dữ liệu mới)
streamlit run app.py

# Chế độ thu thập dữ liệu thời gian thực (cập nhật mỗi 1 giờ)
streamlit run app.py -- realtime

# Chỉ cập nhật dữ liệu hiện tại
streamlit run app.py -- current

# Chỉ cập nhật dữ liệu dự báo
streamlit run app.py -- forecast
```

---

## 7. Cấu trúc thư mục
```text
Vietnam-Air-Quality-Dashboard/
│
├── app.py                        # Entry point — layout chính & crawler
├── requirements.txt              # Danh sách thư viện
│
├── components/                   # Các thành phần UI dùng chung
│   ├── header.py                 # Header (logo, tiêu đề, nút làm mới)
│   ├── navigation.py             # Navigation rail (4 tab)
│   ├── sidebar.py                # State management & tab definitions
│   ├── overview.py               # Component tổng quan
│   └── *.svg                     # Icon chất ô nhiễm (PM2.5, PM10, O3…)
│
├── tabs/                         # Nội dung từng tab
│   ├── overview_tab.py           # Tab Tổng quan
│   ├── aqi_tab.py                # Tab AQI phân tích
│   ├── weather_tab.py            # Tab Thời tiết
│   ├── weather_dashboard.py      # Dashboard thời tiết chi tiết
│   └── interaction_tab.py        # Tab Tương tác
│
├── services/                     # Tầng dữ liệu & thu thập
│   ├── data_loader.py            # Load & cache dữ liệu từ Parquet
│   └── crawl_data/               # Crawler tự động
│       ├── update_aqi_hourly.py  # Cập nhật AQI theo giờ
│       ├── get_province_aqi.py   # Tổng hợp AQI tỉnh/thành
│       └── get_forecast.py       # Lấy dữ liệu dự báo
│
├── utils/                        # Tiện ích chung
│   ├── helpers.py                # Hàm tính AQI, màu sắc, constants
│   ├── css.py                    # Inject CSS tùy chỉnh
│   └── loading.py                # Loading screen animation
│
├── styles/
│   └── main.css                  # Stylesheet chính
│
└── data/                         # Dữ liệu lưu trữ cục bộ
    ├── aqi/<tỉnh>/               # Parquet AQI theo tỉnh (realtime)
    ├── aqi_year_2025/<tỉnh>/     # Parquet AQI lịch sử năm 2025
    ├── forecast/                 # Dữ liệu dự báo
    └── location/                 # Tọa độ lat/lon các tỉnh
```

---

## 8. Thư viện phụ thuộc
| Thư viện | Phiên bản | Mục đích |
|:---|:---:|:---|
| **Polars** | 1.12 | Xử lý dữ liệu hiệu năng cao |
| **PyArrow** | 23.0 | Hỗ trợ định dạng Parquet |
| **Streamlit** | 1.55 | Framework web app |
| **Plotly** | 6.6 | Biểu đồ tương tác |
| **Pandas** | 2.3 | Xử lý dữ liệu bảng |
| **NumPy** | 2.4 | Tính toán số |
| **Scikit-learn** | 1.8 | Mô hình dự báo AQI |
| **BeautifulSoup4** | 4.12 | Thu thập dữ liệu web |
| **Requests** | 2.32 | Gọi API |
| **Statsmodels** | 0.14 | Phân tích thống kê |
| **Seaborn / Matplotlib** | 0.13 / 3.10 | Biểu đồ bổ sung |

---

<div align="center">
  <p><b>Nhóm 8 · 2026 · Đồ án môn học Trực quan hóa Dữ liệu</b></p>
  <p><i>Trường Đại học Khoa học Tự nhiên - ĐHQG TP.HCM</i></p>
  <br/>
  <p><b>Trải nghiệm ứng dụng tại:</b> <a href="https://vietnam-air-quality-dashboard.streamlit.app/">https://vietnam-air-quality-dashboard.streamlit.app/</a></p>
</div>