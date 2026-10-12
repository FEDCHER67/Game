# G12-US — BUILDING_DETAILS_US — STYLE_KIT_v3

23 original static facade and street modules for **American Downtown**. They fill the Downtown gaps listed for map plan R01 v17 (`ArtSource/References/Map/MAP_PLAN_R01_v17_REPORT.md`). This is the companion of `../BUILDING_DETAILS` (G12), which covers the post-Soviet Rough District. It keeps G12's conventions: metres, wall-plane pivots, closed low-poly shells, weighted normals, chunky .10 m metalwork, numbered revisions that are never overwritten, and identical FBX settings. Detail comes from geometry, not textures, in the One-Armed Robber manner.

Family `SK3-BLDDETAILS-US-001`, revision **v01**. `validation_v01.json` passes all 23 modules: **3,884 triangles** in total. `export_audit_v01_01.json` reimports all 23 FBXs in Blender. It checks one root mesh, triangle count, bounds within 1 mm, origin, the 11 ordered slots, palette UVs, custom normals, no degenerate triangles and no rigs or actions. Both files were produced in the cloud with the PyPI `bpy` 5.2.1 module.

**Only the script, this README and the JSON reports are in git.** Git LFS uploads are blocked in the cloud, so the `.blend` and `.fbx` files and the previews are **not committed**. Rebuild them locally with the commands below. The builder is deterministic: `validation_v01.json` stores a `geometry_sha1` per module, and the rebuild must reproduce it.

## Module table

Size is the actual Blender XYZ bounding box in metres (width x projection/depth x height). Triangles are counted after triangulation, including every part and cap.

