# G19 - Low poly rocks and bare trees, v01

Prepared on **2026-10-14** for VOLUNTEERS ONLY. Source author: **Trekkerac / happykeys**. **3 bare trees + 11 rocks**, **14 individual FBXs**, **15,788 triangles** in total, one source-palette material per model. Trees are 5, 7 and 9 m tall; rock maximum extents range from 0.3 to 2.5 m.

Preparation and Blender FBX round-trip checks are complete. Six models retain documented source topology defects. Unity integration and map playtesting are **NOT RUN**, as requested. No Unity controls, imports, commits, staging, deletions, or shared project-file edits were performed. All project outputs are inside this new asset folder. Temporary conversion scripts are outside the project.

## Licence and provenance

The [asset page](https://happykeys.itch.io/rocks-and-dead-trees) declares **CC0**. The linked [palette page](https://milkandbanana.itch.io/gradient-color-pallete) independently lists **Creative Commons Zero v1.0 Universal**. The archive contains no separate licence file and no conflicting licence was found. See [source/PROVENANCE.md](source/PROVENANCE.md) for the exact publisher wording, retrieval date, download method, snapshots and hashes.

Original untouched archive: `source/LowPolyTreesAndRocks.zip` (1,354,382 bytes).

SHA-256: `a088b1462c6d5dfcc32b0c17bc11447fa8c540e9e38263ac533d5e48f2486d17`.

Both extracted files match their ZIP member bytes. The source `.blend` refers to an external palette that was not included separately. Conversion therefore uses the self-contained GLB and saves its embedded 2048 x 2048 PNG unchanged as `fbx/Gradient_Palette_v01.png`. The native `.blend` has the same 14 model objects and no Text datablocks; it was inspected as data with automatic script execution disabled. No archive code was run.

## Models

Sizes below are **Blender X x Y x Z**, in metres (Z is height). Every exported mesh has its origin at zero, unit object scale and zero rotation. The pivot is at the tree's trunk base or at the rock's XY bounding-box centre on its bottom plane. A capsule count of 2 means one trunk capsule and one thick low-branch capsule.

| ID / FBX | Final size XYZ (m) | Triangles | FBX bytes | Collider proxies |
| --- | --- | ---: | ---: | --- |
| [TREE_BARE_01](fbx/TREE_BARE_01_v01.fbx) | 3.036 x 3.207 x 5.000 | 514 | 34,684 | 2 capsule |
| [TREE_BARE_02](fbx/TREE_BARE_02_v01.fbx) | 3.015 x 3.488 x 7.000 | 1,550 | 65,228 | 1 capsule |
| [TREE_BARE_03](fbx/TREE_BARE_03_v01.fbx) | 4.628 x 3.547 x 9.000 | 1,374 | 61,628 | 2 capsule |
| [ROCK_01](fbx/ROCK_01_v01.fbx) | 0.300 x 0.217 x 0.223 | 174 | 26,588 | none (decorative) |
| [ROCK_02](fbx/ROCK_02_v01.fbx) | 0.457 x 0.468 x 0.550 | 180 | 27,388 | 1 box |
| [ROCK_03](fbx/ROCK_03_v01.fbx) | 0.850 x 0.691 x 0.608 | 180 | 27,468 | 1 box |
| [ROCK_04](fbx/ROCK_04_v01.fbx) | 1.100 x 0.993 x 0.902 | 734 | 48,092 | 1 box |
| [ROCK_05](fbx/ROCK_05_v01.fbx) | 1.350 x 1.012 x 0.564 | 383 | 37,068 | 1 box |
| [ROCK_06](fbx/ROCK_06_v01.fbx) | 1.600 x 0.706 x 0.593 | 288 | 31,644 | 1 box |
| [ROCK_07](fbx/ROCK_07_v01.fbx) | 0.666 x 0.795 x 1.800 | 286 | 31,836 | 1 box |
| [ROCK_08](fbx/ROCK_08_v01.fbx) | 1.634 x 1.629 x 2.000 | 984 | 51,532 | 1 box |
| [ROCK_09](fbx/ROCK_09_v01.fbx) | 2.021 x 1.676 x 2.100 | 753 | 54,428 | 1 box |
| [ROCK_10](fbx/ROCK_10_v01.fbx) | 2.350 x 0.738 x 0.689 | 2,746 | 111,020 | 1 box |
| [ROCK_11](fbx/ROCK_11_v01.fbx) | 2.045 x 2.500 x 1.668 | 5,642 | 211,036 | 1 box |

The original dimensions below are the imported GLB world-space extents, including its authored object rotation and nonuniform scale, before recentering. glTF uses metres, but the source authoring scale is not physically calibrated: original tree heights are approximately 10-25 m. The single factor shown is applied after baking those source transforms. Tree factors target height; rock factors target the largest extent. Exact min/max bounds, source transforms and pivot offsets are in [manifest_v01.json](manifest_v01.json).

| ID | Original object | Original XYZ (source metres) | Uniform scale factor |
| --- | --- | --- | ---: |
| TREE_BARE_01 | `Tree.001` | 6.325 x 6.681 x 10.415 | 0.480053914 |
| TREE_BARE_02 | `Tree` | 6.566 x 7.595 x 15.245 | 0.459174901 |
| TREE_BARE_03 | `Tree0` | 13.006 x 9.968 x 25.290 | 0.355868250 |
| ROCK_01 | `rock0` | 0.851 x 0.615 x 0.632 | 0.352573919 |
| ROCK_02 | `Rock` | 1.729 x 1.773 x 2.083 | 0.264071088 |
| ROCK_03 | `Rock.001` | 2.707 x 2.201 x 1.936 | 0.313998326 |
| ROCK_04 | `rock1` | 1.387 x 1.252 x 1.138 | 0.793119415 |
| ROCK_05 | `Rock.003` | 4.715 x 3.536 x 1.969 | 0.286301364 |
| ROCK_06 | `rock` | 4.362 x 1.925 x 1.616 | 0.366842761 |
| ROCK_07 | `rock.001` | 1.614 x 1.925 x 4.362 | 0.412698239 |
| ROCK_08 | `rock3` | 1.693 x 1.688 x 2.072 | 0.965026522 |
| ROCK_09 | `Rock.002` | 4.220 x 3.501 x 4.385 | 0.478862475 |
| ROCK_10 | `rock4` | 5.845 x 1.836 x 1.713 | 0.402064366 |
| ROCK_11 | `rock_d` | 8.291 x 10.137 x 6.763 | 0.246625672 |

## Cleanup, materials and FBX contract

Duplicate vertices were merged at 0.000001 m. Degenerate faces and loose geometry were removed where present; normals were recalculated. Original hard edges were recovered from GLB corner normals before welding to retain the low-poly shading. No empty objects or animation are exported. Source silhouettes and palette UVs are preserved; the six source junction defects below were not aggressively remeshed.

Export settings match `ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS/README.md`: selected one mesh only, `axis_forward=-Z`, `axis_up=Y`, `apply_unit_scale=True`, `global_scale=1`, `use_mesh_modifiers=False`, `mesh_smooth_type=FACE`, `bake_anim=False`, `path_mode=STRIP`, `use_custom_props=False`; `add_leaf_bones=False`. All transforms are applied before export. No armature is present.

All FBXs reference **MAT_HK_SourcePalette**, using the supplied PNG. Keep the PNG beside the FBXs when copying them. The atlas is sRGB and source UVs are retained. There is one shared material, rather than baked recoloured texture copies. These palette UVs are not an evenly tiled bark/rock unwrap: use flat colours, the existing palette, triplanar materials, or deliberately author new UVs when remapping.

Later Unity import guidance from the reference kit: Scale Factor 1, Bake Axis Conversion enabled, normals imported, tangents none, animation off, no generated mesh collider. This guidance was not tested in Unity in this task. Model-local proxy coordinates are supplied in both Blender `(x,y,z)` and Unity `(x,z,-y)` conventions.

## Collider handoff

[manifest_v01.json](manifest_v01.json) supplies exact analytic dimensions and centres: **5 capsules and 10 boxes**. `happykeys_prepared_v01.blend` includes corresponding closed wire debug meshes in **COL_Collision_Proxies**, parented to their render models and hidden in both viewport and render by default. Unhide the collection objects to inspect them. The FBXs contain only their render mesh; collider meshes are not mixed into exports. Create engine CapsuleCollider/BoxCollider components from the manifest instead of using the debug meshes as MeshColliders.

- Each tree has one conservative capsule for its primary trunk. Bent trunks make these intentionally broader than some sections of the mesh.
- TREE_BARE_01 and TREE_BARE_03 each have one extra capsule for the thick basal branch reaching below 2.5 m. TREE_BARE_02 has no extra branch proxy: its main lateral branch is above 2.5 m; the thin downward twig, around 0.10 m thick, is decorative.
- Every rock of at least 0.4 m maximum extent has one axis-aligned bounds box. ROCK_01 is 0.3 m and has no collider. Bounds boxes are conservative, especially on irregular ROCK_11.
- Capsule `height_m` includes both hemispheres; `sphere_centres_*` are the centres of those hemispheres, not capsule tips. `axis_*` defines the capsule's local long-axis direction. Coordinates exclude the display translations in the prepared Blender lineup.

Suggested placement: all three trees suit Rough District streets or yards and the Forest edge. Rocks suit ravine banks, field edges and the Forest edge. Variation, terrain burial, spacing and natural cluster composition remain for the map chat. No map objects or existing leafless trees were changed.

## Previews and editable scene

- [previews/lineup_v01.png](previews/lineup_v01.png): original palette; all 14 models at a common metre scale.
- [previews/rough_district_recolour_v01.png](previews/rough_district_recolour_v01.png): same geometry, camera and lighting with cold grey-brown bark and grey rocks.
- `happykeys_prepared_v01.blend`: packed original palette, laid-out models, both recolour materials, hidden proxy debug meshes, camera, grid and lights. Local mesh pivots remain at ground; reset each model's display translation before re-exporting. All delivered FBXs were exported before lineup translations were assigned.

Both PNGs are **1600 x 1100**, orthographic, with a 1 m ground grid. Cycles, 64 samples, denoising, Standard colour transform, neutral illumination. The recolour is a flat-swatch material preview, not a textured production material or a changed FBX.

Palette reference: `ArtSource/Textures/StyleKit_v3/candidate_v07/grade_v07.json`, SHA-256 `b3282ef21536423f4d285804ca15a303865436993468f33626ee6c537f1577ab`.

The v07 bark mean is warm `#846450`. For the specifically requested cold/desaturated look, **MAT_HK_RoughDistrict_Bark_v07** uses that mean with HSV saturation x0.30, value x0.94, hue retained, then +0.012 sRGB blue: resulting base colour **#7C7371**. **MAT_HK_RoughDistrict_Rock_v07** uses the unmodified v07 `1d_gravel` mean **#9C9EA1**. Roughness is 0.9. Full-precision colours and formulas are in the manifest. The grade file has no dedicated natural-rock category, so gravel grey is the stated role mapping. The shared grade file was not modified.

## Verification

- **PASS** - archive SHA-256 and byte-for-byte extracted members checked; page and palette licence evidence preserved.
- **PASS** - all 14 FBXs independently reimported in Blender **5.2.1 LTS**; one mesh per file, no empty objects or animation, expected triangles, zero degenerate triangles, metre bounds, ground contact, identity transforms, UVs, normals and texture availability verified. Maximum bounds error was below 0.000001 m. See [validation_v01.json](validation_v01.json) for every measured result.
- **PASS** - 15 proxy debug meshes are closed, hidden from rendering and parented to their matching model.
- **PASS** - prepared `.blend` reopened with automatic scripts disabled; 14 model objects, 15 proxy objects, zero empty objects. Its packed 2048 x 2048 palette has exactly the same SHA-256 as the external PNG.
- **PASS** - both final 1600 x 1100 PNGs inspected visually: complete silhouettes, ground contact, readable IDs, consistent scale, and no missing-texture pink. This is a technical preview review; artistic acceptance belongs to the lead.
- **NOT RUN** - Unity import, map placement, physics clearance and gameplay/performance tests; another chat owns Unity.
- **WARNING** - six source render meshes are not watertight/manifold. Round-trip success does not change that fact.

The builder emitted Blender packed-image fallback messages while relocating the GLB palette. The subsequent independent FBX texture checks and reopened-master packed-image hash check passed; no unresolved external texture dependency was found in the prepared deliverables. The untouched native source `.blend` still has its original absent external palette reference.

Commands actually used (helpers outside the project; their logs remain in the same temporary directory):

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --disable-autoexec --python-exit-code 1 --python 'C:/Users/Zeyo-ne/AppData/Local/Temp/G19_happykeys_20261014/prepare_g19.py'
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --disable-autoexec --python-exit-code 1 --python 'C:/Users/Zeyo-ne/AppData/Local/Temp/G19_happykeys_20261014/audit_g19.py'
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --disable-autoexec --python-exit-code 1 --python 'C:/Users/Zeyo-ne/AppData/Local/Temp/G19_happykeys_20261014/check_master.py'
```

Do not rerun into this revision: the helpers refuse to replace deliverables. Any future revision must use a new numbered output folder/files.

## Open issues

Source mesh junctions remaining after cleanup (counts after welding at 0.000001 m):

| Model | Non-manifold edges | Of those, boundary edges |
| --- | ---: | ---: |
| TREE_BARE_02 | 7 | 2 |
| TREE_BARE_03 | 18 | 12 |
| ROCK_05 | 4 | 1 |
| ROCK_06 | 1 | 0 |
| ROCK_07 | 1 | 0 |
| ROCK_09 | 14 | 6 |

These source defects are preserved and disclosed. The meshes are suitable for visual review, but are not certified watertight solids and must not become collision meshes. If a close camera angle exposes a defect, make a new repair revision; do not overwrite v01.

ROCK_10 (2,746 triangles) and ROCK_11 (5,642 triangles) are substantially denser than the simpler rocks. No LODs were requested or generated. Large-scale scattering needs the map team's performance check. Primitive colliders also need in-map clearance testing, particularly bent tree trunks, the low branches and irregular rock boxes. Recolour materials require lead acceptance and a deliberate engine remap.

## Complete file list

All paths below are relative to this v01 folder. This `README.md` is the additional report file; individual FBX sizes and model dimensions are also listed above.

| File | Bytes |
| --- | ---: |
| `extracted/OutisideBlocks.blend` | 1,717,154 |
| `extracted/OutisideBlocks.glb` | 1,095,256 |
| `fbx/Gradient_Palette_v01.png` | 543,841 |
| `fbx/ROCK_01_v01.fbx` | 26,588 |
| `fbx/ROCK_02_v01.fbx` | 27,388 |
| `fbx/ROCK_03_v01.fbx` | 27,468 |
| `fbx/ROCK_04_v01.fbx` | 48,092 |
| `fbx/ROCK_05_v01.fbx` | 37,068 |
| `fbx/ROCK_06_v01.fbx` | 31,644 |
| `fbx/ROCK_07_v01.fbx` | 31,836 |
| `fbx/ROCK_08_v01.fbx` | 51,532 |
| `fbx/ROCK_09_v01.fbx` | 54,428 |
| `fbx/ROCK_10_v01.fbx` | 111,020 |
| `fbx/ROCK_11_v01.fbx` | 211,036 |
| `fbx/TREE_BARE_01_v01.fbx` | 34,684 |
| `fbx/TREE_BARE_02_v01.fbx` | 65,228 |
| `fbx/TREE_BARE_03_v01.fbx` | 61,628 |
| `happykeys_prepared_v01.blend` | 1,283,319 |
| `manifest_v01.json` | 58,419 |
| `previews/lineup_v01.png` | 1,923,302 |
| `previews/rough_district_recolour_v01.png` | 1,913,618 |
| `source/itch_page_2026-10-14.html` | 23,227 |
| `source/LowPolyTreesAndRocks.zip` | 1,354,382 |
| `source/palette_page_2026-10-14.html` | 46,601 |
| `source/PROVENANCE.md` | 2,801 |
| `validation_v01.json` | 19,909 |
