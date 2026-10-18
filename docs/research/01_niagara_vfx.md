# 01 — VFX plan with no editor clicks (UE 5.8.2, Linux, Iris Xe)

Engine root below is `E=/home/samo/UnrealEngine-5.8`. Every claim was checked against the engine files on disk on 2026-10-18. Where I could only infer something from `strings` on a binary `.uasset`, or where it needs a live editor run (which I was not allowed to do), it is marked **UNVERIFIED**.

---

## TL;DR — recommended stack (most reliable first)

| Layer | What | Why |
|---|---|---|
| **A. Cascade StarterContent** (`P_Fire`, `P_Explosion`, `P_Sparks`, `P_Smoke`, `P_Ambient_Dust`) | Already authored and already look like fire. Spawned from C++ with `UGameplayStatics::SpawnEmitterAttached/AtLocation`. | They need no compile step and no authoring. Cascade still runs at runtime in 5.8 (see §3). You only copy files into `Content/`. |
| **B. Niagara systems from the DMXFixtures plugin** (`/DMXFixtures/Fireworks/Systems/VFX_Shell_Peony`, `VFX_Trail_Comet`, `/DMXFixtures/Pyro/Systems/VFX_ColdSparks_*`, `/DMXFixtures/WaterFountains/Systems/VFX_WaterJet`) | High-quality, Epic-authored Niagara systems that **expose User parameters** (colour, scale, velocity). | This is the only Niagara content on disk that has User params you can retint from C++. You enable one plugin in `.uproject`. |
| **C. C++-driven lights + emissive meshes** (`UPointLightComponent`, `/Engine/BasicShapes/Sphere` + a Python-generated unlit additive material) | The fireball core, glow, shockwave ring and breath cone. | Works with no particle system at all. This is the guaranteed fallback. |
| D. Niagara engine templates (`/Niagara/DefaultAssets/Templates/...`) | Last resort only. | They have **no User params** and use grey/white `DefaultSpriteMaterial`, so they look like debug placeholders unless re-authored (see §2). |

> **CRITIC FIX (layer B):** `DMXFixtures` is **not** enabled in the current `/var/www/html/Twilight/Game/Twilight.uproject` (checked 2026-10-18). Its dependency chain is larger than stated in §2: `DMXFixtures` → `DMXEngine` (`.../VirtualProduction/DMX/DMXEngine/DMXEngine.uplugin`), which in turn needs **`DatasmithContent`, `DMXGDTF`, `Takes`** (Takes → `AudioCapture`, `LevelSequenceEditor`, `NamingTokens`), plus `DMXProtocol`, `DMXModularFeatures` and `ProceduralMeshComponent`. The Linux editor `.so` files for all of these exist, so `-game` from the editor binary works. A packaged build must compile all of these runtime modules as well, which adds packaging time and risk. Every `NS_*` call site **must** null-check the loaded system and the spawned component, and fall back to Cascade or meshes. If you are short on time, skip layer B and use A + C.

For lighting the scene, do not rely on particle lights. Engine scalability sets `r.ParticleLightQuality=0` (no particle lights) at EffectsQuality 0/1 (`$E/Engine/Config/BaseScalability.ini:811,840`). Put a real `UPointLightComponent` on the fireball, the hero and the explosions.

---

## 1) Niagara templates on disk

Folder: `$E/Engine/Plugins/FX/Niagara/Content/DefaultAssets/Templates` (47 assets). The object path is `/Niagara/DefaultAssets/Templates/<Sub>/<Name>.<Name>`.

### Systems (`UNiagaraSystem`)
I extracted the renderer, sim target and module data with `strings` on each `.uasset`.

| Object path | Sim | Renderers | Notes |
|---|---|---|---|
| `/Niagara/DefaultAssets/Templates/Systems/SimpleExplosion.SimpleExplosion` | CPU | Sprite + Mesh (`S_Arrow`/`M_Gnomon_Alpha`) | Burst + ShapeLocation + gravity/drag + ScaleColor. Uses `DefaultSpriteMaterial` |
| `/Niagara/DefaultAssets/Templates/Systems/RadialBurst.RadialBurst` | CPU | Sprite + Ribbon (`DefaultRIbbonMaterial`) | Location events → ribbon trails |
| `/Niagara/DefaultAssets/Templates/Systems/DirectionalBurst.DirectionalBurst` | CPU | Sprite + Ribbon | Cone velocity + events |
| `/Niagara/DefaultAssets/Templates/Systems/AttributeReaderTrails.AttributeReaderTrails` | GPU | Sprite | Collision |
| `/Niagara/DefaultAssets/Templates/Systems/DirectionalBurstLightweight.DirectionalBurstLightweight` | Stateless ("Lightweight") | Sprite | |
| `/Niagara/DefaultAssets/Templates/Systems/FountainLightweight.FountainLightweight` | Stateless | Sprite | |
| `/Niagara/DefaultAssets/Templates/Systems/MinimalLightweight.MinimalLightweight` | Stateless | Sprite | |

### Emitters (`UNiagaraEmitter`; these cannot be spawned directly, they must sit inside a system)
`/Niagara/DefaultAssets/Templates/Emitters/` holds: `BlowingParticles` (GPU), `ConfettiBurst` (GPU), `DirectionalBurst`, `DynamicBeam` (ribbon), `Fountain`, `HangingParticulates` (wind + drag, good for embers), `LocationBasedRibbon` (ribbon), `Minimal`, `OmnidirectionalBurst`, `RecycleParticlesInView` (GPU, camera recycler, good for ambient), `SimpleSpriteBurst`, `SingleLoopingParticle`, `StaticBeam`, `UpwardMeshBurst`.

### Others
`/Niagara/DefaultAssets/Templates/BehaviorExamples/*` (25 teaching systems, e.g. `RibbonShapes`, `SpawnGroupsFromMultipleBones`, `SubUVAnimation`) and `/Niagara/DefaultAssets/Templates/CascadeConversion/CompletelyEmpty`.

