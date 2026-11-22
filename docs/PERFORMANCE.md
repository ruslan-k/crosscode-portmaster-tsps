# Performance (TrimUI Smart Pro S, SpruceOS, Mali-G57)

## Native compositing: real-display evidence, 2026-11-23

The previous claim that only a new GPU renderer could improve the heavy map was
incorrect. The `js` timer includes native Canvas2D. Four `destination-out`
`drawImage` calls consumed about 16.26 ms/frame on `arid.forest-1`; this was a
larger target than widening the already optimized opaque-copy loop.

**Scope:** 17 new lines in shared `gfx/surface.h::blend_pixel`:
- specialize `destination-out`: preserve RGB for positive unrounded alpha and
  round alpha as `(da * (255 - a) + 127) / 255`; clear all channels only when
  the reference produces exactly zero unrounded alpha;
- specialize source-over when destination alpha is 255: simplify the original
  integer expression, retaining its truncation rather than introducing a new
  rounding rule.

No game JavaScript, resolution, effects, update rules, input implementation,
GPU backend, dependency, allocation or runtime option was changed. The build
script applies both the existing raster patch and the new composite patch;
`QUIX_FAST_OPAQUE_BLIT=0` disables only the former.

### Matched hardware experiment

Spruce principal -> standard_launch -> SDL/GLES on the real 1280x720 display.
Canvas 568x320, preset 5 then `ig.game.teleport("arid.forest-1", null)`, player
(856,936,0), camera (580,772). Lighting, weather, particles and speedlines all
true; all assist multipliers remained 1. CPU4 reported 1992000 kHz at the start
and end of every accepted run. Gamepad input was excluded **only in the test
processes** with `SDL_GAMECONTROLLER_IGNORE_DEVICES=0x045e/0x028e`; every sampled
pad state was null. The original game saves were never used as writable test
files: a separate real assets directory linked immutable resources and copied
`cc.save*`; NW.js dataPath resolved into that sandbox.

Order A/B/C/B/A, 30 seconds of map warmup. The first three runs completed
120-second windows. A return attempt moved the player four pixels after about
90 seconds and was rejected; its replacement and the final A used 60 seconds.
All reported rows use the **same first 60 seconds**, chosen by monotonic time,
not by FPS. Every sampled map, player, camera, canvas size and effects setting
matched. Invalid loading, input-contaminated and moving-scene attempts are not
included in the results.

| Arm | Frames | Rendered FPS | Frame p50 ms | Frame p95 ms | Frames >33.33 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| A: previous blit patch / `SDL_F0` | 1317 | 21.96 | 45.04 | 48.20 | 1317 |
| B: destination-out / `SDL_F1` | 1875 | 31.26 | 31.78 | 33.65 | 125 |
| C: both specializations / `SDL_F2` | 1976 | 32.95 | 30.09 | 32.47 | 16 |
| B return / `SDL_F3R` | 1860 | 31.01 | 32.06 | 33.90 | 152 |
| A return / `SDL_F4` | 1305 | 21.77 | 45.75 | 47.65 | 1305 |

FPS is frame count / summed complete frame intervals, not median per-second
`--fps`. p50/p95 are quantiles of actual frame intervals; frames overlapping
measurement boundaries are excluded. Raw CSVs, measurement timestamps, states,
config/effects snapshots, binary hashes and summaries are in
[`benchmarks/results/20261123-native-compositing`](../benchmarks/results/20261123-native-compositing).

The combined gain against the mean of A controls is **11.09 FPS
(+50.7%)**. Destination-out alone adds 9.27 FPS;
source-over adds a further 1.81 FPS. A drift is
0.20 FPS; B drift is
0.26 FPS.

Native mean `destination-out` time falls from about 16.26 to 3.26 ms/frame.
The source-over specialization reduces the plain drawImage bin from about
6.70 to 4.99 ms/frame. These timers are nested inside the JS/native phase;
they must not be added to inclusive JS or canvas timers. All runs reported zero
VmSwap at exit. RSS/HWM are preserved in metadata; their end measurements occur
after 60 or 120 seconds and are **not a matched memory-regression experiment**.

