# Sausage Buddy — get-ups and idle variants

**Current deliverables: the four `*_v02.blend` and `*_v02.fbx` files in this folder.** v01 files are retained as the initial review revision; use v02. No input model, existing animation, Unity asset, WORK_SYNC.md or Git index was changed by this task.

Original local animation, authored in Blender 5.2.1 LTS using character-frame joint rotations and analytical two-bone IK. No downloaded/mocap take, paid generator or external motion was used. Each editable Blend contains the unchanged original A v04 Body, Face and Outfit with one skeletal action. Each FBX is animation-only, with one take, zero meshes, no extra root or leaf bones. Facial shape-key tracks are deliberately absent, matching Walk_v02.

Rig: `Buddy_Rig_Mixamo65`; root bone: `mixamorig:Hips`; 65 bones. Character faces Blender -Y, +X is left, +Z is up; 1 unit = 1 metre. Bone order, names, hierarchy and imported bind matrices match Walk_v02. A/B v04 have identical rest rigs. Original A/B Blend/FBX and Walk_v02 hashes remain unchanged.

| Clip | Frames | Seconds | Loop | Standing penetration (mm) | Support sole error (mm) | Largest half-frame local rotation (deg) |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| GetUp_FromBack_v02 | 1–79 | 2.6 | No | 0.330 | 0.330 | 20.95 |
| GetUp_FromBelly_v02 | 1–76 | 2.5 | No | 0.215 | 0.215 | 18.38 |
| Idle_Variant_A_v02 | 1–121 | 4.0 | Yes | 0.001 | 0.001 | 2.87 |
| Idle_Variant_B_v02 | 1–121 | 4.0 | Yes | 0.001 | 0.039 | 5.29 |

All clips run at 30 fps. The get-ups end at the existing Idle frame-1 pose (maximum matrix component difference 8.9406967e-07, floating-point conversion). Both idles start at that same pose; their last frames duplicate their first with **exact matrix equality**. They also ease their motion to zero at the seam. Imported FBX loop seam error is at most 0.

Get-ups have zero net horizontal hips displacement, and the maximum horizontal range across both is 0.000119 mm (floating-point noise). Vertical recovery is authored in the Hips curves. Idle A transfers weight through 41.57 mm horizontally; B through 26.00 mm. Neither travels forward, and both return to their starting hips position.

## Visual review

- **GetUp_FromBack_v02:** Neutral supine start; sit up, dazed head wobble, palm brace, tuck into a crouch, push to standing and settle. [Contact sheet](Previews/GetUp_FromBack_v02/GetUp_FromBack/GetUp_FromBack_v02_contact_sheet.png); side and three-quarter PNGs are in the adjacent folders.
- **GetUp_FromBelly_v02:** Neutral prone start; place palms, push chest up, gather knees, half-kneel, stand with a dazed sway and settle. [Contact sheet](Previews/GetUp_FromBelly_v02/GetUp_FromBelly/GetUp_FromBelly_v02_contact_sheet.png); side and three-quarter PNGs are in the adjacent folders.
- **Idle_Variant_A_v02:** Bored weight transfer, small breath and two sideways looks. [Contact sheet](Previews/Idle_Variant_A_v02/Idle_Variant_A/Idle_Variant_A_v02_contact_sheet.png); side and three-quarter PNGs are in the adjacent folders.
- **Idle_Variant_B_v02:** Three impatient right-foot taps, then a right-temple scratch and relaxed return. [Contact sheet](Previews/Idle_Variant_B_v02/Idle_Variant_B/Idle_Variant_B_v02_contact_sheet.png); side and three-quarter PNGs are in the adjacent folders.

Each contact sheet contains ten labeled times from the side and the same ten from three-quarter. The author inspected both views of every current clip. Early review sheets/logs are retained as provenance. Corrections include whole-body lying orientation, horizontal bracing palms, a continuous IK hinge-plane roll, an eased lying/standing arm transition, and a joint-authored scratch arc that avoids an IK singularity. No reviewed model revision was overwritten.

## Unity import and recovery alignment

Use Unity 6000.5.11f1, **Generic**, **Copy From Other Avatar** with the original A v04 avatar, **Preserve Hierarchy**, no animation compression. Preserve the `Buddy_Rig_Mixamo65/mixamorig:Hips/...` curve path. Match Walk_v02's unit/axis settings. FBX takes are named `Buddy_Rig_Mixamo65|<clip>` (Blender's reimport may prepend the rig name again).

Get-ups: Loop Time off; retain authored Hips height and orientation curves. Idles: Loop Time on over the full take, including the duplicate end frame. The rig object stays fixed at the original floor origin; no extra root-motion node is added. Decide Animator root-motion extraction during integration so it does not apply the recovery height twice.

The first frames are held briefly for blending from ragdoll. Back starts face up with the head toward local +Y; belly starts face down with the head toward local -Y. Align the actor's yaw and floor placement to that lying direction before the ragdoll-to-animation blend. The final pose faces local -Y. First hips heights: back 0.3070 m; belly 0.2401 m. These poses are animation targets, not a guarantee of contact on arbitrary terrain.

This source-only task did not import or modify Assets. Unity import, ragdoll blending, network behaviour and player acceptance remain integration checks; Blender previews are not proof of those outcomes.

## Validation and provenance

`validation_v02.json` samples every clip at 120 Hz, measures actual skinned shoe vertices, checks exact source rig/mesh/topology/weights, Idle alignment, finite transforms, positive bone determinants and continuous quaternion key signs, and reimports each FBX. Standing samples cover 1.7 s through the end of each recovery and the full idles; B's lifted tapping foot is excluded from support-ground-error measurements but included in penetration measurements. Feet and floor-stage body clearance are also reported over the entire get-ups. The rapid cartoon sit-to-crouch motion is retained; all half-frame angular steps are below the documented 25-degree discontinuity gate.

FBX imported animated world-matrix component error is at most 1.8358231e-05; bind-matrix difference from Walk_v02 is zero. Nonfinite components, mirrored bone samples and adjacent quaternion sign flips: zero. Measurement thresholds and scope are explicit in `validate_getups.py`; the original v01 partial validation predates the strengthened angular gate and is superseded.

Across the full get-ups, including lying/transition contact, the largest all-mesh floor penetration is 4.544 mm. This occurs outside the standing interval; standing shoe results are listed separately above.

`source_inspection_v01.json` records the exact Idle reference, source hashes, 14,176 original review-mesh triangles and identity mesh scales. Exported geometry budget is zero triangles; geometry/material/UV optimization does not apply to these animation-only FBXs, and the original skinned meshes were preserved. `provenance_v02.json` records input, script, deliverable and preview hashes.

## Reproduction

From this folder, run Blender 5.2 headless with `--factory-startup --python build_getups.py -- --check-only --revision 3`, then `-- --final --preview --revision 3` for a new, unused revision. The script refuses to overwrite numbered Blends, FBXs, authoring reports or PNGs. Use `validate_getups.py -- --revision 3` for source/reimport checks. Create contact sheets with `contact_sheets.ps1 -ReviewRoot <absolute Previews/clip_v03 folder>`. Original v04 sources are read-only inputs. Documentation finalization is specific to this delivery's v02 validation.
