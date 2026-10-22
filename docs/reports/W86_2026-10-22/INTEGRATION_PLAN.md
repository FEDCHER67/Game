# Интеграция в играбельную W86 — разведка и план (2026-10-22)

Read-only discovery for Fedya's brief `integrate-vadim-assets-and-playable-loop.md`. No Unity, no project edits, only `git fetch`.
State read: `main` = `origin/main` = `e231401f` (Vadim TASK-000898). Local uncommitted W86 work exists: `W85Builder.cs`, `W85Look.cs`, `W85Rollout.cs`, `Tools/MapV85/*` modified; `W85Build/Data/v02/`, `W86Relief.cs`, `W85FarView.cs`, TextureTest v07 untracked. Do not touch these. `W85PlayIntegrator.cs` itself is unmodified.
Play scene evidence below comes from grepping script/prefab GUIDs in `Map_W85_Play_v01.unity` (56 MB) and its source `Map_Look_v19_Play_i10_capture_delivery.unity`. The W86 integrator picks the newest `Data/v*` automatically (`DataDir()`), so v02 builds the same way.

## 1. Обновления Вадима (commit 976100c7, published by e231401f; no other Vadim commits since 10-20 except map v78–v85 work)

14 Sausage Buddy models. All of them are real files (not LFS pointers): FBX 1.27–1.61 MB, .blend 3.1–3.3 MB, 7 preview PNGs, and `validation_*.json`. The rig is the same Mixamo 65-bone skeleton as the existing pool. Each has the 13 shared clips in the .blend; the FBX has only Idle, which is the existing convention: the importer uses the shared `SausageBuddy_Greybox.controller` with Buddy A's avatar. Triangles come from the validation JSON. The crowd budget is 15k (`build_types_opt_v01.py` BUDGET), and the importer flags anything over 20k as HEAVY.

| Type | Rev | Tris | Scale | Hand prop | New / update | Role (Vadim spec / README) | Where it goes now |
|---|---|---|---|---|---|---|---|
| CONSTR_INDIAN | v08 | 20,932 | 1.0 | – | UPDATE (Unity has v07 + opt) | Construction crowd (new moustache) | construction table, bump rev |
| CONSTR_MEXICAN | v05 | 20,063 | 1.0 | – | UPDATE (Unity v04 + opt) | Construction crowd | construction table, bump rev |
| CONSTR_UZBEK | v05 | 17,380 | 1.0 | – | UPDATE (Unity v04 + opt) | Construction crowd | construction table, bump rev |
| HAMLET_MUZHIK | v01 | 18,058 | 1.0 | LeftHand (basket) | NEW | Hamlet crowd (README Hamlet row) | hamlet table |
| OLD_POPKING | v01 | 18,101 | 1.0 | – | NEW | Downtown street NPC, "not VIP" (spec 5б) | downtown table |
| HAMLET_HUNTER_GRANDPA | v01 | 21,420 | 1.0 | RightHand (shotgun) | NEW | Hamlet responder / "police" (spec 4.4, POL-12: max 1). Group moved to Силовики (TASK-000894; the JSON still says Хутор) | import only. Responder AI does not exist |
| POLICE_THIN | v02 | 16,510 | 1.06 | – | NEW in Unity (replaces militia v01, never imported) | Downtown/Beach/Port/Construction police (POL C11/C12) | police crews: `MapPolicePlacer` already names the crews `PoliceCrew_N_Thin/Fat`. Blocked: no police in W85 (§3) |
| POLICE_FAT | v02 | 19,274 | 1.0 | RightHand (donut) | NEW in Unity | as above | as above |
| FBI_AGENT | v01 | 16,096 | 1.0 | – | NEW | Elite security, FBI building + gate trap (ELITE spec 5, canon 18.10) | import only. Gate trap not built; W85 has no Elite crowd |
| ARMY_SOLDIER | v01 | 21,925 | 1.1 | – | NEW | Tramduro island garrison | import only. Island restricted (POL C31) |
| TRAMDURO | v01 | 19,467 | 1.0 | – | NEW | Finale model (island) | import only |
| VIP_BEASTMAN | v01 | 25,139 | 1.05 | RightHand (cheque) | NEW | Elite VIP, "later / special orders in the city" (spec 5а.1 p5, 7.11) | import only |
| VIP_SPEEDSTER | v01 | 23,026 | 1.0 | – | NEW (8k tris of hair twists) | Elite VIP | import only |
| VIP_BLINDFOLD | v01 | 19,058 | 1.08 | – | NEW | Elite VIP | import only |

