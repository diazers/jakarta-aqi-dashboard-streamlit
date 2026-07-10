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
VIEWER_HEIGHT = 720  # px, height of the zoom/compare canvas
# ------------------------------------------------------------------------

station = st.selectbox("Select Station", STATIONS, index=0)

may_path = IMAGE_DIR / f"May_{station}.png"
june_path = IMAGE_DIR / f"June_{station}.png"


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


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
    st.caption(f"Comparing {station}: May 11–31, 2026 vs June 1–14, 2026")
else:
    missing = [p.name for p in (may_path, june_path) if not p.exists()]
    st.error(
        f"Missing image file(s): {', '.join(missing)}\n\n"
        f"Expected them at: `{IMAGE_DIR}`"
    )

st.markdown("---")
st.caption("Source: NOAA HYSPLIT + DLH Jakarta PM2.5")
