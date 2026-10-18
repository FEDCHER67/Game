# G39 — Work inventory core, phase 1

Date: 2026-10-18 (Europe/Moscow). Status: **PASS — engine-free implementation and standalone tests**. Unity was not opened, called, or compiled. No writes were made to Assets or ProjectSettings; no git stage, commit or push. Required specs were read, including both final Decisions sections; all remain unchanged. The live buyers Core was read and copied into staging, and its protected hashes remain unchanged.

## Delivered

- **WI-B:** one serialized host ledger, defensive-copy records/definitions/snapshots, all 18 item definitions, immutable extraction provenance through public APIs, organ quality/spoilage/cold chain/packaging, syringe/vial/blood state, donor and special-order lineage keys, corpse interval carryover, stock consumption, split/merge/max-stack enforcement, retired identities, per-player 64-result receipts plus persistent high-water marks, and exact tier-change timestamps. Merged identities and transformed blood portions are tombstoned. `RetireBloodPortion` keeps the reusable syringe. Destroying a cooler spills and warms its contents; impact damage reaches every organ inside it.
- **Fedya decisions:** two-handed cooler with tool/selection lock; kit key cycling and empty hands after the last entry; no simultaneous body hold and tool use; purchased shelf plus two mounts; entire player inventory retained on leave, including selected kit item, held/carry state, cooler contents, fills, provenance and freshness. Absent items cannot be moved, opened, impacted, consumed, confiscated or replicated into the active world. Rejoin restores their remaining durations. The old leave-drop method and behavioural tests are removed. The historical baseline log is retained only as evidence of the original prototype.
- **Containers:** six pockets, one optional kit key inside those six, shelf 12, two one-cooler mounts, cooler 8, powered/unpowered fridge 24, table tray 6, buyer case 8, stash 4, return tray 8. No nested coolers; a cooler can occupy a van mount. Ordinary world cargo remains possible before the upgrade. Additional return trays are created by the meeting lifecycle adapter as needed.
- **Pure intent server:** SelectSlot, Use begin/hold/end, Secondary, Take, Put, PickUp, Drop, Throw, Place, explicit SetOpen, Carry begin/end/throw. Connection ownership, object identity against host-resolved ids, finite data, reach/LOS inputs, source ownership, capacity, camera/input locks, supplies, target rules, press expiry and persistent press ids are validated. NPC tool effects are returned as data for the existing CaptureRules host step. No Unity physics, networking or duplicate patient model is introduced.
- **WI-I pure portion:** v2 inventory fragment with ledger, per-player blocks, activeSlot/kit subselection, presence, receipts, retired ids and plain poses. JSON round trips, pause/resume, save validation and safe repair of team-container slot mismatches. Damaged private inventories fail validation instead of leaking possessions into the world. Legacy conversion preserves organ/blood IDs and poses, maps quality, splits oversized stacks, preserves old blood age, converts table stock/bag masks and reports overflow at the player's position. The file helper creates a byte-exact, create-once `.v1.bak`, refuses overlapping paths/repeated migration, and publishes via flushed `.tmp` → atomic replace with `.bak`.
- **WI-C:** JSON + CSV for all 18 items, RU/EN names and hints, all 31 result/refusal keys, 10 container kinds, quality mapping and explicit tuning drafts. NUnit checks these against the compiled catalog. Head bags stay Stage B data.
- **Buyers copy:** `UnloadItem`, `SetDeliveredCooled`, latch-bearing `LoadItem`, `RemoveItem` with persistent removal tombstones, and team-held registration. `SetItemHolder` and `SetPackaged` support the concrete pickup/packaging consumers. Team holder `@team` never becomes an XP participant. Existing buyers tests run against this copy. The exact patch is `handoff/BUYERS_API_G39.patch`.
- **Pure edge hooks:** `MostValuableOf`/`ConfiscateMostValuable` for arrest; separate `KnockOutHeldItem` drops the held unit and retains the other pockets. Knockout is never used for disconnect.

## Verification and evidence

Original prototype: **37/37 console checks passed before editing** (`evidence/baseline-selftest.txt`). Its behaviours were ported to independent NUnit/console scenarios, with leave-drop replaced by the final persistence decision and the specified 0.6-second impact cooldown.

Final NUnit: **351/351 passed; 0 failed, 0 skipped**. Final console: **RESULT PASS 200/200**. These are two runners over the same inventory scenarios, not additive test counts.

| Group | Cases |
|---|---:|
| Inventory scenarios | 200 |
| New buyers API | 17 |
| Existing buyers regressions | 130 |
| Draft/assembly validation | 4 |

Both runtime assemblies were verified as .NET Standard 2.1 with no Unity/FishNet assembly references. Runtime and runner projects use C# 9 and warnings as errors. Final builds completed without compiler warnings/errors. The exact buyers API patch passed the read-only `git apply --check`; see `evidence/buyers-patch-check.txt`.

Commands, from `C:/Dev/Game`:

```powershell
& .\ArtSource\Dev\WorkInventory_staging\Run-Tests.ps1
& .\ArtSource\Dev\WorkInventory_staging\Run-Mutations.ps1
. .\ArtSource\Dev\WorkInventory_staging\Environment.ps1
dotnet run -c Release --project .\ArtSource\Dev\WorkInventory_staging\selftest
```

`Environment.ps1` redirects CLI state, NuGet packages/caches and temporary files into staging. The final NUnit TRX/log and console output are in `evidence/inventory-final.trx`, `evidence/inventory-final.txt` and `evidence/selftest-final.txt`. The full command/test logs include intermediate runs. One intermediate run after tightening resolved-target validation failed because a carry-lock test omitted its target id; the fixture was corrected to submit a valid target and then exercise the intended hand lock. That failure is retained in `inventory-reviewed.*`.

