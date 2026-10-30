# VOLUNTEERS ONLY — world map v11 → 3D map: brief for Claude

Status: **2D world map v11 approved by Vadim on 11.10.2026** ("всё заебись"). This brief is the input for Fedya's Claude Code chat, which already built the previous 3D map (Map_Greybox_v12 / Map_Look_v12) from the older top-down plan MAP_PLAN_R01_v12. v11 replaces that plan for geography, district placement, roads and district layouts. Gameplay canon stays in docs/PRODUCT.md and the canon document; this brief only covers the map and its look. The brief is in English to save tokens; Vadim's words are quoted in Russian where the exact feeling matters.

## 0. What to do, in one paragraph

Rebuild the 3D map from the v11 plan: terrain, coast, water, roads and bridges, all buildings and district objects in their places. Give it a pleasant, coherent stylized low-poly look with real 3D detail on buildings and well-chosen textures. Add light nature detailing everywhere: bushes, grass, small stones, hillocks and micro-relief. Agree the look with Fedya on a few hero samples first (see §10), then roll it out. Do not overwrite the v12 scenes or assets; make new numbered versions.

## 1. Input files

All in `ArtSource/References/Map/World_v11/`:

| File | What it is |
|---|---|
| `WORLD_MAP_v11.json` | **Main machine-readable input.** Metres; terrain, coast segments, ridge, small mountain, hills with suggested heights, river with width profile, canal, lakes/ponds/pools, sand, forest zones (dense/light), clearings, roads with classes and widths, road areas, bridges, districts, bases, 216 building footprints with kind/floors, structures (fences, piers, parks, fire escapes, rooftop water towers, etc.) and numbered points of interest with names. |
| `WORLD_MAP_v11_json_check.png` | The JSON drawn back as a picture. Use it to check your parser. |
| `VOLUNTEERS_MAP_v11_FINAL.png` | The approved map, 7370 × 3800 px, **1 px = 0.2 m**. |
| `VOLUNTEERS_MAP_v11_PREVIEW.png` | The same map, 2600 px wide. |
| `VOLUNTEERS_MAP_v11_MASTER.svg` | Vector master (1 unit = 0.2 m). Groups: L00_sea … L12_title_legend; districts are `<g id="D..">` with `translate()`. |
| `Districts/Dxx_*_on_world_map_v11.png` | Each district cut from the final map at 1:1, with its numbered objects. |
| `Districts/D05_Downtown_plan_v16.*`, `D05_Downtown_spec_v04_ru.txt` | Detailed Downtown plan and its spec (Russian): object numbers 01–20+, street furniture. |
| `Districts/D03_International_Construction_plan_v10.*`, `..._legend_v08_ru.txt` | Detailed Construction plan and legend (Russian). |
| `Districts/D01/D02/D04/D09_*_source_plan*.png` | Original approved plans of Forest, Hamlet, Rough district and City Beach, with labels. |
| `References/REF_*.webp/png` | Look references, see §4 and §8. |

The 2D builder lives on Vadim's PC (`Desktop\Map\00_Сборка_общей_карты\build_v04`, `build_world_v04.py`, exporter `export_world_json.py`). Ask Vadim's chat for a re-export instead of editing the JSON by hand.

## 1a. Your earlier map work and rules — reconcile first

Since 05.10 your chat has done map work:
- plans R01 v13–v15, built from the older Master v02 and Fedya's references;
- the digitizing frame `Master_v02/`;
- the police and crowd bakers;
- the style trial.

**World map v11 supersedes Master v02 and R01 v15 as the map to build.** Reuse your tools, not that geometry.

Your process rules still apply:
- Fedya approves the 2D map first.
- Later edits change only named areas.
- Roads stay ≤ 2 lanes.
- The van reaches every gameplay point.
- No fences on district borders, except special perimeters.

**Step 0 — Fedya reviews v11 against his own earlier wishes.** Raise any objection in WORK_SYNC before the 3D build. Known differences:

| Topic | Fedya's v13–v15 | v11 (Vadim) |
|---|---|---|
| Crossing | kept as "our" zone | replaced by **International Construction** (canon) |
| Port | NE corner with a polluting outflow into the sea | small port in the NE; Vadim removed the pier and the discharge pipe |
| Beach parking | where the old industrial zone was | City Beach has its own parking (01) south of the canal |
| Elite marina | T-pier, floating jetties, 10 berths, motor boats, breakwater light | three yacht piers facing east; your extra boats and breakwater light can enrich it in 3D if both agree |
| Quiet Valley | nightclub, bowling, arcade and a valley building removed | lab (base 5), waterfall, pond and **casino**, per Vadim's original plan |
| Fences | none on district borders | the Construction site has one fence around the site, as approved by Vadim; Quiet Valley has a low perimeter fence with open gates; Elite, port and military base have their own perimeters |
| Boulevard | ≤ 2 lanes | 14 m with a green median, i.e. one wide lane plus a parking strip per side; agree whether it counts as 2+2 |

