#!/usr/bin/env bash
# Empaqueta EcoDICOM.app en macOS (debe ejecutarse EN una Mac).
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Error: este script solo corre en macOS."
  echo "En Windows use build_exe.bat. Para CI, vea .github/workflows/build-macos.yml"
  exit 1
fi

PYTHON="${PYTHON:-python3}"
if [[ ! -d .venv ]]; then
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt pyinstaller

rm -rf build/EcoDICOM dist/EcoDICOM dist/EcoDICOM.app
pyinstaller --noconfirm --clean EcoDICOM-macos.spec

echo ""
echo "Listo:"
echo "  $(pwd)/dist/EcoDICOM.app"
echo ""
echo "Datos de usuario (DICOM + SQLite):"
echo "  ~/Documents/EcoDICOM/"
echo ""
echo "Para abrir:"
echo "  open dist/EcoDICOM.app"
echo ""
echo "Nota: la primera vez macOS puede bloquear la app (sin firma Apple)."
echo "  Clic derecho > Abrir, o:"
echo "  xattr -cr dist/EcoDICOM.app"
