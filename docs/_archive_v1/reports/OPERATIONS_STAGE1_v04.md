# Operations stage 1 — v04 (ragdoll carry, one belly incision, kidneys from below, liver loop, top camera)

Date: 2026-10-18. Agent: CL-G32FIN (Claude worker), finishing GPT chat G32's unfinished v04 on top of the approved checkpoint `0957711d`. Project `C:\Dev\Game`, Unity 6000.5.11f1, URP, FishNet. No commits, no staging, no push. `play_copy` was not touched. Player-facing guide (Russian): `OPERATIONS_STAGE1_v02_HOWTO_RU.md` (updated for v04).

## 1. Summary

Fedya's three requests now work with real input, for the host and over the network:

1. **Ragdoll carry and magnet snap.**
   - The patient is the existing 11-body NPC ragdoll (`NpcRagdoll` + `Buddy_RagdollProfile`, unchanged) while he is carried, thrown or lying where he was dropped.
   - When he is let go over the pad, the root is re-seated under the body. The existing NPC wake blend then morphs the limbs into the table clip while the approved 0.6 s alignment slides him onto `PatientRest`.
   - The server simulates the ragdoll. Clients receive the bone poses relative to the root.
2. **One big belly incision.**
   - **Kidneys:** two cords hang below each kidney. They are snipped with the scalpel and the kidney is then pulled up with the hands.
   - **Liver:** cut round with a guided loop. The loop is forgiving, can be cut either way round and can be paused and resumed. The liver is then pulled with the hands.
   - All quality rules (sloppy −1, direct cut −2, yank −1) and the death rolls are unchanged.
3. **Table camera:** straight top-down and close. The top of the head is near the top edge (viewport 0.97) and the opening ends just above the tool bar (0.14). The tray stays on the right. Wheel down gives a wide view with all five straps. Wheel up returns to the close view and stops there.

| Check | Result |
|---|---|
| EditMode, whole project | **208/208 pass** (operations: 33 `OperationRulesTests` unchanged, 16 `OperationAbdomenRulesTests`) |
| PlayMode `OnlyVolunteers.Operation.PlayTests`, real input | **7/7 pass** (170.9 s). PASS lines: loop 70, edges 52, rotated 29, hud720 3, v04-loop 79, v04-guide-edges 40, v04-throw 7; 0 FAIL |
| Windows Development player `Working/Reviews/Operations/stage1_v4/build/OperationsStage1v04.exe` | Succeeded, 0 errors, 14 warnings, 197 MB |
| Two processes over localhost (`run-localhost-v04.ps1`, folder `net04`) | host 37 PASS, client 22 PASS, 0 FAIL; exit codes 0/0; no exceptions in either log. The client observed the host's ragdoll carry (50 pose updates, zero locally simulated bodies), handed the body back to the Animator at the snap, and snipped, looped and pulled organs itself |

## 2. Review of G32's work

**Kept** (sound, and inside the constraints):
- the ragdoll adapter design (`OperationPatientRagdoll`);
- the grabber change from bone to parent `NetworkPhysicsBody`;
- the shared-zone state and rules partial (`OperationAbdomenRules`);
- the `OperationAbdomen` presentation component;
- the table routing for guide 3;
- the kidney cords from below;
- the v04 tuning flag (the v01/v02 assets keep their per-organ guides);
- the upgrade editor script;
- the three new PlayMode entries;
- the probe's routing of the old scenarios through the shared flow.

**Fixed.** Root causes of G32's 7 failing checks, and other defects found in review:

| Problem | Cause | Fix |
|---|---|---|
| Liver loop never completed with real mouse movement; liver not released, not pulled, not in hand, "each organ once" failed | Three causes: (a) the loop lay in the tilted liver-marker plane 2 cm above the marker, so its lower half was under the opening floor and invisible; (b) only one direction could make progress; (c) the band was ±5 cm round a 5 cm loop, so a cut straight through the liver counted | New loop rules (§3.2): the loop plane is raised; either direction works; the band is ±3.1 cm and stops short of the centre; leaps between samples are ignored; resume uses the start dot |
| "strap 0 found under the cursor" | The probe aimed at the strap's bounds centre, which in the top view lies under the scalpel on the tray. G32's wheel-out also lifted the camera to ~4.8 m | New wide view (up 1.2 m and 0.5 m toward the feet). `Straps()` wheels out like a player when a strap is off screen, and aims along the strap's visible top face |
| "leaving and re-entering preserves the one cut" | Most likely the progress was read 0.15 s after the release, before the last pointer packets had settled | Read after 0.3 s, plus a new check right after leaving. The server keeps the cut (0.48 → 0.48) |
| Clients never showed the ragdoll (only found by the two-process run, which G32 never ran) | `NpcRagdoll.PartCount` is 0 until its rig is resolved, so every pose RPC was rejected | `ragdoll.Ready` is called before the size check |
| Poses sent at 20 Hz forever, in world space | — | Root-relative poses, sent only when a bone moved (> 2 mm or 0.6°), with a 1 s heartbeat and the last pose kept for late joiners |
| The resting ragdoll jittered | The collider-less 6 kg handle hung on its joint and dragged the body into the floor | The handle is weightless and has no gravity while not held |
| The snap popped the ragdoll to the clip pose and spun the body 90° during the slide | — | The root is re-seated under the lying hips, turned like `PatientRest`, before the slide starts. The existing NPC wake blend (0.35 s, 0.5 s for the head) runs, and the component is disabled again afterwards |
| The dangling ragdoll shoved the free gurney ~0.3 m during the carry. This also drifted the shared PlayMode session, so "rotated" and v04-loop failed in the suite | — | The gurney is braked (kinematic) while someone carries the patient within table reach. New check: the gurney moves 0.000 m |
| The liver model was seen edge-on from the top camera, as a thin sliver | — | It is turned face-up (and scaled ×1.3) inside its own site. Presentation only; the hit volume and rules are unchanged |
| The cut trail was invisible | A `TransformZ` LineRenderer faces −Z | The trail is turned over and widened |
| Belly skin showed through the cavity. Skin "flaps" stuck out over the arms like oars. The opening ran under the closed torso strap and behind the tool bar | — | The opening sits 1.4 cm above the marker midpoint, is centred higher and is smaller (0.28 × 0.30 m). Instead of the flaps it has a pink wound lip and a pulled-back skin band inside the belly outline |
| G32 changed `ProjectSettings` (Enter Play Mode Options with domain reload off; `runInBackground` on) | Out of scope and project-wide | Reverted to HEAD |
| Liver HUD texts said "cut the cords" | — | Loop-specific texts: «Печень · обвести N%», «Сначала обведи печень скальпелем [4]», «Обводи по кругу… N%» |

## 3. Behaviour details

### 3.1 Opening and kidneys
- Belly line: 0.26 m along the midline, from under the chin down, with a pulsing start dot, three direction chevrons and a red trail.
- The start rules are those of v02: start at the dot, resume up to 0.3 ahead, no start from the far end.
- Tolerance is ±5 cm; within ±2 cm the cut is neat. A mostly sloppy cut costs each organ −1 once.
- The kidney cords run from under the kidney's lower half to 2.6 cm below it, just above the opening floor.
- Snipping uses the unchanged 0.3 s hold and cord hit rules. Snipping never counts as a direct cut.