Other Vadim decisions in the same push that affect what is already in Unity:
- **BAD_ALTGIRL is VIP-only and was removed from Rough** (TASK-000883, spec 5б). Our `NpcSpawnTables_v01` still lists her in `rough` (`NpcTypesImportV01.WriteTables`), and she walks in W85.
- The Port pool is FOREMAN and SAILOR only. That matches our table.
- The spec draft (`docs/specs/NPC_BEHAVIOUR_SPEC_2026-10-21_v01.md`, status DRAFT) covers the following. Layer A: activities with weights and per-POI limits, plus funny skits once per 30–60 s in view. Layer B: district "wit" and a responder for each district. Downtown/beach call the police. Hamlet calls the hunter grandpa, who misses 90–95 % of his shots. In Rough the gopniks fight. At the construction site the crew fights and the police cover their eyes. In the forest nobody reacts. Witnesses call on the spot instead of running to a point, which replaces the current `CrowdWitness` run-to-hotspot. None of this is implemented. It is design input, not something to integrate now.

How the models plug into our system: `Types_v01/Editor/NpcTypesImportV01.cs` has a hard-coded `Pool` (id, rev). It copies the FBX, and prefers `ArtSource/.../Types_opt_v01/SAUSAGE_BUDDY_<ID>_vNN_opt_v01.fbx` when one exists. It builds the prefabs `SausageBuddy_<ID>` (NpcRig, plus `NpcHeldProps` when there are `Props_*Hand` meshes) and the presets. It rewrites the tables in `WriteTables`. `W85PlayIntegrator` step 5 calls `AddTypeTemplates` (one inactive template per table and placement type), and `CrowdDirector.TypeTable.TakeFor()` draws by district. The decimation workflow is `ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v01/build_types_opt_v01.py`. It also has a hard-coded POOL, takes `--types` and `--out`, budget 15k, tolerance 1.5 mm. It removes hidden faces and decimates the outfit, keeping rig, object names and materials, and it never overwrites an existing revision. That workflow took the previous CONSTR revisions about 20.9k → 15.5k.

## 2. Другая готовая, но не подключённая работа

