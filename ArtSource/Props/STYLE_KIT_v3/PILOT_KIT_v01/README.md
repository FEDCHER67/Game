# G16 — PILOT_KIT_v01 — STYLE_KIT_v3

37 original static modules for the Hamlet and Rough District map pilots. Chunky low-poly silhouettes, modelled facade depth, broad wood/metal forms and muted colours from the exact category target HSV values in `ArtSource/Textures/StyleKit_v3/candidate_v07/grade_v07.json`. No texture noise, photographic surfaces, vertex jitter, people, rigs or animation.

The editable export master is **SK3-PILOT-001_v01.blend**. One mesh and one `_v01.fbx` per ID below. **7,208 triangles total**, all within the declared budgets. `validation_v01.json` contains 37 passing module records and **572 compound box collision proxies**. `export_audit_v01_01.json` re-imports every FBX and compares it with the saved master. `collision_surface_audit_v01_01.json` independently checks 1,152 standable-surface samples against that master.

Built with Blender 5.2.1 LTS in background mode on 13 October 2026. Only this new folder was written. No Unity execution/import, commits, shared-library changes, replaced deliverables or file deletions.

## Module table

Size is the measured Blender **XYZ bounding-box extent**, in metres (width x depth/projection x height), including small projecting parts. Z is up; facade outward is -Y. Window sizes include trim and sill. Door nominal 1.0 x 2.1 m describes the leaf; the complete frame is larger. Budget counts include all caps and triangulated polygons. Group A = missing Hamlet props; B = rural house detail; C = plots/yards; D = Rough District.

