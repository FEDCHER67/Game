# G12 — BUILDING_DETAILS — STYLE_KIT_v3

33 original static, non-living facade modules for post-Soviet buildings. Palette and geometry pipeline: STYLE_BIBLE_v2b, STYLE_KIT_v2 BEACH and HAND_PROPS. Shape direction: broad low-poly profiles, selective 2–3 cm chamfers, weighted normals, chunky 10 cm metalwork, and readable protrusions. No people, rigs, animation, photographs, random noise, commits, Unity imports, shared-library edits, or replaced deliverables.

The editable export master is SK3-BLDDETAILS-001_v01.blend. One FBX per ID below, with suffix _v01.fbx. validation_v01.json passes all 33 modules: 2,872 triangles in total. export_audit_v01_01.json independently reimports all 33 FBXs and checks metre bounds within 1 mm, origin, palette UVs, all eight ordered material slots, custom normals, and absence of degenerate triangles or animation. The master packs the existing palette image. Preview geometry is kept separately in SK3-BLDDETAILS-001_Demos_v01.blend.

## Module table

Size is actual Blender XYZ bounding-box extent, in metres (width x projection/depth x height). For windows, the requested 0.90 x 1.20, 1.20 x 1.50 and 1.80 x 1.50 are the complete outer width/height including sill and lintel. Triangle counts include every component and cap, after polygon triangulation.

