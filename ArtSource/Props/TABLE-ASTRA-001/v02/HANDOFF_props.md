# HANDOFF — operating table v02 props (CL-PROPS), stopped 2026-10-15 at the lead's request

## Done (all new files, nothing existing modified)

- `ArtSource/Props/TABLE-ASTRA-001/v02/Scripts/v02_common.py` — helpers: append the v01 table (only the
  TABLE_ASTRA_Geometry/Rig collections, no preview floor/lights) and the patient (rig, Body, Face, Shorts, INC_*),
  world BVH, Blender->Unity conversion (`C_B2U`, `unity_pos`, `unity_quat`, `unity_euler`), materials, overwrite guard.
- `ArtSource/Props/TABLE-ASTRA-001/v02/Scripts/pose_lib_v01.py` — FK posing by bone rotations only
  (`basis = Rest^-1 * L * Rest`, L given in rest armature axes), `place_rig`, per-region pad-gap metrics
  (regions by dominant weight; head split into `head_cap` (rest z < 1.30) and `head_back`).
- Exploration driver (scratch, not a deliverable): `%TEMP%/claude/.../scratchpad/pose/explore_multi.py <params.json>`.
- No .blend/.fbx/.json deliverable written yet. Unity was never touched; the Unity lock was never taken.
- Input hashes (unchanged): patient .blend 56202bf7…6d2, patient .fbx 06566f4e…827, table v01 .blend e0c6b72e…bd0,
  table v01 .fbx f33ba70e…dfe (identical to Assets/…/TableAstra/Model/TABLE-ASTRA-001.fbx), NetworkTableAstra.prefab e29b88ff…acc.

## Facts measured (use them)

- Pad (GEO_Padded_Top): the lying surface is FLAT at z 0.646–0.664 (crowned ~1 cm at the centre line). 0.79 is only the
  head-end pillow wedge: rises from y≈-0.62 (z 0.663) to y≈-0.93 (z 0.789), ~24° incline. Pad side faces at x≈±0.295,
  z 0.55–0.655; top edge rounds off from |x|≈0.275. Frame side rails at x≈±0.29..0.3185, top z 0.578 (y=-0.5)
  sloping to 0.540 (y=0.6) — only ~2.3 cm outside the pad side face (matters for open-strap sweeps).
- Original straps: ~1 cm thick flat bands, 7.6 cm wide, flat-shaded, wrap over the top and down both side faces to
  z≈0.543; raised chamfered buckle block (~8 cm × band width × ~2.5 cm) near the -X side. 59/60 tris.
- Unity mapping (verified from NetworkTableAstra.prefab WheelContacts): prefab-local = (-x_b, z_b, -y_b);
  model child `TableAstraVisual` has localRotation (-0.7071, 0, 0, 0.7071). Rotation about a strap's local X keeps the
  same angle sign Blender->Unity; rotations about local Y/Z flip sign.
- Patient rest: Hips 0.82, neck joints 1.18/1.25, shoulders x=±0.2 at 1.165, legs x=±0.1. Trunk back y≈+0.09..+0.106,
  belly front y≈-0.116. Head is a capsule z 1.08–1.747, radius 0.134 (Y) / 0.142 (X), centre axis y=0.

## TABLE_REST pose status (in progress, nothing fixed yet)

- Chosen convention (matches GetUp_FromBack_v03): armature object = PatientRest on the pad directly under the hips,
  rotation Rz(180°) relative to RIG_Table_Root (Unity Euler (0,180,0)); in armature space the body lies head toward +Y,
  face +Z; Hips L = Rx(-90°). Provisional placement: root (0, 0.0, 0.66) table-local; hips head height 0.1112 m above it.
- With that: buttocks/shorts gap 1.0 mm, upper back 0.5 mm, mid back 6 mm (torso rests flat). Provisional INC positions
  (table-local Blender): KIDNEY_L (-0.075, -0.115, 0.886), KIDNEY_R (0.075, -0.115, 0.886), LIVER (0.060, -0.215, 0.885).
- PITFALL 1 — head: the head capsule (0.134) is deeper than the upper back (0.106), so with a flat torso its neck cap
  sinks ~2–3 cm into the flat pad whatever the head rotation (plain neck/head flexion: -9 to -22 mm). Fix found:
  neck S-curve — Neck flexion with Head counter-rotation lifts the head joint. neck 35 / head -10 → head_cap +1.6 mm,
  but head_back floats 56 mm above the pillow (net 25° too much). NEXT: keep neck ≈35–40, lower head to ≈-15..-25 so
  the back of the head rests on the pillow (head_back ≈1–3 mm) with head_cap ≥1 mm. Spine curl [0,3,6] also clears the
  head but lifts the shoulders and pushes the arms into the pad — avoid.
- Still to tune: legs (heels 29 mm, calves 64 mm above pad → leg_back ≈ +2..3°, small knee), arms (forearm 24 mm,
  hand 12 mm above pad → more arm_back + elbow so the forearm lies parallel; arm_down ≈86–88° so the wrist sits
  ~2.5–4 cm from the shorts — the arm strap's inner end needs that gap), relaxed finger curl. Then add checks for
  arm-vs-torso self penetration (arms are part of the continuous trunk mesh).

## Straps — not started; design notes

- PITFALL 2 — torso strap: above the liver opening (top edge ≈ standing z 1.085) only ~3.5–4 cm of chest shows before
  the head's chin cap (cap bottom z≈1.08 at centre, ≈1.12 at x=±0.1). A 7.6 cm band "across the chest above all
  incisions" must cross the chin/throat. Recommended: STRAP_TORSO across the pelvis/waistband just BELOW the kidney
  openings (standing z ≈0.795–0.87; it also crosses the forearms). Get the lead's/Fedya's decision.
- Recommended mechanics: hinge on the pad top outer edge; strap local +X = hinge axis (along the edge), +Y inward,
  +Z up, positive rotation opens (same sign in Unity). A rigid band cannot "hang" (a long one would hit the rail or
  floor); ~110–130° flip-up/outward reads as open. Keep the original look with small STATIC tail pieces wrapping the
  pad side face under each hinge (and a receiver tail on the torso strap's buckle side). Fit bands as a loft of
  per-slice upper convex hulls (pad + limb) offset 6–8 mm; validate with dense sampling.

## Incisions, tray/stand, Unity — not started

- Incision pieces must be authored in the final TABLE_REST pose (markers move with the Spine bone).
- Unity notes: v01 table FBX meta = materialImportMode 2, materialLocation 1 (embedded), no remaps; patient FBX
  preserveHierarchy 1. Clip import pattern (e.g. Cargo_Sit_Idle_v05.fbx.meta): Generic, avatarSetup 2, avatar source
  guid c9bf60023bda34f4ea85893f556f7edf (A_v04), animationCompression 0, takeName `Buddy_Rig_Mixamo65|<action>`.
  FBX clip export settings: ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Cargo_v01/build_cargo_v08.py `export()`
  (armature only, bake_anim_use_all_actions — make sure Patient_TableRest is the ONLY action in the file).

## Exact next steps

1. Finish the pose (head, legs, arms), write `build_table_rest_v01.py`, save Patient_TableRest_v01.blend/.fbx + contract.
2. Decide the torso-strap position (pitfall 2), build TABLE-ASTRA-001_v02 with the five straps + validation.
3. Incisions, instrument stand, review renders/sheet, then Unity (lock, import, prefabs, review scene, screenshots).
