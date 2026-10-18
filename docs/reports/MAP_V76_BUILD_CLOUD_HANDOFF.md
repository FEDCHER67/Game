# Map v76 build — cloud handoff (live, updated after every push)

Branch `claude/map-v76-build` (from main b694fa64). Brief: CLOUD_MAP_V76_BUILD + addenda (exact as Vadim designed; reuse existing materials; push after every step).
Sources: `docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v01.md` (+ v02, newer, same decisions with numbers), `ArtSource/References/Map/World_v76/*`.

## Pipeline (`Tools/MapV76/`, Python 3 + numpy/scipy/scikit-image/Pillow; renders: `pip install bpy`)
Run in order from `Tools/MapV76/`:
| step | script | output |
|---|---|---|
| 1 | `s01_classify.py` | surface classes of the v76 render, 1 m grid (`out/classes_v76.png`, `Data/v01/classes.json`) |
| 2 | `s02_network.py` | `roads_v76.json` (script splines post-shifted + vectorised asphalt/dirt), `water_v76.json`, `border_v76.json`, `features_v76.json` |
| 3 | `s03_terrain.py` (+ `s03b_shade.py` preview) | `Heightmap_v76_2049_r16.bytes` (RAW16 LE, 2049², row0 = south; terrain 1744×135×950 m at Y −15), `Holes_v76_2048_bits.bytes` (tunnel portals), `terrain_v76.json` (pads, tunnel, road grades, lakes, peaks); `out/relief_shaded_v76.png`, `out/relief_vs_map_v76.png` |

Data dir: `Assets/OnlyVolunteers/Map/W76Build/Data/v01/`. Coordinates: world v76 m, x east, y north (Unity X, Z).
`build_world_v76.py` constants are pre-shift → converted with `post_shift_v76.shift_m` (copied verbatim in `common.py`).
v52→v76 checklist source: `Tools/MapV76/data_src/v52_to_v76_changes.json` (48 items, 16 superseded).

## Status
- [x] 1 classes  - [x] 2 roads/water/border/features
- [x] 3 terrain heightmap (hill B 50.7, Elite 44.0, NW ridge 94.5 m; serpentine VIEW B max grade 12 % — open question)  - [ ] 4 district layouts  - [ ] 5 vegetation masks  - [ ] 6 material map (reuse existing)
- [ ] 7 C# W76Builder  - [ ] 8 bpy renders  - [ ] 9 checklist report  - [ ] 10 draft PR

## Next exact step
Write `Tools/MapV76/s04_districts.py`: building layouts per district → `districts_v76.json` (sources/transforms listed in §District sources).

## District sources (v11 m → v76 = v11 + warp_m (build_world_v76.py l.206) + shift_m)
Net offsets: west (forest/hamlet/valley) +70/0; Downtown/beach/Elite +160/−28; Rough v11 +110/+97; Tramduro +270/+45; Port: warp ≈+250/+45 then scale about PORT_C (1.25, 0.8).
Hamlet `Working/Reviews/Hamlet_2026-10-14/HAMLET_LAYOUT_v04.json`; Construction `Desktop_Map_sources_2026-10-18/Интернациональная стройка/build_stroyka_v10.py` (x = 604 + 1.15(lx−410)/5, y = 418 − 0.95(ly−393)/5);
Rough `World_v11/Districts/D04_Rough_District_layout_v45.json` (local m, origin SW outer-road corner); Downtown `docs/specs/DOWNTOWN_LEGEND_v26.md` + `Город/build_gorod_v27.py`;
Port `D06_Industrial_Port_layout_v03.json`; Elite `D07_Elite_Hill_layout_v09.json` + `World_v74/make_elite_v10.py`; Tramduro `Working/Reviews/Tramduro_2026-10-14/TRAMDURO_LAYOUT_v06.json`;
fallback for all: `World_v11/WORLD_MAP_v11.json` buildings[] (216, floors/height).
Facade kit merged from `claude/facade-kit-v01`: `ArtSource/Props/FACADE_KIT_v01` (manifest, sockets, ROOF_COLLISION_NOTE.md).
