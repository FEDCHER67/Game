# OPERATIONS STAGE 1 — v02 patient fit

Status: preview ready for Fedya's approval. Blender source only; no Unity import, export, commit or review bridge.

## Review deliverables

- `Operations_PATIENT_v02_review.blend` — authoritative review assembly.
- `../../../Working/Reviews/Operations/props_stage1_v02.png` — nine-panel review sheet (repository-root path: Working/Reviews/Operations/props_stage1_v02.png).
- `Previews/v02_review/` — full-resolution Blender renders and numerical profile data.
- `source_inspection_v02.json` — approved input hashes, geometry, materials, marker matrices and fit contract.
- `validation_v02.json` — all checks and per-case numerical clearance evidence.
- `Scripts/build_patient_fit_v02.py`, `geometry_v02.py`, `validate_patient_fit_v02.py` — reproducible build and validator. Set OPS_PASS to a fresh revision for a new build; existing Blend outputs are protected from overwrite. OPS_VALIDATE selects the revision to validate.

Earlier drafts in this v02 folder are development evidence. Use only the named review assembly above. All v01 files remain untouched.

## Approved fixture and pose

The sole patient input is `ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v01/SAUSAGE_BUDDY_PATIENT_v01.blend`. Body, Face, Shorts, the 65-bone rig and the three incision markers are appended from that file. Its SHA-256 is recorded and verified. The original character file is unchanged.

The review uses evaluated static copies posed with the source rig. Arms are slightly spread for independent restraint clearance: global Y rotations +65° left / -65° right, global X 6°; upper legs X 5°; neck X 15°. The patient-to-table transform is X=-X, Y=0.85-Z, Z=0.795-Y at normal scale. Table head is -Y. Patient left is -X in the lying assembly. Model units are metres.

Small fixed arm supports attach the extended arm saddles to the table frame. Existing table meshes, transforms and materials are identical to TABLE-ASTRA-001; only the two reference straps are omitted in favour of the five replacements. The prepared normal trunk is separated from the head/hand islands in this review copy before the three local Boolean cuts. The continuous source trunk and original source file are not altered.

## Strap controls

The five exact roots are STRAP_L_ARM, STRAP_R_ARM, STRAP_L_LEG, STRAP_R_LEG and STRAP_TORSO.

| Property | Range | Meaning |
|---|---|---|
| open | 0–1 | 0 closed, 1 open; independent 115° rotation around local Y at the fixed hinge |
| girth | -1–1 | -1 thin=1; 0 normal; +1 belly=1 |
| muscle | 0–1.7 | Same muscle amount as buddy_wear.reshape() |
| body_scale | 1–1.05 | Actual character scale, with authored combined-shape corrections |

Each band has Normal, THIN, FAT, MUSCLE, SCALE105 and combined scale-correction shape keys. Drivers bind them to that band's root. Set matching properties on all five roots for a patient; individual adjustment remains possible. Saddle shape keys follow the same girth controls but never follow the hinge's opening rotation. `_MOUNT_*` and `_PIN_*` are fixed parts, separate from the moving band and buckle.

Validation covers normal, thin=1, belly=1 and muscle=1.7, each at scale 1 and 1.05, plus three intermediate shapes at scale 1.025. These match the current one-body-type-axis convention. Arbitrary simultaneous thin/belly/muscle combinations are not certified. Intermediate shape tests exercise the actual driver interpolation, not substitute meshes.

## Prepared incision states

INCISION_KIDNEY_L, INCISION_KIDNEY_R and INCISION_LIVER copy the full posed transform of INC_KIDNEY_L, INC_KIDNEY_R and INC_LIVER respectively. Their origins and local +Z surface normals match the approved source markers. Rim and cover vertices are projected onto the belly along those normals.

Each root has an `open` property: values below 0.5 show the separate skin cover and subtle closed guide; values at or above 0.5 show the authored rim, recess wall and floor. `review_visible` hides the incision assembly when displaying alternative fit fixtures. Cutters belong to 99_PREPARED_CUTTERS and remain hidden. The normal review body contains live Boolean cuts; future export must evaluate the prepared body along with the selected opening state, rather than placing a recess over an uncut body. This review does not export a patient or modify its rig/animation asset.

The recesses are shallow, muted, cartoon cavities without blood or anatomical tissue detail. Closed guides are review curves, excluded from prop triangle budgets. The incision proof is on the approved normal patient; alternative fixtures demonstrate strap girth.

## Tray and camera

TRAY_INSTRUMENT and all tray meshes retain the accepted geometry, palette, bottom pivot and SYRINGE / SCALPEL / KNIFE / ORGAN slots. The assembly is shifted 0.22 m outward along -X solely to clear the arm strap's opening sweep. Instruments and the organ reference move with it.

CAMERA_G25_FIXED maps the G25 tuning camera into the table's local Blender coordinates: position (1.8, 0, 3.6), target (0, 0, 1), perspective field of view 48°. This is a Blender framing check, not a Unity screenshot. CAMERA_PATIENT, CAMERA_INCISIONS and CAMERA_GIRTH provide the other review views.

## Validation and triangle counts

All 20 checks pass. Dense underside contact sampling covers 34,320 points across 11 body/scale cases. The hinge sweep also samples vertices and face centres in five opening states. The clearance tolerance allows at most 1 mm surface penetration; detailed minima/maxima are in validation_v02.json. This is sampled geometry validation, not an exhaustive collision proof.

| Group | Evaluated triangles | Budget |
|---|---:|---:|
| Each arm restraint, including mounts/support | 440 | 450 |
| Each leg restraint, including mounts/saddle | 440 | 450 |
| Torso restraint, including mounts | 444 | 500 |
| Instrument tray | 628 | 700 |
| Each incision opening plus closed cover | 220 | 300 |
| Total new prop geometry | 3,492 | Within all group limits |

Patient, table, instrument references, hidden cutters and review-only curves are not counted as new prop geometry. All new prop meshes are closed manifold solids with applied unit scale. Exact marker transforms, independent opening states, fixed mounts, preserved table/tray geometry, packed textures and source-file hashes are checked separately.

STOP: await Fedya's OK before any Unity integration.
