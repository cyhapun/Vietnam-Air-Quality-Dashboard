# Phân tích Chỉ số Chất lượng Không khí tại Việt Nam

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.55-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-6.6-2C97D1?logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22C55E)

**Môn học:** Trực quan hóa Dữ liệu | **GVHD:** Bùi Tiến Lên
**Khoa:** Công nghệ Thông tin — **Trường:** Đại học Khoa học Tự nhiên, ĐHQG-HCM | **Nhóm 8 · 2026**

---

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

### 1.2 Thành viên nhóm & Phân công

| # | Họ và Tên | MSSV | Phần đảm nhận | Đóng góp |
|:--|:----------|:-----|:--------------|:--------:|
| 1 | *(Thành viên 1)* | — | Tab Tổng quan, Hero UI, KPI cards | 20% |
| 2 | *(Thành viên 2)* | — | Tab AQI, biểu đồ chuỗi thời gian | 20% |
| 3 | *(Thành viên 3)* | — | Tab Thời tiết, tích hợp dữ liệu khí tượng | 20% |
| 4 | *(Thành viên 4)* | — | Tab Tương tác, lọc & so sánh đa chiều | 20% |
| 5 | *(Thành viên 5)* | — | Thu thập dữ liệu (crawler), data loader, styling | 20% |

---

## 2. Giới thiệu Dữ liệu

### 2.1 Nguồn dữ liệu

| Nguồn | Mô tả | Định dạng |
|:------|:------|:----------|
| **IQAir API** | AQI theo giờ tại các trạm quan trắc | JSON → CSV |
| **OpenWeatherMap** | Nhiệt độ, độ ẩm, gió, áp suất | JSON → CSV |
| **Dữ liệu lịch sử 2025** | Chuỗi thời gian AQI năm 2025 tổng hợp | CSV nén |

Dữ liệu được thu thập tự động bằng background crawler chạy mỗi **1 giờ/lần**, lưu trữ tại `data/aqi/<tỉnh>/` theo cấu trúc phân cấp tỉnh → file CSV theo ngày.

### 2.2 Mô tả bộ dữ liệu

- **Phạm vi địa lý:** 34 tỉnh/thành trên cả nước (Hà Nội, TP.HCM, Đà Nẵng, Cần Thơ, Hải Phòng,…)
- **Tần suất:** Theo giờ (hourly) — cập nhật định kỳ
- **Số trường chính:** AQI, PM2.5, PM10, O3, NO2, SO2, CO, nhiệt độ, độ ẩm, tốc độ gió, áp suất
- **Thời gian lưu trữ lịch sử:** Năm 2025 (`data/aqi_year_2025/`)
- **Dự báo:** Dữ liệu dự báo 24h tới (`data/forecast/`)

---

## 3. Phân tích What-Why

### 3.1 Phân tích biến số (Variable Types)

| Biến | Loại | Vai trò |
|:-----|:-----|:--------|
| `timestamp` | Thời gian (datetime) | Trục thời gian chính |
| `city` / `province` | Phân loại (categorical) | Bộ lọc địa lý |
| `aqi` | Định lượng liên tục | Chỉ số tổng hợp chính |
| `pm2_5`, `pm10` | Định lượng liên tục | Chất ô nhiễm dạng hạt |
| `o3`, `no2`, `so2`, `co` | Định lượng liên tục | Chất ô nhiễm khí |
| `temperature`, `humidity` | Định lượng liên tục | Điều kiện khí tượng |
| `wind_speed`, `wind_dir` | Định lượng / Phân loại | Yếu tố khuếch tán ô nhiễm |
| `aqi_label` | Thứ tự (ordinal) | Phân loại mức độ: Tốt → Nguy hiểm |
| `time_slot` | Phân loại có thứ tự | Khung giờ trong ngày |
| `date`, `month`, `season` | Thời gian dẫn xuất | Phân tích theo mùa/tháng |

### 3.2 Câu hỏi phân tích (Tasks)

