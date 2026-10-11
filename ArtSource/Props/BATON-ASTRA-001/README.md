# BATON-ASTRA-001

Cartoon rubber police baton with one perpendicular tonfa handle. Clean charcoal rubber, broad round forms and smooth shading; no logos or fine surface noise. Target final budget: **200–500 triangles**.

## Reference design

55 cm overall length; main shaft nominal 4 cm diameter; 14 cm primary grip with three broad shallow rings; one 14 cm side handle with rounded end. Side handle axis 16 cm below the upper end. Entire item is one rubber prop, with slightly lighter grips.

Four square orthographic references made in ordinary ChatGPT: FRONT, LEFT, RIGHT, BACK. Upright pose, grey background, soft studio lighting. The pack is **Source/TripoViews/Rev04/**, all four PNGs 1254×1254. **Approved here by Claude on behalf of Fedya, 2026-10-05.**

| Tripo slot | Exact candidate |
| --- | --- |
| Front | Source/TripoViews/Rev04/01_front.png |
| Left | Source/TripoViews/Rev04/02_left.png |
| Right | Source/TripoViews/Rev04/03_right.png |
| Back | Source/TripoViews/Rev04/04_back.png |

FRONT is unchanged from Rev01, LEFT from corrected Rev02, BACK from Rev03; RIGHT Rev04 enlarges the circular side-handle end. Earlier candidates are preserved. Source/reference_manifest_Rev04.json records exact hashes and sizes. See PROVENANCE.md and REPORT.md.

## Finished asset

- **BATON_ASTRA_001_v02.blend** and matching FBX: **494 triangles**, smooth shading, matte black rubber.
- 0.55 m height, 0.176 m width, 0.05 m maximum depth; origin at the lower shaft tip, front −Y, side handle +X.
- One closed connected mesh, one material and UV set; locally baked 512px base-colour atlas packed in Blender and embedded in FBX.
- Six orthographic previews and hero image: Previews/*_v02.png. Mesh and independent FBX reimport checks both PASS.
- The hidden REFERENCE_Tripo_source_not_exported collection retains the source geometry for comparison. Export only Item_Baton; reference geometry and presentation lights/camera are excluded from FBX and final triangle count.
- Local v01 is preserved. V02 replaces reduction artefacts with source-fitted connected loop retopology and restores three broad sections on each grip.

One Smart Mesh / quads / P2.0 multi-view generation, target500, Create exactly100. Cost100; balance680 → **580**. All four inputs cleared. Original FBX retained unchanged at Working/Tripo/baton_tripo_base.fbx. No repeat generation or paid extras. See PROVENANCE.md and REPORT.md for evidence.
