# Operations stage 1 — v03 (animation integration and polish)

Date: 2026-10-16. Agent: CL-FINAL (Claude worker). Project `C:\Dev\Game`, Unity 6000.5.11f1, URP, FishNet.
Builds on v02 (`OPERATIONS_STAGE1_v02.md`) and the animation agent's `ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Operation_v01/`. No commits, no staging, no push. Controls are unchanged, so `OPERATIONS_STAGE1_v02_HOWTO_RU.md` was not touched.

**Scope change during the work (from the lead):** polish item 4c (1.3× incisions) was dropped, because the incisions will be redesigned into one big belly incision by another agent. The enlargement I had already made was fully reverted (tuning, presentation and table code are back to the v02 incision values). The table camera was not changed.

## 1. Summary

- The eight real clips now drive the patient on every peer. `Patient_Operation.controller` maps OpState 0–6 to Awake / Asleep / Struggle / Panic / Dead / EscapeFall / KnockedOut, and the `ShockDeath` trigger plays Op_ShockDeath, then Op_Dead.
- The escape is now the real clip. The server keeps the root on PatientRest for the 3 s clip. It then moves the root under the landed body, in the same frame as a snap to KnockedOut. Nothing pops, slides or snaps back onto the table.
- The procedural limb, head and torso layer is mostly off. Only small touches remain (§4).
- The instrument stand is on the far side of the table, beside the upper chest and shoulders. The legs are no longer hidden from the table camera.
- Open straps now swing 178° and lie flat outward, about 8 cm above the pad. They no longer stand up to 1.2–1.27 m.
- Because the stand and the flat torso strap now sit where the original escape left the table, the escape and knocked-out clips are **mirrored** in Unity. He now leaves over his right side, the table camera's side.

| Check | Result |
|---|---|
| EditMode rules tests | **33/33 PASS** |
| PlayMode real-input tests | **4/4 PASS** (108.9 s). Checks: loop 75, edges 52 (4 new escape checks), rotated 32, hud720 3 PASS lines; 0 FAIL |
| Animation evidence scenario `evidence` (new, real table camera) | 30 PASS, 0 FAIL |
| Windows Development player, rebuilt into `Working/Reviews/Operations/stage1_v2/build/OperationsStage1v02.exe` | Succeeded, 0 errors, 15 warnings (none from Stage1), 202.6 MB |
| Two processes over localhost, with the new build | host 36 PASS, client 25 PASS, 0 FAIL; exit codes 0/0; no exceptions in either log |

Counts use the same method as v02's logs (number of `PASS ` lines). They equal v02 except for the 4 escape checks added to edges.

`play_copy` was not touched.

## 2. Animation docs and import (task 1)

New file: `ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Operation_v01/README.md`, in the style of Cargo_v01. It covers:
- the frames, placement and contracts;
- what each clip shows;
- the per-clip validation numbers from `validation_op_v01.json` (all 8 pass);
- the Unity import, the mirrored escape and the controller contract;
- how to reproduce the clips.

I checked the import settings of all 8 FBX files in Unity:
- Generic, Copy From Other Avatar = `SAUSAGE_BUDDY_A_v04Avatar`;
- compression Off, Preserve Hierarchy on;
- 660 bindings each;
- Loop Time on for Awake, Asleep, Struggle, Panic, Dead and KnockedOut, and off for ShockDeath and EscapeFall.

No change was needed.

## 3. Controller wiring (task 2)

`Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Patient_Operation.controller` was rebuilt in place (same GUID, same parameter names `OpState` and `ShockDeath`).

| State | Clip |
|---|---|
| TableAwake | Op_Lie_Awake |
| TableAsleep | Op_Lie_Asleep |
| Struggle | Op_Struggle |
| Panic | Op_Panic |
| Dead | Op_Dead |
| EscapeFall | **Op_EscapeFall_Mirror_v01** |
| KnockedOut (default) | **Op_KnockedOut_Mirror_v01** |
| ShockDeath (new) | Op_ShockDeath, exit time 1 → Dead with no blend (its end pose equals Dead) |

Transitions:
- Each of the seven OpState states has its own `OpState == n` transitions (42 in total). There are no AnyState OpState transitions any more, because they would cut ShockDeath short once OpState = 4.
- Crossfades are 0.25 s, 0.1 s into EscapeFall, and 0 s from EscapeFall to KnockedOut.
- AnyState → ShockDeath takes 0.1 s, on the trigger.

