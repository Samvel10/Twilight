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

# Chapters 2 «Hayk» + 3 «Aralez» audio (subagent, 2026-10-18 21:28–21:40)

12. **21:28 Read the chapter-1 toolkit** (`dsp.py`, `gen_sfx.py`, `gen_music.py`, `analyze.py`, README, this log). Decided to import it rather than copy it: `gs.finish` / `gs.finish_loop` / `gs.glottal_roar` / `gs.choir`, and `gm.Track` / `add_reed` / `dhol_*` / `taiko` / `daf` / `choir` / `string_note` / `mixdown`.
13. **21:30 Wrote `src/gen_chapters23.py`.**
    - New: IFFT "spectral additive" oscillators (`ifft_partials`, `brass`, `ifft_drone`, `pad_chord`), so drones and pads are loop-periodic and cheap. The UE build was using all cores (load about 11.5).
    - Also new: a deterministic glass `bell()`, `davul_dum()`, `drip()` and the stereo-safe `finish_loop_st()`.
    - Reed ornaments follow each track's own mode via `gm.SCALE`: A Phrygian for Hayk, D double-harmonic for Aralez.
14. **21:31 First SFX render.** Ran `OMP_NUM_THREADS=1 nice -n 15 python3 gen_chapters23.py sfx_`. It took about 10 s and wrote all 13 SFX. Every duration was exact and every peak was -1 dBFS or lower.
15. **21:32 Music render** (in the background, nice 15, single-threaded): about 2.5 min for both loops.
16. **21:33 Spectrogram and band-energy review** (scratch script, not kept). Fixes:
    - **bow_release:** the twang was too bright and buzzy. Fix: excitation low-passed, damping 0.5, a moving SVF low-pass so the highs die first, and a lighter limb thump.
    - **wraith_hiss:** not dark enough. Fix: sibilance halved, overall low-pass at 6 kHz, growl louder.
    - **bow_draw:** the creak was continuous. Fix: sparser gating.
    - **war_drums_loop:** 100–400 Hz sat 11 dB under the sub. Fix: +5 dB at 190 Hz, +3 dB at 2.5 kHz and a -4 dB low shelf, so the drums read on laptop speakers.
    - **flesh/ground hits:** the thump fundamental was raised to 58–64 Hz.
    - **cave drips:** shorter, and the reverb wet was cut from 0.7 to 0.45.
17. **21:36 Fixed `music_hayk`.** In the mono sum its intro showed a comb-filter pattern. The cause was brass fed as `[br, roll(br, 37)]`. It is now mono-centred, and the stereo reverb gives the width. Re-rendered in about 78 s.
18. **21:38 Verification.**
    - `gen_chapters23.py --verify` and `analyze.py`: ALL CHECKS PASSED, across all 35 files.
    - New files: 0 clipped samples, DC at most 2.6e-4, durations exact, loop seams 0.03–0.42x (analyze.py metric).
    - `ffmpeg ebur128`: music_hayk I = -14.0 LUFS (peak -1.5), music_aralez -14.0 LUFS (peak -6.0).
19. **21:39 Docs.**
    - README: new section with a table of 15 files, plus updated folder and regeneration notes.
    - `run_all.sh` now runs `gen_chapters23.py`.
    - CREDITS: chapters 2–3 are fully procedural, with no downloads.
    - `ue_import_audio.py` scans the folders, so the new files, and the loop flags for `*_loop` and `music_*`, are covered without changes.

Not done or blocked:
- No human listening was possible. Quality was judged from spectrograms and numeric analysis only.
- No UE import was run. Nothing under `Game/` was touched.
