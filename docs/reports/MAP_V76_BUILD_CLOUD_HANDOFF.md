# Map v76 build — cloud handoff (live, updated after every push)

Branch `claude/map-v76-build` (from main b694fa64). Brief: CLOUD_MAP_V76_BUILD + addenda (exact as Vadim designed; reuse existing materials; push after every step).
Sources: `docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v01.md` (+ v02, newer, same decisions with numbers), `ArtSource/References/Map/World_v76/*`.

## Pipeline (`Tools/MapV76/`, Python 3 + numpy/scipy/scikit-image/Pillow; renders: `pip install bpy`)
Run in order from `Tools/MapV76/`:
| step | script | output |
|---|---|---|
| 1 | `s01_classify.py` | surface classes of the v76 render, 1 m grid (`out/classes_v76.png`, `Data/v01/classes.json`) |
| 2 | `s02_network.py` | `roads_v76.json` (script splines post-shifted + vectorised asphalt/dirt), `water_v76.json`, `border_v76.json`, `features_v76.json` |

Data dir: `Assets/OnlyVolunteers/Map/W76Build/Data/v01/`. Coordinates: world v76 m, x east, y north (Unity X, Z).
`build_world_v76.py` constants are pre-shift → converted with `post_shift_v76.shift_m` (copied verbatim in `common.py`).
v52→v76 checklist source: `Tools/MapV76/data_src/v52_to_v76_changes.json` (48 items, 16 superseded).

## Status
- [x] 1 classes  - [x] 2 roads/water/border/features
- [ ] 3 terrain heightmap  - [ ] 4 district layouts  - [ ] 5 vegetation masks  - [ ] 6 material map (reuse existing)
- [ ] 7 C# W76Builder  - [ ] 8 bpy renders  - [ ] 9 checklist report  - [ ] 10 draft PR

## Next exact step
Write `Tools/MapV76/s03_terrain.py` (heightmap 2049² RAW16 over 1744×950 m, relief per handoff §2.2–2.3 / v02 §4).
