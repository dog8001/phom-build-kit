import os
import subprocess
import sys
from datetime import datetime

import streamlit as st

from .paths import COMPARISON_RUNS_PATH, ROOT, RUN_OVERRIDES_DIR
from .storage import read_env_file, read_text
from .utils import MODE_TO_REASONING


def list_compare_files() -> list:
    files = []
    for folder in [COMPARISON_RUNS_PATH, ROOT / "03_modules"]:
        if folder.exists():
            files.extend(sorted(folder.glob("*.md")))
    return files


def build_user_prompt(module: dict) -> str:
    architecture = read_text(ROOT / "00_architecture" / "PHOM_Architecture_v1.md")
    known_seed = read_text(ROOT / "01_input" / "Pierre_Known_Context_Seed_v1.md")
    evidence = read_text(ROOT / "01_input" / "Pierre_Evidence_Base.md")
    profiles = read_text(ROOT / "01_input" / "Existing_Profiles.md")
    corpus = read_text(ROOT / "01_input" / "Text_Corpus.md")
    return f"""
Current module:
ID: {module['id']}
Title: {module['title']}
Goal: {module['goal']}

PHOM architecture:
{architecture}

Known context seed:
{known_seed}

Evidence base:
{evidence}

Existing profiles:
{profiles}

Text corpus:
{corpus}

Build only this module.
""".strip()


def run_build(module_id: str, mode: str, prompt_override: str | None = None):
    cmd = [sys.executable, str(ROOT / "scripts" / "build_module.py"), module_id]
    env = os.environ.copy()
    if mode == "dry-run":
        cmd.append("--dry-run")
    else:
        env["PHOM_REASONING_EFFORT"] = MODE_TO_REASONING[mode]
    if prompt_override:
        env["PHOM_USER_PROMPT_OVERRIDE"] = prompt_override
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr, cmd


def save_run_prompt(module_id: str, mode: str, model: str, reasoning: str, prompt: str, command: list[str]):
    RUN_OVERRIDES_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RUN_OVERRIDES_DIR / f"{ts}_{module_id}_{mode.replace(' ', '_')}_{reasoning}.md"
    content = f"# Run Prompt Snapshot\n\n- Timestamp: {datetime.now().isoformat(timespec='seconds')}\n- Module: {module_id}\n- Mode: {mode}\n- Model: {model}\n- Reasoning effort: {reasoning}\n- Command: `{' '.join(command)}`\n\n## Prompt Used\n\n```\n{prompt}\n```\n"
    path.write_text(content, encoding="utf-8")
    return path


def render_control_panel_page(module_ids: list[str], module_lookup: dict[str, dict]) -> None:
    st.title("Control Panel")
    selected_module_id = st.selectbox("Select module", module_ids, key="cp_module")
    selected_mode = st.selectbox("Select mode", ["dry-run", "API low", "API medium", "API high", "API xhigh"], key="cp_mode")
    selected_module = module_lookup[selected_module_id]
    config_model = os.getenv("PHOM_MODEL") or read_env_file(ROOT / ".env").get("PHOM_MODEL", "gpt-5.5")
    selected_reasoning = "none" if selected_mode == "dry-run" else MODE_TO_REASONING[selected_mode]
    command_preview = [sys.executable, str(ROOT / "scripts" / "build_module.py"), selected_module_id]
    if selected_mode == "dry-run":
        command_preview.append("--dry-run")
    prompt_value = st.text_area("Exact prompt/instruction", value=build_user_prompt(selected_module), height=260, key="prompt_override")
    approved = st.checkbox("I approve this run", value=False)
    st.subheader("Preview / Edit / Approve")
    st.json(selected_module)
    st.write(f"**Model:** `{config_model}`")
    st.write(f"**Reasoning effort:** `{selected_reasoning}`")
    st.code(" ".join(command_preview), language="bash")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Run dry-run", disabled=selected_mode != "dry-run"):
            saved = save_run_prompt(selected_module_id, selected_mode, config_model, selected_reasoning, prompt_value, command_preview)
            code, stdout, stderr, executed_cmd = run_build(selected_module_id, selected_mode, prompt_override=prompt_value)
            st.code(" ".join(executed_cmd)); st.code(stdout or "<no stdout>")
            if stderr: st.code(stderr)
            st.info(f"Saved prompt snapshot: {saved.relative_to(ROOT)}")
            st.success("Dry-run finished." if code == 0 else f"Dry-run failed ({code}).")
    with c2:
        if st.button("Run API build", type="primary", disabled=not (selected_mode != "dry-run" and approved)):
            saved = save_run_prompt(selected_module_id, selected_mode, config_model, selected_reasoning, prompt_value, command_preview)
            code, stdout, stderr, executed_cmd = run_build(selected_module_id, selected_mode, prompt_override=prompt_value)
            st.code(" ".join(executed_cmd)); st.code(stdout or "<no stdout>")
            if stderr: st.code(stderr)
            st.info(f"Saved prompt snapshot: {saved.relative_to(ROOT)}")
            st.success("Build completed." if code == 0 else f"Build failed ({code}).")

    st.subheader("Review Outputs")
    st.text_area("Module output", value=read_text(ROOT / selected_module["output_file"]) or "No module output found.", height=220)
    st.text_area("Review questions", value=read_text(ROOT / selected_module["review_file"]) or "No review questions found.", height=180)
    st.subheader("Compare Runs")
    files = list_compare_files()
    if files:
        labels = [str(p.relative_to(ROOT)) for p in files]
        left_label = st.selectbox("File A", labels, index=0, key="cmp_a")
        right_label = st.selectbox("File B", labels, index=1 if len(labels) > 1 else 0, key="cmp_b")
        c1, c2 = st.columns(2)
        c1.text_area(f"A: {left_label}", value=read_text(ROOT / left_label), height=300)
        c2.text_area(f"B: {right_label}", value=read_text(ROOT / right_label), height=300)
