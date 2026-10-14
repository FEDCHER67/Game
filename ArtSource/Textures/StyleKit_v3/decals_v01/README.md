# G17 — Ground wear and litter decals v01

Original procedurally painted textures for the Hamlet and Rough District map pilots. Created with Python, NumPy and Pillow; no photographs, downloaded imagery, external generation services or Unity execution. All task writes are contained in this `decals_v01/` folder. No files were deleted, staged or committed.

## Files and scale

Paths below are relative to `ArtSource/Textures/StyleKit_v3/decals_v01/`. Dimensions are width × height. All PNGs are 8-bit RGBA; albedos and the review sheets carry an explicit sRGB PNG chunk. Normals are **linear data**, not sRGB albedo.

| File | Pixels / format | World scale | Intended use and alpha |
| --- | --- | --- | --- |
| `LITTER_ATLAS_v01.png` | 2048 × 2048, 4 × 4 cells | Each 512 px cell = 0.50 × 0.50 m | Individually selected static decals. Transparent cells, centred items, antialiased silhouettes. Opaque small litter; oil uses low coverage. |
| `LITTER_ATLAS_v01.json` | JSON | Cell and visible item dimensions in metres | UV rectangles, top-left pixel rectangles, item IDs, nearby placement guidance and nominal individual object sizes. |
| `WHEEL_TRACKS_DIRT_v01_albedo.png` | 1024 × 2048 | 3 × 6 m; 2.4 m rut centre-to-centre gauge | Repeating terrain overlay or elongated decal. Two compacted ruts; transparent middle and outer margins, soft irregular edges. |
| `WHEEL_TRACKS_DIRT_v01_normal.png` | 1024 × 2048 | Matches rut albedo exactly | Soft tangent-space normal, 7.5 mm authored depression. Same coverage alpha as albedo. |
| `WORN_PATH_v01_albedo.png` | 512 × 2048 | 1.2 × 4 m | Repeating footpath overlay or elongated decal. Bare-earth core, olive transition and irregular transparent margins. |
| `WORN_PATH_v01_normal.png` | 512 × 2048 | Matches path albedo exactly | Soft tangent-space normal, 4.5 mm authored depression. Same coverage alpha as albedo. |
| `GROUND_WEAR_PATCHES_v01.png` | 1024 × 1024, 2 × 2 cells | Each 512 px cell = 1.50 × 1.50 m | Individually selected localized ground decals. Irregular soft coverage; quieter than the surrounding route layout. |
| `CONCRETE_CRACKS_STAINS_v01.png` | 1024 × 1024, 2 × 2 cells | Each 512 px cell = 1.50 × 1.50 m | Individually selected courtyard decals. Thin crack and low-opacity rust/water marks; restrained asphalt patch. |
| `decals_v01.json` | JSON | All strips and 2 × 2 atlas cell scales | Pack metadata, palette anchors, atlas UVs, wrap directions and normal convention. |
| `previews/decals_v01_on_surfaces.png` | 1600 × 1600, RGBA | Actual base/decal metre ratios within every panel | **Final review sheet.** All litter and wear cells, both strips on grass and dirt, and shaded normal/seam crops. Sheet alpha is opaque. |
| `tools/make_decals_v01.py` | Python | Fixed seed `170013` | Re-runnable generator and in-memory checks; only writes inside this folder and refuses existing output files. |
| `validation_v01.json` | JSON | Per-texture measurements | Dimensions, alpha coverage, seams, normals, palette, contrast, output hashes and reference hashes. |
| `verification_audit_v01.json` | JSON | Export audit | Recorded deterministic rerun, decoded PNG colour-space checks, reference/hash comparison, overwrite refusal and visual inspection. |
| `previews/review_01.png` | 1600 × 1600, RGBA | Same metre ratios as final sheet | Superseded work-in-progress review, retained under the no-deletion rule. Its oil edge was corrected in the final sheet. Do not use it as the final reference. |