Default materials: `/Niagara/DefaultAssets/DefaultSpriteMaterial`, `DefaultRIbbonMaterial` (sic), `DefaultTextureSpriteMaterial`, `M_DepthFade_SpriteSimple`.

**User params in the templates: none.** `strings` finds no `User.*` names in any of the 7 template systems. You therefore **cannot recolour them at runtime**: `SetVariableLinearColor` only writes User/override parameters.

---

## 2) Getting usable Niagara systems headless

### (a) Duplicating a template with Python
APIs (both Python-visible):
- `unreal.EditorAssetLibrary.duplicate_asset(source_path, dest_path)` → `$E/Engine/Plugins/Editor/EditorScriptingUtilities/Source/EditorScriptingUtilities/Public/EditorAssetLibrary.h:175`. Also `duplicate_directory` (:185) and `save_asset(path, only_if_is_dirty=True)` (:281).
- `unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, package_path, original)` → `$E/Engine/Source/Developer/AssetTools/Public/IAssetTools.h:450-451` (`UFUNCTION(BlueprintCallable)`).

Compile behaviour: `UNiagaraSystem::PreSave` calls `WaitForCompilationComplete()` before it serialises (`$E/Engine/Plugins/FX/Niagara/Source/Niagara/Private/NiagaraSystem.cpp:357-365`). So `save_asset` blocks until the VM scripts are compiled, and that also happens in `-run=pythonscript` (the cooker compiles Niagara the same headless way). GPU sims also need compute shaders, which the shader compile workers build. **UNVERIFIED:** I did not run it, because launching the editor was out of scope for me.

What you **can** edit from Python after duplicating:
- `UNiagaraSystem::EmitterHandles` is a plain `UPROPERTY()` with no Edit or BlueprintVisible flag (`$E/Engine/Plugins/FX/Niagara/Source/Niagara/Classes/NiagaraSystem.h:975-976`). That makes it **invisible to Python**: Python exports only BlueprintVisible properties, or `CPF_Edit` ones in the editor (`$E/Engine/Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/PyGenUtil.cpp:1609-1613, 1811-1815`).
- The renderer objects themselves **are** reachable with `unreal.ObjectIterator(unreal.NiagaraSpriteRendererProperties)` (`PyCore.cpp:871`). Their `Material` is `UPROPERTY(EditAnywhere)` (`.../Niagara/Public/NiagaraSpriteRendererProperties.h:159-160`, ribbon `.../NiagaraRibbonRendererProperties.h:241-242`), so `set_editor_property('material', mat)` works. That lets you swap the grey default material for a fire material headlessly (script in §4-F).
- Module inputs (colour, spawn rate, velocity), adding User params and adding a Light renderer are **not** script-exposed. 5.8 does ship a C++ API for that, `UNiagaraExternalEditUtilities` (`$E/Engine/Plugins/FX/Niagara/Source/NiagaraEditor/Public/NiagaraExternalSystemEditorUtilities.h:1237`), with `CreateNiagaraSystem` (:1252), `AddUserVariable` (:1383), `SetRendererData` (:1401) and `SetStackInputData` (:1402). Its functions are `UE_API static` with **no `UFUNCTION`** (0 UFUNCTIONs in the header), so the only way to use it is from an editor-only C++ module or commandlet in the project. That is possible but adds build risk. I do **not** recommend it for tonight.

### (b) Referencing `/Niagara/...` (or `/DMXFixtures/...`) directly at runtime
- Template assets are ordinary `UNiagaraSystem`s. The old template flags are `_DEPRECATED` (`NiagaraSystem.h:496-502`), so nothing stops them from running or cooking.
- Niagara is `"EnabledByDefault": true` (`$E/Engine/Plugins/FX/Niagara/Niagara.uplugin:13`). Its content mounts as `/Niagara/`.
- **Uncooked** (`UnrealEditor Twilight.uproject -game`, or PIE): any `/Niagara/...` or `/DMXFixtures/...` path loads as-is.
- **Cooked/packaged:** the cooker only cooks what is referenced. Hard-reference the assets from a cooked asset or map, or force them in with `DefaultGame.ini`. The property is at `$E/Engine/Source/Developer/DeveloperToolSettings/Classes/Settings/ProjectPackagingSettings.h:568`:
  ```ini
  [/Script/UnrealEd.ProjectPackagingSettings]
  +DirectoriesToAlwaysCook=(Path="/Game/StarterContent/Particles")
  +DirectoriesToAlwaysCook=(Path="/DMXFixtures/Fireworks")
  +DirectoriesToAlwaysCook=(Path="/DMXFixtures/Pyro")
  +DirectoriesToAlwaysCook=(Path="/DMXFixtures/WaterFountains")
  +DirectoriesToAlwaysCook=(Path="/DMXFixtures/Shared/VFX")
  ```
  `ConstructorHelpers::FObjectFinder` in a C++ constructor creates a hard reference from the CDO. **UNVERIFIED** whether the 5.8 cooker follows CDO references by itself, so keep the ini lines as a safety net.
- Materials used by Niagara in a **cooked** build must have `bUsedWithNiagaraSprites`/`bUsedWithNiagaraRibbons` set (`$E/Engine/Source/Runtime/Engine/Public/Materials/Material.h:751-759`). Otherwise they render as the default material. The editor sets these flags automatically only while running uncooked (`bAutomaticallySetUsageInEditor`, :934). StarterContent particle materials only have `bUsedWithParticleSprites` (Cascade), so do not plug them into Niagara renderers for a cooked build without setting the flag in Python.

