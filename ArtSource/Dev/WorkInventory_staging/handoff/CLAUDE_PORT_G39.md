# G39 — port after the Unity workstream releases its lock

This package has only been built and exercised outside Unity. All runtime C# projects target `netstandard2.1`, C# 9, warnings as errors. The console and NUnit runners target .NET 8.

1. Copy the **eight `.cs` files in `src/`** into `Assets/OnlyVolunteers/Items/Core/`. Do not copy project files, test binaries, packages, or the buyers source copy into this folder. Keep existing asset identities and let Unity create metadata for new files when the lock is released.
2. Create `Assets/OnlyVolunteers/Items/Core/OnlyVolunteers.Items.Core.asmdef`:

```json
{
  "name": "OnlyVolunteers.Items.Core",
  "rootNamespace": "OnlyVolunteers.Items.Core",
  "references": [],
  "autoReferenced": true,
  "noEngineReferences": true
}
```

3. Review `BUYERS_API_G39.patch` against the live buyers revision, then apply its changes to the existing buyers core. It changes `BuyerRules.cs`, `BuyerState.cs` and adds `BuyerInventoryApi.cs`; it does not replace the buyer subsystem. The patch was checked with `git apply --check` only. Original SHA-256 hashes are in `evidence/protected-inputs.json`.
4. Keep one host `ItemLedger` and one `ItemIntentServer`. Map the authenticated connection to the persistent player id; never trust an id in the request. Populate `IntentContext` from the **server** player/seat, resolved target ids, distance, line of sight, current camera/input mode and capture facts. `Restrained` for blood means restrained hands. Only empty hands may start body dragging. `Use` produces target effects; the adapter applies these to CaptureRules in the same serialized host step. It owns dose consequences, donor blood-portion counters, ragdolls and presentation. Target a container with `Put`, a surface with `Place`, and a buyer through the sales bridge, rather than a tool-on-NPC `Use`.
5. Forward monotonic active-world seconds, not game hours or wall-clock elapsed time. Separate game seconds are provenance only. Poll `DrainTierChanges()` for each exact tier-loss timestamp and `DrainChangedIds()` for replication. Send cues/effects **only when a result is successful and `Replayed == false`**. Persist receipts and high-water marks; resume request and press counters above the saved values after reconnect. A replay returns its original result without advancing the clock.
6. Six numbered pocket slots remain. The kit occupies one of those keys (index 5 by default) while nonempty, and has 12 internal entries as a provisional capacity. `KitCycle` orders ties → anesthesia syringe → blood syringe → empty blood bags → sealed blood bags → body bags → organ pouches → head bags → vials, then selection becomes empty hands. Equal types use definition id, then instance id. Picking ordinary objects uses pockets; putting supplies in the kit is an explicit destination. The UI may map shop/start-kit delivery to that destination.
7. `EnsureVan(vanId)` creates a 12-slot shelf and two single-cooler mounts **disabled until purchased**. `PurchaseVanStorage` enables the same upgrade on all three. World physics handles loose cargo before purchase. Stored goods get attached socket views; no separate item physics remains in the shelf/mount. Fridge power changes must call `SetPowered` at the transition time. Cooler impacts call `ApplyImpact(coolerId, serverImpactSpeed, now)`; an adapter must not also apply a second hit to its children.
8. On leave call `ItemIntentServer.PlayerLeft`. Remove that player's carried cooler and other views from the world; do not release/drop/retire their ledger inventory. Filter world replication and buyer projections through `IsWorldAvailable`. On rejoin call `RejoinPlayer` with the same persistent id, then restore pockets, kit subselection, carry and contents. Inventory timers pause while absent; anchors rebase on rejoin to preserve remaining durations. `KnockOutHeldItem` is a separate future hook and must never be called on disconnect. The authoritative save includes all players, even absent ones; owner-only inventory replication must not broadcast everyone's full save.
9. Save `InventorySaveV2` as the inventory fragment of the host's existing world save: `items` is the sole item ledger, `players` stores selections/presence, `itemPoses` uses plain vectors/quaternions. `Snapshot`/`Restore` make copies. Restore the active clock exactly. Map legacy fields into `LegacyV1`; `LegacyMigration.Apply` requires a fresh ledger, returns overflow poses and warnings, and preserves partial table-tool fills separately for the existing table block. Nearby tray sockets are resolved by the future Unity adapter (7 cm rule). `InventorySaveFile.MigrateV1` demonstrates create-once byte-exact `.v1.bak` and atomic v2 publication to a distinct fragment file. **Do not replace a full CaptureSaveData file with this inventory-only DTO**: compose it with the existing NPC, van, table, funds and buyer blocks in the host world save transaction. Unknown/malformed migration data prevents file publication.
10. Merchandise projection: organ kind maps directly to buyer product kind; tier maps 1:1 to `QualityTier`; `SourceNpcId = ItemCatalog.OrderSource(organ)` (role lineage first, otherwise patient id), `SourceNpcType = DonorNpcType`, packaging and delivered-cooled latch come from the ledger. Register team-container goods through `RegisterTeamItem`, then report an actual pickup with `SetItemHolder`. Blood bags are sealed instances; unsealed syringe blood uses `BloodSaleIdentity` (`id#FillSeq`) and must pass `BloodExpired` before being offered. Use `RetireBloodPortion(itemId, fillSeq, now)` after a confirmed portion sale; it empties the syringe and tombstones that portion, retaining the tool. Packaging/discarding also tombstones the old portion: remove its unsold buyer projection when that action succeeds. The existing C01 one-time intro exception remains in buyers rules.
11. WI-J transaction boundary: serialize sale confirmation and case moves on one host queue. Prevalidate the destination, call buyers `UnloadItem` before publishing a case withdrawal, and do not move if it fails. Load with the latch-bearing overload. Update quality/package projections before quoting or confirmation; require the displayed expected total. On confirmed sale retire exactly the sold ledger IDs before processing the next intent. Disposal/confiscation calls buyers `RemoveItem`; it keeps a tombstone. Meeting completion moves unsold goods to one or more 8-slot return trays; the caller creates extra trays, never discards overflow. `ItemIntentServer` currently handles the inventory operation; the WI-J coordinator still owns this cross-core transaction. In-process locks are not a transaction across two independent cores, disk and network.

Standalone verification from `C:/Dev/Game`:

```powershell
& .\ArtSource\Dev\WorkInventory_staging\Run-Tests.ps1
& .\ArtSource\Dev\WorkInventory_staging\Run-Mutations.ps1
```

To run the console suite without allowing CLI caches outside staging:

```powershell
. .\ArtSource\Dev\WorkInventory_staging\Environment.ps1
dotnet run -c Release --project .\ArtSource\Dev\WorkInventory_staging\selftest
```

Unity import/EditMode, visuals, real input, two-process FishNet, driver/passenger geometry, shelf attachment while driving, and world-save composition are later integration checks. The pure checks do not establish those outcomes.
