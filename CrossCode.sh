#!/bin/bash
# CrossCode on quixjs (SPRUCE/TSPS bring-up): the game's own web assets,
# no Electron, no browser.

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
  controlfolder="$XDG_DATA_HOME/PortMaster"
elif [ -d "/mnt/SDCARD/Persistent/portmaster/PortMaster" ]; then
  controlfolder="/mnt/SDCARD/Persistent/portmaster/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi

source $controlfolder/control.txt
[ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"
get_controls

GAMEDIR="/mnt/SDCARD/Roms/PORTS/crosscode-qx"
cd $GAMEDIR || exit 1

> "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

QUIXJS="./quixjs.aarch64"

# the console .asoundrc sends the default PCM to a "Playback" that does not
# exist; MainUI is gone by now, so we can hold the card directly
export SDL_AUDIODRIVER=alsa
export AUDIODEV=${AUDIODEV:-plughw:0,0}

export QUIXJS_FONT="$GAMEDIR/fonts/DejaVuSans-Bold.ttf"
export LD_LIBRARY_PATH="$GAMEDIR/libs.aarch64:$LD_LIBRARY_PATH"
export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"

echo "quixjs $(cat VERSION 2>/dev/null) crosscode-qx ($CFW_NAME)"
$ESUDO chmod +x "$GAMEDIR/quixjs.aarch64"

if [ -n "$GPTOKEYB2" ]; then
  $GPTOKEYB2 "quixjs.aarch64" &
else
  $GPTOKEYB "quixjs.aarch64" &
fi

pm_platform_helper "$GAMEDIR/quixjs.aarch64"
$QUIXJS -c port.toml --fullscreen

pm_finish
