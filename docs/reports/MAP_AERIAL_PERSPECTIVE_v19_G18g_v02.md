# G18g — v19 aerial perspective, completed

2026-10-14. Implemented and saved in `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19.unity` and `Map_Look_v19_Play.unity`. Unity 6000.5.11f1 / pinned URP 17.5.0. This report supersedes the old startup-blocked `MAP_AERIAL_PERSPECTIVE_v19_G18g_status_v01.md`.

**Result:** distant surfaces converge to their district's horizon colour, including water and transparent materials. Nearby objects retain detail. Rough fog remains **v04 + 50% of the difference toward v03**, including droplets and banks. Forest density is unchanged. G18g changes the fog colour to the existing district horizon as requested; it does not repeat the layout or tree edits.

The updated overnight protocol and G18g brief were reread on completion. Both now explicitly say **do not run the review bridge**. No G18g bridge was run. The earlier G18 fix round had already received **PASS** in `Working/Reviews/_overnight/G18_claude_review.md`, round 2. Its stale fix-request file is superseded. Final editor state: **Map_Look_v19_Play saved, Play stopped**, active pipeline `PC_RPAsset`; G18 lock released with `unity_lock.ps1 -Cmd release -Id G18 -Done`.

## Deliverables

All image paths are under `C:/Dev/Game/Working/Reviews/Map_v19_Pilots/`. Sheets contain actual Unity renders, only resized and labelled.

| Current sheet | Contents |
| --- | --- |
| `aerial_perspective_v01.jpg` | Three fixed v19 before/after long views: Hamlet hill toward Downtown, north bridge along river, Rough edge outward |
| `aerial_review_v01_h.jpg` | 17 Hamlet walking / van views |
| `aerial_review_v01_r.jpg` | 11 road-chain / bridge walking / van views |
| `aerial_review_v01_k.jpg` | 15 Rough walking / van views |
| `aerial_review_v01_t.jpg` | Three overhead layout views; atmosphere deliberately disabled for readable plans |
| `palette_test_rough_v08.jpg` | Seven Rough views including garage lane and inner yard; latest 50% fog and aerial horizon colour |
| `palette_test_transition_v07.jpg` | Same four Hamlet → road → Rough transition poses |
| `aerial_edges_v01.jpg` | West, north, east and south edge views |

`aerial_sheet_manifest_v01.json` lists every sheet/source pair. `review_poses_v19_final_v02.json` supplies the 46 usual positions. It carries the G18 corrections k02b/k06b/k08b; the three stale camera-inside-building poses are not used. Long-view baselines were captured before aerial integration, with the same recorded coordinates, eye heights, pitch, FOV 75°, near clip .05 m, far clip 1200 m and 1920×1080 resolution (`aerial_long_poses_v01.json`). The approved geometry is unchanged between each pair. Ordinary scene camera far clip remains 460 m; clear-district haze is already approximately 99.6–99.9% at that distance.

Sources: `aerial_before_*.png`, `aerial_after_v01_*.png`, `aerial_final_v01_*.png`, `aerial_palette_v01_*.png`, `aerial_transition_v01_*.png`. Edge sources are `aerial_edges_v02_*.png`, with the east view replaced by `aerial_edge_depthfix_v01.png`. Early `aerial_probe_*`, incomplete `aerial_edges_v01_*`, and `aerial_edge_no_sea_v01.png` are diagnostic, not final. Nothing was deleted or overwritten.

All eight sheets were opened and inspected. Near walls, garage doors, paths, the van, foliage and props remain readable; distant groups lose contrast into the district horizon. Rough retains its dark overcast sky and cold grade. Four compass edge shots show no exposed finite terrain boundary. At the low eastern shore, blue nearby water remains visible; pixel rows 535–546 at the centre of the 1920×1080 image are exactly `(194,207,212)` across sea and sky, followed by a gradual return to water colour. This is a soft distance gradient, not a terrain-end seam.

## Implementation and scope

New runtime folder: `Assets/OnlyVolunteers/Map/LookV3/Palette19/Aerial_v01/`.

- `DistrictAerial19V01.cs`: optional camera-scoped extension of the existing atmosphere. It supplies one set of numeric shader parameters and the existing height texture, then restores previous globals after the camera. It does not own a second sky or light system.
- `Aerial19V01.hlsl`: shared distance, height, dense-fog and outer-edge evaluation for opaque and transparent receivers.
- `AerialDepth19V01.shader`: opaque depth/world-position overlay, using the existing `DistrictFogPass19V01` camera-enqueued Render Graph pass before transparents.
- `DistrictSkyAerial19V01.shader`: same district sky palette, with a flat matching horizon band and cloud/sun contribution faded out at the horizon. The band blends from .035 in clear districts to .15 in Forest/Rough, preventing pale distant silhouettes from abruptly crossing a much darker horizon strip.
- `WaterAerial19V01.shader`, `GlassAerial19V01.shader`, `SmokeAerial19V01.shader`, `MistAerial19V01.shader`, `TextAerial19V01.shader`, and two forward includes: preserve the source surface/alpha behavior and apply the shared aerial colour at the final fog stage.
- `Materials/`: scene-only copies for sky, depth overlay, mist, halo, lake/river/sea water, van glass, chimney smoke and world text. Original material assets remain untouched.

