import base64
import pandas as pd


def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return None


AQI_DEF = [
    (0,   50,  "Tốt",        "#10b981"),
    (51,  100, "Trung bình", "#eab308"),
    (101, 150, "Kém",        "#f97316"),
    (151, 200, "Xấu",        "#ef4444"),
    (201, 300, "Rất xấu",    "#a855f7"),
    (301, 500, "Nguy hại",   "#9f1239"),
]

POLL_BANDS = {
    "aqi":   [(0, 50), (51, 100), (101, 150), (151, 200), (201, 300), (301, 500)],
    "pm2_5": [(0, 12), (12, 35), (35, 55), (55, 150), (150, 250), (250, 500)],
    "pm10":  [(0, 54), (54, 154), (154, 254), (254, 354), (354, 424), (424, 600)],
    "o3":    [(0, 106), (106, 137), (137, 166), (166, 205), (205, 392), (392, 500)],
    "no2":   [(0, 100), (100, 188), (188, 677), (677, 1220), (1220, 2348), (2348, 3000)],
    "so2":   [(0, 91), (91, 196), (196, 484), (484, 796), (796, 1582), (1582, 2000)],
    "co":    [(0, 5), (5, 11), (11, 14), (14, 17), (17, 34), (34, 50)], # mg/m3 hoặc scale nhỏ
}

def val_meta(v, poll_type="aqi"):
    if pd.isna(v):
        return "N/A", "#94a3b8"
    bands = POLL_BANDS.get(poll_type, POLL_BANDS["aqi"])
    for i, (lo, hi) in enumerate(bands):
        if v <= hi:
            idx = min(i, len(AQI_DEF) - 1)
            return AQI_DEF[idx][2], AQI_DEF[idx][3]
    return AQI_DEF[-1][2], AQI_DEF[-1][3]

def aqi_meta(v):
    for lo, hi, lbl, col in AQI_DEF:
        if v <= hi: return lbl, col
    return "Nguy hại", "#b91c1c"

def band_lbl(v):
    for lo, hi, l, _ in AQI_DEF:
        if lo <= v <= hi: return l
    return "Nguy hại"

def aqi_health_guidance(v):
    if v <= 50:
        return "Không khí tốt", "Nhóm nhạy cảm có thể sinh hoạt ngoài trời bình thường.", "#22c55e"
    if v <= 100:
        return "Mức trung bình", "Người có bệnh hô hấp nên giảm hoạt động kéo dài ngoài trời.", "#0ea5e9"
    if v <= 150:
        return "Bắt đầu ảnh hưởng", "Trẻ em, người già và người có bệnh nền nên hạn chế ra ngoài giờ cao điểm.", "#f59e0b"
    if v <= 200:
        return "Không tốt cho sức khỏe", "Nên đeo khẩu trang lọc bụi mịn và giảm vận động mạnh ngoài trời.", "#f97316"
    return "Rất xấu", "Ưu tiên ở trong nhà, đóng cửa và dùng máy lọc nếu có.", "#ef4444"

def rank_rows_html(rank_df):
    rows = []
    for i, row in enumerate(rank_df.itertuples(index=False), start=1):
        lbl, clr = aqi_meta(row.aqi)
        rows.append(
            f"<div class='iq-rank-row'>"
            f"<div class='iq-rank-no'>{i}</div>"
            f"<div><div class='iq-rank-city'>{row.city}</div><div class='iq-rank-pm'>PM2.5: {row.pm2_5:.1f} µg/m³</div></div>"
            f"<div class='iq-rank-aqi' style='color:{clr}'>{row.aqi:.0f}</div>"
            f"</div>"
        )
    return "".join(rows)

def hex_rgba(h, a=0.12):
    h = h.lstrip("#"); r,g,b = int(h[:2],16), int(h[2:4],16), int(h[4:],16)
    return f"rgba({r},{g},{b},{a})"

CITY_PALETTE = [
    "#0284c7", "#0ea5e9", "#06b6d4", "#0891b2", "#0369a1",
    "#2563eb", "#3b82f6", "#14b8a6", "#0f766e", "#22c55e",
    "#f59e0b", "#f97316", "#ef4444", "#b45309", "#1d4ed8",
]