**ID mapping for police, crowd and NPC variety:**
- Districts use ids `01`–`10`. 01–09 keep the numbering of your v15 fragments: 01 forest, 02 hamlet, 03 = construction instead of crossing, 04 rough, 05 downtown, 06 port, 07 elite, 08 valley, 09 beach. 10 is Tramduro island.
- Bases map to your old ids: `Base 1`→B01 wagon, `Base 2`→B02 grandpa's hut, `Base 3`→B03 Rough, `Base 4`→B04 Downtown, `Base 5`→B05 final lab. There is no B06 (Elite prestige property is not a main base).
- Police stations are Downtown objects 10 (SW, rotunda) and 11 (NE, with the taxi depot); check that a 4-car lot fits.
- The JSON `pois` give every other numbered object with a name.

## 2. Scale and coordinates

- Metres. Origin is the bottom-left corner of the map frame, x points east and y points north, the same convention as MAP_PLAN_R01_v12.json. Unity: `(x, terrain_height, y)`.
- Frame: 1474 × 760 m. Playable land is about 1300 × 700 m: the main island plus Tramduro island.
- PNG to metres: `x_m = px * 0.2`, `y_m = (3800 - py) * 0.2`.
- Real sizes from the plan:
  - Downtown streets: 10 m roadway plus 3 m sidewalks.
  - Boulevard: 14 m.
  - Rural asphalt: 6.4 m plus shoulders.
  - Village dirt streets: 5.4 m.
  - Lanes: 3.4 m.
  - Container cabins at the Construction site: 6 × 2.4 m.

  Keep these real sizes; they were tuned for the van.
- **Heights are not in the plan, except as suggestions** in the JSON:
  - ridge 60–150 m;
  - small mountain about 35 m;
  - Elite hill about 22 m;
  - other hills 6–10 m.

  Water level is 0. Land near the coast is 1–3 m above water, rock coasts 3–10 m. The city sits on almost flat ground with gentle slopes.

## 3. What the plan fixes and what is yours

**Follow the plan exactly:**
- district positions and outlines;
- every building footprint, its orientation and the numbered objects;
- the road network: classes, widths, junctions, bridges;
- river, canal, coast type (rock, sand, quay), hills, the small mountain, the ridge border;
- fences and gates, bases, piers.

**Yours to design:**
- **Nature — entirely yours, and it must be really beautiful,** not just filled in: forests, groves, meadows, wildflowers, bushes, grass, stones and rocks, river banks, coast, micro-relief, transitions between districts.
  > Vadim: «не нужно recreate каждое дерево с плана — это просто план по зданиям, дорогам, холмам и т. д., за природу ты отвечаешь сам»; «пиздатую природу делай».

  The circles on the 2D map are symbols. Use the JSON forest zones (dense/light), groves, clearings and meadows for character and density, then design and place nature yourself.
- Facade design, roof details, materials and textures, small street and yard props, lighting, water shading.
- Small geometric adjustments for driving: slopes, curve radii, curb ramps. Keep the topology and connections of the plan.

**Assets — ask Fedya.** Before you pick, generate, download or import any asset — models, textures, kits, store packs, Tripo or other AI generations — ask Fedya and use what he approves. That covers vegetation and nature assets too. You decide the design and placement of nature; Fedya decides which assets go in.

## 4. Global look — the quality bar

Vadim's words: «не должно быть блевотного ощущения; я не требую высоких полигонов, но картинка должна быть приятной на глаз». The current pipeline produced flat, texture-poor results before («почему я летаю по карте, а текстурок почти нет»); the new map must not.

**Base style = Fedya's STYLE_BIBLE_v2.** `docs/art/STYLE_BIBLE_v2.md`, kit `ArtSource/Props/STYLE_KIT_v2`, trial scene `Map_Look_v13_trial`. It means palette colours, form instead of noise, white trims, MSAA, SSAO and a 45° sun. Fedya is still waiting for Vadim's verdict on it.

