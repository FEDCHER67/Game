# G24 tall grass staging

Complete source set: `v01/ThirdParty` -> `Assets/OnlyVolunteers/ThirdParty/GrassInstancer_MB`; `v01/Grass` -> `Assets/OnlyVolunteers/Map/Grass`.

1. Compile source-only with `python ArtSource/Dev/Grass_staging/compile_staging_v01.py`.
2. Acquire Unity exclusively using the user-provided G24 lock script (32-minute outer timeout). Do not import while another worker owns Unity. Refresh within 20 minutes.
3. Through the existing Coplay bridge, check exact project/version and stopped Play state. Pause AssetDatabase imports, run `install_new_only_v01.py`, then resume imports in a finally path. The installer refuses existing destinations and checks G24 ownership.
4. Confirm Unity C# and shader errors, then call `OnlyVolunteers.Map.Grass.Editor.GrassVerification24.GpuCulling()`.
5. On the latest approved v19 look scene, call `GrassPlacement24.Build("v01")`. It creates a new scene revision, 3-triangle blade asset, grass material and compact immutable binary placement dataset. It never changes TerrainData, low tufts, sky, render assets or ProjectSettings.
6. Open the corresponding v19 Play source scene; call `GrassPlacement24.AttachPlay("Assets/OnlyVolunteers/Map/Grass/Baked_v01/GrassData_v01.asset","v01")` only after matching terrain and geometry sources.
7. `GrassVerification24.Placement("v01")` validates every blade against the hard-surface mask and validates chunk coverage/heights/bounds, plus stratified water/ground samples.
8. Capture five exact before/after poses and six fixed wind times with `GrassReview24.Shot`; originals and metadata stay in Working/Reviews/Grass. Assemble them with `make_review_sheet_v01.py`.
9. During Play, `GrassReview24.StartPerformance` takes 60 warm-up + 180 ordinary frame samples for Hamlet without/with and hills without/with. No background-setting or quality-setting edits. It restores camera enabled states and removes only its temporary runtime object.
10. Stop Play, save the new scene revision, restore the initial active scene, release Unity, finish the English report and run the required G24 review bridge. At most two fix rounds.

Assumptions to carry into the report:
- Use approach 3's finite 16 m chunks + GPU frustum/distance culling. Upstream depth occlusion is not conservative/mipmapped, so it is omitted pending evidence rather than risking vanishing clumps.
- View distance 150 m with the final 20 m shrinking into the preserved short layer. Tall grass receives URP fog and writes opaque depth for G18's depth-based atmosphere. Actual G18g compatibility must be checked after handoff.
- `village` = Hamlet; `fields` = Quiet Valley; `transition` = construction district; `residential` = Rough District; `old_town` = Downtown.
- Quiet Valley/Elite interiors are trimmed; tall rough outer edges occupy the outer 18 m of their actual district bounds. Forest uses meadow splats outside tree canopy cells. Sparse dune grass occupies dry terrain above water. Construction/Port/island grass is conservatively sparse.
- Full-density patches are separated by 20 m macro noise and smaller open pockets; road clearance selects 0.10–0.25 m short grass, meadow heights are 0.50–0.90 m. Dry clumps are 0.22–0.48 m and dunes 0.28–0.55 m.
- Rendering is local presentation only, with no network authority and no colliders. Optional player/van bending is omitted.
- The CPU shader compiler evidence does not prove GPU compilation, visual quality, acceptable performance, or successful Unity integration.

The upstream source was treated as data and never executed. Only this scoped port is eligible for Unity import. No downloaded model/image asset is used.
