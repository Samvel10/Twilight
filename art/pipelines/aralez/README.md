# Aralez: realistic winged dog-spirit (prototype deliverable)

Everything lives under `proto2/aralez/`. **/var/www/html/Twilight was not modified.** I only read from it: the hero assets,
`TwPoseAnimInstance` and `T_Perlin_Noise_M` were copied into the scratch projects.

## 1. What it is
- **Body:** a real dog model. It is the CC-BY Shiba-Inu rig, made 1.35x bigger, so it stands about 80 cm at the
  shoulders, about the size of an Armenian gampr. The rig has 191 bones and includes the jaw, a 6-bone tongue, ears and a 7-bone tail.
  I removed the original clips and wrote **5 new clips in Blender**:
  `Aralez_Idle` (4 s loop), `Aralez_Glide` (3 s loop), `Aralez_Flap` (1 s loop, timed to the wingbeat),
  `Aralez_Land` (1.6 s one-shot: reach → touch → crouch → stand), `Aralez_Lick` (1.6 s loop: head down, jaw open, two tongue licks).
  The jaw is closed in the solemn poses, because the source model grins.
- **Wings:** my own work (CC0). Each wing is built from **feather cards**: 10 primaries, 13 secondaries, 4 tertials,
  greater/median/lesser coverts (top and underside), scapulars, and a tube along the leading edge so the wing has thickness.
  The total is 6.6k tris. The rig has 7 bones (`wings_root`, `L/R_humerus`, `L/R_forearm`, `L/R_hand`) and the span is about 3.9 m.
  The textures are a procedural feather atlas: primary, secondary, covert and contour feathers, with barbs, split vanes, rachis,
  cream-to-gold tips and faint barring. There is also a normal map and a roughness/thickness map.
- **Flap:** done in code by `UAralezWingComponent` (a `UPoseableMeshComponent`). It blends four modes:
  Flap (wingbeat at about 1.1 Hz, with the hand folding on the upstroke), Glide (dihedral, tips curled up, slow "breathing"),
  Mantle (landing air-brake) and Arch (wings raised over the fallen hero). The same math is in `scripts/wingflap.py`, and the
  baked clips `Wing_Flap/Glide/Mantle/Fold` come from it, so the clips and the C++ match.
- **Divine look (kept subtle):** a warm fresnel rim on the fur and feathers (0.18–0.2), feathers lit through from behind
  (two-sided foliage, transmission 0.2), 2 fur shells that only show near the camera (soft silhouette), a 12 cd warm point light
  on the back, and light-shaft bloom from the sun. I tried an additive "golden mist" shell around the body. It washed the dog out
  and looked fake, so I turned it off (`M_AralezHalo` is still there with intensity 0).

## 2. Sources and licences (put in art/CREDITS_3D.md)
| asset | author | licence | link | use |
|---|---|---|---|---|
| "Animated Dog, Shiba Inu" | **quander** | **CC BY 4.0** | sketchfab.com/3d-models/9abfce885a834399b2c3ccaed51cd474 (Objaverse mirror `glbs/000-088/9abfce88…glb`) | Aralez body, rig and texture. Modified: rescaled, clips replaced, new materials |
| Feather atlas, fur strand mask, wings mesh and rig, wing/body animation, highland terrain | this work | CC0 | `scripts/make_feathers.py`, `bl_wings.py`, `bl_dog.py`, `make_terrain.py` | |
| kloppenheim_06_puresky (HDRI), aerial_grass_rock, grass_medium_01, boulder_01, rock_moss_set_02, kite_shield, antique_estoc, wooden_axe | Poly Haven | CC0 | polyhaven.com | test scene only |
| Fallen warrior | Andy Woodhead, "Rigged for UE4 – Spartan" | CC BY 4.0 | (already credited by the hero task) | test scene only |