The path's 1.2 m width describes its whole footprint, including transparent margins; its exposed-earth core is narrower. Rut centres share a subtle bend while remaining exactly 2.4 m apart throughout the 6 m repeat. Approximate visible rut widths vary around 0.3 m.

## Atlas contents and UVs

Cells are numbered from the PNG's top-left, left to right, then downward. JSON `uv_rect` is **[u_min, v_min, width, height]**, with the UV origin at bottom-left. Consequently, top-left litter cell 01 has `[0, 0.75, 0.25, 0.25]`; bottom-right cell 16 has `[0.75, 0, 0.25, 0.25]`. Use the supplied rectangles rather than treating the entire atlas as a world-sized decal.

| Litter row | Column 1 | Column 2 | Column 3 | Column 4 |
| --- | --- | --- | --- | --- |
| 1 | Single cigarette end | Five cigarette ends near a bench | Bottle cap | Two bottle caps |
| 2 | Crumpled wrapper | Flattened can | Bottle-glass scatter | Sunflower-seed husks |
| 3 | Three dry leaves | Small paper scrap | Chewing-gum spot | Oil stain |
| 4 | Single dry leaf | Torn wrapper | Folded paper scrap | Small husk cluster |

Representative unrotated dimensions are 35 × 8.5 mm for a cigarette end, 29 mm diameter for a cap, 15.5 × 6.5 mm for a husk and 120 × 65 mm for the flattened can. `intended_item_size_m` records each cell's visible image-axis bounding box at alpha ≥ 8/255, including cluster gaps and object rotation. Individual objects are intentionally small inside their 0.5 m cells, not scaled up to fill them.

`GROUND_WEAR_PATCHES_v01` order: top-left trampled grass; top-right muddy puddle edge; bottom-left gravel spill; bottom-right bare earth. `CONCRETE_CRACKS_STAINS_v01` order: top-left branching crack; top-right rust drip; bottom-left wall-foot water stain; bottom-right patched pothole. Their UVs and 1.5 m footprints are in `decals_v01.json`.

## Placement and rendering notes

- Hamlet: use wheel tracks on grass/dirt at actual vehicle access, footpaths between gates and entrances, and small wear patches at repeated stopping or walking points. Leave quiet ground between placements.
- Rough District: use cigarette/husk clusters near benches, caps and wrappers near service points, and selected courtyard cracks and repair patches. Align the rust mark below a relevant pipe or metal contact; place the water stain against a wall foot. Avoid blanket coverage or evenly scattered litter.
- G17 explicitly requests cracks, stains and a puddle edge. These are localized exceptions to the general prohibition in `docs/ArtDirection.md`, not a change to the project's overall surface treatment. No black AO, baked cast shadows, photo grime or per-pixel noise was added.
- Albedo uses straight/unassociated alpha. Blend by its alpha; do not multiply the stored RGB by alpha a second time. Transparent padding carries colour, with 12-pixel local RGB dilation and at least 12 fully transparent pixels at cell boundaries.
- Clamp atlas addressing. Keep filtering within the selected cell and retain its padding; avoid a full-atlas repeat. Very distant atlas mip levels can still merge adjacent cells, so atlas-safe mip handling and engine compression need review at integration.
- Strip wrap is **U Clamp, V Repeat**. Only V is intended to tile. Albedo and normal first/last V rows match exactly in all four channels. The middle between wheel ruts is transparent, retaining the existing ground.
- Normals encode tangent-space **+Y**, with green toward increasing V/up the PNG; transparent texels are `(128,128,255,0)`. Import as a normal/data texture, use coverage from the albedo, and blend with the underlying surface normal. Alpha is coverage, not smoothness or height. Use restrained normal strength; these are visual overlays, not terrain displacement or collision.
- No normal maps are needed for the three small-mark atlases. No metallic, roughness, smoothness or emissive maps are included.

## Palette and preview construction

The generator reads mean sRGB values directly from `candidate_v07/grade_v07.json`: grass `#6F804D`, dirt `#91775E`, gravel `#9C9EA1`, mud `#6E5344`, asphalt `#5F666C`, sidewalk `#BDB5A8`, concrete `#ADABA6` and metal `#8E9396`. Colours are mixtures or restrained offsets around those anchors. Albedo RGB is capped at 209/255, including antialiasing and transparent padding.