Vadim's look requirements in this section and in §5–§8 are his direction for the whole map. They mostly agree with the bible: real 3D detail, no photo grime, pleasant and calm. Where a concrete rule differs, do not silently override either side. Show both options on the hero samples (§10) and let Fedya and Vadim decide. Possible differences:
- how much material texture the village wood, Elite plaster/stone and water get;
- shallow-water transparency;
- how "worn" the Rough district is.

Overall: stylized low-poly with clean readable shapes, in the spirit of the city references `REF_downtown_city_01–04`. Crisp edges, soft daylight. Not photo textures and not noisy.

**3D, not boxes with pictures.** This applies to every building in every district.
> Vadim: «вот этот вайб, что у нас всё 3D с выступами какими-то, а не просто прямоугольная коробка, на которую натянули 2D текстурки».

Model real depth:
- window frames with recesses of 10–25 cm;
- sills, lintels, cornices, parapets, plinths;
- balconies, porches and stoops, door frames;
- roof overhangs, chimneys, rooftop boxes, gutters and pipes;
- fire escapes, AC units, signs, awnings.

Each repeated detail is a small kit mesh, so it stays cheap. This is also the bible's facade grammar (§7): plinth, pilasters, bands, frames, sills, lintels, shutters, cornices, balconies. Surface patterns only add material: brick, roof tiles, planks, panel seams, paving.

**Textures.**
- Default to the bible: palette swatches plus its 5 line patterns, mipmaps and anisotropy; no photo grime.
- If Vadim and Fedya want more material on some surfaces (village wood, Elite stone and plaster, water), add it as clean tileable textures or trim sheets with consistent texel density. Nothing stretched, smeared or blurry.
- Colours come from the palette and district recipes: harmonious, never neon.
- Check the look on both Vadim's and Fedya's PCs: no missing or low-res textures on one machine. Earlier, textures differed between PCs, so make sure the needed materials and textures are committed or regenerate identically.

**Lighting and post.** Warm soft sun, sky ambient, light fog toward the horizon, subtle AO, mild bloom on lamps at night. The day must read well from the van and on foot.

**Readability for gameplay.** Bases, shops, police, KPPs and van entrances must be recognizable from the road.

## 5. Terrain and nature, everywhere

Vadim: «добавить кусты, неровности, холмики, траву, камешки на карту — ощущение небольшой проработанности, а не одинаковая местность на зелёных полигонах; несложная, но детализированная».

**Micro-relief.** No large flat green plane.
- Gentle 0.3–1.5 m undulations and hillocks.
- Shallow ditches along rural roads.
- Small embankments at bridges.
- Slightly raised plots in the Hamlet.
- Smooth transitions into the 2D hills.

**Ground layers.** Use several and blend them softly by noise and slope:
- meadow grass and worn grass;
- dirt patches and road gravel shoulders;
- forest floor: needles, moss, blueberry shrubs;
- sand and wet sand at the waterline;
- rock on steep slopes.

**Detail scattering.** Use small clusters with empty space between them, not uniform noise:
- grass tufts and patches of wildflowers;
- bushes of 2–3 kinds;
- pebbles, small boulders, stumps, fallen branches and logs;
- reeds at the water;
- ferns and mushrooms in the forest.

Denser along fences, walls, roadsides and riverbanks; sparse in the middle of fields. Keep roads, entrances and van loading spots clear.

**Forest types** (JSON `vegetation.forest_zones`):
- **dense** — the Forest district, behind Rough district, the slopes of the small mountain, between Forest and Quiet Valley, the west shore. The van cannot pass: trunks every 3–6 m, logs and boulders. Still see-through at eye level (see §8, 01 Forest).
- **light** — groves and clumps with open drivable gaps between them, mixed deciduous (birch, oak, linden) with some pines.

**Drivability.** The van must be able to drive almost everywhere through meadows and light forest, with uneven but passable ground. It must not pass rocks, cliffs, dense forest, the ridge, the small mountain's steep parts, or deep water.
> Vadim: «природа не должна мешать, что на бусике невозможно нигде проехать… но не везде возможен, просто не очень усложнён».

Police chases need loops and alternatives; the road network was designed with loops for escapes, so keep every road connection.

**Separators between districts.** Districts are never square zones. Between them lie 40–100 m of nature: forest belts, hills, the river, rocks. Trees and terrain come right up to the buildings; no rectangular clearings around a district.

**Mountains.**
- The ridge is only the north-west border of the map: steep grey rock with pines at the foot, out of bounds.
- The small mountain between Rough district and Downtown has a rocky crest and pine slopes; roads go around it.
- Rock outcrops sit on some hills; rocky islets sit in the sea.

