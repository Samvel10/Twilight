#!/usr/bin/env bash
# Launch the Twilight games for playing / presenting (fullscreen, performance power profile).
# Uses the packaged Shipping build in ../Build if it exists, otherwise the editor binary in -game mode.
# Usage: play.sh [L_Menu|L_Vahagn|L_Hayk|L_Aralez] [extra args...]     (TW_EDITOR=1 forces the editor binary)
UE=${UE:-$HOME/UnrealEngine-5.8}
G=$(cd "$(dirname "$0")/.." && pwd)
MAP=${1:-L_Menu}
powerprofilesctl set performance 2>/dev/null || true
export MESA_SHADER_CACHE_MAX_SIZE=4G
PKG=$(ls "$G"/../Build/Linux*/Twilight.sh 2>/dev/null | head -1)
if [ -z "$TW_EDITOR" ] && [ -n "$PKG" ]; then
  # Shipping ignores a command-line map; the hub reads -TwMap= and opens the chapter itself
  exec "$PKG" -TwMap=$MAP -fullscreen "${@:2}"
fi
exec "$UE/Engine/Binaries/Linux/UnrealEditor" "$G/Twilight.uproject" /Game/Twilight/Maps/$MAP -game -fullscreen -NoSplash -ExecCmds="DisableAllScreenMessages" "${@:2}"
