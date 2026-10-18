# Patient escape animations — contract v01 (Escape_v01)

Clips: `ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Escape_v01/` (FBX + .blend + `_authoring.json` per clip, build scripts, `escape_clips_manifest_v01.json`, `esc_pose_keys_v01.json`, `Esc_BuckleTargets_v01.json/.fbx`). Contact sheet: `escape_anims_v01_contact_sheet.png` in this folder.

## Basics

- Rig `Buddy_Rig_Mixamo65`, root `mixamorig:Hips`, 65 bones, skeleton unchanged. Bind pose = Patient_v05 = Patient_TableRest_v01 (difference 0).
- 30 fps. Keys every half frame (60 Hz), linear. Each FBX holds one armature, one take `Buddy_Rig_Mixamo65|<clip>`, and no meshes.
- Unity import: same as Operation_v01. Generic, Copy From Other Avatar = `SAUSAGE_BUDDY_A_v04Avatar`, Anim. Compression Off. Loop Time is on only for the 3 `*_Loop_v01` clips.
- Authoring space = the patient's `PatientRest` (table child at Unity `(0, 0.66, 0)`, Euler `(0, 180, 0)`). Head points +Y, face +Z, the patient's LEFT = +X, pad top at z ≈ 0.
- Unity PatientRest-local position = `(-x, z, -y)` of the authoring space.
- **Root motion: none.** Apply Root Motion stays off, as for the Operation clips; the Hips curves place the body. One exception is `Esc_HopRun_R` (see below).
- **Straps:** there are 4 limb straps, `STRAP_ARM_L/R` and `STRAP_LEG_L/R`. The torso strap is removed (Fedya 2026-10-18), so no torso clips exist and the sit-up needs only free arms.
- **Exit side:** the patient leaves on his RIGHT, the table-camera side. The instrument stand stays on his left.

## Pose keys (exact seams)

Every clip starts and ends on one of these poses with identical raw values (seam error 0). Chained clips therefore need no crossfade; 0–0.05 s is enough.

| Key | Pose |
|---|---|
| `LIE` | TABLE_REST. The same pose as `Op_Lie_Awake/Panic/Struggle` start/end, so you can go straight from those clips into the escape clips. |
| `SIT` | Sitting up on the table. Legs straight in their rest place, so any leg strap may still be closed. Palms planted beside the hips. |
| `EDGE_R` | Sitting on the patient's right pad edge, legs hanging. All straps are open. |
| `RUN0` | `Escape_Police_v01/Flee_Run_v01` frame 1 on the floor at the RUN0 root (see HopRun). |
| `REACH_R` / `REACH_L` | Grab pose of `Esc_Lie_UnbuckleArmR_ByL` / `...ArmL_ByR` at 1.25 s. Start of the matching lying slump. |
| `LEGS_REACH` | Grab pose of `Esc_Sit_UnbuckleLegsBoth` at 0.80 s. Start of `Esc_Slump_Sit`. |

Raw values for all keys are in `esc_pose_keys_v01.json`.

## Clips

Strap columns: **closed** = must be closed, **open** = must be open, **any** = either state; the limb then stays in its strap line, so the clip works whether that strap is open or closed.