Other settings:
- Root motion is off: the Animator has Apply Root Motion off, and the authored Hips curves place the body. Sampling confirms the hips stay at 0.111 m above the root on the table.
- The patient prefab's Animator uses this controller, the A_v04 avatar and AlwaysAnimate culling (verified).
- OpState is still set from replicated state on every peer.

**Escape consistency.** `NetworkOperationTable.FallOffTable` no longer teleports the body to the foot end. The new flow:
1. The root stays kinematic on PatientRest for `escapeFallSeconds` (3 s), and a replicated `OperationView.falling` flag is set.
2. Then `Land()` moves the root to PatientRest ⊕ `escapeLandingOffset` (1.5, −0.66, 0.36), using a floor raycast, with the same yaw as PatientRest.
3. It sets the floor physics box first, then makes the body dynamic at zero velocity.
4. On each peer, `OperationPresentation` detects the root jump and calls `OperationPatientRig.SnapState(KnockedOut)` (`Animator.Play` + `Update(0)`), also from `Application.onBeforeRender`. The clip switch and the root jump therefore land in the same frame.

The mirrored contract was measured: the EscapeFall end equals the KnockedOut start, 0.000 mm / 0.000°.

Other parts of the escape change:
- Re-alignment is blocked while falling.
- F9 cancels the fall.
- The patient's NetworkTransform now has teleport enabled (threshold 1 m), so clients jump instead of interpolating the 1.5 m move.
- A death by failed escape holds the landed pose, frozen, so a corpse does not breathe.
- The thud sound now plays at the impact, 2.0 s into the clip.

Evidence and checks for the escape:
- The edges test now checks that the root stays on PatientRest during the clip, then that he lands on the camera side (table-local x = −1.50), with the hips over the root (no pop). It then checks that he has not moved 1 s later (no slide).
- `[OPS] LANDED … overlaps: none` is logged.
- The first build of this pushed the body 17 cm because the old lying box was still active at landing; that is fixed.

**KnockedOut physics box.** The KnockedOut clip lies along the root's X axis, but the prefab box lies along Z. `OperationPatientRig.SetFloorPose` swaps the box while he is off the table: center (0.025, 0.19, 0.07), size (1.68, 0.38, 0.56), sampled from the clip. Without the swap, players would grab thin air beside the visible body. The fresh floor spawn now uses yaw −90°, so he lies alongside the gurney with his head toward the head end.

**Mirroring.** Mirrored copies were made because the far side now holds the stand and the flat-open torso strap. With the straps at 178°, the original clip has 273–382 vertex contacts with the open torso strap from 1.43 s on. The mirrored clip has zero contacts with the straps, stand, frame, handle, wheels and anchors.
- Tool: `Assets/OnlyVolunteers/Operation/Stage1/Editor/OperationClipMirrorV03.cs`, menu *OnlyVolunteers → Operation → Mirror patient escape clips (v03)*. It never overwrites.
- Outputs: `Animations/Op_EscapeFall_Mirror_v01.anim` and `Op_KnockedOut_Mirror_v01.anim`.
- Method: reflect in model space, swap Left and Right, apply a rest correction; the rig is symmetric to 0.001 mm. Bone error against the reflected source is ≤ 2.7 mm. The KnockedOut loop seam is 0.
- The source FBX and blend files were not changed.

## 4. Procedural motion (task 3)

`OperationPresentation.UpdatePatient` now leaves the motion to the clips:

| Layer | v02 | v03 |
|---|---|---|
| Head shake | up to 18° (panic, awake, overdose) | **off** |
| Torso sway (`LimbMotion[4]`) | up to 5° | **off** |
| Limb swing on strapped limbs | 0.1–0.12 | **off** |
| Limb swing on unstrapped limbs | up to 1.0 (22° arms / 12° legs) | 0.25 × escape progress while struggling, 0.3 in panic (≤ 6.6° / 3.6°) |
| Spine twitch (`Twitch`) | 0.25–1.25 (overdose) | 0.1–0.4, overdose distress only |
| Face blend shapes (Blink, Worried, Surprised, Happy) | yes | **kept unchanged** |

One state choice changed. An awake patient who is not strapped and is wriggling toward the edge (escape progress > 25 %) now plays the Struggle clip instead of TableAwake plus procedural flailing. A strapped, awake patient plays Struggle as before.

## 5. Polish

