#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
MODULE_LIST_PATH = ROOT / "00_architecture" / "PHOM_Module_List_v1.json"
COMPARISON_RUNS_PATH = ROOT / "comparison_runs"

MODE_TO_REASONING = {
    "API low": "low",
    "API medium": "medium",
    "API high": "high",
    "API xhigh": "xhigh",
}
VALID_REASONING_EFFORTS = set(MODE_TO_REASONING.values())


def load_modules() -> list[dict]:
    return json.loads(MODULE_LIST_PATH.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def get_latest_log(module_id: str, suffix: str) -> Path | None:
    candidates = sorted((ROOT / "06_logs").glob(f"{module_id}*{suffix}"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None




def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def is_valid_model_name(model: str) -> bool:
    if not model:
        return False
    if "thinking" in model:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9._:-]+", model))


def validate_config() -> tuple[bool, list[str]]:
    messages: list[str] = []
    env_path = ROOT / ".env"
    env_values = read_env_file(env_path)

    if env_path.exists():
        messages.append(f".env found: {env_path}")
    else:
        messages.append(".env file is missing")

    model = os.getenv("PHOM_MODEL") or env_values.get("PHOM_MODEL", "")
    effort = os.getenv("PHOM_REASONING_EFFORT") or env_values.get("PHOM_REASONING_EFFORT", "")
    api_key = os.getenv("OPENAI_API_KEY") or env_values.get("OPENAI_API_KEY", "")

    if is_valid_model_name(model):
        messages.append(f"PHOM_MODEL looks valid: {model}")
    else:
        messages.append(f"Invalid PHOM_MODEL: {model!r}")

    if effort in VALID_REASONING_EFFORTS:
        messages.append(f"PHOM_REASONING_EFFORT looks valid: {effort}")
    else:
        messages.append(f"Invalid PHOM_REASONING_EFFORT: {effort!r} (expected one of {sorted(VALID_REASONING_EFFORTS)})")

    if api_key:
        messages.append("OPENAI_API_KEY is configured")
    else:
        messages.append("OPENAI_API_KEY is missing")

    ok = env_path.exists() and is_valid_model_name(model) and effort in VALID_REASONING_EFFORTS and bool(api_key)
    return ok, messages

def list_compare_files() -> list[Path]:
    files: list[Path] = []
    for folder in [COMPARISON_RUNS_PATH, ROOT / "03_modules"]:
        if folder.exists():
            files.extend(sorted(folder.glob("*.md")))
    return files


def run_build(module_id: str, mode: str) -> tuple[int, str, str, list[str]]:
    cmd = [sys.executable, str(ROOT / "scripts" / "build_module.py"), module_id]
    env = os.environ.copy()

    if mode == "dry-run":
        cmd.append("--dry-run")
    else:
        env["PHOM_REASONING_EFFORT"] = MODE_TO_REASONING[mode]

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr, cmd


def main() -> None:
    st.set_page_config(page_title="PHOM Build Control Panel", layout="wide")
    st.title("PHOM Build Kit — Control Panel")

    modules = load_modules()
    module_ids = [m["id"] for m in modules]

    st.sidebar.header("Build Controls")
    selected_module_id = st.sidebar.selectbox("Select module", module_ids)
    selected_mode = st.sidebar.selectbox("Select mode", ["dry-run", "API low", "API medium", "API high", "API xhigh"])

    selected_module = next(m for m in modules if m["id"] == selected_module_id)

    tab_dashboard, tab_build, tab_review, tab_compare = st.tabs(
        ["Dashboard", "Build Module", "Review Outputs", "Compare Runs"]
    )

    with tab_dashboard:
        built = [m for m in modules if (ROOT / m["output_file"]).exists()]
        missing = [m for m in modules if not (ROOT / m["output_file"]).exists()]

        c1, c2, c3 = st.columns(3)
        c1.metric("Module count", len(modules))
        c2.metric("Built modules", len(built))
        c3.metric("Missing modules", len(missing))

        st.subheader("Built")
        st.write([m["id"] for m in built] or "None")
        st.subheader("Missing")
        st.write([m["id"] for m in missing] or "None")

    with tab_build:
        st.subheader("Selected module metadata")
        st.json(selected_module)
        model_display = os.getenv("PHOM_MODEL", "<unset>")
        effort_display = os.getenv("PHOM_REASONING_EFFORT", "<unset>")
        command_preview = [sys.executable, str(ROOT / "scripts" / "build_module.py"), selected_module_id]
        if selected_mode == "dry-run":
            command_preview.append("--dry-run")
        else:
            command_preview.append(f"# PHOM_REASONING_EFFORT={MODE_TO_REASONING[selected_mode]}")

        with st.expander("Debug config", expanded=True):
            st.write(f"PHOM_MODEL: `{model_display}`")
            st.write(f"PHOM_REASONING_EFFORT: `{effort_display}`")
            st.code(" ".join(command_preview))

        if st.button("Validate Config"):
            valid, messages = validate_config()
            for msg in messages:
                st.write(f"- {msg}")
            if valid:
                st.success("Config validation passed.")
            else:
                st.error("Config validation failed.")

        if st.button("Run build", type="primary"):
            with st.spinner(f"Running {selected_mode} for {selected_module_id}..."):
                code, stdout, stderr, executed_cmd = run_build(selected_module_id, selected_mode)
            st.caption("Command output")
            st.code(" ".join(executed_cmd))
            st.code(stdout or "<no stdout>")
            if stderr:
                st.code(stderr)
            if code == 0:
                st.success("Build completed.")
            else:
                st.error(f"Build failed (exit code {code}).")

        st.info("API key is read from your local environment/.env by scripts/build_module.py and is never displayed here.")

    with tab_review:
        st.subheader("Generated module markdown")
        module_md = read_text(ROOT / selected_module["output_file"])
        st.text_area("Module output", value=module_md or "No module output found.", height=240)

        st.subheader("Review questions markdown")
        review_md = read_text(ROOT / selected_module["review_file"])
        st.text_area("Review questions", value=review_md or "No review questions found.", height=200)

        st.subheader("Logs")
        draft_log = get_latest_log(selected_module_id, "_draft.md")
        critique_log = get_latest_log(selected_module_id, "_critique.md")

        for label, path in [("Draft log", draft_log), ("Critique log", critique_log)]:
            if path:
                st.markdown(f"**{label}:** `{path.relative_to(ROOT)}`")
                st.text_area(label, value=read_text(path), height=180)
            else:
                st.markdown(f"**{label}:** not found")

    with tab_compare:
        files = list_compare_files()
        if not files:
            st.warning("No markdown files found in comparison_runs or 03_modules.")
        else:
            labels = [str(p.relative_to(ROOT)) for p in files]
            left_label = st.selectbox("File A", labels, index=0)
            right_default = 1 if len(labels) > 1 else 0
            right_label = st.selectbox("File B", labels, index=right_default)

            left_text = read_text(ROOT / left_label)
            right_text = read_text(ROOT / right_label)

            c1, c2 = st.columns(2)
            c1.text_area(f"A: {left_label}", value=left_text, height=400)
            c2.text_area(f"B: {right_label}", value=right_text, height=400)


if __name__ == "__main__":
    main()