| ID | Size XYZ (m) | Tris / budget | Pivot | Snapping rules |
| --- | --- | ---: | --- | --- |
| SCARECROW | 1.28 x 0.406 x 1.9 | 124 / 800 | Ground Z=0, footprint centre X=Y=0; front -Y | Front -Y. Post foot on ground; 1.90 m overall. Coat sleeve and hem deliberately uneven. |
| MAILBOX_RURAL | 0.588 x 0.715 x 1.51 | 60 / 500 | Ground Z=0, footprint centre X=Y=0; front -Y | Post foot at origin. Mouth/front -Y; mount beside gate outside clear opening. |
| CART_WOODEN | 1.783 x 2.61 x 1.22 | 416 / 1500 | Ground Z=0, footprint centre X=Y=0; front -Y | Two wheels and one forward shaft. Bed top Z=.72 m. Front/shaft -Y. |
| WOODPILE | 2 x 0.8 x 1.4 | 1116 / 1200 | Ground Z=0, footprint centre X=Y=0; front -Y | Overall envelope 2.0 x .8 x 1.4 m. Logs face -Y; open sides. |
| SHED_RUINED | 3.256 x 2.84 x 2.767 | 420 / 1800 | Ground Z=0, footprint centre X=Y=0; front -Y | 3 x 2.6 m wall footprint; clear front opening. Broken walls and three missing roof panels; no invisible hull. |
| BARN_RUINED | 5.254 x 4.24 x 3.997 | 420 / 3000 | Ground Z=0, footprint centre X=Y=0; front -Y | 5 x 4 m wall footprint; open front, partial walls and holed pitched roof. Ground origin. |
| TRACTOR_BROKEN | 1.92 x 3.2 x 2.395 | 416 / 3000 | Ground Z=0, footprint centre X=Y=0; front -Y | Length 3.20 m along Y; front -Y. Missing front-right wheel, visible axle and grounded support block. |
| HAY_BALE_ROUND | 1.44 x 1.22 x 1.22 | 196 / 500 | Ground Z=0, footprint centre X=Y=0; front -Y | Axis X, flat octagonal ground contact; 1.4 m long. Broad bands, no fine straw noise. |
| HAY_BALE_SQUARE | 1.1 x 0.695 x 0.6 | 84 / 300 | Ground Z=0, footprint centre X=Y=0; front -Y | 1.1 x .65 x .60 m core. Top standable; broad two-band silhouette. |
| WIN_FRAME_RURAL_090x120 | 0.9 x 0.28 x 1.2 | 88 / 120 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Outer W/H includes nalichnik and sill; sill bottom at floor +.90. Glass front Y=-.035, trim front Y=-.18. |
| WIN_FRAME_RURAL_120x140 | 1.2 x 0.28 x 1.4 | 88 / 120 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Outer W/H includes nalichnik and sill; sill bottom at floor +.90. Glass front Y=-.035, trim front Y=-.18. |
| WIN_SHUTTERS_RURAL | 2.38 x 0.185 x 1.22 | 144 / 300 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Open pair for WIN_FRAME_RURAL_120x140; same wall pivot and bottom. Centre opening 1.20 m. |
| DOOR_FRAME_RURAL | 1.28 x 0.38 x 2.24 | 96 / 320 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Door leaf 1.0 x 2.1 m; front Y=+.12, true 12 cm wall recess. Cut host opening 1.0 x 2.1 m, depth >=.20 m. Closed static leaf. |
| PORCH_RURAL | 2.088 x 2.16 x 3.016 | 192 / 1500 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Wall Y=0. Three .15 m risers and .32 m treads; platform 1.50 x 1.10 m, top Z=.45. Door sits at Z=.45. Two roof posts. |
| PLINTH_STONE_1M | 1 x 0.235 x 0.6 | 120 / 180 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Exact X pitch 1 m; flat capped ends X=+/- .50. Bottom Z=0, top .60; interrupt at doors. |
| EAVE_FASCIA_1M | 1 x 0.2 x 0.28 | 24 / 80 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Exact X pitch 1 m, capped ends; board bottom at roof eave elevation. |
| GABLE_VENT | 0.72 x 0.195 x 0.58 | 96 / 200 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Wall plane; mount in gable with bottom at desired elevation. Opaque back prevents wall flicker. |
| CHIMNEY_BRICK_RURAL | 0.74 x 0.74 x 1.34 | 132 / 400 | Roof plane Z=0, footprint centre X=Y=0 | Roof-plane origin Z=0. Four flue walls leave real opening; cap/rim supports standing. |
| FENCE_PICKET_2M | 2 x 0.21 x 1.2 | 132 / 400 | Ground Z=0, footprint centre X=Y=0; front -Y | X pitch 2 m between end sockets +/-1. Separate POST on sockets. Flat picket tops, height 1.20 m; solid boards, open gaps. |
| POST | 0.24 x 0.24 x 1.34 | 24 / 100 | Ground Z=0, footprint centre X=Y=0; front -Y | Picket fence socket post. Centre on joints or gate outside; 0.18 m square, top 1.30 m. |
| GATE_PICKET | 1.48 x 1.104 x 1.3 | 156 / 400 | Ground Z=0, footprint centre X=Y=0; front -Y | Open 90 degrees toward -Y, hinge X=-.56. Clear passage X=[-.50,.50], 1.00 m. Posts included. No collider across opening. |
| FENCE_BOARD_2M | 2 x 0.355 x 1.8 | 168 / 400 | Ground Z=0, footprint centre X=Y=0; front -Y | Solid 2 m board panel, 1.8 m high. Exact X pitch 2 m; integrated back posts remain inside ends. |
| GATE_DOUBLE | 3.88 x 1.61 x 1.92 | 336 / 600 | Ground Z=0, footprint centre X=Y=0; front -Y | Two leaves opened 90 degrees toward -Y. Included posts; clear 3.00 m passage X=[-1.5,1.5]. Static open gate, no opening collider. |
| RETAINING_EDGE_TIMBER_1M | 1 x 0.4 x 0.6 | 36 / 180 | Ground Z=0, footprint centre X=Y=0; front -Y | Exact X pitch 1 m; height .60 m, flat continuous .40 m-deep top. Place along raised soil boundary. |
| RETAINING_EDGE_STONE_1M | 1 x 0.46 x 0.6 | 60 / 200 | Ground Z=0, footprint centre X=Y=0; front -Y | Exact X pitch 1 m; height .60 m. Flat .46 m-deep cap spans the full tile, no end protrusions. |
| GARDEN_BED_2M | 2 x 1 x 0.383 | 252 / 500 | Ground Z=0, footprint centre X=Y=0; front -Y | Outer size 2.0 x 1.0 m. Border top .30 m, soil top .23 m. Sparse planting leaves paths visible. |
| WELL_RURAL | 2.155 x 1.5 x 2.576 | 340 / 1000 | Ground Z=0, footprint centre X=Y=0; front -Y | Open 0.8 m square shaft. Four log walls and rim have individual collision; roof posts and crank are solid. No invisible lid. |
| OUTHOUSE | 1.42 x 1.432 x 2.303 | 164 / 1000 | Ground Z=0, footprint centre X=Y=0; front -Y | 1.3 x 1.2 m footprint, closed static front -Y. Broad crescent-like vent relief; no animation. |
| GARAGE_DOOR_METAL_3M | 3.28 x 0.31 x 2.5 | 180 / 400 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Wall plane Y=0; clear frame width 3 m, opening height 2.36 m. Two closed static leaves. Host wall cut-out required. |
| GARAGE_DOOR_METAL_3M_AJAR | 3.28 x 1.425 x 2.5 | 180 / 400 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Same frame as closed. Right leaf 58 degrees outward; collision rotates with leaf. Approx .68 m access at door plane; not van-width. |
| GARAGE_ROW_ROOF_EDGE_1M | 1 x 0.38 x 0.32 | 24 / 100 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Exact X pitch 1 m. Origin is bottom of edge at garage roof elevation. Flat capped ends. |
| DUMPSTER_ENCLOSURE | 4 x 2 x 1.5 | 72 / 400 | Ground Z=0, footprint centre X=Y=0; front -Y | Outer 4 x 2 m; wall height 1.5 m. Front -Y has 3.6 m clear opening. No front wall/collision. |
| BENCH_SOVIET | 1.8 x 0.595 x 0.97 | 108 / 800 | Ground Z=0, footprint centre X=Y=0; front -Y | Seat top .46 m, length 1.8 m. Chunky concrete ends, wooden slats and one shortened back slat. |
| LAUNDRY_POLE_PAIR | 3.46 x 1.15 x 2.24 | 72 / 200 | Ground Z=0, footprint centre X=Y=0; front -Y | Pair centres X=+/-1.6 m, span 3.2 m. Bare courtyard T-poles only; no laundry or lines, per ArtDirection.md. |
| CONCRETE_LEDGE_1M | 1 x 0.625 x 0.45 | 24 / 100 | Ground Z=0, footprint centre X=Y=0; front -Y | Exact X pitch 1 m; top Z=.45, .60 m deep and continuous. Ground centre origin. |
| BASEMENT_ENTRANCE | 1.85 x 2.7 x 2.79 | 276 / 1200 | Wall plane Y=0, bottom-centre X=Z=0; outward -Y | Wall Y=0, pavement Z=0. Descend toward +Y: six .18 m risers, .30 m treads; landing top -1.08. Cut terrain X=[-.84,.84], Y=[-2.60,0], depth 1.20; cut basement doorway. |
| METAL_STAIR_EXTERNAL | 5.02 x 1.56 x 3.85 | 372 / 1800 | Wall Y=0 at lower flight start X=Z=0; outward -Y | Wall plane Y=0, lower entrance X=0 at ground. Flight rises +X: 14 risers .20 m, run .28 m each; top landing X=[3.92,5.02], top Z=2.80. Clear tread width 1.20 m; rails outside. |

