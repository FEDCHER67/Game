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
| 4 | `s04_west.py`, `s04_north.py`, `s04_south.py` | `districts/<name>_v76.json` (schema `Tools/MapV76/DISTRICT_SCHEMA.md`), overlays `out/check_<district>.png` |
| 5 | `s05_vegetation.py` | `vegetation_v76.json` (11.5k trees: pine/spruce/birch/oak/leafy, dense = no-drive), `masks/veg_{forest,nodrive,swamp,grass}_v76.png`; `out/check_vegetation.png` |
| 6 | `s06_materials.py` | `materials_v76.json` — 21 reused existing materials/terrain layers (by texture GUID), 25 to create (texture has no material yet) |

Data dir: `Assets/OnlyVolunteers/Map/W76Build/Data/v01/`. Coordinates: world v76 m, x east, y north (Unity X, Z).
`build_world_v76.py` constants are pre-shift → converted with `post_shift_v76.shift_m` (copied verbatim in `common.py`).
v52→v76 checklist source: `Tools/MapV76/data_src/v52_to_v76_changes.json` (48 items, 16 superseded).

## Status
- [x] 1 classes  - [x] 2 roads/water/border/features
- [x] 3 terrain heightmap (hill B 50.7, Elite 44.0, NW ridge 94.5 m; serpentine VIEW B max grade 12 % — open question)  - [x] 4 district layouts (all 10)  - [x] 5 vegetation  - [x] 6 material map
- [x] 7 splat (`s07_splat.py`) + C# `Assets/OnlyVolunteers/Map/W76Build/Editor/W76Builder.cs` (menu OnlyVolunteers/Map/W76 Build/Build Map_W76_Build_v01; Roslyn syntax-checked, NOT compiled in Unity) + Runtime W76Atmosphere / W76MapMarkers
- [~] 8 bpy renders (`s08_render_bpy.py`; full-map top done `out/renders/map_top_vs_2d_v76.png`; district renders may be partial)
- [ ] 9 checklist report  - [x] 10 draft PR https://github.com/FEDCHER67/Game/pull/30

## Next exact step (local agent)
1. `cd Tools/MapV76 && python3 s08_render_bpy.py` (pip install bpy) — finish district top + 6 oblique renders in `out/renders/`.
2. Write `s09_checklist.py`: tick each non-superseded item of `data_src/v52_to_v76_changes.json` against the data (build_key -> file/field), output `out/v52_to_v76_checklist.json`.
3. Open Unity, run the menu, read `Generated/v01/W76_build_log.txt`; fix compile errors if any (APIs checked by grep only).
4. Verify in Unity: roof ray check, tunnel glare, Rough fog / Construction bright, water v09 flow on rivers, arches passable, invisible wall.
Open questions (handoff v02 §16): Downtown street width; water v09/v10; Elite trap timing; lifeguard towers 6 vs ≤2; Port shift 250 vs 190; AZS outside Construction clip; VIEW B serpentine grade 12 % (>8 %).
Material reuse: see `materials_v76.json` (21 reused, 25 created + W76_water_flow/swamp/waterfall/steppe_far).

## District sources (v11 m → v76 = v11 + warp_m (build_world_v76.py l.206) + shift_m)
Net offsets: west (forest/hamlet/valley) +70/0; Downtown/beach/Elite +160/−28; Rough v11 +110/+97; Tramduro +270/+45; Port: warp ≈+250/+45 then scale about PORT_C (1.25, 0.8).
Hamlet `Working/Reviews/Hamlet_2026-10-14/HAMLET_LAYOUT_v04.json`; Construction `Desktop_Map_sources_2026-10-18/Интернациональная стройка/build_stroyka_v10.py` (x = 604 + 1.15(lx−410)/5, y = 418 − 0.95(ly−393)/5);
Rough `World_v11/Districts/D04_Rough_District_layout_v45.json` (local m, origin SW outer-road corner); Downtown `docs/specs/DOWNTOWN_LEGEND_v26.md` + `Город/build_gorod_v27.py`;
Port `D06_Industrial_Port_layout_v03.json`; Elite `D07_Elite_Hill_layout_v09.json` + `World_v74/make_elite_v10.py`; Tramduro `Working/Reviews/Tramduro_2026-10-14/TRAMDURO_LAYOUT_v06.json`;
fallback for all: `World_v11/WORLD_MAP_v11.json` buildings[] (216, floors/height).
Facade kit merged from `claude/facade-kit-v01`: `ArtSource/Props/FACADE_KIT_v01` (manifest, sockets, ROOF_COLLISION_NOTE.md).