The water shader is a derivative of the project's existing MIT UberStylizedWater/G14 version, preserving flow, waves, shoreline and refraction code. Glass/smoke derive from the locally pinned URP shaders. Provenance is in the new folder's README; no download or package change occurred.

Small changes to existing v19 support:

1. `Palette19/DistrictWeather19V05.cs`: `Weather.horizon` remains the single serialized source; `horizonColour` is an alias and `SetHorizonColour(districtId, colour)` exposes it. Existing 60 m weights drive sky, grade and aerial colour together. With aerial present, fog colour is the blended horizon.
2. `Palette19/DistrictFog19V05.cs`: optional aerial reference and configure call; allows the same existing pass in clear districts. Historical v05 defaults remain for old scenes; final v19 scenes serialize the approved 50% settings.
3. `Editor/V19PilotTools.cs`: temporary review van uses the v19 glass copy when aerial is active. No shared vehicle prefab or tree model/material was changed.
4. New `Editor/V19AerialBuildV01.cs`, `V19AerialPixelCheckV01.cs`, `V19AerialReceiverCheckV01.cs`: scene integration, repeatable capture, and real GPU checks. `Apply()` rejects other scene names and Play mode; reports unhandled transparent shaders instead of silently skipping them.

The scoped Render Graph pass reads the declared depth input and explicitly binds it. Its destination is read only by fixed-function alpha blending, not sampled as a source texture. Every pass-data field is assigned for each recording, the render callback is static, and no global render-pipeline asset or extra colour copy is introduced. The final aerial shader treats only clear depth as sky (1e-7 tolerance), avoiding the earlier 1e-5 cutoff that could skip real geometry near a long far clip.

## Colour, distance and height

The canonical horizon remains the approved palette, not Omno's gamut. RGB values below are sRGB; post-processing still applies the approved district grade.

| District | Horizon RGB | Nominal 50% distance |
| --- | --- | --- |
| Forest | 161,173,167 | Existing dense real fog |
| Hamlet | 180,205,220 | 175 m |
| Construction | 194,189,176 | 150 m |
| Rough | 155,167,177 | Existing halfway fog |
| Downtown | 180,205,220 | 175 m |
| Industrial Port | 181,195,202 | 100 m |
| Elite Hill | 180,205,220 | 175 m |
| Quiet Valley | 180,205,220 | 175 m |
| Beach | 211,217,206 | 175 m |
| Tramduro | 188,205,210 | 150 m |

For clear districts, opacity is `1 − exp(−ln(2) × ((max(0,d−35))/(half−35))² × heightMultiplier)`. It is zero through 35 m; at 40 m it is at most about 0.5% even in Port. Height multiplier varies smoothly from 1.12 low down to .85 at average ray altitude 24 m and above. Thus the nominal clear 50% point becomes roughly 167–187 m, and the port point roughly 96–106 m. `aerial_curve_reference_v01.csv` records the calculation at 0,12,24 m altitude. This mild modulation is separate from the retained ground-relative dense mist in Forest/Rough.

The outermost 100 m terrain skirt fades fully to the horizon at its finite boundary; this contribution also applies to sea outside the terrain. It is gated off within 40 m of the viewer, grows smoothly through 100 m, and does not move terrain or gameplay objects. The skirt lies outside the district footprints.

Far colours converge to the horizon in linear light. Dark distant objects lighten and lose contrast, as visible in the sheets. A surface already brighter than the horizon may lose brightness as it converges; preserving every bright pixel's luminance would conflict with exact horizon convergence. No separate dark fog tint or multiplicative darkening was added.

## Rough and Forest preservation

Both saved scenes were queried and agree:

| Parameter | Final Rough | Forest |
| --- | ---: | ---: |
| Distance density | .0179 = lerp(.0048,.031,.5) | .026, unchanged |
| Distance onset | 22.5 m = lerp(45,0,.5) | 0 m, unchanged |
| Ground weight / extinction | .5 / .0275 | .72 / .0396, unchanged |
| Droplets | 82, opacity .074 | 140, opacity .13, unchanged |
| Banks | Three stronger pockets at .1425; other eleven at .11 with half v03 thickness | Four at .14, unchanged |

The density and eight-sample ground-height integration remain the approved implementation. Fog colour now follows the district horizon, as G18g explicitly requires; this makes the existing Rough haze visibly paler without increasing extinction. v04 contrast, exposure, sky mood and grade remain. Forest's strength, bank placements and droplets remain. G23's cancelled tree-shortening/thickening/wind request was not reintroduced.

