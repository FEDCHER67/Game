# Operations stage 1 — v02 (playable pass)

Date: 2026-10-16. Agent: CL-GAME (Claude, gameplay). Project `C:\Dev\Game`, Unity 6000.5.11f1, URP, FishNet 4.7.3 / Tugboat, KCC.
Builds on G25's v01 (`docs/reports/OPERATIONS_STAGE1_v01.md`) and the investigation in `Working/Reviews/Operations/stage1_v2/HANDOFF_gameplay.md`.
No commits, no staging, no push. The Russian player guide is `docs/reports/OPERATIONS_STAGE1_v02_HOWTO_RU.md`.

## 1. Summary

Stage 1 now plays end to end with a mouse, using the same server-authoritative FishNet architecture:

carry the knocked-out patient with the normal grab → he slides onto the pad by himself (0.6 s) → **[E] Встать к столу** → click the 5 straps → hold LMB with the blue syringe until he falls asleep (face and speech give feedback) → fill the red syringe from an arm and click an empty bag (sealed bag, $50) → cut along the dotted line from the green dot → snip the cords with a short hold → pull the organ out with empty hands → click the tray → leave with E.

Every step has a hover highlight, a Russian hint at the cursor, a sound and a world toast. Every refusal names its reason («Он дёргается — пристегни или усыпи», «Пациент мёртв», «Начни от зелёной точки…»). Nothing fails silently any more.

The new scene is `Assets/OnlyVolunteers/Scenes/Dev/Operation_Net_Stage1_v02.unity` (a copy of NetworkTest plus the operating room). The v01 scene is left as it was.

Verification, all on the final code:

| Check | Result |
|---|---|
| EditMode rules tests | **33/33 PASS** (21 G25 tests + 12 new) |
| PlayMode real-input tests (Unity Test Runner, virtual mouse/keyboard through the real view, grabber and HUD) | **4/4 PASS**: loop 76 checks, edges 49, rotated table 33, HUD 1280×720 4; 0 FAIL |
| Two standalone processes, host + client over localhost | host 37 PASS, client 26 PASS, 0 FAIL; joint pull with 2 holders; client quits mid-pull; no rollback |
| Windows Development player build | Succeeded, 0 errors, 15 warnings (none from Stage1 v02) |
| NetworkTest scene | host starts, the player has NetworkInventory (6 slots), no console errors or warnings |
| v01 scene `Operation_Net_Stage1.unity` | host starts, fresh world, no console errors or warnings |
| Final console after the last compile | 0 errors, 0 warnings |

A human playtest of feel (mouse sensitivity, camera, timings) is **NOT RUN**. The automated runs prove the rules and the input path, not the fun.

## 2. Root causes of Fedya's failures

Main evidence: Fedya's own save, `%USERPROFILE%\AppData\LocalLow\DefaultCompany\VOLUNTEERS ONLY\OnlyVolunteers\operations_stage1_v01.json`. It held a patient who was dead from an overdose (residual 1.2023 against G25's limit of 1.2), with all straps closed, cuts at 1.0/1.0/0.155 and not one cord released.

1. **The save loaded on every launch with no reset, and a dead patient silently ignored input.** After the first overdose, every later session started with a corpse. Anesthesia and blood were dropped without a word (`else if (State.alive)`, `CollectBlood` returning false). This is the whole "I can't inject / can't take blood" report.
   *Fix:* fresh world by default (`loadSavedOperation` false; `-ops-load` restores), dev **F10** new patient and **F9** place on table, a death banner, and an explicit refusal hint for every action on a corpse. Fedya's dead save was renamed to `operations_stage1_v01.dead_backup_2026-10-15.json` (with its `.bak`).
2. **The overdose came with no feedback.** Nothing changed while LMB was held, so a player held "until it works" and killed him (overdose at 4.8 s of holding).
   *Fix:* a progressive face and speech sequence, a dose ring, a plunger and liquid level, a "Засыпает → Спит" card, a "Уснул" toast, distress above the safe range («хватит?..», then «ХВАТИТ!!» with twitching) and a wider window. See §4.
