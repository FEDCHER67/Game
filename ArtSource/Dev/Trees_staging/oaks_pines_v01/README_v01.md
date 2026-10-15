# G23 — COZY oaks and umbrella pines: Blender approval candidate

Step 1 is complete. Fedya's visual approval is the next gate. Nothing has been imported into Unity or placed in the map.

## Final candidates

- `Cozy_Oaks_Pines_v01_02.blend`: all six final model candidates, LODs and collider proxies.
- `Cozy_Oaks_Pines_Preview_v01_02.blend`: the comparison studio, including approved reference trees.
- `Models/Oak_A_v01_02.fbx`, `Models/Oak_B_v01_02.fbx`, `Models/Oak_C_v01_02.fbx`.
- `Models/Pine_A_v01.fbx`, `Models/Pine_B_v01.fbx`, `Models/Pine_C_v01.fbx`.
- `C:/Dev/Game/Working/Reviews/Trees/oaks_pines_v01.png`: the requested combined approval sheet.

The oak crown was refined in a separate numbered revision after render inspection: foliage now extends lower and more evenly around the main forks. The final selection is Oak v01_02 plus unchanged Pine v01. Initial Oak v01 exports and previews remain as diagnostics; they are not the final selection. No approved v04 or Forest v03 model was rebuilt or re-exported.

## Measured map sizes

Measured from the latest saved i08 TerrainData:
`Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/SceneData/Terrain_v19_i08_leafy_mass.asset`.
The asset contains 8,525 instances and 36 prototypes. All 2,778 oak/pine records were cross-checked against the i06 instance snapshot because these families were unchanged by i07/i08.

Height is the actual mesh vertex extent multiplied by the instance height scale. Crown width is the maximum local X/Z extent of leaf-submesh vertices multiplied by the instance width scale, before yaw. Padded renderer bounds are not used.

| Family | Instances | Median height | Height range | Median crown width | Crown width range |
|---|---:|---:|---:|---:|---:|
| Oak | 769 | 8.872 m | 4.053–20.118 m | 7.696 m | 2.691–20.262 m |
| Pine | 2,009 | 12.986 m | 7.282–20.096 m | 6.861 m | 3.418–11.931 m |

Each A/B/C candidate uses its family median height and crown width. Variant differences are in the trunks, branch networks and foliage distribution. The old placeholders in the sheet are representative oak_b and pine_a meshes scaled to the family statistical medians; they do not represent a single selected map instance. Each future map placement must still match its own old world size, with the requested ratio clamp and seeded variation.

## Geometry and palette

| Final model | LOD0 triangles | LOD1 triangles | LOD2 triangles |
|---|---:|---:|---:|
| Oak A v01_02 | 6,252 | 3,384 | 1,888 |
| Oak B v01_02 | 6,174 | 3,328 | 1,846 |
| Oak C v01_02 | 6,684 | 3,600 | 1,984 |
| Pine A v01 | 5,684 | 3,206 | 1,902 |
| Pine B v01 | 6,186 | 3,530 | 2,120 |
| Pine C v01 | 6,164 | 3,438 | 2,014 |

Oaks use the approved v04 opaque folded-leaf primitive, broad irregular crowns, thick gnarled trunks and visible heavy inner branches. Pines use elongated folded needle slabs, high flat crowns and long curved bare trunks. These are closed opaque meshes, not alpha cards or smooth crown blobs.

Existing palette: Bark `#68503C`, LeafDark `#3A6E38`, Leaf `#5C9640`, LeafLight `#86B04A`, LeafPine `#2C6042`. Pine bark keeps the existing warm brown palette. The original Mesh helper was read from `ArtSource/Dev/Trees_staging/v04/build_leafy_v04_03.py`; no old asset builder was executed.

Each FBX contains three LOD meshes. The native blend contains two capsule proxies per tree; the corresponding centre, axis, radius and height recipes are recorded in `validation_candidates_v01_02.json`. Unity LODGroup and CapsuleCollider components remain for the approved integration step.

## Shared wind staging

Seven material assets and their identities are staged in `WindMaterials/`. `wind_bindings_v01.json` maps exported material names to the existing `OnlyVolunteers/Wind/v02/GenericFoliage` shader and shared V19Wind include. No shader or per-model wind code was added.

| Family | Wind response | Flexible height at median size |
|---|---:|---:|
| Oak | 0.055 | 9.049 m |
| Pine | 0.028 | 17.531 m |

These settings target a nearly still lower trunk and heavier limbs, with the pine crown moving less than the oak. They are staged settings, not verified in-game motion. At integration, stiffness height must follow instance world height as in i08, while retaining the shared global gust field. Fog, depth, shadows, motion and actual Unity material import must be checked then.

## Validation and preview

`fbx_roundtrip_v01_02.json`: PASS for six FBX files and all 18 LOD meshes reimported into a fresh Blender process. Triangle counts, dimensions, base pivots, metre scale, UV presence and material mappings passed. No nonmanifold edges, loose vertices or degenerate faces were found. Twelve capsule recipes passed. All 2,052 protected source/Unity files in the captured manifest remained unchanged.

Accepted evidence: `validation_candidates_v01_02.json`, `fbx_roundtrip_v01_02.json`, `roundtrip_v01_02_checked.log`, `map_sizes_v01.json`, `preview_manifest_v01_02.json` and `sheet_manifest_v01.json`. The earlier `roundtrip_v01_02.log` records a failed script-launch attempt and is not the accepted validation run.

The sheet was visually inspected. Both family lineups and the approved Apple v04_03, Poplar v04_04 and Forest v03 fir use one orthographic scale of 72 pixels per metre and the established Hamlet studio lighting. The two branch/foliage close-ups are enlarged and labelled. These are Blender previews, not in-game captures.

Blender MCP was unavailable, so generation, rendering and FBX validation used installed Blender 5.2.1 LTS in background processes. No live Blender session was altered. Build, render, measurement and validation scripts and logs are included here.

## Open / deferred

Await Fedya's approval of the sheet. Unity import, map replacement, instance scale matching, Play tests, performance checks, scene-chain entry and the integration report belong to Step 2 after the separate go message. No Unity lock, Unity scene changes, commits or review bridge were used in Step 1.
