# TASK M1 — World map v11 → R01 v16

Data and scripts only. No Unity build, NavMesh bake, driving test, asset import, commit or WORK_SYNC edit was performed.

## Deliverables

- `map_plan_v16.py` — exclusive-create converter, native flat adapters, v12 crowd algorithms, render and verification.
- `MAP_PLAN_R01_v16.json` — R01 core plus lossless source and optional extensions.
- `MAP_PLAN_R01_v16.png` — muted R01 style, exact source geometry and numbered POIs.
- `MAP_PLAN_R01_v16_OVERLAY.png` — 45% v16 PNG blended with the v11 preview at the identical viewport.
- `MAP_PLAN_R01_v16_REPORT.md` — this report.
- `Greybox/greybox_v16_flat.json`, `Look/look_v16_flat.json`, `Crowd/crowd_v16.json`.
- Shared `Greybox/flatten_plan.py` and `Look/flatten_look.py` have an isolated v16 dispatch plus optional `--plan`/output routing; legacy algorithms are unchanged.

## Coordinates and schema

No coordinate conversion: metres, bottom-left frame origin, +X east, +Y north; Unity `(x, terrain_height, y)`. Frame 1474 × 760 m. v12 core field names and flat consumer shapes remain available.

Extensions: `world_v11` (entire source); `district_mapping`, numeric `world_id`/`world_district_id` and string aliases; `base_mapping`/`gameplay_mapping`; raw `structures` and all named `pois`; `terrain_hints`/`vegetation_hints`; width-profile water; `road_areas`; exact `bridges` with deck polygons/axes/piers; special `fences` with gate intervals; all `sand_areas`; `police_parking_proposals`; optional `marina_enrichment` and its independent settings. Both flats retain these under `world_v11_extensions`. Look additionally exposes the optional marina layer at its root.

Buildings keep all source footprints, kind, floors, height and roof colour; centroid and minimum oriented box are derived. Look uses CCW exact footprints, constrained triangles and existing rect decomposition. Entrance direction is a labelled nearest-road proposal, not an approved door.

