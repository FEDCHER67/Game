# G23 — Pine v02 approval candidate

Pine A/B/C now have three dense, slightly offset crown tiers occupying the top 34% of the tree. Crown layers contain overlapping closed folded needle fronds and smaller needle slabs, with visible supporting branches. Trunk curves are retained; nominal trunk and main-limb radii are 15% thicker. The palette and stiff shared V19Wind settings are unchanged. Approved Oak A/B/C v01_02 were not modified or re-exported.

## Final selection and output

- `Cozy_Pines_v02_02.blend` — final three pines, three LODs each, two trunk capsule proxies each, hidden tier guides and read-only v01 references.
- `Models/Pine_A_v02_02.fbx`, `Models/Pine_B_v02_02.fbx`, `Models/Pine_C_v02_02.fbx` — final exports.
- `Cozy_Pines_Preview_v02_02.blend` — comparison studio.
- `C:/Dev/Game/Working/Reviews/Trees/pines_v02.png` — requested comparison sheet: current placeholder, Pine v01 A, Pine v02 A/B/C, unchanged approved Oak A, and a crown close-up from below.

The first v02 pass is retained. Its two-tier Pine C left too much vertical space between layers, so the separate final v02_02 pass gives every variant three tiers, with more vertical irregularity. It also forms dense cluster interiors from overlapping folded fronds instead of a separate closed cluster pad. Use only the v02_02 models from this folder as the final candidate.

## Dimensions and budgets

Every variant keeps the measured i08 pine family median: **12.986 m height and 6.861 m crown width**. Foliage runs from **8.571 m to 12.986 m**. The existing map census remains 2,009 umbrella pines. No new map measurements or scene writes were needed; source measurements are in `../oaks_pines_v01/map_sizes_v01.json`.

| Variant | Clusters v01 → v02 | Increase | LOD0 tris | LOD1 tris | LOD2 tris |
|---|---:|---:|---:|---:|---:|
| A | 30 → 42 | 40.0% | 6,468 | 3,798 | 2,662 |
| B | 36 → 50 | 38.9% | 6,788 | 4,038 | 2,710 |
| C | 30 → 42 | 40.0% | 6,804 | 4,134 | 2,662 |

B uses 50 clusters as the nearest whole-number approximation to a 40% increase. All three variants use three tiers, within the requested 2–3 range. Tier spacing, radial spread and offsets vary per tree. Each cluster contains six long folded fronds plus 8–11 smaller needle slabs at LOD0. Opaque overlapping geometry closes the interior while individual pointed silhouettes remain visible around tier edges. Small peripheral gaps and the intentional spaces between tiers remain.

Base pivots and metre units are preserved. Two capsule proxies per tree are saved in the native blend; six collider recipes with Blender/Unity coordinate fields are in `validation_v02_02.json`. The FBX files contain the three LOD render meshes, not Unity components. The lower trunk cut is flattened to the ground plane after thickening.

## Wind and palette

`wind_bindings_v02.json` reuses the existing Pine material set in `../oaks_pines_v01/WindMaterials/` without copying or changing it. Shader: `OnlyVolunteers/Wind/v02/GenericFoliage`; wind response `0.028`; flexible height `17.531229 m` at the median size. No shader or per-model wind code was added. Per-instance stiffness scaling and actual wind motion remain for the separately approved Unity integration step.

Palette unchanged: Bark `#68503C`, LeafDark `#3A6E38`, LeafPine `#2C6042`. The original closed folded-leaf/tube helper is read from `../v04/build_leafy_v04_03.py`; its asset builder is not executed.

## Checks

**PASS — Blender build/topology/budget.** `build_pines_v02_02.py`, log `build_v02_02.log`, results `validation_v02_02.json`. Every LOD0 is below 7,000 triangles; all nine meshes have no nonmanifold edges, loose vertices or degenerate faces. Dimensions and grounded pivots passed.

**PASS — FBX round trip.** `validate_roundtrip_v02_02.py`, log `roundtrip_v02_02.log`, results `fbx_roundtrip_v02_02.json`. Three FBX files were imported into fresh Blender scenes. All nine LOD meshes passed triangle counts, dimensions to 1 mm, identity scale, base pivots, UV presence, closed topology and material mappings. All six capsule recipes were valid.

**PASS — preservation.** All 2,127 files recorded by `prepare_v02.py` retained their SHA-256 hashes, including approved oaks, prior source assets and protected Unity files. Earlier numbered pine candidates remain intact.

**PASS — rendered inspection.** Both final renders were inspected. The final sheet uses the previous Hamlet light recipe and one orthographic scale of 72 pixels per metre for all six lineup trees. The underside close-up is enlarged and labelled. The current placeholder is the same representative pine_a geometry scaled to the family median; Oak A is appended unchanged from the approved source blend. These are Blender previews, not in-game shots.

**NOT RUN — Unity.** No import, shader compilation, Play test, motion check, scene change, lock acquisition or review bridge. No commits. Fedya's visual approval is the open item.

## Reproduction / execution

Blender MCP could not connect. Background fallback used installed Blender **5.2.1 LTS**, without altering a live Blender session. Commands were run from `C:/Dev/Game`:

```powershell
python ArtSource/Dev/Trees_staging/pines_v02/prepare_v02.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v02/build_pines_v02.py
python ArtSource/Dev/Trees_staging/pines_v02/refine_pines_v02_02.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v02/build_pines_v02_02.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v02/validate_roundtrip_v02_02.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v02/render_preview_v02_02.py
python ArtSource/Dev/Trees_staging/pines_v02/make_sheet_v02.py
```

Scripts refuse to overwrite numbered blend/FBX/preview deliverables. Use a new revision when rerunning generation. The first `build_v02.log` contains the caught pre-export base-pivot assertion; `build_v02_checked.log` is the corrected first-pass run. The final accepted evidence is the v02_02 set named above. Render logs include non-fatal Blender deprecation/HIP-library warnings; the final renders and saved preview completed successfully.
