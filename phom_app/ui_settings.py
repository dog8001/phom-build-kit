import os
import streamlit as st

from .paths import ROOT
from .storage import read_env_file, write_env_file
from .utils import is_valid_model_name, validate_config


def render_settings_page() -> None:
    st.title("Settings")
    env_path = ROOT / ".env"
    env_values = read_env_file(env_path)
    model = st.text_input("PHOM_MODEL", value=os.getenv("PHOM_MODEL") or env_values.get("PHOM_MODEL", "gpt-5.5"))
    current_effort = os.getenv("PHOM_REASONING_EFFORT") or env_values.get("PHOM_REASONING_EFFORT", "medium")
    effort = st.selectbox("PHOM_REASONING_EFFORT", ["low", "medium", "high", "xhigh"], index=["low", "medium", "high", "xhigh"].index(current_effort))
    st.text_input("OPENAI_API_KEY", value="********", disabled=True, help="Hidden for safety.")
    st.text_input("ROOT path", value=str(ROOT), disabled=True)
    st.text_input("Modules path", value=str(ROOT / "03_modules"), disabled=True)
    if st.button("Save safe settings"):
        if not is_valid_model_name(model):
            st.error("Invalid PHOM_MODEL format.")
        else:
            write_env_file(env_path, {"PHOM_MODEL": model, "PHOM_REASONING_EFFORT": effort})
            os.environ["PHOM_MODEL"] = model
            os.environ["PHOM_REASONING_EFFORT"] = effort
            st.success("Saved PHOM_MODEL and PHOM_REASONING_EFFORT to .env")
    if st.button("Validate config"):
        ok, messages = validate_config()
        for msg in messages:
            st.write(f"- {msg}")
        st.success("Validation passed") if ok else st.error("Validation failed")
