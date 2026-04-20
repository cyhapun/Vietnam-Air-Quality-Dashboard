import streamlit as st


def render_header(state, logo_html):
    globals().update(state)
    colorblind_on = bool(st.session_state.get("colorblind_mode", False))
    header_class = "hdr hdr-cb" if colorblind_on else "hdr"
    toggle_href = "?cb=toggle"
    colorblind_badge = (
      f"<a class='hdr-mode-link' href='{toggle_href}' target='_self' title='Bấm để bật/tắt chế độ mù màu'><div class='hdr-mode hdr-mode-on'><span class='hdr-mode-mark'>■</span>Chế độ mù màu: Bật</div></a>"
        if colorblind_on
      else f"<a class='hdr-mode-link' href='{toggle_href}' target='_self' title='Bấm để bật/tắt chế độ mù màu'><div class='hdr-mode'><span class='hdr-mode-mark'>●</span>Chế độ mù màu: Tắt</div></a>"
    )

    st.markdown(
        f"""
    <div class="{header_class}">
      <div class="hdr-left">
        <div class="hdr-logo">{logo_html}</div>
        <div>
          <div class="hdr-school">ĐẠI HỌC KHOA HỌC TỰ NHIÊN, ĐHQG–HCM &nbsp;·&nbsp; KHOA CNTT &nbsp;·&nbsp; Trực quan hóa Dữ liệu</div>
          <div class="hdr-title">Phân tích Chỉ số Chất lượng Không khí tại Việt Nam</div>
          <div class="hdr-sub">GVHD: Bùi Tiến Lên &nbsp;·&nbsp; Lớp CQ2023/24 &nbsp;·&nbsp; Nhóm 8 &nbsp;·&nbsp; TP.HCM – 2026</div>
          {colorblind_badge}
        </div>
      </div>
      <div class="hdr-right">
        <div class="hdr-stat">
          <div class="hdr-stat-val">{len(sel)}</div>
          <div class="hdr-stat-lbl">Khu vực</div>
        </div>
        <div class="hdr-stat">
          <div class="hdr-stat-val">Từ {s_d.strftime('%d/%m/%y')} đến {e_d.strftime('%d/%m/%y')}</div>
          <div class="hdr-stat-lbl">Thời gian</div>
        </div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