**Coast.** Typed segments come from the JSON:
- rock cliffs with boulders and skerries;
- sand beaches with a wet band and foam;
- the port quay as a concrete edge;
- the Quiet Valley cove: sand between rocks.

The Forest reaches the sea over rocks; there is no beach access from the Forest.

## 6. Water

Vadim: «у воды сделай нормальные хорошие текстурки». Water is a big part of the picture (sea on three sides, river, canal), so it must look good.

- **Sea.** Use a stylized shader, not a flat blue plane:
  - colour by depth: clear turquoise over sand, deeper blue farther out;
  - soft animated normals from two slow scrolling maps at low amplitude;
  - fresnel and a sun highlight;
  - a soft foam line along beaches, around rocks, islets, piers and bridge piers;
  - small shore waves on the sand;
  - the bible's shallow band (`water.light`, about 8 m) and foam at the shore; it specifies opaque water. If a little transparency over the sand looks better, show it as an option on the hero sample.

  Model the sea floor near the coast (sand slope, rocks). No harsh tiling, no flicker, no oversaturated cyan. If the van falls into the sea, return it to the last land point, as in the previous plan.
- **River.**
  - Clearer and slightly greener than the sea, with visible flow along its direction (flow map or scrolling along the spline).
  - White water at the waterfall foot and at narrow spots.
  - Banks: wet mud band, stones, reeds, grass.
  - Widths come from the JSON width profile.
- **Waterfall.** It drops from the mountain lake down the ridge: an animated falling sheet, white foam and mist at the base, a small pool.
- **Canal.**
  - Straight, 13.2 m of water between stone walls about 1.4 m wide each.
  - Calm, darker water.
  - Promenade railing on the Downtown side, three footbridges to the beach.
  - The mouth opens into the bay with a footbridge.
- **Ponds and lakes.**
  - The Hamlet pond is calm, with reeds and lily pads.
  - The Forest has a lake and one large bog: dark water with grass hummocks.
  - The Quiet Valley pond sits under the waterfall.
- **Pools and fountains.**
  - Villa pools: bright, clean, tiled edges.
  - Downtown quatrefoil fountain on the square.
  - Fountain in front of the palace on Tramduro.

## 7. Roads, bridges and street furniture

- **One asphalt** for all asphalt roads: dark, about #5F666C as on the 2D map.
  - **Rural asphalt:** light gravel/grass shoulders, worn edges, a few patches, optional faded centre dashes.
  - **City asphalt:** crisp white markings, bold zebras only where the plan has them, stop lines, curbs about 15 cm high with ramps at driveways, plazas and parks so the van can get in.
  - The rural roads widen smoothly into the boulevard at both city entries (`road_areas` in the JSON). Keep it seamless: same colour, no wedge.
- **Dirt roads** (village streets, forest roads): two ruts with grass in the middle, puddles in dips, soft edges blending into grass. **Lanes** to houses and fields are narrower and grassier.
- **Junctions.**
  - A minor road meets a major one at a clean T.
  - Roads run straight onto bridges along the bridge axis.
  - District roads continue world roads without steps or bulges.

  Vadim spent several iterations on this; keep every junction clean in 3D too.
- **Bridges** (JSON `bridges`):
  - three road bridges over the river: stone or concrete, with railings, deck about 8 m;
  - the long Tramduro bridge from the port: concrete beam bridge on piers every ~16 m, railings, lamps;
  - three light footbridges over the canal and one over the canal mouth.
- **Street furniture.** In the city, follow the Downtown spec (`D05_Downtown_spec_v04_ru.txt`, section 7a): hydrants at corners, curbs with ramps, zebras, traffic lights, stop / give way / pedestrian / parking / no-entry signs, lamps, benches, bins, trees in pits. Elsewhere use the light versions per district. Lamps, railings and fence posts double as NPC **GripAnchor** points (canon).
- **Van access.** Gates are at least 4 m wide, turning radii work for the van, and every base has a loading spot.

## 8. Districts: plan, vibe, materials

Numbers such as "02" refer to the numbered objects in the JSON `pois` and on the district crops. Every district must feel different at a glance, while the whole map keeps one consistent style.

### 01 Forest (Лес) — Finnish pine forest, Base 1

- **Plan:**
  - dense forest in the south-west, reaching the sea over rocks; no beach access from here;
  - Base 1 is an old railway wagon at the end of a short dead-end railway;
  - a clearing with a burnt-out campfire (stones, ash, charred logs) right next to the wagon;
  - one large bog to the north-west of the wagon and a forest lake to the north-east, hills to the south-east;
  - winding dirt roads:
    - from the wagon east over the hills;
    - north to the Hamlet;
    - north-east to the main road;
    - east to Quiet Valley.
