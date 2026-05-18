#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    modules = json.loads((ROOT / "00_architecture" / "PHOM_Module_List_v1.json").read_text(encoding="utf-8"))
    modules = sorted(modules, key=lambda m: m["priority"])

    parts = [
        "# PHOM Master v1",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Note",
        "This master document is assembled from individual PHOM modules. Edit modules first, then reassemble.",
        "",
    ]

    for m in modules:
        path = ROOT / m["output_file"]
        if path.exists():
            parts.append("\n---\n")
            parts.append(path.read_text(encoding="utf-8"))
        else:
            parts.append("\n---\n")
            parts.append(f"# {m['title']}\n\n_NOT BUILT YET: {m['id']}_\n")

    out = ROOT / "05_master" / "PHOM_Master_v1.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
