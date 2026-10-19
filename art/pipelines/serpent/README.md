# Serpent vishap: real snake scan, spline-driven, any length

A giant serpent vishap with a real snake's head, scales, eyes and open mouth. It is built from a photogrammetry scan of
a real pit viper. The scan is straightened, elongated, retopologised and rigged as a 50-bone chain. A drop-in C++
component (`USerpentBodyComponent`) poses the bones every frame along any world-space path: the head's flight trail,
an arch rising out of a lake, a coil, and so on. Optional parts: keratin horns, an ember glow in the mouth only, and five
colour variants. There are no wings, which matches the myth (serpent and fish-like vishaps).

## Source and licence
- Body and head: "ヒメハブ Okinawa Pit Viper / Dwarf Lancehead, *Ovophis okinavensis*" by **ffish.asia / floraZia.com**,
  sketchfab.com/3d-models/dwarf-lancehead-snake-ovophis-okinavensis-18858ce6cc7c4a74b7f208a1c3a7b195.
  - The Sketchfab API today lists it as **CC0 Public Domain**. The 2022 Objaverse GLB metadata says CC-BY-4.0, so credit it anyway.
  - It is an original museum-style specimen scan. ffish.asia scans hundreds of Japanese species and this is their own upload, not a rip.
  - The GLB was downloaded without login from the Objaverse mirror:
    https://huggingface.co/datasets/allenai/objaverse/resolve/main/glbs/000-147/18858ce6cc7c4a74b7f208a1c3a7b195.glb
  - Credit line: *"Vishap" serpent body: "Okinawa Pit Viper (Ovophis okinavensis)" 3D scan by ffish.asia / floraZia.com
    (CC0 / CC-BY 4.0), straightened, elongated, retopologised, re-textured and rigged.*
- Horns (`SM_VishapHorns.glb`) and scale detail maps (`T_VishapScales_*`): procedural, own work, CC0.
- Proto backdrop only (not delivered): Poly Haven CC0 scans and the belfast_sunset_puresky HDRI, copied from the islands proto.

## Files (deliver/)
| file | what |
|---|---|
| `SK_VishapSerpent.glb` | LOD0: 40k tris, 23k verts, 50 bones, UV0 (baked atlas), UV1 (body-aligned scale coords), COLOR_0 (masks + UV1 frame) |
| `SK_VishapSerpent_LOD1.glb`, `_LOD2.glb` | 12k / 4k tris, same skeleton and UV0 atlas, so the textures are shared |
| `SM_VishapHorns.glb` | optional horn pair, 10k tris, authored in Head-bone space (attach at bone `Head`, identity offset) |
| `textures/T_VishapSerpent_D.png` | 2k albedo, baked from the scan |
| `textures/T_VishapSerpent_N.png` | 2k tangent normal (DirectX/UE green, no flip), baked from the 550k-tri scan |
| `textures/T_VishapSerpent_M.png` | 2k mouth-interior mask (palate, tongue, mouth floor): drives the ember glow |
| `textures/T_VishapScales_N.png`, `_H.png` | 1k tiling keeled-scale normal + cavity (8x8 scales), sampled in UV1 |
| `cpp/SerpentBodyComponent.h/.cpp` | **the drop-in component** (UE 5.8, Engine module only) |
| `cpp/SerpentDemo.h/.cpp` | proto actor: analytic flight paths, camera, perf A/B, screenshots (reference only) |
| `cpp/AVishap_integration.md` | exact code to wire it into the existing `AVishap` (Trail, JawOpen, HitFlash, hit volumes, mouth) |
| `scripts/` | full pipeline (see below) |
| `shots/` | renders (see the end of this file) |

## Skeleton and bone naming
- `Head`: root, at the neck pivot (origin). +X runs to the snout and the head is 0.51 m long at scale 1. +Z is up.
- `Jaw`: child of `Head`, the hinge at (0.12, 0, -0.014) m. Lower jaw, mouth floor and tongue are weighted to it.
- `Spine_01` … `Spine_48`: a chain along -X, 0.198 m apart, with the tail tip at -9.49 m. Every rest rotation is identity.
- Total rest length is 10.0 m (1000 cm). Scale the component to get any size: 2.6 = 26 m, 9 = 90 m boss.
- Skinning uses 2 bones per vertex with a smoothstep between neighbouring links. The head is rigid; the jaw blends over
  6 cm at the hinge.

## The spline-driving algorithm (`USerpentBodyComponent::ApplyPath(Path, UpHint, Time)`)
1. `Path[0]` is the head and the following points run back along the body, at any spacing. The code builds the
   cumulative arc length.
2. Each chain bone *i* has a rest distance `d_i` from the head (from the reference skeleton). Its position is the path
   point at arc length `d_i × componentScale`, found by binary search and lerp. The tangent blends the neighbouring
   segment directions so it stays C1-ish. Past the end of the path the tail continues straight.
