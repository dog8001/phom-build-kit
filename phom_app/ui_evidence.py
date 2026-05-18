from datetime import datetime
import streamlit as st
from .paths import EVIDENCE_FILE, ROOT
from .storage import read_text


def render_evidence_page(module_ids: list[str]) -> None:
    st.title("Evidence")
    module_tag = st.selectbox("Optional module/domain tag", [""] + module_ids, key="e_module")
    note = st.text_area("Evidence note", height=180)
    if st.button("Append evidence"):
        if not note.strip():
            st.warning("Enter a note before saving.")
        else:
            EVIDENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
            prefix = f"\n\n### {datetime.now().isoformat(timespec='seconds')}"
            if module_tag:
                prefix += f" | {module_tag}"
            with EVIDENCE_FILE.open("a", encoding="utf-8") as f:
                f.write(prefix + "\n" + note.strip() + "\n")
            st.success(f"Evidence appended to {EVIDENCE_FILE.relative_to(ROOT)}")
    st.subheader("Current evidence file")
    st.text_area("Evidence base", value=read_text(EVIDENCE_FILE), height=280)
