# Ops/capture round 3 — cloud handoff (2026-10-18)

The cloud session finished round 3 on branch `claude/ops-round3-finish` (from `wip/claude-ops-round3`, be1c311b). **There is no Unity in the cloud: nothing below was compiled or run.** The checks were careful reading, a C# syntax parse of every changed file (tree-sitter: 0 errors), and a symbol pass: every member access in Operation/Capture/Player/Inventory code resolves to a declaration in the repo or a Unity/.NET/FishNet/NUnit API. Type-level errors can still exist, so compile first.

## State found on the WIP branch

The brief said round 3 code referenced missing members (`OperationToolKind.Suture`, `OperationRules.Suture/CanBeginSuture/Held/NextUnbuckle`, `OperationState.zoneSuture/LimbsStrapped`, `OperationTuning.torsoStrap/unbuckleSeconds/suturedModel`, `PatientCue.Stitch/Sutured/Unbuckled`, `OperationStraps`). All of them already exist on be1c311b. The stopped agent had finished items 1, 2, 6a–c and 7, including the HUD, presentation, network stroke, suture tool prefab and the anatomy v05 menu entry. The rule tests (`OperationRound3RulesTests`) were traced by hand against the rules and should pass.

## What this session added

| Item | Change | Files |
|---|---|---|
| 3. Field kit at the table | When the player is by the table (not in the E view), the kit aims at the patient's `OperationPatientRig` body triggers. Ties go into the patient's facts. Anaesthesia goes through `NetworkOperationTable.ServerFieldDose`, using the table syringe's rule. Blood goes through `ServerFieldDrawBlood` (`CanDrawBlood` + `FillBlood`). The kit keeps its own barrel and fill. The HUD shows the dose bar and hints. | `Capture/Scripts/CaptureFieldKit.cs`, `CaptureTableBridge.cs` (`TableTieFor`, `TieTablePatient`), `Operation/Stage1/Scripts/NetworkOperationTable.cs` |
| 4. "Stops being a person" | A **living** patient can end up off the table, either after the escape fall lands or by lying beside the pad. If nobody holds him for 1.2 s, the table releases him (`ServerDischargeLiving`). `CaptureTableBridge.TryDischarge` then re-creates him exactly like a loaded capture (`CaptureSave.Respawn`), with the same PatientId, OperationState, facts and ties. If awake, he is Groggy for about 2 s, then gets up and flees. If asleep, he stays limp. Laid on the pad again, he is re-admitted. The hat/glasses drop only once per patient. | `NetworkOperationTable.cs`, `CaptureTableBridge.cs` |
| 4. Escape-step hooks | `OperationRules.NextUnbuckle(out strap, out hand)` and `PatientCue.Unbuckled` were already there. This session added `LastUnbuckledStrap` / `LastUnbuckledHand`, which are valid when the cue fires, and a test for them. | `Core/OperationState.cs`, `Tests/OperationRound3RulesTests.cs` |
| 5. Charged throw | Shared pure helper `OnlyVolunteers.Inventory.ThrowCharge` (Inventory.Core): a tap is 2 m/s, a full charge takes 1.1 s, the top speed is 9 m/s at ≤1 kg and 4.5 m/s at ≥60 kg, plus a small lift. `Clamp` runs on the server. Sites: hotbar **G** (`InventoryInput`: press starts the charge, release throws; `IInventoryView.RequestThrowSelected`; `NetworkInventory.ServerThrowPhysical` throws a held organ with its mass; offline items count as 1 kg; pocket `WorldItem`s have no physics and still just drop). Carried body bag **LMB** (`CaptureCorpseHands`: press then release; a body counts as heavy, so a full charge gives the old 4.5 m/s). One IMGUI bar, `ThrowChargeIndicator`. `OperationPhysicalItem.ServerRelease` now caps at 10.6 m/s instead of 6. EditMode tests: `Inventory/Tests/EditMode/ThrowChargeTests.cs`. | `Inventory/Core/ThrowCharge.cs`, `Inventory/Runtime/{IInventoryView,LocalInventory,NetworkInventory,InventoryInput,ThrowChargeIndicator}.cs`, `Capture/Scripts/CaptureCorpseDisposal.cs`, `OperationPhysicalItem.cs` |
| 6c (extra) | `CaptureTableBridge.AimingAtPatient` now excludes `OperationSurgicalBones.Mask` too. | `CaptureTableBridge.cs` |

New `.meta` files were written by hand (minimal two-line form, like the repo's): `ThrowCharge.cs`, `ThrowChargeTests.cs`, `ThrowChargeIndicator.cs`.

## Verify locally in Unity (in this order)

1. **Compile.** Open the project, wait for the import, and get zero console errors. Likely spots if anything fails: the `switch` blocks in `CaptureFieldKit.UseOnTable`, the FishNet codegen for the new `[ServerRpc] ServerThrowPhysical`, and the `using ThrowCharge = …` aliases in `CaptureCorpseDisposal.cs`.
2. **EditMode tests.** Run `OperationRound3RulesTests`, `OperationRulesTests`, `OperationAbdomenRulesTests`, `ThrowChargeTests`, `CaptureRulesTests` and the inventory model tests. All should be green.
3. **Art v05.** Run the menu `OnlyVolunteers/Operation/Integrate anatomy v05 (lower opening, intestines, sutured state)` once. It reads `ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v05/ORGANS_LAYOUT_v05.json`, copies or validates the v05 FBX files and sets `tuning.suturedModel`. Then run `Build suture tool (needle holder v01)`, which is a no-op if already done (the prefab is already in `toolPrefabs`). Check that `OperationSutured_v05` has `SUTURE_STITCH_01..20`, `SUTURE_SKIN` and `SUTURE_BLOOD` as named meshes.
4. **PlayMode / real input.** Run the existing probes, especially `bag` (it presses LMB for 2 frames: a tap toss, about 2 m/s, which must still pass "velocity > 1"), the v04 throw, the corpse disposal and the gurney probes.
5. **Manual.** Go through `CAPTURE_DELIVERY_PLAYTEST_v04_RU.md`. Points that need eyes in particular:
   - Discharge: the field NPC appears at the landed hips (head direction and face-up come from the patient's `mixamorig:Hips`/`Head`). He comes back **dressed** in the crowd template: a known visual gap, because the undressed look exists only on the patient model.
   - Field kit at the table: the ray must hit the rig's trigger capsules, and the table pad or straps in front must not block it.
   - The G hold no longer drops on **press** but on **release**. Check that nothing else depended on that, for example scenario drivers that only tap G.
6. **Build.** The v04 exe for Fedya's playtest.

## Known limits / not done

- Ties on the table patient are facts plus visuals only. They do not stop the free hand from unbuckling, because the rules don't know ties yet.
- Hitting the patient with Q while he is **on the table** is not added. Off the table he is a normal NPC again, so Q works there.
- The discharge happens on the stage-A host only (admission mode); the dev operation scene keeps the stage-1 behaviour.
- `CaptureCorpseHands.ThrowSpeed/ThrowLift` constants are now unused (kept as public API).
