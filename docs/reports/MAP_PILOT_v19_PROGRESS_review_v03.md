# G18 — v19 Hamlet fix round 1, final review v03

2026-10-14. Current scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play.unity`. The wider orchard van turn and all 22 final route outcomes pass. The Hamlet compaction targets are met, the courtyard has additional purposeful infill, and the new Rough fog is halfway from v04 to v03. This report supersedes the old round-0 report and the startup-blocked review_v02 report. G18g aerial perspective follows separately.

## Current instructions and review resolution

- Fedya explicitly cancelled all v17/v18 comparisons and comparison sheets. Deliver v19 alone. The bridge request for v18 spacing/top-down comparisons and a round-0 comparison sheet is superseded; historical measurements remain in their original files.
- Latest Rough request replaces 25% with **50% of the v04→v03 difference**. Forest and other districts stay unchanged. The new sheet is **palette_test_rough_v06.jpg**.
- The startup blockage is resolved. Fedya explicitly requires **Ignore Warning** on Unity's Administrator Privileges Detected dialog; never Restart as Standard User. The contrary old bridge precondition is superseded.
- Tree shortening/thickening/wind belongs to G23 and remains cancelled here. Approved happykeys integration is retained.
- No questions, commits, staging, pushes, deletions, WORK_SYNC edits or downloads. The lock helper is used. No run-in-background setting, ProjectSettings or global URP asset is changed by this continuation.

## Final review images

All evidence paths below use `R = Working/Reviews/Map_v19_Pilots/`. Every sheet was opened and inspected. They are unretouched Unity renders, resized and labelled only.

| Sheet | Contents |
| --- | --- |
| R`review_v19_r1_h.jpg` | 17 original Hamlet walking/van poses |
| R`review_v19_r1_r.jpg` | 11 original road/bridge walking/van poses |
| R`review_v19_r1_k.jpg` | 15 original Rough walking/van poses |
| R`review_v19_r1_t.jpg` | 3 original top views |
| R`palette_test_rough_v06.jpg` | Latest fog, 7 Rough poses including garage lane and inner yard |
| R`palette_test_transition_v06.jpg` | 4 original Hamlet→road→Rough transition poses |
| R`review_v19_trees_v02.jpg` | Approved bare-tree integration |
| R`review_v19_rocks_v02.jpg` | Forest/village/fields/Rough natural clusters |

Final 46 source captures are `after_r1b_*.png`; atmosphere sources are `palette_r1_v06_*.png`, nature sources `nature_r1_*.png`. `v19_review_sheet_manifest_v03.json` maps them. The earlier partial `after_r1_` set predates the final garden clearance and is diagnostic, not final. All 69 distinct final sheet/source images decode successfully.

## Layout and terrain

The current source is build_v07: 511 source buildings, 62 existing placements changed, 12 added structures (10 garages and 2 barns), 18 changed roads. Existing building dimensions and nonpilot placements are unchanged. There are no new building/plot overlaps. A pre-existing 3.112 m² overlap between 02_B03 and 02_h_north is retained. Two original-size kit sheds are additional scene infill, counted separately below.

| Current v19 metric | Result |
| --- | ---: |
| Hamlet house edge gap, two-neighbour mean / maximum | 17.934 / 25.334 m (targets ≤18 / ≤30) |
| Hamlet building-free circle diameter | 40.901 m (target ≤45) |
| Hamlet district / building coverage | 31,273.5 m² / 9.715% |
| Household plots | 16, total 6,028.762 m² |
| Hamlet short loop length | 92.056 m |
| Rough block edge gap, mean / maximum | 6.217 / 19.252 m |
| Rough district / source-building coverage | 39,131.52 m² / 30.587% |
| Rough building-free circle before / after two kit sheds | 33.287 / 28.372 m |

Evidence: `data_round1_geometry_v02.json`, `courtyard_geometry_finish_v02.json`. Empty-circle metrics count buildings, not trees, garden beds or terrain. Hamlet houses now group along shorter northern streets; the southern land is deliberately an orchard/working field, old well and relief rather than another residential block. Two barns, hay groups and field edges give it purpose. The dead-end field lane is retained as field09 service access, not represented as a through road. Both southern POIs were checked against the actual collider grid and walked successfully (field09 and old well). Ground views h07/h11 end against relief/tree groups; h08/h12 retain broader working-field openings. This is an explicit aesthetic limit for Fedya, not a claim that all meadow views disappeared.

Rough k03 now has two worn sheds, garden beds, low fencing, a bench and worn working strips in the middle/near courtyard. The first garden placement obstructed the playground approach. The final clearance revision moved the beds/fences 8 m east and the bench to (695,599), refitted soil to ground, and retained the original playground walking line. The final route passes; no obstacles were deleted to make it pass.

The orchard van takes a wider northern turn around the existing hay cluster: (212,456)→(218,461)→(230,464)→(239,464)→(244,457)→(241.6344,448.8869). All hay remains. The build_v07 source retains 18 earlier purposeful hay clearance moves.

Relief includes connected ravines and gullies, hollows, calm plots, fitted roads, two southern view hills centred at (267,408), design height 7.8 m, and (325,417), 6.5 m, and the isolated 11.8 m rise at (438,638). Achieved heights, after fitting, are:

| Pilot | Height span | Range | Slopes >25° / >45° |
| --- | --- | --- | --- |
| Hamlet | -3.54..8.10 m | 11.63 m | 4.1% / 0.11% |
| Road chain | -5.43..11.76 m | 17.19 m | 12.4% / 0.79% |
| Rough | 0..3.06 m | 3.06 m | 0.1% / 0% |

All pilot road grades meet ≤8%: main chain max **7.7%**, Hamlet streets ≤0.2%, Rough drive 0.8%, north bridge 0.5% (`road_grades_round1_v02.txt`). Pre-existing out-of-scope Elite grades up to 24.3% and Tramduro bridge 22.9% remain. One continuous TerrainData matches its collider, with zero holes. The 75 purposeful anchors lie -0.08..0 m from sampled ground; the 15 new courtyard anchors are within floating-point epsilon of ground. The steep outside NW Hamlet bank still drops 6.43 m over 2 m near (160,606): continuous terrain, not a tile crack, and not certified traversable. Evidence: `scene_round1_audit_v02.txt`, earlier detailed `seams_ground_final_v01.txt`.

## Palette, fog, nature and life

The approved ten-district palette/sky table is retained: Forest .50 misty grey-green; Hamlet .80 brightest sunny; Construction .60 dusty daylight; Rough .50 cold overcast; Downtown .60 colourful; Port .55 cooler mist; Elite .75 clean sun; Valley .75 pastoral; Beach .75 warm sun; Tramduro .60 sea haze. Shared legacy Look_mat_* and v07 textures remain unchanged. District grade, sky, lighting and ambience use the same 60 m spatial blend. The prior measured road 5–95% Rough blend spans 58.09 m.

| Rough v06 strength parameter | Final value / derivation |
| --- | --- |
| Distance density | .0179 = lerp(.0048, .031, .5) |
| Haze start | 22.5 m = lerp(45, 0, .5) |
| Ground weight / extinction | .5 / .0275 = .055 × .5 |
| Camera droplets | 82 = halfway from 24 to 140 |
| Droplet opacity | .074 = halfway from .018 to .13 |
| Three v04 mist pockets | Opacity .1425 = halfway from .065 to .22; size/height halfway |
| Eleven banks absent in v04 | Opacity .11, half v03 vertical thickness/height |

All 14 Rough banks use their relocated v19 centres; four Forest banks are untouched. Forest density remains .026 and ground extinction .0396. The approved v04 sky, contrast +18, saturation -35, exposure -.20 and cold fog colour remain; sky optical contribution, forward scatter, lamp/headlight strength were not treated as fog-density changes. Scene totals: 18 banks, 27 halos (including two van lights), two headlights. Near paths and entrances remain visible in the v06 sheet. This is the requested numerical halfway strength, not a claim of a subjective halfway appearance.

The old fog runtime could switch the global quality pipeline and serialize that reference on disable. That implementation is removed. `DistrictFog19V05` now owns a per-camera `DistrictFogPass19V01`, with transient materials and a RenderGraph depth read/alpha overlay before transparent objects. It enqueues on the existing camera renderer without modifying any renderer or pipeline asset. A matching-pose probe and full captures preserve the existing look. The active pipeline remains PC_RPAsset; ProjectSettings diff is empty.

Approved happykeys content remains: 1,269 T01–T03 Rough/fade-zone trees (435/403/431), varied yaw/±15% scale and cold bark; 2,135 manifest capsule proxies. No G23 shortening/thickening/wind. Other trees retain their models/materials. 280 rocks in 60 natural clusters have 247 manifest box proxies; R01 is decorative. Six R11 pilot blockers and four solid logs supplement them. All 14 imported FBXs match their CC0 vendor sources byte-for-byte; licence README is in `Assets/OnlyVolunteers/ThirdParty/happykeys_rocks_dead_trees/v01/`.

Storytelling kit v02 includes household/workyard clusters, laundry, gardens, flowers, gate furniture, dog/hen shelters, wood/axe, bicycle and household props. Three occupied houses have warm panes/curtains and chimney smoke. Five butterflies, 13 Rough black crows and 40 additional lightweight birds supply visual life. Missing animated hens/dogs/cows/bees and missing clips are openly deferred; no downloads occurred.

## Final actual Play routes

Input `routes_v19_round1_final_v04.json`; result **routes_round1_final_g18_v05.json/.txt**. All 22 outcomes match expectation. This is the current route matrix. The old frozen w01/w02/w04/w05 lines intersect relocated buildings/terrain and are **SUPERSEDED**, not current access routes. Earlier failed garden-stage result v04 is preserved as diagnostic.

Stock van E0/B0/H0, mass 1,800 kg, motor 1,250 Nm, max 105 km/h, brake 4,200, steering 34°/11°, anti-roll 9,000. Roads target 45 km/h, orchard 16 km/h. Existing KCC/van controllers run actual Unity frames at 1/60 s after Awake. Crowd/police are temporarily off only during repeatable route tests; both stay enabled in the saved scene and ordinary smoke.

| Route | Time | Travel | Expected outcome |
| --- | ---: | ---: | --- |
| `v09_road_hamlet_loop` | 17.5 s | 137 m | PASS |
| `v01_road_B02_to_B03` | 61.4 s | 516 m | PASS |
| `v02_road_bridge_to_B03` | 32.1 s | 241 m | PASS |
| `v04_road_B03_to_bridge` | 30.3 s | 241 m | PASS |
| `v06_road_B02_to_bridge` | 32.1 s | 257 m | PASS |
| `v08_road_rough_drive` | 46.2 s | 397 m | PASS |
| `v10_road_hamlet_south` | 13.3 s | 116 m | PASS |
| `v03_off_bridge_to_B03` | 12.1 s | 25 m | BLOCKED AS INTENDED |
| `v05_off_B03_to_bridge` | 12.1 s | 33 m | BLOCKED AS INTENDED |
| `v07_off_B02_to_bridge` | 10.4 s | 17 m | BLOCKED AS INTENDED |
| `w03_walk_B02_door` | 3.7 s | 17.1 m | PASS |
| `w01_walk_road_cut_replacement` | 31.5 s | 146.5 m | PASS |
| `w02_walk_hamlet_meadow_replacement` | 13.6 s | 63.7 m | PASS |
| `w04_walk_B03_yard_replacement` | 10.8 s | 50.0 m | PASS |
| `w05_walk_rough_north_replacement` | 7.2 s | 33.2 m | PASS |
| `p_van_hamlet_orchard_passage` | 46.3 s | 117 m | PASS |
| `p_walk_hamlet_orchard_passage` | 23.9 s | 111.5 m | PASS |
| `p_walk_road_berm_footpass` | 29.0 s | 135.1 m | PASS |
| `p_walk_rough_west_passage` | 18.7 s | 79.4 m | PASS |
| `p_walk_rough_playground_gate` | 12.0 s | 56.0 m | PASS |
| `p_walk_south_field09` | 15.0 s | 70.0 m | PASS |
| `p_walk_south_old_well` | 3.7 s | 17.0 m | PASS |

No van route tipped or had fewer than two grounded wheels. Orchard peak roll/pitch is approximately 11°/17°. The harness chassis-clearance estimate reads negative even on flat roads and is **not calibrated grounding evidence**; arrival, speed, actual contact witnesses, wheel contact and tilt are the valid measures.

Unchanged natural collision evidence remains valid: real trunk/rock van contacts in `routes_body_contacts_g18_v06`; walker trunk surface clearance 0.00079 m and zero computed penetration (`trunk_contact_geometry_v02.txt`); rock walker block; log walker deflection and real van contact with the same log temporarily isolated across a clear road in unsaved Play (`routes_log_flat_g18_v08`). The log result proves the collider, not every original log approach. No collision geometry changed in this final fix.

## Validation and remaining limits

| Check | Result / evidence |
| --- | --- |
| Compile / scene audit | PASS: 0 missing scripts/materials/unsupported shaders across 25,281 transforms; final Console 0 errors |
| Greybox | Rebuilt Map_Greybox_v19 from build_v07; final Look/Play retain additional palette/life/courtyard overlays |
| Clinic initialization | PASS: loop, registry, station, dropoff, runner and inventory all present (`clinic_round1_v01.txt`) |
| Ordinary Play smoke | PASS: 600 actual frames /10 simulated seconds, crowd and police active, KCC initialized, 0 Console errors (`runtime_round1_smoke_v02.txt`) |
| Road/POI graph | One source road component; crowd export 100 points/20 loops/110 connections, one network component, 0 blocked/illegal/sand violations. Old decorative beach footbridges account for five pedestrian subset components |
| Settings/assets | PASS: protected snapshots 185/688/5,326 files, no missing protected files; permitted builder source differences recorded; 14/14 vendor FBXs identical, no missing metas, empty ProjectSettings diff (`final_integrity_round1_v02.json`) |
| Walking/van/top review | All 46 poses and fog/nature sheets inspected; broad working-land openings documented |
| Carried-NPC and every architectural traversal | NOT RUN; no exhaustive carry/roof/jump/landing matrix |
| Every old prop corner / every POI loaded-van approach | NOT RUN; collider-grid checks, pilot routes and named southern POIs only |
| Complete catch/load/operate/save loop | NOT RUN; initialization checked, gameplay not redesigned |
| Audible mix | NOT RUN; wiring verified, no listening acceptance or missing-sound substitution |
| FPS | NOT RUN, explicitly outside priority |
| Human final layout/atmosphere approval | Still Fedya's decision; quantitative checks do not prove aesthetic acceptance |

## Ambience inventory and proposed sources


`Ambience_v19_full_v07.asset` extends the existing AmbienceData/Player, with per-revision mappings, district crossfades and small spot emitters. Existing library mappings: Hamlet/Elite/Fields `amb_birds`; Downtown `amb_city`; Port/Tramduro `amb_sea_gulls`; Beach `amb_sea`. Existing river/lake/sea/fountain beds remain. Rough/Forest/Construction have no inappropriate fallback bed. Hens, crow and distant-dog spot IDs remain silent until clips are approved.

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


## Current paths and rebuilding

Authoritative source: `ArtSource/References/Map/map_plan_v19_build_v07.py`, `MAP_PLAN_R01_v19_build_v07.json`, `Look/look_v19_build_v07_flat.json`, `Greybox/greybox_v19_build_v07_flat.json`, `Crowd/crowd_v19_build_v07.json`, `MAP_PLAN_R01_v19_BUILD_PATCH_v07.json`.

Final scenes: `Assets/OnlyVolunteers/Scenes/Map/Map_Greybox_v19.unity`, `Map_Look_v19.unity`, `Map_Look_v19_Play.unity`. Current generated Look: `Assets/OnlyVolunteers/Map/LookV3/Generated/Map_Look_v19_build009/`. Palette/life: `Palette19/Full_v07/`; terrain: `Full_v07/Finish_v03/Terrain_finish_v03.asset`; final fog/courtyard materials/meshes: `Full_v07/ReviewFinish_v02/` (includes GardenWorkSoil_v03 and DepthHeightFog_v06).

Gameplay revisions: `Assets/OnlyVolunteers/Police/Data/police_v19_build_v08.asset`, `Assets/OnlyVolunteers/Map/Data/crowd_v19_build_v07.json`, `Assets/OnlyVolunteers/Audio/Resources/Ambience_v19_full_v07.asset`, `Water_v19_build_v07.asset`.

Final overlay helpers: `Assets/OnlyVolunteers/Map/LookV3/Editor/V19ReviewFinishV02.cs`, `V19CourtyardClearanceV03.cs`; runtime `Palette19/DistrictFog19V05.cs`, new `DistrictFogPass19V01.cs`. Existing G18 layout/terrain/palette/life/bake tools remain the underlying implementation. `urp_camera_fog_validation_v01.md` documents the scoped renderer checks.

Rebuild into new numbered outputs: build_v07 data → style-v3 Look → full palette/life → gameplay/clinic → police/crowd/ambience/water → Finish_v03 terrain/clearances → ReviewFinishV02 → CourtyardClearanceV03 → validation/captures. The base Look menu alone does not reproduce overlays. Never use the legacy latest-plan menu.

Intermediate scenes retained for Fedya's later cleanup decision (none deleted):
- `Assets/OnlyVolunteers/Scenes/Map/Map_Greybox_v19_LayoutCheck_v01.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Greybox_v19_Review_v01.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_LayoutCheck_v01.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v01.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v02.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v03.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v04.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_LayoutCheck_v01.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_Review_v01.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_ReviewDraft_v04.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_ReviewDraft_v06.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Review_v01.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_ReviewDraft_v03.unity`
- `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_ReviewDraft_v05.unity`

Final state before bridge: saved Map_Look_v19_Play, Play stopped, not paused, capture timestep zero, both background values false, PC_RPAsset active. G18 lock released before review; it will be reacquired for the separately requested G18g. The latest user instruction resolves the earlier blocked bridge verdict. No completed G18g work is claimed by this report.
