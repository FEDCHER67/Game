# G23 — foliage mass correction, i08

2026-10-15, Moscow. New saved scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i08_leafy_mass.unity`, based on i07. i07 and earlier scenes/assets remain unchanged. No commits or review bridge.

## Change and size rule

Resized **999 poplars, 243 apples, 47 palms and 1,949 bushes** (3,237 Terrain instances plus the ordinary garden apple). Counts, approved A/B/C variants, seeded yaw, colours and every pivot are unchanged. Forest conifers, bare trees, rocks and the other 5,288 Terrain records are untouched. No new plants were added.

Measured the original i06 and approved LOD0 geometry directly, excluding padded wind bounds. Height is the full vertex Y extent. Crown width is the larger local X/Z extent of the **leaf material submeshes**, excluding bark and fruit. This is native crown-envelope width before yaw, matching the requested prototype-size formula. The ordinary garden apple was independently checked in the original i06 scene: `tree_apple_a`, world scale 0.9.

For each instance, using the exact original i07 random factor `j` (0.9–1.1):

```
widthScale  = oldNativeCrownWidth * oldWidthScale / newNativeCrownWidth * j
heightWant  = oldNativeHeight    * oldHeightScale / newNativeHeight    * j
heightScale = widthScale / clamp(widthScale / heightWant, 0.8, 1.25)
```

Crown width therefore matches the original instance times the retained jitter; height follows the same target unless the shape limit requires adjustment. This adds the original i07 variation on top of the old dimensions, as requested; it does not generate a new random factor.

| Type | Count | Ratio below 0.8 | Ratio above 1.25 | Total clamped |
|---|---:|---:|---:|---:|
| Apple | 243 | 22 | 32 | 54 |
| Poplar | 999 | 499 | 11 | 510 |
| Palm | 47 | 11 | 1 | 12 |
| Bush | 1,949 | 716 | 366 | 1,082 |
| **Total** | **3,238** | **1,248** | **410** | **1,658** |

Median world dimensions, metres; each cell is **height / crown width**:

| Type | i06 | i07 | i08 |
|---|---:|---:|---:|
| Apple | 5.27 / 5.55 | 4.65 / 4.79 | **5.24 / 5.51** |
| Poplar | 15.01 / 3.70 | 12.55 / 3.91 | **13.64 / 3.69** |
| Palm | 8.54 / 7.51 | 6.32 / 6.38 | **8.30 / 7.33** |
| Bush | 1.82 / 2.69 | 1.35 / 2.22 | **1.71 / 2.69** |

The poplar median height remains below i06 because many original height/width combinations exceed the allowed aspect ratio. Width takes priority. The approved models' leaf density and silhouette are unchanged; restoring dimensions cannot reproduce the old solid placeholder crowns' opacity.

Evidence: `Working/Reviews/Trees/i08/native_dimensions.json`, `scale_plan.json`, `dimension_summary.json`, `instances_readback.json`, `independent_scale_check.json`.

## Wind and assets

New revision folder: `Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/`. Twelve prefab copies reuse the **same 36 mesh assets**, three LOD thresholds/cull, and trunk capsules. No FBX reimport/export or model edit. A separate TerrainData, `SceneData/Terrain_v19_i08_leafy_mass.asset` (GUID `c00b23ab7d81d1441acb0554ae23d1de`), retains all 8,525 records and 36 prototype slots.

The old generic shader interpreted `_FlexibleHeight` in world metres. To scale stiffness without changing i07, i08 uses a separate generic shader revision, `Shaders/GenericFoliageWind_v03.shader`, and 16 material copies. **All saved material properties are identical** to i07; only the shader reference changes. Response, colours, textures, masks, stiffness values, instancing and the shared global V19Wind field are preserved. There is no per-model wind code.

The shared vertex function multiplies stiffness height by the length of the instance matrix's transformed up axis. This works for Terrain instances and ordinary prefabs, in forward, shadow, depth and depth-normal passes. Base displacement remains zero; the relative stiffness profile remains the same as a tree grows. Fog/aerial perspective, shadowing and depth remain active. Exactly one original V19Wind owner remains.

**PASS — analytical stiffness/bounds:** normalized profiles match across all 3,238 scales to numerical precision. Existing wind padding still contains the conservative displacement bound; no mesh bounds were edited. **PASS — Play rendering:** the new shader compiled, the four map views rendered, and 16 poplar-road frames show shared gust motion. Material-property equality was checked with Unity `SerializedProperty.DataEquals`. Evidence: `wind_scale_check.json`, `material_preservation.json`, `wind_capture_check.json`.

## Hedge continuity

**32 remaining gaps over 0.10 m** were detected across **247 neighbour pairs / 298 bushes** in inferred rows. Comparable counts are **31 in i06, 40 in i07, 32 in i08**. The largest i08 projected gap is **2.03 m**. The garden review row has **zero** such gaps across **17 pairs / 18 bushes**, though the detailed leaf cards still have internal transparency.

Assumption: Terrain records contain no hedge IDs. The audit identifies consecutive bush records spaced 0.35–4 m apart, in runs of at least three near-aligned plants (turn at most 45 degrees), retaining interior corners. Wide entrances and isolated scatter are excluded. It measures the gap between actual rotated/scaled leaf envelopes along the neighbour line; this is a count of definite horizontal separations in those inferred runs, not a claim that every leaf-level opening is closed. All pair indices, locations and three-revision gap measurements are in `hedge_gap_audit.json`. **No extra instances were added.**

## Play checks and references

**PASS:** orchard walk/van, poplar-road walk/van, Beach walk/van, garden walk and garden driveway van arrived, using the same real KCC/VanController route harness and input paths as i07.

**Known baseline FAIL, unchanged:** the full garden van line stops at **(290,520), after 44 m**, against the garden apple capsule and tree-swing seat. It failed at the same point in i06 and i07. The usable garden driveway check still arrives (32 m driven, 7.8 s). The harness also records existing chassis/ground contact; arrival is not a claim of perfect clearance. No movement, collider recipe, route placement or gameplay tuning was changed.

Route evidence: `Working/Reviews/Map_v19_Pilots/routes_g23_i08_v01.json` and `.txt`; inputs: `Working/Reviews/Trees/i08/routes_input_v01.json`.

**PASS — saved/reopened scene:** zero missing mesh/material/script references; all **16 terrain layers, 36 tree prototypes and five detail prototypes** resolve. No TerrainData repair. Maximum pivot/terrain error is **0.00000191 m**. Per-slot paths and GUIDs are in `final_scene_check.json`.

**PASS — final Console/compilation:** zero fresh errors/warnings in the clean initialized Play run and final saved-scene check. The first benchmark after compilation encountered an unbound KCC controller and is **excluded**. Reopening the saved scene initialized the existing controller normally; the accepted rerun began at frame 1442 with its controller bound. No gameplay code or settings were changed. Existing project-wide obsolete-API compilation warnings were not addressed.

## Matched performance

RTX 5070 Ti; actual named Play scenes, 1280×720 HDR, 08:00, 120 warm-up + 240 normal frames/view. These are whole-scene Editor measurements. Grass visibility counts match i06/i07/i08 in all four views. The original completed i06/i07 benchmark camera poses are reused, including the original Beach benchmark at (844,225); the sheet retains the dry-land Beach camera at (846,217).

| View | FPS i06 / i07 / i08 | Frame ms i06 / i07 / i08 | GPU ms i06 / i07 / i08 | GPU delta vs i06 / i07 |
|---|---:|---:|---:|---:|
| Orchard | 125.0 / 118.3 / **112.5** | 8.00 / 8.45 / **8.89** | 3.781 / 3.897 / **4.000** | +0.219 / +0.103 |
| Poplar road | 100.1 / 101.5 / **95.1** | 9.99 / 9.85 / **10.52** | 6.190 / 5.224 / **6.534** | +0.345 / +1.310 |
| Beach | 228.3 / 226.2 / **220.7** | 4.38 / 4.42 / **4.53** | 2.437 / 2.477 / **2.471** | +0.034 / −0.005 |
| Garden | 193.2 / 150.7 / **188.6** | 5.18 / 6.64 / **5.30** | 2.314 / 2.388 / **1.823** | −0.492 / −0.565 |

Largest i08 frame increase versus i07: **+0.67 ms on the poplar road**; largest GPU increase: **+1.31 ms** there. These single Editor runs include normal CPU/GPU variability and do not isolate shader cost. Accepted evidence: `performance_i08_v02.json`, `performance_comparison_v02.json`, `performance_selection.json`. The earlier `performance_i08.json` and its first comparison are retained solely as rejected diagnostic data.

## Review and handoff

- **Sheet:** `Working/Reviews/Trees/leafy_v04_in_map_i08.jpg`, four cameras, **i06 | i07 | i08**. Earlier columns reuse the original final i07 review's PNGs, unaltered.
- **Wind GIF:** `Working/Reviews/Trees/leafy_v04_wind_i08.gif`, 16 frames/four seconds, poplar road.
- **Reproduction:** `ArtSource/Dev/Trees_staging/i08_v01/`; new Unity helper `G23MassI08` builds bindings, integrates, validates and captures explicitly. Nothing runs an automatic map rebuild.
- **Preservation PASS:** all **1,930 protected files** are unchanged, including approved models, i07/earlier scenes, their dependencies and ProjectSettings. Scene diff contains the terrain/collider data references and garden-apple scale/material overrides; Unity also reserialized an unused light bounding-sphere field with its override still disabled. No light setting or global URP asset was changed.
- Final scene is saved and reopened, Play stopped, no temporary benchmark component. i08 is appended to the scene chain; lock released after checks. Remaining items are the reported hedge gaps and unchanged garden endpoint obstruction. No commits or review bridge.
