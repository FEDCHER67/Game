# Tramduro Island — v01

## Выжимка для Вадима

1. Компактный остров-крепость: показная роскошь перемешана с военными.
2. Белый дом на холме, тщательно проработан снаружи; игрок никогда не заходит внутрь.
3. Трамдуро до финала виден только в приложении Z; на карте не гуляет.
4. Похищение у резиденции; способ финального выхода остаётся открытым.
5. Один общий периметр, единственный подготовленный вход по существующему мосту.
6. Два танка под открытым навесом, один вертолёт на одной площадке.
7. 20–25 военных ходят группами по 2–3 и поодиночке среди парадной роскоши.
8. Золотая статуя около 6 м, монументальный водопад, гольф с несколькими лунками.
9. Один-два катера патрулируют рядом; большого корабля и причала нет.
10. На закрытом въезде атакуют сразу; бусик обычно уничтожают раньше заезда. Финальный вывоз открыт.

## Concept and authority

Owner answers override both source briefs. This is a compact island fortress with expensive ceremonial gardens threaded by armed personnel, not two isolated compounds. The closed presidential façade dominates a low hill; a golden statue, oversized waterfall and several golf holes coexist with a two-tank garage and a single helicopter. From mainland: white roofline, gold monument, falling water, 20–25 moving military/searchlights and offshore boats. No real campaign slogans or logos.

Coordinates: world metres, x east/y north. New land objects stay inside the brief's [1204,506,1410,670] planning bbox AND actual source land. The source coastline actually spans roughly [1196.4,484.8,1410,682.11]; preserve this inherited outline rather than clipping or enlarging it. Outer rocky land remains coast, not an extra district. Bridge and offshore boats are declared bbox exceptions. Dimensions below are build proposals; confirmed counts/constraints take precedence.

## Zoning

| Zone | Box x0,y0,x1,y1 | Content |
|---|---|---|
| Shared fortress | 1218,510,1398,665 | One coastal perimeter; common military routes through luxury grounds. |
| Hill residence | 1308,618,1356,640 | Existing-scale 48×22m closed residence; deep porticoes, wings, recessed windows, stairs, roof details. |
| Ceremonial garden | 1310,583,1385,650 | 6m statue; 22×28m engineered waterfall monument, 18×10m basin. |
| Compact golf | 1246,609,1302,655 | Three short holes/greens; golf-cart prop. No full-size course or minigame assumed. |
| Service area | 1234,516,1332,579 | 26×18m open canopy/two tanks, clear apron; one small proposed staff block. |
| Air pad | 1345,531,1369,555 | One 24m pad, one helicopter including rotor envelope. |
| Bridge arrival | 1204,581,1238,603 | Existing connection, physical barrier, booth offset from traffic. |

Zones overlap intentionally and do not generate fences. Keep residence recognizable at its current scale instead of enlarging it; spend detail on exterior depth. No accessible rooms, service entrances or interior capture route. Ornamental landscaping never becomes rows of identical parcel cages.

## Circulation and security

Bridge lands at (1204,586). A connected 6.4m spine feeds the canopy, residence loop and helipad; a 4.2m lower service loop lets walking military traverse the island. These are garrison roads; ordinary player van entry is effectively defeated by guards before reaching the base, not by an invisible vehicle restriction. Final extraction transport remains OPEN. Union junction surfaces—no road laid as a rectangular slab across another. Preserve ≥3.5m driving and ≥1.5m walking clearances. Open canopy faces a clear service apron; tanks fit inside separate bays. Pad approach stops outside helicopter rotor footprint. Level these working areas; blend the proposed residence rise into a broad ascent. Check actual van turns/traction in Unity; coordinates alone do not prove them.

The bridge has a visible physical checkpoint. Outside staffing target: 20–25 military; mixed 2–3-person patrols and lone personnel. Grounds stay mostly open with rare useful cover. Cliffs, lookout posts, walking patrols and 1–2 moving offshore patrol boats provide readable defence; no hidden barriers, invincible soldiers or story-unlock rule for entry. Do not add minefields, air-defence batteries or a giant fleet from the original brainstorm. Guards immediately attack at the closed entry; patrol boats intervene when nearby intruders are detected. Exact damage, detection, pursuit and respawn parameters remain OPEN; no invented timers.

