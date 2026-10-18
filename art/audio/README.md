# Audio: Vahagn: Vishapakagh

This folder holds game-ready WAVs for SFX and music. All files are **48 kHz, 16-bit PCM** with TPDF dither. SFX are **mono**, so UE can spatialise them in 3D. Music is **stereo** and loops seamlessly at about **-14 LUFS** with peaks of -1 dBFS or lower.

The music and almost all of the SFX are synthesized procedurally by the Python scripts in `src/`. They use numpy, scipy and, optionally, numba. Seeds are fixed, so a re-run produces the same files. Three SFX also layer short CC0 recordings from Kenney (see `CREDITS.md`). No paid or AI services were used.

```
art/audio/
  sfx/      17 mono SFX (sfx_*.wav)
  music/    3 stereo loops (music_*.wav)
  src/      dsp.py, gen_sfx.py, gen_music.py, analyze.py, run_all.sh,
            ue_import_audio.py, cc0_sources/kenney/ (CC0 originals + licenses)
  CREDITS.md
```

Regenerate everything with `bash src/run_all.sh`. SFX take about 15 s. Music takes 3–6 min, depending on CPU load.

## Files

| File | Dur (s) | Ch | Peak dBFS | LUFS | Loop | Content / suggested use |
|---|---:|:-:|---:|---:|:-:|---|
| sfx/sfx_fireball_cast.wav | 1.40 | 1 | -1.0 | -12.7 | | whoosh (sweeping band-pass) + ignition "fwoomp" (opening low-pass) + thump + crackles |
| sfx/sfx_fireball_impact.wav | 2.00 | 1 | -1.0 | -18.7 | | medium fiery explosion: crack, filtered body, sub drop, debris, after-burn sizzle |
| sfx/sfx_big_explosion.wav | 5.00 | 1 | -1.0 | -19.8 | | double blast + long sub pressure wave + rumble + debris, valley reverb |
| sfx/sfx_vishap_roar.wav | 4.40 | 1 | -1.0 | -15.2 | | monster roar: glottal source + growl (period doubling) + throat distortion + moving formants, plus a layer pitched down one octave and a reptile hiss |
| sfx/sfx_vishap_hit.wav | 1.10 | 1 | -1.0 | -18.5 | | meaty impact (Kenney punch pitched to 0.72x) + slap/crunch + short snarl-yelp |
| sfx/sfx_vishap_death.wav | 5.20 | 1 | -1.0 | -16.5 | | falling death cry + gurgle + body crash/fire burst at 2.55 s |
| sfx/sfx_fire_breath.wav | 2.00 | 1 | -2.0 | -12.5 | yes | roaring flame jet with turbulent AM and crackle (play looping while breathing) |
| sfx/sfx_player_hurt.wav | 1.00 | 1 | -1.0 | -20.2 | | punch + armour plate (Kenney CC0) + concussion thump + quiet ring + sizzle |
| sfx/sfx_boost.wav | 2.00 | 1 | -1.0 | -11.3 | | wind rush (rising band-pass sweeps) + buffeting + small flame flare |
| sfx/sfx_wind_loop.wav | 8.00 | 1 | -3.0 | -18.8 | yes | high-altitude wind: 4 gusting noise bands + 6 drifting whistles, exactly periodic |
| sfx/sfx_flame_aura_loop.wav | 6.00 | 1 | -4.0 | -21.9 | yes | soft crackling fire bed around Vahagn |
| sfx/sfx_ui_click.wav | 0.20 | 1 | -6.0 | -28.0 | | Kenney click_001 + faint "forged metal" ping |
| sfx/sfx_ui_hover.wav | 0.14 | 1 | -12.0 | -22.2 | | soft rising airy blip |
| sfx/sfx_wave_start.wav | 5.50 | 1 | -1.0 | -13.8 | | war-horn call (D2, then the fifth A2 with an octave-down horn) + war drums + mountain echo |
| sfx/sfx_victory.wav | 6.00 | 1 | -1.0 | -14.6 | | drum roll, big hit, D-major horn fanfare, zurna trill to D5, choir "ah" |
| sfx/sfx_defeat.wav | 6.50 | 1 | -1.0 | -16.1 | | low drums, mournful duduk descent A-Bb-A-G-F-E-D, choir "oo", drone |
| sfx/sfx_special_nova.wav | 5.40 | 1 | -1.0 | -18.4 | | 0.75 s charge (riser + accelerating tremolo + crackle), then a huge fire blast, expanding ring whoosh, shimmer and sub drop |
| music/music_menu.wav | 72.00 | 2 | -3.0 | -14.0 | yes | 80 BPM, 24 bars. Dam drone (D2/A2/D3), choir pad, kanun arpeggios, two duduk melodies, soft dhol heartbeat, wind |
| music/music_battle.wav | 80.00 | 2 | -2.6 | -14.0 | yes | 120 BPM, 40 bars in 5 sections: dhol/daf groove, low-string ostinato, duduk lead, then zurna lead, a breakdown with a slow duduk line, and a full reprise. Fills, cymbal swells and a riser |
| music/music_boss.wav | 60.00 | 2 | -3.0 | -14.0 | yes | 128 BPM, 32 bars: taiko + 16th-note dhol, 16th-note string ostinato, brass braams, dissonant choir, zurna lead doubled by duduk. Progression D–Eb–Bb–A |

