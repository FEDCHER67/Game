# G22 original painted sky v04

Target: Unity 6000.5.11f1 / URP 17.5.0. No external package, image texture, account or paid asset required. Source provenance is `ArtSource/Dev/Sky_staging/PROVENANCE.md`.

## Standalone scene

After the complete package has been imported and Unity has compiled it, the shared editor owner can invoke `SkyReviewBuilder22.Build()` while holding the `G22` lock granted by `unity_lock.ps1`. It creates **new files only** at `Assets/OnlyVolunteers/Sky/G22_v04/Generated/` and `Assets/OnlyVolunteers/Scenes/Dev/Sky_Test_v04.unity`. It refuses an existing deliverable, Play mode, compilation or dirty scenes. It returns to the prior active scene. It does not add the scene to Build Settings.

The scene has rolling procedural terrain, pines and rounded trees, distant hills, a path, a cottage, night windows, a street lamp, a camera, an ACES volume and the sun/moon sky rig. All review geometry is original or uses Unity's built-in primitives.

In Play: `[` / `]` scrub backward / forward at one game hour per real second; hold Shift for six hours per second. `\` pauses/resumes the clock. Default full cycle: 24 real minutes. Keys use the installed Input System. Clock progression follows scaled game time; cloud drift follows scaled game time; debug scrub uses unscaled time. Inspector changes and `SetHour()` allow direct 0–24-hour selection.

Subscribe to `clock.NightChanged` (`Action<bool>`) or the Inspector `On Night Changed` UnityEvent. The event publishes on enable and on day/night state changes; scrub is a state resync, not a replay of every skipped crossing. A newly enabled listener should read `clock.IsNight` once; `SkyNightObjects22` demonstrates this. Night is 18:36–06:00. The sample enables its windows and lamp together.

## Time and mood API

`SkyModel22.Evaluate(hour, mood, sunAzimuth)` is the common pure sampling function. `SkyRenderer22.Mood` is the standalone mood. A `SkyDistrictSource22` may instead return one camera-position-specific mood per render.

`SkyMood22` exposes cloud cover, gloom, sunlight/ambient multipliers, global tint, fog start/end, district daytime zenith/horizon/cloud colours and their blend weight. The model preserves district colour at noon, increasingly uses sunrise/sunset colour at low sun, and uses a readable blue night. Heavy cloud cover and low district light multipliers remain effective at noon. The final `SkyState22.horizon` and `fog` are exactly equal. The shader keeps a matching flat horizon band below approximately two degrees of elevation; celestial glow and clouds fade out of this band. Light and sky changes are scoped to camera rendering and previous global state is restored afterward.

The material exposes cloud light/shade, gradient colours, celestial directions/colours, cloud cover/gloom, star visibility, golden-hour/daylight weights, wind time, scale and ray steps. The renderer supplies them from one clock. Original bounded ray marching through a procedural cloud slab gives soft shaded volume; no renderer feature is needed. This is sky-only cloud volume, without cloud shadows on terrain, weather precipitation or fly-through support.

## v19 integration — do on a new map scene revision after review

1. Preserve the current map scene and source controller. Add one G22 clock, renderer, sky material and moon directional light to the **new** revision. Use the map's existing sun light in `SkyRenderer22.Configure`.
2. Add `SkyDistrictV19Bridge22` outside the `Runtime` assembly folder. Assign the existing `DistrictWeather19V05` as its `source`, and assign the bridge to the renderer's district-source field.
3. Disable the old weather owner component (and any older weather/atmosphere owner). Keep its serialized arrays intact. The bridge refuses to render while its selected old weather owner is enabled. Do not run two sky owners.
4. Keep the existing local district volumes. The bridge clones the old owner's blend-volume profile, blends the authored grade per camera, then restores the prior values. It releases only its own transient clones and restores the prior volume profile on disable.
5. Keep `DistrictFog19V05` active if its approved renderer/pipeline setup is already present. The bridge calls its existing `ConfigureCamera` with the same weights and applies the current time's fog colour to the transient fullscreen material. The old fog-template asset is never edited. Native mist-bank/halo colours remain owned by G18 and need a night art review.
6. Attach lamp/window listeners to the clock. Existing G18 flicker/life scripts are not edited by this package. Choose which component owns each lamp's enabled state.
7. Review all districts and their boundaries at dawn, noon and night. No production map scene is automatically modified by the G22 tools.

The bridge consumes v19's actual arrays, not a guessed spatial map. IDs: `village` Hamlet, `residential` Rough, `forest`, `elite`, `fields`, `beach`, `old_town`, `transition`, `tramduro`, `industrial`. The same `DistrictBlend19.Weights` and configured `blendMetres` (60 in v19) blend cloud cover, actual palette, fog extinction, light and grade. V05 is the integration target found in the working tree on 14 October; previous v04–v04 scene controllers require an explicit adapter revision.

## Reproducible review

While G22 owns the shared editor and the prior scene is clean:

1. `SkyReviewCapture22.Open()` stores the prior single scene and opens Sky_Test.
2. `SkyVerification22.Run()` checks cycle math, night events, midnight continuity, lighting and Rough-at-noon behaviour in Unity.
3. `SkyReviewCapture22.Capture(phase, overcast)` for phase 0–5 and both booleans renders twelve 1920×1080 PNGs plus sidecar values. Labels/hours: dawn 05:39, morning 08:00, noon 12:00, golden hour 17:27, dusk 19:06, night 22:00. “Clear” is fair weather with 0.28 cover; overcast is 0.97 cover and 0.52 gloom. Truly cloudless is cover 0.
4. `SkyInputCheck22.Start()` batches clock, night listeners, drift, pause and scrub checks into one normal Play session. It injects only a temporary Unity Input System keyboard, restores the prior device and stops Play. The current work protocol permits bringing Unity forward if frames need it; never change background settings. `SkyHorizonPixelCheck22.Run()` separately compares real pixels of a fully fogged URP Lit surface against the adjacent sky at all twelve time/mood combinations.
5. Stop Play and call `SkyReviewCapture22.Restore()`. Review code refuses overwriting its evidence. Repeated captures use a new revision argument.
6. Run `ArtSource/Dev/Sky_staging/make_review_sheet_v04.py` after all twelve real PNGs exist. It makes the cycle sheet and the requested day/night COZY comparison; it refuses missing inputs.

Inspect Console and shader messages before accepting any capture. Compilation is not visual approval. GPU cost, human key feel and full-map/night-fog acceptance require actual testing.

The final per-camera `HorizonColourEvaluated(Camera, Color)` event exposes the exact shared sky/fog colour. G18g has not yet created its controller API; no connection to a nonexistent component is claimed. The existing V05 bridge and the new sky/fog pixel test are separate from that pending G18g integration.
