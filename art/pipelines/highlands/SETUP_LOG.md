# Highlands environment prototype: setup log (scratch only; /var/www/html/Twilight is untouched)

## 1. Site choice (DEM)
- AWS/Mapzen terrarium tiles (no login). Overview z10 of 43.9-45.6E / 39.55-40.65N (`gen/dem/overview_col.png`, blue = below 1900 m).
- Chosen centre 45.10E 40.27N: the Geghama ridge with **Azhdahak** (3597 m, "dragon" volcano; vishap stones lie at its lakes) descending
  east to the west shore of **Lake Sevan** (DEM surface 1898.0 m). Masis/Ararat is 93 km SW and Aragats is NW, both in the far ring.
- Three nested regions (`scripts/dem_build.py`): core 30 km at 18.75 m (z12 + slope-weighted detail noise), mid 120 km at 100 m (z11),
  far 360 km at 400 m (z9). Each ring has the inner 2x2 tiles removed. Curvature is applied with refraction (R_eff = 7/6 R), so Masis
  sinks about 580 m as it does in reality.
- Fixes: lake = flat (|H-1898|<1, 3x3 range < 1.5 m) components > 2 km^2, holes filled, bed carved to 45 m depth with a 700 m shelf.
  SRTM 1-degree seams at 45E/40N (5-10 m steps) are blurred in a 250 m band.
- Run: `python3 -P scripts/dem_build.py gen heights meshes water maps` (about 1 min with cached tiles; the first fetch took about 10 min).

## 2. Baked maps (`scripts/dem_maps.py`)
- World-space normal maps: core 4096 (DEM + micro relief), mid 4096 (z12 DEM), far 2048 (z10).
- Mask RGBA = rock / scree / snow / lush, from slope, curvature, elevation, aspect, D8 flow accumulation and noise.
- Light RGBA = baked sunset sun visibility (sun az 255, el 8, curvature-aware horizon march across all rings) / sky visibility (AO) /
  stream channels / shore band.
- Iteration 1: rock mask was empty in the core (thresholds 27-40 deg; the DEM-smoothed Geghama slopes are < 25 deg).
  Re-tuned to 19-31 deg plus crest boulder fields above 2950 m. Snowline set to 3150 m.

## 3. Assets (licences in README)
- Poly Haven CC0: kloppenheim_06_puresky (sun el 8.0, u 218 deg), aerial_grass_rock, lichen_rock, aerial_rocks_01, snow_02,
  river_small_rocks, + rocks rock_07/09, namaqualand_boulder_02/05, boulder_01, stone_01.
- Poly Haven trees are scan-grade (fir_tree_01 7.8M tris, pine_tree_01 17M) and unusable without Nanite. Instead, CC-BY via the
  Objaverse HF mirror: evolveduk "Pine Tree" (5.6k tris, Tree It), "Juniper" (2.6k); 3dhdscan "Simple grass chunks" (scanned cards);
  emarshall "Plants Asset Set" (grass, poppies, daisies). Copernicus GLO-30 is not public for Armenia (404), so terrarium is used.

## 4. UE import (scratch project ue/Highlands.uproject, content-only, game renderer settings + game DefaultScalability)
- s1_import.py: 192 tiles, about 8 s each. Interchange (no Nanite, no materials), then L1..L3 merged via set_lod_from_static_mesh,
  screen sizes 1.15/0.58/0.29 (core) and 1.1/0.55 (mid/far), full-precision UVs, no lightmap UVs. The water mesh is 7 chunks (33k quads, 200 m cells).