Credit line: *Aralez body: "Animated Dog, Shiba Inu" by quander (sketchfab.com/quander), CC BY 4.0, modified
(rescaled, re-animated, new materials); wings, feathers and animation: original.*

**How I checked originality.** quander published this model on 2019-07-28 with an original description, and quander has
other original work (an animated T-Rex). The models with the same 33,384 faces ("Playful Dog", "Doge", "Dog gold" by Yapoco,
and others) all came later and are re-uploads, so I skipped them. I also rejected these:
- 3DHaupt's "Wolf with Animations": CC-BY-**NC-SA**.
- The WildMesh wolf: NC.
- AnimalMesh3D: says "personal use only".
- The 107-clip "Labrador": tagged `cotw`, so likely ripped from a game.
- sdpm's "Italian White Wolf": part of a 2021 burst of zoo animals with copied Wikipedia text.
- Xfdfgd/kenchoo wolves: not in Objaverse, so not downloadable without a login.
- Every wing/angel model I found was either a costume shape or derivative (for example fae → Adipriatna).

That is why I built the wings myself.

## 3. Files
```
deliver/
  assets/  SK_Aralez.glb (dog, 5 clips)   SK_AralezWings.glb (wings, 4 baked clips)   SK_Aralez.glb.socket.txt
           T_Feather_BC.png (sRGB+alpha)  T_Feather_N.png  T_Feather_RT.png (R rough, G thickness, B ao)  T_FurStrands.png
  src/     shiba_inu_quander_original_9abfce88.glb   (untouched download)
  scripts/ build_aralez.sh  -- the whole pipeline: textures -> Blender (wings, dog) -> UE import + materials + MIs
           bl_common.py poses.py bl_dog.py bl_wings.py wingflap.py make_feathers.py make_terrain.py
           ue_import.py (Interchange, build_nanite=False; steps dog,wings,tex,mats,mis [+ph,hdri,terrain,scene for the test map])
           ue_build_maps.py, shoot.sh, run_cmd.sh (test maps and -game screenshots), hdr_sun.py (finds the sun in an HDRI)
  cpp/     AralezWingComponent.h/.cpp  (procedural wings)   AralezBodyComponent.h/.cpp (dog + wings + shells + light)
           AralezShowcase.h/.cpp (test actor: fixed mode or Glide->Flap->Land->Lick cycle)
  shots/   see section 7
```
To run it: `BLENDER=<blender 4.2> deliver/scripts/build_aralez.sh /var/www/html/Twilight/Game/TwilightAssets.uproject /Game/Twilight/Aralez`.
I tested it end to end into a fresh project. It produces:
- `/Game/Twilight/Aralez/Dog/SK_Aralez/SkeletalMeshes/SK_Aralez` and the clips `SK_AralezAralez_{Idle,Glide,Flap,Land,Lick}`
- `/Game/Twilight/Aralez/Wings/SK_AralezWings/SkeletalMeshes/SK_AralezWings` (+ `SK_AralezWingsWing_*`)
- `/Game/Twilight/Aralez/Mat/{M,MI}_AralezFur, M/MI_AralezFeather, M_AralezFurShell, MI_AralezFurShell_1/2`

Blender 4.2 LTS comes from download.blender.org (no login). It was used headless only.

## 4. Material parameters (final; set by `ue_import.py` step `mis`)
| MI | parent | values |
|---|---|---|
| MI_AralezFur | M_AralezFur (default lit, two-sided) | Tint (1,.96,.90), Desat .15, Brightness 1, RoughScale .85 (× MR.G), Specular .30, RimIntensity .18, RimExp 3.2, RimColor (1,.74,.42), DivineGlow .03 |
| MI_AralezFeather | M_AralezFeather (TwoSidedFoliage, masked 0.4, two-sided) | Tint (1,.97,.92), JitterLo/Hi .80/1.12 (vertex colour G = random per feather), UnderDark .78 (back faces), RoughScale 1.2 (× RT.R), Specular .22, TransColor (1,.70,.40), TransIntensity .20 (× (1−RT.G)), RimIntensity .20 (× (.35+.65·vertex R)), RimColor (1,.76,.45) |
| MI_AralezFurShell_1/2 | M_AralezFurShell (masked .2, WPO) | ShellFrac .5 / 1.0, FurLength 1.4 cm (+ droop .35), StrandTiling 70, Taper .75, DarkCut .12 (no fur on eyes, nose or pads), RootDark .75 → TipBright 1.05 |

