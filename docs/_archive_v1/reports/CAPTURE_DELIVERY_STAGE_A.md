# Capture → table Stage A — G35 delivery report

Status: implementation and requested flow checks delivered; Ragdoll regression gate FAIL (open r25). Review build and startup smoke PASS; not a clean final regression acceptance. Updated 2026-10-18.

Work is confined to C:\Dev\Game, with the shared G35 Unity lock. No staging, commits or pushes. Only map i10 is edited; protected source models, skeleton/clips, Capture/Data JSON and other map scenes are untouched by G35. Existing dirty work was preserved using the starting hash inventory.

## Behavior delivered

- Capture retains one PatientId/state from field through van/table. The real-input scenario now fails explicitly if it needs a placement fallback. Bay crouch uses the same real Input System Ctrl as gameplay; no KCC tuning was changed. The complete run_loop_07 passes: initial physical loading, 3-body door/capacity, top-up, drive, unloading and physical table carry, without either placement fallback.
- Strap interaction is PREP-only for every tool, validated on both input and server. The actual visible mesh is the target. The right arm has its own target; body/shoulder clicks do not toggle torso straps. A heavy gurney parks against incidental loading and releases its brake for deliberate grabbing.
- Approved Patient/OperationAbdomen v02 copies are integrated: marker frames, one stencil opening, gradient interior, kidney/liver scale and orientation, short separate artery/vein cords, belly guide, liver loop and marker +Z extraction. Original rig/avatar/clips are retained. Kidney/liver inventory sizes are 0.15/0.22 m.
- Dead, unstrapped patients can leave the table as the existing 11-body network ragdoll. Holding R consumes one bag and puts one physical body-bag item into NetworkInventory. G drops, E picks up and LMB throws. Packing preserves identity/evidence; River/Lake/Canal immersion splashes, sinks and only then resolves identity and clears evidence links. v02 G34 closed bag/atlas/convex collider are imported copies.
- The existing capture save includes optional corpse/bag poses, held state and bag stock. Witness carry hooks record +10 unbagged / +2 bagged; no suspicion implementation was added. Extraction mortality probabilities are unchanged; a surviving patient cannot be packed.

## Verification record

| Check | Result | Evidence |
|---|---|---|
| Full EditMode | PASS 240/240 | Working/Reviews/Capture/stageA/g35_editmode_results.xml |
| Operations | PASS 9/9 latest case results, full run plus targeted reruns | g35_verification_summary.json; original and rerun XML retained |
| Capture | PASS 6/6 latest case results, full run plus targeted reruns | g35_verification_summary.json |
| Complete capture → van → table → kidney | PASS, no placement fallback | run_loop_07/run-log.txt; g35_capture_targeted_02.xml |
| Corpse carry, R bag in hands, G/E/LMB, bag disposal, held-bag reload | PASS | run_corpse_03/run_g35-corpse, run_corpse-reload; g35_capture_targeted_02.xml |
| Unbagged corpse: real LMB grab/drop into River, Lake and Canal | PASS | run_water_04/run_g35-water; g35_water_final_results.xml |
| NPC Loading | PASS 19/19, matches baseline 19/19 | g35_npcloading_i10.txt; baseline_npcloading_i09.txt |
| Ragdoll full i10 | FAIL 32/34: known r7 pair-rear timing; new observation r25 wall-push | g35_ragdoll_i10.txt; recorded baseline 31/34 (r6/r6b/r7) |
| Ragdoll runover comparison | FAIL: i09 5/5; i10 4/5; fresh i10 without loading/autosave 4/5 | g35_baseline_comparison.json; all three reports retained |
| Final release player build | PASS: 0 errors, 12 warnings, 955 MB, 31.02 s | g35_build_result.txt; build/CaptureDelivery_StageA.exe |
| Actual release-player startup smoke | PASS: Direct3D 11, map/crowd, solo host, table and local player initialized; no runtime error | g35_player_smoke.log; g35_build_verification.json |

Unity: 6000.5.11f1, existing CoplayDev unity-mcp v10.2.0, one hidden batch Editor. Runtime assertions use the existing real-input scenarios; corpse actions use virtual Mouse/Keyboard, not feature RPCs. The map runs as the existing solo FishNet host. Domain-reload callback loss was verified against the real fresh NUnit XML before clearing stale jobs.


## Evidence and reproduction

All evidence below is under `C:\Dev\Game\Working\Reviews\Capture\stageA`.