3. **E pick-up in table mode missed the tools.** `CursorPoint` intersected a plane at y = 1.30 m while the tools lay at about 1.06 m. From the table camera that is about 20 cm of parallax, against a pick radius of 18 cm. This was established from the geometry and not reproduced with input before the code was replaced.
   *Fix:* every target is now a real physics raycast against hover colliders (§5.4).
4. **Cutting rejected normal drags.** Any sample more than 2.4 cm ahead of the progress was dropped. A human drag of 12 cm in 0.2–0.3 s jumped past that window and stopped dead. The start of the guide was not marked, and a cut from the wrong end failed silently.
   *Fix:* projection onto the guide clamped by blade speed (no rejection), a pulsing start dot, a 30 % resume window, a cut trail and the hint «Начни от зелёной точки и веди по пунктиру».
5. **Cords were practically impossible to release.** The targets were 10 px squares, the blade had to stay within 1.75 cm for 0.65 s, and the direct-cut zone was right next to them.
   *Fix:* 3D tubes that reach 2.6 cm past the opening rim, a hit radius of 4.5 cm, a hold of 0.3 s, and a cord on the ray always beats the organ. A direct cut happens only on a deliberate press that **starts** on the organ.
6. **Tools were dynamic rigidbodies that drifted, fell and were saved on the floor.**
   *Fix:* tools are kinematic in named slots. A dropped tool flies back to its slot after 2 s. Tool positions are not saved.
7. **G25's automated runs bypassed the input.** Their probe called the RPCs with exact world points and always started fresh, so none of the above was ever exercised.
   *Fix:* the v02 driver plays only through virtual devices and the real view (§7).

Defects found while building v02:

- The grab spring (220 N/m) sags about 0.55 m under the 12 kg patient, so a carried patient dragged under the table edge. The driver now holds high; for players, auto-align accepts any release over the pad box.
- A dropped item or tool teleported, because writing the transform of an interpolated kinematic body leaves a stale `Rigidbody.position`. It is now synced before switching to dynamic.
- A quick click on the organ was lost between two FixedUpdates. A direct cut is now evaluated when the RPC arrives.
- `Shader.Find` returns null in player builds, so the procedural visuals were invisible there. They now use referenced template materials.
- The KIDNEY model is a **pair** of kidneys, so one item looked like two (`KeepOneKidney` strips one), and v01 left the extracted organ hanging 20 cm above the chest.
- v01's `PatientContact()` used world x/z, which breaks on a rotated table. All validation is now table-local.

## 3. What changed

**Rules (Core assembly, `Operation/Stage1/Core/`)**
- `OperationState.cs`:
  - new cues (Escaped, KnockedOut, IncisionOpened, SloppyCut, DirectCut, Yank, BloodPortion, Overdosing, Dazed, BagSealed);
  - per-organ `sloppyCut/offLine/directCuts/yanks`;
  - patient `knockedOut/dazedRemaining/escapes`;
  - world stock, barrel, blood fill and bag mask.
- `OperationRules`:
  - alignment and daze;
  - escape only when awake, aligned, not dazed and without the torso strap;
  - `CanDrawBlood(arm)`, `FillBlood` (progress kept);
  - `CanBeginCut`, `CutTowards` (projection plus speed cap; sloppy by off-line distance);
  - `DirectCut`, `SnipCord`, pull with `Yank`.
- `OperationGeometry`: guide points, cords and the pad/work volume in table- or marker-local space.
- `OperationText`: Russian tier labels and colours, strap and organ names, causes of death.
- `OperationTuning.cs`: v02 values (§4); the v01 fields are kept for old assets.
- `OperationTargets.cs` (new): the target code scheme (`kind<<16 | index<<8 | sub`), body parts, tool slots, hint ids, and the test hooks (`OperationTestHooks.Runner/ForcedRoll/SaveSlot`).

