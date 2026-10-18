# Audio production log (subagent, 2026-10-18)

The audio subagent wrote this log for the Vahagn audio work. Each step lists what was done, the command or tool, why, and the result. Newest entries are at the bottom.

1. **20:30 Environment check.**
   - Ran `python3 -c "import numpy, scipy, numba, matplotlib"`. Versions: numpy 2.4.3, scipy 1.17.1, numba 0.65.1, matplotlib 3.10.9.
   - ffmpeg is at `~/.local/bin/ffmpeg` and includes the ebur128 filter.
   - Listed the StarterContent Audio `.uasset` files (24). They are documented in README and were not converted.
2. **20:32 Wrote `src/dsp.py`.** It contains the noise, filters (including the numba TPT SVF), additive oscillators, synthetic-IR convolution reverb (linear and circular), limiter, compressor, BS.1770 LUFS and the WAV writer.
3. **20:35 Wrote `src/gen_sfx.py` and ran the first render** (`python3 gen_sfx.py`, about 10 s). All 17 files were written.
4. **20:37 Wrote `src/analyze.py` and checked band energies.**
   - Too much energy above 10 kHz (hissy) in the roar, explosion and victory.
   - Horn too dull.
   - Fixes:
     - Brightness became a per-sample cutoff in Hz.
     - Added an 11 kHz "air" low-pass in `finish()`.
     - Crackle kernels are now low-passed at 9 kHz, and the debris amplitude decays.
     - The cymbal was redesigned.
5. **20:40 Wrote `src/gen_music.py`** (menu 80 BPM/72 s, battle 120 BPM/80 s, boss 128 BPM/60 s), using ring-buffer circular rendering.
   - First render: about 2.5 min.
   - The lead masked the drums. The fix was to auto-balance stems to loudness targets (`mixdown(targets)`).
6. **20:44 Downloaded Kenney CC0 packs** with curl from kenney.nl into scratch (interface, impact and RPG sounds).
   - Decoded the chosen files with ffmpeg and inspected their spectrograms.
   - Kept click_001, impactPunch_heavy_000/002 and impactPlate_heavy_000, with their licenses, in `src/cc0_sources/kenney/`.
   - Layered them into the UI click, the vishap hit and the player hurt.
7. **20:47 Laptop-speaker EQ.**
   - SFX: low shelf of -3 dB at 90 Hz, plus a mid "punch" layer in explosions.
   - Music master: shelf of -3 dB at 85 Hz and +1.5 dB at 3 kHz.
   - The music re-render took about 15 min because CPU load was around 12 from the parallel UE build.
8. **20:58 Rebuilt the roar model.** The old roar's spectrogram looked like broadband noise.
   - New model: lower jitter, level-dependent throat saturation before the vocal tract, and four moving SVF formants.
   - Harmonics and formant sweeps are now visible in the spectrogram. Roar, hit and death were re-rendered.
9. **21:05 Darkened the horn** (fmax 6.5 kHz, cutoff 2.1 kHz) and re-rendered the stingers.
10. **21:07 Final check.** `python3 src/analyze.py` reported ALL CHECKS PASSED.
    - 0 clipped samples and every peak at -1 dBFS or lower.
    - Music at -14.0 LUFS, confirmed with ffmpeg ebur128.
    - Loop seam jumps under 0.5x.
11. **21:08 Wrote README.md, CREDITS.md, run_all.sh and ue_import_audio.py.** The import script's APIs were grepped in the 5.8 headers. The script was not executed, because the editor is owned by the main agent.

Blocked or not done:
- No human listening was possible. Quality was judged from spectrograms and numeric analysis only.
- The UE import has not been run.