## Placement contracts

All export objects have origin (0,0,0), unit scale and zero rotation. The master uses a six-column review grid with 7 m spacing. These object translations are display offsets only; mesh vertices and JSON collision data remain module-local. Reset a module's display translation to zero before exporting it manually. Free-standing pivots are on the ground at the main footprint's centre, not necessarily at the centre of the complete bounds when shafts, handles or flags project out. Roof equipment uses roof plane Z=0. Basement and wall pieces have the documented wall-plane exceptions.

- **Wall details:** wall plane Y=0, front -Y. Window glass front is Y=-.035, behind the wooden jamb front at -.18; it can sit outside an uncut wall, following G12. The rural door is a true wall recess: its leaf front is Y=+.12. Cut the host wall opening 1.0 m wide, 2.1 m high and at least .20 m deep. Its raised face panels sit forward of the recessed leaf. Place a porch door at Z=.45.
- **Porch:** three .15 m rises and .32 m treads lead onto a 1.50 x 1.10 m platform with top Z=.45. Side rails and the two canopy posts sit outside the platform. The rear is open for the host doorway. No whole-porch collision box obstructs the walking space.
- **External stair:** 14 risers at .20 m, .28 m tread run; rise 2.80 m. Clear tread width 1.20 m, top platform 1.10 x 1.20 m. Flight ascends +X beside wall Y=0. Landing exit at +X stays open. Colliders are individual solid treads, not an invisible ramp.
- **Basement:** pavement entrance at Y=-2.60, Z=0. Six .18 m descents lead toward +Y to landing Z=-1.08. Excavate X=[-.84,.84], Y=[-2.60,0] down to -1.20; cut a corresponding host doorway. Do not place over an intact ground collider. Previews raise the complete piece for a cutaway view; those display offsets are not export offsets.
- **Tiling:** straight 1 m trims, ledges and retaining edges terminate at X=+/- .50; fences at +/-1. Tile at their exact documented pitch with matching end caps, no overlap or scale. Continuous flat retaining tops are .40 m deep (timber) or .46 m (stone), at Z=.60. Concrete ledge top is .60 m deep at Z=.45. Interrupted stone relief stays subordinate to the continuous cap.
- **Fences and gates:** solid fence boards/rails have collision at the visible members, including flat top surfaces. `POST` is the separate picket socket post. Board fence posts are included. Gates include their own posts, are static in the open pose, and preserve at least 1.0 m / 3.0 m clear passages. Never create a bounding collider over the opening. Double gate leaves open toward -Y; their thickness and braces remain outside the documented clear passage.
- **Garages:** closed and ajar variants share a 3.0 m frame opening. Right leaf of the ajar variant opens 58 degrees; its collision rotates with it. This variant leaves only a narrow pedestrian gap, not a vehicle passage. Both require a host-wall cut-out. These are static meshes, not animated door assemblies.
- **Ruins/well/enclosure:** collision is per wall, post, roof panel and rim. Roof holes, ruined walls, the well shaft and the dumpster enclosure front remain real openings. No solid module hull fills them. Ruins have no floor slab; provide terrain beneath them.
- **Tractor:** 3.20 m overall length, three tires, exposed front-right axle and a grounded wooden support block. Cart has two wheels, a single draw shaft and a standable plank bed at Z=.72.
- **Laundry poles:** bare T-poles only. No ropes, laundry or clothes were added, following the art direction's no-laundry-lines rule.

