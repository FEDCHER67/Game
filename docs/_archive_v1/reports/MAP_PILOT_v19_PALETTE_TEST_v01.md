# G18 checkpoint P — district palette preview v01

Date: 2026-10-14 (Europe/Moscow). Status: **READY FOR FEDYA'S REVIEW; G18 STOPPED AT CHECKPOINT P.**

This preview applies the complete ten-district palette table supplied by the lead on 2026-10-14. It is a separate palette test of the saved **v18 style-v3** layout. It is not the finished v19 layout, terrain or route result. No legacy look menu was used.

## Review outputs

All sheets show **current v18 style v3 | new v19 palette**, with matching camera positions, rotations, eye height, FOV, render pipeline and 1920 × 1080 source captures.

| Sheet in `Working/Reviews/Map_v19_Pilots/` | Views |
| --- | --- |
| `palette_test_hamlet_v01.jpg` | Five Hamlet review poses: main street, B02, pond, bypass approach, church corner |
| `palette_test_rough_v01.jpg` | Five Rough District review poses: entrance, B03 courtyard, garages, inner lane, north edge |
| `palette_test_downtown_v01.jpg` | Three Downtown spots: boulevard, north street, inner street |
| `palette_test_other.jpg` | One view each of Forest, Construction, Industrial Port, Elite Hill, Quiet Valley, City Beach and Tramduro |

Camera definitions: `palette_poses_v01.json`. Full-resolution images: `palette_current_v01_*.png` and `palette_new_v01_*.png` (20 of each). The ten Hamlet/Rough poses retain their original review definitions; ten added poses cover Downtown and the other districts. Sheets were inspected visually. Fedya's subjective approval remains pending.

