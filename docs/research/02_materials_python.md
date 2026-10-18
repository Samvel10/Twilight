# 02 — Building materials headlessly with editor Python (UE 5.8)

**Engine:** `/home/samo/UnrealEngine-5.8` (`$E` below). I checked every claim against the source on disk on 2026-10-18. Anything I could not prove from source is marked **UNVERIFIED**.
**Script:** `/var/www/html/Twilight/docs/research/materials_build.py`. It is complete and re-runnable. It builds 7 materials and 13 MIs under `/Game/Twilight/Materials`.
**Testing so far:** `python3 -m py_compile` passes. A full mock run against a stub `unreal` module also passes: every helper call, pin and tuple path ran, and it reported 0 errors. It has **not** been run in the real editor yet, because I was told not to launch UE. The first real run is the final check (§5).

---

## 0. TL;DR for the main agent

1. Copy the script, for example to `/var/www/html/Twilight/Game/Scripts/materials_build.py`.
2. Close any editor that has `Twilight.uproject` open, then run:
   ```bash
   /home/samo/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd \
     /var/www/html/Twilight/Game/Twilight.uproject \
     -run=pythonscript -script=/var/www/html/Twilight/Game/Scripts/materials_build.py \
     -unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput 2>&1 | tee /tmp/mat_build.log
   grep -E "TwilightMat|LogPython|Error" /tmp/mat_build.log | tail -60
   ```
   A successful run ends with `[TwilightMat] === done: 7 materials, 0 errors ===` and `Python script executed successfully`.
3. The `.uproject` already enables `PythonScriptPlugin` and `EditorScriptingUtilities` with `TargetAllowList: ["Editor"]`. I checked this read-only. Nothing to change.
4. StarterContent is already at `/Game/StarterContent`. I verified that `T_Perlin_Noise_M`, `T_Water_N`, `T_Rock_Slate_D`, `T_Rock_Basalt_D`, `T_Tech_Hex_Tile_N` and `T_MacroVariation` exist. The script falls back to `/Engine/...` textures if any are missing.
5. Shaders are **not** guaranteed to compile inside the commandlet. Check for real compile errors on the first normal editor or game launch: `grep -iE "Failed to compile Material|error.*M_(Fire|Water|Rock|Vishap|Sky|Additive)" Saved/Logs/Twilight.log`.

---

## 1. Verified API (5.8 source)

### 1.1 `unreal.MaterialEditingLibrary`
Header: `$E/Engine/Source/Editor/MaterialEditor/Public/MaterialEditingLibrary.h`. The implementation is in `.../MaterialEditor/Private/MaterialEditingLibrary.cpp`. All functions below are `UFUNCTION(BlueprintCallable/BlueprintPure)`, so Python exposes them as snake_case static methods.

| Python | C++ signature | Header line |
|---|---|---|
| `create_material_expression(material, expression_class, node_pos_x=0, node_pos_y=0)` | `UMaterialExpression* CreateMaterialExpression(UMaterial*, TSubclassOf<UMaterialExpression>, int32 NodePosX=0, int32 NodePosY=0)` | :167-168 |
| `connect_material_property(from_expression, from_output_name, property)` → bool | `bool ConnectMaterialProperty(UMaterialExpression*, FString FromOutputName, EMaterialProperty)` | :231-232 |
| `connect_material_expressions(from_expression, from_output_name, to_expression, to_input_name)` → bool | `bool ConnectMaterialExpressions(UMaterialExpression*, FString, UMaterialExpression*, FString)` | :241-242 |
| `disconnect_material_property(material, property)` | | :259-260 |
| `recompile_material(material)` → `list[str]` (compile errors) | `TArray<FString> RecompileMaterial(UMaterial*)` | :266-267 |
| `layout_material_expressions(material)` | | :291-292 |
| `get_material_expressions(material)` / `get_num_material_expressions` | | :140-145 |
| `delete_material_expression(material, expression)` / `delete_all_material_expressions(material)` | | :149-154 |
| `set_base_material_usage(material, usage, value=True)` | (`set_material_usage` is deprecated, :187) | :204-205 |
| `get_material_expression_input_names(expr)` / `..._output_names(expr)` | the exact strings that `connect_*` accepts | :324-333 |
| `set_material_instance_parent(instance, new_parent)` | | :407-408 |
| `set_material_instance_scalar/vector/texture_parameter_value(instance, name, value, association=GLOBAL_PARAMETER)` | | :420-421 / :456-457 / :429-430 |
| `get_material_instance_scalar_parameter_value(instance, name)` | | :416-417 |
| `clear_all_material_instance_parameters(instance)`, `update_material_instance(instance)` | | :411-412, :489-490 |

