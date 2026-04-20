import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.helpers import AQI_DEF, POLLS, aqi_meta, ml, ax, chart_h, PT, GC, LC, TF, hex_rgba, POLL_BANDS, val_meta

# Map UI City names -> actual folder names
CITY_FOLDERS = {
    "An Giang": "an_giang", "Bắc Ninh": "bac_ninh", "Cà Mau": "ca_mau", "Cần Thơ": "can_tho",
    "Cao Bằng": "cao_bang", "Đà Nẵng": "da_nang", "Đắk Lắk": "dak_lak", "Điện Biên": "dien_bien",
    "Đồng Nai": "dong_nai", "Đồng Tháp": "dong_thap", "Gia Lai": "gia_lai", "Hà Nội": "ha_noi",
    "Hà Tĩnh": "ha_tinh", "Hải Phòng": "hai_phong", "Thành phố Hồ Chí Minh": "ho_chi_minh",
    "Huế": "hue", "Hưng Yên": "hung_yen", "Khánh Hòa": "khanh_hoa", "Lai Châu": "lai_chau",
    "Lâm Đồng": "lam_dong", "Lạng Sơn": "lang_son", "Lào Cai": "lao_cai", "Nghệ An": "nghe_an",
    "Ninh Bình": "ninh_binh", "Phú Thọ": "phu_tho", "Quảng Ngãi": "quang_ngai", "Quảng Ninh": "quang_ninh",
    "Quảng Trị": "quang_tri", "Sơn La": "son_la", "Tây Ninh": "tay_ninh", "Thái Nguyên": "thai_nguyen",
    "Thanh Hóa": "thanh_hoa", "Tuyên Quang": "tuyen_quang", "Vĩnh Long": "vinh_long"
}

REGIONS = {
    "Miền Bắc": ["Hà Nội", "Bắc Ninh", "Cao Bằng", "Điện Biên", "Hải Phòng", "Hưng Yên", "Lai Châu", "Lạng Sơn", "Lào Cai", "Ninh Bình", "Phú Thọ", "Quảng Ninh", "Sơn La", "Thái Nguyên", "Tuyên Quang"],
    "Miền Trung": ["Đà Nẵng", "Huế", "Hà Tĩnh", "Khánh Hòa", "Lâm Đồng", "Nghệ An", "Quảng Ngãi", "Quảng Trị", "Gia Lai", "Đắk Lắk", "Thanh Hóa"],
    "Miền Nam": ["Thành phố Hồ Chí Minh", "An Giang", "Cà Mau", "Cần Thơ", "Đồng Nai", "Đồng Tháp", "Tây Ninh", "Vĩnh Long"]
}

@st.cache_data(ttl=3600*24, show_spinner=False)
def get_location_map(dir_path):
    """
    Scans a directory for parquet files and maps filenames to their location names.
    Reads the first row of each file to extract the 'location' column.
    
    Args:
        dir_path (str): The directory path to scan.
        
    Returns:
        dict: A mapping of filename to location name.
    """
    mapping = {}
    if not os.path.exists(dir_path):
        return mapping
    for f in os.listdir(dir_path):
        if f.endswith(".parquet") and f != "all.parquet":
            clean_name = f.replace(".parquet", "")
            try:
                # Read just the first row, only the 'location' column to be extra fast
                df_loc = pd.read_parquet(os.path.join(dir_path, f), columns=["location"]).head(1)
                if not df_loc.empty and pd.notna(df_loc.iloc[0, 0]):
                    loc_val = str(df_loc.iloc[0, 0]).strip()
                    # Resolve duplicates if any
                    if loc_val in mapping.values():
                        loc_val = f"{loc_val} ({clean_name})"
                    mapping[f] = loc_val
                else:
                    mapping[f] = clean_name
            except Exception:
                mapping[f] = clean_name
    return mapping

@st.cache_data(ttl=3600, show_spinner=False)
def load_tier2_data(city_folder, filename):
    """
    Loads real-time AQI data for a specific station.
    
    Args:
        city_folder (str): The folder name for the city.
        filename (str): The parquet filename.
        
    Returns:
        pd.DataFrame: Cleaned and sorted DataFrame, or empty DataFrame on failure.
    """
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "..", "data", "aqi", city_folder, filename)
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_parquet(file_path)
        if df.empty: return df
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp", "aqi"])
        df = df.sort_values("timestamp")
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_tier2_year_data(city_folder, filename):
    """
    Loads historical daily AQI data for a specific station (Yearly scope).
    
    Args:
        city_folder (str): The folder name for the city.
        filename (str): The parquet filename.
        
    Returns:
        pd.DataFrame: Cleaned and sorted DataFrame, or empty DataFrame on failure.
    """
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "..", "data", "aqi_year_2025", city_folder, filename)
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_parquet(file_path)
        if df.empty: return df
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp", "aqi"])
        df = df.sort_values("timestamp")
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_forecast_data(city_folder, filename):
    """
    Loads forecast AQI data for a specific station, attempting filename normalization if an exact match fails.
    
    Args:
        city_folder (str): The folder name for the city.
        filename (str): The target parquet filename.
        
    Returns:
        pd.DataFrame: Deduplicated and sorted forecast DataFrame, or empty DataFrame on failure.
    """
    base_dir = os.path.dirname(__file__)
    # Try exact match first
    file_path = os.path.join(base_dir, "..", "data", "forecast", city_folder, filename)
    
    if not os.path.exists(file_path):
        # Mismatch logic: Forecast files are often normalized (lowercase, no accents, underscores)
        # We try to normalize the filename to match.
        import re
        s = filename.replace(".parquet", "")
        # Standard normalization used in get_forecast.py
        s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ]', 'a', s)
        s = re.sub(r'[èéẹẻẽêềếệểễÈÉẸẺẼÊỀẾỆỂỄ]', 'e', s)
        s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'o', s)
        s = re.sub(r'[ìíịỉĩÌÍỊỈĨ]', 'i', s)
        s = re.sub(r'[ùúụủũưừứựửữÙÚỤỦŨƯỪỨỰỬỮ]', 'u', s)
        s = re.sub(r'[ỳýỵỷỹỲÝỴỶỸ]', 'y', s)
        s = re.sub(r'[đĐ]', 'd', s)
        s = re.sub(r'[^a-zA-Z0-9\s]', '', s).strip().lower()
        normalized_filename = re.sub(r'\s+', '_', s) + ".parquet"
        
        file_path = os.path.join(base_dir, "..", "data", "forecast", city_folder, normalized_filename)

    if not os.path.exists(file_path):
        return pd.DataFrame()
        
    try:
        df = pd.read_parquet(file_path)
        if df.empty: return df
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp", "aqi"])
        # Deduplicate by averaging values for the same timestamp
        df = df.groupby("timestamp", observed=False).mean(numeric_only=True).reset_index()
        df = df.sort_values("timestamp")
        return df
    except Exception:
        return pd.DataFrame()

def render_hourly_forecast(df_forecast, poll_key, poll_label, city_name, unit_name):
    """
    Renders a horizontally scrollable hourly forecast UI.
    
    Args:
        df_forecast (pd.DataFrame): The forecast data.
        poll_key (str): The key for the pollutant metric (e.g. 'aqi', 'pm2_5').
        poll_label (str): Display label for the metric.
        city_name (str): The city name.
        unit_name (str): The specific station or unit name.
    """
    if df_forecast.empty:
        return
    
    # Filter for future data (from current hour onwards)
    now = pd.Timestamp.now().replace(minute=0, second=0, microsecond=0)
    df_future = df_forecast[df_forecast["timestamp"] >= (now - pd.Timedelta(hours=1))].copy()
    
    if df_future.empty:
        return

    # Clean location string: if 'Tổng quan' is in unit_name, just show city_name
    if "Tổng quan" in unit_name:
        location_str = city_name
    else:
        location_str = f"{city_name} - {unit_name}"
    
    st.markdown(f'''<div style="margin-top: 1rem; margin-bottom: 1rem;">
<div style="font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 2px;">Dự báo {poll_label} theo giờ</div>
<div style="font-size: 14px; color: #64748b;">Khu vực: <span style="font-weight: 600; color: #334155;">{location_str}</span></div>
</div>''', unsafe_allow_html=True)

    # Build horizontal scroll container
    scroll_html = '<div style="display: flex; overflow-x: auto; gap: 12px; padding-bottom: 16px; scrollbar-width: thin;">'
    
    for i, (_, row) in enumerate(df_future.head(48).iterrows()):
        ts = row["timestamp"]
        val = row[poll_key] if poll_key in row else row["aqi"]
        lbl, col = val_meta(val, poll_key if poll_key in row else "aqi")
        
        hr_str = "Bây giờ" if i == 0 else ts.strftime("%H:%M")
        
        # Determine day label (only for i=0 or hour=00:00)
        day_label = ""
        is_boundary = False
        if i == 0 or ts.hour == 0:
            day_label = f"Th {ts.weekday() + 2}" if ts.weekday() != 6 else "CN"
            if i != 0: is_boundary = True # Start of a new day

        border_style = "border-left: 1px dashed #cbd5e1; padding-left: 12px;" if is_boundary else ""
        
        scroll_html += f'''<div style="display:flex; flex-direction:column; align-items:center; min-width: 65px; {border_style}">
<div style="height: 18px; font-size: 11px; font-weight: 700; color: #0f172a; margin-bottom: 4px; text-align: center;">{day_label}</div>
<div style="font-size: 12px; color: #64748b; margin-bottom: 8px;">{hr_str}</div>
<div style="background: {col}; color: white; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 13px; min-width: 42px; text-align: center;">{val:.0f}</div>
</div>'''
            
    scroll_html += '</div>'
    st.markdown(scroll_html, unsafe_allow_html=True)