| # | Câu hỏi | Loại tác vụ |
|:--|:--------|:------------|
| T1 | Chất lượng không khí hiện tại tại Việt Nam đang ở mức nào? | Tóm tắt (Summarize) |
| T2 | Tỉnh/thành nào đang ô nhiễm nhất? | Xếp hạng (Rank) |
| T3 | AQI biến động như thế nào theo thời gian (24h/7 ngày/30 ngày)? | Xu hướng (Trend) |
| T4 | Phân phối PM2.5 theo tỉnh/thành và khung giờ? | Phân phối (Distribution) |
| T5 | Thời tiết ảnh hưởng đến AQI như thế nào? | Tương quan (Correlation) |
| T6 | So sánh AQI giữa các tỉnh/thành theo thời gian? | So sánh (Compare) |
| T7 | Dự báo chất lượng không khí 24h tiếp theo? | Dự báo (Forecast) |
| T8 | Mức độ phơi nhiễm tích lũy theo thời gian tương đương bao nhiêu điếu thuốc? | Tính toán (Derive) |

---

## 4. Thiết kế Dashboard (How)

### 4.1 Bố cục tổng thể

Dashboard chia thành **4 tab** điều hướng qua navigation rail bên trái, kết hợp header cố định chứa logo, thông tin nhóm, nút làm mới dữ liệu và chế độ mù màu.

### 4.2 Tab 1 — Tổng quan (Overview)

**Mục đích:** Cung cấp cái nhìn nhanh về tình trạng chất lượng không khí hiện tại.

| Thành phần | Mark | Channel | Insight |
|:-----------|:-----|:--------|:--------|
| **Hero AQI Card** | Số (Text) | Màu sắc theo dải AQI (xanh→đỏ), kích thước font | Đọc ngay mức AQI tổng thể và phân loại |
| **Bản đồ bong bóng Việt Nam** | Point (bubble) | Vị trí (lat/lon), màu = AQI, kích thước = PM2.5 | Phân bố địa lý ô nhiễm, phát hiện vùng nóng |
| **Trend Grid** | Text + Icon | Màu xanh/đỏ cho delta, icon mũi tên | So sánh biến động AQI và PM2.5 theo chu kỳ |
| **Pollutant Mini Cards** | Card + Bar | Màu border = mức độ, giá trị số | Xem nhanh từng chất ô nhiễm và khuyến nghị |
| **Donut Chart phân phối AQI** | Arc | Màu theo dải AQI, góc = tỷ lệ | Tỷ lệ thời điểm đạt từng mức chất lượng |

**Design Rationale:**
- Hero card đặt ở trên cùng theo nguyên tắc **F-pattern reading** — người dùng nhìn thấy chỉ số quan trọng nhất ngay lập tức.
- Bản đồ dùng **dual encoding** (màu + kích thước) tăng khả năng phân biệt vùng ô nhiễm cao.
- Màu sắc tuân thủ chuẩn AQI quốc tế (Xanh lá → Vàng → Cam → Đỏ → Tím → Nâu).

### 4.3 Tab 2 — AQI

**Mục đích:** Phân tích sâu chỉ số AQI theo chuỗi thời gian và so sánh đa tỉnh.

| Thành phần | Mark | Channel | Insight |
|:-----------|:-----|:--------|:--------|
| **Line chart chuỗi thời gian AQI** | Line | X = thời gian, Y = AQI, màu = tỉnh/thành | Xu hướng AQI, phát hiện đỉnh ô nhiễm theo giờ/ngày |
| **Bar chart xếp hạng tỉnh/thành** | Bar (horizontal) | Độ dài = AQI trung bình, màu = mức độ | Tỉnh nào ô nhiễm nhất trong kỳ chọn |
| **Heatmap AQI theo giờ × ngày** | Rect (heatmap) | X = giờ, Y = ngày, màu = AQI | Khung giờ và ngày ô nhiễm nhất trong tuần |
| **Histogram phân phối AQI** | Bar | X = dải AQI, Y = tần suất | Phân phối tổng thể — lệch phải = thường xuyên ô nhiễm |

**Design Rationale:**
- Line chart đa tỉnh dùng **consistent color palette** riêng biệt cho từng tỉnh để so sánh dễ dàng.
- Heatmap giúp khám phá **pattern theo mùa/thời điểm** mà line chart đơn lẻ không thể hiện tốt.

### 4.4 Tab 3 — Thời tiết (Weather)

**Mục đích:** Phân tích mối quan hệ giữa điều kiện khí tượng và chất lượng không khí.