- **Vibe** (`REF_forest_finnish_pines.webp`):
  > Vadim: «финский вайб высоких сосен, через которых сложно проехать на бусике, но это не густой лес, через который вообще ничего не видно».
  - Tall straight pines with bare orange-brown upper trunks and high crowns, some spruces.
  - Floor of moss, blueberry and lingonberry shrubs and short grass.
  - From eye level you see far between the trunks: quiet, cool, slightly gloomy.
  - Off-road the van struggles: trunk spacing, roots, boulders, fallen trunks. The roads stay drivable with smooth slopes and wide enough curves.
- **Details:** ferns, mushrooms, stumps, mossy boulders, fallen trunks, a few birches at the clearings, light mist in the hollows. Group the details with empty space between them; keep the wagon exit, the campfire and the roads clear.

### 02 Hamlet (Хутор) — calm small village, Base 2

- **Plan:** Vadim's original plan, with the pharmacy removed and houses added.
  - The church is the leftmost and topmost building.
  - Grandpa's hut (Base 2) sits left of and below the centre, with its own dirt road and a yard for the van.
  - Twelve houses stand scattered at slight angles, not in rows (four were added on the world map). Each has a plot, vegetable beds and a shed.
  - Barn and farmyard, village shop, the water tower landmark (asset `ArtSource/Props/WATER-TOWER-ASTRA-001`), old wells, the pond, two yellow fields with haystacks, meadows with grass tufts, fruit trees.
  - Dirt streets meet the asphalt road along the east edge at clean T-junctions.
- **Vibe** (`REF_hamlet_illustration.png` for the composition):
  - A quiet, slightly cute and tidy CIS village with lots of open grass, gardens and fields.
  - Fewer trees than the illustration.
  - **No fences around village houses at all** (Vadim: «нет заборов у домов деревенских, никаких»). Plots are read from the beds, sheds, paths and small hedges.
  - The edge blends into the forest: gardens and meadows, then sparse trees and bushes, then the forest edge.
- **Buildings must be real 3D**, not 2D textures on boxes («хорошие текстурки для деревни, а не 2D, натянутая непонятно на что»):
  - log or plank walls with visible board and log ends;
  - carved window frames with shutters and sills;
  - porches with steps, posts and a small roof;
  - gable roofs (slate, corrugated sheet or shingles) with overhangs and chimneys, brick plinths.

  Paint is muted: green, blue, ochre, faded red. The church is a small rural church, for example with a bell tower and a small dome; it and the water tower are the tallest silhouettes.
- **Props:** woodpiles, benches by doors, buckets, barrels, a cart, scarecrow, garden tools, crop rows. Lights only at the shop, the base and key forks.

### 03 International Construction (Интернациональная стройка) — CIS construction site, no base

- **Plan v10:**
  - **Fence and gates.**
    - One fence of blue profiled sheet, about 2 m, around the whole site, about 120 × 115 m.
    - Wide open gates without barriers: main gate about 19 m with a guard booth and wheel wash, workshop gate about 18 m, east gate about 18 m.
    - Four 12 m cuts for the van.
  - **Buildings under construction.**
    - Building A (04): a 5-floor monolithic concrete frame with two stair/lift cores, scaffolding and a goods hoist.
    - Building B (05): a foundation slab with the first columns and rebar.
    - Tower crane (06) and a materials yard (03): bricks, blocks, rebar, formwork, pipes, sand and gravel piles.
  - **Container camp (07)** in typical CIS style: 6 × 2.4 m block containers in even rows with 1 m gaps; two two-storey rows with a gallery and stairs; foreman's office at the entrance; canteen, shower, a row of chemical toilets, skip, water tank, smoking corner with benches, a barrel fire. A PAZ bus at the east gate.
  - **Around the camp.**
    - Old 4-storey migrants' dormitory (08) in the north-east corner.
    - Van workshop (01) with tyres, scrap and a rusty car body.
    - Small gas station (02) outside the fence by the main road.
  - **Roads.** The main road runs straight along the south fence to the Downtown boulevard. The road to Rough district runs straight along the east fence. A road goes south to Quiet Valley.
- **Vibe:** an ordinary CIS construction site in a smaller format.
  - Muddy ground with ruts and puddles.
  - Buildings stand straight and logical; materials lie slightly messy, but where they belong.