### 3.2 Liver loop (`OperationAbdomenRules.cs`)
- The loop is an ellipse of 6.0 × 5.2 cm around the liver marker, 3 cm above it. It has 36 dashes, six chevrons, a pulsing start dot at the top and a red trail.
- **Direction:** for the first 8 % of the loop, progress is the distance from the seam either way, so a wiggle at the dot is harmless. After that the direction is fixed and stored in `OrganState.connectionDirection`.
- **Progress:** the cursor's angle round the loop is unwrapped to the nearest turn, so crossing the seam closes the loop. It is limited by the existing blade speed cap.
- **Band:** ±3.1 cm (60 % of the radius, so the centre is never "on the loop"). Within ±2 cm the cut is neat.
- A leap of more than a quarter of the loop between two samples is ignored.
- **Starting and resuming:** the press must be on the band, at most 0.1 behind and 0.2 ahead of the current progress, i.e. at the start dot.
- **Connections:** each third of the loop releases one of the liver's three connections («Чик!»). The full loop releases the liver.
- **Quality:** a mostly sloppy loop costs the liver alone −1. A scalpel click on the liver itself is still a direct cut (−2). Timed snips on the liver are refused.
- The hit volumes of the loop are taller than the liver's own, so a press near the line starts a stroke instead of stabbing the liver.

### 3.3 Camera

Tuning in `OperationStage1_v02.asset`:

| Field | Value | Meaning |
|---|---|---|
| `cameraPosition` | (0.14, 2.03, 0.425) | table-local, looking straight down; screen up is toward the head |
| `cameraLookAt` | (0.14, 0.89, 0.425) | |
| `minZoom` | −1 | wheel-out limit |
| `wideCameraOffset` | (0, 1.2, −0.5) | offset at full wheel-out |

What the close framing shows at 1920×1080:
- head top at viewport 0.97;
- opening end at 0.14, guide end at 0.16 (above the tool bar);
- all three tray organ slots, the bags and the tools;
- arm straps, and the open torso band to the right of the tool bar.

The leg straps need the wheel-out (about 6 notches); this is documented in the HOWTO. Wheel-in stops at the close framing, and further notches zoom toward the cursor as before.

### 3.4 Network
- The server owns the physics: the bodies are dynamic only on the server. The PlayMode tests check 11 dynamic bodies on the host, and the two-process run checks zero on the client.
- Clients get root-relative bone poses through `ObserversRpc(BufferLast)`. They apply them to kinematic copies with light smoothing, and mirror the held / not-held collision rule against players.
- On the snap, the client runs the same wake blend from its last received pose.

## 4. Existing files changed (reason)

