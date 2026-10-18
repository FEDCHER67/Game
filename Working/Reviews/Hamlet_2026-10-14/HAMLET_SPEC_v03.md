# Hamlet v03 — district specification

## Кратко для Вадима

1. Хутор — смесь уютных и потрёпанных хозяйств, преимущественно со старыми деревянными домами.
2. Всего 18 обычных домов и один заброшенный; вместе с базой деда — 20 жилых построек.
3. Дома собраны в нерегулярные группы: естественная деревня, а не одинаковая сетка и не случайный разброс.
4. Пустоту заполняют сады, хозяйство и рельеф; грядок немного, дворы различаются по занятиям жителей.
5. Между домами нет заборов-клеток; проезды и пешие проходы остаются открытыми.
6. Бусик может ехать по траве, полям и грядкам; на грядках сильнее трясёт, деревья и постройки мешают естественно.
7. Зелени много, при этом улицы, входы и жители читаются с уровня игрока.
8. В хуторе оживлённо: днём снаружи 20–25 взрослых жителей, они ходят между домами и общественными местами.
9. Из животных — только свиньи и куры; старый коровник сохраняется как сельхозпостройка без коров.
10. В сельпо, сарай и заброшенный дом вход физический, без кат-сцен; базу деда обустраиваем отдельно.
11. Оставлены кладбище, сад, рыбацкое место и тракторы; обязательно круглые рулоны сена, как на фото.
12. Внутренние дороги перепланированы, внешние связи и основные ориентиры сохранены.
13. Сама карта не изменена: это спецификация и координатный план для сборщика; точные числа и мелкие детали — проектные предложения.

## 0. Authority, scope and conflicts

The owner's answers on 14 October 2026 override the attached initial brief: do not build 30–40 homes, a new two-storey district, a cattle population, dogs, an apiary, a football field, a playground, a dance venue, or an unfinished brick home. The approved extra places are cemetery, small orchard, river fishing access and ordinary parked tractors. Detailed small household props remain a reviewable dressing proposal.

This document specifies a local Hamlet revision. It does not edit the master SVG, redraw neighbouring districts, change the global game canon, implement NPC AI or prove vehicle handling. The two eastern asphalt junction anchors and southern Forest connection remain. Build new internal street geometry only inside the Hamlet integration area.

Confirmed: design principles and the survey answers. Proposed implementation defaults: precise placements, 18 occupied houses, seven small plots, building variants, counts of trees/props/animals, all terrain heights and route profiles below. They are concrete assembly instructions for review, not retroactively approved gameplay systems.

**Disclosed brief contradictions:** the locked church reaches y=602.6, while the district bbox ends at y=599.8. Preserve the church and flag its existing 2.8 m exception; do not quietly resize it. The two locked eastern road ends at x=388/390 also lie outside the district bbox: keep the short existing connector stubs as integration exceptions. Fishing access is the explicitly requested exception. The old cemetery centre has been shifted to (174,588) to fit the valid land instead of copying its out-of-bounds draft footprint. The well uses its actual small bank-side ring, not the old rectangular water label. No surrounding-map change is claimed.

All x/y are world metres, x east and y north; map scale 5 pixels/metre. House width follows local x, depth local y; rotation is counterclockwise from east. World ground elevation is inherited from neighbouring roads, not invented as an absolute sea-level datum. People are approximately 1.75 m; van approximately 5.5 × 2.1 m; doors 2.1–2.4 m tall and 1.2–1.5 m wide; house storeys about 2.8 m. Use broad open barn/base doorways approximately 1.6–2.0 m where dragging an NPC requires it. These doorway dimensions are proposed build targets.

## 1. Zoning and composition

Zoning polygons organise land use; they may overlap (e.g. settlement and planted meadow). They are not parcel boundaries or collision geometry. Never outline every polygon as a fence. Keep cultivated fields and pond as protected actual polygons. Create readable foreground yards, tree-backed midground groups and terrain folds; avoid seeing the entire village as one flat carpet. Do not fill every green patch: green gaps serve orchards, pasture, shade, drainage or vehicle cuts.

| Zone | Polygon (m) | Purpose |
| --- | --- | --- |
| 02-Z-NW | (133, 506) → (216, 506) → (216, 548) → (206, 574) → (156, 578) → (133, 564) | Old timber households and grandfather base; visible irregular clusters with shared open edges. |
| 02-Z-CHURCH | (133, 575) → (191, 575) → (191, 599.8) → (133, 599.8) | Church surroundings and cemetery; church footprint carries a documented north-boundary exception. |
| 02-Z-NORTH | (216, 548) → (323, 548) → (323, 577) → (246, 577) → (246, 570) → (216, 570) | Barn and three neighbouring households; ordinary farm life, no tractor repair business. |
| 02-Z-ORCHARD | (199, 571) → (244, 571) → (244, 596) → (199, 596) | Small old orchard; retain gaps and missing trees, not a perfectly repeated grid. |
| 02-Z-CENTRE | (254, 499) → (330, 499) → (330, 534) → (254, 534) | Shop, civic meeting place and two households; adult NPC circulation hub. |
| 02-Z-SE | (254, 404) → (362, 404) → (370, 471) → (320, 480) → (254, 466) | Loose timber households among rolling grass; off-road van routes remain broadly possible. |
| 02-Z-POND | (156, 440) → (226, 440) → (230, 489) → (181, 496) → (156, 477) | Pond bank, old well and shade trees; preserve water, leave visible bank access. |
| 02-Z-SW | (204, 429) → (235, 429) → (232, 451) → (204, 448) | One abandoned home and worn garden edge, no unfinished house. |
| 02-Z-FIELD1 | (329, 550) → (368, 550) → (368, 591) → (329, 591) | Preserved north-east cultivated field; machinery and trees outside cultivated polygon. |
| 02-Z-FIELD2 | (144, 389) → (203, 389) → (203, 428) → (144, 428) | Preserved south-west cultivated field; broad surrounding grass is bumpy but traversable. |


## 2. Streets and road joins

Main and north remain 5.4 m dirt roads. Local loop/base approaches are 4.2 m; short farm/service tracks 3.6 m. These are usable ground widths, not total shoulder width. At least 3.5 m remains clear for van lanes, 1.5 m for pedestrian routes. Roads follow rolling terrain but are smoother than off-road grass.

**Explicit changes from v11:** main keeps (390,466) and its north-west church connection but now bends through clusters; north keeps (388,545) but passes south of barn; south keeps (234,375) and Forest connection but relocates its start to the main junction (249,498); loop becomes a softer terrain-following loop joining south at (235,394); base reaches the actual fixed van pad; church extends to the south forecourt; field09 stops outside Field 2; tower becomes a curved service track. Short barn/shop approaches are new. No external connection is deleted.

Use these polylines as a connected street graph. Smooth within approximately 1.2 m of the proposed control line only after rechecking building/field clearance. Form a single unioned surface at every junction: no overlapping slab outlines, abrupt rectangle ends, embedded curbs or one road's texture border crossing another. Fade dirt into asphalt over a short transition without duplicating road markings. Keep street-end coordinates fixed where they meet the existing master roads. Mark service tracks as unpainted dirt, not miniature city roads.

| ID | Class / width | Centreline | Change / function |
| --- | --- | --- | --- |
| 02-R-main | dirt_main / 5.4 m | (390, 466) → (372, 473) → (350, 482) → (326, 487) → (295, 489) → (271, 491) → (249, 498) → (230, 510) → (224, 530) → (224, 548) → (206, 552) → (180, 550) → (158, 549) → (147, 550) | Retains south-east asphalt entry; approaches residential clusters without equal parcel spacing. |
| 02-R-north | dirt_main / 5.4 m | (224, 548) → (248, 541) → (271, 540) → (302, 540) → (330, 542) → (365, 546) → (388, 545) | Retains north-east asphalt entry and passes south of the communal barn. |
| 02-R-south | dirt_main / 5.4 m | (249, 498) → (250, 478) → (244, 457) → (237, 431) → (232, 410) → (235, 394) → (234, 375) | Retains Forest connection; follows the west side of the southern settlements. |
| 02-R-loop | dirt_local / 4.2 m | (326, 487) → (328, 462) → (335, 439) → (334, 417) → (330, 396) → (323, 382) → (293, 385) → (264, 390) → (235, 394) | Replaces rigid rectangular loop with a connected, terrain-following local street. |
| 02-R-base | dirt_access / 4.2 m | (230, 510) → (215, 505) → (199, 506) → (193, 511) → (186.4, 511.1) | Ends on the existing van pad; smooth the bend for a real van, not a pivot turn. |
| 02-R-church | dirt_access / 3.6 m | (147, 550) → (143, 563) → (143, 578) | Extends the old dead-end to the church south forecourt. |
| 02-R-field09 | farm_track / 3.6 m | (235, 394) → (220, 396) → (208, 400) | Ends at the south-east field approach, outside the cultivated polygon. |
| 02-R-tower | service_track / 3.6 m | (350, 482) → (343, 497) → (344, 508) → (338, 513) | Curves to the south side of the preserved water tower. |
| 02-R-barn | dirt_access / 4.2 m | (271, 540) → (271, 545.8) | Short loading approach to the barn south apron. |
| 02-R-shop | dirt_access / 3.6 m | (271, 491) → (270.3, 495.8) | Short shop entrance approach; pedestrian forecourt remains distinct. |


## 3. Houses, scale and identity

18 occupied homes + 1 abandoned home; grandfather base is separate, bringing total dwelling structures to 20. The grandfather base is a marker/reserved footprint only, not a furnishing prescription. Every ordinary home is one storey: no large repeated three-storey boxes, no proposed new two-storey subtype. Occupied mix: 7 old log cottages (39%), 5 old board-clad homes (28%), 4 weathered timber/tin-roof homes (22%), 2 modest brick homes (11%). Colours: faded wood, occasional muted paint/limewash, dull tin and restrained brick; do not assign rainbow asset colours.

Give timber façades physical depth: modest foundation, window/door recesses, trims, roof overhang, repair patch, porch. Four reusable structural families are acceptable; vary roof repair, front orientation, porch and maintenance without stretching an entire asset. Only seven small vegetable plots are proposed, not a garden behind every house; the remaining yards have working grass or sparse planting. Owner profiles describe a household's daily activity, not a new NPC class or quest. Each house record includes a physical front-door point and nearest street ID in JSON.

| House | Type | Centre | Rotation | W × D | Floors | Roof | Household |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 02-H01 | old_log | (160, 562) | 8 | (8, 6) | 1 | faded sheet metal with local repairs | old couple; flowers, firewood |
| 02-H02 | old_board | (181, 562) | -6 | (7, 9) | 1 | weathered corrugated metal | vegetable grower; working beds |
| 02-H03 | tin_timber | (199, 560) | 5 | (8, 7) | 1 | weathered corrugated metal | poultry keeper; chickens |
| 02-H04 | old_log | (196, 539) | -10 | (9, 7) | 1 | faded sheet metal with local repairs | frugal household; stored timber |
| 02-H05 | old_board | (211, 523) | 12 | (8, 6) | 1 | weathered corrugated metal | pig keeper; trough and small shelter |
| 02-H06 | old_log | (245, 557) | -4 | (9, 7) | 1 | faded sheet metal with local repairs | retired field worker; practical shed |
| 02-H07 | tin_timber | (251, 577) | 9 | (7, 8) | 1 | weathered corrugated metal | fruit grower; crates and sparse flower bed |
| 02-H08 | old_board | (307, 559) | 4 | (8, 7) | 1 | weathered corrugated metal | tractor driver; normal yard, no workshop |
| 02-H09 | brick | (316, 523) | -7 | (8, 7) | 1 | muted weathered tile | slightly better-kept household; vegetable beds |
| 02-H10 | old_log | (284, 516) | 2 | (9, 7) | 1 | faded sheet metal with local repairs | older villager; shaded outdoor table |
| 02-H11 | old_board | (280, 476) | 10 | (8, 6) | 1 | weathered corrugated metal | poultry household by main street |
| 02-H12 | tin_timber | (311, 472) | -4 | (8, 9) | 1 | weathered corrugated metal | pig-keeping household; muddy corner |
| 02-H13 | old_log | (352, 462) | -8 | (8, 7) | 1 | faded sheet metal with local repairs | fishing household; drying gear |
| 02-H14 | old_board | (260, 456) | 7 | (7, 9) | 1 | weathered corrugated metal | busy vegetable grower; linen line |
| 02-H15 | old_log | (272, 435) | -11 | (8, 7) | 1 | faded sheet metal with local repairs | wood-fired household; woodpile |
| 02-H16 | tin_timber | (286, 412) | 9 | (8, 6) | 1 | weathered corrugated metal | poultry household; patchy maintenance |
| 02-H17 | brick | (311, 418) | -9 | (8, 7) | 1 | muted weathered tile | small pig-keeping household |
| 02-H18 | old_log | (350, 411) | 8 | (8, 6) | 1 | faded sheet metal with local repairs | field worker; tools and vegetables |
| 02-H19 | abandoned_board | (215, 432) | -12 | (8, 6) | 1 | faded sheet metal with local repairs | unoccupied; roof damage and rusted small car |


## 4. Unfenced households

No property-boundary fences, rectangular cells, dense continuous hedges or arbitrary waist-high walls. Garden beds, small outbuildings, a mature tree and owner activity suggest the household boundary. Pig-pen livestock rails are a local animal enclosure at the communal barn only; they do not surround house plots. Gardeners keep beds; poultry households keep coops; pig households keep small shelters and feed; older residents maintain flowers or wood; fishing residents store nets. Do not furnish grandfather base here: no suggested refrigerator, motorcycle, workbench, garden, shed, porch redesign or interior layout. Do not place a doghouse after the owner chose only pigs/chickens.

The table lists exact first-pass household objects. The separate small-detail catalogue adds owner-linked dressing. Keep a broad open side route around each house where practical; do not turn every shed into a scripted hiding maze. Ordinary homes may be closed interiors, but do not fake an accessible doorway that leads to nothing. Shop/barn/abandoned-house interiors are part of the same physical world: no cutscene, teleport, loading-screen transition or scripted door-opening presentation. The grandfather base is explicitly excluded from this district furnishing plan; only its existing footprint and access are reserved. A physically open door/opening is enough; ordinary physical doors are an integration choice, not a required new system.

| House / front | Household objects: id, centre, size, angle |
| --- | --- |
| 02-H01 / south | 02-H01-Y1: flower_strip (159.59, 570.99) (3, 1) 8°; 02-H01-Y2: shed (154.51, 569.13) (3, 2.5) 13°; 02-H01-Y3: woodpile (164.82, 569.6) (2.5, 1) 8°; 02-H01-Y4: outdoor_table (151.41, 564.69) (1.5, 0.8) 13° |
| 02-H02 / south | 02-H02-Y1: vegetable_garden (179.69, 570.9) (6, 4) -6°; 02-H02-Y2: shed (172.18, 563.81) (3, 2.5) -1°; 02-H02-Y3: clothesline (188.92, 566.28) (3.5, 0.4) -6°; 02-H02-Y4: water_barrel (174.82, 568.54) (0.7, 0.7) -1° |
| 02-H03 / south | 02-H03-Y1: chicken_coop (197.07, 568.79) (2.5, 2) 5°; 02-H03-Y2: open_working_grass (192.38, 566.09) (4, 3) 10°; 02-H03-Y3: feed_bin (192.38, 566.09) (0.8, 0.8) 5°; 02-H03-Y4: water_barrel (202.46, 568.31) (0.7, 0.7) 10° |
| 02-H04 / north | 02-H04-Y1: woodpile (196.69, 530.03) (4, 1.2) -10°; 02-H04-Y2: shed (191.42, 531.25) (3.5, 2.5) -5°; 02-H04-Y3: open_working_grass (201.71, 532.05) (4, 3) -10°; 02-H04-Y4: outdoor_table (201.71, 532.05) (1.5, 0.8) -5° |
| 02-H05 / east | 02-H05-Y1: pig_shelter (202.58, 519.82) (3, 2.5) 12°; 02-H05-Y2: feed_trough (202.28, 525.22) (1.8, 0.7) 17°; 02-H05-Y3: vegetable_garden (205.93, 515.57) (4, 3) 12°; 02-H05-Y4: water_barrel (205.13, 529.82) (0.7, 0.7) 17° |
| 02-H06 / south | 02-H06-Y1: flower_strip (246.29, 565.91) (3, 1) -4°; 02-H06-Y2: shed (240.95, 565.04) (3, 2.5) 1°; 02-H06-Y3: woodpile (251.17, 563.55) (2.5, 1) -4°; 02-H06-Y4: outdoor_table (237.07, 561.26) (1.5, 0.8) 1° |
| 02-H07 / south | 02-H07-Y1: vegetable_garden (253.52, 585.64) (6, 4) 9°; 02-H07-Y2: shed (243.74, 582.32) (3, 2.5) 14°; 02-H07-Y3: clothesline (258.02, 582.63) (3.5, 0.4) 9°; 02-H07-Y4: water_barrel (248.11, 585.52) (0.7, 0.7) 14° |
| 02-H08 / south | 02-H08-Y1: shed (311.07, 567.03) (3.5, 2.5) 4°; 02-H08-Y2: open_working_grass (299.06, 554.76) (4, 3) 9°; 02-H08-Y3: wheelbarrow (305.73, 567.91) (1.4, 0.6) 4°; 02-H08-Y4: woodpile (300.85, 565.57) (2.5, 1) 9° |
| 02-H09 / north | 02-H09-Y1: vegetable_garden (317.88, 514.2) (6, 4) -7°; 02-H09-Y2: shed (308.37, 518.22) (3, 2.5) -2°; 02-H09-Y3: clothesline (322.59, 516.87) (3.5, 0.4) -7°; 02-H09-Y4: water_barrel (312.5, 514.71) (0.7, 0.7) -2° |
| 02-H10 / north | 02-H10-Y1: flower_strip (284.0, 507.0) (3, 1) 2°; 02-H10-Y2: shed (278.84, 508.63) (3, 2.5) 7°; 02-H10-Y3: woodpile (289.16, 508.63) (2.5, 1) 2°; 02-H10-Y4: outdoor_table (275.54, 512.92) (1.5, 0.8) 7° |
| 02-H11 / north | 02-H11-Y1: chicken_coop (279.88, 467.0) (2.5, 2) 10°; 02-H11-Y2: vegetable_garden (274.74, 468.7) (5, 3) 15°; 02-H11-Y3: feed_bin (285.06, 468.56) (0.8, 0.8) 10°; 02-H11-Y4: water_barrel (271.5, 473.03) (0.7, 0.7) 15° |
| 02-H12 / north | 02-H12-Y1: pig_shelter (311.68, 463.03) (3, 2.5) -4°; 02-H12-Y2: feed_trough (306.41, 464.26) (1.8, 0.7) 1°; 02-H12-Y3: open_working_grass (302.8, 468.3) (4, 3) -4°; 02-H12-Y4: water_barrel (316.7, 465.04) (0.7, 0.7) 1° |
| 02-H13 / north | 02-H13-Y1: shed (348.59, 453.67) (3, 2.5) -8°; 02-H13-Y2: net_drying_rack (344.43, 457.13) (2.5, 0.3) -3°; 02-H13-Y3: open_working_grass (344.43, 457.13) (4, 3) -8°; 02-H13-Y4: outdoor_table (344.43, 457.13) (1.5, 0.8) -3° |
| 02-H14 / west | 02-H14-Y1: vegetable_garden (268.81, 454.14) (6, 4) 7°; 02-H14-Y2: shed (266.14, 449.42) (3, 2.5) 12°; 02-H14-Y3: clothesline (268.28, 459.52) (3.5, 0.4) 7°; 02-H14-Y4: water_barrel (268.28, 459.52) (0.7, 0.7) 12° |
| 02-H15 / west | 02-H15-Y1: woodpile (280.93, 433.89) (4, 1.2) -11°; 02-H15-Y2: shed (278.68, 428.97) (3.5, 2.5) -6°; 02-H15-Y3: open_working_grass (279.95, 439.22) (4, 3) -11°; 02-H15-Y4: outdoor_table (279.95, 439.22) (1.5, 0.8) -6° |
| 02-H16 / south | 02-H16-Y1: chicken_coop (287.53, 420.87) (2.5, 2) 9°; 02-H16-Y2: open_working_grass (282.17, 420.14) (4, 3) 14°; 02-H16-Y3: feed_bin (282.17, 420.14) (0.8, 0.8) 9°; 02-H16-Y4: water_barrel (292.34, 418.39) (0.7, 0.7) 14° |
| 02-H17 / east | 02-H17-Y1: pig_shelter (302.06, 419.06) (3, 2.5) -9°; 02-H17-Y2: feed_trough (303.07, 413.74) (1.8, 0.7) -4°; 02-H17-Y3: vegetable_garden (304.29, 424.0) (4, 3) -9°; 02-H17-Y4: water_barrel (306.94, 409.97) (0.7, 0.7) -4° |
| 02-H18 / west | 02-H18-Y1: shed (358.99, 410.56) (3.5, 2.5) 8°; 02-H18-Y2: open_working_grass (357.11, 405.49) (4, 3) 13°; 02-H18-Y3: wheelbarrow (357.11, 405.49) (1.4, 0.6) 8°; 02-H18-Y4: woodpile (357.61, 415.8) (2.5, 1) 13° |
| 02-H19 / east | 02-H19-Y1: rusted_car (206.24, 434.08) (3.8, 1.6) -12°; 02-H19-Y2: broken_timber (206.63, 428.69) (2, 1) -7°; 02-H19-Y3: overgrown_beds (209.02, 438.73) (4, 3) -12° |


## 5. Anchors and unique places

Keep the primary composition: church north-west; grandfather nearby to its south; communal farm north-central; shop centre; tower east; pond/well west; yellow fields north-east and south-west. The new village should still be recognisable from the reference arrangement.

Former cowshed stays in place as a communal barn; the old cow-pen location is used for pigs. No cow spawns. The two parked tractors are ordinary farm machinery; no dedicated repair yard, service business or mechanically interactive tractor system is implied. Orchard and cemetery are small land uses; graves/trees must not become an obstacle maze.

Fishing access crosses the pre-existing eastern asphalt at grade and reaches the river. Do not invent a new bridge across the river. The exact world river bank and shared traffic envelope must be surveyed by the assembler before placing the dock abutment and boat. Do not alter river geometry to force these props to fit.

| ID | Kind | Location / bounds | Size | Notes |
| --- | --- | --- | --- | --- |
| 02-A-CHURCH | church | (143.6, 592.3) | (18.4, 20.6) | Preserve existing outline exactly; north edge 602.6 m is 2.8 m outside supplied district bbox. Do not shrink or move it. |
| 02-A-BASE | grandfather_base | (166, 520) | (10, 7.5) | Existing base marker only. Owner will design all base furnishing/interior separately; keep location and access. |
| 02-A-BASE-PAD | van_loading_pad | (186.4, 511.1) | (9.2, 9.2) | Preserved parking/loading pad; flat gravel; reversing allowed, not claimed as full U-turn area. |
| 02-A-BASE-TURN | manoeuvring_apron | (186.4, 511.1) | (15, 14) | Open extension around fixed pad; broad multi-point manoeuvre, validate turning in Unity. |
| 02-A-BARN | communal_barn | (273.6, 555) | (18, 10) | Preserve former cowshed structure and position. No cows in v03; communal farm storage with nearby pigs/chickens. |
| 02-A-HAY | hay_shelter | (293, 556) | (6, 10) | Preserve anchor; broad roof with usable open sides. |
| 02-A-PEN | small_pig_pen | (273.6, 565.6) | (14, 7) | Former cow-pen anchor reused for pigs. Low livestock rails only here; no fences between house plots. |
| 02-A-BARN-PAD | van_loading_pad | (273.6, 547.5) | (15, 4.5) | Flat barn apron; preserve door-to-van passage. |
| 02-A-SHOP | village_shop | (270.3, 502.5) | (12, 8) | Physical open entrance facing south; readable porch and shop sign; no scene transition. |
| 02-A-SQUARE | meeting_forecourt | (250, 507.5) | (11, 9) | Preserved plaza; obelisk and benches, no football or dance venue. |
| 02-A-OBELISK | obelisk | (249, 509) | (1.2, 1.2) | Small rural marker, not a dominant monument. |
| 02-A-BENCH1 | bench | (245.8, 510.2) | (1.8, 0.5) | A seat facing plaza. |
| 02-A-BENCH2 | bench | (253.5, 510.2) | (1.8, 0.5) | Offset second seat; clear walking route. |
| 02-A-SIGN | shop_notice_board | (261.8, 505) | (1.5, 0.25) | Paper notes, opening hours and old notices. |
| 02-A-TOWER | water_tower | (338.4, 517.8) | (3.8, 3.8) | Rozhnovsky tower; about 12 m tall; circular base inside stated footprint. |
| 02-A-WELL | old_well | (217.9, 472.7) | (0.75, 0.75) | Small circular masonry ring on actual dry bank. Decorative roof can overhang water; no ground collider for roof. |
| 02-A-POND | pond | actual polygon in JSON | () | Exact source village pond polygon, not its rectangular bbox. Water blocks van travel. |
| 02-A-FIELD1 | cultivated_field | (348.5, 570.5) | (39, 41) | Preserve established cultivated bounds; no houses or road surfaces placed inside. |
| 02-A-FIELD2 | cultivated_field | (173.5, 408.5) | (59, 39) | Preserve established cultivated bounds; no houses or road surfaces placed inside. |
| 02-U-CEMETERY | cemetery | (174, 588) | (23, 15) | Placed east of church, wholly inside district; no new NPC category or quest implied. |
| 02-U-ORCHARD | orchard | (221.5, 583.5) | (45, 25) | Small old orchard; productive trees with irregular gaps, no apiary. |
| 02-U-TRACTOR1 | parked_tractor | (286, 570) | (4, 2.2) | Ordinary parked agricultural tractor; no dedicated workshop. |
| 02-U-TRACTOR2 | parked_tractor | (319, 558) | (4, 2.2) | Second tractor on grass outside field; keep field approach. |
| 02-U-TRAILER | farm_trailer | (319, 564) | (4, 2.1) | Occasional farm attachment, no repair area. |
| 02-U-STOP | bus_stop | (366, 481) | (3.4, 1.5) | Within district beside lower approach; no abandoned kiosk. |
| 02-U-WATER1 | standpipe | (239, 508) | (0.4, 0.4) | Shared water tap near street, moved off the new driving surface. |
| 02-U-WATER2 | standpipe | (321, 477) | (0.4, 0.4) | Small tap by eastern houses. |
| 02-U-WASTE1 | shared_bin | (222, 520) | (1, 0.8) | Small practical refuse spot; not a dump district. |
| 02-U-WASTE2 | shared_bin | (338, 430) | (1, 0.8) | Second refuse collection point. |
| 02-U-TRANSFORMER | transformer_box | (296, 527) | (2.5, 2) | Service box with pole connection; not a new gameplay system. |
| 02-FISH-PATH | pedestrian_path | (364, 466) → (369, 459) → (382, 453) → (397, 451) → (408, 451) | () | Shared-world river access exception. Cross existing bypass at grade; do not cut a new road or regenerate river. Place landward dock abutment on surveyed west bank. |
| 02-FISH-DOCK | fishing_platform | (411, 451) | (5, 2) | River anchor. Final bank abutment is a 3D integration check; platform may project over water. |
| 02-FISH-BOAT | upturned_boat | (404, 456) | (3.8, 1.5) | Bank-dressing outside bypass traffic envelope; confirm river dry-bank location. |
| 02-FISH-NETS | fishing_nets | (405, 449) | (2.2, 0.3) | Nets on two stakes; line visuals have no blocking collider. |


## 6. Infrastructure

Utility poles follow main/north/south/loop outside the driving surface. The JSON contains explicit pole points and service-wire endpoints, not a instruction to scatter 26 poles regardless of length. Heights: poles about 7 m, street wires about 6 m, service drops about 4.2 m at the house end. Poles collide; wires/lamps do not add invisible ground walls. Integrate branches at street junctions using the nearest compatible pole; no independent floating wire networks. Adjust wire attachment to the roof, not the centre of the house in 3D.

Six simple lamps share utility supports rather than city-style rows of identical ornamental lamps. Water taps (239,508), (321,477), the small transformer (296,527), modest refuse spots (222,520), (338,430), noticeboard and existing shop benches have concrete records. The bus stop (366,481) is on the lower approach within district bounds; its sign is not a separate abandoned kiosk.

One shallow main-road ditch is 0.7 m wide and 0.25 m deep, with soft edges. It is driveable at low speed and broken/culverted at access points; never make it a continuous steep moat. Detail catalogue culverts and footbridges are crossing-bound recipes: instantiate only at a real path/driveway crossing, not as independent random yard props. Footbridges are for foot circulation, not a barrier in broad grass shortcuts. Do not render these proposed dressing points as finished engineering drainage works.

| Pole | Centre | Height |
| --- | --- | --- |
| 02-P-01 | (358.85, 473.41) | 7 |
| 02-P-02 | (331.25, 481.21) | 7 |
| 02-P-03 | (298.44, 484.17) | 7 |
| 02-P-04 | (265.97, 487.77) | 7 |
| 02-P-05 | (236.08, 500.72) | 7 |
| 02-P-06 | (219.4, 530.66) | 7 |
| 02-P-07 | (209.04, 546.61) | 7 |
| 02-P-08 | (178.78, 545.34) | 7 |
| 02-P-09 | (146.58, 545.42) | 7 |
| 02-P-10 | (225.29, 552.42) | 7 |
| 02-P-11 | (250.75, 545.48) | 7 |
| 02-P-12 | (278.09, 544.6) | 7 |
| 02-P-13 | (305.31, 544.85) | 7 |
| 02-P-14 | (332.59, 546.93) | 7 |
| 02-P-15 | (253.39, 502.22) | 7 |
| 02-P-16 | (251.29, 465.78) | 7 |
| 02-P-17 | (242.99, 435.55) | 7 |
| 02-P-18 | (237.24, 407.03) | 7 |
| 02-P-19 | (238.59, 374.76) | 7 |
| 02-P-20 | (330.27, 491.35) | 7 |
| 02-P-21 | (333.29, 460.41) | 7 |
| 02-P-22 | (339.27, 431.63) | 7 |
| 02-P-23 | (336.03, 403.08) | 7 |
| 02-P-24 | (318.15, 377.86) | 7 |
| 02-P-25 | (289.84, 380.88) | 7 |
| 02-P-26 | (262.25, 385.6) | 7 |
| 02-P-27 | (230.41, 389.99) | 7 |


## 7. Nature and terrain

Planting is organised in loose groves, orchard and household fruit groups. Tree ground collisions are trunks only. Shade crowns begin around 3.2 m, fruit crowns around 2.5 m; do not block all pedestrian sightlines at head height. Exact trunk positions are in JSON. Their deterministic selection is constrained by groves and house activities, not a uniform scatter over the map. Crown spacing can be adjusted artistically while retaining validated trunk/passages.

Soft lilac/elder/berry shrubs are passable for people and van; no collider per bush. Keep gaps, no shrub walls outlining plots. Reeds belong at pond margins only. The tree/shrub counts below are build proposals; greenery quality depends on grouping and views, not maximising instance count.

| Planting group | Count |
| --- | --- |
| grove_west | 24 |
| grove_south | 10 |
| green_centre | 12 |
| grove_east | 16 |
| grove_north | 12 |
| orchard_trees | 18 |
| household_fruit | 16 |
| pond_willows | 6 |
| Soft household shrub groups | 36 |

| Terrain | Extent | Relative height | Purpose |
| --- | --- | --- | --- |
| 02-TR-north_fold | (253, 576) → (321, 576) → (321, 598) → (253, 598) | 3.8 | Broad northern rolling rise; soften slopes and keep agricultural approaches driveable. |
| 02-TR-central_rise | (254, 430) → (295, 430) → (310, 450) → (289, 469) → (254, 469) | 2.6 | Low central rise between homes; sparse shade trees, clear grassy approaches. |
| 02-TR-east_rise | (337, 393) → (370, 393) → (370, 450) → (345, 450) | 3.4 | Eastern rolling ground beside houses; no sheer wall separating neighbourhoods. |
| 02-TR-west_hollow | (135, 430) → (159, 430) → (172, 445) → (169, 488) → (145, 491) → (135, 471) | -1.4 | Shallow open hollow near pond and forest; does not enlarge pond or force a road tunnel. |
| 02-TR-south_ripple | (205, 376) → (230, 376) → (229, 419) → (207, 419) | 1.5 | Bumpy grass beside south-west field, traversable by van. |
| 02-TR-MICRO | (132.6, 373.6) → (374.0, 373.6) → (374.0, 599.8) → (132.6, 599.8) | [0.15, 0.55] | Apply to meadow/off-road only, with soft rounded crests. Tuning targets, not proven van physics. Roads 0.05–0.18 m; door aprons and loading pads flatten. |


**Van feel:** broad grass is mostly traversable; repeated rounded undulations make the van pitch/roll and jolt. Start meadow variation at 0.15–0.55 m over 3–8 m wavelengths, rare 0.8 m bumps. Larger landforms blend over broad slopes, roughly 4–12 degrees as a tuning target, not a proven traction limit. Match their pads under houses to the surrounding grade; do not put a 3 m hump through a doorstep. Firm dirt is smoother (roughly 0.05–0.18 m variation), loading zones flat. Taper all height features to zero at existing-road connections; blend their overlapping influences rather than add every peak.

No forced wheel-stopping ridges, sharp sawtooth terrain, continuous ravine cutting the village in half or invisible no-drive zones. Buildings, poles, big rocks and trunks are solid. Grass, soft bushes, small visual tools and hanging wires are not. NPC navigation also needs terrain validation; this document does not prove existing navmesh generation supports the result.

## 8. Small details for owner review

The owner approved rich varied households in principle; the following 52 families are **proposed dressing**, not 52 separately confirmed game mechanics. Dimensions are approximate build dimensions; count is district-wide, and existing household objects are counted once. [H] marks a solid low/large obstacle that can affect a chase, not a guarantee of full visual concealment. Prefer collision on appropriate large objects; do not add precise colliders to every tiny item. Mounted visual families use parent-bound placement recipes; ground items have exact JSON centres. Composite visuals do not create new ground blocks.