Tramduro is absent from normal world NPC spawns and routines; pre-final presence is phone app **Z** only. He appears physically for the final kidnapping near his residence. EXACT outdoor emergence remains OPEN: do not canonise evacuation, speech, car departure or a helicopter unlock. Keep usable external forecourt/roads for later physical capture and van loading. Never substitute automatic capture or a house-entry cutscene.

## Memorable details

1. Gold cartoon-president statue/pedestal [H].
2. Monumental recirculating rock waterfall [H].
3. Ornate basin with soldiers walking beside it [H].
4. Several golf flags among military patrols.
5. Parked golf cart [H].
6. Rich white portico and closed ceremonial doors [H].
7. Gilded architectural railing [H].
8. Fictional oversized presidential flag.
9. Marble benches beside guard routes [H].
10. Expensive planters adjoining military access [H].
11. Two tanks visible under an open-sided canopy [H].
12. One helicopter beside manicured grounds [H].
13. Mounted searchlights and ceremonial loudspeaker.

[H] means a physical obstacle/cover opportunity, not guaranteed safety. No statue/tank/boat/helicopter control mechanics are implied.

## Changes from v11

Preserve island/bridge footprint and approximate palace location. Replace two oversized hangars with one open canopy (1265,557) containing two tanks. Replace three barracks/HQ/vehicle park with a compact service yard and proposed staff block (1262,528); no extra armoured fleet. Move booth to (1226,596) off traffic. Keep exactly one helipad, now (1357,543), and place one helicopter. Replace separate military and palace fences with a common perimeter. Replace eastern beach dressing with rocks; no new landing entrance. Add statue (1332,591), engineered waterfall (1374,636), three-hole golf west of residence and 1–2 offshore moving boats. Do not regenerate the master map or adjoining districts.

## Placement JSON

`TRAMDURO_LAYOUT_v01.json` duplicates the following block. Mounted/composite children intentionally overlap their hosts. Source coastline is referenced unchanged; terrain zones are clipped to land. Heights are relative proposed ground deltas. Guard and boat paths are route proposals, not implemented AI. Final scenario remains open.