- [Capture loop contact sheet](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_capture_contact_sheet.png) and [81 s MP4](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_capture_loop.mp4).
- [Operation before/after](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_operation_before_after.png), captured from actual Unity Play Mode.
- [Corpse/bag/reload contact sheet](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_corpse_contact_sheet.png), [21 s corpse/bag MP4](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_corpse_bag_flow.mp4), and [water disposal MP4](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_water_disposal.mp4).
- [Per-case verification index](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_verification_summary.json). Original failing XML/run logs remain beside the passing reruns.
- [Protected file check](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_protected_files_check.json): 188 covered protected files match their starting SHA-256. NPC Loading and Ragdoll test sources also have no Git diff.

Exact verification entry points: the Unity MCP `run_tests` tool, mode `EditMode` for the whole suite, and mode `PlayMode` with the existing `OnlyVolunteers.Operation.Stage1.Tests.OperationRealInputPlayTests` / `OnlyVolunteers.Capture.Tests.CaptureDeliveryPlayTests` cases enumerated in the per-case index. Capture runs use `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity`. NPC Loading and Ragdoll run by adding their unchanged runtime dev-test components in fresh Play sessions on i10: `OnlyVolunteers.Map.Dev.NpcLoadingTest` (Seed 151, TimeScale 3, RunSweep true), then `OnlyVolunteers.Characters.Npc.Dev.RagdollSmokeTest` (Seed 9, TimeScale 3, Only empty, PerfFrames 300). Their full reports are preserved.

Failures found and corrected during this work remain visible in the history: initial carry routes needed placement fallbacks; the final route is physically valid. The body-bag builder used a runtime-only network-object property and failed to register the prefab; it now reads the prefab component. Broad liver-guide selection hid visible kidney targets; selection is narrowed to the visible line. Moving small targets are followed by the input driver. The final water fixture stabilizes the player so a falling eye cannot invalidate the existing server origin guard. Gameplay thresholds and the original assertions were retained.


## Review build

[CaptureDelivery_StageA.exe](C:/Dev/Game/Working/Reviews/Capture/stageA/build/CaptureDelivery_StageA.exe) — keep the adjacent `_Data`, MonoBleedingEdge and DLL files with the executable. Built by `OnlyVolunteers.Capture.Editor.CaptureStageABuilder.BuildPlayer()` for Windows x64, only the i10 scene, `BuildOptions.None`. Build succeeded with 0 errors and 12 warnings (9 obsolete Unity API uses, 2 unused PoliceDirector fields, 1 KCC serialization analyzer warning), all in files not changed by G35.

The actual player was started hidden with graphics using `-batchmode -capture-fresh -screen-width 1280 -screen-height 720 -logFile C:\Dev\Game\Working\Reviews\Capture\stageA\g35_player_smoke.log`. The log confirms Direct3D 11, 63 crowd NPCs, local host/client, admission table and owned player. No exception/error or save write appeared. Only the recorded smoke process was stopped. This is a startup check, not a claim that the full automated gameplay scenarios ran in the release player.

## Scope and known limits

Stage A is solo capture/delivery on i10. Networked capture/van/crowd (CD-10), witnesses/police suspicion, shops/prices/upgrades and head bags remain Stage B. Bag supply is the explicit prototype stock of two, persisted in the existing save. The test results describe executed automated checks; human acceptance of handling and visuals remains a playtest decision. The full Operations and Capture totals above combine the latest executed result for each case across the full runs and targeted reruns; they are not claims that one final combined run passed.


## Open Ragdoll comparison issue

The full unchanged Ragdoll test on i10 is **32/34, FAIL**, not an unchanged-green baseline. The recorded i09 baseline was 31/34 with r6, r6b and r7 failures. Current r6 and r6b pass; r7 pair rear-door loading takes 6.3 s against its unchanged 6 s limit. A newly observed **r25 wall-push** failure remains: after pushing a lying NPC against a wall at 10 km/h and backing away, the body follows the van 1.8–2.4 m rather than becoming free (1.5 m threshold).

The unchanged `Only="runover"` subset passes 5/5 on i09, fails 4/5 on i10, and still fails 4/5 on i10 with save loading and autosave disabled only in memory. This rules out the editor save as the sole cause. Normal runs report errors=0, NaNs=0 and lostGrips=0. The new corpse component registered no corpses during the fresh subset. Cause is **not established**; this report does not attribute it to new corpse code or declare it pre-existing merely because the core physics source was untouched.

A further diagnostic with the Capture director inactive broke dependent network setup (NullReferenceException observations, global FAIL); it is retained as an **invalid diagnostic**, not used to claim acceptance or causation. Normal scene settings were reloaded from disk afterward (director active, LoadOnStart true, AutosaveSeconds 60, bag assigned, scene not dirty). No diagnostic scene changes were saved. The review build retains the normal gameplay configuration. Resolving r25 and then rerunning the Ragdoll comparison remains open; M5 is not a clean regression acceptance.

