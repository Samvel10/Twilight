# Armenian highlands environment: real DEM, Lake Sevan, Masis on the horizon (scratch prototype)

All work is in `proto2/highlands/`. `/var/www/html/Twilight` was **not** modified.
Scratch UE project: `proto2/highlands/ue/Highlands.uproject` (content-only, renderer and scalability copied from the game:
no Nanite, no Lumen, no VSM, TAA, game `DefaultScalability.ini` / `DefaultGameUserSettings.ini`). Test level: `/Game/Test/L_Highlands`.

## What it is
- **Site**: the real Geghama ridge with **Azhdahak** (3597 m; the "dragon" volcano, where vishap stones stand by mountain lakes), running
  east to the west shore of **Lake Sevan**. Masis/Ararat (5137 m, 93 km SW) and Aragats sit in the far ring. Earth curvature
  with refraction is applied, so Masis sits about 580 m lower, as it does in reality.
- **Terrain**: 3 nested static-mesh tile rings, each tile with its own LOD chain plus skirts (no Landscape, so the game can
  spawn it at runtime or stream it as a sublevel):

  | ring | size | tiles | grid (LOD0) | LODs | source | tris LOD0/tile |
  |---|---|---|---|---|---|---|
  | core | 30 km | 10x10 x 3 km | 18.75 m | 4 (x2 steps) | terrarium z12 (SRTM 30 m) + detail | 52k |
  | mid | 120 km (core cut out) | 60 x 15 km | 100 m | 3 | z11 | 45k |
  | far | 360 km (mid cut out) | 32 x 60 km | 400 m | 3 | z9 | 45k |
- **Detail added to the DEM** (core only): SRTM speckle smoothed on gentle ground (43 m Gaussian where slope < 12 deg), plus erosion
  rills elongated 6:1 down the fall line (2.4 m on slopes), 0.9 m hummocks, and a 0.35 m micro relief in the normal map.
- **Baked per-ring maps** (`scripts/dem_maps.py`):
  - `T_<ring>_N`: world-space normal (core 4096 = 7.3 m/texel).
  - `T_<ring>_Mask` RGBA: rock / scree / snow / lush.
  - `T_<ring>_Light` RGBA: **baked sunset terrain shadow** (sun az 255, el 8, ray-marched over all rings with curvature) / sky AO /
    stream channels / shore band.
  - `T_core_Canopy`: forest cover baked from the tree scatter, painted by the terrain beyond the tree cull distance.
- **Lake**: Sevan surface from the DEM (flat at 1898.0 m), mapped to world Z = 0. The bed is carved to 45 m depth (700 m shelf).
  The water is opaque, lit, with SSR and sky-cube reflections and 8 analytic ripple waves (`M_HLLake`). The water mesh is 7 chunks
  of 200 m cells (33k quads) following the curvature.
- **Vegetation and rocks**: HISM, about 960k instances. Rules are in `scripts/scatter.py` and the table below.
- **Lighting**: Poly Haven `kloppenheim_06_puresky` HDRI, used as a visible dome (`M_HLSky`, yaw solved analytically to the
  sun) and as the SkyLight cubemap. Directional sun at 8 deg, yaw -15 (from az 255). Exponential height fog with a second
  low haze layer, manual exposure.

## Screenshots (Read them)
- `shots/FINAL_views.jpg`: final 10 Sevan views (t13); `shots/FINAL_van.jpg`: 4 Lake Van (Hayk) views. `shots/t1.jpg` → `t12.jpg`: every iteration, with the problems found in each.
- `shots/FINAL_before_after.jpg`: the current game (sea and islands) next to the new highlands.
- `shots/sky_compare.jpg`: 3 Poly Haven sunset skies compared (kloppenheim kept, for its clouds and sun rays).
- raw PNGs in `shots/raw/<view>_t13.png` and `<view>_van2.png` (1600x900).

## Performance (Intel Iris Xe, i7-13700H, Vulkan SM5, 1600x900, game scalability)
Two measurements:
1. `scripts/perf.sh <view>`: `-game` run, CSV profiler with GPU stats, steady state after warm-up.
   Results are in `perf/final_<view>.txt` / `.csv` and in the table below.
   **The GPU was shared with other agents' editors during every run**, so the best 300-frame window is reported along with
   the average.
