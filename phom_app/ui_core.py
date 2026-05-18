import streamlit as st

from .paths import MASTER_DIR, ROOT
from .storage import read_text


def render_home_page(modules: list[dict]) -> None:
    st.title("Home / Dashboard")
    built = [m for m in modules if (ROOT / m["output_file"]).exists()]
    missing = [m for m in modules if not (ROOT / m["output_file"]).exists()]
    c1, c2, c3 = st.columns(3)
    c1.metric("Module count", len(modules))
    c2.metric("Built modules", len(built))
    c3.metric("Missing modules", len(missing))
    st.write("Built:", [m["id"] for m in built] or "None")
    st.write("Missing:", [m["id"] for m in missing] or "None")


def render_core_page(module_ids: list[str], module_lookup: dict[str, dict]) -> None:
    st.title("PHOM Core")
    selected_module_id = st.selectbox("Select module", module_ids, key="core_module")
    selected_module = module_lookup[selected_module_id]
    st.subheader("Generated module markdown")
    st.text_area("Module output", value=read_text(ROOT / selected_module["output_file"]) or "No module output.", height=280)

    masters = sorted(MASTER_DIR.glob("*.md")) if MASTER_DIR.exists() else []
    st.subheader("Master file (05_master)")
    if masters:
        master_label = st.selectbox("Select master file", [str(p.relative_to(ROOT)) for p in masters])
        st.text_area("Master content", value=read_text(ROOT / master_label), height=240)
    else:
        st.info("No master markdown files found in 05_master/.")