- **Materials:**
  - raw concrete with formwork marks;
  - rusty rebar;
  - blue ribbed profiled sheet, ribs modelled;
  - containers with modelled ribbed panels in light grey, blue and beige;
  - old plaster on the dormitory.

### 04 Rough District (Неблагополучный район) — post-Soviet courtyards, Base 3

- **Plan:** Vadim's approved plan (`D04_Rough_District_source_plan_v04.png`, JSON ids).
  - 5-storey panel and brick blocks (khrushchyovkas) around courtyards, arches, dead-end alleys, rows of metal garages.
  - Football yard (04) between the den (05) and the 24h shop (03), shawarma, trash areas.
  - Base 3 is inside the grey L-shaped house in the south-west; the entrance is from the courtyard round the corner, and the van parks in its yard.
  - A U-shaped asphalt drive goes around the district. Exits:
    - west, to the north bridge and the Hamlet;
    - south-west corner, to the Construction site;
    - south-east corner, to Downtown;
    - north-east, to the port.
- **Vibe:** a lived-in, poor, post-Soviet district of a provincial northern town — "Norilsk courtyards".
  - Khrushchyovkas, brick houses, narrow passages, arches, blank end walls, garages.
  - Faded paint and modest signs. Show the age with form — dark plinths, blank end walls, garages, bins, cramped yards (bible §7.4) — rather than photo grime.
  - Drinkers hang out at the den and the shop. Gloomy and everyday, with humour; stylized and readable.
- **3D details:**
  - modelled panel seams;
  - balconies glazed in different ways, some open with junk;
  - entrance canopies, steps, railings, basement windows, drainpipes, satellite dishes;
  - inset window frames;
  - ribbed metal garage doors.
- **Props:**
  - lamps (GripAnchors) and wall lights at entrances and in the arches;
  - big trash containers, benches with bins at entrances;
  - sparse bushes and trees, small front gardens;
  - litter only where people leave it: butts and cans by the bench and den, bags by the containers;
  - old notices, a little graffiti.

  No laundry dryers, no uniform dirt, no random clutter.

### 05 Downtown (Город) — stylized NYC-like city centre, Base 4

- **Plan v16 + spec v04:** a modern, civilized centre.
  - **Streets.** A grid of straight 10 m streets and a 14 m boulevard with a green median and trees.
  - **Central blocks.**
    - Central square (04) with a quatrefoil fountain (15).
    - Two skyscrapers (01, 02) with one shared underground parking (03).
    - Offices (05, 06), a van shop with a forecourt (07), an ATM (08).
  - **Corners.**
    - Two police stations at opposite corners: 10 in the south-west, with a rotunda corner; 11 in the north-east, with the taxi depot (12).
    - Base 4 (13) in the south-east corner: the only U-shaped house, with a gated yard for the van.
  - **Other objects.** Bus stop (14), L-shaped shops (16–19), parks (20+).
  - **South edge and entrances.**
    - The south edge is a promenade along the canal, with palms and three footbridges to the beach.
    - The boulevard enters from the west (Construction) and the east (Elite); street Vc enters from the north (Rough district).
- **Vibe** (`REF_downtown_city_01–04.webp`):
  > Vadim: «как на этих скринах — пиздатые здания сами, и не только куча разных зданий вместе, а ещё большие прикольные дома».

  Building types:
  - brick walk-ups with black fire escapes and wooden water towers on the roofs;
  - beige and ochre mid-rises with light wells;
  - a round blue glass tower and glass offices;
  - a stone building with a colonnade;
  - brick lofts with saw-tooth roofs.

  At street level: stoops with railings, awnings, shop fronts with signs, rooftop billboards.

  Streets: dark asphalt with crisp white markings and bold zebras, traffic lights on poles, curbs and tiled sidewalks, hydrants.

  Palette: brick reds, teal, olive green, ochre, beige, cream, glass blue.
- **Heights and features.**
  - JSON `floors`: typically 3–6, glass offices 10, round tower 15, skyscrapers about 20.
  - The JSON lists the facades with fire escapes and the roofs with water towers and billboards. Houses stand wall to wall along the streets.

### 06 Industrial Port (Порт) — small working port

- **Plan:**
  - A concrete yard with a fence, top right on the map.
  - KPP without a barrier (01), warehouse (02), container stacks (04), two round tanks (05), service post (08).
  - A quay with a gantry crane, bollards and fenders.
  - The long bridge to Tramduro starts at its east end.
  - There is no pier and no discharge pipe; Vadim removed them.