2. `scripts/prof.sh`: editor ProfileGPU A/B sequencer (hide groups, toggle cvars). It gave the per-pass costs that drove the
   optimisations, for example:
   - velocity pass from WPO foliage: 3.9 ms → 0 (static switch `Wind`);
   - masked distant pines: 4.6 ms → ~1.3 ms, via opaque lathe far LOD + canopy map + 4 km cull;
   - grass with 370k instances costs about 0.5-1 ms.

| view (-game, 1600x900, steady 900 frames) | fps (avg) | frame ms avg / p95 | GPU ms avg / p95 | biggest GPU passes (ms) |
|---|---|---|---|---|
| meadow: ground, grass + flowers, pines on horizon | **72.3** | 13.8 / 16.5 | 12.2 / 12.9 | BasePass 3.2, PrePass 2.0, TAA 1.2, ShadowDepths 0.9 |
| grove: 120 m over a 45k-pine plantation, backlit | **79.5** | 12.6 / 15.5 | 10.9 / 11.3 | BasePass 3.6, PrePass 1.5, TAA 1.2 |
| lake300: flight 300 m over the Sevan shore | **95.8** | 10.4 / 11.9 | 8.8 / 9.2 | BasePass 2.4, TAA 1.2, PrePass 0.8 |
| over1500: 1.5 km up, whole core + lake + far rings | **70.0** | 14.3 / 20.2 | 12.4 / 13.1 | BasePass 4.6, TAA 1.3, Lights 1.1 |

These figures include TAA, post, lights and shadows, which the game pays for anyway. The game measured ~100 fps with its own sea scene.
Env-only budget: about 9-12 ms GPU, so 50+ fps should hold with characters and FX on top. Before the optimisations the meadow
view ran at 43 fps (GPU 19 ms). Logs: `perf/final_<view>.txt`; raw CSVs in `proto2/highlands/perf/`.
`SkyAtmosphereEditor` (0.35 ms) only exists in editor-binary -game runs.

## Asset list and licences
| asset | source | licence | used as |
|---|---|---|---|
| kloppenheim_06_puresky (also tested industrial_sunset_02_puresky, evening_road_01_puresky) | Poly Haven | CC0 | sky dome + SkyLight |
| aerial_grass_rock, rocky_terrain_02, lichen_rock, aerial_rocks_01, snow_02, river_small_rocks | Poly Haven | CC0 | terrain layers |
| boulder_01, namaqualand_boulder_02/05, rock_07, rock_09, stone_01 | Poly Haven | CC0 | scattered basalt boulders (regraded dark) |
| "Pine Tree" (Corsican pine) by **emarshall**, sketchfab.com/3d-models/9dfbe65769c840a0ab366c67d8e6762d | Sketchfab via Objaverse | CC BY 4.0 | `SM_PineC`, the plantation pine (own LODs + far LOD) |
| "Plants Asset Set" by **emarshall**, sketchfab.com/3d-models/2edf52774f4d4cde8d8c3a19b8dda205 | Sketchfab via Objaverse | CC BY 4.0 | grass clumps (dry/green), poppies, daisies (split into plants) |
| "Simple grass chunks" by **3dhdscan** (Daniel Skl, own scans), sketchfab.com/3d-models/eb4f6dc9d4e3455ea3435385faf58b60 | Sketchfab via Objaverse | CC BY 4.0 | scanned grass tufts |
| "Juniper" by **evolveduk** (made in Tree It), sketchfab.com/3d-models/e74c7156984542c2a4cdf6ce8a0c8e96 | Sketchfab via Objaverse | CC BY 4.0 | junipers on rocky slopes |
| "Pine Tree" by evolveduk, sketchfab.com/3d-models/d45218a3fab349e5b1de040f29e7b6f9 | Sketchfab via Objaverse | CC BY 4.0 | fallback pine (`pine_model: "Pine"`), not used in final |
| Elevation: Mapzen Terrain Tiles on AWS Open Data (terrarium) | SRTM (NASA), GMTED2010 (USGS), ETOPO1 (NOAA) etc. | attribution: https://github.com/tilezen/joerd/blob/master/docs/attribution.md | terrain, maps |
| T_MacroNoise (procedural fBm) | own (islands prototype) | CC0 | macro variation |

