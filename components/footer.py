from datetime import datetime

import streamlit as st


def render_footer():
    st.markdown('</div>', unsafe_allow_html=True)

    # ── FOOTER ──
    members = [
            "23120283 · Phạm Quốc Khánh",
            "23120301 · Phạm Thành Nam",
            "23120318 · Trương Quang Phát",
            "23120329 · Châu Huỳnh Phúc",
            "23120334 · Huỳnh Tấn Phước",
    ]
    member_chips = "".join([f'<span class="ftr-member">{m}</span>' for m in members])

    st.markdown(f"""
    <div class="ftr">
      <div class="ftr-txt">Vietnam AQI Analytics · ĐH Khoa học Tự nhiên TP.HCM · GVHD: Bùi Tiến Lên · {datetime.now().strftime('%d/%m/%Y')}</div>
        <div class="ftr-marquee">
            <div class="ftr-track">
                {member_chips}{member_chips}
            </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
