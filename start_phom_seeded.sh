#!/usr/bin/env bash
set -e

# Run this after PHOM has been installed and .env has your API key.

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "No .venv found. Creating it now..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

echo "Building first seeded module..."
python3 scripts/build_module.py L0_01_life_timeline
python3 scripts/assemble_master.py

echo ""
echo "Done."
echo "Open results:"
echo "  open 03_modules/L0_01_life_timeline.md"
echo "  open 04_review_questions/L0_01_life_timeline_questions.md"
echo "  open 05_master/PHOM_Master_v1.md"