def render_daily_forecast(df_forecast, poll_key, poll_label, city_name, unit_name):
    """
    Renders a vertical list showing the daily average forecast for the next 4 days.
    
    Args:
        df_forecast (pd.DataFrame): The forecast data.
        poll_key (str): The key for the pollutant metric.
        poll_label (str): Display label for the metric.
        city_name (str): The city name.
        unit_name (str): The specific station or unit name.
    """
    if df_forecast.empty:
        return
        
    # Group by date
    df_forecast["date"] = df_forecast["timestamp"].dt.date
    daily = df_forecast.groupby("date", observed=False).agg({poll_key: "mean"}).reset_index()
    
    # Filter for today and future
    today = pd.Timestamp.now().date()
    daily = daily[daily["date"] >= today].head(4)
    
    container_html = '<div style="background: white; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">'
    
    for i, (_, row) in enumerate(daily.iterrows()):
        d = row["date"]
        val = row[poll_key]
        lbl, col = val_meta(val, poll_key)
        
        day_pref = "Hôm nay" if d == today else d.strftime("%A")
        # Vietnamese translation for days
        day_map = {"Monday": "Thứ 2", "Tuesday": "Thứ 3", "Wednesday": "Thứ 4", "Thursday": "Thứ 5", "Friday": "Thứ 6", "Saturday": "Thứ 7", "Sunday": "CN"}
        if d != today:
             day_pref = day_map.get(d.strftime("%A"), d.strftime("%d/%m"))
             
        bg_row = "transparent" if i % 2 == 0 else "#f8fafc"
        
        container_html += f'''<div style="display: flex; align-items: center; padding: 18px 20px; background: {bg_row}; border-bottom: 1px solid #f1f5f9;">
<div style="width: 80px; font-weight: 600; color: #334155; flex-shrink: 0;">{day_pref}</div>
<div style="width: 70px; display: flex; justify-content: center; flex-shrink: 0;">
<div style="background: {col}; color: white; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 14px; min-width: 50px; text-align: center;">{val:.0f}</div>
</div>
<div style="flex: 1; margin-left: 15px; font-size: 13px; font-weight: 500; color: {col};">{lbl}</div>
<div style="width: 90px; text-align: right; color: #64748b; font-size: 12px; flex-shrink: 0;">{d.strftime("%d/%m/%Y")}</div>
</div>'''
        
    container_html += '</div>'
    st.markdown(container_html, unsafe_allow_html=True)

def render_health_advice_box(avg_val, poll_type):
    """
    Renders a health advice box based on the current average AQI or pollutant value.
    
    Args:
        avg_val (float): The average value to evaluate.
        poll_type (str): The type of pollutant (e.g., 'aqi', 'pm2_5').
    """
    lbl, clr = val_meta(avg_val, poll_type)
    
    advice_content = {
        "Tốt": "Chất lượng không khí tốt, không ảnh hưởng tới sức khỏe",
        "Vừa phải": "Chất lượng không khí ở mức chấp nhận được. Tuy nhiên đối với những người nhạy cảm (người cao tuổi, trẻ em, người mắc các bệnh hô hấp, tim mạch…) có thể chịu những tác động nhất định tới sức khỏe.",
        "Không lành mạnh cho nhóm nhạy cảm": "Những người nhạy cảm gặp phải các vấn đề về sức khỏe, những người bình thường ít ảnh hưởng.",
        "Không khỏe mạnh": "Những người bình thường bắt đầu có các ảnh hưởng tới sức khỏe, nhóm người nhạy cảm có thể gặp những vấn đề sức khỏe nghiêm trọng hơn.",
        "Rất không tốt cho sức khỏe": "Cảnh báo hưởng tới sức khỏe: mọi người bị ảnh hưởng tới sức khỏe nghiêm trọng hơn.",
        "Nguy hiểm": "Cảnh báo khẩn cấp về sức khỏe: Toàn bộ dân số bị ảnh hưởng tới sức khỏe tới mức nghiêm trọng."
    }
    
    icon_map = {
        "Tốt": "https://www.iqair.com/dl/assets/svg/aqi/ic_face_48_green.svg",
        "Vừa phải": "https://www.iqair.com/dl/assets/svg/aqi/ic_face_48_yellow.svg",
        "Không lành mạnh cho nhóm nhạy cảm": "https://www.iqair.com/dl/assets/svg/aqi/ic_face_48_orange.svg",
        "Không khỏe mạnh": "https://www.iqair.com/dl/assets/svg/aqi/ic_face_48_red.svg",
        "Rất không tốt cho sức khỏe": "https://www.iqair.com/dl/assets/svg/aqi/ic_face_48_purple.svg",
        "Nguy hiểm": "https://www.iqair.com/dl/assets/svg/aqi/ic_face_48_maroon.svg"
    }
    
    icon_url = icon_map.get(lbl)
    desc = advice_content.get(lbl, "Hệ thống đang cập nhật khuyến cáo cho mức độ này...")
    
    # Header with dynamic icon (SVG or Material Fallback)
    if icon_url:
        icon_html = f'<img src="{icon_url}" style="width: 38px; height: 38px; margin-right: 12px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));" />'
    else:
        # Fallback for "Nguy hiểm" or others
        icon_html = f'<span class="material-symbols-rounded" style="color: {clr}; font-size: 32px; margin-right: 10px;">warning</span>'

    st.markdown(f'''<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0" rel="stylesheet" />
<div style="height: 100%; min-height: 270px; background-color: {hex_rgba(clr, 0.08)}; border: 1.5px solid {hex_rgba(clr, 0.3)}; border-radius: 12px; padding: 22px 24px; display: flex; flex-direction: column;">
    <div style="display: flex; align-items: center; margin-bottom: 12px;">
        {icon_html}
        <span style="color: {clr}; font-size: 15px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.8px;">KHUYẾN CÁO SỨC KHỎE</span>
    </div>
    <div style="color: #0f172a; font-size: 20px; font-weight: 700; margin-bottom: 12px; display: flex; align-items: center;">
        <div style="width: 12px; height: 12px; background: {clr}; border-radius: 50%; margin-right: 10px;"></div>
        {lbl}
    </div>
    <div style="color: #334155; font-size: 15px; line-height: 1.6; flex: 1; font-weight: 500;">
        {desc}
    </div>
    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px dashed {hex_rgba(clr, 0.4)}; color: #64748b; font-size: 12px; font-style: italic;">
        * Khuyến cáo dựa trên mức độ ô nhiễm trung bình dự báo.
    </div>
</div>''', unsafe_allow_html=True)

