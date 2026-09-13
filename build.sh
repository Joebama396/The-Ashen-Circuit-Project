#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/vendor${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
mkdir -p build dist AppDir
python3 -m PyInstaller --noconfirm --clean --onefile --windowed --name ashen-circuit \
  --add-data "assets/characters/party_overworld_v4.png:assets/characters" \
  game.py
mkdir -p AppDir/usr/bin AppDir/usr/share/applications AppDir/usr/share/icons/hicolor/256x256/apps
cp dist/ashen-circuit AppDir/usr/bin/ashen-circuit
cp icon.png AppDir/ashen-circuit.png
cp icon.png AppDir/usr/share/icons/hicolor/256x256/apps/ashen-circuit.png
cp ashen-circuit.desktop AppDir/ashen-circuit.desktop
cp AppRun AppDir/AppRun
chmod +x AppDir/AppRun AppDir/usr/bin/ashen-circuit
if [[ ! -x "$ROOT/appimagetool-x86_64.AppImage" ]]; then
  echo "Missing appimagetool-x86_64.AppImage in project root" >&2
  exit 1
fi
ARCH=x86_64 "$ROOT/appimagetool-x86_64.AppImage" --appimage-extract-and-run AppDir "dist/The_Ashen_Circuit-x86_64.AppImage"
chmod +x "dist/The_Ashen_Circuit-x86_64.AppImage"
