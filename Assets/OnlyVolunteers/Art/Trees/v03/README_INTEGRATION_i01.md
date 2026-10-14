# Forest conifers v03 — i01 integration

Approved source: `ArtSource/Dev/Trees_staging/v03`, candidate **v03_04**. FBX and texture files are exact source copies. Source shader header comments describe the earlier staging step; this complete imported set was compiled and checked in Unity 6000.5.11f1 / URP 17.5 on 2026-10-14.

Four prefabs in `Prefabs/` contain three LODs and a root trunk capsule. Derived `Meshes/` bake the FBX axis conversion to upright Unity Y with identity child transforms; UV0.x remains the per-frond root-to-tip mask. Mesh bounds include 0.25 m horizontal wind padding. LOD screen fractions are 0.18 / 0.065 / 0.005; the last LOD is geometry, not a billboard.

All 16 materials enable GPU instancing. Each variant has one bark material and three frond tints. Fronds use the original RGBA texture, `_ALPHATEST_ON`, cutoff 0.5, and render queue 2450; bark is opaque at queue 2000. Texture mipmaps preserve coverage at 0.5, with clamp wrapping and trilinear filtering. No global render settings are changed.

`_TreeShape = (0, 1/height, 2/crownWidth, height*0.008)` for each variant. Height/width pairs: 9/5.76, 8/5.52, 7.5/5.10, 6/3.54 metres. Wind settings are `(0.72, 0.18, 0.94, 0.34)`. Bottom 4% is pinned. Forward, shadow, depth and depth-normal passes share the same deformation and alpha clipping. URP fog and opaque depth allow G18's aerial perspective to fade the crowns. `_TreesPreviewClock` is a temporary capture override and is zero in normal operation.

`SceneData/Terrain_v19_i01_trees.asset` is a new copy of G18's final TerrainData. Only 1,042 Forest pine instances change prototype, yaw and uniform scale. Seed 230304; variant counts A/B/Fir/Young = 243/278/254/267; native dimensions with 0.9–1.1 scale jitter. All 8,525 tree positions and all non-target public TreeInstance fields are exactly preserved.

`Editor/G23ForestIntegrationV03.cs` is explicit integration/validation tooling, never automatic. It refuses to overwrite existing deliverables. Do not rerun the map builder for this handoff. Future v19 rebuilds need a fresh numbered scene/TerrainData and the same Forest-boundary replacement after final tree placement; see `docs/reports/TREES_FOREST_v03_INTEGRATION_i01.md`.