### (c) Runtime parameter overrides from C++
`$E/Engine/Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h`:
- `SetVariableLinearColor(FName, const FLinearColor&)` :470 · `SetVariableVec3` :506 · `SetVariableFloat` :533 · `SetVariableInt` :542 · `SetVariableBool` :551 · `SetVariableMaterial(FName, UMaterialInterface*)` :568 · `SetVariableStaticMesh` :571 · `SetVariableTexture` :574
- `SetEmitterEnable(FName, bool)` :78 · `SetAsset` :295 · `SetAutoDestroy` :403 · `ReinitializeSystem` :650
- Names work with or without the `User.` prefix. The store redirects the bare name (`.../Niagara/Public/NiagaraUserRedirectionParameterStore.h:10,29`). The **type must match** the declared User param type.
- Spawning (`.../Niagara/Public/NiagaraFunctionLibrary.h`): `SpawnSystemAtLocation(WorldCtx, Sys, Loc, Rot, Scale, bAutoDestroy, bAutoActivate, ENCPoolMethod, bPreCullCheck)` :93 · `SpawnSystemAttached(Sys, AttachTo, Socket, Loc, Rot, EAttachLocation, bAutoDestroy, bAutoActivate, Pool, bPreCull)` :96 (plus a Scale overload at :98). Pool enum `ENCPoolMethod::{None, AutoRelease, ManualRelease}` (`.../NiagaraComponentPoolMethodEnum.h:13-27`).
- Build.cs: add `"Niagara"` to `PublicDependencyModuleNames`. Includes: `NiagaraComponent.h`, `NiagaraFunctionLibrary.h`, `NiagaraSystem.h`.

**Which on-disk systems expose which User params** (names from `strings`; the **types are UNVERIFIED**, so log them at startup with the helper below):

| System (object path) | User params | Sim |
|---|---|---|
| `/DMXFixtures/Fireworks/Systems/VFX_Shell_Peony.VFX_Shell_Peony` | `PrimColor`, `SecColor`, `SparkColor`, `ScaleMod`, `SparkStopTime` | GPU |
| `/DMXFixtures/Fireworks/Systems/VFX_Shell_Chrysanthemum` / `_Crossette` / `_Ring` / `_Strobe` | same set (+`Emitter` on Ring) | GPU |
| `/DMXFixtures/Fireworks/Systems/VFX_Shell_Willow` | `PrimColor`, `SecColor`, `SparkColor`, `ScaleMod` | CPU |
| `/DMXFixtures/Fireworks/Systems/VFX_Trail_Comet.VFX_Trail_Comet` | `GlowColor`, `GlowFlicker`, `GlowSize`, `PrimColor`, `SecColor`, `SparkColor`, `ScaleMod` | GPU |
| `/DMXFixtures/Fireworks/Systems/VFX_Trail_Pearl` | `PrimColor`, `SecColor` | GPU |
| `/DMXFixtures/Pyro/Systems/VFX_ColdSparks_Stream` / `_Burst` | `DensityScale`, `VelocityScale` | GPU |
| `/DMXFixtures/WaterFountains/Systems/VFX_WaterJet.VFX_WaterJet` | `MuzzleVelocity` | — |
| All `/Niagara/DefaultAssets/Templates/*` | **none** | — |

These DMX systems depend only on Niagara, curve DIs, the NPC `/DMXFixtures/Fireworks/FWGlobals` (`NPC.FWGlobals.Gravity`, `AirResistance`) and the `/DMXFixtures/Shared/VFX/Materials/*` glow materials. Those materials already carry `bUsedWithNiagaraSprites/Ribbons`. The systems do **not** reference DMX data interfaces. Brightness passes through the MPC `/DMXFixtures/Shared/VFX/Materials/Master/MPC_VFX_Globals` scalar `EVAdjust`, which you can set from C++ with `UKismetMaterialLibrary::SetScalarParameterValue(World, MPC, "EVAdjust", v)` (`$E/Engine/Source/Runtime/Engine/Classes/Kismet/KismetMaterialLibrary.h:30`).

Enable the plugin in `Twilight.uproject`. It is not on by default, and it pulls in DMXEngine, DMXProtocol, DMXModularFeatures and ProceduralMeshComponent, whose Linux editor binaries already exist under `$E/Engine/Plugins/VirtualProduction/DMX/*/Binaries/Linux`:
```json
"Plugins": [ { "Name": "DMXFixtures", "Enabled": true } ]
```

Type-safe introspection helper (run once at BeginPlay and read the log):
```cpp
#include "NiagaraSystem.h"
static void LogUserParams(UNiagaraSystem* Sys)
{
    if (!Sys) return;
    TArray<FNiagaraVariable> Vars;
    Sys->GetExposedParameters().GetUserParameters(Vars);           // NiagaraSystem.h:368, NiagaraUserRedirectionParameterStore.h:32
    for (const FNiagaraVariable& V : Vars)
        UE_LOG(LogTemp, Log, TEXT("[FX] %s  %s : %s"), *Sys->GetName(), *V.GetName().ToString(), *V.GetType().GetName());
}
```

---

## 3) Cascade (StarterContent) in 5.8

