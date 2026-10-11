# R01 v17 — Phase A (Downtown + Rough District): game scale, density, occlusion, muted atmosphere

Generator: `map_plan_v17.py` (reads v16, fixed seeds, exclusive-create). Outputs: `MAP_PLAN_R01_v17.json/.png`,
`Greybox/greybox_v17_flat.json`, `Look/look_v17_flat.json`, `Crowd/crowd_v17.json` (crowd validation passed).
Review set: `Working/Reviews/Map_v17_A/` (after_*, before/after van shots, contact sheet, sightlines, perf, smoke, metrics).

## Rules applied
- Storeys 2.8 m, shop ground floor 3.3 m (new optional `ground_h` in the look json), parapet ≤ 0.6 m, doors 1.1 × 2.3 m (v17 buildings only).
- Downtown: perimeter-block lots along every street-facing block edge, frontage 8–20 m (max facade 21 m), depth ≤ 15 m,
  0.25 m joints, one 3.5 m alley on edges > 70 m; 6 curated recipes (2–6 floors, brick loft); neighbours 1–2 floors apart
  (75 %); corners +1 floor. Landmarks: 05_B002 11 fl on 20 × 20 m, 05_B022 10 fl. Courtyards: annexes, garages, yard fences, trees, cars.
- Plaza: open paving limited to the 40 × 40 m core round Vadim's fountain POI 15; tree-lined square, 14 market stalls, kiosks/ATM, benches, lamps, clock column.
- Streets: kerb parking both sides (car centre 1 m from the kerb, gaps at junctions/driveways/bus stops), street trees 11 m, lamps 23 m, bins, hydrants, signs, 2 bus stops (one at POI 05:14).
- Rough District: panel blocks > 48 m split into 1.5 m-staggered sections (4–5 floors kept), 58 entrances every 12–16 m on the yard side with canopy/bench/bin, bushes along facades, tree rows, 23 fenced front gardens, kindergarten, 3 garage rows, dumpster pads, laundry poles, sheds, transformer kiosk, yard Ladas, fenced pitch, poplar/birch rows along the drive.
- Common land round both districts: tree tunnels on inter-district roads, 21 forest clumps with undergrowth, garage cooperative, 12 allotment plots, power line (7 lattice pylons), billboards, 10 low relief hills (3–9 m).

## Deviations from v16/v11 (for Vadim)
1. Downtown: 41 source buildings replaced by 181 lots + 13 annexes + courtyard garages/sheds; kept 14 (police ×2, taxi depot, van shop, base 4 house, 4 corner shops, 2 podiums, glass podium, 2 landmarks). 05_B004 (2nd 20-floor tower) removed; 05_B002 20 → 11 floors and 23 → 20 m footprint; 05_B022 15 → 10 floors.
2. Downtown fire escapes / rooftop tanks / billboards regenerated for the lots (53 removed, 33 + 26 + 8 added).
3. Downtown park lawns 05_park_03…12 trimmed to the courtyards behind the street walls (e.g. 05_park_04 2249 → 535 m²).
4. 11 "park / square" POIs on block edges kept as pocket squares (lots stop 7.5 m short); POI 03 ramps kept clear.
5. Rough: 6 panel blocks split into sections (ids `<id>`, `<id>_s2`); entrance proposals moved to the yard side.
6. Kept storey counts get game-scale heights (e.g. panel 16.0 → 14.0 m, Downtown 3-floor 9.6 → 8.9 m).
7. Unchanged: district envelopes, road centrelines/classes, water, bridges, coasts, exits, all 134 points (POIs, bases, police parking, trip-meter ids, spawn), van graph. No fence on any district border.

## Metrics (v16 → v17)
| | Downtown | Rough District |
|---|---|---|
| buildings (main) | 55 → 208 (195), floors median 5 → 4, max 20 → 11, max height 64 → 31 m | 56 → 84 (27), 5 floors, 16 → 14 m |
| built-up share of district box | 26.0 → 34.8 % | 28.8 → 30.0 % |
| largest empty circle (roads excluded) | r 39.4 → 12.7 m (plaza core excluded as deliberate) | r 20.7 → 9.5 m |
| sightlines eye 1.7 m: median / >60 / >120 / >250 m | 26.5 m / 26.8 / 11.9 / 6.1 % → 10.3 m / 6.6 / 2.4 / 1.7 % | 23.0 m / 19.2 / 8.0 / 1.2 % → 13.6 m / 6.6 / 1.7 / 0.5 % |
| perf (editor Play, same spot) | plaza 6.9 → 8.1 ms, street 4.6 → 5.6 ms | yard 4.9 → 5.3 ms |

Rebuild: run `map_plan_v17.py` (only if the data changes), then Unity menus in this order: OnlyVolunteers/Map/Police/Bake Police Data (latest plan);
OnlyVolunteers/Audio/Bake Ambience Zones (latest plan); OnlyVolunteers/Audio/Bake Water Zones (latest plan); OnlyVolunteers/Map/Build Rough Greybox (latest plan);
OnlyVolunteers/Map/Style v3/Build Map Look v17 + Gameplay (style v3, phase A).
