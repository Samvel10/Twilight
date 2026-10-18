# Audio credits — Vahagn: Vishapakagh

All music and almost all SFX are **procedurally synthesized** by the scripts in
`src/` (numpy/scipy, no samples, no paid or AI services). Seeds are fixed, so a
re-run gives the same files.

Chapter 2 «Hayk» and chapter 3 «Aralez» (13 SFX + `music_hayk`, `music_aralez`, made by
`src/gen_chapters23.py`) are 100 % procedural: no downloads and no third-party samples.

## Third-party CC0 recordings (layered into 3 SFX)

| Source file | Used in | Pack | Author | License |
|---|---|---|---|---|
| `click_001.ogg` | `sfx_ui_click.wav` (main transient) | Interface Sounds 1.0 — https://kenney.nl/assets/interface-sounds | Kenney (www.kenney.nl) | CC0 1.0 — http://creativecommons.org/publicdomain/zero/1.0/ |
| `impactPunch_heavy_000.ogg` | `sfx_vishap_hit.wav` (pitched down to 0.72x) | Impact Sounds 1.0 — https://kenney.nl/assets/impact-sounds | Kenney | CC0 1.0 |
| `impactPunch_heavy_002.ogg` | `sfx_player_hurt.wav` (0.85x) | Impact Sounds 1.0 | Kenney | CC0 1.0 |
| `impactPlate_heavy_000.ogg` | `sfx_player_hurt.wav` (armour layer, 0.9x) | Impact Sounds 1.0 | Kenney | CC0 1.0 |

The original `.ogg` files, 48 kHz mono WAV decodes (`ffmpeg -ac 1 -ar 48000`) and the
pack license texts are in `src/cc0_sources/kenney/`. CC0 needs no attribution;
we list it anyway. Delete that folder and the generator falls back to the purely
procedural layers.

## Unreal Engine StarterContent (engine-bundled, not copied here)

The UE `StarterContent` audio, under the Unreal Engine EULA, can be used in-engine
directly. It is listed in `README.md`. None of it is used in these WAVs.