## Changed files

The full absolute-path inventory is [g35_changed_files.md](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_changed_files.md). Its [JSON manifest](C:/Dev/Game/Working/Reviews/Capture/stageA/g35_changed_files.json) lists every source/asset/document with SHA-256, plus individual generated evidence and player files. Starting hashes: Working/Reviews/Capture/stageA/g35_start_manifest.json. Reasons for existing-file edits are below; the complete source list is appended at the end.

Russian controls: [CAPTURE_DELIVERY_STAGE_A_HOWTO_RU.md](C:/Dev/Game/docs/reports/CAPTURE_DELIVERY_STAGE_A_HOWTO_RU.md).

Handoff: G35-owned batch Unity and smoke player are closed; Play stopped on i10 before close; shared Unity lock released. EditorSettings matches the exact takeover hash. No files staged, committed or pushed. Ragdoll r25 remains the open acceptance issue.


## Reasons for editing existing files

Paths below are relative to C:\Dev\Game; the final manifest gives every absolute path and .meta.

| Existing file or closely related group | Reason |
|---|---|
| Capture/Core/CaptureRules.cs | Optional corpse/bag list and bag stock in the existing v1 save DTO. |
| Capture/Scripts/CaptureDirector.cs | Own the disposal component, resolve identity only on water completion, arbitrate physical bag versus both grabbers. |
| Capture/Scripts/CaptureSave.cs | Save/restore the optional corpse/bag fields using the existing save flow. |
| Capture/Scripts/CaptureTableBridge.cs | Replace table R-delete with packing; keep identity on clothing evidence. |
| Capture/Scripts/CaptureScenarioDriver.cs | Real Ctrl state and isolated corpse scenarios/save slots. |
| Capture/Scripts/CaptureScenarios.cs | Physical carry/reach route corrections and explicit failure for any placement fallback. |
| Capture/PlayTests/CaptureDeliveryPlayTests.cs | Partial class seam for the added corpse tests; original four tests retained. |
| Player/Scripts/KccFirstPersonInput.cs | Read Input System Ctrl alongside legacy Ctrl, so the same intended crouch works in the bay and test. No motor parameters changed. |
| Operation/Stage1/Core/OperationState.cs | Approved v02 cord geometry branch; existing rule behavior stays intact. |
| Operation/Stage1/Core/OperationAbdomenRules.cs | Approved belly/loop coordinates in the v02 marker frame; old layout branch retained. |
| Operation/Stage1/Core/OperationTuning.cs and Data/OperationStage1_v02.asset | Explicit v02 presentation references and approved sizes; no mortality changes. |
| Operation/Stage1/Prefabs/Stage1_Patient_v02.prefab | Bind approved model/markers while preserving prefab identity, rig/avatar/controller and clips. |
| Operation/Stage1/Scripts/OperationPatientAnchors.cs | Expose the additional abdomen/guide markers. |
| Operation/Stage1/Scripts/OperationAbdomen.cs | Approved opening/guide presentation; transfer visuals to a detached corpse. |
| Operation/Stage1/Scripts/OperationPresentation.cs | Exact strap targets, approved organ scale/orientation and small separate cords; relinquish detached corpse visuals. |
| Operation/Stage1/Scripts/OperationTableView.cs | PREP-only strap intent and v02 opening/cord/guide hit selection. |
| Operation/Stage1/Scripts/NetworkOperationTable.cs | Server PREP/visible-strap validation, table brake and narrow dead/unstrapped ragdoll handoff. |
| Operation/Stage1/Scripts/OperationPatientRagdoll.cs | Use the existing ragdoll implementation for a detached corpse and restore. |
| Operation/Stage1/Scripts/OperationHud.cs | Explain normal corpse carry and bag packing after death. |
| Operation/Stage1/Scripts/OperationNetworkProbe.cs / OperationNetworkProbeV04.cs | Real-input PREP routing, moving v02 target acquisition, exact v02 geometry assertions, and safe fixture placement. No assertions removed. |
| Operation/Stage1/PlayTests/OperationRealInputPlayTests.cs | Partial class seam for the added strap/brake tests. |
| Operation/Stage1/Data/OperationSpawnables_v02.asset / Assets/DefaultPrefabObjects.asset | Register the body bag; DefaultPrefabObjects is FishNet's generated registry entry. |
| Inventory/Items/Item_Kidney.asset / Item_Liver.asset | Correct physical inventory model size to approved 0.15/0.22 m. |
| Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity | Assign the body-bag prefab on the i10 capture director only. |
| docs/reports/CAPTURE_DELIVERY_STAGE_A_HOWTO_RU.md | Updated PREP, corpse, inventory bag, water disposal and save instructions. |
| Working/Reviews/Capture/stageA/PROGRESS.md | Durable checkpoints including failures, corrections and executed evidence. |

