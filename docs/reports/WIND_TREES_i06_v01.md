# G23c — retained-tree wind and birch replacements, i06

2026-10-14. Base: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i05_wind_grass.unity`. Saved: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i06_wind_trees.unity`. This follows Fedya's corrected G23c scope: birches are **replaced**, and wind is added only to retained Forest/bare models. No builder rebuild.

## Changes

- Replaced **762 birches: 758 current poplars and 4 current apples**. Total Terrain trees remains **8,525**, with **zero birch instances**. Every original position, colour and lightmap colour is preserved. Replacement yaw is seeded random; one uniform factor in 0.9–1.1 multiplies the former instance's height and width scales. Original poplar/apple variants remain selectable.
- The four apple replacements are in `Y19_hamlet_north_allotment` (1), `Y19_hamlet_market_garden` (1), and `Y19_plot_02_ground_04` (2). Classification used v19 Hamlet garden/lawn/allotment/fruit-yard polygons, plus proximity within 12 m of existing Hamlet apple clusters. All other positions use poplar. The exact index, position, reason, yaw and factor for all 762 are in `Working/Reviews/Wind/trees_i06/birch_replacements_v02.json` (seed 230406).
- **1,042 approved v03 Forest conifers** now use G24's shared `V19Wind`, with response **0.16** and stiffness height **5 m**, for visible crown motion. **1,468 existing bare/leafless trees** use response **0.045**, stiffness height **14 m**: height weighting keeps the lower trunk almost still and permits small tip motion. Bases remain mathematically pinned. Geometry and static collider shapes are unchanged.
- All other current leafy trees, bushes, palms, pines and rocks retain their existing bindings. The proposed v04 leafy replacements are staged in Blender only, pending Fedya's approval.

Owned Unity files: `Assets/OnlyVolunteers/Map/Wind/Trees_v01/` (new material/prefab copies, `Terrain_v19_i06_wind.asset`, shader and review helpers) and the new i06 scene. Editable staging: `ArtSource/Dev/Trees_staging/Wind_i06_v01/`. Some unused material/prefab copies prepared before the scope correction remain unreferenced; none of their ordinary leafy wind bindings are enabled in i06.

`GenericFoliageWind_v02.shader` reuses **the existing G24 `V19Wind.hlsl`**, with no separate wind owner or duplicated deformation function. Its additional `DisableBatching=True` tag preserves object-space pivots through static/dynamic batching; GPU instancing remains enabled. The same deformation runs in forward, shadow, depth and depth-normal passes. It writes depth and receives URP fog and G18's depth-based aerial perspective. Terrain prefab LOD bounds are conservatively expanded; source meshes and collider geometry are untouched. The generic ordinary-renderer bounds helper is available but absent from this Terrain-only final scene.

## Checks and captures

- Compilation and final fresh Console: **0 errors**. Shader errors: **false**. Missing scene scripts: **0**. Shared wind owners: **1**.
- Compared all 8,525 original/current instance records: exactly the 762 requested substitutions; unchanged fields on every retained tree. Replacement scale/yaw ranges pass. All 24 prototype slots resolve; zero remaining birches. Collider shapes and retained mesh references checked.
- **1,595 protected files hash-identical**, including i05 dependencies, old art/materials/shaders, G24 wind v01, and ProjectSettings. Evidence: `Working/Reviews/Wind/trees_i06/protected_final_check.json`. Other chats' existing cleanup/deletions and WORK_SYNC changes were left alone.
- Play: orchard walk **ARRIVED**, 111.5 m, max lateral error 0.4 m; Hamlet van loop **ARRIVED**, 173 m, max 43 km/h. The established route harness records chassis-ground contact at (320,486), max roll 21°, pitch 34°, and 11 frames with fewer than two grounded wheels. This is a completed route check, not a claim of flawless vehicle terrain clearance. Raw result: `Working/Reviews/Map_v19_Pilots/routes_g23_i06_v02.*`.
- Sheet: `Working/Reviews/Wind/wind_trees_v01.jpg` — six actual Play renders for each retained group, 12–16 s of shared wind. GIF: `Working/Reviews/Wind/wind_trees_v01.gif` — 40 frames / 4 seconds, Forest view. The GIF uses Forest because the corrected scope deliberately leaves Hamlet leafy-tree wind for v04. Sky, weather and fog clocks are held; the shared wind changes.
- Final capture files start `corrected_` under `Working/Reviews/Wind/trees_i06/`. Earlier diagnostic captures and pre-correction evidence are explicitly excluded in `capture_manifest_final.json`.

## Frame time

RTX 5070 Ti; fixed 1280×720 render target, 08:00 light; 120 warm-up + 240 normal Play frames per cell. i05 Terrain/bindings compared against corrected i06 Terrain/bindings within the same scene. Grass counts are identical per matched view. Unity temporarily lost foreground during sampling and resumed; medians/p95 include the measured frame stream. These are Editor measurements of the **combined replacement + shader change**, not isolated wind cost or shipping FPS. The initial variable-viewport run and the interrupted pre-correction run are excluded.

| View | Median frame ms, i05 → i06 | p95 frame ms | Median GPU ms |
|---|---:|---:|---:|
| Hamlet | 5.44 → 5.12 | 7.66 → 7.12 | 2.80 → 2.19 |
| Forest | 6.95 → 6.56 | 9.02 → 8.63 | 3.55 → 2.94 |
| Beach | 4.64 → 4.82 | 7.16 → 7.37 | 2.15 → 2.25 |
| Rough | 19.76 → 9.19 | 25.01 → 12.03 | 11.24 → 4.27 |

Raw: `Working/Reviews/Wind/trees_i06/performance_g23c_v03_replacements720.json`. Its inherited harness note mentions a shared bounds helper; that component is absent in this final Terrain-only scene.

## Reusing the shared wind in three steps

1. Use a model in metres, local Y up with a base pivot, or set `_WindPivotOS`. No baked wind mesh, UV mask or vertex colour is required.
2. Duplicate the generic foliage/bush material; assign the model's colours/texture and alpha cutoff, then tune `_WindResponse` and `_FlexibleHeight` for the type. Apply the same stiffness to connected branch/leaf slots. Enable instancing and retain matching shadow/depth/fog passes. Expand culling bounds for the chosen bend.
3. Keep exactly one scene `V19Wind` (already present in i06), choose its preset and assign the material. All types read its travelling gust field and district multipliers; world position provides different local gust phases.

Play stopped and i06 saved. No review bridge, commits or new leafy-model import. The v04 sheet is the next approval gate.
