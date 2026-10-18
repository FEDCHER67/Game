"""Build exact API patch, scope verification, report and complete file inventory from local evidence."""
import difflib
import hashlib
import json
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

game = Path('C:/Dev/Game')
stage = game / 'ArtSource/Dev/WorkInventory_staging'
drafts = game / 'docs/drafts/work_inventory'
report = game / 'docs/reports/WORK_INVENTORY_CORE_G39.md'
manifest = stage / 'created-and-changed-files.txt'
handoff = stage / 'handoff'
handoff.mkdir(exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

protected = json.loads((stage / 'evidence/protected-inputs.json').read_text(encoding='utf-8-sig'))
protected_results = [{'path': p, 'unchanged': sha(Path(p)) == h} for p, h in protected.items()]
assert all(p['unchanged'] for p in protected_results), 'Protected reference changed; inspect before publishing the report'
patch = []
for name in ['BuyerRules.cs', 'BuyerState.cs', 'BuyerInventoryApi.cs']:
    old = game / 'Assets/OnlyVolunteers/Buyers/Core' / name
    new = stage / 'buyers' / name
    path = 'Assets/OnlyVolunteers/Buyers/Core/' + name
    patch.extend(difflib.unified_diff(old.read_text(encoding='utf-8-sig').splitlines(True) if old.exists() else [],
                                    new.read_text(encoding='utf-8-sig').splitlines(True),
                                    fromfile='a/' + path if old.exists() else '/dev/null', tofile='b/' + path))
(handoff / 'BUYERS_API_G39.patch').write_bytes(''.join(patch).encode('utf-8'))
patch_check = subprocess.run(['git', 'apply', '--check', '--', str(handoff / 'BUYERS_API_G39.patch')], cwd=game, capture_output=True, text=True)
(stage / 'evidence/buyers-patch-check.txt').write_text(
    'Command: git apply --check -- ArtSource/Dev/WorkInventory_staging/handoff/BUYERS_API_G39.patch\n'
    + f'Exit code: {patch_check.returncode}\n' + patch_check.stdout + patch_check.stderr
    + ('PASS: the exact patch applies cleanly; Assets was not modified.\n' if patch_check.returncode == 0 else ''), encoding='utf-8')
assert patch_check.returncode == 0, patch_check.stderr

ns = {'t': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
trx = ET.parse(stage / 'evidence/inventory-final.trx').getroot()
counters = trx.find('t:ResultSummary/t:Counters', ns).attrib
assert counters['failed'] == '0' and counters['passed'] == counters['total']
classes = {u.attrib['id']: u.find('t:TestMethod', ns).attrib['className'] for u in trx.findall('t:TestDefinitions/t:UnitTest', ns)}
groups = {'Inventory scenarios': 0, 'New buyers API': 0, 'Existing buyers regressions': 0, 'Draft/assembly validation': 0}
for test in trx.findall('t:Results/t:UnitTestResult', ns):
    cls = classes[test.attrib['testId']]
    key = 'Inventory scenarios' if 'AcceptanceTests' in cls else 'New buyers API' if 'BuyerInventoryApiTests' in cls else 'Draft/assembly validation' if 'DraftDataTests' in cls else 'Existing buyers regressions'
    groups[key] += 1
mutations = json.loads((stage / 'evidence/mutation-results.json').read_text(encoding='utf-8-sig'))
assert len(mutations) == 5 and all(m['Failed'] > 0 and m['OriginalHash'] == m['RestoredHash'] == sha(stage / m['Source']) for m in mutations)
console = (stage / 'evidence/selftest-final.txt').read_text(encoding='utf-8-sig').strip().splitlines()[-1]
assert console == f"RESULT PASS {groups['Inventory scenarios']}/{groups['Inventory scenarios']}"

verification = {
    'date': '2026-10-18 Europe/Moscow', 'testCounters': counters, 'testGroups': groups,
    'console': console, 'mutationsCaught': len(mutations), 'protectedInputs': protected_results,
    'buyersPatchCheck': 'PASS: git apply --check (read-only)',
    'runtimeSourceHashes': {str(p): sha(p) for folder in ['src', 'buyers'] for p in (stage / folder).glob('*.cs')},
    'scope': 'All task-authored files and command-managed caches are inside C:/Dev/Game. No Unity tool invoked. No commits.'
}
(stage / 'evidence/verification-summary.json').write_text(json.dumps(verification, indent=2) + '\n', encoding='utf-8')

report_body = f'''# G39 — Work inventory core, phase 1

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

Final NUnit: **{counters['passed']}/{counters['total']} passed; 0 failed, 0 skipped**. Final console: **{console}**. These are two runners over the same inventory scenarios, not additive test counts.

| Group | Cases |
|---|---:|
''' + ''.join(f'| {name} | {count} |\n' for name, count in groups.items()) + '''
Both runtime assemblies were verified as .NET Standard 2.1 with no Unity/FishNet assembly references. Runtime and runner projects use C# 9 and warnings as errors. Final builds completed without compiler warnings/errors. The exact buyers API patch passed the read-only `git apply --check`; see `evidence/buyers-patch-check.txt`.

Commands, from `C:/Dev/Game`:

```powershell
& .\\ArtSource\\Dev\\WorkInventory_staging\\Run-Tests.ps1
& .\\ArtSource\\Dev\\WorkInventory_staging\\Run-Mutations.ps1
. .\\ArtSource\\Dev\\WorkInventory_staging\\Environment.ps1
dotnet run -c Release --project .\\ArtSource\\Dev\\WorkInventory_staging\\selftest
```

`Environment.ps1` redirects CLI state, NuGet packages/caches and temporary files into staging. The final NUnit TRX/log and console output are in `evidence/inventory-final.trx`, `evidence/inventory-final.txt` and `evidence/selftest-final.txt`. The full command/test logs include intermediate runs. One intermediate run after tightening resolved-target validation failed because a carry-lock test omitted its target id; the fixture was corrected to submit a valid target and then exercise the intended hand lock. That failure is retained in `inventory-reviewed.*`.

Five intentional rule mutations were compiled and run. Each produced actual failed assertions, not just compilation failure. Each source was restored in `finally`, verified by SHA-256, then the full restored suite and console suite ran successfully.

| Mutation | Deliberate break | Failed tests | Representative detection |
|---|---|---:|---|
'''
descriptions = ['Room loss interval 300 → 301 seconds', 'Allow slot selection during a two-handed carry', 'Let absent inventory spoil', 'Mark every case load cooled without checking history', 'Bypass duplicate receipts and stale-request guard']
for m, desc in zip(mutations, descriptions):
    report_body += f"| {m['Mutation']} | {desc} | {m['Failed']} | `{m['FailingTests'][0]}` |\n"
report_body += '''
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

'''
baseline = json.loads((stage / 'evidence/baseline-files.json').read_text(encoding='utf-8-sig'))
before = {str(Path(p)).casefold(): h for p, h in baseline.items()}
files = set(p for folder in [stage, drafts] for p in folder.rglob('*') if p.is_file())
files.update([manifest, report])
changed = sorted((p for p in files if not p.exists() or before.get(str(p).casefold()) != sha(p)), key=lambda p: str(p).casefold())
assert all(str(p.resolve()).casefold().startswith(str(game.resolve()).casefold() + '\\') for p in changed)
manifest.write_text('\n'.join(str(p) for p in changed) + '\n', encoding='utf-8')
authored = [p for p in changed if p == report or p.parent == drafts or p.parent == stage or '/src/' in p.as_posix() and '/obj/' not in p.as_posix() and '/bin/' not in p.as_posix() or
            any('/' + folder + '/' in p.as_posix() for folder in ['checks', 'handoff']) or any('/' + folder + '/' in p.as_posix() for folder in ['tests', 'selftest']) and p.suffix in ['.cs', '.csproj'] and '/obj/' not in p.as_posix() or
            '/buyers/' in p.as_posix() and p.suffix in ['.cs', '.csproj'] and '/obj/' not in p.as_posix()]
report_body += f'{len(changed)} created/changed files total; {len(authored)} authored/copied source, data and handoff files (remaining entries are generated evidence/tooling).\n\n'
report_body += 'Authored/copied deliverables:\n\n' + ''.join(f'- `{p}`\n' for p in authored)
report_body += '\nFull inventory (including all generated files):\n\n```text\n' + '\n'.join(str(p) for p in changed) + '\n```\n'
report.write_text(report_body, encoding='utf-8')
print(json.dumps({'tests': counters['total'], 'groups': groups, 'mutations': len(mutations), 'files': len(changed), 'authored': len(authored), 'report': str(report)}))
