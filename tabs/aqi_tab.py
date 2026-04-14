import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.helpers import AQI_DEF, POLLS, aqi_meta, ml, ax, chart_h, PT, GC, LC, TF, hex_rgba, POLL_BANDS, val_meta

# Bảng map Tên thành phố giao diện -> tên thư mục thực tế
CITY_FOLDERS = {
    "An Giang": "an_giang", "Bắc Ninh": "bac_ninh", "Cà Mau": "ca_mau", "Cần Thơ": "can_tho",
    "Cao Bằng": "cao_bang", "Đà Nẵng": "da_nang", "Đắk Lắk": "dak_lak", "Điện Biên": "dien_bien",
    "Đồng Nai": "dong_nai", "Đồng Tháp": "dong_thap", "Gia Lai": "gia_lai", "Hà Nội": "ha_noi",
    "Hà Tĩnh": "ha_tinh", "Hải Phòng": "hai_phong", "Thành phố Hồ Chí Minh": "ho_chi_minh",
    "Huế": "hue", "Hưng Yên": "hung_yen", "Khánh Hòa": "khanh_hoa", "Lai Châu": "lai_chau",
    "Lâm Đồng": "lam_dong", "Lạng Sơn": "lang_son", "Lào Cai": "lao_cai", "Nghệ An": "nghe_an",
    "Ninh Bình": "ninh_binh", "Phú Thọ": "phu_tho", "Quảng Ngãi": "quang_ngai", "Quảng Ninh": "quang_ninh",
    "Quảng Trị": "quang_tri", "Sơn La": "son_la", "Tây Ninh": "tay_ninh", "Thái Nguyên": "thai_nguyen",
}

@st.cache_data(ttl=3600*24, show_spinner=False)
def get_location_map(dir_path):
    mapping = {}
    if not os.path.exists(dir_path):
        return mapping
    for f in os.listdir(dir_path):
        if f.endswith(".csv") and f != "all.csv":
            clean_name = f.replace(".csv", "")
            try:
                # Read just the first row, only the 'location' column to be extra fast
                df_loc = pd.read_csv(os.path.join(dir_path, f), usecols=["location"], nrows=1)
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
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "..", "data", "aqi", city_folder, filename)
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(file_path)
        if df.empty: return df
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp", "aqi"])
        df = df.sort_values("timestamp")
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_forecast_data(city_folder, filename):
    base_dir = os.path.dirname(__file__)
    # Try exact match first
    file_path = os.path.join(base_dir, "..", "data", "forecast", city_folder, filename)
    
    if not os.path.exists(file_path):
        # Mismatch logic: Forecast files are often normalized (lowercase, no accents, underscores)
        # We try to normalize the filename to match.
        import re
        s = filename.replace(".csv", "")
        # Standard normalization used in get_forecast.py
        s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ]', 'a', s)
        s = re.sub(r'[èéẹẻẽêềếệểễÈÉẸẺẼÊỀẾỆỂỄ]', 'e', s)
        s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'o', s)
        s = re.sub(r'[ìíịỉĩÌÍỊỈĨ]', 'i', s)
        s = re.sub(r'[ùúụủũưừứựửữÙÚỤỦŨƯỪỨỰỬỮ]', 'u', s)
        s = re.sub(r'[ỳýỵỷỹỲÝỴỶỸ]', 'y', s)
        s = re.sub(r'[đĐ]', 'd', s)
        s = re.sub(r'[^a-zA-Z0-9\s]', '', s).strip().lower()
        normalized_filename = re.sub(r'\s+', '_', s) + ".csv"
        
        file_path = os.path.join(base_dir, "..", "data", "forecast", city_folder, normalized_filename)

    if not os.path.exists(file_path):
        return pd.DataFrame()
        
    try:
        df = pd.read_csv(file_path)
        if df.empty: return df
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp", "aqi"])
        # Deduplicate by averaging values for the same timestamp
        df = df.groupby("timestamp").mean(numeric_only=True).reset_index()
        df = df.sort_values("timestamp")
        return df
    except Exception:
        return pd.DataFrame()

