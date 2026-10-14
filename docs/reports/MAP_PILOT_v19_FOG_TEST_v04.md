# G18 — Checkpoint P, Rough District atmosphere v04

2026-10-14. **STOP — awaiting Fedya’s approval of the Rough District.** Forest v03 remains approved and unchanged. Full G18 layout, stronger terrain, routes and the final v19 build remain pending.

## Review

- `Working/Reviews/Map_v19_Pilots/palette_test_rough_v04.jpg` — seven original v03 poses, including the garage lane and B03 inner yard.
- `Working/Reviews/Map_v19_Pilots/palette_test_transition_v04.jpg` — the same four Hamlet → road → Rough poses.
- Columns: **current v18 / style v3 | new v19 palette test v04**. The existing v18 comparison captures were reused; all new views were rendered again in Unity. No retouching: sheet assembly only resizes and labels the captures.
- Authoritative new captures: `palette_new_v04r01_*.png` (12 at 1920×1080, including one Forest preservation check). Poses: unchanged `palette_fog_poses_v03.json`; sheet mapping: `palette_sheet_manifest_v04.json`.
- Review scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v04.unity`.

## Rough District changes

The reference `ref_rough_vibe_fedya.png` guided the change toward clear, cold streets, pale blocks, darker garage fronts and a heavy overcast sky. The previous milky veil has been removed from nearby and middle-distance objects.

- Distance haze coefficient reduced from **0.031 to 0.0048 /m**, with a **45 m clear-distance offset**. The exponential-squared term is now `1 − exp(−(0.0048 × max(0, distance − 45))²)`. Its calculated veiling is 1.4% at 70 m, 12.2% at 120 m and 22.4% at 150 m. These are shader values, not a human-certified visibility measurement; the walking-height review images show readable façades and paths.
- **No blanket height-fog layer in the Rough District.** Three thin, slowly drifting pockets remain at `(590,596)`, `(683,653)` and `(718,632)`: 9–11 m wide, 1.1 m high, centred about 0.65 m above terrain. Peak particle opacity is 0.065 instead of 0.22. The approach has no additional mist banks.
- Haze colour is a subdued cool grey `(0.40, 0.46, 0.49)` rather than pale grey-white. The horizon-scattering coefficient is 0.28 instead of 6, allowing the heavy cloud pattern to remain visible.
- Rough exposure **−0.20 EV**, contrast **+18**, saturation **−35**, white-balance temperature **−12**. Palette blend remains **t = 0.5**. The dark overcast sky parameters, diffuse sun, ambient intensity and weak shadows retain their v03 values.
- Near-camera motes reduced to 24 at very low opacity (0.018); lamp/window scatter reduced to 22% and fog headlamps to 25% of the former Rough strength. The existing lamps and window cues remain.
- The same 60 m district blending field drives the transition. Along the sampled approach, Rough weight grows from 5% to 95% over **56.1 m**. The four review poses retain the gradual change from sunny Hamlet to cold overcast Rough.

## Forest and trees preserved

Forest fog retains the v03 density **0.026 /m**, ground extinction **0.0396 /m**, original height integration, fog colour, sky, light, grade, all 140 droplets and four original banks. The Forest comparison has **one changed pixel by one 8-bit green value** across the entire 1920×1080 image; no visible difference. Evidence: `fog_forest_pixel_check_v04.json` and `fog_scene_check_v04.json`.

The scene references the unchanged v03 terrain asset with **8,525 tree instances**, which was already verified against v02. No tree models, tree instances, vegetation materials, props, audio or layout were edited. The green tree in `k20_garage_story` remains. Tree redesign still waits for approved references.

## Implementation

New files only:

- `Assets/OnlyVolunteers/Map/LookV3/Palette19/DistrictFog19V04.cs`
- `Assets/OnlyVolunteers/Map/LookV3/Palette19/DistrictFog19V04.shader`
- `Assets/OnlyVolunteers/Map/LookV3/Palette19/DistrictWeather19V04.cs`
- `Assets/OnlyVolunteers/Map/LookV3/Editor/V19PaletteP4.cs`
- `Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v04/` — copied PC pipeline/renderer, new haze material and Rough-only grade profile.
- The separate v04 scene named above. Earlier controllers are disabled in this scene; only the v04 atmosphere controller is active. Previous deliverables remain intact.

URP wiring is unchanged from the validated v03 pass: installed `FullScreenPassRendererFeature`, before transparents, depth input, no scene-colour copy, hardware alpha blending. Forest soft-particle materials and the saved terrain height field are reused without edits. PC review scope remains; transparent objects without depth writes still use the underlying scene depth. Future terrain changes require rebaking the height field.

## Verification

| Result | Check and evidence |
| --- | --- |
| PASS | Unity 6000.5.11f1 compiled the new scripts; `ShaderUtil.GetShaderMessages(Shader.Find("OnlyVolunteers/StyleV3/DistrictFog19V04"))` returned zero shader messages. |
| PASS | `V19PaletteP4.Build()` created the separate v04 scene; `V19PaletteP4.Capture("palette_new_v04r01_")` produced all 12 new images. All seven Rough and four transition views were visually inspected. |
| PASS | Normal Play initialized before stepping. A camera probe then ran six positions over 240 Game-view frames: Hamlet, three road positions, garage lane and Forest. Rough: density 0.0048, zero blanket ground extinction, 24 motes / three banks. Forest: 0.026, 0.0396, 140 / four. Bank coordinates changed with simulated time. Evidence: `fog_runtime_probe_final_v04.csv`. |
| PASS | Final Play run and scene unload had **zero Console errors**. The first diagnostic probe forced `Camera.Render()` to the screen and encountered mismatched UI attachment dimensions / render-pass errors. That diagnostic method was discarded; the successful retry used normal Game-view rendering without forced screen renders. `fog_runtime_probe_v04.csv` is superseded by the final CSV. |
| PASS | 161 approach samples retained the smooth blending field. Largest sampled weight step was 0.03356 per 0.967 m; one small 0.000282 decrease reflects neighbouring district normalization. No hard switch was introduced. Evidence: `fog_transition_samples_v04.csv`. |
| PASS | `verify_fog_v04.py`: **4,751 / 4,751 protected pre-existing files unchanged by SHA-256**, no missing Unity metadata. Includes shared legacy Look files, v07/Art assets, previous palette tests/scenes, audio and ProjectSettings. Evidence: `palette_integrity_start_v04.json`, `palette_integrity_final_v04.json`. |
| PASS | After stopping, restored clean `Map_Look_v18_Play`, original `Assets/Settings/PC_RPAsset.asset`, linear scene fog 60–400 m, and no temporary fog rig. |
| NOT RUN | Human visual approval, full 15-route suite, full v19 layout/terrain build and performance certification. These are outside this revision or await checkpoint approval. |

Review evidence and assembly/verification scripts are in `Working/Reviews/Map_v19_Pilots/`. No downloads, commits, pushes, legacy look builds or changes to either runInBackground setting were made.

## Handoff

Play stopped; original v18 scene clean; Unity lock released at handoff. **Stop here for Fedya’s Rough v04 verdict.** On approval, retain the approved Forest v03 fog and carry the approved Rough v04 atmosphere into the remaining G18 work. Do not resume terrain/layout, the `before18_g18_v02` route restart or the full v19 build before that approval. Trees remain separately deferred.