The LUFS figures were measured with the BS.1770-4 implementation in `src/dsp.py` and cross-checked with `ffmpeg -af ebur128`. The two agreed: battle I = -14.0 LUFS (peak -2.6), boss -14.0 (-2.9), menu -14.0 (-3.0). SFX are peak-normalised rather than loudness-normalised, because one-shots are mixed by the game. Set relative levels in UE with Sound Classes or volume multipliers. A starting point: UI 0.5, loops 0.4–0.6, roars/explosions 1.0, music 0.5–0.7 under gameplay.

### Analysis check (`python3 src/analyze.py`)

Every file passes:
- Format is 48 kHz/16-bit.
- 0 clipped samples, and every peak is -1 dBFS or lower.
- DC is below 2e-4 (max 0.000166, in the UI click). Everything else is below 6e-5.
- The loop seam is continuous. "seam" is the jump between the last and first sample, divided by the 99th-percentile sample-to-sample step. Every loop is under 0.5x, which means no click.

The dB value beside the seam figure is the RMS ratio of the last 50 ms to the first 50 ms. It is informational only. In battle/boss the loop restarts on a drum downbeat, so the start is louder.

Pass `--png DIR` to also write a spectrogram of each file. These were inspected during tuning: harmonic structure of the reeds and roar, decay shapes, and high-frequency balance.

## How the sounds are made (src/dsp.py)

- **Noise:** FFT-shaped white/pink/brown noise. It is exactly periodic, so loops built from it are seamless by construction. Turbulence comes from random amplitude modulation.
- **Oscillators:** band-limited additive synthesis (no aliasing). Harmonic weights follow formant curves. A per-sample brightness cutoff gives dynamic timbre: louder notes are brighter. A TPT state-variable filter (numba-JIT) handles moving filters such as whooshes and the roar's formants. Karplus-Strong with all-pass tuning plays the kanun.
- **Duduk / zurna:** continuous legato phrases with portamento, grace notes, mordents and trills, plus delayed vibrato (about 5.3 Hz, ±22–28 cents), breath noise, attack chiff, swell on long notes and re-articulation of repeated notes. The duduk has a formant near 1.15 kHz and stronger odd harmonics. The zurna is nasal and bright, with formants near 2.3 and 1.1 kHz.
- **Mode:** D Phrygian dominant (Hijaz): D Eb F# G A Bb C.
- **Drums:** synthesised dhol (bass "dum" with pitch drop plus inharmonic modes, and a treble "tak" stick), daf with jingles, and taiko. Timing is humanised by ±3–5 ms and velocities are varied.
- **Reverb:** convolution with synthetic impulse responses. Decay depends on frequency across 4 bands, with early reflections and decorrelated left/right channels. For loops the convolution is circular, so the reverb tail wraps from the end of the loop into its start. A plain loop crossfade is not needed: every music track is rendered into a ring buffer of exactly the loop length.
- **Mastering:**
  - Stems are auto-balanced to loudness targets.
  - Then come a gentle stereo-linked compressor, a sub-shelf cut of -3 dB at 85 Hz (so laptop speakers keep their headroom) and +1.5 dB of presence at 3 kHz.
  - Then tanh saturation and a look-ahead brick-wall limiter.
  - Last is iterative normalisation to -14 LUFS.
  - Every step runs loop-aware: the signal is tiled three times and the middle lap is kept.