def render_hourly_forecast(df_forecast, poll_key, poll_label, city_name, unit_name):
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
            day_label = ts.strftime("Th %w") if ts.weekday() != 6 else "CN"
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
    if df_forecast.empty:
        return
        
    # Group by date
    df_forecast["date"] = df_forecast["timestamp"].dt.date
    daily = df_forecast.groupby("date").agg({poll_key: "mean"}).reset_index()
    
    # Filter for today and future
    today = pd.Timestamp.now().date()
    daily = daily[daily["date"] >= today].head(7)
    
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
        
        container_html += f'''<div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; background: {bg_row}; border-bottom: 1px solid #f1f5f9;">
<div style="font-weight: 600; color: #334155; width: 100px;">{day_pref}</div>
<div style="flex: 1; display: flex; align-items: center; justify-content: center;">
<div style="background: {col}; color: white; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 14px; min-width: 50px; text-align: center;">{val:.0f}</div>
<div style="margin-left: 12px; font-size: 13px; font-weight: 500; color: {col};">{lbl}</div>
</div>
<div style="width: 100px; text-align: right; color: #64748b; font-size: 12px;">{d.strftime("%d/%m/%Y")}</div>
</div>'''
        
    container_html += '</div>'
    st.markdown(container_html, unsafe_allow_html=True)

def render_health_advice_box(avg_val, poll_type):
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
<div style="height: 100%; min-height: 380px; background-color: {hex_rgba(clr, 0.08)}; border: 1.5px solid {hex_rgba(clr, 0.3)}; border-radius: 12px; padding: 24px; display: flex; flex-direction: column;">
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

