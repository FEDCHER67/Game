G43 — GPT-6 Astra, reasoning MAX. Paste when the cloud map build (branch claude/map-v76-build) is built locally in Unity.

[G43] Move the capture → operations setup onto the new map (Map W76 build).

Read first: docs/reports/CAPTURE_DELIVERY_STAGE_A.md, docs/reports/CAPTURE_DELIVERY_STAGE_A_HOWTO_RU.md, docs/reports/CAPTURE_DELIVERY_PLAYTEST_v04_RU.md (+ v05 if present), docs/reports/OPS_ROUND3_CLOUD_HANDOFF.md, docs/reports/OPS_ROUND4_CLOUD_HANDOFF.md, docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v01.md §5.2 (grandpa's yard "as in Fedya's build i09: barrel, paint cans + brush, red rocking chair, van pad"), docs/reports/MAP_V76_BUILD_CLOUD_HANDOFF.md.
Source scene (DO NOT modify it): Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity. Target: the new map scene Map_W76_Build_v01.unity (built from branch claude/map-v76-build) — make a COPY named Map_W76_Play_v01_capture.unity and work only in the copy.

Move/rebuild in the copy, adapted to the new geometry:
1. Base 2 (grandpa's hut, Hamlet): the open shed "Операционная деда" with the operating table/gurney (NetworkTableAstra / OperatingTableAstra_v02 prefab), instrument stand, blood bags, tray; grandpa's yard props per handoff §5.2; the van spawn pad.
2. All capture/operation runtime objects and wiring from i10: CaptureDirector (and every serialized reference it has), CaptureTableBridge, CaptureCorpseDisposal, CaptureFieldKit, HUD/view-model objects, NetworkManager/NetworkSession + solo-host autostart, the player pawn with NetworkPlayer (externalControl), NetworkGrabber, inventory, OperationStage1 tuning asset, spawnables (DefaultPrefabObjects), save settings (LoadOnStart/Autosave), body-bag art refs.
3. Crowd/NPCs for capture in the Hamlet (same crowd system and density as i10's hamlet; CaptureNpc components), district id for quality (Hamlet).
4. Water kinds for corpse disposal: the new river/lake/canal water must report WaterKind River/Lake/Canal to WaterQuery (ponds/puddles/pools not); depth >= 0.35 m where disposal should work.
5. FishNet scene NetworkObjects: make sure every scene NetworkObject has a unique, valid scene id after copying (re-generate if needed) — no duplicate ids, no missing prefab ids.
6. Layers/tags (SurgicalBone, Vehicle, NpcBody…) and physics settings unchanged.

Verification (mandatory, real input):
- Point the existing capture/operations probes and PlayMode tests at the new scene (keep i10 tests too): bag, corpse, corpse-reload, gurney, gurney2, straps, field-blood, rules, save-a/save-b, FullLoop, water disposal; Ops PlayMode suite; EditMode suite. Report counts vs. i10 (expected: EditMode all green, Ops 11/11, Capture 12/13 with the known flaky FullLoop).
- Build the release player of the new scene to Working/Reviews/Capture/stageA/build_v05/CaptureDelivery_W76.exe (CaptureStageABuilder with the new scene), smoke-run your own process 30 s, no errors.
- Screenshots: base 2 yard + shed + table (3 angles), Hamlet capture road, a disposal water spot; into Working/Reviews/Map_W76_build/ops_move/.
Hacks are OK if documented (Fedya: "whatever it takes"), but no gameplay code changes in Operation/** or Capture/** unless a test proves the move needs it — list any such change.

Rules: Unity lock before ANY Unity use: powershell -NoProfile -File C:\Users\Zeyo-ne\.ai-bridge\unity_lock.ps1 -Cmd acquire -Id G43 (refresh ≤20 min, release -Done). Never two Unity processes; don't touch processes you didn't start; don't modify the map scene (work in the copy). Back up and restore save files (capture_stageA_*.json) if tests change them. Only C:\Dev\Game; nothing under C:\Users\Zeyo-ne\.codex; no commits; list changed files + a short RU playtest instruction docs/reports/CAPTURE_DELIVERY_PLAYTEST_W76_RU.md ("что сделать → что увидеть").