## Material slots and later texture replacement

Every module has exactly these eight ordered slots, including unused ones: **plaster, brick, concrete, metal_painted, metal_dark, wood, glass, roof**. This preserves the G12 remapping contract. All eight reference one locally packed 256 x 256 palette image, `Pilot_Palette_v07_v01.png`. UV0 collapses each face to a palette-cell centre. RGB is the swatch; alpha is smoothness and never transparency. `palette_v01.json` records every source category, exact target HSV, sRGB value, smoothness and UV centre.

The original G12 palette is read-only and contains the older bright swatches, so this kit uses a **new local v07 atlas** with the same role-slot and UV-selector approach. Do not remap to the old bright atlas by image name. `hay` and sack cloth use the sand target; coat and crops use olive grass; rust uses clay-roof target; glass and blue painted panels use slate/corrugated target. No unapproved new accent hue was invented. Hay, soil and plant placeholders use `wood`; coat cloth uses `metal_painted`, matching G12's replaceable-colour fallback for cloth. Role replacement may therefore need per-module exceptions for these surfaces.

Default smoothness .05; glass .35; metal/blue paint .30. Metallic .10 on metal roles, 0 on other roles. Glass is opaque. Use sRGB, Point filtering, Clamp, no mipmaps and no compression for the palette. Tiled textures need world-space/triplanar mapping or new UVs; collapsed palette UVs do not provide a texture scale. There is no new shader, material import or Unity asset in this task.