Five intentional rule mutations were compiled and run. Each produced actual failed assertions, not just compilation failure. Each source was restored in `finally`, verified by SHA-256, then the full restored suite and console suite ran successfully.

| Mutation | Deliberate break | Failed tests | Representative detection |
|---|---|---:|---|
| M1-room-interval | Room loss interval 300 → 301 seconds | 8 | `Spoilage_QueriesAndPackagingNeverRestoreTier` |
| M2-two-hands | Allow slot selection during a two-handed carry | 1 | `Carry_TwoHandsBlockSelectionAndSecondCarry` |
| M3-disconnected-freeze | Let absent inventory spoil | 3 | `Leave_WholeInventoryAndCarriedContentsRemainExact` |
| M4-cold-chain | Mark every case load cooled without checking history | 5 | `ColdChain_StintGap_59,999_0` |
| M5-request-dedup | Bypass duplicate receipts and stale-request guard | 5 | `Receipts_FailuresAreDeduplicated` |

All failing test names and original/restored hashes are in `evidence/mutation-results.json`; each mutation has its own TRX and log. This is a targeted five-rule sanity check, not a comprehensive mutation score.

## Decisions made in this implementation

1. **One quality scale:** inventory and buyers use 1–5. Capture/table grades 0–4 convert once with `Tier.FromCaptureGrade(grade) = grade + 1`; reverse conversion is `tier - 1`. Labels are Damaged/Убитое 20%, Acceptable/Сойдёт 40%, Good/Хорошее 60%, Perfect/Отличное 80%, Perfect+/Идеальное 100%. Price multipliers remain 0.3/1/1.6/2.6/4.2. Invalid grades are rejected, not silently clamped. Percent is a label, not a separate quality variable.
2. **Kit layout:** index 5 (key 6) by default, configurable at player creation, occupies one of the six pockets while nonempty. Provisional internal bound: 12 entries, with ordinary stack caps. Order: ties, anesthesia syringe, blood syringe, empty blood bags, sealed blood bags, body bags, organ pouches, head bags, vials; then empty hands. Same-class ties use definition id then instance id. Organ pouches/vials follow the explicitly requested sequence. New world pickups use ordinary pockets; kit routing is an explicit destination.
3. **Absent-player time:** “restored exactly” means no spoilage, blood expiry, impact cooldown consumption, free cold accumulation or warm-gap consumption while absent. Rejoin rebases active-time anchors by the absence duration; item identities, counts, locations, selection, provenance, tiers, progress and remaining durations are preserved. Extraction game time does not shift. World time and other players' goods continue normally. Closing the whole world adds no elapsed time at all.
4. **Upgrades:** shelf and both mounts use one monotonic purchased upgrade, matching Fedya's default. The core records attachment in a container; physical vehicle motion remains adapter work.
5. **Spoilage/impact presets:** room 300 s, cooler 1500 s, powered fridge paused; minimum cold stint 60 s, maximum warm gap 60 s inclusive; impact speed strictly above 2.4 m/s for organs and 4 m/s for coolers; cooldown 0.6 s. Rejected contacts do not extend the cooldown. Packaging has no spoilage effect. Corpse progress carries the unfinished fraction of the 40-second interval after 45 seconds' grace, with the body's already-degraded tier supplied at extraction.
6. **Tool state:** syringe capacity 3 and injection rate 0.5 units/s match the inspected current OperationTuning; other hold durations follow the spec presets. These are fictional gameplay units. Target consequences and donor portion counts stay in CaptureRules. Blood sale identity is per fill; packaging/discarding/selling retires that portion while retaining the syringe.
7. **Receipt policy:** keep the last 64 results per player and a saved high-water mark forever. A cached retry returns the original result even with another payload; an evicted old id is refused. All intent kinds share that sequence. New connections resume above the high-water and last press id; pending holds are cancelled, not restored.
8. **Migration scope:** the helper writes an inventory fragment to a distinct v2 path so it cannot accidentally overwrite unmodelled NPC/van/funds data. The original complete legacy file is retained byte-for-byte; Claude composes this fragment into the existing world-save transaction. Existing partial table-tool fills remain on the table and are returned in the migration report. Table output positions are preserved; tray proximity is a later spatial adapter operation. Whole stacks are split deterministically; no random migration identities.
9. **Arrest:** compare direct pocket/kit items and the carried unit by placeholder catalog value, settling quality first. The cooler is valued as one equipment unit; if confiscated, its contained goods leave with it. Destruction instead spills contents at its last pose. The separate shared-fund 10% penalty belongs to the economy authority.
10. **State boundary:** core accessors return copies. Atomicity/serialization applies within each core instance. The future WI-J coordinator must serialize and prevalidate transfers against sales, unload before publishing a withdrawal, refresh merchandise projections, and retire successful sales before the next intent. The buyers-copy race tests verify either unload or sale wins, without claiming a completed cross-core/network/disk transaction.

## Acceptance coverage and remaining integration

The pure parts of WI-01 through WI-21 are represented: identity/stack/pocket rules; selection/kit cycling; tool hold, stock, provenance and release rules; spoilage, cold chain, impacts and packaging; purchased storage capacities; pickup/capacity/extraction races; revised leave/rejoin; snapshots; host-only fragment writes; migration; arrest and knockout hooks. WI-17 uses Fedya's final persistence rule, never its superseded drop wording. Snapshot tests check the data required for late join; they do not prove actual replication or privacy filtering in FishNet.

**NOT RUN / later work:** Unity import/EditMode, real UI/input and cameras, physics/LOS calculation, vehicle attachment at 60 km/h, world spawning/despawning, real donor-side tool consequences, cross-core WI-J case/stash/sale coordination, complete world-save composition, and two-process network tests. No subjective feel or visual acceptance is claimed. No scene, prefab, Unity asset or asmdef was created in Assets.

