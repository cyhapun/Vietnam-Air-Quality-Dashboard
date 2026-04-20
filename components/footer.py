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
<div class="pro-ftr-col-title">Giám sát Chất lượng Không khí</div>
<ul class="pro-ftr-list">
<li><span>Dữ liệu AQI Thời gian thực:</span> Hiển thị chỉ số AQI hiện tại của các tỉnh thành lớn</li>
<li><span>Chi tiết Chất ô nhiễm:</span> PM2.5, PM10, O3, NO2, SO2, CO</li>
<li><span>Phân tích Lịch sử:</span> Biểu đồ chuỗi thời gian có khả năng tương tác</li>
<li><span>Tính toán Chỉ số AQI:</span> Dựa trên hệ thống tiêu chuẩn của EPA</li>
</ul>
</div>
<div class="pro-ftr-col">
<div class="pro-ftr-col-title">Trực quan hóa Tương tác</div>
<ul class="pro-ftr-list">
<li><span>Bản đồ Việt Nam:</span> Bản đồ phân mức (Choropleth) theo tỉnh thành</li>
<li><span>Biểu đồ Chuỗi thời gian:</span> Phân tích xu hướng theo giờ, ngày và tháng</li>
<li><span>Công cụ Đối chiếu:</span> So sánh giữa các thành phố & các mốc thời gian</li>
<li><span>Bản đồ Nhiệt (Heatmaps):</span> Trực quan hóa mô hình phân bố ô nhiễm</li>
</ul>
</div>
<div class="pro-ftr-col">
<div class="pro-ftr-col-title">Phân tích bằng Học máy (ML)</div>
<ul class="pro-ftr-list">
<li><span>Dự đoán AQI:</span> Ứng dụng thuật toán RandomForestRegressor</li>
<li><span>Dự báo Xu hướng:</span> Dự báo chất lượng không khí trong 24 giờ tới</li>
<li><span>Phân tích Tương quan:</span> Đánh giá tác động của thời tiết đến mức độ ô nhiễm</li>
<li><span>Diễn giải Mô hình:</span> Sử dụng giá trị SHAP để giải thích các dự đoán</li>
</ul>
</div>
<div class="pro-ftr-col">
<div class="pro-ftr-col-title">Tích hợp Dữ liệu Thời tiết</div>
<ul class="pro-ftr-list">
<li><span>Thông tin Thời tiết:</span> Nhiệt độ, độ ẩm, sức gió và lượng mưa</li>
<li><span>Phân tích Tác động:</span> Mối liên hệ giữa thời tiết và chất lượng không khí</li>
</ul>
<div class="pro-ftr-col-title" style="margin-top: 16px;">Tính năng Nâng cao</div>
<ul class="pro-ftr-list">
<li><span>Hỗ trợ Truy cập:</span> Chế độ hiển thị dành cho người mù màu</li>
<li><span>Trích xuất Dữ liệu:</span> Hỗ trợ lưu trữ dưới định dạng CSV</li>
<li><span>Hệ thống Tối ưu:</span> Tự động làm mới & Giao diện tương thích đa thiết bị</li>
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
<div class="pro-ftr-team-label">Đội ngũ Phát triển</div>
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