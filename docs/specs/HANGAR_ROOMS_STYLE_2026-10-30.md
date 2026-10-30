# Hangar rooms: one style (Vadim 30.10.2026)

Vadim: "одна палитра, но цвета разные; свет один; детализация примерно везде одинаковая". The base hangar (GPT ref B, `V2_НОВАЯ_ИГРА/ПРОМПТ_ChatGPT/_результаты/42_База_ангар_v01/02_B_Обжитой.png`) and its texture set 45 (`.../_результаты/45_Текстуры_ангара_v01`) are the reference. The v1 workshop (Workshop_W86, red/grey industrial, bright) and pharmacy (Pharmacy_W86, turquoise retail, bright) are reused for their geometry only and re-dressed to these rules.

## 1. One palette, a different accent per room

Shared base (every room and the hall):

| Role | Colour (sRGB) | Notes |
| --- | --- | --- |
| Floor | hangar concrete, texture 01 | the same floor in all rooms (bay may add oil/tyre marks) |
| Structure, frames, trims | graphite #3A3B3D (texture 04) | door/window frames, shelf posts, counters' edges |
| Walls outside the rooms | each room its own exterior (Vadim 30.10 night: no shared wood cladding) | workshop keeps its v1 corrugated grey; pharmacy and gear their own |
| Light neutrals | warm off-white #D9CDB4 | never pure white |
| Warning | signal yellow #E0A824 + hazard stripe (06) | small doses |
| Crates, pallets | olive crate (11), light wood (12) | some in every room |

Room accent (same saturation and brightness band for all three: muted, about 35-45 % saturation, 45-60 % value):

| Room | Accent | Where |
| --- | --- | --- |
| VAN UPGRADES (workshop) | oxide red #9A4A36 | lift posts, tool chests, workbench frame (was bright #B23A2C) |
| PHARMACY | pharmacy green #4F8A6E | counter fronts, shelf units, wall band (was turquoise) |
| GEAR (armoury) | khaki #7A7A4E + dark tan #8C7A55 | counter, lockers (olive metal 09), camo uniforms (10) |

No saturated or pure colours outside small accents (labels, the green cross, tool handles).

## 2. One light

- The same warm lamps everywhere: about 3000 K (#FFB46B), the same fixture style (pendant/strip in graphite), soft pools, dim corners. No white shop/office light (the pharmacy's v1 ceiling grid and strips go, or are re-lit warm).
- Rooms are slightly brighter inside than the hall (readable shelves), never brighter than the signs.
- Signs: dark plate, warm glowing letters (texture 14), the same size class for all three.
- Few shadowed lights (at most 1 per room), no SSAO, nothing shimmers (CLAUDE.md "No flicker").

## 3. One detail level

- Each room: one hero object (lift with the van / pharmacy counter + wall shelves / gun wall behind mesh), 3-5 medium objects, small fill only on shelves.
- The same bevel size (1-2 cm), the same texture scale rules (UV in metres, no stretching), textures only from set 45 plus tints.
- Budget per room: about 15-20 k triangles with props.
- Same stylised matte look (smoothness <= 0.3, metallic low).

## 4. Details are real 3D, not painted (Vadim 30.10, main rule)

Vadim, looking at the hangar crates: a box with handles, latches and rims painted on is not acceptable. Every visible detail is geometry:

- Crates: body + raised rim/frame edges, corner caps, real latches and a recessed handle (or a bar handle) as meshes; lid seam as a real step.
- Pallets: separate planks with gaps and blocks underneath.
- Wood cladding: real boards (grooves/gaps between boards, slight depth offsets), not a flat plane with a board texture.
- Corrugated walls and roller doors: real ribs/slats in the mesh (the v1 workshop already had 0.1875 m trapezoid ribs).
- Shelves, lockers, counters, signs: posts, lips, vents, frames, plate thickness modelled.
- Textures then only add colour, wear and fine variation on top of the 3D shapes (texture set 45 stays as the colour source), never fake the shapes.
- Still low-poly: chunky bevels, no tiny bolts; keep the budget per room (about 15-20 k triangles) and use LOD or merged meshes so FPS stays >= 144 at 4K.
- Shape language = the One-Armed Robber (OAR) rules we used for the v1 downtown (stairs, balconies, frames modelled): docs/ArtDirection.md §2 "Shape language" — chunky (visible thickness >= 0.06 m on parts < 1 m, >= 0.10 m on longer ones), three levels only (mass -> secondary forms -> accents >= 0.2 m, no bolts or scratches), one-segment bevels 2-4 cm on props, 6-10 cm on large props, two segments + weighted normals on props the player stands next to, flat faces on hard surfaces, no outline/toon shader.

## 5. Even surfaces, crisp markings (Vadim 30.10, night)

- Walls and boards are one even colour: no baked dark/light stripes, no alternating light and dark boards. Shading comes only from the real 3D ribs and grooves.
- Hall walls use the v1 workshop wall texture he likes (WS86_corrugated_grey_v01: T7_metal_trapez albedo + normal), tinted to the hall's cozy-dark grey.
- Floor markings, lettering and arrows are crisp at eye height and read as clear yellow under the warm light (hue about 45-55°, not orange).
- Each room is told apart at a glance by its own surfaces and accent colour.
- Hall walls stay dark (one even dark graphite), and the hall floor is a touch darker than in build d7ffafb7.
