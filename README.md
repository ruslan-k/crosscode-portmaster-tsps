# CrossCode — PortMaster port for TrimUI Smart Pro S (SpruceOS)

Port of **CrossCode 1.4.2-2** to the TrimUI Smart Pro S (TSPS, 1280x720, Mali-G57)
running the game's own web assets on **quixjs 0.2.2** — a JS runtime in C
(JavaScriptCore + SDL2 + OpenGL ES 2), https://github.com/lowlevel-1989/quixjs.
No Electron, no Chromium, no browser.

Status: playable — picture, sound, gamepad, saves. The stock runtime reaches
~55 fps in light maps and ~20 fps in heavy outdoor maps. The game draws a
568x320 canvas scaled to 1280x720. Patched-runtime measurements and their
limitations are in [docs/PERFORMANCE.md](docs/PERFORMANCE.md).

## What is in this repo

| Path | Purpose |
| --- | --- |
| `CrossCode.sh` | PortMaster launcher (SpruceOS PortMaster path, ALSA env, gptokeyb2 target) |
| `port.toml` | quixjs config: game dir, 568x320 default canvas, fps cap, nw.js layer |
| `ccx-boot.js` | The port shim: what `node-webkit.html` supplied that quixjs does not (see below) |
| `port.json`, `gameinfo.xml` | PortMaster / EmulationStation metadata |
| `install.sh` | Assembles the port: quixjs binary + shim + assets |
| `docs/PERFORMANCE.md` | Frame-time measurements and what was tried |

Game data is **not** included.

## Build

1. Get the game assets. Either the PC release (`assets/` next to `Game.exe`)
   or the Android OBB, which is a FAT32 image:

   ```sh
   sudo mount -o loop,ro -t vfat main.1.de.radicalfishgames.crosscode.obb /mnt/obb
   # the game is /mnt/obb/assets: data/ game/ impact/ js/ media/ modules/ mods/
   ```

2. Assemble:

   ```sh
   ./install.sh /mnt/SDCARD/Roms/PORTS/crosscode-qx /mnt/obb/assets
   cp CrossCode.sh port.json gameinfo.xml /mnt/SDCARD/Roms/PORTS/
   ```

   `install.sh` downloads `quixjs-0.2.2-linux-aarch64.tar.gz` from the quixjs
   release, unpacks `quixjs.aarch64`, `libs.aarch64/`, `fonts/`, copies the
   assets into `gamedata/assets/`, installs `ccx-boot.js` there and drops
   `port.toml` next to them.

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
* **Render size** — `IG_GAME_SCALE=1` (the game's native 568x320). At 2
  (1136x640) the software canvas costs 2.3x more frame time for a small gain in
  sharpness, and it is the same as *Options > Video > Pixel Size* in game.
* **Pad** — read through `navigator.getGamepads()` (quixjs implements it); the
  virtual pad shows up as "Xbox 360 Controller" through PortMaster's
  `gamecontrollerdb.txt`.

## Credits

* [quixjs](https://github.com/lowlevel-1989/quixjs) by lowlevel-1989 — the
  JavaScriptCore + SDL2 + GLES2 runtime this port is built on, including the
  nw.js layer, the SDL backend and the aarch64 release used here. Everything
  under `crosscode-qx/{quixjs.aarch64,libs.aarch64,fonts}` comes from its
  `0.2.2` release. Since 0.2.2 `libs/` only carries what the CFW does not
  (SDL2_ttf, libvpx, libopus); SDL2, SDL2_image, freetype and libpng come from
  SpruceOS.
* CrossCode and its assets — Radical Fish Games.

## Known issues

* Heavy outdoor maps can stay around 20 fps with the stock runtime. The `js`
  timer includes native software Canvas2D rendering; a ~2.2 ms `present` does
  not establish a JavaScript-only bottleneck. All effects remain enabled.
* Gamepad rumble and the game's own "fullscreen" option are inert (the runtime
  is already fullscreen).
* Saves go to `crosscode-qx/gamedata/assets/cc.save` (+ `.backup`, `.backup2`);
  they are the game's own format, so a save from the Electron port on the same
  version loads here.

## Experimental performance work

The packed-blit and compositing patches require a rebuilt runtime;
`install.sh` still downloads the stock upstream binary. Build and test with:

```sh
bash build/build_crosscode_quixjs.sh
bash tests/run-composite.sh build/quixjs-0.2.2
```

The result is `build/quixjs-crosscode.aarch64`. To use it in an assembled port,
back up its original `quixjs.aarch64`, then copy the rebuilt executable there
under that name. Keep `libs.aarch64/` and the game assets unchanged.
`QUIX_FAST_OPAQUE_BLIT=0` disables only the packed blit, not the exact
compositing specializations; retain the original executable for a full rollback.
Real-device results and benchmark scope are in
[docs/PERFORMANCE.md](docs/PERFORMANCE.md).