POLLS = {
    "pm2_5": dict(label="PM2.5", unit="µg/m³", who=15,   color="#ef4444", desc="Bụi mịn < 2.5µm"),
    "pm10":  dict(label="PM10",  unit="µg/m³", who=45,   color="#f97316", desc="Bụi thô < 10µm"),
    "o3":    dict(label="O₃",    unit="µg/m³", who=100,  color="#0ea5e9", desc="Ozone mặt đất"),
    "no2":   dict(label="NO₂",   unit="µg/m³", who=25,   color="#14b8a6", desc="Khí thải giao thông"),
    "co":    dict(label="CO",    unit="µg/m³", who=4000, color="#0369a1", desc="Đốt cháy không hoàn toàn"),
    "so2":   dict(label="SO₂",   unit="µg/m³", who=40,   color="#f59e0b", desc="Công nghiệp & nhiệt điện"),
}

SLOT_CLR = {
    "Sáng (6–12h)":  "#0284c7",
    "Chiều (12–18h)":"#f59e0b",
    "Tối (18–24h)":  "#0369a1",
    "Đêm (0–6h)":    "#94a3b8",
}

PT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Be Vietnam Pro", color="#334155", size=10),
    margin=dict(l=4, r=4, t=24, b=4),
)
GC = "rgba(0,0,0,0.04)"
LC = "#e2e8f0"
TF = dict(color="#64748b", size=9)

def ml(fig, h=None, **kw):
    cfg = {**PT, **({"height": h} if h else {}), **kw}
    fig.update_layout(**cfg)
    return fig

def ax(title=""):
    r = dict(tickfont=TF, gridcolor=GC, linecolor=LC, zeroline=False)
    if title:
        r["title"] = dict(text=title, font=dict(size=9, color="#64748b"))
    return r

def chart_h(n_rows, min_h=260, row_h=24, max_h=560):
    return int(min(max_h, max(min_h, n_rows * row_h + 70)))

def fmt_delta(curr, prev, unit=""):
    if prev is None or pd.isna(prev):
        return "Không đủ dữ liệu", "#64748b"
    delta = curr - prev
    if abs(delta) < 0.05:
        return f"■ 0.0{unit}", "#64748b"
    arrow = "▲" if delta > 0 else "▼"
    color = "#dc2626" if delta > 0 else "#16a34a"
    return f"{arrow} {delta:+.1f}{unit}", color

UI_MODES = ["Premium Sky", "Bloomberg Pro", "Apple Clean"]

def set_plot_theme(mode: str):
    global PT, GC, LC, TF
    if mode == "Bloomberg Pro":
        PT = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Be Vietnam Pro", color="#334155", size=10),
            margin=dict(l=4, r=4, t=24, b=4),
        )
        GC = "rgba(51,65,85,0.09)"
        LC = "#cbd5e1"
        TF = dict(color="#475569", size=9)
    elif mode == "Apple Clean":
        PT = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Be Vietnam Pro", color="#1f2937", size=10),
            margin=dict(l=4, r=4, t=24, b=4),
        )
        GC = "rgba(148,163,184,0.15)"
        LC = "#e2e8f0"
        TF = dict(color="#64748b", size=9)
    else:
        PT = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Be Vietnam Pro", color="#334155", size=10),
            margin=dict(l=4, r=4, t=24, b=4),
        )
        GC = "rgba(0,0,0,0.04)"
        LC = "#e2e8f0"
        TF = dict(color="#64748b", size=9)

