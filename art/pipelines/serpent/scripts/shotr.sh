#!/bin/bash
# retry wrapper: GPU memory is shared with other agents' editors; OOM crashes are retried
D=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/serpent
for a in 1 2 3 4; do
  OUT=$($D/scripts/shot.sh "$@" 2>&1)
  if [ -f $D/shots/$1.png ]; then echo "$OUT" | grep -v "Segmentation" | tail -${TAILN:-3}; exit 0; fi
  echo "attempt $a failed: $(echo "$OUT" | grep -a 'VK_ERROR\|Fatal' | head -1 | cut -c1-120)"; sleep 20
done
