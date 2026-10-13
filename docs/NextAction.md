# Next action — first playable loop (2026-10-13)

The loop catch -> load -> drive -> unload -> operation -> money -> save runs in `Map_Look_v17_Play` (object `FC_ClinicLoop`, code `Assets/OnlyVolunteers/Clinic/`). Every step passed scripted MCP checks (docs/Progress.md); nobody has played it with real keys yet.

## 1. Exact next step: Fedya plays one full loop (about 10 minutes)

1. Unity 6000.5.11f1, open `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v17_Play.unity`, Play, click into the Game view.
2. Follow "Полный цикл: от поимки до награды" in docs/drafts/PLAYTEST_GUIDE_2026-10-12.md: hit an NPC near the start (Q), drag it into the van (LMB, side door E), drive to B01 Вагон by the panel and the beacon (or F2 at the wheel), drag the patient into the ПРИЁМКА circle, E at the table, cut / pull / tape, see "+$…", press K, stop Play, Play again and check the money.
3. Write down: total loop time, where it got stuck or boring, whether the panel/beacon/labels are readable, whether the operation camera works, whether it is funny rather than gross. Red Console lines go into the report.

Pass: one loop finished by hand, money shown and still there after the second Play, no red errors.

## 2. Next agent task (after the playtest notes)

"Checkpoint save of the patient" (fc-patient-lifecycle): extend `ClinicSaveData` to version 2 with a migration from v1 and save the active patient (id, stage Loaded or AtBase, Condition/grade). On load, a Loaded patient appears lying in the van's cargo bay (fresh crowd NPC carrying the saved id), an AtBase patient appears strapped on the table; never two copies, never a second reward. Verify in Play: save with the patient in the van, re-enter Play, the same id is in the van; same for the table. Files: `Clinic/Scripts/ClinicSave.cs`, `ClinicLoop.cs`, `PatientRegistry.cs`, `ClinicStation.cs`.

## 3. After that, in this order

1. Spend money: buy van upgrade levels at the base instead of the free debug keys 7/8/9.
2. Make the map builder (`Map/Look/Editor/MapLookGameplay.cs`) add `FC_ClinicLoop`, so a map rebuild keeps the loop (today: menu OnlyVolunteers/Clinic/Add Patient Loop To Open Map Scene, then save the scene).
3. A buyer (phone Messages) instead of the instant payment; organ into the inventory.