- Incident: /tmp (root fs) hit 0 bytes free during the run (the disk is shared; 98-99% used). Deleted my project DDC and kept logs
  small. ~/.config/Epic/.../Editor/*.json became empty (written while the disk was full); this is harmless, they are regenerated.
- UnrealEditor-Cmd -nullrhi segfaults at quit (ModeManagerInteractiveToolsContext not packaged) AFTER the script saved everything; ignore.

## 5. Render t1 (shots/t1.jpg): already reads as real terrain; problems found
- Isotropic ridged detail noise rendered as smeared streaks plus regularly spaced "moguls". Replaced with downslope-elongated rills
  (6:1 anisotropic value noise along the smoothed fall line) plus 0.9 m hummocks, applied AFTER the lake test (v1 noise made dry specks in Sevan).
- Rock layer read as a dark blue-grey grid: lichen_rock mean albedo is only 0.049 (measured), so tint is now 1.9, tile 11 m, plus a 2nd
  rotated scale blended by macro noise.
- Grazing-angle sheen on grass: specular 0.35 -> 0.15. Baked shadow darken 0.35 -> 0.5, faded in from 200-450 m.
- Added the real aerial photo rocky_terrain_02 (90 m scan) as a luminance overlay on the meadow for 1-50 m patchiness.
- HDRI yaw solved analytically from TextureCompressorModule LookupLongLat (u = (1+atan2(X,-Y)/pi)/2): sun at u=218.4 deg means
  material Yaw 0.398 turns. The sky probe toward yaw 165 confirms the sun sits there.

## 6. Vegetation (t3-t11)
- t3: trees/rocks invisible. Mesh path was wrong (Interchange puts assets at <dest>/<name>/StaticMeshes/<name>). Grass was too
  green and sparse.
- t4: UE auto reduction deletes leaf cards, so distant pines became bare sticks. Fixed with own LODs: pyfqmr on the trunk only,
  leaf cards thinned by area and enlarged (venv in proto2/highlands/venv, since system pip is blocked by PEP 668).
- set_lod_from_static_mesh maps every section of LOD>=1 to slot 0, so leaves rendered with bark. Re-mapped with set_lod_material_slot.
- Masked alpha mip-averaging made far leaves vanish. Added `AlphaBoostMax`/`AlphaBoostDist` (opacity x up to 2.2 with distance).
- Far LOD = lathe of the real crown profile (80th-pct radius per height bin, 9 sides, alternating whorl rings, jitter), opaque
  `M_HLTreeFar` with noise "needle clump" normals, separate 'Far' material slot. Reads as conifers at 100+ m (t11).
- Tree It pine replaced by emarshall's Corsican pine (denser, darker crown) with LODs 46k/21.7k/15.3k/309.
- Pines clustered into plantations (700 m noise > 0.66 x 90 m glade noise); 45k trees.

## 7. Performance work (ProfileGPU sequencer `scripts/prof.sh`, -game CSV `scripts/perf.sh`)
- -game meadow v1: 43 fps, GPU 19 ms. RenderVelocities 3.9 ms (WPO wind on all foliage) -> static switch `Wind` off.
- Editor A/B (hide groups): grass about 0-1 ms, rocks about 0.3 ms, pines 4.6 ms (thousands of masked distant trees).
  -> opaque far LOD at about 120-180 m, tree cull 3.8-4.2 km, canopy map painted by the terrain beyond (T_core_Canopy) -> about 1.3 ms.
- r.DBuffer=False tested: no measurable change (reverted). Editor overhead about 1.1 ms (ElementBatch).
- -game final (GPU free of other editors during these runs): meadow 72 fps (GPU 12.2 ms), grove 79.5 fps (GPU 10.9 ms); see README.

## 8. Final passes
- -game final: meadow 72.3 fps (GPU 12.2), grove 79.5 (10.9), lake300 95.8 (8.8), over1500 70.0 (12.4). The GPU was free of other
  editors in these windows; best and worst segments were equal.
- Sky comparison (kloppenheim_06 / industrial_sunset_02 / evening_road_01): kept kloppenheim for its clouds and sun rays.
  Fog density reduced to 0.00019 with a bluer colour; sky exposure 0.8.
- Meadow texture rows visible from 300 m on flat ground (Van plain) -> 3 scales at different rotations (11/47/-29 deg).
- Grass mix biased toward dry clumps (green probability = lush x 0.55).
- Lake Van (Hayk) built with the same scripts and HL_SITE=van: gen_van (core 52% lake, land 1647-2331 m), /Game/Terrain_van,
  level /Game/Test/L_Van, no pines, plus rocks/junipers/grass. Renders shots/van2.jpg.