| ID | Size XYZ (m) | Tris / budget | Pivot | Used slots | Snapping / placement |
| --- | --- | ---: | --- | --- | --- |
| US_STOREFRONT_CASTIRON_3M | 3 x 0,52 x 3,2 | 400 / 420 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | concrete, glass, metal_dark, metal_painted, wood | 3.0 m wide x 3.2 m high ground floor; threshold at origin. Fascia top Z=3.2; awning mounts with valance at Z=2.1. |
| US_STOREFRONT_CASTIRON_4_5M | 4,5 x 0,52 x 3,2 | 448 / 460 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | concrete, glass, metal_dark, metal_painted, wood | 4.5 m wide x 3.2 m high ground floor; threshold at origin. Same section as 3M; adjacent storefronts abut column to column. |
| US_AWNING_CANVAS_3M | 3 x 1,2 x 1 | 72 / 150 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | canvas, metal_dark | 3 m width; wall origin at lowest valance level, wall rail +.95 m. Over US_STOREFRONT_CASTIRON_3M at Z=2.10. Cloth colour = canvas slot. |
| US_AWNING_CANVAS_4_5M | 4,5 x 1,2 x 1 | 72 / 150 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | canvas, metal_dark | 4.5 m width; wall origin at lowest valance level, wall rail +.95 m. Over US_STOREFRONT_CASTIRON_4_5M at Z=2.10. Cloth colour = canvas slot. |
| US_BLADE_SIGN | 0,3 x 1 x 1,9 | 80 / 120 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | accent, metal_dark | Projecting sign; wall plane origin at bottom of board. Mount at Z>=3.0 between storefront fascia and first-floor windows. Faces = accent slot. |
| US_NEON_SIGN_BOARD | 2,4 x 0,18 x 0,9 | 184 / 200 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | emissive, metal_dark | 2.4 m wide wall board, wall plane bottom-centre origin. Tubes on 0.06 m stand-offs; emissive slot. Mount above the storefront fascia. |
| US_WALL_AD_PANEL | 4 x 0,06 x 3 | 124 / 140 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | accent, plaster | 4.0 x 3.0 m painted ad on a blank brick wall; wall plane bottom-centre origin. Field = accent slot, lettering/border = plaster. Raised 1-3 cm, never coplanar with the wall. |
| US_LINTEL_BRICK_JACK | 1,5 x 0,1 x 0,38 | 84 / 120 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | brick, concrete | Flat splayed jack arch for WIN_FRAME_M (1.2 m). Z=0 = window top (sill +1.5 m); width 1.50 m, 6 cm relief, protruding keystone. |
| US_ARCH_BRICK_SEGMENTAL | 1,5 x 0,1 x 0,496 | 136 / 140 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | brick, concrete | Segmental brick arch for WIN_FRAME_M (1.2 m). Spring line Z=0 = window top; 9 voussoirs, rise .22 m, ring ~.23 m. |
| US_STOOP_BROWNSTONE | 2,3 x 2,9 x 2,51 | 268 / 300 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | brick, concrete, metal_dark | Wall plane bottom-centre origin on ground. 7 x .18 m rises to a 1.0 m landing at Z=1.26 (parlour door threshold); six .30 m treads; 2.3 m wide incl. cheeks. Brownstone = brick slot. |
| US_CORNICE_PRESSED_METAL_1M | 1 x 0,66 x 0,84 | 92 / 160 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | metal_painted | Tile along X at exactly 1 m pitch; flat end caps. Two console brackets per metre at X=+/-.25 keep the rhythm continuous. Top Z=.84; sits on the parapet/top-floor line. |
| US_CORNICE_DENTIL_1M | 1 x 0,3 x 0,4 | 92 / 120 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | concrete | Tile along X at exactly 1 m pitch; five .10 m dentils at .20 m pitch (X=-.4..+.4) so joints repeat seamlessly. Top Z=.40. |
| US_ROOF_STAIR_BULKHEAD | 2,5 x 3,565 x 3,11 | 128 / 220 | Roof plane Z=0, footprint centre X=Y=0; door faces -Y | brick, concrete, emissive, metal_dark, metal_painted, roof | Roof-plane origin at footprint centre; 2.2 x 3.0 m brick box, 2.5 m walls; steel door on -Y. Keep 1.8 m clear in front of the door. |
| US_LOADING_DOCK_DOOR | 3,4 x 1,12 x 4,5 | 180 / 220 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | concrete, metal_dark, metal_painted | Wall plane origin on street ground. 1.2 m dock, 3.0 x 3.0 m sectional door (sill Z=1.2), header to 4.5 m. Truck backs on -Y; keep 4 m clear. |
| US_CHAINLINK_PANEL_3M | 3 x 0,087 x 1,73 | 216 / 240 | Ground plane Z=0, fence line Y=0, panel centre X=0 | metal_painted | Fence line Y=0; tile along X at exactly 3 m pitch with US_CHAINLINK_POST at every joint (X=+/-1.5). Top rail Z=1.75. Mesh wires .035 m: deliberate thin exception. |
| US_CHAINLINK_POST | 0,277 x 0,32 x 2 | 74 / 80 | Ground plane Z=0, post centre X=Y=0 | concrete, metal_dark, metal_painted | Fence line Y=0, post centre X=0. Place at every 3 m panel joint and both gate sides. 2.0 m tall incl. dome cap. |
| US_CHAINLINK_GATE_1_2M | 1,2 x 0,16 x 1,85 | 232 / 240 | Ground plane Z=0, fence line Y=0, panel centre X=0 | metal_dark, metal_painted | Fence line Y=0; gate opening centre X=0 between posts at X=+/-0.60. Hinges on -X; swing about (-.60,0). Frame 1.10 x 1.75 m. |
| US_STREETLIGHT_COBRA | 0,554 x 2,677 x 7,68 | 294 / 320 | Ground plane Z=0, pole base centre X=Y=0; arm -Y | concrete, emissive, metal_dark, metal_painted | Ground origin at pole base; arm reaches 2.25 m towards -Y (the carriageway). Kerb-side, 23 m spacing (map plan v17). Lens = emissive. |
| US_PARKING_METER | 0,26 x 0,24 x 1,49 | 110 / 120 | Ground plane Z=0, footprint centre X=Y=0; front -Y | glass, metal_dark, metal_painted | Ground origin; kerb edge .45 m from the kerb line, head faces the sidewalk (-Y). One per kerb parking bay. |
| US_NEWSPAPER_BOX | 0,54 x 0,51 x 1,16 | 88 / 120 | Ground plane Z=0, footprint centre X=Y=0; front -Y | accent, glass, metal_dark, metal_painted | Ground origin; set against a building or lamp, door faces -Y. Body colour = accent. |
| US_MAILBOX | 0,52 x 0,66 x 1,22 | 116 / 150 | Ground plane Z=0, footprint centre X=Y=0; front -Y | accent, metal_dark, metal_painted, plaster | Ground origin; USPS-style collection box, chute faces -Y (sidewalk). Body = accent. |
| US_FIRE_HYDRANT | 0,54 x 0,446 x 0,85 | 266 / 280 | Ground plane Z=0, footprint centre X=Y=0; front -Y | accent, metal_painted | Ground origin at barrel centre; pumper nozzle faces the street (-Y). Kerb-side, .6 m from kerb. Body = accent. |
| US_DUMPSTER | 2,24 x 1,35 x 1,36 | 128 / 220 | Ground plane Z=0, footprint centre X=Y=0; front -Y | accent, metal_dark | Ground origin at footprint centre; lids slope up to the back (+Y); fork pockets on X sides. Alley/courtyard placement. Body = accent. |

