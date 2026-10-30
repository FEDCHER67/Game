# G22 — Free stylized sky and day/night cycle v01

**Status: STAGING COMPLETE; C# COMPILE-CHECKED; UNITY / VISUAL VERIFICATION NOT RUN.**

14 October 2026. Target: Unity **6000.5.11f1**, URP **17.5.0**, existing Input System **1.20.0**. Working project: `C:/Dev/Game`.

The lead owns the Unity handoff. The user's final instruction is to finish staging and this report, then **STOP and wait**. G22 must not message G18 directly. The shared lock still contained `gpt-g18 2026-10-14T00:34:50.584845+00:00` at the last check. No Unity calls, Asset imports, scene changes, window activation, background-setting changes, commits, staging for Git, pushes, deletions, or edits to WORK_SYNC.md were performed by G22.

This is not a claim of completed visuals or a playable, verified sky. The shader has not yet been compiled by Unity or visually inspected. The requested `.unity` scene, twelve captures and comparison sheet are **not yet generated**. Their source tools are staged and C# compile-checked.

## What is prepared

An original procedural sky: a gradient horizon/zenith, warm low-sun colour, sun disc and glow, moon, stars, and a bounded cloud-volume ray marcher with soft shaded cloud bodies. The cloud shape uses procedural noise, height shaping, absorption and two directional density samples for light/shade. It has no image textures, external packages, renderer feature, paid service or account requirement.

One clock exposes 0–24 solar hours and a configurable real-time cycle, default 24 minutes. It drives the celestial rotations, sun/moon colour and intensity, ambient light, fog colour, and night notifications. Heavy cover and district lighting multipliers remain effective at noon. A new adapter reads G18's existing v19 district/weather arrays and blend field without modifying their files.

The review builder creates a small original terrain, distant hills, pines and rounded trees, a cottage, a path, rocks, warm night windows and a street lamp. This geometry is for judging the sky, not a replacement for map art.

## Files

All package sources are in `ArtSource/Dev/Sky_staging/v01/`. Intended import root, after the lead grants the lock: `Assets/OnlyVolunteers/Sky/G22_v01/`.

| Staged path beneath `v01/` | Purpose |
| --- | --- |
| `Runtime/SkyModel22.cs` | Time wrapping, cycle math, art-directed celestial and lighting state, mood combination |
| `Runtime/SkyClock22.cs` | 24-minute clock, Input System debug keys, C# and Inspector night events |
| `Runtime/SkyRenderer22.cs` | Per-camera sky, light, ambient and fog application with state restoration |
| `Runtime/SkyDistrictSource22.cs` | Small camera-position mood interface for a concrete map consumer |
| `Runtime/SkyNightObjects22.cs` | Example night listener for lights and emissive window objects |
| `Runtime/OnlyVolunteers.Sky22.asmdef` | Runtime compilation boundary; references existing Input System |
| `Shaders/PaintedSky22.shader` | Original procedural sky and cloud volume |
| `Integration/SkyDistrictV19Bridge22.cs` | Adapter for the existing `DistrictWeather19V05`, `DistrictBlend19`, and optional v05 fog |
| `Editor/SkyReviewBuilder22.cs` | New-only scene, materials and procedural geometry builder |
| `Editor/SkyReviewCapture22.cs` | Twelve deterministic 1920×1080 render captures and numeric sidecars |
| `Editor/SkyVerification22.cs` | Unity checks for cycle math, lighting, continuity and events; prepared, not run |
| `Editor/SkyPlayVerification22.cs` | Normal-frame Play check for clock and night listeners; prepared, not run |
| `Editor/OnlyVolunteers.Sky22.Editor.asmdef` | Editor-only tools; existing URP/Core references |
| `README.md` | Setup, integration, controls and reproducible review instructions |

Supporting new files in `ArtSource/Dev/Sky_staging/`:

- `PROVENANCE.md` — detailed licensing and reference-use record.
- `References/` — exact licence snapshots, pinned licence audit JSON, and the two unchanged public COZY reference JPEGs for internal comparison only.
- `compile_staging_v01.py` — C# compiler invocation using the project's existing Unity reference assemblies; response files and DLLs are staging intermediates.
- `compile_evidence_v01.txt` — final successful C# compile output.
- `readiness_v01.json` — source-only readiness and editor ownership limitation.
- `install_new_only_v01.py` — lock-checked, new-files-only import helper. Refuses an existing destination and runs the source compile first.
- `make_review_sheet_v01.py` — layouts actual captures into the cycle and COZY comparison sheets; refuses missing source images.
- `package_manifest_v01.json` — source package hashes for lead handoff.

`Working/Reviews/Sky/CAPTURE_STATUS_v01.md` records the pending evidence. There are no G22 image captures in that directory yet. Unity `.meta` files are not hand-invented; Unity must generate them on the first permitted import, after which their GUIDs must be preserved.

