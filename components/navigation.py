import streamlit as st

from components.sidebar import TAB_ITEMS

REFRESH_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.85.83 6.72 2.25" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M21 3v6h-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>"""


def render_navigation(active_tab: str):
    """Render hover sidebar directly in page DOM for reliable query-param nav."""
    colorblind_on = st.session_state.get("colorblind_mode", False)
    cb_param = "&cb=1" if colorblind_on else "&cb=0"

    items_html = []
    for key, icon_svg, label in TAB_ITEMS:
        active_cls = " is-active" if key == active_tab else ""
        items_html.append(
            f"<a class='az-nav-item{active_cls}' href='?tab={key}{cb_param}' target='_self' title='{label}'>"
            f"<span class='az-nav-icon'>{icon_svg}</span>"
            f"<span class='az-nav-label'>{label}</span>"
            f"</a>"
        )
    items_html.append(
        f"<a class='az-nav-item az-nav-refresh' href='?refresh=1&tab={active_tab}{cb_param}' target='_self' title='Refresh Data'>"
        f"<span class='az-nav-icon'>{REFRESH_ICON_SVG}</span>"
        f"<span class='az-nav-label'>Refresh Data</span>"
        f"</a>"
    )

    pass

    # Sentinel div — CSS uses :has(._az-nav-sentinel) to target only this column/row
    st.markdown(
        "<div class='_az-nav-sentinel' style='min-height:400px;width:75px;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='az-nav-host'><nav class='az-nav'>{''.join(items_html)}</nav></div>",
        unsafe_allow_html=True,
    )
