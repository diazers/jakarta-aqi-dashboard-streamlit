import streamlit as st
from pathlib import Path
from streamlit_image_comparison import image_comparison

st.set_page_config(page_title="Feeling Bad Air?", page_icon="🌫️", layout="wide")

st.title("🏭️ Feeling Bad Air?")
st.caption("Slide to compare pollutant transport patterns between May and June 2026")

# ---- CONFIG ----------------------------------------------------------
# Streamlit runs relative to the repo root (where app.py lives), so we
# resolve from this file's location up to the repo root, then into data/images.
REPO_ROOT = Path(__file__).resolve().parent.parent  # pages/ -> repo root
IMAGE_DIR = REPO_ROOT / "data" / "images"

STATIONS = ["DKI1", "DKI2", "DKI3", "DKI4", "DKI5"]
# ------------------------------------------------------------------------

station = st.selectbox("Select Station", STATIONS, index=0)

may_path = IMAGE_DIR / f"May_{station}.png"
june_path = IMAGE_DIR / f"June_{station}.png"

col_left, col_right = st.columns([1, 4])
with col_left:
    st.markdown(f"**Station:** {station}")
    st.markdown("**Comparing:**")
    st.markdown("- May 1–31, 2026")
    st.markdown("- June 1–14, 2026")

with col_right:
    if may_path.exists() and june_path.exists():
        image_comparison(
            img1=str(may_path),
            img2=str(june_path),
            label1=f"May 2026 — {station}",
            label2=f"June 2026 — {station}",
            width=900,
            starting_position=50,
            show_labels=True,
            make_responsive=True,
            in_memory=True,
        )
    else:
        missing = [p.name for p in (may_path, june_path) if not p.exists()]
        st.error(
            f"Missing image file(s): {', '.join(missing)}\n\n"
            f"Expected them at: `{IMAGE_DIR}`"
        )

st.markdown("---")
st.caption("Source: NOAA HYSPLIT + DLH Jakarta PM2.5")