| ID | Size XYZ (m) | Tris / budget | Pivot | Snapping rules |
| --- | --- | ---: | --- | --- |
| WIN_FRAME_S | 0,9 x 0,28 x 1,2 | 116 / 120 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Nominal outer W x H includes sill/lintel; wall Y=0. Sill at floor +0.90 m. |
| WIN_FRAME_M | 1,2 x 0,28 x 1,5 | 116 / 120 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Nominal outer W x H includes sill/lintel; wall Y=0. Sill at floor +0.90 m. |
| WIN_FRAME_L | 1,8 x 0,28 x 1,5 | 116 / 120 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Nominal outer W x H includes sill/lintel; wall Y=0. Sill at floor +0.90 m. |
| WIN_SHUTTERS | 2,4 x 0,16 x 1,4 | 80 / 80 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | For WIN_FRAME_M. Same bottom as window; opened pair extends 0.58 m each side. |
| WIN_BARS | 1,2 x 0,1 x 1,5 | 96 / 120 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Overlay WIN_FRAME_M; bottom aligned; stand-off beyond frame face. Ground floor only. |
| WIN_AC_UNIT | 0,8 x 0,475 x 0,63 | 72 / 80 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Mount beside/below a window; origin on wall below housing. W .80 m. |
| BALCONY_SOVIET_OPEN | 3 x 1,16 x 1,18 | 200 / 300 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Width 3.0 m; slab underside at origin. Repeat at floor pitch 2.8 or 3.2 m. |
| BALCONY_GLAZED | 3 x 1,16 x 2,68 | 244 / 400 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | 3.0 m width; slab underside at floor. Wainscot uses one accent family per building. |
| CORNICE_1M | 1 x 0,25 x 0,35 | 32 / 60 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Tile along X at exactly 1 m pitch; flat end caps, no overlap. |
| CORNICE_2M | 2 x 0,25 x 0,35 | 32 / 60 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Tile along X at exactly 2 m pitch; flat end caps, no overlap. |
| CORNICE_CORNER | 0,75 x 0,75 x 0,35 | 50 / 60 | Convex wall corner (0,0,0), bottom of eaves | Convex 90-degree turn. Connect straight ends at (-.50,0,0) and (0,.50,0). |
| LEDGE_FLOOR_1M | 1 x 0,1 x 0,22 | 20 / 40 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | X pitch 1 m; Z=0 is lower edge of 0.22 m belt course. |
| PLINTH_1M | 1 x 0,16 x 0,5 | 20 / 40 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | X pitch 1 m; ground Z=0; base-band height .50 m. Interrupt at doors. |
| PILASTER | 0,4 x 0,08 x 3 | 20 / 60 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Stack vertically at 3.0 m pitch; width .40 m. End caps are square to prevent gaps. |
| CORNER_QUOINS | 0,5 x 0,5 x 3 | 60 / 60 | Convex wall corner (0,0,0), bottom of quoin stack | Stack Z at 3 m pitch. Corner wraps front (-Y) and right (+X); no scaling. |
| DOOR_FRAME_ENTRANCE | 1,6 x 0,28 x 2,4 | 108 / 200 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Outer 1.60 x 2.40 m; threshold at origin. Place above porch top .45 m. |
| DOOR_CANOPY | 2,4 x 1,5 x 0,685 | 56 / 200 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | 2.40 m width, 1.50 m projection. Origin at underside of plate; mount at door top +.10 m. |
| PORCH_STEPS_3 | 2,2 x 1,05 x 0,45 | 28 / 200 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Ground-level origin on wall; three .15 m rises, .35 m treads; top Z=.45 m. |
| DRAINPIPE_SEGMENT_1M | 0,18 x 0,232 x 1 | 32 / 40 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Vertical Z pitch 1 m. Centreline Y=-.18 m, diameter .12 m; stack without scaling. |
| DRAINPIPE_ELBOW | 0,12 x 0,404 x 0,3 | 32 / 40 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Bottom socket centre (0,-.18,0); upper socket (0,-.48,.30). Fits 1 m segment. |
| DRAINPIPE_FUNNEL | 0,36 x 0,312 x 0,36 | 34 / 40 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Lower socket centre (0,-.18,0); top catches roof/eaves. Connect segment below. |
| ROOF_PARAPET_1M | 1 x 0,4 x 0,8 | 32 / 200 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | X pitch 1 m. Z=0 on roof deck; cap width .40 m, cap underside Z=.65 m. |
| ROOF_CHIMNEY | 0,76 x 0,76 x 1,19 | 36 / 200 | Roof plane Z=0, footprint centre X=Y=0 | Roof-plane origin at footprint centre; .60 m brick shaft. |
| ROOF_VENT | 0,76 x 0,76 x 0,8 | 104 / 200 | Roof plane Z=0, footprint centre X=Y=0 | Footprint-centre origin on roof deck. Compact mushroom vent. |
| ROOF_WATER_TANK | 1,2 x 1,2 x 1,67 | 120 / 200 | Roof plane Z=0, footprint centre X=Y=0 | Roof-centre origin, 1.20 m tank diameter; three .10 m legs. |
| ROOF_SATELLITE_DISH | 1 x 0,9 x 1,395 | 156 / 200 | Roof plane Z=0, mast base centre X=Y=0 | Roof-plane pivot on mast base; aim with Z rotation only. |
| ROOF_ANTENNA | 1,2 x 1,1 x 1,8 | 84 / 200 | Roof plane Z=0, mast base centre X=Y=0 | Roof-centre origin. 1.8 m mast; broad .10 m antenna members. |
| SHOP_AWNING_STRIPED | 3 x 1,12 x 0,61 | 144 / 150 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | 3 m width; wall origin at lowest valance level, rear fixing +.60 m above it. |
| SHOP_SIGNBOARD_BLANK | 3 x 0,2 x 0,65 | 40 / 150 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | 3 m width. Wall-plane bottom origin; blank face reserved for later text. |
| SHOP_ROLLER_SHUTTER | 3 x 0,24 x 2,4 | 140 / 150 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | 3 m wide x 2.4 m high; threshold at origin. Closed static shutter. |
| GARAGE_DOOR_METAL | 2,6 x 0,25 x 2,3 | 76 / 80 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | 2.6 m wide x 2.3 m high; threshold at origin. Double-leaf silhouette. |
| FIRE_ESCAPE_STAIR_FLOOR | 4,55 x 1,2 x 4,039 | 348 / 400 | Wall plane Y=0 at lower landing centre, X=Z=0 | Rise 3.0 m, run 3.6 m + .9 m top platform; stack delta=(3.6,0,3). Mirror/alternate for dogleg. |
| GAS_PIPE_RUN_1M | 1 x 0,22 x 0,12 | 28 / 30 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Horizontal X pitch 1 m; pipe centre Z=.06, Y=-.16. Use mustard palette yellow. |

## Placement contracts

Blender is X right, Z up, metres; outward from a facade is -Y. All FBXs have an object origin at (0,0,0), unit scale and no rotation. The master lays the meshes out in a six-column review grid; those display translations are excluded from FBX exports. Wall-plane origin means local Y=0, not the geometric centre of the projecting mesh. The canopy origin is deliberately the underside of the slab; its brackets extend below Z=0. Roof equipment uses footprint/mast centre on Z=0. Cornice corners and quoins use the convex corner rather than a bottom-centre wall pivot. The staircase origin is its lower landing on the wall.

Straight trims have flat capped ends at X=+/-0.5 or +/-1.0 m. Tile with the stated exact pitch; the closed end caps touch without requiring overlapping meshes. CORNICE_CORNER has the same cross-section as straight cornices and a true shared miter. Its front socket is (-0.50,0,0); its right-wall socket is (0,0.50,0). For the right wall, rotate a straight segment 90 degrees around Z, so its outward direction is +X. At a corner, stop straight runs at the sockets rather than placing full straight pieces through the corner.

