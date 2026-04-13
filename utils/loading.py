from contextlib import contextmanager
from html import escape
import time
from typing import Optional

import streamlit as st


@contextmanager
def dashboard_loading(
    message: str = "Dang tai du lieu...",
    hint: Optional[str] = None,
    overlay: bool = False,
    min_duration: float = 0.0,
    art_data_url: Optional[str] = None,
):
    """Render a dashboard loader while a block is executing."""
    placeholder = st.empty()
    safe_message = escape(message)
    safe_hint = escape(hint) if hint else "He thong dang xu ly du lieu..."
    loader_art = art_data_url or st.session_state.get("_loader_art_url")
    icon_urls = st.session_state.get("_loader_icon_urls", [])
    icon_labels = st.session_state.get("_loader_icon_labels", [])
    art_html = ""
    if loader_art:
        safe_loader_art = escape(loader_art, quote=True)
        art_html = (
            f"<div class=\"app-loader-theme-art\" "
            f"style=\"background-image:url('{safe_loader_art}')\"></div>"
        )

    theme_html = ""
    if icon_urls:
        icon_nodes = []
        legend_labels = []
        for idx, icon_url in enumerate(icon_urls[:6]):
            raw_label = icon_labels[idx] if idx < len(icon_labels) else f"AQI {idx + 1}"
            safe_label = escape(str(raw_label))
            safe_icon_url = escape(str(icon_url), quote=True)
            icon_nodes.append(
                f"<span class=\"app-loader-theme-icon\" style=\"background-image:url('{safe_icon_url}')\" "
                f"title=\"{safe_label}\" aria-label=\"{safe_label}\"></span>"
            )
            legend_labels.append(safe_label)

        legend_html = ""
        if legend_labels:
            legend_html = (
                "<div class=\"app-loader-theme-legend\">"
                + " &middot; ".join(legend_labels)
                + "</div>"
            )

        theme_html = (
            "<div class=\"app-loader-theme-block\" aria-hidden=\"true\">"
            "<div class=\"app-loader-theme-icons\">"
            + "".join(icon_nodes)
            + "</div>"
            + legend_html
            + "</div>"
        )
    wrap_class = "app-loader-wrap app-loader-wrap-overlay" if overlay else "app-loader-wrap"

    started_at = time.perf_counter()

    placeholder.markdown(
        f"""
        <div class="{wrap_class}" role="status" aria-live="polite">
            <div class="app-loader">
                {art_html}
                <div class="app-loader-orbit" aria-hidden="true">
                    <span class="app-loader-core"></span>
                    <span class="app-loader-ring app-loader-ring-a"></span>
                    <span class="app-loader-ring app-loader-ring-b"></span>
                </div>
                <div class="app-loader-copy">
                    <div class="app-loader-kicker">Vietnam AQI Dashboard</div>
                    <div class="app-loader-text">{safe_message}</div>
                    <div class="app-loader-sub">{safe_hint}</div>
                    <div class="app-loader-progress" aria-hidden="true">
                        <span></span>
                    </div>
                </div>
                <div class="app-loader-skeleton" aria-hidden="true">
                    <span></span><span></span><span></span>
                </div>
                {theme_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        elapsed = time.perf_counter() - started_at
        if min_duration > 0 and elapsed < min_duration:
            time.sleep(min_duration - elapsed)
        placeholder.empty()