- **Vibe and materials:** working, slightly rusty, but tidy.
  - Corrugated metal walls with modelled ribs.
  - Colourful containers in 1–3 tiers with modelled corrugation and doors.
  - Oil stains on the concrete, sea-worn quay edges.

### 07 Elite Hill (Элитный холм) — modern villas on the headland

- **Plan:**
  - **Compound.**
    - On the hill of the east headland.
    - One high fence with barbed wire around the compound and a KPP with a barrier (06) at the west entrance.
    - A private asphalt drive winds up the hill.
  - **Villas and centre.**
    - Four modern villas (01–04) on terraces at different heights and angles, each with a garden and a pool.
    - A central round plaza with a **golden statue** of a money symbol (07); it is the main landmark, not a fountain.
    - Private security house (05).
  - **East edge and the sea.**
    - A lookout terrace (08) on the east edge.
    - Stairs (12) lead through a small gate down to the private beach.
    - Three yacht piers (11) face **east** with moored yachts.
    - Sand wraps around the headland down to the bay and continues to City Beach.
- **Vibe** (`REF_elite_modern_villa_vibe.webp`):
  > Vadim: «нормальные приятные текстурки; я не говорю именно такие, но видишь вот этот вайб: всё 3D с выступами, а не прямоугольная коробка с 2D-текстурами».
  - Layered volumes in white and light plaster, dark window frames, big glass, flat roofs with pergolas and roof terraces.
  - Cantilevers, wood slat screens, stone cladding, glass balustrades.
  - Glass garages, string lights.
  - Manicured lawns, hedges, palms, garden lights.
  - Calm, prestigious, guarded.
- **Materials:** smooth plaster, warm wood slats, natural stone, clear glass, pool tiles. Nothing is a plain box.

### 08 Quiet Valley (Тихая долина) — secluded valley before a cove, Base 5

- **Plan:** Vadim's original plan, made narrower and smaller.
  - **Access.**
    - A low perimeter fence with an open north entry (04, no KPP) and an open gate to the beach (05).
    - A snake asphalt road from the river bridge down to the beach gate.
  - **Inside.**
    - Base 5, the final private lab (01), at the top right, with a short road and a forecourt.
    - A real waterfall: a rock drop with a pond (02).
    - An open lawn on the left.
    - Casino (03) near the beach exit, with a small parking lot.
    - A footpath loop along the fence.
  - **Cove.** A small sand beach between rocks. Do not turn the coast into one long beach.
- **Vibe:** calm, green, isolated, a little mysterious. Not an elite compound and not a regime facility.
  - The lab is modern: concrete, glass, clean lines.
  - The casino has a lit sign.
  - `REF_quiet_valley_illustration.png` gives the composition only; do not copy its architecture.

### 09 City Beach (Городской пляж) — open public beach

- **Plan:**
  - Wide sand south of the canal.
  - Three footbridges from the Downtown promenade.
  - Facilities: parking (01), kiosk (05), toilet and shower block (06), lifeguard tower (07), pier (08), two rest zones with umbrellas and loungers (09, 10), paths.
  - **West:** sand, then grass dunes, then sparse trees, then light forest.
  - **East:** the sand runs around the bay to Elite's beach, with palms and a promenade.
- **Vibe:** open, well-kept, warm and bright (`REF_city_beach_illustration.png`).
  - Palms not too dense, colourful umbrellas.
  - Bins, benches, signs, life rings, flags, lamps on the approaches, changing cabins.
  - Wet sand band and small waves.

### 10 Tramduro Island (Остров Трамдуро) — residence and military base

- **Plan:**
  - A compact rocky island reached by the long bridge from the port.
  - KPP at the bridge end (01); the road goes to the military base gate.
  - **Fenced military base:** two arched hangars (02), barracks (03), HQ (04), helipad (05), vehicle park with trucks and APCs (06), a watch tower.
  - **Palace of Tramduro (07):** White-House-like but its own design — a dome rotunda, two wings, a colonnade, a lawn, a fountain and an oval drive.
  - A small beach on the east side.
- **Vibe:** formal and guarded: a white palace against olive military.

### Bases

The JSON `bases` lists their positions.

| Base | District | Where |
|---|---|---|
| 1 | Forest | old railway wagon |
| 2 | Hamlet | grandpa's hut |
| 3 | Rough District | L-shaped house, courtyard parking |
| 4 | Downtown | U-shaped house, SE corner, gated yard |
| 5 | Quiet Valley | final private lab |

There is **no base** in the International Construction site; Vadim decided this on 11.10.2026. Numbering follows the order above.

