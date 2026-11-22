# Performance (TrimUI Smart Pro, SpruceOS, Mali-G57)

Measured with `quixjs --fps` (the line it prints once a second: JS time, present
time) and `--profile` (JavaScriptCore sampling profiler, 10 ms samples).

## Frame time by render size

| `IG_GAME_SCALE` | canvas | fps (title) | JS per frame | present |
| --- | --- | --- | --- | --- |
| 2 | 1136x640 | 9.9 | 96.9 ms | 3.7 ms |
| 1 | 568x320 | 22.6 | 41.8 ms | 2.3 ms |

Both runs with the same build and the same map. The port ships scale 1.

In game (cargo ship, light map) the same build reports ~56 fps with 15 ms of JS;
heavy outdoor maps sit around 20 fps with ~42 ms of JS. `present` stays at
~2.2 ms throughout, so the ceiling is the game's JavaScript, not the blitter or
the display path.

## Profiler (900 frames, dummy backend, 1850 samples)

```
quixjs C functions:
  19.9%  3685 ms   469046 calls   7.86 us  drawImage
  19.4%  3584 ms      499 calls 7182.41 us  decode (PNG, load time only)
   8.0%  1489 ms     9018 calls  165.11 us  fillRect
   0.8%   140 ms     1761 calls   79.71 us  clip

JIT tier of the sampled JS: Baseline 8.1%, DFG 18.9%, FTL 5.5%, LLInt 0.7%
```

`drawImage` is 7.9 us per call because the canvas is software (RGBA buffer in C):
that cost scales with the pixels drawn, which is why the render size is the
biggest lever. PNG decode is load-time only.

## What was tried and did not help

* CPU governor `performance`, big cores 1992 -> 2160 MHz: 21.4 fps vs 22.6 fps,
  i.e. noise. Restored to the SpruceOS default; the port is not frequency-bound.
* `js_memory` 256 MB: memory footprint ~460 MB RSS; lowering it is not a speed
  win, the allocation rate is small (~2.7 MB/s).

## Levers that keep the effects

* The game's *Options > Video* switches (lighting, weather, env-particles,
  speedlines) cut JS work and change the look; the port leaves them all on.
* `[hooks]` in `port.toml` can replace hot game functions with faster ones
  without touching the game files — the next step if 20 fps in heavy maps is not
  acceptable.

## Experimental optimizations (A/B, not device-verified)

The heavy outdoor route previously measured 41.8 ms of JS/Canvas work versus
2.3 ms presenting a frame. Do **not** claim this is a GPU bottleneck or
disable lighting, weather, particles or speedlines to hide it.

1. `port.toml` now gives quixjs's initially allocated canvas the same
   **568x320** size as the game's `IG_GAME_SCALE=1`. This avoids allocating
   the default 1136x640 scratch surface before the game resizes. Test that
   CrossCode's video options, framebuffer and saves still behave identically.
2. `ccx-boot.js` reuses the inert jQuery stub element instead of creating
   a new JavaScript object on each `$()`. The stub still ignores DOM operations.
3. `patches/quixjs-crosscode-raster.patch` adds a strictly optional
   `QUIX_FAST_OPAQUE_BLIT=1` path in quixjs 0.2.2's
   `runtime/gfx/raster.c`: four fully opaque RGBA pixels are copied together
   and four fully transparent pixels skipped together. Mixed-alpha pixels
   use the original blend function. It changes no effect toggles or resolution.
   The unmodified upstream binary ignores this flag.

To build an optimized ARM64 runtime on a Linux machine with Git, clang,
make and network access (first build downloads the sysroot and WebKit/JSC):

```sh
bash build/build_crosscode_quixjs.sh
QUIXJS_BIN="$PWD/build/quixjs-crosscode.aarch64" \
  ./install.sh /mnt/SDCARD/Roms/PORTS/crosscode-qx
```

