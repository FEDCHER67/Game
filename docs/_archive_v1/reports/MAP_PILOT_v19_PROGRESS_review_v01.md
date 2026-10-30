# G18 — final v19 pilot build and validation

2026-10-14. Scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play.unity`, Unity 6000.5.11f1. The final layout is built and review shots are ready. Automated checks below are evidence, not Fedya's subjective acceptance.

## Latest instructions override the original bridge brief

- Fedya cancelled **all version comparisons**: no final v17/v18 routes, before/after or three-column sheets are required. This report and the final sheets review **v19 alone**. Historical baseline reports, captures and measurements remain preserved.
- Fedya approved checkpoint P, then requested Rough fog v04 plus **25% of the difference toward v03**, retaining the v04 contrast, sky and grade. Forest retains v03 fog. The approved palette/sky table applies to all ten districts.
- The approved G19 CC0 happykeys trees and rocks are integrated. The later shorter/thicker tree and vertex-wind request was **cancelled and transferred to G23**. It is not part of this delivery. Two unused wind shader drafts are parked outside Assets in `Working/Reviews/Map_v19_Pilots/cancelled_tree_draft_v01/`; no tree instances received that change.
- Global palette, sky, atmosphere, approved nature and life were later authorized beyond the original pilots. Building/road layout changes remain limited to the pilots and their road chain.
- Overnight protocol: no questions; G18 Unity priority; release the lock before the Claude review bridge; apply at most two fix rounds. No commits, staging, pushes, WORK_SYNC edits or sound downloads. Neither run-in-background setting was changed.

## Start here: final review images

All paths below are under `Working/Reviews/Map_v19_Pilots/`. Images are actual Unity renders; sheets only resize and label them. Walking/van/top poses retain the original coordinates, directions and framing. A relocated building can intentionally occupy a formerly open view.

| Sheet | Content |
| --- | --- |
| `review_v19_h.jpg` | Hamlet: 13 walking and 4 van poses |
| `review_v19_r.jpg` | Road chain: walking, bridge raised views and van approaches, 11 poses |
| `review_v19_k.jpg` | Rough District: 11 walking and 4 van poses |
| `review_v19_t.jpg` | One top view of each pilot |
| `palette_test_rough_v05.jpg` | Final fog/sky/grade, including garage lane and inner courtyard, 7 poses |
| `palette_test_transition_v05.jpg` | Hamlet → road → Rough District, 4 poses |
| `review_v19_trees.jpg` | Integrated happykeys trees at the Rough garages |
| `review_v19_rocks.jpg` | Forest, village, fields and residential rock clusters |

The 46 original-pose PNGs are `after_s1*.png`; the 12 atmosphere captures are `palette_new_v05_*.png`; four nature captures are `nature_after19_*.png`. `v19_review_sheet_manifest_v01.json` maps every sheet row to its original PNG. The integrity check decoded all 69 distinct sheet/source images successfully. No final comparison sheets were produced.

## Layout, scale and terrain

62 existing buildings moved, 10 garage shells were added, and 18 roads changed. No existing building dimensions or nonpilot building placements changed; the final footprint audit found no new building overlaps. Hamlet houses and their plots form three closer groups, with a shortened southern loop, orchard workyard, hay field, allotments and B02 loading space. Rough blocks form courtyard groups with garage rows, service yard, parking and playground. Four east garages were shifted west after they obstructed the real van loop. The Hamlet scarecrow was moved off a required passage.

| Final v19 metric | Value |
| --- | ---: |
| House footprint-edge gaps, current two-neighbour mean / maximum | 28.50 / 50.76 m |
| Block footprint-edge gaps, current two-neighbour mean / maximum | 6.22 / 19.25 m |
| Hamlet district area / building coverage | 47,268 m² / 6.03% |
| Rough district area / building coverage | 39,131.52 m² / 30.59% |
| 16 household plots, combined area | 7,392.65 m² |
| Hamlet / Rough largest building-free circle **diameter** | 86.05 / 33.29 m |
| Shortened `02_h_loop` centreline | 160.13 m |

Neighbour pairs are the union of each building's two nearest neighbours. Building-only empty circles do not count orchards, fields, gardens or terrain as occupancy. The Hamlet still has broad working-land views; this is not a claim that every large gap became built up. Original per-building/point/road change lists and historical spacing measurements remain in `ArtSource/References/Map/MAP_PLAN_R01_v19_REPORT.md` and `MAP_PLAN_R01_v19_CHANGES.json`; the final review does not require their version comparison.

Terrain includes connected gullies/ravines, hollows, garden rises, road cuttings and larger landforms. Measured final height changes span -3.31 to +7.41 m in the Hamlet, -5.50 to +11.76 m on the road chain and approximately 0 to +3.13 m around the Rough edge. Calm yards and road fitting deliberately attenuate some design peaks. The final isolated 11.8 m rise at (438,638), radius 22 m, has measured clearance from buildings, roads, water and fences; it does not disturb the main road. Design targets are not presented as achieved heights everywhere.

Road measurements use the built surface: maximum longitudinal grade over a 6 m window, supported by 2 m samples. **All pilot streets and the road chain meet ≤8%; the maximum is 7.7% on `hamlet_rough_e`.** North bridge deck is 0.5%; Rough drive is 0.8%. Whole-map sampling also records pre-existing steeper Elite Hill roads (up to 24.3%) and the Tramduro bridge (22.9%), outside this layout scope. This is not a whole-map ≤8% claim.

One continuous TerrainData and matching TerrainCollider have zero holes. All 66 new purposeful-place ground anchors have renderer bottoms between -0.08 m and 0 m relative to the anchor ground. The steep NW Hamlet outside bank around (160,606) still falls about 6.4 m within 2 m; half-metre profiles are in `seams_ground_final_v01.txt`. It is continuous ground, not a terrain tile crack, but remains a steep boundary and is not certified as a traversable surface. Corner-by-corner fitting of every old prop is not claimed.

Deliberate broad views include the working field at h08, west orchard/meadow at h12, and bridge landscape openings. Relief and built groups compose the road endpoints; fog is atmospheric support. The old pond viewpoint h06 is now partly screened by the nearer household/fence/hay group. Final aesthetic acceptance remains with Fedya.

## Palette, sky, fog, nature and life

Per-district v19 material/ground variants interpolate toward the bright legacy colours. Shared `Look_mat_*` materials and v07 textures are untouched. Hamlet uses the legacy fruit/apple tree treatment and retains hedges and iron fences. Local URP Volumes and the district controller blend grade, sky colours/clouds, sun/ambient intensity and haze. A common 60 m blend also drives ambience; the final road sample measured 58.09 m between 5% and 95% Rough weight, with a maximum weight change of 0.033 per roughly 1.02 m step.

| District | t | Implemented mood |
| --- | ---: | --- |
| Forest | .50 | grey-green mist; approved v03 dense fog |
| Hamlet | .80 | brightest, clean sunny blue/cloudy village |
| Construction | .60 | neutral daylight and dust haze |
| Rough | .50 | cold, desaturated, dark overcast, retained contrast |
| Downtown | .60 | bright, colourful blue sky |
| Port | .55 | cooler sea mist |
| Elite | .75 | clean sunny gardens |
| Fields / Quiet Valley | .75 | pastoral blue and soft clouds |
| Beach | .75 | warm sunny exposure below Hamlet |
| Tramduro | .60 | slightly muted sea haze |

Rough v05 distance density is **0.01135**, haze starts at **33.75 m**, ground extinction is **0.01375** (base 0.055 × 0.25). Forest remains **0.026** distance / **0.0396** ground. v04 contrast +18, saturation -35 and exposure -0.20 remain on Rough. Low banks include stronger local patches and clear pockets; close droplets stay restrained. The scene has 18 banks, 25 scatter halos and two van headlights connected to fog. Forest's water-in-air treatment remains unchanged. `palette_test_rough_v05.jpg` is the requested final re-shot.

Happykeys integration: **1,269** Rough/fade-zone tree replacements (T01/T02/T03: 435/403/431), deterministic irregular placement, varied yaw and ±15% scale, cold bark recolour, **2,135** explicit manifest capsule proxies. Core audit found no remaining ordinary deciduous tree prototype; conifers and soft bushes remain. The pale pole seen near k01/k10 is a concrete street lamp, not a birch. No shortening, trunk widening or wind change from G23 was applied.

There are **280 rocks in 60 natural clusters**, with 247 manifest box proxies; R01 is decorative without collision. Six larger R11 pilot blockers and four source-fitted solid logs supplement them. Cluster selection excludes roads, paths, buildings, fences, water and gameplay points. Original vendor FBXs remain byte-identical: 14/14 checked. Licence/provenance is copied into `Assets/OnlyVolunteers/ThirdParty/happykeys_rocks_dead_trees/v01/README.md` (happykeys/Trekkerac, CC0).

The v02 storytelling kit adds laundry, garden/flower clusters, gate furniture, doghouse, hen enclosure, wood/axe, bicycle and household details. Three further occupied-house clusters add curtains/warm panes and three chimney emitters. Five butterflies and the existing Rough black crows are retained. Forty additional lightweight birds span Downtown, Beach, Port, Tramduro, Elite, Valley, Hamlet and Forest edge; each group has two perched birds and the rest circle/flap. They are inexpensive stylized silhouettes, not distinct zoologically detailed models. No human/character animation was authored.

Not all requested animals and sound events exist yet: no new animated hens/dog/cows/bee models, and missing library sounds are intentionally silent, especially in Rough/Forest. They are listed below rather than filled with cheerful or misleading substitutes. No audio downloads occurred.

## Real Play routes and contact tests — v19 only

Route runs use the stock van **E0/B0/H0**, mass 1,800 kg, motor 1,250 Nm, maximum 105 km/h, brake 4,200, steering 34°/11°, anti-roll 9,000. The ordinary road driver targets 45 km/h. The existing KCC and van controllers run through actual Unity frames at 1/60 s. Crowd/police are temporarily disabled only for repeatable route tests, not in the saved scene. Awake initialization is verified before stepping; neither background setting is changed. The ordinary-scene smoke test separately leaves both systems active.

The final centreline-following file is `routes_v19_streets_final_v03.json`; result evidence is `routes_streets_final_g18_v03.json/.txt` under the review folder.

| Route | Time | Driven distance | Result |
| --- | ---: | ---: | --- |
| v01 B02 → B03 | 61.4 s | 515.5 m | PASS |
| v02 north bridge → B03 | 32.1 s | 241.0 m | PASS |
| v04 B03 → north bridge | 30.3 s | 241.2 m | PASS |
| v06 B02 → north bridge | 32.0 s | 256.6 m | PASS |
| v08 Rough drive | 46.2 s | 396.7 m | PASS |
| v09 Hamlet loop | 23.9 s | 172.7 m | PASS |
| v10 Hamlet south | 13.3 s | 116.1 m | PASS |

All seven arrived, none tipped and no frame had fewer than two grounded wheels. Peak roll was 1.1°, pitch 5.6°. The harness's approximate chassis-clearance value is uncalibrated (negative even on flat roads); its repeated “chassis touches” event is **not reliable proof of grounding**. Speed, successful passage, tilt and wheel-contact results are the useful observations.

The original 15 frozen lines were also run on v19 final geometry in `routes_after_s1_g18_v03.json/.txt`. Its three direct vehicle cuts are blocked: v03 after 25 m / 12.1 s at the ravine/rocks; v05 after 33 m / 12.1 s at terrain/trunks; v07 after 28 m / 11.8 s at the fence. Road travel succeeds where the direct cut does not. Old fixed walk lines w01, w02, w04 and w05 do **not** all pass: w01 stops at the cut; w02 intersects moved house 18; w04 points through the west base house; w05 hits garage 003. These raw failures remain recorded, not silently rewritten as successes.

Readable final passages and access routes were then tested against the built geometry:

| Passage | Time / travel | Result / evidence |
| --- | --- | --- |
| Hamlet orchard, foot | 25.3 s / 112.8 m | PASS, `routes_supplement_g18_v02` |
| Road berm, foot | 28.9 s / 135.0 m, max rise 2.6 m | PASS, same evidence |
| Rough west passage, foot | 18.7 s / 79.4 m | PASS, same evidence |
| Rough playground gate, foot | 12.0 s / 55.9 m | PASS, same evidence |
| B03 courtyard via east entry | 12.8 s / 59.5 m | PASS, same evidence |
| B02 door approach | 3.7 s / 17.1 m | PASS, `routes_after_s1_g18_v03` |
| Hamlet orchard, van, north side of hay cluster | 37.6 s / 108 m, target 16 km/h | PASS, `routes_contacts_final_g18_v03` |

The orchard gate is visibly and physically 8.6 m wide. The route goes north of the hay stack instead of through it (`orchard_passage_finish_v04.json`). Road-chain and Rough alternate passages are pedestrian passages; blocked direct van cuts are intentional. The orchard van passage has greater tilt (9° roll / 17° pitch) than the streets, no tipping or airborne frames.

Natural contact evidence:

- **Tree:** `routes_body_contacts_g18_v06` records actual PhysX contact with `TREE_BARE_01_TRUNK` and stops the van. The walker slides around the trunk rather than passing through it; 178 recorded positions, actual runtime KCC radius 0.35 m, minimum surface gap 0.00079 m and zero computed penetration (`trunk_contact_geometry_v02.txt`). Earlier v01 used the edit-mode 0.5 m radius and is superseded.
- **Rock:** the van has actual `ROCK_11_BOX` contact; the walker is blocked at the same visible rock (`routes_body_contacts_g18_v06`, `routes_supplement_g18_v02`).
- **Log:** in-place log approaches can be blocked first by nearby fence/well/terrain. The walker takes a 1.7 m deflection around isolated log 02, with no measured mesh penetration (`routes_log_walk_final_v04`, its trace CSV); the nonconvex-mesh ClosestPoint gap in `log_contact_geometry_v01.txt` is invalid and is **not** used as evidence. To separate the log from neighbouring obstacles, the actual log 02 instance was temporarily moved across a clear road **in unsaved Play only**, keeping its mesh/material/collider unchanged. The van stops with actual `V19_log_02` PhysX body contact in `routes_log_flat_g18_v08`. The original scene placement is restored on Play exit. This proves the collider, not every original log approach.
- Diagnostic `body_contacts_g18_v05` failed because the transient witness was initially in an Editor folder. It was moved through AssetDatabase, preserving its meta; v06 succeeds. The witness is editor-conditional, never persisted into the scene. Failures from v05 are not current runtime errors.

## Acceptance matrix

Evidence abbreviations: **R** = `Working/Reviews/Map_v19_Pilots/`; **M** = `ArtSource/References/Map/`. Statuses apply to the named check, not to unchecked parts of a wider specification.

| Check | How / result boundary | Evidence | Status |
| --- | --- | --- | --- |
| Human scale, dimensions | No changed old building sizes; stock player/van; street captures | R`data_final_geometry_v03.json`, h/k sheets | PASS |
| Human scale, carried NPC fit | Carrying through each changed entrance was not exercised | No carry-test evidence | NOT RUN |
| Compaction and circulation | Measured footprint gaps, whole-plot grouping, final road/base/passages | M`MAP_PLAN_R01_v19_REPORT.md`, final street/passages routes, h/k/t sheets | PASS |
| Terrain, achieved relief / pilot roads | Surface sampling, final rise, calm plots and ≤7.7% road chain | R`terrain_full_v03.txt`, `road_grades_final_v03.txt`, r/t sheets | PASS |
| Ground anchors and terrain continuity | One TerrainData, no holes, 66 new anchors -0.08..0 m, continuous blend; steep outer bank explicitly recorded | R`scene_final_audit_v01.txt`, `seams_ground_final_v01.txt` | PASS |
| Ordinary van travel | Seven final street routes and orchard passage, no tipping or airborne frames | R`routes_streets_final_g18_v03`, `routes_contacts_final_g18_v03` | PASS |
| Off-road travel | Three direct van cuts blocked; one readable foot passage per pilot, orchard also usable by van | R`routes_after_s1_g18_v03`, `routes_supplement_g18_v02` | PASS |
| Original frozen walk lines | Four obstructed lines retained; replacement approaches pass separately | R`routes_after_s1_g18_v03` | FAIL |
| Natural collision | Actual trunk/rock van contacts, walker block/deflection; isolated actual log proxy van contact | R`routes_body_contacts_g18_v06`, `routes_log_flat_g18_v08`, trunk/foot traces | PASS |
| Views, captured inspection | All 46 same poses inspected; working-field/bridge panoramas documented | R`review_v19_h/r/k/t.jpg` | PASS |
| Final subjective visual acceptance | Fedya approved palette P; final layout and v05 sheets still need his review | Final sheets above | NOT RUN |
| Unfinished gaps, ordinary review views | No missing scripts/materials/shaders/terrain holes; no obvious voids in inspected poses | R`scene_final_audit_v01.txt`, final sheets | PASS |
| All reachable raised surfaces / building collision | Per-type approach/jump/landing/exit tests and full old-prop corner audit were not run in this layout stage | No complete architectural traversal matrix | NOT RUN |
| Environmental detail | Coherent household/garage/workyard groups, imported kits, trees/rocks and life | R`kit_v01_unity_import_g18_v01.txt`, `kit_unity_import_v02.txt`, nature sheets | PASS |
| Connectivity, exported graphs and pilot routes | Road graph one component; crowd graph rebuilt; B02/B03 road and foot approaches pass | M v19 report/CHANGES, R`police_final_v03.txt`, final routes | PASS |
| Every relocated POI, loaded van and carried NPC | Graph validation exists, but exhaustive individual physical test not completed | Scope limitation | NOT RUN |
| Full-scene initialization | 600 actual frames / 10 simulated seconds with crowd/police active; bird displacement and audio wiring inspected; zero new Console errors | R`runtime_final_smoke_v01.txt`, `runtime_audio_final_v01.txt` | PASS |
| Listening test / missing ambience | Paused stepping does not play DSP audio; audible mix not claimed; missing clips intentionally silent | Audio inventory below | NOT RUN |
| Data/assets/settings preservation | Protected snapshots, vendor FBX hashes, metas, no ProjectSettings diff | R`final_integrity_v01.json` | PASS |
| Performance | Explicitly excluded by Fedya; no FPS benchmark | User instruction | NOT RUN |

The crowd export has one connected graph, 100 POIs, 20 loops and 110 connections, with no reported blocked/illegal crossings or sand violations. Runtime data parses 4,228 nodes, 70 runtime POIs plus 20 spawns and 10 witness locations. Police rebake has 1,596 nodes / 1,632 edges and five bases. The source pedestrian road subset still includes disconnected decorative beach footbridges outside the pilots; it is not represented as one universally walkable network.

## Ambience inventory and deferred source choices

`Ambience_v19_full_v02.asset` extends the existing AmbienceData/Player, with per-revision mappings, district crossfades and small spot emitters. Existing library mappings: Hamlet/Elite/Fields `amb_birds`; Downtown `amb_city`; Port/Tramduro `amb_sea_gulls`; Beach `amb_sea`. Existing river/lake/sea/fountain beds remain. Rough/Forest/Construction have no inappropriate fallback bed. Hens, crow and distant-dog spot IDs remain silent until clips are approved.

Runtime wiring found 308 AudioSources, 284 with clips, one enabled listener, village bed at 0.20 and fountain bed at 0.32. `isPlaying` was false during paused frame stepping, so this is **wiring/gain evidence, not a listening pass**. The water bake contains 38 zones; no waterfall emitter was generated, which remains an audio gap.

Source shorthand below is a proposal only. No missing sound was downloaded or cleared by the lead. **FS-CC0** means search Freesound with a CC0 licence filter, then verify the exact selected file's licence/provenance; the site has several licences, so this is not a licence claim about every search result ([Freesound licensing FAQ](https://freesound.org/help/faq/)). Verified candidates: [Crows singing, IgnasD, CC0](https://opengameart.org/content/crows-singing); [wind1, Luke.RUSTLTD, CC0](https://opengameart.org/content/wind1); [Kenney Impact Sounds, CC0](https://kenney.nl/assets/impact-sounds). Suitability still needs listening and the lead's download approval.

| District | Missing sound / event | Suggested free source and licence |
| --- | --- | --- |
| Rough | Caws; distant stray dog; car alarm; cold wind; flickering-lamp buzz | Crows singing CC0; wind1 CC0; FS-CC0 for dog/alarm/electrical buzz |
| Hamlet | Hens/rooster, distant dog/cows, bees, wind chimes | FS-CC0, one approved recording per event |
| Forest | Woodpecker, cuckoo, owl, tree wind, edge crows | FS-CC0 for species; wind1 CC0; Crows singing CC0 |
| Downtown | Pigeon coos, city chatter, distant music | FS-CC0; select music separately with explicit CC0 rights |
| Beach | Distant voices | FS-CC0; existing sea/gull sounds retained |
| Port | Ship horn, crane/container clanks | FS-CC0 horn; Kenney Impact Sounds CC0 as candidate clanks |
| Elite | Sprinklers and distant mower | FS-CC0; existing fountain bed retained |
| Fields | Larks, crickets, field wind, waterfall emitter/recording | FS-CC0 species/waterfall; wind1 CC0 |
| Construction | Machinery, hammering, diegetic radio | FS-CC0 machinery/radio; Kenney CC0 impacts as hammer candidate |
| Tramduro | Military-radio chatter, distant helicopter | FS-CC0, avoid copyrighted broadcast content |

## Files and build handoff

Final source data:

- `ArtSource/References/Map/map_plan_v19.py` and `map_plan_v19_build_v02.py`.
- `MAP_PLAN_R01_v19_build_v02.json`, `Look/look_v19_build_v02_flat.json`, `Greybox/greybox_v19_build_v02_flat.json`, `Crowd/crowd_v19_build_v02.json` under the same folder.
- `MAP_PLAN_R01_v19_BUILD_PATCH_v02.json` records the clearance/calm-yard fixes. `MAP_PLAN_R01_v19_FINISH_v03.json` records the final isolated rise, gate and explicit trunk proxies. Original v19 plan/report/PNG/CHANGES remain preserved.

Final Unity assets:

- `Assets/OnlyVolunteers/Scenes/Map/Map_Greybox_v19.unity`, `Map_Look_v19.unity`, `Map_Look_v19_Play.unity`. Earlier G18 scene iterations remain as separately named review scenes.
- `Assets/OnlyVolunteers/Map/LookV3/Generated/Map_Look_v19_build003/` and `Assets/OnlyVolunteers/Map/LookV3/Palette19/Full_v02/`, including `Finish_v03/Terrain_finish_v03.asset` and matching fog-height texture/gate.
- `Assets/OnlyVolunteers/Police/Data/police_v19_build_v03.asset`; `Assets/OnlyVolunteers/Map/Data/crowd_v19_build_v02.json`; `Assets/OnlyVolunteers/Audio/Resources/Water_v19.asset` and `Ambience_v19_full_v02.asset`.
- `Assets/OnlyVolunteers/ThirdParty/happykeys_rocks_dead_trees/v01/`, plus `Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v01/` and the previously created v02 storytelling kit. Provenance and import audit files are retained.

Implementation files are in `Assets/OnlyVolunteers/Map/LookV3/Editor/`: `V19Infill`, `V19FullPalette`, `V19FullLife`, `V19FinalGeometry`, `V19FullReview`, `V19PilotTools` and the checkpoint P builders. Terrain uses the existing HeightModel/V3Terrain path with v19 fields and final geometry overlay. `Palette19/DistrictWeather19V05`, `DistrictFog19V05` (including shader), shared `DistrictBlend19` and `DistrictLife19V02` implement the active district presentation. The transient `G18RouteContactWitness.cs` is editor-conditional and never saved in a scene.

Revision switches were added to MapLookBuilderV3 / MapLookGameplayV3, MapLookBuilder, MapGreyboxBuilder, MapCrowdPlacer, V3LookData and PoliceBaker. HeightModel's changes fit v19 relief/plots. AmbiencePlayer adds the optional scene-owned data override and spatial district mix. Existing revisions keep their former data paths.

The delivered scenes are the reviewable result. For another rebuild, allocate a **new numbered output revision** first; do not blindly rerun destructive legacy menus or overwrite `Full_v02`. Pipeline order used here: generate v19 data and corrected v02 exports → import/validate kits and happykeys → style-v3 Look build → apply approved full palette/life → gameplay build from the prepared Look → clinic loop and headlight references → police/crowd/ambience/water revisions → final terrain/gate/trunk geometry in Look and Play → final Greybox build → route checks/captures. Rebuilding only the base Look menu does not reproduce the subsequent palette/finish overlays. Never use the legacy “latest plan” look menu.

## Integrity and remaining limits

`final_integrity_v01.json` checked 185 baseline files, 688 prebuild protected files and 5,326 full-build snapshot files. No protected file is missing. Differences are limited to the recorded permitted builder/tool/runtime source edits; no protected old scene/data, legacy material or v07 texture changed. The explicitly authorized earlier C0 v18 style-v3 replacement had already been completed before the full-build snapshot. All checked Unity files/folders have metas; 14 vendor FBXs match the source exactly.

After the last scene save, the fog component's temporary renderer override caused Unity to serialize the v19 pipeline into QualitySettings. Its original `Assets/Settings/PC_RPAsset.asset` reference was restored through Unity and saved. Final `git diff --exit-code -- ProjectSettings/` is empty. Fog remains enabled in the scene and acquires its v19 renderer on the next Play/scene initialization. Both run-in-background values remain false and were never assigned. No external-window minimising/moving/resizing was used in this continuation; Game-view focus and initialized frame stepping were sufficient.

Open items are explicit: final human layout/atmosphere approval; carried-NPC entry and architectural traversal tests; exhaustive every-POI physical audit; missing sound choices and an audible mix test; the steep outer Hamlet bank and old out-of-pilot grades; a few deliberately broad working-land views; G23's separate tree redesign. The full scene has the clinic loop installed, but a complete catch/load/operate/save gameplay loop was not retested for this map layout task. No performance benchmark was run.

The editor is left on the saved `Map_Look_v19_Play`, Play stopped, unpaused, capture timestep restored to zero and no transient collision witness in the scene (`editor_final_state_v01.txt`). The lock is released for the overnight review. Review bridge results and any fix rounds are recorded below once returned.