## Licences and visual study

All runtime code and shader in G22 are original project work. None of the three allowed bases was copied into the implementation or installed.

| Inspected repository | Licence file and pinned commit | Result |
| --- | --- | --- |
| [Celestia](https://github.com/ZenoxZX/celestia) | MIT, `LICENSE.md`; `1251f7c872fa5957a3366b3a4ef059b3d0ec723b` | Verified; not incorporated |
| [UnityVolumetricCloudsURP](https://github.com/jiaozi158/UnityVolumetricCloudsURP) | MIT, `LICENSE`; `26c59bd371cc2af7b70741f6aea01adfdc8cc7bc` | Verified; not incorporated |
| [unity-stylized-sky](https://github.com/danielshervheim/unity-stylized-sky) | BSD-3-Clause, `LICENSE`; `f5612b9d14cbd68a2563465afdd8dcf338dea9d9` | Verified; not incorporated |

The [published COZY day image](https://distantlands.space/images/cozy-case-study/cozy_4.jpg), [night image](https://distantlands.space/images/cozy-case-study/cozy_1.jpg), and [Asset Store page](https://assetstore.unity.com/packages/vfx/shaders/cozy-stylized-weather-3-271742) were studied. The visible target is broad, softly shaded cloud masses, a pale cyan horizon, a blue upper sky, a deep navy night, fine stars and warm window accents. **Similarity is not yet established without a Unity render.**

Only the public promotional JPEGs were downloaded for the requested internal reference comparison. They remain outside Assets; they are copyrighted Distant Lands promotional material, not freely licensed game assets. No COZY package, source code, textures or account access was obtained. See PROVENANCE.md for exact licence URLs, rights notes and hashes.

## Parameters and controls

| Parameter | Default / meaning |
| --- | --- |
| Hour | 12; input is wrapped to `[0,24)` |
| CycleMinutes | 24 real minutes per full day; configurable, minimum 0.1 |
| Running | Enabled; scaled game time advances the cycle |
| Debug scrub | Hold `[` or `]`: ±1 game hour/real second; Shift: ±6 |
| Debug pause | `\` toggles clock progression |
| Night | 18:36–06:00; `IsNight`, C# `NightChanged`, Inspector UnityEvent |
| Fair cloud cover | 0.38; 0 is fully cloudless; 1 is maximum cover |
| Overcast capture | Cover 0.97, gloom 0.52 |
| Rough standalone mood | Cover 0.97, gloom 0.82, light multiplier 0.40, ambient multiplier 0.80 |
| Sun azimuth | 25 degrees; simple stylized daily orbit, full moon opposite sun |
| WindSpeed | 0.15; independent cloud-drift clock, scaled time |
| CloudScale | 1; procedural horizontal shape scale |
| CloudSteps | 48; bounded 24–80 ray-march samples |
| District parameters | Cover, gloom, light/ambient multipliers, tint, fog start/end, authored daytime zenith/horizon/cloud/fog colours and palette blend weight |

The model includes a nonzero night ambient floor and moon illumination. Scrubbing resynchronizes night state; it does not replay every skipped sunrise/sunset. Listeners should read `IsNight` when subscribing, as the example listener does. New listeners must unsubscribe when disabled.

The material exposes the gradient colours, light/shade cloud colours, sun/moon direction and colour, cover/gloom, stars, golden/daylight factors, wind time, shape scale and sample count. Sun and moon share one shadow-casting role at a time. Previous light settings and global RenderSettings are restored after camera rendering and on disable.

## Hooking into G18's map

**Do this only after visual review, on a new map scene revision under the shared lock. No existing map scene was changed.**

1. Add one G22 clock and renderer with the imported sky material, the existing map sun, and a new moon directional light.
2. Add `SkyDistrictV19Bridge22`, assign the existing `DistrictWeather19V05` source and assign the bridge to `SkyRenderer22.DistrictSource`.
3. Disable the old weather owner component, preserving its authored arrays. Ensure no older atmosphere/sky owner is active. The adapter refuses rendering while its selected source owner is enabled.
4. Preserve existing local grading volumes. The bridge clones the source blend-volume profile, applies per-camera district grade, restores values after rendering, and restores the previous profile on disable. It never edits the authored profile asset.
5. Keep the already-configured `DistrictFog19V05` active if the map uses its approved fog pipeline. The adapter supplies the same district weights and time-of-day fog colour to the transient fullscreen fog material. G18's native mist banks and halos retain their own colours; evaluate them at night before accepting the integration.
6. Hook street lamps/windows to `NightChanged` or attach the example listener. Existing G18 life/flicker scripts remain intact; select one component to own each lamp's enabled state.

The bridge uses `DistrictBlend19.Weights` and the source's `blendMetres` (60 m in the v19 reports). It reads the actual colours, cloud cover, sun/ambient multipliers, fog ranges and grade from the source arrays. Thus Hamlet's bright fluffy mood, Rough's grey overcast, Forest's subdued grey-green mood, and the other authored district palettes remain available. Sunrise/sunset/night colour combines with those inputs. IDs handled: `village`, `residential`, `forest`, `elite`, `fields`, `beach`, `old_town`, `transition`, `tramduro`, `industrial`.

Only v05 has the concrete adapter in this revision, matching the latest source found in the working tree. Older v02–v04 scene controllers require a new adapter revision rather than guessing or modifying their files. Full-map blend behaviour is still untested for G22.

## Checks actually performed

| Status | Check and evidence |
| --- | --- |
| PASS | Read worker rules, shared rules, current architecture/state, pinned project/package versions, v19 palette/fog reports and current controller sources. |
| PASS | `python ArtSource/Dev/Sky_staging/compile_staging_v01.py`: runtime, editor tools and map integration compile against existing pinned Unity references with **zero C# errors and warnings** in the final output. See `compile_evidence_v01.txt`. This is source compilation, not Unity import evidence. |
| PASS | Licence-file inspection: all three allowed repositories; exact commit, URL, text and SHA-256 recorded. |
| PASS | Import lock refusal: `python ArtSource/Dev/Sky_staging/install_new_only_v01.py` returned `BLOCKED: G22 does not own unity.lock` before compiling or copying any assets. Expected protective refusal. |
| PASS | Evidence refusal: `python ArtSource/Dev/Sky_staging/make_review_sheet_v01.py` reported all twelve missing Unity PNGs and created no synthetic comparison. Expected protective refusal. Pillow is available. |
| BLOCKED / NOT RUN | Live Unity identity/state, asset import, C# import compilation and shader compilation: editor remains with G18. No Unity tool was called. |
| NOT RUN | `SkyVerification22.Run()` and the prepared Play verification. No runtime-pass claim is made. |
| NOT RUN | Building/opening `Assets/OnlyVolunteers/Scenes/Dev/Sky_Test.unity`, scene reload, Console checks, missing-script checks, Play controls, camera-state restoration, map adapter/grade/fog integration. |
| NOT RUN | All requested captures, comparison sheet, GPU timings and subjective likeness/readability checks. |

## Lead continuation after lock handoff

1. Confirm exclusive editor ownership, exact project/version, clean scene state, stopped Play and baseline Console. Use the repository's existing CoplayDev unity-mcp bridge; do not install a second bridge or change packages.
2. Acquire `unity.lock` as `gpt-g22 ...` without overwriting another owner. Run the new-only import helper. Allow one complete import and inspect C# and shader diagnostics before using components.
3. Invoke `SkyReviewBuilder22.Build()`, then `SkyReviewCapture22.Open()` and `SkyVerification22.Run()`. Inspect the first actual render and tune only a new numbered deliverable if necessary.
4. Capture phases 0–5 with `SkyReviewCapture22.Capture(phase, false)` and `Capture(phase, true)`. Planned files: `dawn`, `morning`, `noon`, `golden_hour`, `dusk`, `night`, each with `_clear_v01.png` and `_overcast_v01.png`, in `Working/Reviews/Sky/`.
5. Run `SkyPlayVerification22.Start()`. If Unity cannot initialize normal frames in the background, ask in chat and wait for the user to bring it forward. Never activate/move/minimize windows or change runInBackground. `Resume()` continues the pending probe.
6. Stop Play, restore the original clean scene with `SkyReviewCapture22.Restore()`, inspect final Console, and verify metadata/dependencies and protected-file preservation.
7. Generate `cycle_contact_sheet_v01.png` and `cozy_style_comparison_v01.png` from the real captures. Write a **new report revision** with actual results. Release the lock and stop for visual review.

## Open issues

- No actual Unity image exists yet: cloud shape, softness, colour balance, moon visibility and similarity to COZY need visual iteration.
- Ray-marched clouds are sky-only: no terrain cloud shadows, cloud fly-through, weather precipitation, astronomical calendar, seasons or changing moon phases. These are not requirements of this staging pass.
- GPU cost of 48 cloud steps at 1080p is unmeasured. This is not a performance certification.
- Runtime restoration, Play input, event/listener behaviour and the G18 bridge have compiled but not executed in Unity.
- G18's native mist/halo colours remain authored by G18; the fullscreen fog colour is combined with time, but the complete night fog appearance requires map review.
- Clock authority is local. FishNet synchronization and persistence are not implemented or claimed.
- The `clear` review preset means fair weather with some puffy clouds, not zero cloud cover. Set cover to 0 for a truly cloudless diagnostic.

**Stopped after staging and this report, as instructed. Await the lead's Unity handoff; do not contact G18 directly.**