**Total: 23 modules, 3,884 triangles.** Each FBX is `<ID>_v01.fbx`.

## Placement contracts

The axes are the same as G12: Blender X right, Z up, outward from a facade is -Y. Every FBX has its origin at (0,0,0), unit scale and no rotation.

- **Wall pieces**: the origin is on the wall plane, Y=0, bottom-centre. Nothing goes behind Y=0 (validated). Storefronts, the stoop and the loading dock stand on the street ground. Awnings use the lowest valance edge as Z=0, as `SHOP_AWNING_STRIPED` does. Put an awning at Z=2.10 over the storefront of the same width. The storefront fascia top is Z=3.20. The dentil cornice can run as a belt course straight on top of it (Z=3.20).
- **Window heads** (`US_LINTEL_BRICK_JACK`, `US_ARCH_BRICK_SEGMENTAL`): Z=0 is the top of G12 `WIN_FRAME_M`, which is the sill height +1.50 m. Both pieces are exactly 1.50 m wide.
- **Stoop**: the landing top is Z=1.26. Place G12 `DOOR_FRAME_ENTRANCE` at Z=1.26 on the same X.
- **Tileable cornices**: tile at exactly 1 m pitch with flat end caps. The consoles (X=±.25) and dentils (X=-.4…+.4 at .20 m) are positioned so the joints repeat seamlessly. No corner pieces were made: stop runs at the building corner, or use G12 `CORNICE_CORNER` (that profile is different).
- **Chain-link fence**: `PANEL_3M` tiles at 3 m. Put a `POST` at every joint (X=±1.5). The gate spans 1.2 m between two posts, with the hinge on -X and the swing axis at (-.60,0). The mesh wire is .035 m thick. This is a deliberate exception to the .10 m rule, like glass in G12. The diamonds are chunky, 3/7 m along X.
- **Ground pieces**: Z=0 is the ground (pavement), at the footprint centre. Nothing goes below Z=0 (validated). The cobra-head arm points -Y, towards the carriageway. Street lamps are 23 m apart, per the v17 map plan.
- **Roof piece**: `US_ROOF_STAIR_BULKHEAD` uses Z=0 at the roof deck and the footprint centre. The door faces -Y.

## Material slots → StyleKit_v3 categories

All 23 modules have the same **11** slots in this exact order. The **first eight are identical to G12** (`plaster, brick, concrete, metal_painted, metal_dark, wood, glass, roof`), so the Rough District remap stays valid. Three US slots are added after them. The awning colour comes through the `canvas` slot, as the brief asks. Body paint for the hydrant, mailbox, newspaper box, dumpster, sign faces and wall ad comes through `accent`, assigned per instance. Neon and lamps use `emissive`.

The Blender materials are flat Principled colours. Each one is the v07 mean of its category, read from `../../../Textures/StyleKit_v3/candidate_v07/grade_v07.json` at build time; `colour_source_sha256` in the validation JSON records that file. A role with no v07 category uses a Look_Palette_v2 swatch muted by the v07 initial grade (S×0.75, V×0.85). UV0 still points at the centre of a Look_Palette_v2 cell, as in G12, so that palette stays usable as a fallback. Tiled ProcTextures need world or triplanar mapping, because UV0 is only a palette selector.

| # | Slot | StyleKit_v3 category | Blender colour | Source |
| ---: | --- | --- | --- | --- |
| 0 | plaster | 3b_plaster_stucco | #B8AD98 | grade_v07.json after.mean_hex |
| 1 | brick | 3a_brick | #8C4F42 | grade_v07.json after.mean_hex |
| 2 | concrete | 3c_concrete_panels | #ADABA6 | grade_v07.json after.mean_hex |
| 3 | metal_painted | 6a_painted_metal_panels | #8E9396 | grade_v07.json after.mean_hex |
| 4 | metal_dark | 6b_lightly_weathered_metal | #4D5052 | v07 mean at value 0.32 (dark cast iron) |
| 5 | wood | 5a_wood_planks_fences | #856450 | grade_v07.json after.mean_hex |
| 6 | glass | — (no v07 category yet) | #63758E | Look_Palette_v2 glass.dark, v07 initial grade S*0.75 V*0.85 |
| 7 | roof | 4d_flat_bitumen_roof | #3E4247 | grade_v07.json after.mean_hex |
| 8 | canvas | — (no v07 category yet) | #974A4F | Look_Palette_v2 red.dark, v07 initial grade S*0.75 V*0.85 |
| 9 | accent | 6a_painted_metal_panels | #47567F | Look_Palette_v2 cobalt.dark, v07 initial grade S*0.75 V*0.85 |
| 10 | emissive | — (no v07 category yet) | #FFE2A8 | Look_Palette_v2 lamp_glow, unmuted (light source) |

