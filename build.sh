#!/usr/bin/env bash
# build.sh — Build Canvas Study Help for macOS or Linux
# Usage: bash build.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Canvas Study Help — Build Script ==="
echo "Platform: $(uname -s)"

# 1. Ensure Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Install Python 3.8+ and try again." >&2
    exit 1
fi
PYTHON="python3"
echo "Python: $($PYTHON --version)"

# 2. Create/activate a virtualenv (optional but clean)
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment…"
    $PYTHON -m venv .venv
fi
source .venv/bin/activate

# 3. Install build dependencies
echo "Installing PyInstaller…"
pip install --quiet --upgrade pip
pip install --quiet pyinstaller

# 4. Build
echo "Building with PyInstaller…"
pyinstaller canvas-study.spec --noconfirm

echo ""
echo "=== Build complete! ==="

if [ "$(uname -s)" = "Darwin" ]; then
    echo "App bundle: dist/CanvasStudyHelp.app"
    echo "Tip: drag CanvasStudyHelp.app to /Applications"
else
    echo "Executable:  dist/CanvasStudyHelp"
    echo "Tip: copy to ~/bin/ or /usr/local/bin/ for system-wide access"
fi
