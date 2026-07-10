import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Feeling Bad Air?", page_icon="🌫️", layout="wide")

st.title("🌫️ Feeling Bad Air?")
st.caption(
    "Scroll or pinch to zoom, drag to pan, and drag the center bar to compare "
    "pollutant transport patterns between May and June 2026"
)

# ---- CONFIG ----------------------------------------------------------
# Streamlit runs relative to the repo root (where app.py lives), so we
# resolve from this file's location up to the repo root, then into data/images.
REPO_ROOT = Path(__file__).resolve().parent.parent  # pages/ -> repo root
IMAGE_DIR = REPO_ROOT / "data" / "images"

STATIONS = ["DKI1", "DKI2", "DKI3", "DKI4", "DKI5"]
VIEWER_HEIGHT = 480  # px, height of the zoom/compare canvas

NARRATION_1 = """
## 1. Brief Summary

**May 11–31, 2026 (Transition from Wet to Dry Season)**

Across the five monitoring stations, a contrasting shift is visible in both air mass pathways (trajectories) and pollutant intensity (PM2.5 concentrations) based on the HYSPLIT-CWT analysis for Jakarta between late May and early June 2026.

During the latter half of May, air masses primarily arrive from a wide, fan-like array of directions, including the South-Southeast, East-Northeast, and South-Southwest. The high-concentration "hotspot" (the red and orange core) remains tightly localized and concentrated directly over the Greater Jakarta area (including Jakarta, Depok, Bekasi, and parts of Bogor and Tangerang).

Notably, May 2026 contains several long weekends and major public holidays — including Labour Day, the Ascension Day long weekend, Idul Adha, and the consecutive Waisak and Pancasila Day holidays spanning into June 1st. Increased mobility, tourism, and heavy traffic leaving and re-entering the capital during these periods caused sharp spikes in local emissions. This accumulation of local urban emissions alongside surrounding regional inputs serves as an early indicator that Jakarta's pollution stems from a combination of localized sources and transboundary air pollution.

**June 1–14, 2026 (Establishment of the Dry Season)**

In early June, the maximum CWT value surges drastically to 153.54 µg/m³, nearly doubling the peak observed in May.

During this period, wind trajectories undergo a unified, distinct shift: all primary clusters originate exclusively from the East and East-Southeast. The high-concentration plume (represented by the dark red and brown contours) extends eastward in a wide corridor stretching over major industrial hubs, including Bekasi, Karawang, and Purwakarta. This provides further evidence of transboundary air pollution. Because the regional wind speeds are faster during this period, the air masses travel longer distances over a shorter timeframe, producing the elongated trajectories shown on the map.
"""

NARRATION_2 = """
## 2. Monsoon Influence and Seasonal Wind Dynamics

The sharp contrast between May and June is driven by the establishment of the Southeast (East) Monsoon, which marks the definitive onset of Indonesia's dry season.

**Wind Direction Shift**

In May, Jakarta experiences a transitional weather period (*pancaroba*). Wind directions are variable and unstable, causing the trajectory clusters to spread out in multiple directions. By June, the Southeast Monsoon stabilizes completely. Strong, persistent trade winds blow from the Australian continent across the Java Sea and the mainland of Java toward the northwest.

**Wind Speed and Atmospheric Stagnation**

While regional monsoonal winds are steady, the lower troposphere over western Java during June frequently experiences a lower Planetary Boundary Layer Height (PBLH) alongside nighttime surface wind stagnation. As air masses travel long distances from the east and southeast along Java's northern industrial corridor, they continuously accumulate industrial and vehicular pollution, eventually funnelling it directly into the Jakarta basin.
"""

NARRATION_3 = """
## 3. The Rise of Pollutants (PM2.5)

The rapid escalation of PM2.5 concentrations in June is a direct result of transboundary transport combining with highly unfavorable meteorological dispersion.

- **Upwind Industrial Contributions:** As shown in the June map, the dominant air masses pass directly through the heavily industrialized zones east of Jakarta (Bekasi, Karawang, and Purwakarta). These areas host dense clusters of manufacturing plants, coal-fired power stations, and heavy commercial traffic corridor emissions.
- **Lack of Wet Scavenging:** In May, residual rain events still wash out particulates from the atmosphere via precipitation scavenging. By June, rainfall drops significantly. Without rain to precipitate fine particles out of the air column, PM2.5 accumulates rapidly, leading to the prolonged, intense pollution episodes illustrated by the deep red 140–150 µg/m³ CWT contours.
"""
# ------------------------------------------------------------------------

# Supporting figures referenced in the narration
FIGURE_DIR = REPO_ROOT / "data" / "images" / "figures"

station = st.selectbox("Select Station", STATIONS, index=0)

