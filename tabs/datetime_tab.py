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
    "Thanh Hóa": "thanh_hoa", "Tuyên Quang": "tuyen_quang", "Vĩnh Long": "vinh_long"
}

@st.cache_data(ttl=3600, show_spinner=False)
def load_tier2_data(city_folder, filename):
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

def render(global_df):
    ctx = st.session_state.get("dashboard_context", {})
    if ctx: globals().update(ctx)
    
    st.markdown('<div class="card" style="padding: 1.5rem; margin-bottom: 1rem;">'
                '<div class="card-title" style="margin-bottom: 4px;"><span class="q-tag">Lịch Sử</span>Phân tích Chuỗi thời gian & Xu hướng</div>'
                '<div class="card-sub" style="margin-bottom: 16px;">Theo dõi dao động nồng độ chất ô nhiễm tại một khu vực cụ thể qua các mốc thời gian.</div>', 
                unsafe_allow_html=True)    
    cities = list(CITY_FOLDERS.keys())
    
    # Initialize State
    if "dt_selected_city" not in st.session_state:
        st.session_state["dt_selected_city"] = "Thành phố Hồ Chí Minh"
    if "dt_selected_tier2" not in st.session_state:
        st.session_state["dt_selected_tier2"] = "Tổng quan (Thành phố Hồ Chí Minh)"
    if "dt_chart_type" not in st.session_state:
        st.session_state["dt_chart_type"] = "Đường (Spline)"
    if "dt_time_range" not in st.session_state:
        st.session_state["dt_time_range"] = "24h"
    if "dt_pollutant" not in st.session_state:
        st.session_state["dt_pollutant"] = "aqi"
        
    c1, c2, c3, c4, c5 = st.columns([1.6, 1.6, 1.2, 1.0, 1.0])
    
    with c1:
        # Safe fallback for index
        idx_city = 0
        if st.session_state["dt_selected_city"] in cities:
            idx_city = cities.index(st.session_state["dt_selected_city"])
            
        selected_city = st.selectbox(
            "Thành phố / Tỉnh", 
            options=cities, 
            index=idx_city,
            key="_city_select"
        )
        if selected_city != st.session_state["dt_selected_city"]:
            st.session_state["dt_selected_city"] = selected_city
            st.session_state["dt_selected_tier2"] = f"Tổng quan ({selected_city})"
            st.rerun()

    # Locate Tier 2 units dynamically
    folder_name = CITY_FOLDERS.get(selected_city, "ho_chi_minh")
    base_dir = os.path.dirname(__file__)
    dir_path = os.path.join(base_dir, "..", "data", "aqi", folder_name)
    tong_quan_lbl = f"Tổng quan ({selected_city})"
    tier2_options = [tong_quan_lbl]
    file_map = {tong_quan_lbl: "all.parquet"}
    
    if os.path.exists(dir_path):
        files = os.listdir(dir_path)
        for f in files:
            if f.endswith(".parquet") and f != "all.parquet":
                clean_name = f.replace(".parquet", "")
                tier2_options.append(clean_name)
                file_map[clean_name] = f
                
    tier2_options.sort() # Optional: sort alphabetical
    
    # Ensure "Tổng quan" is always first
    if tong_quan_lbl in tier2_options:
        tier2_options.remove(tong_quan_lbl)
        tier2_options.insert(0, tong_quan_lbl)
        
    # Reset tier2 selection if not found
    if st.session_state["dt_selected_tier2"] not in tier2_options:
        st.session_state["dt_selected_tier2"] = tier2_options[0]

    with c2:
        selected_tier2 = st.selectbox(
            "Đơn vị (Huyện/Xã/Phường)", 
            options=tier2_options,
            index=tier2_options.index(st.session_state["dt_selected_tier2"]),
            key="_tier2_select"
        )
        if selected_tier2 != st.session_state["dt_selected_tier2"]:
            st.session_state["dt_selected_tier2"] = selected_tier2
            st.rerun()

    with c3:
        # Use native segmented_control with Material Icons style if supported
        try:
            chart_opts = [":material/show_chart:", ":material/bar_chart:"]
            sel_default = ":material/show_chart:" if st.session_state["dt_chart_type"] == "Đường (Spline)" else ":material/bar_chart:"
            
            # Using st.segmented_control to show only icons
            raw_sel = st.segmented_control(
                "Loại biểu đồ", 
                options=chart_opts, 
                default=sel_default
            )
            
            # Fallback for deselection
            if raw_sel is None:
                chart_type = st.session_state["dt_chart_type"]
            else:
                chart_type = "Đường (Spline)" if raw_sel == ":material/show_chart:" else "Cột (Bar)"
                
        except AttributeError:
            # Fallback for older Streamlit versions
            chart_type = st.radio("Loại biểu đồ", ["Đường (Spline)", "Cột (Bar)"], index=0 if st.session_state["dt_chart_type"] == "Đường (Spline)" else 1, horizontal=True)

        if chart_type != st.session_state["dt_chart_type"]:
            st.session_state["dt_chart_type"] = chart_type
            st.rerun()

    with c4:
        tr_opts = ["24h", "7 ngày", "30 ngày", "3 tháng", "6 tháng", "1 năm"]
        idx_tr = tr_opts.index(st.session_state["dt_time_range"]) if st.session_state["dt_time_range"] in tr_opts else 1
        time_range = st.selectbox("Thời gian", tr_opts, index=idx_tr)
        if time_range != st.session_state["dt_time_range"]:
            st.session_state["dt_time_range"] = time_range
            st.rerun()

    with c5:
        polls_keys = ["aqi"] + list(POLLS.keys())
        
        def fmt_poll(k):
            if k == "aqi": return "AQI (US)"
            return POLLS[k]["label"]
            
        curr_pol = st.session_state.get("dt_pollutant", "aqi")
        if curr_pol not in polls_keys:
            curr_pol = "aqi"
            
        selected_poll = st.selectbox(
            "Thông số", 
            options=polls_keys, 
            index=polls_keys.index(curr_pol), 
            format_func=fmt_poll
        )
        
        poll_lbl = fmt_poll(selected_poll)
        selected_poll_key = selected_poll
        
        if selected_poll != curr_pol:
            st.session_state["dt_pollutant"] = selected_poll
            st.rerun()

    # Load and process data
    target_file = file_map.get(selected_tier2, "all.parquet")
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
        "6 tháng": pd.Timedelta(days=180),
        "1 năm": pd.Timedelta(days=365)
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
    cT1, cT2 = st.columns([1.2, 1], gap="small")
    
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
    # Tối giản số điểm dữ liệu cho view lớn để tránh bị chèn ép biểu đồ
    if len(df_sub) > 50:
        rule_map = {
            "7 ngày": "6h",
            "30 ngày": "1D",
            "3 tháng": "3D",
            "6 tháng": "7D",
            "1 năm": "14D"
        }
        rule = rule_map.get(time_range)
        if rule:
            df_sub = df_sub.set_index("timestamp").resample(rule).mean(numeric_only=True).dropna().reset_index()

    # Prepare array colors & labels for Plotly based on selected pollutant scale
    df_sub["clr"] = df_sub[y_col].apply(lambda x: val_meta(x, y_col)[1])
    df_sub["lbl"] = df_sub[y_col].apply(lambda x: val_meta(x, y_col)[0])
    
    # Calculate overall average color for the line chart
    avg_val = df_sub[y_col].mean()
    _, avg_color = val_meta(avg_val, y_col)

    fig = go.Figure()
    if chart_type == "Đường (Spline)":
        fig.add_trace(go.Scatter(
            x=df_sub["timestamp"],
            y=df_sub[y_col],
            mode="lines+markers",
            line=dict(color=avg_color, width=5.0, shape="spline", smoothing=1),
            marker=dict(size=7, color=df_sub["clr"], line=dict(width=1, color="#fff")),
            hovertemplate=(
                "<b>%{x|%H:%M, %d %b %Y}</b><br>"
                f"{poll_lbl}: <b>%{{y:.1f}}{y_unit}</b><br>"
                "Phân loại: %{customdata[0]}<extra></extra>"
            ),
            customdata=df_sub[["lbl"]]
        ))
    else:
        fig.add_trace(go.Bar(
            x=df_sub["timestamp"],
            y=df_sub[y_col],
            marker_color=df_sub["clr"],
            marker_line=dict(width=1, color="#fff"),
            opacity=0.9,
            hovertemplate=(
                "<b>%{x|%H:%M, %d %b %Y}</b><br>"
                f"{poll_lbl}: <b>%{{y:.1f}}{y_unit}</b><br>"
                "Phân loại: %{customdata[0]}<extra></extra>"
            ),
            customdata=df_sub[["lbl"]]
        ))

    ml(
        fig,
        h=420,
        xaxis=dict(**ax(), tickformat="%H:%M\n%d/%m", hoverformat="%H:%M"),
        yaxis=dict(**ax(f"{poll_lbl}{y_unit}")),
        margin=dict(l=10, r=10, t=20, b=10)
    )
    
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    
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
    
    st.markdown('</div>', unsafe_allow_html=True)