Preview tints used per module are stored in the validation JSON under `preview_tints`. They are muted the same way: canvas red/green, mailbox and newspaper box blue, hydrant red, dumpster green, wall ad mustard, neon pink. In previews they are applied as object-linked slot overrides; the exported meshes keep the default slot materials. In Unity, make a material instance per colour and assign it to the `canvas` or `accent` slot.

## Build and export (local, Windows)

From `C:/Dev/Game`, using the same Blender as G12:

```powershell
# full build: master .blend, 23 FBX, validation, previews (Cycles); refuses to overwrite anything
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS_US/build_building_details_us.py -- --revision 1 --samples 32
```

`validation_v01.json` and `export_audit_v01_01.json` are already in git. The full build refuses to run while `validation_v01.json` exists. To recreate the v01 binaries locally, rename the committed JSONs first or move them out of the folder. After the build, check that the `geometry_sha1` values match the committed ones, for example with `git diff --no-index`. Then put the committed JSONs back. Do not commit the build's own copy of the validation: it may record a different Blender version string.

```powershell
# rebuild/validate in memory only, writes nothing
& '...blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS_US/build_building_details_us.py -- --revision 1 --check-only
# reimport the FBXs and write the next export_audit_v01_NN.json
& '...blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS_US/build_building_details_us.py -- --revision 1 --audit-existing --no-render
# only missing previews, after comparing geometry hashes with validation_v01.json
& '...blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS_US/build_building_details_us.py -- --revision 1 --preview-existing
```

The cloud build used these commands, from the repository root, after `pip install bpy==5.2.1` (Python 3.13):

```bash
python3 -I ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS_US/build_building_details_us.py -- --revision 1 --samples 32 --cpu
python3 -I ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS_US/build_building_details_us.py -- --revision 1 --audit-existing
```

Other flags: `--no-render` exports without previews; `--cpu` forces CPU Cycles. Change geometry only in a **new** `--revision N`. The script imports `../BUILDING_DETAILS/build_building_details.py` and `STYLE_KIT_v2/_lib` read-only and changes neither.

**FBX export settings** (identical to G12): selected single mesh, `object_types={'MESH'}`, `axis_forward='-Z'`, `axis_up='Y'`, `apply_unit_scale=True`, scale 1, `use_mesh_modifiers=False`, `mesh_smooth_type='FACE'`, `add_leaf_bones=False`, `bake_anim=False`, `path_mode='STRIP'`, `use_custom_props=False`. **Unity**: Scale Factor 1, Bake Axis Conversion on, normals imported, tangents none, no animation, no generated collider. Remap the 11 slots by role to the StyleKit_v3 v07 materials listed above. Unity import and placement on the map are not part of this task.

## Local outputs (not in git)

- `SK3-BLDDETAILS-US-001_v01.blend`: the master. It holds the 23 export meshes in a 6-column grid; the local pivots stay at (0,0,0).
- `<ID>_v01.fbx` × 23.
- `SK3-BLDDETAILS-US-001_Demos_v01.blend`, plus `preview_manifest_v01.json` (committed).
- `Previews/v01/01_all_modules_lineup.png`: all 23 modules with triangle labels and a 1.75 m scale box.
- `Previews/v01/02_downtown_street_eye_3q.png`, `03_downtown_street_high_3q.png` and `04_ground_floor_closeup.png`. They show a 15 × 9 × 9.6 m three-storey brick building: two storefronts with awnings, the stoop with a G12 door, neon and blade signs, lintels and arches over G12 `WIN_FRAME_M`, pressed-metal and dentil cornices, a roof bulkhead, a wall ad, the loading dock, and kerb furniture (cobra light, hydrant, meters, mailbox, newspaper boxes, dumpster, fence). `02_..._plain_box_same_camera.png` is the same camera with the modules hidden.

## Known limits

- The cloud previews were inspected visually (lineup, street, close-up). Subjective acceptance and Unity placement remain with the project owners.
- The neon board carries generic blocky lettering ("EAT"). Other words need a new revision or a separate module.
- There are no corner pieces for the US cornices, no 2 m versions, and no sash-window module. The heads sit over G12 `WIN_FRAME_M`.
- The segmental arch reads as a relieving arch over a rectangular window; the window itself is not arched.
- The brownstone colour uses the `brick` slot (3a_brick). The chain-link mesh is real geometry, not alpha, so it is expensive in long runs (216 tris per 3 m). For long fences, consider an alpha-card LOD later.
