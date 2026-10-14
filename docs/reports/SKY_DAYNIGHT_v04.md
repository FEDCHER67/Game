# G22 — free painted sky / day-night cycle, Unity review v04

14 October 2026. Unity **6000.5.11f1**, URP **17.5.0**, Input System **1.20.0**. Project: `C:/Dev/Game`.

**Implemented, imported, shader-compiled, rendered and Play-checked. G18g integration is blocked by its missing implementation.** The latest sky is v04. The original `SKY_DAYNIGHT_v01.md` remains an accurate historical staging report; it was not overwritten. This report supersedes its pending Unity/capture status.

## Review entry points

- Latest saved scene: **`Assets/OnlyVolunteers/Scenes/Dev/Sky_Test_v04.unity`**.
- Latest package: **`Assets/OnlyVolunteers/Sky/G22_v04/`**, namespace `OnlyVolunteers.Sky22V04`.
- Twelve final 1920×1080 captures: **`Working/Reviews/Sky/{phase}_{clear|overcast}_v04.png`**.
- Correctly labelled contact sheet: **`Working/Reviews/Sky/cycle_contact_sheet_v05.png`**.
- COZY comparison: **`Working/Reviews/Sky/cozy_style_comparison_v05.png`**.
- Additional district mood examples: `rough_noon_v04.png`, `rough_night_v04.png`.

The exact originally requested `Sky_Test.unity` exists as the first imported v02 trial. Its successor scenes are `Sky_Test_v03.unity` and `Sky_Test_v04.unity`. New numbered revisions preserve earlier deliverables under AGENTS.md. **Use v04 for review and integration.** The v02/v03 packages have separate namespaces and assembly names and are not referenced by the latest scene. Their files and trial captures were retained rather than deleted. The v04 contact sheet has an obsolete 0.38 fair-cover label; the new v05 sheets correct it to the actual **0.28** without changing any capture pixels.

## Implemented behaviour

An original skybox shader renders the gradient, sun disc/glow, full moon, procedural stars and drifting cloud volume. Clouds use bounded ray marching through procedural 3D noise, a shaped height envelope, absorption and directional density samples for soft light/shade. No third-party sky code, image texture, paid asset, package installation or account is required.

The clock wraps to 0–24 hours. Default full cycle is 24 real minutes of scaled game time. Dawn is pink, morning/noon cyan, golden hour warm, dusk blue-purple, and night navy with a moon, stars, nonzero ambient illumination and warm window/lamp accents. Overcast changes both cloud opacity and lighting. The Rough mood remains visibly gloomy at noon; see its separate actual render.

The first render exposed excessive cloud coverage, near-horizon sampling bands, dim windows and an obscured review moon. New v03/v04 revisions reduce those artifacts, enable the window emission keyword correctly, improve night illumination, use a clearer cloud phase and reduce star density. The final fair cloud composition is intentionally soft; it is an original approximation of the reference style, not a reproduction of COZY. Subjective art acceptance remains with Fedya/the lead.

## Parameters and controls