- The Cascade **runtime** is in the Engine module and still active: `class UParticleSystemComponent : public UFXSystemComponent` (`$E/Engine/Source/Runtime/Engine/Classes/Particles/ParticleSystemComponent.h:491`). The class has no deprecation macro. The only deprecations in that header concern auto-attach (:810-845).
- The Cascade **plugin** is editor-only and says so: *"Cascade assets can still run in a game with this plugin disabled."* (`$E/Engine/Plugins/FX/Cascade/Cascade.uplugin`, module Type `Editor`).
- Render cvars default to on: `fx.Cascade.SpriteRenderingEnabled/MeshRenderingEnabled/BeamRenderingEnabled/TrailRenderingEnabled = true` (`$E/Engine/Source/Runtime/Engine/Private/Particles/ParticleSystemRender.cpp:50-80`). `fx.Cascade.SetTemplateDenyList` is empty by default (`ParticleSystemComponent.cpp:157`).
- Spawn API (`$E/Engine/Source/Runtime/Engine/Classes/Kismet/GameplayStatics.h`): `SpawnEmitterAtLocation(WorldCtx, Template, Loc, Rot, Scale, bAutoDestroy, EPSCPoolMethod, bAutoActivate)` :534 · `SpawnEmitterAttached(Template, AttachTo, Socket, Loc, Rot, Scale, EAttachLocation, bAutoDestroy, Pool, bAutoActivate)` :588.
- Per-component control (`ParticleSystemComponent.h`): `SetEmitterEnable(FName, bool)` :1137 · `SetFloatParameter/SetVectorParameter/SetColorParameter` :1155/1161/1167 (they only affect emitters that use *Particle Parameter* distributions; the StarterContent systems have **none**, so recolouring is not possible) · `SetMaterial(int32, UMaterialInterface*)` :1449 · `SetTemplate` :1261 · `BeginTrails/EndTrails` :1288/1294 (AnimTrail emitters only, which StarterContent lacks).

What is inside each system (from `strings`):

| Asset | Emitters (names in the name table) | Materials | Notes |
|---|---|---|---|
| `/Game/StarterContent/Particles/P_Fire` | Flames, Smoke, Embers, Sparks, Distortion (**UNVERIFIED** as exact emitter names) | M_Fire_SubUV, M_smoke_subUV, M_Radial_Gradient, **M_Heat_Distortion** (refraction) | GPU sprites (`ParticleModuleTypeDataGpu`), depth-buffer collision, `ParticleModuleLight`, Orbit |
| `/Game/StarterContent/Particles/P_Explosion` | FireBall, Shockwave, Smoke, Sparks (+ light) | M_explosion_subUV, M_Burst, m_flare_01, M_radial_ramp, M_smoke_subUV | GPU sparks, light module |
| `/Game/StarterContent/Particles/P_Sparks` | Sparks, "Spark burst", Smoke | M_Spark, M_Radial_Gradient, M_smoke_subUV | GPU, VelocityInheritParent, light |
| `/Game/StarterContent/Particles/P_Smoke` | Smoke | M_smoke_subUV | CPU |
| `/Game/StarterContent/Particles/P_Ambient_Dust` | — | M_Dust_Particle | GPU, nice floating motes |
| `/Game/StarterContent/Particles/P_Steam_Lit` | — | M_smoke_subUV | lit smoke, useful as sea mist |

**Install, headless and with no editor.** These are plain file copies with the paths unchanged, so the `/Game/StarterContent/...` references resolve:
```bash
SC=/home/samo/UnrealEngine-5.8/Samples/StarterContent/Content/StarterContent
DST=/var/www/html/Twilight/Game/Content/StarterContent
mkdir -p $DST/Textures
cp -r $SC/Particles $DST/
for t in T_Burst_M T_Dust_Particle_D T_Explosion_SubUV T_Fire_SubUV T_Fire_Tiled_D T_Water_N T_Smoke_SubUV T_Smoke_Tiled_D T_Spark_Core; do cp $SC/Textures/$t.uasset $DST/Textures/; done
# (the whole StarterContent is 613 MB, so copy only what is needed; add Audio/ separately if wanted)
```
The texture dependency list comes from `strings` on each `Particles/Materials/*.uasset`. `M_Radial_Gradient`/`M_radial_ramp` also use `/Engine/Functions/Engine_MaterialFunctions01/Gradient/RadialGradient`, which ships with the engine.

---

## 4) Effect recipes (asset + C++ + overrides)

Common header (in e.g. `VahagnFX.h`, a `UBlueprintFunctionLibrary` or a plain namespace):
```cpp
#include "Kismet/GameplayStatics.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Components/PointLightComponent.h"

namespace VFX
{
    template<typename T> T* Load(const TCHAR* Path) { return LoadObject<T>(nullptr, Path); } // runtime load; or ConstructorHelpers in ctor
    // Cascade
    static const TCHAR* P_Fire      = TEXT("/Game/StarterContent/Particles/P_Fire.P_Fire");
    static const TCHAR* P_Explosion = TEXT("/Game/StarterContent/Particles/P_Explosion.P_Explosion");
    static const TCHAR* P_Sparks    = TEXT("/Game/StarterContent/Particles/P_Sparks.P_Sparks");
    static const TCHAR* P_Smoke     = TEXT("/Game/StarterContent/Particles/P_Smoke.P_Smoke");
    static const TCHAR* P_Dust      = TEXT("/Game/StarterContent/Particles/P_Ambient_Dust.P_Ambient_Dust");
    static const TCHAR* P_Steam     = TEXT("/Game/StarterContent/Particles/P_Steam_Lit.P_Steam_Lit");
    // Niagara (DMXFixtures plugin)
    static const TCHAR* NS_Peony    = TEXT("/DMXFixtures/Fireworks/Systems/VFX_Shell_Peony.VFX_Shell_Peony");
    static const TCHAR* NS_Comet    = TEXT("/DMXFixtures/Fireworks/Systems/VFX_Trail_Comet.VFX_Trail_Comet");
    static const TCHAR* NS_Sparks   = TEXT("/DMXFixtures/Pyro/Systems/VFX_ColdSparks_Stream.VFX_ColdSparks_Stream");
    static const TCHAR* NS_SparkBurst=TEXT("/DMXFixtures/Pyro/Systems/VFX_ColdSparks_Burst.VFX_ColdSparks_Burst");
    static const TCHAR* NS_WaterJet = TEXT("/DMXFixtures/WaterFountains/Systems/VFX_WaterJet.VFX_WaterJet");
    static const FLinearColor FireOrange(4.0f, 1.2f, 0.15f);   // HDR >1 → bloom
    static const FLinearColor FireGold  (6.0f, 3.0f, 0.6f);
    static const FLinearColor VishapGreen(0.4f, 3.0f, 0.8f);   // poison accent for enemies
}
```
Load once, keeping a `UPROPERTY() TObjectPtr<UParticleSystem>` in the GameMode or GameInstance so GC does not unload it, and **warm everything up at match start**: spawn each effect once off-screen, 2 km below the sea. That prevents the first-use hitch from PSO/shader caching during the live demo.

