# G23 — approved Forest conifers integrated into v19 i01

2026-10-14, 16:52 Moscow. Integration is complete; Play is stopped and the new scene is saved.

## Result and paths

- New scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i01_trees.unity`, derived directly from the chain's `Map_Look_v19_Play.unity`.
- Complete art set: `Assets/OnlyVolunteers/Art/Trees/v03/` — four approved v03_04 FBX files, original needle RGBA texture, v03 shader/include, 12 upright mesh assets, 16 instanced materials and four capsule/LOD prefabs. See `README_INTEGRATION_i01.md` there for material and wind settings.
- New TerrainData: `Assets/OnlyVolunteers/Art/Trees/v03/SceneData/Terrain_v19_i01_trees.asset`.
- Six-view comparison: `Working/Reviews/Trees/forest_v03_in_map_v01.jpg`. Original captures, camera manifest, three Play wind samples and verification records: `Working/Reviews/Trees/i01/`.
- Repeatable, explicit editor tooling: `Assets/OnlyVolunteers/Art/Trees/v03/Editor/G23ForestIntegrationV03.cs`; matching source under `ArtSource/Dev/Trees_staging/v03/Integration/`.

Replaced **1,042 Forest conifers** inside x=127.4–346, z=81–315.2, preserving every position. Counts: Spruce A 243, Spruce B 278, Fir 254, Young 267. Seed 230304 determines variant, yaw and uniform 0.9–1.1 scale. Assumption: jitter applies to the approved native 6–9 m models, rather than retaining the old trees' additional scale spread. The other **7,483 trees**, including roadside deciduous and Rough District bare trees, retain all public instance fields exactly.

## Checks

- Unity 6000.5.11f1 / URP 17.5: compilation passed, wind shader errors zero, Console errors zero, missing scripts zero in Edit and Play.
- Imported model heights and all 12 triangle counts match the approved source. Fronds use cutoff 0.5, coverage-preserving mipmaps and GPU instancing. The instanced alpha-test shader variant warmed successfully; this is a functional check, not a GPU timing benchmark.
- Three matching before/after views show cutout fronds and distant crowns fading into the existing Forest fog/aerial perspective. Forward, shadow, depth and depth-normal passes share wind and alpha clipping; depth writing remains enabled.
- Paused-Play samples at wind times 12/13.5/15 s show movement with all other clocks frozen. The capture override was restored to zero. Each variant's native Terrain trunk collision was hit at the expected scaled capsule radius: 0.273/0.257/0.241/0.185 m in the sampled instances.
- Existing route harness: van Hamlet loop **ARRIVED**, 172.6 m driven, maximum 42.8 km/h; player orchard passage **ARRIVED**, 111.5 m walked. The van recorded a chassis-ground contact at (320,486), without failing the route; this terrain was not changed. Crowd/police were temporarily suppressed by that harness during its repeatable route checks.
- All 1,050,625 terrain height samples, terrain size and layer references match the source. Protected-file hashes match for the base scene, original TerrainData, ProjectSettings and PC_RPAsset (30 files). Scene differences are the two TerrainData references plus Unity reserializing an unused light bounding-sphere value whose override is disabled.

## Handoff / open items

No map rebuild, global rendering change, original deliverable overwrite, commit or review bridge. No blocking issue remains. Existing legacy bare-tree shader advisories and capture-helper render-texture warnings are outside this change.

The look builder was not modified. A future v19 rebuild must append these four prefabs after final terrain tree placement and apply the same Forest-only predicate, position-preserving replacement, seed and scale rule to a **new** TerrainData and scene revision. The editor integration method documents that operation and refuses existing output paths; choose fresh revision paths before reuse. Continue this integration round from **i01**, not the original v19 base.
