#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:?Usage: tests/run-composite.sh /path/to/patched/quixjs}"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
for TEST in destination_out source_over; do
  "${CC:-cc}" -O2 -ffunction-sections -fdata-sections -I"$SRC/runtime" \
    "$ROOT/tests/test_$TEST.c" "$SRC/runtime/gfx/surface.c" \
    -Wl,--gc-sections -lm -o "$OUT/$TEST"
  "$OUT/$TEST"
done
