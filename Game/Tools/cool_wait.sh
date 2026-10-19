#!/usr/bin/env bash
# Waits (up to MAX seconds) until the CPU package cools below LIMIT °C before a heavy game launch,
# so repeated play-tests don't keep the laptop at its thermal ceiling.
LIMIT=${COOL_LIMIT:-76}; MAX=${COOL_MAX:-240}
t() { for z in /sys/class/thermal/thermal_zone*; do [ "$(cat $z/type)" = "x86_pkg_temp" ] && echo $(( $(cat $z/temp) / 1000 )); done | head -1; }
for i in $(seq 1 $((MAX / 10))); do
  T=$(t); [ -z "$T" ] && exit 0
  [ "$T" -lt "$LIMIT" ] && { echo "[cool] CPU ${T}C ok"; exit 0; }
  echo "[cool] CPU ${T}C >= ${LIMIT}C, resting..."; sleep 10
done
echo "[cool] still warm after ${MAX}s, continuing"
