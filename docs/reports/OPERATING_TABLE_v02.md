# Operating table v02 (TABLE-ASTRA-001 + five straps): report

Date: 2026-10-16. Author: CL-PROPS (Claude worker). Nothing was committed or pushed.

## What was made

This version replaces the operating-table work from G26 that Fedya rejected. It reuses the existing gurney TABLE-ASTRA-001: the caster rig, markers, frame, pad, wheels and materials are unchanged. The two v01 reference straps, GEO_Strap_01 and GEO_Strap_02, are retired.

There are exactly **five straps**, in the original style:
- Flat charcoal bands, 7.6 cm wide and 1 cm thick, flat-shaded, using MAT_Straps_Charcoal.
- Each has a raised chamfered buckle block.

| Strap | Where | Hinge side |
|---|---|---|
| STRAP_ARM_L / STRAP_ARM_R | distal forearm, centre table-Y -0.045 | own pad edge |
| STRAP_LEG_L / STRAP_LEG_R | shin above the ankle, centre table-Y 0.62 | own pad edge |
| STRAP_TORSO | across the pelvis and shorts, centre table-Y 0.055, also over both wrists. Its band edge is 2 cm below the kidney openings | patient's left edge, so it opens away from the camera side |

Hinges and anchors:
- Each strap's origin is its hinge on the pad's outer top edge.
- Local +X is the hinge axis, local +Y points inward and local +Z points up.
- A positive rotation of **120°** about local +X opens the strap: it flips up and outward.
- A static object, GEO_Strap_Anchors, holds the parts that do not move:
  - a short side tab down the pad side face, in the original wrap-around look;
  - a hinge barrel under every strap;
  - the torso receiver tab.

How the closed straps were fitted:
- Each band is fitted in polar coordinates around its own hinge.
- At every radius the band sits at the smallest angle that keeps 7.2 mm clearance from the TABLE_REST body.
- Because of this, opening the strap can never sweep through the body.
- The torso band is the convex "taut belt" hull of that fit.

**TABLE_REST pose.** This is a one-frame clip. The patient lies on the pad with these contact gaps:

| Contact | Gap (mm) |
|---|---|
| Back of the head on the pillow wedge | 3.3 |
| Neck cap | 3.4 |
| Upper back | 0.5 |
| Shorts / buttocks | 1.0 |
| Heels | 1.4 |
| Forearms | 1.5 |
| Hands | 2.2 |
| Upper arms | 3.6 |

How the pose was reached:
- The neck uses an S-curve: neck +37°, head -25.5°.
- Hips extension is 3.2°.
- The arms are at 84° down, 20° back, with 26° elbow and -7° wrist deviation.
- The thumbs are laid along the index finger.
- There is no penetration anywhere.

Gaps that remain above 5 mm are not support contacts:
- The calves are 37 mm above the pad, held up by the heels and buttocks.
- The thighs near the buttocks are 41 mm above the pad.
- The mid back is 6 mm above the pad.

**Incisions.** These are cartoon pieces with no gore, authored on the TABLE_REST belly:
- The OPEN piece is a skin-coloured oval rim, a rose inner wall and a dark shallow floor.
- The COVER piece is a thin skin patch with a light dotted guide line.
- Sizes are 9.2 × 5.4 cm for the kidneys and 9.2 × 5.8 cm for the liver.
- Each piece's origin and axes are its INC_* marker.

**Instrument stand.** This is a wheeled Mayo-style stand in the gurney palette:
- A graphite frame and dark rubber casters.
- A matte-steel tray with a blue-grey mat.
- 480 triangles.
- The tray floor is at 0.690 m, just above the pad.
- It has 9 SLOT_* empties.

## Files

ArtSource, all in ArtSource/Props/TABLE-ASTRA-001/v02/; v01 was not touched:
- Patient_TableRest_v01.blend / .fbx. The FBX is armature only, with the single take `Buddy_Rig_Mixamo65|Patient_TableRest`: 1 frame, 65 bones, Buddy export settings.
- TABLE-ASTRA-001_v02.blend / .fbx. The v01 export settings were used. The blend also contains the patient lying on the table as a reference.
- OperationIncisions_v01.blend / .fbx and InstrumentStand_v01.blend / .fbx.
- table_rest_contract_v01.json (the contract), table_rest_metrics_v01.json, table_v02_build_validation.json, OperationIncisions_v01_validation.json and validation_v02.json.
- Scripts/:
  - build_table_rest_v01.py, build_table_v02.py, build_incisions_v01.py, build_instrument_stand_v01.py
  - validate_v02.py, render_review_v02.py
  - plus the existing v02_common.py and pose_lib_v01.py
  - Every builder refuses to overwrite existing outputs.
- Previews/v02_01 … v02_12 *.png: Blender Eevee review renders.

