# CrossCode — PortMaster port for TrimUI Smart Pro S (SpruceOS)

Port of **CrossCode 1.4.2-2** to the TrimUI Smart Pro S (TSPS, 1280x720, Mali-G57)
running the game's own web assets on **quixjs 0.2.2** — a JS runtime in C
(JavaScriptCore + SDL2 + OpenGL ES 2), https://github.com/lowlevel-1989/quixjs.
No Electron, no Chromium, no browser.

Status: playable — picture, sound, gamepad, saves. The game draws a 568x320
canvas scaled to 1280x720. The stock runtime reaches ~55 fps in light maps and
~20 fps in heavy outdoor maps. The rebuilt runtime adds CPU Canvas2D fast paths:
in a matched animated idle `arid.forest-1` scene it reached **32.95 fps**, versus
~22 fps with the previous blit-patched runtime (**+50.7%**), at the same resolution
with effects enabled. This is not a locked-30-fps guarantee for every map or fight.
See [performance optimizations](#performance-optimizations) for installation and
[docs/PERFORMANCE.md](docs/PERFORMANCE.md) for raw evidence and test scope.

## What is in this repo

| Path | Purpose |
| --- | --- |
| `CrossCode.sh` | PortMaster launcher (SpruceOS PortMaster path, ALSA env, gptokeyb2 target) |
| `port.toml` | quixjs config: game dir, 568x320 default canvas, fps cap, nw.js layer |
| `ccx-boot.js` | The port shim: what `node-webkit.html` supplied that quixjs does not (see below) |
| `port.json`, `gameinfo.xml` | Packaging / front-end metadata templates; not installed by `install.sh` |
| `install.sh` | Assembles the port: quixjs binary + shim + assets |
| `build/build_crosscode_quixjs.sh`, `patches/` | Rebuild quixjs with the packed-blit and compositing fast paths |
| `tests/run-composite.sh` | Exhaustive integer-blending equivalence tests |
| `docs/PERFORMANCE.md` | Frame-time measurements, validation and production rollout |

Game data is **not** included.

## Build

These are fresh-install steps, with the card available at `/mnt/SDCARD`.
The plain installer uses the stock upstream runtime; use
[performance optimizations](#performance-optimizations) for a patched build.
For an existing port, use the update instructions there without an assets
argument, so game saves are not overwritten by a fresh copy of the assets.

1. Get the game assets. Either the PC release (`assets/` next to `Game.exe`)
   or the Android OBB, which is a FAT32 image:

   ```sh
   sudo mkdir -p /mnt/obb
   sudo mount -o loop,ro -t vfat main.1.de.radicalfishgames.crosscode.obb /mnt/obb
   # the game is /mnt/obb/assets: data/ game/ impact/ js/ media/ modules/ mods/
   ```

2. Assemble:

   ```sh
   ./install.sh /mnt/SDCARD/Roms/PORTS/crosscode-qx /mnt/obb/assets
   ```

   `install.sh` downloads `quixjs-0.2.2-linux-aarch64.tar.gz` from the quixjs
   release, unpacks `quixjs.aarch64`, `libs.aarch64/`, `fonts/`, copies the
   assets into `gamedata/assets/`, installs `ccx-boot.js` there and drops
   `port.toml` next to them. It also installs `CrossCode.sh` in the parent PORTS
   directory; no second launcher copy is needed.

## Port specifics

quixjs runs the game's `<script>`s itself, so the HTML shell is replaced by
`ccx-boot.js`. What it has to provide, and why:

* **`IG_*` globals** — `node-webkit.html` sets `IG_WIDTH=568`, `IG_HEIGHT=320`,
  `IG_GAME_SCALE`, `IG_GAME_CACHE`, etc. before the bundle runs.
* **`window.name`, `self`, `top`, `parent`, `frames`** — the Impact bundle and
  jQuery-era code read them (`name` is what broke first).
* **`DOMParser`** — `impact.base.dom` builds one at module load; a document-shaped
  stub is enough, the game's UI is canvas.
* **`canvas.style.width` as a CSS string** — `ig.System.resize` does
  `style.width.replace("px","")*1`; quixjs stores that style value as a number.
* **`document.getElementById`** — `#game` and `#options` do not exist; they are
  returned as empty elements so the engine's HTML-shell calls are no-ops.
* **`$` / `jQuery`** — the bundle calls `$("#game").css(...)` and loads every
  JSON with `$.ajax({dataType:"json"})`; `$.ajax`/`$.getJSON` are implemented on
  top of `XMLHttpRequest`.
* **`process.versions['node-webkit']`** — the bundle picks its platform from
  `window.require && typeof window.process == "object"`; with the value set it
  takes the DESKTOP path, which is the one that saves to files through
  `require("fs")` + `nw.gui.App.dataPath` (= the game folder).
* **the start call** — `window.onload` in the HTML polls for
  `window.startCrossCode` and calls it; the shim does the same.

Other knobs, in the launcher and the toml:

* **Audio** — `SDL_AUDIODRIVER=alsa`, `AUDIODEV=plughw:0,0`. SpruceOS's
  `/mnt/SDCARD/.asoundrc` sends the default PCM to a `Playback` PCM that does not
  exist, so without these SDL opens no device and the game is silent.
* **PortMaster path** — on SpruceOS PortMaster lives in
  `/mnt/SDCARD/Persistent/portmaster/PortMaster`; the stock PortMaster launcher
  template only probes `/opt/...` and `/roms/ports/PortMaster`.
* **Render size** — `IG_GAME_SCALE=1` (the game's native 568x320). An earlier
  stock-runtime test took ~2.3x more frame time at scale 2 (1136x640); that is not
  a measurement of the optimized build. This is the same setting as
  *Options > Video > Pixel Size* in game.
* **Pad** — read through `navigator.getGamepads()` (quixjs implements it); the
  virtual pad shows up as "Xbox 360 Controller" through PortMaster's
  `gamecontrollerdb.txt`.
* **Normal launch** — `-c port.toml --fullscreen`, without FPS/profiler/debug
  flags. `log.txt` is the ordinary startup/error log, overwritten on each launch.

## Credits

* [quixjs](https://github.com/lowlevel-1989/quixjs) by lowlevel-1989 — the
  JavaScriptCore + SDL2 + GLES2 runtime this port is built on, including the
  nw.js layer, the SDL backend and the aarch64 release used here. Libraries and
  fonts come from its `0.2.2` release; the executable is either that stock release
  or a local rebuild of the same tag with this repo's Canvas2D patches.
  Since 0.2.2 `libs/` only carries what the CFW does not
  (SDL2_ttf, libvpx, libopus); SDL2, SDL2_image, freetype and libpng come from
  SpruceOS.
* CrossCode and its assets — Radical Fish Games.

## Known issues

* Locked 30 fps across all maps and long fights is not verified. In the optimized
  heavy-scene test, 16 of 1976 frames still exceeded 33.33 ms. No effects were
  disabled, and no 30 fps cap was added. The `js` timer includes native software
  Canvas2D rendering, not just JavaScript execution.
* Gamepad rumble and the game's own "fullscreen" option are inert (the runtime
  is already fullscreen).
* Saves go to `crosscode-qx/gamedata/assets/cc.save` (+ `.backup`, `.backup2`);
  they are the game's own format, so a save from the Electron port on the same
  version loads here.

## Performance optimizations

The packed opaque-copy/transparent-skip path and exact `destination-out` and
opaque-destination `source-over` specializations require a rebuilt runtime.
They do not change the game's logic, resolution or effects, and are not a new
GPU Canvas2D backend. Build on a Linux development host with the upstream
PortMaster build dependencies; the first build downloads the sysroot and
JavaScriptCore dependencies:

```sh
bash build/build_crosscode_quixjs.sh
bash tests/run-composite.sh build/quixjs-0.2.2
```

The result is `build/quixjs-crosscode.aarch64`. For a fresh port with the OBB
mounted as above:

```sh
QUIXJS_BIN="$PWD/build/quixjs-crosscode.aarch64" \
  ./install.sh /mnt/SDCARD/Roms/PORTS/crosscode-qx /mnt/obb/assets
```

For an existing port, exit the game first and back up the original executable
and any customized port files. Omit the assets argument:

```sh
QUIXJS_BIN="$PWD/build/quixjs-crosscode.aarch64" \
  ./install.sh /mnt/SDCARD/Roms/PORTS/crosscode-qx
```

This refreshes the executable, bundled libraries/fonts, launcher, config and port
shim together. It does not recopy the game assets or modify `cc.save*`.
Without `QUIXJS_BIN`, a fresh install still selects the stock upstream runtime.
`QUIX_FAST_OPAQUE_BLIT=0` disables only the packed blit, not the exact compositing
specializations. Restore the original executable to return to the previous runtime.
The shipping build has no benchmark CSV/shadow instrumentation. Real-device
results, correctness checks and the clean production rollout are in
[docs/PERFORMANCE.md](docs/PERFORMANCE.md).
