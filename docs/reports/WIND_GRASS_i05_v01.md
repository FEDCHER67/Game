# G24 — generic shared wind, i05

2026-10-14, Moscow. **Wind implementation PASS; inherited terrain dependencies need lead repair.**

Saved scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i05_wind_grass.unity`, based on i04 vanpaint. Density cancellation was applied throughout: **3,642,380 blades / 4,259 chunks**, the same v04 mesh, data, 116,556,160-byte payload, placement and compute culling. No new grass bake.

## Changes

- `Assets/OnlyVolunteers/Map/Wind/v01/Runtime/V19Wind.cs`: one shared owner; direction, travelling gusts, turbulence, calm/breezy/stormy presets, and blended district strength. The small district lookup texture is generated in memory; it is not a model or placement bake.
- `Shaders/V19Wind.hlsl` under that folder: generic height-above-pivot bend, radial flutter and optional vertex-alpha flexibility. No required UV layout, vertex colour, bones or model-specific data.
- `Shaders/GenericFoliageWind_v01.shader`: ordinary foliage material, instancing variants, shared deformation in forward/shadow/depth/depth-normal passes. Automatic ordinary-renderer bounds padding handles uneven scales and restores bounds when the material is removed.
- `Shaders/IndirectGrassWind_v01.shader` and `Materials/TallGrass_SharedWind_v01.mat`: first map consumer, with lighter bending tips and the existing palette, fog, visibility distance and GPU culling preserved.
- `Materials/GenericGrassWind_v01.mat`, `GenericFoliageWind_v01.mat`, `GenericBushWind_v01.mat`: reusable presets. New review helpers are in `Editor/` and `Runtime/WindPerformance24.cs`; none is saved as a running scene helper. Source/evidence staging: `ArtSource/Dev/Grass_staging/Wind_v01/`.

Breezy uses 8° base + 32° gust, capped at 45°, 40 m travelling bands at 8 m/s. Multipliers: Hamlet .95, Forest .55, Rough 1.20, Beach 1.15, open land 1.12, blended using the district data. Trees retain their existing materials for G23's next integration. The unchanged short-detail layer cannot currently render because its inherited prototypes are missing.

## Checks

All checks used Unity 6000.5.11f1 through the existing unityMCP bridge.

| Check | Result / evidence |
|---|---|
| Live compilation / shader support | PASS; both shaders supported, zero shader errors. Generic SRP compatibility code 0; indirect grass intentionally opts out locally (code 10); global SRP Batcher remains enabled. |
| Actual GPU deformation | PASS: `WindIntegration24.GpuProbe()`; 8.000° rest, 40.000° gust, 8 m tree fixture tip movement .558 m; pivot/ground/zero-mask vertices pinned. |
| Generic material without mesh preparation | PASS: ordinary built-in capsule meshes, no vertex colours, all four passes compiled and forward rendering captured; `generic_material_fixture_v01.txt`. |
| Uneven-scale culling bounds | PASS: `V19Wind.RefreshModelBounds()`, 8,800 displaced test vertices, thin (.02,4,.02) scale and rotated uneven parent; no cumulative growth; bounds restore correctly. `nonuniform_bounds_v01.txt`. |
| Existing GPU culling | PASS: `GrassVerification24.GpuCulling()`, exact visible IDs 0,1,5,6. Max current grass displacement stays within the existing chunk padding; `grass_culling_envelope_v01.json`. |
| Play walk / van | PASS: `V19PilotTools.StartRoutes(i05,"g24_i05_v01",null,"../Grass/route_input_i02_v01.json")`; walked 111.5 m; van drove 137.5 m, max 43.7 km/h. Existing chassis-ground contact was recorded at (320,486), with no airborne frames. `Working/Reviews/Map_v19_Pilots/routes_g24_i05_v01.json`. |
| Final scene | PASS: saved, Play stopped, exactly one wind owner, zero missing scripts across 25,315 objects, clock restored to running at 08:00, zero fresh Console errors. |
| Preservation | PASS: `python ArtSource/Dev/Grass_staging/Wind_v01/evidence/final_integrity_v02.py`; all 912 retained protected files match their pre-wind hashes. Scene diff is only the grass material reference and the new V19Wind object/root. |

Evidence above is in `Working/Reviews/Wind/` unless another directory is given. One old renderer buffer-binding error occurred during import; it was recorded in `import_console_baseline_v01.json`, then resource recreation recovered it. It did not recur in the Play checks. Frame Debugger inspection was NOT RUN; no claim of a captured event-by-event pass audit.

## Frame time

Final ordinary Play run: `WindIntegration24.StartPerformance("i05_v04")`, RTX 5070 Ti, 2560×1248, fixed 08:00 lighting, 60 warm-up + 180 measured frames per cell. Original material → shared wind, with identical grass counts.

| View | Median frame ms | p95 frame ms | Median GPU ms | Visible blades |
|---|---:|---:|---:|---:|
| Hamlet | 4.845 → 4.993 | 6.720 → 6.923 | 4.452 → 4.560 | 51,483 |
| Between districts | 17.681 → 17.853 | 19.116 → 19.621 | 13.864 → 13.934 | 40,533 |

Evidence: `performance_i05_v04.json`. These are short Editor measurements of the currently loaded map, including gameplay overhead; repeat after restoring the inherited vegetation. v01 is INVALID (no benchmark-camera buffers), v02 used a small window, v03 is a supporting full-size run before the bounds fix. The helper now rejects duplicate/early runs and an incorrect starting material.

## How to add wind to a new model — 3 steps

1. Duplicate the appropriate **GenericGrassWind**, **GenericFoliageWind** or **GenericBushWind** material from `Assets/OnlyVolunteers/Map/Wind/v01/Materials/`. Use a model with local Y up; if its origin is not at its base, set the material's **Local base pivot offset**. No bake or vertex painting is required.
2. Assign it to the model's renderer/submeshes, then set its texture/tint and optional alpha cutoff. Start with Wind response **1 / .10 / .22** for grass/tree/bush and tune Root stiffness height. Existing vertex RGB tint or alpha flexibility can be enabled optionally.
3. Keep exactly one **V19Wind** in the scene (i05 already has it), choose **Breezy**, and press Play. Direction/gusts/district strength are shared automatically; ordinary renderer bounds are padded centrally. No per-model wind component is needed.

For G23, the ordinary shader is `OnlyVolunteers/Wind/v01/GenericFoliage`; custom rendering paths can call the same `V19WindDeform` function in `V19Wind.hlsl`. Terrain tree/billboard integration still needs its own in-map validation in G23's turn. A future builder rebuild must add one V19Wind, bind its district source/terrain rectangle, and assign the new grass material; this turn did not rebuild or edit the builder.

## Captures and open issue

- Six-frame Play sheet: `Working/Reviews/Wind/wind_grass_v01.jpg`.
- Hamlet grass + surviving apple-tree view: `Working/Reviews/Wind/wind_grass_v01.gif`, 960×540, 40 frames, 4.0 seconds. Sky/other motion was held while the real shared wind advanced for review; the apple tree awaits G23's wind material.
- **Inherited dependency check FAIL:** i04 and i05 share `Assets/OnlyVolunteers/Art/Trees/v03/SceneData/Terrain_v19_i01_trees.asset` (GUID `9b09c90b1fda6eb498b926723b2614e3`). All 16 terrain layers, 16/24 tree prototypes and all 5 detail prototypes are unresolved. The 8,525 tree instances remain serialized. This produces checkerboard ground and missing vegetation, visible honestly in the captures. See `inherited_terrain_dependencies_v01.txt`. Those assets/settings were not altered by this wind task; restoring the referenced assets belongs to the lead's cleanup follow-up.

Assumptions: the density cancellation takes precedence; existing trees are G23's next step; the brief's no-review-bridge rule supersedes the initial staging brief. No commit, staging, deletion, map rebuild, ProjectSettings/global URP change or background-running setting change was made.