Unity:
- Assets/OnlyVolunteers/Props/TableAstra/Model_v02/TABLE-ASTRA-001_v02.fbx
  - Imported with the same settings as v01: MaterialDescription, embedded, Generic, no avatar.
  - Its materials are **remapped to the v01 FBX materials**.
- Assets/OnlyVolunteers/Operation/Stage1/Art/OperationIncisions_v01.fbx
  - Buddy_Skin is remapped to the patient FBX's Buddy_Skin.
  - MAT_Incision_Wall, MAT_Incision_Cavity and MAT_Incision_Guide are embedded.
- Assets/OnlyVolunteers/Operation/Stage1/Art/InstrumentStand_v01.fbx
  - The frame, pad and wheel materials are remapped to v01.
  - MAT_Astra_MatteSteel is embedded.
- Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Animations/Patient_TableRest_v01.fbx
  - Generic, Copy From Other Avatar using the A_v04 avatar.
  - Compression off, Preserve Hierarchy on.
  - It holds the clip `Patient_TableRest`: 660 curves, length 1/30 s, loop off.
- Assets/OnlyVolunteers/Operation/Stage1/Prefabs/OperatingTableAstra_v02.prefab
  - It is a copy of NetworkTableAstra.prefab with the visual model swapped to v02.
  - TableAstraCasterMotion was re-added with the same settings.
  - These are kept: NetworkObject, NetworkTransform, NetworkPhysicsBody, Rigidbody, BoxCollider and the four WheelContact spheres.
  - New children: PatientRest, CameraAnchor and TrayAnchor. TrayAnchor contains an InstrumentStand_v01 instance.
  - OperatingTableStraps is on the root.
  - The prefab is registered in Assets/DefaultPrefabObjects.asset; FishNet had already added it automatically when the prefab was created.
  - NetworkTableAstra.prefab is unchanged (sha256 e29b88ff…).
- Assets/OnlyVolunteers/Operation/Stage1/Prefabs/InstrumentStand_v01.prefab: no colliders, slots included.
- Assets/OnlyVolunteers/Operation/Stage1/Scripts/OperatingTableStraps.cs
  - `SetOpen(int index, float open01)` gives a smoothed rotation about local +X; `SetOpenImmediate` does it without smoothing.
  - Strap order: L arm, R arm, L leg, R leg, torso. It is not networked.
- Assets/OnlyVolunteers/Scenes/Dev/OperatingTable_v02_Review.unity contains:
  - the table, with the patient sampled in TABLE_REST and the straps closed;
  - the KIDNEY_L opening plus the KIDNEY_R and LIVER covers;
  - the stand.

Screenshots, in Working/Reviews/Operations/table_v02/:
- 01_table_camera … 10_head_pillow, at 1600×1000 from URP in batch mode.
- **table_v02_sheet.png** puts them together.
- unity_build_report.txt is the Unity import and measurement log.

## Contract (summary; full data in table_rest_contract_v01.json)

Coordinate frames:
- **Unity prefab-local = (-x, z, -y)** of Blender table-local.
- The head end (pillow) is Unity +Z.
- The patient's left is Unity +X; the patient's right is Unity -X.

**PatientRest**:
- localPosition (0, 0.66, 0), localEulerAngles (0, 180, 0).
- The patient model goes under it at identity, and the clip carries the lying pose on Hips.
- Measured in Unity: Hips at (0, 0.7712, 0) and Head at (0, 0.813, 0.416).

**Pad surface**:
- The lying surface is at y 0.646–0.664: 0.663 at the centre line, 0.653 at |x| 0.27.
- The pillow wedge rises to 0.789 at the head end.

**Straps.** The hinge is local +X for all straps; the open angle is 120°, positive, with the same sign in Blender and Unity.

| Strap | Pivot (Unity prefab-local) | Hinge axis (prefab) |
|---|---|---|
| STRAP_ARM_L | (0.2984, 0.6596, 0.045) | (0, 0, -1) |
| STRAP_ARM_R | (-0.3017, 0.6599, 0.045) | (0, 0, 1) |
| STRAP_LEG_L | (0.2973, 0.6623, -0.62) | (0, 0, -1) |
| STRAP_LEG_R | (-0.2992, 0.6629, -0.62) | (0, 0, 1) |
| STRAP_TORSO | (0.2982, 0.6598, -0.055) | (0, 0, -1) |

**INC_* markers in TABLE_REST**:

| Marker | Unity prefab-local | Skin normal (Blender) |
|---|---|---|
| KIDNEY_L | (0.075, 0.8768, 0.115) | (-0.30, 0.04, 0.95) |
| KIDNEY_R | (-0.075, 0.8772, 0.115) | (0.34, 0.03, 0.94) |
| LIVER | (-0.06, 0.8766, 0.215) | (0.24, -0.10, 0.97) |