Open design choices for later review: kit capacity/index and optional kit pickup routing; placeholder spoilage/cold-delivery/impact balance; normal supply restock/purchases and table-to-pocket fallback; shelf/cabinet visuals; final item asset/icon authoring. These do not block this engine-free phase. The pure APIs expose the relevant state and explicit refusals rather than inventing UI or shops.

## Claude port note

Target: `Assets/OnlyVolunteers/Items/Core/`, containing the eight staging `src/*.cs` files. Create `OnlyVolunteers.Items.Core.asmdef` with `noEngineReferences: true` and no references. Review/apply `handoff/BUYERS_API_G39.patch` into the existing Buyers/Core; it has not been applied here. Detailed host-input, persistence, item-projection and transaction notes are in `handoff/CLAUDE_PORT_G39.md`.

Standalone test dependencies only, unchanged from the established buyers test tooling: Microsoft.NET.Test.Sdk 17.11.1 ([MIT](https://github.com/microsoft/vstest)), NUnit 3.14.0 ([MIT](https://github.com/nunit/nunit)), NUnit3TestAdapter 4.6.0 ([MIT](https://github.com/nunit/nunit3-vs-adapter)). Restored versions are recorded in project.assets.json under staging. Core projects have no NuGet package dependency. Rollback: do not port the staging files; no Unity package or runtime asset was replaced.

## Exact created/changed file inventory

The companion `ArtSource/Dev/WorkInventory_staging/created-and-changed-files.txt` contains the same exact list below, including generated build/test/cache evidence. It is based on hashes of the initial staging files. Existing unchanged files are excluded; files owned by other workstreams are excluded. All paths are under `C:/Dev/Game`.

851 created/changed files total; 46 authored/copied source, data and handoff files (remaining entries are generated evidence/tooling).

Authored/copied deliverables:

- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Build-Drafts.py`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerCatalog.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerInventoryApi.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerOrders.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerRules.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\Buyers.Copy.csproj`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerState.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerTransactions.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\CatalogChecks.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\CheckSupport.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\IntentChecks.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\PlayerChecks.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\SaveChecks.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\StorageChecks.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\created-and-changed-files.txt`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Environment.ps1`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\handoff\BUYERS_API_G39.patch`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\handoff\CLAUDE_PORT_G39.md`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\NuGet.Config`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Prepare-Handoff.py`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Run-Mutations.ps1`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Run-Tests.ps1`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\Program.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\WorkInventory.SelfTest.csproj`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\InventorySave.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemActions.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemCatalog.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemCoreTypes.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemIntents.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemLedger.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\LegacyMigration.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\PlayerInventory.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\AcceptanceTests.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\buyer_baseline\BuyerNegotiationAndMeetingTests.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\buyer_baseline\BuyerOrderAndTransactionTests.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\buyer_baseline\BuyerPriceAndProgressionTests.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\buyer_baseline\BuyerTestSupport.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\BuyerInventoryApiTests.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\DraftDataTests.cs`
- `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\WorkInventory.Tests.csproj`
- `C:\Dev\Game\docs\drafts\work_inventory\containers_G39.json`
- `C:\Dev\Game\docs\drafts\work_inventory\item_definitions_G39.csv`
- `C:\Dev\Game\docs\drafts\work_inventory\item_definitions_G39.json`
- `C:\Dev\Game\docs\drafts\work_inventory\localization_G39.json`
- `C:\Dev\Game\docs\drafts\work_inventory\quality_and_tuning_G39.json`
- `C:\Dev\Game\docs\reports\WORK_INVENTORY_CORE_G39.md`

Full inventory (including all generated files):

```text
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\.dotnet\.dotnet\10.0.401.aspNetCertificateSentinel
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\.dotnet\.dotnet\10.0.401.dotnetFirstUseSentinel
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\.dotnet\.dotnet\10.0.401.toolpath.sentinel
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Build-Drafts.py
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\bin\Release\netstandard2.1\Buyers.Copy.deps.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\bin\Release\netstandard2.1\Buyers.Copy.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\bin\Release\netstandard2.1\Buyers.Copy.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerCatalog.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerInventoryApi.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerOrders.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerRules.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\Buyers.Copy.csproj
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerState.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\BuyerTransactions.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Buyers.Copy.csproj.nuget.dgspec.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Buyers.Copy.csproj.nuget.g.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Buyers.Copy.csproj.nuget.g.targets
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\project.assets.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\project.nuget.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\Buyers.Copy.AssemblyInfo.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\Buyers.Copy.AssemblyInfoInputs.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\Buyers.Copy.assets.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\Buyers.Copy.csproj.CoreCompileInputs.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\Buyers.Copy.csproj.FileListAbsolute.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\Buyers.Copy.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\Buyers.Copy.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\Buyers.Copy.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\buyers\obj\Release\netstandard2.1\Buyers.Copy.sourcelink.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\CatalogChecks.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\CheckSupport.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\IntentChecks.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\PlayerChecks.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\SaveChecks.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\checks\StorageChecks.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\created-and-changed-files.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Environment.ps1
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\baseline-files.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\baseline-selftest.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\buyers-patch-check.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\inventory-final.trx
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\inventory-final.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\inventory-first.trx
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\inventory-first.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\inventory-premutation.trx
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\inventory-premutation.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\inventory-reviewed.trx
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\inventory-reviewed.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M1-room-interval.trx
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M1-room-interval.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M2-two-hands.trx
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M2-two-hands.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M3-disconnected-freeze.trx
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M3-disconnected-freeze.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M4-cold-chain.trx
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M4-cold-chain.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M5-request-dedup.trx
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\M5-request-dedup.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\mutation-results.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\protected-inputs.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\selftest-final.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\selftest-first.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\evidence\verification-summary.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\handoff\BUYERS_API_G39.patch
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\handoff\CLAUDE_PORT_G39.md
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\http-cache\670c1461c29885f9aa22c281d8b7da90845b38e4$ps_api.nuget.org_v3_index.json\service_index.dat
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\http-cache\670c1461c29885f9aa22c281d8b7da90845b38e4$ps_api.nuget.org_v3_index.json\vuln_data_base.dat
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\http-cache\670c1461c29885f9aa22c281d8b7da90845b38e4$ps_api.nuget.org_v3_index.json\vuln_data_update.dat
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\http-cache\670c1461c29885f9aa22c281d8b7da90845b38e4$ps_api.nuget.org_v3_index.json\vuln_index.dat
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\NuGet.Config
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\amd64\CodeCoverage.exe
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\amd64\covrun64.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\amd64\msdia140.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\amd64\VanguardInstrumentationProfiler_x64.config
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\arm64\covrunarm64.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\arm64\msdia140.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\arm64\VanguardInstrumentationProfiler_arm64.config
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\CodeCoverage.config
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\CodeCoverage.exe
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\codecoveragemessages.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\coreclr\Microsoft.VisualStudio.CodeCoverage.Shim.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\covrun32.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\msdia140.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\CodeCoverage\VanguardInstrumentationProfiler_x86.config
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\cs\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\de\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\es\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\fr\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\alpine\x64\libCoverageInstrumentationMethod.so
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\alpine\x64\libInstrumentationEngine.so
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\alpine\x64\VanguardInstrumentationProfiler_x64.config
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\arm64\MicrosoftInstrumentationEngine_arm64.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\macos\x64\libCoverageInstrumentationMethod.dylib
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\macos\x64\libInstrumentationEngine.dylib
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\macos\x64\VanguardInstrumentationProfiler_x64.config
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\ubuntu\x64\libCoverageInstrumentationMethod.so
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\ubuntu\x64\libInstrumentationEngine.so
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\ubuntu\x64\VanguardInstrumentationProfiler_x64.config
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\x64\MicrosoftInstrumentationEngine_x64.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\InstrumentationEngine\x86\MicrosoftInstrumentationEngine_x86.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\it\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\ja\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\ko\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Microsoft.CodeCoverage.Core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Microsoft.CodeCoverage.Instrumentation.Core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Microsoft.CodeCoverage.Instrumentation.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Microsoft.CodeCoverage.Interprocess.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Microsoft.CodeCoverage.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Microsoft.CodeCoverage.targets
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Microsoft.DiaSymReader.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Microsoft.VisualStudio.TraceDataCollector.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Mono.Cecil.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Mono.Cecil.Pdb.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\Mono.Cecil.Rocks.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\pl\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\pt-BR\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\ru\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\ThirdPartyNotices.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\tr\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\zh-Hans\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\build\netstandard2.0\zh-Hant\Microsoft.VisualStudio.TraceDataCollector.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\Icon.png
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\lib\net462\Microsoft.VisualStudio.CodeCoverage.Shim.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\lib\netcoreapp3.1\Microsoft.VisualStudio.CodeCoverage.Shim.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\microsoft.codecoverage.17.11.1.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\microsoft.codecoverage.17.11.1.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\microsoft.codecoverage.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.codecoverage\17.11.1\ThirdPartyNotices.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\build\net462\Microsoft.NET.Test.Sdk.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\build\net462\Microsoft.NET.Test.Sdk.targets
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\build\netcoreapp3.1\Microsoft.NET.Test.Sdk.Program.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\build\netcoreapp3.1\Microsoft.NET.Test.Sdk.Program.fs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\build\netcoreapp3.1\Microsoft.NET.Test.Sdk.Program.vb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\build\netcoreapp3.1\Microsoft.NET.Test.Sdk.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\build\netcoreapp3.1\Microsoft.NET.Test.Sdk.targets
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\buildMultiTargeting\Microsoft.NET.Test.Sdk.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\Icon.png
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\lib\net462\_._
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\lib\netcoreapp3.1\_._
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\microsoft.net.test.sdk.17.11.1.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\microsoft.net.test.sdk.17.11.1.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.net.test.sdk\17.11.1\microsoft.net.test.sdk.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.netcore.platforms\1.1.0\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.netcore.platforms\1.1.0\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.netcore.platforms\1.1.0\dotnet_library_license.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.netcore.platforms\1.1.0\lib\netstandard1.0\_._
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.netcore.platforms\1.1.0\microsoft.netcore.platforms.1.1.0.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.netcore.platforms\1.1.0\microsoft.netcore.platforms.1.1.0.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.netcore.platforms\1.1.0\microsoft.netcore.platforms.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.netcore.platforms\1.1.0\runtime.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.netcore.platforms\1.1.0\ThirdPartyNotices.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\Icon.png
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\cs\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\cs\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\de\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\de\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\es\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\es\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\fr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\fr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\it\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\it\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\ja\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\ja\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\ko\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\ko\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\Microsoft.TestPlatform.CoreUtilities.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\Microsoft.TestPlatform.PlatformAbstractions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\Microsoft.VisualStudio.TestPlatform.ObjectModel.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\pl\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\pl\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\pt-BR\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\pt-BR\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\ru\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\ru\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\tr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\tr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\zh-Hans\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\zh-Hans\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\zh-Hant\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\net462\zh-Hant\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\cs\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\cs\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\de\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\de\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\es\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\es\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\fr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\fr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\it\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\it\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\ja\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\ja\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\ko\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\ko\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\Microsoft.TestPlatform.CoreUtilities.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\Microsoft.TestPlatform.PlatformAbstractions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\Microsoft.VisualStudio.TestPlatform.ObjectModel.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\pl\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\pl\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\pt-BR\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\pt-BR\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\ru\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\ru\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\tr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\tr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\zh-Hans\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\zh-Hans\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\zh-Hant\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netcoreapp3.1\zh-Hant\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\cs\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\cs\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\de\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\de\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\es\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\es\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\fr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\fr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\it\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\it\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\ja\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\ja\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\ko\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\ko\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\Microsoft.TestPlatform.CoreUtilities.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\Microsoft.TestPlatform.PlatformAbstractions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\Microsoft.VisualStudio.TestPlatform.ObjectModel.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\pl\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\pl\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\pt-BR\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\pt-BR\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\ru\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\ru\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\tr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\tr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\zh-Hans\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\zh-Hans\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\zh-Hant\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\lib\netstandard2.0\zh-Hant\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\microsoft.testplatform.objectmodel.17.11.1.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\microsoft.testplatform.objectmodel.17.11.1.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.objectmodel\17.11.1\microsoft.testplatform.objectmodel.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\build\netcoreapp3.1\Microsoft.TestPlatform.TestHost.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\build\netcoreapp3.1\x64\testhost.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\build\netcoreapp3.1\x64\testhost.exe
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\build\netcoreapp3.1\x86\testhost.x86.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\build\netcoreapp3.1\x86\testhost.x86.exe
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\Icon.png
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\net462\_._
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\cs\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\cs\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\cs\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\de\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\de\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\de\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\es\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\es\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\es\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\fr\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\fr\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\fr\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\it\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\it\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\it\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\ja\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\ja\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\ja\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\ko\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\ko\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\ko\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\Microsoft.TestPlatform.CommunicationUtilities.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\Microsoft.TestPlatform.CoreUtilities.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\Microsoft.TestPlatform.CrossPlatEngine.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\Microsoft.TestPlatform.PlatformAbstractions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\Microsoft.TestPlatform.Utilities.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\Microsoft.VisualStudio.TestPlatform.Common.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\Microsoft.VisualStudio.TestPlatform.ObjectModel.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\pl\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\pl\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\pl\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\pt-BR\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\pt-BR\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\pt-BR\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\ru\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\ru\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\ru\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\testhost.deps.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\testhost.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\tr\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\tr\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\tr\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\x64\msdia140.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\x86\msdia140.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\zh-Hans\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\zh-Hans\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\zh-Hans\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\zh-Hant\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\zh-Hant\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\lib\netcoreapp3.1\zh-Hant\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\microsoft.testplatform.testhost.17.11.1.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\microsoft.testplatform.testhost.17.11.1.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\microsoft.testplatform.testhost.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\microsoft.testplatform.testhost\17.11.1\ThirdPartyNotices.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\NETStandard.Library.targets
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\NETStandard.Library.targets
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\Microsoft.Win32.Primitives.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\mscorlib.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\netstandard.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\netstandard.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.AppContext.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Collections.Concurrent.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Collections.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Collections.NonGeneric.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Collections.Specialized.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.ComponentModel.Composition.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.ComponentModel.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.ComponentModel.EventBasedAsync.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.ComponentModel.Primitives.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.ComponentModel.TypeConverter.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Console.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Data.Common.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Data.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Diagnostics.Contracts.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Diagnostics.Debug.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Diagnostics.FileVersionInfo.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Diagnostics.Process.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Diagnostics.StackTrace.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Diagnostics.TextWriterTraceListener.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Diagnostics.Tools.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Diagnostics.TraceSource.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Diagnostics.Tracing.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Drawing.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Drawing.Primitives.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Dynamic.Runtime.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Globalization.Calendars.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Globalization.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Globalization.Extensions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.Compression.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.Compression.FileSystem.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.Compression.ZipFile.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.FileSystem.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.FileSystem.DriveInfo.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.FileSystem.Primitives.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.FileSystem.Watcher.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.IsolatedStorage.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.MemoryMappedFiles.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.Pipes.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.IO.UnmanagedMemoryStream.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Linq.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Linq.Expressions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Linq.Parallel.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Linq.Queryable.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.Http.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.NameResolution.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.NetworkInformation.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.Ping.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.Primitives.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.Requests.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.Security.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.Sockets.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.WebHeaderCollection.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.WebSockets.Client.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Net.WebSockets.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Numerics.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.ObjectModel.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Reflection.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Reflection.Extensions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Reflection.Primitives.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Resources.Reader.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Resources.ResourceManager.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Resources.Writer.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.CompilerServices.VisualC.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.Extensions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.Handles.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.InteropServices.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.InteropServices.RuntimeInformation.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.Numerics.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.Serialization.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.Serialization.Formatters.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.Serialization.Json.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.Serialization.Primitives.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Runtime.Serialization.Xml.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Security.Claims.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Security.Cryptography.Algorithms.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Security.Cryptography.Csp.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Security.Cryptography.Encoding.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Security.Cryptography.Primitives.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Security.Cryptography.X509Certificates.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Security.Principal.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Security.SecureString.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.ServiceModel.Web.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Text.Encoding.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Text.Encoding.Extensions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Text.RegularExpressions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Threading.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Threading.Overlapped.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Threading.Tasks.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Threading.Tasks.Parallel.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Threading.Thread.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Threading.ThreadPool.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Threading.Timer.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Transactions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.ValueTuple.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Web.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Windows.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Xml.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Xml.Linq.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Xml.ReaderWriter.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Xml.Serialization.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Xml.XDocument.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Xml.XmlDocument.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Xml.XmlSerializer.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Xml.XPath.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\build\netstandard2.0\ref\System.Xml.XPath.XDocument.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\lib\netstandard1.0\_._
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\LICENSE.TXT
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\netstandard.library.2.0.0.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\netstandard.library.2.0.0.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\netstandard.library.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\netstandard.library\2.0.0\THIRD-PARTY-NOTICES.TXT
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\net20\Newtonsoft.Json.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\net20\Newtonsoft.Json.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\net35\Newtonsoft.Json.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\net35\Newtonsoft.Json.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\net40\Newtonsoft.Json.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\net40\Newtonsoft.Json.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\net45\Newtonsoft.Json.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\net45\Newtonsoft.Json.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\netstandard1.0\Newtonsoft.Json.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\netstandard1.0\Newtonsoft.Json.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\netstandard1.3\Newtonsoft.Json.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\netstandard1.3\Newtonsoft.Json.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\netstandard2.0\Newtonsoft.Json.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\lib\netstandard2.0\Newtonsoft.Json.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\LICENSE.md
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\newtonsoft.json.13.0.1.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\newtonsoft.json.13.0.1.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\newtonsoft.json.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\newtonsoft.json\13.0.1\packageIcon.png
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\net462\nunit.engine.api.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\net462\nunit.engine.core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\net462\nunit.engine.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\net462\NUnit3.TestAdapter.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\net462\NUnit3.TestAdapter.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\net462\NUnit3TestAdapter.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\net462\testcentric.engine.metadata.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\netcoreapp3.1\nunit.engine.api.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\netcoreapp3.1\nunit.engine.core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\netcoreapp3.1\nunit.engine.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\netcoreapp3.1\NUnit3.TestAdapter.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\netcoreapp3.1\NUnit3.TestAdapter.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\netcoreapp3.1\NUnit3TestAdapter.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\build\netcoreapp3.1\testcentric.engine.metadata.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\docs\README.md
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\nunit3testadapter.4.6.0.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\nunit3testadapter.4.6.0.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\nunit3testadapter.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit3testadapter\4.6.0\nunit_256.png
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\build\NUnit.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\CHANGES.md
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\icon.png
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\lib\net35\nunit.framework.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\lib\net35\nunit.framework.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\lib\net40\nunit.framework.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\lib\net40\nunit.framework.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\lib\net45\nunit.framework.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\lib\net45\nunit.framework.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\lib\netstandard2.0\nunit.framework.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\lib\netstandard2.0\nunit.framework.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\LICENSE.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\NOTICES.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\nunit.3.14.0.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\nunit.3.14.0.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\nunit.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\nunit\3.14.0\README.md
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\.nupkg.metadata
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\.signature.p7s
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\lib\netstandard1.1\System.Reflection.Metadata.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\lib\netstandard1.1\System.Reflection.Metadata.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\lib\netstandard2.0\System.Reflection.Metadata.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\lib\netstandard2.0\System.Reflection.Metadata.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\lib\portable-net45+win8\System.Reflection.Metadata.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\lib\portable-net45+win8\System.Reflection.Metadata.xml
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\LICENSE.TXT
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\system.reflection.metadata.1.6.0.nupkg
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\system.reflection.metadata.1.6.0.nupkg.sha512
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\system.reflection.metadata.nuspec
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\THIRD-PARTY-NOTICES.TXT
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\useSharedDesignerContext.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\packages\system.reflection.metadata\1.6.0\version.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Prepare-Handoff.py
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Run-Mutations.ps1
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\Run-Tests.ps1
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\bin\Release\net8.0\WorkInventory.Core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\bin\Release\net8.0\WorkInventory.Core.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\bin\Release\net8.0\WorkInventory.SelfTest.deps.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\bin\Release\net8.0\WorkInventory.SelfTest.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\bin\Release\net8.0\WorkInventory.SelfTest.exe
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\bin\Release\net8.0\WorkInventory.SelfTest.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\bin\Release\net8.0\WorkInventory.SelfTest.runtimeconfig.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\project.assets.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\project.nuget.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\.NETCoreApp,Version=v8.0.AssemblyAttributes.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\apphost.exe
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\ref\WorkInventory.SelfTest.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\refint\WorkInventory.SelfTest.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInve.F008A8C8.Up2Date
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.AssemblyInfo.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.AssemblyInfoInputs.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.assets.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.csproj.AssemblyReference.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.csproj.CoreCompileInputs.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.csproj.FileListAbsolute.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.genruntimeconfig.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\Release\net8.0\WorkInventory.SelfTest.sourcelink.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\WorkInventory.SelfTest.csproj.nuget.dgspec.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\WorkInventory.SelfTest.csproj.nuget.g.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\obj\WorkInventory.SelfTest.csproj.nuget.g.targets
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\Program.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest\WorkInventory.SelfTest.csproj
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\bin\Release\netstandard2.1\WorkInventory.Core.deps.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\bin\Release\netstandard2.1\WorkInventory.Core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\bin\Release\netstandard2.1\WorkInventory.Core.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\InventorySave.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemActions.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemCatalog.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemCoreTypes.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemIntents.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\ItemLedger.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\LegacyMigration.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\project.assets.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\project.nuget.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\WorkInventory.Core.AssemblyInfo.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\WorkInventory.Core.AssemblyInfoInputs.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\WorkInventory.Core.assets.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\WorkInventory.Core.csproj.CoreCompileInputs.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\WorkInventory.Core.csproj.FileListAbsolute.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\WorkInventory.Core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\WorkInventory.Core.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\WorkInventory.Core.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\Release\netstandard2.1\WorkInventory.Core.sourcelink.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\WorkInventory.Core.csproj.nuget.dgspec.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\WorkInventory.Core.csproj.nuget.g.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\obj\WorkInventory.Core.csproj.nuget.g.targets
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\src\PlayerInventory.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\AcceptanceTests.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\.msCoverageSourceRootsMapping_WorkInventory.Tests
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Buyers.Copy.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Buyers.Copy.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\cs\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\cs\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\cs\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\cs\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\cs\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\de\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\de\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\de\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\de\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\de\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\es\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\es\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\es\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\es\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\es\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\fr\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\fr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\fr\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\fr\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\fr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\it\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\it\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\it\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\it\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\it\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ja\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ja\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ja\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ja\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ja\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ko\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ko\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ko\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ko\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ko\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Microsoft.TestPlatform.CommunicationUtilities.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Microsoft.TestPlatform.CoreUtilities.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Microsoft.TestPlatform.CrossPlatEngine.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Microsoft.TestPlatform.PlatformAbstractions.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Microsoft.TestPlatform.Utilities.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Microsoft.VisualStudio.CodeCoverage.Shim.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Microsoft.VisualStudio.TestPlatform.Common.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Microsoft.VisualStudio.TestPlatform.ObjectModel.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\Newtonsoft.Json.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\nunit.engine.api.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\nunit.engine.core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\nunit.engine.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\nunit.framework.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\NUnit3.TestAdapter.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\NUnit3.TestAdapter.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pl\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pl\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pl\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pl\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pl\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pt-BR\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pt-BR\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pt-BR\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pt-BR\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\pt-BR\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ru\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ru\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ru\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ru\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\ru\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\testcentric.engine.metadata.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\testhost.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\testhost.exe
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\tr\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\tr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\tr\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\tr\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\tr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\WorkInventory.Core.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\WorkInventory.Core.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\WorkInventory.Tests.deps.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\WorkInventory.Tests.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\WorkInventory.Tests.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\WorkInventory.Tests.runtimeconfig.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hans\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hans\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hans\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hans\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hans\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hant\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hant\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hant\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hant\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\bin\Release\net8.0\zh-Hant\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\buyer_baseline\BuyerNegotiationAndMeetingTests.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\buyer_baseline\BuyerOrderAndTransactionTests.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\buyer_baseline\BuyerPriceAndProgressionTests.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\buyer_baseline\BuyerTestSupport.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\BuyerInventoryApiTests.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\DraftDataTests.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\project.assets.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\project.nuget.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\.NETCoreApp,Version=v8.0.AssemblyAttributes.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\ref\WorkInventory.Tests.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\refint\WorkInventory.Tests.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInve.646F042C.Up2Date
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.AssemblyInfo.cs
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.AssemblyInfoInputs.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.assets.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.csproj.AssemblyReference.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.csproj.CoreCompileInputs.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.csproj.FileListAbsolute.txt
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.dll
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.genruntimeconfig.cache
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.pdb
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\Release\net8.0\WorkInventory.Tests.sourcelink.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\WorkInventory.Tests.csproj.nuget.dgspec.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\WorkInventory.Tests.csproj.nuget.g.props
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\obj\WorkInventory.Tests.csproj.nuget.g.targets
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tests\WorkInventory.Tests.csproj
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\00cecc560bc8447098a8edbd5ab74367\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\00cecc560bc8447098a8edbd5ab74367\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\01105deca9b640d29e741690a0ed24aa\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\01105deca9b640d29e741690a0ed24aa\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\0136615b0d4e478582908ccebb717a7d\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\0136615b0d4e478582908ccebb717a7d\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\10432cebbd354f05b61d62acc810a182\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\10432cebbd354f05b61d62acc810a182\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\10c0a21160994d0ea6694c417b320eed\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\10c0a21160994d0ea6694c417b320eed\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\1165533ee1d84f93b801a3351f5e8f07\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\1165533ee1d84f93b801a3351f5e8f07\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\1165533ee1d84f93b801a3351f5e8f07\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\16483aa13a5943db848b730e5262cb01\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\16483aa13a5943db848b730e5262cb01\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\16483aa13a5943db848b730e5262cb01\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\17b247f25ee64620b64c28e5fe6a229d\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\17b247f25ee64620b64c28e5fe6a229d\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\1d8a373d637d4c24a5aea11beb20d9c1\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\1d8a373d637d4c24a5aea11beb20d9c1\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\21cfeb568aba431199f907006f230f5d\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\21cfeb568aba431199f907006f230f5d\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\22937075810145c09ffcb9f9eac57f50\original.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\25380f2750ec466cb0a3330941981587\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\25380f2750ec466cb0a3330941981587\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\2724ddddc8464d77b25f5621432e2508\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\2724ddddc8464d77b25f5621432e2508\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\286bfdcb55014727b6f1b358c8a6dde5\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\286bfdcb55014727b6f1b358c8a6dde5\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\286bfdcb55014727b6f1b358c8a6dde5\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\2a4cfde663d0401a9d495b7d75da097c\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\2a4cfde663d0401a9d495b7d75da097c\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\2a98d97554034ef9ae5a3dbd9f232183\original.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\2d83151571464e16845657b2e698f658\original.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\305ac7638b474cbba6d56aba78fc6a51\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\305ac7638b474cbba6d56aba78fc6a51\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\374e7a3dad094855b53d5bf9ed20aa47\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\374e7a3dad094855b53d5bf9ed20aa47\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\374e7a3dad094855b53d5bf9ed20aa47\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\3ae0d86f3fb34b3e8ca1ec6cc6380b96\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\3ae0d86f3fb34b3e8ca1ec6cc6380b96\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\3ae0d86f3fb34b3e8ca1ec6cc6380b96\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\3c4e75ade1b54fdab25d10ec7f82422f\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\3c4e75ade1b54fdab25d10ec7f82422f\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\3ca6a0a31a934588bd948166a1dda570\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\3ca6a0a31a934588bd948166a1dda570\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\44245b6a7c0d4ca1a074522ec02165ca\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\44245b6a7c0d4ca1a074522ec02165ca\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\44245b6a7c0d4ca1a074522ec02165ca\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\4ee15e34197845e0ac3d8976a17bcfab\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\4ee15e34197845e0ac3d8976a17bcfab\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\50864aaf82d644dfbd30360e3139a38c\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\50864aaf82d644dfbd30360e3139a38c\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\567c76a8a18a419bb177f214a162f017\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\567c76a8a18a419bb177f214a162f017\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\5be297c5efb94d1fb49f8b988dd40747\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\5be297c5efb94d1fb49f8b988dd40747\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\5be297c5efb94d1fb49f8b988dd40747\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\68f9c930048d40f8993ea9081396ad68\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\68f9c930048d40f8993ea9081396ad68\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\68f9c930048d40f8993ea9081396ad68\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\6ed73bea5ba440f4890f383243697b3d\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\6ed73bea5ba440f4890f383243697b3d\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\7033cefb76ea48a3b7b9a8695d2ded0e\original.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\73bb546c47b5450a87f30c05fdd90598\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\73bb546c47b5450a87f30c05fdd90598\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\7fcd7ddc124d43c191e368e9284105c2\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\7fcd7ddc124d43c191e368e9284105c2\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\7fcd7ddc124d43c191e368e9284105c2\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\804f431f6fa2445c8e039eeed502c8a1\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\804f431f6fa2445c8e039eeed502c8a1\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\81862f14f204406dbacefcf5ad4a4378\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\81862f14f204406dbacefcf5ad4a4378\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\84f55a726c1143cd8472a89767574681\original.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\859f88d3959049feb20da46fd0a076ce\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\859f88d3959049feb20da46fd0a076ce\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\8e076c87c2994bf3b23052d7ed9b98a4\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\8e076c87c2994bf3b23052d7ed9b98a4\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\95396b4303714ed4b5d4f5aef470e59b\original.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\9821ab419fc643b9b6bb8c03b58c1985\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\9821ab419fc643b9b6bb8c03b58c1985\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\9821ab419fc643b9b6bb8c03b58c1985\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\9a2eff8f49b241c8b8d4a8b18a454501\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\9a2eff8f49b241c8b8d4a8b18a454501\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\9a7facdd2f254d57b058bafce442a762\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\9a7facdd2f254d57b058bafce442a762\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a0c6d514497a4588a92399b3b8d32148\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a0c6d514497a4588a92399b3b8d32148\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a0c6d514497a4588a92399b3b8d32148\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a6af24dc16664cd58d4626561cdeb250\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a6af24dc16664cd58d4626561cdeb250\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a8e0317480b2440c8da2068ab2402ddf\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a8e0317480b2440c8da2068ab2402ddf\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a8e0317480b2440c8da2068ab2402ddf\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a9c3278a26324315b4ebcbd549d2ddf6\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\a9c3278a26324315b4ebcbd549d2ddf6\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\afcf6be079da481089ce7180c488dc71\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\afcf6be079da481089ce7180c488dc71\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\afcf6be079da481089ce7180c488dc71\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\b9a5e21f2c8044f3a60409a3d0f36549\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\b9a5e21f2c8044f3a60409a3d0f36549\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\c0fed7b93c2940cdbef93fd2f58bdac9\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\c0fed7b93c2940cdbef93fd2f58bdac9\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\c6da515d9ed24dd7b359e5633288645a\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\c6da515d9ed24dd7b359e5633288645a\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\c6da515d9ed24dd7b359e5633288645a\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\cf50637ddb3a40b39fdfed3eb7b4024d\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\cf50637ddb3a40b39fdfed3eb7b4024d\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\d420a46e03a343e3a4a16c1ff3f3f4ca\old.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\d420a46e03a343e3a4a16c1ff3f3f4ca\old.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\dac38b4706d24c05961074eda130ab38\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\dac38b4706d24c05961074eda130ab38\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\dfc3ded6a5b540a3ab9741c69791dd19\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\dfc3ded6a5b540a3ab9741c69791dd19\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\e37ff3e2e4dd47fc89f4379bd89871b7\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\e37ff3e2e4dd47fc89f4379bd89871b7\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\e6c64e4cd59e4118ab7a3a9189a364c7\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\e6c64e4cd59e4118ab7a3a9189a364c7\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\e6c64e4cd59e4118ab7a3a9189a364c7\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\e92d7dc75f094ebb9bc14d109fa3a98a\original.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\eb8d4a1e6dcc433a84ac934ab467e472\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\eb8d4a1e6dcc433a84ac934ab467e472\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\eb8d4a1e6dcc433a84ac934ab467e472\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\f1a336a9abb84f539d4bf30db6096350\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\f1a336a9abb84f539d4bf30db6096350\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\f1a336a9abb84f539d4bf30db6096350\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\f3bcaf66c2a8463ba1b3f06f05b38a93\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\f3bcaf66c2a8463ba1b3f06f05b38a93\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\f5c6af7327ba42619c367befc4e17a59\capture_stageA_v01.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\f5c6af7327ba42619c367befc4e17a59\capture_stageA_v01.v1.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\f5c6af7327ba42619c367befc4e17a59\inventory_v2.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\fda387c1864645e88d5be825ea447c1f\inventory.json
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\fda387c1864645e88d5be825ea447c1f\inventory.json.bak
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_14436_20261018_172518_120.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_17668_20261018_165938_351.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_17668_20261018_165938_598.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_23616_20261018_172520_481.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_23760_20261018_173239_624.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_24836_20261018_173237_472.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_24916_20261018_172516_262.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_27184_20261018_173243_858.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_28716_20261018_172512_188.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_31768_20261018_172510_310.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_33888_20261018_171028_733.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_34440_20261018_173245_757.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_37024_20261018_173250_001.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_37548_20261018_171733_098.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_38168_20261018_172508_339.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_38976_20261018_170847_512.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_39300_20261018_172514_184.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_39356_20261018_173241_779.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_39652_20261018_172331_246.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_40876_20261018_172413_961.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_41812_20261018_171922_117.log
C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp\Microsoft.NET.Workload_4308_20261018_173247_683.log
C:\Dev\Game\docs\drafts\work_inventory\containers_G39.json
C:\Dev\Game\docs\drafts\work_inventory\item_definitions_G39.csv
C:\Dev\Game\docs\drafts\work_inventory\item_definitions_G39.json
C:\Dev\Game\docs\drafts\work_inventory\localization_G39.json
C:\Dev\Game\docs\drafts\work_inventory\quality_and_tuning_G39.json
C:\Dev\Game\docs\reports\WORK_INVENTORY_CORE_G39.md
```
