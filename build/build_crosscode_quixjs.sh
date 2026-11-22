#!/usr/bin/env bash
# Rebuild the quixjs ARM64 executable with the CrossCode Canvas2D fast paths.
# The game data and installed port are not modified.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${QUIXJS_VERSION:-0.2.2}"
SRC="${QUIXJS_SRC:-$ROOT/build/quixjs-$VERSION}"
OUT="${QUIXJS_OUTPUT:-$ROOT/build/quixjs-crosscode.aarch64}"
if [ ! -e "$SRC/.git" ]; then
  mkdir -p "$(dirname "$SRC")"
  git clone --depth 1 --branch "$VERSION" https://github.com/lowlevel-1989/quixjs.git "$SRC"
fi
cd "$SRC"
for PATCH in "$ROOT/patches/quixjs-crosscode-raster.patch" "$ROOT/patches/quixjs-crosscode-composite.patch"; do
  if git apply --check "$PATCH"; then
    git apply "$PATCH"
  elif git apply --reverse --check "$PATCH"; then
    echo "Already applied: $PATCH"
  else
    echo "Patch $PATCH does not apply to $SRC; verify the quixjs revision" >&2
    exit 1
  fi
done
# Upstream PortMaster target links JavaScriptCore and cross-compiles aarch64.
# The first build downloads the Debian buster sysroot and JSC dependencies.
make -j"${JOBS:-4}" PLATFORM=portmaster PM_ARCHES=aarch64 obj/portmaster/quixjs.aarch64
mkdir -p "$(dirname "$OUT")"
install -m755 obj/portmaster/quixjs.aarch64 "$OUT"
file "$OUT"
echo "Optimized runtime: $OUT"
echo 'QUIX_FAST_OPAQUE_BLIT=0 disables only the packed blit; compare separate builds for compositing.'
