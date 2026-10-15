# G23 — approved leafy trees, i07

2026-10-15, Moscow. Integrated Fedya's approved set into `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i07_leafy_v04.unity`, based on the saved i06 scene. No map rebuild, commit or review bridge.

## Delivered assets and counts

New runtime folder: `Assets/OnlyVolunteers/Art/Trees/Leafy_v04/`. It contains exactly 12 approved FBXs, 12 prefabs, 36 derived meshes with the FBX axis conversion baked, 16 shared-wind materials, and a separate i07 TerrainData. Apple/Palm/Bush use **v04_03**; Poplar uses **v04_04**. No unpicked leafy iteration was imported or selected.

| Type | Before → after | A / B / C after | LOD0 / LOD1 / LOD2 triangles per variant |
|---|---:|---:|---:|
| Apple | 243 → 243 | 86 / 79 / 78 | 5,276 / 2,988 / 1,678 |
| Poplar | 999 → 999 | 326 / 327 / 346 | 6,496 / 3,716 / 2,378 |
| Palm | 47 → 47 | 17 / 7 / 23 | 3,806 / 2,610 / 1,582 |
| Bush | 1,949 → 1,949 | 626 / 670 / 653 | 1,916 / 1,176 / 806 |

Apples comprise 242 Terrain instances and one ordinary garden prefab. All **758 former birch positions now use approved poplars**, and all **four garden/orchard birch positions use approved apples**. Total Terrain instances remains **8,525**: 3,237 replaced and 5,288 retained exactly. This includes untouched Forest v03 conifers, happykeys bare trees, other non-target trees and the existing rock placement.

Seed **230407** selects A/B/C, yaw and one uniform scale in **0.9–1.1**. Scale is relative to the approved model's native metre dimensions; old placeholder height/width distortions are not carried forward. Every original world pivot and Terrain colour/lightmap colour is retained. Maximum measured replacement-pivot error against terrain is **0.00000191 m**. No terrain height, layer, detail, density or ground-contact repair was performed.

Each prefab has three LODs and a cull threshold. Two simple static capsules follow each tree's lower trunk; bushes have no collider. The imported FBX's Z handedness was verified against the geometry and applied to the staged capsule centre/axis coordinates; capsule radii/heights remain the authored values. New derived mesh bounds include conservative wind displacement; LOD thresholds compensate for that padding.

## Shared wind and rendering

All 16 material copies retain the approved `WindMaterials/*_v04_03.mat` settings and use the existing `OnlyVolunteers/Wind/v02/GenericFoliage` shader, which includes G24's original `V19Wind.hlsl`. No new wind shader, per-model deformation code, global wind setting or global URP setting was introduced. Exactly one existing `V19Wind` remains in i07.

Per-type response / stiffness height: Apple **0.13 / 2.5 m**, Poplar **0.075 / 8 m**, Palm **0.18 / 6 m**, Bush **0.22 / 0.7 m**. Connected foliage and bark slots share the same field/profile, keeping the base pinned and lower trunk nearly still. GPU instancing is enabled. Opaque folded leaves cast/receive shadows, write depth in matching wind passes, receive URP fog, and participate in the existing depth-based aerial perspective. The foggy poplar comparison visibly shows distant crowns fading into the horizon.

## Verification

- **PASS — import/prefabs:** `G23LeafyIntegration.BuildAssets()` compiled and built the 12 prefabs. All 36 LODs checked for metre height/base pivot, material coverage, triangle counts and wind bounds. All selected FBXs are byte-identical to their approved ArtSource exports.
- **PASS — instance integration:** `G23LeafyIntegration.Validate()` checks all 8,525 old/new records, selected revision paths, variation ranges, ground contact, retained prototypes, LODs, collider counts and shadow flags. Zero missing scripts, invalid materials or shader errors. Evidence: `Working/Reviews/Trees/i07/integration_validation.json`, `replacements.json`, `asset_validation.json`, `birch_lineage_check.json`.
- **PASS — initial Play checks:** orchard walk and van, poplar-road walk and van, Beach walk and van, and garden walk arrived. The full garden van line stopped beside the apple trunk/tree swing; its baseline comparison and driveway-access check are recorded below.
- **PASS — actual wind captures:** 32 frames over four seconds in the Hamlet orchard, with the shared wind advancing and the lighting held at 08:00. The crown-area image difference confirms visible motion; branches/leaves and their shadows move through the actual map shader.
- **Preservation:** original i06/earlier scenes, approved ArtSource, old dependencies and ProjectSettings are protected by a 1,756-file SHA-256 manifest. No global asset save was used. Final check is recorded in `protected_final_check.json`.

Route evidence: `Working/Reviews/Map_v19_Pilots/routes_g23_i07_v01.json/.txt`; input is `Working/Reviews/Trees/i07/routes_input_v01.json`. The existing `V19PilotTools.StartRoutes` harness drives the real van and walks the KCC player by inputs, using its deterministic Play stepping. It records chassis/ground contact even on completed routes; arrival is not a claim of perfect terrain clearance. No player/vehicle tuning was changed.

## Performance against i06