Lighting the shots were judged under (test map only): sun 9 lux at 3600 K, pitch −5°, yaw 128°. This matches the HDRI
sun at azimuth −52° and elevation 4.6°, which I measured with a zenith probe. Skylight is the kloppenheim_06_puresky cubemap at
intensity 1, visible dome 4 km. Height fog: density .02, falloff .35, start 15 m, directional inscattering (1,.55,.28).
Manual exposure −0.7 EV, bloom .45.

**Gotchas I hit (they apply to the game import too):**
1. **Skinned-mesh textures must be `never_stream`.** Interchange skeletal meshes have no UV-density data, so in `-game` the
   streamer keeps their textures at the 1×1 mip and the dog renders white. `ue_import.py` sets never_stream on them.
2. The MR texture is linear colour. Use a **Linear Color sampler, not Masks**, or the material falls back to the default material.
3. Interchange leaves glTF material instances in the mesh slots, and those multiply by vertex colour (the wings turned rainbow).
   `mis` reassigns the slots, and `UAralezBodyComponent` sets the MIs explicitly as well.
4. Asset-registry order is not stable. Read texture roles from the Interchange MI, not from list order.
5. In the test level a dome bigger than about 20 km across is culled, and `fog_cutoff_distance` blacks out anything past it.

## 5. Wing attachment and the procedural flap
- The dog mesh faces **+Y** in mesh space, so the component yaws it −90 to face +X. Blender maps to UE as (x, −y, z)×100.
- **Wing attachment:** `Wings->SetupAttachment(Dog, "chest_jnt")` with relative location **(0, 4.6, 5.5)** and zero rotation.
  `chest_jnt` has identity rotation in the reference pose, so the wing root sits between the shoulder blades and follows the
  chest in every clip. `SK_Aralez.glb.socket.txt` has the exact position.
- **`UAralezWingComponent::WingPose()`** returns, for each bone, degrees of (twist about span, −elevation, sweep back).
  `ApplyPose()` builds the wing frame from the reference skeleton (Span = shoulder→wrist, Up = +Z, Back is signed by the elbow
  offset). It applies the angles as "rotate A toward B" quaternions, so the result is correct in either handedness. It composes
  them down the chain (humerus · forearm · hand) on top of the reference component-space rotations, then calls
  `SetBoneRotationByName(…, ComponentSpace)`. Mode weights ease in at `BlendSpeed` 3/s. `GetStrokePhase()` lets you sync the
  body (the Flap clip has its top of stroke at phase .25), and `GetBodyLift()` gives a ±6 cm bob for the wingbeat.
  I checked it at runtime in a C++ test project: the bone positions match the Blender math (glide: forearm ~11° up, ~7° back).
  See `shots/flap_cycle_cpp_procedural.jpg` and `cpp_mode_cycle_glide_flap_land_lick.jpg`.

## 6. Integration (C++, not applied)
1. Run the pipeline with dest `/Game/Twilight/Aralez`. Add `cpp/AralezWingComponent.*` and `cpp/AralezBodyComponent.*`
   to `Game/Source/Twilight/`. They use `UTwPoseAnimInstance` and need no new modules: Engine only.
   They compile cleanly on UE 5.8 (built in `proto2/aralez/cpp_test`).
