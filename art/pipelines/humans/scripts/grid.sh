#!/bin/bash
# grid.sh out.jpg cols w h img... -- tile screenshots
OUT=$1; C=$2; W=$3; H=$4; shift 4; N=$#; IN=""; F=""; i=0
for f in "$@"; do IN="$IN -i $f"; F="$F[$i]scale=$W:$H[s$i];"; i=$((i+1)); done
L=""; for j in $(seq 0 $((N-1))); do L="$L[s$j]"; done
LAY=""; for j in $(seq 0 $((N-1))); do LAY="$LAY$(( (j%C)*W ))_$(( (j/C)*H ))|"; done
ffmpeg -hide_banner -loglevel error -y $IN -filter_complex "$F${L}xstack=inputs=$N:layout=${LAY%|}:fill=black" -q:v 3 $OUT && echo $OUT