| Parameter | v04 default / meaning |
| --- | --- |
| Hour | 12; wrapped to `[0,24)` |
| CycleMinutes | 24; configurable, minimum 0.1 |
| Running | true; follows scaled game time |
| Debug scrub | Hold `[` / `]`: −/+1 game hour per real second; Shift multiplies by 6 |
| Debug pause | `\` toggles progression |
| Night state | Before 06:00 or from 18:36; C# `NightChanged` and Inspector UnityEvent |
| Fair cloud cover | 0.28; 0 is cloudless, 1 maximum coverage |
| Overcast capture | Cover 0.97; gloom 0.52 |
| Rough standalone | Cover 0.97; gloom 0.82; light ×0.40; ambient ×0.80 |
| WindSpeed / CloudScale | 0.15 / 1 |
| CloudSteps | 64, configurable 24–80 |
| Cloud phase | Review scene/captures start at CloudTime 650; drifts during Play |
| Sun azimuth | 25 degrees; stylized orbit, full moon opposite sun |
| Night moon maximum | 0.32 directional-light intensity before mood/cover attenuation |
| District inputs | Cover, gloom, sun/ambient multipliers, tint, fog start/end, daytime zenith/horizon/cloud colours, palette weight |
| Review grading | Local scene volume: ACES, exposure +0.35; no global URP asset edit |

`SkyClock22.SetHour()` resynchronizes state; it does not replay every skipped dawn/dusk. New subscribers should read `IsNight` when enabling and unsubscribe when disabling. `SkyNightObjects22` demonstrates this with the cottage windows and street lamp. Only one light casts sun/moon shadows at a time.

## Shared horizon colour and G18g dependency

**The sky side is implemented and tested. The G18g controller side does not exist yet.** At acquisition, `docs/reports/MAP_AERIAL_PERSPECTIVE_v19_G18g_status_v01.md` explicitly reported implementation not started: no shader, component, material, scene or image. G22 did not invent a controller API, modify G18 files, or claim a completed map connection.

`SkyModel22.Evaluate(hour, mood)` now computes one final `SkyState22.horizon`. **`SkyState22.fog` is exactly that same colour.** The shader keeps the skyline band below approximately two degrees of elevation at this colour, with sun/moon glow, stars and clouds faded out of that band. The far horizon therefore matches the fog even during dawn, sunset and night.

`SkyRenderer22.HorizonColourEvaluated` is a public **`Action<Camera, Color>`** event raised for each applied camera state. It supplies the exact final colour used by the shader and RenderSettings. Values are Unity gamma-space `Color` values; a custom linear HLSL fog uniform should use the appropriate linear conversion once, as the existing V05 fog bridge does. `LastState.horizon` exposes the latest sampled value. The existing `SkyDistrictSource22.AfterAtmosphere(Camera, SkyState22)` callback also receives it.

When G18g supplies its public API, its adapter must:

1. Read the controller's authored per-district base horizon colour into `SkyMood22.daytimeHorizon`, using the existing district weights.
2. Route the evaluated camera horizon colour into G18g's final haze colour. Do not independently colour fog or add an unmatched horizon glow.
3. Preserve G18g's distance/height curve and material coverage; G22 does not replace those algorithms.
4. Verify the three requested G18g long views and all relevant custom/transparent materials at dawn, noon and night.

This final wiring and full-map visual validation are **OPEN / DEPENDENCY BLOCKED**, not passed. No messaging to G18 was performed.

## Existing v19 adapter and map hookup

`Integration/SkyDistrictV19Bridge22.cs` reads the currently available `DistrictWeather19V05` arrays and `DistrictBlend19.Weights`. It blends actual district cover, palette, fog range, sun/ambient values and grade. IDs include Hamlet (`village`), Rough (`residential`), Forest, Elite, Fields, Beach, Old Town, Transition, Tramduro and Industrial. It refuses ownership while the selected old weather component is enabled. Grade is applied on a transient profile clone and restored after each camera and on disable; authored profiles remain intact.

On a **new approved map scene revision**, assign one G22 clock/renderer, its sky material, the existing map sun, a new moon, and the appropriate district adapter. Disable the old sky/weather owner while preserving its data. Connect street lamps/windows to the night event, choosing one owner for each light's enabled state.

**Current protocol takes precedence over the legacy README's V05 fog option:** do not activate/reuse V05's global pipeline-override path for the new aerial-perspective integration. Use G18g's eventual camera/scene-scoped path. G22 did not edit ProjectSettings, packages or the global URP asset. The V05 adapter's isolated blend/profile contract passed; this is not a certification of the old fullscreen fog on the full map, or of G18g's unfinished all-material aerial perspective.

## Files

The latest complete source set is staged at `ArtSource/Dev/Sky_staging/v04/` and imported at `Assets/OnlyVolunteers/Sky/G22_v04/`.

| Relative path | Purpose |
| --- | --- |
| `Runtime/SkyModel22.cs` | Day/night palette, celestial directions, lighting, mood combination, shared horizon/fog |
| `Runtime/SkyClock22.cs` | Configurable cycle, Input System controls, night events |
| `Runtime/SkyRenderer22.cs` | Per-camera application/restoration, drift and horizon callback |
| `Runtime/SkyDistrictSource22.cs` | Camera-position district sampling interface |
| `Runtime/SkyNightObjects22.cs` | Window/lamp listener |
| `Shaders/PaintedSky22.shader` | Original gradient/celestial/procedural cloud rendering |
| `Integration/SkyDistrictV19Bridge22.cs` | Concrete existing V05 district adapter |
| `Integration/Editor/SkyMapDiagnostics22.cs` | Real G18-type blend/profile contract checks |
| `Editor/SkyReviewBuilder22.cs` | New scene and original review geometry/materials |
| `Editor/SkyReviewCapture22.cs` | Deterministic real Unity captures and numeric sidecars |
| `Editor/SkyVerification22.cs` | Clock, lighting, event and continuity checks |
| `Editor/SkyRenderDiagnostics22.cs` | Actual shader and per-camera restoration checks |
| `Editor/SkyHorizonPixelCheck22.cs` | Actual distant Lit surface versus adjacent sky pixel comparison |
| `Tests/Editor/SkyInputCheck22.cs` | Combined runtime/input Play suite |
| `Generated/` | Saved terrain/pine meshes, materials and local grading profile |

Assembly definitions separate runtime, editor tools and editor checks. Integration stays in the predefined assemblies because G18's types live in Assembly-CSharp. Unity generated all metadata; the final scene has 92 dependencies and zero missing scripts. The earlier standalone Play helper remains available but the final checks used the combined suite in one run.

Supporting staging files include `compile_staging_v04.py`, `install_new_only_v04.py`, `make_review_sheet_v05.py`, `installed_manifest_v04.json`, `protected_before_import_v02.json`, `preservation_after_v04.json`, original provenance/licence snapshots, and preserved earlier revisions.

## Licences and references

All G22 implementation code, shader and procedural scene geometry are original project work. No code from the allowed bases was incorporated. Their licence files were nevertheless inspected and pinned, as requested:

| Repository | Verified licence and commit |
| --- | --- |
| [Celestia](https://github.com/ZenoxZX/celestia) | MIT, `LICENSE.md`, `1251f7c872fa5957a3366b3a4ef059b3d0ec723b` |
| [UnityVolumetricCloudsURP](https://github.com/jiaozi158/UnityVolumetricCloudsURP) | MIT, `LICENSE`, `26c59bd371cc2af7b70741f6aea01adfdc8cc7bc` |
| [unity-stylized-sky](https://github.com/danielshervheim/unity-stylized-sky) | BSD-3-Clause, `LICENSE`, `f5612b9d14cbd68a2563465afdd8dcf338dea9d9` |

Exact licence text, URLs and hashes are in `ArtSource/Dev/Sky_staging/PROVENANCE.md` and `References/licence_audit_v01.json`.

Studied references: [COZY day](https://distantlands.space/images/cozy-case-study/cozy_4.jpg), [COZY night](https://distantlands.space/images/cozy-case-study/cozy_1.jpg), [Asset Store page](https://assetstore.unity.com/packages/vfx/shaders/cozy-stylized-weather-3-271742). The unchanged public promotional JPEGs are only in ArtSource and the requested internal comparison sheet, labelled © Distant Lands. They are excluded from game Assets and redistribution. No COZY package/files or paid asset was acquired.

## Evidence and validation

All evidence below is under `Working/Reviews/Sky/` unless specified.

| Result | Check |
| --- | --- |
| PASS | Offline Roslyn compile of runtime, editor, V05 adapter, map diagnostics and input-check assemblies against pinned Unity references |
| PASS | Unity import compilation; supported shader; no ShaderUtil errors after real rendering |
| PASS | `verification_v04.txt`: 24-minute cycle mathematics, wrapping, sun/moon direction, stars, golden hour, Rough noon, midnight continuity, finite lighting throughout the day, event transitions and pause |
| PASS | `render_diagnostics_v04.txt`: sky, light, ambient and fog state restored after rendering at 00:00, 06:00, noon Rough and 19:00 |
| PASS | `horizon_pixels_v04.txt`: all twelve time/mood combinations; fully fogged URP Lit surface versus adjacent horizon. Maximum RGB difference no greater than 1/255 (tolerance 3/255) |
| PASS | `horizon_event_v04.txt`: actual camera callbacks provide the applied shared horizon colour |
| PASS | `district_contract_v04.txt`: real G18 blend code, 50/50 transition, gloomy Rough noon, nonzero night light, per-camera grade and profile restoration; isolated contract data |
| PASS | `play_verification_v04.txt`: normal Play frames, runtime clock/night events/windows/lamp and drift; **53 frames**, one combined Play run |
| PASS | `input_check_v04.txt`: backslash toggles progression, bracket scrubs forward, Shift+bracket backward, release stops scrubbing. Temporary Unity keyboard removed; no OS key injection |
| PASS | `scene_validation_v04.json`: saved latest scene, zero missing scripts, 92 dependencies, no shader messages |
| PASS | Twelve real 1920×1080 PNGs and sidecars, two corrected v05 sheets, extra Rough noon/night images |
| PASS | Zero Console errors/warnings at final sky validation. Earlier project startup/tree warnings existed before import |
| PASS | `ArtSource/Dev/Sky_staging/preservation_after_v04.json`: all **115** protected pre-import file hashes unchanged; no missing metadata in latest package |
| OPEN | G18g controller wiring, actual full-map boundaries, custom transparencies/water/particles and all-district dawn/noon/night inspection |

Captures: dawn **05:39**, morning **08:00**, noon **12:00**, golden hour **17:27**, dusk **19:06**, night **22:00**, each fair/overcast. They use the same camera, cloud phase and local grade. The full cycle was checked mathematically and through runtime ticks, not by claiming a 24-minute soak run. The GPU used was **NVIDIA GeForce RTX 5070 Ti, Direct3D11**; no frame-budget/performance certification is claimed.

## Handoff and remaining limitations

The updated helper granted G22 ownership. No short-sleep lock polling was used after the midday protocol update. Unity was already responsive when G22 acquired it; no startup-security dialog was bypassed. No native UI action or foreground change was needed for the completed Play suite.

Unity was returned to **`Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play.unity`**, clean, with Play stopped. G22 released through `unity_lock.ps1 -Cmd release -Id G22` after the render/test step. No commits, Git staging, pushes, project-file deletions or WORK_SYNC edits occurred. No ProjectSettings, runInBackground or global URP asset changes occurred.

Open issues: G18g dependency described above; subjective COZY likeness; production GPU cost; full-map night mist/halo colouring; no terrain cloud shadows, cloud fly-through, precipitation, calendar, seasons, moon phases, networking or persistence. These extra systems were not silently added. The procedural review terrain is deliberately simple and is not replacement map art.

Assumptions: “clear” means fair weather with puffy clouds, not zero coverage; the original file names and earlier captures remain preserved; the sky may finish its standalone checks while G18g is blocked; only v04 should be integrated into a new map revision. The Claude bridge will review this current report with `-Task G22`; its verdict/fix follow-up is separate evidence, not preclaimed here.