The source exporter records each of six City Beach paths twice, matching SVG border (#C2C2B7) and inner surface (#EBE8D9) strokes. All 84 source records remain in plan/flat extensions. Native flats emit 78 distinct source ribbons plus 8 bridge carriers (86 total): one inner beach ribbon per pair, with the wider border retained as Look ground and source metadata. This avoids duplicate coplanar ribbons without changing source geometry.

District JSON exports only bbox/label positions. R01 `polygon_m` currently contains explicitly labelled source bounding boxes for legacy ID lookup. SVG coloured ground patches do not establish complete district boundaries for all ten districts; no rectangular district ground painting is generated. Approved district envelopes require a re-export.

Canonical plan water level is 0. Source river has 201 width samples; tapered polygons preserve the profile. Canal water is 13.2 m with 1.4 m walls per side (16 m total). The canal mouth separately retains its source dimensions.

## District mapping

| v11 | R01 / crowd / police / ambience ID | Aliases | Buildings |
|---|---|---|---:|
| 01 | forest | forest | 3 |
| 02 | village | village, hamlet | 28 |
| 03 | transition | transition, construction | 24 |
| 04 | residential | residential, rough, alley | 56 |
| 05 | old_town | old_town, downtown | 55 |
| 06 | industrial | industrial, port | 28 |
| 07 | elite | elite | 6 |
| 08 | fields | fields, valley | 2 |
| 09 | beach | beach | 5 |
| 10 | tramduro | tramduro | 9 |

The first nine IDs are supported by the existing ambience mapping; `tramduro` needs a new ambience recipe. Numeric IDs stay optional; existing string keys are preserved.

## Base mapping and road reachability

| v11 | R01 | District | Exact anchor (x, y) m | From spawn road stop, m | Anchor → road stop, m |
|---|---|---|---|---:|---:|
| Base 1 | B01 | forest | [192.8, 176.2] | 447.743 | 9.213 |
| Base 2 | B02 | village | [167.0, 519.8] | 0.000 | 27.412 |
| Base 3 | B03 | residential | [589.8, 575.8] | 527.063 | 21.800 |
| Base 4 | B04 | old_town | [1070.4, 281.6] | 1130.523 | 11.600 |
| Base 5 | B05 | fields | [519.2, 252.0] | 583.474 | 21.124 |

Exactly five main bases. B06 is intentionally removed; Elite villas remain properties.

## Every legacy gameplay ID

The 43 IDs in v12 `points` are exhaustively mapped below. Source `pois` are label anchors, sometimes inside a footprint or over water. A mapped anchor does not certify a van can occupy the annotation position. Nearest exact road stops are separately exported; all local door/loading clearance and the unmatched functions require decisions.

| ID | Status | v11 reference / question | Exact anchor m | From spawn stop, m |
|---|---|---|---|---:|
| B01 | mapped | base:Base 1 | [192.8, 176.2] | 447.743 |
| P02 | mapped | base:Base 2 | [167.0, 519.8] | 0.000 |
| P03 | unmatched | The former Hamlet pharmacy is explicitly a regular house. Was the pharmacy removed from gameplay? | — | — |
| WATER_TOWER | mapped | structure:02_07_water_tower | [338.4, 517.8] | 234.536 |
| B02 | mapped | base:Base 2 | [167.0, 519.8] | 0.000 |
| P04 | unmatched | No shadow buyer/receiving point is identified. This ID is a hard-coded trip-meter destination. | — | — |
| B03 | mapped | base:Base 3 | [589.8, 575.8] | 527.063 |
| P06 | unmatched | No bar is identified; Rough shawarma is a different function. Where is the bar? | — | — |
| P07 | mapped | poi:04:05 | [687.2, 621.6] | 624.463 |
| P05 | mapped | poi:03:01 | [538.0, 370.0] | 534.523 |
| P08 | unmatched | No hospital is identified. This ID is a hard-coded trip-meter destination. | — | — |
| P10 | mapped | poi:05:10 | [680.0, 278.8] | 752.123 |
| P11 | mapped | poi:05:08 | [884.8, 410.2] | 988.323 |
| P11-3 | unmatched | No hospital ATM is identified. | — | — |
| B04 | mapped | base:Base 4 | [1070.4, 281.6] | 1130.523 |
| P15 | unmatched | Four Elite villas exist, but which villa replaces the old VIP/mansion P15? | — | — |
| P15-2 | unmatched | Which Elite villa replaces the second mansion P15-2? | — | — |
| B05 | mapped | base:Base 5 | [519.2, 252.0] | 583.474 |
| P14 | unmatched | No railway depot is identified; taxi depot 05:12 is a different function. | — | — |
| P12 | unmatched | No tow/impound yard is identified. | — | — |
| CHIMNEY | unmatched | No old industrial chimney is exported; the old B01 sightline is unresolved. | — | — |
| P01 | unmatched | No advertising/job-board landmark is exported. Where is the gameplay noticeboard? | — | — |
| BAD_CENTER | unmatched | Several Rough courtyards exist; no canonical central meeting/reference point is specified. | — | — |
| CLOCK_SQUARE | mapped | poi:05:04 | [807.6, 394.6] | 820.723 |
| ELITE_GATE | mapped | poi:07:06 | [1170.4, 355.6] | 1152.092 |
| P09 | unmatched | No behind-supermarket meeting spot is identified; no supermarket is named. | — | — |
| P09-2 | unmatched | No courtyard meeting spot is identified. | — | — |
| P09-3 | unmatched | B05 is now the Valley lab; no meeting spot beside it is specified. | — | — |
| P11-2 | unmatched | No Rough shop ATM is identified. | — | — |
| P13 | unmatched | Lakes/ponds are exported, but no gameplay water-access/van-stop point is specified. | — | — |
| P13-2 | unmatched | No gameplay river-access/van-stop point is specified. | — | — |
| P13-3 | unmatched | Canal promenade exists, but no gameplay canal-access/van-stop point is specified. | — | — |
| P13-4 | unmatched | Rough trash objects 08/14 exist; which is the gameplay disposal point? | — | — |
| P13-5 | unmatched | No Downtown gameplay disposal point is identified. | — | — |
| P16 | unmatched | No NW exit post or closed escape route is exported. | — | — |
| P16-2 | unmatched | No NE exit post or closed escape route is exported. | — | — |
| BAD_BLOCK | unmatched | Which Rough courtyard replaces old courtyard 1? | — | — |
| BAD_BLOCK_2 | unmatched | Which Rough courtyard replaces old courtyard 2? | — | — |
| BAD_BLOCK_3 | unmatched | Which Rough courtyard replaces old courtyard 3? | — | — |
| B06 | removed | Removed by the brief: there are exactly five main bases. | — | — |
| P09-4 | unmatched | Construction replaces Crossing; no meeting spot is specified. | — | — |
| BEACH_ENTRY | unmatched | The old Elite vehicle beach entry is replaced by stairs 07:12. Confirm an approved van entrance to City Beach parking 09:01. | — | — |
| BEACH_VALLEY_ENTRY | mapped | poi:08:05 | [507.2, 133.6] | 673.587 |
| P10-2 (new) | mapped | poi:05:11, NE police station | [1058.8, 412.8] | 1126.923 |

Spawn and van start remain keyed by P02 → Base 2. P10 → Downtown 10 (SW); P10-2 → Downtown 11 (NE). Each of the 119 source numbered POIs has a stable `Dxx_POI_nn` ID and an exact source anchor, irrespective of legacy gameplay resolution.

## Numerical checks

| Check | Result |
|---|---|
| Lossless source copy | PASS: 216 buildings, 205 structures, 119 numbered POIs, 84 roads, 10 road areas, 8 bridges |
| Source building centroid error | PASS: max 0 m across 216 |
| Native Look footprint mesh | PASS: 216 CCW footprints; max symmetric difference 0 m²; centroid error 0 m |
| Van graph | PASS: 1649 nodes, 1688 edges, 1 component; 40 documented endpoint joins inside source road surfaces |
| Mapped road-stop reachability | PASS: 5/5 bases and 134/134 exported point stops; node gap < 0.000001 m |
| Legacy gameplay resolution | 14/43 mapped, 28 unmatched questions, 1 removed; +1 new NE station |
| Van access at the actual gameplay object | OPEN: annotation-to-stop offset and local door/loading geometry remain explicit; no invented access roads |
| Lanes | PASS: max 2 per direction; 14 m boulevard/green median is approved 2+2 by Fedya, zero violations |
| Source bridge ends | 5/8 connect both source road/path surfaces; all 4/4 vehicle bridges connect |
| Mainland → Tramduro coast | OPEN: source bridge axis starts 8.799156 m beyond source land; existing port-road surface supplies labelled legacy boundary/sea compatibility corridor |
| Fences | PASS: zero generated district border fences; 6 source property perimeters retained; zero road centreline blocks after recorded openings |
| Source terrain retained | 10 hill/mountain hints, 16 forest zones, 3 clearings, 8 sand polygons; coast/ridge/lake/bog/pools retained |
| Native flat totals | 86 road/path carriers (78 distinct source + 8 decks; 6 SVG stroke pairs consolidated), 216 buildings, 8 Look crossings, 34 sidewalk strips, 119 ground polygons; 4727 deterministic trees |
| Police 4-car lots | PASS: 2/2 source lots fit 4 stalls (2.6 × 5.2 m) and 6 m aisle; 5 m access has zero building overlap; dimensions are proposals |
| Crowd | PASS: 20 loops, 1 police patrol, 20 hidden spawns, 54 activity POIs, 9 witness spots, 94 connections, 1 exported component |
| Crowd geometry/occlusion | PASS: zero blocked paths, zero unapproved road crossings, zero town/police sand paths; 60 building-occluded observer rays; grid 522820 nodes at 0.625 m |
| Protected map/source files | PASS: 127 existing v12–v15/source file hashes unchanged; M1 writes no C# or WORK_SYNC files |
| Unity / NavMesh / gameplay drive-through | NOT RUN (outside M1) |

Road graph reachability covers the source transport network, not off-road approaches. Full per-point stop coordinates, offsets and path lengths are in `checks.van_reachability`. Door/loading feasibility must be checked by the lead before treating the conversion as gameplay-ready.

### Bridge endpoint gaps

| Bridge | End 1 road/path and gap m | End 2 road/path and gap m |
|---|---|---|
| bridge_main | hamlet_bypass: 0.000000 | main_bridge_construction: 0.000000 |
| bridge_valley | construction_valley: 0.000000 | 08_main: 0.000000 |
| bridge_north | hamlet_bypass: 0.000000 | hamlet_rough_e: 0.000000 |
| bridge_tramduro | 06_port_road: 0.000000 | 10_main: 0.000000 |
| footbridge_beach_1 | 09_path_1: 20.800000 | 05_S: 12.600000 |
| footbridge_beach_2 | 09_path_12: 22.400000 | 05_AX: 9.600000 |
| footbridge_beach_3 | 09_path_3: 20.800000 | 05_S: 12.600000 |
| footbridge_canal_mouth | promenade_bay: 0.000000 | promenade_bay: 0.000000 |

The three City Beach footbridges keep the exact source deck polygons. Six explicitly proposed pedestrian approaches in crowd data cross existing dry meadow to source paths/streets; no road, paving or deck endpoint is moved.

Crowd exports 24 beach-lie points at source lounger references and all nine supported v12 activities except the absent bar. Activity positions are connected dry-graph projections: max reference offset 32.711 m; shop queue at 04_low_02 is 24.535 m from its proposed door and football activity is 14.365 m from the pitch centre. These two placements require local alignment/approach review; no precise queue or animation placement is claimed.

### Fence perimeters

| ID | Source kind | Gates/cuts | Height m (status) |
|---|---|---:|---|
| 03_fence | fence_profiled_sheet_blue | 7 | 2: source approximate |
| 06_yard | concrete_port_yard_with_fence | 2 | 2.4: proposal; source gives no numeric height |
| 07_fence | high_fence_with_barbed_wire | 2 | 2.4: proposal; source gives no numeric height |
| 08_06_fence | low_perimeter_fence_open_gates | 4 | 1: proposal; source gives no numeric height |
| 10_base_fence | military_fence | 1 | 2.4: proposal; source gives no numeric height |
| 10_palace_lawn | palace_lawn_with_fence | 1 | 1: proposal; source gives no numeric height |

Construction source gates retain 19/18/18 m openings and four 12 m van cuts. Other road/fence openings are explicitly derived proposals (road width + 2 m); heights outside Construction are proposals because JSON has no numbers. The Elite stairs opening is a 1.8 m proposal. The extra palace-lawn property fence is retained from v11 and is flagged for confirmation.

## Fedya addendum: optional Elite marina

The three east-facing v11 yacht piers remain byte-equal in geometry. Six white yacht hull polygons are read from the approved SVG and kept as exclusion geometry; their JSON absence is documented. Four motorboats retain v14 hull dimensions/shape under rigid rotation/translation. The v14 breakwater shape and dependent light are an independent optional layer, detached from the coast and rotated to the east of the v11 piers.

Switches: `marina_enrichment_settings.enabled=false` disables the whole layer; each item also has `enrichment:true`, `optional:true`, `enabled`. Motorboats default enabled. Breakwater and light default disabled, with `requires_confirmation:"Vadim"`; enable both only after that decision. Existing C# does not consume this optional layer yet. Purple render geometry shows the proposal for review even when disabled.

| Item | Centre / axis / position (metres) | Heading / size | Default |
|---|---|---|---|
| MARINA16_BOAT_M1 | [1372, 346] | 0°; 8 × 2.8 m | ON |
| MARINA16_BOAT_M3 | [1372, 320] | 0°; 8 × 2.8 m | ON |
| MARINA16_BOAT_M2 | [1372, 296] | 0°; 8 × 2.8 m | ON |
| MARINA16_BOAT_M4 | [1372, 270] | 0°; 8 × 2.8 m | ON |
| MARINA16_BREAKWATER | [[1426.999856, 353.000253], [1428.128649, 347.968897], [1429.780892, 340.750131], [1431.417502, 332.656284], [1432.499504, 324.999947], [1432.878452, 317.953061], [1432.843539, 310.875064], [1432.511647, 303.859396], [1432.000067, 297.000089], [1431.550964, 290.12505], [1431.031408, 283.249928], [1429.996253, 276.749858], [1428.000171, 270.999906], [1424.73454, 266.039073], [1420.500053, 261.687754], [1415.765639, 257.992621], [1410.999971, 255.000459], [1405.742099, 252.859756], [1399.937421, 251.500169], [1394.663975, 250.640609], [1390.999873, 249.999801]] | —°; — × 6.0 m | OFF / Vadim |
| MARINA16_LIGHT | [1390.999873, 249.999801] | —°; — × — m | OFF / Vadim |

Complete polygon vertices and transformed breakwater axis are in `marina_enrichment`. Coordinates above are relative to the original source pier frame; no v14 pier/pontoon/road geography is inherited.

| Item | Coast clearance m | Pier clearance m | Yacht clearance m | Stairs (3 m buffered) clearance m | Overlap m² |
|---|---:|---:|---:|---:|---:|
| MARINA16_BOAT_M1 | 13.312 | 11.000 | 4.833 | 44.802 | 0 |
| MARINA16_BOAT_M3 | 6.203 | 9.000 | 2.400 | 28.764 | 0 |
| MARINA16_BOAT_M2 | 9.129 | 9.000 | 2.400 | 26.838 | 0 |
| MARINA16_BOAT_M4 | 19.161 | 11.000 | 4.833 | 41.407 | 0 |
| MARINA16_BREAKWATER | 47.874 | 31.981 | 32.609 | 70.211 | 0 |

All 10 enrichment polygon pairs have zero overlap; land, piers, yachts and sand overlaps are zero for each item. The navigation light intentionally sits on its parent breakwater. No base, road graph, source structure or crowd obstacle is added by this optional layer.

## Overlay and v12 proof

Render and overlay are 2600 × 1341 pixels. X scale 1.763907734057 px/m; Y scale 1.764473684211 px/m (preview rounding). Origin pixel (0, 1341); zero translation, zero rotation, no fitted registration or crop. Pixel quantization is at most half a pixel per axis.

| v12 regeneration | Byte equality to committed output | SHA-256 |
|---|---|---|
| greybox: flatten_plan.py v12 --veg (write redirected to TEMP) | PASS (108621 bytes) | `999c4db05de906db67fb22266e247e1d2899c9c88567be76b8ee3535266d5ecc` |
| look: flatten_look.py v12 --out TEMP/look_v12_flat.json | PASS (760544 bytes) | `53280665573a1a8337c6149728dbec072feca775ffbd80e27396b022db28d177` |

### Verified deterministic v16 regeneration

Two separately generated data/render sets are byte-identical for all six files below. Each set used the existing flattener entrypoints and passed geometry/crowd checks. The report records current preservation observations separately.

| File | SHA-256 (both generations) |
|---|---|
| MAP_PLAN_R01_v16.json | `63492828b4336f27e92648f93a6b08756573d600ecfe1f2dea733e7b7426ee07` |
| MAP_PLAN_R01_v16.png | `f32c9e33dc13ce028944f2b60d18cee9a87fc3ec134ba6deca6c289bd9eabf3b` |
| MAP_PLAN_R01_v16_OVERLAY.png | `e4bad4baf828aa1741a2783c4955693cf0e09f1c042a47bc80bb469c8c22bce9` |
| Greybox/greybox_v16_flat.json | `de047106dacdb5a751aa071cb1b2a0e0459ad9c8a27f621a8c157477119b64da` |
| Look/look_v16_flat.json | `9406a9ff0af3c0d5e71996c3b77e93f2ec639436745ea52c2f2e17794f684579` |
| Crowd/crowd_v16.json | `47d3fc93c7965d78157c38d2d588d34e120324c1bfea55f6f021eb88de9812e7` |

Both regenerations write to system TEMP. Greybox uses `--veg` to reproduce the committed vegetation-bearing file; Look uses its unchanged default dressing/extras/kits/vegetation options. v12–v15 files remain untouched.

## Current consumer limits / lead handoff

- Existing latest-plan menus detect the v16 filenames. Native Greybox is an OBB mass approximation; exact footprints are preserved as optional data and natively triangulated in Look.
- Legacy Look height code uses ground ~0, sea -0.6 and inland water -0.3; canonical water=0, coast heights, ridge profile and rotated hill hints are retained for the lead to support. Existing C# ignores hill rotation and ridge extensions. Do not claim 3D terrain fidelity from this data check.
- Exact variable-width river/canal polygons reach the native polygon-water mesh, which currently uses the lake visual/material path. Typed water appearance and canal walls need consumer support.
- Existing bridge builder uses its own pier/deck height recipe; exact axes, widths and suggested long-bridge piers are in extensions. New structure kinds (fire escapes, rooftop towers, billboards, yacht piers, stairs, fixtures) and the optional marina need consumer support.
- Fences use the legacy generic fence drawing; exact perimeter/openings reach its collider geometry. Blue sheets, barbed wire and low-fence styles require lead art support.
- Current police config selects P10 only. NE P10-2 is present but multi-station police behavior needs a separate lead change. The four-car parking proposals are native LookParking records, so the existing baker can read the selected station lot.
- Current gameplay helpers hard-code missing P04/P08 and fall back to the map centre; legacy B05 labels may still say Industrial although its data is now the Valley lab. Resolve these before a playable build.
- The downtown fountain is only a numbered POI in JSON, so no invented fountain polygon is supplied. The source palace fountain polygon is passed as `functional_sites[type=fountain]` for the ambience reader.
- Crowd grid/routes follow actual dry geometry, including proposed unpaved bridge approaches/property-yard walks. Bar activity is omitted because no source bar exists. Tramduro 2/2 crowd density is an explicit proposal. Camera occlusion, NavMesh, actual props and height projection remain runtime gates.

## Open questions for Vadim / Fedya

1. Supply approved district outlines in JSON. Bounding boxes are a temporary ID lookup and may overlap; police district classification and ambience envelopes need true outlines.
2. Resolve every unmatched gameplay ID in the exhaustive table. In particular P04/P08 are required by current trip markers; confirm removal/replacement of the pharmacy, bar, hospital, railway depot, tow yard, meeting/water/disposal spots and exit posts.
3. Confirm an approved van entrance to City Beach. Elite access 07:12 is pedestrian stairs; the source does not define a City Beach vehicle road. No new beach access is invented.
4. Re-export/confirm mainland land or bridge approach at Tramduro: source coast/bridge gap is 8.799156 m. Compatibility data keeps source positions but must not be mistaken for approved coast infill.
5. Confirm six footbridge pedestrian approaches, source bridge-to-POI annotation discrepancies and precise local loading/door access at bases/gameplay objects.
6. Vadim: confirm optional breakwater/light placement (currently OFF), detached offshore. Fedya already approved the motorboats and optional enrichment. Confirm whether the detached offshore breakwater is preferred to a future coast tie-in.
7. Confirm numeric boulevard median width, property gate widths/heights outside Construction, palace-lawn fence, and Tramduro crowd/ambience recipe.
8. Re-export the Downtown fountain footprint and clarify why the "one large bog" is two exported water polygons; both are preserved.

## Reproduction

Use system Python 3.12 with Shapely 2.2+, NumPy and Pillow. The script refuses to replace any existing v16 deliverable.

```text
python -B ArtSource/References/Map/map_plan_v16.py --out-dir <empty temporary folder>
python -B ArtSource/References/Map/Greybox/flatten_plan.py v16 --plan <temporary plan.json> --out <new temporary greybox.json>
python -B ArtSource/References/Map/Look/flatten_look.py v16 --plan <temporary plan.json> --out <new temporary look.json>
```

The full generator invokes both existing flattener entrypoints, adapts the immutable v12 crowd implementation, validates outputs and proves legacy v12 equality. Determinism can be checked by generating twice into different empty folders and comparing the six data/render outputs. The report additionally records preservation observations. Existing map/source hashes are checked before/after each run; C# and WORK_SYNC are read-only in M1 and may be changed by work outside this task.

## Initial-scan changes outside M1 writes

7 C#/handoff files differ from the initial task preservation manifest. M1 wrote only the new v16 artifacts and the two named shared Python flatteners; it did not write any C# or WORK_SYNC file. The protected-map/source PASS above covers immutable inputs/deliverables. All initial v12–v15 map/source hashes remain unchanged.

| File | Initial SHA-256 | Current SHA-256 |
|---|---|---|
| Assets/OnlyVolunteers/Map/Scripts/GreyboxKccPawn.cs | `781c84c02a71568671841d3b9afc3d4d0677282d5ccbc571c6657f05f48f73d3` | `4e55d9f22e0398f483a1f627868b9cfc715c6c19766ebe164d88e85ee9d4f05a` |
| Assets/OnlyVolunteers/Map/Scripts/GreyboxNpc.cs | `40b0388de7f2e0948c7e4298641a3e9c2f36ab91745483e20b5ee232e585b38e` | `e7ebcdb6b2d0d7506c74d1e5fabea28c2a8afb293c12b87558c6978655f1ea28` |
| Assets/OnlyVolunteers/Map/Scripts/GreyboxNpcBody.cs | `53c3a45f6c51f5030c7a0f33dfcb46c6b11ddbeaaf23200c2fada9ce99bab4a4` | `1bbfce6dad128117f391ca08cd4737717206107d354c15f62c88b72a7a259c00` |
| Assets/OnlyVolunteers/Police/Scripts/PoliceCarMotor.cs | `412081eef056f1046c8d0edbcc5f36578b3e574b264dd2d657bed5e9c8c47ae3` | `4e65ff52ff78ef827c26b800e0fe96c0ecd646c67e77c734e38c36ac7073aa0a` |
| Assets/OnlyVolunteers/Audio/Scripts/AmbiencePlayer.cs | `7e91b5ce143beb5b582766864597cbea200fb19a86f7ec2c3c00aa36de44935d` | `d357ac930258559149017b32c3e0bbe41089fff27608c501ce0a7bd5a2e839e3` |
| Assets/OnlyVolunteers/Audio/Scripts/SfxSurfaces.cs | `dd04317710bdfa928337ada91b53640d2588855babfde4d637f7e11ea27b884b` | `d751b228ba5e4863685f80bf0c37867e9f73eb2a51416162d62007cdbe1ea321` |
| WORK_SYNC.md | `4a5a633df8f438852c7b5917c5ce07012b4102077d50caa9dff7d01a86a8cb90` | `7582b1b2be6f8901ace6e34b0b50c19c40a315f69451e889e42d7d060ce87510` |