may_path = IMAGE_DIR / f"May_{station}.png"
june_path = IMAGE_DIR / f"June_{station}.png"


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def render_figure(path: Path, caption: str, height: int = 380) -> None:
    """Render an image constrained to a fixed height box (object-fit: contain),
    so figures with different native aspect ratios still display at a matched size."""
    b64 = _b64(path)
    st.markdown(
        f"""
        <div style="height:{height}px; display:flex; align-items:center; justify-content:center;
                    background:#ffffff; border-radius:6px; overflow:hidden;">
            <img src="data:image/png;base64,{b64}"
                 style="max-width:100%; max-height:100%; object-fit:contain;" />
        </div>
        <div style="font-size:13px; color:#aaa; margin-top:6px;">{caption}</div>
        """,
        unsafe_allow_html=True,
    )


if may_path.exists() and june_path.exists():
    may_b64 = _b64(may_path)
    june_b64 = _b64(june_path)

    html_code = f"""
    <style>
      #zc-wrap {{
        position: relative;
        width: 100%;
        height: {VIEWER_HEIGHT}px;
        overflow: hidden;
        background: #0e1117;
        border-radius: 8px;
        touch-action: none;
        cursor: grab;
        user-select: none;
      }}
      #zc-wrap:active {{ cursor: grabbing; }}
      .zc-img {{
        position: absolute;
        top: 50%; left: 50%;
        height: 100%;
        width: auto;
        max-width: none;
        transform-origin: center center;
        pointer-events: none;
      }}
      #zc-top {{ clip-path: inset(0 50% 0 0); }}
      #zc-handle {{
        position: absolute;
        top: 0; bottom: 0;
        width: 4px;
        background: #fff;
        left: 50%;
        transform: translateX(-50%);
        cursor: ew-resize;
        z-index: 5;
        touch-action: none;
      }}
      #zc-handle::after {{
        content: "\\25C2\\25B8";
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        background: #fff;
        color: #000;
        border-radius: 50%;
        width: 34px; height: 34px;
        display: flex; align-items: center; justify-content: center;
        font-size: 13px;
      }}
      .zc-label {{
        position: absolute;
        top: 10px;
        padding: 4px 10px;
        background: rgba(0,0,0,0.6);
        color: #fff;
        font-family: sans-serif;
        font-size: 13px;
        border-radius: 4px;
        z-index: 6;
        pointer-events: none;
      }}
      #zc-controls {{
        margin-top: 8px;
        font-family: sans-serif;
        font-size: 12px;
        color: #aaa;
        display: flex;
        align-items: center;
      }}
      #zc-reset {{
        margin-left: 10px;
        padding: 3px 10px;
        font-size: 12px;
        border-radius: 4px;
        border: 1px solid #555;
        background: #262730;
        color: #fff;
        cursor: pointer;
      }}
    </style>

    <div id="zc-wrap">
      <div class="zc-label" style="left:10px;">May 2026 — {station}</div>
      <div class="zc-label" style="right:10px;">June 2026 — {station}</div>
      <img id="zc-bottom" class="zc-img" src="data:image/png;base64,{may_b64}" />
      <img id="zc-top" class="zc-img" src="data:image/png;base64,{june_b64}" />
      <div id="zc-handle"></div>
    </div>
    <div id="zc-controls">
      Scroll / pinch to zoom &nbsp;•&nbsp; drag image to pan &nbsp;•&nbsp;
      drag center bar to compare &nbsp;•&nbsp; double-click to reset
      <button id="zc-reset">Reset view</button>
    </div>

    <script>
    (function() {{
      const wrap = document.getElementById('zc-wrap');
      const imgTop = document.getElementById('zc-top');
      const imgBottom = document.getElementById('zc-bottom');
      const handle = document.getElementById('zc-handle');
      const resetBtn = document.getElementById('zc-reset');

      let scale = 1, panX = 0, panY = 0;
      let sliderPct = 50;
      let isPanning = false;
      let draggingHandle = false;
      let startX = 0, startY = 0;
      let lastTouchDist = null;

      function applyTransform() {{
        const t = `translate(-50%, -50%) translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`;
        imgTop.style.transform = t;
        imgBottom.style.transform = t;
      }}

      function applyClip() {{
        imgTop.style.clipPath = `inset(0 ${{100 - sliderPct}}% 0 0)`;
        handle.style.left = sliderPct + '%';
      }}

      function clampScale(s) {{ return Math.min(8, Math.max(1, s)); }}

      wrap.addEventListener('wheel', function(e) {{
        e.preventDefault();
        const delta = e.deltaY < 0 ? 1.12 : 1/1.12;
        scale = clampScale(scale * delta);
        applyTransform();
      }}, {{ passive: false }});

      wrap.addEventListener('mousedown', function(e) {{
        if (e.target === handle) return;
        isPanning = true;
        startX = e.clientX - panX;
        startY = e.clientY - panY;
      }});
      window.addEventListener('mousemove', function(e) {{
        if (!isPanning) return;
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        applyTransform();
      }});
      window.addEventListener('mouseup', function() {{ isPanning = false; }});

      wrap.addEventListener('dblclick', function() {{
        scale = 1; panX = 0; panY = 0;
        applyTransform();
      }});
      resetBtn.addEventListener('click', function() {{
        scale = 1; panX = 0; panY = 0; sliderPct = 50;
        applyTransform(); applyClip();
      }});

      handle.addEventListener('mousedown', function(e) {{
        draggingHandle = true;
        e.stopPropagation();
      }});
      window.addEventListener('mousemove', function(e) {{
        if (!draggingHandle) return;
        const rect = wrap.getBoundingClientRect();
        let pct = ((e.clientX - rect.left) / rect.width) * 100;
        pct = Math.min(100, Math.max(0, pct));
        sliderPct = pct;
        applyClip();
      }});
      window.addEventListener('mouseup', function() {{ draggingHandle = false; }});

      function touchDist(t1, t2) {{
        const dx = t1.clientX - t2.clientX;
        const dy = t1.clientY - t2.clientY;
        return Math.sqrt(dx*dx + dy*dy);
      }}

      wrap.addEventListener('touchstart', function(e) {{
        if (e.touches.length === 2) {{
          lastTouchDist = touchDist(e.touches[0], e.touches[1]);
        }} else if (e.touches.length === 1) {{
          if (e.target === handle) {{
            draggingHandle = true;
          }} else {{
            isPanning = true;
            startX = e.touches[0].clientX - panX;
            startY = e.touches[0].clientY - panY;
          }}
        }}
      }}, {{ passive: true }});

      wrap.addEventListener('touchmove', function(e) {{
        if (e.touches.length === 2) {{
          e.preventDefault();
          const dist = touchDist(e.touches[0], e.touches[1]);
          if (lastTouchDist) {{
            const delta = dist / lastTouchDist;
            scale = clampScale(scale * delta);
            applyTransform();
          }}
          lastTouchDist = dist;
        }} else if (e.touches.length === 1) {{
          if (draggingHandle) {{
            const rect = wrap.getBoundingClientRect();
            let pct = ((e.touches[0].clientX - rect.left) / rect.width) * 100;
            pct = Math.min(100, Math.max(0, pct));
            sliderPct = pct;
            applyClip();
          }} else if (isPanning) {{
            panX = e.touches[0].clientX - startX;
            panY = e.touches[0].clientY - startY;
            applyTransform();
          }}
        }}
      }}, {{ passive: false }});

      wrap.addEventListener('touchend', function(e) {{
        if (e.touches.length < 2) lastTouchDist = null;
        if (e.touches.length === 0) {{ isPanning = false; draggingHandle = false; }}
      }});

      applyTransform();
      applyClip();
    }})();
    </script>
    """

    components.html(html_code, height=VIEWER_HEIGHT + 40, scrolling=False)
    st.caption(f"Comparing {station}: May 1–31, 2026 vs June 1–14, 2026")