### A. Hero fire aura on the skeletal mesh
Mannequin bones (from `SK_Mannequin.uasset` strings): `hand_r`, `hand_l`, `spine_03`, `spine_05`, `head`, `pelvis`, `foot_l/r`, `lowerarm_r`, … plus sockets `foot_l_Socket`/`foot_r_Socket`.
```cpp
void AVahagnCharacter::StartFireAura()
{
    USkeletalMeshComponent* M = GetMesh();
    UParticleSystem* Fire = VFX::Load<UParticleSystem>(VFX::P_Fire);
    auto Attach = [&](FName Bone, float S) {
        UParticleSystemComponent* C = UGameplayStatics::SpawnEmitterAttached(Fire, M, Bone, FVector::ZeroVector,
            FRotator::ZeroRotator, FVector(S), EAttachLocation::SnapToTarget, /*bAutoDestroy*/false);
        if (C) C->SetEmitterEnable(TEXT("Distortion"), false); // kill refraction on iGPU (emitter name UNVERIFIED; harmless if wrong)
        return C;
    };
    AuraHandR  = Attach(TEXT("hand_r"), 0.25f);   // sword/fire hand
    AuraHandL  = Attach(TEXT("hand_l"), 0.18f);
    AuraBack   = Attach(TEXT("spine_03"), 0.35f); // "burning mane"
    // light that actually lights the character + nearby water
    AuraLight = NewObject<UPointLightComponent>(this);
    AuraLight->SetupAttachment(M, TEXT("spine_03"));
    AuraLight->SetIntensityUnits(ELightUnits::Candelas);
    AuraLight->SetIntensity(80.f); AuraLight->SetAttenuationRadius(600.f);
    AuraLight->SetLightColor(FLinearColor(1.f, 0.45f, 0.12f)); AuraLight->SetCastShadows(false);
    AuraLight->RegisterComponent();
}
// flicker in Tick: AuraLight->SetIntensity(70 + 25*FMath::PerlinNoise1D(Time*7));
```
Because Cascade emitters simulate in world space by default, flames left by fast flight stream behind the hero, which reads well. If it smears too much, lower the scale or switch to `P_Sparks` on the back. **UNVERIFIED** for this exact asset; check the look at speed. Add `/Game/StarterContent/Particles/P_Ambient_Dust` attached to the root at scale 0.5 for glittering motes. Optional premium: attach `NS_Sparks` (ColdSparks_Stream) to `hand_r` with `SetVariableFloat("DensityScale", 0.3f)`.

### B. Fireball projectile (core + trail + light)
```cpp
AFireball::AFireball()
{
    Core = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Core"));   // /Engine/BasicShapes/Sphere + MI_FireGlow (see §F); scale 0.4
    Core->SetCollisionEnabled(ECollisionEnabled::NoCollision); Core->SetCastShadow(false);
    Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
    Light->SetupAttachment(RootComponent); Light->SetIntensity(5000.f); Light->SetAttenuationRadius(800.f);
    Light->SetLightColor(FLinearColor(1.f, .5f, .15f)); Light->SetCastShadows(false);
}
void AFireball::BeginPlay()
{
    Super::BeginPlay();
    // Option 1 (Niagara, best looking): comet trail
    if (UNiagaraSystem* Comet = VFX::Load<UNiagaraSystem>(VFX::NS_Comet))
    {
        Trail = UNiagaraFunctionLibrary::SpawnSystemAttached(Comet, RootComponent, NAME_None, FVector::ZeroVector,
            FRotator::ZeroRotator, EAttachLocation::SnapToTarget, /*bAutoDestroy*/false, true, ENCPoolMethod::None);
        if (!Trail) { return; }   // CRITIC FIX: SpawnSystemAttached can return nullptr (pre-cull / invalid system)
        Trail->SetVariableLinearColor(TEXT("PrimColor"),  VFX::FireOrange);   // types UNVERIFIED – check LogUserParams
        Trail->SetVariableLinearColor(TEXT("SecColor"),   VFX::FireGold);
        Trail->SetVariableLinearColor(TEXT("SparkColor"), VFX::FireGold);
        Trail->SetVariableLinearColor(TEXT("GlowColor"),  VFX::FireOrange);
        Trail->SetVariableFloat(TEXT("ScaleMod"), 0.15f);                     // fireworks are authored huge; tune 0.05–0.3
    }
    else // Option 2 (Cascade fallback): world-space flames left behind = trail
    {
        UGameplayStatics::SpawnEmitterAttached(VFX::Load<UParticleSystem>(VFX::P_Fire), RootComponent, NAME_None,
            FVector::ZeroVector, FRotator::ZeroRotator, FVector(0.3f), EAttachLocation::SnapToTarget, false);
    }
}
// On impact: Trail->Deactivate(); SetLifeSpan(1.5f) so the trail fades instead of popping.
```

### C. Impact explosion
```cpp
void FX_Impact(UObject* W, const FVector& P, float Scale = 1.f)
{
    UGameplayStatics::SpawnEmitterAtLocation(W, VFX::Load<UParticleSystem>(VFX::P_Explosion), P,
        FRotator::ZeroRotator, FVector(Scale), true, EPSCPoolMethod::AutoRelease);
    // flash light (particle lights are off at low Effects quality)
    if (AActor* A = W->GetWorld()->SpawnActor<AActor>(AActor::StaticClass(), FTransform(P)))
    {
        UPointLightComponent* L = NewObject<UPointLightComponent>(A); A->SetRootComponent(L); L->RegisterComponent();
        L->SetIntensity(50000.f * Scale); L->SetAttenuationRadius(1500.f * Scale); L->SetLightColor(FLinearColor(1,.55f,.2f));
        L->SetCastShadows(false); A->SetLifeSpan(0.25f);   // or fade in Tick
    }
}
```
EPSCPoolMethod lives in `$E/Engine/Source/Runtime/Engine/Classes/Particles/WorldPSCPool.h:15`.