def ui_mode_css(mode: str, reduce_motion: bool) -> str:
    if mode == "Bloomberg Pro":
        css = """
        .stApp {
            background:
                linear-gradient(180deg, #eef2f7 0%, #f5f7fb 40%, #f8fafc 100%) !important;
        }
        .hdr {
            border-radius: 8px !important;
            background: linear-gradient(132deg, #0b1320 0%, #1e293b 55%, #1f3c5b 100%) !important;
            border: 1px solid rgba(148,163,184,0.35) !important;
            box-shadow: 0 14px 28px rgba(15, 23, 42, 0.22) !important;
        }
        .hdr-badge {
            border-color: rgba(251,191,36,0.46) !important;
            background: rgba(245,158,11,0.16) !important;
        }
        .kpi-box, .trend-card, .card, .ins-item, .iq-wrap {
            border-radius: 8px !important;
            border-color: #c7d3e2 !important;
            box-shadow: 0 8px 18px rgba(15,23,42,0.08) !important;
            background: rgba(255,255,255,0.96) !important;
        }
        .card:hover {
            transform: none !important;
            box-shadow: 0 10px 22px rgba(15,23,42,0.1) !important;
        }
        .stTabs [data-baseweb=\"tab\"] {
            border-radius: 6px !important;
            border: 1px solid #cbd5e1 !important;
            background: #f8fafc !important;
            color: #334155 !important;
        }
        .stTabs [aria-selected=\"true\"] {
            background: linear-gradient(150deg, #0f172a, #1e293b) !important;
            color: #f8fafc !important;
            border-color: #334155 !important;
            box-shadow: 0 6px 14px rgba(15,23,42,0.24) !important;
        }
        .ftr {
            border-radius: 8px !important;
            background: linear-gradient(140deg, #0f172a 0%, #1e293b 100%) !important;
        }
        section[data-testid=\"stSidebar\"] {
            background:
                linear-gradient(180deg, #ffffff 0%, #f3f6fa 100%) !important;
        }
        """
    elif mode == "Apple Clean":
        css = """
        .stApp {
            background:
                radial-gradient(900px 300px at 15% -10%, rgba(2,132,199,0.09), transparent 70%),
                radial-gradient(720px 260px at 95% 0%, rgba(14,165,233,0.08), transparent 65%),
                linear-gradient(180deg, #f8fbff 0%, #f4f8fd 55%, #f8fafc 100%) !important;
        }
        .hdr {
            background: rgba(255,255,255,0.8) !important;
            border: 1px solid rgba(148,163,184,0.25) !important;
            box-shadow: 0 16px 34px rgba(15, 23, 42, 0.1) !important;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }
        .hdr-school, .hdr-sub, .hdr-stat-lbl, .hdr-badge-lbl {
            color: #64748b !important;
        }
        .hdr-title, .hdr-stat-val {
            color: #0f172a !important;
        }
        .hdr-badge {
            background: #f8fafc !important;
            border: 1px solid #dbeafe !important;
        }
        .kpi-box, .trend-card, .card, .ins-item, .iq-wrap {
            border-radius: 16px !important;
            border-color: rgba(148,163,184,0.2) !important;
            box-shadow: 0 16px 34px rgba(15,23,42,0.08) !important;
            background: rgba(255,255,255,0.88) !important;
        }
        .stTabs [data-baseweb=\"tab\"] {
            border-radius: 999px !important;
            border: 1px solid #dbeafe !important;
            background: rgba(255,255,255,0.85) !important;
        }
        .stTabs [aria-selected=\"true\"] {
            background: linear-gradient(140deg, #0ea5e9 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            border-color: transparent !important;
        }
        section[data-testid=\"stSidebar\"] {
            background:
                linear-gradient(180deg, #ffffff 0%, #f8fbff 60%, #f5f8fd 100%) !important;
        }
        """
    else:
        css = """
        .stApp {
            background:
                radial-gradient(1200px 420px at 8% -10%, rgba(14,165,233,0.18), transparent 65%),
                radial-gradient(920px 380px at 92% 3%, rgba(245,158,11,0.14), transparent 62%),
                linear-gradient(180deg, #eef4ff 0%, #f3f7fb 45%, #f8fbff 100%) !important;
        }
        """

    if reduce_motion:
        css += """
        *, *::before, *::after {
            animation: none !important;
            transition: none !important;
            scroll-behavior: auto !important;
        }
        """

    return f"<style>{css}</style>"

# ═══════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════