```json
{"schema":"tramduro_island_spec_v01","date":"2026-10-14","units":"metres","axes":"x-east,y-north;rotation-CCW-from-east","planning_bbox_m":[1204,506,1410,670],"source":"C:\\Users\\chern_0eqkb03\\Desktop\\GAME\\ArtSource\\References\\Map\\World_v11\\WORLD_MAP_v11.json","source_coast_preserved":true,"status":"Owner-approved direction; exact placements/counts not individually approved are build proposals","open":["final_outdoor_appearance","detection_damage_pursuit_parameters","wanted_rules","vehicle_controls"],"objects":[{"id":"residence","kind":"closed_residence","centre_m":[1332,629],"size_m":[48,22],"rotation_deg":0,"notes":"Keep scale; rich porticoes, recessed windows, wings, parapets. No player interior.","solid":true,"height_m":9.6},
{"id":"portico","kind":"portico_steps","centre_m":[1332,615],"size_m":[10,4],"rotation_deg":0,"notes":"Exterior detail; doors remain closed. Never infer indoor gameplay.","solid":true,"parent":"residence"},
{"id":"statue_plaza","kind":"marble_plaza","centre_m":[1332,591],"size_m":[22,16],"rotation_deg":0,"notes":"Open luxury forecourt; exterior capture scenario remains undecided.","solid":false},
{"id":"statue","kind":"gold_statue","centre_m":[1332,591],"size_m":[3.4,3.4],"rotation_deg":0,"notes":"Heroic cartoon Tramduro: raised arm and exaggerated chest; statue plus pedestal totals 6m.","solid":true,"height_m":6,"parent":"statue_plaza"},
{"id":"waterfall","kind":"monumental_waterfall","centre_m":[1374,636],"size_m":[22,28],"rotation_deg":0,"notes":"Showy decorative rocks, broad waterfall, expensive lit basin; recirculating water, no new river.","solid":true,"height_m":10},
{"id":"waterfall_pool","kind":"water_basin","centre_m":[1374,628],"size_m":[18,10],"rotation_deg":0,"notes":"Child of waterfall; walking soldiers patrol beside water.","solid":false,"parent":"waterfall"},
{"id":"waterfall_face","kind":"cascade_face","centre_m":[1374,640],"size_m":[16,6],"rotation_deg":0,"notes":"Broad visible falling water; parent owns collision.","solid":false,"height_m":9,"parent":"waterfall"},
{"id":"garage","kind":"two_tank_open_canopy","centre_m":[1265,557],"size_m":[26,18],"rotation_deg":0,"notes":"Open-sided canopy: two visible tanks, roof on side pillars, generous physical access. Normal player van ingress defeated by guards.","solid":false,"height_m":6},
{"id":"canopy_post1","kind":"canopy_support","centre_m":[1253,549],"size_m":[0.45,0.45],"rotation_deg":0,"notes":"Open-side roof support.","solid":true,"height_m":5,"parent":"garage"},
{"id":"canopy_post2","kind":"canopy_support","centre_m":[1253,557],"size_m":[0.45,0.45],"rotation_deg":0,"notes":"Open-side roof support.","solid":true,"height_m":5,"parent":"garage"},
{"id":"canopy_post3","kind":"canopy_support","centre_m":[1253,565],"size_m":[0.45,0.45],"rotation_deg":0,"notes":"Open-side roof support.","solid":true,"height_m":5,"parent":"garage"},
{"id":"canopy_post4","kind":"canopy_support","centre_m":[1277,549],"size_m":[0.45,0.45],"rotation_deg":0,"notes":"Open-side roof support.","solid":true,"height_m":5,"parent":"garage"},
{"id":"canopy_post5","kind":"canopy_support","centre_m":[1277,557],"size_m":[0.45,0.45],"rotation_deg":0,"notes":"Open-side roof support.","solid":true,"height_m":5,"parent":"garage"},
{"id":"canopy_post6","kind":"canopy_support","centre_m":[1277,565],"size_m":[0.45,0.45],"rotation_deg":0,"notes":"Open-side roof support.","solid":true,"height_m":5,"parent":"garage"},
{"id":"tank1","kind":"tank","centre_m":[1260,556],"size_m":[3.4,8],"rotation_deg":0,"notes":"Parked under canopy, facing north. Driving mechanic not decided.","solid":true,"height_m":2.8,"parent":"garage"},
{"id":"tank2","kind":"tank","centre_m":[1270,556],"size_m":[3.4,8],"rotation_deg":0,"notes":"Parked under canopy, facing north. Driving mechanic not decided.","solid":true,"height_m":2.8,"parent":"garage"},
{"id":"garage_apron","kind":"service_apron","centre_m":[1265,573],"size_m":[28,12],"rotation_deg":0,"notes":"Keep service access clear; tanks connect north to spine. No separate fenced military rectangle.","solid":false},
{"id":"staff","kind":"staff_support_block","centre_m":[1262,528],"size_m":[16,8],"rotation_deg":0,"notes":"Proposed compact replacement for three barracks/HQ; functional service, not new district.","solid":true,"height_m":3.2,"status":"proposed"},
{"id":"helipad","kind":"helipad","centre_m":[1357,543],"size_m":[24,24],"rotation_deg":0,"notes":"Only landing pad; flat, open approach, vehicle access west. Arrival/evacuation mechanics open.","solid":false},
{"id":"helicopter","kind":"helicopter","centre_m":[1357,543],"size_m":[12,11],"rotation_deg":0,"notes":"One helicopter including rotor envelope; no piloting mechanic inferred.","solid":true,"height_m":4,"parent":"helipad"},
{"id":"checkpoint","kind":"guard_booth","centre_m":[1226,596],"size_m":[6.4,5.2],"rotation_deg":0,"notes":"Move existing booth north of traffic lane; checkpoint and visible patrol.","solid":true,"height_m":3.2},
{"id":"barrier","kind":"bridge_barrier","centre_m":[1226,586],"size_m":[0.25,6.4],"rotation_deg":0,"notes":"Single physical lane control; open/closed state uses existing rules.","solid":false,"gate_crossing":true,"parent":"checkpoint"},
{"id":"golf","kind":"three_short_hole_golf_area","polygon_m":[[1261,649],[1250,609],[1280,611],[1302,625],[1301,654],[1270,655]],"rotation_deg":0,"notes":"Visible compact several-hole luxury course; decorative only, no golf minigame."},
{"id":"green1","kind":"golf_green","centre_m":[1263,632],"size_m":[8,7],"rotation_deg":0,"notes":"Distinct short hole, flag and subtly raised turf.","solid":false,"parent":"golf"},
{"id":"green2","kind":"golf_green","centre_m":[1286,643],"size_m":[8,7],"rotation_deg":0,"notes":"Distinct short hole, flag and subtly raised turf.","solid":false,"parent":"golf"},
{"id":"green3","kind":"golf_green","centre_m":[1287,623],"size_m":[8,7],"rotation_deg":0,"notes":"Distinct short hole, flag and subtly raised turf.","solid":false,"parent":"golf"},
{"id":"golfcart","kind":"golf_cart","centre_m":[1252,603],"size_m":[2.4,1.3],"rotation_deg":0,"notes":"Luxury prop beside golf approach; gameplay controls not decided.","solid":true},
{"id":"spine","kind":"road","polyline_m":[[1204,586],[1238,586],[1264,586],[1288,586],[1308,586],[1320,579],[1320,560],[1328,548],[1347,548]],"width_m":6.4,"rotation_deg":0,"notes":"Union junction surfaces; preserve clearance."},
{"id":"residence_loop","kind":"road","polyline_m":[[1264,586],[1275,604],[1292,615],[1305,610],[1320,607],[1342,607],[1357,611],[1365,606],[1367,592],[1350,581],[1320,579]],"width_m":6.4,"rotation_deg":0,"notes":"Union junction surfaces; preserve clearance."},
{"id":"garage_access","kind":"road","polyline_m":[[1264,586],[1265,573]],"width_m":6.4,"rotation_deg":0,"notes":"Union junction surfaces; preserve clearance."},
{"id":"service_loop","kind":"road","polyline_m":[[1238,586],[1239,555],[1245,541],[1269,536],[1289,541],[1308,540],[1328,548]],"width_m":4.2,"rotation_deg":0,"notes":"Union junction surfaces; preserve clearance."},
{"id":"bridge","kind":"existing_bridge","polyline_m":[[1090.0,588.0],[1092.65,587.9],[1096.2,587.77],[1100.44,587.62],[1105.12,587.45],[1110.05,587.27],[1114.98,587.1],[1119.71,586.94],[1124.0,586.8],[1127.94,586.68],[1131.78,586.55],[1135.54,586.44],[1139.25,586.33],[1142.93,586.22],[1146.59,586.13],[1150.28,586.06],[1154.0,586.0],[1157.82,585.96],[1161.73,585.94],[1165.69,585.94],[1169.62,585.95],[1173.48,585.96],[1177.2,585.98],[1180.73,585.99],[1184.0,586.0],[1187.12,586.0],[1190.17,586.0],[1193.11,586.0],[1195.88,586.0],[1198.4,586.0],[1200.64,586.0],[1202.53,586.0],[1204.0,586.0]],"width_m":8.8,"road_width_m":6.4,"rotation_deg":0,"notes":"Preserve existing axis/abutments.","external_exception":true},
{"id":"perimeter","kind":"common_perimeter_fence","polyline_m":[[1218,581],[1225,561],[1237,536],[1251,518],[1275,517],[1300,510],[1324,516],[1345,513],[1371,514],[1377,535],[1388,555],[1398,580],[1388,604],[1392,625],[1387,651],[1364,666],[1334,665],[1311,660],[1286,663],[1263,653],[1246,642],[1234,623],[1224,603],[1218,591]],"height_m":3,"rotation_deg":0,"notes":"Open gap between last/first points at bridge approach; only common perimeter, no lawn/base cages."},
{"id":"watch1","kind":"watch_post","centre_m":[1240,621],"size_m":[3,3],"rotation_deg":0,"notes":"Small lookout on common perimeter; visible rather than invincible.","solid":true,"height_m":6},
{"id":"light1","kind":"searchlight","centre_m":[1240,621],"size_m":[0.3,0.3],"rotation_deg":0,"notes":"Mounted on lookout; no separate ground collider.","solid":false,"mount_height_m":6,"parent":"watch1"},
{"id":"watch2","kind":"watch_post","centre_m":[1284,654],"size_m":[3,3],"rotation_deg":0,"notes":"Small lookout on common perimeter; visible rather than invincible.","solid":true,"height_m":6},
{"id":"light2","kind":"searchlight","centre_m":[1284,654],"size_m":[0.3,0.3],"rotation_deg":0,"notes":"Mounted on lookout; no separate ground collider.","solid":false,"mount_height_m":6,"parent":"watch2"},
{"id":"watch3","kind":"watch_post","centre_m":[1376,552],"size_m":[3,3],"rotation_deg":0,"notes":"Small lookout on common perimeter; visible rather than invincible.","solid":true,"height_m":6},
{"id":"light3","kind":"searchlight","centre_m":[1376,552],"size_m":[0.3,0.3],"rotation_deg":0,"notes":"Mounted on lookout; no separate ground collider.","solid":false,"mount_height_m":6,"parent":"watch3"},
{"id":"planter1","kind":"ornamental_planter","centre_m":[1256,581],"size_m":[1.2,1.2],"rotation_deg":0,"notes":"Luxury obstacle with passage beside it.","solid":true},
{"id":"planter2","kind":"ornamental_planter","centre_m":[1306,593],"size_m":[1.2,1.2],"rotation_deg":0,"notes":"Luxury obstacle with passage beside it.","solid":true},
{"id":"planter3","kind":"ornamental_planter","centre_m":[1358,601],"size_m":[1.2,1.2],"rotation_deg":0,"notes":"Luxury obstacle with passage beside it.","solid":true},
{"id":"bench1","kind":"marble_bench","centre_m":[1323,599.5],"size_m":[2,0.6],"rotation_deg":0,"notes":"Rich garden furniture beside shared patrol route.","solid":true},
{"id":"bench2","kind":"marble_bench","centre_m":[1341,599.5],"size_m":[2,0.6],"rotation_deg":0,"notes":"Rich garden furniture beside shared patrol route.","solid":true},
{"id":"flag","kind":"fictional_presidential_flag","centre_m":[1304,644],"size_m":[0.5,0.5],"rotation_deg":0,"notes":"Readable oversized fictional emblem; no real campaign slogan.","solid":true,"height_m":11},
{"id":"gilded_rail","kind":"gilded_rail","centre_m":[1359,634],"size_m":[0.3,10],"rotation_deg":0,"notes":"Architectural luxury accent, not a ring around residence.","solid":true},
{"id":"speaker","kind":"ceremonial_speaker","centre_m":[1300,592],"size_m":[0.7,0.7],"rotation_deg":0,"notes":"Ceremonial loudspeaker next to passing soldiers; audio proposal, not quest trigger.","solid":true},
{"id":"tree01","kind":"ornamental_tree","centre_m":[1241,599],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree02","kind":"ornamental_tree","centre_m":[1263,650],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree03","kind":"ornamental_tree","centre_m":[1274,654],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree04","kind":"ornamental_tree","centre_m":[1301,659],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree05","kind":"ornamental_tree","centre_m":[1353,651],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree06","kind":"ornamental_tree","centre_m":[1361,618],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree07","kind":"ornamental_tree","centre_m":[1387,614],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree08","kind":"ornamental_tree","centre_m":[1386,646],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"palm"},
{"id":"tree09","kind":"ornamental_tree","centre_m":[1377,574],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree10","kind":"ornamental_tree","centre_m":[1369,523],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"palm"},
{"id":"tree11","kind":"ornamental_tree","centre_m":[1327,523],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree12","kind":"ornamental_tree","centre_m":[1282,522],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree13","kind":"ornamental_tree","centre_m":[1247,550],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"tree14","kind":"ornamental_tree","centre_m":[1282,573],"size_m":[0.6,0.6],"rotation_deg":0,"notes":"Formal planting; trunk collision.","solid":true,"crown_diameter_m":5,"tree_type":"ornamental"},
{"id":"flowers1","kind":"formal_flower_bed","centre_m":[1318,598],"size_m":[4,1.5],"rotation_deg":0,"notes":"Symmetrical luxury flower planting; passable, no hedge maze.","solid":false},
{"id":"flowers2","kind":"formal_flower_bed","centre_m":[1347,599],"size_m":[4,1.5],"rotation_deg":0,"notes":"Symmetrical luxury flower planting; passable, no hedge maze.","solid":false},
{"id":"flowers3","kind":"formal_flower_bed","centre_m":[1302,638],"size_m":[4,1.5],"rotation_deg":0,"notes":"Symmetrical luxury flower planting; passable, no hedge maze.","solid":false},
{"id":"flowers4","kind":"formal_flower_bed","centre_m":[1359,651],"size_m":[4,1.5],"rotation_deg":0,"notes":"Symmetrical luxury flower planting; passable, no hedge maze.","solid":false},
{"id":"guard_bridge","kind":"walking_military_patrol","polyline_m":[[1232,596],[1236,597],[1240,580],[1248,573],[1265,582],[1240,593],[1232,596]],"width_m":1.5,"rotation_deg":0,"notes":"Walking route, not standing NPC row. Mixed 2–3 and single walking military; 20–25 outside total. Behaviour implementation untested."},
{"id":"guard_luxury","kind":"walking_military_patrol","polyline_m":[[1290,601],[1305,601],[1321,602],[1353,602],[1360,621],[1360,640],[1332,653],[1300,650],[1290,601]],"width_m":1.5,"rotation_deg":0,"notes":"Walking route, not standing NPC row. Mixed 2–3 and single walking military; 20–25 outside total. Behaviour implementation untested."},
{"id":"guard_service","kind":"walking_military_patrol","polyline_m":[[1238,547],[1261,538],[1290,548],[1312,555],[1339,558],[1380,564],[1381.5,547],[1373,530],[1340,524],[1281,533],[1238,547]],"width_m":1.5,"rotation_deg":0,"notes":"Walking route, not standing NPC row. Mixed 2–3 and single walking military; 20–25 outside total. Behaviour implementation untested."},
{"id":"boat_route1","kind":"patrol_boat_route","polyline_m":[[1220,667],[1270,715],[1380,713],[1445,654],[1440,631],[1409,650],[1368,697],[1281,697],[1226,653],[1220,667]],"rotation_deg":0,"notes":"Offshore patrol, outside island bbox; no dock, bridge passage or navy ship.","external_exception":true},
{"id":"boat1","kind":"patrol_boat","centre_m":[1220,667],"size_m":[9,3],"rotation_deg":0,"notes":"One of two proposed moving patrol boats; use route of same index.","solid":false,"external_exception":true,"route_id":"boat_route1"},
{"id":"boat_route2","kind":"patrol_boat_route","polyline_m":[[1434,600],[1450,556],[1415,493],[1374,473],[1340,468],[1330,468],[1318,455],[1348,451],[1400,465],[1445,492],[1464,544],[1456,590],[1434,600]],"rotation_deg":0,"notes":"Offshore patrol, outside island bbox; no dock, bridge passage or navy ship.","external_exception":true},
{"id":"boat2","kind":"patrol_boat","centre_m":[1434,600],"size_m":[9,3],"rotation_deg":0,"notes":"One of two proposed moving patrol boats; use route of same index.","solid":false,"external_exception":true,"route_id":"boat_route2"}],"terrain":[{"id":"hill","kind":"residence_hill","polygon_m":[[1298,612],[1359,612],[1360,657],[1298,657]],"height_delta_m":7,"rotation_deg":0,"notes":"Proposed hill; broad road ascent, level closed residence pad. Blend, never move coast."},
{"id":"military_grade","kind":"service_grade","polygon_m":[[1234,516],[1380,516],[1380,580],[1234,580]],"height_delta_m":0.6,"rotation_deg":0,"notes":"Planning region clipped to existing land; garage/helipad flat."},
{"id":"cliffs","kind":"existing_coastal_cliffs","source_geometry":"WORLD_MAP_v11.island_tramduro.polygon_m","height_range_m":[4,9],"rotation_deg":0,"notes":"Existing shore unchanged; replace east beach dressing with rocky edge. No prepared landing."}],"security":{"military_outside":[20,25],"patrol_style":"mixed_2-3_and_single","entry_response":"immediate_attack_at_closed_entry","cover":"mostly_open_rare_cover","normal_van_ingress":"defeated_by_guard_fire_not_invisible_wall","final_extraction":"OPEN","boats":"patrol_and_intervene_on_detection"},"tramduro":{"ordinary_world_presence":false,"pre_final_visibility":"phone_app_Z_only","physical_appearance":"final_kidnapping_only","residence_interior_accessible":false,"final_exit_scenario":"OPEN"}}
```

Checks: see `TRAMDURO_VALIDATION_v01.json`. Coordinate clearance/route checks are separate from NOT RUN Unity driving, patrol AI, capture, helicopter effects and visual acceptance.