RTX 5070 Ti, actual named Play scenes, matched 1280×720 HDR cameras, 08:00, 120 warm-up + 240 normal frames per view. Grass visibility counts match in all four pairs. These are whole-scene **Editor** measurements, not isolated foliage cost or shipping FPS.

| View | Median FPS i06 → i07 | Median frame ms i06 → i07 | Median GPU ms i06 → i07 | GPU delta |
|---|---:|---:|---:|---:|
| Hamlet orchard | 125.0 → 118.3 | 8.00 → 8.45 | 3.781 → 3.897 | +0.116 ms |
| Poplar road | 100.1 → 101.5 | 9.99 → 9.85 | 6.190 → 5.224 | −0.966 ms |
| Beach palms | 228.3 → 226.2 | 4.38 → 4.42 | 2.437 → 2.477 | +0.039 ms |
| Garden bushes | 193.2 → 150.7 | 5.18 → 6.64 | 2.314 → 2.388 | +0.073 ms |

Largest measured total-frame increase is **+1.46 ms in the garden**; its p95 rose from 7.35 to 10.80 ms. The small GPU increase there does not establish the cause of the larger CPU/frame difference. Raw data and deltas: `Working/Reviews/Trees/i07/performance_i06.json`, `performance_i07.json`, `performance_comparison.json`. These completed runs use identical cameras between revisions. The Beach benchmark camera is the original (844,225) pose; the final sheet uses the improved dry-land (846,217) pose. An optional later resample stalled when Unity lost foreground and was stopped; it is excluded. Neither background-running setting was touched.

## TerrainData dependency audit — no repair

**i07 is not currently affected by the missing-reference condition described in the i04→i05 chain note.** Both live Unity references and the corresponding on-disk assets/metas were checked:

| Revision | TerrainData asset | GUID | Resolved layers / tree prototypes / detail prototypes |
|---|---|---|---|
| i06 | `Assets/OnlyVolunteers/Map/Wind/Trees_v01/Terrain_v19_i06_wind.asset` | `debb903a685c03441a7864077fb3d851` | 16 / 24 / 5 |
| i07 | `Assets/OnlyVolunteers/Art/Trees/Leafy_v04/SceneData/Terrain_v19_i07_leafy.asset` | `6342192943b9e4a4997b028ba1be19f6` | 16 / 36 / 5 |

**Missing layers: none. Missing tree prototypes: none. Missing required detail prototypes: none. Missing diffuse textures for terrain layers: none.** The five detail prototypes use meshes; empty optional texture fields are expected. i07 retains the same 16 layers and five detail prototypes, and appends 12 approved tree/bush prototype slots to the original 24.

Every individual slot, asset path and GUID is listed in `Working/Reviews/Trees/i07/terrain_audit_i06.json` and `terrain_audit_i07.json`; texture references are in `terrain_layer_textures.json`. The historical G24 report named `Assets/OnlyVolunteers/Art/Trees/v03/SceneData/Terrain_v19_i01_trees.asset`, GUID `9b09c90b1fda6eb498b926723b2614e3`. This task did not repair or modify that earlier asset or infer when its missing dependencies were restored.

## Review files and reproduction

- Sheet: `Working/Reviews/Trees/leafy_v04_in_map_i07.jpg` — four places, actual i06/i07 Play renders at identical cameras and lighting.
- Wind GIF: `Working/Reviews/Trees/leafy_v04_wind_i07.gif`.
- Final capture selection: `Working/Reviews/Trees/i07/capture_manifest_final.json`; earlier diagnostic stills are preserved but excluded.
- Import/build/review source: `ArtSource/Dev/Trees_staging/i07_v01/`. Unity entry points: `G23LeafyIntegration.BuildAssets`, `Integrate`, `Validate`, `AuditTerrain`; review helpers are temporary and are not saved as scene components. The map builder is unchanged; a future rebuild must explicitly select these approved prefabs/materials and the same replacement rules.

## Final handoff

- **PASS — garden access:** the 36 m driveway approach arrived in both i06 and i07 (32 m driven, 7.8 s). The full 54 m garden line failed at the same position, (290,520), in both scenes, against the original/replacement apple and unchanged tree swing. This existing terminal blockage is reported, not repaired. Evidence: `routes_g23_i06_garden_v02.*` and `routes_g23_i07_garden_v02.*` under `Working/Reviews/Map_v19_Pilots/`.
- **PASS — final saved/reopened i07:** Play stopped, scene clean, compilation idle, zero missing mesh/material/script references, zero temporary benchmark components, one shared wind owner, and zero fresh Console errors or warnings. Earlier project-wide obsolete-API compilation warnings were not changed by this task. `Working/Reviews/Trees/i07/final_scene_check.json` records the readback.
- **PASS — preservation:** all 1,756 protected files are unchanged, including i06 and earlier scenes; all 12 imported FBXs match their approved source hashes. The review sheet and 32-frame GIF were opened/inspected, and the scene chain was appended.
- Open: the existing garden endpoint obstruction and the measured +1.46 ms garden frame-time increase above. No TerrainData dependency repair is required by the current i07 audit. No commits or review bridge. Unity lock released after the final checks.