**4a. Instrument stand on the far side.**
- In `OperatingTableAstra_v02.prefab`, TrayAnchor moved from (−0.57, 0, −0.29) to (0.57, 0, 0.38) and is rotated 180° about Y.
- The SLOT_* positions inside the stand instance are mirrored (prefab overrides). The order is unchanged: syringe row nearest the table, then bags, then organs; anesthesia toward the head, then blood syringe, then scalpel. Tools keep the table-aligned orientation.
- Gameplay reads every pose from the slots, so no code change was needed. The tuning `trayPosition` is only used by the placeholder-table fallback and was left alone.

Why z = 0.38, at upper-chest/shoulder level rather than mid-chest: the open torso strap (z −0.09…−0.02) and the left arm strap (z 0.007…0.083) lie on that side. The tray spans ±0.27 m, so z ≥ 0.36 is the lowest position that clears them.

Checks:
- The camera still shows the whole patient, the stand and the tray (`01`–`07`).
- All tool, bag and tray clicks work through the real camera (loop, edges, rotated, hud720 and the two-process run all pass).
- The camera was not changed.

**EscapeFall side.** The escape now leaves over the patient's right side (the camera side) and lands at table x ≈ −1.5 m, clear of the stand and the gurney. The far side is not used.

**4b. Open straps.**
- `OperatingTableStraps.openAngles` changed from 120° to **178°** for all five straps; this is a prefab value.
- 95–100° was tested and rejected: it stands the torso band vertical, with its top at 1.27 m, taller than before.
- At 178° the bands lie flat outward:

| Strap | Highest point at 120° | Highest point at 178° |
|---|---|---|
| Torso | 1.21 m | 0.74 m |
| Arm and leg straps | 0.77–0.90 m | ≤ 0.68 m |

- A Blender BVH sweep in 2.5° steps against the v02 table meshes shows the frame is first touched at 185° (torso), 187.5° (left arm) and 190° (right arm), and the pad at ≥ 197.5°. 178° leaves a margin of 7° or more.
- The opened straps do not touch the patient in the Awake or Panic clips, the mirrored escape, or the stand.
- From the steep table camera, the flat torso band on the far side still shows as a dark stripe beyond the pad, because a horizontal band seen from above projects long. `13_strap_open_angle_options_120_100_150_180.png` compares the options.

**4c. Incisions.** Skipped by the lead's decision. The v02 incisions are unchanged.

## 6. Evidence (`Working/Reviews/Operations/stage1_v3/`)

| File | Content |
|---|---|
| 01_awake_straps_open.png | TableAwake after F9 (dazed), straps open, stand on the far side |
| 02_struggle.png | strapped and awake: Struggle |
| 03_asleep.png | TableAsleep after a 2 s injection |
| 04_panic.png | Panic with the «ПРОСЫПАЕТСЯ!» banner |
| 05_rescued_asleep.png | after the rescue injection (the evidence dose is high, so the face shows overdose distress) |
| 06_shock_death.png | ShockDeath, 0.3 s after the shock |
| 07_dead.png | Dead after ShockDeath |
| 08_escape_fall_sequence.png | the mirrored escape seen from aside at 0.35 / 0.9 / 1.45 / 2.0 / 2.6 / 3.6 s |
| 09_stand_overview.png, 10_stand_far_side.png | the new stand placement |
| 11_straps_open_flat.png | open straps lying flat |
| 12_knocked_out_floor.png | KnockedOut on the floor (fresh patient) |
| 13_strap_open_angle_options_120_100_150_180.png | strap-angle comparison from the table camera |
| contact_sheet_v03.png | 01–12 labelled |
| operations_stage1_v03_awake_inject_asleep_panic_rescue.mp4 | 13.6 s, real time, table camera: awake → straps → inject → asleep → panic → rescue |
| operations_stage1_v03_escape_table_cam.mp4 | 13 s, table camera: daze → escape → landing |
| run_evidence/ | all shots, the 30-check log and the frames (`v09_escape_*_table_cam.png` show the escape through the game camera) |
| run_loop, run_edges, run_rotated, run_hud720 | PlayMode run logs, screenshots and frames |
| net03/ | two-process host/client logs |

Critical review of the evidence:
- No popping at the escape landing (2.59 s and 3.59 s frames are identical; the hips stay over the root).
- No penetration found by the vertex/collider checks.
- No limbs came out of closed straps in Struggle or Panic; the animation agent's validation measured at most 4.7 mm of strap penetration in Panic (tolerance 8 mm).
- Mirrored and source clips both dip up to 1.3–1.9 mm under the floor between keys in Unity (Euler-curve interpolation). This is invisible.

Re-run the evidence: Play `Operation_Net_Stage1_v02.unity`, then call `OperationTestHooks.Runner.Begin("evidence")`, or start the player with `-ops-scenario evidence`. The probe's default evidence folder is now `stage1_v3/run_<scenario>`, so v02 evidence is never overwritten.