| Clip | s / frames | Loop | Start → End | Closed | Open | Any | Strap opens (event `StrapOpen`) | Next |
|---|---|---|---|---|---|---|---|---|
| `Esc_Lie_UnbuckleArmR_ByL_v01` | 2.60 / 1–79 | – | LIE → LIE | ARM_R | ARM_L | LEG_L, LEG_R | ARM_R at 1.40 s (0.538) | SitUp |
| `Esc_Lie_UnbuckleArmL_ByR_v01` | 2.60 / 1–79 | – | LIE → LIE | ARM_L | ARM_R | LEG_L, LEG_R | ARM_L at 1.40 s (0.538) | SitUp |
| `Esc_Lie_TugArmR_Loop_v01` | 2.00 / 1–61 | yes | LIE ↔ LIE | ARM_R | ARM_L | legs | – | loop, or UnbuckleArmR_ByL |
| `Esc_Lie_TugArmL_Loop_v01` | 2.00 / 1–61 | yes | LIE ↔ LIE | ARM_L | ARM_R | legs | – | loop, or UnbuckleArmL_ByR |
| `Esc_SitUp_v01` | 1.00 / 1–31 | – | LIE → SIT | – | ARM_L, ARM_R | legs | – | Unbuckle leg(s), or SwingOff |
| `Esc_Sit_UnbuckleLegL_v01` | 2.30 / 1–70 | – | SIT → SIT | LEG_L | arms | LEG_R | LEG_L at 1.35 s (0.587) | other leg, or SwingOff |
| `Esc_Sit_UnbuckleLegR_v01` | 2.30 / 1–70 | – | SIT → SIT | LEG_R | arms | LEG_L | LEG_R at 1.35 s (0.587) | other leg, or SwingOff |
| `Esc_Sit_UnbuckleLegsBoth_v01` | 2.60 / 1–79 | – | SIT → SIT | LEG_L, LEG_R | arms | – | LEG_R at 1.08 s (0.415), LEG_L at 1.42 s (0.546) | SwingOff |
| `Esc_Sit_TugLegs_Loop_v01` | 1.60 / 1–49 | yes | SIT ↔ SIT | ≥1 leg (use only then) | arms | – | – | loop, or a leg unbuckle |
| `Esc_SwingOff_R_v01` | 1.20 / 1–37 | – | SIT → EDGE_R | – | all 4 | – | – | HopRun |
| `Esc_HopRun_R_v01` | 1.50 / 1–46 | – | EDGE_R → RUN0 | – | all 4 | – | – | Flee_Run_v01 (loop) |
| `Esc_Slump_LieReachR_v01` | 1.30 / 1–40 | – | REACH_R → LIE | ARM_R | ARM_L | legs | – | Op_Lie_Asleep / Awake / Panic |
| `Esc_Slump_LieReachL_v01` | 1.30 / 1–40 | – | REACH_L → LIE | ARM_L | ARM_R | legs | – | same |
| `Esc_Slump_Sit_v01` | 1.40 / 1–43 | – | LEGS_REACH → LIE | – | arms | legs | – | same |

Clip side naming: `ArmR_ByL` means the free LEFT hand opens the RIGHT wrist strap.

### Events

Full lists with times and normalized times are in each `_authoring.json` and in the manifest.

- `StrapOpen` (the only gameplay-relevant event): at this time set the strap state to Open and start the strap flip.
- `Grab`, `Slip`, `Release`, `Land`, `Limp`, `BackHitsPad`, `RunStart`, `HandOffToRun` are cosmetic or audio cues.

**Strap flip curve.** This is the rotation about the strap's local +X; the sign is the same in Unity; 0 = closed, 120 = open. Interpolate monotonically.

| Strap | Angle keys |
|---|---|
| Arm | `(t_open, 0°) → (t_open+0.12, 30°) → (t_open+0.30, 120°)` |
| Leg | `(t_open, 0°) → (t_open+0.12, 40°) → (t_open+0.30, 120°)` |

During the first 0.12 s the hand holds the buckle and follows it; then it lets go and the strap flips by itself.

### Buckle targets

`Esc_BuckleTargets_v01.json/.fbx` hold the empties `BUCKLE_ARM_L/R` and `BUCKLE_LEG_L/R`. Each is the top-face centre of the buckle block on the closed table v02 strap, with Z = outward normal, under `TABLE_ROOT_REF` = table root. The JSON also gives the hinge pivot and the buckle path at 0–120°.

Unity table-local positions:

| Buckle | Position |
|---|---|
| ARM_L | (0.233, 0.761, 0.045) |
| ARM_R | (-0.236, 0.764, 0.045) |
| LEG_L | (0.212, 0.682, -0.620) |
| LEG_R | (-0.214, 0.683, -0.620) |

The palm is placed 4 mm (arm) or 12 mm (leg) above that point, along the normal.

## Gameplay chaining (state on waking → sequence)