Provenance checks: Objaverse metadata gives the description for each (3dhdscan links its own ArtStation scans; evolveduk models are
Tree It generations; emarshall describes original sets). No re-uploads or game rips were found.
Copernicus GLO-30 was not usable (Armenia tiles are not public), and Poly Haven trees are 7-17M-tri scans, which are unusable without Nanite.

Credit lines for `art/CREDITS_3D.md`:
```
Terrain elevation: Mapzen Terrain Tiles (AWS Open Data), SRTM/NASA, GMTED2010/USGS, ETOPO1/NOAA and others.
"Pine Tree" and "Plants Asset Set" by emarshall (sketchfab.com/emarshall), CC BY 4.0, modified (LODs, split plants).
"Simple grass chunks" by 3dhdscan (Daniel Skl), CC BY 4.0, modified.
"Juniper" by evolveduk, CC BY 4.0, modified (LODs).
Sky, terrain textures and rocks: Poly Haven (CC0).
```

## Scatter rules (`scripts/scatter.py`; data in `gen/scatter/*.f32` rows x,y,z cm, yaw, scale, variant)
| type | count | rule | mesh / LOD | cull (cm) | shadow |
|---|---|---|---|---|---|
| Pine (PineC) | 45k | elev < 2250 m, slope < 22 deg, off beach/rock; dense plantations = 700 m noise > 0.66 x 90 m glade noise | 46k / 21.7k / 15.3k / 309 (opaque far LOD) at screen size 1 / 0.5 / 0.25 / 0.08 | 380k-420k + canopy map beyond | yes |
| Juniper | 12k | 2000-2900 m, rock mask about 0.4, noise patches | 2.6k / 1.0k / 0.6k / 159 | 120k-150k | yes |
| Boulders | 260k | rock^2 + rock x clustered 220 m field noise, not on snow/lake; size exp(N(0,.45)) x (0.6+1.4 x mask) | 6 Poly Haven scans, 2.6-4.5k tris LOD0, 4 LODs | 200k-250k | yes |
| Shore stones | 25k | shore band (Light.A > 0.35) | same rocks, small | 30k-40k | no |
| Grass | 370k | within 140 m of ground cameras; 5 clumps/m^2 x lush/rock/snow/shore mask; 4 dry + 4 green emarshall + scanned tuft | 7-60 tris cards, scale xy 1.7 | 4000-4200 (thinning 22-40 m) | no |
| Flowers | 10k | lush patches (60 m noise); poppy fields vs daisy patches (400 m noise) | 7-374 tris | same as grass | no |

**Runtime grass in the game.** The static level only scatters grass around the test views. The game must generate it around
the player (see the integration section).

## Material parameters (G-helper scripts: `scripts/hl_materials.py`, `scripts/s3_veg.py`; defaults are the final values)
- `M_HLTerrain` (one master, `TangentSpaceNormal = false`, about 24 samples through shared samplers). The MIs `MI_HLTerrain_core|mid|far`
  swap `RegionNormal/Mask/Light/Canopy`. The mid and far MIs set `DetailFadeDist` to 20000/10000 and `BakedShadowStart` to 0.
  - Meadow: `MeadowTile` 1500, 2 scales (x3.37), `DryTint` (1.18,.98,.62), `LushTint` (.88,.95,.5), `LushNoise` .8, `OverlayTile` 9000, `OverlayAmount` .55.
  - Macro: `MacroScale1` 52000, `MacroScale2` 6100, `MacroMin/Max` .72/1.22.
  - Rock: `RockTile` 1100 (triplanar from the region normal, 2 rotated scales), `RockTint` (1.9,1.85,1.8), `RockDesat` .45, fade to mean colour 250-900 m.
  - Scree: `ScreeTile` 2400, `ScreeTint` .62. Snow: `SnowTile` 500, `SnowBright` 2.0. Shore: `ShoreTile` 350, `ShoreStart` .45, `WetDarken` .55.
  - Light: `ShadowDarken` .5, `BakedShadowStart` 20000 (fades in to 45000 so it does not double the CSM), `AOAmount` 1.
  - Canopy: `CanopyStart` 250000, `CanopyFull` 380000, `CanopyColor` (.03,.038,.022).
  - Surface: `Specular` .15 (.4 wet/snow), `MeadowRough` .92, `RockRough` .78, `SnowRough` .55, `DetailNormal` .8, `DetailFadeDist` 60000.
