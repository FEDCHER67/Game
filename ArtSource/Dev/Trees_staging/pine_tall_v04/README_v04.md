# Pine_Tall v04 — approximately 40% fuller than approved v03

G23, 2026-10-15. Blender-only response to Fedya's request for more intermediate branches, some additional branch length and more foliage, producing approximately 40% greater fullness overall.

**Final candidate: PineTall A/B/C v04_04.** Previous approved v03 and all numbered development candidates remain preserved. No Unity import, lock operation, map placement, commits or review bridge.

## Result

Eight new main branches and two intermediate twigs per tree fill irregular gaps between existing branches. Existing side branches extend radially by 12%. Each tree has ten additional foliage clumps, retaining 17 separate opaque needle plates per LOD0 clump. Individual clumps are also fuller: their linear scale increases by 21.3% / 23.5% / 18.0% for A/B/C, tuned against the combined silhouette rather than applying a fixed count increase alone.

Height, trunk, roots, dead stubs, bare lower trunk, palette, two trunk capsules per tree and shared stiff V19Wind bindings remain unchanged. Crowns become roughly 15% wider; this follows the new request to extend side branches rather than enforcing the older width envelope.

| Variant | Main branches v03 → v04 | Clumps v03 → v04 | LOD0 plates v03 → v04 | Height | Crown width v03 → v04 |
|---|---:|---:|---:|---:|---:|
| A | 31 → 39 | 75 → 85 | 1,275 → 1,445 | 18.50 m | 4.50 → 5.175 m |
| B | 33 → 41 | 79 → 89 | 1,343 → 1,513 | 20.00 m | 4.90 → 5.630 m |
| C | 30 → 38 | 73 → 83 | 1,241 → 1,411 | 17.00 m | 4.20 → 4.812 m |

| Variant | Mean foliage silhouette increase | LOD0 | LOD1 | LOD2 |
|---|---:|---:|---:|---:|
| A | +39.5% | 7,544 | 5,570 | 3,532 |
| B | +39.7% | 7,936 | 5,862 | 3,720 |
| C | +39.7% | 7,348 | 5,424 | 3,438 |

“Fullness” has no unique physical unit. The quantitative comparison is the union area of the opaque foliage silhouette, viewed orthographically from four azimuths (0°, 45°, 90°, 135°), at identical scale, 50 pixels/metre. The table averages the four relative increases for each variant. This supports the requested approximate visual change; it is not a claim of 40% more wood, branches or physical volume. See `fullness_measurement_v04_04.json` and the before/after diagnostic silhouette PNGs.

To retain the existing sub-8k LOD0 budget without removing needle plates, all LOD0 plates use closed four-triangle folded lances. Branch cross-section tessellation is reduced on small limbs only. The main trunk, roots and dead stubs retain their previous geometry. LOD1/2 keep 9/5 plates per clump. Base pivots, metre units, three LODs and the cull recipe remain.

## Deliverables

- `Cozy_PineTall_v04_04.blend` — final editable source.
- `Models/PineTall_A_v04_04.fbx`, `PineTall_B_v04_04.fbx`, `PineTall_C_v04_04.fbx` — final exports, three LODs each.
- `Cozy_PineTall_Preview_v04_04.blend` — comparison scene.
- `C:/Dev/Game/Working/Reviews/Trees/pine_tall_v04.png` — v03/v04 pairs for A/B/C and matched close-up, Hamlet lighting and common scale.
- `prefab_recipe_v04_04.json`, `wind_bindings_v04_04.json`, `validation_v04_04.json` — final native widths, unchanged capsules/material bindings and measurements.
- `Preview/PineTall_A_crown_v04_03.png` — additional crown close-up. The rendered v04_03 geometry is identical to final v04_04; only object revision names and native-width metadata were corrected. Nine mesh fingerprints in `geometry_identity_v04_04.json` verify this identity.

Use only the final `_v04_04` model exports. Earlier v04 / v04_02 / v04_03 files are preserved development studies. Initial measured increases were 26–33%; the second pass reached 35–37%; the final geometry reaches 39–40%.

## Verification

All commands ran from `C:/Dev/Game`, using `C:/Program Files/Blender Foundation/Blender 5.2/blender.exe` (5.2.1 LTS). Local background Blender was used; the previously unavailable live bridge was not required.

**PASS — model generation and real render.**

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v04/build_pine_tall_v04_03.py
python ArtSource/Dev/Trees_staging/pine_tall_v04/measure_fullness_v04_03.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v04/render_preview_v04_03.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v04/finalize_v04_04.py
```

Evidence: `build_v04_03.log`, `render_v04_03.log`, `finalize_attempt02_v04_04.log`, source JSON and PNGs. Nine meshes have no non-manifold edges, loose vertices or degenerate triangles. Same-camera renders and the final sheet were visually inspected. Fuller crowns retain irregular pockets and exposed branches rather than forming smooth cones.

The first metadata-finalization attempt expected a `_v04_03` object suffix, while the source mesh objects still used `_v04_LOD`. It stopped before writing the final candidate. The corrected finalizer normalizes object names and native-width custom properties. Initial diagnostic logs remain; the second run passes.

**PASS — final FBX roundtrip and independent structure checks.**

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v04/validate_roundtrip_v04_04.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v04/validate_structure_v04_04.py
python ArtSource/Dev/Trees_staging/pine_tall_v04/make_sheet_v04.py
```

Evidence: `roundtrip_attempt02_v04_04.log`, `fbx_roundtrip_v04_04.json`, `structure_validation_v04_04.log`, `structure_validation_v04_04.json`. All three final FBX reimported, with all nine LOD triangle counts, dimensions (within 1 mm), UVs, base pivots, unit scale, closed geometry and material remaps verified. Actual disconnected leaf-component counts match the plate totals. Each tree gains ten woody components (eight main branches plus two twigs). Trunk/root/stub geometry and all six capsule proxy meshes/transforms are identical to v03. Shared wind bindings are identical. Final native-width metadata matches actual geometry.

All 543 protected previous deliverables, tree assets and map scene files match their starting hashes.

**NOT RUN — Unity, Play, wind motion or i10 placement.** This remains the Blender approval stage. Await visual approval and the separate placement go.