## Collision data contract

`validation_v01.json` -> `assets[ID].colliders` is the collision authority. Every module has a nonempty list. All values are **Blender mesh-local XYZ metres**; they do not include the master grid, the preview layout, or an engine import transform.

Each proxy supplies `shape: box`, `center_m`, full `size_m` (not half extents), and `rotation_quaternion_xyzw` describing box-local to module-local rotation. `classification` is `solid` or `walkable`. Both are solid collision bodies; `walkable` labels intended traversal surfaces, never triggers. `supports_standing` also marks solid fence/rail tops. A `top_surface` record gives its local centre, normal and full XY extent. Use the same axis/unit transform as the render mesh importer for centres and orientation matrices; never convert rotation by simply reordering quaternion components. Unity's final basis conversion is not engine-tested here.

Oriented box proxies are created from the exact visible box transforms. Regular octagonal tires/logs use the exact union of four inscribed boxes joining opposite polygon edges; this matches the faceted visible solid, including its flat contacts, without oversized bounding boxes. Thus 572 proxies represent 37 modules; the woodpile alone has many log proxies. Some proxies overlap by design as parts of a union. Small applied decorative face accents (cloth patches, relief, narrow bands, crops, vent/cut-end colour accents) have no separate physics; they do not replace usable walking surfaces. Closed component shells and interior component caps are intentional, as in G12.

The build checks exact visible-box corners, polygon-prism containment and edge coverage, unobstructed gate clearances, defined platform coverage, door recess, tread rises and walkable classification. The independent saved-master audit additionally measures 1,152 standable samples against actual triangles. These are geometry checks, not character-controller or vehicle playtests.

## Export settings

Same static FBX settings as G12/BEACH/HAND_PROPS: selected one root mesh, `object_types={'MESH'}`, `axis_forward='-Z'`, `axis_up='Y'`, `apply_unit_scale=True`, `global_scale=1`, `use_mesh_modifiers=False`, `mesh_smooth_type='FACE'`, `add_leaf_bones=False`, `bake_anim=False`, `path_mode='STRIP'`, `use_custom_props=False`. File type is binary FBX 7400. No collision objects are mixed into the render FBXs; collision is supplied as JSON.

Expected Unity import settings follow G12: Scale Factor 1, Bake Axis Conversion enabled, imported normals, tangents none, no animation, no generated collider; remap the eight roles. Engine integration and the collider consumer remain outside this task.

## What was checked

| Check | Status | Evidence |
| --- | --- | --- |
| 37 requested modules/variants, budgets, bounds, pivots, applied transforms | PASS | `validation_v01.json`; total 7,208 tris |
| Deterministic rebuild, closed outward shells, no degenerate triangles, custom normals | PASS | Per-module checks in `validation_v01.json` |
| Eight ordered material roles and palette-cell UV0 | PASS | Validation plus FBX re-import checks |
| All 37 FBXs re-imported in fresh Blender states | PASS | `export_audit_v01_01.json`; largest bound difference 0.000000715 m, below 1 mm |
| Saved master contains exactly 37 module meshes, packed palette, metric units | PASS | `export_audit_v01_01.json` master checks |
| Proxy fit, gate openings, platforms, exact tile end planes, stair rises, 12 cm door recess | PASS | `validation_v01.json` |
| Independent standable surfaces against saved master geometry | PASS | `collision_surface_audit_v01_01.json`; 1152 samples, max error 0.000000321 m |
| Preview renders and visual inspection | PASS | `Previews/v01/`, `visual_review_v01.md` |
| Unity import, material remap, physics, carrying/van access and performance | NOT RUN | Explicitly prohibited by task; requires integration/playtest |
| Owner approval of v07 palette / artistic acceptance | NOT RUN | v07 remains a project candidate |