## 7. Files changed

- `Characters/SausageBuddy/Patient/Patient_Operation.controller`: rebuilt as in §3.
- New: `Characters/SausageBuddy/Patient/Animations/Op_EscapeFall_Mirror_v01.anim`, `Op_KnockedOut_Mirror_v01.anim`, and `Operation/Stage1/Editor/OperationClipMirrorV03.cs`.
- `Operation/Stage1/Core/OperationTuning.cs` and `Data/OperationStage1_v02.asset`: new fields `escapeFallSeconds` = 3 and `escapeLandingOffset` = (1.5, −0.66, 0.36). No other tuning change.
- `Operation/Stage1/Scripts/NetworkOperationTable.cs`:
  - the falling and landing flow, plus the `OperationView.falling` flag;
  - the floor box at spawn and landing;
  - fresh spawn yaw −90°;
  - no re-alignment while falling;
  - the `[OPS] LANDED` log line.
- `Operation/Stage1/Scripts/OperationPatientRig.cs`: `OpState`, `SnapState`, `SetFrozen`, `SetFloorPose`.
- `Operation/Stage1/Scripts/OperationPresentation.cs`:
  - the clip-driven `UpdatePatient`;
  - the landing snap, also run from `onBeforeRender`;
  - the delayed thud;
  - `FailedEscapeFall` sets the escape time.
- `Operation/Stage1/Scripts/OperationNetworkProbe.cs`:
  - 4 escape checks in edges;
  - the new `evidence` scenario with overview shots;
  - the default evidence folder is now stage1_v3.
- `Operation/Stage1/Prefabs/OperatingTableAstra_v02.prefab`: TrayAnchor position and rotation, mirrored SLOT overrides, strap open angles 178.
- `Operation/Stage1/Prefabs/Stage1_Patient_v02.prefab`: NetworkTransform teleport on (threshold 1 m).
- `ArtSource/.../Operation_v01/README.md` (new).
- Not touched:
  - the map scenes, van, police, crowd and KCC;
  - the patient FBX, the skeleton and the SAUSAGE_BUDDY_* sources;
  - the Operation_v01 sources (FBX, blend, scripts);
  - the camera and the HOWTO;
  - `play_copy`.
- `ProjectSettings/EditorSettings.asset`: the batch editor rewrote two empty fields with trailing spaces again, as in v02. I restored it to HEAD.

Note for whoever re-runs `OperationStage1BuilderV02.Build`:
- It keeps a controller that has 7 or more states, so the wiring survives.
- It resets the tuning asset to the code defaults, which already contain the v03 values.
- If the controller asset is ever deleted, the builder recreates the old AnyState layout with placeholder clips. Rewire it then as in §3.

## 8. Remaining issues and decisions for the lead

1. **The escape now goes toward the table camera.** He sits up, climbs off toward the player and drops out of the table view; only a hand or legs stay visible at the bottom of the frame (`run_evidence/v09_escape_*_table_cam.png`). The toast still says «Сбежал… Тащи обратно».
   - He lands at x −1.5 m, beside where a table-mode player usually stands (the test player at −1.25, +0.45 did not collide).
   - Alternatives: keep this; or re-author a foot-end escape (needs a new clip); or return the stand to the camera side and use the original clips (the controller then needs only two clip swaps and `escapeLandingOffset` (−1.5, −0.66, 0.36)).
2. **The far torso strap still reads as a stripe from the steep table camera.** At 178° it lies flat, but a horizontal band seen from above projects long. If the redesigned camera keeps this angle, consider a shorter or flexible torso band in the props (a geometry change), or hide it while open.
3. **The landing snap was not tested over the network.** The two-process run covers the loop, the joint pull and quitting, not the escape. The landing snap on a remote client relies on NetworkTransform teleport plus the `onBeforeRender` check. Worth one manual two-player escape.
4. The stand sits at upper-chest/shoulder level (z 0.38) rather than mid-chest, because of the flat-open arm and torso straps (§5).
5. The incision redesign agent should know:
   - the v02 incision code paths and tuning values are unchanged;
   - `OperationPatientAnchors` and `SitePoint`/`SiteLocal` are where any site-centre shift belongs;
   - the right-kidney and liver markers are only 10 cm apart along the body, so their v02 pieces nearly touch (0.8 cm gap). That is why 1.3× did not fit without moving them.
6. No human playtest of the new animation feel.
