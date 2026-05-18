#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
MODULE_LIST_PATH = ROOT / "00_architecture" / "PHOM_Module_List_v1.json"
COMPARISON_RUNS_PATH = ROOT / "comparison_runs"

MODE_TO_MODEL = {
    "API low": "gpt-5.5-thinking-low",
    "API medium": "gpt-5.5-thinking",
    "API high": "gpt-5.5-thinking-high",
    "API xhigh": "gpt-5.5-thinking-xhigh",
}


def load_modules() -> list[dict]:
    return json.loads(MODULE_LIST_PATH.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def get_latest_log(module_id: str, suffix: str) -> Path | None:
    candidates = sorted((ROOT / "06_logs").glob(f"{module_id}*{suffix}"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def list_compare_files() -> list[Path]:
    files: list[Path] = []
    for folder in [COMPARISON_RUNS_PATH, ROOT / "03_modules"]:
        if folder.exists():
            files.extend(sorted(folder.glob("*.md")))
    return files


def run_build(module_id: str, mode: str) -> tuple[int, str, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / "build_module.py"), module_id]
    env = os.environ.copy()

    if mode == "dry-run":
        cmd.append("--dry-run")
    else:
        env["PHOM_MODEL"] = MODE_TO_MODEL[mode]

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


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
        if st.button("Run build", type="primary"):
            with st.spinner(f"Running {selected_mode} for {selected_module_id}..."):
                code, stdout, stderr = run_build(selected_module_id, selected_mode)
            st.caption("Command output")
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