else:
    missing = [p.name for p in (may_path, june_path) if not p.exists()]
    st.error(
        f"Missing image file(s): {', '.join(missing)}\n\n"
        f"Expected them at: `{IMAGE_DIR}`"
    )

st.markdown("---")
st.markdown(NARRATION_1)

st.markdown(NARRATION_2)

fig_monsoon = FIGURE_DIR / "monsoon_wind_map.png"
fig_inversion = FIGURE_DIR / "inversion_diagram.png"

fig2_col_1, fig2_col_2 = st.columns(2)
with fig2_col_1:
    if fig_monsoon.exists():
        render_figure(
            fig_monsoon,
            caption="Seasonal wind reversal across Indonesia: winds and rainy/dry season "
                    "timing flip between the Northwest and Southeast Monsoon, driving the "
                    "May-to-June shift in air mass origin over Jakarta.",
        )
with fig2_col_2:
    if fig_inversion.exists():
        render_figure(
            fig_inversion,
            caption="Nighttime temperature inversion: cool air trapped beneath a warmer "
                    "layer prevents vertical mixing, holding pollutants near the surface "
                    "until the inversion breaks down.",
        )

st.markdown(NARRATION_3)

fig_dispersion = FIGURE_DIR / "urban_dispersion_cfd.png"
fig_deposition = FIGURE_DIR / "wet_deposition_washout.png"

fig_col_1, fig_col_2 = st.columns(2)
with fig_col_1:
    if fig_dispersion.exists():
        render_figure(
            fig_dispersion,
            caption="Simulated pollutant dispersion around an urban canopy, showing how "
                    "tall buildings, rooftop shear layers, and low-rise canopy effects "
                    "trap and channel pollutants near the source before they disperse "
                    "downwind.",
        )
with fig_col_2:
    if fig_deposition.exists():
        render_figure(
            fig_deposition,
            caption="Illustration of wet deposition: rainfall washes fine and coarse "
                    "particles out of the atmosphere and into waterways, a removal "
                    "pathway that weakens sharply once rainfall drops in the dry season.",
        )

st.markdown("---")
st.caption("Source: NOAA HYSPLIT + DLH Jakarta PM2.5")