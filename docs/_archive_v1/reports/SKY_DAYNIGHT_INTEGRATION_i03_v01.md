# G22 — day/night sky integrated into v19 i03

2026-10-14, 17:31 Moscow. Integration complete; Unity saved with Play stopped, lock released. No review bridge.

## Result and paths

- **Scene:** `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i03_sky.unity`, derived in place from `Map_Look_v19_Play_i02_grass.unity`. No map rebuild.
- **Sky:** existing complete `Assets/OnlyVolunteers/Sky/G22_v04/` runtime, shader and `Generated/PaintedSky_v04.mat`. The interrupted v05 is not referenced. No COZY cloud changes.
- **New integration code:** `Assets/OnlyVolunteers/Sky/MapIntegration_i03_v01/`: `SkyMapNight22I03.cs`, `Editor/SkyMapInstall22I03.cs`, and `Editor/SkyMapReview22I03.cs` with Unity metas. Source and preservation evidence: `ArtSource/Dev/Sky_staging/Map_i03_v01/`.
- **Review:** `Working/Reviews/Sky/sky_in_map_v01.jpg`, plus `sky_in_map_hamlet_v01.jpg`, `sky_in_map_rough_v01.jpg`, and `sky_in_map_forest_v01.jpg`. Nine actual 1920×1080 Play renders cover those districts at 12:00, 17:27 and 22:00. Sources are `map_i03_*_v01.png`; coordinates and parameters are in matching text files and `capture_manifest_i03_v01.json`. Sheets only resize and label the renders.

One clock and renderer use the existing map sun and a new directional moon. Start is **08:00**, cycle **24 minutes** of unpaused game time. Existing debug controls remain: `[` / `]` scrub, Shift accelerates, backslash pauses/resumes the clock. The previous `DistrictWeather19V05` component is disabled; all ten district palettes and its references remain serialized.

The existing v04 district adapter combines time with G18's 60 m district blends and grading. Its final `state.horizon == state.fog` is applied before `DistrictFog19V05.ConfigureCamera`; that calls `DistrictAerial19V01.ConfigureCamera` with the same colour. Sky, opaque depth aerial perspective and transparent receivers therefore use the same camera-specific horizon. The serialized daytime palette is not overwritten each frame. Globals restore after each camera. Rough density remains **.0179**, Forest **.026**, with existing banks and droplets retained.

The clock's night event drives three existing flickering lamp lights and **173 emissive material slots**: lamp glow, three warm panes and two garage windows. Materials are cloned only at runtime, shared among matching slots, restored on disable, and never saved into assets. Stationary halo cues follow the same night state; vehicle and police light ownership is preserved. No additional point lights or gameplay owner were added.

## Checks

| Check | Result and evidence |
| --- | --- |
| Compilation | **PASS** — staging Roslyn compile of runtime/editor sets, then live Unity 6000.5.11f1 import. `compile_install.py --install`; final shader has no ShaderUtil errors. |
| Installed horizon and ownership | **PASS** — 10 districts × five times, 50 cases, maximum far-surface versus adjacent-sky RGB difference **0**. Exact sky/aerial colour equality, night bindings and global restoration passed in every case. `horizon_night_play_i03_v01.txt`. |
| Ordinary Play clock and drift | **PASS** — 3,307 frames, 36.06208 game seconds; hour advanced .6010399 versus .6010347 expected. Cloud time advanced 36.06317 seconds. `clock_play_i03_v01.txt`. |
| Player and van | **PASS** — existing route harness: orchard walk **111.5 m**; Hamlet van route **137.5 m**, maximum **43.7 km/h**, both arrived. Same initial chassis/ground contact as i02, no route failure. `Working/Reviews/Map_v19_Pilots/routes_g22_i03_v01.json`. Harness suppresses crowd/police for repeatability. |
| Final scene | **PASS** — zero Console errors, zero missing scripts, one clock/renderer, no v05 dependency, saved clean at 08:00, Play stopped. `final_scene_i03_v01.txt`. |
| Preservation | **PASS** — **2,997** protected files/dependencies unchanged, none missing; all new script metas present. Base scene, tree/grass assets, ProjectSettings, packages and pipeline assets unchanged. Existing scene geometry blocks unchanged; two new objects added. `preservation_after_i03_v01.json`, `scene_diff_i03_v01.json` in staging. |

One **graphics ring buffer capacity warning** appeared during the burst of offscreen probe renders; no Console error resulted. No pipeline or command-line tuning was made. The saved scene also contains Unity's incidental change to the sun's unused bounding-sphere override data (`m_UseBoundingSphereOverride` remains 0).

## Limits and rebuild notes

The chosen complete v04 retains its existing early twilight star fade and cloud appearance; the stopped v05 fixes are not claimed complete. Night water brightness and subjective night readability remain for Fedya's review. GPU profiling, multiplayer clock synchronization and the full clinic loop were **NOT RUN** in this integration.

The shared map builder was not edited. A future v19 rebuild must reapply the G18g scene, trees and grass first, then add the same clock, renderer, district adapter and night binder; reuse the map sun, add the moon, disable the old weather owner, and assign the v04 sky material. The new install tool deliberately accepts only a clean i02 scene and refuses an existing i03 output, protecting this chain.

No new third-party files or paid assets were used. Original sky provenance and inspected upstream licences remain in `ArtSource/Dev/Sky_staging/PROVENANCE.md`; existing project material licences are unchanged. No commits, deletions, WORK_SYNC edits, global URP edits, runInBackground changes or window operations occurred.
