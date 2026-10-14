"""Write the G16 report once, from measured validation/audit results."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
v=json.loads((HERE/'validation_v01.json').read_text(encoding='utf8'))
a=json.loads((HERE/'export_audit_v01_01.json').read_text(encoding='utf8'))
c=json.loads((HERE/'collision_surface_audit_v01_01.json').read_text(encoding='utf8'))
rows=[]
for name,r in v['assets'].items():
    rows.append('| '+name+' | '+' x '.join(f'{s:.3f}'.rstrip('0').rstrip('.') for s in r['size_m'])+f' | {r["triangles"]} / {r["budget"]} | '+r['pivot']+' | '+r['snapping']+' |')
text=f'''# G16 — PILOT_KIT_v01 — STYLE_KIT_v3

37 original static modules for the Hamlet and Rough District map pilots. Chunky low-poly silhouettes, modelled facade depth, broad wood/metal forms and muted colours from the exact category target HSV values in `ArtSource/Textures/StyleKit_v3/candidate_v07/grade_v07.json`. No texture noise, photographic surfaces, vertex jitter, people, rigs or animation.

The editable export master is **SK3-PILOT-001_v01.blend**. One mesh and one `_v01.fbx` per ID below. **7,208 triangles total**, all within the declared budgets. `validation_v01.json` contains 37 passing module records and **572 compound box collision proxies**. `export_audit_v01_01.json` re-imports every FBX and compares it with the saved master. `collision_surface_audit_v01_01.json` independently checks 1,152 standable-surface samples against that master.

Built with Blender {v['blender']} in background mode on 13 October 2026. Only this new folder was written. No Unity execution/import, commits, shared-library changes, replaced deliverables or file deletions.

## Module table

Size is the measured Blender **XYZ bounding-box extent**, in metres (width x depth/projection x height), including small projecting parts. Z is up; facade outward is -Y. Window sizes include trim and sill. Door nominal 1.0 x 2.1 m describes the leaf; the complete frame is larger. Budget counts include all caps and triangulated polygons. Group A = missing Hamlet props; B = rural house detail; C = plots/yards; D = Rough District.

| ID | Size XYZ (m) | Tris / budget | Pivot | Snapping rules |
| --- | --- | ---: | --- | --- |
'''+ '\n'.join(rows)+f'''

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

Same static FBX settings as G12/BEACH/HAND_PROPS: selected one root mesh, `object_types={{'MESH'}}`, `axis_forward='-Z'`, `axis_up='Y'`, `apply_unit_scale=True`, `global_scale=1`, `use_mesh_modifiers=False`, `mesh_smooth_type='FACE'`, `add_leaf_bones=False`, `bake_anim=False`, `path_mode='STRIP'`, `use_custom_props=False`. File type is binary FBX 7400. No collision objects are mixed into the render FBXs; collision is supplied as JSON.

Expected Unity import settings follow G12: Scale Factor 1, Bake Axis Conversion enabled, imported normals, tangents none, no animation, no generated collider; remap the eight roles. Engine integration and the collider consumer remain outside this task.

## What was checked

| Check | Status | Evidence |
| --- | --- | --- |
| 37 requested modules/variants, budgets, bounds, pivots, applied transforms | PASS | `validation_v01.json`; total 7,208 tris |
| Deterministic rebuild, closed outward shells, no degenerate triangles, custom normals | PASS | Per-module checks in `validation_v01.json` |
| Eight ordered material roles and palette-cell UV0 | PASS | Validation plus FBX re-import checks |
| All 37 FBXs re-imported in fresh Blender states | PASS | `export_audit_v01_01.json`; largest bound difference {a['max_bbox_error_m']:.9f} m, below 1 mm |
| Saved master contains exactly 37 module meshes, packed palette, metric units | PASS | `export_audit_v01_01.json` master checks |
| Proxy fit, gate openings, platforms, exact tile end planes, stair rises, 12 cm door recess | PASS | `validation_v01.json` |
| Independent standable surfaces against saved master geometry | PASS | `collision_surface_audit_v01_01.json`; {c['total_samples']} samples, max error {c['max_surface_error_m']:.9f} m |
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
'''
path=HERE/'README.md'
with path.open('x',encoding='utf8',newline='\n') as f: f.write(text)
print(path)