The final sheet uses the actual v07 grass, dirt road, gravel, asphalt, sidewalk and concrete albedos. Base tiling comes from `materials_v3_v07.json`: grass/dirt/gravel/sidewalk repeat every 2 m; asphalt/concrete every 3 m. Base and decal metres are matched 1:1, with isotropic scale in each panel; the printed ruler and panel scale vary to accommodate long strips and tiny litter. The litter panels use 268 px/m, rut panels 70 px/m, path panels 105 px/m and wear panels approximately 146.7 px/m. This is a scale-correct top-down comparison, not a claim of physical monitor size or a Unity camera render.

Compositing decodes the sRGB inputs, blends in linear light, then re-encodes sRGB. Two small grass panels apply neutral raking light to the decoded normals across a V seam. The other panels show unlit albedo. No scene exposure, fog, tone mapping or engine lighting is simulated.

## Reproduction

Run from `C:\Dev\Game` using the already available environment (Python 3.12.10, NumPy 2.5.4, Pillow 12.3.0 for this export; exact runtime is also recorded in `validation_v01.json`):

```powershell
python ArtSource/Textures/StyleKit_v3/decals_v01/tools/make_decals_v01.py --check-only
```

This regenerates everything twice in memory, validates it and compares all 11 generated export files byte for byte against the saved delivery. It writes nothing. A plain invocation generates those files only when they do not exist; it refuses the complete batch before writing if any output already exists. `--review NEW_NAME.png` can save a new named review sheet without touching any existing file. README and the independent audit are reports, not generator outputs.

If dependencies are unavailable, the equivalent fixed-version invocation is:

```powershell
uv run --with numpy==2.5.4 --with pillow==12.3.0 ArtSource/Textures/StyleKit_v3/decals_v01/tools/make_decals_v01.py --check-only
```

No installation or download was required for this task. Use the recorded versions for byte-identical PNG reproduction.

## Checks and remaining review

- **PASS — generation and determinism.** The generator and the `--check-only` command above ran successfully. Two independent builds matched; all 11 saved generated files were byte-identical to regeneration.
- **PASS — dimensions and channels.** Every image decoded as RGBA at its specified resolution. All export albedos/previews have sRGB tags; normals have linear-data metadata and no sRGB tag.
- **PASS — transparency and layout.** All 24 atlas cells contain marks with transparent gutters; all 16 litter cells are centred. UV-to-pixel conversion, 0.5 m litter footprints, strip aspect scales and the 2.4 m gauge were checked.
- **PASS — seams and normals.** Both strip pairs have exact V endpoint equality and transparent U margins. Normal alpha equals albedo alpha; unit-vector error remains below 0.008 after 8-bit encoding. Maximum authored normal tilt is 4.50352° for wheel tracks and 2.08314° for the footpath.
- **PASS — palette and contrast measurements.** The albedo value cap was checked. Courtyard crack/stain/patch peak composited luma changes are approximately 9–16/255 on their matching surfaces, with cell averages below 2.8/255. Small light paper marks have higher local contrast but occupy only about 2–2.5% of their cells. Detailed per-item figures are in `validation_v01.json`.
- **PASS — saved-file audit and preservation.** All generated content hashes and the generator hash matched. All 15 recorded reference hashes still matched after export. A plain generation attempt with existing files failed as intended; every existing output byte was preserved. See `verification_audit_v01.json`.
- **PASS — offline visual review.** The final `previews/decals_v01_on_surfaces.png` was opened and inspected: all cells, matched surfaces, true item proportions, quiet areas, soft edges and repeat-seam crops. The oil halo seen in the retained first review was removed before final export.
- **NOT RUN — Unity import, lighting, mip/compression and nearby player-camera checks.** Unity was explicitly prohibited. v07 remains a palette candidate; these files do not certify its artistic acceptance. Final placement density and player-scale readability remain for the Hamlet and Rough District pilot integration review.
