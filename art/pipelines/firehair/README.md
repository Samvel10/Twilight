# Vahagn: hair of fire, beard of flame (approach B: geometric flame strands)

> "...he had hair of fire, a beard of flame, and his eyes were suns." (Movses Khorenatsi, *The Birth of Vahagn*)

The hero keeps the realistic CC-BY Spartan body that the game already uses (`spartan_vahagn`). The bronze helmet is
hidden. The head is the same mesh as Hayk's (6 881 head-weighted vertices, same bounding box, checked in Blender).
These pieces are added:

| piece | what it is |
|---|---|
| **flame locks** `SM_VahagnFireHair` | One static mesh of 12 416 triangles with **194 procedural flame tongues**: 59 wide "cap" tongues that form a burning mass on the scalp, 67 taller hair tongues that rise up and back, 19 sideburn tongues and 49 beard tongues. The beard tongues hang from the jaw and chin and their tips flick forward and up. Each tongue is 2 crossed, twisting, tapered ribbon cards (16 segments). It is rooted on the real scalp and jaw polygons of the Spartan head, Poisson-sampled. The mesh is authored in the hero's component space and attached to the `head` bone with the inverse ref-pose head transform. There is no jaw bone, so the beard moves rigidly with the head. |
| **fire material** `M_FH_FireStrand` | Translucent, **unlit**, two-sided. Two samples of a scrolling tileable fBm texture erode a soft tongue shape (wavy edges, root fade-in, more erosion towards the tip). The result is a temperature that drives a black-body LUT: deep red to orange to yellow to white. The core is hot and the tips are cooler, redder and more transparent. **Opacity follows temperature**, so dim fire becomes transparent instead of black. The material adds a per-lock flicker, a DepthFade (4 cm) so the cards don't show hard lines where they cut into the scalp, and world-position-offset sway. A `Wind` vector (cm at the tip, v²-weighted) streams the flames up and back in flight. Each lock's random id is packed into the integer part of UV0, so only one UV channel is needed (UE's lightmap-UV build overwrites UV1). |
| **fire skin** `M_FH_HeroSkinFire` / `MI_FH_VahagnBodyFire` | The game's `M_HeroSkin` graph, rebuilt with the same parameters (`MI_Vahagn_Body` values copied), plus `FireMaskTex` (`T_FH_BodyMask`). R is the ember glow on the beard/brow geometry and the scalp: animated ember noise with a flicker. G is the iris, emissive gold at 90: **eyes like small suns** that bloom. B recolours the facial hair and scalp to soot-black char, so no brown "wig" hair shows between the flames. The face skin is left unchanged. It keeps `HitFlash`/`FlashColor`/`EmissiveIntensity`/`CrestGlow`/`RimIntensity`, so the existing MID code keeps working. |
| **fire light** | One unshadowed point light (700 unitless, radius 130 cm) inside the flames above the brow. The burning hair warms the forehead and face. It does not affect the translucency lighting volume. |

All geometry, textures and materials are procedural and original to this work. No third-party fire assets are used.

## Screenshots (`deliver/shots/`, 1600×900, `-game` window captures, sun 8° colour (1,.56,.32))
1. `1_menu_front_3m.png`: menu-style front portrait at 3 m (FOV 40, hover pitch −20° as in the game)
2. `2_chase_6m_flying.png` (+ `2_chase_6m_flying_crop2x.png`): the game's chase boom (560 cm, socket (0,85,110), FOV 88), with the body pitched −62°, `MM_Fall_Loop`, flight `Wind`
3. `3_front_view_5m.png` (+ `_crop2x`): the game's front view (boom yaw +180°, −8°, socket (0,0,70), FOV 88)
4. `4_close_3q_head.png`: side 3/4 close-up of the head (FOV 40, 1.5 m). `work_anim_frame_b.png` is the same view 0.35 s later and shows the flow/flicker animation.
5. `5_current_helmet_menu_3m.png`: the **current** helmeted Vahagn with the same camera. `5_compare_current_vs_fire.png` puts the two side by side.

`contact_sheet.jpg` collects them all.

## Built assets (scratch UE project `proto3/firehair_strands/FireHair`)
```
/Game/Twilight/FireHair/Meshes/SM_VahagnFireHair          static mesh, 12 416 tris, 1 material slot, no collision, no shadow
/Game/Twilight/FireHair/Materials/M_FH_FireStrand         master: translucent unlit, two-sided, WPO
/Game/Twilight/FireHair/Materials/MI_FH_FireStrand        default instance (assigned on the mesh)
/Game/Twilight/FireHair/Materials/MI_FH_FireStrand_Flight look-dev instance with Wind=(-25,0,60) (the game sets Wind per tick)
/Game/Twilight/FireHair/Materials/M_FH_HeroSkinFire       master: default-lit skin + fire mask (same parameters as M_HeroSkin)
/Game/Twilight/FireHair/Materials/MI_FH_VahagnBodyFire    body slot 0 (MI_Vahagn_Body values + T_FH_BodyMask)
/Game/Twilight/FireHair/Materials/M_FH_Invisible          look-dev only (hides the helmet in editor maps)
/Game/Twilight/FireHair/Textures/T_FH_Noise               256² tileable fBm (R billows, G turbulence, B ridged)
/Game/Twilight/FireHair/Textures/T_FH_FireLUT             256×4 black-body ramp, uncompressed, clamped, no mips
/Game/Twilight/FireHair/Textures/T_FH_BodyMask            1024² RGBA mask in the Spartan Body UV
/Game/Proto/L_FH_Menu, L_FH_Chase, L_FH_Front, L_FH_Close, L_FH_Orig (+ L_FH_ChaseSide, L_FH_ChaseOrig, L_FH_MenuNoHair, L_FH_MenuNoLight, L_FH_OrigFx for diagnostics/perf)
```
The source files are in `deliver/assets/`: `SM_VahagnFireHair.glb`, the three `T_FH_*.png` and `headpolys.npz` (the extracted head polygons).

### Tunable parameters
- `M_FH_FireStrand` (group Fire): `Intensity` 12, `HeatMin` 0.55, `TipCool` 0.9, `Opacity` 0.72, `OpacityGain` 1.7, `FlowSpeed` 1.1, `NoiseLength` 0.75, `EdgeWobble` 0.3, `EdgeSoft` 1.1, `Sharp` 1.7, `Erode0` 0.3, `ErodeTip` 0.75, `RootFade` 14, `Flicker` 0.15.
- `M_FH_FireStrand` (group Motion): `Sway` 2.2 cm, `Wind` (vector, cm at the tip).
- `M_FH_HeroSkinFire`: `EmberIntensity` 6, `EmberColor`, `EmberTiling` 36, `EmberSpeed` 0.25, `EmberThreshold` 0.3, `CharColor`, `CharAmount` 1, `EyeColor` (1,.66,.26), `EyeIntensity` 90.
- Longer or shorter flames: set `FH_SCALE` (length multiplier) or `FH_SEED`, then run `gen_firehair.py` again.

## How to build
Everything runs from `deliver/scripts/`. These scripts never touch `/var/www/html/Twilight`; they only read the hero GLB, the game's `Tools/materials_build.py` helpers and `Tools/cool_wait.sh`.
```
./build_all.sh             # bl_extract -> gen_textures -> gen_firehair -> ue_build (tex,mesh,mat) -> final_shots   (PERF=1 adds perf_matrix)
./iterate.sh <outdir> Menu,Close mesh,mat     # quick loop: regenerate mesh, rebuild assets + maps, shoot
./perf_matrix.sh 3         # interleaved `profilegpu` captures: fire vs current hero; parse with gpuprof.py / gpudiff.py
```
- `bl_extract.py` (Blender 4.2, headless) extracts the head polygons and the Body base colour from `art/models/hero/spartan_vahagn.glb`.
- `gen_textures.py` (numpy/PIL) writes the noise, the LUT and the body mask. The facial-hair UV island and the eye islands are found from the UV layout and the vertex positions. The scalp uses a hairline function.
- `gen_firehair.py` (Blender) builds the flame locks and writes a GLB in the hero's glTF frame.
- `ue_build.py` (UE editor python) imports the assets and builds the materials and instances. It reuses `G`/`setup_material`/`finish_material` from `Game/Tools/materials_build.py`.
- `ue_scenes.py` builds the look-dev maps. `fh_common.spawn_hero()` rebuilds the AVahagnCharacter rig: capsule centre → BodyPivot (pitch/roll) → mesh at (0,0,−92), yaw −90, scale 0.86, plus the game's `Glow` light.
- `shoot.sh` / `perf.sh` run `-game` and capture **only our own window** (`xdotool search --all --pid`). Another agent's "FireHairTest" window matched the old name-only search, which is fixed here.
- `run_ue.sh` runs `cool_wait.sh` before every launch, and only one UE process is started at a time.

### Putting it into the game (asset side)
Pick one:
- (a) Run the build against the game's asset project:
  `FH_STEPS=tex,mesh,mat ~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd /var/www/html/Twilight/Game/TwilightAssets.uproject -run=pythonscript -script=<deliver>/scripts/ue_build.py -unattended -nop4 -nosplash`
  The build needs `/Game/Twilight/Hero/Materials/MI_Vahagn_Body`, `/Game/Twilight/Hero/Textures/T_SkinDetail_N` and `/Game/StarterContent/Textures/T_Perlin_Noise_M`, which are all present in the game.
- (b) Copy `FireHair/Content/Twilight/FireHair/` into `Game/Content/Twilight/FireHair/`. The engine version and all referenced paths are identical.

`/Game/Twilight` is already in `DirectoriesToAlwaysCook`, so the new folder is cooked without further changes.

## C++ integration (AVahagnCharacter)
`VahagnCharacter.h` (private members):
```cpp
UPROPERTY() TObjectPtr<class UStaticMeshComponent> FireHair;
UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> FireHairMat;
UPROPERTY() TObjectPtr<UPointLightComponent> FireHairLight;
FVector FireWind = FVector::ZeroVector;
```
`VahagnCharacter.cpp` includes:
```cpp
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
```
In `BeginPlay()`, inside `if (bRealHero)`, **before** the per-slot MID loop:
```cpp
// fire skin on the body (charred, ember-glowing beard/scalp, eyes like suns); the MID loop below wraps it as before
if (UMaterialInterface* FireSkin = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Twilight/FireHair/Materials/MI_FH_VahagnBodyFire.MI_FH_VahagnBodyFire")))
    GetMesh()->SetMaterial(0, FireSkin);
```
**After** the MID loop:
```cpp
// helmet off: hide every render section that uses material slot 5
if (const FSkeletalMeshRenderData* RD = GetMesh()->GetSkeletalMeshRenderData())
    for (int32 Lod = 0; Lod < RD->LODRenderData.Num(); ++Lod)
        for (int32 S = 0; S < RD->LODRenderData[Lod].RenderSections.Num(); ++S)
            if (RD->LODRenderData[Lod].RenderSections[S].MaterialIndex == 5)
                GetMesh()->ShowMaterialSection(5, S, false, Lod);
// (fallback: GetMesh()->SetMaterial(5, LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Twilight/FireHair/Materials/M_FH_Invisible.M_FH_Invisible")));)

// hair of fire / beard of flame: the mesh is authored in the hero's component space -> undo the head bone's ref pose
if (UStaticMesh* HairMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Twilight/FireHair/Meshes/SM_VahagnFireHair.SM_VahagnFireHair")))
{
    FireHair = NewObject<UStaticMeshComponent>(this, TEXT("FireHair"));
    FireHair->SetStaticMesh(HairMesh);
    FireHair->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    FireHair->SetCastShadow(false);
    FireHair->SetupAttachment(GetMesh(), TEXT("head"));
    const FReferenceSkeleton& Ref = GetMesh()->GetSkeletalMeshAsset()->GetRefSkeleton();
    FTransform HeadCS = FTransform::Identity;
    for (int32 B = Ref.FindBoneIndex(TEXT("head")); B != INDEX_NONE; B = Ref.GetParentIndex(B))
        HeadCS = HeadCS * Ref.GetRefBonePose()[B];            // local(head) * local(neck) * ... * local(root)
    FireHair->SetRelativeTransform(HeadCS.Inverse());
    FireHair->RegisterComponent();
    FireHairMat = FireHair->CreateDynamicMaterialInstance(0);

    FireHairLight = NewObject<UPointLightComponent>(this, TEXT("FireHairLight"));
    FireHairLight->SetupAttachment(FireHair);
    FireHairLight->SetRelativeLocation(FVector(0.f, 24.f, 214.f));   // above the brow, inside the flames (hero component space)
    FireHairLight->SetIntensityUnits(ELightUnits::Unitless);
    FireHairLight->SetIntensity(700.f);
    FireHairLight->SetLightColor(FLinearColor(1.f, 0.45f, 0.15f));
    FireHairLight->SetAttenuationRadius(130.f);
    FireHairLight->SetSourceRadius(12.f);
    FireHairLight->SetCastShadows(false);
    FireHairLight->SetAffectTranslucentLighting(false);
    FireHairLight->RegisterComponent();
}
```
In `UpdateVisuals(float Dt)`, after the pivot block (`V` and `Speed` are already locals there):
```cpp
if (FireHairMat)
{
    // flames stream up and back with flight speed (look-dev value at 2700 uu/s = (-25,0,60) cm at the tips)
    const float K = FMath::Clamp(Speed / 2700.f, 0.f, 1.3f);
    const FVector WantWind = -V.GetSafeNormal() * 25.f * K + FVector(0.f, 0.f, 60.f * K);
    FireWind = FMath::VInterpTo(FireWind, WantWind, Dt, 3.f);
    FireHairMat->SetVectorParameterValue(TEXT("Wind"), FLinearColor(FireWind.X, FireWind.Y, FireWind.Z, 0.f));
}
if (FireHairLight)
{
    const float T = GetWorld()->GetTimeSeconds();
    FireHairLight->SetIntensity(700.f * (0.88f + 0.12f * FMath::Sin(T * 11.f) * FMath::Sin(T * 6.3f + 1.f)));
}
```
Notes:
- `BeginBirth()` calls `GetMesh()->SetVisibility(false, true)`, which propagates to the attached hair and light, so the reed-birth sequence keeps working unchanged.
- `HitFlash`/`FlashColor` keep working on the body MID. The `CrestGlow` on `BodyMat2` (slot 5) now drives a hidden section, which is harmless.
- The existing hand flames (`TwFx::AttachFlame`) stay as they are. The old `head` flame is already skipped for the real hero.

## Measured GPU cost (Iris Xe, Vulkan SM5, 1600×900, TAA, no Lumen/Nanite/VSM; `profilegpu`, 3 interleaved runs per variant)
Each `profilegpu` capture is one frame. The table gives the mean of 3 interleaved runs per variant, 2 to 3 runs for the 6 m pair.

| what (passes attributable to this change) | menu front 3 m | chase 6 m |
|---|---|---|
| flame-lock draw `Translucency(AfterDOF)` | **0.20 ms** (0.19–0.26) | **0.09 ms** |
| fire point light (`RenderLight PointLight2`, unshadowed, r = 130 cm) | **0.15–0.21 ms** | **~0.05 ms** |
| fire skin + hidden helmet (`MenuNoHair` vs `Orig`, whole frame) | ±0 (−0.46 ms, noise) | – |
| **incremental total in the game** | **≈ 0.35–0.45 ms** | **≈ 0.15 ms** |

Whole-frame check against a fair baseline, the current hero plus one small translucent stand-in for the game's
always-on hand flames (`OrigFx`): 21.89 vs 21.90 ms at 3 m, a difference inside the ±0.7 ms run-to-run noise.

**Caveat:** if *no* other translucent primitive is on screen, the first translucent mesh switches on UE's
translucency-lighting-volume work: `Clear/Inject/FilterTranslucentVolume`, **about +1.1 ms** on this GPU.
That happened in a scene with no other translucency (`MenuNoLight` vs `MenuNoHair`: +1.25 ms, or about +1.3–2.3 ms whole frame against the bare `Orig`).
The game always draws the hand flames and pelvis sparks (translucent particles), so it already pays this cost. All the game's fire
materials are unlit, so `r.TranslucencyLightingVolume 0` would save about 1 ms project-wide. That is a separate decision and is not made here.
Other agents' UE processes sometimes ran at the same time; the counts are in `logs/perf_matrix*.txt`. The raw profiles are in `logs/old/` and `logs/perf_*.log`.
Tools: `perf.sh` types `profilegpu` into our own `-game` window, `gpuprof.py` lists the key rows and `gpudiff.py` averages per-pass deltas.

## Licences
- Body: "Rigged for UE4 - Spartan - free" by **Andy Woodhead**, CC BY 4.0, sketchfab.com/3d-models/666f485199db43488b14035f2a3840bf. Modified: helmet hidden, body material re-tinted with a fire mask. This is the same asset and credit line the game already uses for Vahagn and Hayk.
- Flame-lock mesh, fire material, noise/LUT/mask textures, scripts: original procedural work made for Twilight. No third-party content.
- Look-dev only (not shipped by this change): Poly Haven "belfast_sunset_puresky" HDRI and "aerial_grass_rock" ground, both CC0. Epic StarterContent `T_Perlin_Noise_M` is used by the skin mottling, which the game's `M_HeroSkin` already uses (UE EULA).

## Honest weaknesses
- **Chase cam (6 m, behind/above, −62° dive):** the head points forward and down and the shoulders hide most of it. From behind, the hair reads as a blaze rising from the head, not as individual locks. The flight `Wind` (−25,0,60) is tuned for readability and bends the flames up more than physics would. In a side view the stretched tongues look streaky (`L_FH_ChaseSide`).
- **Cards:** with a still frame and a close camera, a few tongues show their crossed-card or "petal" structure. The overall colour is mostly yellow-orange with little deep red; real fire is often redder and smokier. There is no smoke and no heat haze, because both would add translucency or distortion cost.
- **Rigid:** the locks follow the head bone only. There is no jaw bone and no secondary motion beyond the WPO sway; the flames do not react to head turns or to casting.
- **Scalp/beard skin:** the charcoal-and-ember mask is driven by the 1024² Spartan texture, where the head is tiny in UV. Close up, the glowing scalp between flames looks like a blotchy burnt crust rather than a clean hairline.
- **Eyes:** the iris is emissive, so the eyes read as glowing slits or white-gold points with bloom, not as detailed "suns" with a corona. There is no lens flare.
- **Body skin:** the face and body are the existing realistic Spartan skin, but the game's `Glow` light (9000, kept for parity) makes the body look somewhat plasticky and over-lit in the 3 m menu shot. The ground plane stands in for Lake Sevan in look-dev.
- **Perf:** the translucent hair triggers the translucency lighting volume when nothing else translucent is on screen (see above). In the game this is already paid.
- The C++ snippet is written against the current `VahagnCharacter.cpp/.h` but has **not been compiled in the game**; that tree was not modified, as required.
