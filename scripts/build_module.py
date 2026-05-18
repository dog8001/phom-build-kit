#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def load_modules() -> list[dict]:
    return json.loads(read(ROOT / "00_architecture" / "PHOM_Module_List_v1.json"))


def find_module(module_id: str) -> dict:
    for m in load_modules():
        if m["id"] == module_id:
            return m
    raise SystemExit(f"Unknown module id: {module_id}")


def call_model(client: OpenAI, model: str, system_prompt: str, user_prompt: str) -> str:
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.output_text


def extract_questions(final_module: str, module_title: str) -> str:
    marker = "## 8. Open questions for Pierre"
    if marker in final_module:
        return f"# Review Questions — {module_title}\n\n" + final_module.split(marker, 1)[1].split("## 9.", 1)[0].strip()
    return f"# Review Questions — {module_title}\n\nNo explicit questions extracted. Review module manually."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module_id", help="Module id from 00_architecture/PHOM_Module_List_v1.json")
    parser.add_argument("--skip-critic", action="store_true", help="Only run builder pass")
    parser.add_argument("--dry-run", action="store_true", help="Create placeholder module/review outputs without API calls")
    args = parser.parse_args()

    module = find_module(args.module_id)
    model = os.getenv("PHOM_MODEL", "gpt-5.5-thinking")

    if args.dry_run:
        header = f"<!-- Generated: {datetime.now().isoformat(timespec='seconds')} | Module: {module['id']} | Mode: dry-run -->\n\n"
        dry_content = f"""# {module['title']}

## Dry-run placeholder

- **Module ID:** {module['id']}
- **Goal:** {module['goal']}
- **Model setting (ignored in dry-run):** {model}

No API call was made. This file confirms wiring and output paths.
"""
        write(ROOT / module["output_file"], header + dry_content)
        write(
            ROOT / module["review_file"],
            f"# Review Questions — {module['title']}\n\n- Dry-run mode: no generated questions.\n",
        )
        print(f"Dry-run complete for {module['id']}.")
        print(f"Saved: {module['output_file']}")
        print(f"Saved: {module['review_file']}")
        return

    if load_dotenv:
        load_dotenv(ROOT / ".env")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY missing. Copy .env.example to .env and add your key.")

    try:
        from openai import OpenAI
    except ImportError as e:
        raise SystemExit("Missing dependency: openai. Run: pip install -r requirements.txt") from e

    client = OpenAI(api_key=api_key)

    architecture = read(ROOT / "00_architecture" / "PHOM_Architecture_v1.md")
    known_seed = read(ROOT / "01_input" / "Pierre_Known_Context_Seed_v1.md")
    evidence = read(ROOT / "01_input" / "Pierre_Evidence_Base.md")
    profiles = read(ROOT / "01_input" / "Existing_Profiles.md")
    corpus = read(ROOT / "01_input" / "Text_Corpus.md")

    builder_prompt = read(ROOT / "02_prompts" / "module_builder_prompt.md").replace("{module_title}", module["title"])
    critic_prompt = read(ROOT / "02_prompts" / "module_critic_prompt.md").replace("{module_title}", module["title"])
    reviser_prompt = read(ROOT / "02_prompts" / "module_reviser_prompt.md")

    user_prompt = f"""
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
"""

    print(f"Building module: {module['id']} — {module['title']}")
    draft = call_model(client, model, builder_prompt, user_prompt)
    write(ROOT / "06_logs" / f"{module['id']}_draft.md", draft)

    if args.skip_critic:
        final = draft
        critique = ""
    else:
        critique_user_prompt = f"""
Module goal:
{module['goal']}

Draft module:
{draft}

Critique this draft according to PHOM standards.
"""
        print("Running critique pass...")
        critique = call_model(client, model, critic_prompt, critique_user_prompt)
        write(ROOT / "06_logs" / f"{module['id']}_critique.md", critique)

        revise_user_prompt = f"""
Original draft:
{draft}

Critique:
{critique}

Revise the module into final form.
"""
        print("Running revision pass...")
        final = call_model(client, model, reviser_prompt, revise_user_prompt)

    header = f"<!-- Generated: {datetime.now().isoformat(timespec='seconds')} | Module: {module['id']} | Model: {model} -->\n\n"
    write(ROOT / module["output_file"], header + final)

    questions = extract_questions(final, module["title"])
    write(ROOT / module["review_file"], questions)

    print(f"Saved: {module['output_file']}")
    print(f"Saved: {module['review_file']}")


if __name__ == "__main__":
    main()