### Correctness and clean-build validation

- Host and real aarch64 device: **16,777,216 cases per specialization** comparing
  all 8-bit alpha/channel combinations with the previous implementation.
  Destination-out uses `blend_pixel_slow` as oracle; source-over uses the original
  integer source-over formula, not the differently rounded floating-point path.
- Host AddressSanitizer + UndefinedBehaviorSanitizer passed both suites.
- A test-only shadow runtime copied each destination surface, executed the
  previous blending on one copy and the new blending on the other, then compared
  every byte after each drawImage/fillRect. Real arid and Bergen gameplay passed
  **11,679 native operations**, with no mismatches. Repeated comparisons
  of the same surfaces are not physical display overdraw. This slow validation
  build was not used for FPS measurements.
- Clean release build contains only the raster and composite patches, no CSV
  timing or shadow-verification code. Built twice through the updated build
  script, including its already-applied patch path; the SHA stayed identical.
  Aarch64 ELF requires GLIBC up to 2.27. Release SHA-256:
  `ee3bed2c824d8f044d7982b81c24e221f1e133e6be8c966e152b7c2a6ab5c30d`.
- The exact clean binary ran through principal-flow SDL in arid and Bergen;
  KMS captures show lighting, fog, particles/snow and HUD intact. A synthetic
  right-input check moved the player from (856,936) to (973.21,936). This is not
  a new physical-controller validation.
- Original executable, launcher, boot/config and all three save files retained
  their pre-test SHA-256 values. The temporary menu launcher and save sandbox
  were removed; no test process or pending launch remained. MainUI returned and
  its idle-clock display was captured through DRM/KMS. The clean candidate
  remains separately staged, not substituted for the production executable.

**Limit:** the combined run has p95 32.47 ms and p99
33.20 ms, but 16/1976 frames exceed 33.33 ms
(99.19% are within budget). This is evidence for this animated idle heavy
scene, **not a guarantee of locked 30 FPS in every fight or map**. No 30 FPS cap
was added. Long combat replays and every-map coverage remain unverified.

Build: `bash build/build_crosscode_quixjs.sh`. Pixel tests:
`bash tests/run-composite.sh /path/to/patched/quixjs`.
`benchmarks/native-timing.patch`, `benchmarks/shadow-blend.patch`,
`benchmarks/native-sandbox.py` and `benchmarks/native-scene.py` retain the tested
measurement/verification fixtures. They are not applied by the shipping build.
The fixtures require device Python 3 and upstream `tools/console.py` copied next
to the port config. Their paths are intentionally pinned to the measured deployment. Apply
native-timing to either A or C before an instrumented build; apply shadow-blend
after both shipping patches and native-timing for correctness-only validation.
Use Spruce's standard PORTS launch flow for SDL and do not run it alongside MainUI.
The baseline A contains the earlier packed-blit/overlap guard, not an unrelated
stock-runtime upgrade. Licensed game assets and saves are not included.