def render_comparison_bar_chart(df, poll_key, time_range, poll_label):
    """
    Renders a point-to-point comparison delta badge to show changes in pollution levels.
    
    Args:
        df (pd.DataFrame): The DataFrame containing historical data.
        poll_key (str): The column name for the target pollutant.
        time_range (str): The chosen time range for comparison (e.g. '24h', '7 ngày').
        poll_label (str): The display label for the pollutant.
    """
    if df.empty or poll_key not in df.columns:
        return
        
    last_ts = df["timestamp"].max()
    curr_val = df.loc[df["timestamp"] == last_ts, poll_key].values[0]
    
    # New Point-to-Point Logic
    delta_map = {
        "24h": pd.Timedelta(days=1),
        "7 ngày": pd.Timedelta(days=7),
        "30 ngày": pd.Timedelta(days=30),
        "3 tháng": pd.Timedelta(days=90),
        "1 năm": pd.Timedelta(days=365)
    }
    label_map = {
        "24h": "Hôm qua",
        "7 ngày": "7 ngày trước",
        "30 ngày": "30 ngày trước",
        "3 tháng": "3 tháng trước",
        "1 năm": "1 năm trước"
    }
    
    delta = delta_map.get(time_range, pd.Timedelta(days=1))
    
    if time_range == "1 năm":
        prev_ts = df["timestamp"].min()
        period_lbl = "Đầu chu kỳ"
    else:
        period_lbl = f"{label_map.get(time_range, 'Trước')} (cùng giờ)"
        prev_ts = last_ts - delta
        
    # Find the record closest to (but not after) the target past timestamp
    prev_rows = df[df["timestamp"] <= prev_ts]
    
    if not prev_rows.empty:
        # Check if the closest record is reasonably close (within 3 hours) to be valid "same hour"
        closest_row = prev_rows.iloc[-1]
        if time_range == "1 năm":
            prev_val = closest_row[poll_key]
        else:
            time_diff = abs((closest_row["timestamp"] - prev_ts).total_seconds()) / 3600
            
            if time_diff <= 3: # Allow 3hr window for missing samples
                prev_val = closest_row[poll_key]
            else:
                prev_val = None
    else:
        prev_val = None

    if prev_val is None:
        st.info(f"Không tìm thấy dữ liệu đối chứng tại cùng khung giờ cho mốc {time_range}.")
        return

    diff = curr_val - prev_val
    pct = (diff / prev_val * 100) if prev_val != 0 else 0
    
    # UI logic for the Delta Box
    status_color = "#16a34a" if diff <= 0 else "#dc2626"
    status_msg = "Cải thiện" if diff <= 0 else "Kém đi"
    arrow = "↓" if diff <= 0 else "↑"
    
    # Header with integrated Delta Badge
    if time_range == "1 năm":
        subtitle_lbl = "So sánh dữ liệu cuối chu kỳ với đầu chu kỳ"
        curr_lbl = "Cuối chu kỳ"
    else:
        subtitle_lbl = f"So sánh dữ liệu hiện tại ({last_ts.strftime('%H:%M %d/%m')}) với {period_lbl.lower()}"
        curr_lbl = "Hiện tại"
        
    st.markdown(f'''<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
        <div>
            <div style="font-size: 16px; font-weight: 700; color: #0f172a;">Biến động nồng độ {poll_label}</div>
            <div style="font-size: 12px; color: #64748b;">{subtitle_lbl}</div>
        </div>
        <div style="background: {hex_rgba(status_color, 0.12)}; border: 1.5px solid {hex_rgba(status_color, 0.25)}; padding: 8px 15px; border-radius: 10px; text-align: right; min-width: 110px;">
            <div style="color: {status_color}; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">{status_msg}</div>
            <div style="font-size: 20px; font-weight: 900; color: {status_color};">{arrow}{abs(pct):.1f}%</div>
        </div>
    </div>''', unsafe_allow_html=True)
    
    # Get semantic colors and apply alpha
    _, curr_c = val_meta(curr_val, poll_key)
    _, prev_c = val_meta(prev_val, poll_key)
    curr_color = hex_rgba(curr_c, 0.88)
    prev_color = hex_rgba(prev_c, 0.88)
    
    fig = go.Figure()
    
    # Add a horizontal reference line from the previous value
    fig.add_shape(
        type="line", line=dict(color="#94a3b8", width=1.5, dash="dash"),
        x0=-0.5, x1=1.5, y0=prev_val, y1=prev_val
    )
    
    # Past Bar
    fig.add_trace(go.Bar(
        x=[period_lbl],
        y=[prev_val],
        text=[f"<b>{prev_val:.1f}</b>"],
        textposition='auto',
        name=period_lbl,
        marker_color=hex_rgba(prev_c, 0.4), # More subtle past
        marker_line=dict(width=2, color="#fff"),
        hovertemplate=f"{period_lbl}: <b>%{{y:.1f}}</b><extra></extra>"
    ))
    
    # Current Bar
    fig.add_trace(go.Bar(
        x=[curr_lbl],
        y=[curr_val],
        text=[f"<b>{curr_val:.1f}</b>"],
        textposition='auto',
        name=curr_lbl,
        marker_color=curr_color, # Stronger current
        marker_line=dict(width=2, color="#fff"),
        hovertemplate=f"{curr_lbl}: <b>%{{y:.1f}}</b><extra></extra>"
    ))
    
    fig.update_layout(
        showlegend=False,
        height=450,
        margin=dict(l=10, r=10, t=50, b=10), # Increased top margin for labels
        yaxis={**ax(), "gridcolor": "rgba(148,163,184,0.08)", "zeroline": False},
        xaxis=dict(**ax()),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        bargap=0.5, # Thinner, more elegant bars
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"comp_chart_{poll_key}")

def render_correlation_heatmap(df_sub, time_range):
    """
    Renders a triangular heatmap showing the Pearson correlation between different pollutants.
    
    Args:
        df_sub (pd.DataFrame): The filtered dataset containing pollutant columns.
        time_range (str): The time range being analyzed, used for display labels.
    """
    # Select only pollutant columns
    cols = ["aqi", "pm2_5", "pm10", "o3", "no2", "co", "so2"]
    available_cols = [c for c in cols if c in df_sub.columns]
    
    if len(available_cols) < 2:
        return
        
    # Filter for numeric columns and ensure they ARE numeric
    # CSV uses 'pm2_5' instead of 'pm2.5'
    pollutant_cols = ["aqi", "pm2_5", "pm10", "o3", "no2", "co", "so2"]
    available_cols = [c for c in pollutant_cols if c in df_sub.columns]
    
    if len(available_cols) < 2:
        return

    # Ensure numeric types and drop NaNs
    df_corr = df_sub[available_cols].copy()
    for col in available_cols:
        df_corr[col] = pd.to_numeric(df_corr[col], errors='coerce')
        
    """
    # DYNAMIC AQI LOGIC - Commented out per user request
    # This was used to fix low correlation issues due to static file data
    def get_aqi_sub(val, bps, index_range=[0, 50, 100, 150, 200, 300, 400, 500]):
        if val <= bps[0]: return 0
        for i in range(len(bps)-1):
            if val <= bps[i+1]:
                return index_range[i] + (index_range[i+1]-index_range[i])/(bps[i+1]-bps[i]) * (val-bps[i])
        return 500
    
    def calc_comprehensive_aqi(row):
        aqis = []
        if "pm2_5" in row and not pd.isna(row["pm2_5"]):
            aqis.append(get_aqi_sub(row["pm2_5"], [0, 12, 35.4, 55.4, 150.4, 250.4, 350.4, 500.4]))
        if "pm10" in row and not pd.isna(row["pm10"]):
            aqis.append(get_aqi_sub(row["pm10"], [0, 54, 154, 254, 354, 424, 504, 604]))
        if "no2" in row and not pd.isna(row["no2"]):
            aqis.append(get_aqi_sub(row["no2"], [0, 53, 100, 360, 649, 1249, 1649, 2049]))
        if "so2" in row and not pd.isna(row["so2"]):
            aqis.append(get_aqi_sub(row["so2"], [0, 35, 75, 185, 304, 604, 804, 1004]))
        if "co" in row and not pd.isna(row["co"]):
            aqis.append(get_aqi_sub(row["co"]/1145, [0, 4.4, 9.4, 12.4, 15.4, 30.4, 40.4, 50.4]))
        return max(aqis) if aqis else 0
    
    df_corr["aqi"] = df_corr.apply(calc_comprehensive_aqi, axis=1)
    """

    df_corr = df_corr.dropna()
    
    if len(df_corr) < 3:
        st.info("Cần thêm dữ liệu sạch để tính toán tương quan.")
        return
        
    corr_matrix = df_corr.corr()
    
    # Map back to labels
    labels = []
    for c in available_cols:
        if c == "aqi": labels.append("AQI")
        elif c == "pm2_5": labels.append("PM2.5") # Map back to display name
        else: labels.append(POLLS[c]["label"])
        
    # Create mask for triangular heatmap (keep only lower triangle, exclude diagonal)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=0)
    df_masked = corr_matrix.where(~mask)

    # Create matrices for text and hover
    text_matrix = []
    hover_matrix = []
    for i in range(len(labels)):
        t_row = []
        h_row = []
        for j in range(len(labels)):
            if i > j:
                val = corr_matrix.values[i, j]
                t_row.append(f"<b>{val:.2f}</b>")
                h_row.append(f"Tương quan giữa <b>{labels[j]}</b> và <b>{labels[i]}</b>: <b>{val:.2f}</b>")
            else:
                t_row.append("")
                h_row.append("")
        text_matrix.append(t_row)
        hover_matrix.append(h_row)

    # Standard scientific colorscale: Red (Positive Correlation) to Blue (Negative Correlation)
    fig = go.Figure(data=go.Heatmap(
        z=df_masked.values,
        x=labels,
        y=labels,
        customdata=hover_matrix,
        text=text_matrix,
        texttemplate="%{text}",
        textfont={"size": 11, "family": "Be Vietnam Pro"},
        colorscale='RdBu_r', 
        zmin=-1, zmax=1,
        xgap=2, ygap=2,
        hovertemplate="%{customdata}<extra></extra>"
    ))
    
    fig.update_layout(
        height=450, # Further increased for maximum visibility
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=11, color="#475569"), side="bottom"),
        yaxis=dict(tickfont=dict(size=11, color="#475569"), autorange="reversed")
    )
    
    st.markdown(f'''<div style="margin-bottom: 20px;">
        <div style="font-size: 16px; font-weight: 700; color: #0f172a;">Tương quan đa biến</div>
        <div style="font-size: 12px; color: #64748b;">Mối liên hệ giữa các chất trong {time_range}</div>
    </div>''', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"corr_heatmap_{time_range}")