## UE StarterContent audio (already in the engine, usable directly; not converted)

`/home/samo/UnrealEngine-5.8/Samples/StarterContent/Content/StarterContent/Audio/`. Once StarterContent is in the project, these appear under `/Game/StarterContent/Audio/`.

| Asset | Likely use as a backup or extra layer |
|---|---|
| Explosion01, Explosion02, Explosion_Cue | fireball impact / big explosion alternative |
| Fire01, Fire01_Cue | flame aura / burning-vishap loop |
| Fire_Sparks01, Fire_Sparks01_Cue | ember crackle layer on the flame aura |
| Smoke01, Smoke01_Cue; Steam01, Steam01_Cue | hiss under fire breath / dying vishap smoke |
| Collapse01, Collapse02, Collapse_Cue | vishap body crashing to the ground or into the sea |
| Light01, Light02 (+ _Cue) | small ignition / switch sounds |
| Starter_Wind05, Starter_Wind06 | extra wind ambience |
| Starter_Birds01 | not suitable (peaceful birds) |
| Starter_Music01, Starter_Music_Cue, Starter_Background_Cue | generic, not Armenian; not recommended |

## Importing into UE 5.8 (headless)

Run `src/ue_import_audio.py` when the editor is free. It was **not** run here, because the main agent owns the editor.

```
UnrealEditor-Cmd /var/www/html/Twilight/Game/Twilight.uproject -run=pythonscript \
  -script=/var/www/html/Twilight/art/audio/src/ue_import_audio.py
```

- It imports the WAVs to `/Game/Audio/SFX` and `/Game/Audio/Music` with `unreal.AssetImportTask` and `AssetToolsHelpers.get_asset_tools().import_asset_tasks()`.
- For loops it sets `looping=True` and `set_sound_asset_compression_type(SoundAssetCompressionType.ADPCM)`. ADPCM is a time-domain codec, so it adds no encoder priming gap at the loop point.
- Then it saves each asset with `EditorAssetLibrary.save_asset`.

The script header gives the source references in the UE 5.8 tree:
- `AssetImportTask.h:35-82`
- `IAssetTools.h:541-542, 896-898`
- `SoundWave.h:347-349` (enum), `449-451` (`bLooping`), `489-491` (setter)
- `EditorAssetLibrary.h:281`

Status: UNVERIFIED at runtime. It was written against the headers and has not been executed.

For music in C++, use `UGameplayStatics::SpawnSound2D(this, Wave, Vol, 1.f, 0.f, nullptr, /*persist*/false, /*bAutoDestroy*/false)` (`GameplayStatics.h:699`) with the looping SoundWave. Use `UAudioComponent::FadeIn` / `FadeOut` (`AudioComponent.h:500,511`) when switching menu → battle → boss.

## Credits

See `CREDITS.md`. Everything is original procedural audio, except four Kenney CC0 samples (one click, two punches, one plate) layered into the UI click, the vishap hit and the player hurt.
