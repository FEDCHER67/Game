# G23c leafy trees v04 — approval candidate v04_03

**Current candidate:** `Leafy_Trees_v04_03.blend`, twelve `Models/*_v04_03.fbx` files and the sixteen matching staged `WindMaterials/*_v04_03.mat` files. Earlier v04_01/v04_02 iterations are retained, superseded working candidates. Do not import those by wildcard.

Preview: `C:/Dev/Game/Working/Reviews/Trees/leafy_trees_v04.png`. It contains the current i05 unscaled prototype beside each family, all twelve candidate variants at one orthographic camera scale, and actual crown close-ups. Lighting is the same bright sunny Hamlet studio approximation for every family, using existing project RGB values; this is a Blender render, not a Unity capture.

The COZY image was studied for separated foliage structure. All geometry is original. No COZY image, texture or model is embedded in these assets. `ReferenceCurrent/` contains comparison-only OBJ/MTL exports of the project's existing apple, poplar, palm and bush prototypes, not replacement assets.

## Models

| Family (A / B / C) | Height, metres | Maximum crown width, metres | LOD0 / LOD1 / LOD2 triangles |
|---|---|---|---|
| Apple | 4.70 / 4.15 / 5.20 | 4.90 / 5.10 / 4.50 | 5,276 / 2,988 / 1,678 |
| Poplar | 12.50 / 14.00 / 11.50 | 3.20 / 2.90 / 3.50 | 5,836 / 3,344 / 2,150 |
| Palm | 6.80 / 8.00 / 6.00 | 6.50 / 6.80 / 6.20 | 3,806 / 2,610 / 1,582 |
| Bush | 1.35 / 1.75 / 1.05 | 2.20 / 2.05 / 2.50 | 1,916 / 1,176 / 806 |

- Apple: four primary forks, secondary branches and terminal shoots; 360 separate folded leaves and eight small red apples per LOD0 model. Slightly crooked trunks and different crown envelopes.
- Poplar: 24 rising branch systems with secondary shoots; 576 separate leaves, dense overlapping clusters and narrow irregular columns.
- Palm: curved ring-segment trunks, twelve arching fronds, 360 individual leaflets.
- Bush: five primary stems, secondary twigs, 120 separate leaves. Lower branches are filled to produce a bush rather than a small tree.
- Every leaf is a thin, **closed opaque folded mesh**, including its back surface. No alpha texture is required. Shadow/depth/fog behavior therefore uses ordinary opaque depth with the shared wind shader's existing passes.

Metres; origin at the base; scale (1,1,1). FBX contains three named LOD meshes at the same origin. Blender Z-up is exported with -Z forward / Y up, unit scale 1 and `FBX_SCALE_UNITS`; no animation, lights, cameras or collision proxies exported with render meshes. UVs are valid, intentionally overlapping because the materials are constant colour.

The native file contains organized geometry, hidden collision proxies, current comparison meshes, and a visible studio lineup. `validation_v04_03.json` contains two static trunk capsules per tree, fitted to the actual lower trunk centerline after final scaling, including the curved palms. Coordinates under `center_Unity` and `axis_Unity` are already Y-up. Set a CapsuleCollider's direction to Y, rotate its holder from Vector3.up to the supplied axis, and use the given centre/radius/height. Bushes have no collider. These capsules are specifications/proxies until the approved Unity import.

## Shared wind — three-step setup after approval

1. Import only the approved `*_v04_03.fbx` files into a new numbered Unity folder, using metres and baked Y-up axis conversion. Set up the three LODs. Preserve the base pivot; do not bake a per-model wind animation or required vertex mask.
2. Import only `WindMaterials/*_v04_03.mat` with their `.meta` files. Remap FBX material slots using `wind_bindings_v04_03.json`. These are staged copies of G24's generic foliage material, referencing the already compiled `OnlyVolunteers/Wind/v02/GenericFoliage`, which directly includes G24's original `V19Wind.hlsl`. GPU instancing is on; cutoff 0; cull back faces. All connected slots of each family share stiffness settings: apple 0.13 / 2.5 m, poplar 0.075 / 8 m, palm 0.18 / 6 m, bush 0.22 / 0.7 m (`_WindResponse` / `_FlexibleHeight`). Nothing requires bespoke deformation code.
3. Keep the existing single scene `V19Wind`. Add the specified static capsules and sufficient renderer/LOD culling bounds for the bend. For ordinary MeshRenderers, the generic `FoliageBounds23` helper is available; for Terrain prototypes, set conservative LOD bounds. Verify wind, LOD transitions, shadow/depth/fog and frame time in Unity before replacing the map's current prototypes.

The `.mat` files are **staged, not imported**. Blender preview materials are Principled colour approximations; Blender does not execute the URP shader. The generic Unity shader was compiled and exercised on retained trees in i06. The new v04 models' Unity appearance/performance remains to be checked only after Fedya approves the sheet.

## Validation and reproduction

- Blender 5.2.1 LTS, Cycles/OptiX, 32 samples and denoising. The live Blender MCP endpoint was unavailable; work used the installed Blender background process without disturbing an open Blender scene.
- `validation_v04_03.json`: all 36 native LOD meshes pass the triangle budgets, base origins, unit scales, and zero non-manifold edges, loose vertices or degenerate faces. Branch junctions intentionally overlap closed botanical tubes.
- `fbx_roundtrip_v04_03.json`: **36/36 pass** after fresh FBX reimports; world-metre dimensions within 1 mm, triangle counts, base pivots, closed topology and complete staged material remap coverage checked.
- `build_leafy_v04_03.py`, `prepare_wind_materials_v04_03.py`, `validate_roundtrip_v04_03.py` and `make_sheet_v04_03.py` are the editable sources. Generators refuse to overwrite existing outputs. Use a new numbered revision for future changes.

No new leafy assets have been copied into `Assets/`. No map rebuild, review bridge or commit. Await Fedya's visual approval.
