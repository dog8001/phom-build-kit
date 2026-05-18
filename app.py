#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
MODULE_LIST_PATH = ROOT / "00_architecture" / "PHOM_Module_List_v1.json"
COMPARISON_RUNS_PATH = ROOT / "comparison_runs"
QUESTIONS_DIR = ROOT / "04_review_questions"
ANSWERS_DIR = ROOT / "07_answers"
RUN_OVERRIDES_DIR = ROOT / "08_run_overrides"
EVIDENCE_FILE = ROOT / "01_input" / "Pierre_Evidence_Base.md"
MASTER_DIR = ROOT / "05_master"

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


def write_env_file(path: Path, updates: dict[str, str]) -> None:
    existing = read_env_file(path)
    existing.update({k: v for k, v in updates.items() if v is not None})
    lines = [f"{k}={v}" for k, v in sorted(existing.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    ok = is_valid_model_name(model) and effort in VALID_REASONING_EFFORTS and bool(api_key)
    return ok, messages


def list_compare_files() -> list[Path]:
    files: list[Path] = []
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


def run_build(module_id: str, mode: str, prompt_override: str | None = None) -> tuple[int, str, str, list[str]]:
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


def save_run_prompt(module_id: str, mode: str, model: str, reasoning: str, prompt: str, command: list[str]) -> Path:
    RUN_OVERRIDES_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = f"{ts}_{module_id}_{mode.replace(' ', '_')}_{reasoning}.md"
    path = RUN_OVERRIDES_DIR / slug
    content = (
        f"# Run Prompt Snapshot\n\n"
        f"- Timestamp: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Module: {module_id}\n"
        f"- Mode: {mode}\n"
        f"- Model: {model}\n"
        f"- Reasoning effort: {reasoning}\n"
        f"- Command: `{' '.join(command)}`\n\n"
        "## Prompt Used\n\n"
        f"```\n{prompt}\n```\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


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


def render_questions_page(modules: list[dict], module_lookup: dict[str, dict]) -> None:
    st.header("Questions")
    module_ids = [m["id"] for m in modules]
    module_id = st.selectbox("Select module/domain", module_ids, key="q_module")

    question_path = QUESTIONS_DIR / f"{module_id}_questions.md"
    if not question_path.exists():
        fallback = module_lookup[module_id]["review_file"]
        question_path = ROOT / fallback

    text = read_text(question_path)
    if not text:
        st.info("No question file found for this module.")
        return

    questions = [ln.strip("- ").strip() for ln in text.splitlines() if ln.strip().startswith("-")]
    if not questions:
        st.text_area("Question source", value=text, height=240)
        return

    answer_file = ANSWERS_DIR / f"{module_id}_answers.json"
    existing = {}
    if answer_file.exists():
        existing = json.loads(answer_file.read_text(encoding="utf-8"))

    st.write(f"Loaded {len(questions)} questions from `{question_path.relative_to(ROOT)}`")
    answers: dict[str, str] = dict(existing)
    for idx, q in enumerate(questions, start=1):
        key = f"ans_{module_id}_{idx}"
        answers[q] = st.text_area(f"Q{idx}: {q}", value=existing.get(q, ""), key=key, height=100)

    if st.button("Save answers"):
        ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
        filtered = {k: v for k, v in answers.items() if v.strip()}
        answer_file.write_text(json.dumps(filtered, indent=2), encoding="utf-8")
        st.success(f"Saved {len(filtered)} partial/full answers to {answer_file.relative_to(ROOT)}")


def main() -> None:
    st.set_page_config(page_title="PHOM/QI Workspace v0.2", layout="wide")

    if not check_login():
        return

    modules = load_modules()
    module_lookup = {m["id"]: m for m in modules}
    module_ids = [m["id"] for m in modules]

    st.sidebar.title("PHOM/QI Workspace v0.2")
    page = st.sidebar.radio(
        "Navigate",
        ["Home / Dashboard", "PHOM Core", "Questions", "Evidence", "Control Panel", "Settings"],
    )

    if page == "Home / Dashboard":
        st.title("Home / Dashboard")
        built = [m for m in modules if (ROOT / m["output_file"]).exists()]
        missing = [m for m in modules if not (ROOT / m["output_file"]).exists()]
        c1, c2, c3 = st.columns(3)
        c1.metric("Module count", len(modules))
        c2.metric("Built modules", len(built))
        c3.metric("Missing modules", len(missing))
        st.write("Built:", [m["id"] for m in built] or "None")
        st.write("Missing:", [m["id"] for m in missing] or "None")

    elif page == "PHOM Core":
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

    elif page == "Questions":
        render_questions_page(modules, module_lookup)

    elif page == "Evidence":
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

    elif page == "Control Panel":
        st.title("Control Panel")
        selected_module_id = st.selectbox("Select module", module_ids, key="cp_module")
        selected_mode = st.selectbox("Select mode", ["dry-run", "API low", "API medium", "API high", "API xhigh"], key="cp_mode")
        selected_module = module_lookup[selected_module_id]

        config_model = os.getenv("PHOM_MODEL") or read_env_file(ROOT / ".env").get("PHOM_MODEL", "gpt-5.5")
        selected_reasoning = "none" if selected_mode == "dry-run" else MODE_TO_REASONING[selected_mode]
        command_preview = [sys.executable, str(ROOT / "scripts" / "build_module.py"), selected_module_id]
        if selected_mode == "dry-run":
            command_preview.append("--dry-run")

        default_prompt = build_user_prompt(selected_module)
        st.subheader("Preview / Edit / Approve")
        st.json(selected_module)
        st.write(f"**Model:** `{config_model}`")
        st.write(f"**Reasoning effort:** `{selected_reasoning}`")
        st.code(" ".join(command_preview), language="bash")

        prompt_value = st.text_area("Exact prompt/instruction", value=default_prompt, height=260, key="prompt_override")
        approved = st.checkbox("I approve this run", value=False)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Run dry-run", disabled=selected_mode != "dry-run"):
                saved = save_run_prompt(selected_module_id, selected_mode, config_model, selected_reasoning, prompt_value, command_preview)
                code, stdout, stderr, executed_cmd = run_build(selected_module_id, selected_mode, prompt_override=prompt_value)
                st.code(" ".join(executed_cmd))
                st.code(stdout or "<no stdout>")
                if stderr:
                    st.code(stderr)
                st.info(f"Saved prompt snapshot: {saved.relative_to(ROOT)}")
                st.success("Dry-run finished." if code == 0 else f"Dry-run failed ({code}).")
        with c2:
            can_run_api = selected_mode != "dry-run" and approved
            if st.button("Run API build", type="primary", disabled=not can_run_api):
                saved = save_run_prompt(selected_module_id, selected_mode, config_model, selected_reasoning, prompt_value, command_preview)
                code, stdout, stderr, executed_cmd = run_build(selected_module_id, selected_mode, prompt_override=prompt_value)
                st.code(" ".join(executed_cmd))
                st.code(stdout or "<no stdout>")
                if stderr:
                    st.code(stderr)
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

    elif page == "Settings":
        st.title("Settings")
        env_path = ROOT / ".env"
        env_values = read_env_file(env_path)

        model = st.text_input("PHOM_MODEL", value=os.getenv("PHOM_MODEL") or env_values.get("PHOM_MODEL", "gpt-5.5"))
        effort = st.selectbox("PHOM_REASONING_EFFORT", ["low", "medium", "high", "xhigh"], index=["low", "medium", "high", "xhigh"].index((os.getenv("PHOM_REASONING_EFFORT") or env_values.get("PHOM_REASONING_EFFORT", "medium"))))
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


if __name__ == "__main__":
    main()