3. Frames: forward = towards the head. Up is parallel-transported from the head (UpHint projected), then blended
   towards UpHint by `UprightBlend` (0.35) so the back stays up without flips.
4. Bank comes from the curvature of the path (1/m) × `BankPerCurvature` (900 deg·m, clamp 45°). It is smoothed over
   neighbouring links and never taken from the swim wave, because that would corkscrew the body.
5. A travelling swim wave goes on top: lateral + 25 % vertical,
   `A·L·sin(2π·d/(λ·L) − 2π·f·t)` with an envelope of 0 at the head rising to full by 18 % of the body.
   Defaults are A = 0.05, λ = 0.38, f = 1.1 Hz.
6. Final forward = central difference of the posed neighbours. Bone world rotation =
   `MakeFromXZ(F,U) · RestFrame⁻¹ · RefRotCS_i`. Writing the result as component space → local
   (`BoneSpaceTransforms`) is O(N) with a single `RefreshBoneTransforms()`.
   The `Poseable SetBoneTransformByName` path is O(N²) and is avoided.
7. Extras: `HeadScale` (1.35) scales the head uniformly and thickens the first 4 neck links in cross-section only.
   `JawOpen` opens the jaw around the lateral axis: −0.8 closes the scan's half-open mouth, +1 opens it ~38° wider.
   `HeadAttachment` is a static mesh attached to bone `Head`. `LodDistances` forces the LOD by the nearest body point.
   `CalcBounds` covers the posed bones.
CPU cost (measured, Development build): `ApplyPath` takes about 86 µs per serpent per frame, including `RefreshBoneTransforms`. There is no animation graph and no physics asset.

## Materials (`/Game/Twilight/Vishap/Materials`)
`M_VishapSerpent`: Clear Coat shading model, built through MakeMaterialAttributes because the clear-coat pins are
hidden from Python. Parameters and their defaults:

| group | param | default | meaning |
|---|---|---|---|
| Colour | Recolor | 0.85 | 0 = scan colours, 1 = fully re-tinted by the palette below |
| Colour | DarkColor | (0.010, 0.017, 0.008) | blotches, back: green-black |
| Colour | LightColor | (0.22, 0.15, 0.05) | ground scales, belly: dull bronze |
| Colour | PatternGain / PatternContrast | 2.2 / 1.6 | scan-luminance → palette mapping |
| Colour | Brightness | 1.0 | |
| Surface | NormalStrength | 0.7 | baked macro normal (scan) |
| Surface | ScaleDetail | 0.85 | tiling keeled scales (UV1), off on the head, wide ventral plates on the belly |
| Surface | CavityStrength | 0.45 | darkens and roughens the grooves between scales |
| Surface | WetRough / GrooveRough / Wetness / WetTightness | 0.26 / 0.62 / 1 / 6 | wet scale tops |
| Surface | ClearCoat / ClearCoatRoughness | 0.45 / 0.12 | thin wet film: sharp sunset glints |
| Surface | Specular / GrooveAO | 0.45 / 0.6 | |
| Mouth | MouthGlow | 3 | ember emissive in the mouth mask only. Drive it to about 20 during the breath windup |
| Mouth | EmberDetail | 3 | keeps the palate and tongue structure inside the glow |
| Mouth | EmberColor / MouthTint | (1, 0.12, 0.02) / (0.4, 0.07, 0.035) | |
| Game | HitFlash / FlashColor | 0 / (1, 0.85, 0.7) | same parameter name as the game's other materials |

Instances: `MI_Vishap_Default` (green-black / bronze), `MI_Vishap_Bronze`, `MI_Vishap_Olive`, `MI_Vishap_Storm`
(cold slate, boss), and `MI_Vishap_Scan` (original specimen colours). `M_VishapHorn` (keratin: RootColor, TipColor,
TipFalloff, RingFreq, Roughness) is on `SM_VishapHorns`.

The UV1 detail normal is rotated into the UV0 tangent frame per vertex. COLOR_0 stores R = body mask,
G/B = cos/sin of the UV0→UV1 tangent angle, and A = mirrored. The values are pre-linearised because UE stores vertex
colours as sRGB bytes. If the mesh is re-imported with different tangents, run `rig.py` again; never edit vertex colours by hand.

## Proto project (for re-rendering)
`SerpentProto/SerpentProto.uproject` is a C++ scratch project. Build it with
`~/UnrealEngine-5.8/Engine/Build/BatchFiles/Linux/Build.sh SerpentProtoEditor Linux Development -project=…`, then run
`scripts/build_ue.sh` to import and `scripts/final_shots.sh` for the whole comparison set. `ASerpentDemo` reads the
`-SerpMode=sky|rise|coil|line -SerpT= -SerpCamDist= -SerpCamYaw= -SerpCamPitch= -SerpCamAt= -SerpChase -SerpHorns
-SerpJaw= -SerpMat= -SerpScale= -SerpToggle= -SerpProfAB` switches.

