from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from .ui_questions import render_questions_page

ROOT = Path(__file__).resolve().parents[1]


def load_modules() -> list[dict]:
    path = ROOT / "00_architecture" / "PHOM_Module_List_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    st.set_page_config(page_title="PHOM/QI Workspace", layout="wide")
    modules = load_modules()
    page = st.sidebar.radio("Navigate", ["Home / Dashboard", "Questions"])
    if page == "Questions":
        render_questions_page(ROOT, modules)
    else:
        st.title("Home / Dashboard")
        st.write("Use sidebar to open Questions.")


if __name__ == "__main__":
    main()
