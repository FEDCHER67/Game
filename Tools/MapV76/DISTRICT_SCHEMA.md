# districts/<name>_v76.json — schema (read by W76Builder.cs)

All coordinates: world v76 metres, x east, y north (Unity X = x, Z = y). Heights in m above the local terrain unless `abs`.
```json
{
 "district": "rough", "sources": ["path …"], "transform": "how local -> v76 was computed",
 "pad_height_m": 5.0,
 "buildings": [{
   "id": "04-H1a", "kind": "khrushchevka|house|church|tower|villa|warehouse|container|kiosk|garage|…",
   "footprint": [[x, y], …],               // CCW polygon, wall line (no overhang); rectangles as 4 points
   "floors": 5, "floor_h_m": 2.8, "height_m": 14.0,
   "roof": {"type": "flat|gable|hip|shed|pyramid|none", "material": "<material key>", "ridge_axis_deg": 0, "ridge_h_m": 2.5, "overhang_m": 0.4, "parapet_h_m": 0.6},
   "walls": "<material key>", "tint": "#RRGGBB or null",
   "entrances": [{"pos": [x, y], "facing_deg": 0, "kind": "door|podyezd|arch|garage_gate|rollshutter|gate", "w_m": 1.2}],
   "facade_kit": "rough|downtown|hamlet|none",
   "sockets": {"balconies": "mixed|open|glazed|none", "windows": true, "fire_escape": false, "ac_units": 0, "water_tank": false, "awning": false, "ridge_cap": "slate|metal|tile|null"},
   "collider": "full_roof",                  // always: body box + roof volume per ROOF_COLLISION_NOTE.md
   "notes": "…"
 }],
 "props": [{"id": "…", "kind": "bench|lamp|tree|car|container|…", "pos": [x, y], "rot_deg": 0, "size": [w, d, h], "grip_anchor": false}],
 "zones": [{"id": "…", "kind": "plaza|yard|playground|field|pool|track|fence|…", "poly": [[x, y], …], "surface": "<material key>"}]
}
```
`facing_deg` / `rot_deg`: 0 = +x (east), CCW positive (as v11 layouts).

Material keys (handoff §3.1 / v02 §7.1): `stucco_SK3b` (tinted), `stucco_SK3b_v07`, `brick_SK3a`, `concrete_panel_SK3c`, `cinder_SK3d`,
`boards_SK5a`, `boards_pier_SK5a_v02`, `logs_SK5b`, `KH1b`, `facade_downtown_stucco`, `facade_downtown_brick`, `facade_storefront`,
`facade_hamlet`, `facade_elite_villa`, `facade_warehouse`, `tower_glass`, `roof_tile_SK4a`, `roof_slate_SK4b`, `roof_wavy_slate`,
`roof_flat_SK4d`, `roof_profsheet_SK4c`, `metal_rusty`, `metal_painted_SK6a`, `asphalt_A5d12`, `asphalt_old_SK2a`, `sidewalk_S1`,
`plaza_M3`, `cobble_SK2c`, `concrete_SK3c`, `gravel_SK1d`, `dirt_SK1b`, `rubber`, `pool_tile`, `fence_net`, `sand_white`, `lawn`.