Saved preview scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v01.unity`.

## Implementation

New code and assets only:

- `Assets/OnlyVolunteers/Map/LookV3/Editor/V19PaletteTest.cs`: checkpoint builder and matched capture helper. The builder requires a clean, saved v18 source and refuses an existing output revision. It does not run layout, police, crowd, audio or legacy look builders.
- `Assets/OnlyVolunteers/Map/LookV3/Palette19/DistrictAtmosphere19.cs`: camera-dependent atmosphere, active in edit and Play modes, including offscreen review cameras. It restores the previous fog state after each camera render.
- `Assets/OnlyVolunteers/Map/LookV3/Palette19/V19PaletteSurface.shader`: style-v3 surface variant with a continuous world-space palette field and a legacy colour endpoint.
- `Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v01/`: preview-owned terrain, palette field, 63 surface material variants, grass and tree prefab/material copies, and eleven Volume profiles.

Ground blends the eight original v07 terrain layers with eight preview-owned copies of the actual legacy terrain layers from the Map Look registry. The 16-layer splat uses the district blend value at every terrain sample. Walls and roofs blend their existing textured v3 albedo toward the legacy look data's building colours or legacy material-family swatches. Grass tufts use the same continuous field. Existing road markings, glass, signs and gameplay props retain their authored colours.

The legacy fruit trees were already present in v18 style v3. The preview reuses their exact meshes and colours via owned prefab/material copies: `Assets/OnlyVolunteers/Art/Map/Prefabs/TREES/tree_apple_a.prefab` and `tree_apple_b.prefab`, originating in `TR_AppleTree_A/B`, with `MP_Bark`, `MP_Leaf`, `MP_Leaf_Dark` and `MP_Fruit_Red`. There are **161 apple trees in the Hamlet lookup rectangle**. These vegetation albedo endpoints are identical in v18 style v3 and the legacy registry, so their palette interpolation is a no-op; local lighting produces the visible difference. The preview retains all tree positions, hedges and fence geometry. No shared legacy `Look_mat_*`, MP material, v07 texture, v17 asset or v18 scene was edited.

Each district has a local URP Volume with exposure, saturation, contrast and white balance; blend distance is 60 m. A lower-priority transition Volume supplies intermediate daylight. The original v17 sky, sun and ACES profile remain the foundation. The brightest exposure is Hamlet; the lowest is shared by Rough District and Forest. This constrains the lighting recipe, not the luminance of every differently coloured object in the map.

The source plan currently provides district lookup rectangles, not approved organic district outlines. Their cores are inset by 15 m. Outside those cores, normalized inverse-square distance weights smoothly blend neighbouring palettes and haze. Within a core, its exact table value applies. The same field drives surface materials, terrain splats and atmosphere. Linear fog uses blended **effective haze density = 1 / (end − start)**, avoiding abrupt fog-mode changes. Forest and Rough District share the highest haze density; canopy shadows supply the Forest's darker local shading.

| District | t in core | Exposure EV | Saturation | Contrast | White balance temperature | Fog start/end m |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Hamlet | 0.80 | 0.70 | 6 | 3 | 4 | 95 / 520 |
| Elite Hill | 0.75 | 0.64 | 5 | 3 | 3 | 90 / 490 |
| Quiet Valley | 0.75 | 0.64 | 4 | 2 | 5 | 90 / 490 |
| City Beach | 0.75 | 0.68 | 4 | 2 | 7 | 95 / 510 |
| Downtown | 0.60 | 0.55 | 10 | 5 | 3 | 90 / 480 |
| Construction | 0.60 | 0.43 | 0 | 0 | 2 | 55 / 370 |
| Tramduro | 0.60 | 0.43 | -2 | -2 | 0 | 60 / 385 |
| Industrial Port | 0.55 | 0.32 | -4 | -5 | -6 | 40 / 310 |
| Rough District | 0.50 | 0.22 | -7 | -12 | -3 | 22 / 245 |
| Forest | 0.50 | 0.22 | -7 | -12 | -3 | 22 / 245 |

The former dark v18 grade is exposure 0.15, saturation -15, contrast 8. The new darkest districts therefore remain brighter than that old baseline while being the darkest members of the new district set.

## Verification

| Check | Result and evidence |
| --- | --- |
| Compilation and shader rendering | **PASS** in the open Unity 6000.5.11f1 editor via the configured unityMCP bridge; `refresh_unity(scope="all", mode="force", compile="request")`, followed by `read_console(types=["error"])`: zero errors. Existing obsolete-API warnings remain. |
| Build | **PASS**: `V19PaletteTest.Build(1)` from the clean saved `Map_Look_v18_Play`; 2,241 renderers received palette material variants; ten local Volumes plus the transition Volume. |
| Matched screenshots | **PASS**: `V19PaletteTest.Capture("palette_current_v01_")` on v18, then `Capture("palette_new_v01_")` on the preview; 20 pairs, all four sheets inspected. |
| Actual post-processing at all ten cores | **PASS**: `VolumeManager.instance.Update(probe.transform, 1)` and stack `ColorAdjustments` reads match the table. Evidence: `palette_district_checks_v01.json`. |
| Play mode | **PASS**: preview ran to frame 13,376 / simulated time 66.96 s. Runtime renders sampled the real begin-camera callback: Hamlet fog 95–520 m; Rough fog 22–245 m. Evidence: `palette_play_checks_v01.json`, `palette_play_hamlet_v01.png`, `palette_play_rough_v01.png`. Console remained at zero errors. Play stopped afterward; no scene was saved during Play. |
| Road-chain transition sampling | **PASS** on Hamlet → bypass → bridge → hamlet_rough_e → Rough, at intervals no greater than 0.5 m: largest adjacent palette change 0.002066, exposure change 0.004047 EV, effective density change 0.000008933 / m. Evidence: `palette_transition_checks_v01.json`. |
| Terrain/layout preservation | **PASS**: every sampled heightmap element matches v18 exactly (maximum difference 0); all 8,525 tree transforms match. No road, building, plot, collider or relief builder ran. |
| Protected-file integrity | **PASS**: SHA-256 comparison of all 1,757 files in `palette_integrity_start_v01.json`; zero changed or missing. Includes v17/v18 scenes, legacy Look assets, v07 kit files, existing LookV3 assets, ProjectSettings and the pre-existing SausageBuddy controller state. Final evidence: `palette_integrity_final_v01.json`. |
| Performance acceptance | **NOT RUN**. The palette preview adds terrain endpoint layers and material variants; final v19 performance profiling remains part of G18. Runtime progress above is not an FPS benchmark. |
| New routes / stronger relief / completed v19 layout | **NOT RUN**, deliberately held behind checkpoint P approval. |
| Human visual acceptance | **PENDING FEDYA**. |

Neither run-in-background setting was changed. Existing unrelated local changes were preserved. No staging, commit, push or WORK_SYNC edit was performed.

## Resume only after checkpoint P approval

1. Re-take the Unity lock. Restart all 15 routes on the saved v18 style-v3 Play scene with label **`before18_g18_v02`**. The earlier `before18_g18_v01` attempt was interrupted during route 12 and is not a completed baseline. The authoritative v17 baseline remains `before_g18_v03`.
2. Resume the unfinished `ArtSource/References/Map/map_plan_v19.py` draft. It is not an accepted layout and has not emitted final v19 data. Finish compaction and street work; implement the newly requested stronger relief (2–6 m ravines, 1–3 m hollows, 3–8 m hills, up to 10–12 m interdistrict rises), keeping roads at or below 8% and plots/loading areas calm.
3. Apply the approved palette recipe to the final v19 build, adapting the palette cores to the final district geometry. Perform normal required gameplay/audio/police/crowd/clinic bakes and checks.
4. Produce final three-column v17 | v18 | v19 review sheets, route comparisons and the full G18 report.

At checkpoint handoff, Play is stopped, the editor is returned to the original saved v18 style-v3 Play scene, the separate palette preview remains saved, and the task's Unity lock is released. G18 waits for Fedya's palette approval.