**Runtime (`Operation/Stage1/Scripts/`)**
- `NetworkOperationTable.cs`: rewritten; see the architecture in §5.
- `OperationTool.cs`: rewritten as kinematic, slot-docked tools with a held/loose/returning state machine, plunger and liquid.
- `OperationTableView.cs`: rewritten as the table mode (camera blend, cursor, hover and raycast priority, intents, zoom, keys, WASD leave).
- `OperationPresentation.cs`: rewritten. It builds the strap, bag, tray and incision targets on the props models and turns cues into faces, speech, sounds, splashes and toasts.
- `OperationHud.cs` (new, uGUI, built in code):
  - patient card, panic and death banners, hotbar, hint pill;
  - progress ring, tension bar, organ card;
  - speech bubble, remote cursors «P2», toasts.
- `OperationPatientRig.cs` (new): bone hover colliders for 9 body parts, the Face blend shapes, the animator contract and a small procedural struggle layer.
- `OperationPhysicalItem.cs`: rewritten. Organs and bags are WorldItems; they are held at the cursor in table mode and carried in first person after leaving.
- Smaller new files: `OpsInput.cs`, `OperationTargetTag.cs`, `OperationVisuals.cs`, `OperationStrapsPlaceholder.cs`, `OperationStage1Spawner.cs`.
- `OperationNetworkProbe.cs`: rewritten as the dev scenario driver. It runs only with `-ops-scenario` or from a test, and only in the editor or a development build.

**Editor and tests**
- `Editor/OperationStage1BuilderV02.cs`: menu *OnlyVolunteers → Operation → Build Network Stage 1 v02*. It regenerates:
  - the tuning asset, the prefabs and the scene;
  - the material templates and the bag item;
  - the animator controller.
- `Tests/OperationRulesTests.cs`: 21 updated + 12 new tests.
- `PlayTests/` (new asmdef plus `OperationRealInputPlayTests.cs`): 4 UnityTests.

**Outside Stage1 (minimal)**
- `Clinic/Scripts/ClinicSave.cs`: the test save slot (`OperationTestHooks.SaveSlot`, or `-ops-test` → `operations_stage1_test_v02.json`).
- `Network/Scripts/NetworkGrabber.cs`: LMB also reads `OpsInput.Mouse` (virtual devices), and the cursor-lock check goes through `OpsInput.CursorLocked`. Behaviour for players is unchanged.
- `Network/Scripts/NetworkPlayer.cs`: `MotorForward` and `SetLocalHudVisible`.
- `Network/Prefabs/NetworkPlayer.prefab`: gained `NetworkInventory` and `InventoryInput`, as the lead decided.
- `Assets/DefaultPrefabObjects.asset`: FishNet re-registered the new prefabs automatically.
- `ProjectSettings/EditorSettings.asset`: the batch editor had flipped `m_AsyncShaderCompilation` to 0; I set it back to 1. What remains in the git diff is Unity's trailing-space re-serialisation of two empty fields.
- Not touched: the KCC motor and its settings, the map scenes, the van, police and crowd, the patient FBX and `SAUSAGE_BUDDY_*` sources, `WORK_SYNC.md`.

**Generated assets:**
- prefabs `Stage1_{Patient,Tool_Anesthesia,Tool_Blood,Tool_Scalpel,Item_Kidney,Item_Liver,Item_BloodBag,Table_Placeholder,InstrumentStand_Placeholder}_v02`;
- `Data/OperationStage1_v02.asset`, `Data/OperationSpawnables_v02.asset`, `Data/Item_BloodBagStage1_v02.asset` (item id 110, $50);
- the v02 materials;
- `Animations/Patient_TableRest_Placeholder_v01.anim`;
- `Characters/SausageBuddy/Patient/Patient_Operation.controller`.

On the props agent's `OperatingTableAstra_v02.prefab` I only added gameplay components, hover colliders and wiring.

