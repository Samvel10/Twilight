#!/usr/bin/env bash
# Launch the Twilight games for playing / presenting (fullscreen, performance power profile).
UE=${UE:-$HOME/UnrealEngine-5.8}
G=$(cd "$(dirname "$0")/.." && pwd)
MAP=${1:-L_Menu}
powerprofilesctl set performance 2>/dev/null || true
export MESA_SHADER_CACHE_MAX_SIZE=4G
exec "$UE/Engine/Binaries/Linux/UnrealEditor" "$G/Twilight.uproject" /Game/Twilight/Maps/$MAP -game -fullscreen -NoSplash -ExecCmds="DisableAllScreenMessages" "${@:2}"
