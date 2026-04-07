import streamlit as st


def render_header(state, logo_html):
    globals().update(state)
    st.markdown(f"""
    <div class="hdr">
      <div class="hdr-left">
        <div class="hdr-logo">{logo_html}</div>
        <div>
          <div class="hdr-school">ĐẠI HỌC KHOA HỌC TỰ NHIÊN, ĐHQG–HCM &nbsp;·&nbsp; KHOA CNTT &nbsp;·&nbsp; Trực quan hóa Dữ liệu</div>
          <div class="hdr-title">Phân tích Chỉ số Chất lượng Không khí tại Việt Nam</div>
          <div class="hdr-sub">GVHD: Bùi Tiến Lên &nbsp;·&nbsp; Lớp CQ2023/24 &nbsp;·&nbsp; Nhóm 8 &nbsp;·&nbsp; TP.HCM – 2026</div>
        </div>
      </div>
      <div class="hdr-right">
        <div class="hdr-stat">
          <div class="hdr-stat-val">{len(sel)}</div>
          <div class="hdr-stat-lbl">Khu vực</div>
        </div>
        <div class="hdr-stat">
          <div class="hdr-stat-val">{len(df):,}</div>
          <div class="hdr-stat-lbl">Bản ghi</div>
        </div>
        <div class="hdr-stat">
          <div class="hdr-stat-val">{s_d.strftime('%d/%m/%y')} → {e_d.strftime('%d/%m/%y')}</div>
          <div class="hdr-stat-lbl">Thời gian</div>
        </div>
        <div class="hdr-badge">
          <div class="hdr-badge-val" style="color:{_col}">{avg_aqi}</div>
          <div class="hdr-badge-lbl">AQI · {_lbl}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

