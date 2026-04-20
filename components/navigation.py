import streamlit as st
import streamlit.components.v1 as components

from components.sidebar import TAB_ITEMS

REFRESH_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.85.83 6.72 2.25" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M21 3v6h-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>"""


def render_navigation(active_tab: str):
    """Hover sidebar rendered as a components.html iframe.
    Navigation uses window.parent.location.replace() via JavaScript so it stays
    within the webview instead of opening an external browser (which anchor tag
    clicks trigger in VS Code's built-in browser).
    The iframe is positioned absolute via CSS (main.css) so it overlays the
    content column when expanded.
    """
    items_html = []
    for key, icon_svg, label in TAB_ITEMS:
        active_cls = " is-active" if key == active_tab else ""
        items_html.append(
            f"<div class='az-nav-item{active_cls}' data-tab='{key}' title='{label}'>"
            f"<span class='az-nav-icon'>{icon_svg}</span>"
            f"<span class='az-nav-label'>{label}</span>"
            f"</div>"
        )
    items_html.append(
        f"<div class='az-nav-item az-nav-refresh' data-tab='{active_tab}' data-refresh='1' title='Refresh Data'>"
        f"<span class='az-nav-icon'>{REFRESH_ICON_SVG}</span>"
        f"<span class='az-nav-label'>Refresh Data</span>"
        f"</div>"
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<link href='https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@500;700&display=swap' rel='stylesheet'>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:transparent;overflow:hidden;font-family:'Be Vietnam Pro',system-ui,sans-serif}}
.az-nav{{
  position:absolute;top:0;left:0;
  width:68px;
  background:linear-gradient(180deg,#0f2743 0%,#102844 70%,#112d4e 100%);
  border-right:1px solid rgba(255,255,255,0.08);
  border-radius:0 20px 20px 0;
  box-shadow:8px 0 26px rgba(15,23,42,0.26);
  padding:14px 8px;
  display:flex;flex-direction:column;gap:4px;
  overflow:hidden;
  transition:width .24s cubic-bezier(.22,1,.36,1),box-shadow .24s ease,border-radius .24s ease;
  z-index:9999;
}}
.az-nav:hover{{width:244px;box-shadow:12px 0 34px rgba(15,23,42,0.36)}}
.az-nav-item{{
  display:flex;align-items:center;gap:12px;
  min-height:46px;padding:9px 14px;
  border-radius:14px;
  color:#cbd5e1;
  font-size:.9rem;font-weight:700;
  white-space:nowrap;
  border:1px solid transparent;
  transition:background .2s ease,border-color .2s ease,color .2s ease,transform .2s ease;
  cursor:pointer;user-select:none;
}}
.az-nav-item:hover{{background:rgba(31,79,125,.46);border-color:rgba(148,184,214,.36);color:#f1f5f9;transform:translateX(1px)}}
.az-nav-item.is-active{{
  background:linear-gradient(135deg,#ff8a00,#ff6a00);
  color:#fff;border-color:rgba(255,255,255,.18);
  box-shadow:0 10px 24px rgba(15,23,42,.34);
}}
.az-nav-icon{{width:28px;min-width:28px;height:28px;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.az-nav-icon svg{{width:22px;height:22px}}
.az-nav-label{{opacity:0;max-width:0;overflow:hidden;transform:translateX(-6px);transition:opacity .2s ease .06s,max-width .24s cubic-bezier(.22,1,.36,1),transform .2s ease .06s}}
.az-nav:hover .az-nav-label{{opacity:1;max-width:170px;transform:translateX(0)}}
.az-nav-refresh{{margin-top:10px;border-top:1px solid rgba(148,184,214,.26);padding-top:14px!important}}
</style>
</head>
<body>
<nav class='az-nav'>{''.join(items_html)}</nav>
<script>
(function(){{
  function elevateNavFrame(){{
    try {{
      var frame = window.frameElement;
      if (!frame) return;
      frame.style.position = 'absolute';
      frame.style.zIndex = '2147483004';
      frame.style.overflow = 'visible';
      var host = frame.parentElement;
      if (host) {{
        host.style.position = 'absolute';
        host.style.zIndex = '2147483003';
        host.style.overflow = 'visible';
      }}
    }} catch (e) {{}}
  }}

  elevateNavFrame();

  document.addEventListener('mouseenter', elevateNavFrame, true);
  document.addEventListener('mousemove', elevateNavFrame, true);

  document.querySelectorAll('[data-tab]').forEach(function(el){{
    el.addEventListener('click',function(){{
      var tab=this.getAttribute('data-tab');
      var refresh=this.getAttribute('data-refresh')==='1';
      var p=window.parent.location;
      var base=p.protocol+'//'+p.host+p.pathname;
      window.parent.location.replace(base+(refresh?'?refresh=1&tab='+tab:'?tab='+tab));
    }});
  }});
}})();
</script>
</body>
</html>"""

    # Sentinel div — CSS uses :has(._az-nav-sentinel) to target only this column/row
    st.markdown(
        "<div class='_az-nav-sentinel' style='min-height:380px;width:74px;'></div>",
        unsafe_allow_html=True,
    )
    components.html(html, height=380, scrolling=False)