def render_regional_comparison(global_df, poll_key, poll_label, time_range):
    """
    Renders a comparative boxplot and insights panel to compare pollution distribution between two regions or cities.
    
    Args:
        global_df (pd.DataFrame): The main dataset containing city and region information.
        poll_key (str): The pollutant key to compare.
        poll_label (str): The display label for the pollutant.
        time_range (str): The selected time range for filtering data.
    """
    if time_range == "1 năm":
        from services.data_loader import load_weather_data, _apply_aqi_labels
        with st.spinner("Đang tải dữ liệu tổng quan 1 năm..."):
            df_to_use = load_weather_data()
            if not df_to_use.empty:
                df_to_use = _apply_aqi_labels(df_to_use)
    else:
        df_to_use = global_df

    if df_to_use.empty or poll_key not in df_to_use.columns:
        return

    # 1. Initialize session state for mode
    if "aqi_comp_mode" not in st.session_state:
        st.session_state.aqi_comp_mode = "Theo Miền"
    comp_mode = st.session_state.aqi_comp_mode

    # 2. Filter by time range
    max_d = df_to_use["timestamp"].max()
    delta_map = {
        "24h": pd.Timedelta(hours=24),
        "7 ngày": pd.Timedelta(days=7),
        "30 ngày": pd.Timedelta(days=30),
        "3 tháng": pd.Timedelta(days=90),
        "1 năm": pd.Timedelta(days=365)
    }
    min_d = max_d - delta_map.get(time_range, pd.Timedelta(hours=24))
    df_sub = df_to_use[df_to_use["timestamp"] >= min_d].copy()

    if df_sub.empty:
        return

    # 3. Define options and defaults based on mode
    if comp_mode == "Theo Miền":
        options = list(REGIONS.keys())
        default1, default2 = "Miền Bắc", "Miền Nam"
        
        prov_to_reg = {}
        for reg, provs in REGIONS.items():
            for p in provs: prov_to_reg[p] = reg
        df_sub["comp_label"] = df_sub["province"].map(prov_to_reg).astype(str)
    else:
        options = sorted(df_sub["province"].unique().astype(str))
        default1 = "Hà Nội" if "Hà Nội" in options else options[0]
        default2 = "Hồ Chí Minh" if "Hồ Chí Minh" in options else options[-1]
        df_sub["comp_label"] = df_sub["province"].astype(str)

    # 4. Section Header
    if time_range == "1 năm":
        actual_min = df_sub["timestamp"].min()
        actual_max = df_sub["timestamp"].max()
        if pd.notna(actual_min) and pd.notna(actual_max):
            date_range_str = f"{actual_min.strftime('%d/%m/%Y')} - {actual_max.strftime('%d/%m/%Y')}"
        else:
            date_range_str = f"{min_d.strftime('%d/%m')} - {max_d.strftime('%d/%m/%Y')}"
    else:
        date_range_str = f"{min_d.strftime('%d/%m')} - {max_d.strftime('%d/%m/%Y')}"
    st.markdown(f'''<div style="margin-top: 2rem; margin-bottom: 20px;">
        <div style="font-size: 20px; font-weight: 700; color: #0f172a;">Phân tích Đối chiếu</div>
        <div style="font-size: 13px; color: #64748b;">So sánh trực tiếp nồng độ {poll_label} - Giai đoạn: {date_range_str}</div>
    </div>''', unsafe_allow_html=True)

    # 5. Layout Setup
    col_left, col_right = st.columns([1.6, 1], gap="large")
    
    with col_left:
        # Selector Row - Increased width for c_mode to prevent wrapping
        c_mode, c_sel1, c_sel2 = st.columns([1.5, 1, 1], gap="medium")
        
        with c_mode:
            st.markdown("<div style='font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 8px;'>PHẠM VI</div>", unsafe_allow_html=True)
            b1, b2 = st.columns(2, gap="small")
            if b1.button("Theo Miền", type="primary" if comp_mode == "Theo Miền" else "secondary", width="stretch", key=f"btn_mien_{poll_key}"):
                st.session_state.aqi_comp_mode = "Theo Miền"
                st.session_state[f"comp_sel1_{poll_key}"] = "Miền Bắc"
                st.session_state[f"comp_sel2_{poll_key}"] = "Miền Nam"
                st.rerun()
            if b2.button("Theo Tỉnh thành", type="primary" if comp_mode == "Theo Tỉnh thành" else "secondary", width="stretch", key=f"btn_tinh_{poll_key}"):
                st.session_state.aqi_comp_mode = "Theo Tỉnh thành"
                st.session_state[f"comp_sel1_{poll_key}"] = "Hà Nội"
                st.session_state[f"comp_sel2_{poll_key}"] = "Hồ Chí Minh"
                st.rerun()

        with c_sel1:
            st.markdown("<div style='font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 8px;'>KHU VỰC 1</div>", unsafe_allow_html=True)
            if f"comp_sel1_{poll_key}" not in st.session_state or st.session_state[f"comp_sel1_{poll_key}"] not in options:
                st.session_state[f"comp_sel1_{poll_key}"] = default1
            sel1 = st.selectbox("Khu vực 1", options, key=f"comp_sel1_{poll_key}", label_visibility="collapsed")
        
        with c_sel2:
            st.markdown("<div style='font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 8px;'>KHU VỰC 2</div>", unsafe_allow_html=True)
            options2 = [o for o in options if o != sel1]
            if f"comp_sel2_{poll_key}" not in st.session_state or st.session_state[f"comp_sel2_{poll_key}"] not in options2:
                st.session_state[f"comp_sel2_{poll_key}"] = default2 if default2 in options2 else options2[0]
            sel2 = st.selectbox("Khu vực 2", options2, key=f"comp_sel2_{poll_key}", label_visibility="collapsed")

        # 6. Process Plot Data
        df_raw = df_sub[df_sub["comp_label"].isin([sel1, sel2])].copy()
        
        # Calculate mean for Insights
        df_plot = df_raw.groupby("comp_label", observed=False)[poll_key].mean().reset_index()
        df_plot = df_plot.rename(columns={"comp_label": "label"})
        df_plot["label"] = df_plot["label"].astype(str)
        df_plot["sort_idx"] = df_plot["label"].apply(lambda x: 0 if x == sel1 else 1)
        df_plot = df_plot.sort_values("sort_idx")

        if len(df_plot) < 2:
            st.info("Không có đủ dữ liệu cho cặp so sánh này.")
        else:
            fig = go.Figure()
            for sel in [sel1, sel2]:
                df_sel = df_raw[df_raw["comp_label"] == sel]
                if not df_sel.empty:
                    mean_val = df_sel[poll_key].mean()
                    _, color = val_meta(mean_val, poll_key)
                    fig.add_trace(go.Box(
                        y=df_sel[poll_key],
                        name=sel,
                        marker_color=color,
                        boxmean=True, # Show dashed line for Mean value
                        boxpoints='outliers', # Only show outliers
                        marker=dict(size=4, opacity=0.8),
                        line=dict(width=2),
                        hovertemplate=f"{sel}<br>{poll_label}: <b>%{{y:.1f}}</b><extra></extra>"
                    ))

            fig.update_layout(
                height=320, margin=dict(l=10, r=10, t=10, b=10),
                xaxis={**ax("Khu vực Đối chiếu"), "showline": False, "tickfont": dict(size=13, color="#0f172a")},
                yaxis={**ax(f"Phân bố {poll_label} ({time_range})"), "showgrid": True},
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"regional_comp_chart_{poll_key}")

    # 7. Insights (Right Column)
    with col_right:
        if len(df_plot) >= 2:
            med1 = df_raw[df_raw["comp_label"] == sel1][poll_key].median()
            med2 = df_raw[df_raw["comp_label"] == sel2][poll_key].median()
            max1 = df_raw[df_raw["comp_label"] == sel1][poll_key].max()
            max2 = df_raw[df_raw["comp_label"] == sel2][poll_key].max()
            
            diff = abs(med1 - med2)
            ratio = (diff / med2 * 100) if med2 > 0 else 0
            status1, color1 = val_meta(med1, poll_key)
            status2, color2 = val_meta(med2, poll_key)
            
            if diff < 0.1:
                eval_text = "Mặt bằng chung chất lượng không khí giữa hai khu vực là <b>tương đồng</b>."
                detail_text = "Cả hai đều có mức trung vị gần như bằng nhau. Bạn có thể quan sát thêm độ trải dài của hộp để xem nơi nào có nhiều biến động hơn."
                b_color = "#94a3b8"
            elif ratio < 1:
                eval_text = f"Chênh lệch trung vị giữa hai khu vực là <b>không đáng kể</b> (khoảng {ratio:.2f}%)."
                detail_text = "Mặt bằng chung khá giống nhau, sự khác biệt chủ yếu nằm ở các đợt ô nhiễm cực đoan (chấm nhỏ phía trên hộp)."
                b_color = "#94a3b8"
            else:
                cleaner = sel1 if med1 < med2 else sel2
                polluted = sel2 if med1 < med2 else sel1
                eval_text = f"Về mặt bằng chung, <b>{cleaner}</b> sạch hơn <b>{polluted}</b> khoảng <b>{ratio:.1f}%</b>."
                
                max_diff_text = f" Đặc biệt, mức ô nhiễm đỉnh điểm tại <b>{sel1}</b> lên tới {max1:.0f}, trong khi <b>{sel2}</b> là {max2:.0f}."
                if med2 > 100 or med1 > 100:
                    detail_text = f"Nồng độ trung vị {poll_label} đang ở mức cao. Boxplot cho thấy <b>{cleaner}</b> có sự phân bố ổn định và an toàn hơn.{max_diff_text}"
                else:
                    detail_text = f"Dựa trên dải phân bố, <b>{cleaner}</b> duy trì chất lượng không khí ở dải an toàn tốt hơn.{max_diff_text}"
                b_color = color1 if med1 < med2 else color2

            # Health Advice based on the worse area's maximum values
            max_val = max(max1, max2)
            if max_val <= 50:
                advice = "Điều kiện lý tưởng cho mọi hoạt động ngoài trời tại cả hai khu vực. Hầu như không có rủi ro đột biến."
            elif max_val <= 100:
                advice = "Chất lượng không khí khá an toàn. Tuy nhiên, nhóm nhạy cảm vẫn nên lưu ý vào các ngày xuất hiện mốc đột biến (outliers)."
            else:
                worse_peak = sel1 if max1 > max2 else sel2
                advice = f"Cảnh báo: Đã ghi nhận các đỉnh ô nhiễm nguy hiểm tại <b>{worse_peak}</b>. Cần chú ý bảo vệ hô hấp trong các đợt bùng phát này."

            # Ensure no leading whitespace for the f-string to prevent markdown code block rendering
            html_insight = f'''<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.5rem; height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
<div>
    <div style="font-size: 14px; font-weight: 700; color: #475569; margin-bottom: 1.25rem; letter-spacing: 0.5px;">Phân tích phân bố</div>
    <div style="margin-bottom: 1.25rem;">
        <div style="font-size: 13px; color: #64748b;">Chênh lệch Trung vị (Median)</div>
        <div style="font-size: 28px; font-weight: 800; color: #0f172a;">{diff:.1f} <span style="font-size: 14px; font-weight: 500; color: #64748b;">đơn vị</span></div>
    </div>
    <div style="padding: 14px; background: white; border-radius: 8px; border-left: 4px solid {b_color}; margin-bottom: 1.25rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
        <div style="font-size: 14px; color: #1e293b; line-height: 1.6;">{eval_text}</div>
        <div style="font-size: 13px; color: #64748b; line-height: 1.5; margin-top: 8px;">{detail_text}</div>
    </div>
</div>
<div>
    <div style="font-size: 13px; color: #64748b; line-height: 1.8; margin-bottom: 1rem;">
        • <b>{sel1}</b>: Trạng thái Trung vị <span style="color: {color1}; font-weight: 700;">{status1}</span><br>
        • <b>{sel2}</b>: Trạng thái Trung vị <span style="color: {color2}; font-weight: 700;">{status2}</span>
    </div>
    <div style="padding-top: 12px; border-top: 1px dashed #e2e8f0;">
        <div style="font-size: 12px; font-weight: 700; color: #475569; margin-bottom: 4px; text-transform: uppercase;">Khuyến nghị từ Outliers</div>
        <div style="font-size: 13px; color: #1e293b; line-height: 1.5;">{advice}</div>
    </div>
</div>
</div>'''
            st.markdown(html_insight, unsafe_allow_html=True)