| Work | Where | Finished? (evidence) | In W85 play? | Compatible with main? | Verdict |
|---|---|---|---|---|---|
| Ops round 4: reopen sutured belly, smooth suture, escape clips in gameplay, 1.5× speed, trunks stay | `origin/claude/ops-round4` 1d2ea9e2, 25 files, also merged in `wip/claude-ops-round3` | Code complete per `docs/reports/OPS_ROUND4_CLOUD_HANDOFF.md`, but **never compiled** (cloud). Answers Fedya's build_v04 feedback items 1–5 | No (main = round 3) | `git merge-tree`: 0 conflicts. Escape_v01 FBX are present locally | **Integrate (B1)** |
| FP hands v01 | `origin/claude/fp-hands-v01` 4ac2a557 | Standalone code + spec only; "Art not started"; hooks §9 not done; compile NOT RUN | No | 0 conflicts | Not finished. Skip (decision D6) |
| Phone spec review / Ops stage-2 spec review | `origin/claude/phone-review`, `origin/claude/ops2-review` (1 doc each) | Docs | n/a | 0 conflicts | Merge docs (B2) |
| G39 work inventory core | `ArtSource/Dev/WorkInventory_staging` (8 src files, 351 pure tests, `handoff/CLAUDE_PORT_G39.md`) | Pure .NET core; Unity adapter, save composition and FishNet not done | No. W85 uses the older `Inventory/Runtime/NetworkInventory` | A competing version of the inventory | Decision D4 |
| Buyers core (sales rules) | `Assets/OnlyVolunteers/Buyers` (BuyerRules/Catalog/Orders/Transactions + JSON data + EditMode tests) | Rules done; **no MonoBehaviour, no scene user** | No | in main | Basis for the money step (D1) |
| Sales / Phone / Work-inventory / Police specs (G36/G41/G39/G42) | `docs/specs/*_2026-10-18_v01.md` | All state "implementation not performed" | – | – | Design only |
| Phone (Tab, Vadim) | `Map/Scripts/GreyboxPhone.cs` + `UI/Phone` | Presentation-only. Messages "CALL BUYER" spawns nobody; Bank has its own placeholder `Cash = 85` | Yes (GreyboxPhone ×1) | – | Already in |
| Police v1 (patrols, chases, wanted level) + crowd witnesses | `Assets/OnlyVolunteers/Police`, `Map/Scripts/Crowd/CrowdWitness.cs` | Worked on v12/v19 maps; data `police_v19_build_v08.asset` | **No**: i10 has `Police` root (PoliceDirector 1, PoliceUnit 4, PoliceOfficer 8); W85 has 0. `W85PlayIntegrator.Carry` omits "Police" | Baker reads `MAP_PLAN_R01_vNN.json` road_graph; W85 has only `roads_v85.json` polylines | Decision D2 |
| ClinicLoop v17 (instant payment, quick save) | `Assets/OnlyVolunteers/Clinic`, `FC_ClinicLoop` in i10 | Superseded by Stage A (D3 removed the drop-off pad) | No | – | Do not revive |
| Network M0/M1 | `docs/specs/NETWORK_MAP_PLAN_v01.md` | Not started (no commits) | – | – | Out of scope |
| Cloud art kits (street/vehicles/landmarks/small props/facade/textures), buddy-v05-lowpoly, cloud/inventory, codex/* | remote branches 1–4 ahead | Already built locally into main (add/add conflicts = same files) or superseded | – | – | Nothing to merge |
| Anim branches (walk/getups/idle-cargo/crowd/escape/escape-v01b) | remote | 0 ahead: already in main | – | – | Done |

## 3. Петля по канону — статус в W85 play

| Step | Status | Evidence (file / class / where it enters the scene) |
|---|---|---|
| Find NPC (district crowds, 37 types) | **Wired** | `CrowdDirector` + `NpcSpawnTables_v01` (TakeFor, CrowdDirector.cs:332); 37 type templates + 40/40 A/B in the scene; integrator §5 `AddTypeTemplates`; `W85CrowdCull`. Elite / Quiet Valley / Tramduro have no crowd routes. Beach/hamlet **placements** (buried + mound, castle, detector, lounger, bodybuilder at the bar) are never spawned: no code reads `NpcSpawnTables.Placements` |
| Stun (Q) | **Wired** | `GreyboxInteractor` ×1, `GreyboxNpc` ×117 |
| Tie / anesthesia / blood | **Wired** | `CaptureFieldKit` added at runtime by `CaptureDirector` (CaptureDirector.cs:92), slot 2. Head bag = stage 2 (CAPTURE D14), missing |
| Load into van | **Wired** | `PhysicsGrabber`/`NetworkGrabber`, `VanCargoSpace` ×1, `CaptureVanCapacity` added at runtime (:105), capacity 3 |
| Drive to base | **Wired** | `Van.prefab` (VanController, VanUpgrades), `VanDriveInput`, `VanCameraRig`; van placed on the base-2 pad by integrator §3. **Bug:** `GreyboxTripMeter` F1–F8 spots are the carried v19 coordinates (playtest note "не нажимать") |
| Base 2, carry to table, cloud, undress | **Wired** | `CaptureDirector` (TablePrefab spawned at TableSpawn), `CaptureTableBridge` (:218). Integrator moves the i10 shed and paint station onto hut `B_02-A-BASE` |
| Operation (straps, cut, organs, suture, death, escape) | **Wired (round 3)**; round 4 not merged | `NetworkOperationTable` via CaptureDirector; round 4 = §2 |
| Corpse bag + water disposal | **Wired** | `CaptureCorpseDisposal` (:88), WaterQuery → W85 WaterData (integrator §6) |
| Organs as items | **Wired** | `OperationPhysicalItem : IPhysicalInventoryItem`, carried by `NetworkInventory` |
| Sale (buyer / phone) | **Missing** | Buyers core has no runtime user. Phone Messages "Scrap Guy" spawns no one |
| Money | **Missing** | `NetworkInventory.ServerAddCash` has **no callers**; the only payer is `ClinicLoop` (not in W85, superseded). Phone Bank has a separate placeholder balance |
| Upgrades (spend money) | **Implemented, not purchasable** | `VanUpgrades` on the Van prefab; free debug keys 7/8/9 (`VanDriveInput.cs:67`); no prices anywhere (economy draft not approved) |
| Police / heat | **Implemented for v19, not wired** | Witness → `RaiseAlert` still fires (no hotspots → "phone" branch, CrowdWalker.cs:868), but no `PoliceDirector`, patrol or units in W85. The G42 zone model is not implemented |
| Save / load (K) | **Wired** | `CaptureDirector` + `W85EditorSaveSlot` |

Playable today: crowd → stun → tie → van → base 2 → table → operation → organ in hand / corpse in river → save. It stops at "organ in hand": no sale, no money, no police.

## 4. План (порядок выполнения)

Sequencing: wait until the other agent has finished `Map_W85_Play_v02` (Unity lock, and the same integrator). Asset-side work (A1–A3) is off-scene and can be done first. Hook every scene change into `W85PlayIntegrator.Make` (or an importer menu) so each map rebuild keeps it. Do not hand-edit the play scene. The map, art, lighting and the TextureTest v07 review are not touched.

### A. Персонажи
- **A1** `ArtSource/.../Types_opt_v01/build_types_opt_v01.py` POOL: add CONSTR_INDIAN 8, CONSTR_MEXICAN 5, CONSTR_UZBEK 5, HAMLET_MUZHIK 1, OLD_POPKING 1, and the 9 import-only types. Run `--types <new ids> --out <fresh dir>`, then copy the new `*_vNN_opt_v01.fbx/.blend` into `Types_opt_v01/` (new names; old reports stay). **safe/reversible**
- **A2** `NpcTypesImportV01.Pool`: bump CONSTR_INDIAN→8, MEXICAN→5, UZBEK→5; add HAMLET_MUZHIK 1, OLD_POPKING 1, and the 9 import-only types (prefabs and presets, no table rows). Run the menu "NPC Types v01: Import…" and check the log for HEAVY / RIG DIFFERS / feet. **safe/reversible**
- **A3** `NpcTypesImportV01.WriteTables`: add MUZHIK to `hamlet`, POPKING to `downtown`, and **remove BAD_ALTGIRL from `rough`** (Vadim TASK-000883). VIP / FBI / ARMY / TRAMDURO / POLICE / HUNTER get no crowd rows. **safe** (follows Vadim's explicit pool)
- **A4** Re-run the play-scene step: the integrator §5 `AddTypeTemplates` picks up the new templates. Smoke test: MUZHIK in the Hamlet, POPKING in Downtown, the new CONSTR in Construction; stun and capture one each. **safe**
- **A5** (after D2) `MapPolicePlacer.Place(buddies)`: pass `[SausageBuddy_POLICE_THIN, SausageBuddy_POLICE_FAT]`. Add a `police` row to `NpcSpawnTables` and have `CrowdDirector.cs:332` pass "police" for `CrowdRole.Police`. **safe once police exists**
- **A6** HUNTER_GRANDPA / FBI / ARMY / VIPs / TRAMDURO: no spawns until their systems exist. **needs Fedya's decision** (D3)

### B. Фичи из веток
- **B1** Merge `origin/claude/ops-round4` (0 conflicts) on a local branch → compile → EditMode (`OperationRound4RulesTests` + round 3) → menus "Integrate escape clips v01" + "Bake Player-Safe Query Meshes (v01)" → manual check from `CAPTURE_DELIVERY_PLAYTEST_v05_RU.md`. **safe/reversible** (branch; revert = drop the merge)
- **B2** Merge the docs-only `claude/phone-review` and `claude/ops2-review`. **safe**
- **B3** FP hands, G39 inventory core, network M0+: not in this pass (D4, D6).

### C. Связка петли (small integration fixes)
- **C1** `W85PlayIntegrator`: rewrite `GreyboxTripMeter.Spots` (F1–F8) to the W85 bases and the van pad from the district data, instead of the v19 coordinates. **safe**
- **C2** `W85PlayIntegrator`: a placement step that spawns `NpcSpawnTables.Placements` as idle `GreyboxNpc`: BEACH_BURIED + SandMound, CASTLE, DETECTOR, SUNBURN on a lounger, BODYBUILDER at the hamlet pull-up bar. Positions come from beach zones (`09e-lounger-*` exist in beach_v85.json); hamlet_v85.json has **no pull-up bar anchor**, so the bodybuilder is skipped and logged. Skip any placement whose zone is missing. **safe** (data already approved)
- **C3** `W85PlayIntegrator`: put the play scene first in Build Settings, so Shift+K "new game" reloads it rather than NetworkTest. **safe/reversible**, but it changes the build scene list. Mention it to Fedya
- **C4** Find the single "missing script" warning that appears on Play (an object created at runtime; FEDYA_TO_VADIM "not investigated"). **safe**
- **C5** Money and sale: minimal "first buyer" at base 2, following SALES SG-D27/D29/D31. A wooden crate by the shed and C01's car outside the base: put an organ on the crate → price from `BuyerCatalog.UnitPrice(kind, tier, …)` → `NetworkInventory.ServerAddCash` → HUD toast. No haggling, no phone flow. **needs Fedya's decision** (D1)
- **C6** Spend money: prices for van upgrade levels + a buy point at base 2, replacing the free 7/8/9 keys. **needs Fedya's decision** (D5; the economy draft is not approved)
- **C7** Police in W85: carry the i10 "Police" root + a new W85 → `PoliceMapData` bake (roads_v85 polylines + Downtown streets + a station from downtown data) + a crowd patrol line. **needs Fedya's (and Vadim's) decision** (D2)
- **C8** Final smoke run with real keys: map loads, move, crowd types visible, one full catch → van → table → organ (→ sale/cash if C5 is approved) → K save → reload; no red console lines.

## 5. Решения для Феди (only real conflicts)

- **D1 Sale and money.** Today the loop ends at "organ in hand". Option A: a minimal first-buyer crate at base 2 (spec SG-D27 "Хутор — ящик у сарая"), with prices from the existing Buyers core and cash into NetworkInventory. Option B: wait for full sales Stage A (SG-D50: C01, meetings, phone, haggling). **Recommend A**: it is small, it reuses approved data and stays inside the spec, and it closes the loop for a playtest.
- **D2 Police in W85.** Police and suspicion are Vadim's area (TASK-000835). Police v1 works only on v19 data, and G42 (zones, hunter grandpa, gangs) is unbuilt. Option A: port Police v1 to W85 now (new baker adapter, a few hours) and wear the new THIN/FAT models. Option B: no police in this build, and say so. **Recommend B for this build, A next**, after Vadim confirms that v1 behaviour is acceptable as the interim before G42.
- **D3 Special characters.** VIPs, FBI, Army, Tramduro and the hunter grandpa have roles, but no systems yet (VIP special orders, Elite gate trap, island, responder AI). **Recommend import + presets + opt meshes only, no spawns.** Optional: show the hunter grandpa as one unique idle NPC in the Hamlet until his AI exists. Is that OK, given that he is capturable as a normal NPC?
- **D4 Inventory versions.** The live `NetworkInventory` is in W85. The G39 ledger core is staged with 351 tests but not integrated. `cloud/inventory` is obsolete. **Recommend keeping the live one for this build; port G39 as its own task.**
- **D5 Upgrade prices.** None exist (economy draft not approved). Keep the debug keys, or approve placeholder prices? **Recommend keeping the debug keys until D1 has run in a playtest.**
- **D6 FP hands.** Code only, no art, hooks not done. **Recommend not integrating now.**
- **Money owner (FYI).** The phone Bank (placeholder $85) and inventory cash are two balances. PHONE_SPEC says "one shared fund". Unify them when D1 lands.
