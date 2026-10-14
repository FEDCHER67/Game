# G23 COZY tree v02 staging

Latest authority: Fedya's follow-up expands the requested work to new forest conifer crowns and an optional broadleaf trial. Existing leafy assets, including Vadim's work, remain unchanged.

## Art direction and sources

Reference studied in a browser only: https://distantlands.space/images/cozy-case-study/cozy_4.jpg. No reference files were copied. The conifers use uneven overlapping bough tiers, pointed drooping silhouettes and warm exposed trunks. The trial broadleaf uses golden irregular crown lobes and rising forks. Happykeys keeps its original geometry and approved recolour.

`Source/Trees_Cozy_v02.blend` contains original G23 crown geometry, two shapes per family, two LODs. Four FBXs under `v02/Models/` export those models. Blender exports and imports were checked at 1m normalized height with applied transforms. Runtime dimensions derive from each original tree's height. Solid colour materials intentionally use no texture UVs. Separate closed branch/crown pieces overlap by design. These are stylised opaque meshes, not watertight manufacturing meshes.

Conifer LOD0/1: 972/320 triangles. Broadleaf LOD0/1: 704/260 triangles. Three colour slots per model. Asset budgets exclude the preserved happykeys originals.

## Revision behaviour

`V19TreesCozyV02`: master `V19Revision = CozyV02`, plus independent `ForestConifers`, `BetweenDistrictBroadleafTrial`, `RoughBareTrees` booleans, default true. Set the broadleaf trial false to retain/restore the previous roadside trees. `Original` restores all previous prefabs. Other map revisions are excluded.

Conifers are selected inside the existing `forest` district bounds from V19PaletteTest. Broadleaf trial trees are selected outside every existing district rectangle (the operational definition of roadside/common land). District gardens, palm trees, bushes, hedges and grass remain original. Happykeys bare trees use the v02 prefabs. The legacy leafless prefab also has a prepared compatible revision.

TreeInstance positions, rotations, colours and scale factors are retained. The generic builder still computes scale from original height; v02 height is therefore 0.78 times the previous height, not cancelled by rescaling. Bare visual X/Z dimensions and trunk colliders grow by 1.25. New crown maximum horizontal spans are 0.52/0.47 of revised height for conifers A/B, and 0.72/0.68 for broadleaf A/B, retaining the authored reference silhouette; new basal trunk radius is measured from the old visual trunk, enlarged 1.25, and matched by the new capsule. All old assets remain selectable.

The final terrain cache is cloned into a new numbered asset when selection changes. G23 never rebuilds v19. G18 must run its approved build and regenerate its separate bare-tree collision proxies after choosing the switches.

## Wind

URP 17.5 Lit lighting plus shared deformation in forward, shadow, depth and depth-normal passes. Bottom 4% pinned; quadratic height mask and radial tip weighting. Slow wave, slower gust, per-instance phase from world origin. Peak offset bounded by 1.298% of nominal revised height. GPU instancing macros in all realtime passes, instancing enabled on materials. No per-tree runtime components. Culling bounds padded; normals retain their rest orientation for this small displacement. Meta/baked-light pass is at rest.

## Import transaction

Complete code/models/shader remain outside Assets until G23 owns the overnight Unity lock, after G18, G20 and G22. Hold AssetDatabase.StartAssetEditing, run install_v02.py, always StopAssetEditing, refresh and verify compilation. Installer checks exact builder anchors against current peer edits and fingerprints protected assets/scenes/settings. Unity authors new GUIDs. BuildAssets creates new prefab/material/mesh assets; BuildScene makes only Trees_Test.unity.

Validation: staged C# compile, Blender round-trip, live Unity shader validation, dimensions/colliders, spatial selection and rollback, native Terrain trunk raycasts and GPU instancing probe in Play, separate comparisons and three deterministic wind captures per group. Final evidence and limitations belong in docs/reports/TREES_COZY_v02.md.
