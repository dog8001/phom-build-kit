from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def write_json_list(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_user_domain_module(user_domains_path: Path, domain: str, module_id: str) -> None:
    rows = load_json_list(user_domains_path)
    if any(r.get("domain") == domain and r.get("module_id") == module_id for r in rows if isinstance(r, dict)):
        return
    rows.append({
        "domain": domain,
        "module_id": module_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": "user_created",
    })
    write_json_list(user_domains_path, rows)


def make_custom_question_id(module_id: str) -> str:
    safe_module = re.sub(r"[^a-zA-Z0-9_]+", "_", module_id.strip().lower()).strip("_") or "module"
    return f"custom_{safe_module}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def append_custom_question(question_bank_path: Path, domain: str, module_id: str, question: str, why_needed: str, priority: str) -> dict:
    rows = load_json_list(question_bank_path)
    row = {
        "question_id": make_custom_question_id(module_id),
        "domain": domain,
        "module_id": module_id,
        "question": question.strip(),
        "why_needed": why_needed.strip(),
        "priority": priority,
        "status": "open",
        "source": "user_custom",
    }
    rows.append(row)
    write_json_list(question_bank_path, rows)
    return row


def append_answer(answers_jsonl_path: Path, payload: dict) -> None:
    answers_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with answers_jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
