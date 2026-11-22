#!/bin/sh
# Fixed-scene A/B runner for CrossCode on quixjs (TSPS).
# Usage: run-ab.sh LABEL BINARY LIBDIR [MEASURE_SECONDS]
# Restores the pristine save before each arm, loads save preset 3
# (autumn.entrance), dismisses the one-time dialog, then samples --fps.
# Keeps the pristine baseline at <port>/perf-ab/saves-backup/cc.save*.
set -eu
LABEL=$1; BIN=$2; LIBS=$3; SECS=${4:-90}
P=/mnt/SDCARD/Roms/PORTS/crosscode-qx
BASE=${AB_BASE:-$P/perf-ab}
OUT=$BASE/runs/$LABEL
mkdir -p "$OUT"
# Every arm starts from the identical saved game state.
cp -f "$BASE"/saves-backup/cc.save* "$P/gamedata/assets/"
SOCK=/tmp/ccab-$LABEL.sock
rm -f "$SOCK"
cd "$P"
export QUIXJS_FONT="$P/fonts/DejaVuSans-Bold.ttf"
export LD_LIBRARY_PATH="$LIBS:$P/libs.aarch64:${LD_LIBRARY_PATH:-}"
nohup setsid "$BIN" -b dummy --debug="$SOCK" --fps -c port.toml > "$OUT/log.txt" 2>&1 < /dev/null &
PID=$!
echo "$PID" > "$OUT/pid"
C="python3 $P/console.py -s $SOCK"
sleep 25                                   # title + asset load
$C eval 'sc.savePreset.load(3); 1' > "$OUT/load.txt" 2>&1
sleep 14                                   # preset scene load
$C press Enter >/dev/null 2>&1 || true
sleep 3
$C press Enter >/dev/null 2>&1 || true
sleep 8
$C eval 'ig.game.mapName' > "$OUT/map.txt" 2>&1 || true
$C shot "$OUT/shot-start.png" >/dev/null 2>&1 || true
sleep "$SECS"                              # measured steady window
$C shot "$OUT/shot-end.png" >/dev/null 2>&1 || true
kill "$PID" 2>/dev/null || true
sleep 2
kill -9 "$PID" 2>/dev/null || true
grep '^FPS:' "$OUT/log.txt" > "$OUT/fps.txt" || true
MAP=$(tail -1 "$OUT/map.txt" 2>/dev/null || echo unknown)
[ "$MAP" = "autumn.entrance" ] || { echo "SCENE MISMATCH: $MAP"; exit 2; }
[ -s "$OUT/fps.txt" ] || { echo "NO FPS SAMPLES"; exit 3; }
echo "OK label=$LABEL map=$MAP samples=$(wc -l < "$OUT/fps.txt")"