| File | Changed by | Reason |
|---|---|---|
| `Network/Scripts/NetworkGrabber.cs` | G32, kept | A ray hitting a ragdoll bone resolves to the patient's `NetworkPhysicsBody` (client ray and server validation). Only the operation scenes use `NetworkPhysicsBody` |
| `Network/Scripts/NetworkPhysicsBody.cs` | G32, kept | Read-only `GrabPoint`, so the ragdoll joint is placed at the hand |
| `Operation/Stage1/Core/OperationState.cs` | G32 + me | `partial` rules. Zone and liver-loop state fields (I added `connectionDirection`). Shared-mode guards in `SnipCord`, `Pull` and `Extract`. Kidney cord geometry from below (I lowered it under the kidney and kept it above the new floor) |
| `Operation/Stage1/Core/OperationTuning.cs` | G32 + me | v04 fields: `sharedAbdomen`, `abdomenCutLength`, `abdomenHalfSize`, `liverLoopRadius`, `minZoom` (G32); `abdomenOffset`, `wideCameraOffset` (me) |
| `Operation/Stage1/Data/OperationStage1_v02.asset` | G32 + me | v04 values, written by the v04 upgrade menu: shared abdomen on, opening and loop sizes, kidney half-size 0.02 × 0.035, `organLift` 0.028, camera, zoom |
| `Operation/Stage1/Prefabs/Stage1_Patient_v02.prefab` | G32, kept | `NpcRagdoll` + `OperationPatientRagdoll` on the root, `NpcRig` (Buddy profile) on the model's Animator object. The FBX and skeleton are untouched |
| `Operation/Stage1/PlayTests/OperationRealInputPlayTests.cs` | G32, kept | Three v04 test entries |
| `Operation/Stage1/Scripts/NetworkOperationTable.cs` | G32 + me | G32: `OperationAbdomen` added; top-down `CameraPose`; zone-guide routing in `SitePoint`, `SiteLocal`, `OrganNormal`, `GuidePosition`, `GuideCoordinates` and `GuideProgress`; save migration; ragdoll hook in `ApplyPatientPhysics`; alignment falls back to the ragdoll's centre of mass; `SharedStroke`. Me: the alignment reads the root after the ragdoll hand-back; gurney brake while the patient is carried near it; `SharedStroke` cleanup and refusal log |
| `Operation/Stage1/Scripts/OperationHud.cs` | G32 + me | Guide progress through the table; liver-loop texts |
| `Operation/Stage1/Scripts/OperationNetworkProbe.cs` (dev driver) | G32 + me | G32: v04 scenario dispatch, evidence folder `stage1_v4` (never overwrites), test save beside the evidence, shared-flow routing of `Cut` and `Snip`. Me: `Straps()` wheels out for off-screen straps and aims along the strap; rotated starts from the scene's gurney spot; diagnostics in two log lines; per-organ pull shot names |
| `Operation/Stage1/Scripts/OperationPresentation.cs` | G32, kept | Hides the v02 per-organ guides, covers, trails and openings, and the liver cords, in shared mode |
| `Operation/Stage1/Scripts/OperationTableView.cs` | G32 + me | G32: focus on enter, wheel-out branch, stroke plane through the guide start. Me: the wide camera offset when wheeled out; per-guide tolerance for the off-line dots |
| `docs/reports/OPERATIONS_STAGE1_v02_HOWTO_RU.md` | G32 + me | v04 controls and steps (Russian) |
| `ProjectSettings/EditorSettings.asset`, `ProjectSettings/ProjectSettings.asset` | G32 | **Reverted to HEAD** (the batch editor's trailing-space rewrite was also restored) |

**New files** (`Assets/OnlyVolunteers/Operation/Stage1/`):
- `Core/OperationAbdomenRules.cs`: shared-guide rules and v04 guide geometry; the loop rules are mine.
- `Scripts/OperationAbdomen.cs`: the opening and guides presentation; I rewrote the visuals.
- `Scripts/OperationPatientRagdoll.cs`: the ragdoll adapter and network sync; reworked as in §2.
- `Scripts/OperationNetworkProbeV04.cs`: the v04 scenarios.
- `Editor/OperationStage1UpgradeV04.cs`: menu *OnlyVolunteers → Operation → Apply shared abdomen and carry v04*, plus `BuildPlayer()`.
- `Tests/OperationAbdomenRulesTests.cs`: 16 tests. G32's 12 were adapted to the new loop semantics with the same intent, and I added 4: the other direction, a wiggle at the start, cutting across the liver, and loop then pull exactly once.

**Not touched:**
- map scenes, van, police, crowd, KCC;
- the patient FBX and skeleton, the animation clips, `SAUSAGE_BUDDY_*`;
- `Characters/Npc/**` (reused as is);
- `play_copy`.

**Note on the old scenarios.** With the shared abdomen on, loop, edges and rotated run the v04 flow (G32's routing):
- the first `Cut()` makes the one belly cut, and later `Cut()` calls are no-ops;
- `Snip(2)` runs the liver loop.

Their per-organ checks "incision N opened" and "cord 2/x snipped / never a direct cut" are therefore replaced by "guide 3 completed", "one belly cut exposes all three organs", "guide 2 completed" and "the loop released the liver's three connections". All other checks are unchanged. The liver's no-damage checks still guard against stabbing (rotated: "liver out with no damage"; v04-loop: "neat new flow preserves organ 2 quality").

## 5. Evidence (`Working/Reviews/Operations/stage1_v4/`)

| File | Content |
|---|---|
| `01_ragdoll_carry.png` | patient dangling from the host's grab (side view) |
| `02a_snap_morph.png`, `02b_snapped.png` | 0.2 s into the magnet hand-back; aligned on `PatientRest` |
| `03_top_camera.png` | close top framing with HUD: head at the top, belly guide, tray, straps |
| `04a_wheel_out_straps.png`, `04b_straps_closed.png` | wide view with all five straps; straps closed by clicks |
| `05_anesthesia.png` | asleep, the belly guide with its start dot and chevrons |
| `06_big_cut.png` | mid-stroke with the red trail |
| `07_opening.png` | one opening: liver loop, both kidneys with cords below |
| `08_kidney_cords_below.png`, `08b_kidney_cords_closeup.png` | the right kidney's two cords below it (the left kidney is already on the tray) |
| `09_kidney_pull.png`, `11_liver_pull.png` | the hands pulling with the tension bar |
| `10a_liver_loop_start.png`, `10b_liver_loop_cut.png` | loop start; 47 % round with the trail, «Чик!» |
| `12_tray.png` | all three organs on the tray, empty opening |
| `13_net_client_sees_ragdoll.png` | the client process sees the host carrying the ragdoll |
| `contact_sheet_v04.png` | the steps above, labelled |
| `operations_stage1_v04_loop.mp4` | 31 s, real time, the full v04 loop from the carry to the tray (960×540) |
| `run_*/` | the seven PlayMode scenario logs, shots and `final-state.json` (`run_v04-loop/frames` is the MP4 source) |
| `net04/` | two-process logs, host and client shots |
| `editmode-tests.txt`, `playmode-tests.txt`, `player-build.txt` | test and build results |
| `g32_before_fix/` | G32's original failing runs, XML results and batch logs, moved here unchanged |

**Critical review of the evidence:**
- The opening, the three organs, the cords and the loop are all clearly readable in the close framing at 1080p and 720p (the same aspect ratio).
- The snap morph frame (`02a`) is a deliberately caught transition: the limbs fold in over about 0.35 s, and nothing pops or spins.
- The probe grabs the patient by the hips, so the head dangles. A player can grab any bone.

## 6. Open issues

1. **Aspect ratio.** The framing was tuned for 16:9. On 4:3 or 16:10 screens the view is narrower and the tray can be partly cut off; the wheel-out still shows it.
2. **Client hand-back.** On a remote client the root's NetworkTransform interpolates to the re-seated position while the wake blend runs. A short swing may be visible on the client. It was verified by state, not watched live.
3. **Gurney brake.** The brake also applies if another player tries to push the gurney while someone carries the patient within 3.2 m of it.
4. **Patient dropped on the floor.** He stays a ragdoll pile until picked up again; there is no get-up or KnockedOut clip. The escape still uses the approved clips.
5. **Pre-existing UI and layout, unchanged:**
   - A server hint (e.g. «Шприц заправлен» after switching tools) can cover the stroke hint for about 2 s.
   - During the belly cut, the organ chips all show the same «разрез N%».
   - The liver world item in tray slot 3 overhangs the tray edge, as in v03.
6. **Breathing.** The belly skin clears the opening floor by about 7 mm; no show-through was seen during the breathing clips.
7. **No human playtest of the new feel.** The loop band, the direction freedom and the camera height should be tried by Fedya. Tuning is in the asset and in `OperationAbdomenGeometry`'s constants.

## 7. Re-running
- Tuning and prefab: menu *OnlyVolunteers → Operation → Apply shared abdomen and carry v04* (it writes only the v02 tuning asset and the patient prefab components).
- Scenarios in the editor: Play the v02 scene, then `OperationTestHooks.Runner.Begin("v04-loop" | "v04-guide-edges" | "v04-throw" | "loop" | "edges" | "rotated" | "hud720")`. Or run the PlayMode assembly `OnlyVolunteers.Operation.PlayTests`.
- Player: `OperationStage1UpgradeV04.BuildPlayer()`, then `powershell -File Working/Reviews/Operations/stage1_v4/run-localhost-v04.ps1 -Run net04`.