| Family | Approx. size (m) | Count | [H] | Placement / purpose |
| --- | --- | --- | --- | --- |
| woodpile | (2.5, 1) | 7 | [H] | Stored firewood at wood-burning homes. |
| split_log | (0.6, 0.18) | 5 | — | Beside woodpile, never spread evenly. |
| stump | (0.5, 0.5) | 3 | [H] | Chopping stump at working yards. |
| axe_in_stump | (0.5, 0.05) | 2 | — | Visual, not an invented tool mechanic. |
| water_barrel | (0.7, 0.7) | 10 | [H] | Collect rain by shed roofs. |
| watering_can | (0.35, 0.25) | 5 | — | Next to vegetable plots. |
| garden_spade | (0.3, 0.08) | 4 | — | Lean against shed, visual only. |
| garden_rake | (0.4, 0.08) | 3 | — | At gardening homes. |
| wheelbarrow | (1.4, 0.6) | 3 | [H] | Working farm yards. |
| wooden_crate | (0.6, 0.4) | 6 | [H] | Orchard produce and shop storage. |
| feed_sack | (0.5, 0.3) | 5 | — | Dry shelter beside pigs or chickens. |
| feed_trough | (1.8, 0.7) | 3 | [H] | Pig-keeping yards. |
| chicken_feeder | (0.45, 0.45) | 3 | — | Beside coops. |
| egg_basket | (0.4, 0.3) | 3 | — | At poultry yards, visual only. |
| clothesline | (3.5, 0.4) | 4 | — | Lines high enough for walking, posts alone collide. |
| linen | (0.7, 0.05) | 5 | — | Visual hanging sheets, not an opaque gameplay wall. |
| wash_basin | (0.5, 0.5) | 3 | — | Laundry households. |
| outdoor_table | (1.5, 0.8) | 6 | [H] | Common social yards. |
| chair | (0.5, 0.5) | 5 | [H] | By outdoor tables. |
| bench | (1.8, 0.5) | 4 | [H] | Shop, yard and pond bank seats. |
| flower_strip | (3, 1) | 5 | — | Uneven care, some yards have none. |
| flower_pot | (0.35, 0.35) | 5 | — | Porches of cared-for homes. |
| compost_heap | (1.8, 1.5) | 3 | — | Gardening homes only. |
| wooden_pallet | (1.2, 0.8) | 3 | [H] | Practical storage, not industrial yard clutter. |
| bucket | (0.3, 0.3) | 5 | — | Well and animal care. |
| rusted_wheel | (0.6, 0.2) | 2 | — | Near tractor and farm shed. |
| tyre | (0.7, 0.25) | 2 | — | A few spare tyres, no tyre-wall maze. |
| handcart | (1.4, 0.75) | 2 | [H] | Farm deliveries. |
| round_hay_bale | (1.6, 1.3) | 5 | [H] | Mandatory owner-reference cylindrical rolled hay/straw bales; layered circular ends and fibrous body, not rectangular bundles. Barn storage outside clear loading apron. |
| haystack | (2.8, 2.8) | 3 | [H] | Field edge/hay shelter; not a road barrier. |
| net_drying_rack | (2.5, 0.3) | 2 | — | Fishing household and river landing. |
| coiled_rope | (0.4, 0.4) | 2 | — | By fishing gear. |
| fishing_bucket | (0.3, 0.3) | 2 | — | Near fishing nets. |
| upturned_boat | (3.8, 1.5) | 1 | [H] | Existing planned river-bank boat. |
| notice_board | (1.5, 0.25) | 1 | [H] | Shop notices already planned. |
| shop_sign | (2, 0.1) | 1 | — | Readable painted sign on shop façade. |
| mailbox | (0.35, 0.25) | 6 | — | Selected front walls, not identical on each home. |
| house_number | (0.25, 0.02) | 8 | — | Mounted visual plates. |
| door_mat | (0.7, 0.45) | 4 | — | Only at cared-for entrances. |
| window_planter | (1, 0.25) | 4 | — | Mounted to houses, no free-floating props. |
| curtain | (1, 0.02) | 6 | — | Visible behind windows; no fabricated interiors. |
| porch_step | (1.4, 0.45) | 5 | — | Low entrance transition, retain carry route. |
| broken_timber | (2, 1) | 1 | [H] | Abandoned home only. |
| rusted_car | (3.8, 1.6) | 1 | [H] | Abandoned home only. |
| reed_clump | (1.5, 1) | 8 | — | Pond margins, gaps for sightlines. |
| rounded_rock | (1, 0.8) | 3 | [H] | Sparse forest edge only, not filled gaps everywhere. |
| drain_culvert | (1, 0.5) | 3 | — | At three drive crossings; no lip that traps van. |
| timber_footbridge | (2.4, 1.8) | 2 | — | Pond-bank ditch foot crossings. |
| mud_patch | (3, 2) | 6 | — | Pig/tractor areas; ground visual, no invented slow debuff. |
| wheel_rut | (4, 1.8) | 6 | — | Soft ground near field entrances. |
| dung_patch | (0.6, 0.4) | 4 | — | Pig shelters only, modest stylized dressing. |
| peeling_paint | (1.5, 0.01) | 8 | — | Façade variation without rebuilding whole asset. |


## 9. Gameplay circulation and assembly priorities

**Primary activity:** target 20–25 adult residents outside during daytime. This is an owner-approved population target, not a prescribed respawn algorithm. Villagers move between homes, shop, communal barn, gardens, cemetery and pond, rather than stand motionless at identical spawn points. Keep lively visible encounters across the village, with the shop an obvious gathering point. Use adult villagers; no new quest system or respawn algorithm is approved here. Mandatory round hay bales: five explicit cylinders, two beside barn storage, one beside Field 1, two beside Field 2. No hay-bale wall or new rolling mechanic is required. Animal plan uses five pig activity markers and twelve chicken markers, proposed counts only. They are marker data, not prebuilt AI or proof of playable capture.

**Transport:** fields and the seven small vegetable plots are vehicle-passable; beds are rougher than meadow, but have no surrounding invisible collider. Crop foliage is nonblocking; raised soil uses rounded low bumps. No new crop-destruction or damage mechanic is specified. Roads give reliable passage; grass gives shorter, bumpier alternatives almost throughout the village. The four named corridors below are guaranteed-clear priority routes to preserve, not the only allowed off-road routes. Do not erect barriers in every other gap. A good cut makes players choose speed/control/short distance while carrying cargo; do not implement cargo damage/reward penalties just because this document describes bumps.

**Capture/loading places:** base's fixed 9.2 m pad plus open manoeuvring apron; barn south apron; open road shoulder near (277,492) for shop; grass beside H11/H12 and the south groups. Keep door-to-van carriage space; roadside loading is not automatically safe or hidden. Allow walking around trunks, porches and sheds; compact groups create local corners without closing the whole settlement.

**Routes:** remain able to drive main ↔ north and main ↔ south ↔ loop, with both eastern exits and Forest exit. A pursuit does not end merely because a district label changes. This local layout adds no police-reset rule, crime-memory timer, NPC farming prohibition, invisible spawn wall around base, or economy change; those remain whole-game design concerns.

| Route | Proposed centreline | Reserved width | Purpose |
| --- | --- | --- | --- |
| 02-G-NW | (157, 540) → (202, 515) → (216, 511) | 4.5 | Base-to-NW households shortcut; keep trunk and solid-prop clearance. Proposal adjusted around actual trunk/prop footprints; no paving or exclusive-drive restriction. |
| 02-G-CENTRE | (260, 529) → (286, 531) → (307, 532) | 4.5 | Grass behind shop and central homes; articulated path may bend around trees. Proposal adjusted around actual trunk/prop footprints; no paving or exclusive-drive restriction. |
| 02-G-SOUTH | (255, 446) → (315, 440) | 4.5 | Cross-yard southern shortcut with bumps; passing between clusters is common. Proposal adjusted around actual trunk/prop footprints; no paving or exclusive-drive restriction. |
| 02-G-EAST | (337, 474) → (340, 453) → (353, 438) → (355, 426) → (366, 413) → (364, 408) → (361, 407) | 4.5 | Eastern off-road passage between rolling folds and homes. Proposal adjusted around actual trunk/prop footprints; no paving or exclusive-drive restriction. |


**Assembly order:** (1) reference master coordinates and preserve anchors; (2) connect and union roads; (3) fit terrain and level pads; (4) houses and open interiors; (5) owner-linked sheds/gardens; (6) reserve van/walk corridors; (7) plant trunks and groves; (8) dress owner activities; (9) wires/decals/signs; (10) walk/drive and adjust local details. Do not start with hundreds of decorative props before routes work.

**Required in-engine checks (not performed by this documentation task):** eye-level views on both approaches, shop square, base, pond, east and south groups; actual van traversing both road loops and several broad grass cuts; two people carrying an NPC through each accessible doorway; van reversing/loading at base and barn; walk between house groups without mesh gaps; verify foliage sightlines, terrain seams and shared asphalt connections. Show orthographic plan plus eye-level screens. A coordinate check is not proof of fun or visual quality.

## 10. Machine-readable layout

The complete external file `HAMLET_LAYOUT_v03.json` is the same JSON embedded below. Objects are not just centre dots: solids include footprints, houses include door positions, roads include connected centreline/width, nature includes individual planting points and terrain includes zones with height proposals. Special composite placements may intentionally contain child items (e.g. pigs inside shelter, obelisk on plaza). Parent-bound detail visuals are recipes, not separate arbitrary ground objects. Heights require integration with actual world terrain.