### D. Vishap death burst (big, readable payoff)
```cpp
void FX_VishapDeath(UObject* W, const FVector& P, float Size /*1=normal, 3=Great Vishap*/)
{
    FX_Impact(W, P, 1.5f * Size);
    if (UNiagaraSystem* Peony = VFX::Load<UNiagaraSystem>(VFX::NS_Peony))
    {
        UNiagaraComponent* N = UNiagaraFunctionLibrary::SpawnSystemAtLocation(W, Peony, P, FRotator::ZeroRotator,
            FVector(1.f), true, true, ENCPoolMethod::AutoRelease);
        if (N) {   // CRITIC FIX: SpawnSystemAtLocation returns nullptr when pre-culled (bPreCullCheck=true default, NiagaraFunctionLibrary.h:93)
        N->SetVariableLinearColor(TEXT("PrimColor"),  VFX::FireOrange);
        N->SetVariableLinearColor(TEXT("SecColor"),   VFX::VishapGreen);   // dragon "blood" accent
        N->SetVariableLinearColor(TEXT("SparkColor"), VFX::FireGold);
        N->SetVariableFloat(TEXT("ScaleMod"), 0.2f * Size);
        }
    }
    UGameplayStatics::SpawnEmitterAtLocation(W, VFX::Load<UParticleSystem>(VFX::P_Smoke), P, FRotator::ZeroRotator, FVector(2.f * Size));
    // + body pieces: hide the serpent mesh, spawn 6–10 sphere/cylinder chunks with emissive MI + physics impulse, LifeSpan 3s
}
```
Boss: chain 5 of these along the spline of the serpent body at 0.15 s intervals (`FTimerHandle`). Add a camera shake and a 0.1 s time-dilation punch (`UGameplayStatics::SetGlobalTimeDilation`).

### E. Vishap fire breath
Use a layered solution. Each layer works on its own, so if one fails the breath still looks acceptable.
1. **Cone mesh**: `/Engine/BasicShapes/Cone`, rotated to point forward from the jaw socket. Use an additive unlit material with panning noise (see §F, `M_FireBreath`), scale X/Y 0.6, Z 6, and animate Z-scale from 0→1 over 0.25 s in Tick. This is the reliable "beam" read.
2. **Fire puffs**: every 0.06 s spawn `P_Fire` at scale 0.4 at the mouth, as a tiny actor that moves forward at 2500 u/s for 0.5 s with gravity off, then auto-destroys. Fifteen live puffs is cheap, and the motion gives a believable flamethrower.
3. **Sparks**: `NS_Sparks` (ColdSparks_Stream) attached to the jaw with relative rotation pointing forward, `SetVariableFloat("VelocityScale", 2.f)`, `SetVariableFloat("DensityScale", 0.5f)`. **UNVERIFIED** whether its velocity is local-space (rotatable). If it is not, drop this layer.
4. A point light on the mouth, orange, ~~3000 cd~~ **150–300 cd** (CRITIC FIX), radius 1200, pulsing. Unit math from `LocalLightComponent.cpp:186-221`: 1 cd = 10000 internal, 1 unitless = 16 internal. So the engine default point light (5000 unitless, `LocalLightComponent.cpp:13-14`) is only **8 cd**. 3000 cd is 375× that, and with AutoExposure off in this project it would blow the whole frame to white. Note also that a `UPointLightComponent` created in C++ defaults to **Unitless** units (`LocalLightComponent.cpp:14`), so `SetIntensity(5000)` in §B means 8 cd and `SetIntensity(50000*Scale)` in §C means 80 cd·Scale. Those are sane values. Only call `SetIntensityUnits(ELightUnits::Candelas)` (`LocalLightComponent.h:57`) when you really mean candelas.
Damage uses a capsule sweep along the cone axis and does not depend on the particles.

### F. Ambient embers / sparks in the air
- `P_Ambient_Dust` (GPU) placed in a grid of 4–6 static emitters around the play volume, or attached to the camera (`SpawnEmitterAttached(..., Camera, NAME_None, FVector(800,0,0))`) so motes always surround the player. It is world space, so motes stream past during flight.
- `P_Sparks` at scale 2 on lava/fire braziers on the mountains.
- Optional Niagara: `/Niagara/DefaultAssets/Templates/Emitters/RecycleParticlesInView` is camera-recycled. It is designed for exactly this, but it is an *emitter*, needs a system, and has a grey material, so it needs §2(a) authoring and is **not** recommended tonight.

### G. Sea spray
- `/DMXFixtures/WaterFountains/Systems/VFX_WaterJet` (User `MuzzleVelocity`). Spawn it at the sea surface under the hero when altitude < 600 u, rotated straight up, `SetVariableFloat("MuzzleVelocity", 800.f)`, and also on vishap emerge/dive points. Its material is `MI_WaterSplashes_4x4` with `M_MistRibbon`.
- Fallback: `P_Steam_Lit` at scale 3 (lit, so it picks up the sunset colour) plus `P_Smoke` tinted by the scene.