In Unity the marker normal is the object's local +Y.

**CameraAnchor**:
- localPosition (-1.6, 1.7, 0.02), looking at (-0.05, 0.78, 0.10).
- localEulerAngles (30.66, 87.05, 0), FOV 50.
- It frames the whole patient and the tray.

**TrayAnchor**: localPosition (-0.57, 0, -0.29), identity rotation, on the patient's right.

**Slots**, stand-local in Unity:

| Row | Slots | x |
|---|---|---|
| Nearest the table | SYRINGE_ANESTHESIA, SYRINGE_BLOOD, SCALPEL | 0.135 |
| Middle | BLOODBAG_1..3 | 0.0 |
| Farthest from the table | ORGAN_1..3 | -0.135 |

All slots are at y 0.692, with z = +0.165, 0.0 and -0.165 within each row.

## Validation

Blender: validate_v02.py checks the saved files independently. **All 20 checks pass**:
- Rig and table nodes are identical to v01: FBX node names, parents and local matrices, plus the blend's RIG_* custom properties and world matrices.
- The v01 straps are retired.
- There are exactly five straps, and each has the hinge_axis and open_angle_deg properties.
- Closed straps have no triangle overlap with the body, pad, frame, handle, braces or wheels.
- Closed straps sit close to the body without touching it. The minimum gap is between 7.09 and 8.01 mm (limit: above 0 and at most 15).
- The opening sweep from 0 to 120° in 2.5° steps has no overlap with the body, pad, frame/rails, handle, braces or wheels. The lowest point during the sweep is 0.626 m.
- The anchors do not overlap anything.
- All six incision pieces sit exactly on their markers: origin error 0, axis error 0. They are at most 0.8 mm below the skin, and only on their sunk outer ring.
- The clip has one take, one frame, 65 bones and is armature only. Its pose round-trips with an error of 8e-7 m.

Triangle counts:

| Object | Triangles |
|---|---|
| STRAP_ARM_L | 130 |
| STRAP_ARM_R | 136 |
| STRAP_LEG_L | 138 |
| STRAP_LEG_R | 154 |
| STRAP_TORSO | 162 |
| GEO_Strap_Anchors | 212 |
| Each incision OPEN piece | 162 |
| Each incision COVER piece | 140 |
| Stand | 480 |

Unity, measured in batch mode:
- The v02 model's root rotation equals the v01 instance rotation.
- The RIG_* positions match the WheelContact positions.
- Every OperationIncisions piece, instanced at the table root, is **0.00 mm / 0.000°** from its patient INC marker after the clip is sampled.
- Opening every strap by +120° moves it outward past the pad edge, so the sign is confirmed.

I reviewed every screenshot. There are no floating or penetrating parts and no z-fighting. The incision covers sit 1–2 mm proud of the skin; this shows as a slight raised patch, which is intended.

## Open issues and notes

- **Unity marker scale.** The patient FBX's INC_* markers have lossyScale 100. If you parent an incision piece under a marker, set worldPositionStays to true, or give the piece localScale 0.01, otherwise it becomes 100× too large. Placing the incision FBX at the table root (identity) already matches the markers exactly.
- **The NetworkTableAstra BoxCollider was kept.** It is 0.78 × 0.18 × 2.03 m centred at y 0.70, so its top is at 0.79, about 13 cm above the pad top where the patient lies. A dynamic patient collider resting on the table would be pushed out. Keep the patient kinematic while it is in TABLE_REST, or shrink that collider in a later revision.
- **The stand has no colliders** and sits under the table's Rigidbody, so it moves with the gurney. It adds no collision shape and does not shift the implicit centre of mass. The gameplay builder can add the tray colliders and hover zones, as its placeholder already does.
- **Unity was run in batch mode.** No editor was open, and CL-GAME's own batch instance was waited out. CL-GAME's work-in-progress scripts did not compile on my first attempt. TableAstraCasterMotion was not tested at runtime in Play Mode; the hierarchy and markers are byte-identical to v01.
- The CameraAnchor frames the patient from 1.6 m away. The incisions are small at that distance, so a local zoom or magnifier is expected.
- The calves rest 37 mm above the pad, which is natural because the heels and buttocks carry the legs.
- The open arm and leg straps read as curved "hooks" beside the pad. This follows from rigid cuffs on edge hinges.
- The STRAP_TORSO triangle count, 162, is slightly above the ~150 guideline.
- **Animation agent:** the TABLE_REST parameters are in table_rest_metrics_v01.json.
  - The rig root stays fixed; the Hips position and rotation carry the lying pose.
  - Positive arm adduction toward the wrists makes the arms collide with the arm-strap tips, so keep the wrists at |x| ≥ 0.19 (Unity) when the arm straps are closed.