- `M_HLLake`: `RippleTile` 700, `RippleStrength` .35, `RippleSpeed` .25, `RippleFadeDist` 150000, `DeepColor` (.006,.02,.024),
  `GrazeColor` (.02,.035,.04), `NearRough` .03 → `FarRough` .09, `Specular` .35.
- `M_HLSky`: `Yaw` 0.398 turns for kloppenheim; .392 for industrial_sunset_02 and .401 for evening_road_01
  (formula in `SETUP_LOG.md` §5); `Exposure` .8. The SkyLight `source_cubemap_angle` = Yaw x 360.
- `M_HLFoliage` (two-sided foliage, masked 0.33): `Desaturate`, `TintA/B` (per-instance), `BaseDarken`, `Transmission`,
  `AlphaBoostMax` 2.2 / `AlphaBoostDist` 15000 (keeps far cards alive), `FadeStart/End` (per-instance thinning),
  static switch `Wind` (off: no WPO, so no velocity pass).
- `M_HLTreeFar` (opaque far LOD): `ColorA/B`, `ClumpScale` 260, `ClumpNormal` 2.2. `M_HLRock`: `Desaturate` .75,
  `Tint` (.36,.35,.34) basalt, `LichenColor`/`LichenAmount` .45 on up-facing.
- Lighting and fog (`scripts/env_params.json`): sun 11 lux (1,.56,.32), el 8, yaw -15; SkyLight .65; fog density .00019,
  falloff .0067 (scale height about 1.5 km), colour (.36,.42,.55), sun inscattering (1,.5,.25) exp 6 from 2 km; 2nd fog .0004 /
  .04 / offset -500 m; manual exposure 0; bloom .4; contrast and saturation 1.08. CSM 200 m (2 cascades) + baked terrain shadow beyond.

## Rebuild from scratch (all commands used; logs are in this folder)
```
P=proto2/highlands; py=python3 -P   # (-P: scipy is user-site; -I would hide it)
$py scripts/dem_build.py gen heights meshes water maps     # DEM fetch, 3 rings, tiles (glTF + LODs + skirts), lake mesh, maps
$py scripts/cams.py gen                                    # test cameras on the terrain
python3 -I scripts/prep_veg.py dl gen/veg                  # plants/trees to clean glTF (pivot, metres, slots), textures
VEG_LODS=1 venv/bin/python -P scripts/prep_veg.py dl gen/veg    # Tree It pine/juniper LODs (pyfqmr) + far LOD
VEG_PINEC=1 venv/bin/python -P scripts/prep_veg.py dl gen/veg   # Corsican pine + LODs + far LOD
$py scripts/scatter.py gen                                 # instance transforms + canopy map
UE=~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd; U=ue/Highlands.uproject; A="-unattended -nop4 -nosplash -nosound -nullrhi"
$UE $U -ExecutePythonScript=scripts/s1_import.py $A                      # textures, HDRI, 192 tiles (LOD merge), water
HL_ONLY=import,mat $UE $U -ExecutePythonScript=scripts/s3_veg.py $A      # plants/rocks import + foliage/rock/far materials
HL_ONLY=treelod  $UE $U -ExecutePythonScript=scripts/s3_veg.py $A        # tree LOD chains + far slot
HL_ONLY=mat,level HL_VEG=1 $UE $U -ExecutePythonScript=scripts/s2_level.py $A   # terrain/lake/sky materials + level + HISM
scripts/render.sh <tag> <cams>       # screenshots   | scripts/perf.sh <view>   # -game perf   | scripts/prof.sh <tag> "<sets>"   # ProfileGPU A/B
```
(The editor-Cmd segfaults at quit in this engine build after `quit_editor`, once everything is saved. This is harmless.)

