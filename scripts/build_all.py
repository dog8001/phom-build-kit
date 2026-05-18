#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["first", "all"], default="first")
    parser.add_argument("--skip-critic", action="store_true")
    args = parser.parse_args()

    modules = json.loads((ROOT / "00_architecture" / "PHOM_Module_List_v1.json").read_text(encoding="utf-8"))

    if args.phase == "first":
        modules = [m for m in modules if m["layer"] in [0, 1, 2]]

    modules = sorted(modules, key=lambda m: m["priority"])

    for module in modules:
        cmd = [sys.executable, str(ROOT / "scripts" / "build_module.py"), module["id"]]
        if args.skip_critic:
            cmd.append("--skip-critic")
        print("\n" + "=" * 80)
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    print("\nAll selected modules built.")


if __name__ == "__main__":
    main()
