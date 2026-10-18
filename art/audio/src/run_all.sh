#!/usr/bin/env bash
# Regenerate every WAV and run the analysis table.  ~1 min SFX + ~3-6 min music.
set -euo pipefail
cd "$(dirname "$0")"
python3 gen_sfx.py
python3 gen_music.py
python3 gen_chapters23.py
python3 analyze.py
