# SETUP_LOG: proto3/firehair_strands (approach B, geometric fire hair). Newest at the bottom.

1. **Recon.** Read `VahagnCharacter.cpp`, the proto2 pipeline scripts and the hero/Hayk assets. In Blender, `spartan_vahagn.glb` and `hayk.glb` have an identical head (6 881 head verts, same bbox). The head is bald, and the beard/moustache/brows are one sculpted strip with its own UV island. The eyes are separate spheres with the iris at the UV edge.
   Decision: use the game's own `spartan_vahagn` with the helmet section hidden. All game clips (incl. `MM_Fall_Loop`) work and integration is trivial; Hayk has no `MM_Fall_Loop`.
2. **Own scratch project** `FireHair/`. Copied from the game: `Content/Twilight/Hero` and `M_HeroSkin`/`M_HeroPBR`/`SP_HeroSkin`. Copied from HumansTest: `M_SkyHDRI`, `Env` (HDRI/ground) and the StarterContent noise. Config is the same as HumansTest. 58 MB.
3. **Probe (UE).** Head bone at component (0,−3.79,186.55) cm; UE = (100x, −100y, 100z) of the glTF/Blender frame; `M_HeroSkin` is default-lit. Note: exec'ing `materials_build.py` overrides `log()`, so `fh_common` re-defines it afterwards.
4. **Textures** (`gen_textures.py`): fBm noise, a black-body LUT, and a body mask (facial hair island + scalp from a hairline function + iris).
5. **Flame locks** (`gen_firehair.py`). The first version used thin streamers that looked like a Super-Saiyan crest. Changes: added broad "cap" tongues, shortened the hair, made the beard compact, and increased segments 12→16 to remove kinks.
6. **Bugs fixed on the way:**
   (a) Interchange puts the mesh in `<dest>/<name>/StaticMeshes/`. We import into `Meshes/Import` and rename.
   (b) Lightmap-UV generation overwrote UV1 and could not be switched off from the commandlet (`StaticMeshEditorSubsystem` is None). The per-lock id is now packed into the integer part of UV0.
   (c) glTF V flip: Blender writes 1−V and UE keeps glTF V, so the generator writes `1-(v+2b)`.
   (d) Close-up framing: `get_socket_location` is unreliable in the commandlet. The head is now computed from the ref-pose component transform.
   (e) **The `xdotool search` name match is OR-ed by default.** The old scripts captured (and the perf script typed into) another agent's "FireHairTest" window. Fixed with `--all --pid`, and all deliverable shots were re-taken afterwards.
7. **Material look iterations** (it1–it11 in `work/`):
   - Dark "black" smudges: opacity now follows temperature.
   - Overexposed white: intensity 22→12, HeatMin/TipCool tuned.
   - Paper-leaf edges: softer EdgeSoft/Sharp, and DepthFade 4 cm.
   - Face blown out by the fire light: 1800→700, moved above the brow.
   - Chase view: flames hidden behind the shoulders. Flight Wind (−24,0,6)→(−45,0,40)→(−25,0,60), so the blaze rises above the back.
8. **Perf** (`perf.sh` + `profilegpu`, interleaved): the draw costs 0.20 ms at 3 m and 0.09 ms at 6 m; the light 0.15–0.2 ms at 3 m.
   An unexpected +1.1 ms turned out to be the translucency lighting volume, which only switches on when there is translucency on screen. Against a fair baseline with a translucent stand-in for the hand flames (`OrigFx`), the whole-frame delta is ≈0. The fire light got `bAffectTranslucentLighting=false`.
9. **Reproducibility**: `build_all.sh` was run from scratch. The menu re-shot differs from the delivered shot by a mean abs diff of 0.86/255, which is flicker timing only.
10. **Cleanup**: deleted `FireHair/DerivedDataCache`, `Intermediate` and `Saved`, and the iteration screenshots in `work/it*`.
