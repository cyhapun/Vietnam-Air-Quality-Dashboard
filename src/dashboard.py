import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# ===================== CONFIG & UI TWEAKS =====================
st.set_page_config(layout="wide", page_title="Smart Air Quality EMS 🌍", page_icon="✨")

# Giao diện Glassmorphism (Kính mờ) hiện đại & Tinh tế
st.markdown("""
<style>
    /* Ẩn bớt khoảng trắng thừa */
    .css-18e3th9, .css-1d391kg { padding-top: 1.5rem; }
    
    /* Hiệu ứng thẻ Glassmorphism cho KPI */
    .glass-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 20px;
        padding: 20px 15px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 15px;
        height: 100%;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(128, 128, 128, 0.4);
    }
    .metric-value { font-size: 2.2rem; font-weight: 800; margin: 0; font-family: 'Segoe UI', sans-serif; line-height: 1.2; }
    .metric-label { font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; display: block; font-weight: 600;}
    
    /* Tùy chỉnh Tab của Streamlit cho gọn gàng */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 15px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ===================== HELPER FUNCTIONS =====================
def get_activity_recommendation(aqi):
    if aqi <= 50: return "✅ Tuyệt vời", "✅ Nên mở", "❌ Không cần"
    elif aqi <= 100: return "✅ Bình thường", "✅ Có thể mở", "⚠️ Cân nhắc"
    elif aqi <= 150: return "⚠️ Giảm cường độ", "❌ Đóng cửa", "✅ Đeo khẩu trang"
    else: return "❌ Ở trong nhà", "❌ Đóng kín", "🚨 Đeo khẩu trang N95"

def get_time_of_day(hour):
    if 0 <= hour < 6: return "Đêm (0h-6h)"
    elif 6 <= hour < 12: return "Sáng (6h-12h)"
    elif 12 <= hour < 18: return "Chiều (12h-18h)"
    else: return "Tối (18h-24h)"

def calc_cigarette_eq(pm25_mean, days):
    # Quy tắc Berkeley Earth: 22 µg/m³ PM2.5 / 24h = 1 điếu thuốc
    return round((pm25_mean / 22.0) * days, 1)

# ===================== STRICT DATA LOADING =====================
@st.cache_data
def load_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "..", "data", "vietnam_air_quality.csv")
    
    if not os.path.exists(file_path):
        st.error(f"🚨 LỖI NGHIÊM TRỌNG: Không tìm thấy file dữ liệu tại: {file_path}")
        st.stop()
        
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['month'] = df['timestamp'].dt.month
    df['hour'] = df['timestamp'].dt.hour
    df['date'] = df['timestamp'].dt.date
    df['day_name'] = df['timestamp'].dt.day_name()
    df['is_weekend'] = df['timestamp'].dt.dayofweek >= 5
    df['time_of_day'] = df['hour'].apply(get_time_of_day)
    df['is_raining'] = df['rain'] > 0
    
    if 'pm2_5' in df.columns and 'pm10' in df.columns:
        df['pm_ratio'] = (df['pm2_5'] / df['pm10'].replace(0, 0.001)).clip(upper=1.0)
        
    return df

with st.spinner("Đang trích xuất dữ liệu đa điểm..."):
    df = load_data()

# ===================== AQI LOGIC =====================
def get_aqi_category(aqi):
    if aqi <= 50: return "Tốt", "#00E400"
    elif aqi <= 100: return "Trung bình", "#FFFF00"
    elif aqi <= 150: return "Kém (Nhạy cảm)", "#FF7E00"
    elif aqi <= 200: return "Xấu", "#FF0000"
    elif aqi <= 300: return "Rất xấu", "#8F3F97"
    else: return "Nguy hại", "#7E0023"

df['aqi_level'] = df['aqi'].apply(lambda x: get_aqi_category(x)[0])

# ===================== SIDEBAR =====================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3203/3203071.png", width=60)
st.sidebar.markdown("### ⚙️ Bảng Điều Khiển")

all_cities = sorted(df['city'].unique().tolist())
selected_cities = st.sidebar.multiselect("🌆 Chọn Khu vực quan trắc", options=all_cities, default=all_cities)

if not selected_cities:
    st.warning("👈 Vui lòng chọn ít nhất 1 khu vực để hiển thị.")
    st.stop()

df = df[df['city'].isin(selected_cities)]

min_date, max_date = df['timestamp'].min().date(), df['timestamp'].max().date()
start, end = st.sidebar.date_input("📅 Khung thời gian", [min_date, max_date], min_value=min_date, max_value=max_date)
df = df[(df['timestamp'].dt.date >= start) & (df['timestamp'].dt.date <= end)]
days_selected = max(1, (end - start).days + 1)

st.sidebar.markdown("---")
st.sidebar.success(f"Dữ liệu đang xét: {len(df):,} bản ghi")

# ===================== HEADER & CUSTOM KPI =====================
st.markdown("<h1 style='text-align:center; margin-bottom: 30px; font-weight: 800;'>🌍 Nền Tảng Phân Tích Môi Trường Tích Hợp</h1>", unsafe_allow_html=True)

current_avg_aqi = int(df['aqi'].mean())
current_avg_pm25 = round(df['pm2_5'].mean(), 1)
worst_city = df.groupby('city')['aqi'].mean().idxmax() if not df.empty else "N/A"
danger_pct = (df['aqi'] > 150).mean() * 100
cig_eq = calc_cigarette_eq(current_avg_pm25, days_selected)
avg_ratio = df['pm_ratio'].mean() if 'pm_ratio' in df.columns else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f"<div class='glass-card'><span class='metric-label'>AQI Trạm Tổng Hợp</span><p class='metric-value' style='color:{get_aqi_category(current_avg_aqi)[1]}'>{current_avg_aqi}</p></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='glass-card'><span class='metric-label'>Bụi PM2.5 (µg/m³)</span><p class='metric-value'>{current_avg_pm25}</p></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='glass-card'><span class='metric-label'>Phơi Nhiễm (Thuốc lá)</span><p class='metric-value' style='color:#e74c3c;'>{cig_eq} 🚬</p></div>", unsafe_allow_html=True)
c4.markdown(f"<div class='glass-card'><span class='metric-label'>Điểm Đen Ô Nhiễm</span><p class='metric-value' style='font-size:1.6rem; margin-top:10px;'>{worst_city}</p></div>", unsafe_allow_html=True)
c5.markdown(f"<div class='glass-card'><span class='metric-label'>Tỷ Lệ Giờ Rủi Ro</span><p class='metric-value'>{danger_pct:.1f}%</p></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ===================== TABS (10 Tính năng) =====================
tab_titles = [
    "🎯 Tổng quan", "🫁 Sức khỏe", "🕰️ Hành vi", "📈 Xu hướng", "⚖️ So sánh", 
    "🗺️ Bản đồ", "🌪️ 3D", "🌧️ Khí tượng", "🚨 Cực đoan", "📊 Dữ liệu"
]
tabs = st.tabs(tab_titles)

# ===================== TAB 1: GAUGE & INSIGHTS =====================
with tabs[0]:
    col_gauge, col_insight = st.columns([1.2, 1])
    with col_gauge:
        status_text, status_color = get_aqi_category(current_avg_aqi)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = current_avg_aqi,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"{status_text}", 'font': {'size': 24, 'color': status_color}},
            gauge = {'axis': {'range': [0, 500], 'tickwidth': 1}, 'bar': {'color': "rgba(0,0,0,0.3)"},
                     'steps': [{'range': [0, 50], 'color': "#00E400"}, {'range': [51, 100], 'color': "#FFFF00"},
                               {'range': [101, 150], 'color': "#FF7E00"}, {'range': [151, 200], 'color': "#FF0000"},
                               {'range': [201, 300], 'color': "#8F3F97"}, {'range': [301, 500], 'color': "#7E0023"}]}
        ))
        fig_gauge.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_insight:
        st.subheader("💡 Khuyến nghị Sinh hoạt (AI)")
        td, mc, kt = get_activity_recommendation(current_avg_aqi)
        st.write(f"- 🏃‍♂️ **Thể dục ngoài trời:** {td}")
        st.write(f"- 🪟 **Lưu thông khí:** {mc}")
        st.write(f"- 😷 **Bảo vệ hô hấp:** {kt}")
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("🔎 Nguồn Bụi Định Danh (PM2.5/PM10)")
        st.progress(min(avg_ratio, 1.0))
        source_text = "Chủ yếu do khói xe/công nghiệp" if avg_ratio > 0.6 else "Chủ yếu do bụi đất tự nhiên/công trình"
        st.caption(f"Tỷ lệ hiện tại: **{avg_ratio:.2f}** ➡️ *{source_text}*")

# ===================== TAB 2: HEALTH IMPACT =====================
with tabs[1]:
    st.subheader("🫁 Phân Tích Tác Động Hô Hấp")
    st.write("Theo tổ chức Berkeley Earth, hít thở không khí chứa 22 µg/m³ PM2.5 trong 24 giờ gây hại tương đương việc hút 1 điếu thuốc lá.")
    
    col_h1, col_h2 = st.columns([1.5, 1])
    with col_h1:
        daily_cigs = df.groupby('date')['pm2_5'].mean().reset_index()
        daily_cigs['cigarettes'] = daily_cigs['pm2_5'] / 22.0
        fig_cig = px.bar(daily_cigs, x='date', y='cigarettes', labels={'cigarettes': 'Số điếu thuốc tương đương', 'date': 'Ngày'}, color='cigarettes', color_continuous_scale='Reds')
        fig_cig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_cig, use_container_width=True)
        
    with col_h2:
        st.markdown(f"""
        <div style='padding: 25px; background: rgba(231, 76, 60, 0.1); border-left: 5px solid #e74c3c; border-radius: 10px; height:100%;'>
            <h3>Báo cáo Phơi nhiễm Nhóm</h3>
            <p style='font-size: 1.2rem; margin-top:20px;'>Trong <b>{days_selected} ngày</b> qua, với mức PM2.5 là <b>{current_avg_pm25} µg/m³</b>, phổi của bạn phải lọc lượng bụi độc hại tương đương với việc hút trực tiếp <b><span style='color:#e74c3c; font-size:1.5rem; font-weight:bold;'>{cig_eq}</span> điếu thuốc lá</b>.</p>
        </div>
        """, unsafe_allow_html=True)

# ===================== TAB 3: BEHAVIORAL PATTERNS =====================
with tabs[2]:
    st.subheader("🕰️ Nhịp sinh học & Chu kỳ Ô nhiễm")
    c_trend1, c_trend2 = st.columns(2)
    with c_trend1:
        time_df = df.groupby('time_of_day')['aqi'].mean().reindex(['Sáng (6h-12h)', 'Chiều (12h-18h)', 'Tối (18h-24h)', 'Đêm (0h-6h)']).reset_index()
        fig_time = px.bar(time_df, x='time_of_day', y='aqi', color='aqi', title="Sự gia tăng theo buổi trong ngày", color_continuous_scale='Reds')
        fig_time.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_time, use_container_width=True)
    with c_trend2:
        df['Day Type'] = df['is_weekend'].map({True: 'Cuối tuần (T7, CN)', False: 'Ngày thường (Đi làm/Học)'})
        fig_box = px.box(df, x='Day Type', y='aqi', color='Day Type', title="Hiệu ứng Ngày làm việc (Giao thông)")
        fig_box.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_box, use_container_width=True)

# ===================== TAB 4: TREND & SMOOTHING =====================
with tabs[3]:
    st.subheader("📈 Phân Tích Xu Hướng Bằng Thuật Toán EWMA")
    st.write("Dữ liệu cảm biến thô thường dao động rất mạnh. Áp dụng Exponentially Weighted Moving Average để nhìn thấu xu hướng.")
    
    metric_smooth = st.radio("Chọn chỉ số:", ['aqi', 'pm2_5', 'pm10'], horizontal=True)
    trend_df = df.groupby('timestamp')[metric_smooth].mean().reset_index()
    trend_df['EWMA'] = trend_df[metric_smooth].ewm(span=24, adjust=False).mean() # Mượt theo chu kỳ 24h
    
    fig_smooth = go.Figure()
    fig_smooth.add_trace(go.Scatter(x=trend_df['timestamp'], y=trend_df[metric_smooth], mode='lines', name='Dữ liệu thô', line=dict(color='rgba(150,150,150,0.4)')))
    fig_smooth.add_trace(go.Scatter(x=trend_df['timestamp'], y=trend_df['EWMA'], mode='lines', name='Xu hướng cốt lõi (EWMA)', line=dict(color='#e74c3c', width=3)))
    fig_smooth.update_layout(hovermode='x unified', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_smooth, use_container_width=True)

# ===================== TAB 5: RADAR COMPARISON =====================
with tabs[4]:
    st.subheader("⚖️ So Sánh Hồ Sơ Ô Nhiễm Khu Vực")
    if len(selected_cities) < 2:
        st.info("💡 Vui lòng chọn từ 2 khu vực trở lên ở thanh bên trái (Sidebar) để kích hoạt biểu đồ so sánh Mạng nhện.")
    else:
        st.write("Phân tích đa biến giữa các thành phố được chọn.")
        radar_df = df.groupby('city')[['aqi', 'pm2_5', 'pm10', 'temp', 'humidity']].mean().reset_index()
        
        # Chuẩn hóa dữ liệu (0-1) để vẽ Radar chính xác vì các thang đo khác nhau
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
        metrics = ['aqi', 'pm2_5', 'pm10', 'temp', 'humidity']
        radar_df[metrics] = scaler.fit_transform(radar_df[metrics])
        
        fig_radar = go.Figure()
        for city in selected_cities:
            city_data = radar_df[radar_df['city'] == city]
            if not city_data.empty:
                fig_radar.add_trace(go.Scatterpolar(
                    r=city_data.iloc[0][metrics].values.tolist(),
                    theta=['AQI Tương đối', 'PM2.5 Tương đối', 'PM10 Tương đối', 'Nhiệt độ Tương đối', 'Độ ẩm Tương đối'],
                    fill='toself', name=city, opacity=0.6
                ))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=False)), showlegend=True, height=500, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_radar, use_container_width=True)

# ===================== TAB 6: GIS MAP =====================
with tabs[5]:
    st.subheader("🗺️ Bản đồ Nhiệt Độ bao phủ Ô nhiễm")
    map_df = df.groupby(['city', 'lat', 'lon']).agg({'aqi': 'mean', 'pm2_5': 'mean'}).reset_index()
    fig_map = px.scatter_mapbox(map_df, lat='lat', lon='lon', size='aqi', color='aqi', hover_name='city', zoom=4.8, color_continuous_scale=px.colors.sequential.Reds)
    fig_map.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0}, height=550)
    st.plotly_chart(fig_map, use_container_width=True)

# ===================== TAB 7: WEATHER 3D =====================
with tabs[6]:
    st.subheader("🌪️ Tương tác Không gian 3 Chiều")
    st.write("Sử dụng chuột xoay biểu đồ để tìm điểm giao thoa nguy hiểm giữa Khí hậu và Bụi mịn.")
    fig_3d = px.scatter_3d(df.sample(min(len(df), 1000)), x='temp', y='humidity', z='aqi', color='wind_speed', size='pm2_5', opacity=0.8, color_continuous_scale='Viridis')
    fig_3d.update_layout(margin=dict(l=0, r=0, b=0, t=0), height=550, paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_3d, use_container_width=True)

# ===================== TAB 8: METEOROLOGY & WASHOUT =====================
with tabs[7]:
    st.subheader("🌧️ Hiệu ứng Khí tượng & Rửa trôi")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("**Hiệu ứng Rửa trôi của Mưa (Washout)**")
        df['Trạng thái Mưa'] = df['is_raining'].map({True: 'Có Mưa', False: 'Trời Khô'})
        fig_rain = px.box(df, x='Trạng thái Mưa', y='pm2_5', color='Trạng thái Mưa', color_discrete_map={'Có Mưa': '#3498db', 'Trời Khô': '#95a5a6'})
        fig_rain.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_rain, use_container_width=True)
    with col_m2:
        st.markdown("**Ma trận Tương quan Pearson**")
        corr = df[['aqi', 'pm2_5', 'pm10', 'temp', 'humidity', 'wind_speed', 'rain']].corr()
        fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale='RdBu_r', aspect="auto")
        fig_corr.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_corr, use_container_width=True)

# ===================== TAB 9: ANOMALY DETECTION =====================
with tabs[8]:
    st.subheader("🚨 Bắt Sự kiện Ô nhiễm Cực đoan")
    st.write("Tự động cô lập Top 5% những thời điểm chỉ số AQI cao đột biến để truy tìm nguyên nhân.")
    threshold = df['aqi'].quantile(0.95)
    anomalies = df[df['aqi'] >= threshold]
    st.error(f"⚠️ Phát hiện **{len(anomalies)}** sự kiện cực đoan (AQI >= {int(threshold)})")
    
    fig_anomaly = px.scatter(df, x='timestamp', y='aqi', color=df['aqi'] >= threshold, color_discrete_map={True: '#e74c3c', False: 'rgba(150,150,150,0.3)'})
    fig_anomaly.add_hline(y=threshold, line_dash="dash", line_color="red", annotation_text="Ngưỡng 95%")
    fig_anomaly.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_anomaly, use_container_width=True)
    
    with st.expander("📄 Truy xuất danh sách cực đoan (Click để mở)"):
        st.dataframe(anomalies[['timestamp', 'city', 'aqi', 'pm2_5', 'wind_speed', 'rain']].sort_values('aqi', ascending=False), use_container_width=True)

# ===================== TAB 10: DATA PROFILING =====================
with tabs[9]:
    st.subheader("📊 Hồ sơ Phân phối (Distributions)")
    metric_dist = st.selectbox("Chọn chỉ số để xem phân phối:", ['aqi', 'pm2_5', 'pm10', 'temp', 'humidity', 'wind_speed'])
    fig_hist = px.histogram(df, x=metric_dist, marginal="box", nbins=50, color_discrete_sequence=['#8e44ad'])
    fig_hist.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_hist, use_container_width=True)

# ===================== EXPORT AREA =====================
st.markdown("---")
col_f1, col_f2 = st.columns([3, 1])
with col_f1:
    st.caption("✨ Xây dựng với kiến trúc Streamlit nâng cao & Thuật toán xử lý dữ liệu chuẩn Khoa học Dữ liệu.")
with col_f2:
    st.download_button("📥 Xuất dữ liệu đã lọc (CSV)", data=df.to_csv(index=False).encode('utf-8'), file_name=f"ems_full_export_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)