def render(global_df):
    """
    Main entry point to render the AQI Tab.
    Handles the UI logic for selecting city, station, and timeframe, and orchestrates the
    rendering of the main charts, top rankings, forecasts, and comparative analyses.
    
    Args:
        global_df (pd.DataFrame): The global context dataframe containing data for all cities.
    """
    ctx = st.session_state.get("dashboard_context", {})
    if ctx: globals().update(ctx)
    
    st.markdown(
        '<div class="card" style="padding: 1.5rem; border-left: 5px solid #0ea5e9; background: linear-gradient(to right, #ffffff, #f8fbff); margin-bottom: 1.5rem;">'
        '<div style="font-size: 1.4rem; font-weight: 700; color: #1e293b; margin-bottom: 8px; display: flex; align-items: center; gap: 12px;">'
        '<span class="q-tag" style="font-size: 0.85rem; padding: 4px 10px; background: #e0f2fe; color: #0369a1; border-radius: 6px;">LỊCH SỬ</span>'
        'Phân tích Chuỗi thời gian & Xu hướng'
        '</div>'
        '<div style="font-size: 1rem; color: #64748b; line-height: 1.5;">Theo dõi dao động nồng độ chất ô nhiễm tại một khu vực cụ thể qua các mốc thời gian.</div>'
        '</div>',
        unsafe_allow_html=True
    )
    cities = list(CITY_FOLDERS.keys())
    
    # Initialize State
    if "aqi_selected_city" not in st.session_state:
        st.session_state["aqi_selected_city"] = "Thành phố Hồ Chí Minh"
    if "aqi_selected_tier2" not in st.session_state:
        st.session_state["aqi_selected_tier2"] = "Tổng quan (Thành phố Hồ Chí Minh)"
    if "aqi_chart_type" not in st.session_state:
        st.session_state["aqi_chart_type"] = "Đường (Spline)"
    if "aqi_time_range" not in st.session_state:
        st.session_state["aqi_time_range"] = "24h"
    if "aqi_pollutant" not in st.session_state:
        st.session_state["aqi_pollutant"] = "aqi"
    
    if "aqi_selected_bar" not in st.session_state:
        st.session_state["aqi_selected_bar"] = None
        
    # Inject local CSS for Blue Theme on Chart Type widget (Frames only)
    st.markdown(f"""
        <style>
        /* Segmented Control Group Border & Width */
        div[data-testid="stSegmentedControl"] {{
            border-radius: 12px !important;
            width: 100% !important;
            display: flex !important;
        }}
        /* All buttons in the control - Adjusted height and width to match Selectbox */
        div[data-testid="stSegmentedControl"] button {{
            flex: 1 !important; /* Expand to fill width */
            border-color: rgba(14, 165, 233, 0.2) !important;
            height: 42px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}
        /* Active button state (The blue theme requested) */
        div[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
            background-color: rgba(14, 165, 233, 0.1) !important;
            border: 1.5px solid #0ea5e9 !important;
            color: #0ea5e9 !important;
        }}
        /* Icon color when active */
        div[data-testid="stSegmentedControl"] button[aria-checked="true"] span {{
            color: #0ea5e9 !important;
        }}
        /* Hover effect */
        div[data-testid="stSegmentedControl"] button:hover {{
            border-color: #0ea5e9 !important;
            color: #0ea5e9 !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([1.6, 1.6, 1.2, 1.0, 1.0])
    
    with c1:
        # Safe fallback for index
        idx_city = 0
        if st.session_state["aqi_selected_city"] in cities:
            idx_city = cities.index(st.session_state["aqi_selected_city"])
            
        selected_city = st.selectbox(
            "Thành phố / Tỉnh", 
            options=cities, 
            index=idx_city,
            key="aqi_city_select"
        )
        
        if selected_city != st.session_state.get("aqi_selected_city"):
            st.session_state["aqi_city_version"] = st.session_state.get("aqi_city_version", 0) + 1
            st.session_state["aqi_selected_city"] = selected_city
            st.session_state["aqi_selected_tier2"] = f"Tổng quan ({selected_city})"
            st.session_state["aqi_selected_bar"] = None
            st.rerun()

    # Locate Tier 2 units dynamically
    folder_name = CITY_FOLDERS.get(selected_city, "ho_chi_minh")
    base_dir = os.path.dirname(__file__)
    if st.session_state.get("aqi_time_range") == "1 năm":
        dir_path = os.path.join(base_dir, "..", "data", "aqi_year_2025", folder_name)
    else:
        dir_path = os.path.join(base_dir, "..", "data", "aqi", folder_name)
    tong_quan_lbl = f"Tổng quan ({selected_city})"
    tier2_options = [tong_quan_lbl]
    file_map = {tong_quan_lbl: "all.parquet"}
    
    if os.path.exists(dir_path):
        loc_mapping = get_location_map(dir_path)
        for f in os.listdir(dir_path):
            if f.endswith(".parquet") and f != "all.parquet":
                clean_name = f.replace(".parquet", "")
                loc_name = loc_mapping.get(f, clean_name)
                tier2_options.append(loc_name)
                file_map[loc_name] = f
                
    tier2_options.sort() # Optional: sort alphabetical
    
    # Ensure "Tổng quan" is always first
    if tong_quan_lbl in tier2_options:
        tier2_options.remove(tong_quan_lbl)
        tier2_options.insert(0, tong_quan_lbl)
        
    # Reset tier2 selection if not found
    if st.session_state["aqi_selected_tier2"] not in tier2_options:
        st.session_state["aqi_selected_tier2"] = tier2_options[0]

    with c2:
        v = st.session_state.get("aqi_city_version", 0)
        widget_key = f"aqi_tier2_select_{selected_city}_{v}"
        
        selected_tier2 = st.selectbox(
            "Đơn vị (Huyện/Xã/Phường)", 
            options=tier2_options,
            index=tier2_options.index(st.session_state["aqi_selected_tier2"]),
            key=widget_key
        )
        
        if selected_tier2 != st.session_state.get("aqi_selected_tier2"):
            st.session_state["aqi_selected_tier2"] = selected_tier2
            st.session_state["aqi_selected_bar"] = None
            st.rerun()

    with c3:
        # Use native segmented_control with Material Icons style if supported
        try:
            chart_opts = [":material/show_chart:", ":material/bar_chart:"]
            sel_default = ":material/show_chart:" if st.session_state["aqi_chart_type"] == "Đường (Spline)" else ":material/bar_chart:"
            
            # Using st.segmented_control to show only icons
            raw_sel = st.segmented_control(
                "Loại biểu đồ", 
                options=chart_opts, 
                default=sel_default,
                key="aqi_chart_segmented"
            )
            
            # Fallback for deselection
            if raw_sel is None:
                chart_type = st.session_state["aqi_chart_type"]
            else:
                chart_type = "Đường (Spline)" if raw_sel == ":material/show_chart:" else "Cột (Bar)"
                
        except AttributeError:
            # Fallback for older Streamlit versions
            chart_type = st.radio("Loại biểu đồ", ["Đường (Spline)", "Cột (Bar)"], index=0 if st.session_state["aqi_chart_type"] == "Đường (Spline)" else 1, horizontal=True, key="aqi_chart_radio")

        if chart_type != st.session_state["aqi_chart_type"]:
            st.session_state["aqi_chart_type"] = chart_type
            st.rerun()

    with c4:
        tr_opts = ["24h", "7 ngày", "30 ngày", "3 tháng", "1 năm"]
        idx_tr = tr_opts.index(st.session_state["aqi_time_range"]) if st.session_state["aqi_time_range"] in tr_opts else 1
        time_range = st.selectbox("Thời gian", tr_opts, index=idx_tr, key="aqi_time_select")
        if time_range != st.session_state["aqi_time_range"]:
            st.session_state["aqi_time_range"] = time_range
            st.session_state["aqi_selected_bar"] = None
            st.rerun()

    with c5:
        polls_keys = ["aqi"] + list(POLLS.keys())
        
        def fmt_poll(k):
            if k == "aqi": return "AQI (US)"
            return POLLS[k]["label"]
            
        curr_pol = st.session_state.get("aqi_pollutant", "aqi")
        if curr_pol not in polls_keys:
            curr_pol = "aqi"
            
        selected_poll = st.selectbox(
            "Thông số", 
            options=polls_keys, 
            index=polls_keys.index(curr_pol), 
            format_func=fmt_poll,
            key="aqi_poll_select"
        )
        
        poll_lbl = fmt_poll(selected_poll)
        selected_poll_key = selected_poll
        
        if selected_poll != curr_pol:
            st.session_state["aqi_pollutant"] = selected_poll
            st.session_state["aqi_selected_bar"] = None
            st.rerun()

    # Load and process data
    target_file = file_map.get(selected_tier2, "all.parquet")
    if time_range == "1 năm":
        df = load_tier2_year_data(folder_name, target_file)
    else:
        df = load_tier2_data(folder_name, target_file)
    
    if df.empty or selected_poll_key not in df.columns:
        st.warning(f"Không có đủ dữ liệu lịch sử đo lường cho {selected_tier2}.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Filter out nulls to avoid broken graphs
    df = df.dropna(subset=[selected_poll_key])

    # Filter by time range
    max_d = df["timestamp"].max()
    if pd.isna(max_d):
        st.warning("Dữ liệu lỗi ngày tháng.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
        
    delta_map = {
        "24h": pd.Timedelta(hours=24),
        "7 ngày": pd.Timedelta(days=7),
        "30 ngày": pd.Timedelta(days=30),
        "3 tháng": pd.Timedelta(days=90),
        "1 năm": pd.Timedelta(days=365)
    }
    
    min_d = max_d - delta_map[time_range]
    df_sub = df[df["timestamp"] >= min_d].copy()
    
    # Keep a full copy for advanced analysis before any resampling for chart visuals
    df_analysis = df_sub.copy()
    
    if df_sub.empty:
        st.warning(f"Không có dữ liệu thu thập được trong khoảng {time_range} qua.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
        
    y_unit = "" if selected_poll_key == "aqi" else (" " + POLLS[selected_poll_key]["unit"])
    y_col = selected_poll_key
    
    val_min = df_sub[y_col].min()
    val_max = df_sub[y_col].max()
    row_min = df_sub.loc[df_sub[y_col].idxmin()]
    row_max = df_sub.loc[df_sub[y_col].idxmax()]
    
    # Title & Cards Layout
    st.markdown('<hr style="margin: 1.5rem 0 1rem 0; border-color: rgba(148,163,184,0.15);">', unsafe_allow_html=True)
    cChart, cRank = st.columns([2.8, 1.2], gap="large")
    cT1, cT2 = cChart.columns([1.4, 1], gap="small")
    
    with cT1:
        st.markdown(f'''<div>
    <div style="color:#64748b; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:2px;">Dữ liệu Chất lượng Không khí Lịch sử</div>
    <div style="font-size:22px; font-family:'Be Vietnam Pro',sans-serif; font-weight:700; color:#0f172a; margin-bottom:4px;">Biểu đồ {poll_lbl}</div>
    <div style="color:#334155; font-size:14px; font-weight:500;">{selected_tier2}</div>
</div>''', unsafe_allow_html=True)
        
    with cT2:
        lbl_min, c_min = val_meta(row_min[y_col], y_col)
        lbl_max, c_max = val_meta(row_max[y_col], y_col)
        str_min_time = row_min["timestamp"].strftime("%H:%M, %d/%m/%Y")
        str_max_time = row_max["timestamp"].strftime("%H:%M, %d/%m/%Y")
        str_val_min = f"{val_min:.0f}" if y_col == "aqi" else f"{val_min:.1f}"
        str_val_max = f"{val_max:.0f}" if y_col == "aqi" else f"{val_max:.1f}"
        
        st.markdown(f'''<div style="display:flex; justify-content: flex-end; gap: 12px; align-items:center; height:100%;">
    <!-- Min Card -->
    <div style="background:{hex_rgba(c_min, 0.12)}; border: 1.5px solid {hex_rgba(c_min, 0.4)}; padding: 10px 14px; border-radius: 10px; display:flex; flex-direction:column; min-width:140px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
            <span style="font-size:22px; font-weight:700; color:{c_min}; line-height:1;">{str_val_min}</span>
            <span style="font-size:11px; padding:2px 6px; background:{c_min}; color:#fff; border-radius:4px; font-weight:600;">{lbl_min}</span>
        </div>
        <div style="color:#64748b; font-size:11px; display:flex; align-items:center;">
            <span style="margin-right:4px;">↓ Tối thiểu</span>
        </div>
        <div style="color:#94a3b8; font-size:10px; font-weight:500;">
            lúc {str_min_time}
        </div>
    </div>
    <!-- Max Card -->
    <div style="background:{hex_rgba(c_max, 0.12)}; border: 1.5px solid {hex_rgba(c_max, 0.4)}; padding: 10px 14px; border-radius: 10px; display:flex; flex-direction:column; min-width:140px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
            <span style="font-size:22px; font-weight:700; color:{c_max}; line-height:1;">{str_val_max}</span>
            <span style="font-size:11px; padding:2px 6px; background:{c_max}; color:#fff; border-radius:4px; font-weight:600;">{lbl_max}</span>
        </div>
        <div style="color:#64748b; font-size:11px; display:flex; align-items:center;">
            <span style="margin-right:4px;">↑ Tối đa</span>
        </div>
        <div style="color:#94a3b8; font-size:10px; font-weight:500;">
            lúc {str_max_time}
        </div>
    </div>
</div>''', unsafe_allow_html=True)
    has_envelope = False
    # Simplify data points for large views to avoid squished charts
    if len(df_sub) > 50:
        rule_map = {
            "7 ngày": "6h",
            "30 ngày": "1D",
            "3 tháng": "3D",
            "1 năm": "7D"
        }
        rule = rule_map.get(time_range)
        if rule:
            if chart_type == "Đường (Spline)":
                # Group data to draw the Min/Max Envelope band and the center Mean line
                grouped = df_sub.set_index("timestamp").resample(rule)[y_col]
                
                df_mean = grouped.mean().dropna().reset_index()
                df_max_env = grouped.max().dropna().reset_index()
                df_min_env = grouped.min().dropna().reset_index()
                
                # Convert df_sub to a table containing mean points to draw the main line
                df_sub = df_mean
                # Add columns for envelope hover tooltips
                df_sub["env_max"] = df_max_env[y_col].values
                df_sub["env_min"] = df_min_env[y_col].values
                has_envelope = True
            else:
                # Bar Chart needs a Uniform time axis so columns have clear widths
                # We still use .max() to pick out the worst pollution points, without flattening them
                df_sub = df_sub.set_index("timestamp").resample(rule)[[y_col]].max().dropna().reset_index()

    # --- Interaction Logic: Filter by selected bar ---
    dt_start, dt_end = min_d, max_d + pd.Timedelta(seconds=1) # Default to full range
    selected_bar_time = st.session_state.get("aqi_selected_bar")
    
    if selected_bar_time and "Tổng quan" in str(selected_tier2):
        try:
            # Convert back to datetime and ensure it's naive (matches parquet data)
            sel_ts = pd.to_datetime(selected_bar_time).replace(tzinfo=None)
            
            # Find the actual bar in df_sub to ensure it exists
            if chart_type == "Cột (Bar)":
                df_match = df_sub[df_sub["timestamp"] == sel_ts]
                if not df_match.empty:
                    # Determine period for ranking
                    dt_start = sel_ts
                    
                    # Calculate end of period based on resampling rule OR hourly
                    rule_delta = {
                        "7 ngày": pd.Timedelta(hours=6),
                        "30 ngày": pd.Timedelta(days=1),
                        "3 tháng": pd.Timedelta(days=3),
                        "1 năm": pd.Timedelta(days=7)
                    }
                    dt_end = dt_start + rule_delta.get(time_range, pd.Timedelta(hours=1))
                    
                    # We no longer filter df_sub here to keep all bars visible (highlight/fade logic below)
                    pass
        except Exception:
            st.session_state["aqi_selected_bar"] = None
    else:
        # Clear selection if not in 'Tổng quan' view
        if st.session_state.get("aqi_selected_bar"):
            st.session_state["aqi_selected_bar"] = None
        selected_bar_time = None
    

    # Prepare array colors & labels for Plotly based on selected pollutant scale
    df_sub["clr"] = df_sub[y_col].apply(lambda x: val_meta(x, y_col)[1])
    df_sub["lbl"] = df_sub[y_col].apply(lambda x: val_meta(x, y_col)[0])
    
    # Clean unit string for tooltips to avoid empty parentheses
    clean_unit = y_unit.strip()
    u_suffix = f" {clean_unit}" if clean_unit else ""
    
    if has_envelope:
        df_sub["env_max_clr"] = df_sub["env_max"].apply(lambda x: val_meta(x, y_col)[1])
        df_sub["env_min_clr"] = df_sub["env_min"].apply(lambda x: val_meta(x, y_col)[1])

    # Calculate overall average color for the line chart
    avg_val = df_sub[y_col].mean()
    _, avg_color = val_meta(avg_val, y_col)

    # customdata: [label, color]
    cd_vals = df_sub[["lbl", "clr"]].values.tolist()

    fig = go.Figure()
    if chart_type == "Đường (Spline)":
        if has_envelope:
            # Trace 1: Draw Lower Bound Line purely for visual (NO HOVER)
            fig.add_trace(go.Scatter(
                x=df_sub["timestamp"],
                y=df_sub["env_min"],
                mode="lines",
                line=dict(width=1, color="rgba(148, 163, 184, 0.4)", shape="spline", smoothing=1),
                hoverinfo="skip",
                showlegend=False
            ))
            
            # Trace 2: Draw Upper Bound Line purely to fill shading down to Trace 1 (NO HOVER)
            fig.add_trace(go.Scatter(
                x=df_sub["timestamp"],
                y=df_sub["env_max"],
                mode="lines",
                line=dict(width=1, color="rgba(148, 163, 184, 0.4)", shape="spline", smoothing=1),
                fill="tonexty", 
                fillcolor="rgba(148, 163, 184, 0.15)",
                hoverinfo="skip",
                showlegend=False
            ))

        x_vals = df_sub["timestamp"].tolist()
        y_vals = df_sub[y_col].tolist()
        c_vals = df_sub["clr"].tolist()

        bands = POLL_BANDS.get(y_col, POLL_BANDS["aqi"])
        base_colors = [col for _,_,_,col in AQI_DEF]
        
        def get_color_score(val):
            for i in range(len(bands)):
                hi = bands[i][1]
                if hi == np.inf or hi is None or hi > 9999: hi = bands[i][0] * 1.5
                if val <= hi:
                    lo = bands[i-1][1] if i > 0 else bands[i][0]
                    frac = (val - lo)/(hi - lo) if hi > lo else 0
                    return i + max(0, frac)
            return len(bands) - 1.0
            
        def get_gradient_color(val):
            # Identify the band index
            idx = 0
            for i, (lo, hi) in enumerate(bands):
                if val <= hi:
                    idx = i
                    break
            else:
                idx = len(bands) - 1

            # Get base colors
            c_curr = base_colors[idx]
            
            # Boundary Smoothing: Only interpolate when very close to the next/prev threshold
            # This ensures colors within the band match the legend, but the transition is still smooth
            trans_zone = 5 # AQI points for transition zone
            
            # Check for next threshold transition
            if idx < len(bands) - 1:
                hi_threshold = bands[idx][1]
                if val > hi_threshold - trans_zone:
                    c_next = base_colors[idx + 1]
                    t = (val - (hi_threshold - trans_zone)) / (trans_zone * 2)
                    t = max(0, min(1, t))
                    return interpolate_hex(c_curr, c_next, t)
            
            # Check for previous threshold transition
            if idx > 0:
                lo_threshold = bands[idx][0]
                if val < lo_threshold + trans_zone:
                    c_prev = base_colors[idx - 1]
                    t = (val - (lo_threshold - trans_zone)) / (trans_zone * 2)
                    t = max(0, min(1, t))
                    return interpolate_hex(c_prev, c_curr, t)

            return c_curr

        def interpolate_hex(c1, c2, t):
            def hex_to_rgb(h): return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            r1, g1, b1 = hex_to_rgb(c1)
            r2, g2, b2 = hex_to_rgb(c2)
            r = int(r1 + (r2 - r1)*t)
            g = int(g1 + (g2 - g1)*t)
            b = int(b1 + (b2 - b1)*t)
            return f"#{r:02x}{g:02x}{b:02x}"

        # Smoothing using pchip for gradient spline Effect
        try:
            from scipy.interpolate import pchip_interpolate
            df_unique = df_sub.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
            if len(df_unique) > 3:
                x_num = df_unique["timestamp"].astype('int64').values
                y_arr = df_unique[y_col].values
                
                # Smooth PCHIP chart, tightly clamping peaks and valleys to not miss signals
                base_grid = np.linspace(x_num.min(), x_num.max(), max(1000, len(x_num)))
                x_interp_num = np.union1d(base_grid, x_num)
                y_interp = pchip_interpolate(x_num, y_arr, x_interp_num)
                x_interp = pd.to_datetime(x_interp_num, unit='ns')
            else:
                x_interp, y_interp = x_vals, y_vals
        except Exception:
            x_interp, y_interp = x_vals, y_vals

        # Group line segments by color to completely bypass Plotly's DOM limits
        color_traces = {}
        for i in range(len(x_interp)-1):
            avg_y = (y_interp[i] + y_interp[i+1]) / 2.0
            h_color = get_gradient_color(avg_y)
            if h_color not in color_traces:
                color_traces[h_color] = {"x": [], "y": []}
            color_traces[h_color]["x"].extend([x_interp[i], x_interp[i+1], None])
            color_traces[h_color]["y"].extend([y_interp[i], y_interp[i+1], None])
            
        for h_color, data in color_traces.items():
            fig.add_trace(go.Scatter(
                x=data["x"],
                y=data["y"],
                mode="lines",
                showlegend=False,
                hoverinfo="skip",
                line=dict(color=h_color, width=3.5)
            ))
            
        # Reactive Hover Layers (Segmented by color for dots & text coloring)
        if has_envelope:
            # Min Hover Segments
            min_segs = []
            if not df_sub.empty:
                cur_s = {"clr": df_sub["env_min_clr"].iloc[0], "x": [], "y": []}
                for i in range(len(df_sub)):
                    c = df_sub["env_min_clr"].iloc[i]
                    if c != cur_s["clr"]:
                        min_segs.append(cur_s)
                        cur_s = {"clr": c, "x": [], "y": []}
                    cur_s["x"].append(df_sub["timestamp"].iloc[i])
                    cur_s["y"].append(df_sub["env_min"].iloc[i])
                min_segs.append(cur_s)

                for s in min_segs:
                    fig.add_trace(go.Scatter(
                        x=s["x"], y=s["y"],
                        name="Tối thiểu",
                        mode="lines",
                        line=dict(width=0.1, color=s["clr"]), # Very thin colored line -> triggers colored dot
                        hovertemplate=f"<span style='color:{s['clr']}'><b>Tối thiểu</b></span>: %{{y:.1f}}{u_suffix}<extra></extra>",
                        showlegend=False
                    ))

        t_name = "Trung bình" if has_envelope else "Chỉ số"
        # Mean markers trace (always visible)
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            name=t_name,
            mode="markers",
            marker=dict(size=6, color=c_vals, opacity=1.0, line=dict(width=1, color="#fff")),
            showlegend=False,
            # Format: <text>: <value>, with colored text
            hovertemplate=f"<span style='color:%{{customdata[1]}}'><b>{t_name}</b></span>: %{{y:.1f}}{u_suffix}<extra></extra>",
            customdata=cd_vals
        ))
        
        if has_envelope:
            # Max Hover Segments
            max_segs = []
            if not df_sub.empty:
                cur_s = {"clr": df_sub["env_max_clr"].iloc[0], "x": [], "y": []}
                for i in range(len(df_sub)):
                    c = df_sub["env_max_clr"].iloc[i]
                    if c != cur_s["clr"]:
                        max_segs.append(cur_s)
                        cur_s = {"clr": c, "x": [], "y": []}
                    cur_s["x"].append(df_sub["timestamp"].iloc[i])
                    cur_s["y"].append(df_sub["env_max"].iloc[i])
                max_segs.append(cur_s)

                for s in max_segs:
                    fig.add_trace(go.Scatter(
                        x=s["x"], y=s["y"],
                        name="Tối đa",
                        mode="lines",
                        line=dict(width=0.1, color=s["clr"]), # Very thin colored line -> triggers colored dot
                        hovertemplate=f"<span style='color:{s['clr']}'><b>Tối đa</b></span>: %{{y:.1f}}{u_suffix}<extra></extra>",
                        showlegend=False
                    ))
    else:
        # Handle highlight/fade effect for selections
        bar_opacities = [0.9] * len(df_sub)
        if selected_bar_time and "Tổng quan" in str(selected_tier2):
             try:
                 sel_ts_norm = pd.to_datetime(selected_bar_time).replace(tzinfo=None)
                 bar_opacities = [0.9 if ts == sel_ts_norm else 0.25 for ts in df_sub["timestamp"]]
             except Exception:
                 pass

        fig.add_trace(go.Bar(
            x=df_sub["timestamp"],
            y=df_sub[y_col],
            marker_color=df_sub["clr"],
            marker_opacity=bar_opacities, # Apply selective opacity
            marker_line=dict(width=1, color="#fff"),
            hovertemplate=f"<span style='color:%{{customdata[1]}}'><b>Chỉ số</b></span>: %{{y:.1f}}{u_suffix}<extra></extra>",
            customdata=cd_vals
        ))

    fig.update_layout(hovermode="x")
    ml(
        fig,
        h=420,
        xaxis=dict(**ax(), tickformat="%H:%M\n%d/%m", hoverformat="%H:%M, %d %b %Y", showspikes=True, spikemode="across", spikesnap="data", showline=True, spikedash="dash", spikethickness=1, spikecolor="#94a3b8"),
        yaxis=dict(**ax(f"{poll_lbl}{y_unit}")),
        margin=dict(l=10, r=10, t=20, b=10)
    )
    
    with cChart:
        # Configuration for selection
        select_data = st.plotly_chart(
            fig, 
            width="stretch", 
            config={"displayModeBar": False}, 
            key="aqi_plotly_chart",
            on_select="rerun" if "Tổng quan" in str(selected_tier2) else "ignore",
            selection_mode="points" if "Tổng quan" in str(selected_tier2) else []
        )
        
        # Process selection event from Plotly (ONLY if in 'Tổng quan' view)
        if select_data and "Tổng quan" in str(selected_tier2):
            try:
                # Use attribute access for SelectionEvent object
                sel_dict = getattr(select_data, "selection", {})
                points = sel_dict.get("points", [])
                
                if points:
                    clicked_x = points[0].get("x")
                    if clicked_x:
                        curr_sel = st.session_state.get("aqi_selected_bar")
                        
                        # Toggle logic: If click same bar twice, reset. Else select new bar.
                        if curr_sel == clicked_x:
                            st.session_state["aqi_selected_bar"] = None
                            st.rerun()
                        else:
                            st.session_state["aqi_selected_bar"] = clicked_x
                            st.rerun()
            except Exception:
                pass
        
        # Legend Explanation
        bands = POLL_BANDS.get(y_col, POLL_BANDS["aqi"])
        legend_html = '<div style="margin-top:0.5rem; padding-top: 1rem; border-top: 1px dashed rgba(148,163,184,0.3); display:flex; justify-content:center; flex-wrap:wrap; gap:12px; font-size:12px;">'
        for i, (lo, hi, lbl, col) in enumerate(AQI_DEF):
            if i < len(bands):
                b_lo, b_hi = bands[i]
                val_str = f"{b_lo}-{b_hi}" if i < 5 else f"{b_lo}+"
                
                # Format as float for CO since the unit is very small
                if y_col == "co":
                    val_str = f"{float(b_lo):.1f}-{float(b_hi):.1f}" if i < 5 else f"{float(b_lo):.1f}+"
                    
                legend_html += f'<div style="display:flex; align-items:center; gap:6px; padding:4px 10px; border-radius:99px; background:{hex_rgba(col,0.1)}; border: 1px solid {hex_rgba(col, 0.4)}"><div style="width:10px; height:10px; border-radius:50%; background:{col};"></div><span style="color:{col}; font-weight:600;">{lbl} ({val_str})</span></div>'
        legend_html += '</div>'
        st.markdown(legend_html, unsafe_allow_html=True)
        
    with cRank:
        # Title of Rank
        rank_time_lbl = time_range
        if st.session_state.get("aqi_selected_bar"):
            # Format display time for the selected bar
            sel_dt = pd.to_datetime(st.session_state["aqi_selected_bar"])
            if time_range == "24h":
                rank_time_lbl = sel_dt.strftime("%H:%M, %d/%m")
            else:
                # For ranges, show the period start and end
                if (dt_end - dt_start).days >= 1:
                    rank_time_lbl = sel_dt.strftime("%d/%m") + f" - {dt_end.strftime('%d/%m')}"
                else:
                    # For sub-day ranges (like 7 days / 6h), show time range
                    rank_time_lbl = sel_dt.strftime("%d/%m %H:%M") + f" - {dt_end.strftime('%H:%M')}"

        st.markdown(f'''<div style="font-size:16px; font-family:'Be Vietnam Pro',sans-serif; font-weight:700; color:#0f172a; margin-bottom:12px;">Top 10 Ô nhiễm ({rank_time_lbl})</div>''', unsafe_allow_html=True)
        
        top_list_html = f'''<div style="display:flex; font-size:12px; font-weight:600; color:#64748b; padding-bottom: 10px; border-bottom: 2px solid rgba(148,163,184,0.1); margin-bottom: 12px; text-transform:uppercase;">
            <div style="flex:4;">Địa điểm</div>
            <div style="flex:3; text-align:center;">Trạng thái</div>
            <div style="flex:2; text-align:right;">{poll_lbl}</div>
        </div>'''
        
        # Calculate Top Locations by reading each individual unit file
        top_locations = []
        for loc_name, f_name in file_map.items():
            # Skip overall summary file
            if "Tổng quan" in loc_name or loc_name == tong_quan_lbl: continue
            
            try:
                # Load raw data for this specific location
                if time_range == "1 năm":
                    loc_df = load_tier2_year_data(folder_name, f_name)
                else:
                    loc_df = load_tier2_data(folder_name, f_name)
                if loc_df.empty or selected_poll_key not in loc_df.columns:
                    continue
                
                # Filter strictly within the time window [dt_start, dt_end)
                # This works for both individual hours (24h view) and resampled blocks (7d, 30d, 3m)
                loc_df_sub = loc_df[(loc_df["timestamp"] >= dt_start) & (loc_df["timestamp"] < dt_end)]
                if loc_df_sub.empty: continue
                
                # Calculate mean (for hourly, it's just the one value; for ranges, it's the average)
                metric_val = loc_df_sub[selected_poll_key].mean()
                top_locations.append({
                    "loc": loc_name,
                    "val": metric_val
                })
            except Exception:
                continue
            
        if top_locations:
            top_df = pd.DataFrame(top_locations).sort_values(by="val", ascending=False).head(10)
            for _, row in top_df.iterrows():
                v = row["val"]
                loc_name_full = row["loc"]
                
                lbl, c = val_meta(v, selected_poll_key)
                str_v = f"{v:.0f}" if selected_poll_key == "aqi" else f"{v:.1f}"
                
                top_list_html += f'''<div style="display:flex; align-items:center; background-color: rgba(248,250,252,0.6); padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(148,163,184,0.15);">
                     <div style="flex:4; font-size:13px; font-weight:600; color:#1e293b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-right:8px;" title="{loc_name_full}">{loc_name_full}</div>
                     <div style="flex:3; display:flex; justify-content:center;">
                         <span style="background-color: {c}; color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight:600; white-space:nowrap;">{lbl}</span>
                     </div>
                     <div style="flex:2; text-align:right; font-size:15px; font-weight:700; color:#0f172a;">{str_v}</div>
                </div>'''
        else:
            top_list_html += '''<div style="color:#64748b; font-size:13px; font-style:italic; text-align:center; padding: 20px 0;">Không có dữ liệu trong khoảng thời gian này</div>'''

        st.markdown(top_list_html, unsafe_allow_html=True)
    
    # ── FORECAST SECTION ──
    st.markdown('<hr style="margin: 1.5rem 0; border-color: rgba(148,163,184,0.15);">', unsafe_allow_html=True)
    
    df_forecast = load_forecast_data(folder_name, target_file)
    if not df_forecast.empty:
        # Lấy nhãn hiển thị từ từ điển POLLS có sẵn
        poll_label = POLLS.get(selected_poll_key, {}).get("label", selected_poll_key.upper())
        
        render_hourly_forecast(df_forecast, selected_poll_key, poll_label, selected_city, selected_tier2)

        # Forecast Header (Moved outside to ensure alignment)
        if "Tổng quan" in selected_tier2:
            location_str = selected_city
        else:
            location_str = f"{selected_city} - {selected_tier2}"

        st.markdown(f'''<div style="margin-top: 1.5rem; margin-bottom: 0.8rem;">
<div style="font-size: 19px; font-weight: 700; color: #0f172a; margin-bottom: 2px;">Dự báo {poll_label} hàng ngày</div>
<div style="font-size: 14px; color: #64748b;">Dự báo tại <span style="font-weight: 600;">{location_str}</span> trong 4 ngày tới</div>
</div>''', unsafe_allow_html=True)
        
        # Daily Forecast & Advice Side-by-Side
        cDaily, cAdvice = st.columns([1.6, 1], gap="medium")
        with cDaily:
            render_daily_forecast(df_forecast, selected_poll_key, poll_label, selected_city, selected_tier2)
        with cAdvice:
            # Get average forecast for advice
            avg_forecast = df_forecast[selected_poll_key].mean()
            # Removed spacer to align with the list start
            render_health_advice_box(avg_forecast, selected_poll_key)
            
        # ── ADVANCED ANALYSIS SECTION ──
        st.markdown('<hr style="margin: 1.5rem 0; border-color: rgba(148,163,184,0.15);">', unsafe_allow_html=True)
        st.markdown(f'''<div style="margin-bottom: 1.5rem;">
            <div style="font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">Phân tích Tương quan & So sánh</div>
        </div>''', unsafe_allow_html=True)

        col_comp, col_heat = st.columns([1.25, 1.25], gap="large")
        with col_comp:
            render_comparison_bar_chart(df, selected_poll_key, time_range, poll_lbl)
        with col_heat:
            render_correlation_heatmap(df_analysis, time_range)

        # ── REGIONAL COMPARISON SECTION (Moved to bottom) ──
        st.markdown('<hr style="margin: 1.5rem 0; border-color: rgba(148,163,184,0.15);">', unsafe_allow_html=True)
        render_regional_comparison(global_df, selected_poll_key, poll_lbl, time_range)
    else:
        st.info("Hiện chưa có dữ liệu dự báo cho khu vực này.")
        
    st.markdown('</div>', unsafe_allow_html=True)
