# Vadim's wishes for the 3D map (as of push a084e6de, 20.10.2026) — checklist

Sources read: Vadim's commits 885ae418, ad30f81c, 972aa302, faeddcff, 3005501e, 9ba8d060, 3ab133f4, 51b86d1f, cf2050ee, a084e6de;
`docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md` (master, = "v10"), `..._2026-10-18_v02.md` ("v02"), `..._2026-10-20_v03…v09.md`,
`docs/specs/MAP_SPEC_2026-10-13_v01.md` ("MAP_SPEC"), WORK_SYNC TASK-000839…000857 plus older Vadim relief TASKs
(633, 659, 660, 686, 711, 718, 741, 744, 749, 751, 786, 827), HAMLET_SPEC_2026-10-18, ROUGH_LEGEND_v45, ROUGH_SPEC v01,
DOWNTOWN_LEGEND_v26 / SPEC v03, ELITE_SPEC v01, BEACH_SPEC v01. Seniority (v10 §0): v10 → district spec/legend → v02 → picture.
Quotes are Vadim's own words (from WORK_SYNC prompts or quoted in the handoffs).

## R. Relief (terrain)

| # | Wish | Source | Vadim's words |
|---|---|---|---|
| R1 | Terrain "harmoniously uneven": hills, ravines, looks good AND is convenient for van gameplay | v10 §3; TASK-000856 | «местность… должна быть гармонично неровной… Чтобы были холмы, овраги и это все как бы гармонично и хорошо смотрелось. И удобно было это по геймплею» |
| R2 | Not enough unevenness: empty flat fields get soft small relief (waves, bumps, ditches, banks) | v10 §3; v02 §4; TASK-000751 | «неровности местности, наоборот, сейчас не хватает» |
| R3 | Benchmark = Fedya's v19 relief: flat ground ~5 m, relief "where needed"; elliptic hillocks 2–8 m, rises between districts to 10–12 m, relief at village edges and along roads | v02 §4; TASK-000633 | «перепады высот реально добавил, и они получились довольно пиздатыми и в меру» / «где надо — есть, где не надо — нету» |
| R4 | Relief is a composition: every hill/ravine has a role — separate districts, hide unwanted views ("not see the whole map"), guide detours, give viewpoints, make off-road interesting | v10 §3.1; TASK-000660 | «холм-гора, который должен защищать от того, что мы видим всю карту» |
| R5 | Micro relief 0.3–1.5 m (waves, bumps, ditches, beds, tussocks) | v10 §3.1; MAP_SPEC table | — |
| R6 | Separating hills / hollows / embankments 3–8 m, in places 10–12 m between districts | v10 §3.1; MAP_SPEC; v02 §4 | — |
| R7 | Ravines and hollows to streams and the river 2–6 m, SOFT, gentle slopes, grass on the bottom | v10 §3.1 | — |
| R8 | Pits/hollows 1–3 m are part of the relief (only van traps are forbidden) — number dropped in v10 | v02 §4 (lost in v10) | — |
| R9 | Hill B: summit 50 m, continuous barrier river→sea between Rough and Downtown; tunnel under it; VIEW B serpentine through the east part; VIEW C cornice | v10 §3.1, §5; v02 §3; TASK-000660 | «мне тоннель так-то нравится» (v02 §3) |
| R10 | VIEW B viewpoint ~+46 m, view on city, bay and port; "do not remove" (number dropped in v10) | v02 §3 (lost in v10) | — |
| R11 | Elite hill ≈44 m, a bit lower than hill B's peak; uneven plateau +40…+44 m; villas staggered on own terraces | v10 §3.1, §7.7; v02 §8.7; TASK-000827 | «элитный холм… чуть-чуть ниже, чем… максимальный пик в view B» / «Там тоже местность неровная на самом холме» |
| R12 | NW ridge ~92–95 → 56 m with foothills (denser pines, screes, boulders); mountains only in the NW (map edge) | v10 §3.1; v02 §3 | — |
| R13 | Low right ridge ~30 m (rocky ridge on Rough's east edge hides the harbour) | v10 §3.1; v02 §3 | — |
| R14 | One river: mountain lake → waterfall → gorge 6–13 m (river "not at ground level") → two natural land bridges at the Hamlet → gorge with high grey rocks at Quiet Valley → waterfall into the sea | v10 §3.1, §5; v02 §3 | — |
| R15 | Natural forms: elongated, varied steepness, saddles, washouts, rock outcrops on steep places. NO identical domes, NO grid "pox", NO sharp walls and steps | v10 §3.1 | — |
| R16 | Districts on calm pads: Rough and Downtown at the same height; Construction on a +8 m hill | v10 §3.1; v02 §4; TASK-000660 | «они должны быть на одинаковой высоте» |
| R17 | Pad edges blend softly into the surrounding relief — NO "cake" cliff around a district; no abrupt changes / artificial border at district boundaries | v10 §3.1; MAP_SPEC "Terrain composition" | — |
| R18 | Yards, loading areas, parking, plazas, paths are level | v10 §3.1; MAP_SPEC | — |
| R19 | Houses, paths, shoulders, banks fitted to the ground: nothing floats, nothing buried, no gaps under foundations; plinth grows on slopes | v10 §3.1; MAP_SPEC | — |
| R20 | Between districts 40–100 m of nature (hills, copses, hollows, streams); no empty "table" meadows, square clearings, dead-end lowlands; open places lead somewhere ("карта дышит") | v10 §3.1; v02 §2; TASK-000718 | «ты можешь ехать по равнине, и ты понимаешь, что рано или поздно ты куда-нибудь приедешь» |
| R21 | Rough: ground flat (Y = 0), only light unevenness for looks, no hills or pits | ROUGH_LEGEND §1.8; ROUGH_SPEC 2б | — |
| R22 | Hamlet: relief in 3D only — gentle bumps +1.5…+3.8 m, dip −1.4 m (from the layout `terrain`), micro 0.15–0.55 m; fields/beds drivable but shake the van | HAMLET_SPEC §2; v02 §8.2 (layout v04 features: slopes 4–12°, "no sheer wall") | — |
| R23 | Elite is a hill visible from the city, not a cliff/cape | v02 §8.7 | — |
| R24 | Tramduro: sharp rocks 5–10 m on the shores, helipad on a +3 m mound, palace on a +2 m hill | v02 §8.10 | — |
| R25 | Forest: no exit straight onto the beach (high hill in the SE) | v02 §8.1; v10 §7.1 | — |
| R26 | North: land border, endless steppe seen beyond, invisible wall along the fence (raised edge), no sea | v10 §5; v02 §8.4 | — |
| R27 | Do not press with mountains; mountains not a compass; no "city in a bowl", no hills everywhere | v02 §2, §13; TASK-000639/643/698/783 | «не сдавливало со всех сторон» |
| R28 | VIEW B serpentine: no ~15 m cut; road close to the slope surface; low earth berm/bank ~1–1.5 m (max ~2 m) with grass and stones that stops the van rolling off; grade stays 12 %; view on city and bay opens | v10 §3.2, §12 q8; v05–v09 §6/§7; TASK-000847 | «стена такая земляная… сделала не такой высокой… Чтобы она как бы была, и ты не смог на бусике съехать с холма» |
| R29 | Road grades ≤ 8 %; approved exceptions: VIEW B 12 %, Elite stone road avg ~12.5 %, max 15 % | v10 §3.2; v03–v09 §3; MAP_SPEC | — |
| R30 | Road embankments and cuts with gentle side slopes | v10 §3.2 | — |
| R31 | No van traps: no pits/lowlands the van can't leave, no tipping on flat ground | v10 §3.2; MAP_SPEC | — |
| R32 | Off-road: van crosses most meadow but slower and bumpy; dense forest, rocks, steep slopes impassable; shortcuts never faster than roads | v10 §3.2; v02 §2; MAP_SPEC | «колошматит по кочкам» |
| R33 | Drive every hill/ravine near roads and districts along and across at max van stats; smooth where inconvenient without purpose | v10 §3.2 | — |
| R34 | Before the final build: grey height mock → top height picture with labels + 4–6 ground / van shots (where hills and ravines are, how high, why) → Vadim's "yes" | v10 §3.3, §13 step 3; v02 §0.2 | — |
| R35 | Picturesqueness comes from relief, not "a couple of buildings"; scenic roads must not tire with frequent driving | v02 §2 (TASK-000649, 685) | — |
| R36 | Beach slightly uneven; place hills and small details the plan doesn't show | TASK-000744; v02 §8.9 (TASK-000833) | «немножко неровного пляжа добавляй» |

## J. Roads and joins

| # | Wish | Source | Vadim's words |
|---|---|---|---|
| J1 | Continuous surface: a road flows into a road with no step in width or HEIGHT, no gap, no shoulder "ring" over asphalt | v10 §6; v09 §6 | «почему они опять криво соединяются друг с другом» |
| J2 | Side road joins at a right angle or smooth radius, straight last 10–20 m, its axis reaches the main road's axis; no zigzags, humps, loops | v10 §6; v09 §6 | — |
| J3 | Every road leads somewhere; no dangling ends (approved dead ends only) | v10 §6; TASK-000851 | «сконнекти все дороги… чтобы при сборке их не было на Федином ПК» |
| J4 | No road through a fence: a gate with posts, or the road goes around outside | v10 §6, §7.8; TASK-000852/854 | «Почему она… через забор» |
| J5 | Widths: city 12 m + 2×5 m sidewalks = 22 m facade to facade; rural asphalt 6.4 m + gravel shoulder; village main 5.4 / local 4.2 / farm 3.6 m; Elite stone 4.5 m; alleys 5.6 m | v10 §6; TASK-000840 | «как в One Arm Robber… один в один по размеру» |
| J6 | Markings only on asphalt; dirt road = two ruts, grass in the middle, puddles | v10 §6 | — |
| J7 | Downtown entries (W; E Elite stone road; N tunnel and VIEW B; S beach) continue as carriageway to the street; lowered kerb | v10 §6; v08/v09 §6 | «что это за начало дороги? такого не должно быть» |
| J8 | Bridges on the road axis, level approach, start where the bank ends; Quiet Valley road continuous over a railed bridge; Tramduro: real bridge on piers 8.8 m (6.4 carriageway) | v10 §5–§6 | — |
| J9 | Drive each join both ways; top screenshot of every junction in the report | v10 §6 | — |
| J10 | Port: map road runs smoothly through the port, no step at the entry, to the Tramduro bridge; cornice VIEW C joins as a T | v10 §7.6; v09 §6 | «вот здесь все еще какая то хуйня» (TASK-000852, port entry) |
| J11 | Hamlet → Rough road along the river over a natural land bridge; NO Construction → Rough road | v10 §5; v02 §3 | — |
| J12 | Loops and alternative routes for chases; several entries into Downtown and Rough; no single long straight road visible from afar | v10 §4 | — |
| J13 | Tunnel exits not against a house: approach ~25 m (Rough side) / ~40 m (Downtown side), portals at the hill foot | v02 §3 | — |
| J14 | Vector roads: stitch ends closer than ~3 m (s02_network) | v08/v09 §6 (dropped from v10) | — |

## D. Districts (items that affect the 3D build)

| # | Wish | Source | Vadim's words |
|---|---|---|---|
| D1 | Forest "ok": Finnish pine forest, dense = impassable; base 1 wagon at a dead-end rail; one swamp, one lake; path to the Hamlet; no exit to the beach | v10 §7.1; v02 §8.1 | «лес ок» |
| D2a | Hamlet v07/layout v06: 24 houses + grandpa's hut; core in the centre; +3 near forest (H20–22), +2 near the mountain (H23–24), each with 3.6 m drive, plot, shed, garden | v10 §7.2; v08/v09 §4; TASK-000851 | «рядом с лесом немножко домов, парочку… И около горы пару домов» |
| D2b | Fields flat and smaller: 32×26 stubble, 40×26 ploughed, furrows 2.5 m, grass boundary; round hay bales at field edges / shelter | v10 §7.2; TASK-000851 | «поля как-то ровнее… чуть поменьше поля» |
| D2c | Church, square with table under tree, cemetery, orchard, pigsty, pond, fishing spot | v10 §7.2 | — |
| D2d | Hamlet joins nature without a seam: no backing plate, no plate edge, no visible district border | v10 §7.2; TASK-000851 | «нормально по природе соедини, а то… как будто все еще картинка на картинку наложена» |
| D2e | NOT: fences between houses, "cages", wires, kolkhoz barn, shop | v10 §7.2; HAMLET_SPEC | — |
| D2f | Grandpa's yard as in Fedya's i09 scene: barrel, paint, rocking chair, van pad | v10 §7.2; HAMLET_SPEC §2 | — |
| D3a | Construction: ONE fence along the site with main gate ~19 m to the road; no double fence | v10 §7.3; TASK-000853..856 | — |
| D3b | Two small unfinished buildings: A 24×14 frame (top floor open, scaffold, hoist, tower crane), B 20×12 slab + first columns | v10 §7.3; TASK-000840 | «два непостроенных таких небольших дома на одном стоит кран» |
| D3c | Cabins one-storey, separate group at the east fence, ~3 m passages | v10 §7.3; TASK-000841 | «обособленно… не прямо друг к другу в притирку» |
| D3d | Warehouse, machinery, van workshop, dorm; bright and sunny; fuel station — ask | v10 §7.3 | — |
| D4a | Rough denser: gaps ~10 % narrower, blocks +4 %, same layout | v10 §7.4; TASK-000851 | «чуть-чуть поплотнее… чтобы бусик не прям настолько свободно про[езжал]» |
| D4b | W–E through-drive stays but stepped via arches: A4 ~13 m higher, A5 ~15 m lower; no straight shot | v10 §7.4; TASK-000841/847 | «проезд не нужно убирать… левую арку чуть-чуть повыше, а правую чуть-чуть пониже» |
| D4c | S–N passages closed: left by 12 garages at the north fence (6 m deep, gates south, ~7.5 m drive below, ~16 m in front); right by L-wing of block E over A5 | v10 §7.4; TASK-000846–850 | «повыше и полевее, чтобы там можно было проехать» |
| D4d | Football box 40×33 m; gaps shop–box ~6 m, box–H13 ~8 m | v10 §7.4; TASK-000850 | — |
| D4e | North fence straight, with KPP (v06–v09: step over H1 removed, fence ~3 m further north — dropped in v10) | v10 §7.4; v06–v09 §2 | — |
| D4f | Ground: dry yellow-brown grass with ruts (not asphalt, not green); ring road asphalt; arches ≈6–7 m deep, opening ≥4 m | v10 §7.4; ROUGH_LEGEND §1 | — |
| D5a | Downtown streets 12 + 2×5 m; no see-through sightline hill→beach (Vd, Vs3 T-joins) | v10 §7.5; TASK-000840/842 | «сквозь город можем видеть… от холма до пляжа. Вот нужно припланировать, чтобы их не было вообще» |
| D5b | Everything built up: no surface parking lots; keep parking 03, taxi 12, fuel 41; no boulevard stubs, no lone houses outside the ring | v10 §7.5; TASK-000843/852/855 | «не надо так много парковок… пусть у нас будут домами все закрыто» |
| D5c | Alleys: single dead-end in NW1 and SW2, two dead-ends with a plug elsewhere; block 07 = van shop with gate on the street | v10 §7.5; TASK-000844 | «необязательно везде сдвоенные переулки, где-то можно одинарный» |
| D5d | Houses as in Fedya's v76 by size/structure but one floor higher (5–8, corners higher), brighter and more American, fewer repeats | v10 §7.5; TASK-000842 | «может, они должны быть на этаж выше… яркие, более американские, и не такие повторяющиеся» |
| D5e | Trees only in squares 20 and 23 | v10 §7.5; TASK-000854/855 | «сверху даунтауна… стоят у тебя деревья. На дороге самой» |
| D6 | Port: road through smoothly; cornice VIEW C T-join | v10 §7.6 | — |
| D7a | Elite: hill ~44 m; stone road semi-ring 180° on the N slope from the boulevard to the EAST gate; west gate closed (solid fence); 4.5 m stone, no markings, outer parapet, lamps; climb starts right at the city | v10 §7.7; TASK-000840 | «сделаем, что он на 180 петля, и мы уже заезжаем с той стороны» |
| D7b | Road offset from the fence 24 → 9 m; on the east the road runs between the fence and the coastal rocks (number dropped in v10) | v09 §3 | — |
| D7c | Trap gate marker; FBI building + ring in the centre; 4 villas staggered on the uneven +40…+44 plateau | v10 §7.7 | — |
| D7d | No beach exit from the estate; Elite beach under the hill reached by two sand ruts from the City Beach; foot palms every ~11 m; no patch on the slope; gap ≥ 3 m to the nearest boulevard house | v10 §7.7, §12 q13 | «элитный пляж… соединение посередине лучше продумай» |
| D8a | Quiet Valley: final lab = best base of the game; casino at the beach gate | v10 §7.8 | — |
| D8b | Low wooden fence ~1 m; openings only at the north entry (asphalt) and the beach gate | v10 §7.8; TASK-000851 | — |
| D8c | NW fence corner intact; dirt road from the forest goes around it outside and joins the asphalt right after the bridge | v10 §7.8; TASK-000854 | «дорога не должна заходить на левый угол тихой долины. Она должна обходить его» |
| D8d | River falls into the sea at the east edge; high grey rocks separate the valley from the beach | v10 §7.8 | — |
| D9a | Beach: white sand #F7F2E0 | v10 §7.9 | — |
| D9b | Two lifeguard towers, one at each van entry | v10 §7.9; TASK-000855 | — |
| D9c | Pier starts at the waterline: ~50 m into the sea + platform 30×12 | v10 §7.9; TASK-000851 | «где уже вода начинается, там начинается причал. Чтобы он не мешал» |
| D9d | Palm park between promenade and beach: two rows every ~11 m, no overlaps | v10 §7.9; TASK-000852 | «Деревья друг на друга накладываются» |
| D9e | Van passages on sand free; ruts continue to the Elite beach | v10 §7.9 | — |
| D10 | Tramduro: entry only by the bridge from the port with checkpoint; south military, north lawn + palace; van bombed on the bridge | v10 §7.10 | — |
| D11 | North border: chain-link fence, 2 towers, KPP with ONE sliding gate and "Leave the country" button; steppe; invisible wall; no sea, no rock cliff | v10 §5; v02 §8.4; TASK-000786 | «мне вот этот скальный обрыв не нравится» |

## V. Vegetation and small details

| # | Wish | Source | Vadim's words |
|---|---|---|---|
| V1 | Trees by density zones (dense / sparse / empty / palm rows), groups and singles, varied height and age, glades, no grid; never on roads, sidewalks, van lanes, loading pads, functional yards, water, roofs; ≥ ~2 m from road edge, ≥ ~3 m from facades (except front gardens) | v10 §1.2; TASK-000856 | «деревья он вообще не должен собирать деревья один в один, как на карте… где много деревьев должно быть, где мало» |
| V2 | Small details by function rules, not picture points: lamps every ~25–35 m on the sidewalk/shoulder edge, at junctions, yard entries; never in lanes/ruts/water; Rough lamps only at house corners, play areas, outer road; no wires in Hamlet/Rough; signs at junctions facing traffic; traffic lights at boulevard junctions and the plaza; zebras per legend; benches at entrances, bin by bench, hydrants at block corners; cars parallel to kerb in groups (Rough: 8 old ones); bins in alleys/service yards; nothing blocks the van | v10 §8; TASK-000856 | «с всякими фонарями, столбами… знаками… они стоят у тебя сейчас очень тупо» |
| V3 | Colliders: houses box/convex, trunks capsule (dense forest really blocks), rocks/logs solid, grass/soft bushes none; GripAnchors on lamps, rails, posts, lights, signs, hydrants, benches | v10 §4; v02 §2 | — |
| V4 | Rows only where intended (promenade palms, orchard); palms not overlapping | v10 §1.2, §7.9 | — |

## S. Surfaces and textures

| # | Wish | Source | Vadim's words |
|---|---|---|---|
| S1 | Textures agreed with VADIM via coded picture sheets ("да / поменять") before the build | v10 §9, §13 step 2; v02 §0 | — |
| S2 | Surface transitions smooth via natural edges (kerb, verge, grass edge, gravel strip, 1–3 m terrain-layer blend); no texture on texture, no translucent patches, no halos | v10 §1.2, §9; TASK-000856 | «если… две текстуры стекаются друг в друга, то он не должен пытаться это воспроизводить» |
| S3 | Rough dry grass → green meadow gradually over 40–80 m | v10 §9 | — |
| S4 | Water: Uber Stylized Water v05, Sea_trial_calm_v09; rivers without waves, with flow | v10 §9; v02 §7.3 | — |
| S5 | One-Armed Robber style everywhere: painted clean colours, no photo dirt, no acid colours | v10 §9 | — |

## L. Light, sky, fog

| # | Wish | Source |
|---|---|---|
| L1 | As in Fedya's v19 by district (v02 §6 table): Rough grey, foggy, dim; Construction bright, no fog; Hamlet brightest; transitions 40–80 m | v10 §10; v02 §6 |
| L2 | Tunnel exit glare ("слепит") | v10 §5, §10 |
| L3 | Only cheap tricks; Play on PC_RPAsset | v10 §10 |

## G. Gameplay dimensions

| # | Wish | Source |
|---|---|---|
| G1 | Van ~5.5×2.1 m, always max stats | v10 §4 |
| G2 | NPC gathering places; van can get close (kerb, lawn, passages, yards); hidden grab spots (dead-end lanes, wells, gaps behind garages) | v10 §4 |
| G3 | Loops, several entries to Downtown and Rough, places to shake police (arches, yards, parking, tunnel, copses), no single long straight roads seen from afar | v10 §4 |
| G4 | Gates/arches opening ≥ 4 m; dead-end lanes 5.6 m; yards/loading ≥ 12–15 m to turn; loading pad at every base; kerbs ~15 cm with ramps; stairs/narrow passages not drivable | v10 §4 |
| G5 | Roads are the fastest and most reliable way | v10 §3.2; MAP_SPEC |
| G6 | Feeling of space: wide streets, open meadows, views from hills — but every place has a purpose | v10 §4 |

## N. What Vadim does NOT want

| # | Item | Source |
|---|---|---|
| N1 | Square / symmetric districts, "rounded squares" | v10 §11; v02 §13 |
| N2 | Empty "table" meadows, dead-end lowlands | v10 §11; TASK-000718 |
| N3 | Mountains on all sides, mountains as a compass; city in a "bowl"; hills everywhere | v10 §11; v02 §13 |
| N4 | Uniform bumps on a grid; identical domes | v10 §3.1, §11 |
| N5 | Forest dumped "to fill" | v10 §11 |
| N6 | Extra parallel roads and road tails | v10 §11 |
| N7 | Roads through fences, crooked joins, road stubs, steps at joins and bridges | v10 §11, §14 |
| N8 | Canal by the city | v10 §11 |
| N9 | Trees on roads and in water | v10 §11; TASK-000854/855 |
| N10 | Double fences | v10 §11 |
| N11 | Lone house stubs in the meadow | v10 §11 |
| N12 | Parking lots / waste ground in Downtown | v10 §11 |
| N13 | Text and logos on models | v10 §11 |
| N14 | Boxes instead of houses, giant houses | v10 §11 |
| N15 | Photo dirt, acid colours | v10 §11 |
| N16 | Paid assets | v10 §11 |
| N17 | Sharp walls and steps in the relief; "cake" cliff around districts; ~15 m cut on the serpentine | v10 §3.1, §3.2 |
| N18 | District fences on district boundaries (except Construction, Elite, port, Tramduro, Quiet Valley low fence, state border) | v02 §2 |
| N19 | Rock cliff along the Rough north shore | TASK-000786 |

## P. Working order Vadim asked for

| # | Step | Source |
|---|---|---|
| P1 | First send Vadim a short work plan + numbered list of map/spec/logic mismatches, in pictures | v10 §0, §13 step 1 |
| P2 | Textures with Vadim via sheets until "yes" on each item | v10 §13 step 2 |
| P3 | Relief: grey height mock → top picture + ground shots → Vadim's "yes" (= R34) | v10 §13 step 3 |
| P4 | Each district: top view next to its plan, shots from all angles, van drive, FPS | v10 §13 step 5 |
| P5 | Report "fixed by logic" with every deliberate deviation from the 2D map | v10 §14 |
| P6 | Changes to gameplay / approved decisions → picture with variants 1/2/3, wait for Vadim | v10 §1.3 |
| P7 | New numbered scenes and data, approved work not overwritten; free assets only, with Fedya's consent | v10 §13 step 8 |
| P8 | Everything checked from the player camera and the van, not only from above | v10 §14 |

## What v10 compressed or lost (vs v02 and v03–v09)
- VIEW B height "+46 m" (v02 §3) — v10 keeps VIEW B but no height (R10).
- "Pits 1–3 m" in the relief recipe (v02 §4) — v10 only says "no traps" (R8).
- Hamlet bump numbers +1.5…+3.8 / −1.4 / micro 0.15–0.55 (v02 §8.2, HAMLET_SPEC) — v10 refers to HAMLET_SPEC only (R22).
- Elite road offset from the fence 24 → 9 m and "between fence and coastal rocks" (v09 §3) (D7b).
- Rough north fence: step over H1 removed, fence ~3 m further north (v06–v09) (D4e).
- s02 vector stitching tolerance ~3 m (v08/v09 §6) (J14).
- 3D checks "no point on a street sees hill B and the beach at once" and "nowhere a straight S→N gap to the fence in Rough" (v03–v09) — v10 keeps them in shortened form.
- Tunnel approach lengths ~25 / ~40 m, portals at the foot (v02 §3) (J13).
