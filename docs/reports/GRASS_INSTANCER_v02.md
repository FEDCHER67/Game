# G24 — grass #02 integrated into v19 i02

2026-10-14, 17:17 Moscow. Complete. This report supersedes the pre-integration staging report `GRASS_INSTANCER_v01.md`.

## Delivered

- Scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i02_grass.unity`, derived directly from the chain's i01 trees scene, without rebuilding the map.
- Renderer, compute shader, grass shader and MIT notice: `Assets/OnlyVolunteers/ThirdParty/GrassInstancer_MB/`.
- Placement, review tools and final dataset: `Assets/OnlyVolunteers/Map/Grass/`; the scene uses **Baked_v04**. Earlier diagnostic bakes remain preserved and are not referenced by the final scene.
- Review sheet: `Working/Reviews/Grass/grass_v01.jpg`. Five matched before/after views and six wind frames are actual paused-Play renders at 1600×900. `capture_manifest_i02_v01.json` identifies the source images; the Rough pair uses v02.
- Source/staging/provenance: `ArtSource/Dev/Grass_staging/` and `ArtSource/ThirdParty/MangoButtermilch_GrassInstancer/v01/`.

Pinned upstream: https://github.com/MangoButtermilch/Unity-Grass-Instancer, commit `f5983739d6159dbad115950e9ac349a1dd44e78e`. **MIT**, copyright 2022 MangoButtermilch; full notice retained. All 234 extracted files matched the pinned archive. Upstream was treated as data; no upstream program, model or texture was executed/imported.

## Layer and assumptions

Approach 3 port: 16 m chunks, conservative GPU frustum/distance culling, indirect indexed drawing, three triangles per broad tapered blade. **3,642,380 blades / 4,259 chunks**; 150 m draw distance, final 20 m shrink-out, root-to-tip district palette and travelling gusts (strength .24, speed 1.25). Occlusion culling and optional character bending are omitted. No grass colliders or network/gameplay owner were added.

Meadows are .50–.90 m, roadsides .10–.25 m, trimmed lawns .12–.24 m, Rough clumps .22–.48 m and dunes .28–.55 m. Irregular patches preserve open pockets. Existing terrain textures, all five low-grass prototypes, G23 trees and TerrainData remain unchanged. Opaque depth and matching depth-normal deformation let the existing G18g camera-scoped aerial pass cover grass; the captured hill/Rough views show it within the existing atmosphere.

Exclusions use actual road/paving meshes, relocated building footprints, hard yards, water-height tests and eight approved passing van routes (2 m corridor half-width plus raster clearance). Deliberately blocked shortcut tests are excluded from the route input. The giant sea mesh extends under dry land, so its raw triangles are not used as a land mask. Ground below Y=0 can be dry; the map's water test decides. Downtown's plan parks currently fall under existing paving exclusions, so **no new grass is placed there**; shared city geometry was not changed. Beach's existing green ground texture is also retained.

District counts: Hamlet 138,431; between districts 3,389,217; Rough 6,040; Beach 5,309; Forest clearings 783; Quiet Valley 20,686; Elite 48,762; Construction 8,973; Port 2,400; Tramduro 21,779.

## Verification

- **PASS — Unity 6000.5.11f1 / URP 17.5:** C# compiled; final shader supported with zero errors; Console errors zero before and after Play. Missing scripts zero in Edit and Play. Final source-only compilation also passed (`ArtSource/Dev/Grass_staging/evidence/compile_final_i02_v01.txt`).
- **PASS — SRP Batcher:** globally enabled throughout. Shader compatibility code 10 confirms this grass shader alone opts out through its material constant buffer. Evidence: `shader_status_i02_final_v01.txt`.
- **PASS — actual GPU culling:** camera inside a giant chunk, off-axis/behind/distant rejection, exact partial chunk tails and no duplicate IDs. Returned IDs 0,1,5,6 (`gpu_culling_i02_v01.txt`).
- **PASS — placement:** all blades checked against hard masks, heights, payload/chunk coverage and world bounds; 191,705 water/ground samples, zero violations, zero measured ground error. Evidence: `placement_audit_i02_final_v04.txt`.
- **PASS — ordinary Play and movement:** 4,891 frames observed in the benchmark/capture run. Existing route harness separately completed the Hamlet van route (137.5 m driven, maximum 43.7 km/h) and orchard walk (111.5 m). A chassis-ground touch at the starting position was logged without route failure; terrain was not changed. Harness results: `Working/Reviews/Map_v19_Pilots/routes_g24_i02_v01.json`; crowds/police are suppressed by that existing harness for repeatability.
- **PASS — preservation:** hashes of 1,594 protected files match, including i01, G23 assets/TerrainData, atmosphere, ProjectSettings and PC_RPAsset. Scene comparison adds exactly one grass GameObject, its Transform/component and a SceneRoots entry; no existing object block changed. All new asset metas exist (`integrity_i02_v01.json`).

Live Play timings on RTX 5070 Ti, 1469×719, 60 warm-up + 180 measured ordinary frames per cell (`performance_i02_v01.json`):

| View | Median ms, off → on | p95 ms, off → on | GPU median ms, off → on | Visible / candidate chunks |
|---|---:|---:|---:|---:|
| Hamlet | 4.777 → 4.803 | 6.978 → 7.057 | 1.148 → 1.266 | 48,886 / 92 |
| Between districts | 19.710 → 19.859 | 21.923 → 22.246 | 14.287 → 14.391 | 40,453 / 87 |

No frame-time collapse was observed. These short Editor measurements include existing gameplay/workload; they are not a standalone-build benchmark or a statistically established sub-millisecond cost. Normal rendering performs no synchronous GPU readback.

## Handoff

Play is stopped; **i02 is saved and active**. Both background settings stayed false. No global rendering change, map rebuild, commit, deletion, WORK_SYNC edit or review bridge. The current integration protocol explicitly supersedes the old bridge instruction.

The look builder is unchanged. After a future v19 rebuild, run `GrassPlacement24.Build` on the finished terrain/trees into fresh baked and scene revision paths; update the approved corridor snapshot if routes change. It refuses an existing grass layer or existing output. Final look acceptance remains with Fedya; multiplayer and other GPUs are not tested.
