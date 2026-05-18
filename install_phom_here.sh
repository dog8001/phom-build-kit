#!/usr/bin/env bash
set -e

# PHOM installer for Mac/Linux
# Usage:
#   1) Put PHOM_Build_Kit_v3_seeded_installer.zip inside your QI System folder
#   2) Run from that folder:
#      bash install_phom_here.sh
#
# If you run it from another folder, it installs PHOM there.

ZIP_NAME="PHOM_Build_Kit_v3_seeded_installer.zip"
TARGET_DIR="PHOM_Build_Kit_v3_seeded_installer"

echo "PHOM installer"
echo "Current folder:"
pwd
echo ""

if [ ! -f "$ZIP_NAME" ]; then
  echo "Could not find $ZIP_NAME in current folder."
  echo ""
  echo "Put this zip in your QI System folder, for example:"
  echo '  /Users/pierrecarlsson/Documents/QI System/'
  echo ""
  echo "Then run:"
  echo "  cd \"/Users/pierrecarlsson/Documents/QI System\""
  echo "  bash install_phom_here.sh"
  exit 1
fi

if [ -d "$TARGET_DIR" ]; then
  echo "Folder already exists: $TARGET_DIR"
  echo "I will not overwrite it."
  echo "Rename or remove it if you want a clean reinstall."
  exit 1
fi

echo "Unzipping $ZIP_NAME..."
unzip -q "$ZIP_NAME"

echo ""
echo "Installed folder:"
echo "$(pwd)/$TARGET_DIR"
echo ""

cd "$TARGET_DIR"

echo "Creating Python virtual environment..."
python3 -m venv .venv

echo "Activating venv and installing requirements..."
source .venv/bin/activate
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "1) Add your OpenAI API key:"
echo "   open \"$(pwd)/.env\""
echo ""
echo "2) After saving the key, run:"
echo "   cd \"$(pwd)\""
echo "   source .venv/bin/activate"
echo "   python3 scripts/build_module.py L0_01_life_timeline"
echo ""
echo "Or run the seeded quickstart:"
echo "   bash scripts/quickstart_seeded.sh"
