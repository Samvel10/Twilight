#!/usr/bin/env bash
# Helpers for recorded tests of the PACKAGED build. source it, then:
#   tw_launch <out_dir> [game args...]   -> starts the game, waits for its window, raises it (sets W X Y WIDTH HEIGHT GPID)
#   tw_rec_start <file.mp4> [mouse=1]     -> records the game window region (FFPID)
#   tw_rec_stop; tw_shot <file.jpg>; tw_click <x> <y>; tw_key <key> [hold_s]; tw_quit
G=/var/www/html/Twilight/Game
tw_launch() {
  local out=$1; shift; mkdir -p "$out"
  "$G/Tools/cool_wait.sh" >&2
  "$G/../Build/Linux/Twilight.sh" -windowed -ResX=1600 -ResY=900 -WinX=0 -WinY=0 "$@" > "$out/game.log" 2>&1 &
  W=""; for i in $(seq 1 120); do GPID=$(pidof Twilight-Linux-Shipping); [ -n "$GPID" ] && W=$(xdotool search --onlyvisible --pid $GPID 2>/dev/null | tail -1); [ -n "$W" ] && break; sleep 1; done
  sleep 2; xdotool windowactivate --sync "$W" 2>/dev/null; xdotool windowraise "$W"; sleep 0.5
  eval "$(xdotool getwindowgeometry --shell "$W")"
}
tw_rec_start() { ffmpeg -hide_banner -loglevel error -y -f x11grab -draw_mouse ${2:-1} -framerate 25 -video_size $((WIDTH/2*2))x$((HEIGHT/2*2)) -i :0.0+${X},${Y} -c:v libx264 -preset veryfast -crf 24 -pix_fmt yuv420p "$1" < /dev/null & FFPID=$!; }
tw_rec_stop() { kill -INT $FFPID 2>/dev/null; wait $FFPID 2>/dev/null; }
tw_shot() { ffmpeg -hide_banner -loglevel error -y -f x11grab -draw_mouse 1 -video_size ${WIDTH}x${HEIGHT} -i :0.0+${X},${Y} -frames:v 1 "$1"; }
tw_click() { xdotool windowactivate "$W" 2>/dev/null; xdotool mousemove $((X + $1)) $((Y + $2)); sleep 0.25; xdotool mousedown 1; sleep 0.12; xdotool mouseup 1; }
tw_key() { xdotool keydown "$1"; sleep ${2:-0.1}; xdotool keyup "$1"; }
tw_alive() { pidof Twilight-Linux-Shipping >/dev/null; }
tw_quit() { local p=$(pidof Twilight-Linux-Shipping); [ -n "$p" ] && kill $p; sleep 2; }