All runtime paths in this table begin Assets/OnlyVolunteers unless the complete Assets/ prefix is shown. New files implement the exact strap targets/brake, v02 opening/shaders/importer, corpse/bag/save DTO/builder, and their real-input tests. They are enumerated with metadata in the final manifest.

## Complete source, asset and document inventory

80 changed/new source, imported asset, metadata and document paths. Generated screenshots, frame sequences, logs, MP4s and player files are enumerated individually in the linked JSON manifest. Unity Library/Temp caches are excluded.

- `C:\Dev\Game\Assets\DefaultPrefabObjects.asset` — modified (generated FishNet registry)
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BODYBAG_ASTRA_001_v02.fbx` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BODYBAG_ASTRA_001_v02.fbx.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BODYBAG_ASTRA_001_v02_Atlas_00.png` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BODYBAG_ASTRA_001_v02_Atlas_00.png.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BodyBag_Cargo_v02.asset` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BodyBag_Cargo_v02.asset.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BodyBag_Cargo_v02.mat` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BodyBag_Cargo_v02.mat.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BodyBag_Cargo_v02.prefab` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Art\BodyBag_Cargo_v02.prefab.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Core\CaptureCorpseSave.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Core\CaptureCorpseSave.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Core\CaptureRules.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Editor\CaptureCorpseBuilder.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Editor\CaptureCorpseBuilder.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\PlayTests\CaptureCorpseRealInputPlayTests.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\PlayTests\CaptureCorpseRealInputPlayTests.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\PlayTests\CaptureDeliveryPlayTests.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureBodyBag.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureBodyBag.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureCorpseDisposal.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureCorpseDisposal.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureDirector.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureSave.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureScenarioDriver.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureScenarios.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureScenariosCorpse.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureScenariosCorpse.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureTableBridge.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Characters\SausageBuddy\Patient\SAUSAGE_BUDDY_PATIENT_v02.fbx` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Characters\SausageBuddy\Patient\SAUSAGE_BUDDY_PATIENT_v02.fbx.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Items\Item_Kidney.asset` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Items\Item_Liver.asset` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Art\OperationAbdomen_v02.fbx` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Art\OperationAbdomen_v02.fbx.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Art\OperationAbdomen_v02_Gradient.png` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Art\OperationAbdomen_v02_Gradient.png.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Art\Shaders.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Art\Shaders\OperationMaskStencil_v02.shader` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Art\Shaders\OperationMaskStencil_v02.shader.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Art\Shaders\OperationSkinStencil_v02.shader` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Art\Shaders\OperationSkinStencil_v02.shader.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationAbdomenRules.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationAnatomyV02.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationAnatomyV02.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationState.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationTuning.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Data\OperationSpawnables_v02.asset` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Data\OperationStage1_v02.asset` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Editor\OperationStage1AnatomyV02.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Editor\OperationStage1AnatomyV02.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\PlayTests\OperationG35RealInputPlayTests.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\PlayTests\OperationG35RealInputPlayTests.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\PlayTests\OperationRealInputPlayTests.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Prefabs\Stage1_Patient_v02.prefab` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\NetworkOperationTable.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationAbdomen.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationHud.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationNetworkProbe.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationNetworkProbeCorpse.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationNetworkProbeCorpse.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationNetworkProbeG35.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationNetworkProbeG35.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationNetworkProbeV04.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationOpeningV02.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationOpeningV02.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationPatientAnchors.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationPatientRagdoll.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationPresentation.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationStrapTargets.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationStrapTargets.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationTableBrake.cs` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationTableBrake.cs.meta` — new-or-generated
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationTableView.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Player\Scripts\KccFirstPersonInput.cs` — modified
- `C:\Dev\Game\Assets\OnlyVolunteers\Scenes\Map\Map_Look_v19_Play_i10_capture_delivery.unity` — modified
- `C:\Dev\Game\docs\reports\CAPTURE_DELIVERY_STAGE_A.md` — new-or-generated
- `C:\Dev\Game\docs\reports\CAPTURE_DELIVERY_STAGE_A_HOWTO_RU.md` — modified
- `C:\Dev\Game\Working\Reviews\Capture\stageA\PROGRESS.md` — modified
