#!/bin/bash
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands
UE=~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd; U=/var/www/html/Twilight/Game/TwilightAssets.uproject; A="-unattended -nop4 -nosplash -nosound -nullrhi"
cd $P
for site in "" van ararat; do
  /var/www/html/Twilight/Game/Tools/cool_wait.sh
  case $site in ararat) export HL_CLON=44.35 HL_CLAT=40.05 HL_LAKE=0;; van) export HL_CLON=43.25 HL_CLAT=38.52 HL_LAKE=1647;; *) unset HL_CLON HL_CLAT HL_LAKE;; esac
  HL_SITE=$site HL_ONLY=level HL_VEG=1 $UE $U -ExecutePythonScript=$P/scripts/s2_level.py $A 2>&1 | grep -E "HL scatter|HL level saved|HL errors|LogPython: Error" | tail -5
  echo "SITE_DONE [$site]"
done
echo ALL_DONE