2. In `AAralezSpirit::BuildBody()`, replace the sphere/cone parts with:
```cpp
#include "AralezBodyComponent.h"
Aralez = NewObject<UAralezBodyComponent>(this, TEXT("Aralez"));
Aralez->SetupAttachment(BodyRoot);
Aralez->SetRelativeLocation(FVector(0, 0, -60));   // feet under the capsule centre: the dog's root is at its paws
Aralez->RegisterComponent();
Aralez->Build();                                   // dog + wings at chest_jnt + 2 near-camera fur shells + warm light
```
   In `Animate()` / `Move()`, use `Aralez->SetMode(EAralezMode::Flap)` while climbing or dashing and
   `EAralezMode::Glide` while descending. Use `EAralezMode::Land` when touching down by a fallen hero, then
   `EAralezMode::Lick` while healing. Land falls back to Idle by itself. `GetWings()->SetFlapRate(1.0f + Speed01 * 0.5f)`.
   Delete `WingL/WingR` and the procedural `Flap` code.
   Remove the head/body glow spheres. Keep the trail if wanted, but at half opacity: the fur and feathers now carry the look.
3. Myth staging, as `MYTHS_AND_GAMES_hy.md` asks: the Aralez comes down out of the sunset clouds onto Ara's field, lands
   beside each fallen hero (mantle pose), and licks the wounds (arch-wing pose over the body). The licked hero then stands up.
   The 5 m lick shots show the exact staging: dog at head + 72 cm along the body normal, facing the head.

## 7. Screenshots (`deliver/shots`, in-game `-game` renders, 1600x900, Iris Xe)
- `aralez_glide_5m.jpg`, `aralez_lick_5m.jpg`, `aralez_lick_face_5m.jpg`: 5 m
- `aralez_flap_20m.jpg`, `aralez_landing_20m.jpg`: 20 m
- `aralez_descent_60m.jpg`, `battlefield_60m.jpg`: 60 m
- `comparison_before_after.jpg`: the current game Aralez next to the new one, with 2.5–5x crops of the 20/60 m shots
- `flap_cycle_baked_clips.jpg`: 8 frames 0.12 s apart, clips playing in-game
- `flap_cycle_cpp_procedural.jpg`: the same, driven by the C++ component
- `cpp_mode_cycle_glide_flap_land_lick.jpg`
- `perf_stat_unit_irisxe.jpg`, `feather_atlas.jpg`

## 8. GPU cost (Iris Xe, 1600x900, `stat unit`, no other UE process running)
| view | with Aralez + 2 shells | no shells | no Aralez |
|---|---|---|---|
| licking, 5 m (screen-filling) | 21.6 ms | 22.3 ms | 20.3 ms |
| flying, 5 m | 13.5 ms | 14.4 ms | 12.5 ms |
| 20 m | 10.95 ms | — | 10.6 ms |

The Aralez costs **≈1–2 ms GPU up close and ~0 at 20 m+**. The shells are within run-to-run noise (±1 ms), and they switch off
beyond 9 m anyway. The mesh is 33k tris (body) + 6.6k (wings), with one 1k colour texture, one 1k MR texture and a 2k feather atlas.
When another agent's UE process shared the GPU, the same views measured 5–8 ms higher, so compare numbers only from quiet runs.
The heavy 60 m test view (43 ms) is my test scene, with 2,000 instanced Poly Haven grass clumps and no LODs. It is not the Aralez.

## 9. Known limits and next steps
- The source is a Shiba, so the face reads as a friendly dog rather than a wolf. The coat is fawn/cream (Shiba/Akita colouring)
  and the build is stocky; the 1.35x scale doesn't change those proportions. A CC-BY realistic *wolf* or *gampr* with a good rig
  was not available without a login.
- The wing fold is rigid per feather. For a full fold, the feathers would need fan bones.
- The fallen warrior uses the Spartan `MM_Fall_Loop` pose laid on its back, because the retargeted death clips end bent over
  (their root motion is lost).
- There are no run or jump clips. `poses.py` has the GALLOP_1/2 key poses ready for a gallop cycle if gameplay needs one.
