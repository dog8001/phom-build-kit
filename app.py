#!/usr/bin/env python3
from __future__ import annotations

import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
MODULE_LIST_PATH = ROOT / "00_architecture" / "PHOM_Module_List_v1.json"
COMPARISON_RUNS_PATH = ROOT / "comparison_runs"
DOTENV_PATH = ROOT / ".env"

MODE_TO_MODEL = {
    "API low": "low",
    "API medium": "medium",
    "API high": "high",
    "API xhigh": "xhigh",
}


def load_modules() -> list[dict]:
    return json.loads(MODULE_LIST_PATH.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def upsert_dotenv(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updated = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            existing_key = line.split("=", 1)[0].strip()
            if existing_key == key:
                out.append(f"{key}={value}")
                updated = True
                continue
        out.append(line)
    if not updated:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def get_latest_generated_module(modules: list[dict]) -> str:
    latest_path: Path | None = None
    latest_name = "None"
    for module in modules:
        output_path = ROOT / module["output_file"]
        if output_path.exists() and (latest_path is None or output_path.stat().st_mtime > latest_path.stat().st_mtime):
            latest_path = output_path
            latest_name = module["id"]
    return latest_name


def get_latest_log(module_id: str, suffix: str) -> Path | None:
    candidates = sorted((ROOT / "06_logs").glob(f"{module_id}*{suffix}"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def list_compare_files() -> list[Path]:
    files: list[Path] = []
    for folder in [ROOT / "03_modules", COMPARISON_RUNS_PATH]:
        if folder.exists():
            files.extend(sorted(folder.glob("*.md")))
    return files


def is_valid_model_name(model_name: str) -> bool:
    if not model_name:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._")
    return all(ch in allowed for ch in model_name)


def validate_config(path: Path) -> list[tuple[str, bool, str]]:
    env_values = parse_dotenv(path)
    model = env_values.get("PHOM_MODEL", "")
    api_key = env_values.get("OPENAI_API_KEY", "")
    checks = [
        ("env file loaded", path.exists(), f"Path: {path}"),
        ("valid model name", is_valid_model_name(model), f"PHOM_MODEL={model or '(unset)'}"),
        ("API config looks correct", bool(api_key and api_key.startswith("sk-")), "OPENAI_API_KEY present and shaped like an API key"),
    ]
    return checks


def run_build(module_id: str, mode: str) -> tuple[int, str, str, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / "build_module.py"), module_id]
    env = os.environ.copy()

    if mode == "dry-run":
        cmd.append("--dry-run")
    else:
        reasoning_effort = MODE_TO_MODEL[mode]
        upsert_dotenv(DOTENV_PATH, "PHOM_REASONING_EFFORT", reasoning_effort)
        env["PHOM_REASONING_EFFORT"] = reasoning_effort

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    debug_cmd = " ".join(cmd)
    return proc.returncode, proc.stdout, proc.stderr, debug_cmd


def unified_diff(a: str, b: str, a_label: str, b_label: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            a.splitlines(),
            b.splitlines(),
            fromfile=a_label,
            tofile=b_label,
            lineterm="",
        )
    )


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
        compare_files = list_compare_files()

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total module count", len(modules))
        c2.metric("Completed modules", len(built))
        c3.metric("Missing modules", len(missing))
        c4.metric("Latest generated module", get_latest_generated_module(modules))
        c5.metric("Comparison runs available", len(compare_files))

    with tab_build:
        st.subheader("Selected module metadata")
        st.json(selected_module)
        st.write(f"**Selected reasoning mode:** `{selected_mode}`")
        preview_cmd = [sys.executable, str(ROOT / "scripts" / "build_module.py"), selected_module_id]
        if selected_mode == "dry-run":
            preview_cmd.append("--dry-run")

        col1, col2 = st.columns(2)
        run_action = None
        if col1.button("Build module", type="primary"):
            run_action = selected_mode if selected_mode != "dry-run" else "API medium"
        if col2.button("Dry run"):
            run_action = "dry-run"

        if run_action:
            with st.spinner(f"Running {run_action} for {selected_module_id}..."):
                code, stdout, stderr, debug_cmd = run_build(selected_module_id, run_action)
            st.markdown("### Debug")
            st.code(debug_cmd, language="bash")
            st.caption("Command output")
            st.code(stdout or "<no stdout>")
            if stderr:
                st.code(stderr)
            if code == 0:
                st.success("Build completed.")
            else:
                st.error(f"Build failed (exit code {code}).")

        env_values = parse_dotenv(DOTENV_PATH)
        st.markdown("### Debug")
        st.write(f"- current PHOM_MODEL: `{env_values.get('PHOM_MODEL', '(unset)')}`")
        st.write(f"- current PHOM_REASONING_EFFORT: `{env_values.get('PHOM_REASONING_EFFORT', '(unset)')}`")
        st.write(f"- exact subprocess command: `{ ' '.join(preview_cmd) }`")
        if st.button("Validate Config"):
            checks = validate_config(DOTENV_PATH)
            for label, ok, detail in checks:
                if ok:
                    st.success(f"{label}: {detail}")
                else:
                    st.error(f"{label}: {detail}")
        st.info("No API keys are shown or required in this UI.")

    with tab_review:
        st.subheader("Module markdown")
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
            c1.text_area(f"A: {left_label}", value=left_text, height=320)
            c2.text_area(f"B: {right_label}", value=right_text, height=320)

            st.subheader("Basic text diff")
            diff_text = unified_diff(left_text, right_text, left_label, right_label)
            st.code(diff_text or "No differences.", language="diff")


if __name__ == "__main__":
    main()