1. **Both arm straps closed:** no escape. Use `Op_Panic` / `Op_Struggle`; the 8 s rule of OPERATIONS_SPEC §10.4 applies.
2. **One arm strap closed (X):** optionally 1–n × `Esc_Lie_TugArmX_Loop`, then `Esc_Lie_UnbuckleArmX_By<other>`.
3. **Both arms free:** `Esc_SitUp`.
4. **Leg straps:**
   - both closed → `Esc_Sit_UnbuckleLegsBoth`;
   - one closed → `Esc_Sit_UnbuckleLegL` or `...LegR`;
   - optionally `Esc_Sit_TugLegs_Loop` before either.
5. `Esc_SwingOff_R` → `Esc_HopRun_R` → hand-off to the free NPC running `Flee_Run_v01`.

Escape time without optional tug loops:

| Straps closed on waking | Time |
|---|---|
| none | 3.7 s |
| one arm (Fedya's example) | 6.3 s |
| one leg | 6.0 s |
| both legs | 6.3 s |
| one arm + one leg | 8.6 s |
| one arm + both legs | 8.9 s |

Each tug loop adds 2.0 s (arm) or 1.6 s (legs).

## Interrupt (re-injection or hit)

| Interrupt during | Crossfade (0.15–0.25 s) into |
|---|---|
| a wrist reach (`UnbuckleArmR_ByL` or `TugArmR_Loop`) | `Esc_Slump_LieReachR` |
| the mirrored left-arm clips | `Esc_Slump_LieReachL` |
| `Esc_SitUp` or any sitting clip | `Esc_Slump_Sit` |

All slumps end exactly on `LIE`. Continue with `Op_Lie_Asleep` (re-injected) or `Op_Lie_Awake` / `Op_Panic` (hit) using a 0.25 s crossfade.

**Not covered in v01:** an interrupt during `SwingOff` / `HopRun` (on the edge or off the table). Options:
- let gameplay ragdoll the patient;
- order an `Esc_Slump_Edge` clip in v02.

## HopRun root hand-off

- The Hips leave the table in PatientRest space.
- The clip ends exactly on Flee_Run_v01 frame 1, moving at Flee_Run's authored 3.2 m/s along its facing.
- At the end, put the free NPC root at **RUN0**:
  - PatientRest-local Unity position (1.6685, -0.66, 1.1373), yaw +50° about Unity +Y;
  - equivalently table-local (-1.669, 0, -1.137), yaw 230°;
  - this is on the camera side, toward the foot end.
- Then play `Flee_Run_v01` with the root moving 3.2 m/s × playback speed.
- Landing event at 0.52 s.

## Validation

Method: the keyed actions were sampled at 120 Hz and skinned (Body/Face/Shorts v05) against table v02 (pad, straps); each FBX was re-imported.

- Seams: 0 at every start and end.
- Key step ≤ 20.95° per half frame.
- FBX re-import: bind error 1.6e-5, bone position error ≤ 3e-6 m.
- Pad: worst −1.12 mm (fingers, UnbuckleArmL_ByR at 1.62 s); every other clip ≥ −0.8 mm.
- Floor: HopRun lowest point 0.3 mm above the floor.
- Self-penetration of forearm/hand vs trunk/head: 0.
- Closed-strap segments stay on their strap line. They slide along it by ≤ 29 mm (Operation_v01 allowed ≤ 40 mm).
- IK overreach ≤ 14 mm in the reaches. HopRun feet reach 67 mm, which is the hop take-off where the feet leave their marks.

**Not checked:**
- Nothing was imported into Unity, and the Unity strap tween is not wired.
- The hand meets the buckle as a palm-on-buckle placement; there is no per-finger grip.

## Rebuild

From the repository root (Blender 5.2):

```
blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Escape_v01/build_esc_v01.py -- --keys
blender -b --factory-startup --python .../build_esc_v01.py -- --clip <Name> --final --validate --stills <dir>
```

- Clip names: UnbuckleArmR_ByL, UnbuckleArmL_ByR, TugArmR, TugArmL, SitUp, UnbuckleLegL, UnbuckleLegR, UnbuckleLegsBoth, TugLegs, SwingOff, HopRun, SlumpLieReachR, SlumpLieReachL, SlumpSit.
- Then run `python make_sheet_esc.py <dir> <png>` and `python make_manifest_esc.py`.
- The scripts never overwrite existing files.
