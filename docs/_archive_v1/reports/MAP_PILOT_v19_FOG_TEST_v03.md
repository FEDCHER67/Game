# G18 — Checkpoint P, visible fog revision v03

2026-10-14. **STOP — awaiting Fedya’s visual approval.** Full v19 terrain/layout and route work remains gated.

## Review files

All sheets use unretouched 1920×1080 Unity renders, reduced only for sheet assembly. Columns remain **v18 / style v3 | new v19 test**. The original six Rough poses and four transition poses are unchanged (eye height 1.85 m, FOV 75°, far plane 460 m). One extra walking view looks along the garage lane.

- `Working/Reviews/Map_v19_Pilots/palette_test_rough_v03.jpg` — seven views, including B03 inner yard, garages and new `k21_walk_garage_lane`.
- `Working/Reviews/Map_v19_Pilots/palette_test_transition_v03.jpg` — original four Hamlet → road → Rough poses.
- `Working/Reviews/Map_v19_Pilots/palette_test_forest_v03.jpg` — lighter version of the same fog.
- Scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v03.unity`.
- Authoritative new raw images: `palette_new_v03r05_*.png` (12). Fresh v18 comparison images: `palette_current_v03_*.png` (12).
- Mapping and camera data: `palette_sheet_manifest_v03.json`, `palette_fog_poses_v03.json` in the same review folder.

## Fog changes

The approved v02 sky, lighting grade, ambience and layout supply the underlying scene. A v19-only depth pass now adds pale cool grey-white fog; the original surface fog is disabled while this dense fog is active, avoiding double application.

- Exponential-squared distance extinction: Rough density 0.031/m; Forest 0.026/m. The distance term alone veils Rough objects by about 32% at 20 m, 58% at 30 m, 91% at 50 m and 99% at 70 m; the ground layer adds further veiling. Walking views visibly retain nearby doors and lane edges while the lane recedes into mist. The requested 35–50 m impression remains an art judgement for Fedya.
- Height fog integrates eight terrain-relative samples along the view ray. It is densest near the ground, falls with a 2.3 m scale, and fades out between 4 and 7 m above local terrain. Rough ground extinction is 0.055/m; Forest 0.0396/m. The saved 256×256 height field follows this test terrain.
- The fogged horizon converges to the same mist colour as distant geometry. Higher overcast clouds keep their v02 sky settings; distant trees no longer appear as bright cutouts against an unfogged sky.
- 140 fine camera-relative droplets, 6–21 mm in size, with very low opacity and slow drift. They are deliberately subtle in stills.
- 18 placed mist banks: 14 in the Rough approach, lanes and yards, four in the Forest. Centres are about 1.7–2.6 m above ground; cards are 12–21 m wide and 3–4.4 m high. Soft radial edges, procedural variation, slow drift and a 2.2 m depth fade prevent hard terrain/wall intersections.
- 25 scatter emitters cover existing lamp heads, three worn lamps, two dim garage windows and two v19-only van headlamps. The worn-lamp halos were fitted to the actual bulb mesh. Window illumination stays cold and restrained. The headlamps fade with the dense-fog district weight; no new player control was added.
- The existing 60 m district blend drives fog, particles and halos together. Sampling the approach measured **56.1 m between 5% and 95% Rough weight**, with continuous entry and exit.

## Trees: latest correction applied

**Every tree is retained exactly as in checkpoint P v02, including the green poplar in `k20_garage_story`.** All 8,525 instances match the serialized v02 positions, rotations, scales, colours and prototype indices. Tree models and materials were not edited. The provisional 242 substitutions made before Fedya’s correction were fully reverted, and the substitution code was removed from the v03 builder.

`fog_tree_restore_verified_v03.json` is the final tree verification. The earlier `fog_tree_audit_v03.json` and captures r01–r04 are superseded working evidence and must not be used for approval. Tree redesign waits for Fedya’s chosen references.

## Verification

- Reviewed all seven Rough walking-height views, all four transition views and the Forest view. The new garage-lane view shows the close-to-distant fog progression; B03 yard edges and close entrances remain visible.
- Final Play-mode probe: six positions / 240 stepped frames after normal game initialization. Hamlet: density 0 and no mist particles. Road Rough weights: 0.075 → 0.374 → 0.999. Rough core: density 0.031, 140 droplets / 14 banks. Forest: density 0.026, 140 droplets / four banks. Bank positions changed over simulated time, confirming drift.
- Final evidence: `fog_runtime_probe_final_v03.csv`, `fog_transition_samples_final_v03.csv`. Earlier diagnostic CSVs use the editor’s comma decimal locale; use these final invariant-format files.
- Final Unity console: **zero errors** during the corrected Play run and after stopping/unloading. Both new shaders compile without shader messages. Existing legacy tree billboarding warnings remain outside this fog revision.
- Opening/closing the test restores the original `PC_RPAsset`, original scene fog (linear 60–400 m) and removes all temporary fog particle rigs. A persistence issue found during testing was fixed: cleanup restores only the temporary pipeline reference in QualitySettings, preserving other settings. No background-running setting was changed.
- SHA-256 comparison: **4,718 / 4,718 protected pre-existing files unchanged**, including shared legacy Look materials, v07/Art assets, earlier palette tests/scenes, audio and ProjectSettings. See `palette_integrity_final_v03.json`. All new fog assets have Unity metadata.
- This is a PC review pass. It uses one depth-reading fullscreen pass, no scene-colour copy, at most 140 droplets + 32 banks + 32 halos, and no particle shadows or collisions. GPU timing/mobile/XR certification was not part of this checkpoint. The full 15-route suite has not been restarted.

## URP renderer validation

1. **Summary:** uses the installed URP 17.5 `FullScreenPassRendererFeature` before transparents, in a v19-only copied renderer/pipeline.
2. **Confirmed issues resolved:** stopped particle systems discarded manually supplied particles; initialized paused systems now retain them. Fogged geometry initially contrasted with an unfogged horizon; the horizon now receives matching mist. Temporary quality-setting persistence now cleans up correctly.
3. **Remaining risks:** PC-only review configuration; transparent objects without depth writes use the underlying scene depth. Stronger future terrain requires rebaking the height field and reviewing intersections again.
4. **Resource wiring:** `requirements = Depth`, `fetchColorBuffer = false`. The shader outputs fog colour/alpha with hardware blending, so it does not sample scene colour. URP’s installed feature declares the depth read and uses its static render function. There is no custom colour texture allocation or global texture publication.
5. **Final implementation:** `DistrictFog19V03.cs`, `DistrictWeather19V03.cs`, `DistrictFog19V03.shader`, `MistSoft19V03.shader`, and editor builder `V19PaletteP3.cs`.
6. **Missing information:** Fedya’s approval of the final density and chosen future tree references; production GPU/mobile targets are not validated here.

## Handoff

Play mode is stopped. The editor is left in saved, clean `Map_Look_v18_Play`; the Unity lock is released when this report is handed back. Nothing was committed or pushed. No downloads, legacy look builds, layout builds, route restarts or changes to runInBackground were made.

Resume only after Fedya approves checkpoint P: carry the approved fog/palette into full v19, rebake its height field after the stronger terrain, then restart all 15 v18 routes as `before18_g18_v02` and continue G18’s layout, v19 build, route checks and v17 | v18 | v19 sheets. Tree work waits separately for approved references.
