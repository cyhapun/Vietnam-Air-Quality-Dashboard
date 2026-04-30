import streamlit as st

from utils.helpers import UI_MODES, aqi_meta, apply_colorblind, set_plot_theme, ui_mode_css

TAB_ITEMS = [
    (
        "overview",
        """<svg viewBox="0 0 24 24" fill="none"><path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5.5v-6.5h-5V22H4a1 1 0 0 1-1-1v-10.5Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>""",
        "Tổng quan",
    ),
    (
        "aqi",
        """<svg viewBox="0 0 24 24" fill="none"><path d="M4 16c2-1.5 4-1.5 6 0m2-3c2-1.5 4-1.5 6 0m-14 6c2-1.5 4-1.5 6 0m2 0c2-1.5 4-1.5 6 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="6" cy="7" r="2" fill="currentColor"/></svg>""",
        "AQI",
    ),
    (
        "weather",
        """<svg viewBox="0 0 24 24" fill="none"><path d="M6 18h11a4 4 0 1 0-.7-7.94A6 6 0 0 0 5.2 9.4 4.2 4.2 0 0 0 6 18Z" stroke="currentColor" stroke-width="1.8"/><circle cx="18.5" cy="6.5" r="2.5" stroke="currentColor" stroke-width="1.6"/></svg>""",
        "Thời tiết",
    ),
    (
        "interaction",
        """<svg viewBox="0 0 24 24" fill="none"><path d="m10 13 4-4m-6.5 9.5 2.5-2.5a4 4 0 0 0 0-5.6 4 4 0 0 0-5.6 0L2 12.9a4 4 0 0 0 5.6 5.6Zm9-9 2.5-2.5a4 4 0 1 0-5.6-5.6L13.4 4a4 4 0 0 0 0 5.6 4 4 0 0 0 5.6 0Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>""",
        "Tương tác",
    ),
]


def _get_active_tab():

    valid = {k for k, _, _ in TAB_ITEMS}
    default_tab = "overview"

    raw_tab = None
    if hasattr(st, "query_params"):
        raw_tab = st.query_params.get("tab")
    else:
        raw_tab = st.experimental_get_query_params().get("tab", [None])[0]

    if isinstance(raw_tab, list):
        raw_tab = raw_tab[0] if raw_tab else None

    if raw_tab in valid:
        st.session_state["active_tab"] = raw_tab
    elif "active_tab" not in st.session_state:
        st.session_state["active_tab"] = default_tab

    return st.session_state.get("active_tab", default_tab)


def build_state(DF):

    active_tab = _get_active_tab()

    if "ui_mode" not in st.session_state:
        st.session_state["ui_mode"] = UI_MODES[0]
    if "reduce_motion" not in st.session_state:
        st.session_state["reduce_motion"] = False
    if "colorblind_mode" not in st.session_state:
        st.session_state["colorblind_mode"] = False

    apply_colorblind(bool(st.session_state.get("colorblind_mode", False)))
    set_plot_theme(st.session_state["ui_mode"])
    st.markdown(
        ui_mode_css(st.session_state["ui_mode"], st.session_state["reduce_motion"]),
        unsafe_allow_html=True,
    )

    # Keep rendering/theme behavior stable without showing old sidebar controls.

    # Minimal "global filter" defaults now that sidebar only acts as navigation.
    df = DF.copy()
    sel = sorted(df["city"].dropna().astype(str).unique().tolist())
    s_d = df["date_ts"].min().date()
    e_d = df["date_ts"].max().date()
    avg_aqi = int(df["aqi"].mean()) if not df["aqi"].dropna().empty else 0
    _lbl, _col = aqi_meta(avg_aqi)

    return {
        "active_tab": active_tab,
        "df": df,
        "sel": sel,
        "s_d": s_d,
        "e_d": e_d,
        "avg_aqi": avg_aqi,
        "_lbl": _lbl,
        "_col": _col,
    }