| Thành phần | Mark | Channel | Insight |
|:-----------|:-----|:--------|:--------|
| **Scatter plot AQI vs. Nhiệt độ/Độ ẩm** | Point | X = biến thời tiết, Y = AQI, màu = mức AQI | Tương quan nhiệt độ/độ ẩm với ô nhiễm |
| **Line chart kép AQI + Thời tiết** | Line (dual axis) | Y trái = AQI, Y phải = nhiệt độ/độ ẩm | So sánh đồng thời biến động khí tượng và AQI |
| **Wind rose chart** | Polar bar | Góc = hướng gió, bán kính = tần suất | Hướng gió chính gây phân tán/tích tụ ô nhiễm |
| **KPI cards thời tiết** | Text + Icon | Màu ngưỡng cảnh báo | Tóm tắt điều kiện thời tiết hiện tại |

**Design Rationale:**
- Dual-axis chart giúp thấy ngay **nghịch tương quan** độ ẩm cao → AQI giảm (mưa rửa không khí).
- Wind rose dùng **polar encoding** phù hợp tự nhiên với bản chất chu kỳ của hướng gió.

### 4.5 Tab 4 — Tương tác (Interaction)

**Mục đích:** Cho phép người dùng tự khám phá dữ liệu theo nhiều chiều.

| Thành phần | Mark | Channel | Insight |
|:-----------|:-----|:--------|:--------|
| **Biểu đồ so sánh đa tỉnh** | Line / Bar grouped | Màu = tỉnh, X = thời gian | So sánh trực tiếp AQI giữa các địa phương |
| **Scatter matrix (PM2.5 × các chất)** | Point | Vị trí, màu | Phát hiện tương quan giữa các chất ô nhiễm |
| **Bộ lọc linh hoạt** | Control (dropdown/slider) | — | Lọc theo tỉnh, thời gian, loại ô nhiễm |
| **Forecast chart** | Line + Area (confidence) | X = thời gian tương lai, vùng bóng = khoảng tin cậy | Dự báo AQI 24h tới |

**Design Rationale:**
- Cho phép người dùng đặt câu hỏi mở → **exploratory analysis** thay vì chỉ cung cấp câu trả lời cố định.
- Forecast area chart dùng **shaded region** để thể hiện mức độ bất định của dự báo.

---

## 5. Thảo luận

### 5.1 Khó khăn gặp phải

- **Dữ liệu không đều:** Một số tỉnh/thành thiếu trạm quan trắc, dẫn đến chuỗi thời gian bị gián đoạn. Xử lý bằng cách suy diễn từ tỉnh lân cận hoặc bỏ qua kỳ thiếu.
- **Hiệu năng với dữ liệu lớn:** Tải 34 tỉnh × 8760 giờ (cả năm 2025) gây chậm. Giải quyết bằng `@st.cache_data`, lưu `.npz` nén và lazy loading theo tab.
- **Đồng bộ crawler ngầm:** Background thread trong Streamlit dễ bị khởi tạo nhiều lần khi app rerun. Xử lý bằng `@st.cache_resource` để đảm bảo chỉ chạy một thread.
- **Responsive layout:** Streamlit có hạn chế về layout tùy chỉnh; cần inject CSS tùy chỉnh để đạt giao diện chuyên nghiệp.

### 5.2 Hạn chế & Hướng phát triển

| Hạn chế | Hướng phát triển |
|:--------|:-----------------|
| Dữ liệu phụ thuộc API thứ 3 | Xây dựng pipeline thu thập từ Cục Môi trường Việt Nam |
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

```
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
│   ├── data_loader.py            # Load & cache dữ liệu từ CSV
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
    ├── aqi/<tỉnh>/               # CSV AQI theo tỉnh (realtime)
    ├── aqi_year_2025/<tỉnh>/     # CSV AQI lịch sử năm 2025
    ├── forecast/                 # Dữ liệu dự báo
    └── location/                 # Tọa độ lat/lon các tỉnh
```

---

## 8. Thư viện phụ thuộc

| Thư viện | Phiên bản | Mục đích |
|:---------|:---------|:---------|
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

**Nhóm 8 · Trực quan hóa Dữ liệu · Khoa CNTT · ĐHKHTN ĐHQG-HCM · 2026**

</div>