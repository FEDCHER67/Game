# G26 — Operations props, Stage 1 preview

**Status: awaiting Fedya's visual OK. Stop here.**

- Requested review sheet: `C:/Dev/Game/Working/Reviews/Operations/props_stage1_v01.png`.
- Current editable scene: `Operations_stage1_v02.blend`. Revision v02 removes overlapping buckle-corner surfaces from the first assembled revision; v01 and work-in-progress files are retained.
- Matching clean renders: `Previews/v02/01_patient_closed.png` through `06_fixed_camera.png`.
- Checks from reopening the current scene: `validation_v02.json`.

## Contents and use

All coordinates are metres; Blender +Z is up, the head of the table points -Y. Left/right are the patient's own sides, so patient left is -X in this assembly.

| Named root | New evaluated triangles, including fixed mounts / alternate cover |
|---|---:|
| STRAP_L_ARM | 328 |
| STRAP_R_ARM | 328 |
| STRAP_L_LEG | 328 |
| STRAP_R_LEG | 328 |
| STRAP_TORSO | 332 |
| TRAY_INSTRUMENT | 628 |
| INCISION_KIDNEY_L | 220 |
| INCISION_KIDNEY_R | 220 |
| INCISION_LIVER | 220 |
| **Total** | **2,932** |

This total excludes the existing table, NPC, instruments, displayed kidney, review stand, lighting and hidden Boolean cutters. Each incision's 220 triangles include its separate closed cover; the open rim/recess itself is 158 triangles. These are evaluated triangle counts, including modifiers.

### Restraints

Each exact STRAP_* root is an independent hinge at its mount. In Blender, set its custom `open` property to **0 = closed**, **1 = open**; intermediate values rotate smoothly around local Y. The root also records `hinge_axis`, `closed_angle_deg` and `open_angle_deg` (signed 115 degrees).

The moving band, hollow buckle frame, latch tongue and pale release tab are children of that root. Fixed pins, saddles and mounts are separate meshes with `fixed_mount_for` metadata. Keep the fixed pieces attached to the table when integrating; do not parent them under the moving hinge. Left and right signs are already authored.

The original two straps are omitted from this assembled reference so exactly five restraints are shown. The original table file remains untouched. All other 17 table meshes, their vertex positions/topology, world transforms and existing wheel hierarchy are preserved. Added parts sit at mounts and padded limb saddles. The torso strap is above the three abdomen openings.

### Tray

`TRAY_INSTRUMENT` has its origin at the underside centre. The approximately 0.48 x 0.38 x 0.055 m tray has a continuous shallow shell, matte blue floor, pale steel rim, grip ends and four divided spaces. `TRAY_SLOT_SYRINGE`, `TRAY_SLOT_SCALPEL`, `TRAY_SLOT_KNIFE` and `TRAY_SLOT_ORGAN` are placement markers.

The displayed syringe, scalpel, tier-0 knife and kidney are existing project assets at original scale, in the reference collection. The simple pedestal under the tray is a **review support only**, in the studio collection; it is not a new delivered cart.

### Prepared incisions

Each exact INCISION_* root contains an authored skin-colored rim, inner wall and solid recessed floor, plus a separate `*_CLOSED_COVER`. Hidden `*_CUTTER` meshes drive live Boolean cuts in the staged abdomen surface. To show a closed state, hide that root's `*_OPENING` and reveal its cover; the cover occupies the prepared aperture. No arbitrary cutting or graphic anatomy is modeled.

The user brief specifically requested three independent opening pieces. They are sibling access pieces for the shared abdomen zone described by spec §8; this preview does not redefine the gameplay sequence or change the spec.

The Sausage Buddy fit fixture comes from `NPC_BASE_01_v09.blend`. It is a **static posed reference**, with a lifted shirt hem and separated prepared abdomen island, kept only in this staging scene. Source character meshes, rig, animation files and Unity assets were not edited. Runtime attachment, skinning and patient-pose variation remain part of later integration after approval.

## Visual match and provenance

Geometry authored locally in Blender; no paid generation, external asset downloads or AI texture generation. The assembly reuses the table's charcoal straps, blue-gray pad and graphite frame materials and the NPC's warm skin/oat palette. The matte steel follows the existing scalpel steel color. A subdued brown shadow material is used only inside abstract access recesses.

Read-only references: TABLE-ASTRA-001, SYRINGE-ASTRA-001, SCALPEL-ASTRA-001, BONESAW-ASTRA-001, KnifeTier0Astra, NPC_BASE_01_v09, and the recolored KIDNEY-ASTRA-001. Source paths/materials/mesh counts are recorded in `source_inspection_v01.json`. The knife image texture is packed into the assembled scene.

## Verification

Run from PowerShell:

```powershell
$env:OPS_VALIDATE='v02'
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python 'C:\Dev\Game\ArtSource\Props\OPERATIONS_STAGE1_v01\Scripts\validate_stage1.py'
```

**PASS:** scene reopens; exact roots; metric scale; unit scales on new mesh parts; closed manifold evaluated prop meshes; no loose vertices or zero-area faces; triangle budgets; each independent hinge reaches its authored open angle without moving another hinge or its pivot; tray underside origin; four tray markers; three prepared openings and alternate covers; packed textures; table geometry and world-transform comparison against the original file.

**PASS, sampled scope:** band vertex clearance against the staged patient at open = 0, 0.25, 0.5, 0.75 and 1. This is a geometric check for the authored fit pose, not continuous collision certification or a runtime physics test.

**PASS:** six actual Cycles renders inspected for fit, visible states, instrument separation, belly-opening readability and whole-table framing. The fixed camera is approximate: a final G25 camera transform was not available in the inspected project.

**NOT RUN / outside this approval stage:** Unity import, FBX export, runtime interactions, rigged deformation, multiplayer and physical playtesting. No Unity calls, commits, staging, pushes, WORK_SYNC edits or review bridge were performed.

**Open:** Fedya's visual approval. Do not import or integrate until that approval is given.
