# G13 — v03 to v04: changed files only

Four requested fixes affect five categories. Added 15 numbered 1024² textures; the other 18 manifest entries retain their exact v03 data and paths. Prior source, texture, script and JSON payload hashes match the pre-generation snapshot. No staging, commits, deletion, source downloads or worker writes to old deliverables.

| Category | Visual/content delta | New texture files | v04 material |
|---|---|---|---|
| `1b_dirt_road` | sand #F1DEAC → existing wood.light #AB825B: distinct warm earth brown-ochre, between sand and mud. Normal/mask copied unchanged. | [albedo](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/1b_dirt_road/1b_dirt_road_v04_albedo.png) · [normal](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/1b_dirt_road/1b_dirt_road_v04_normal.png) · [mask](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/1b_dirt_road/1b_dirt_road_v04_mask.png) | [M3_1b_dirt_road_v04.mat](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Materials/M3_1b_dirt_road_v04.mat) |
| `4c_corrugated_metal` | Soft ridge stripes ±6% value, 26 cycles across 1.976 m = exactly 7.6 cm pitch; OpenGL ridge normal from 4 mm height amplitude. Mask copied unchanged. | [albedo](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/4c_corrugated_metal/4c_corrugated_metal_v04_albedo.png) · [normal](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/4c_corrugated_metal/4c_corrugated_metal_v04_normal.png) · [mask](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/4c_corrugated_metal/4c_corrugated_metal_v04_mask.png) | [M3_4c_corrugated_metal_v04.mat](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Materials/M3_4c_corrugated_metal_v04.mat) |
| `3b_plaster_stucco` | Large, soft periodic painted tonal patches, ±5% value. Normal/mask copied unchanged. | [albedo](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/3b_plaster_stucco/3b_plaster_stucco_v04_albedo.png) · [normal](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/3b_plaster_stucco/3b_plaster_stucco_v04_normal.png) · [mask](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/3b_plaster_stucco/3b_plaster_stucco_v04_mask.png) | [M3_3b_plaster_stucco_v04.mat](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Materials/M3_3b_plaster_stucco_v04.mat) |
| `3c_concrete_panels` | Large patches ±5% value; faint grid seams every 1.5 m (2×2 panels in a 3×3 m tile), seam shade 2.5%, lower-edge shade 1.8%. Normal/mask copied unchanged. | [albedo](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/3c_concrete_panels/3c_concrete_panels_v04_albedo.png) · [normal](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/3c_concrete_panels/3c_concrete_panels_v04_normal.png) · [mask](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/3c_concrete_panels/3c_concrete_panels_v04_mask.png) | [M3_3c_concrete_panels_v04.mat](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Materials/M3_3c_concrete_panels_v04.mat) |
| `2a_asphalt` | Keeps the calm v03 despeckled surface; adds only broad periodic patches ±3% value. Normal/mask copied unchanged. | [albedo](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/2a_asphalt/2a_asphalt_v04_albedo.png) · [normal](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/2a_asphalt/2a_asphalt_v04_normal.png) · [mask](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/2a_asphalt/2a_asphalt_v04_mask.png) | [M3_2a_asphalt_v04.mat](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/Materials/M3_2a_asphalt_v04.mat) |

## Added supporting files

| Added file(s) | Delta |
|---|---|
| [materials_v3_v04.json](C:/Dev/Game/Assets/OnlyVolunteers/Art/StyleKit_v3/materials_v3_v04.json) | New manifest: only the five rows above point to v04; corrugation tile becomes 1.976×2 m and concrete becomes 3×3 m. Existing builder selects the greatest revision automatically; no C# source edit. |
| [contact_v04.png](C:/Dev/Game/ArtSource/Textures/StyleKit_v3/previews/contact_v04.png) | Updated complete 2×2 tiled, labelled sheet with the five v04 replacements. |
| [diff_v04.png](C:/Dev/Game/ArtSource/Textures/StyleKit_v3/previews/diff_v04.png) | Five-category old/new albedo comparison with final normal maps. |
| [offset_index_v04.png](C:/Dev/Game/ArtSource/Textures/StyleKit_v3/previews/offset_index_v04.png) | Half-offset overview for the changed sets. |
| `ArtSource/Textures/StyleKit_v3/previews/offset_v04/{category}_offset.png` for the five listed categories | Five new full-size half-offset albedo/normal/mask images; 512 px offset. |
| [process_v3_v04.py](C:/Dev/Game/ArtSource/Textures/StyleKit_v3/tools/process_v3_v04.py) | Deterministic, exclusive-write delta generator over the preserved v03 implementation and images. |
| [verify_v04_v02.py](C:/Dev/Game/ArtSource/Textures/StyleKit_v3/tools/verify_v04_v02.py) | Verifies payload immutability separately from external Unity import metadata; checks actual built v04 material GUIDs and scale. |
| [validation_v04.json](C:/Dev/Game/ArtSource/Textures/StyleKit_v3/validation_v04.json) | Initial successful 69-map seam/data check, deterministic five-set re-render and full prior-file hash snapshot, taken before the external Unity import. |
| [validation_v04_check02.json](C:/Dev/Game/ArtSource/Textures/StyleKit_v3/validation_v04_check02.json) | Final successful check: all image/source/script/JSON payloads unchanged, explicit external metadata differences, and five observed v04 material checks. |
| `ArtSource/Textures/StyleKit_v3/tools/offline_v04/compile_v04.rsp`, `compile_v04.log`, `StyleKitV3MaterialBuilder_v04.dll` | Fresh C# 9 offline compile of the existing auto-latest builder against Unity 6000.5.11f1: exit 0. Twelve CS0649 warnings are JsonUtility-filled fields. |
| `ArtSource/Textures/StyleKit_v3/G13_DIFF_v04.md` | This delta-only report. |

## Checks and external Unity build

All 69 textures referenced by the mixed manifest passed 1024² format, RGB/RGBA, unit normal, mask layout, archive/original hash and exact opposite-edge checks. The five revised sets regenerate byte-for-byte. Corrugation frequency is 26 cycles/tile and the physical period is 0.076 m. Ridge tangent slope RMS increased from 0.012060 to 0.165115. Concrete panel spacing is exactly 1.5 m. The final contact sheet and offset overview were inspected visually.

During this run, an external live Unity operation generated `Assets/OnlyVolunteers/Art/StyleKit_v3/materials_built_v01.json` from the new revision-4 manifest. The five requested `.mat` files listed in the table now exist. Their albedo/normal/mask GUIDs, URP keywords, BumpScale=1 and metric tiling were inspected and match v04. This worker did not launch Unity or invoke the menu.

The same external operation changed 54 pre-existing v03 texture `.meta` files and generated new texture/material metadata. They were left untouched by this worker and are recorded separately in validation_v04_check02.json, outside the authored delta. The original strict all-file preservation recheck detected those metadata differences; the final scoped check passed for every pre-existing non-metadata payload. No v03 texture PNG, script, manifest or preview was overwritten.

Still open: appearance under the actual map lighting and scene assignments have not been playtested here. No further files were changed for these checks.
