from __future__ import annotations

import re
from datetime import datetime

from .paths import ANSWERS_JSONL_PATH, QUESTION_BANK_PATH, USER_DATASET_PATH
from .storage import append_jsonl, read_json_file, read_text, write_json_file


def _slugify(text: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return clean or "general"


def _extract_questions_from_text(text: str) -> list[str]:
    candidates: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        normalized = re.sub(r"^#{1,6}\s*", "", line).strip()
        normalized = re.sub(r"^[-*+]\s+", "", normalized).strip()
        normalized = re.sub(r"^\d+[.)]\s+", "", normalized).strip()
        if not normalized:
            continue
        looks_question = normalized.endswith("?")
        numbered = bool(re.match(r"^\d+[.)]\s+", line))
        bullet = bool(re.match(r"^[-*+]\s+", line))
        heading = line.startswith("#")
        if looks_question or numbered or bullet or (heading and "?" in normalized):
            candidates.append(normalized)
    seen: set[str] = set()
    deduped: list[str] = []
    for c in candidates:
        key = c.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return deduped


def save_question_bank(question_bank: list[dict]) -> None:
    write_json_file(QUESTION_BANK_PATH, question_bank)


def load_question_bank(modules: list[dict], root) -> list[dict]:
    existing = read_json_file(QUESTION_BANK_PATH, [])
    if isinstance(existing, list) and existing:
        return existing

    bootstrapped: list[dict] = []
    for module in modules:
        module_id = module["id"]
        domain = module_id.split("_")[0] if "_" in module_id else module_id
        review_path = root / module["review_file"]
        for idx, q in enumerate(_extract_questions_from_text(read_text(review_path)), start=1):
            q_id = f"{module_id}_{idx:03d}_{_slugify(q)[:24]}"
            bootstrapped.append({"question_id": q_id, "domain": domain, "module_id": module_id, "question": q, "why_needed": "Bootstrapped from review questions", "priority": "medium", "status": "open"})

    save_question_bank(bootstrapped)
    return bootstrapped

def append_answer(answer: dict) -> None:
    append_jsonl(ANSWERS_JSONL_PATH, answer)

def load_saved_answers(domain: str, module_id: str) -> list[dict]:
    saved_answers: list[dict] = []
    if not ANSWERS_JSONL_PATH.exists():
        return saved_answers
    for line in ANSWERS_JSONL_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = __import__('json').loads(line)
        except __import__('json').JSONDecodeError:
            continue
        if row.get("module_id") == module_id and row.get("domain") == domain:
            saved_answers.append(row)
    return saved_answers

def make_custom_question_id(module_id: str) -> str:
    safe_module = re.sub(r"[^a-zA-Z0-9_]+", "_", module_id.strip().lower()).strip("_") or "module"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"custom_{safe_module}_{ts}"

def append_custom_question(question_bank: list[dict], domain: str, module_id: str, question: str, why_needed: str, priority: str) -> dict:
    new_question = {"question_id": make_custom_question_id(module_id), "domain": domain, "module_id": module_id, "question": question.strip(), "why_needed": why_needed.strip(), "priority": priority, "status": "open", "source": "user_custom"}
    question_bank.append(new_question)
    save_question_bank(question_bank)
    return new_question

def append_user_dataset_entry(domain: str, module_id: str, entry: str) -> None:
    USER_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    block = f"\n\n## {stamp} | domain={domain} | module={module_id}\n\n{entry.strip()}\n"
    with USER_DATASET_PATH.open("a", encoding="utf-8") as f:
        f.write(block)
