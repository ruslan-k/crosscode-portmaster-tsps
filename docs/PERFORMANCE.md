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
