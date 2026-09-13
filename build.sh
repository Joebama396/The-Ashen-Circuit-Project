#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/vendor${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
mkdir -p build dist AppDir
python3 -m PyInstaller --noconfirm --clean --onefile --windowed --name ashen-circuit \
  --add-data "assets/characters/party_motion_v1.png:assets/characters" \
  --add-data "assets/audio/battle_theme_1.mp3:assets/audio" \
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
ARCH=x86_64 "$ROOT/appimagetool-x86_64.AppImage" --appimage-extract-and-run AppDir "dist/The_Ashen_Circuit-1.3-x86_64.AppImage"
chmod +x "dist/The_Ashen_Circuit-1.3-x86_64.AppImage"
cp Play-The-Ashen-Circuit.sh dist/Play-The-Ashen-Circuit.sh
cp START_HERE.txt dist/START_HERE.txt
chmod +x dist/Play-The-Ashen-Circuit.sh
# An extracted, portable build works without FUSE, Python, or package installs.
mkdir -p build/portable/The-Ashen-Circuit
cp -a AppDir/. build/portable/The-Ashen-Circuit/
cp README.md build/portable/The-Ashen-Circuit/README.md
cp START_HERE.txt build/portable/The-Ashen-Circuit/START_HERE.txt
portable_temp="dist/The_Ashen_Circuit-1.3-Linux-Portable.writing.tar.gz"
tar -czf "$portable_temp" -C build/portable The-Ashen-Circuit
gzip -t "$portable_temp"
mv "$portable_temp" dist/The_Ashen_Circuit-1.3-Linux-Portable.tar.gz
# Keep the primary download self-contained: the launcher and its matching
# AppImage always travel together, even when browsers block standalone scripts.
zip_temp="dist/The_Ashen_Circuit-1.3-Ubuntu.writing.zip"
zip -j -q "$zip_temp" \
  dist/The_Ashen_Circuit-1.3-x86_64.AppImage \
  dist/Play-The-Ashen-Circuit.sh \
  dist/START_HERE.txt
unzip -tq "$zip_temp"
mv "$zip_temp" dist/The_Ashen_Circuit-1.3-Ubuntu.zip
(
  cd dist
  sha256sum The_Ashen_Circuit-1.3-x86_64.AppImage \
    Play-The-Ashen-Circuit.sh \
    The_Ashen_Circuit-1.3-Ubuntu.zip \
    The_Ashen_Circuit-1.3-Linux-Portable.tar.gz \
    START_HERE.txt \
    > SHA256SUMS-1.3.txt
)