## Integration notes for the lead (nothing applied to the game)
1. **Content**: migrate `/Game/Terrain/**` (192 tile meshes, 7 water meshes, 11 maps), `/Game/Env/Materials/**`, the used
   `/Game/Env/Layers` (aerial_grass_rock diff+nor, rocky_terrain_02 diff, lichen_rock diff+nor, aerial_rocks_01 diff+nor,
   snow_02 diff, river_small_rocks diff, T_MacroNoise), `/Game/Env/HDRI/kloppenheim_06_puresky_4k`, `/Game/Env/Veg/**`
   (SM_PineC, SM_Juniper, SM_Grass*, SM_Poppy*, SM_Daisy*, LODs, Tex) and `/Game/Env/Rocks/**`.
   The simplest route is to rerun the scripts against `Game/TwilightAssets.uproject` with ROOT paths changed. Disk use is about 600 MB uncooked.
2. **Spawning** (the game builds its maps procedurally). Either:
   - (a) build this level as `/Game/Twilight/Maps/Env/L_Env_Geghama` with `s2_level.py`, minus cameras and minus Sun/Sky/Fog/PPV
     if TwEnvironment keeps owning them. Then in `AVahagnGameMode::BeginPlay`:
     `bool bOk; ULevelStreamingDynamic::LoadLevelInstance(GetWorld(), TEXT("/Game/Twilight/Maps/Env/L_Env_Geghama"), FVector::ZeroVector, FRotator::ZeroRotator, bOk);`
   - (b) spawn in C++ from `gen/mesh/<ring>_layout.json` (tile name + location): one `UStaticMeshComponent` per tile with
     `MI_HLTerrain_<ring>`, `SetCastShadow(ring == core)`, mobility Static. Trees and rocks come from `gen/scatter/*.f32`
     into `UHierarchicalInstancedStaticMeshComponent` (`AddInstances(Transforms, false, true)`), using the cull distances from the table.
   - World origin = 45.10E 40.27N at lake level. X = east, Y = south. Vahagn spawn suggestion: lake300 view (9 km east,
     -2 km, +430 m), or over the incised valleys at (-5.5 km, 6.1 km, +1250 m).
3. **TwEnvironment values**: use the light, fog and sky values above. The terrain's baked shadow assumes sun az 255 / el 8.
   If the game moves the sun, rebake with `SUN_AZ/SUN_EL` in `dem_maps.py` (about 4 min), or set `ShadowDarken` = 1.
4. **Runtime grass** (needed for ground-level shots in Hayk/Aralez): load `gen/core_H.npy` (or export it as raw float16) and
   `T_core_Mask` on the CPU. Every 0.5 s, fill 16 m cells within 48 m of the camera using the same deterministic rules as
   `scatter.py` (`terrain_z` triangle-exact height formula, weight = lush/rock/snow/shore). Add or remove cell batches on one
   HISM per grass variant. About 4-6k instances are live, costing 0.5-1 ms.
5. **Wind**: `M_HLFoliage` `Wind` is off everywhere (perf). Turning it on for grass only (MI static switch) adds the velocity
   pass for those instances: about 1 ms when 4k clumps are visible.
6. **Collision**: core tiles use complex-as-simple collision (needed for the grass traces and character landing). Mid and far
   need none, so turn their collision off in the game.
7. **Hayk (built)**: second level `/Game/Test/L_Van`, made with the same scripts and `HL_SITE=van`
   (`HL_CLON=43.25 HL_CLAT=38.52 HL_LAKE=1647`, data in `gen_van/`, content in `/Game/Terrain_van`, MIs `MI_HLTerrain_*_van`).
   It is the east shore of Lake Van (Van plain, Erek/Varak hills, Süphan in the mid ring, Masis 160 km away in the far ring).
   No pines (the area is steppe), but it has rocks, junipers and grass. Screenshots: `shots/FINAL_van.jpg`.
   Commands: `HL_SITE=van ... s1_import.py`, then `HL_SITE=van HL_ONLY=mat,level HL_VEG=1 ... s2_level.py`.
8. **Aralez / others**: the same pipeline is site-agnostic. `HL_CLON/HL_CLAT/HL_LAKE` env vars recentre it.
   For Aralez (Ara vs Shamiram) use the Ararat plain, about 44.35E 40.05N, with `HL_LAKE` about 850
   (no lake; Z = 0 near the plain) and `N_PINE=0`.
