#!/bin/bash
# Assembles the CrossCode port for quixjs (aarch64). No game data in the repo.
#
#   ./install.sh <port dir, e.g. /mnt/SDCARD/Roms/PORTS/crosscode-qx> [assets dir]
#
# <assets dir> is the game's assets/ folder (PC release or the assets/ of the
# Android OBB: sudo mount -o loop,ro -t vfat main.1.*.obb /mnt/obb).
set -euo pipefail

GAMEDIR=${1:?usage: install.sh <port dir> [assets dir]}
ASSETS=${2:-}
HERE=$(cd "$(dirname "$0")" && pwd)
# Optional controlled A/B of quixjs releases (0.2.2 remains the proven
# baseline). QUIXJS_BIN installs a locally rebuilt raster-optimized runtime.
QUIXJS_VERSION=${QUIXJS_VERSION:-0.2.2}
URL="https://github.com/lowlevel-1989/quixjs/releases/download/${QUIXJS_VERSION}/quixjs-${QUIXJS_VERSION}-linux-aarch64.tar.gz"

mkdir -p "$GAMEDIR/gamedata"

# 1. runtime
if [ ! -x "$GAMEDIR/quixjs.aarch64" ] || [ ! -d "$GAMEDIR/libs.aarch64" ] || \
   [ "${QUIXJS_REINSTALL:-0}" = 1 ] || [ -n "${QUIXJS_BIN:-}" ]; then
  tmp=$(mktemp -d)
  echo "downloading quixjs ${QUIXJS_VERSION} (aarch64)"
  curl -fL --retry 3 -o "$tmp/q.tar.gz" "$URL"
  tar xzf "$tmp/q.tar.gz" -C "$tmp"
  src="$tmp/quixjs-${QUIXJS_VERSION}-linux-aarch64"
  if [ -n "${QUIXJS_BIN:-}" ]; then
    [ -f "$QUIXJS_BIN" ] || { echo "No local quixjs binary: $QUIXJS_BIN" >&2; exit 1; }
    install -m755 "$QUIXJS_BIN" "$GAMEDIR/quixjs.aarch64"
  else
    install -m755 "$src/quixjs" "$GAMEDIR/quixjs.aarch64"
  fi
  rm -rf "$GAMEDIR/libs.aarch64" "$GAMEDIR/fonts"
  cp -r "$src/libs" "$GAMEDIR/libs.aarch64"
  cp -r "$src/fonts" "$GAMEDIR/fonts"
  rm -rf "$tmp"
fi

# 2. game
if [ -n "$ASSETS" ]; then
  [ -f "$ASSETS/js/game.compiled.js" ] || { echo "no $ASSETS/js/game.compiled.js"; exit 1; }
  mkdir -p "$GAMEDIR/gamedata/assets"
  echo "copying assets (this is ~900 MB)"
  cp -a "$ASSETS/." "$GAMEDIR/gamedata/assets/"
fi
[ -f "$GAMEDIR/gamedata/assets/js/game.compiled.js" ] || {
  echo "assets missing: put the game's assets/ in $GAMEDIR/gamedata/assets/"; exit 1; }

# 3. the port's own files
install -m644 "$HERE/ccx-boot.js" "$GAMEDIR/gamedata/assets/ccx-boot.js"
install -m644 "$HERE/port.toml"   "$GAMEDIR/port.toml"
install -m755 "$HERE/CrossCode.sh" "$(dirname "$GAMEDIR")/CrossCode.sh"
echo "ok: $(dirname "$GAMEDIR")/CrossCode.sh + $GAMEDIR"