```json

{
  "schema": "volunteers_only.hamlet_layout.v03",
  "date": "2026-10-14",
  "units": "metres",
  "coordinate_system": "x east, y north; heights are relative terrain deltas; rotations CCW from east",
  "district_bbox_m": [
    132.6,
    373.6,
    374.0,
    599.8
  ],
  "source_map": "C:\\Users\\chern_0eqkb03\\Desktop\\GAME\\ArtSource\\References\\Map\\World_v11\\WORLD_MAP_v11.json",
  "status": "Reviewable placement proposal implementing owner-approved design; not a regenerated map or runtime implementation",
  "confirmed_decisions": [
    "15–20 homes maximum; old timber predominant, brick rare",
    "Irregular coherent groups, rich varied unfenced yards",
    "Green but visible streets and yards; rolling and bumpy off-road terrain",
    "Broad off-road van access, natural trunk/building obstacles",
    "Pigs and chickens only; 20–25 adult villagers outside by day",
    "Open physical interiors: base, shop, barn, abandoned home",
    "Cemetery, small orchard, fishing place and parked tractors; no tractor workshop",
    "One abandoned home, no unfinished home",
    "Internal streets may be redesigned; preserve all external connections",
    "Base furnishing/interior separate; preserve marker/access only",
    "Few vegetable beds; fields and beds driveable with bumps",
    "Round rolled hay/straw bales matching owner reference are mandatory",
    "Old clutter local and purposeful; most yards inhabited, no village-wide dump"
  ],
  "proposed_defaults": [
    "18 ordinary homes plus one abandoned; grandfather base is a twentieth dwelling",
    "Exact coordinates, counts of props/trees/animals, terrain amplitudes and prop recipes are implementation proposals",
    "Exact detail instances/counts remain build proposals; purposeful local clutter is owner-approved"
  ],
  "boundary_exceptions": [
    "Existing locked church; explicit disclosed source contradiction.",
    "Two retained asphalt connectors outside district bbox",
    "Requested fishing access outside district bbox"
  ],
  "zones": [
    {
      "id": "02-Z-NW",
      "kind": "planning_zone",
      "polygon_m": [
        [
          133,
          506
        ],
        [
          216,
          506
        ],
        [
          216,
          548
        ],
        [
          206,
          574
        ],
        [
          156,
          578
        ],
        [
          133,
          564
        ]
      ],
      "notes": "Old timber households and grandfather base; visible irregular clusters with shared open edges.",
      "exclusive": false
    },
    {
      "id": "02-Z-CHURCH",
      "kind": "planning_zone",
      "polygon_m": [
        [
          133,
          575
        ],
        [
          191,
          575
        ],
        [
          191,
          599.8
        ],
        [
          133,
          599.8
        ]
      ],
      "notes": "Church surroundings and cemetery; church footprint carries a documented north-boundary exception.",
      "exclusive": false
    },
    {
      "id": "02-Z-NORTH",
      "kind": "planning_zone",
      "polygon_m": [
        [
          216,
          548
        ],
        [
          323,
          548
        ],
        [
          323,
          577
        ],
        [
          246,
          577
        ],
        [
          246,
          570
        ],
        [
          216,
          570
        ]
      ],
      "notes": "Barn and three neighbouring households; ordinary farm life, no tractor repair business.",
      "exclusive": false
    },
    {
      "id": "02-Z-ORCHARD",
      "kind": "planning_zone",
      "polygon_m": [
        [
          199,
          571
        ],
        [
          244,
          571
        ],
        [
          244,
          596
        ],
        [
          199,
          596
        ]
      ],
      "notes": "Small old orchard; retain gaps and missing trees, not a perfectly repeated grid.",
      "exclusive": false
    },
    {
      "id": "02-Z-CENTRE",
      "kind": "planning_zone",
      "polygon_m": [
        [
          254,
          499
        ],
        [
          330,
          499
        ],
        [
          330,
          534
        ],
        [
          254,
          534
        ]
      ],
      "notes": "Shop, civic meeting place and two households; adult NPC circulation hub.",
      "exclusive": false
    },
    {
      "id": "02-Z-SE",
      "kind": "planning_zone",
      "polygon_m": [
        [
          254,
          404
        ],
        [
          362,
          404
        ],
        [
          370,
          471
        ],
        [
          320,
          480
        ],
        [
          254,
          466
        ]
      ],
      "notes": "Loose timber households among rolling grass; off-road van routes remain broadly possible.",
      "exclusive": false
    },
    {
      "id": "02-Z-POND",
      "kind": "planning_zone",
      "polygon_m": [
        [
          156,
          440
        ],
        [
          226,
          440
        ],
        [
          230,
          489
        ],
        [
          181,
          496
        ],
        [
          156,
          477
        ]
      ],
      "notes": "Pond bank, old well and shade trees; preserve water, leave visible bank access.",
      "exclusive": false
    },
    {
      "id": "02-Z-SW",
      "kind": "planning_zone",
      "polygon_m": [
        [
          204,
          429
        ],
        [
          235,
          429
        ],
        [
          232,
          451
        ],
        [
          204,
          448
        ]
      ],
      "notes": "One abandoned home and worn garden edge, no unfinished house.",
      "exclusive": false
    },
    {
      "id": "02-Z-FIELD1",
      "kind": "planning_zone",
      "polygon_m": [
        [
          329,
          550
        ],
        [
          368,
          550
        ],
        [
          368,
          591
        ],
        [
          329,
          591
        ]
      ],
      "notes": "Preserved north-east cultivated field; machinery and trees outside cultivated polygon.",
      "exclusive": false
    },
    {
      "id": "02-Z-FIELD2",
      "kind": "planning_zone",
      "polygon_m": [
        [
          144,
          389
        ],
        [
          203,
          389
        ],
        [
          203,
          428
        ],
        [
          144,
          428
        ]
      ],
      "notes": "Preserved south-west cultivated field; broad surrounding grass is bumpy but traversable.",
      "exclusive": false
    }
  ],
  "streets": [
    {
      "id": "02-R-main",
      "kind": "street",
      "road_class": "dirt_main",
      "width_m": 5.4,
      "polyline_m": [
        [
          390,
          466
        ],
        [
          372,
          473
        ],
        [
          350,
          482
        ],
        [
          326,
          487
        ],
        [
          295,
          489
        ],
        [
          271,
          491
        ],
        [
          249,
          498
        ],
        [
          230,
          510
        ],
        [
          224,
          530
        ],
        [
          224,
          548
        ],
        [
          206,
          552
        ],
        [
          180,
          550
        ],
        [
          158,
          549
        ],
        [
          147,
          550
        ]
      ],
      "rotation_deg": null,
      "notes": "Retains south-east asphalt entry; approaches residential clusters without equal parcel spacing.",
      "external_exception": true,
      "junction_radius_m": 6.0
    },
    {
      "id": "02-R-north",
      "kind": "street",
      "road_class": "dirt_main",
      "width_m": 5.4,
      "polyline_m": [
        [
          224,
          548
        ],
        [
          248,
          541
        ],
        [
          271,
          540
        ],
        [
          302,
          540
        ],
        [
          330,
          542
        ],
        [
          365,
          546
        ],
        [
          388,
          545
        ]
      ],
      "rotation_deg": null,
      "notes": "Retains north-east asphalt entry and passes south of the communal barn.",
      "external_exception": true,
      "junction_radius_m": 6.0
    },
    {
      "id": "02-R-south",
      "kind": "street",
      "road_class": "dirt_main",
      "width_m": 5.4,
      "polyline_m": [
        [
          249,
          498
        ],
        [
          250,
          478
        ],
        [
          244,
          457
        ],
        [
          237,
          431
        ],
        [
          232,
          410
        ],
        [
          235,
          394
        ],
        [
          234,
          375
        ]
      ],
      "rotation_deg": null,
      "notes": "Retains Forest connection; follows the west side of the southern settlements.",
      "external_exception": false,
      "junction_radius_m": 6.0
    },
    {
      "id": "02-R-loop",
      "kind": "street",
      "road_class": "dirt_local",
      "width_m": 4.2,
      "polyline_m": [
        [
          326,
          487
        ],
        [
          328,
          462
        ],
        [
          335,
          439
        ],
        [
          334,
          417
        ],
        [
          330,
          396
        ],
        [
          323,
          382
        ],
        [
          293,
          385
        ],
        [
          264,
          390
        ],
        [
          235,
          394
        ]
      ],
      "rotation_deg": null,
      "notes": "Replaces rigid rectangular loop with a connected, terrain-following local street.",
      "external_exception": false,
      "junction_radius_m": 6.0
    },
    {
      "id": "02-R-base",
      "kind": "street",
      "road_class": "dirt_access",
      "width_m": 4.2,
      "polyline_m": [
        [
          230,
          510
        ],
        [
          215,
          505
        ],
        [
          199,
          506
        ],
        [
          193,
          511
        ],
        [
          186.4,
          511.1
        ]
      ],
      "rotation_deg": null,
      "notes": "Ends on the existing van pad; smooth the bend for a real van, not a pivot turn.",
      "external_exception": false,
      "junction_radius_m": 6.0
    },
    {
      "id": "02-R-church",
      "kind": "street",
      "road_class": "dirt_access",
      "width_m": 3.6,
      "polyline_m": [
        [
          147,
          550
        ],
        [
          143,
          563
        ],
        [
          143,
          578
        ]
      ],
      "rotation_deg": null,
      "notes": "Extends the old dead-end to the church south forecourt.",
      "external_exception": false,
      "junction_radius_m": 4.0
    },
    {
      "id": "02-R-field09",
      "kind": "street",
      "road_class": "farm_track",
      "width_m": 3.6,
      "polyline_m": [
        [
          235,
          394
        ],
        [
          220,
          396
        ],
        [
          208,
          400
        ]
      ],
      "rotation_deg": null,
      "notes": "Ends at the south-east field approach, outside the cultivated polygon.",
      "external_exception": false,
      "junction_radius_m": 4.0
    },
    {
      "id": "02-R-tower",
      "kind": "street",
      "road_class": "service_track",
      "width_m": 3.6,
      "polyline_m": [
        [
          350,
          482
        ],
        [
          343,
          497
        ],
        [
          344,
          508
        ],
        [
          338,
          513
        ]
      ],
      "rotation_deg": null,
      "notes": "Curves to the south side of the preserved water tower.",
      "external_exception": false,
      "junction_radius_m": 4.0
    },
    {
      "id": "02-R-barn",
      "kind": "street",
      "road_class": "dirt_access",
      "width_m": 4.2,
      "polyline_m": [
        [
          271,
          540
        ],
        [
          271,
          545.8
        ]
      ],
      "rotation_deg": null,
      "notes": "Short loading approach to the barn south apron.",
      "external_exception": false,
      "junction_radius_m": 6.0
    },
    {
      "id": "02-R-shop",
      "kind": "street",
      "road_class": "dirt_access",
      "width_m": 3.6,
      "polyline_m": [
        [
          271,
          491
        ],
        [
          270.3,
          495.8
        ]
      ],
      "rotation_deg": null,
      "notes": "Short shop entrance approach; pedestrian forecourt remains distinct.",
      "external_exception": false,
      "junction_radius_m": 4.0
    }
  ],
  "objects": [
    {
      "id": "02-A-CHURCH",
      "kind": "church",
      "centre_m": [
        143.6,
        592.3
      ],
      "size_m": [
        18.4,
        20.6
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          134.4,
          582.0
        ],
        [
          152.8,
          582.0
        ],
        [
          152.8,
          602.6
        ],
        [
          134.4,
          602.6
        ]
      ],
      "notes": "Preserve existing outline exactly; north edge 602.6 m is 2.8 m outside supplied district bbox. Do not shrink or move it.",
      "hard_obstacle": true,
      "boundary_exception": "Existing locked church; explicit disclosed source contradiction.",
      "accessible_interior": false
    },
    {
      "id": "02-A-BASE",
      "kind": "grandfather_base",
      "centre_m": [
        166,
        520
      ],
      "size_m": [
        10,
        7.5
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          161.0,
          516.25
        ],
        [
          171.0,
          516.25
        ],
        [
          171.0,
          523.75
        ],
        [
          161.0,
          523.75
        ]
      ],
      "notes": "Existing base marker only. Owner will design all base furnishing/interior separately; keep location and access.",
      "hard_obstacle": true,
      "accessible_interior": true,
      "separate_design": true
    },
    {
      "id": "02-A-BASE-PAD",
      "kind": "van_loading_pad",
      "centre_m": [
        186.4,
        511.1
      ],
      "size_m": [
        9.2,
        9.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          181.8,
          506.5
        ],
        [
          191.0,
          506.5
        ],
        [
          191.0,
          515.7
        ],
        [
          181.8,
          515.7
        ]
      ],
      "notes": "Preserved parking/loading pad; flat gravel; reversing allowed, not claimed as full U-turn area.",
      "hard_obstacle": false,
      "clear_area": true
    },
    {
      "id": "02-A-BASE-TURN",
      "kind": "manoeuvring_apron",
      "centre_m": [
        186.4,
        511.1
      ],
      "size_m": [
        15,
        14
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          178.9,
          504.1
        ],
        [
          193.9,
          504.1
        ],
        [
          193.9,
          518.1
        ],
        [
          178.9,
          518.1
        ]
      ],
      "notes": "Open extension around fixed pad; broad multi-point manoeuvre, validate turning in Unity.",
      "hard_obstacle": false,
      "clear_area": true
    },
    {
      "id": "02-A-BARN",
      "kind": "communal_barn",
      "centre_m": [
        273.6,
        555
      ],
      "size_m": [
        18,
        10
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          264.6,
          550.0
        ],
        [
          282.6,
          550.0
        ],
        [
          282.6,
          560.0
        ],
        [
          264.6,
          560.0
        ]
      ],
      "notes": "Preserve former cowshed structure and position. No cows in v03; communal farm storage with nearby pigs/chickens.",
      "hard_obstacle": true,
      "accessible_interior": true
    },
    {
      "id": "02-A-HAY",
      "kind": "hay_shelter",
      "centre_m": [
        293,
        556
      ],
      "size_m": [
        6,
        10
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          290.0,
          551.0
        ],
        [
          296.0,
          551.0
        ],
        [
          296.0,
          561.0
        ],
        [
          290.0,
          561.0
        ]
      ],
      "notes": "Preserve anchor; broad roof with usable open sides.",
      "hard_obstacle": true
    },
    {
      "id": "02-A-PEN",
      "kind": "small_pig_pen",
      "centre_m": [
        273.6,
        565.6
      ],
      "size_m": [
        14,
        7
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          266.6,
          562.1
        ],
        [
          280.6,
          562.1
        ],
        [
          280.6,
          569.1
        ],
        [
          266.6,
          569.1
        ]
      ],
      "notes": "Former cow-pen anchor reused for pigs. Low livestock rails only here; no fences between house plots.",
      "hard_obstacle": true,
      "local_fence_only": true
    },
    {
      "id": "02-A-BARN-PAD",
      "kind": "van_loading_pad",
      "centre_m": [
        273.6,
        547.5
      ],
      "size_m": [
        15,
        4.5
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          266.1,
          545.25
        ],
        [
          281.1,
          545.25
        ],
        [
          281.1,
          549.75
        ],
        [
          266.1,
          549.75
        ]
      ],
      "notes": "Flat barn apron; preserve door-to-van passage.",
      "hard_obstacle": false,
      "clear_area": true
    },
    {
      "id": "02-A-SHOP",
      "kind": "village_shop",
      "centre_m": [
        270.3,
        502.5
      ],
      "size_m": [
        12,
        8
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          264.3,
          498.5
        ],
        [
          276.3,
          498.5
        ],
        [
          276.3,
          506.5
        ],
        [
          264.3,
          506.5
        ]
      ],
      "notes": "Physical open entrance facing south; readable porch and shop sign; no scene transition.",
      "hard_obstacle": true,
      "accessible_interior": true
    },
    {
      "id": "02-A-SQUARE",
      "kind": "meeting_forecourt",
      "centre_m": [
        250,
        507.5
      ],
      "size_m": [
        11,
        9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          244.5,
          503.0
        ],
        [
          255.5,
          503.0
        ],
        [
          255.5,
          512.0
        ],
        [
          244.5,
          512.0
        ]
      ],
      "notes": "Preserved plaza; obelisk and benches, no football or dance venue.",
      "hard_obstacle": false,
      "clear_area": true
    },
    {
      "id": "02-A-OBELISK",
      "kind": "obelisk",
      "centre_m": [
        249,
        509
      ],
      "size_m": [
        1.2,
        1.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          248.4,
          508.4
        ],
        [
          249.6,
          508.4
        ],
        [
          249.6,
          509.6
        ],
        [
          248.4,
          509.6
        ]
      ],
      "notes": "Small rural marker, not a dominant monument.",
      "hard_obstacle": true,
      "parent": "02-A-SQUARE"
    },
    {
      "id": "02-A-BENCH1",
      "kind": "bench",
      "centre_m": [
        245.8,
        510.2
      ],
      "size_m": [
        1.8,
        0.5
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          244.9,
          509.95
        ],
        [
          246.7,
          509.95
        ],
        [
          246.7,
          510.45
        ],
        [
          244.9,
          510.45
        ]
      ],
      "notes": "A seat facing plaza.",
      "hard_obstacle": true,
      "parent": "02-A-SQUARE"
    },
    {
      "id": "02-A-BENCH2",
      "kind": "bench",
      "centre_m": [
        253.5,
        510.2
      ],
      "size_m": [
        1.8,
        0.5
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          252.6,
          509.95
        ],
        [
          254.4,
          509.95
        ],
        [
          254.4,
          510.45
        ],
        [
          252.6,
          510.45
        ]
      ],
      "notes": "Offset second seat; clear walking route.",
      "hard_obstacle": true,
      "parent": "02-A-SQUARE"
    },
    {
      "id": "02-A-SIGN",
      "kind": "shop_notice_board",
      "centre_m": [
        261.8,
        505
      ],
      "size_m": [
        1.5,
        0.25
      ],
      "rotation_deg": 90,
      "polygon_m": [
        [
          261.925,
          504.25
        ],
        [
          261.925,
          505.75
        ],
        [
          261.675,
          505.75
        ],
        [
          261.675,
          504.25
        ]
      ],
      "notes": "Paper notes, opening hours and old notices.",
      "hard_obstacle": true
    },
    {
      "id": "02-A-TOWER",
      "kind": "water_tower",
      "centre_m": [
        338.4,
        517.8
      ],
      "size_m": [
        3.8,
        3.8
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          336.5,
          515.9
        ],
        [
          340.3,
          515.9
        ],
        [
          340.3,
          519.7
        ],
        [
          336.5,
          519.7
        ]
      ],
      "notes": "Rozhnovsky tower; about 12 m tall; circular base inside stated footprint.",
      "hard_obstacle": true,
      "height_m": 12
    },
    {
      "id": "02-A-WELL",
      "kind": "old_well",
      "centre_m": [
        217.9,
        472.7
      ],
      "size_m": [
        0.75,
        0.75
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          218.275,
          472.7
        ],
        [
          218.2622,
          472.7971
        ],
        [
          218.2248,
          472.8875
        ],
        [
          218.1652,
          472.9652
        ],
        [
          218.0875,
          473.0248
        ],
        [
          217.9971,
          473.0622
        ],
        [
          217.9,
          473.075
        ],
        [
          217.8029,
          473.0622
        ],
        [
          217.7125,
          473.0248
        ],
        [
          217.6348,
          472.9652
        ],
        [
          217.5752,
          472.8875
        ],
        [
          217.5378,
          472.7971
        ],
        [
          217.525,
          472.7
        ],
        [
          217.5378,
          472.6029
        ],
        [
          217.5752,
          472.5125
        ],
        [
          217.6348,
          472.4348
        ],
        [
          217.7125,
          472.3752
        ],
        [
          217.8029,
          472.3378
        ],
        [
          217.9,
          472.325
        ],
        [
          217.9971,
          472.3378
        ],
        [
          218.0875,
          472.3752
        ],
        [
          218.1652,
          472.4348
        ],
        [
          218.2248,
          472.5125
        ],
        [
          218.2622,
          472.6029
        ]
      ],
      "notes": "Small circular masonry ring on actual dry bank. Decorative roof can overhang water; no ground collider for roof.",
      "hard_obstacle": true
    },
    {
      "id": "02-A-POND",
      "kind": "pond",
      "polygon_m": [
        [
          177.2,
          477.4
        ],
        [
          177.48,
          477.67
        ],
        [
          177.8,
          478.01
        ],
        [
          178.14,
          478.42
        ],
        [
          178.52,
          478.89
        ],
        [
          178.92,
          479.39
        ],
        [
          179.36,
          479.93
        ],
        [
          179.84,
          480.49
        ],
        [
          180.35,
          481.06
        ],
        [
          180.9,
          481.63
        ],
        [
          181.48,
          482.18
        ],
        [
          182.1,
          482.71
        ],
        [
          182.76,
          483.21
        ],
        [
          183.46,
          483.65
        ],
        [
          184.2,
          484.04
        ],
        [
          184.98,
          484.36
        ],
        [
          185.8,
          484.6
        ],
        [
          186.69,
          484.78
        ],
        [
          187.67,
          484.93
        ],
        [
          188.73,
          485.04
        ],
        [
          189.85,
          485.13
        ],
        [
          191.03,
          485.18
        ],
        [
          192.25,
          485.2
        ],
        [
          193.49,
          485.19
        ],
        [
          194.76,
          485.15
        ],
        [
          196.04,
          485.07
        ],
        [
          197.31,
          484.97
        ],
        [
          198.56,
          484.82
        ],
        [
          199.79,
          484.65
        ],
        [
          200.98,
          484.44
        ],
        [
          202.12,
          484.19
        ],
        [
          203.2,
          483.91
        ],
        [
          204.2,
          483.6
        ],
        [
          205.16,
          483.24
        ],
        [
          206.11,
          482.83
        ],
        [
          207.04,
          482.37
        ],
        [
          207.96,
          481.87
        ],
        [
          208.86,
          481.32
        ],
        [
          209.74,
          480.74
        ],
        [
          210.59,
          480.14
        ],
        [
          211.41,
          479.5
        ],
        [
          212.2,
          478.84
        ],
        [
          212.96,
          478.17
        ],
        [
          213.68,
          477.48
        ],
        [
          214.36,
          476.78
        ],
        [
          214.99,
          476.08
        ],
        [
          215.58,
          475.38
        ],
        [
          216.12,
          474.69
        ],
        [
          216.6,
          474.0
        ],
        [
          217.04,
          473.31
        ],
        [
          217.44,
          472.59
        ],
        [
          217.8,
          471.84
        ],
        [
          218.12,
          471.09
        ],
        [
          218.4,
          470.31
        ],
        [
          218.65,
          469.53
        ],
        [
          218.85,
          468.73
        ],
        [
          219.01,
          467.94
        ],
        [
          219.13,
          467.14
        ],
        [
          219.21,
          466.34
        ],
        [
          219.25,
          465.55
        ],
        [
          219.25,
          464.77
        ],
        [
          219.2,
          464.0
        ],
        [
          219.11,
          463.25
        ],
        [
          218.98,
          462.51
        ],
        [
          218.8,
          461.8
        ],
        [
          218.57,
          461.1
        ],
        [
          218.29,
          460.38
        ],
        [
          217.96,
          459.67
        ],
        [
          217.59,
          458.95
        ],
        [
          217.17,
          458.24
        ],
        [
          216.7,
          457.53
        ],
        [
          216.19,
          456.83
        ],
        [
          215.65,
          456.15
        ],
        [
          215.07,
          455.48
        ],
        [
          214.46,
          454.84
        ],
        [
          213.81,
          454.22
        ],
        [
          213.14,
          453.62
        ],
        [
          212.44,
          453.06
        ],
        [
          211.71,
          452.54
        ],
        [
          210.97,
          452.05
        ],
        [
          210.2,
          451.6
        ],
        [
          209.39,
          451.18
        ],
        [
          208.53,
          450.78
        ],
        [
          207.61,
          450.39
        ],
        [
          206.64,
          450.02
        ],
        [
          205.64,
          449.68
        ],
        [
          204.6,
          449.36
        ],
        [
          203.54,
          449.07
        ],
        [
          202.46,
          448.81
        ],
        [
          201.37,
          448.59
        ],
        [
          200.28,
          448.4
        ],
        [
          199.18,
          448.25
        ],
        [
          198.1,
          448.15
        ],
        [
          197.03,
          448.08
        ],
        [
          195.99,
          448.07
        ],
        [
          194.98,
          448.11
        ],
        [
          194.0,
          448.2
        ],
        [
          193.03,
          448.35
        ],
        [
          192.05,
          448.56
        ],
        [
          191.06,
          448.83
        ],
        [
          190.07,
          449.15
        ],
        [
          189.07,
          449.51
        ],
        [
          188.08,
          449.92
        ],
        [
          187.1,
          450.37
        ],
        [
          186.14,
          450.85
        ],
        [
          185.19,
          451.36
        ],
        [
          184.28,
          451.9
        ],
        [
          183.39,
          452.45
        ],
        [
          182.54,
          453.03
        ],
        [
          181.73,
          453.61
        ],
        [
          180.97,
          454.21
        ],
        [
          180.26,
          454.8
        ],
        [
          179.6,
          455.4
        ],
        [
          178.99,
          456.01
        ],
        [
          178.42,
          456.67
        ],
        [
          177.88,
          457.35
        ],
        [
          177.38,
          458.06
        ],
        [
          176.9,
          458.8
        ],
        [
          176.47,
          459.56
        ],
        [
          176.07,
          460.33
        ],
        [
          175.7,
          461.11
        ],
        [
          175.37,
          461.9
        ],
        [
          175.07,
          462.69
        ],
        [
          174.8,
          463.48
        ],
        [
          174.58,
          464.25
        ],
        [
          174.38,
          465.02
        ],
        [
          174.22,
          465.77
        ],
        [
          174.09,
          466.5
        ],
        [
          174.0,
          467.2
        ],
        [
          173.96,
          467.9
        ],
        [
          174.0,
          468.62
        ],
        [
          174.1,
          469.36
        ],
        [
          174.26,
          470.1
        ],
        [
          174.46,
          470.85
        ],
        [
          174.7,
          471.59
        ],
        [
          174.96,
          472.32
        ],
        [
          175.25,
          473.04
        ],
        [
          175.55,
          473.73
        ],
        [
          175.85,
          474.39
        ],
        [
          176.14,
          475.02
        ],
        [
          176.42,
          475.6
        ],
        [
          176.67,
          476.14
        ],
        [
          176.89,
          476.62
        ],
        [
          177.07,
          477.05
        ],
        [
          177.2,
          477.4
        ]
      ],
      "rotation_deg": 0,
      "notes": "Exact source village pond polygon, not its rectangular bbox. Water blocks van travel."
    },
    {
      "id": "02-A-FIELD1",
      "kind": "cultivated_field",
      "centre_m": [
        348.5,
        570.5
      ],
      "size_m": [
        39,
        41
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          329.0,
          550.0
        ],
        [
          368.0,
          550.0
        ],
        [
          368.0,
          591.0
        ],
        [
          329.0,
          591.0
        ]
      ],
      "notes": "Preserve established cultivated bounds; no houses or road surfaces placed inside.",
      "hard_obstacle": false
    },
    {
      "id": "02-A-FIELD2",
      "kind": "cultivated_field",
      "centre_m": [
        173.5,
        408.5
      ],
      "size_m": [
        59,
        39
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          144.0,
          389.0
        ],
        [
          203.0,
          389.0
        ],
        [
          203.0,
          428.0
        ],
        [
          144.0,
          428.0
        ]
      ],
      "notes": "Preserve established cultivated bounds; no houses or road surfaces placed inside.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-CEMETERY",
      "kind": "cemetery",
      "centre_m": [
        174,
        588
      ],
      "size_m": [
        23,
        15
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          162.5,
          580.5
        ],
        [
          185.5,
          580.5
        ],
        [
          185.5,
          595.5
        ],
        [
          162.5,
          595.5
        ]
      ],
      "notes": "Placed east of church, wholly inside district; no new NPC category or quest implied.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-00",
      "kind": "grave",
      "centre_m": [
        165.4,
        583.2
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          164.9,
          582.25
        ],
        [
          165.9,
          582.25
        ],
        [
          165.9,
          584.15
        ],
        [
          164.9,
          584.15
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-01",
      "kind": "grave",
      "centre_m": [
        169.9,
        583.2
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          169.4,
          582.25
        ],
        [
          170.4,
          582.25
        ],
        [
          170.4,
          584.15
        ],
        [
          169.4,
          584.15
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-02",
      "kind": "grave",
      "centre_m": [
        174.4,
        583.2
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          173.9,
          582.25
        ],
        [
          174.9,
          582.25
        ],
        [
          174.9,
          584.15
        ],
        [
          173.9,
          584.15
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-03",
      "kind": "grave",
      "centre_m": [
        178.9,
        583.2
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          178.4,
          582.25
        ],
        [
          179.4,
          582.25
        ],
        [
          179.4,
          584.15
        ],
        [
          178.4,
          584.15
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-04",
      "kind": "grave",
      "centre_m": [
        165.4,
        586.5
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          164.9,
          585.55
        ],
        [
          165.9,
          585.55
        ],
        [
          165.9,
          587.45
        ],
        [
          164.9,
          587.45
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-05",
      "kind": "grave",
      "centre_m": [
        169.9,
        586.5
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          169.4,
          585.55
        ],
        [
          170.4,
          585.55
        ],
        [
          170.4,
          587.45
        ],
        [
          169.4,
          587.45
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-06",
      "kind": "grave",
      "centre_m": [
        174.4,
        586.5
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          173.9,
          585.55
        ],
        [
          174.9,
          585.55
        ],
        [
          174.9,
          587.45
        ],
        [
          173.9,
          587.45
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-07",
      "kind": "grave",
      "centre_m": [
        178.9,
        586.5
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          178.4,
          585.55
        ],
        [
          179.4,
          585.55
        ],
        [
          179.4,
          587.45
        ],
        [
          178.4,
          587.45
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-08",
      "kind": "grave",
      "centre_m": [
        165.4,
        589.8000000000001
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          164.9,
          588.85
        ],
        [
          165.9,
          588.85
        ],
        [
          165.9,
          590.75
        ],
        [
          164.9,
          590.75
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-09",
      "kind": "grave",
      "centre_m": [
        169.9,
        589.8000000000001
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          169.4,
          588.85
        ],
        [
          170.4,
          588.85
        ],
        [
          170.4,
          590.75
        ],
        [
          169.4,
          590.75
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-10",
      "kind": "grave",
      "centre_m": [
        174.4,
        589.8000000000001
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          173.9,
          588.85
        ],
        [
          174.9,
          588.85
        ],
        [
          174.9,
          590.75
        ],
        [
          173.9,
          590.75
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-GRAVE-11",
      "kind": "grave",
      "centre_m": [
        178.9,
        589.8000000000001
      ],
      "size_m": [
        1,
        1.9
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          178.4,
          588.85
        ],
        [
          179.4,
          588.85
        ],
        [
          179.4,
          590.75
        ],
        [
          178.4,
          590.75
        ]
      ],
      "notes": "Small cemetery rows; low markers, clear paths.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-ORCHARD",
      "kind": "orchard",
      "centre_m": [
        221.5,
        583.5
      ],
      "size_m": [
        45,
        25
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          199.0,
          571.0
        ],
        [
          244.0,
          571.0
        ],
        [
          244.0,
          596.0
        ],
        [
          199.0,
          596.0
        ]
      ],
      "notes": "Small old orchard; productive trees with irregular gaps, no apiary.",
      "hard_obstacle": false
    },
    {
      "id": "02-U-TRACTOR1",
      "kind": "parked_tractor",
      "centre_m": [
        286,
        570
      ],
      "size_m": [
        4,
        2.2
      ],
      "rotation_deg": -10,
      "polygon_m": [
        [
          283.839,
          569.264
        ],
        [
          287.779,
          568.569
        ],
        [
          288.161,
          570.736
        ],
        [
          284.221,
          571.431
        ]
      ],
      "notes": "Ordinary parked agricultural tractor; no dedicated workshop.",
      "hard_obstacle": true
    },
    {
      "id": "02-U-TRACTOR2",
      "kind": "parked_tractor",
      "centre_m": [
        319,
        558
      ],
      "size_m": [
        4,
        2.2
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          317.272,
          556.508
        ],
        [
          321.185,
          557.34
        ],
        [
          320.728,
          559.492
        ],
        [
          316.815,
          558.66
        ]
      ],
      "notes": "Second tractor on grass outside field; keep field approach.",
      "hard_obstacle": true
    },
    {
      "id": "02-U-TRAILER",
      "kind": "farm_trailer",
      "centre_m": [
        319,
        564
      ],
      "size_m": [
        4,
        2.1
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          317.262,
          562.557
        ],
        [
          321.175,
          563.389
        ],
        [
          320.738,
          565.443
        ],
        [
          316.825,
          564.611
        ]
      ],
      "notes": "Occasional farm attachment, no repair area.",
      "hard_obstacle": true
    },
    {
      "id": "02-U-STOP",
      "kind": "bus_stop",
      "centre_m": [
        366,
        481
      ],
      "size_m": [
        3.4,
        1.5
      ],
      "rotation_deg": -22,
      "polygon_m": [
        [
          364.143,
          480.941
        ],
        [
          367.295,
          479.668
        ],
        [
          367.857,
          481.059
        ],
        [
          364.705,
          482.332
        ]
      ],
      "notes": "Within district beside lower approach; no abandoned kiosk.",
      "hard_obstacle": true
    },
    {
      "id": "02-U-WATER1",
      "kind": "standpipe",
      "centre_m": [
        239,
        508
      ],
      "size_m": [
        0.4,
        0.4
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          238.8,
          507.8
        ],
        [
          239.2,
          507.8
        ],
        [
          239.2,
          508.2
        ],
        [
          238.8,
          508.2
        ]
      ],
      "notes": "Shared water tap near street, moved off the new driving surface.",
      "hard_obstacle": true
    },
    {
      "id": "02-U-WATER2",
      "kind": "standpipe",
      "centre_m": [
        321,
        477
      ],
      "size_m": [
        0.4,
        0.4
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          320.8,
          476.8
        ],
        [
          321.2,
          476.8
        ],
        [
          321.2,
          477.2
        ],
        [
          320.8,
          477.2
        ]
      ],
      "notes": "Small tap by eastern houses.",
      "hard_obstacle": true
    },
    {
      "id": "02-U-WASTE1",
      "kind": "shared_bin",
      "centre_m": [
        222,
        520
      ],
      "size_m": [
        1,
        0.8
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          221.5,
          519.6
        ],
        [
          222.5,
          519.6
        ],
        [
          222.5,
          520.4
        ],
        [
          221.5,
          520.4
        ]
      ],
      "notes": "Small practical refuse spot; not a dump district.",
      "hard_obstacle": true
    },
    {
      "id": "02-U-WASTE2",
      "kind": "shared_bin",
      "centre_m": [
        338,
        430
      ],
      "size_m": [
        1,
        0.8
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          337.5,
          429.6
        ],
        [
          338.5,
          429.6
        ],
        [
          338.5,
          430.4
        ],
        [
          337.5,
          430.4
        ]
      ],
      "notes": "Second refuse collection point.",
      "hard_obstacle": true
    },
    {
      "id": "02-U-TRANSFORMER",
      "kind": "transformer_box",
      "centre_m": [
        296,
        527
      ],
      "size_m": [
        2.5,
        2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          294.75,
          526.0
        ],
        [
          297.25,
          526.0
        ],
        [
          297.25,
          528.0
        ],
        [
          294.75,
          528.0
        ]
      ],
      "notes": "Service box with pole connection; not a new gameplay system.",
      "hard_obstacle": true
    },
    {
      "id": "02-FISH-PATH",
      "kind": "pedestrian_path",
      "polyline_m": [
        [
          364,
          466
        ],
        [
          369,
          459
        ],
        [
          382,
          453
        ],
        [
          397,
          451
        ],
        [
          408,
          451
        ]
      ],
      "width_m": 1.8,
      "rotation_deg": null,
      "notes": "Shared-world river access exception. Cross existing bypass at grade; do not cut a new road or regenerate river. Place landward dock abutment on surveyed west bank.",
      "boundary_exception": "Requested fishing access beyond district."
    },
    {
      "id": "02-FISH-DOCK",
      "kind": "fishing_platform",
      "centre_m": [
        411,
        451
      ],
      "size_m": [
        5,
        2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          408.5,
          450.0
        ],
        [
          413.5,
          450.0
        ],
        [
          413.5,
          452.0
        ],
        [
          408.5,
          452.0
        ]
      ],
      "notes": "River anchor. Final bank abutment is a 3D integration check; platform may project over water.",
      "hard_obstacle": false,
      "boundary_exception": "Requested fishing access beyond district."
    },
    {
      "id": "02-FISH-BOAT",
      "kind": "upturned_boat",
      "centre_m": [
        404,
        456
      ],
      "size_m": [
        3.8,
        1.5
      ],
      "rotation_deg": -18,
      "polygon_m": [
        [
          401.961,
          455.874
        ],
        [
          405.575,
          454.7
        ],
        [
          406.039,
          456.126
        ],
        [
          402.425,
          457.3
        ]
      ],
      "notes": "Bank-dressing outside bypass traffic envelope; confirm river dry-bank location.",
      "hard_obstacle": true,
      "boundary_exception": "Requested fishing access beyond district."
    },
    {
      "id": "02-FISH-NETS",
      "kind": "fishing_nets",
      "centre_m": [
        405,
        449
      ],
      "size_m": [
        2.2,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          403.9,
          448.85
        ],
        [
          406.1,
          448.85
        ],
        [
          406.1,
          449.15
        ],
        [
          403.9,
          449.15
        ]
      ],
      "notes": "Nets on two stakes; line visuals have no blocking collider.",
      "hard_obstacle": false,
      "boundary_exception": "Requested fishing access beyond district."
    },
    {
      "id": "02-HAY-ROLL-01",
      "kind": "round_hay_bale",
      "centre_m": [
        303,
        568
      ],
      "size_m": [
        1.6,
        1.3
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          302.353,
          567.198
        ],
        [
          303.918,
          567.531
        ],
        [
          303.647,
          568.802
        ],
        [
          302.082,
          568.469
        ]
      ],
      "notes": "Mandatory rolled cylinder like owner photo; spiral end faces, coarse muted straw; lying on curved side. Not a rectangular bundle.",
      "hard_obstacle": true,
      "parent": "02-A-HAY",
      "height_m": 1.6,
      "cylinder_axis": "local_y",
      "axial_length_m": 1.3,
      "diameter_m": 1.6,
      "physics_status": "Static layout collision only; rolling/pushing mechanics not decided."
    },
    {
      "id": "02-HAY-ROLL-02",
      "kind": "round_hay_bale",
      "centre_m": [
        306,
        571
      ],
      "size_m": [
        1.6,
        1.3
      ],
      "rotation_deg": -8,
      "polygon_m": [
        [
          305.117,
          570.468
        ],
        [
          306.702,
          570.245
        ],
        [
          306.883,
          571.532
        ],
        [
          305.298,
          571.755
        ]
      ],
      "notes": "Mandatory rolled cylinder like owner photo; spiral end faces, coarse muted straw; lying on curved side. Not a rectangular bundle.",
      "hard_obstacle": true,
      "parent": "02-A-HAY",
      "height_m": 1.6,
      "cylinder_axis": "local_y",
      "axial_length_m": 1.3,
      "diameter_m": 1.6,
      "physics_status": "Static layout collision only; rolling/pushing mechanics not decided."
    },
    {
      "id": "02-HAY-ROLL-03",
      "kind": "round_hay_bale",
      "centre_m": [
        324,
        582
      ],
      "size_m": [
        1.6,
        1.3
      ],
      "rotation_deg": 19,
      "polygon_m": [
        [
          323.455,
          581.125
        ],
        [
          324.968,
          581.646
        ],
        [
          324.545,
          582.875
        ],
        [
          323.032,
          582.354
        ]
      ],
      "notes": "Mandatory rolled cylinder like owner photo; spiral end faces, coarse muted straw; lying on curved side. Not a rectangular bundle.",
      "hard_obstacle": true,
      "parent": "02-A-FIELD1",
      "height_m": 1.6,
      "cylinder_axis": "local_y",
      "axial_length_m": 1.3,
      "diameter_m": 1.6,
      "physics_status": "Static layout collision only; rolling/pushing mechanics not decided."
    },
    {
      "id": "02-HAY-ROLL-04",
      "kind": "round_hay_bale",
      "centre_m": [
        207,
        415
      ],
      "size_m": [
        1.6,
        1.3
      ],
      "rotation_deg": -12,
      "polygon_m": [
        [
          206.082,
          414.531
        ],
        [
          207.647,
          414.198
        ],
        [
          207.918,
          415.469
        ],
        [
          206.353,
          415.802
        ]
      ],
      "notes": "Mandatory rolled cylinder like owner photo; spiral end faces, coarse muted straw; lying on curved side. Not a rectangular bundle.",
      "hard_obstacle": true,
      "parent": "02-A-FIELD2",
      "height_m": 1.6,
      "cylinder_axis": "local_y",
      "axial_length_m": 1.3,
      "diameter_m": 1.6,
      "physics_status": "Static layout collision only; rolling/pushing mechanics not decided."
    },
    {
      "id": "02-HAY-ROLL-05",
      "kind": "round_hay_bale",
      "centre_m": [
        207,
        422
      ],
      "size_m": [
        1.6,
        1.3
      ],
      "rotation_deg": 7,
      "polygon_m": [
        [
          206.285,
          421.257
        ],
        [
          207.873,
          421.452
        ],
        [
          207.715,
          422.743
        ],
        [
          206.127,
          422.548
        ]
      ],
      "notes": "Mandatory rolled cylinder like owner photo; spiral end faces, coarse muted straw; lying on curved side. Not a rectangular bundle.",
      "hard_obstacle": true,
      "parent": "02-A-FIELD2",
      "height_m": 1.6,
      "cylinder_axis": "local_y",
      "axial_length_m": 1.3,
      "diameter_m": 1.6,
      "physics_status": "Static layout collision only; rolling/pushing mechanics not decided."
    },
    {
      "id": "02-H01",
      "kind": "house",
      "centre_m": [
        160,
        562
      ],
      "size_m": [
        8,
        6
      ],
      "rotation_deg": 8,
      "polygon_m": [
        [
          156.456,
          558.473
        ],
        [
          164.379,
          559.586
        ],
        [
          163.544,
          565.527
        ],
        [
          155.621,
          564.414
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_log",
      "floors": 1,
      "roof_material": "faded sheet metal with local repairs",
      "owner": "old couple; flowers, firewood",
      "yard_profile": "elder",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        160.418,
        559.029
      ],
      "front_face": "south",
      "street_connection": "02-R-main"
    },
    {
      "id": "02-H02",
      "kind": "house",
      "centre_m": [
        181,
        562
      ],
      "size_m": [
        7,
        9
      ],
      "rotation_deg": -6,
      "polygon_m": [
        [
          177.049,
          557.891
        ],
        [
          184.01,
          557.159
        ],
        [
          184.951,
          566.109
        ],
        [
          177.99,
          566.841
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_board",
      "floors": 1,
      "roof_material": "weathered corrugated metal",
      "owner": "vegetable grower; working beds",
      "yard_profile": "gardener",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        180.53,
        557.525
      ],
      "front_face": "south",
      "street_connection": "02-R-main"
    },
    {
      "id": "02-H03",
      "kind": "house",
      "centre_m": [
        199,
        560
      ],
      "size_m": [
        8,
        7
      ],
      "rotation_deg": 5,
      "polygon_m": [
        [
          195.32,
          556.165
        ],
        [
          203.29,
          556.862
        ],
        [
          202.68,
          563.835
        ],
        [
          194.71,
          563.138
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "tin_timber",
      "floors": 1,
      "roof_material": "weathered corrugated metal",
      "owner": "poultry keeper; chickens",
      "yard_profile": "poultry",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        199.305,
        556.513
      ],
      "front_face": "south",
      "street_connection": "02-R-main"
    },
    {
      "id": "02-H04",
      "kind": "house",
      "centre_m": [
        196,
        539
      ],
      "size_m": [
        9,
        7
      ],
      "rotation_deg": -10,
      "polygon_m": [
        [
          190.961,
          536.335
        ],
        [
          199.824,
          534.772
        ],
        [
          201.039,
          541.665
        ],
        [
          192.176,
          543.228
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_log",
      "floors": 1,
      "roof_material": "faded sheet metal with local repairs",
      "owner": "frugal household; stored timber",
      "yard_profile": "wood",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        196.608,
        542.447
      ],
      "front_face": "north",
      "street_connection": "02-R-main"
    },
    {
      "id": "02-H05",
      "kind": "house",
      "centre_m": [
        211,
        523
      ],
      "size_m": [
        8,
        6
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          207.711,
          519.234
        ],
        [
          215.536,
          520.897
        ],
        [
          214.289,
          526.766
        ],
        [
          206.464,
          525.103
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_board",
      "floors": 1,
      "roof_material": "weathered corrugated metal",
      "owner": "pig keeper; trough and small shelter",
      "yard_profile": "pig",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        214.913,
        523.832
      ],
      "front_face": "east",
      "street_connection": "02-R-main"
    },
    {
      "id": "02-H06",
      "kind": "house",
      "centre_m": [
        245,
        557
      ],
      "size_m": [
        9,
        7
      ],
      "rotation_deg": -4,
      "polygon_m": [
        [
          240.267,
          553.822
        ],
        [
          249.245,
          553.195
        ],
        [
          249.733,
          560.178
        ],
        [
          240.755,
          560.805
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_log",
      "floors": 1,
      "roof_material": "faded sheet metal with local repairs",
      "owner": "retired field worker; practical shed",
      "yard_profile": "elder",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        244.756,
        553.509
      ],
      "front_face": "south",
      "street_connection": "02-R-north"
    },
    {
      "id": "02-H07",
      "kind": "house",
      "centre_m": [
        251,
        577
      ],
      "size_m": [
        7,
        8
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          248.169,
          572.502
        ],
        [
          255.083,
          573.597
        ],
        [
          253.831,
          581.498
        ],
        [
          246.917,
          580.403
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "tin_timber",
      "floors": 1,
      "roof_material": "weathered corrugated metal",
      "owner": "fruit grower; crates and sparse flower bed",
      "yard_profile": "gardener",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        251.626,
        573.049
      ],
      "front_face": "south",
      "street_connection": "02-R-north"
    },
    {
      "id": "02-H08",
      "kind": "house",
      "centre_m": [
        307,
        559
      ],
      "size_m": [
        8,
        7
      ],
      "rotation_deg": 4,
      "polygon_m": [
        [
          303.254,
          555.229
        ],
        [
          311.234,
          555.788
        ],
        [
          310.746,
          562.771
        ],
        [
          302.766,
          562.212
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_board",
      "floors": 1,
      "roof_material": "weathered corrugated metal",
      "owner": "tractor driver; normal yard, no workshop",
      "yard_profile": "farm",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        307.244,
        555.509
      ],
      "front_face": "south",
      "street_connection": "02-R-north"
    },
    {
      "id": "02-H09",
      "kind": "house",
      "centre_m": [
        316,
        523
      ],
      "size_m": [
        8,
        7
      ],
      "rotation_deg": -7,
      "polygon_m": [
        [
          311.603,
          520.014
        ],
        [
          319.544,
          519.039
        ],
        [
          320.397,
          525.986
        ],
        [
          312.456,
          526.961
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "brick",
      "floors": 1,
      "roof_material": "muted weathered tile",
      "owner": "slightly better-kept household; vegetable beds",
      "yard_profile": "gardener",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        316.427,
        526.474
      ],
      "front_face": "north",
      "street_connection": "02-R-north"
    },
    {
      "id": "02-H10",
      "kind": "house",
      "centre_m": [
        284,
        516
      ],
      "size_m": [
        9,
        7
      ],
      "rotation_deg": 2,
      "polygon_m": [
        [
          279.625,
          512.345
        ],
        [
          288.619,
          512.659
        ],
        [
          288.375,
          519.655
        ],
        [
          279.381,
          519.341
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_log",
      "floors": 1,
      "roof_material": "faded sheet metal with local repairs",
      "owner": "older villager; shaded outdoor table",
      "yard_profile": "elder",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        283.878,
        519.498
      ],
      "front_face": "north",
      "street_connection": "02-R-north"
    },
    {
      "id": "02-H11",
      "kind": "house",
      "centre_m": [
        280,
        476
      ],
      "size_m": [
        8,
        6
      ],
      "rotation_deg": 10,
      "polygon_m": [
        [
          276.582,
          472.351
        ],
        [
          284.46,
          473.74
        ],
        [
          283.418,
          479.649
        ],
        [
          275.54,
          478.26
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_board",
      "floors": 1,
      "roof_material": "weathered corrugated metal",
      "owner": "poultry household by main street",
      "yard_profile": "poultry",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        279.479,
        478.954
      ],
      "front_face": "north",
      "street_connection": "02-R-main"
    },
    {
      "id": "02-H12",
      "kind": "house",
      "centre_m": [
        311,
        472
      ],
      "size_m": [
        8,
        9
      ],
      "rotation_deg": -4,
      "polygon_m": [
        [
          306.696,
          467.79
        ],
        [
          314.676,
          467.232
        ],
        [
          315.304,
          476.21
        ],
        [
          307.324,
          476.768
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "tin_timber",
      "floors": 1,
      "roof_material": "weathered corrugated metal",
      "owner": "pig-keeping household; muddy corner",
      "yard_profile": "pig",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        311.314,
        476.489
      ],
      "front_face": "north",
      "street_connection": "02-R-main"
    },
    {
      "id": "02-H13",
      "kind": "house",
      "centre_m": [
        352,
        462
      ],
      "size_m": [
        8,
        7
      ],
      "rotation_deg": -8,
      "polygon_m": [
        [
          347.552,
          459.091
        ],
        [
          355.474,
          457.977
        ],
        [
          356.448,
          464.909
        ],
        [
          348.526,
          466.023
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_log",
      "floors": 1,
      "roof_material": "faded sheet metal with local repairs",
      "owner": "fishing household; drying gear",
      "yard_profile": "fisher",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        352.487,
        465.466
      ],
      "front_face": "north",
      "street_connection": "02-R-main"
    },
    {
      "id": "02-H14",
      "kind": "house",
      "centre_m": [
        260,
        456
      ],
      "size_m": [
        7,
        9
      ],
      "rotation_deg": 7,
      "polygon_m": [
        [
          257.075,
          451.107
        ],
        [
          264.022,
          451.96
        ],
        [
          262.925,
          460.893
        ],
        [
          255.978,
          460.04
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_board",
      "floors": 1,
      "roof_material": "weathered corrugated metal",
      "owner": "busy vegetable grower; linen line",
      "yard_profile": "gardener",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        256.526,
        455.573
      ],
      "front_face": "west",
      "street_connection": "02-R-south"
    },
    {
      "id": "02-H15",
      "kind": "house",
      "centre_m": [
        272,
        435
      ],
      "size_m": [
        8,
        7
      ],
      "rotation_deg": -11,
      "polygon_m": [
        [
          267.406,
          432.328
        ],
        [
          275.259,
          430.801
        ],
        [
          276.594,
          437.672
        ],
        [
          268.741,
          439.199
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_log",
      "floors": 1,
      "roof_material": "faded sheet metal with local repairs",
      "owner": "wood-fired household; woodpile",
      "yard_profile": "wood",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        268.073,
        435.763
      ],
      "front_face": "west",
      "street_connection": "02-R-south"
    },
    {
      "id": "02-H16",
      "kind": "house",
      "centre_m": [
        286,
        412
      ],
      "size_m": [
        8,
        6
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          282.519,
          408.411
        ],
        [
          290.42,
          409.663
        ],
        [
          289.481,
          415.589
        ],
        [
          281.58,
          414.337
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "tin_timber",
      "floors": 1,
      "roof_material": "weathered corrugated metal",
      "owner": "poultry household; patchy maintenance",
      "yard_profile": "poultry",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        286.469,
        409.037
      ],
      "front_face": "south",
      "street_connection": "02-R-loop"
    },
    {
      "id": "02-H17",
      "kind": "house",
      "centre_m": [
        311,
        418
      ],
      "size_m": [
        8,
        7
      ],
      "rotation_deg": -9,
      "polygon_m": [
        [
          306.502,
          415.169
        ],
        [
          314.403,
          413.917
        ],
        [
          315.498,
          420.831
        ],
        [
          307.597,
          422.083
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "brick",
      "floors": 1,
      "roof_material": "muted weathered tile",
      "owner": "small pig-keeping household",
      "yard_profile": "pig",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        314.951,
        417.374
      ],
      "front_face": "east",
      "street_connection": "02-R-loop"
    },
    {
      "id": "02-H18",
      "kind": "house",
      "centre_m": [
        350,
        411
      ],
      "size_m": [
        8,
        6
      ],
      "rotation_deg": 8,
      "polygon_m": [
        [
          346.456,
          407.473
        ],
        [
          354.379,
          408.586
        ],
        [
          353.544,
          414.527
        ],
        [
          345.621,
          413.414
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "old_log",
      "floors": 1,
      "roof_material": "faded sheet metal with local repairs",
      "owner": "field worker; tools and vegetables",
      "yard_profile": "farm",
      "accessible_interior": false,
      "ordinary": true,
      "door_m": [
        346.039,
        410.443
      ],
      "front_face": "west",
      "street_connection": "02-R-loop"
    },
    {
      "id": "02-H19",
      "kind": "house",
      "centre_m": [
        215,
        432
      ],
      "size_m": [
        8,
        6
      ],
      "rotation_deg": -12,
      "polygon_m": [
        [
          210.464,
          429.897
        ],
        [
          218.289,
          428.234
        ],
        [
          219.536,
          434.103
        ],
        [
          211.711,
          435.766
        ]
      ],
      "notes": "Owner activity determines yard; never duplicate a whole yard kit.",
      "hard_obstacle": true,
      "house_type": "abandoned_board",
      "floors": 1,
      "roof_material": "faded sheet metal with local repairs",
      "owner": "unoccupied; roof damage and rusted small car",
      "yard_profile": "abandoned",
      "accessible_interior": true,
      "ordinary": false,
      "door_m": [
        218.913,
        431.168
      ],
      "front_face": "east",
      "street_connection": "02-R-south"
    },
    {
      "id": "02-H01-Y1",
      "kind": "flower_strip",
      "centre_m": [
        159.59,
        570.99
      ],
      "size_m": [
        3,
        1
      ],
      "rotation_deg": 8,
      "polygon_m": [
        [
          158.174,
          570.286
        ],
        [
          161.145,
          570.704
        ],
        [
          161.006,
          571.694
        ],
        [
          158.035,
          571.276
        ]
      ],
      "notes": "Belongs to 02-H01; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H01"
    },
    {
      "id": "02-H01-Y2",
      "kind": "shed",
      "centre_m": [
        154.51,
        569.13
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": 13,
      "polygon_m": [
        [
          153.33,
          567.575
        ],
        [
          156.253,
          568.249
        ],
        [
          155.69,
          570.685
        ],
        [
          152.767,
          570.011
        ]
      ],
      "notes": "Belongs to 02-H01; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H01"
    },
    {
      "id": "02-H01-Y3",
      "kind": "woodpile",
      "centre_m": [
        164.82,
        569.6
      ],
      "size_m": [
        2.5,
        1
      ],
      "rotation_deg": 8,
      "polygon_m": [
        [
          163.652,
          568.931
        ],
        [
          166.127,
          569.279
        ],
        [
          165.988,
          570.269
        ],
        [
          163.513,
          569.921
        ]
      ],
      "notes": "Belongs to 02-H01; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H01"
    },
    {
      "id": "02-H01-Y4",
      "kind": "outdoor_table",
      "centre_m": [
        151.41,
        564.69
      ],
      "size_m": [
        1.5,
        0.8
      ],
      "rotation_deg": 13,
      "polygon_m": [
        [
          150.769,
          564.132
        ],
        [
          152.231,
          564.469
        ],
        [
          152.051,
          565.248
        ],
        [
          150.589,
          564.911
        ]
      ],
      "notes": "Belongs to 02-H01; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H01"
    },
    {
      "id": "02-H02-Y1",
      "kind": "vegetable_garden",
      "centre_m": [
        179.69,
        570.9
      ],
      "size_m": [
        6,
        4
      ],
      "rotation_deg": -6,
      "polygon_m": [
        [
          176.497,
          569.225
        ],
        [
          182.465,
          568.597
        ],
        [
          182.883,
          572.575
        ],
        [
          176.915,
          573.203
        ]
      ],
      "notes": "Belongs to 02-H02; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H02"
    },
    {
      "id": "02-H02-Y2",
      "kind": "shed",
      "centre_m": [
        172.18,
        563.81
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": -1,
      "polygon_m": [
        [
          170.658,
          562.586
        ],
        [
          173.658,
          562.534
        ],
        [
          173.702,
          565.034
        ],
        [
          170.702,
          565.086
        ]
      ],
      "notes": "Belongs to 02-H02; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H02"
    },
    {
      "id": "02-H02-Y3",
      "kind": "clothesline",
      "centre_m": [
        188.92,
        566.28
      ],
      "size_m": [
        3.5,
        0.4
      ],
      "rotation_deg": -6,
      "polygon_m": [
        [
          187.159,
          566.264
        ],
        [
          190.64,
          565.898
        ],
        [
          190.681,
          566.296
        ],
        [
          187.2,
          566.662
        ]
      ],
      "notes": "Belongs to 02-H02; unfenced, keep routes through yard. Only supports/posts collide; line itself does not.",
      "hard_obstacle": false,
      "parent": "02-H02"
    },
    {
      "id": "02-H02-Y4",
      "kind": "water_barrel",
      "centre_m": [
        174.82,
        568.54
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": -1,
      "polygon_m": [
        [
          174.464,
          568.196
        ],
        [
          175.164,
          568.184
        ],
        [
          175.176,
          568.884
        ],
        [
          174.476,
          568.896
        ]
      ],
      "notes": "Belongs to 02-H02; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H02"
    },
    {
      "id": "02-H03-Y1",
      "kind": "chicken_coop",
      "centre_m": [
        197.07,
        568.79
      ],
      "size_m": [
        2.5,
        2
      ],
      "rotation_deg": 5,
      "polygon_m": [
        [
          195.912,
          567.685
        ],
        [
          198.402,
          567.903
        ],
        [
          198.228,
          569.895
        ],
        [
          195.738,
          569.677
        ]
      ],
      "notes": "Belongs to 02-H03; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H03"
    },
    {
      "id": "02-H03-Y2",
      "kind": "open_working_grass",
      "centre_m": [
        192.38,
        566.09
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": 10,
      "polygon_m": [
        [
          190.671,
          564.265
        ],
        [
          194.61,
          564.96
        ],
        [
          194.089,
          567.915
        ],
        [
          190.15,
          567.22
        ]
      ],
      "notes": "Belongs to 02-H03; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H03"
    },
    {
      "id": "02-H03-Y3",
      "kind": "feed_bin",
      "centre_m": [
        192.38,
        566.09
      ],
      "size_m": [
        0.8,
        0.8
      ],
      "rotation_deg": 5,
      "polygon_m": [
        [
          192.016,
          565.657
        ],
        [
          192.813,
          565.726
        ],
        [
          192.744,
          566.523
        ],
        [
          191.947,
          566.454
        ]
      ],
      "notes": "Belongs to 02-H03; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H03"
    },
    {
      "id": "02-H03-Y4",
      "kind": "water_barrel",
      "centre_m": [
        202.46,
        568.31
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": 10,
      "polygon_m": [
        [
          202.176,
          567.905
        ],
        [
          202.865,
          568.026
        ],
        [
          202.744,
          568.715
        ],
        [
          202.055,
          568.594
        ]
      ],
      "notes": "Belongs to 02-H03; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H03"
    },
    {
      "id": "02-H04-Y1",
      "kind": "woodpile",
      "centre_m": [
        196.69,
        530.03
      ],
      "size_m": [
        4,
        1.2
      ],
      "rotation_deg": -10,
      "polygon_m": [
        [
          194.616,
          529.786
        ],
        [
          198.555,
          529.092
        ],
        [
          198.764,
          530.274
        ],
        [
          194.825,
          530.968
        ]
      ],
      "notes": "Belongs to 02-H04; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H04"
    },
    {
      "id": "02-H04-Y2",
      "kind": "shed",
      "centre_m": [
        191.42,
        531.25
      ],
      "size_m": [
        3.5,
        2.5
      ],
      "rotation_deg": -5,
      "polygon_m": [
        [
          189.568,
          530.157
        ],
        [
          193.054,
          529.852
        ],
        [
          193.272,
          532.343
        ],
        [
          189.786,
          532.648
        ]
      ],
      "notes": "Belongs to 02-H04; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H04"
    },
    {
      "id": "02-H04-Y3",
      "kind": "open_working_grass",
      "centre_m": [
        201.71,
        532.05
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": -10,
      "polygon_m": [
        [
          199.48,
          530.92
        ],
        [
          203.419,
          530.225
        ],
        [
          203.94,
          533.18
        ],
        [
          200.001,
          533.875
        ]
      ],
      "notes": "Belongs to 02-H04; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H04"
    },
    {
      "id": "02-H04-Y4",
      "kind": "outdoor_table",
      "centre_m": [
        201.71,
        532.05
      ],
      "size_m": [
        1.5,
        0.8
      ],
      "rotation_deg": -5,
      "polygon_m": [
        [
          200.928,
          531.717
        ],
        [
          202.422,
          531.586
        ],
        [
          202.492,
          532.383
        ],
        [
          200.998,
          532.514
        ]
      ],
      "notes": "Belongs to 02-H04; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H04"
    },
    {
      "id": "02-H05-Y1",
      "kind": "pig_shelter",
      "centre_m": [
        202.58,
        519.82
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          201.373,
          518.285
        ],
        [
          204.307,
          518.909
        ],
        [
          203.787,
          521.355
        ],
        [
          200.853,
          520.731
        ]
      ],
      "notes": "Belongs to 02-H05; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H05"
    },
    {
      "id": "02-H05-Y2",
      "kind": "feed_trough",
      "centre_m": [
        202.28,
        525.22
      ],
      "size_m": [
        1.8,
        0.7
      ],
      "rotation_deg": 17,
      "polygon_m": [
        [
          201.522,
          524.622
        ],
        [
          203.243,
          525.148
        ],
        [
          203.038,
          525.818
        ],
        [
          201.317,
          525.292
        ]
      ],
      "notes": "Belongs to 02-H05; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H05"
    },
    {
      "id": "02-H05-Y3",
      "kind": "vegetable_garden",
      "centre_m": [
        205.93,
        515.57
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          204.286,
          513.687
        ],
        [
          208.198,
          514.519
        ],
        [
          207.574,
          517.453
        ],
        [
          203.662,
          516.621
        ]
      ],
      "notes": "Belongs to 02-H05; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H05"
    },
    {
      "id": "02-H05-Y4",
      "kind": "water_barrel",
      "centre_m": [
        205.13,
        529.82
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": 17,
      "polygon_m": [
        [
          204.898,
          529.383
        ],
        [
          205.567,
          529.588
        ],
        [
          205.362,
          530.257
        ],
        [
          204.693,
          530.052
        ]
      ],
      "notes": "Belongs to 02-H05; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H05"
    },
    {
      "id": "02-H06-Y1",
      "kind": "flower_strip",
      "centre_m": [
        246.29,
        565.91
      ],
      "size_m": [
        3,
        1
      ],
      "rotation_deg": -4,
      "polygon_m": [
        [
          244.759,
          565.516
        ],
        [
          247.751,
          565.307
        ],
        [
          247.821,
          566.304
        ],
        [
          244.829,
          566.513
        ]
      ],
      "notes": "Belongs to 02-H06; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H06"
    },
    {
      "id": "02-H06-Y2",
      "kind": "shed",
      "centre_m": [
        240.95,
        565.04
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": 1,
      "polygon_m": [
        [
          239.472,
          563.764
        ],
        [
          242.472,
          563.816
        ],
        [
          242.428,
          566.316
        ],
        [
          239.428,
          566.264
        ]
      ],
      "notes": "Belongs to 02-H06; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H06"
    },
    {
      "id": "02-H06-Y3",
      "kind": "woodpile",
      "centre_m": [
        251.17,
        563.55
      ],
      "size_m": [
        2.5,
        1
      ],
      "rotation_deg": -4,
      "polygon_m": [
        [
          249.888,
          563.138
        ],
        [
          252.382,
          562.964
        ],
        [
          252.452,
          563.962
        ],
        [
          249.958,
          564.136
        ]
      ],
      "notes": "Belongs to 02-H06; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H06"
    },
    {
      "id": "02-H06-Y4",
      "kind": "outdoor_table",
      "centre_m": [
        237.07,
        561.26
      ],
      "size_m": [
        1.5,
        0.8
      ],
      "rotation_deg": 1,
      "polygon_m": [
        [
          236.327,
          560.847
        ],
        [
          237.827,
          560.873
        ],
        [
          237.813,
          561.673
        ],
        [
          236.313,
          561.647
        ]
      ],
      "notes": "Belongs to 02-H06; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H06"
    },
    {
      "id": "02-H07-Y1",
      "kind": "vegetable_garden",
      "centre_m": [
        253.52,
        585.64
      ],
      "size_m": [
        6,
        4
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          250.87,
          583.195
        ],
        [
          256.796,
          584.134
        ],
        [
          256.17,
          588.085
        ],
        [
          250.244,
          587.146
        ]
      ],
      "notes": "Belongs to 02-H07; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H07"
    },
    {
      "id": "02-H07-Y2",
      "kind": "shed",
      "centre_m": [
        243.74,
        582.32
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": 14,
      "polygon_m": [
        [
          242.587,
          580.744
        ],
        [
          245.498,
          581.47
        ],
        [
          244.893,
          583.896
        ],
        [
          241.982,
          583.17
        ]
      ],
      "notes": "Belongs to 02-H07; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H07"
    },
    {
      "id": "02-H07-Y3",
      "kind": "clothesline",
      "centre_m": [
        258.02,
        582.63
      ],
      "size_m": [
        3.5,
        0.4
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          256.323,
          582.159
        ],
        [
          259.78,
          582.706
        ],
        [
          259.717,
          583.101
        ],
        [
          256.26,
          582.554
        ]
      ],
      "notes": "Belongs to 02-H07; unfenced, keep routes through yard. Only supports/posts collide; line itself does not.",
      "hard_obstacle": false,
      "parent": "02-H07"
    },
    {
      "id": "02-H07-Y4",
      "kind": "water_barrel",
      "centre_m": [
        248.11,
        585.52
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": 14,
      "polygon_m": [
        [
          247.855,
          585.096
        ],
        [
          248.534,
          585.265
        ],
        [
          248.365,
          585.944
        ],
        [
          247.686,
          585.775
        ]
      ],
      "notes": "Belongs to 02-H07; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H07"
    },
    {
      "id": "02-H08-Y1",
      "kind": "shed",
      "centre_m": [
        311.07,
        567.03
      ],
      "size_m": [
        3.5,
        2.5
      ],
      "rotation_deg": 4,
      "polygon_m": [
        [
          309.411,
          565.661
        ],
        [
          312.903,
          565.905
        ],
        [
          312.729,
          568.399
        ],
        [
          309.237,
          568.155
        ]
      ],
      "notes": "Belongs to 02-H08; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H08"
    },
    {
      "id": "02-H08-Y2",
      "kind": "open_working_grass",
      "centre_m": [
        299.06,
        554.76
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          297.319,
          552.966
        ],
        [
          301.27,
          553.591
        ],
        [
          300.801,
          556.554
        ],
        [
          296.85,
          555.929
        ]
      ],
      "notes": "Belongs to 02-H08; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H08"
    },
    {
      "id": "02-H08-Y3",
      "kind": "wheelbarrow",
      "centre_m": [
        305.73,
        567.91
      ],
      "size_m": [
        1.4,
        0.6
      ],
      "rotation_deg": 4,
      "polygon_m": [
        [
          305.053,
          567.562
        ],
        [
          306.449,
          567.66
        ],
        [
          306.407,
          568.258
        ],
        [
          305.011,
          568.16
        ]
      ],
      "notes": "Belongs to 02-H08; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H08"
    },
    {
      "id": "02-H08-Y4",
      "kind": "woodpile",
      "centre_m": [
        300.85,
        565.57
      ],
      "size_m": [
        2.5,
        1
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          299.694,
          564.881
        ],
        [
          302.163,
          565.272
        ],
        [
          302.006,
          566.259
        ],
        [
          299.537,
          565.868
        ]
      ],
      "notes": "Belongs to 02-H08; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H08"
    },
    {
      "id": "02-H09-Y1",
      "kind": "vegetable_garden",
      "centre_m": [
        317.88,
        514.2
      ],
      "size_m": [
        6,
        4
      ],
      "rotation_deg": -7,
      "polygon_m": [
        [
          314.659,
          512.581
        ],
        [
          320.614,
          511.849
        ],
        [
          321.101,
          515.819
        ],
        [
          315.146,
          516.551
        ]
      ],
      "notes": "Belongs to 02-H09; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H09"
    },
    {
      "id": "02-H09-Y2",
      "kind": "shed",
      "centre_m": [
        308.37,
        518.22
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": -2,
      "polygon_m": [
        [
          306.827,
          517.023
        ],
        [
          309.825,
          516.918
        ],
        [
          309.913,
          519.417
        ],
        [
          306.915,
          519.522
        ]
      ],
      "notes": "Belongs to 02-H09; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H09"
    },
    {
      "id": "02-H09-Y3",
      "kind": "clothesline",
      "centre_m": [
        322.59,
        516.87
      ],
      "size_m": [
        3.5,
        0.4
      ],
      "rotation_deg": -7,
      "polygon_m": [
        [
          320.829,
          516.885
        ],
        [
          324.303,
          516.458
        ],
        [
          324.351,
          516.855
        ],
        [
          320.877,
          517.282
        ]
      ],
      "notes": "Belongs to 02-H09; unfenced, keep routes through yard. Only supports/posts collide; line itself does not.",
      "hard_obstacle": false,
      "parent": "02-H09"
    },
    {
      "id": "02-H09-Y4",
      "kind": "water_barrel",
      "centre_m": [
        312.5,
        514.71
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": -2,
      "polygon_m": [
        [
          312.138,
          514.372
        ],
        [
          312.838,
          514.348
        ],
        [
          312.862,
          515.048
        ],
        [
          312.162,
          515.072
        ]
      ],
      "notes": "Belongs to 02-H09; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H09"
    },
    {
      "id": "02-H10-Y1",
      "kind": "flower_strip",
      "centre_m": [
        284.0,
        507.0
      ],
      "size_m": [
        3,
        1
      ],
      "rotation_deg": 2,
      "polygon_m": [
        [
          282.518,
          506.448
        ],
        [
          285.517,
          506.553
        ],
        [
          285.482,
          507.552
        ],
        [
          282.483,
          507.447
        ]
      ],
      "notes": "Belongs to 02-H10; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H10"
    },
    {
      "id": "02-H10-Y2",
      "kind": "shed",
      "centre_m": [
        278.84,
        508.63
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": 7,
      "polygon_m": [
        [
          277.504,
          507.207
        ],
        [
          280.481,
          507.572
        ],
        [
          280.176,
          510.053
        ],
        [
          277.199,
          509.688
        ]
      ],
      "notes": "Belongs to 02-H10; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H10"
    },
    {
      "id": "02-H10-Y3",
      "kind": "woodpile",
      "centre_m": [
        289.16,
        508.63
      ],
      "size_m": [
        2.5,
        1
      ],
      "rotation_deg": 2,
      "polygon_m": [
        [
          287.928,
          508.087
        ],
        [
          290.427,
          508.174
        ],
        [
          290.392,
          509.173
        ],
        [
          287.893,
          509.086
        ]
      ],
      "notes": "Belongs to 02-H10; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H10"
    },
    {
      "id": "02-H10-Y4",
      "kind": "outdoor_table",
      "centre_m": [
        275.54,
        512.92
      ],
      "size_m": [
        1.5,
        0.8
      ],
      "rotation_deg": 7,
      "polygon_m": [
        [
          274.844,
          512.432
        ],
        [
          276.333,
          512.614
        ],
        [
          276.236,
          513.408
        ],
        [
          274.747,
          513.226
        ]
      ],
      "notes": "Belongs to 02-H10; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H10"
    },
    {
      "id": "02-H11-Y1",
      "kind": "chicken_coop",
      "centre_m": [
        279.88,
        467.0
      ],
      "size_m": [
        2.5,
        2
      ],
      "rotation_deg": 10,
      "polygon_m": [
        [
          278.823,
          465.798
        ],
        [
          281.285,
          466.232
        ],
        [
          280.937,
          468.202
        ],
        [
          278.475,
          467.768
        ]
      ],
      "notes": "Belongs to 02-H11; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H11"
    },
    {
      "id": "02-H11-Y2",
      "kind": "vegetable_garden",
      "centre_m": [
        274.74,
        468.7
      ],
      "size_m": [
        5,
        3
      ],
      "rotation_deg": 15,
      "polygon_m": [
        [
          272.713,
          466.604
        ],
        [
          277.543,
          467.898
        ],
        [
          276.767,
          470.796
        ],
        [
          271.937,
          469.502
        ]
      ],
      "notes": "Belongs to 02-H11; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H11"
    },
    {
      "id": "02-H11-Y3",
      "kind": "feed_bin",
      "centre_m": [
        285.06,
        468.56
      ],
      "size_m": [
        0.8,
        0.8
      ],
      "rotation_deg": 10,
      "polygon_m": [
        [
          284.736,
          468.097
        ],
        [
          285.523,
          468.236
        ],
        [
          285.384,
          469.023
        ],
        [
          284.597,
          468.884
        ]
      ],
      "notes": "Belongs to 02-H11; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H11"
    },
    {
      "id": "02-H11-Y4",
      "kind": "water_barrel",
      "centre_m": [
        271.5,
        473.03
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": 15,
      "polygon_m": [
        [
          271.253,
          472.601
        ],
        [
          271.929,
          472.783
        ],
        [
          271.747,
          473.459
        ],
        [
          271.071,
          473.277
        ]
      ],
      "notes": "Belongs to 02-H11; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H11"
    },
    {
      "id": "02-H12-Y1",
      "kind": "pig_shelter",
      "centre_m": [
        311.68,
        463.03
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": -4,
      "polygon_m": [
        [
          310.096,
          461.888
        ],
        [
          313.089,
          461.678
        ],
        [
          313.264,
          464.172
        ],
        [
          310.271,
          464.382
        ]
      ],
      "notes": "Belongs to 02-H12; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H12"
    },
    {
      "id": "02-H12-Y2",
      "kind": "feed_trough",
      "centre_m": [
        306.41,
        464.26
      ],
      "size_m": [
        1.8,
        0.7
      ],
      "rotation_deg": 1,
      "polygon_m": [
        [
          305.516,
          463.894
        ],
        [
          307.316,
          463.926
        ],
        [
          307.304,
          464.626
        ],
        [
          305.504,
          464.594
        ]
      ],
      "notes": "Belongs to 02-H12; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H12"
    },
    {
      "id": "02-H12-Y3",
      "kind": "open_working_grass",
      "centre_m": [
        302.8,
        468.3
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": -4,
      "polygon_m": [
        [
          300.7,
          466.943
        ],
        [
          304.69,
          466.664
        ],
        [
          304.9,
          469.657
        ],
        [
          300.91,
          469.936
        ]
      ],
      "notes": "Belongs to 02-H12; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H12"
    },
    {
      "id": "02-H12-Y4",
      "kind": "water_barrel",
      "centre_m": [
        316.7,
        465.04
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": 1,
      "polygon_m": [
        [
          316.356,
          464.684
        ],
        [
          317.056,
          464.696
        ],
        [
          317.044,
          465.396
        ],
        [
          316.344,
          465.384
        ]
      ],
      "notes": "Belongs to 02-H12; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H12"
    },
    {
      "id": "02-H13-Y1",
      "kind": "shed",
      "centre_m": [
        348.59,
        453.67
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": -8,
      "polygon_m": [
        [
          346.931,
          452.641
        ],
        [
          349.901,
          452.223
        ],
        [
          350.249,
          454.699
        ],
        [
          347.279,
          455.117
        ]
      ],
      "notes": "Belongs to 02-H13; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H13"
    },
    {
      "id": "02-H13-Y2",
      "kind": "net_drying_rack",
      "centre_m": [
        344.43,
        457.13
      ],
      "size_m": [
        2.5,
        0.3
      ],
      "rotation_deg": -3,
      "polygon_m": [
        [
          343.174,
          457.046
        ],
        [
          345.67,
          456.915
        ],
        [
          345.686,
          457.214
        ],
        [
          343.19,
          457.345
        ]
      ],
      "notes": "Belongs to 02-H13; unfenced, keep routes through yard. Only supports/posts collide; line itself does not.",
      "hard_obstacle": false,
      "parent": "02-H13"
    },
    {
      "id": "02-H13-Y3",
      "kind": "open_working_grass",
      "centre_m": [
        344.43,
        457.13
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": -8,
      "polygon_m": [
        [
          342.241,
          455.923
        ],
        [
          346.202,
          455.366
        ],
        [
          346.619,
          458.337
        ],
        [
          342.658,
          458.894
        ]
      ],
      "notes": "Belongs to 02-H13; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H13"
    },
    {
      "id": "02-H13-Y4",
      "kind": "outdoor_table",
      "centre_m": [
        344.43,
        457.13
      ],
      "size_m": [
        1.5,
        0.8
      ],
      "rotation_deg": -3,
      "polygon_m": [
        [
          343.66,
          456.77
        ],
        [
          345.158,
          456.691
        ],
        [
          345.2,
          457.49
        ],
        [
          343.702,
          457.569
        ]
      ],
      "notes": "Belongs to 02-H13; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H13"
    },
    {
      "id": "02-H14-Y1",
      "kind": "vegetable_garden",
      "centre_m": [
        268.81,
        454.14
      ],
      "size_m": [
        6,
        4
      ],
      "rotation_deg": 7,
      "polygon_m": [
        [
          266.076,
          451.789
        ],
        [
          272.031,
          452.521
        ],
        [
          271.544,
          456.491
        ],
        [
          265.589,
          455.759
        ]
      ],
      "notes": "Belongs to 02-H14; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H14"
    },
    {
      "id": "02-H14-Y2",
      "kind": "shed",
      "centre_m": [
        266.14,
        449.42
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          264.933,
          447.885
        ],
        [
          267.867,
          448.509
        ],
        [
          267.347,
          450.955
        ],
        [
          264.413,
          450.331
        ]
      ],
      "notes": "Belongs to 02-H14; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H14"
    },
    {
      "id": "02-H14-Y3",
      "kind": "clothesline",
      "centre_m": [
        268.28,
        459.52
      ],
      "size_m": [
        3.5,
        0.4
      ],
      "rotation_deg": 7,
      "polygon_m": [
        [
          266.567,
          459.108
        ],
        [
          270.041,
          459.535
        ],
        [
          269.993,
          459.932
        ],
        [
          266.519,
          459.505
        ]
      ],
      "notes": "Belongs to 02-H14; unfenced, keep routes through yard. Only supports/posts collide; line itself does not.",
      "hard_obstacle": false,
      "parent": "02-H14"
    },
    {
      "id": "02-H14-Y4",
      "kind": "water_barrel",
      "centre_m": [
        268.28,
        459.52
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          268.01,
          459.105
        ],
        [
          268.695,
          459.25
        ],
        [
          268.55,
          459.935
        ],
        [
          267.865,
          459.79
        ]
      ],
      "notes": "Belongs to 02-H14; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H14"
    },
    {
      "id": "02-H15-Y1",
      "kind": "woodpile",
      "centre_m": [
        280.93,
        433.89
      ],
      "size_m": [
        4,
        1.2
      ],
      "rotation_deg": -11,
      "polygon_m": [
        [
          278.852,
          433.683
        ],
        [
          282.779,
          432.919
        ],
        [
          283.008,
          434.097
        ],
        [
          279.081,
          434.861
        ]
      ],
      "notes": "Belongs to 02-H15; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H15"
    },
    {
      "id": "02-H15-Y2",
      "kind": "shed",
      "centre_m": [
        278.68,
        428.97
      ],
      "size_m": [
        3.5,
        2.5
      ],
      "rotation_deg": -6,
      "polygon_m": [
        [
          276.809,
          427.91
        ],
        [
          280.29,
          427.544
        ],
        [
          280.551,
          430.03
        ],
        [
          277.07,
          430.396
        ]
      ],
      "notes": "Belongs to 02-H15; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H15"
    },
    {
      "id": "02-H15-Y3",
      "kind": "open_working_grass",
      "centre_m": [
        279.95,
        439.22
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": -11,
      "polygon_m": [
        [
          277.701,
          438.129
        ],
        [
          281.627,
          437.366
        ],
        [
          282.199,
          440.311
        ],
        [
          278.273,
          441.074
        ]
      ],
      "notes": "Belongs to 02-H15; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H15"
    },
    {
      "id": "02-H15-Y4",
      "kind": "outdoor_table",
      "centre_m": [
        279.95,
        439.22
      ],
      "size_m": [
        1.5,
        0.8
      ],
      "rotation_deg": -6,
      "polygon_m": [
        [
          279.162,
          438.901
        ],
        [
          280.654,
          438.744
        ],
        [
          280.738,
          439.539
        ],
        [
          279.246,
          439.696
        ]
      ],
      "notes": "Belongs to 02-H15; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H15"
    },
    {
      "id": "02-H16-Y1",
      "kind": "chicken_coop",
      "centre_m": [
        287.53,
        420.87
      ],
      "size_m": [
        2.5,
        2
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          286.452,
          419.687
        ],
        [
          288.921,
          420.078
        ],
        [
          288.608,
          422.053
        ],
        [
          286.139,
          421.662
        ]
      ],
      "notes": "Belongs to 02-H16; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H16"
    },
    {
      "id": "02-H16-Y2",
      "kind": "open_working_grass",
      "centre_m": [
        282.17,
        420.14
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": 14,
      "polygon_m": [
        [
          280.592,
          418.201
        ],
        [
          284.473,
          419.168
        ],
        [
          283.748,
          422.079
        ],
        [
          279.867,
          421.112
        ]
      ],
      "notes": "Belongs to 02-H16; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H16"
    },
    {
      "id": "02-H16-Y3",
      "kind": "feed_bin",
      "centre_m": [
        282.17,
        420.14
      ],
      "size_m": [
        0.8,
        0.8
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          281.837,
          419.682
        ],
        [
          282.628,
          419.807
        ],
        [
          282.503,
          420.598
        ],
        [
          281.712,
          420.473
        ]
      ],
      "notes": "Belongs to 02-H16; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H16"
    },
    {
      "id": "02-H16-Y4",
      "kind": "water_barrel",
      "centre_m": [
        292.34,
        418.39
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": 14,
      "polygon_m": [
        [
          292.085,
          417.966
        ],
        [
          292.764,
          418.135
        ],
        [
          292.595,
          418.814
        ],
        [
          291.916,
          418.645
        ]
      ],
      "notes": "Belongs to 02-H16; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H16"
    },
    {
      "id": "02-H17-Y1",
      "kind": "pig_shelter",
      "centre_m": [
        302.06,
        419.06
      ],
      "size_m": [
        3,
        2.5
      ],
      "rotation_deg": -9,
      "polygon_m": [
        [
          300.383,
          418.06
        ],
        [
          303.346,
          417.591
        ],
        [
          303.737,
          420.06
        ],
        [
          300.774,
          420.529
        ]
      ],
      "notes": "Belongs to 02-H17; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H17"
    },
    {
      "id": "02-H17-Y2",
      "kind": "feed_trough",
      "centre_m": [
        303.07,
        413.74
      ],
      "size_m": [
        1.8,
        0.7
      ],
      "rotation_deg": -4,
      "polygon_m": [
        [
          302.148,
          413.454
        ],
        [
          303.943,
          413.328
        ],
        [
          303.992,
          414.026
        ],
        [
          302.197,
          414.152
        ]
      ],
      "notes": "Belongs to 02-H17; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H17"
    },
    {
      "id": "02-H17-Y3",
      "kind": "vegetable_garden",
      "centre_m": [
        304.29,
        424.0
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": -9,
      "polygon_m": [
        [
          302.08,
          422.831
        ],
        [
          306.031,
          422.206
        ],
        [
          306.5,
          425.169
        ],
        [
          302.549,
          425.794
        ]
      ],
      "notes": "Belongs to 02-H17; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H17"
    },
    {
      "id": "02-H17-Y4",
      "kind": "water_barrel",
      "centre_m": [
        306.94,
        409.97
      ],
      "size_m": [
        0.7,
        0.7
      ],
      "rotation_deg": -4,
      "polygon_m": [
        [
          306.566,
          409.645
        ],
        [
          307.265,
          409.596
        ],
        [
          307.314,
          410.295
        ],
        [
          306.615,
          410.344
        ]
      ],
      "notes": "Belongs to 02-H17; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H17"
    },
    {
      "id": "02-H18-Y1",
      "kind": "shed",
      "centre_m": [
        358.99,
        410.56
      ],
      "size_m": [
        3.5,
        2.5
      ],
      "rotation_deg": 8,
      "polygon_m": [
        [
          357.431,
          409.079
        ],
        [
          360.897,
          409.566
        ],
        [
          360.549,
          412.041
        ],
        [
          357.083,
          411.554
        ]
      ],
      "notes": "Belongs to 02-H18; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H18"
    },
    {
      "id": "02-H18-Y2",
      "kind": "open_working_grass",
      "centre_m": [
        357.11,
        405.49
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": 13,
      "polygon_m": [
        [
          355.499,
          403.579
        ],
        [
          359.396,
          404.478
        ],
        [
          358.721,
          407.401
        ],
        [
          354.824,
          406.502
        ]
      ],
      "notes": "Belongs to 02-H18; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H18"
    },
    {
      "id": "02-H18-Y3",
      "kind": "wheelbarrow",
      "centre_m": [
        357.11,
        405.49
      ],
      "size_m": [
        1.4,
        0.6
      ],
      "rotation_deg": 8,
      "polygon_m": [
        [
          356.459,
          405.095
        ],
        [
          357.845,
          405.29
        ],
        [
          357.761,
          405.885
        ],
        [
          356.375,
          405.69
        ]
      ],
      "notes": "Belongs to 02-H18; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H18"
    },
    {
      "id": "02-H18-Y4",
      "kind": "woodpile",
      "centre_m": [
        357.61,
        415.8
      ],
      "size_m": [
        2.5,
        1
      ],
      "rotation_deg": 13,
      "polygon_m": [
        [
          356.505,
          415.032
        ],
        [
          358.94,
          415.594
        ],
        [
          358.715,
          416.568
        ],
        [
          356.28,
          416.006
        ]
      ],
      "notes": "Belongs to 02-H18; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H18"
    },
    {
      "id": "02-H19-Y1",
      "kind": "rusted_car",
      "centre_m": [
        206.24,
        434.08
      ],
      "size_m": [
        3.8,
        1.6
      ],
      "rotation_deg": -12,
      "polygon_m": [
        [
          204.215,
          433.693
        ],
        [
          207.932,
          432.902
        ],
        [
          208.265,
          434.467
        ],
        [
          204.548,
          435.258
        ]
      ],
      "notes": "Belongs to 02-H19; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H19"
    },
    {
      "id": "02-H19-Y2",
      "kind": "broken_timber",
      "centre_m": [
        206.63,
        428.69
      ],
      "size_m": [
        2,
        1
      ],
      "rotation_deg": -7,
      "polygon_m": [
        [
          205.577,
          428.316
        ],
        [
          207.562,
          428.072
        ],
        [
          207.683,
          429.064
        ],
        [
          205.698,
          429.308
        ]
      ],
      "notes": "Belongs to 02-H19; unfenced, keep routes through yard. ",
      "hard_obstacle": true,
      "parent": "02-H19"
    },
    {
      "id": "02-H19-Y3",
      "kind": "overgrown_beds",
      "centre_m": [
        209.02,
        438.73
      ],
      "size_m": [
        4,
        3
      ],
      "rotation_deg": -12,
      "polygon_m": [
        [
          206.752,
          437.679
        ],
        [
          210.664,
          436.847
        ],
        [
          211.288,
          439.781
        ],
        [
          207.376,
          440.613
        ]
      ],
      "notes": "Belongs to 02-H19; unfenced, keep routes through yard. ",
      "hard_obstacle": false,
      "parent": "02-H19"
    },
    {
      "id": "02-P-01",
      "kind": "wooden_utility_pole",
      "centre_m": [
        358.85,
        473.41
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          358.7,
          473.26
        ],
        [
          359.0,
          473.26
        ],
        [
          359.0,
          473.56
        ],
        [
          358.7,
          473.56
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-02",
      "kind": "wooden_utility_pole",
      "centre_m": [
        331.25,
        481.21
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          331.1,
          481.06
        ],
        [
          331.4,
          481.06
        ],
        [
          331.4,
          481.36
        ],
        [
          331.1,
          481.36
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-03",
      "kind": "wooden_utility_pole",
      "centre_m": [
        298.44,
        484.17
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          298.29,
          484.02
        ],
        [
          298.59,
          484.02
        ],
        [
          298.59,
          484.32
        ],
        [
          298.29,
          484.32
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-04",
      "kind": "wooden_utility_pole",
      "centre_m": [
        265.97,
        487.77
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          265.82,
          487.62
        ],
        [
          266.12,
          487.62
        ],
        [
          266.12,
          487.92
        ],
        [
          265.82,
          487.92
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-05",
      "kind": "wooden_utility_pole",
      "centre_m": [
        236.08,
        500.72
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          235.93,
          500.57
        ],
        [
          236.23,
          500.57
        ],
        [
          236.23,
          500.87
        ],
        [
          235.93,
          500.87
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-06",
      "kind": "wooden_utility_pole",
      "centre_m": [
        219.4,
        530.66
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          219.25,
          530.51
        ],
        [
          219.55,
          530.51
        ],
        [
          219.55,
          530.81
        ],
        [
          219.25,
          530.81
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-07",
      "kind": "wooden_utility_pole",
      "centre_m": [
        209.04,
        546.61
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          208.89,
          546.46
        ],
        [
          209.19,
          546.46
        ],
        [
          209.19,
          546.76
        ],
        [
          208.89,
          546.76
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-08",
      "kind": "wooden_utility_pole",
      "centre_m": [
        178.78,
        545.34
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          178.63,
          545.19
        ],
        [
          178.93,
          545.19
        ],
        [
          178.93,
          545.49
        ],
        [
          178.63,
          545.49
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-09",
      "kind": "wooden_utility_pole",
      "centre_m": [
        146.58,
        545.42
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          146.43,
          545.27
        ],
        [
          146.73,
          545.27
        ],
        [
          146.73,
          545.57
        ],
        [
          146.43,
          545.57
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-10",
      "kind": "wooden_utility_pole",
      "centre_m": [
        225.29,
        552.42
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          225.14,
          552.27
        ],
        [
          225.44,
          552.27
        ],
        [
          225.44,
          552.57
        ],
        [
          225.14,
          552.57
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-11",
      "kind": "wooden_utility_pole",
      "centre_m": [
        250.75,
        545.48
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          250.6,
          545.33
        ],
        [
          250.9,
          545.33
        ],
        [
          250.9,
          545.63
        ],
        [
          250.6,
          545.63
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-12",
      "kind": "wooden_utility_pole",
      "centre_m": [
        278.09,
        544.6
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          277.94,
          544.45
        ],
        [
          278.24,
          544.45
        ],
        [
          278.24,
          544.75
        ],
        [
          277.94,
          544.75
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-13",
      "kind": "wooden_utility_pole",
      "centre_m": [
        305.31,
        544.85
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          305.16,
          544.7
        ],
        [
          305.46,
          544.7
        ],
        [
          305.46,
          545.0
        ],
        [
          305.16,
          545.0
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-14",
      "kind": "wooden_utility_pole",
      "centre_m": [
        332.59,
        546.93
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          332.44,
          546.78
        ],
        [
          332.74,
          546.78
        ],
        [
          332.74,
          547.08
        ],
        [
          332.44,
          547.08
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-15",
      "kind": "wooden_utility_pole",
      "centre_m": [
        253.39,
        502.22
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          253.24,
          502.07
        ],
        [
          253.54,
          502.07
        ],
        [
          253.54,
          502.37
        ],
        [
          253.24,
          502.37
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-16",
      "kind": "wooden_utility_pole",
      "centre_m": [
        251.29,
        465.78
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          251.14,
          465.63
        ],
        [
          251.44,
          465.63
        ],
        [
          251.44,
          465.93
        ],
        [
          251.14,
          465.93
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-17",
      "kind": "wooden_utility_pole",
      "centre_m": [
        242.99,
        435.55
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          242.84,
          435.4
        ],
        [
          243.14,
          435.4
        ],
        [
          243.14,
          435.7
        ],
        [
          242.84,
          435.7
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-18",
      "kind": "wooden_utility_pole",
      "centre_m": [
        237.24,
        407.03
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          237.09,
          406.88
        ],
        [
          237.39,
          406.88
        ],
        [
          237.39,
          407.18
        ],
        [
          237.09,
          407.18
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-19",
      "kind": "wooden_utility_pole",
      "centre_m": [
        238.59,
        374.76
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          238.44,
          374.61
        ],
        [
          238.74,
          374.61
        ],
        [
          238.74,
          374.91
        ],
        [
          238.44,
          374.91
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-20",
      "kind": "wooden_utility_pole",
      "centre_m": [
        330.27,
        491.35
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          330.12,
          491.2
        ],
        [
          330.42,
          491.2
        ],
        [
          330.42,
          491.5
        ],
        [
          330.12,
          491.5
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-21",
      "kind": "wooden_utility_pole",
      "centre_m": [
        333.29,
        460.41
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          333.14,
          460.26
        ],
        [
          333.44,
          460.26
        ],
        [
          333.44,
          460.56
        ],
        [
          333.14,
          460.56
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-22",
      "kind": "wooden_utility_pole",
      "centre_m": [
        339.27,
        431.63
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          339.12,
          431.48
        ],
        [
          339.42,
          431.48
        ],
        [
          339.42,
          431.78
        ],
        [
          339.12,
          431.78
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-23",
      "kind": "wooden_utility_pole",
      "centre_m": [
        336.03,
        403.08
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          335.88,
          402.93
        ],
        [
          336.18,
          402.93
        ],
        [
          336.18,
          403.23
        ],
        [
          335.88,
          403.23
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-24",
      "kind": "wooden_utility_pole",
      "centre_m": [
        318.15,
        377.86
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          318.0,
          377.71
        ],
        [
          318.3,
          377.71
        ],
        [
          318.3,
          378.01
        ],
        [
          318.0,
          378.01
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-25",
      "kind": "wooden_utility_pole",
      "centre_m": [
        289.84,
        380.88
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          289.69,
          380.73
        ],
        [
          289.99,
          380.73
        ],
        [
          289.99,
          381.03
        ],
        [
          289.69,
          381.03
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-26",
      "kind": "wooden_utility_pole",
      "centre_m": [
        262.25,
        385.6
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          262.1,
          385.45
        ],
        [
          262.4,
          385.45
        ],
        [
          262.4,
          385.75
        ],
        [
          262.1,
          385.75
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-P-27",
      "kind": "wooden_utility_pole",
      "centre_m": [
        230.41,
        389.99
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          230.26,
          389.84
        ],
        [
          230.56,
          389.84
        ],
        [
          230.56,
          390.14
        ],
        [
          230.26,
          390.14
        ]
      ],
      "notes": "About 7 m tall. Routed next to street; poles collide, suspended wire does not.",
      "hard_obstacle": true,
      "height_m": 7
    },
    {
      "id": "02-T-001",
      "kind": "tree",
      "centre_m": [
        157.83,
        455.32
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 76,
      "polygon_m": [
        [
          158.03,
          454.987
        ],
        [
          158.163,
          455.52
        ],
        [
          157.63,
          455.653
        ],
        [
          157.497,
          455.12
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-002",
      "kind": "tree",
      "centre_m": [
        160.22,
        479.87
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 169,
      "polygon_m": [
        [
          160.542,
          480.087
        ],
        [
          160.003,
          480.192
        ],
        [
          159.898,
          479.653
        ],
        [
          160.437,
          479.548
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-003",
      "kind": "tree",
      "centre_m": [
        154.99,
        463.85
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 181,
      "polygon_m": [
        [
          155.26,
          464.13
        ],
        [
          154.71,
          464.12
        ],
        [
          154.72,
          463.57
        ],
        [
          155.27,
          463.58
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-004",
      "kind": "tree",
      "centre_m": [
        149.08,
        463.32
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 226,
      "polygon_m": [
        [
          149.073,
          463.709
        ],
        [
          148.691,
          463.313
        ],
        [
          149.087,
          462.931
        ],
        [
          149.469,
          463.327
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-005",
      "kind": "tree",
      "centre_m": [
        148.97,
        458.95
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 358,
      "polygon_m": [
        [
          148.686,
          458.685
        ],
        [
          149.235,
          458.666
        ],
        [
          149.254,
          459.215
        ],
        [
          148.705,
          459.234
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-006",
      "kind": "tree",
      "centre_m": [
        161.22,
        486.6
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 338,
      "polygon_m": [
        [
          160.862,
          486.448
        ],
        [
          161.372,
          486.242
        ],
        [
          161.578,
          486.752
        ],
        [
          161.068,
          486.958
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-007",
      "kind": "tree",
      "centre_m": [
        151.1,
        481.88
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 320,
      "polygon_m": [
        [
          150.713,
          481.846
        ],
        [
          151.134,
          481.493
        ],
        [
          151.487,
          481.914
        ],
        [
          151.066,
          482.267
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-008",
      "kind": "tree",
      "centre_m": [
        148.09,
        491.36
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 216,
      "polygon_m": [
        [
          148.151,
          491.744
        ],
        [
          147.706,
          491.421
        ],
        [
          148.029,
          490.976
        ],
        [
          148.474,
          491.299
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-009",
      "kind": "tree",
      "centre_m": [
        147.45,
        445.71
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 24,
      "polygon_m": [
        [
          147.311,
          445.347
        ],
        [
          147.813,
          445.571
        ],
        [
          147.589,
          446.073
        ],
        [
          147.087,
          445.849
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-010",
      "kind": "tree",
      "centre_m": [
        147.1,
        468.12
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 61,
      "polygon_m": [
        [
          147.207,
          467.746
        ],
        [
          147.474,
          468.227
        ],
        [
          146.993,
          468.494
        ],
        [
          146.726,
          468.013
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-011",
      "kind": "tree",
      "centre_m": [
        138.7,
        501.26
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 73,
      "polygon_m": [
        [
          138.883,
          500.917
        ],
        [
          139.043,
          501.443
        ],
        [
          138.517,
          501.603
        ],
        [
          138.357,
          501.077
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-012",
      "kind": "tree",
      "centre_m": [
        144.17,
        448.36
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 353,
      "polygon_m": [
        [
          143.864,
          448.121
        ],
        [
          144.409,
          448.054
        ],
        [
          144.476,
          448.599
        ],
        [
          143.931,
          448.666
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-013",
      "kind": "tree",
      "centre_m": [
        136.26,
        462.49
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 284,
      "polygon_m": [
        [
          135.927,
          462.69
        ],
        [
          136.06,
          462.157
        ],
        [
          136.593,
          462.29
        ],
        [
          136.46,
          462.823
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-014",
      "kind": "tree",
      "centre_m": [
        150.72,
        450.78
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 183,
      "polygon_m": [
        [
          150.98,
          451.069
        ],
        [
          150.431,
          451.04
        ],
        [
          150.46,
          450.491
        ],
        [
          151.009,
          450.52
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-015",
      "kind": "tree",
      "centre_m": [
        136.2,
        445.01
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 294,
      "polygon_m": [
        [
          135.837,
          445.149
        ],
        [
          136.061,
          444.647
        ],
        [
          136.563,
          444.871
        ],
        [
          136.339,
          445.373
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-016",
      "kind": "tree",
      "centre_m": [
        142.41,
        494.2
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 85,
      "polygon_m": [
        [
          142.66,
          493.902
        ],
        [
          142.708,
          494.45
        ],
        [
          142.16,
          494.498
        ],
        [
          142.112,
          493.95
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-017",
      "kind": "tree",
      "centre_m": [
        142.43,
        463.64
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 116,
      "polygon_m": [
        [
          142.798,
          463.513
        ],
        [
          142.557,
          464.008
        ],
        [
          142.062,
          463.767
        ],
        [
          142.303,
          463.272
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-018",
      "kind": "tree",
      "centre_m": [
        160.46,
        467.04
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          160.185,
          466.765
        ],
        [
          160.735,
          466.765
        ],
        [
          160.735,
          467.315
        ],
        [
          160.185,
          467.315
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-019",
      "kind": "tree",
      "centre_m": [
        143.22,
        487.12
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 186,
      "polygon_m": [
        [
          143.465,
          487.422
        ],
        [
          142.918,
          487.365
        ],
        [
          142.975,
          486.818
        ],
        [
          143.522,
          486.875
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-020",
      "kind": "tree",
      "centre_m": [
        154.1,
        453.31
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 11,
      "polygon_m": [
        [
          153.883,
          452.988
        ],
        [
          154.422,
          453.093
        ],
        [
          154.317,
          453.632
        ],
        [
          153.778,
          453.527
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-021",
      "kind": "tree",
      "centre_m": [
        155.97,
        486.37
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 4,
      "polygon_m": [
        [
          155.715,
          486.076
        ],
        [
          156.264,
          486.115
        ],
        [
          156.225,
          486.664
        ],
        [
          155.676,
          486.625
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-022",
      "kind": "tree",
      "centre_m": [
        148.76,
        474.12
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 251,
      "polygon_m": [
        [
          148.59,
          474.47
        ],
        [
          148.41,
          473.95
        ],
        [
          148.93,
          473.77
        ],
        [
          149.11,
          474.29
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-023",
      "kind": "tree",
      "centre_m": [
        143.03,
        502.04
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 158,
      "polygon_m": [
        [
          143.388,
          502.192
        ],
        [
          142.878,
          502.398
        ],
        [
          142.672,
          501.888
        ],
        [
          143.182,
          501.682
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-024",
      "kind": "tree",
      "centre_m": [
        160.74,
        471.82
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 342,
      "polygon_m": [
        [
          160.393,
          471.643
        ],
        [
          160.917,
          471.473
        ],
        [
          161.087,
          471.997
        ],
        [
          160.563,
          472.167
        ]
      ],
      "notes": "Exact selected planting point within grove_west. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_west"
    },
    {
      "id": "02-T-025",
      "kind": "tree",
      "centre_m": [
        225.58,
        382.76
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 106,
      "polygon_m": [
        [
          225.92,
          382.571
        ],
        [
          225.769,
          383.1
        ],
        [
          225.24,
          382.949
        ],
        [
          225.391,
          382.42
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-026",
      "kind": "tree",
      "centre_m": [
        214.07,
        419.85
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 180,
      "polygon_m": [
        [
          214.345,
          420.125
        ],
        [
          213.795,
          420.125
        ],
        [
          213.795,
          419.575
        ],
        [
          214.345,
          419.575
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-027",
      "kind": "tree",
      "centre_m": [
        212.37,
        387.46
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 120,
      "polygon_m": [
        [
          212.746,
          387.359
        ],
        [
          212.471,
          387.836
        ],
        [
          211.994,
          387.561
        ],
        [
          212.269,
          387.084
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-028",
      "kind": "tree",
      "centre_m": [
        223.39,
        392.08
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 171,
      "polygon_m": [
        [
          223.705,
          392.309
        ],
        [
          223.161,
          392.395
        ],
        [
          223.075,
          391.851
        ],
        [
          223.619,
          391.765
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-029",
      "kind": "tree",
      "centre_m": [
        218.36,
        392.39
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 26,
      "polygon_m": [
        [
          218.233,
          392.022
        ],
        [
          218.728,
          392.263
        ],
        [
          218.487,
          392.758
        ],
        [
          217.992,
          392.517
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-030",
      "kind": "tree",
      "centre_m": [
        226.41,
        388.89
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 154,
      "polygon_m": [
        [
          226.778,
          389.017
        ],
        [
          226.283,
          389.258
        ],
        [
          226.042,
          388.763
        ],
        [
          226.537,
          388.522
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-031",
      "kind": "tree",
      "centre_m": [
        222.69,
        405.39
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 229,
      "polygon_m": [
        [
          222.663,
          405.778
        ],
        [
          222.302,
          405.363
        ],
        [
          222.717,
          405.002
        ],
        [
          223.078,
          405.417
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-032",
      "kind": "tree",
      "centre_m": [
        219.16,
        383.9
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 57,
      "polygon_m": [
        [
          219.241,
          383.52
        ],
        [
          219.54,
          383.981
        ],
        [
          219.079,
          384.28
        ],
        [
          218.78,
          383.819
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-033",
      "kind": "tree",
      "centre_m": [
        217.71,
        410.7
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 14,
      "polygon_m": [
        [
          217.51,
          410.367
        ],
        [
          218.043,
          410.5
        ],
        [
          217.91,
          411.033
        ],
        [
          217.377,
          410.9
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-034",
      "kind": "tree",
      "centre_m": [
        208.51,
        389.49
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 322,
      "polygon_m": [
        [
          208.124,
          389.443
        ],
        [
          208.557,
          389.104
        ],
        [
          208.896,
          389.537
        ],
        [
          208.463,
          389.876
        ]
      ],
      "notes": "Exact selected planting point within grove_south. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_south"
    },
    {
      "id": "02-T-035",
      "kind": "tree",
      "centre_m": [
        276.16,
        464.51
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 130,
      "polygon_m": [
        [
          276.547,
          464.476
        ],
        [
          276.194,
          464.897
        ],
        [
          275.773,
          464.544
        ],
        [
          276.126,
          464.123
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-036",
      "kind": "tree",
      "centre_m": [
        270.91,
        459.29
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 51,
      "polygon_m": [
        [
          270.951,
          458.903
        ],
        [
          271.297,
          459.331
        ],
        [
          270.869,
          459.677
        ],
        [
          270.523,
          459.249
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-037",
      "kind": "tree",
      "centre_m": [
        277.03,
        449.93
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 48,
      "polygon_m": [
        [
          277.05,
          449.542
        ],
        [
          277.418,
          449.95
        ],
        [
          277.01,
          450.318
        ],
        [
          276.642,
          449.91
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-038",
      "kind": "tree",
      "centre_m": [
        290.41,
        463.41
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 284,
      "polygon_m": [
        [
          290.077,
          463.61
        ],
        [
          290.21,
          463.077
        ],
        [
          290.743,
          463.21
        ],
        [
          290.61,
          463.743
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-039",
      "kind": "tree",
      "centre_m": [
        299.77,
        464.42
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 187,
      "polygon_m": [
        [
          300.009,
          464.726
        ],
        [
          299.464,
          464.659
        ],
        [
          299.531,
          464.114
        ],
        [
          300.076,
          464.181
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-040",
      "kind": "tree",
      "centre_m": [
        281.41,
        456.65
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 315,
      "polygon_m": [
        [
          281.021,
          456.65
        ],
        [
          281.41,
          456.261
        ],
        [
          281.799,
          456.65
        ],
        [
          281.41,
          457.039
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-041",
      "kind": "tree",
      "centre_m": [
        303.15,
        452.28
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 117,
      "polygon_m": [
        [
          303.52,
          452.16
        ],
        [
          303.27,
          452.65
        ],
        [
          302.78,
          452.4
        ],
        [
          303.03,
          451.91
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-042",
      "kind": "tree",
      "centre_m": [
        258.8,
        467.59
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 300,
      "polygon_m": [
        [
          258.424,
          467.691
        ],
        [
          258.699,
          467.214
        ],
        [
          259.176,
          467.489
        ],
        [
          258.901,
          467.966
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-043",
      "kind": "tree",
      "centre_m": [
        265.87,
        461.92
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 178,
      "polygon_m": [
        [
          266.154,
          462.185
        ],
        [
          265.605,
          462.204
        ],
        [
          265.586,
          461.655
        ],
        [
          266.135,
          461.636
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-044",
      "kind": "tree",
      "centre_m": [
        304.63,
        456.64
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 169,
      "polygon_m": [
        [
          304.952,
          456.857
        ],
        [
          304.413,
          456.962
        ],
        [
          304.308,
          456.423
        ],
        [
          304.847,
          456.318
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-045",
      "kind": "tree",
      "centre_m": [
        287.96,
        452.46
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 169,
      "polygon_m": [
        [
          288.282,
          452.677
        ],
        [
          287.743,
          452.782
        ],
        [
          287.638,
          452.243
        ],
        [
          288.177,
          452.138
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-046",
      "kind": "tree",
      "centre_m": [
        304.87,
        466.84
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 14,
      "polygon_m": [
        [
          304.67,
          466.507
        ],
        [
          305.203,
          466.64
        ],
        [
          305.07,
          467.173
        ],
        [
          304.537,
          467.04
        ]
      ],
      "notes": "Exact selected planting point within green_centre. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "green_centre"
    },
    {
      "id": "02-T-047",
      "kind": "tree",
      "centre_m": [
        351.28,
        416.34
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 149,
      "polygon_m": [
        [
          351.657,
          416.434
        ],
        [
          351.186,
          416.717
        ],
        [
          350.903,
          416.246
        ],
        [
          351.374,
          415.963
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-048",
      "kind": "tree",
      "centre_m": [
        344.26,
        420.21
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 84,
      "polygon_m": [
        [
          344.505,
          419.908
        ],
        [
          344.562,
          420.455
        ],
        [
          344.015,
          420.512
        ],
        [
          343.958,
          419.965
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-049",
      "kind": "tree",
      "centre_m": [
        346.08,
        429.77
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 297,
      "polygon_m": [
        [
          345.71,
          429.89
        ],
        [
          345.96,
          429.4
        ],
        [
          346.45,
          429.65
        ],
        [
          346.2,
          430.14
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-050",
      "kind": "tree",
      "centre_m": [
        351.46,
        424.61
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 92,
      "polygon_m": [
        [
          351.744,
          424.345
        ],
        [
          351.725,
          424.894
        ],
        [
          351.176,
          424.875
        ],
        [
          351.195,
          424.326
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-051",
      "kind": "tree",
      "centre_m": [
        345.44,
        399.74
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 234,
      "polygon_m": [
        [
          345.379,
          400.124
        ],
        [
          345.056,
          399.679
        ],
        [
          345.501,
          399.356
        ],
        [
          345.824,
          399.801
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-052",
      "kind": "tree",
      "centre_m": [
        367.43,
        392.38
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 195,
      "polygon_m": [
        [
          367.624,
          392.717
        ],
        [
          367.093,
          392.574
        ],
        [
          367.236,
          392.043
        ],
        [
          367.767,
          392.186
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-053",
      "kind": "tree",
      "centre_m": [
        362.21,
        433.54
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 196,
      "polygon_m": [
        [
          362.399,
          433.88
        ],
        [
          361.87,
          433.729
        ],
        [
          362.021,
          433.2
        ],
        [
          362.55,
          433.351
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-054",
      "kind": "tree",
      "centre_m": [
        344.69,
        443.26
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 297,
      "polygon_m": [
        [
          344.32,
          443.38
        ],
        [
          344.57,
          442.89
        ],
        [
          345.06,
          443.14
        ],
        [
          344.81,
          443.63
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-055",
      "kind": "tree",
      "centre_m": [
        354.85,
        394.3
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 30,
      "polygon_m": [
        [
          354.749,
          393.924
        ],
        [
          355.226,
          394.199
        ],
        [
          354.951,
          394.676
        ],
        [
          354.474,
          394.401
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-056",
      "kind": "tree",
      "centre_m": [
        357.16,
        432.13
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 226,
      "polygon_m": [
        [
          357.153,
          432.519
        ],
        [
          356.771,
          432.123
        ],
        [
          357.167,
          431.741
        ],
        [
          357.549,
          432.137
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-057",
      "kind": "tree",
      "centre_m": [
        341.01,
        407.45
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 345,
      "polygon_m": [
        [
          340.673,
          407.256
        ],
        [
          341.204,
          407.113
        ],
        [
          341.347,
          407.644
        ],
        [
          340.816,
          407.787
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-058",
      "kind": "tree",
      "centre_m": [
        362.62,
        412.09
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 23,
      "polygon_m": [
        [
          362.474,
          411.729
        ],
        [
          362.981,
          411.944
        ],
        [
          362.766,
          412.451
        ],
        [
          362.259,
          412.236
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-059",
      "kind": "tree",
      "centre_m": [
        350.05,
        405.13
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 53,
      "polygon_m": [
        [
          350.104,
          404.745
        ],
        [
          350.435,
          405.184
        ],
        [
          349.996,
          405.515
        ],
        [
          349.665,
          405.076
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-060",
      "kind": "tree",
      "centre_m": [
        340.21,
        442.94
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 65,
      "polygon_m": [
        [
          340.343,
          442.575
        ],
        [
          340.575,
          443.073
        ],
        [
          340.077,
          443.305
        ],
        [
          339.845,
          442.807
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-061",
      "kind": "tree",
      "centre_m": [
        349.6,
        435.76
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          349.371,
          435.445
        ],
        [
          349.915,
          435.531
        ],
        [
          349.829,
          436.075
        ],
        [
          349.285,
          435.989
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-062",
      "kind": "tree",
      "centre_m": [
        345.54,
        438.04
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 233,
      "polygon_m": [
        [
          345.486,
          438.425
        ],
        [
          345.155,
          437.986
        ],
        [
          345.594,
          437.655
        ],
        [
          345.925,
          438.094
        ]
      ],
      "notes": "Exact selected planting point within grove_east. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_east"
    },
    {
      "id": "02-T-063",
      "kind": "tree",
      "centre_m": [
        321.85,
        578.66
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 8,
      "polygon_m": [
        [
          321.616,
          578.349
        ],
        [
          322.161,
          578.426
        ],
        [
          322.084,
          578.971
        ],
        [
          321.539,
          578.894
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-064",
      "kind": "tree",
      "centre_m": [
        316.52,
        594.05
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 221,
      "polygon_m": [
        [
          316.547,
          594.438
        ],
        [
          316.132,
          594.077
        ],
        [
          316.493,
          593.662
        ],
        [
          316.908,
          594.023
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-065",
      "kind": "tree",
      "centre_m": [
        274.67,
        579.24
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 9,
      "polygon_m": [
        [
          274.441,
          578.925
        ],
        [
          274.985,
          579.011
        ],
        [
          274.899,
          579.555
        ],
        [
          274.355,
          579.469
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-066",
      "kind": "tree",
      "centre_m": [
        316.95,
        585.81
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 192,
      "polygon_m": [
        [
          317.162,
          586.136
        ],
        [
          316.624,
          586.022
        ],
        [
          316.738,
          585.484
        ],
        [
          317.276,
          585.598
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-067",
      "kind": "tree",
      "centre_m": [
        289.54,
        579.56
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 165,
      "polygon_m": [
        [
          289.877,
          579.754
        ],
        [
          289.346,
          579.897
        ],
        [
          289.203,
          579.366
        ],
        [
          289.734,
          579.223
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-068",
      "kind": "tree",
      "centre_m": [
        260.14,
        595.12
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 64,
      "polygon_m": [
        [
          260.267,
          594.752
        ],
        [
          260.508,
          595.247
        ],
        [
          260.013,
          595.488
        ],
        [
          259.772,
          594.993
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-069",
      "kind": "tree",
      "centre_m": [
        310.42,
        593.43
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 202,
      "polygon_m": [
        [
          310.572,
          593.788
        ],
        [
          310.062,
          593.582
        ],
        [
          310.268,
          593.072
        ],
        [
          310.778,
          593.278
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-070",
      "kind": "tree",
      "centre_m": [
        270.21,
        579.27
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 186,
      "polygon_m": [
        [
          270.455,
          579.572
        ],
        [
          269.908,
          579.515
        ],
        [
          269.965,
          578.968
        ],
        [
          270.512,
          579.025
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-071",
      "kind": "tree",
      "centre_m": [
        285.56,
        590.29
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 213,
      "polygon_m": [
        [
          285.641,
          590.67
        ],
        [
          285.18,
          590.371
        ],
        [
          285.479,
          589.91
        ],
        [
          285.94,
          590.209
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-072",
      "kind": "tree",
      "centre_m": [
        304.81,
        585.94
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 47,
      "polygon_m": [
        [
          304.824,
          585.551
        ],
        [
          305.199,
          585.954
        ],
        [
          304.796,
          586.329
        ],
        [
          304.421,
          585.926
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-073",
      "kind": "tree",
      "centre_m": [
        302.62,
        580.62
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 98,
      "polygon_m": [
        [
          302.931,
          580.386
        ],
        [
          302.854,
          580.931
        ],
        [
          302.309,
          580.854
        ],
        [
          302.386,
          580.309
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-074",
      "kind": "tree",
      "centre_m": [
        285.08,
        580.03
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 343,
      "polygon_m": [
        [
          284.737,
          579.847
        ],
        [
          285.263,
          579.687
        ],
        [
          285.423,
          580.213
        ],
        [
          284.897,
          580.373
        ]
      ],
      "notes": "Exact selected planting point within grove_north. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "shade",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "grove_north"
    },
    {
      "id": "02-T-075",
      "kind": "tree",
      "centre_m": [
        232.46,
        588.02
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 104,
      "polygon_m": [
        [
          232.793,
          587.82
        ],
        [
          232.66,
          588.353
        ],
        [
          232.127,
          588.22
        ],
        [
          232.26,
          587.687
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-076",
      "kind": "tree",
      "centre_m": [
        209.3,
        577.44
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 287,
      "polygon_m": [
        [
          208.957,
          577.623
        ],
        [
          209.117,
          577.097
        ],
        [
          209.643,
          577.257
        ],
        [
          209.483,
          577.783
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-077",
      "kind": "tree",
      "centre_m": [
        205.26,
        575.95
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 242,
      "polygon_m": [
        [
          205.146,
          576.322
        ],
        [
          204.888,
          575.836
        ],
        [
          205.374,
          575.578
        ],
        [
          205.632,
          576.064
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-078",
      "kind": "tree",
      "centre_m": [
        222.83,
        589.56
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 96,
      "polygon_m": [
        [
          223.132,
          589.315
        ],
        [
          223.075,
          589.862
        ],
        [
          222.528,
          589.805
        ],
        [
          222.585,
          589.258
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-079",
      "kind": "tree",
      "centre_m": [
        211.3,
        594.57
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 294,
      "polygon_m": [
        [
          210.937,
          594.709
        ],
        [
          211.161,
          594.207
        ],
        [
          211.663,
          594.431
        ],
        [
          211.439,
          594.933
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-080",
      "kind": "tree",
      "centre_m": [
        213.69,
        573.41
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 358,
      "polygon_m": [
        [
          213.406,
          573.145
        ],
        [
          213.955,
          573.126
        ],
        [
          213.974,
          573.675
        ],
        [
          213.425,
          573.694
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-081",
      "kind": "tree",
      "centre_m": [
        227.37,
        589.92
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 63,
      "polygon_m": [
        [
          227.49,
          589.55
        ],
        [
          227.74,
          590.04
        ],
        [
          227.25,
          590.29
        ],
        [
          227.0,
          589.8
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-082",
      "kind": "tree",
      "centre_m": [
        201.14,
        590.0
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 326,
      "polygon_m": [
        [
          200.758,
          589.926
        ],
        [
          201.214,
          589.618
        ],
        [
          201.522,
          590.074
        ],
        [
          201.066,
          590.382
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-083",
      "kind": "tree",
      "centre_m": [
        208.62,
        584.12
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 138,
      "polygon_m": [
        [
          209.008,
          584.14
        ],
        [
          208.6,
          584.508
        ],
        [
          208.232,
          584.1
        ],
        [
          208.64,
          583.732
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-084",
      "kind": "tree",
      "centre_m": [
        219.64,
        582.08
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 325,
      "polygon_m": [
        [
          219.257,
          582.012
        ],
        [
          219.708,
          581.697
        ],
        [
          220.023,
          582.148
        ],
        [
          219.572,
          582.463
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-085",
      "kind": "tree",
      "centre_m": [
        200.87,
        578.47
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 213,
      "polygon_m": [
        [
          200.951,
          578.85
        ],
        [
          200.49,
          578.551
        ],
        [
          200.789,
          578.09
        ],
        [
          201.25,
          578.389
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-086",
      "kind": "tree",
      "centre_m": [
        236.66,
        591.83
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 175,
      "polygon_m": [
        [
          236.958,
          592.08
        ],
        [
          236.41,
          592.128
        ],
        [
          236.362,
          591.58
        ],
        [
          236.91,
          591.532
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-087",
      "kind": "tree",
      "centre_m": [
        232.99,
        594.69
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 313,
      "polygon_m": [
        [
          232.601,
          594.704
        ],
        [
          232.976,
          594.301
        ],
        [
          233.379,
          594.676
        ],
        [
          233.004,
          595.079
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-088",
      "kind": "tree",
      "centre_m": [
        241.22,
        588.13
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 168,
      "polygon_m": [
        [
          241.546,
          588.342
        ],
        [
          241.008,
          588.456
        ],
        [
          240.894,
          587.918
        ],
        [
          241.432,
          587.804
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-089",
      "kind": "tree",
      "centre_m": [
        216.33,
        578.71
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 61,
      "polygon_m": [
        [
          216.437,
          578.336
        ],
        [
          216.704,
          578.817
        ],
        [
          216.223,
          579.084
        ],
        [
          215.956,
          578.603
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-090",
      "kind": "tree",
      "centre_m": [
        231.09,
        573.53
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 250,
      "polygon_m": [
        [
          230.926,
          573.882
        ],
        [
          230.738,
          573.366
        ],
        [
          231.254,
          573.178
        ],
        [
          231.442,
          573.694
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-091",
      "kind": "tree",
      "centre_m": [
        225.0,
        573.4
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 151,
      "polygon_m": [
        [
          225.374,
          573.507
        ],
        [
          224.893,
          573.774
        ],
        [
          224.626,
          573.293
        ],
        [
          225.107,
          573.026
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-092",
      "kind": "tree",
      "centre_m": [
        209.14,
        590.34
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 197,
      "polygon_m": [
        [
          209.323,
          590.683
        ],
        [
          208.797,
          590.523
        ],
        [
          208.957,
          589.997
        ],
        [
          209.483,
          590.157
        ]
      ],
      "notes": "Exact selected planting point within orchard_trees. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "orchard_trees"
    },
    {
      "id": "02-T-093",
      "kind": "tree",
      "centre_m": [
        272.18,
        513.47
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 232,
      "polygon_m": [
        [
          272.133,
          513.856
        ],
        [
          271.794,
          513.423
        ],
        [
          272.227,
          513.084
        ],
        [
          272.566,
          513.517
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-094",
      "kind": "tree",
      "centre_m": [
        316.86,
        507.61
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 61,
      "polygon_m": [
        [
          316.967,
          507.236
        ],
        [
          317.234,
          507.717
        ],
        [
          316.753,
          507.984
        ],
        [
          316.486,
          507.503
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-095",
      "kind": "tree",
      "centre_m": [
        324.98,
        536.97
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 158,
      "polygon_m": [
        [
          325.338,
          537.122
        ],
        [
          324.828,
          537.328
        ],
        [
          324.622,
          536.818
        ],
        [
          325.132,
          536.612
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-096",
      "kind": "tree",
      "centre_m": [
        302.9,
        518.69
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 48,
      "polygon_m": [
        [
          302.92,
          518.302
        ],
        [
          303.288,
          518.71
        ],
        [
          302.88,
          519.078
        ],
        [
          302.512,
          518.67
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-097",
      "kind": "tree",
      "centre_m": [
        329.38,
        515.55
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 230,
      "polygon_m": [
        [
          329.346,
          515.937
        ],
        [
          328.993,
          515.516
        ],
        [
          329.414,
          515.163
        ],
        [
          329.767,
          515.584
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-098",
      "kind": "tree",
      "centre_m": [
        309.56,
        573.73
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 130,
      "polygon_m": [
        [
          309.947,
          573.696
        ],
        [
          309.594,
          574.117
        ],
        [
          309.173,
          573.764
        ],
        [
          309.526,
          573.343
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-099",
      "kind": "tree",
      "centre_m": [
        295.11,
        513.81
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 333,
      "polygon_m": [
        [
          294.74,
          513.69
        ],
        [
          295.23,
          513.44
        ],
        [
          295.48,
          513.93
        ],
        [
          294.99,
          514.18
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-100",
      "kind": "tree",
      "centre_m": [
        215.17,
        515.5
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 102,
      "polygon_m": [
        [
          215.496,
          515.288
        ],
        [
          215.382,
          515.826
        ],
        [
          214.844,
          515.712
        ],
        [
          214.958,
          515.174
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-101",
      "kind": "tree",
      "centre_m": [
        299.41,
        562.63
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 180,
      "polygon_m": [
        [
          299.685,
          562.905
        ],
        [
          299.135,
          562.905
        ],
        [
          299.135,
          562.355
        ],
        [
          299.685,
          562.355
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-102",
      "kind": "tree",
      "centre_m": [
        214.92,
        535.5
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 274,
      "polygon_m": [
        [
          214.626,
          535.755
        ],
        [
          214.665,
          535.206
        ],
        [
          215.214,
          535.245
        ],
        [
          215.175,
          535.794
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-103",
      "kind": "tree",
      "centre_m": [
        277.02,
        527.6
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 193,
      "polygon_m": [
        [
          277.226,
          527.93
        ],
        [
          276.69,
          527.806
        ],
        [
          276.814,
          527.27
        ],
        [
          277.35,
          527.394
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-104",
      "kind": "tree",
      "centre_m": [
        209.15,
        529.5
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 325,
      "polygon_m": [
        [
          208.767,
          529.432
        ],
        [
          209.218,
          529.117
        ],
        [
          209.533,
          529.568
        ],
        [
          209.082,
          529.883
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-105",
      "kind": "tree",
      "centre_m": [
        187.63,
        563.93
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 141,
      "polygon_m": [
        [
          188.017,
          563.971
        ],
        [
          187.589,
          564.317
        ],
        [
          187.243,
          563.889
        ],
        [
          187.671,
          563.543
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-106",
      "kind": "tree",
      "centre_m": [
        320.89,
        532.39
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 2,
      "polygon_m": [
        [
          320.625,
          532.106
        ],
        [
          321.174,
          532.125
        ],
        [
          321.155,
          532.674
        ],
        [
          320.606,
          532.655
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-107",
      "kind": "tree",
      "centre_m": [
        237.99,
        553.92
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 100,
      "polygon_m": [
        [
          238.309,
          553.697
        ],
        [
          238.213,
          554.239
        ],
        [
          237.671,
          554.143
        ],
        [
          237.767,
          553.601
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-108",
      "kind": "tree",
      "centre_m": [
        191.32,
        569.31
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 141,
      "polygon_m": [
        [
          191.707,
          569.351
        ],
        [
          191.279,
          569.697
        ],
        [
          190.933,
          569.269
        ],
        [
          191.361,
          568.923
        ]
      ],
      "notes": "Exact selected planting point within household_fruit. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "fruit",
      "crown_diameter_m": 3.8,
      "crown_start_height_m": 2.5,
      "height_m": 5,
      "planting_group": "household_fruit"
    },
    {
      "id": "02-T-109",
      "kind": "tree",
      "centre_m": [
        213.42,
        448.01
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 142,
      "polygon_m": [
        [
          213.806,
          448.057
        ],
        [
          213.373,
          448.396
        ],
        [
          213.034,
          447.963
        ],
        [
          213.467,
          447.624
        ]
      ],
      "notes": "Exact selected planting point within pond_willows. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "willow",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "pond_willows"
    },
    {
      "id": "02-T-110",
      "kind": "tree",
      "centre_m": [
        169.36,
        468.58
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 268,
      "polygon_m": [
        [
          169.095,
          468.864
        ],
        [
          169.076,
          468.315
        ],
        [
          169.625,
          468.296
        ],
        [
          169.644,
          468.845
        ]
      ],
      "notes": "Exact selected planting point within pond_willows. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "willow",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "pond_willows"
    },
    {
      "id": "02-T-111",
      "kind": "tree",
      "centre_m": [
        222.56,
        471.28
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 183,
      "polygon_m": [
        [
          222.82,
          471.569
        ],
        [
          222.271,
          471.54
        ],
        [
          222.3,
          470.991
        ],
        [
          222.849,
          471.02
        ]
      ],
      "notes": "Exact selected planting point within pond_willows. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "willow",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "pond_willows"
    },
    {
      "id": "02-T-112",
      "kind": "tree",
      "centre_m": [
        216.16,
        453.47
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 92,
      "polygon_m": [
        [
          216.444,
          453.205
        ],
        [
          216.425,
          453.754
        ],
        [
          215.876,
          453.735
        ],
        [
          215.895,
          453.186
        ]
      ],
      "notes": "Exact selected planting point within pond_willows. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "willow",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "pond_willows"
    },
    {
      "id": "02-T-113",
      "kind": "tree",
      "centre_m": [
        212.72,
        482.24
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 212,
      "polygon_m": [
        [
          212.807,
          482.619
        ],
        [
          212.341,
          482.327
        ],
        [
          212.633,
          481.861
        ],
        [
          213.099,
          482.153
        ]
      ],
      "notes": "Exact selected planting point within pond_willows. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "willow",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "pond_willows"
    },
    {
      "id": "02-T-114",
      "kind": "tree",
      "centre_m": [
        221.95,
        459.54
      ],
      "size_m": [
        0.55,
        0.55
      ],
      "rotation_deg": 320,
      "polygon_m": [
        [
          221.563,
          459.506
        ],
        [
          221.984,
          459.153
        ],
        [
          222.337,
          459.574
        ],
        [
          221.916,
          459.927
        ]
      ],
      "notes": "Exact selected planting point within pond_willows. Collision is trunk only; crowns above eye/van height.",
      "hard_obstacle": true,
      "tree_type": "willow",
      "crown_diameter_m": 5,
      "crown_start_height_m": 3.2,
      "height_m": 9,
      "planting_group": "pond_willows"
    },
    {
      "id": "02-S-01",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        167.0,
        562.0
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          166.1,
          561.3
        ],
        [
          167.9,
          561.3
        ],
        [
          167.9,
          562.7
        ],
        [
          166.1,
          562.7
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H01"
    },
    {
      "id": "02-S-02",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        175.88,
        566.77
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 137,
      "polygon_m": [
        [
          177.162,
          566.532
        ],
        [
          175.553,
          568.032
        ],
        [
          174.598,
          567.008
        ],
        [
          176.207,
          565.508
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H02"
    },
    {
      "id": "02-S-03",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        211.31,
        561.51
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 7,
      "polygon_m": [
        [
          210.105,
          560.657
        ],
        [
          212.686,
          560.974
        ],
        [
          212.515,
          562.363
        ],
        [
          209.934,
          562.046
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H03"
    },
    {
      "id": "02-S-04",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        200.41,
        544.44
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 51,
      "polygon_m": [
        [
          200.388,
          543.3
        ],
        [
          201.52,
          544.699
        ],
        [
          200.432,
          545.58
        ],
        [
          199.3,
          544.181
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H04"
    },
    {
      "id": "02-S-05",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        213.37,
        510.83
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 281,
      "polygon_m": [
        [
          212.473,
          511.776
        ],
        [
          212.893,
          509.617
        ],
        [
          214.267,
          509.884
        ],
        [
          213.847,
          512.043
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H05"
    },
    {
      "id": "02-S-06",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        253.78,
        556.39
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 356,
      "polygon_m": [
        [
          252.434,
          555.782
        ],
        [
          255.028,
          555.601
        ],
        [
          255.126,
          556.998
        ],
        [
          252.532,
          557.179
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H06"
    },
    {
      "id": "02-S-07",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        240.81,
        579.92
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 164,
      "polygon_m": [
        [
          241.868,
          580.345
        ],
        [
          240.138,
          580.841
        ],
        [
          239.752,
          579.495
        ],
        [
          241.482,
          578.999
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H07"
    },
    {
      "id": "02-S-08",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        303.39,
        553.0
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 239,
      "polygon_m": [
        [
          303.357,
          554.303
        ],
        [
          302.223,
          552.418
        ],
        [
          303.423,
          551.697
        ],
        [
          304.557,
          553.582
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H08"
    },
    {
      "id": "02-S-09",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        322.73,
        524.93
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 16,
      "polygon_m": [
        [
          321.673,
          523.899
        ],
        [
          324.173,
          524.615
        ],
        [
          323.787,
          525.961
        ],
        [
          321.287,
          525.245
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H09"
    },
    {
      "id": "02-S-10",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        277.76,
        519.18
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 153,
      "polygon_m": [
        [
          278.88,
          519.395
        ],
        [
          277.276,
          520.212
        ],
        [
          276.64,
          518.965
        ],
        [
          278.244,
          518.148
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H10"
    },
    {
      "id": "02-S-11",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        282.39,
        469.42
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 290,
      "polygon_m": [
        [
          281.356,
          470.214
        ],
        [
          282.108,
          468.147
        ],
        [
          283.424,
          468.626
        ],
        [
          282.672,
          470.693
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H11"
    },
    {
      "id": "02-S-12",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        304.33,
        480.24
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 129,
      "polygon_m": [
        [
          305.692,
          479.67
        ],
        [
          304.056,
          481.691
        ],
        [
          302.968,
          480.81
        ],
        [
          304.604,
          478.789
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H12"
    },
    {
      "id": "02-S-13",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        345.61,
        459.15
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 204,
      "polygon_m": [
        [
          346.147,
          460.156
        ],
        [
          344.503,
          459.423
        ],
        [
          345.073,
          458.144
        ],
        [
          346.717,
          458.877
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H13"
    },
    {
      "id": "02-S-14",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        268.61,
        457.83
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          267.68,
          456.917
        ],
        [
          269.832,
          457.374
        ],
        [
          269.54,
          458.743
        ],
        [
          267.388,
          458.286
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H14"
    },
    {
      "id": "02-S-15",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        268.71,
        441.18
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 118,
      "polygon_m": [
        [
          269.938,
          440.361
        ],
        [
          268.718,
          442.656
        ],
        [
          267.482,
          441.999
        ],
        [
          268.702,
          439.704
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H15"
    },
    {
      "id": "02-S-16",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        288.43,
        403.54
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 286,
      "polygon_m": [
        [
          287.509,
          404.212
        ],
        [
          288.005,
          402.482
        ],
        [
          289.351,
          402.868
        ],
        [
          288.855,
          404.598
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H16"
    },
    {
      "id": "02-S-17",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        315.0,
        425.84
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 63,
      "polygon_m": [
        [
          315.124,
          424.542
        ],
        [
          316.123,
          426.502
        ],
        [
          314.876,
          427.138
        ],
        [
          313.877,
          425.178
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H17"
    },
    {
      "id": "02-S-18",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        343.33,
        402.76
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 231,
      "polygon_m": [
        [
          343.604,
          404.211
        ],
        [
          341.968,
          402.19
        ],
        [
          343.056,
          401.309
        ],
        [
          344.692,
          403.33
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H18"
    },
    {
      "id": "02-S-19",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        219.11,
        426.34
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 306,
      "polygon_m": [
        [
          218.015,
          426.657
        ],
        [
          219.073,
          425.2
        ],
        [
          220.205,
          426.023
        ],
        [
          219.147,
          427.48
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H19"
    },
    {
      "id": "02-S-20",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        160.85,
        568.95
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 83,
      "polygon_m": [
        [
          161.411,
          567.773
        ],
        [
          161.679,
          569.956
        ],
        [
          160.289,
          570.127
        ],
        [
          160.021,
          567.944
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H01"
    },
    {
      "id": "02-S-21",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        196.45,
        566.14
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 15,
      "polygon_m": [
        [
          195.375,
          565.127
        ],
        [
          197.887,
          565.8
        ],
        [
          197.525,
          567.153
        ],
        [
          195.013,
          566.48
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H02"
    },
    {
      "id": "02-S-22",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        205.99,
        559.63
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 357,
      "polygon_m": [
        [
          205.055,
          558.978
        ],
        [
          206.852,
          558.884
        ],
        [
          206.925,
          560.282
        ],
        [
          205.128,
          560.376
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H03"
    },
    {
      "id": "02-S-23",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        187.5,
        541.28
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 165,
      "polygon_m": [
        [
          188.744,
          541.671
        ],
        [
          186.619,
          542.241
        ],
        [
          186.256,
          540.889
        ],
        [
          188.381,
          540.319
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H04"
    },
    {
      "id": "02-S-24",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        211.12,
        516.0
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 271,
      "polygon_m": [
        [
          210.397,
          517.288
        ],
        [
          210.443,
          514.688
        ],
        [
          211.843,
          514.712
        ],
        [
          211.797,
          517.312
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H05"
    },
    {
      "id": "02-S-25",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        235.36,
        564.8
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 141,
      "polygon_m": [
        [
          236.5,
          564.778
        ],
        [
          235.101,
          565.91
        ],
        [
          234.22,
          564.822
        ],
        [
          235.619,
          563.69
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H06"
    },
    {
      "id": "02-S-26",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        244.03,
        576.39
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 185,
      "polygon_m": [
        [
          245.065,
          577.183
        ],
        [
          242.873,
          576.991
        ],
        [
          242.995,
          575.597
        ],
        [
          245.187,
          575.789
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H07"
    },
    {
      "id": "02-S-27",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        299.74,
        573.26
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 117,
      "polygon_m": [
        [
          300.954,
          572.419
        ],
        [
          299.774,
          574.736
        ],
        [
          298.526,
          574.101
        ],
        [
          299.706,
          571.784
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H08"
    },
    {
      "id": "02-S-28",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        310.34,
        529.74
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 130,
      "polygon_m": [
        [
          311.455,
          529.501
        ],
        [
          310.298,
          530.879
        ],
        [
          309.225,
          529.979
        ],
        [
          310.382,
          528.601
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H09"
    },
    {
      "id": "02-S-29",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        288.98,
        506.64
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 298,
      "polygon_m": [
        [
          287.846,
          507.283
        ],
        [
          288.878,
          505.34
        ],
        [
          290.114,
          505.997
        ],
        [
          289.082,
          507.94
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H10"
    },
    {
      "id": "02-S-30",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        286.82,
        477.57
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 13,
      "polygon_m": [
        [
          285.711,
          476.596
        ],
        [
          288.244,
          477.18
        ],
        [
          287.929,
          478.544
        ],
        [
          285.396,
          477.96
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H11"
    },
    {
      "id": "02-S-31",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        304.94,
        475.5
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 150,
      "polygon_m": [
        [
          306.069,
          475.656
        ],
        [
          304.511,
          476.556
        ],
        [
          303.811,
          475.344
        ],
        [
          305.369,
          474.444
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H12"
    },
    {
      "id": "02-S-32",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        354.05,
        455.31
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 287,
      "polygon_m": [
        [
          353.059,
          456.157
        ],
        [
          353.702,
          454.053
        ],
        [
          355.041,
          454.463
        ],
        [
          354.398,
          456.567
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H13"
    },
    {
      "id": "02-S-33",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        263.07,
        462.29
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 64,
      "polygon_m": [
        [
          263.129,
          460.815
        ],
        [
          264.269,
          463.152
        ],
        [
          263.011,
          463.765
        ],
        [
          261.871,
          461.428
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H14"
    },
    {
      "id": "02-S-34",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        265.46,
        432.49
      ],
      "size_m": [
        1.8,
        1.4
      ],
      "rotation_deg": 201,
      "polygon_m": [
        [
          266.049,
          433.466
        ],
        [
          264.369,
          432.821
        ],
        [
          264.871,
          431.514
        ],
        [
          266.551,
          432.159
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.0,
      "parent": "02-H15"
    },
    {
      "id": "02-S-35",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        292.49,
        409.38
      ],
      "size_m": [
        2.2,
        1.4
      ],
      "rotation_deg": 338,
      "polygon_m": [
        [
          291.208,
          409.143
        ],
        [
          293.248,
          408.319
        ],
        [
          293.772,
          409.617
        ],
        [
          291.732,
          410.441
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.25,
      "parent": "02-H16"
    },
    {
      "id": "02-S-36",
      "kind": "soft_shrub_cluster",
      "centre_m": [
        300.05,
        412.18
      ],
      "size_m": [
        2.6,
        1.4
      ],
      "rotation_deg": 208,
      "polygon_m": [
        [
          300.869,
          413.408
        ],
        [
          298.574,
          412.188
        ],
        [
          299.231,
          410.952
        ],
        [
          301.526,
          412.172
        ]
      ],
      "notes": "Lilac/elderberry/berry shrubs; open gaps, walkable and van-passable; no invisible hedge collider.",
      "hard_obstacle": false,
      "height_m": 1.5,
      "parent": "02-H17"
    },
    {
      "id": "02-D-001",
      "kind": "stump",
      "centre_m": [
        167.02,
        569.6
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          166.77,
          569.35
        ],
        [
          167.27,
          569.35
        ],
        [
          167.27,
          569.85
        ],
        [
          166.77,
          569.85
        ]
      ],
      "notes": "Chopping stump at working yards.",
      "hard_obstacle": true,
      "parent": "02-H01-Y3",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-002",
      "kind": "stump",
      "centre_m": [
        197.07,
        532.2
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 80,
      "polygon_m": [
        [
          197.273,
          531.91
        ],
        [
          197.36,
          532.403
        ],
        [
          196.867,
          532.49
        ],
        [
          196.78,
          531.997
        ]
      ],
      "notes": "Chopping stump at working yards.",
      "hard_obstacle": true,
      "parent": "02-H04-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-003",
      "kind": "stump",
      "centre_m": [
        249.1,
        564.3
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 160,
      "polygon_m": [
        [
          249.42,
          564.449
        ],
        [
          248.951,
          564.62
        ],
        [
          248.78,
          564.151
        ],
        [
          249.249,
          563.98
        ]
      ],
      "notes": "Chopping stump at working yards.",
      "hard_obstacle": true,
      "parent": "02-H06-Y3",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-004",
      "kind": "watering_can",
      "centre_m": [
        180.38,
        574.43
      ],
      "size_m": [
        0.35,
        0.25
      ],
      "rotation_deg": 79,
      "polygon_m": [
        [
          180.469,
          574.234
        ],
        [
          180.536,
          574.578
        ],
        [
          180.291,
          574.626
        ],
        [
          180.224,
          574.282
        ]
      ],
      "notes": "Next to vegetable plots.",
      "hard_obstacle": false,
      "parent": "02-H02-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-005",
      "kind": "watering_can",
      "centre_m": [
        204.07,
        517.79
      ],
      "size_m": [
        0.35,
        0.25
      ],
      "rotation_deg": 130,
      "polygon_m": [
        [
          204.278,
          517.736
        ],
        [
          204.053,
          518.004
        ],
        [
          203.862,
          517.844
        ],
        [
          204.087,
          517.576
        ]
      ],
      "notes": "Next to vegetable plots.",
      "hard_obstacle": false,
      "parent": "02-H05-Y3",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-006",
      "kind": "watering_can",
      "centre_m": [
        255.79,
        581.18
      ],
      "size_m": [
        0.35,
        0.25
      ],
      "rotation_deg": 297,
      "polygon_m": [
        [
          255.599,
          581.279
        ],
        [
          255.758,
          580.967
        ],
        [
          255.981,
          581.081
        ],
        [
          255.822,
          581.393
        ]
      ],
      "notes": "Next to vegetable plots.",
      "hard_obstacle": false,
      "parent": "02-H07-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-007",
      "kind": "watering_can",
      "centre_m": [
        322.09,
        513.31
      ],
      "size_m": [
        0.35,
        0.25
      ],
      "rotation_deg": 348,
      "polygon_m": [
        [
          321.893,
          513.224
        ],
        [
          322.235,
          513.151
        ],
        [
          322.287,
          513.396
        ],
        [
          321.945,
          513.469
        ]
      ],
      "notes": "Next to vegetable plots.",
      "hard_obstacle": false,
      "parent": "02-H09-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-008",
      "kind": "watering_can",
      "centre_m": [
        274.13,
        473.66
      ],
      "size_m": [
        0.35,
        0.25
      ],
      "rotation_deg": 97,
      "polygon_m": [
        [
          274.275,
          473.502
        ],
        [
          274.233,
          473.849
        ],
        [
          273.985,
          473.818
        ],
        [
          274.027,
          473.471
        ]
      ],
      "notes": "Next to vegetable plots.",
      "hard_obstacle": false,
      "parent": "02-H11-Y2",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-009",
      "kind": "wheelbarrow",
      "centre_m": [
        163.91,
        567.8
      ],
      "size_m": [
        1.4,
        0.6
      ],
      "rotation_deg": 56,
      "polygon_m": [
        [
          163.767,
          567.052
        ],
        [
          164.55,
          568.213
        ],
        [
          164.053,
          568.548
        ],
        [
          163.27,
          567.387
        ]
      ],
      "notes": "Working farm yards.",
      "hard_obstacle": true,
      "parent": "02-H01",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-010",
      "kind": "wooden_crate",
      "centre_m": [
        222.5,
        585.46
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 63,
      "polygon_m": [
        [
          222.542,
          585.102
        ],
        [
          222.814,
          585.637
        ],
        [
          222.458,
          585.818
        ],
        [
          222.186,
          585.283
        ]
      ],
      "notes": "Orchard produce and shop storage.",
      "hard_obstacle": true,
      "parent": "02-U-ORCHARD",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-011",
      "kind": "wooden_crate",
      "centre_m": [
        219.74,
        584.82
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 143,
      "polygon_m": [
        [
          220.1,
          584.799
        ],
        [
          219.621,
          585.16
        ],
        [
          219.38,
          584.841
        ],
        [
          219.859,
          584.48
        ]
      ],
      "notes": "Orchard produce and shop storage.",
      "hard_obstacle": true,
      "parent": "02-U-ORCHARD",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-012",
      "kind": "wooden_crate",
      "centre_m": [
        220.6,
        580.74
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 252,
      "polygon_m": [
        [
          220.502,
          581.087
        ],
        [
          220.317,
          580.516
        ],
        [
          220.698,
          580.393
        ],
        [
          220.883,
          580.964
        ]
      ],
      "notes": "Orchard produce and shop storage.",
      "hard_obstacle": true,
      "parent": "02-U-ORCHARD",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-013",
      "kind": "wooden_crate",
      "centre_m": [
        222.7,
        581.65
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 303,
      "polygon_m": [
        [
          222.369,
          581.793
        ],
        [
          222.696,
          581.289
        ],
        [
          223.031,
          581.507
        ],
        [
          222.704,
          582.011
        ]
      ],
      "notes": "Orchard produce and shop storage.",
      "hard_obstacle": true,
      "parent": "02-U-ORCHARD",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-014",
      "kind": "wooden_crate",
      "centre_m": [
        223.53,
        584.36
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 23,
      "polygon_m": [
        [
          223.332,
          584.059
        ],
        [
          223.884,
          584.293
        ],
        [
          223.728,
          584.661
        ],
        [
          223.176,
          584.427
        ]
      ],
      "notes": "Orchard produce and shop storage.",
      "hard_obstacle": true,
      "parent": "02-U-ORCHARD",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-015",
      "kind": "wooden_crate",
      "centre_m": [
        221.01,
        585.64
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 103,
      "polygon_m": [
        [
          221.272,
          585.393
        ],
        [
          221.137,
          585.977
        ],
        [
          220.748,
          585.887
        ],
        [
          220.883,
          585.303
        ]
      ],
      "notes": "Orchard produce and shop storage.",
      "hard_obstacle": true,
      "parent": "02-U-ORCHARD",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-016",
      "kind": "feed_sack",
      "centre_m": [
        202.01,
        521.95
      ],
      "size_m": [
        0.5,
        0.3
      ],
      "rotation_deg": 105,
      "polygon_m": [
        [
          202.22,
          521.747
        ],
        [
          202.09,
          522.23
        ],
        [
          201.8,
          522.153
        ],
        [
          201.93,
          521.67
        ]
      ],
      "notes": "Dry shelter beside pigs or chickens.",
      "hard_obstacle": false,
      "parent": "02-H05-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-017",
      "kind": "feed_sack",
      "centre_m": [
        309.49,
        462.84
      ],
      "size_m": [
        0.5,
        0.3
      ],
      "rotation_deg": 185,
      "polygon_m": [
        [
          309.726,
          463.011
        ],
        [
          309.228,
          462.968
        ],
        [
          309.254,
          462.669
        ],
        [
          309.752,
          462.712
        ]
      ],
      "notes": "Dry shelter beside pigs or chickens.",
      "hard_obstacle": false,
      "parent": "02-H12-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-018",
      "kind": "feed_sack",
      "centre_m": [
        301.87,
        416.87
      ],
      "size_m": [
        0.5,
        0.3
      ],
      "rotation_deg": 265,
      "polygon_m": [
        [
          301.742,
          417.132
        ],
        [
          301.699,
          416.634
        ],
        [
          301.998,
          416.608
        ],
        [
          302.041,
          417.106
        ]
      ],
      "notes": "Dry shelter beside pigs or chickens.",
      "hard_obstacle": false,
      "parent": "02-H17-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-019",
      "kind": "feed_sack",
      "centre_m": [
        205.39,
        520.52
      ],
      "size_m": [
        0.5,
        0.3
      ],
      "rotation_deg": 14,
      "polygon_m": [
        [
          205.184,
          520.314
        ],
        [
          205.669,
          520.435
        ],
        [
          205.596,
          520.726
        ],
        [
          205.111,
          520.605
        ]
      ],
      "notes": "Dry shelter beside pigs or chickens.",
      "hard_obstacle": false,
      "parent": "02-H05-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-020",
      "kind": "feed_sack",
      "centre_m": [
        312.61,
        465.02
      ],
      "size_m": [
        0.5,
        0.3
      ],
      "rotation_deg": 65,
      "polygon_m": [
        [
          312.64,
          464.73
        ],
        [
          312.852,
          465.183
        ],
        [
          312.58,
          465.31
        ],
        [
          312.368,
          464.857
        ]
      ],
      "notes": "Dry shelter beside pigs or chickens.",
      "hard_obstacle": false,
      "parent": "02-H12-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-021",
      "kind": "chicken_feeder",
      "centre_m": [
        194.22,
        569.34
      ],
      "size_m": [
        0.45,
        0.45
      ],
      "rotation_deg": 169,
      "polygon_m": [
        [
          194.484,
          569.518
        ],
        [
          194.042,
          569.604
        ],
        [
          193.956,
          569.162
        ],
        [
          194.398,
          569.076
        ]
      ],
      "notes": "Beside coops.",
      "hard_obstacle": false,
      "parent": "02-H03-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-022",
      "kind": "chicken_feeder",
      "centre_m": [
        278.84,
        464.29
      ],
      "size_m": [
        0.45,
        0.45
      ],
      "rotation_deg": 249,
      "polygon_m": [
        [
          278.711,
          464.581
        ],
        [
          278.549,
          464.161
        ],
        [
          278.969,
          463.999
        ],
        [
          279.131,
          464.419
        ]
      ],
      "notes": "Beside coops.",
      "hard_obstacle": false,
      "parent": "02-H11-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-023",
      "kind": "chicken_feeder",
      "centre_m": [
        288.63,
        418.96
      ],
      "size_m": [
        0.45,
        0.45
      ],
      "rotation_deg": 300,
      "polygon_m": [
        [
          288.323,
          419.042
        ],
        [
          288.548,
          418.653
        ],
        [
          288.937,
          418.878
        ],
        [
          288.712,
          419.267
        ]
      ],
      "notes": "Beside coops.",
      "hard_obstacle": false,
      "parent": "02-H16-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-024",
      "kind": "egg_basket",
      "centre_m": [
        194.99,
        569.51
      ],
      "size_m": [
        0.4,
        0.3
      ],
      "rotation_deg": 161,
      "polygon_m": [
        [
          195.228,
          569.587
        ],
        [
          194.85,
          569.717
        ],
        [
          194.752,
          569.433
        ],
        [
          195.13,
          569.303
        ]
      ],
      "notes": "At poultry yards, visual only.",
      "hard_obstacle": false,
      "parent": "02-H03-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-025",
      "kind": "egg_basket",
      "centre_m": [
        278.81,
        465.08
      ],
      "size_m": [
        0.4,
        0.3
      ],
      "rotation_deg": 241,
      "polygon_m": [
        [
          278.776,
          465.328
        ],
        [
          278.582,
          464.978
        ],
        [
          278.844,
          464.832
        ],
        [
          279.038,
          465.182
        ]
      ],
      "notes": "At poultry yards, visual only.",
      "hard_obstacle": false,
      "parent": "02-H11-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-026",
      "kind": "egg_basket",
      "centre_m": [
        289.24,
        419.49
      ],
      "size_m": [
        0.4,
        0.3
      ],
      "rotation_deg": 321,
      "polygon_m": [
        [
          288.99,
          419.499
        ],
        [
          289.301,
          419.248
        ],
        [
          289.49,
          419.481
        ],
        [
          289.179,
          419.732
        ]
      ],
      "notes": "At poultry yards, visual only.",
      "hard_obstacle": false,
      "parent": "02-H16-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-027",
      "kind": "wash_basin",
      "centre_m": [
        186.72,
        566.2
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 182,
      "polygon_m": [
        [
          186.961,
          566.459
        ],
        [
          186.461,
          566.441
        ],
        [
          186.479,
          565.941
        ],
        [
          186.979,
          565.959
        ]
      ],
      "notes": "Laundry households.",
      "hard_obstacle": false,
      "parent": "02-H02-Y3",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-028",
      "kind": "wash_basin",
      "centre_m": [
        257.71,
        580.45
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 262,
      "polygon_m": [
        [
          257.497,
          580.732
        ],
        [
          257.428,
          580.237
        ],
        [
          257.923,
          580.168
        ],
        [
          257.992,
          580.663
        ]
      ],
      "notes": "Laundry households.",
      "hard_obstacle": false,
      "parent": "02-H07-Y3",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-029",
      "kind": "wash_basin",
      "centre_m": [
        324.68,
        516.19
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 342,
      "polygon_m": [
        [
          324.365,
          516.029
        ],
        [
          324.841,
          515.875
        ],
        [
          324.995,
          516.351
        ],
        [
          324.519,
          516.505
        ]
      ],
      "notes": "Laundry households.",
      "hard_obstacle": false,
      "parent": "02-H09-Y3",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-030",
      "kind": "chair",
      "centre_m": [
        149.38,
        563.83
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 203,
      "polygon_m": [
        [
          149.512,
          564.158
        ],
        [
          149.052,
          563.962
        ],
        [
          149.248,
          563.502
        ],
        [
          149.708,
          563.698
        ]
      ],
      "notes": "By outdoor tables.",
      "hard_obstacle": true,
      "parent": "02-H01-Y4",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-031",
      "kind": "chair",
      "centre_m": [
        202.2,
        529.91
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 283,
      "polygon_m": [
        [
          201.9,
          530.097
        ],
        [
          202.013,
          529.61
        ],
        [
          202.5,
          529.723
        ],
        [
          202.387,
          530.21
        ]
      ],
      "notes": "By outdoor tables.",
      "hard_obstacle": true,
      "parent": "02-H04-Y4",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-032",
      "kind": "chair",
      "centre_m": [
        239.27,
        561.38
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 3,
      "polygon_m": [
        [
          239.033,
          561.117
        ],
        [
          239.533,
          561.143
        ],
        [
          239.507,
          561.643
        ],
        [
          239.007,
          561.617
        ]
      ],
      "notes": "By outdoor tables.",
      "hard_obstacle": true,
      "parent": "02-H06-Y4",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-033",
      "kind": "chair",
      "centre_m": [
        275.81,
        515.1
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 83,
      "polygon_m": [
        [
          276.028,
          514.821
        ],
        [
          276.089,
          515.318
        ],
        [
          275.592,
          515.379
        ],
        [
          275.531,
          514.882
        ]
      ],
      "notes": "By outdoor tables.",
      "hard_obstacle": true,
      "parent": "02-H10-Y4",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-034",
      "kind": "chair",
      "centre_m": [
        342.33,
        457.77
      ],
      "size_m": [
        0.5,
        0.5
      ],
      "rotation_deg": 163,
      "polygon_m": [
        [
          342.642,
          457.936
        ],
        [
          342.164,
          458.082
        ],
        [
          342.018,
          457.604
        ],
        [
          342.496,
          457.458
        ]
      ],
      "notes": "By outdoor tables.",
      "hard_obstacle": true,
      "parent": "02-H13-Y4",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-035",
      "kind": "bench",
      "centre_m": [
        156.29,
        556.06
      ],
      "size_m": [
        1.8,
        0.5
      ],
      "rotation_deg": 238,
      "polygon_m": [
        [
          156.555,
          556.956
        ],
        [
          155.601,
          555.429
        ],
        [
          156.025,
          555.164
        ],
        [
          156.979,
          556.691
        ]
      ],
      "notes": "Shop, yard and pond bank seats.",
      "hard_obstacle": true,
      "parent": "02-H01",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-036",
      "kind": "bench",
      "centre_m": [
        186.2,
        557.32
      ],
      "size_m": [
        1.8,
        0.5
      ],
      "rotation_deg": 318,
      "polygon_m": [
        [
          185.364,
          557.736
        ],
        [
          186.702,
          556.532
        ],
        [
          187.036,
          556.904
        ],
        [
          185.698,
          558.108
        ]
      ],
      "notes": "Shop, yard and pond bank seats.",
      "hard_obstacle": true,
      "parent": "02-H02",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-037",
      "kind": "flower_strip",
      "centre_m": [
        157.84,
        555.34
      ],
      "size_m": [
        3,
        1
      ],
      "rotation_deg": 252,
      "polygon_m": [
        [
          157.828,
          556.921
        ],
        [
          156.901,
          554.068
        ],
        [
          157.852,
          553.759
        ],
        [
          158.779,
          556.612
        ]
      ],
      "notes": "Uneven care, some yards have none.",
      "hard_obstacle": false,
      "parent": "02-H01",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-038",
      "kind": "flower_strip",
      "centre_m": [
        187.18,
        558.71
      ],
      "size_m": [
        3,
        1
      ],
      "rotation_deg": 332,
      "polygon_m": [
        [
          185.621,
          558.973
        ],
        [
          188.27,
          557.564
        ],
        [
          188.739,
          558.447
        ],
        [
          186.09,
          559.856
        ]
      ],
      "notes": "Uneven care, some yards have none.",
      "hard_obstacle": false,
      "parent": "02-H02",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-039",
      "kind": "flower_pot",
      "centre_m": [
        159.44,
        568.8
      ],
      "size_m": [
        0.35,
        0.35
      ],
      "rotation_deg": 266,
      "polygon_m": [
        [
          159.278,
          568.987
        ],
        [
          159.253,
          568.638
        ],
        [
          159.602,
          568.613
        ],
        [
          159.627,
          568.962
        ]
      ],
      "notes": "Porches of cared-for homes.",
      "hard_obstacle": false,
      "parent": "02-H01-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-040",
      "kind": "flower_pot",
      "centre_m": [
        249.09,
        566.66
      ],
      "size_m": [
        0.35,
        0.35
      ],
      "rotation_deg": 15,
      "polygon_m": [
        [
          248.966,
          566.446
        ],
        [
          249.304,
          566.536
        ],
        [
          249.214,
          566.874
        ],
        [
          248.876,
          566.784
        ]
      ],
      "notes": "Porches of cared-for homes.",
      "hard_obstacle": false,
      "parent": "02-H06-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-041",
      "kind": "flower_pot",
      "centre_m": [
        284.89,
        509.01
      ],
      "size_m": [
        0.35,
        0.35
      ],
      "rotation_deg": 66,
      "polygon_m": [
        [
          284.979,
          508.779
        ],
        [
          285.121,
          509.099
        ],
        [
          284.801,
          509.241
        ],
        [
          284.659,
          508.921
        ]
      ],
      "notes": "Porches of cared-for homes.",
      "hard_obstacle": false,
      "parent": "02-H10-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-042",
      "kind": "flower_pot",
      "centre_m": [
        154.95,
        555.59
      ],
      "size_m": [
        0.35,
        0.35
      ],
      "rotation_deg": 175,
      "polygon_m": [
        [
          155.14,
          555.749
        ],
        [
          154.791,
          555.78
        ],
        [
          154.76,
          555.431
        ],
        [
          155.109,
          555.4
        ]
      ],
      "notes": "Porches of cared-for homes.",
      "hard_obstacle": false,
      "parent": "02-D-037",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-043",
      "kind": "flower_pot",
      "centre_m": [
        186.43,
        555.91
      ],
      "size_m": [
        0.35,
        0.35
      ],
      "rotation_deg": 255,
      "polygon_m": [
        [
          186.306,
          556.124
        ],
        [
          186.216,
          555.786
        ],
        [
          186.554,
          555.696
        ],
        [
          186.644,
          556.034
        ]
      ],
      "notes": "Porches of cared-for homes.",
      "hard_obstacle": false,
      "parent": "02-D-038",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-044",
      "kind": "compost_heap",
      "centre_m": [
        182.41,
        575.09
      ],
      "size_m": [
        1.8,
        1.5
      ],
      "rotation_deg": 57,
      "polygon_m": [
        [
          182.549,
          573.927
        ],
        [
          183.529,
          575.436
        ],
        [
          182.271,
          576.253
        ],
        [
          181.291,
          574.744
        ]
      ],
      "notes": "Gardening homes only.",
      "hard_obstacle": false,
      "parent": "02-H02-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-045",
      "kind": "compost_heap",
      "centre_m": [
        200.4,
        516.95
      ],
      "size_m": [
        1.8,
        1.5
      ],
      "rotation_deg": 166,
      "polygon_m": [
        [
          201.455,
          517.46
        ],
        [
          199.708,
          517.895
        ],
        [
          199.345,
          516.44
        ],
        [
          201.092,
          516.005
        ]
      ],
      "notes": "Gardening homes only.",
      "hard_obstacle": false,
      "parent": "02-H05-Y3",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-046",
      "kind": "compost_heap",
      "centre_m": [
        257.49,
        579.75
      ],
      "size_m": [
        1.8,
        1.5
      ],
      "rotation_deg": 304,
      "polygon_m": [
        [
          256.365,
          580.077
        ],
        [
          257.371,
          578.584
        ],
        [
          258.615,
          579.423
        ],
        [
          257.609,
          580.916
        ]
      ],
      "notes": "Gardening homes only.",
      "hard_obstacle": false,
      "parent": "02-H07-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-047",
      "kind": "wooden_pallet",
      "centre_m": [
        165.52,
        557.69
      ],
      "size_m": [
        1.2,
        0.8
      ],
      "rotation_deg": 322,
      "polygon_m": [
        [
          164.801,
          557.744
        ],
        [
          165.747,
          557.005
        ],
        [
          166.239,
          557.636
        ],
        [
          165.293,
          558.375
        ]
      ],
      "notes": "Practical storage, not industrial yard clutter.",
      "hard_obstacle": true,
      "parent": "02-H01",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-048",
      "kind": "wooden_pallet",
      "centre_m": [
        186.2,
        566.68
      ],
      "size_m": [
        1.2,
        0.8
      ],
      "rotation_deg": 42,
      "polygon_m": [
        [
          186.022,
          565.981
        ],
        [
          186.914,
          566.784
        ],
        [
          186.378,
          567.379
        ],
        [
          185.486,
          566.576
        ]
      ],
      "notes": "Practical storage, not industrial yard clutter.",
      "hard_obstacle": true,
      "parent": "02-H02",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-049",
      "kind": "wooden_pallet",
      "centre_m": [
        195.29,
        565.94
      ],
      "size_m": [
        1.2,
        0.8
      ],
      "rotation_deg": 122,
      "polygon_m": [
        [
          195.947,
          565.643
        ],
        [
          195.311,
          566.661
        ],
        [
          194.633,
          566.237
        ],
        [
          195.269,
          565.219
        ]
      ],
      "notes": "Practical storage, not industrial yard clutter.",
      "hard_obstacle": true,
      "parent": "02-H03",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-050",
      "kind": "bucket",
      "centre_m": [
        241.1,
        507.36
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 343,
      "polygon_m": [
        [
          240.913,
          507.26
        ],
        [
          241.2,
          507.173
        ],
        [
          241.287,
          507.46
        ],
        [
          241.0,
          507.547
        ]
      ],
      "notes": "Well and animal care.",
      "hard_obstacle": false,
      "parent": "02-U-WATER1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-051",
      "kind": "bucket",
      "centre_m": [
        322.0,
        478.96
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 63,
      "polygon_m": [
        [
          322.066,
          478.758
        ],
        [
          322.202,
          479.026
        ],
        [
          321.934,
          479.162
        ],
        [
          321.798,
          478.894
        ]
      ],
      "notes": "Well and animal care.",
      "hard_obstacle": false,
      "parent": "02-U-WATER2",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-052",
      "kind": "bucket",
      "centre_m": [
        245.11,
        513.9
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 44,
      "polygon_m": [
        [
          245.106,
          513.688
        ],
        [
          245.322,
          513.896
        ],
        [
          245.114,
          514.112
        ],
        [
          244.898,
          513.904
        ]
      ],
      "notes": "Well and animal care.",
      "hard_obstacle": false,
      "parent": "02-U-WATER1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-053",
      "kind": "bucket",
      "centre_m": [
        319.39,
        475.5
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 223,
      "polygon_m": [
        [
          319.397,
          475.712
        ],
        [
          319.178,
          475.507
        ],
        [
          319.383,
          475.288
        ],
        [
          319.602,
          475.493
        ]
      ],
      "notes": "Well and animal care.",
      "hard_obstacle": false,
      "parent": "02-U-WATER2",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-054",
      "kind": "bucket",
      "centre_m": [
        242.6,
        508.06
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 1,
      "polygon_m": [
        [
          242.453,
          507.907
        ],
        [
          242.753,
          507.913
        ],
        [
          242.747,
          508.213
        ],
        [
          242.447,
          508.207
        ]
      ],
      "notes": "Well and animal care.",
      "hard_obstacle": false,
      "parent": "02-U-WATER1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-055",
      "kind": "rusted_wheel",
      "centre_m": [
        287.98,
        572.12
      ],
      "size_m": [
        0.6,
        0.2
      ],
      "rotation_deg": 47,
      "polygon_m": [
        [
          287.849,
          571.832
        ],
        [
          288.258,
          572.271
        ],
        [
          288.111,
          572.408
        ],
        [
          287.702,
          571.969
        ]
      ],
      "notes": "Near tractor and farm shed.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-056",
      "kind": "rusted_wheel",
      "centre_m": [
        318.69,
        560.18
      ],
      "size_m": [
        0.6,
        0.2
      ],
      "rotation_deg": 98,
      "polygon_m": [
        [
          318.831,
          559.897
        ],
        [
          318.747,
          560.491
        ],
        [
          318.549,
          560.463
        ],
        [
          318.633,
          559.869
        ]
      ],
      "notes": "Near tractor and farm shed.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR2",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-057",
      "kind": "tyre",
      "centre_m": [
        287.41,
        572.54
      ],
      "size_m": [
        0.7,
        0.25
      ],
      "rotation_deg": 61,
      "polygon_m": [
        [
          287.35,
          572.173
        ],
        [
          287.689,
          572.786
        ],
        [
          287.47,
          572.907
        ],
        [
          287.131,
          572.294
        ]
      ],
      "notes": "A few spare tyres, no tyre-wall maze.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-058",
      "kind": "tyre",
      "centre_m": [
        318.18,
        560.04
      ],
      "size_m": [
        0.7,
        0.25
      ],
      "rotation_deg": 112,
      "polygon_m": [
        [
          318.427,
          559.762
        ],
        [
          318.165,
          560.411
        ],
        [
          317.933,
          560.318
        ],
        [
          318.195,
          559.669
        ]
      ],
      "notes": "A few spare tyres, no tyre-wall maze.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR2",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-059",
      "kind": "handcart",
      "centre_m": [
        164.86,
        567.04
      ],
      "size_m": [
        1.4,
        0.75
      ],
      "rotation_deg": 46,
      "polygon_m": [
        [
          164.643,
          566.276
        ],
        [
          165.616,
          567.283
        ],
        [
          165.077,
          567.804
        ],
        [
          164.104,
          566.797
        ]
      ],
      "notes": "Farm deliveries.",
      "hard_obstacle": true,
      "parent": "02-H01",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-060",
      "kind": "handcart",
      "centre_m": [
        171.02,
        561.3
      ],
      "size_m": [
        1.4,
        0.75
      ],
      "rotation_deg": 184,
      "polygon_m": [
        [
          171.692,
          561.723
        ],
        [
          170.296,
          561.625
        ],
        [
          170.348,
          560.877
        ],
        [
          171.744,
          560.975
        ]
      ],
      "notes": "Farm deliveries.",
      "hard_obstacle": true,
      "parent": "02-H02",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-061",
      "kind": "haystack",
      "centre_m": [
        297.6,
        546.06
      ],
      "size_m": [
        2.8,
        2.8
      ],
      "rotation_deg": 234,
      "polygon_m": [
        [
          297.29,
          548.016
        ],
        [
          295.644,
          545.75
        ],
        [
          297.91,
          544.104
        ],
        [
          299.556,
          546.37
        ]
      ],
      "notes": "Field edge/hay shelter; not a road barrier.",
      "hard_obstacle": true,
      "parent": "02-H08",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-062",
      "kind": "haystack",
      "centre_m": [
        299.16,
        550.59
      ],
      "size_m": [
        2.8,
        2.8
      ],
      "rotation_deg": 227,
      "polygon_m": [
        [
          299.091,
          552.569
        ],
        [
          297.181,
          550.521
        ],
        [
          299.229,
          548.611
        ],
        [
          301.139,
          550.659
        ]
      ],
      "notes": "Field edge/hay shelter; not a road barrier.",
      "hard_obstacle": true,
      "parent": "02-H08",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-063",
      "kind": "haystack",
      "centre_m": [
        303.95,
        551.06
      ],
      "size_m": [
        2.8,
        2.8
      ],
      "rotation_deg": 249,
      "polygon_m": [
        [
          303.145,
          552.869
        ],
        [
          302.141,
          550.255
        ],
        [
          304.755,
          549.251
        ],
        [
          305.759,
          551.865
        ]
      ],
      "notes": "Field edge/hay shelter; not a road barrier.",
      "hard_obstacle": true,
      "parent": "02-H08",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-064",
      "kind": "net_drying_rack",
      "centre_m": [
        349.09,
        469.99
      ],
      "size_m": [
        2.5,
        0.3
      ],
      "rotation_deg": 110,
      "polygon_m": [
        [
          349.658,
          468.867
        ],
        [
          348.803,
          471.216
        ],
        [
          348.522,
          471.113
        ],
        [
          349.377,
          468.764
        ]
      ],
      "notes": "Fishing household and river landing.",
      "hard_obstacle": false,
      "parent": "02-H13",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-065",
      "kind": "fishing_bucket",
      "centre_m": [
        344.51,
        459.33
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 88,
      "polygon_m": [
        [
          344.655,
          459.175
        ],
        [
          344.665,
          459.475
        ],
        [
          344.365,
          459.485
        ],
        [
          344.355,
          459.185
        ]
      ],
      "notes": "Near fishing nets.",
      "hard_obstacle": false,
      "parent": "02-H13-Y2",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-066",
      "kind": "fishing_bucket",
      "centre_m": [
        346.94,
        470.45
      ],
      "size_m": [
        0.3,
        0.3
      ],
      "rotation_deg": 168,
      "polygon_m": [
        [
          347.118,
          470.566
        ],
        [
          346.824,
          470.628
        ],
        [
          346.762,
          470.334
        ],
        [
          347.056,
          470.272
        ]
      ],
      "notes": "Near fishing nets.",
      "hard_obstacle": false,
      "parent": "02-D-064",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-067",
      "kind": "reed_clump",
      "centre_m": [
        175.42,
        478.44
      ],
      "size_m": [
        1.5,
        1
      ],
      "rotation_deg": 102,
      "polygon_m": [
        [
          176.065,
          477.81
        ],
        [
          175.753,
          479.278
        ],
        [
          174.775,
          479.07
        ],
        [
          175.087,
          477.602
        ]
      ],
      "notes": "Pond margins, gaps for sightlines.",
      "hard_obstacle": false,
      "parent": "02-A-POND",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-068",
      "kind": "reed_clump",
      "centre_m": [
        185.86,
        486.56
      ],
      "size_m": [
        1.5,
        1
      ],
      "rotation_deg": 182,
      "polygon_m": [
        [
          186.592,
          487.086
        ],
        [
          185.093,
          487.034
        ],
        [
          185.128,
          486.034
        ],
        [
          186.627,
          486.086
        ]
      ],
      "notes": "Pond margins, gaps for sightlines.",
      "hard_obstacle": false,
      "parent": "02-A-POND",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-069",
      "kind": "reed_clump",
      "centre_m": [
        207.22,
        484.41
      ],
      "size_m": [
        1.5,
        1
      ],
      "rotation_deg": 262,
      "polygon_m": [
        [
          206.829,
          485.222
        ],
        [
          206.62,
          483.737
        ],
        [
          207.611,
          483.598
        ],
        [
          207.82,
          485.083
        ]
      ],
      "notes": "Pond margins, gaps for sightlines.",
      "hard_obstacle": false,
      "parent": "02-A-POND",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-070",
      "kind": "reed_clump",
      "centre_m": [
        220.08,
        472.32
      ],
      "size_m": [
        1.5,
        1
      ],
      "rotation_deg": 342,
      "polygon_m": [
        [
          219.212,
          472.076
        ],
        [
          220.639,
          471.613
        ],
        [
          220.948,
          472.564
        ],
        [
          219.521,
          473.027
        ]
      ],
      "notes": "Pond margins, gaps for sightlines.",
      "hard_obstacle": false,
      "parent": "02-A-POND",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-071",
      "kind": "reed_clump",
      "centre_m": [
        219.85,
        458.14
      ],
      "size_m": [
        1.5,
        1
      ],
      "rotation_deg": 62,
      "polygon_m": [
        [
          219.939,
          457.243
        ],
        [
          220.644,
          458.567
        ],
        [
          219.761,
          459.037
        ],
        [
          219.056,
          457.713
        ]
      ],
      "notes": "Pond margins, gaps for sightlines.",
      "hard_obstacle": false,
      "parent": "02-A-POND",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-072",
      "kind": "reed_clump",
      "centre_m": [
        206.7,
        447.95
      ],
      "size_m": [
        1.5,
        1
      ],
      "rotation_deg": 142,
      "polygon_m": [
        [
          207.599,
          447.882
        ],
        [
          206.417,
          448.806
        ],
        [
          205.801,
          448.018
        ],
        [
          206.983,
          447.094
        ]
      ],
      "notes": "Pond margins, gaps for sightlines.",
      "hard_obstacle": false,
      "parent": "02-A-POND",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-073",
      "kind": "reed_clump",
      "centre_m": [
        187.39,
        448.21
      ],
      "size_m": [
        1.5,
        1
      ],
      "rotation_deg": 222,
      "polygon_m": [
        [
          187.613,
          449.083
        ],
        [
          186.498,
          448.08
        ],
        [
          187.167,
          447.337
        ],
        [
          188.282,
          448.34
        ]
      ],
      "notes": "Pond margins, gaps for sightlines.",
      "hard_obstacle": false,
      "parent": "02-A-POND",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-074",
      "kind": "reed_clump",
      "centre_m": [
        174.18,
        459.66
      ],
      "size_m": [
        1.5,
        1
      ],
      "rotation_deg": 302,
      "polygon_m": [
        [
          173.359,
          460.031
        ],
        [
          174.153,
          458.759
        ],
        [
          175.001,
          459.289
        ],
        [
          174.207,
          460.561
        ]
      ],
      "notes": "Pond margins, gaps for sightlines.",
      "hard_obstacle": false,
      "parent": "02-A-POND",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-075",
      "kind": "rounded_rock",
      "centre_m": [
        153.51,
        564.62
      ],
      "size_m": [
        1,
        0.8
      ],
      "rotation_deg": 158,
      "polygon_m": [
        [
          154.123,
          564.804
        ],
        [
          153.196,
          565.178
        ],
        [
          152.897,
          564.436
        ],
        [
          153.824,
          564.062
        ]
      ],
      "notes": "Sparse forest edge only, not filled gaps everywhere.",
      "hard_obstacle": true,
      "parent": "02-H01",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-076",
      "kind": "rounded_rock",
      "centre_m": [
        177.29,
        556.06
      ],
      "size_m": [
        1,
        0.8
      ],
      "rotation_deg": 238,
      "polygon_m": [
        [
          177.216,
          556.696
        ],
        [
          176.686,
          555.848
        ],
        [
          177.364,
          555.424
        ],
        [
          177.894,
          556.272
        ]
      ],
      "notes": "Sparse forest edge only, not filled gaps everywhere.",
      "hard_obstacle": true,
      "parent": "02-H02",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-077",
      "kind": "rounded_rock",
      "centre_m": [
        207.28,
        558.09
      ],
      "size_m": [
        1,
        0.8
      ],
      "rotation_deg": 347,
      "polygon_m": [
        [
          206.703,
          557.813
        ],
        [
          207.677,
          557.588
        ],
        [
          207.857,
          558.367
        ],
        [
          206.883,
          558.592
        ]
      ],
      "notes": "Sparse forest edge only, not filled gaps everywhere.",
      "hard_obstacle": true,
      "parent": "02-H03",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-078",
      "kind": "mud_patch",
      "centre_m": [
        195.22,
        526.44
      ],
      "size_m": [
        3,
        2
      ],
      "rotation_deg": 138,
      "polygon_m": [
        [
          197.004,
          526.179
        ],
        [
          194.774,
          528.187
        ],
        [
          193.436,
          526.701
        ],
        [
          195.666,
          524.693
        ]
      ],
      "notes": "Pig/tractor areas; ground visual, no invented slow debuff.",
      "hard_obstacle": false,
      "parent": "02-H05-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-079",
      "kind": "mud_patch",
      "centre_m": [
        315.85,
        461.99
      ],
      "size_m": [
        3,
        2
      ],
      "rotation_deg": 346,
      "polygon_m": [
        [
          314.153,
          461.383
        ],
        [
          317.064,
          460.657
        ],
        [
          317.547,
          462.597
        ],
        [
          314.636,
          463.323
        ]
      ],
      "notes": "Pig/tractor areas; ground visual, no invented slow debuff.",
      "hard_obstacle": false,
      "parent": "02-H12-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-080",
      "kind": "mud_patch",
      "centre_m": [
        298.87,
        423.79
      ],
      "size_m": [
        3,
        2
      ],
      "rotation_deg": 124,
      "polygon_m": [
        [
          300.538,
          423.106
        ],
        [
          298.86,
          425.593
        ],
        [
          297.202,
          424.474
        ],
        [
          298.88,
          421.987
        ]
      ],
      "notes": "Pig/tractor areas; ground visual, no invented slow debuff.",
      "hard_obstacle": false,
      "parent": "02-H17-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-081",
      "kind": "mud_patch",
      "centre_m": [
        199.02,
        522.22
      ],
      "size_m": [
        3,
        2
      ],
      "rotation_deg": 146,
      "polygon_m": [
        [
          200.823,
          522.21
        ],
        [
          198.336,
          523.888
        ],
        [
          197.217,
          522.23
        ],
        [
          199.704,
          520.552
        ]
      ],
      "notes": "Pig/tractor areas; ground visual, no invented slow debuff.",
      "hard_obstacle": false,
      "parent": "02-H05-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-082",
      "kind": "mud_patch",
      "centre_m": [
        308.69,
        459.94
      ],
      "size_m": [
        3,
        2
      ],
      "rotation_deg": 226,
      "polygon_m": [
        [
          309.013,
          461.714
        ],
        [
          306.929,
          459.556
        ],
        [
          308.367,
          458.166
        ],
        [
          310.451,
          460.324
        ]
      ],
      "notes": "Pig/tractor areas; ground visual, no invented slow debuff.",
      "hard_obstacle": false,
      "parent": "02-H12-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-083",
      "kind": "mud_patch",
      "centre_m": [
        297.81,
        426.42
      ],
      "size_m": [
        3,
        2
      ],
      "rotation_deg": 120,
      "polygon_m": [
        [
          299.426,
          425.621
        ],
        [
          297.926,
          428.219
        ],
        [
          296.194,
          427.219
        ],
        [
          297.694,
          424.621
        ]
      ],
      "notes": "Pig/tractor areas; ground visual, no invented slow debuff.",
      "hard_obstacle": false,
      "parent": "02-H17-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-084",
      "kind": "wheel_rut",
      "centre_m": [
        290.6,
        568.05
      ],
      "size_m": [
        4,
        1.8
      ],
      "rotation_deg": 337,
      "polygon_m": [
        [
          288.407,
          568.003
        ],
        [
          292.089,
          566.44
        ],
        [
          292.793,
          568.097
        ],
        [
          289.111,
          569.66
        ]
      ],
      "notes": "Soft ground near field entrances.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-085",
      "kind": "wheel_rut",
      "centre_m": [
        313.21,
        550.85
      ],
      "size_m": [
        4,
        1.8
      ],
      "rotation_deg": 231,
      "polygon_m": [
        [
          313.769,
          552.971
        ],
        [
          311.252,
          549.862
        ],
        [
          312.651,
          548.729
        ],
        [
          315.168,
          551.838
        ]
      ],
      "notes": "Soft ground near field entrances.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR2",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-086",
      "kind": "wheel_rut",
      "centre_m": [
        286.69,
        573.53
      ],
      "size_m": [
        4,
        1.8
      ],
      "rotation_deg": 79,
      "polygon_m": [
        [
          287.192,
          571.395
        ],
        [
          287.955,
          575.322
        ],
        [
          286.188,
          575.665
        ],
        [
          285.425,
          571.738
        ]
      ],
      "notes": "Soft ground near field entrances.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-087",
      "kind": "wheel_rut",
      "centre_m": [
        315.01,
        554.99
      ],
      "size_m": [
        4,
        1.8
      ],
      "rotation_deg": 217,
      "polygon_m": [
        [
          316.066,
          556.912
        ],
        [
          312.871,
          554.505
        ],
        [
          313.954,
          553.068
        ],
        [
          317.149,
          555.475
        ]
      ],
      "notes": "Soft ground near field entrances.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR2",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-088",
      "kind": "wheel_rut",
      "centre_m": [
        285.85,
        565.7
      ],
      "size_m": [
        4,
        1.8
      ],
      "rotation_deg": 268,
      "polygon_m": [
        [
          285.02,
          567.73
        ],
        [
          284.881,
          563.733
        ],
        [
          286.68,
          563.67
        ],
        [
          286.819,
          567.667
        ]
      ],
      "notes": "Soft ground near field entrances.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-089",
      "kind": "wheel_rut",
      "centre_m": [
        323.78,
        559.46
      ],
      "size_m": [
        4,
        1.8
      ],
      "rotation_deg": 17,
      "polygon_m": [
        [
          322.131,
          558.015
        ],
        [
          325.956,
          559.184
        ],
        [
          325.429,
          560.905
        ],
        [
          321.604,
          559.736
        ]
      ],
      "notes": "Soft ground near field entrances.",
      "hard_obstacle": false,
      "parent": "02-U-TRACTOR2",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-090",
      "kind": "dung_patch",
      "centre_m": [
        202.31,
        517.64
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 263,
      "polygon_m": [
        [
          202.148,
          517.962
        ],
        [
          202.075,
          517.367
        ],
        [
          202.472,
          517.318
        ],
        [
          202.545,
          517.913
        ]
      ],
      "notes": "Pig shelters only, modest stylized dressing.",
      "hard_obstacle": false,
      "parent": "02-H05-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-091",
      "kind": "dung_patch",
      "centre_m": [
        314.52,
        463.63
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 12,
      "polygon_m": [
        [
          314.268,
          463.372
        ],
        [
          314.855,
          463.497
        ],
        [
          314.772,
          463.888
        ],
        [
          314.185,
          463.763
        ]
      ],
      "notes": "Pig shelters only, modest stylized dressing.",
      "hard_obstacle": false,
      "parent": "02-H12-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-092",
      "kind": "dung_patch",
      "centre_m": [
        303.06,
        421.02
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 63,
      "polygon_m": [
        [
          303.102,
          420.662
        ],
        [
          303.374,
          421.197
        ],
        [
          303.018,
          421.378
        ],
        [
          302.746,
          420.843
        ]
      ],
      "notes": "Pig shelters only, modest stylized dressing.",
      "hard_obstacle": false,
      "parent": "02-H17-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-D-093",
      "kind": "dung_patch",
      "centre_m": [
        199.71,
        520.22
      ],
      "size_m": [
        0.6,
        0.4
      ],
      "rotation_deg": 172,
      "polygon_m": [
        [
          200.035,
          520.376
        ],
        [
          199.441,
          520.46
        ],
        [
          199.385,
          520.064
        ],
        [
          199.979,
          519.98
        ]
      ],
      "notes": "Pig shelters only, modest stylized dressing.",
      "hard_obstacle": false,
      "parent": "02-H05-Y1",
      "status": "proposed_dressing"
    },
    {
      "id": "02-H05-PIG",
      "kind": "pig_spawn_marker",
      "centre_m": [
        202.58,
        519.82
      ],
      "size_m": [
        0.9,
        0.45
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          202.13,
          519.595
        ],
        [
          203.03,
          519.595
        ],
        [
          203.03,
          520.045
        ],
        [
          202.13,
          520.045
        ]
      ],
      "notes": "Proposed animal marker, not a built AI implementation.",
      "hard_obstacle": false,
      "parent": "02-H05-Y1"
    },
    {
      "id": "02-H12-PIG",
      "kind": "pig_spawn_marker",
      "centre_m": [
        311.68,
        463.03
      ],
      "size_m": [
        0.9,
        0.45
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          311.23,
          462.805
        ],
        [
          312.13,
          462.805
        ],
        [
          312.13,
          463.255
        ],
        [
          311.23,
          463.255
        ]
      ],
      "notes": "Proposed animal marker, not a built AI implementation.",
      "hard_obstacle": false,
      "parent": "02-H12-Y1"
    },
    {
      "id": "02-H17-PIG",
      "kind": "pig_spawn_marker",
      "centre_m": [
        302.06,
        419.06
      ],
      "size_m": [
        0.9,
        0.45
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          301.61,
          418.835
        ],
        [
          302.51,
          418.835
        ],
        [
          302.51,
          419.285
        ],
        [
          301.61,
          419.285
        ]
      ],
      "notes": "Proposed animal marker, not a built AI implementation.",
      "hard_obstacle": false,
      "parent": "02-H17-Y1"
    },
    {
      "id": "02-A-PIG-0",
      "kind": "pig_spawn_marker",
      "centre_m": [
        270,
        565.6
      ],
      "size_m": [
        0.9,
        0.45
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          269.55,
          565.375
        ],
        [
          270.45,
          565.375
        ],
        [
          270.45,
          565.825
        ],
        [
          269.55,
          565.825
        ]
      ],
      "notes": "Only pigs and chickens are approved animal species.",
      "hard_obstacle": false,
      "parent": "02-A-PEN"
    },
    {
      "id": "02-A-PIG-1",
      "kind": "pig_spawn_marker",
      "centre_m": [
        274,
        565.6
      ],
      "size_m": [
        0.9,
        0.45
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          273.55,
          565.375
        ],
        [
          274.45,
          565.375
        ],
        [
          274.45,
          565.825
        ],
        [
          273.55,
          565.825
        ]
      ],
      "notes": "Only pigs and chickens are approved animal species.",
      "hard_obstacle": false,
      "parent": "02-A-PEN"
    },
    {
      "id": "02-H03-CHICKEN-0",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        196.82,
        568.54
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          196.67,
          568.44
        ],
        [
          196.97,
          568.44
        ],
        [
          196.97,
          568.64
        ],
        [
          196.67,
          568.64
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H03-Y1"
    },
    {
      "id": "02-H03-CHICKEN-1",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        197.32,
        568.54
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          197.17,
          568.44
        ],
        [
          197.47,
          568.44
        ],
        [
          197.47,
          568.64
        ],
        [
          197.17,
          568.64
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H03-Y1"
    },
    {
      "id": "02-H03-CHICKEN-2",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        196.82,
        569.04
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          196.67,
          568.94
        ],
        [
          196.97,
          568.94
        ],
        [
          196.97,
          569.14
        ],
        [
          196.67,
          569.14
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H03-Y1"
    },
    {
      "id": "02-H03-CHICKEN-3",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        197.32,
        569.04
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          197.17,
          568.94
        ],
        [
          197.47,
          568.94
        ],
        [
          197.47,
          569.14
        ],
        [
          197.17,
          569.14
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H03-Y1"
    },
    {
      "id": "02-H11-CHICKEN-0",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        279.63,
        466.75
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          279.48,
          466.65
        ],
        [
          279.78,
          466.65
        ],
        [
          279.78,
          466.85
        ],
        [
          279.48,
          466.85
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H11-Y1"
    },
    {
      "id": "02-H11-CHICKEN-1",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        280.13,
        466.75
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          279.98,
          466.65
        ],
        [
          280.28,
          466.65
        ],
        [
          280.28,
          466.85
        ],
        [
          279.98,
          466.85
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H11-Y1"
    },
    {
      "id": "02-H11-CHICKEN-2",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        279.63,
        467.25
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          279.48,
          467.15
        ],
        [
          279.78,
          467.15
        ],
        [
          279.78,
          467.35
        ],
        [
          279.48,
          467.35
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H11-Y1"
    },
    {
      "id": "02-H11-CHICKEN-3",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        280.13,
        467.25
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          279.98,
          467.15
        ],
        [
          280.28,
          467.15
        ],
        [
          280.28,
          467.35
        ],
        [
          279.98,
          467.35
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H11-Y1"
    },
    {
      "id": "02-H16-CHICKEN-0",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        287.28,
        420.62
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          287.13,
          420.52
        ],
        [
          287.43,
          420.52
        ],
        [
          287.43,
          420.72
        ],
        [
          287.13,
          420.72
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H16-Y1"
    },
    {
      "id": "02-H16-CHICKEN-1",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        287.78,
        420.62
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          287.63,
          420.52
        ],
        [
          287.93,
          420.52
        ],
        [
          287.93,
          420.72
        ],
        [
          287.63,
          420.72
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H16-Y1"
    },
    {
      "id": "02-H16-CHICKEN-2",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        287.28,
        421.12
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          287.13,
          421.02
        ],
        [
          287.43,
          421.02
        ],
        [
          287.43,
          421.22
        ],
        [
          287.13,
          421.22
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H16-Y1"
    },
    {
      "id": "02-H16-CHICKEN-3",
      "kind": "chicken_spawn_marker",
      "centre_m": [
        287.78,
        421.12
      ],
      "size_m": [
        0.3,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          287.63,
          421.02
        ],
        [
          287.93,
          421.02
        ],
        [
          287.93,
          421.22
        ],
        [
          287.63,
          421.22
        ]
      ],
      "notes": "Proposed loose chicken activity marker, no yard fence.",
      "hard_obstacle": false,
      "parent": "02-H16-Y1"
    },
    {
      "id": "02-L-0",
      "kind": "pole_lamp",
      "centre_m": [
        358.85,
        473.41
      ],
      "size_m": [
        0.2,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          358.75,
          473.31
        ],
        [
          358.95,
          473.31
        ],
        [
          358.95,
          473.51
        ],
        [
          358.75,
          473.51
        ]
      ],
      "notes": "Mounted on utility pole; no new ground obstacle.",
      "hard_obstacle": false,
      "parent": "02-P-01",
      "mount_height_m": 5
    },
    {
      "id": "02-L-1",
      "kind": "pole_lamp",
      "centre_m": [
        236.08,
        500.72
      ],
      "size_m": [
        0.2,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          235.98,
          500.62
        ],
        [
          236.18,
          500.62
        ],
        [
          236.18,
          500.82
        ],
        [
          235.98,
          500.82
        ]
      ],
      "notes": "Mounted on utility pole; no new ground obstacle.",
      "hard_obstacle": false,
      "parent": "02-P-05",
      "mount_height_m": 5
    },
    {
      "id": "02-L-2",
      "kind": "pole_lamp",
      "centre_m": [
        146.58,
        545.42
      ],
      "size_m": [
        0.2,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          146.48,
          545.32
        ],
        [
          146.68,
          545.32
        ],
        [
          146.68,
          545.52
        ],
        [
          146.48,
          545.52
        ]
      ],
      "notes": "Mounted on utility pole; no new ground obstacle.",
      "hard_obstacle": false,
      "parent": "02-P-09",
      "mount_height_m": 5
    },
    {
      "id": "02-L-3",
      "kind": "pole_lamp",
      "centre_m": [
        305.31,
        544.85
      ],
      "size_m": [
        0.2,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          305.21,
          544.75
        ],
        [
          305.41,
          544.75
        ],
        [
          305.41,
          544.95
        ],
        [
          305.21,
          544.95
        ]
      ],
      "notes": "Mounted on utility pole; no new ground obstacle.",
      "hard_obstacle": false,
      "parent": "02-P-13",
      "mount_height_m": 5
    },
    {
      "id": "02-L-4",
      "kind": "pole_lamp",
      "centre_m": [
        242.99,
        435.55
      ],
      "size_m": [
        0.2,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          242.89,
          435.45
        ],
        [
          243.09,
          435.45
        ],
        [
          243.09,
          435.65
        ],
        [
          242.89,
          435.65
        ]
      ],
      "notes": "Mounted on utility pole; no new ground obstacle.",
      "hard_obstacle": false,
      "parent": "02-P-17",
      "mount_height_m": 5
    },
    {
      "id": "02-L-5",
      "kind": "pole_lamp",
      "centre_m": [
        333.29,
        460.41
      ],
      "size_m": [
        0.2,
        0.2
      ],
      "rotation_deg": 0,
      "polygon_m": [
        [
          333.19,
          460.31
        ],
        [
          333.39,
          460.31
        ],
        [
          333.39,
          460.51
        ],
        [
          333.19,
          460.51
        ]
      ],
      "notes": "Mounted on utility pole; no new ground obstacle.",
      "hard_obstacle": false,
      "parent": "02-P-21",
      "mount_height_m": 5
    }
  ],
  "utility_links": [
    {
      "id": "02-P-01--02-P-02",
      "kind": "utility_wire",
      "from_id": "02-P-01",
      "to_id": "02-P-02",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 28.68
    },
    {
      "id": "02-P-02--02-P-03",
      "kind": "utility_wire",
      "from_id": "02-P-02",
      "to_id": "02-P-03",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 32.94
    },
    {
      "id": "02-P-03--02-P-04",
      "kind": "utility_wire",
      "from_id": "02-P-03",
      "to_id": "02-P-04",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 32.67
    },
    {
      "id": "02-P-04--02-P-05",
      "kind": "utility_wire",
      "from_id": "02-P-04",
      "to_id": "02-P-05",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 32.57
    },
    {
      "id": "02-P-05--02-P-06",
      "kind": "utility_wire",
      "from_id": "02-P-05",
      "to_id": "02-P-06",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 34.27
    },
    {
      "id": "02-P-06--02-P-07",
      "kind": "utility_wire",
      "from_id": "02-P-06",
      "to_id": "02-P-07",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 19.02
    },
    {
      "id": "02-P-07--02-P-08",
      "kind": "utility_wire",
      "from_id": "02-P-07",
      "to_id": "02-P-08",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 30.29
    },
    {
      "id": "02-P-08--02-P-09",
      "kind": "utility_wire",
      "from_id": "02-P-08",
      "to_id": "02-P-09",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 32.2
    },
    {
      "id": "02-P-10--02-P-11",
      "kind": "utility_wire",
      "from_id": "02-P-10",
      "to_id": "02-P-11",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 26.39
    },
    {
      "id": "02-P-11--02-P-12",
      "kind": "utility_wire",
      "from_id": "02-P-11",
      "to_id": "02-P-12",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 27.35
    },
    {
      "id": "02-P-12--02-P-13",
      "kind": "utility_wire",
      "from_id": "02-P-12",
      "to_id": "02-P-13",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 27.22
    },
    {
      "id": "02-P-13--02-P-14",
      "kind": "utility_wire",
      "from_id": "02-P-13",
      "to_id": "02-P-14",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 27.36
    },
    {
      "id": "02-P-15--02-P-16",
      "kind": "utility_wire",
      "from_id": "02-P-15",
      "to_id": "02-P-16",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 36.5
    },
    {
      "id": "02-P-16--02-P-17",
      "kind": "utility_wire",
      "from_id": "02-P-16",
      "to_id": "02-P-17",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 31.35
    },
    {
      "id": "02-P-17--02-P-18",
      "kind": "utility_wire",
      "from_id": "02-P-17",
      "to_id": "02-P-18",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 29.09
    },
    {
      "id": "02-P-18--02-P-19",
      "kind": "utility_wire",
      "from_id": "02-P-18",
      "to_id": "02-P-19",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 32.3
    },
    {
      "id": "02-P-20--02-P-21",
      "kind": "utility_wire",
      "from_id": "02-P-20",
      "to_id": "02-P-21",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 31.09
    },
    {
      "id": "02-P-21--02-P-22",
      "kind": "utility_wire",
      "from_id": "02-P-21",
      "to_id": "02-P-22",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 29.39
    },
    {
      "id": "02-P-22--02-P-23",
      "kind": "utility_wire",
      "from_id": "02-P-22",
      "to_id": "02-P-23",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 28.73
    },
    {
      "id": "02-P-23--02-P-24",
      "kind": "utility_wire",
      "from_id": "02-P-23",
      "to_id": "02-P-24",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 30.92
    },
    {
      "id": "02-P-24--02-P-25",
      "kind": "utility_wire",
      "from_id": "02-P-24",
      "to_id": "02-P-25",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 28.47
    },
    {
      "id": "02-P-25--02-P-26",
      "kind": "utility_wire",
      "from_id": "02-P-25",
      "to_id": "02-P-26",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 27.99
    },
    {
      "id": "02-P-26--02-P-27",
      "kind": "utility_wire",
      "from_id": "02-P-26",
      "to_id": "02-P-27",
      "height_m": 6,
      "notes": "Catenary visual; no collider; span length recorded.",
      "span_m": 32.14
    },
    {
      "id": "SERVICE-02-H01",
      "kind": "service_wire",
      "from_id": "02-P-09",
      "to_id": "02-H01",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 21.33
    },
    {
      "id": "SERVICE-02-H02",
      "kind": "service_wire",
      "from_id": "02-P-08",
      "to_id": "02-H02",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 16.81
    },
    {
      "id": "SERVICE-02-H03",
      "kind": "service_wire",
      "from_id": "02-P-07",
      "to_id": "02-H03",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 16.74
    },
    {
      "id": "SERVICE-02-H04",
      "kind": "service_wire",
      "from_id": "02-P-07",
      "to_id": "02-H04",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 15.1
    },
    {
      "id": "SERVICE-02-H05",
      "kind": "service_wire",
      "from_id": "02-P-06",
      "to_id": "02-H05",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 11.37
    },
    {
      "id": "SERVICE-02-H06",
      "kind": "service_wire",
      "from_id": "02-P-11",
      "to_id": "02-H06",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 12.88
    },
    {
      "id": "SERVICE-02-H07",
      "kind": "service_wire",
      "from_id": "02-P-11",
      "to_id": "02-H07",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 31.52
    },
    {
      "id": "SERVICE-02-H08",
      "kind": "service_wire",
      "from_id": "02-P-13",
      "to_id": "02-H08",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 14.25
    },
    {
      "id": "SERVICE-02-H09",
      "kind": "service_wire",
      "from_id": "02-P-13",
      "to_id": "02-H09",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 24.32
    },
    {
      "id": "SERVICE-02-H10",
      "kind": "service_wire",
      "from_id": "02-P-12",
      "to_id": "02-H10",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 29.2
    },
    {
      "id": "SERVICE-02-H11",
      "kind": "service_wire",
      "from_id": "02-P-04",
      "to_id": "02-H11",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 18.31
    },
    {
      "id": "SERVICE-02-H12",
      "kind": "service_wire",
      "from_id": "02-P-03",
      "to_id": "02-H12",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 17.49
    },
    {
      "id": "SERVICE-02-H13",
      "kind": "service_wire",
      "from_id": "02-P-01",
      "to_id": "02-H13",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 13.31
    },
    {
      "id": "SERVICE-02-H14",
      "kind": "service_wire",
      "from_id": "02-P-16",
      "to_id": "02-H14",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 13.1
    },
    {
      "id": "SERVICE-02-H15",
      "kind": "service_wire",
      "from_id": "02-P-17",
      "to_id": "02-H15",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 29.02
    },
    {
      "id": "SERVICE-02-H16",
      "kind": "service_wire",
      "from_id": "02-P-25",
      "to_id": "02-H16",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 31.36
    },
    {
      "id": "SERVICE-02-H17",
      "kind": "service_wire",
      "from_id": "02-P-23",
      "to_id": "02-H17",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 29.14
    },
    {
      "id": "SERVICE-02-H18",
      "kind": "service_wire",
      "from_id": "02-P-23",
      "to_id": "02-H18",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 16.06
    },
    {
      "id": "SERVICE-02-H19",
      "kind": "service_wire",
      "from_id": "02-P-17",
      "to_id": "02-H19",
      "height_m": 4.2,
      "notes": "Decorative service drop; no collision.",
      "span_m": 28.21
    }
  ],
  "drainage": [
    {
      "id": "02-INF-DITCH-MAIN",
      "kind": "drainage_ditch",
      "polyline_m": [
        [
          369,
          476
        ],
        [
          350,
          485
        ],
        [
          329,
          491
        ],
        [
          298,
          493
        ],
        [
          274,
          495
        ]
      ],
      "width_m": 0.7,
      "depth_m": 0.25,
      "rotation_deg": null,
      "notes": "Shallow rounded drainage edge, traversable at low speed, break at house accesses. No continuous trench around homes."
    }
  ],
  "terrain": [
    {
      "id": "02-TR-north_fold",
      "kind": "terrain_feature",
      "polygon_m": [
        [
          253,
          576
        ],
        [
          321,
          576
        ],
        [
          321,
          598
        ],
        [
          253,
          598
        ]
      ],
      "height_delta_m": 3.8,
      "rotation_deg": 0,
      "notes": "Broad northern rolling rise; soften slopes and keep agricultural approaches driveable.",
      "blend_width_m": 10,
      "preferred_slope_deg": [
        4,
        12
      ],
      "hard_obstacle": false
    },
    {
      "id": "02-TR-central_rise",
      "kind": "terrain_feature",
      "polygon_m": [
        [
          254,
          430
        ],
        [
          295,
          430
        ],
        [
          310,
          450
        ],
        [
          289,
          469
        ],
        [
          254,
          469
        ]
      ],
      "height_delta_m": 2.6,
      "rotation_deg": 0,
      "notes": "Low central rise between homes; sparse shade trees, clear grassy approaches.",
      "blend_width_m": 10,
      "preferred_slope_deg": [
        4,
        12
      ],
      "hard_obstacle": false
    },
    {
      "id": "02-TR-east_rise",
      "kind": "terrain_feature",
      "polygon_m": [
        [
          337,
          393
        ],
        [
          370,
          393
        ],
        [
          370,
          450
        ],
        [
          345,
          450
        ]
      ],
      "height_delta_m": 3.4,
      "rotation_deg": 0,
      "notes": "Eastern rolling ground beside houses; no sheer wall separating neighbourhoods.",
      "blend_width_m": 10,
      "preferred_slope_deg": [
        4,
        12
      ],
      "hard_obstacle": false
    },
    {
      "id": "02-TR-west_hollow",
      "kind": "terrain_feature",
      "polygon_m": [
        [
          135,
          430
        ],
        [
          159,
          430
        ],
        [
          172,
          445
        ],
        [
          169,
          488
        ],
        [
          145,
          491
        ],
        [
          135,
          471
        ]
      ],
      "height_delta_m": -1.4,
      "rotation_deg": 0,
      "notes": "Shallow open hollow near pond and forest; does not enlarge pond or force a road tunnel.",
      "blend_width_m": 10,
      "preferred_slope_deg": [
        4,
        12
      ],
      "hard_obstacle": false
    },
    {
      "id": "02-TR-south_ripple",
      "kind": "terrain_feature",
      "polygon_m": [
        [
          205,
          376
        ],
        [
          230,
          376
        ],
        [
          229,
          419
        ],
        [
          207,
          419
        ]
      ],
      "height_delta_m": 1.5,
      "rotation_deg": 0,
      "notes": "Bumpy grass beside south-west field, traversable by van.",
      "blend_width_m": 10,
      "preferred_slope_deg": [
        4,
        12
      ],
      "hard_obstacle": false
    },
    {
      "id": "02-TR-MICRO",
      "kind": "micro_terrain_rule",
      "polygon_m": [
        [
          132.6,
          373.6
        ],
        [
          374.0,
          373.6
        ],
        [
          374.0,
          599.8
        ],
        [
          132.6,
          599.8
        ]
      ],
      "height_range_m": [
        0.15,
        0.55
      ],
      "rare_peak_m": 0.8,
      "wavelength_m": [
        3,
        8
      ],
      "notes": "Apply to meadow/off-road only, with soft rounded crests. Tuning targets, not proven van physics. Roads 0.05–0.18 m; door aprons and loading pads flatten."
    }
  ],
  "npc_population": {
    "adult_residents_outside_daytime": [
      20,
      25
    ],
    "status": "owner_approved_target",
    "notes": "Lively movement between homes and public places; no new spawn/respawn algorithm."
  },
  "gameplay_corridors": [
    {
      "id": "02-G-NW",
      "kind": "offroad_corridor",
      "polyline_m": [
        [
          157,
          540
        ],
        [
          202,
          515
        ],
        [
          216,
          511
        ]
      ],
      "width_m": 4.5,
      "notes": "Base-to-NW households shortcut; keep trunk and solid-prop clearance. Proposal adjusted around actual trunk/prop footprints; no paving or exclusive-drive restriction."
    },
    {
      "id": "02-G-CENTRE",
      "kind": "offroad_corridor",
      "polyline_m": [
        [
          260,
          529
        ],
        [
          286,
          531
        ],
        [
          307,
          532
        ]
      ],
      "width_m": 4.5,
      "notes": "Grass behind shop and central homes; articulated path may bend around trees. Proposal adjusted around actual trunk/prop footprints; no paving or exclusive-drive restriction."
    },
    {
      "id": "02-G-SOUTH",
      "kind": "offroad_corridor",
      "polyline_m": [
        [
          255,
          446
        ],
        [
          315,
          440
        ]
      ],
      "width_m": 4.5,
      "notes": "Cross-yard southern shortcut with bumps; passing between clusters is common. Proposal adjusted around actual trunk/prop footprints; no paving or exclusive-drive restriction."
    },
    {
      "id": "02-G-EAST",
      "kind": "offroad_corridor",
      "polyline_m": [
        [
          337,
          474
        ],
        [
          340,
          453
        ],
        [
          353,
          438
        ],
        [
          355,
          426
        ],
        [
          366,
          413
        ],
        [
          364,
          408
        ],
        [
          361,
          407
        ]
      ],
      "width_m": 4.5,
      "notes": "Eastern off-road passage between rolling folds and homes. Proposal adjusted around actual trunk/prop footprints; no paving or exclusive-drive restriction."
    }
  ],
  "pedestrian_access": [
    {
      "id": "ACCESS-02-H01",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          160.418,
          559.029
        ],
        [
          160.586,
          549.118
        ]
      ],
      "parent": "02-H01",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H02",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          180.53,
          557.525
        ],
        [
          181.912,
          550.147
        ]
      ],
      "parent": "02-H02",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H03",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          199.305,
          556.513
        ],
        [
          199.653,
          551.512
        ]
      ],
      "parent": "02-H03",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H04",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          196.608,
          542.447
        ],
        [
          195.065,
          551.159
        ]
      ],
      "parent": "02-H04",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H05",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          214.913,
          523.832
        ],
        [
          224.853,
          527.156
        ]
      ],
      "parent": "02-H05",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H06",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          244.756,
          553.509
        ],
        [
          240.934,
          543.061
        ]
      ],
      "parent": "02-H06",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H07",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          251.626,
          573.049
        ],
        [
          258,
          568
        ],
        [
          257,
          550
        ],
        [
          241.088,
          543.016
        ]
      ],
      "parent": "02-H07",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H08",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          307.244,
          555.509
        ],
        [
          308.325,
          540.452
        ]
      ],
      "parent": "02-H08",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H09",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          316.427,
          526.474
        ],
        [
          314.721,
          540.909
        ]
      ],
      "parent": "02-H09",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H10",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          283.878,
          519.498
        ],
        [
          284.0,
          540.0
        ]
      ],
      "parent": "02-H10",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H11",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          279.479,
          478.954
        ],
        [
          281.179,
          490.152
        ]
      ],
      "parent": "02-H11",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H12",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          311.314,
          476.489
        ],
        [
          312.026,
          487.902
        ]
      ],
      "parent": "02-H12",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H13",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          352.487,
          465.466
        ],
        [
          358.722,
          478.432
        ]
      ],
      "parent": "02-H13",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H14",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          256.526,
          455.573
        ],
        [
          244.943,
          460.302
        ]
      ],
      "parent": "02-H14",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H15",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          268.073,
          435.763
        ],
        [
          240.37,
          443.516
        ]
      ],
      "parent": "02-H15",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H16",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          286.469,
          409.037
        ],
        [
          281.681,
          386.952
        ]
      ],
      "parent": "02-H16",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H17",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          314.951,
          417.374
        ],
        [
          333.379,
          413.737
        ]
      ],
      "parent": "02-H17",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H18",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          346.039,
          410.443
        ],
        [
          333.457,
          414.151
        ]
      ],
      "parent": "02-H18",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    },
    {
      "id": "ACCESS-02-H19",
      "kind": "pedestrian_access",
      "width_m": 1.8,
      "polyline_m": [
        [
          218.913,
          431.168
        ],
        [
          236.045,
          426.989
        ]
      ],
      "parent": "02-H19",
      "notes": "Clear frontage access; starts at doorway, joins road. House wall collider must omit actual doorway."
    }
  ],
  "small_detail_catalogue": [
    {
      "kind": "woodpile",
      "size_m": [
        2.5,
        1
      ],
      "count": 7,
      "hard_obstacle": true,
      "notes": "Stored firewood at wood-burning homes.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H01-Y3",
        "02-H04-Y1",
        "02-H06-Y3",
        "02-H08-Y4",
        "02-H10-Y3",
        "02-H15-Y1",
        "02-H18-Y4"
      ]
    },
    {
      "kind": "split_log",
      "size_m": [
        0.6,
        0.18
      ],
      "count": 5,
      "hard_obstacle": false,
      "notes": "Beside woodpile, never spread evenly.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H01-Y3",
        "02-H04-Y1",
        "02-H06-Y3",
        "02-H08-Y4",
        "02-H10-Y3"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "stump",
      "size_m": [
        0.5,
        0.5
      ],
      "count": 3,
      "hard_obstacle": true,
      "notes": "Chopping stump at working yards.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-001",
        "02-D-002",
        "02-D-003"
      ]
    },
    {
      "kind": "axe_in_stump",
      "size_m": [
        0.5,
        0.05
      ],
      "count": 2,
      "hard_obstacle": false,
      "notes": "Visual, not an invented tool mechanic.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-D-001",
        "02-D-002"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "water_barrel",
      "size_m": [
        0.7,
        0.7
      ],
      "count": 10,
      "hard_obstacle": true,
      "notes": "Collect rain by shed roofs.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H02-Y4",
        "02-H03-Y4",
        "02-H05-Y4",
        "02-H07-Y4",
        "02-H09-Y4",
        "02-H11-Y4",
        "02-H12-Y4",
        "02-H14-Y4",
        "02-H16-Y4",
        "02-H17-Y4"
      ]
    },
    {
      "kind": "watering_can",
      "size_m": [
        0.35,
        0.25
      ],
      "count": 5,
      "hard_obstacle": false,
      "notes": "Next to vegetable plots.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-004",
        "02-D-005",
        "02-D-006",
        "02-D-007",
        "02-D-008"
      ]
    },
    {
      "kind": "garden_spade",
      "size_m": [
        0.3,
        0.08
      ],
      "count": 4,
      "hard_obstacle": false,
      "notes": "Lean against shed, visual only.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H01-Y2",
        "02-H02-Y2",
        "02-H04-Y2",
        "02-H06-Y2"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "garden_rake",
      "size_m": [
        0.4,
        0.08
      ],
      "count": 3,
      "hard_obstacle": false,
      "notes": "At gardening homes.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H02-Y1",
        "02-H05-Y3",
        "02-H07-Y1"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "wheelbarrow",
      "size_m": [
        1.4,
        0.6
      ],
      "count": 3,
      "hard_obstacle": true,
      "notes": "Working farm yards.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H08-Y3",
        "02-H18-Y3",
        "02-D-009"
      ]
    },
    {
      "kind": "wooden_crate",
      "size_m": [
        0.6,
        0.4
      ],
      "count": 6,
      "hard_obstacle": true,
      "notes": "Orchard produce and shop storage.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-010",
        "02-D-011",
        "02-D-012",
        "02-D-013",
        "02-D-014",
        "02-D-015"
      ]
    },
    {
      "kind": "feed_sack",
      "size_m": [
        0.5,
        0.3
      ],
      "count": 5,
      "hard_obstacle": false,
      "notes": "Dry shelter beside pigs or chickens.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-016",
        "02-D-017",
        "02-D-018",
        "02-D-019",
        "02-D-020"
      ]
    },
    {
      "kind": "feed_trough",
      "size_m": [
        1.8,
        0.7
      ],
      "count": 3,
      "hard_obstacle": true,
      "notes": "Pig-keeping yards.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H05-Y2",
        "02-H12-Y2",
        "02-H17-Y2"
      ]
    },
    {
      "kind": "chicken_feeder",
      "size_m": [
        0.45,
        0.45
      ],
      "count": 3,
      "hard_obstacle": false,
      "notes": "Beside coops.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-021",
        "02-D-022",
        "02-D-023"
      ]
    },
    {
      "kind": "egg_basket",
      "size_m": [
        0.4,
        0.3
      ],
      "count": 3,
      "hard_obstacle": false,
      "notes": "At poultry yards, visual only.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-024",
        "02-D-025",
        "02-D-026"
      ]
    },
    {
      "kind": "clothesline",
      "size_m": [
        3.5,
        0.4
      ],
      "count": 4,
      "hard_obstacle": false,
      "notes": "Lines high enough for walking, posts alone collide.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H02-Y3",
        "02-H07-Y3",
        "02-H09-Y3",
        "02-H14-Y3"
      ]
    },
    {
      "kind": "linen",
      "size_m": [
        0.7,
        0.05
      ],
      "count": 5,
      "hard_obstacle": false,
      "notes": "Visual hanging sheets, not an opaque gameplay wall.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H02-Y3",
        "02-H07-Y3",
        "02-H09-Y3",
        "02-H14-Y3",
        "02-H02-Y3"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "wash_basin",
      "size_m": [
        0.5,
        0.5
      ],
      "count": 3,
      "hard_obstacle": false,
      "notes": "Laundry households.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-027",
        "02-D-028",
        "02-D-029"
      ]
    },
    {
      "kind": "outdoor_table",
      "size_m": [
        1.5,
        0.8
      ],
      "count": 6,
      "hard_obstacle": true,
      "notes": "Common social yards.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H01-Y4",
        "02-H04-Y4",
        "02-H06-Y4",
        "02-H10-Y4",
        "02-H13-Y4",
        "02-H15-Y4"
      ]
    },
    {
      "kind": "chair",
      "size_m": [
        0.5,
        0.5
      ],
      "count": 5,
      "hard_obstacle": true,
      "notes": "By outdoor tables.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-030",
        "02-D-031",
        "02-D-032",
        "02-D-033",
        "02-D-034"
      ]
    },
    {
      "kind": "bench",
      "size_m": [
        1.8,
        0.5
      ],
      "count": 4,
      "hard_obstacle": true,
      "notes": "Shop, yard and pond bank seats.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-A-BENCH1",
        "02-A-BENCH2",
        "02-D-035",
        "02-D-036"
      ]
    },
    {
      "kind": "flower_strip",
      "size_m": [
        3,
        1
      ],
      "count": 5,
      "hard_obstacle": false,
      "notes": "Uneven care, some yards have none.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H01-Y1",
        "02-H06-Y1",
        "02-H10-Y1",
        "02-D-037",
        "02-D-038"
      ]
    },
    {
      "kind": "flower_pot",
      "size_m": [
        0.35,
        0.35
      ],
      "count": 5,
      "hard_obstacle": false,
      "notes": "Porches of cared-for homes.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-039",
        "02-D-040",
        "02-D-041",
        "02-D-042",
        "02-D-043"
      ]
    },
    {
      "kind": "compost_heap",
      "size_m": [
        1.8,
        1.5
      ],
      "count": 3,
      "hard_obstacle": false,
      "notes": "Gardening homes only.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-044",
        "02-D-045",
        "02-D-046"
      ]
    },
    {
      "kind": "wooden_pallet",
      "size_m": [
        1.2,
        0.8
      ],
      "count": 3,
      "hard_obstacle": true,
      "notes": "Practical storage, not industrial yard clutter.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-047",
        "02-D-048",
        "02-D-049"
      ]
    },
    {
      "kind": "bucket",
      "size_m": [
        0.3,
        0.3
      ],
      "count": 5,
      "hard_obstacle": false,
      "notes": "Well and animal care.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-050",
        "02-D-051",
        "02-D-052",
        "02-D-053",
        "02-D-054"
      ]
    },
    {
      "kind": "rusted_wheel",
      "size_m": [
        0.6,
        0.2
      ],
      "count": 2,
      "hard_obstacle": false,
      "notes": "Near tractor and farm shed.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-055",
        "02-D-056"
      ]
    },
    {
      "kind": "tyre",
      "size_m": [
        0.7,
        0.25
      ],
      "count": 2,
      "hard_obstacle": false,
      "notes": "A few spare tyres, no tyre-wall maze.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-057",
        "02-D-058"
      ]
    },
    {
      "kind": "handcart",
      "size_m": [
        1.4,
        0.75
      ],
      "count": 2,
      "hard_obstacle": true,
      "notes": "Farm deliveries.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-059",
        "02-D-060"
      ]
    },
    {
      "kind": "round_hay_bale",
      "size_m": [
        1.6,
        1.3
      ],
      "count": 5,
      "hard_obstacle": true,
      "notes": "Mandatory owner-reference cylindrical rolled hay/straw bales; layered circular ends and fibrous body, not rectangular bundles. Barn storage outside clear loading apron.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-HAY-ROLL-01",
        "02-HAY-ROLL-02",
        "02-HAY-ROLL-03",
        "02-HAY-ROLL-04",
        "02-HAY-ROLL-05"
      ]
    },
    {
      "kind": "haystack",
      "size_m": [
        2.8,
        2.8
      ],
      "count": 3,
      "hard_obstacle": true,
      "notes": "Field edge/hay shelter; not a road barrier.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-061",
        "02-D-062",
        "02-D-063"
      ]
    },
    {
      "kind": "net_drying_rack",
      "size_m": [
        2.5,
        0.3
      ],
      "count": 2,
      "hard_obstacle": false,
      "notes": "Fishing household and river landing.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H13-Y2",
        "02-D-064"
      ]
    },
    {
      "kind": "coiled_rope",
      "size_m": [
        0.4,
        0.4
      ],
      "count": 2,
      "hard_obstacle": false,
      "notes": "By fishing gear.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H13-Y2",
        "02-D-064"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "fishing_bucket",
      "size_m": [
        0.3,
        0.3
      ],
      "count": 2,
      "hard_obstacle": false,
      "notes": "Near fishing nets.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-065",
        "02-D-066"
      ]
    },
    {
      "kind": "upturned_boat",
      "size_m": [
        3.8,
        1.5
      ],
      "count": 1,
      "hard_obstacle": true,
      "notes": "Existing planned river-bank boat.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-FISH-BOAT"
      ]
    },
    {
      "kind": "notice_board",
      "size_m": [
        1.5,
        0.25
      ],
      "count": 1,
      "hard_obstacle": true,
      "notes": "Shop notices already planned.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-A-SIGN"
      ]
    },
    {
      "kind": "shop_sign",
      "size_m": [
        2,
        0.1
      ],
      "count": 1,
      "hard_obstacle": false,
      "notes": "Readable painted sign on shop façade.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-A-SHOP"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "mailbox",
      "size_m": [
        0.35,
        0.25
      ],
      "count": 6,
      "hard_obstacle": false,
      "notes": "Selected front walls, not identical on each home.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H01",
        "02-H02",
        "02-H03",
        "02-H04",
        "02-H05",
        "02-H06"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "house_number",
      "size_m": [
        0.25,
        0.02
      ],
      "count": 8,
      "hard_obstacle": false,
      "notes": "Mounted visual plates.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H01",
        "02-H02",
        "02-H03",
        "02-H04",
        "02-H05",
        "02-H06",
        "02-H07",
        "02-H08"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "door_mat",
      "size_m": [
        0.7,
        0.45
      ],
      "count": 4,
      "hard_obstacle": false,
      "notes": "Only at cared-for entrances.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H01",
        "02-H02",
        "02-H03",
        "02-H04"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "window_planter",
      "size_m": [
        1,
        0.25
      ],
      "count": 4,
      "hard_obstacle": false,
      "notes": "Mounted to houses, no free-floating props.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H01",
        "02-H02",
        "02-H03",
        "02-H04"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "curtain",
      "size_m": [
        1,
        0.02
      ],
      "count": 6,
      "hard_obstacle": false,
      "notes": "Visible behind windows; no fabricated interiors.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H01",
        "02-H02",
        "02-H03",
        "02-H04",
        "02-H05",
        "02-H06"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "porch_step",
      "size_m": [
        1.4,
        0.45
      ],
      "count": 5,
      "hard_obstacle": false,
      "notes": "Low entrance transition, retain carry route.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H01",
        "02-H02",
        "02-H03",
        "02-H04",
        "02-H05"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    },
    {
      "kind": "broken_timber",
      "size_m": [
        2,
        1
      ],
      "count": 1,
      "hard_obstacle": true,
      "notes": "Abandoned home only.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H19-Y2"
      ]
    },
    {
      "kind": "rusted_car",
      "size_m": [
        3.8,
        1.6
      ],
      "count": 1,
      "hard_obstacle": true,
      "notes": "Abandoned home only.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-H19-Y1"
      ]
    },
    {
      "kind": "reed_clump",
      "size_m": [
        1.5,
        1
      ],
      "count": 8,
      "hard_obstacle": false,
      "notes": "Pond margins, gaps for sightlines.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-067",
        "02-D-068",
        "02-D-069",
        "02-D-070",
        "02-D-071",
        "02-D-072",
        "02-D-073",
        "02-D-074"
      ]
    },
    {
      "kind": "rounded_rock",
      "size_m": [
        1,
        0.8
      ],
      "count": 3,
      "hard_obstacle": true,
      "notes": "Sparse forest edge only, not filled gaps everywhere.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-075",
        "02-D-076",
        "02-D-077"
      ]
    },
    {
      "kind": "drain_culvert",
      "size_m": [
        1,
        0.5
      ],
      "count": 3,
      "hard_obstacle": false,
      "notes": "At three drive crossings; no lip that traps van.",
      "status": "proposed_dressing",
      "placement_mode": "crossing_bound",
      "placement_rule": "Culverts at actual ditch/driveway crossings; footbridge only where the bank footpath crosses a drain. Preserve 1.8 m walk or 3.6 m drive clearance. Do not instantiate arbitrary yard points."
    },
    {
      "kind": "timber_footbridge",
      "size_m": [
        2.4,
        1.8
      ],
      "count": 2,
      "hard_obstacle": false,
      "notes": "Pond-bank ditch foot crossings.",
      "status": "proposed_dressing",
      "placement_mode": "crossing_bound",
      "placement_rule": "Culverts at actual ditch/driveway crossings; footbridge only where the bank footpath crosses a drain. Preserve 1.8 m walk or 3.6 m drive clearance. Do not instantiate arbitrary yard points."
    },
    {
      "kind": "mud_patch",
      "size_m": [
        3,
        2
      ],
      "count": 6,
      "hard_obstacle": false,
      "notes": "Pig/tractor areas; ground visual, no invented slow debuff.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-078",
        "02-D-079",
        "02-D-080",
        "02-D-081",
        "02-D-082",
        "02-D-083"
      ]
    },
    {
      "kind": "wheel_rut",
      "size_m": [
        4,
        1.8
      ],
      "count": 6,
      "hard_obstacle": false,
      "notes": "Soft ground near field entrances.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-084",
        "02-D-085",
        "02-D-086",
        "02-D-087",
        "02-D-088",
        "02-D-089"
      ]
    },
    {
      "kind": "dung_patch",
      "size_m": [
        0.6,
        0.4
      ],
      "count": 4,
      "hard_obstacle": false,
      "notes": "Pig shelters only, modest stylized dressing.",
      "status": "proposed_dressing",
      "object_ids": [
        "02-D-090",
        "02-D-091",
        "02-D-092",
        "02-D-093"
      ]
    },
    {
      "kind": "peeling_paint",
      "size_m": [
        1.5,
        0.01
      ],
      "count": 8,
      "hard_obstacle": false,
      "notes": "Façade variation without rebuilding whole asset.",
      "status": "proposed_dressing",
      "placement_mode": "parent_bound_visual",
      "parent_ids": [
        "02-H01",
        "02-H02",
        "02-H03",
        "02-H04",
        "02-H05",
        "02-H06",
        "02-H07",
        "02-H08"
      ],
      "placement_rule": "Mount on appropriate façade/porch/host prop, not on ground; no new collider."
    }
  ],
  "assembly_rules": [
    "Never rescale the whole district or regenerate the whole master map.",
    "Composite host objects may contain mounted visuals; only declared solid footprints enter ground-clearance checks.",
    "Use unioned road surfaces at intersections; remove internal curb/seam/markings.",
    "Foliage crown outlines and planning zones are not blocking ground footprints.",
    "Reserve clear routes before dressing; machine coordinates remain starting proposal until playtested."
  ]
}
```


## 11. Checks and remaining integration questions

See `HAMLET_VALIDATION_v03.json` for actual executed coordinate checks. No map image, SVG, game code, scene, rig or existing specification was modified. No commit, push or staging was performed.

- Church boundary exception is disclosed, not silently treated as in-bounds. Confirm the shared-world planning extent when integrating; preserve the locked church meanwhile.
- Survey the exact eastern shared road corridor and dry river bank before dock/boat placement; local proposed coordinates cannot prove the master traffic envelope.
- Props are reviewable dressing. Mounted visuals and drainage crossings require final host/crossing attachment during assembly rather than literal ground placement.
- Actual van bounce, traction, door transport, animation, NPC density and navigation are NOT RUN and need the vertical slice, not guessed success claims.
- The global crime/economy/near-base farming problem is outside this district specification and is not solved by merely adding hills or moving houses.
