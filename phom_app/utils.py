from __future__ import annotations

import os
import re

from .paths import ROOT
from .storage import read_env_file

MODE_TO_REASONING = {
    "API low": "low",
    "API medium": "medium",
    "API high": "high",
    "API xhigh": "xhigh",
}
VALID_REASONING_EFFORTS = set(MODE_TO_REASONING.values())


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