The installer keeps quixjs **0.2.2** by default. For a separate, unverified
release comparison: `QUIXJS_VERSION=0.4.0 QUIXJS_REINSTALL=1 ./install.sh ...`
(which requires a backup of the previous binary first). To try 0.4.0 with
the source patch, set `QUIXJS_VERSION=0.4.0` during the build too.

For a meaningful experiment, enter the *same outdoor map* with the *same
effects enabled* and use two runs of equal duration:

```sh
# Edit/set these in CrossCode.sh / PortMaster's environment before launching:
QUIX_FAST_OPAQUE_BLIT=0 CROSSCODE_PROFILE=1  # baseline with patched runtime
QUIX_FAST_OPAQUE_BLIT=1 CROSSCODE_PROFILE=1  # fast path enabled
```

`CROSSCODE_PROFILE=1` adds `--fps --profile` and writes sampling data.
Measure median FPS, p95 frame time and JS/canvas frame time; check both
screenshots are pixel-identical. A host-only randomized **30,000-case**
equivalence smoke test of the two pixel loops passed.

Device A/B (2026-11-21, TSPS, one built binary, scale 1, all four effects on,
map `arid.forest-1`, 120 s windows) measured median 22.7 fps / js 41.7 ms with
the flag at 0 and 16.6 fps / js 57.8 ms with it at 1. Those screenshots showed
different spawn/camera/scenes, so that comparison is **rejected as invalid**;
it is not evidence of a regression.

Controlled re-test (2026-11-22, TSPS, `benchmarks/run-ab.sh`): pristine save
restored before every arm, fixed preset 3 -> `autumn.entrance`, identical dialog
dismissal and 90 s steady window, A/B/A on the SAME patched binary:

| arm | flag | median FPS | median js | p95 js |
| --- | --- | --- | --- | --- |
| A2 | 0 | 46.10 | 21.10 ms | 34.40 ms |
| B  | 1 | 49.00 | 19.90 ms | 31.20 ms |
| A3 | 0 | 46.65 | 20.90 ms | 31.20 ms |

Flag effect vs mean of off arms: +2.62 FPS / -1.10 ms js; off-arm drift
+0.55 FPS / -0.20 ms. This is a headless `-b dummy` run (present ~0.3 ms vs
~2.3 ms on the real SDL path) on a moderately heavy map: a modest repeatable
win, NOT the 30 FPS target. The flag stays opt-in (default 0) until a real
display A/B on `arid.forest-1` confirms it.

Upstream quixjs 0.5.1, tested in the same harness with `port.toml` and assets
unchanged, gave 48.85 FPS / 19.90 ms js against baseline arms 47.80 and 46.35
FPS / 20.45 and 21.05 ms js. Its ~1.8 FPS gain is within the ~3% A->A drift,
so a runtime swap is not justified by these data.

Profile of the same fixed scene (0.2.2, 4184 frames): `drawImage` 46.2%
(824296 calls, 51.66 us/call ~10 ms/frame), `fillRect` 5.3%, PNG `decode` 5.1%
(load only), `get globalCompositeOperation` 1.5% (394075 calls). Caller
attribution with a temporary stack-counting wrapper: transformed sprite `draw`
at `game.compiled.js:385` ~67% of calls, effect `draw` at `:1163` ~31%. Those
paths apply rotation/scale/alpha, so removing them would change pixels; a real
fix needs a Canvas2D drawImage backend, not another pixel-loop tweak.

Deterministic pixel check: `-b dummy --fixed-step --frames 300 --screenshot`
with flag 0 and 1 produced identical PNG SHA-256 on device; the 30,000-case
host equivalence test covers mixed-alpha patterns.

Reproduce any further A/B with `benchmarks/run-ab.sh LABEL BINARY LIBDIR SECONDS`
(`AB_BASE` overrides the results directory, which must contain `saves-backup/cc.save*`).
It restores the pristine save before every arm, loads preset 3, dismisses the
one-time dialog, fails closed on a scene mismatch and samples `--fps` only in
the steady window. Compare A/B/A, not two arms; a per-second `--fps` average is
not a per-frame p95.