## Verification

Evidence directory: `Working/Reviews/Map_v19_Pilots/`. Checks used the live editor, not a standalone mock renderer.

| Check | Result / evidence |
| --- | --- |
| Compile and shader validation | **PASS**. Seven new shader assets, zero ShaderUtil errors; zero Console errors after the Play run. `aerial_shader_inventory_v01.txt` |
| Transparent receiver inventory | **PASS**. No unhandled transparent material in final Play scene; water, van glass, chimney smoke, world text and runtime mist/halos use scoped variants. Same integration applied to Look scene. |
| Far geometry versus sky, all districts | **PASS**, 10/10. Actual red opaque geometry at 1600 m with near .05 / far 1800; max RGB difference from adjacent sky **0** after grade. `V19AerialPixelCheckV01.Run("v02")`, `aerial_horizon_pixels_v02.txt` |
| G22 compatibility | **PASS**, 40/40: ten districts × midnight/dawn/noon/dusk, real existing G22 Painted Sky renderer and bridge in a temporary rig; max horizon RGB difference **0**. `aerial_horizon_pixels_g22_v01.txt`. Probe rig destroyed; G22 code/assets untouched. |
| Real GPU distance curve | **PASS**. Black opaque probe at nine distances in Hamlet and Port; at high altitude Hamlet opacity 0 at 20/35/40, .443 at 175, .949 at 350, .978 at 400, .993 at 450. Port .444 at 100, .936 at 175. The high-altitude factor is .85, explaining the nominal 50% offset. `aerial_receiver_pixels_v02.txt` |
| Water/glass/smoke/text/mist/halo | **PASS**, 6/6. Actual receiver shader probes converge exactly to the horizon at 900 m. Near samples remain distinct, ruling out invisible quads as a false pass. The probe substitutes a white atlas for measurable text/particle coverage; it is not a claim to test every shader keyword. Same evidence file. |
| Border continuity | **PASS**. 101 samples over the 121.35 m Hamlet→Rough road segment; maximum adjacent horizon-channel change .005386591, with continuously varying weights/density. `aerial_border_sweep_v01.csv`, `aerial_final_editor_v01.txt` |
| Ordinary Play + runtime cameras | **PASS**. 5106 actual frames / 51.164 s elapsed; KCC initialized; two runtime camera renders. All seven shader vectors and the height texture restore exactly; pipeline unchanged. `aerial_runtime_v01.txt`, `aerial_play_hamlet_v01.png`, `aerial_play_rough_v01.png` |
| Viewpoints and final visual inspection | **PASS**. 46 usual poses plus three paired long views, garage/story views, transition and edge views captured; all eight sheets opened and inspected. Original G18 46-camera collision check remains applicable because G18g moves no geometry. |
| Integrity | **PASS**. All 70 sheet/source images decode. New aerial assets have all metas. Prior protected snapshots 185/688/5326 show no missing files or additional changed paths beyond the recorded G18 set. ProjectSettings and legacy-material diffs empty. `aerial_integrity_final_v01.json` |

Both run-in-background values were observed false and remained false. No window activation, movement, resizing or minimising was needed during this final continuation. No commit, staging, push, deletion, WORK_SYNC edit, package install, global URP/pipeline asset change or new audio download occurred.

## G18 Hamlet fix closure and remaining review limits

G18's full layout/terrain/access report remains `docs/reports/MAP_PILOT_v19_PROGRESS_review_v04.md`, with the reviewer PASS in `Working/Reviews/_overnight/G18_claude_review.md`. The wider orchard/hay turn arrived in 46.3 s / 117 m without tipping; hay retained. Final 22 route outcomes matched expectations: 19 arrivals and 3 deliberately blocked van shortcuts. The B03 van/foot rechecks and stationary four-wheel loading-stop check also passed. This is not a claim that blocked shortcuts are drivable. Geometry and collision checks were not repeated for G18g because it changes rendering only.

Open for Fedya: subjective acceptance of the final haze/sky, the broad southern Hamlet work fields, and remaining Rough lawns. Full catch→load→clinic→save gameplay loop, sound listening, exhaustive architectural traversal, multiplayer rendering and FPS profiling remain **NOT RUN**; G18 already records missing ambience clips and no-download constraints. No new blocker was found. The edge check covers the four documented normal viewpoints and all-district pixel probes, not every possible free-camera location.

G22 can use the existing Weather.horizon/horizonColour backing value and `SetHorizonColour`. When its own sky renderer is active it sets `RenderSettings.fogColor` before invoking visibleFog; the aerial extension consumes that colour. The 40-case integration test verifies this path, but the temporary G22 rig is not installed into these final scenes. New future transparent assets must be integrated with the same aerial helper/variants; original shared materials intentionally remain unaffected.

Final handoff: task work complete, saved scene and sheets ready for Fedya, Unity released. Stop here under the updated protocol; no automatic review or further scene changes.