## 9. Pipeline

You built v12 with this pipeline:
- `flatten_plan.py` / `flatten_look.py` produce `greybox_vNN_flat.json` / `look_vNN_flat.json` in `ArtSource/References/Map/{Greybox,Look}`.
- `MapGreyboxBuilder` and `MapLookBuilder` build `Map_Greybox_vNN` / `Map_Look_vNN`, with TerrainBaker, WaterBuilder, PropScatterer, BuildingStyles, FenceBuilder and DistrictCombiner.

Recommended path:
1. Write a converter from `WORLD_MAP_v11.json` to the flat schemas as the next free revision, **v16**: plan numbers v13–v15 are already your R01 plans, and `Map_Look_v13_trial` is the style trial. Then the existing "Build … (latest plan)" menu items pick it up, and v12 stays intact.
2. Extend the schemas where v11 needs more: building kinds and floors, facade features, typed coast, river width profile, canal walls, bridges, fences and gates, forest zones.
3. Keep `Map_Greybox_v12` / `Map_Look_v12` and their data untouched.
4. Look output under `Assets/OnlyVolunteers/Map/Look/Generated/Map_Look_*` is gitignored and rebuilt per PC. Make the rebuild deterministic so Vadim's PC shows exactly what you approved; otherwise commit what is needed.

## 10. Agreeing the look with Fedya — required steps

Vadim: «очень согласуй с Федей, когда его Claude будет делать 3D-карту на компе». Work step by step and show results before scaling up:

0. **2D approval by Fedya** (§1a): Fedya reviews World map v11 and the differences table. Objections go to WORK_SYNC, then Vadim's chat makes a new 2D revision if needed.
1. **Greybox v16.** Build terrain heights, coast, water, roads, bridges and building masses. Put a top-down screenshot next to `VOLUNTEERS_MAP_v11_PREVIEW.png` and fix any mismatch. Fedya checks it.
2. **Hero samples at final quality.** Show screenshots from player eye height and from the van for each:
   - a Downtown street corner (2 blocks);
   - a Hamlet street with 3 houses;
   - one Elite villa with its pool;
   - the Forest around the wagon;
   - the canal, City Beach and sea water;
   - one Rough district courtyard.

   Build them in the STYLE_BIBLE_v2 style, with Vadim's notes from §4–§8 as options where they differ. Show them next to the existing style trial (`StyleTrial_v2b_*`). **Fedya approves**, and Vadim when he is available, before mass production. Adjust textures and details from their feedback.
3. **District by district.** After each district: screenshots, an FPS reading, and a van drive-through for passability and police-chase loops.
4. **Nature and detail pass** over the whole map: bushes, grass, stones, micro-relief, transitions between districts.
5. **Final.** Lighting, water, performance, the same look on both PCs, and a short report in WORK_SYNC.md.

Log every working prompt as a TASK in WORK_SYNC.md, per docs/TEAM_WORKFLOW.md. Subjective acceptance of look and feel belongs to Fedya and Vadim; compiling or rendering is not acceptance.

## 11. Performance and technical notes

- **Kits and instancing.** Build buildings from kit meshes: window, door, cornice, balcony and fire-escape modules. Use GPU instancing for vegetation and props, LODs for buildings and trees, and occlusion culling in Downtown. Combine static meshes per district (DistrictCombiner).
- **Detail budget.** Limit terrain detail (grass, small stones) by distance. Fade far detail instead of popping it.
- **Textures.** Use the palette atlas, the bible's line patterns and few materials per district. Texel density is consistent and mipmaps are on.
- **Colliders.**
  - simple box/convex colliders on buildings;
  - capsule colliders on tree trunks, so the dense forest really blocks the van;
  - no hard colliders on bushes and grass;
  - colliders on rocks;
  - curb ramps the van can climb.
- **Grip anchors.** Lamps, railings and fence posts work as NPC GripAnchor points.

## 12. Do not

- recreate trees one by one from the 2D circles;
- pick, generate, download or import assets without asking Fedya;
- put 2D facade pictures on plain boxes, or stretch, blur or smear textures; avoid z-fighting and neon or oversaturated colours;
- put fences around the Hamlet houses;
- add buildings, bases, KPPs or roads that the plan does not have; small props are fine;
- make the Forest an opaque wall of foliage, or drivable everywhere;
- create a beach access from the Forest; Elite does have stairs to its own beach;
- overwrite v12 scenes, data or anyone's assets;
- change the approved 2D layout silently. Ask Vadim's chat for a new 2D revision if something does not fit.
