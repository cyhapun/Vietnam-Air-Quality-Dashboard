from datetime import datetime
import streamlit as st

def render_footer():
    """
    Renders a comprehensive SaaS Mega-Footer including key features and team info.
    """
    members = [
        "23120283 · Phạm Quốc Khánh",
        "23120301 · Phạm Thành Nam",
        "23120318 · Trương Quang Phát",
        "23120329 · Châu Huỳnh Phúc",
        "23120334 · Huỳnh Tấn Phước",
    ]
    
    member_chips = "".join([f'<div class="pro-ftr-chip"><span class="pro-ftr-dot"></span>{m}</div>' for m in members])

    # Xóa toàn bộ lùi đầu dòng để Streamlit render dưới dạng HTML thay vì Code Block
    html_content = f"""
<div class="pro-ftr-wrapper">
<div class="pro-ftr-container">
<div class="pro-ftr-features-grid">
<div class="pro-ftr-col">
<div class="pro-ftr-col-title">Comprehensive Air Quality</div>
<ul class="pro-ftr-list">
<li><span>Real-time AQI Data:</span> Display current AQI for major cities</li>
<li><span>Pollutant Breakdown:</span> PM2.5, PM10, O3, NO2, SO2, CO</li>
<li><span>Historical Analysis:</span> Interactive time-series charts</li>
<li><span>AQI Calculation:</span> Based on EPA standards</li>
</ul>
</div>
<div class="pro-ftr-col">
<div class="pro-ftr-col-title">Interactive Visualization</div>
<ul class="pro-ftr-list">
<li><span>Vietnam Map:</span> Choropleth map by province</li>
<li><span>Time-series Charts:</span> Hourly, daily, monthly analysis</li>
<li><span>Comparison Tools:</span> Cross-city & time periods</li>
<li><span>Heatmaps:</span> Pollution patterns visualizer</li>
</ul>
</div>
<div class="pro-ftr-col">
<div class="pro-ftr-col-title">Machine Learning Insights</div>
<ul class="pro-ftr-list">
<li><span>AQI Prediction:</span> Real-time RandomForestRegressor</li>
<li><span>Trend Forecasting:</span> 24-hour forecasts</li>
<li><span>Causality Analysis:</span> Weather vs Pollution relations</li>
<li><span>Model Explainability:</span> SHAP values prediction</li>
</ul>
</div>
<div class="pro-ftr-col">
<div class="pro-ftr-col-title">Weather Integration</div>
<ul class="pro-ftr-list">
<li><span>Weather Data:</span> Temp, humidity, wind, precipitation</li>
<li><span>Impact Analysis:</span> Weather effects on air quality</li>
</ul>
<div class="pro-ftr-col-title" style="margin-top: 16px;">Advanced Features</div>
<ul class="pro-ftr-list">
<li><span>Accessibility:</span> Colorblind Mode</li>
<li><span>Data Export:</span> CSV formats</li>
<li><span>System:</span> Auto-refresh & Responsive Design</li>
</ul>
</div>
</div>
<div class="pro-ftr-divider-main"></div>
<div class="pro-ftr-bottom">
<div class="pro-ftr-info">
<div class="pro-ftr-brand">
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
<span>Vietnam AQI Analytics</span>
</div>
<div class="pro-ftr-divider"></div>
<div class="pro-ftr-text">ĐH Khoa học Tự nhiên TP.HCM</div>
<div class="pro-ftr-divider"></div>
<div class="pro-ftr-text">GVHD: Bùi Tiến Lên</div>
<div class="pro-ftr-divider"></div>
</div>
<div class="pro-ftr-team-box">
<div class="pro-ftr-team-label">Dev Team</div>
<div class="pro-ftr-marquee">
<div class="pro-ftr-track">
{member_chips}{member_chips}
</div>
</div>
</div>
</div>
</div>
</div>
"""
    st.markdown(html_content, unsafe_allow_html=True)