## 4. Feel numbers (tuning asset `Data/OperationStage1_v02.asset`)

| Thing | Value |
|---|---|
| Auto-align | 0.6 s slide after release over the pad; then dazed 4 s; an awake, unstrapped patient escapes after 7 s more |
| Anesthesia | 0.5 units/s. Asleep at 0.8 (**1.6 s** hold); distress above 1.25 (**2.5 s**); overdose at 2.25 (**4.5 s**). Sleep up to 90 s. Syringe 3 units (6 s), bottle stock 9 units. Putting the syringe back (RMB or key) refills it from the stock; F10 resets the stock |
| Blood | 4.5 s hold per syringe, progress kept on release; allowed if asleep, the torso or that arm is strapped, or dead. 2nd portion weakens, 3rd kills. Full syringe + click on an empty bag = sealed bag WorldItem, $50, no grade, no spoilage |
| Incision | 7.5 cm guide; neat within 2 cm, counts within 5 cm, off-line travel weighs 0.5. Start within 20 % of the dot or 30 % of the resume point; blade speed cap 0.7 m/s (a 0.3 s drag finishes it). Sloppy −1 |
| Cords | 2/2/3; 0.3 s hold within a 4.5 cm hit radius; never a direct cut |
| Direct cut | only a press that starts on the organ with the scalpel: −2 «Ты порезал орган!» |
| Pull | 20 cm, spring; a flick faster than 0.9 m/s = yank −1 «Рывок!»; two players add up |
| Death rolls after extraction | 10 % / 20 % by kidney order, 30 % liver, +10 points per blood portion (from G25) |
| Tools | back to their slot 2 s after being dropped (0.35 s flight) |
| Camera | FOV 50, blend 0.35 s, wheel zoom up to 62 % towards the cursor |

## 5. Architecture

**5.1 Authority.** One `NetworkOperationTable` (NetworkBehaviour on the table prefab, spawned on server start by `OperationStage1Spawner`) owns the `OperationWorldState` and runs `OperationRules` in `FixedUpdate`. Clients never change state. They send intents (all `ServerRpc(RequireOwnership = false)`):
- `RequestJoin`, `RequestSelect(ToolSlot)`, `RequestReturn`;
- `RequestClick(targetCode, localPoint, NetworkObject)`;
- `RequestPointer(seq, pressId, pressed, pressTarget, target, localPoint, pull)`, streamed at 20 Hz while LMB is held;
- `RequestDev(9 | 10)`.

Points are sent **table-local**. The server re-validates the participant, the reach (3.2 m), the target code, the tool in hand and the patient state, and answers refusals with a `TargetRpc` hint id. Pointer input expires after 0.5 s.

**5.2 Replication.** A `SyncVar<string>` JSON snapshot (`OperationView`) at about 15 Hz carries the patient, organs, straps, tools, bags, holders and pull values. Discrete events go out as `ObserversRpc` cues (`ObserversCue(cue, organ, client)`) and drive sounds, faces, toasts and the animator. Remote cursors use an unreliable `ObserversRpc`. Tools carry their own SyncVars (holder, mode, fill, loose pose). Organs and bags are standard `WorldItem` NetworkObjects (`OperationPhysicalItem`) with a stable id `PatientId/organ/index`.

**5.3 Table-local geometry.** All validation uses the table transform or the incision markers (`INC_KIDNEY_L/R`, `INC_LIVER` under `mixamorig:Spine`), so a moved or rotated gurney works. The rotated-table test covers this. The gurney is frozen (kinematic) while anyone is at it, and the patient rides along when it moves.

**5.4 Hover and targets.** `OperationTableView` raycasts the camera ray against trigger colliders tagged with `OperationTargetTag`:
- straps; tools; empty bags; the tray zone and organ slots;
- incision boxes; cord capsules; organ capsules;
- 9 bone colliders on the patient;
- items.

