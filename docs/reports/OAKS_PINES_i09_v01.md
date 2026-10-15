# G23 — approved oaks and umbrella pines, i09

2026-10-15. Saved scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i09_oaks_pines.unity`, based on i08. Only Oak A/B/C **v01_02** and Pine A/B/C **v04** were imported. No earlier pine candidates are used. No commits or review bridge.

## Changes

New assets: `Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/`: six byte-identical approved FBX, six prefabs, 18 derived LOD meshes, seven materials, and separate TerrainData. Each prefab has three LODs plus cull and two trunk capsules. Mesh coordinates, colours and approved silhouettes were preserved. New mesh bounds include conservative wind padding; LOD thresholds compensate for the padding.

All **769 oaks and 2,009 umbrella pines** were replaced at identical pivots. All **5,747 other Terrain tree records**, the ordinary garden apple, Forest v03 conifers, bare trees, rocks and leafy v04 assets remain unchanged. Total: 8,525 records. Original 36 prototype references are retained, with six new slots appended; old oak/pine slots have no remaining instances.

Seed **230409** selects A/B/C, yaw and one uniform 0.9–1.1 variation factor. Actual LOD0 vertices measure native height; leaf-submesh vertices measure crown width, excluding bark and wind bounds. The i08 rule is applied:

`widthScale = oldWorldWidth / newNativeWidth * jitter`

`heightScale = widthScale / clamp(widthScale / requestedHeightScale, 0.8, 1.25)`

Width therefore takes priority at the limit. Heights and widths below are median world metres, before yaw.

| Type | Count | A / B / C | Clamped | i08 height / width | i09 height / width |
|---|---:|---|---:|---|---|
| Oak | 769 | 271 / 240 / 258 | 72 | 8.87 / 7.70 | 8.89 / 7.68 |
| Pine | 2,009 | 668 / 631 / 710 | 0 | 12.99 / 6.86 | 12.93 / 6.85 |

LOD0 triangles A/B/C: Oak **6,252 / 6,174 / 6,684**; Pine **7,788 / 7,596 / 7,788**. All 18 LOD counts are recorded in `Working/Reviews/Trees/i09/asset_validation.json`.

## Wind and preservation

The materials use the existing i08 shared shader `OnlyVolunteers/Wind/v03/GenericFoliageScaled` (the instance-height-aware GenericFoliage revision), with the same global V19Wind owner and gust field. No new wind code or global settings. Oak response/stiffness: **0.055 / 9.0493 local m**; pine: **0.028 / 17.5312 local m**. The shader multiplies stiffness by instance height scale; large trunks stay stiff. Opaque foliage casts shadows, writes depth, and receives URP fog/aerial perspective in the captured map views.

**PASS:** all six imported FBX exactly match approved source bytes. All **2,348 protected files** are unchanged. The scene YAML diff contains only the Terrain and TerrainCollider data references. New TerrainData: `Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/SceneData/Terrain_v19_i09_oaks_pines.asset`, GUID `a1c4de308a1a27647bac32499ecb0940`.

## Verification

- **PASS — import / compilation / references:** Unity 6000.5.11f1; 18 LODs, six valid LODGroups, 12 capsules, instanced materials, shadow/depth passes. Final Console: zero errors/warnings. Zero missing scene mesh/material/script references; all 16 terrain layers, 42 tree prototypes and five detail prototypes resolve. No TerrainData repair.
- **PASS — placement:** all original positions and colours retained; all non-target records exact. Maximum pivot/terrain error **0.00000191 m**. Independent width/height formula checks passed for all 2,778 replacements.
- **PASS — real Play routes:** orchard walk/van, poplar-road walk/van, Beach walk/van, garden walk and garden driveway van arrived through the existing KCC/VanController harness. Eight arrivals across nine routes.
- **Known baseline FAIL:** the full garden van endpoint still stops at **(290,520), after 44 m**, against the tree-swing seat and protected garden apple capsule, as in i06–i08. Existing chassis/ground contacts are also reported; arrival does not mean perfect clearance. No gameplay tuning changed.
- **PASS — rendering:** four matched i08/i09 Play views, plus 16 shared-wind frames over four seconds. Final i09 reopened, saved, Play stopped, no temporary benchmark component.

Route evidence: `Working/Reviews/Map_v19_Pilots/routes_g23_i09_v01.json` and `.txt`. Integration and exact prototype paths/GUIDs: `Working/Reviews/Trees/i09/integration_validation.json`. Reproduction scripts: `ArtSource/Dev/Trees_staging/i09_v01/`.

## Performance limitation and comparison

**Normal-loop FPS and isolated GPU milliseconds: NOT AVAILABLE for this round.** Unity repeatedly lost foreground focus to another app and stopped advancing Play frames. The incomplete normal benchmark was discarded; `runInBackground`, ProjectSettings and global URP settings were not changed.

Instead, both actual Play scenes were measured at the **same four i08 benchmark cameras**, 1280×720 HDR, 08:00, fixed shared wind time 12: 12 warm-up + 60 synchronous renders/view. Timing covers `Camera.Render` plus a one-pixel GPU readback, including CPU submission, GPU completion and synchronization overhead. It is a matched rendering-cost comparison, **not FPS or isolated GPU time**.

| Camera | i08 median render ms | i09 median render ms | Delta ms |
|---|---:|---:|---:|
| Orchard | 6.767 | 6.259 | −0.508 |
| Poplar road | 8.100 | 8.039 | −0.061 |
| Beach | 4.511 | 3.766 | −0.744 |
| Garden | 4.206 | 3.989 | −0.218 |

These single Editor samples include variability; the small negative deltas are not a claim of an optimization. Evidence: `render_performance_i08.json`, `render_performance_i09.json`, `render_performance_comparison.json`, `performance_limitation.json`.

## Review

- Sheet: `Working/Reviews/Trees/oaks_pines_in_map_i09.jpg` — i08 | i09, oak street, pine grove, poplar road and wide view. The final wide pair uses `*_wide_v02.png`; earlier fog-obscured wide captures are retained but excluded.
- Wind GIF: `Working/Reviews/Trees/oaks_pines_wind_i09.gif` — oak street, 16 frames / four seconds.
- Scene chain appended; Unity lock released before Part 2. Remaining limitations: unchanged garden obstruction and unavailable normal-loop FPS/GPU comparison. Pine_Tall is the following Blender-only preview task; no i10 placement is authorized yet.
