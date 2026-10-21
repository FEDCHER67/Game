# districts/<name>_v85.json — schema (read by W85Builder.cs, Tools/MapV85 s05/s06/s09)

Data: `Assets/OnlyVolunteers/Map/W85Build/Data/v01/districts/<name>_v85.json` (write with `common.save_json('districts/<name>_v85.json', obj)`).
All coordinates: world v85 metres, x east 0..1744, y north 0..950 (Unity X = x, Z = y). Heights in m above the local terrain unless the
district sets `"abs_heights": true` (Elite). Footprints / polygons counter-clockwise (`common.ccw`). Angles: 0 = +x (east), CCW positive.

Authority (handoff v10 §0, §1): buildings, bases, gates, KPP, bridges, piers, plazas, football box, towers, parking -> 1:1 from the
district plan / layout JSON (not from colour blobs of the world picture). Trees, small details (lamps, benches, bins, hydrants, cars,
signs), road joins and surface transitions -> NOT copied point by point: the district file gives zones and anchors, the central
steps place them by rules (s05 vegetation, s06 details). Drawing artefacts of the plan / world picture are fixed and logged.

```json
{
 "district": "rough", "sources": ["path …"], "transform": "how plan -> world v85 was computed + fit residual (m)",
 "pad_height_m": 5.0, "abs_heights": false, "lighting": "overcast_fog",
 "buildings": [{
   "id": "04-H1a", "kind": "khrushchevka|house|church|tower|villa|warehouse|garage|kiosk|shop|…",
   "material_slot": "rough_khrushchevka",        // building-type slot: ONE place to swap the texture later (see below)
   "footprint": [[x, y], …], "floors": 5, "floor_h_m": 2.8, "height_m": 14.5,
   "roof": {"type": "flat|gable|hip|shed|pyramid|none", "material": "<material key>", "ridge_axis_deg": 0, "ridge_h_m": 2.5,
            "overhang_m": 0.4, "parapet_h_m": 0.6},
   "walls": "<material key>", "tint": "#RRGGBB or null",
   "entrances": [{"pos": [x, y], "facing_deg": 0, "kind": "door|podyezd|arch|garage_gate|rollshutter|gate", "w_m": 1.2, "benches": 0}],
   "arches": [{"id": "A4", "rect": [[x, y] x4], "through": "W-E|N-S", "clear_w_m": 4.0, "clear_h_m": 4.0}],
   "facade_kit": "rough|downtown|hamlet|none",
   "sockets": {"balconies": "mixed|open|glazed|none", "windows": true, "fire_escape": false, "ac_units": 0, "water_tank": false,
               "awning": false, "storefront": false, "ridge_cap": "slate|metal|tile|null"},
   "collider": "full_roof", "disabled": false, "notes": "…"
 }],
 "props": [{"id": "…", "kind": "…", "pos": [x, y], "rot_deg": 0, "size": [w, d, h], "grip_anchor": false}],
 "zones": [{"id": "…", "kind": "plaza|yard|playground|field|pool|parking|fence|street|road|track|veg_zone|no_tree|…",
            "poly": [[x, y], …] or "line"/"poly_line": [[x, y], …], "surface": "<material key>", …}],
 "fixed_by_logic": [{"id": "rough-01", "where": [x, y], "ru": "что сделано не как на картинке", "why_ru": "почему"}],
 "questions_for_vadim": [{"id": "rough-q1", "ru": "вопрос", "options_ru": ["1 …", "2 …"], "default": 1, "applied": "what the data does now"}],
 "counts": {…}
}
```

Props: only KEY objects of the plan (bases, football-box goals, playground kit, pull-up bars, cranes, containers, boats, lifeguard
towers, monuments, designed palm rows ~11 m apart, an orchard grid). NO drawn trees or decorative dots of the world picture.

Vegetation zones for s05 (instead of tree points): `{"kind": "veg_zone", "poly": […], "density": "dense|grove|sparse|row|none",
"species": "pine|birch|oak|leafy|palm|bare|bush"}`; `{"kind": "no_tree", "poly": […], "why": "loading pad|yard with function|plaza|…"}`.
s05 never puts a tree on roads, sidewalks, van drives, loading pads, functional yards, water, roofs; >= 2 m from a road edge, >= 3 m from a
facade (except front gardens), and in Downtown only inside squares 20 and 23.

Anchors for s06 small details (lamps every 25–35 m at the sidewalk / verge edge, at junctions, yard entries, playgrounds; benches at
podyezds / plazas / paths with a bin next to each; hydrants at block corners; parked cars parallel to the curb in groups, never on
junctions or entries; bins in alleys / service yards): give streets (centre line + widths), entrances, playground / trash / parking zones.
In the Rough lamps only at house corners, playgrounds and along the outer road (ROUGH_LEGEND); no wires in the Rough and the Hamlet.

Material slots (`material_slot`): `<district>_<type>` e.g. downtown_house_stucco, downtown_house_brick, downtown_storefront, downtown_tower_glass,
rough_khrushchevka, rough_garage, hamlet_house_log, hamlet_house_board, hamlet_church, construction_frame, construction_cabin, elite_villa,
elite_fbi, port_warehouse, port_tank, tramduro_palace, tramduro_hangar, valley_lab, valley_casino, beach_bar, forest_wagon, generic_concrete.
Each slot maps to the currently approved material key in `materials_v85.json` "slots" (s06_materials); a texture test result later changes
only that table.

Material keys (handoff v02 §7.1, unchanged from v76): `stucco_SK3b` (tinted), `stucco_SK3b_v07`, `brick_SK3a`, `concrete_panel_SK3c`,
`cinder_SK3d`, `boards_SK5a`, `boards_pier_SK5a_v02`, `logs_SK5b`, `KH1b`, `facade_downtown_stucco`, `facade_downtown_brick`,
`facade_storefront`, `facade_hamlet`, `facade_elite_villa`, `facade_warehouse`, `tower_glass`, `roof_tile_SK4a`, `roof_slate_SK4b`,
`roof_wavy_slate`, `roof_flat_SK4d`, `roof_profsheet_SK4c`, `metal_rusty`, `metal_painted_SK6a`, `asphalt_A5d12`, `asphalt_old_SK2a`,
`sidewalk_S1`, `plaza_M3`, `cobble_SK2c`, `concrete_SK3c`, `gravel_SK1d`, `dirt_SK1b`, `rubber`, `pool_tile`, `fence_net`, `sand_white`,
`lawn`, `field_plowed`, `field_stubble`, `worn_grass_L02`, `sand_ruts`.

Check image: `Tools/MapV85/out_v01/check_<name>.png` = crop of `VOLUNTEERS_MAP_PREVIEW_v85.png` (1 px/m) around the district, x3,
footprints red, entrances blue, props magenta, zones cyan / lines green (same as Tools/MapV76/s04_north.py `overlay`).