PILASTER and CORNER_QUOINS stack at 3.0 m. Pillar end caps remain flat. On 2.8 m panel floors, align pilasters independently of floor pitch; they are decoration, not structural floor modules. DRAINPIPE_SEGMENT_1M is a capped six-sided pipe, axis at (0,-0.18,Z), with a wall clip. Both elbow end loops exactly match that pipe. Lower elbow centre=(0,-0.18,0), upper centre=(0,-0.48,0.30); add a segment at the upper offset. Funnel bottom matches the segment socket. Pipe connectors are closed game meshes, not plumbing simulations. GAS_PIPE_RUN_1M runs from X=-0.50 to +0.50 at Z=0.06; its centreline is Y=-0.16.

FIRE_ESCAPE_STAIR_FLOOR has 12 solid treads, .25 m rise, .30 m run and a .90 m top platform. Landing top is Z=3.0, railing extends above the floor. A continued straight flight uses delta=(3.60,0,3.00) so the next flight starts on the platform. A return-flight layout needs a deliberate mirrored/rotated placement and sufficient landing room; no prefab or collision simulation is supplied. The exported mesh is static.

The window glass front is Y=-0.027, behind the frame front Y=-0.18: a real recess of 15.3 cm relative to the trim. Glass remains just outside an uncut Y=0 host wall. This allows the example plain boxes to remain solid and avoids coplanar glass/wall flicker. For a true cut opening, move the module with the reveal/wall geometry as needed. Glass is an opaque 12 mm closed slab using the bible's glass swatch and smoothness, not transparency.

## Material slots and later ProcTexture replacement

Every module has these eight exact slot names in this order: plaster, brick, concrete, metal_painted, metal_dark, wood, glass, roof. They are copies of the shared Look_Palette_v2 shader, all referencing the same packed 256 x 256 palette image. Per-face UV0 is at the centre of an existing palette cell; palette alpha drives smoothness and does not drive transparency. All eight slots are intentional, including unused slots, to keep remapping stable between modules. validation_v01.json lists the used slots and swatches for each asset.

The roles describe the physical surface (wood frames, painted metal awning, brick chimney, concrete trim). Cloth has no dedicated role in the requested slot list, so the awning is assigned metal_painted as its replaceable coloured surface. Replace slots by role when ProcTexture is ready. UV0 is only a palette selector: tiled or unique new textures require world-space/triplanar mapping or new UVs. Do not apply a tiled texture to the collapsed palette UVs and expect correct scale. Minimum structural rods are .10 m, pipes .12 m diameter; glass slabs and shallow decorative face relief are deliberate exceptions to the 6 cm structural thickness rule. Broad front chamfers are used selectively instead of beveling every hidden edge, to stay within the unusually small per-module budgets.

## Build and safe revisions

From C:/Dev/Game, run:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS/build_building_details.py -- --revision 2 --samples 32
```

Use a NEW revision for geometry changes. The builder refuses to replace an existing blend, FBX, validation JSON or PNG; it has no force option. --check-only --no-render rebuilds and validates entirely in memory. --preview-existing adds missing images only after comparing the current geometry hashes with the saved revision. --audit-existing --no-render reimports exports and writes the next unused export_audit_vNN_XX.json. --no-render exports without previews. --cpu selects CPU rendering. The shared STYLE_KIT_v2 files and kit summary are read only; bytecode writing is disabled.

Export settings match BEACH/HAND_PROPS: selected one mesh, mesh only, axis_forward=-Z, axis_up=Y, apply_unit_scale=True, global_scale=1, use_mesh_modifiers=False, mesh_smooth_type=FACE, bake_anim=False, path_mode=STRIP, no custom properties. In Unity: Scale Factor 1, Bake Axis Conversion enabled, normals imported, tangents none, no animation, no generated collider. Remap each of the eight slots to its role material using the existing Style Kit palette for now. The atlas uses sRGB, Point filter, Clamp, no mipmaps and no compression. Engine integration is outside this ArtSource-only task; the exports have been round-trip checked in Blender, not placed in Unity.

## Previews

All preview paths are relative to this folder. They are Cycles renders with the BEACH studio's 45-degree warm sun, three-colour ambient, Standard view transform, and no tone mapping.

- Previews/v01/01_all_modules_lineup.png — all 33 modules on labelled wall-plane panels plus a 0.50 x 0.32 x 1.75 m non-living scale box.
- Previews/v01/02_townhouse_eye_3q.png — three-storey cream plaster townhouse, 3.2 m floor pitch, plain box host.
- Previews/v01/03_panel_block_eye_3q.png — five-storey panel block, 2.8 m floor pitch, open and glazed balconies, blank short end.
- Previews/v01/04_shop_eye_3q.png — one-storey shop, striped awning, blank signboard, side roller shutter.
- The three *_plain_box_same_camera.png renders show the same host boxes with the kit hidden, at the identical camera and light. All facade cameras are at Z=1.75 m.

Final image inspection and remaining weaknesses are recorded in visual_review_v01.md. Subjective artistic acceptance remains with the project owners.