### F (materials). Fallback materials made in Python, headless (no Niagara needed)
APIs: `MaterialEditingLibrary.create_material_expression` (`$E/Engine/Source/Editor/MaterialEditor/Public/MaterialEditingLibrary.h:168`), `connect_material_property` (:232), `connect_material_expressions` (:242), `recompile_material` (:267), factory `MaterialFactoryNew` (`$E/Engine/Source/Editor/UnrealEd/Classes/Factories/MaterialFactoryNew.h:15`), `AssetTools.create_asset` (`IAssetTools.h:349`), enums `BLEND_Additive` / `MSM_Unlit` (`$E/Engine/Source/Runtime/Engine/Classes/Engine/EngineTypes.h:250,709`), `MP_EmissiveColor` (`$E/Engine/Source/Runtime/Engine/Public/SceneTypes.h:149`).
```python
# make_fx_materials.py  — run: UnrealEditor-Cmd Twilight.uproject -run=pythonscript -script=/abs/make_fx_materials.py
import unreal
at  = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
PATH = "/Game/FX/Materials"

def make_glow(name, color=(4.0, 1.2, 0.15), fresnel=True, panning_noise=False):
    full = f"{PATH}/{name}"
    if eal.does_asset_exist(full):
        eal.delete_asset(full)
    m = at.create_asset(name, PATH, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    # CRITIC FIX: the bUsedWith* fields are UE_DEPRECATED(5.8) (Material.h:701-911). set_editor_property still
    # works on them, because they remain UPROPERTY(EditAnywhere), but it skips MarkUsageFlagDirty (Material.cpp:1748-1751).
    # Use the supported API instead (MaterialEditingLibrary.h:204-205):
    for u in ("MATUSAGE_NIAGARA_SPRITES", "MATUSAGE_NIAGARA_RIBBONS", "MATUSAGE_NIAGARA_MESH_PARTICLES",
              "MATUSAGE_PARTICLE_SPRITES", "MATUSAGE_MESH_PARTICLES", "MATUSAGE_INSTANCED_STATIC_MESHES"):
        mel.set_base_material_usage(m, getattr(unreal.MaterialUsage, u), True)
    col = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -800, 0)
    col.set_editor_property("parameter_name", "Color")
    col.set_editor_property("default_value", unreal.LinearColor(*color, 1.0))
    inten = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -800, 200)
    inten.set_editor_property("parameter_name", "Intensity"); inten.set_editor_property("default_value", 1.0)
    mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -500, 0)
    mel.connect_material_expressions(col, "", mul, "A")
    mel.connect_material_expressions(inten, "", mul, "B")
    out = mul
    if fresnel:   # soft "plasma ball" edge on a sphere mesh
        fr = mel.create_material_expression(m, unreal.MaterialExpressionFresnel, -800, 400)
        fr.set_editor_property("exponent", 1.5)
        oneminus = mel.create_material_expression(m, unreal.MaterialExpressionOneMinus, -600, 400)
        mel.connect_material_expressions(fr, "", oneminus, "")
        mul2 = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 100)
        mel.connect_material_expressions(out, "", mul2, "A")
        mel.connect_material_expressions(oneminus, "", mul2, "B")
        out = mul2
    mel.connect_material_property(out, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m)
    eal.save_asset(full, only_if_is_dirty=False)
    return m

make_glow("M_FireGlow")                                   # fireball core, aura shells, explosion flash sphere
make_glow("M_VishapGlow", color=(0.4, 3.0, 0.8))          # enemy eyes / death chunks
make_glow("M_FireBreath", fresnel=False)                  # breath cone (add Panner+Noise later if time)
unreal.log("FX materials done")
```
(Pin names `""` select the first output or input, per `MaterialEditingLibrary.h:236-242`. The expression class Python names follow UE's `MaterialExpressionX` rule. **CRITIC FIX:** `""` is the **only** name that works for OneMinus. `GetShortenPinName` maps `Input` to `NAME_None` (`Editor/UnrealEd/Private/MaterialGraphNode.cpp:610-613`), so passing `"Input"` **always fails**. Do not use the old fallback hint.)

> **CRITIC NOTE:** `materials_build.py` has already built `/Game/Twilight/Materials/M_Additive`, `M_FireSprite` and their MIs (`MI_Additive_Glow`, `MI_Additive_FireballCore`, `MI_FireSprite_*`) with the correct usage flags. The real run was on 2026-10-18 16:59 with 0 errors (`Game/Saved/Logs/TwilightAssets.log:1609-1779`). Use those instead of running `make_fx_materials.py`. The `Color`/`Intensity` parameter names match the MID snippet below (`M_Additive` has `Color`, `Intensity`, `GlowMode`, `Falloff`, `FadeDistance`).

Runtime colour and animation through a dynamic material instance (Engine module only, no plugin):
```cpp
UMaterialInstanceDynamic* MID = Core->CreateDynamicMaterialInstance(0, LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/FX/Materials/M_FireGlow.M_FireGlow")));
MID->SetVectorParameterValue(TEXT("Color"), VFX::FireOrange);
MID->SetScalarParameterValue(TEXT("Intensity"), 1.f + 0.3f*FMath::Sin(Time*20.f)); // flicker
```
**No-particle explosion fallback:** spawn a sphere with `M_FireGlow`, scale it 0.2→6 over 0.35 s while `Intensity` goes 8→0, and spawn a flat cylinder ring (shockwave) the same way. Add the point-light flash from §C. A Bloom post-process on top makes this look decent even if no particle asset loads.

### Optional: recolour a Niagara template headlessly (only if you really want templates)
```python
import unreal
eal = unreal.EditorAssetLibrary
src, dst = "/Niagara/DefaultAssets/Templates/Systems/SimpleExplosion", "/Game/FX/NS_ExplosionTemplate"
eal.duplicate_asset(src, dst)
sys = eal.load_asset(dst)
mat = eal.load_asset("/Game/FX/Materials/M_FireGlow")          # must have used_with_niagara_* = True
pkg = sys.get_outermost().get_path_name()
for cls in (unreal.NiagaraSpriteRendererProperties, unreal.NiagaraRibbonRendererProperties):
    for r in unreal.ObjectIterator(cls):
        if r.get_outermost().get_path_name() == pkg:
            r.set_editor_property("material", mat)
for r in unreal.ObjectIterator(unreal.NiagaraMeshRendererProperties):   # SimpleExplosion has a debug arrow mesh renderer
    if r.get_outermost().get_path_name() == pkg:
        r.set_editor_property("is_enabled", False)                       # bIsEnabled is UPROPERTY(EditAnywhere), Niagara/Classes/NiagaraRendererProperties.h:482-483
eal.save_asset(dst, only_if_is_dirty=False)                          # PreSave waits for compile
```
This is **UNVERIFIED** end to end. The particle colour would still come from the template's module defaults (white or grey), and the material's `Color` param then drives the tint.

---

## 5) Iris Xe performance notes

- **The budget to aim for:** fewer than ~3–5k live sprites total on screen, and fewer than ~150 live per explosion. Fullscreen translucent overdraw is the real killer on an iGPU, not the particle count. Keep big smoke and fire sprites few, and never put many large sprites right in front of the camera. In 3rd person the hero aura sits in front of the camera, so keep its scale small (0.18–0.35 as above).
- **Kill refraction:** `M_Heat_Distortion` in `P_Fire` forces the distortion pass. Disable the emitter (`SetEmitterEnable("Distortion", false)`) **and** set `r.RefractionQuality=0` (EffectsQuality 0/1 already set it to 0: `BaseScalability.ini:800,829`; the read is at `$E/Engine/Source/Runtime/Renderer/Private/DistortionRendering.cpp:146-152`).
- **Global throttles** (all verified to exist):
  - `r.EmitterSpawnRateScale` (Cascade spawn-rate multiplier, `ParticleModules_Spawn.cpp:250`; Low=0.125, Med=0.25, High=0.5 in `BaseScalability.ini:810,839,868`). Recommend `0.5–0.75` for the demo.
  - `fx.Niagara.QualityLevel` (0–4, default 3, `NiagaraPlatformSet.cpp:51-53`).
  - `r.ParticleLightQuality` (0 none / 1 simple / 2 HQ, `ParticleModules.cpp:3079-3081`). Use **1**, and do the important lights with real `UPointLightComponent`s without shadows.
  - `r.SeparateTranslucencyScreenPercentage` (default 100, `TranslucentRendering.cpp:90-94`). Setting it to **50** renders translucency at half resolution and is a big overdraw saving on an iGPU, with a slight softness that is invisible on fire.
  - `r.ParticleLODBias` (`ParticleSystemComponent.cpp`).
  ~~Put these in `Config/DefaultEngine.ini` under `[SystemSettings]` or `[ConsoleVariables]`~~ **CRITIC FIX:** all of these are scalability-group cvars (`BaseScalability.ini [EffectsQuality@N]`, lines 798-949). `[SystemSettings]` is applied at `ECVF_SetBySystemSettingsIni` (0x05, `SystemSettings.cpp:80`), which outranks `ECVF_SetByScalability` (0x02, `IConsoleManager.h:158-165`). Putting them there silently freezes them and breaks every quality toggle. Put them into `Config/DefaultScalability.ini` under `[EffectsQuality@2]` / `[EffectsQuality@3]`, as in report 04 §4.3. Also set **`r.RefractionQuality=0` in both of those sections** while `P_Fire` (with `M_Heat_Distortion`) is in use. Report 04 currently has 1 and 2 there; it is corrected too. For a one-off test, `-ExecCmds="r.EmitterSpawnRateScale 0.6"` (console priority) is fine.
- **GPU vs CPU sim:** Iris Xe on Vulkan (SM5/SM6) supports compute, so GPU sims (StarterContent `TypeDataGpu`, DMX fireworks) are fine and take load off the CPU, which is shared with game logic. GPU emitters need fixed bounds. The authored assets have them, but if they pop out at screen edges, raise `bFixedBounds` / reduce `fx.Niagara.Scalability.DistanceCulling`. Keep **CPU** sims for small counts (smoke puffs, < 100).
- **Pooling:** use `EPSCPoolMethod::AutoRelease` / `ENCPoolMethod::AutoRelease` for every one-shot (impacts, deaths). That avoids component churn during waves.
- **Lights:** no more than ~6–8 dynamic point lights at once with **CastShadows=false**. Fade or destroy flash lights within 0.25 s. Lumen on an iGPU is expensive, so the main agent should probably run without Lumen GI (out of scope here). Unshadowed point lights stay cheap.
- **Warm-up:** pre-spawn every effect once during the loading or intro screen. The first use otherwise compiles PSOs, which causes a visible 100–500 ms hitch on Linux Vulkan.
- **Profiling commands while testing:** `stat fps`, `stat unit`, `stat particles`, `stat niagara`, `fx.Niagara.Debug.Enabled 1`, `r.ScreenPercentage 75` (if the GPU-bound frame is still > 16 ms).

---

## UNVERIFIED items (to test in the first headless or `-game` run)
1. The types of DMX User params (`PrimColor` etc.: LinearColor vs Vec3/Vec4). Run `LogUserParams` at BeginPlay.
2. The correct `ScaleMod` value for fireworks at game scale (start at 0.15 and tune).
3. Exact Cascade emitter names (`Distortion`, `Flames`, …), inferred from the name table.
4. Whether `VFX_ColdSparks_Stream` velocity follows component rotation.
5. Python duplicate + save of a Niagara system compiling cleanly under `-run=pythonscript` (expected to work, because PreSave waits for compile).
6. Whether the cooker picks up assets referenced only from C++ CDOs (use `DirectoriesToAlwaysCook` anyway).
7. ~~`MaterialExpressionOneMinus` pin naming in `connect_material_expressions`.~~ CRITIC FIX: resolved. Use `""` (see §F).
8. CRITIC: `P_Fire` name-table strings were re-checked and contain `Flames`, `Smoke`, `Embers`, `Sparks`, `Distortion` and `M_Heat_Distortion`. That `Distortion` is the emitter name is still inferred, not proven.
