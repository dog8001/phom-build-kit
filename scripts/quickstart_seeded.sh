#!/usr/bin/env bash
set -e

echo "Running seeded PHOM first module..."
python3 scripts/build_module.py L0_01_life_timeline
python3 scripts/assemble_master.py

echo ""
echo "Done."
echo "Open:"
echo "  03_modules/L0_01_life_timeline.md"
echo "  04_review_questions/L0_01_life_timeline_questions.md"
echo "  05_master/PHOM_Master_v1.md"
