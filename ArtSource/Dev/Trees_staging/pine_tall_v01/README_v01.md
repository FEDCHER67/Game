# G23 — Pine_Tall v01 approval preview

2026-10-15. **Final candidate: A/B/C v01_02.** The initial v01 build and its previews remain preserved; only v01_02 appears in the requested review sheet. Blender-only after completing i09 and releasing the Unity lock. No Pine_Tall assets imported, no i10 scene or placement, no commits or review bridge.

## Deliverables

- Source: `Cozy_PineTall_v01_02.blend`; separate lit preview: `Cozy_PineTall_Preview_v01_02.blend`.
- Exports: `Models/PineTall_A_v01_02.fbx`, B and C; three LOD meshes each.
- Sheet: `C:/Dev/Game/Working/Reviews/Trees/pine_tall_v01.png`.
- Scripts/logs: `build_pine_tall_v01_02.py`, `render_preview_v01_02.py`, `validate_roundtrip_v01_02.py`, their numbered logs, plus `make_sheet_v01.py`.
- Validation: `validation_v01_02.json`, `fbx_roundtrip_v01_02.json`, `prefab_recipe_v01.json`, `wind_bindings_v01.json`, `delivery_manifest_v01.json`.

The supplied reference `ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png` was opened and studied, then included in the internal review sheet. It is a structural reference, not a metrically scaled model or a shipped texture. Geometry is original; no external model files were copied.

## Design and dimensions

Narrow, loosely conical crown; irregular horizontal branches with terminal and outer-branch needle clumps, sky pockets, pointed leader, bare lower third and short dead stubs. Uses the same closed folded-frond mesh construction as approved Pine v04, with LeafPine `#2C6042`, LeafDark `#3A6E38`, and slightly warmer Bark `#76503E`. No smooth crown shell or alpha cards.

| Variant | Height / crown width m | Clumps | Main branches | Dead stubs | LOD0 / LOD1 / LOD2 tris |
|---|---|---:|---:|---:|---|
| A | 18.5 / 4.5 | 65 | 26 | 5 | 6,410 / 3,914 / 2,614 |
| B | 20.0 / 4.9 | 69 | 28 | 7 | 6,842 / 4,182 / 2,794 |
| C | 17.0 / 4.2 | 63 | 25 | 4 | 6,194 / 3,780 / 2,524 |

The initial render had overly regular vertical spacing. The numbered v01_02 refinement uses more staggered branch levels and outer-branch clumps without changing the intended height/width range. All initial deliverables remain unchanged.

## Import recipe and wind

Metres, base pivot, identity mesh transforms, FBX -Z forward / Y up, unit scale 1. Three LODs plus cull; two trunk capsule recipes per variant, with hidden wire proxies in the source. Capsule centres/axes in both Blender and Unity coordinates are in the validation and prefab recipe. Botanical component overlaps at branch joints are intentional. UVs intentionally overlap because this is a flat-colour palette material set.

Three staged materials under `WindMaterials/` bind the existing **OnlyVolunteers/Wind/v03/GenericFoliageScaled**, i08's instance-height-aware revision of GenericFoliage. They reuse `V19Wind.hlsl`; there is no model-specific wind code. Response **0.028**, local flexible height **24.3 m**, vertex mask/tint off, opaque/backface culling, tip flash 0.025. The shared shader scales stiffness with the instance matrix; intended eventual placement scale is 0.9–1.1. Runtime sway, shadows/fog and collider behavior for Pine_Tall remain **NOT RUN pending approval and integration**.

## Checks

**PASS — Blender 5.2.1 LTS build:** all nine meshes below 8,000 triangles, zero non-manifold edges, loose vertices or degenerate faces; intended dimensions and zero-height bases verified. Three numbered FBX exports completed.

**PASS — fresh FBX reimport:** all nine LODs retain triangle counts, dimensions within 1 mm, metre scale, base pivots, UVs and material remaps. Six capsule recipes have valid radii/heights and normalized axes.

**PASS — visual inspection:** common-scale lineup and two close-ups rendered in Cycles and inspected. Same Hamlet light, AgX view and exposure as the earlier approved Pine v04 sheet. Pine v04 A, Forest Fir v03_04 and Poplar A v04_04 were appended read-only at their native metre sizes, not rebuilt or exported. Their apparent sizes differ because Pine_Tall is intentionally 17–20 m tall.

**PASS — scoped preservation:** both FBX roundtrip checks found all 2,442 protected project files unchanged. The final check found **2,441 unchanged and one unrelated workspace change** to `Assets/OnlyVolunteers/Inventory/Runtime/WorldItem.cs`, after those checks. G23 made no writes to that inventory file and left it untouched. All protected tree assets, i09 TerrainData/scene, prefabs/materials and earlier models remain unchanged, as do the initial Pine_Tall v01 files. Exact drift is recorded in `preservation_final_v01.json`. Blender MCP was unavailable; the documented background Blender fallback was used. The log's HIP initialization warning is unrelated to the selected NVIDIA OptiX rendering; all PNGs rendered successfully.

## Approval gate

STOP for Fedya's review of `pine_tall_v01.png`. Addendum 3's north/west slopes, irregular Forest edge and modest interior mixture are recorded as the future i10 scope. No placement begins before the lead sends the separate go. Future placement must use the actual map-plan/patch/finish boundaries and i09 TerrainData, add instances only, respect the specified exclusions, and leave every existing i09 tree/rock unchanged.
