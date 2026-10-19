#!/bin/bash
# shoot.sh <map> <out> [wait] -- shoot1.sh with up to 3 attempts (another agent sometimes SIGKILLs -game editors)
D=$(dirname "$0"); P=$(cd $D/.. && pwd)
for t in 1 2 3; do rm -f $P/shots/$2.png; "$D/shoot1.sh" "$@" 2>/dev/null | tail -1; [ -s $P/shots/$2.png ] && exit 0; echo "retry $t"; sleep 3; done; exit 1
