# G23c — leafy v04 preview

2026-10-14. Blender approval candidate **v04_03** is complete. **No new leafy model is imported into Unity.**

- Sheet: `Working/Reviews/Trees/leafy_trees_v04.png` — all 12 variants at a common scale, current models alongside, and actual leaf/branch close-ups in shared sunny Hamlet studio lighting.
- Source: `ArtSource/Dev/Trees_staging/v04/Leafy_Trees_v04_03.blend`.
- Exports: twelve `ArtSource/Dev/Trees_staging/v04/Models/*_v04_03.fbx`, each with three LOD meshes.
- Reusable wind setup: sixteen staged `WindMaterials/*_v04_03.mat`, exact slot mapping in `wind_bindings_v04_03.json`, capsule specifications in `validation_v04_03.json`, and a three-step integration guide in `README_v04.md` in that folder.

Three apples have crooked trunks, branching crowns, separate folded leaves and a few red apples; three poplars have dense narrow crowns and rising branches; three palms have curved segmented trunks and twelve detailed fronds; three bushes have dense irregular foliage with visible twigs. Existing project palette values are retained. COZY informed foliage structure only; no reference assets were copied. The comparison models are exports of the project's current prototypes.

| Family | LOD0 | LOD1 | LOD2 |
|---|---:|---:|---:|
| Apple, each of 3 | 5,276 | 2,988 | 1,678 |
| Poplar, each of 3 | 5,836 | 3,344 | 2,150 |
| Palm, each of 3 | 3,806 | 2,610 | 1,582 |
| Bush, each of 3 | 1,916 | 1,176 | 806 |

All 36 native meshes pass topology/budget/origin/scale checks. Fresh FBX round-trips pass for all 36, including dimensions within 1 mm and staged wind-material coverage. Leaves are closed opaque geometry, so alpha clipping is unnecessary. The staged materials use the shared generic wind's matching forward/shadow/depth/depth-normal passes and fog. Blender uses colour preview materials; the new models' Unity wind/LOD/performance validation is deferred until approval, as requested.

The preceding Unity step is already delivered as `Map_Look_v19_Play_i06_wind_trees.unity`: visible shared wind on 1,042 Forest conifers, restrained wind on 1,468 bare/leafless trees, and **762 birches replaced by 758 current poplars plus 4 current apples** at their original positions. Walk and van checks passed; compile/Console clean; 1,595 protected files unchanged. See `docs/reports/WIND_TREES_i06_v01.md`. The scene chain is appended, Play stopped and Unity lock released.

Open: **Fedya's approval of the sheet before any v04 map integration.** Earlier Blender working candidates v04_01/v04_02 remain preserved. No review bridge or commits.
