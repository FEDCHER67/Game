# Progress — first playable loop (Field Clinic kit, Part 2)

Scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v17_Play.unity` (Unity 6000.5.11f1, URP). Offline map: no FishNet objects take part in the loop (the map's van, NPCs and LocalInventory are offline already; see docs/CURRENT_STATE.md). Paths below are relative to `Assets/OnlyVolunteers/` unless they start with `docs/` or `ProjectSettings/`.

Results: PASS / FAIL / BLOCKED / NOT RUN, only after the check ran. "MCP" = Unity MCP `execute_code` in Play mode; it drives the existing components directly (no real key presses), so input mapping and feel still need a human playtest.

## Packages added

| Package | Version / commit | Licence | Source | Why | Rollback |
|---|---|---|---|---|---|
| `com.yasirkula.assetusagedetector` (Asset Usage Detector, editor only) | 2.6.3, git `b0bf247aa47d9fe8babbddeea6ba2f6949c63455` (= tag v2.6.3, checked with `git ls-remote --tags`) | MIT (`LICENSE.txt` in the package, Copyright 2016 Süleyman Yasir KULA) | https://github.com/yasirkula/UnityAssetUsageDetector | Approved by Fedya, relayed by the lead on 2026-10-13: find asset references before cleanups | Remove its line from `Packages/manifest.json` (packages-lock.json updates itself) |

Check 2026-10-13 (Play stopped): resolved into `Library/PackageCache/com.yasirkula.assetusagedetector@b0bf247aa47d`, assembly `AssetUsageDetector.Editor` compiled and loaded, compile clean (0 errors, only the old CS0618/UAC1001 warnings), menus `Window/Asset Usage Detector/Active Window` and `…/New Window` exist (`Menu.MenuItemExists`). No search or cleanup was run with it.

## 1. Gap analysis (2026-10-13, before any implementation)

| Step | Exists? (file:line evidence) | Tested how | Result |
|---|---|---|---|
| First-person walking | Yes. KCC player `Player/Scripts/KccFirstPersonInput.cs:167` (WASD axes), `Map/Scripts/GreyboxKccPawn.cs:12` (map pawn), sprint/crouch/jump `KccFirstPersonInput.cs:171,214,284` | MCP, v17 Play: KccFirstPersonInput off, `Character.SetInputs(MoveAxisForward=1)` for 5.8 s from the start (170.9, 549.6) | PASS: 18.8 m walked, stable on ground, no errors. Feel: human playtest |
| Van enter / exit | Yes. E at the left door `Map/Scripts/GreyboxInteractor.cs:136` -> `Map/Scripts/GreyboxVanSeat.cs:111` (Enter); exit E at <= 12 km/h `GreyboxVanSeat.cs:105-106`, free side search left/right/rear `GreyboxVanSeat.cs:139` | MCP: pawn put at the door point, `CanEnter` then `Enter()`; drove; exit via `GetOut` (reflection) | PASS: Driving=true, pawn inactive, 1 AudioListener; exit refused at -25 km/h, allowed at 0 km/h, pawn placed 1.65 m left of the van, 1 AudioListener |
| Van cameras first/third person | Yes. `Vehicles/Van/Scripts/VanCameraRig.cs:9` (Chase / Cockpit), toggle key C `Vehicles/Van/Scripts/VanDriveInput.cs:70`; chase camera wall check `VanCameraRig.cs:69-81` | MCP: `ToggleMode()` twice, Game view screenshot after each | PASS: chase view behind the van and cockpit view from the driver eye (1.60 m) both render. No new key needed |
| Van driving | Yes. `Vehicles/Van/Scripts/VanController.cs`, input `VanDriveInput.cs:49-56`, reset R `VanDriveInput.cs:71,124` | MCP: VanDriveInput off, Throttle 1 for 1.8 s, then -1 | PASS: 11.4 km/h after 1.8 s, braking then reverse to -25 km/h. Full route feel: human playtest |
| Target NPC: detection and flee | Yes (every crowd NPC). `Map/Scripts/GreyboxNpc.cs:432` (Scared: pawn < 7 m, moving van < 14 m), flee `GreyboxNpc.cs:61-63` | MCP: pawn teleported 5 m behind the nearest free NPC (Crowd_003) | PASS: Fleeing=true, NPC 15.1 m away one call later |
| Capture: knock-down / ragdoll / carry | Yes. Q hit `Map/Scripts/GreyboxInteractor.cs:77` -> `GreyboxNpc.cs:452` (Hit); 11-body ragdoll `Characters/Npc/Scripts/NpcRagdoll.cs`; LMB drag `Player/Scripts/Physics/PhysicsGrabber.cs:151` | MCP: `Hit(Fist, Head)` on Crowd_003; existing `Map/Scripts/Dev/NpcLoadingTest.cs` (real PhysicsGrabbers, capsule body) | PASS: State Down / Out, stun 11.4 s, ragdoll active. NpcLoadingTest lift/drag a1-c3, f, f2 PASS |
| Loading into the van | Yes, physical. `Map/Scripts/GreyboxVanCargo.cs:395` (Load: pelvis + collar in the bay, at rest 0.5 s, nobody holding), `GreyboxVanCargo.cs:403` (Unload) | MCP: `NpcLoadingTest` in v17 Play (TimeScale 3, seed 151) | PASS: all cases PASS (side door d1-d3, rear e1-e3, solo h1 3.6 s / h2 4.8 s, two hands i 4.9 s), global errors=0. Capsule body only; ragdoll loading not covered by that test |
| Transport | Yes. Loaded NPCs ride with the van, van teleports (F1-F8, R) carry them `GreyboxVanCargo.cs:35-39` | Code read only | NOT RUN in this pass (exercised by the loop test below) |
| Unloading at a base | Partly. Bodies can be dragged out (`GreyboxVanCargo.cs:403`). Bases exist only as police safe zones `Police/Scripts/PoliceMapData.cs:89-91` (B01 door (192.8, 176.2)) and teleport spots `Map/Scripts/GreyboxTripMeter.cs:45`. No drop-off zone, no hand-over of a patient | Code read; scene query of PoliceMapData | MISSING |
| Stylised operation | Exists only in a separate scene: `Operation/Scenes/OperationTest.unity`, `Operation/Scripts/KidneyMiniGame.cs` (cut -> pull -> tape), `Operation/Scripts/OperationSession.cs`, `Operation/Scripts/OperationTestPlayer.cs` (test walker only). Not connected to the map NPCs | Code read; docs/CURRENT_STATE.md records "both kidneys worked in the Unity test" | NOT RUN here (earlier report). Map connection MISSING |
| Reward | Partly. Map cash: LocalInventory starts with $500 `Map/Editor/MapGreyboxBuilder.cs:436`, shown by `Inventory/Runtime/InventoryHud.cs:225`; police arrest takes 10% `Police/Scripts/PoliceDirector.cs:769`. The OperationTest puts a kidney item into the inventory `OperationSession.cs:182`. Nothing pays for a delivered patient on the map | Code read | MISSING (no reward for the loop) |
| Upgrades | Partly. `Vehicles/Van/Scripts/VanUpgrades.cs:46` (levels 0-3), free debug cycle on 7/8/9 `VanDriveInput.cs:67-69`. No purchase | Code read | Debug only; purchase MISSING (not in this part's scope) |
| Save / load | No. Only `persistentDataPath` use is session photos `UI/Phone/Scripts/PhotoAlbum.cs:28` | grep over Assets/OnlyVolunteers | MISSING |
| Light and sound on key events | Sound yes: hits `GreyboxInteractor.cs:84`, van thuds `GreyboxNpc.cs:1048`, `GreyboxNpcBody.cs:632`, police siren `Police/Scripts/PoliceUnit.cs:30`, operation cues `Operation/Scripts/OperationSfx.cs`. Light: no runtime code changes any Light | grep over runtime scripts | Sound PASS by code; reacting light MISSING |

Console during the gap tests: no new errors or warnings (cleared before Play; 0 entries after).

## 2. Implementation (missing pieces only)

New code, all offline, in `Clinic/` (Assembly-CSharp, namespace `OnlyVolunteers.Clinic`), plus one hook in the existing E handler:

| File | Role |
|---|---|
| `Clinic/Scripts/PatientLifecycle.cs` | `PatientStage` (Available, Captured, Loaded, AtBase, InOperation, Resolved), allowed moves, `PatientRecord`, `PatientTag` (id on the NPC), Condition -> starting grade |
| `Clinic/Scripts/PatientRegistry.cs` | One record per caught NPC, stable `P-xxxxxxxxxx` id; follows GreyboxNpc (Down -> Captured, InCargo -> Loaded); refuses illegal moves; `TryResolve` pays once per id, also across saves |
| `Clinic/Scripts/ClinicStation.cs` | Base B01: receiving pad, operating table (existing `OperationTable`), lamp + beacon whose colour follows events, patient stand-in (existing `OperationPatient`); offers "E — оперировать" through `GreyboxUses` |
| `Clinic/Scripts/ClinicDropOff.cs` | Hand-over: captured body lying in the pad circle, not held -> AtBase; the NPC object is removed, the stand-in carries the id |
| `Clinic/Scripts/ClinicOperationRunner.cs` | Runs the existing `KidneyMiniGame` with the map's KCC player: locks movement/hands/phone, camera to the table, Esc cancels (Cut/Pull), reward via the registry |
| `Clinic/Scripts/ClinicSave.cs` | JSON v1 in `persistentDataPath/OnlyVolunteers/fc_loop_save_v1.json`: money, completed patient ids, van upgrade levels; temp file + replace with `.bak` |
| `Clinic/Scripts/ClinicLoop.cs` | The scene object: wires the parts, reward to LocalInventory cash, load on start, quick save, objective panel and toasts |
| `Clinic/Editor/ClinicLoopSetup.cs` | Menu OnlyVolunteers/Clinic/Add Patient Loop To Open Map Scene |
| `Map/Scripts/GreyboxUses.cs` + `Map/Scripts/GreyboxInteractor.cs` (edit) | `IGreyboxUse` registry; GreyboxInteractor asks it right after the cargo handle, so E stays one handler |

Scene: `Map_Look_v17_Play.unity` got one root object `FC_ClinicLoop` (55 added YAML lines, nothing else changed). No new packages.

### Loop run 1 (2026-10-13, MCP in v17 Play)

Scenario setup moves bodies with the existing `INpcBody.PlaceLying` (instead of dragging by hand) and the van with `ResetUpright` (what F2 does); everything after that is the real code.

| Step | How | Result |
|---|---|---|
| Compile | refresh + compile request | PASS: 0 errors, no new warnings (only the old CS0618/UAC1001 ones) |
| Station built | Play: pad (205.5, 176), table (209.5, 180.5), lamp, beacon, `GreyboxUses` = 1 | PASS (pad disc partly hidden under the road mesh: raised 0.09 m afterwards) |
| Capture -> id | `Hit(Fist, Head)` on Crowd_005 | PASS: record P-5aac0ab432 Available -> Captured |
| Load | body laid on the cargo floor | PASS: GreyboxVanCargo InCargo=true, record Captured -> Loaded |
| Transport | pawn `Enter()`, van to B01 (F2 path), then Throttle 1 for 1.8 s | PASS: NPC came along, woke up sitting (CargoSeated), record stayed Loaded, 11 km/h with the passenger, it stayed at the same van-local place |
| Unload + hand-over, 1st try | exit, torso hit in the bay, body laid on the pad | FAIL: the NPC became Groggy, kicked/crawled (never "at rest" for 0.75 s), woke and ran off (record Loaded -> Captured -> Available). Rule relaxed afterwards (see below) |
| Unload + hand-over, 2nd try | head hit (12 s), body laid on the pad | PASS: Captured -> AtBase within 2.8 s, NPC object gone, one object carries the id (stand-in), table busy, lamp green |
| E prompt | pawn 1.4 m from the table, GreyboxInteractor `_act/_label` read back | PASS: `Use`, "E — оперировать (почка, Perfect, ~$650)" (Condition 95 after the re-stun -> Perfect) |
| Operation | `ClinicStation.Use` (= E), then a virtual Input System mouse cut along the line, pulled slowly, taped 3 times | PASS: camera to the table, player locked (MovementLocked, LookSuspended, interactor off); "Почка [Perfect] за 42 с. Чистая работа!" |
| Reward + autosave | log + save file | PASS: AtBase -> InOperation -> Resolved, cash 500 -> 1150 written to the save (`money 1150`, `completedPatients [P-5aac0ab432]`) |
| Console | errors | FAIL (caused by the test, not the loop): editing ClinicStation.cs during Play made Unity recompile in Play mode after the save; the domain reload broke KCC (`KinematicCharacterMotor.cs:798` NullReference every physics step) and the inventory model. Lesson: never edit scripts while in Play |

Fixes after run 1 (made with Play stopped): hand-over no longer needs the body "at rest" (any speed under 1.5 m/s, so a Groggy patient that kicks is accepted), pad raised above the road mesh, lamp post moved out of the operation camera, labels smaller, quick save moved to the Input System (`Key.K`) so it can be tested with a virtual keyboard.

### Loop run 2 (2026-10-13, MCP in v17 Play, after re-entering Play)

Timed steps ran inside one `EditorApplication.update` driver per scenario (the editor ticks Play irregularly between MCP calls). The operation and the keys used a virtual Input System mouse and keyboard (`InputSystem.AddDevice`), with the input settings set to ignore focus for the test and restored afterwards.

| Check | How | Result |
|---|---|---|
| Load on start (re-entering Play) | `ClinicLoop.LastLoadNote`, cash, completed ids | PASS: "loaded $1150, 1 patients, upgrades 0/0/0", cash 1150, P-5aac0ab432 completed |
| No second reward across sessions | `TryResolve` on a record with the saved id P-5aac0ab432 | PASS: refused (warning logged), cash unchanged |
| Illegal move refused | `Move(Loaded -> AtBase)` on a loaded patient | PASS: refused, `RefusedMoves` 0 -> 1, stage stays Loaded |
| Capture, load, transport | Crowd_004 head hit, laid in the bay, van to the pad by `ResetUpright`, exit at 0.7 km/h | PASS: Captured -> Loaded, NPC rode along and woke sitting |
| Hand-over of a Groggy patient | torso hit, driver waited for Groggy (+4.2 s), laid on the pad | PASS: AtBase after 0.86 s, Condition 95 -> Perfect |
| Table busy | second NPC (Crowd_002) laid on the pad while the table was taken | PASS: not handed over for 3 s, stays Captured, "Стол занят…", lamp pulses yellow |
| E through the interactor | `GreyboxInteractor.Do(_act)` (= the E press) | PASS: act Use, operation starts, MovementLocked |
| Cancel | virtual Esc during the Cut step | PASS: InOperation -> AtBase, patient still on the table, controls back (MovementLocked/LookSuspended false, interactor on), cash unchanged |
| Retry and finish | E again, virtual mouse: cut, slow pull, three tapes | PASS: "Почка [Perfect] … Чистая работа!", Resolved, reward 650, cash 1150 -> 1800, controls back |
| Double completion | `TryResolve` again on the resolved record | PASS: not paid, cash stays 1800 |
| Quick save K | virtual K after setting engine level 2 | PASS: "saved $1800, 2 patients, upgrades 2/0/0"; file has `.bak` of the previous save |
| Light reacts | `ClinicStation.LightColor` reads, run 1 screenshot | PASS for idle amber (1, 0.72, 0.38), pad busy yellow pulse (1, 0.92, 0.30) and patient-waiting green (bulb green in the run 1 screenshot). Operating white and the reward gold flash: code only, NOT measured |
| Console | errors/warnings | PASS: 0 errors; only the 3 intended `[Clinic]` warnings of the refusal tests |

### Run 3 (2026-10-13, after the package install, Play re-entered)

| Check | Result |
|---|---|
| Load on start | PASS: "loaded $1800, 2 patients, upgrades 2/0/0", cash 1800, both ids completed, van engine level 2 |
| ProjectSettings | `PlayerSettings.runInBackground` had become 1 in `ProjectSettings/ProjectSettings.asset` during these runs (the agent set `Application.runInBackground` in Play, which in the Editor writes the player setting). Restored to 0 and saved; `git diff ProjectSettings/` is empty. Later runs did not touch it |

### State left behind

- Test save moved out of `persistentDataPath` to the session scratchpad, so the next Play is a new game ($500, nothing completed).
- Screenshots were temporary (`Temp/fc_captures`, deleted). Unity: `Map_Look_v17_Play` open, Play stopped, scene saved (only `FC_ClinicLoop` added), Profiler off and no Profiler window.

## 3. Status of the loop

| Step | Status |
|---|---|
| Capture (Q, LMB drag) | Existing, PASS by MCP; feel: human playtest |
| Load (physical) | Existing, PASS (NpcLoadingTest + loop runs) |
| Drive to base | Existing driving PASS; the route itself (≈370 m hamlet -> forest) was not driven by hand, only teleported (F2 path) |
| Unload at the base pad | NEW, PASS (laid-on-pad bodies; dragging out by hand not tested by a human) |
| Operation on the map | NEW (reuses KidneyMiniGame), PASS with a virtual mouse; readability and fun: human playtest |
| Reward on screen, once per patient | NEW, PASS |
| Save / load / quick save K | NEW, PASS across Play sessions in the Editor. A built player was not run (T13 of the kit: NOT RUN) |
| Light/sound on events | NEW lamp and beacon colours (partly measured), cash register / UI / operation cues (sound not listened to: NOT RUN) |

Not done (outside this part): checkpoint save of a patient in the van or on the table (only money, completed ids and upgrade levels are saved); spending money on upgrades (7/8/9 stay free debug keys); a buyer instead of the instant payment; the map builders do not add `FC_ClinicLoop` (re-add with the menu after a rebuild); network.
