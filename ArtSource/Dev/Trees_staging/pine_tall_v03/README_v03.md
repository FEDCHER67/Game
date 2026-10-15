# Pine_Tall v03 — 15–20% more branches, retained v02 foliage density

G23, 2026-10-15. Fedya accepted the density of Pine_Tall v02 and requested 15–20% more branches with that density preserved. This is a new Blender-only candidate; prior deliverables are untouched.

## Changes

Added **five main limbs and five supporting twigs per variant**, positioned at irregular heights and angles in existing crown gaps. Each new limb carries two complete clumps matching the approved density: **17 separate needle plates per clump at LOD0**, unchanged from v02. Existing trunk, main limbs, twigs, stubs and roots are retained at their original coordinates. The warm bark and LeafPine/LeafDark palette remain unchanged.

| Variant | Main branches v02 → v03 | Increase | Clumps v02 → v03 | LOD0 leaf plates | Height / crown width | LOD0 / LOD1 / LOD2 tris |
|---|---:|---:|---:|---:|---|---|
| A | 26 → 31 | 19.23% | 65 → 75 | 1,275 | 18.50 / 4.50 m | 7,510 / 4,934 / 3,144 |
| B | 28 → 33 | 17.86% | 69 → 79 | 1,343 | 20.00 / 4.90 m | 7,950 / 5,226 / 3,332 |
| C | 25 → 30 | 20.00% | 63 → 73 | 1,241 | 17.00 / 4.20 m | 7,290 / 4,788 / 3,050 |

New clumps are copied from nearby v02 clumps without thinning or reducing plate count. LOD1 and LOD2 retain the v02 densities of 9 and 5 plates per clump, respectively. Existing plate boundary vertices and clump positions are retained. To keep LOD0 below 8,000 triangles despite the extra branches, six smaller core-plate folds in each LOD0 clump use a simpler closed four-triangle shape with the same pointed rim; three larger raised folds and all eight infill plates remain. This is a topology adjustment, not a foliage-density reduction. Close-up renders retain the approved dense appearance.

Two trunk capsule proxies and recipes per variant are unchanged. Base pivots, metres, three LODs plus cull recipe, shared V19Wind bindings and stiff settings are unchanged. No per-model wind code was added.

## Deliverables

- `Cozy_PineTall_v03.blend` — editable source, 9 LOD meshes, six capsule proxies.
- `Models/PineTall_A_v03.fbx`, `PineTall_B_v03.fbx`, `PineTall_C_v03.fbx` — new exports, three LODs each.
- `Cozy_PineTall_Preview_v03.blend` — actual rendered comparison scene.
- `C:/Dev/Game/Working/Reviews/Trees/pine_tall_v03.png` — paired v02 / v03 comparisons for A/B/C, common scale and Hamlet light; matched before/after close-up.
- `Preview/PineTall_A_crown_v03.png` — additional upper-crown render.
- `validation_v03.json`, `fbx_roundtrip_v03.json`, `branch_validation_v03.json`, shared material bindings, prefab recipe, scripts and logs.

## Verification

Commands ran from `C:/Dev/Game` with Blender 5.2.1 LTS. Blender MCP was unavailable, so the project-approved background-Blender fallback was used.

**PASS — generation, geometry and branch counts.**

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v03/build_pine_tall_v03.py
```

Evidence: `build_v03.log`, `validation_v03.json`. All nine meshes have zero non-manifold edges, loose vertices and degenerate faces. All LOD0 budgets are below 8k. Branch increases are within the requested 15–20%. The prior woody vertex/face arrays are preserved verbatim before the new additions.

**PASS — FBX export and reimport.**

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v03/validate_roundtrip_v03.py
```

Evidence: `roundtrip_v03.log`, `fbx_roundtrip_v03.json`. All three FBX reimported; nine LODs match source triangle counts and dimensions within 1 mm, valid base pivots/unit scale, closed geometry, UVs and shared material remaps. All 514 protected previous deliverables, tree assets and map scene files matched their starting hashes.

**PASS — independent density and preservation checks against the v02 .blend.**

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v03/validate_branches_v03.py
```

Evidence: `branch_validation_attempt02_v03.log`, `branch_validation_v03.json`. Counts actual disconnected closed leaf components in all nine meshes; all match the required clump densities and reported totals. Every old woody vertex is retained. Six capsule proxy meshes/transforms and shared wind bindings are unchanged. Referenced staged wind materials resolve.

The first preservation-check attempt compared an unevaluated, unlinked reference object's world matrix and stopped on that assertion (`branch_validation_v03.log`). The validator now links references in its temporary scene and evaluates their matrices before comparison; the repeat passes. No model modification was required.

**PASS — rendered and visually inspected.**

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v03/render_preview_v03.py
python ArtSource/Dev/Trees_staging/pine_tall_v03/make_sheet_v03.py
```

Evidence: `render_v03.log`, rendered PNGs, `preview_manifest_v03.json`, `sheet_manifest_v03.json`. Paired full-tree renders and same-camera clump close-ups show additional branches, retained dense individual tufts, bare lower trunk and irregular sky pockets.

**NOT RUN — Unity import, Play, motion validation or i10 placement.** This is still the Blender preview stage. No Unity tools, lock operations, map changes, commits or review bridge. Await Fedya's visual approval and a separate lead go before placement.