## Earlier experiments



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
~2.2 ms throughout. The `js` timer includes synchronous native Canvas2D work;
this split does **not** establish a JavaScript-only bottleneck.

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
  i.e. inconclusive in that experiment. Restored to the SpruceOS default; this
  does not establish that the port is frequency-independent.
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
# Only in a disposable diagnostic launcher, launched through Spruce principal:
QUIX_FAST_OPAQUE_BLIT=0 ./quixjs.aarch64 -c port.toml --fullscreen --fps --profile
QUIX_FAST_OPAQUE_BLIT=1 ./quixjs.aarch64 -c port.toml --fullscreen --fps --profile
```

The production launcher has no FPS/profiler/debug command-line flags and no
profiling environment switch. Keep these diagnostic commands out of it.
Measure median FPS, p95 frame time and JS/canvas frame time; check both
screenshots are pixel-identical. A host-only randomized **30,000-case**
equivalence smoke test of the two pixel loops passed.

Device A/B (2026-11-21, TSPS, one built binary, scale 1, all four effects on,
map `arid.forest-1`, 120 s windows) measured median 22.7 fps / js 41.7 ms with
the flag at 0 and 16.6 fps / js 57.8 ms with it at 1. Those screenshots showed
different spawn/camera/scenes, so that comparison is **rejected as invalid**;
it is not evidence of a regression.

Re-test (2026-11-22, TSPS, `benchmarks/run-ab.sh`): pristine save restored before
every arm, fixed preset 3 -> `autumn.entrance`, identical dialog dismissal,
90 s steady window, three OFF and three ON arms on the SAME patched binary;
only `QUIX_FAST_OPAQUE_BLIT` differs:

| arms | median FPS (each arm) | mean FPS | mean js |
| --- | --- | --- | --- |
| flag 0: A2, A3, A4 | 46.10, 46.65, 46.45 | 46.40 (sd 0.28) | ~21.0 ms |
| flag 1: B, B2, B3 | 49.00, 50.50, 49.80 | 49.77 (sd 0.75) | ~19.5 ms |

Mean effect: **+3.37 FPS / -1.52 ms js**; the OFF and ON ranges do not overlap.
`QUIX_FAST_OPAQUE_BLIT` is read only by the patched raster branch, so the same
binary with only that variable changed isolates the branch's effect even without
per-block counters.

Real SDL re-test (same device, real display, CPU governor Performance, same
preset and dialog sequence, principal-flow handoff not a stopped-UI run,
89 steady per-second samples per arm, flag 0 / 1 / 0):

| arm | median FPS | p95 FPS | median js | median present |
| --- | --- | --- | --- | --- |
| A0 flag 0 | 50.60 | 55.40 | 17.10 ms | 2.30 ms |
| B1 flag 1 | 53.45 | 59.20 | 16.10 ms | 2.20 ms |
| A2 flag 0 | 50.40 | 54.90 | 17.40 ms | 2.20 ms |

Effect **+2.95 FPS / -1.15 ms js** with 0.2 FPS / 0.3 ms off-arm drift. KMS
screenshots of all three arms show the same autumn scene with no missing layers
or artifacts; their pixel differences are animation/camera phase (two flag-0
arms also differ by 14% of pixels).

Heaviest available preset re-test on the real display (preset 5 ->
`bergen-trail.path-8`, snow/weather, same three-arm protocol):

| arm | median FPS | p95 FPS | median js | median present |
| --- | --- | --- | --- | --- |
| flag 0 | 40.70 | 41.80 | 22.10 ms | 2.20 ms |
| flag 1 | 45.70 | 46.80 | 19.50 ms | 2.20 ms |
| flag 0 | 40.95 | 42.10 | 22.00 ms | 2.20 ms |

Effect **+4.88 FPS / -2.55 ms js** with 0.25 FPS off-arm drift; KMS frames show
the same snowy scene with no missing layers. The gain is larger on the heavier
map, so the launcher sets the flag to `1` by default for patched builds;
`QUIX_FAST_OPAQUE_BLIT=0` still selects the original path.

Remaining caveats from independent review: even the heaviest available preset is
not `arid.forest-1` and animation frames are not pixel-identical across arms.
**30 FPS at 568x320 with all effects on the very heaviest maps is still
unverified** — the measured gain is 3-5 FPS, not a 30-FPS fix.

Block attribution (temporary counters, preset 5, flag 1): of 610165 `drawImage`
calls, 522960 (85.7%) took the translation-only plain path, 74288 took that same
path with non-plain blending (globalAlpha/clip/composite), 12707 the axis-scaled
path and 210 the general path — every entry is accounted for. Inside the packed
loop, 281215911 blocks were fully opaque and 592047252 fully transparent, versus
13623627 mixed *pixels* (~3.4M mixed blocks) and 2517599 scalar tail pixels:
about 99.6% of 4-pixel blocks are uniform, so the branch is heavily exercised.
With flag 0 the same scene sent 3880384100 pixels through the scalar loop
(~1.5M plain-path pixels per rendered frame across all surfaces; this is
rasterizer work, not physical display overdraw). This answers the review's
attribution objection.

Independent review also found a correctness gap in the original patch: an opaque
`memcpy(d, s, 16)` is undefined behaviour when source and destination storage
overlap, while the baseline per-pixel loop has defined read-before-write order.
The Canvas2D binding already copies the source for `drawImage(canvas, ...)`
when source and destination are the same canvas. The patch additionally disables
packed processing for overlapping surface storage and keeps the scalar loop for
those calls. Whole-buffer intersection also covers partially overlapping rows;
the earlier claim that it could miss such rows was incorrect. Headless A/B/A for the guard (flag 1,
preset 5): 43.05 FPS with guard vs 41.90/42.05 without, i.e. no regression.

A 16-pixel NEON grouping was also tested (real build, flag 1, preset 5): 44.80
FPS against 42.80/41.80 control arms: +2.50 FPS, js -1.35 ms at 1.0 FPS control
drift. The js delta clears the review's 0.5 ms decision threshold, but the FPS
signal is only 2.5x control drift and no real-display A/B/A was run, so it was **not**
adopted: it adds a 15-line hot-path branch and the same shared-store aliasing
risk. Following the review's ordering, the smaller 8-pixel scalar grouping with
the original 4-pixel fallback was tested last: 42.30 FPS vs 42.05/42.00 controls,
js -0.15 ms at 0.05 FPS drift — below the 0.5 ms threshold, so the falsifier
fired and packed-loop micro-optimization stops here. Neither experiment changed
the shipped patch.

GPU canvas investigation: the 0.5.1 `gpu2d` API supports fill/clear rectangles
and fill masks, not textured `drawImage`. However, the earlier hook comparison
(37.30 vs 37.80/36.40 FPS) used `-b dummy`: it cannot exercise the real GPU
backend and is **not GPU performance evidence**. `--test` confirming "Hooks: 1"
proves configuration parsing, not GPU activation. A textured drawImage backend
remains possible with pixel-parity validation; unchanged visuals do not prohibit
a renderer implementation change.

Upstream quixjs 0.5.1, tested in the same harness with `port.toml` and assets
unchanged, gave 48.85 FPS / 19.90 ms js against baseline arms 47.80 and 46.35
FPS / 20.45 and 21.05 ms js. Its ~1.8 FPS gain is within the ~3% A->A drift,
so a runtime swap is not justified by these data.

Profile of the same fixed scene (0.2.2, 4184 frames): `drawImage` 46.2%
(824296 calls, 51.66 us/call ~10 ms/frame), `fillRect` 5.3%, PNG `decode` 5.1%
(load only), `get globalCompositeOperation` 1.5% (394075 calls). Caller
attribution with a temporary stack-counting wrapper: transformed sprite `draw`
at `game.compiled.js:385` ~67% of calls, effect `draw` at `:1163` ~31%. Those
paths apply rotation/scale/alpha, so removing the effects would change pixels.
This does not rule out exact CPU optimizations within native compositing.

Deterministic pixel check: `-b dummy --fixed-step --frames 300 --screenshot`
with flag 0 and 1 produced identical PNG SHA-256 on device; the 30,000-case
host equivalence test covers mixed-alpha patterns.

Reproduce any further A/B with `benchmarks/run-ab.sh LABEL BINARY LIBDIR SECONDS`
(`AB_BASE` overrides the results directory, which must contain `saves-backup/cc.save*`).
It restores the pristine save before every arm, loads preset 3, dismisses the
one-time dialog, fails closed on a scene mismatch and samples `--fps` only in
the steady window. Compare A/B/A, not two arms; a per-second `--fps` average is
not a per-frame p95.