Priorities resolve the overlaps:
- nearest wins;
- the tray only if nothing else is hit;
- the body hull loses to any other target within 7 cm;
- open straps lose to tray objects behind them;
- a cord on the ray beats the organ.

The scalpel stroke projects the cursor onto the incision plane, so a drag never slips off.

**5.5 Tools.** Tools are kinematic. They are docked on `SLOT_*` anchors, held (drawn at each holder's cursor on every peer; the server keeps the authoritative held pose), or loose (dynamic, after a drop). A loose tool returns to its slot after 2 s. Keys 1–4 and LMB on a tool take it; RMB returns it. A tool held by another player shows that player's colour and «P#» on the hotbar.

**5.6 Save.** `ClinicSave` keeps the v1 format plus the v02 fields. Saving is still periodic (5 s), but loading is opt-in: `-ops-load`, or the serialized `loadSavedOperation` on the table. Automated runs use `operations_stage1_test_v02.json` and never touch the player slot.

**5.7 Testability.** `OpsInput` lets the dev driver feed virtual devices and override cursor lock in batch mode. The HUD has a capture mode (Screen Space Camera into a RenderTexture) for screenshots. The test asmdef cannot reference Assembly-CSharp, so it drives everything through `OperationTestHooks`.

## 6. Contracts

**Props agent (table, straps, incisions, stand)**

The table prefab `Operation/Stage1/Prefabs/OperatingTableAstra_v02.prefab` must keep these named children:
- `PatientRest`, `CameraAnchor`, `TrayAnchor`;
- `STRAP_ARM_L`, `STRAP_ARM_R`, `STRAP_LEG_L`, `STRAP_LEG_R`, `STRAP_TORSO` (+ `STRAP_TORSO_SecondHalf`);
- `SLOT_SYRINGE_ANESTHESIA`, `SLOT_SYRINGE_BLOOD`, `SLOT_SCALPEL`, `SLOT_BLOODBAG_1..3`, `SLOT_ORGAN_1..3`.

Other parts of the contract:
- **Straps** are driven through `SetOpen(int, float)`, found by type name `OperatingTableStraps` (the props script). `OperationStrapsPlaceholder` is the fallback.
- **Incision pieces** come from `Art/OperationIncisions_v01.fbx`, children `INCISION_{KIDNEY_L,KIDNEY_R,LIVER}_{COVER,OPEN}`. They are placed in marker space.
- **The stand** visual is `Art/InstrumentStand_v01.fbx`, inside `Stage1_InstrumentStand_Placeholder_v02` with simple colliders.
- **The props `Patient_TableRest_v01` clip** is used only if its curves bind to `Buddy_Rig_Mixamo65/...`. Otherwise the builder generates a placeholder clip of the same pose.

Camera: the props `CameraAnchor` sees the incisions at a grazing angle, so the tuning overrides it (`overrideCameraAnchor = true`, table-local position (−1.2, 2.45, 0.1) looking at (−0.08, 0.55, −0.12)). Untick it to use the anchor.

**Animation agent**

The controller is `Characters/SausageBuddy/Patient/Patient_Operation.controller`:
- int `OpState`: 0 TableAwake, 1 TableAsleep, 2 Struggle, 3 Panic, 4 Dead, 5 EscapeFall, 6 KnockedOut;
- trigger `ShockDeath` (AnyState → Dead).

`OperationPresentation` sets `OpState` from the replicated state on every peer. The builder keeps existing states and replaces only null or "TableRest" motions, so re-running it after the animation agent assigns clips does not undo their work. `OperationPatientRig` adds a procedural limb, spine and head layer in `LateUpdate` on top of the animator. Once real Struggle/Panic clips exist, its amplitudes (`LimbMotion`, `Twitch`, `HeadShake`, set in `OperationPresentation.UpdatePatient`) should be turned down or off.

**Gameplay events** for other systems:
- `NetworkOperationTable` cues;
- `OperationPresentation.AnimationHook` (`UnityEvent<PatientCue>`) on every peer.

## 7. Tests and evidence

All evidence is in `Working/Reviews/Operations/stage1_v2/`.

- `editmode-tests.txt`: 33/33 PASS.
- `playmode-tests.txt`: 4/4 PASS. The per-check logs are `run_loop/run-log.txt` (76), `run_edges/run-log.txt` (49), `run_rotated/run-log.txt` (33), `run_hud720/run-log.txt` (4). Each run also leaves its screenshots and a `final-state.json`.
  - **loop**: real grab carry → auto-align → prompt → E → 5 strap clicks → 2 s injection (dose 0.96) → blood with early release (progress kept) → bag ($50) → 3 incisions, 7 cords, 3 pulls → tray → card → zoom → take an organ from the tray → leave with E (organ goes to first-person carry). Grades 4/3/2, death chances 0.20/0.30/0.40 after one blood portion.
  - **edges**:
    - F10 and F9; escape of an awake, unstrapped patient (falls off alive), then carry back;
    - a yank costs exactly −1; an awake extraction triggers panic and the banner; a rescue injection within 8 s;
    - a direct click −2, while a drag over the organ never counts; the dropped scalpel returns to its slot;
    - holding 4.8 s kills by overdose; the death banner; early overdose −2 to all organs; injecting a corpse gives a clear refusal;
    - a W tap stays at the table, holding W leaves.
  - **rotated**: the table is moved by (1.4, 0, 0.6) m and rotated 90°, then the patient is carried onto it again; liver extracted without damage; blood and bag; the gurney is frozen during use and free after; the patient rides along.
  - **hud720**: the HUD at 1280×720.
- `net02/`: two standalone processes (`run-localhost-v02.ps1 -Run net02`).
  - Host: `host/run-log.txt` 37 PASS. Client: `client/run-log.txt` 26 PASS.
  - The client cut, snipped and extracted kidney R and helped pull the liver (peak 2 holders), then quit mid-pull.
  - The host finished; there are exactly 3 items with 3 ids; the client's kidney survived; its scalpel returned to the tray.
- `build-result.txt`, plus the player build in `build/` (188 MB; needed by the script).

Named screenshots (1920×1080, real camera and HUD):

| File | Content |
|---|---|
| 01_overview.png | the room, the knocked-out patient on the floor |
| 02_straps.png | straps 5/5 by clicking |
| 03_injecting.png | injecting: ring, «ммм… баиньки» |
| 04_asleep.png | asleep, sleep pips 3/3 |
| 05_blood_bag.png | sealed bag ($50) |
| 06_cutting.png | cutting along the guide |
| 07_opened_cords.png | open incision, kidney and cords |
| 08_pulling.png | pulling, tension bar |
| 09_organ_card.png | organ card, Russian tier label |
| 10_tray_results.png | tray with 3 organs and a bag |
| 11_panic_banner.png | «ПРОСЫПАЕТСЯ! Срочно наркоз!» with the 8 s ring |
| 12_dead.png | overdose death banner |
| 13_direct_cut.png | direct cut −2 (red flash) |
| 14_zoom.png | local wheel zoom |
| 15_hud_1280x720.png | HUD at 1280×720 |
| 16_net_joint_pull.png | two players pulling the liver (host view) |

Also there:
- `contact_sheet_v02.png`: all 16, labelled;
- `operations_stage1_v02_loop.mp4`: the full host loop, 39 s, 960×540, frames every 0.15 s, real time.

How to re-run:
- **PlayMode:** Test Runner → PlayMode → `OnlyVolunteers.Operation.PlayTests` (about 2 min in total).
- **Two processes:**
  ```powershell
  & Working/Reviews/Operations/stage1_v2/run-localhost-v02.ps1 -Run netXX
  ```
  This uses the build in `build/`. Rebuild with `OperationStage1BuilderV02.BuildPlayer(folder)` after code changes.
- **Driver arguments:** `-ops-scenario <suite|loop|edges|rotated|hud720|net-host|net-client> -ops-evidence <dir> -ops-quit`. Death rolls are forced to "survive" (0.99) in tests unless `natural-rolls` is in the scenario name.

## 8. Limitations and placeholders

- **Animation:** every OpState still plays the TableRest pose. Struggle, panic, twitches and head shakes are procedural. The animation agent is authoring the real clips (`ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Operation_v01/`). Escape is a scripted drop at the foot end with a 2 s no-align guard, not an animation.
- **Sound:** sounds come from the existing procedural `OperationSfx` and the `Sfx` library (mumble, gasp, scream, thud, cash register). No new audio.
- **Visuals:** the organ models are the existing kidney and liver models, with one kidney kept from the pair. The cords, the guide, the hole placeholder and the splashes are primitives. Sealed bags use the `BLOOD_BAG_ASTRA_001_v04` model.
- **Missing mechanics:** v01's "Space — hold the patient" mechanic does not exist in v02. Strapping or anesthesia replace it.
- **Untested:** only 2 players were tested over the network (3–4 NOT RUN). There is no human playtest yet.
- **Logs:** the server logs `[OPS] WORLD/CUE/HINT/JOIN/TOOL/BAG/EXTRACT…` lines to the console. They are useful now and could be trimmed later.
- **Legacy files:** the v01 scene and the v01 prefabs remain and still work with the rewritten scripts. Their old IMGUI-era tuning is not used by v02.

## 9. Decisions for the lead

1. **Camera:** keep the tuning override (steeper, readable incisions) or ask props for a new `CameraAnchor` at about (−1.2, 2.45, 0.1) table-local.
2. **Stand placement:** the props instrument stand sits on the camera side, near the player at the table. It is acceptable, but a mirror to the far side would free the view.
3. **Torso strap:** when open, it swings 120° and stands tall in the view (props animation). Consider a smaller open angle.
4. **Legacy cleanup:** delete the v01 scene, the `Stage1_*_v01` prefabs and `OperationStage1_v01.asset`, or keep them as reference.
5. **Debug logs:** keep the `[OPS]` logs during playtests, strip them later.
6. **Procedural struggle layer:** turn it off when the real clips land (see §6).
7. **Build folder:** `Working/Reviews/Operations/stage1_v2/build/` (188 MB) can be deleted after review; the two-process script needs it.

## 10. How to play (short)

Open `Scenes/Dev/Operation_Net_Stage1_v02.unity` → Play → **Host** in the NetworkSession panel (a second instance: **Client**).

| Where | Input | Action |
|---|---|---|
| First person | LMB hold | grab and carry the patient (existing grab); release over the table and he slides into place |
| First person | E (when «[E] Встать к столу» shows) | enter table mode |
| Table | mouse | free cursor; hover shows the target and a hint |
| Table | LMB on a tool, or keys 2/3/4 | take the anesthesia syringe / blood syringe / scalpel; 1 = empty hands |
| Table | RMB | put the tool back into its slot (the anesthesia syringe refills) |
| Table | LMB on a strap | close / open it |
| Table | hold LMB on the arm, shoulder or neck (blue syringe) | inject; release when «Засыпает» turns into «Спит» (about 2 s) |
| Table | hold LMB on an arm (red syringe), then LMB on an empty bag | draw blood (4.5 s), seal the bag |
| Table | drag LMB from the green dot along the dotted line (scalpel) | cut |
| Table | hold LMB on a cord (scalpel) | snip it (0.3 s) |
| Table | hold LMB on the organ and move up slowly (hands) | pull it out; a fast flick is a yank (−1) |
| Table | LMB on the tray (organ in hand) | put it down; LMB on a tray organ picks it up again |
| Table | mouse wheel | local zoom towards the cursor |
| Table | E / Esc / hold WASD > 0.2 s | leave the table (a held organ goes into your hands) |
| Dev | F10 / F9 | new patient / place the patient on the table at once |