Implementation facts that matter:
- **`create_material_expression`** calls `CreateMaterialExpressionEx(..., SelectedAsset=nullptr)` (cpp :634-637). It does not assign a texture or function, so you set them yourself. It calls `ValidateParameterName(false)`, so you set `parameter_name` *after* creating the node. A new `ComponentMask` gets **R=G=true** by default (cpp ~:766-772), so the script always sets all four of r, g, b, a.
- **Output-name resolution** (`GetExpressionOutputIndexByName`, cpp :81-128): `""` gives output 0. Otherwise it matches `FExpressionOutput::OutputName`. Unnamed outputs also match `"R"`, `"G"`, `"B"` or `"A"` by mask. Named outputs I verified:
  - `TextureSample` and its parameters: `RGB, R, G, B, A, RGBA` (cpp :2574-2580).
  - `VectorParameter`: the same set (cpp :8014+).
  - `ParticleColor`: the same set (cpp :10069+).
  - `WorldPosition`: `XYZ, XY, Z` (cpp :12249+).
- **Input-name resolution** (`GetExpressionInputByName`, cpp :46-75): `""` gives input 0. Otherwise it compares against `UMaterialGraphNode::GetShortenPinName(GetInputName(i))` (`$E/Engine/Source/Editor/UnrealEd/Private/MaterialGraphNode.cpp:597-639`), which renames:
  - `Coordinates` → **`UVs`**
  - `TextureObject` → **`Tex`**
  - `Exponent` → **`Exp`** (this is the Power node)
  - **`Input` → NAME_None**. So single-input nodes (OneMinus, Saturate, Abs, Sine, ComponentMask, Clamp's first pin) can **only** be reached with `""`. Passing `"Input"` **fails**. This corrects the fallback hint in `01_niagara_vfx.md`.
  - `MipLevel` → `Level` and `MipBias` → `Bias`.
  - Pin names come from the `FExpressionInput` member names. I verified these per header: Multiply/Add/Sub/Div/Max/Min/Dot/Append/Distance use `A, B`. Lerp uses `A, B, Alpha`. Panner uses `Coordinate, Time, Speed`. Fresnel uses `ExponentIn, BaseReflectFractionIn, Normal`. SphereMask uses `A, B, Radius, Hardness`. Power uses `Base, Exp`. DepthFade uses `InOpacity, FadeDistance`. Noise uses `Position, FilterWidth`.
- **`recompile_material`** runs `PreEditChange(nullptr)` and `PostEditChange()` inside an `FMaterialUpdateContext`. It updates child MIs' parameter names and then returns `GetMaterialResource(GMaxRHIShaderPlatform)->GetCompileErrors()` (cpp :985-1061). Compilation is asynchronous, so **an empty list does not prove the shader compiles**.
- **`set_material_instance_*_parameter_value` always returns `False`**. `bResult` is never set (cpp :1485-1494, :1507-1516, :1573-1582). Never test the return value. Read the value back instead, which is what the script does.
- **`set_base_material_usage`** returns early if the flag is already set. Otherwise it sets the flag and runs a full `RecompileMaterialInternal` (cpp :830-846). The script calls it right after creating the material, while the graph is still empty, so those recompiles are cheap.
- **`delete_all_material_expressions` is risky.** It range-iterates `Material->GetExpressions()`, which is a live `TConstArrayView` (`Material.h:1479`), while `DeleteMaterialExpression` removes items from that same collection (cpp :563-565, :609). That can skip elements or fire an iterator ensure. I found this by reading the code and did not test it. The script deletes from a Python copy of `get_material_expressions()` instead.

### 1.2 Factories and asset creation
- `unreal.MaterialFactoryNew` (`$E/Engine/Source/Editor/UnrealEd/Classes/Factories/MaterialFactoryNew.h:14-27`). Its only property is `InitialTexture`, a `UPROPERTY()`. `FactoryCreateNew` (`.../Private/Factories/EditorFactories.cpp:514-545`) creates an **empty** material with no Substrate node. It sets `bAutomaticallySetUsageInEditor` from a CVar (:518).
- `unreal.MaterialInstanceConstantFactoryNew` (`.../Factories/MaterialInstanceConstantFactoryNew.h:19-20`). `InitialParent` is a plain `UPROPERTY()`, and Python only exposes properties that are `BlueprintVisible` or `Edit` (`PyGenUtil.cpp:1609-1613`, `:1811-1815`), so **you cannot set it from Python**. Create the MI without a parent, then call `MaterialEditingLibrary.set_material_instance_parent` (cpp :1457-1464, which calls `SetParentEditorOnly`). `FactoryCreateNew` handles a null parent fine (`EditorFactories.cpp:479-491`).
- `unreal.AssetToolsHelpers.get_asset_tools()` (`$E/Engine/Source/Developer/AssetTools/Public/IAssetTools.h:892-898`) gives you `create_asset(asset_name, package_path, asset_class, factory, calling_context=None, overwrite_existing=False)` (`IAssetTools.h:348-349`, a `BlueprintCallable` virtual).
- Saving:
  - `unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=True)` and `save_loaded_asset(obj, only_if_is_dirty=True)` (`$E/Engine/Plugins/Editor/EditorScriptingUtilities/Source/EditorScriptingUtilities/Public/EditorAssetLibrary.h:262, :281`). These need the **EditorScriptingUtilities** plugin.
  - Without the plugin, use `unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(...)` (`$E/Engine/Source/Editor/UnrealEd/Public/Subsystems/EditorAssetSubsystem.h:277`).
  - As a last resort, `unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages, save_content_packages)` (`$E/Engine/Source/Editor/UnrealEd/Public/FileHelpers.h`, inside `class UEditorLoadingAndSavingUtils`).
  - The script tries all three in that order.
- Other helpers: `unreal.load_module(name)`, `unreal.load_asset(path)` and `unreal.log/log_warning/log_error` (`PyCore.cpp:2066-2077`). `unreal.Paths.project_content_dir()`, `engine_content_dir()` and `convert_relative_path_to_full()` come from `UBlueprintPathsLibrary`, which has `ScriptName="Paths"`.

### 1.3 Python naming rules (verified in `PyGenUtil.cpp`)
- **Property names:** `PythonizePropertyName` (:1951-1975) removes a `b` prefix before an uppercase letter and an `In` prefix, then converts to snake_case. Examples: `bIsSky`→`is_sky`, `TwoSided`→`two_sided`, `ConstA`→`const_a`, `SpeedX`→`speed_x`, `AttenuationRadius`→`attenuation_radius`, `HardnessPercent`→`hardness_percent`, `ParameterName`→`parameter_name`, `DefaultValue`→`default_value`.
- **Enum values:** `GetEnumEntryPythonName` (:3108-3161) applies `PythonizeName` in UPPER case. Examples:
  - `MP_EmissiveColor`→`unreal.MaterialProperty.MP_EMISSIVE_COLOR`
  - `BLEND_Additive`→`unreal.BlendMode.BLEND_ADDITIVE`
  - `MSM_Unlit`→`unreal.MaterialShadingModel.MSM_UNLIT`
  - `MATUSAGE_NiagaraSprites`→`unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES`
  - Names that contain digits, such as `NOISEFUNCTION_GradientTex3D`, are **UNVERIFIED**. The script avoids those enums and resolves every enum through `getattr` with a warning.
- `EMaterialShadingModel` and `EMaterialDomain` are `UENUM()` without `BlueprintType` (`EngineTypes.h:706-707`, `MaterialDomain.h:11-12`). They are still generated because types referenced by exported properties are force-exported (`PyWrapperTypeRegistry.cpp:1174`, `ForceShouldExport`).
- `set_editor_property(name, value, notify_mode=DEFAULT)` (`PyWrapperObject.cpp:1133`) calls PreEditChange and PostEditChange when the value changes. That matters for two things:
  - **`texture`** on a TextureSample, TextureSampleParameter2D or TextureObject(Parameter) triggers `PostEditChangeProperty`, which calls **`AutoSetSampleType()`** (`MaterialExpressions.cpp:2625-2633, :4194-4201`). The sampler type then matches the texture's compression and sRGB settings automatically.
  - **`material_function`** on a `MaterialExpressionMaterialFunctionCall` triggers `SetMaterialFunctionEx` (`MaterialExpressions.cpp:15716-15741`), so the pins get created.

### 1.4 UMaterial properties used (`$E/Engine/Source/Runtime/Engine/Public/Materials/Material.h`)
- `material_domain` :482, `blend_mode` :486, `shading_model` :511 (private but `EditAnywhere`, so Python can set it), `two_sided` :561, `is_sky` :1090.
- The `bUsedWith*` fields are `UE_DEPRECATED(5.8, "Always use the GetUsageByFlag() accessor.")` (:701-911). Use `set_base_material_usage` instead.
- The `EMaterialUsage` list is in `.../Materials/MaterialInterface.h:75-110`.
- **Substrate:** the `r.Substrate` default is **0** (`$E/Engine/Source/Runtime/RenderCore/Private/RenderUtils.cpp:2069-2072`), and the project's `DefaultEngine.ini` does not set it, so Substrate is OFF. Even if someone turns it on, `IsHiddenMaterialAssetConversionEnabled()` is hard-wired to true (`RenderUtils.cpp:2564-2569`). Legacy root pins and `ShadingModel` keep working and are converted on the fly (`Material.cpp:5223-5227`, `:5374-5381`).

---

## 2. What the script builds

All parameters are named, grouped and overridable from MIs, and from C++ through `UMaterialInstanceDynamic::SetScalarParameterValue` / `SetVectorParameterValue`. "Instr." is a rough estimate.

| Asset | Shading / blend | Usages set | Graph (summary) | Iris Xe cost |
|---|---|---|---|---|
| **M_FireBody** | DefaultLit, opaque (`FIREBODY_UNLIT=True` switches to Unlit) | SkeletalMesh, NiagaraMesh, SplineMesh | 2× panning `NoiseTex` samples (TexCoord×`NoiseTiling`, time×`FlowSpeed`). Ridged mask `1-abs(2n-1)` raised to `CrackSharpness` gives lava veins. Emissive = lerp(`CrackColorDeep`,`CrackColorHot`)×`EmissiveIntensity`×pulse + Fresnel(`RimExponent`)×`RimColor`×`RimIntensity` + `FlashColor`×`HitFlash`. BaseColor = `SkinColor`×(1-cracks). | 2 tex, ~60 instr. |
| **M_FireSprite** | Unlit, **Additive**, two-sided | NiagaraSprites/Ribbons/Mesh, ParticleSprites (Cascade), MeshParticles | SphereMask(TexCoord, 0.5, r=0.5, hardness 0). Soft = mask^`Falloff`, core = mask^`CoreSharpness`. (`Color`×`Intensity`×soft + `CoreColor`×`CoreIntensity`×core) × ParticleColor.RGB × DepthFade(ParticleColor.A, `FadeDistance`). No textures. | 0 tex, ~30 instr. + depth read |
| **M_Additive** | Unlit, **Additive** | Niagara*, Particle*, Skeletal | lerp(radial UV mask, view-facing core = (1-Fresnel)^`Falloff`, `GlowMode`) × `Color` × `Intensity` × DepthFade. Use `GlowMode` 0 for cards and 1 for fireball spheres. | 0 tex |
| **M_Water_Purple** | DefaultLit, **opaque** | ISM | **WPO**: Σ of 3 sines `sin(2π(dot(WP.xy,dir_i·k_i)/WaveLength + t·WaveSpeed·√k_i))`, weights 1/0.62/0.38, ×`WaveHeight` → (0,0,h). **Normal**: two panning `T_Water_N` samples in world UV (`NormalTile`), lerped from (0,0,1) by `NormalStrength`. **Base**: lerp(`DeepColor`,`HorizonColor`, Fresnel) + crest tint. **Emissive**: fake sky reflection (`SkyReflectColor`×Fresnel×`ReflectIntensity`) + sun glint `pow(sat(dot(ReflectionVectorWS, normalize(SunDir))), SunGlintSharpness)×SunColor×SunGlintIntensity`. `Roughness` 0.08, `Specular` 0.6. Does not depend on SSR, Lumen or translucency. | 2 tex, ~90 instr. (pixel) + cheap VS |
| **M_Rock** | DefaultLit, opaque | ISM | Triplanar: 3 samples of `RockTex` (TextureObjectParameter) on WP/`TexScale` XY, YZ and XZ. Weights from abs(VertexNormalWS)^`BlendSharpness`, normalised. × `Tint` × macro variation (`MacroNoise` at WP.xy/`MacroScale`, lerp 0.65–1.25). Top dusting with `TopColor` via n.z^`TopSharpness`×`TopAmount`. | 4 tex |
| **M_VishapSkin** | DefaultLit, opaque | Skeletal, SplineMesh, ISM, NiagaraMesh | Normal = hex-tile `ScaleNormal` (TexCoord×`ScaleTiling`) lerped by `ScaleNormalStrength`. Veins = ridged 2-octave panning noise^`VeinSharpness` × `VeinColor` × `VeinIntensity` × pulse(`PulseSpeed`). Plus Fresnel rim and `HitFlash`. Base = lerp(`SkinColor`,`SkinColor2`, noise)×(1-veins). `Roughness`, `Metallic`. | 3 tex |
| **M_Sky** | **Unlit**, opaque, `is_sky`, two-sided | – | dir = -CameraVectorWS. lerp(`HorizonColor`,`ZenithColor`, sat(z)^`GradientExponent`), then toward `BelowColor` below the horizon. Sun disc `pow(dot(dir,SunDir),SunDiscExponent)×SunDiscIntensity` + glow + horizon band (1-\|z\|)^`HorizonBandExponent`. All × `SunColor`, + sky×`SkyIntensity`. | 0 tex, ~40 instr. |

**Material instances:**
- `MI_FireBody_Vahagn`, `MI_FireBody_Ember`
- `MI_FireSprite_Flame`, `MI_FireSprite_Core`, `MI_FireSprite_VishapGreen`
- `MI_Additive_Glow`, `MI_Additive_FireballCore`
- `MI_Water_Purple`
- `MI_Rock_Mountain`, `MI_Rock_Basalt`
- `MI_VishapSkin_Serpent`, `MI_VishapSkin_Boss` (red veins)
- `MI_Sky_Sunset`

**Textures:** each is chosen from the first candidate that exists on disk. The script checks the `.uasset` path through `unreal.Paths`, so it does not depend on the asset-registry scan state.
- noise: `/Game/StarterContent/Textures/T_Perlin_Noise_M` (TC_Masks), then `/Engine/MaterialTemplates/Textures/T_Noise01`, then `/Engine/MapTemplates/TilingNoise05`, then `/Engine/EngineMaterials/Good64x64TilingNoiseHighFreq` (TC_Grayscale)
- water normal: `/Game/StarterContent/Textures/T_Water_N` (TC_Normalmap). If it is missing, the Normal pin is left unconnected.
- rock: `T_Rock_Slate_D`, then `T_Rock_Basalt_D`, then `T_Rock_Sandstone_D`, then the noise list
- scales normal: `T_Tech_Hex_Tile_N`, then `T_CobbleStone_Pebble_N`. If both are missing, there is no normal.

I identified the compression settings by grepping each `.uasset` for its `TC_*` string. The sampler type is set automatically (§1.3), so these settings cannot cause a sampler mismatch.

**Design choices for the iGPU:**
- Nothing is translucent except the two additive FX materials.
- There is no SSR dependence. The sun path on the water is computed in the emissive.
- Noise comes from textures (1 fetch each), not from the ALU `Noise` node. The Noise node costs ~16–80 instructions per level according to the comments in `MaterialExpressionNoise.h:14-45`.
- There are no static switches, so each material has one permutation.

### Code-side usage notes
- **Sky fallback:**
  ```cpp
  UStaticMeshComponent* Sky = ...; // mesh /Engine/EngineSky/SM_SkySphere (exists), scale ~ (5000,5000,5000)
  Sky->SetMaterial(0, LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Twilight/Materials/MI_Sky_Sunset.MI_Sky_Sunset")));
  Sky->SetCastShadow(false); Sky->bAffectDistanceFieldLighting=false;
  ```
  `SunDir` is the direction **toward** the sun, which is `-DirectionalLight->GetForwardVector()`. Set it on the sky and the water through MIDs, or from C++ every time the light rotates.
- **Water WPO:** the sea mesh needs vertex density of roughly ≤ `WaveLength`/8 (~300 cm), for example a 256×256 grid plane from ProceduralMeshComponent. `/Engine/BasicShapes/Plane` has only 4 verts and will **not** show waves. Raise the component's `BoundsScale` (~2) so WPO does not cause culling pops.
- **Hit flash:** `MID->SetScalarParameterValue("HitFlash", 1.f)`, then decay it to 0 over 0.15 s. This works on both `M_FireBody` and `M_VishapSkin`.

---

## 3. How to run

### 3.1 Commandlet (recommended, needs no GPU or window)
```bash
/home/samo/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd \
  /var/www/html/Twilight/Game/Twilight.uproject \
  -run=pythonscript -script=/ABS/PATH/materials_build.py \
  -unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput
```
- `UPythonScriptCommandlet::Main` (`$E/Engine/Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/PythonScriptCommandlet.cpp:15-72`) works like this:
  - It parses `-Script=` by hand, either as a quoted string or as a token. Quote the path if it contains spaces.
  - It calls `ForceEnablePythonAtRuntime()` and runs the startup scripts.
  - It executes the file with `EPythonCommandFlags::Unattended`.
  - It returns **-1** if the script raised. The script raises at the end if any error was collected, so CI-style checks work: `echo $?` gives a non-zero result on failure.
- A first run on a fresh project also builds the DDC and compiles the shaders of the default materials. Expect **several minutes** on this laptop.
- I could not find an `-ExecutePythonScript` handler in the 5.8 plugin source. A grep only found `K2Node_ExecutePythonScript`, so that switch is **UNVERIFIED** for 5.8. To run the script inside a full GUI editor, use `-ExecCmds="py /abs/path/materials_build.py"`. This is also **UNVERIFIED**, but `py <file>` is the standard console command.

### 3.2 `.uproject` plugins
Both plugins are `"EnabledByDefault": false`:
- `PythonScriptPlugin.uplugin:13`
- `EditorScriptingUtilities.uplugin:13`

They must be listed in the `.uproject`. The current `/var/www/html/Twilight/Game/Twilight.uproject` **already has**:
```json
{ "Name": "PythonScriptPlugin", "Enabled": true, "TargetAllowList": ["Editor"] },
{ "Name": "EditorScriptingUtilities", "Enabled": true, "TargetAllowList": ["Editor"] },
```
`PythonScriptPlugin` is an `UncookedOnly` module (`PythonScriptPlugin.uplugin:25-27`), so it never ships in the game build. Without EditorScriptingUtilities the script still works through `EditorAssetSubsystem`.

---

## 4. Gotchas (all handled in the script unless noted)

1. **Shader compilation in a commandlet.** Commandlets use NullRHI unless you pass `-AllowCommandletRendering` (`LaunchEngineLoop.cpp:2246`). `recompile_material` returns errors only from the resource that was compiled synchronously (cpp :1056-1059), and compilation is asynchronous anyway. **Real HLSL errors only show up when the editor or game first loads the material.** Check the log after the first launch. Shader maps are not stored in the `.uasset` (only cooked builds contain them), so saving without compiling is fine.
2. **First launch is slow.** Seven new materials × (SM6 Vulkan + usages) ≈ a few thousand shader jobs on top of the engine defaults. `DefaultEngine.ini` targets **SF_VULKAN_SM6 only**. Launch the editor or `-game` once **tonight** so the DDC (`Saved/DDC` / local DDC) is warm before the presentation. Do not add unneeded usage flags, because each flag multiplies the permutations.
3. **Usage flags.** If a flag is missing, the default material renders in `-game` or cooked builds, for example on skeletal or Niagara meshes. The editor only auto-fixes this when `bAutomaticallySetUsageInEditor` is set and the asset gets saved. The script sets flags explicitly with `set_base_material_usage`. **If the vishap is built from SplineMeshComponents, `MATUSAGE_SPLINE_MESH` is required. It is set.**
4. **sRGB and normal sampler types.** A sampler type that does not match the texture's `CompressionSettings`/`SRGB` is a **compile error**: "Sampler type is X, should be Y" (`MaterialExpressionUtils.cpp:14-50, VerifySamplerType`). The mapping is: Normalmap→Normal, Masks→Masks (requires sRGB off), Grayscale→Grayscale or LinearGrayscale depending on sRGB, Default→Color or LinearColor depending on sRGB, and the Virtual* variants for VT textures. The script assigns `texture` through `set_editor_property`, which calls `AutoSetSampleType()`. The script also sets the same texture on every TextureSample that is fed by a TextureObjectParameter, so all samplers agree. **If an MI overrides `RockTex`/`NoiseTex`/`WaterNormal` with a texture of a different compression type, compilation breaks.** Only swap like for like: normal for normal, color for color.
5. **Pin names.** Use `""` for the first or only input. Never pass `"Input"`. Power's exponent pin is `"Exp"`, and a TextureSample's UV pin is `"UVs"`. On failure, the `G.link` helper prints the real names from `get_material_expression_input_names`. A name printed as `None` means "pass `""`".
6. **Parameter naming.** Set `parameter_name` after creation, because creation runs `ValidateParameterName`. Parameter names must be unique per type, and the script shares textures through TextureObjectParameters instead of duplicating parameter names.
7. **Re-running.** `create_asset` on an existing path asks to overwrite, or fails, in unattended mode. The script loads the existing asset and rebuilds its graph in place, so level and MI references survive. It avoids `delete_all_material_expressions` (§1.1).
8. **Asset registry not scanned in the commandlet.** `does_asset_exist` can return False for assets that exist. The script checks the `.uasset` file on disk instead.
9. **Saving.** Assets created by `create_asset` are dirty but **not saved**. You must call `save_loaded_asset`/`save_asset(..., only_if_is_dirty=False)`. Unsaved assets are lost when the commandlet exits. The script saves every asset and then calls `save_dirty_packages` as a safety net.
10. **Do not run while the editor has the project open.** Both processes would write the same packages.
11. **WPO and Large World Coordinates.** `WorldPosition` is LWC. Dividing it by `WaveLength` is fine near the origin. Keep the play area within ±1 km of the origin to avoid shimmering in the sine phases. `Time` grows unboundedly. After hours of uptime the `sin(t)` precision drops, which is irrelevant for an 8-minute match.
12. **SM6 / Iris Xe.** Not about materials, but note it: the project targets only `SF_VULKAN_SM6`. If the Iris Xe Vulkan driver turns out not to support SM6 features, the game will not render. Consider adding `+TargetedRHIs=SF_VULKAN_SM5` as a fallback. **UNVERIFIED** for this laptop. Hand this to the main agent.

---

## 5. Validating after the first real run (5 minutes)

1. The commandlet output contains `[TwilightMat] built ...` lines ×20 and `0 errors`. The exit code is 0.
2. `ls /var/www/html/Twilight/Game/Content/Twilight/Materials/` shows 7 `M_*` and 13 `MI_*` `.uasset` files.
3. On the first editor or `-game` launch: `grep -iE "Failed to compile|Sampler type|\[SM6\].*error" Saved/Logs/Twilight.log` returns nothing.
4. If a connect fails, the log names the exact pin list. Fix the pin string in the relevant `build_*` function and re-run. The rebuild is idempotent.

## 6. UNVERIFIED list
- That the script works end to end in the real 5.8 editor. Only static checks and a mock run were done (§5).
- Python spellings of enum members that contain digits (not used).
- The `-ExecutePythonScript` / `-ExecCmds="py ..."` behaviour in 5.8 GUI mode.
- The `delete_all_material_expressions` skip/ensure behaviour. I inferred it from the code and did not reproduce it.
- Whether this laptop's Iris Xe Vulkan driver supports SM6.
- The visual tuning of the default colours and intensities. Adjust them through the MIs after the first look.