def render(global_df):
    ctx = st.session_state.get("dashboard_context", {})
    if ctx: globals().update(ctx)
    
    st.markdown('<div class="card" style="padding: 1.5rem; margin-bottom: 1rem;">'
                '<div class="card-title" style="margin-bottom: 4px;"><span class="q-tag">Lịch Sử</span>Phân tích Chuỗi thời gian & Xu hướng</div>'
                '<div class="card-sub" style="margin-bottom: 16px;">Theo dõi dao động nồng độ chất ô nhiễm tại một khu vực cụ thể qua các mốc thời gian.</div>', 
                unsafe_allow_html=True)    
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
            st.rerun()

    # Locate Tier 2 units dynamically
    folder_name = CITY_FOLDERS.get(selected_city, "ho_chi_minh")
    base_dir = os.path.dirname(__file__)
    dir_path = os.path.join(base_dir, "..", "data", "aqi", folder_name)
    tong_quan_lbl = f"Tổng quan ({selected_city})"
    tier2_options = [tong_quan_lbl]
    file_map = {tong_quan_lbl: "all.csv"}
    
    if os.path.exists(dir_path):
        loc_mapping = get_location_map(dir_path)
        for f in os.listdir(dir_path):
            if f.endswith(".csv") and f != "all.csv":
                clean_name = f.replace(".csv", "")
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
        tr_opts = ["24h", "7 ngày", "30 ngày", "3 tháng", "6 tháng"]
        idx_tr = tr_opts.index(st.session_state["aqi_time_range"]) if st.session_state["aqi_time_range"] in tr_opts else 1
        time_range = st.selectbox("Thời gian", tr_opts, index=idx_tr, key="aqi_time_select")
        if time_range != st.session_state["aqi_time_range"]:
            st.session_state["aqi_time_range"] = time_range
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
            st.rerun()

    # Load and process data
    target_file = file_map.get(selected_tier2, "all.csv")
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
        "6 tháng": pd.Timedelta(days=180)
    }
    
    min_d = max_d - delta_map[time_range]
    df_sub = df[df["timestamp"] >= min_d].copy()
    
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
    # Tối giản số điểm dữ liệu cho view lớn để tránh bị chèn ép biểu đồ
    if len(df_sub) > 50:
        rule_map = {
            "7 ngày": "6h",
            "30 ngày": "1D",
            "3 tháng": "3D",
            "6 tháng": "7D"
        }
        rule = rule_map.get(time_range)
        if rule:
            if chart_type == "Đường (Spline)":
                # Nhóm dữ liệu để vẽ Band bao phủ (Envelope) Min/Max và đường trung tâm (Mean)
                grouped = df_sub.set_index("timestamp").resample(rule)[y_col]
                
                df_mean = grouped.mean().dropna().reset_index()
                df_max_env = grouped.max().dropna().reset_index()
                df_min_env = grouped.min().dropna().reset_index()
                
                # Biến df_sub thành bảng chứa điểm trung bình để vẽ line chính
                df_sub = df_mean
                # Add columns for envelope hover tooltips
                df_sub["env_max"] = df_max_env[y_col].values
                df_sub["env_min"] = df_min_env[y_col].values
                has_envelope = True
            else:
                # Bar Chart vần trục thời gian chia khoảng Đều (Uniform) để các cột được tính toán chiều ngang to rõ ràng
                # Ta vẫn dùng .max() để nhặt ra mốc ô nhiễm nặng nhất, không lo bị chà phẳng
                df_sub = df_sub.set_index("timestamp").resample(rule)[[y_col]].max().dropna().reset_index()

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
            score = get_color_score(val)
            score = max(0, min(len(base_colors)-1.0, score))
            idx = int(score)
            if idx >= len(base_colors) - 1: return base_colors[-1]
            c1, c2 = base_colors[idx], base_colors[idx+1]
            t = score - idx
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
                
                # Biểu đồ PCHIP mượt mà, kẹp chặt đỉnh và đáy để không miss tín hiệu
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
        fig.add_trace(go.Bar(
            x=df_sub["timestamp"],
            y=df_sub[y_col],
            marker_color=df_sub["clr"],
            marker_line=dict(width=1, color="#fff"),
            opacity=0.9,
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
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="aqi_plotly_chart")
        
        # Legend Explanation
        bands = POLL_BANDS.get(y_col, POLL_BANDS["aqi"])
        legend_html = '<div style="margin-top:0.5rem; padding-top: 1rem; border-top: 1px dashed rgba(148,163,184,0.3); display:flex; justify-content:center; flex-wrap:wrap; gap:12px; font-size:12px;">'
        for i, (lo, hi, lbl, col) in enumerate(AQI_DEF):
            if i < len(bands):
                b_lo, b_hi = bands[i]
                val_str = f"{b_lo}-{b_hi}" if i < 5 else f"{b_lo}+"
                
                # Format số thực cho CO vì đơn vị rất nhỏ
                if y_col == "co":
                    val_str = f"{float(b_lo):.1f}-{float(b_hi):.1f}" if i < 5 else f"{float(b_lo):.1f}+"
                    
                legend_html += f'<div style="display:flex; align-items:center; gap:6px; padding:4px 10px; border-radius:99px; background:{hex_rgba(col,0.1)}; border: 1px solid {hex_rgba(col, 0.4)}"><div style="width:10px; height:10px; border-radius:50%; background:{col};"></div><span style="color:{col}; font-weight:600;">{lbl} ({val_str})</span></div>'
        legend_html += '</div>'
        st.markdown(legend_html, unsafe_allow_html=True)
        
    with cRank:
        # Title of Rank
        st.markdown(f'''<div style="font-size:16px; font-family:'Be Vietnam Pro',sans-serif; font-weight:700; color:#0f172a; margin-bottom:12px;">Top 8 Ô nhiễm ({time_range})</div>''', unsafe_allow_html=True)
        
        top_list_html = f'''<div style="display:flex; font-size:12px; font-weight:600; color:#64748b; padding-bottom: 10px; border-bottom: 2px solid rgba(148,163,184,0.1); margin-bottom: 12px; text-transform:uppercase;">
            <div style="flex:4;">Địa điểm</div>
            <div style="flex:3; text-align:center;">Trạng thái</div>
            <div style="flex:2; text-align:right;">{poll_lbl}</div>
        </div>'''
        
        # calculate Top 10 locations
        top_locations = []
        for loc_name, f_name in file_map.items():
            if "Tổng quan" in loc_name or loc_name == tong_quan_lbl: continue
            
            try:
                loc_df = load_tier2_data(folder_name, f_name)
                if loc_df.empty or selected_poll_key not in loc_df.columns:
                    continue
                
                loc_df_sub = loc_df[loc_df["timestamp"] >= min_d]
                if loc_df_sub.empty: continue
                
                # Use mean value over the selected time range
                metric_val = loc_df_sub[selected_poll_key].mean()
                top_locations.append({
                    "loc": loc_name,
                    "val": metric_val
                })
            except Exception:
                continue
            
        if top_locations:
            top_df = pd.DataFrame(top_locations).sort_values(by="val", ascending=False).head(8)
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
<div style="font-size: 14px; color: #64748b;">Dự báo tại <span style="font-weight: 600;">{location_str}</span> trong 7 ngày tới</div>
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
    else:
        st.info("Hiện chưa có dữ liệu dự báo cho khu vực này.")
        
    st.markdown('</div>', unsafe_allow_html=True)