## Pipeline (all scripts in `scripts/`, run from the proto folder)
1. `sfsearch.py`: Sketchfab public search (no login). The candidates were then filtered to the Objaverse mirror and
   checked on contact sheets (`notes/sheet*.jpg`). Rejected: fan art and game rips (Subnautica "Leviathans"),
   low-poly stylised meshes, coiled scans (they cannot be straightened), and statues.
2. `build_mesh.sh` runs the offline steps (numpy/scipy/pymeshlab/xatlas in a venv; gltf-transform for the weld):
   `merge.py` (bake the 8 sub-meshes, drop the scale-bar box) → `gltf-transform weld` → `straighten.py` (spine from slice
   centres, rotation-minimising frames, project every vertex to (s, u, v), elongate the body ×1.25 and keep the head,
   even out the specimen's food bulges, 10 m long, +X = snout) → `decimate.py` (QEM to 40k) → `bake.py` (xatlas unwrap,
   7M surface samples of the 550k scan, kNN bake of albedo + tangent normal, geometric mouth mask, dilation) → `rig.py`
   (bones, weights, jaw, UV1, vertex-colour frame, seam split, GLB) → `lod.py` (texture-preserving QEM to 12k / 4k on
   the same atlas) → `scales.py` (detail maps) → `horns.py`.
3. `ue_build.py` (UE 5.8 editor Python, headless): Interchange import with **build_nanite=False**, no materials and no
   physics asset → textures (normal maps with **no green flip**) → `M_VishapSerpent` + MIs → horns + `M_VishapHorn` → LOD1/LOD2
   import (`SkeletalMeshEditorSubsystem.import_lod`) → proto level (`SERP_LEVEL=0` skips the level for the game project).
   Environment: `SERP_SRC`, `SERP_DEST` (default `/Game/Twilight/Vishap`), `SERP_CLEARCOAT=0` for default lit.
4. `shot.sh` / `shotr.sh` render a frame from the C++ demo in `-game -RenderOffscreen` with screenshot and quit. They
   retry when the shared Iris Xe runs out of memory because other agents' editors are open.

## Measured on the Iris Xe (1600x900, sunset scene; 2–3 other agents' editors shared the GPU the whole time)
- `ProfileGPU` A/B in one process (`-SerpProfAB`), serpent at 25 m filling about 1/3 of the frame, with horns:
  GPU skin cache **0.14 ms**, shadow depths **+0.3 ms** (0.67–0.72 visible vs 0.28–0.42 hidden). The base pass and prepass
  difference was lost in the noise (±0.3 ms). Estimated total: **≈0.6–0.9 ms close up**, less at distance with LOD1/LOD2.
- Whole-frame A/B (visibility toggled every 4 s) could not be measured cleanly. Other agents' renders moved the
  frame time between 20 and 100 ms. Re-run `SerpentProto … -SerpToggle=4` (or `-SerpProfAB`) on a quiet GPU
  for a final number.
- LOD switch (scale 4 = 40 m serpent), checked via the predicted LOD in the log: LOD0 at 20 and 60 m, LOD1 at 150 m,
  LOD2 at 400 m.
- The scene itself (proto backdrop, fog, TSR at 83 % screen percentage) costs ≈20 ms GPU. That is the proto scene, not the serpent.

## Screenshots (`shots/`)
- `cmp_final_set.jpg`: 20 m close-up (horns, open jaw, ember mouth), 60 m and 150 m sky, rise from the lake, chase cam, backlit.
- `F*.jpg`: the same frames at full resolution. `F1_close20m_plain` = no horns, jaw closed (JawOpen −0.8).
- `cmp_materials.jpg`: Default / Bronze / Olive / Storm / Scan colours.
- `cmp_scale_detail_before_after.jpg`: chase cam with only the baked scan normal (lumpy) vs the UV1 keeled-scale detail.
- `cmp_bank_fix_before_after.jpg`: banking computed from the wave (corkscrew notches) vs from the path curvature.
- `candidates_sheet1/2.jpg`: the candidates that were looked at. `scan_straightened_splat.jpg`: the scan after straightening.

## Known limits and next steps
- The source albedo is 1k for the whole snake. Far and mid views are fine; very close views get their detail from the
  procedural scale normal and cavity.
- There is no splash or foam where the body cuts the lake surface: add the game's `TwFx::Splash` at the waterline
  crossing points (`GetBodyPoint` sampled along the body where z changes sign).
- The horns are procedural, so they read best at 20 m and beyond. They can be dropped (`HeadAttachment = nullptr`)
  for a pure giant-viper look.