## Previews

- `Previews/v01/01_all_modules_lineup.png` — labelled 1280 x 1280 contact sheet of all 37 modules. Individual tiles are fitted for inspection, not a shared scale.
- `Previews/v01/02_A_three_quarter.png` — Hamlet props, 1280 x 1000.
- `Previews/v01/03_B_three_quarter.png` — rural house detail, 1280 x 1000.
- `Previews/v01/04_C_three_quarter.png` — plots and yards, 1280 x 1000.
- `Previews/v01/05_D_three_quarter.png` — Rough District service/courtyard pieces, 1280 x 1000.
- `Previews/v01/Tiles/` — one 320 x 260 inspection tile per module, used to assemble the lineup.
- `SK3-PILOT-001_Previews_v01.blend` — editable preview scenes, separate from the export master. `preview_cameras_v01.json` records the group cameras.

Final previews use Cycles, 32 samples for groups and 16 for tiles, a quiet warm sun and neutral studio ground, Standard view transform and no texture noise. Each group uses one common metre scale and a 1.75 m non-living reference box. Assets are ordered with smaller forms in front to reduce occlusion. `Review/check01` and `Review/check02` preserve pre-export composition reviews; final deliverables are under `Previews/v01`.

## Build and safe revisions

From `C:/Dev/Game`:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01/build_pilot_kit.py -- --check-only --no-render
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01/build_pilot_kit.py -- --revision 2 --no-render
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01/build_pilot_kit.py -- --audit-existing --revision 1 --no-render
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01/build_pilot_kit.py -- --preview-existing --revision 1 --samples 32
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01/audit_collision_surfaces.py
python ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01/assemble_lineup.py
```

Use a NEW revision for geometry changes. Existing blend/FBX/validation/palette files are rejected, not overwritten; no force or deletion option exists. `--check-only` validates entirely in memory. `--audit-existing` creates the next unused numbered audit. `--preview-existing` reads the saved master and fills missing previews only. The collision-surface auditor and lineup/report assemblers target v01 explicitly. Re-running an existing lineup/report is rejected. Bytecode writing is disabled in Blender scripts. Geometry utilities are imported read-only from the existing G12 / STYLE_KIT_v2 library. No external assets or downloaded code are used; geometry and local swatches are original/procedurally authored from project references.

Executed build/audit logs: `check_03.log`, `build_v01.log`, `audit_v01.log`, `collision_audit_v01.log`, `previews_v01.log`. Earlier failed preflight logs are preserved for traceability; they predate the final successful build and did not export deliverables.

## Open issues

1. **Unity integration / playtest not run.** Verify imported basis/unit conversion, material remapping, controller step height, every usable top, collision seams, carrying clearance and van access in the pilot scenes. Numeric geometry checks do not certify gameplay acceptance.
2. **Collision cost unmeasured.** Exact faceted log/tire unions produce 572 proxies across the complete kit; profile repeated woodpiles and retain the recorded contact surfaces if later optimizing.
3. **Host cuts required.** Recessed door, garage openings and basement excavation must be respected by the map builder. No wall/terrain edits or automatic Unity importer are included.
4. **Static variants.** Gates are supplied open, garage leaves closed/ajar; no opening animation, hinge rig or runtime interaction was requested. Planting is decorative and traversable.
5. **Art acceptance remains with the owners.** Muted v07 is still a candidate, used here as requested. Simple rural geometry intentionally has restrained carving/wear; no fine grain or grime was added.

**Unfinished modules: none.**
