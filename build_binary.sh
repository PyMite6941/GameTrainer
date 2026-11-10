#!/bin/bash
# Build a one-file desktop binary for GameTrainer (Linux / Raspberry Pi / desktop).
# Not for mobile — desktop only.
#
#   chmod +x build_binary.sh
#   ./build_binary.sh
#
# Output: dist/gametrainer  (single-file executable)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

VENV="${REPO_DIR}/.venv"
if [[ ! -x "$VENV/bin/python" ]]; then
    echo "Creating virtualenv..."
    python3 -m venv "$VENV"
fi

# Activate
source "$VENV/bin/activate"

echo "Installing/updating runtime dependencies..."
pip install --upgrade pip
pip install numpy opencv-python pygame pandas

echo "Installing PyInstaller..."
pip install pyinstaller

echo "Building one-file binary..."
pyinstaller gametrainer.spec --clean --noconfirm

echo ""
echo "Build complete: $REPO_DIR/dist/gametrainer"
echo "Run: ./dist/gametrainer config/games/console_generic.json --device 0"
echo "     ./dist/gametrainer --build-replay --db ./data/gameplay.db"
echo "     ./dist/gametrainer ./data/replays/replay.json"
