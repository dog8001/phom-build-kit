#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os

import streamlit as st

from phom_app.paths import MODULE_LIST_PATH, ROOT
from phom_app.storage import read_env_file, read_json_file
from phom_app.ui_control_panel import render_control_panel_page
from phom_app.ui_core import render_core_page, render_home_page
from phom_app.ui_evidence import render_evidence_page
from phom_app.ui_questions import render_questions_page
from phom_app.ui_settings import render_settings_page


def load_modules() -> list[dict]:
    return read_json_file(MODULE_LIST_PATH, [])


def check_login() -> bool:
    env = read_env_file(ROOT / ".env")
    expected_user = os.getenv("PHOM_UI_USERNAME") or env.get("PHOM_UI_USERNAME", "")
    expected_pass = os.getenv("PHOM_UI_PASSWORD") or env.get("PHOM_UI_PASSWORD", "")
    if not expected_user or not expected_pass:
        st.sidebar.warning("PHOM_UI_USERNAME/PHOM_UI_PASSWORD not set. Local workspace access is open.")
        return True
    if st.session_state.get("authenticated"):
        return True
    st.title("PHOM/QI Workspace Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        digest_input = hashlib.sha256(f"{username}:{password}".encode()).hexdigest()
        digest_expected = hashlib.sha256(f"{expected_user}:{expected_pass}".encode()).hexdigest()
        if digest_input == digest_expected:
            st.session_state["authenticated"] = True
            st.success("Login successful. Reloading workspace...")
            st.rerun()
        else:
            st.error("Invalid username/password.")
    return False


def main() -> None:
    st.set_page_config(page_title="PHOM/QI Workspace v0.2", layout="wide")
    if not check_login():
        return

    modules = load_modules()
    module_lookup = {m["id"]: m for m in modules}
    module_ids = [m["id"] for m in modules]

    st.sidebar.title("PHOM/QI Workspace v0.2")
    page = st.sidebar.radio("Navigate", ["Home / Dashboard", "PHOM Core", "Questions", "Evidence", "Control Panel", "Settings"])

    if page == "Home / Dashboard":
        render_home_page(modules)
    elif page == "PHOM Core":
        render_core_page(module_ids, module_lookup)
    elif page == "Questions":
        render_questions_page(modules, module_lookup)
    elif page == "Evidence":
        render_evidence_page(module_ids)
    elif page == "Control Panel":
        render_control_panel_page(module_ids, module_lookup)
    elif page == "Settings":
        render_settings_page()


if __name__ == "__main__":
    main()
