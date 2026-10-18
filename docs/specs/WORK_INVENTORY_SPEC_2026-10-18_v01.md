# VOLUNTEERS ONLY: Work Inventory Specification

Revision: v01
Date: 2026-10-18
Status: design proposal for the lead. Nothing in Assets/ was changed and Unity was not opened. A pure C# prototype of the item core exists outside Assets (§11).
Scope: the inventory for work items. That covers organs, blood, field tools, consumables and the containers that hold them, from the field through the van, the base and the table to the buyer.

## 0. Коротко для Феди

- Сейчас «инвентарь по работе» — четыре несвязанных куска. Полоска 1–6 на карте хранит органы как «почка ×2 по $400», без качества и донора. Органы у стола — настоящие предметы, но живут только у стола. Аптечка Z/X/C — просто счётчики. Покупатели ждут предметы с донором, но их никто не создаёт. Полоска и деньги не сохраняются.
- Предлагаю один общий «склад» на хосте. Каждая вещь — отдельный предмет со своим номером. У органа есть качество (Убитое…Идеальное), донор («почка того качка»), время извлечения и запас до следующей порчи. Ещё хранится, упакован ли орган и был ли он в холоде.
- **Карманы: 6 слотов**, клавиши 1–6 и колесо. Что выбрано, то в руках. Та же цифра ещё раз — пустые руки: можно тащить тела ЛКМ, как раньше.
- **Инструменты — обычные предметы:** стяжки, шприц наркоза, шприц для крови, мешки. Взял в руки, навёлся на человека и держишь **ЛКМ**. **ПКМ** — второе действие: набрать наркоз из флакона, перелить кровь в пакет, упаковать орган. Z/X/C и нижние карточки уходят.
- **G** — положить под ноги, **держать G** — швырнуть (орган от сильного удара теряет ступень). **E** — поднять или взять, открыть крышку. **Держать E** — поднять холодильник.
- **Холодильник на 8 мест несут двумя руками.** Ставишь, открываешь и перекладываешь органы по одному: ЛКМ кладёт, E берёт. Так же работают кейс покупателя, тайник и холодильник на базе (24 места, нужен свет).
- **Порча:** в кармане, на лотке и на полу — −1 ступень за 5 минут, в переносном холодильнике — за 25 минут, во включённом стационарном холодильнике порча стоит. Числа потом поменяем.
- В бусике есть полка для мелочи и 2 гнезда под холодильники. На ходу ничего не катается и не теряется.
- В коопе всё решает хост. Каждый видит свои карманы и что у других в руках.
- Сохраняется всё: карманы, холодильники, лотки, органы на полу. Старое сохранение перенесётся само.
- Прототип «склада» уже написан и проверен вне Unity: 37 проверок, все PASS. В конце 5 вопросов.

---

## 1. Scope, sources and labels

This spec designs the long-term work inventory. Another agent is building a first pass in Unity right now: the Z/X/C tools become hotbar items used with LMB. §8.4 says how that pass fits.

**Sources read:**
- `docs/specs/SALES_GAMEPLAY_SPEC_2026-10-18_v01.md`, including the Decisions section;
- `Working/Reviews/Sales/SALES_SPEC_REVIEW_v01.md`: blocker S1–S4, work package E;
- `docs/specs/BUYERS_SPEC_2026-10-15_v02.md`;
- `docs/specs/OPERATIONS_SPEC_2026-10-15_v01.md`: §5, §8–§9, §12–§15, §20, §24;
- `docs/specs/CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md`;
- `docs/specs/NETWORK_MAP_PLAN_v01.md`: §2, §3, M0–M9 and Fedya's decisions;
- `docs/reports/CAPTURE_DELIVERY_STAGE_A.md`, `docs/reports/CAPTURE_DELIVERY_STAGE_A_HOWTO_RU.md`, `Working/Reviews/Capture/stageA/PROGRESS_CLAUDE_REWORK.md`;
- `docs/reports/BUYERS_RULES_v01.md`, `docs/reports/PROPS_OPS_STAGE2_CLEANUP_v01.md`;
- canon §80 (arrest);
- the code under `Assets/OnlyVolunteers`, read only (§2).

**Labels:**
- **Confirmed:** decided by Fedya, here or in a cited spec.
- **Existing:** what the code does today.
- **Proposed:** this document's choice. The lead may adopt it; numbers stay tunable.

Where this spec conflicts with code (`ItemStack` value-only organs, the 0–4 grade scale, `CaptureFieldKit` counters, size-unit capacity), this spec wins. Where it conflicts with a Confirmed decision in another spec, the other spec wins.

**Not in scope:**
- prices and economy, which Fedya deferred: numbers below are placeholders from the ops spec;
- the operation table's own tool flow;
- buyer rules;
- capture physics.

---

## 2. Current state

### 2.1 Four separate item systems

Paths are under `Assets/OnlyVolunteers`.

| System | Main files | What it holds | Per player or shared | Networked | Saved |
|---|---|---|---|---|---|
| **Hotbar module** ("cloud session" draft) | `Inventory/Core/InventoryModel.cs`, `ItemStack.cs`; `Inventory/Runtime/NetworkInventory.cs`, `LocalInventory.cs`, `WorldItem.cs`, `OfflineWorldItem.cs`, `InventoryInput.cs`, `InventoryHud.cs`, `ItemDefinition.cs`, `ItemDatabase.cs` | `ItemStack {ItemId, Count, UnitValue}` × 6 slots, a size capacity of 12, `Cash`, `SelectedIndex`. **Organ quality exists only as price**: two kidneys merge if their `UnitValue` matches. No instance id, tier, donor, spoilage or packaging. | Per player | `NetworkInventory`: server model; owner-only `SyncList<ItemStack>` and `SyncVar cash`; `selected` visible to everyone; one `SyncVar<WorldItem> physicalItem` "in hands" slot for `IPhysicalInventoryItem` objects. `LocalInventory`: offline. | **No.** Hotbar contents and `NetworkInventory` vanish on quit or disconnect. Only the old clinic loop writes cash (`ClinicSave.money`). |
| **Operation table outputs** | `Operation/Stage1/Scripts/NetworkOperationTable.cs`, `OperationPhysicalItem.cs`, `OperationTool.cs`; `Operation/Stage1/Core/OperationState.cs` | `OperationItemState {id = "patientId/organ/i", kind 0 kidney / 1 liver / 2 sealed blood / 3 filled syringe, grade 0–4, pose, freshness, sealedBlood, expired}`. Tray: 3 organ sockets and 3 blood bags. Table stock: `anesthesiaStock`, `anesthesiaBarrel`, `bloodFill`, `bagsUsedMask`. | Shared (one table) | Yes: each output is an `OperationPhysicalItem` NetworkObject with `SyncVar`s identity, grade, kind and holder. An impact above 2.4 m/s costs 1 grade with a 0.6 s cooldown. | **Yes**, inside `CaptureSaveData.table` (`OperationWorldState.items`, with poses). `ServerAdmit` resets the table stock for every new patient. |
| **Capture field kit** (`Capture/`, created today, untracked) | `Capture/Scripts/CaptureFieldKit.cs`, `CaptureHud.cs`, `Capture/Core/CaptureRules.cs` | Plain counters on one local kit: `Ties` (start 10), `AnesthesiaBarrel`, `AnesthesiaStock`, `BloodFill`, `BloodBags`. When `BloodFill` reaches 1, `BloodBags++` (a counter with no donor and no object, so it cannot be sold). `RestockAtBase()` refills. | One kit (solo) | **No** (local MonoBehaviour; NETWORK §3.4 deferred "kit stock per player" to M9) | **Yes:** `FieldKitSave {ties, anesthesiaBarrel, anesthesiaStock, bloodFill, bloodBags, tool}`. Body bag stock is saved in `CaptureSaveData.bodyBags`. |
| **Buyers core** (pure rules, unwired) | `Buyers/Core/BuyerState.cs`, `BuyerRules.cs`, `BuyerOrders.cs` | `BuyerItemState {Id, Kind, Quality 1–5, SourceNpcId, SourceNpcType, Packaged, DeliveredCooled, HolderId, MeetingId, StashOrderId, Sold}`. It expects the host inventory to `RegisterItem` unique ids and to report quality. | Team (host) | No adapter | Snapshot DTO only, no file |

**Related pieces:**
- **Body bags.** `Capture/Scripts/CaptureCorpseDisposal.cs` keeps `Stock = 2`; hold R packs a corpse. `CaptureCorpseHands` handles carrying: E carries, E/G drops, LMB throws.
- **Player speed.** `OperationPlayerSpeed.cs` was added today by the agent working in Unity. It caps speed while pushing the gurney or carrying a bag.
- **Items in the van.** `Map/Scripts/GreyboxVanCargo.cs` treats cargo as physical NPC bodies with no item slots.

### 2.2 Definitions that exist

| Id | Asset | Kind | Size | Base value |
|---|---|---|---|---|
| 101 | `Inventory/Items/Item_Heart.asset` | Organ | 2 | 1000 |
| 102 | Item_Kidney | Organ | 1 | 250 |
| 103 | Item_Liver | Organ | 2 | 350 |
| 104 | Item_Lungs | Organ | 3 | 450 |
| 105 | Item_Brain | Organ | 2 | 1200 |
| 106 | Item_Eye | Organ | 1 | 200 |
| 201 | Item_Scalpel | Tool | 1 | 400 |
| 109 | `Operation/Stage1/Data/Item_BloodStage1_v01.asset` (filled syringe) | Other | 1 | – |
| 110 | `Operation/Stage1/Data/Item_BloodBagStage1_v02.asset` | Other | 1 | 50 |
| 202 | `Capture/Art/BodyBag_Cargo_v02.asset` | Other | 64 | 0 |

`ItemDatabase.asset` lists only 101–106 and 201. There are no definitions or runtime code for zip ties, syringes as carried items, vials, pouches, empty bags, the cooler, the fridge, a buyer case, a stash or a return tray.

**Art already made:** `ArtSource/Props/COOLER-ASTRA-001` v03 (0.40 × 0.24 × 0.35 m, open and closed states), `ORGANBAG-ASTRA-001` v01 (sealed and open), `FRIDGE-ASTRA-001`, `SYRINGE`, `BLOOD-BAG`, `DUCTTAPE`, `BODYBAG`, `CRATE`. The cooler and organ bag wait for Fedya's visual OK (PROPS_OPS_STAGE2_CLEANUP_v01).

### 2.3 Controls today

| Context | Keys (Existing) |
|---|---|
| On foot | Q hit. E context: inside handle, uses, `OfflineWorldItem` pickup, cargo door, seat. LMB holds a body point; the wheel moves it closer or farther. G drops one hotbar item. 1–8 select a hotbar slot (`InventoryInput`). Ctrl crouches. Tab phone. K save, Shift+K new game. |
| Field kit | Z ties, X anesthesia syringe (refills from stock when taken), C blood syringe; the same key again puts it away. **Hold RMB** applies to the aimed NPC within 2.6 m, while LMB may keep holding the body. Three cards Z/X/C (214 × 74 px, 108 px above the bottom) sit above the hotbar strip. |
| Corpse | Hold R ~1 s packs into a body bag. E carries the bag; E or G drops it; LMB throws it. |
| Driving | 1–4 and F doors, plus 7–9, C, R, H (`VanDriveInput`). |
| Table mode | 1–4 tools (hands, anesthesia, blood, scalpel). LMB acts. RMB returns the tool or puts the held item on the tray. The wheel zooms, Tab switches Prep/Operation, Esc or E exits. |

### 2.4 Gaps this spec closes

| # | Gap | Where it hurts |
|---|---|---|
| G1 | No single-organ record outside the table: no instance id, tier, donor, extraction time, spoilage, packaging or cooled flag | Sales S1 (the "biggest prerequisite"); the special order needs the bodybuilder's own kidney |
| G2 | Three quality scales: 0–4 (`OrganQuality`, `CaptureGrades`, the table), 1–5 (buyers), and price only (hotbar) | Wrong tiers at sale |
| G3 | Two pools of anesthesia and blood (field kit and per-patient table stock, which resets on admit); field blood bags are a counter | Blood cannot be sold from the field; double counting |
| G4 | Two inventories on the i10 pawn: `LocalInventory` hotbar and `NetworkInventory` for physical carry | Co-op M1 |
| G5 | Hotbar, cash and dropped `WorldItem`s are not saved; no cooler, fridge, case, stash or return tray at runtime | Sales S2, S3 |
| G6 | Spoilage outside the body is not implemented (only the intro syringe's 120 s expiry) | Ops §13, Sales §6.3 |
| G7 | No rule for when delivery counts as cooled | Sales S4 |
| G8 | Tools are bound to Z/X/C with RMB use; Fedya wants ordinary items used with LMB | This request |
| G9 | Money in four places | NETWORK Q4 (decided: one shared fund). This spec removes cash from the inventory. |

---

## 3. Item model

### 3.1 Principles (Proposed)

1. **One ledger on the host is the single source of truth.** `ItemLedger` holds every work item and every container. Everything else is a view of it:
   - world NetworkObjects;
   - SyncLists and the HUD;
   - the held view model;
   - the `BuyerItemState` projection.

   No second inventory, spoilage clock or cash store (ops §20, sales §10).
2. **Every item has exactly one place:** a container slot, the world (a loose physical object) or a two-handed carry by one player.
3. **Instances, not counts, for anything with state.** Organs, blood bags, syringes, vials and coolers are one record each. Only stateless consumables stack: zip ties, empty organ pouches, empty blood bags, body bags.
4. **Ids:**
   - Organs keep the deterministic extraction id that the table already mints (`P-xxxxxxxxxx/kidney/0`), so a repeated extraction cannot make a second organ.
   - Everything else gets `I-000123` from a saved counter.
   - Ids of sold, consumed or destroyed items are retired and never reused.
5. **One quality scale: tiers 1–5** (1 Damaged/Убитое … 5 Perfect+/Идеальное), as in BUYERS v02 and the buyers core. The capture and table code use 0–4 today; the boundary converts with `tier = grade + 1`.
6. **Slots replace size units.** One item per slot (or one stack). Lungs fit a pocket like a kidney. The `size`/`capacity` fields of `ItemDefinition`/`InventoryModel` are retired for work items. Two-handed items never go into pockets.
7. **Time is active-world seconds** on the host: they advance only while the session runs and freeze when the world is closed (ops §14, capture D13). Spoilage does not use game hours, so the 24- or 45-minute day-length choice (sales review K7) cannot change spoilage.

### 3.2 Definitions (data)

`ItemDef` is built from `ItemDefinition` (ScriptableObject). Proposed new fields on `ItemDefinition`:
- `itemClass` (replaces `ItemKind`);
- `maxStack`;
- `twoHanded`;
- `containerSlots`;
- `organKind`.

The `size` field is ignored for work items.

| Id | Key | Class | Stack | Two-handed | Price (ops placeholder) | Status |
|---|---|---|---|---|---|---|
| 101–106 | organ.heart/kidney/liver/lungs/brain/eye | Organ | 1 | no | base 1000/250/350/450/1200/200 | Existing ids |
| 109 | blood.intro_syringe | BloodSyringe (filled, found) | 1 | no | sells once to C01 for $10 | Existing id, new class |
| 110 | blood.bag | BloodBag (sealed portion) | 1 | no | $50 | Existing id |
| 111 | tool.blood_syringe | BloodSyringe (reusable) | 1 | no | – | **New** |
| 112 | tool.anesthesia_syringe | AnesthesiaSyringe (reusable) | 1 | no | – | **New** |
| 113 | supply.anesthetic_vial | AnestheticVial | 1 | no | $200 / $400 / $800 per ~10 nominal uses (3 formulas) | **New** |
| 114 | supply.zip_ties | ZipTies | 20 | no | $10 per use | **New** |
| 115 | supply.organ_pouch | OrganPouch (empty) | 10 | no | $10 | **New** |
| 116 | supply.empty_blood_bag | EmptyBloodBag | 10 | no | $5 | **New** |
| 117 | supply.head_bag | HeadBag (Stage B) | 5 | no | $10 | **New**, later |
| 201 | tool.scalpel | Tool (also cuts ties) | 1 | no | $400 | Existing |
| 202 | supply.body_bag | BodyBag | 5 | no | price not set | Existing id, new class |
| 301 | container.cooler | Cooler: an item and an 8-slot container | 1 | **yes** | $1,000 | **New** |

The fridge (24 slots), tray, buyer case, stash and return tray are **containers only**. They are furniture or meeting objects, not carryable items.

### 3.3 `ItemRecord` (one instance)

| Field | Type | Meaning |
|---|---|---|
| `Id` | string | Extraction id for organs, `I-nnnnnn` for others |
| `DefId` | int | `ItemDefinition.Id` |
| `Count` | int | Stack size, 1 for instances |
| `Place` | enum | `Container` / `World` / `Carried` |
| `ContainerId`, `Slot` | string, int | When in a container |
| `CarrierId` | string | Player id, for a two-handed carry |
| `HasOrgan` + `Organ` | flag + `OrganData` | Organ state (below) |
| `HasFill` + `Fill` | flag + `FillData` | Syringes, vials, blood |
| `Revision` | long | Bumped on every change; views update on it |

The pose of a `World` item lives on its NetworkObject and in the save's pose table (§6), not in the record.

### 3.4 Per-instance state

**`OrganData`.** Provenance is copied at extraction and never changes afterwards.

| Field | Meaning |
|---|---|
| `Kind` | Kidney, Liver, Lungs (the paired item), Heart, Eye, Brain |
| `Tier` | 1–5 |
| `Progress` | 0..1 toward the next one-grade loss. It is **kept across moves** (ops T-05). |
| `SettledAt` | Active seconds when tier and progress were last brought up to date. Spoilage is evaluated lazily (§7.2). |
| `DonorPatientId` | `PatientId` minted at knockdown |
| `DonorPersonId` | Stable id of an authored unique NPC (sales review K6); empty for crowd NPCs |
| `DonorRoleKey` | The lineage key a special order targets, for example `HAMLET_BODYBUILDER`. The "twin brother" shares it (Fedya, sales decision 3), so a kidney of either matches. |
| `DonorNpcType`, district | For the HUD line and buyer type checks |
| `ExtractedAtGameSeconds` | World clock game time, for receipts and the card |
| `Packaged` | Sealed in an individual pouch (ops §13.1) |
| `ColdSince`, `LastColdStint`, `WarmSince` | Cold-chain history (§7.3) |
| `CaseColdLatch` | Set when loaded into a buyer case if the cold chain held; it is the `DeliveredCooled` reported to the buyers core |
| `LastImpactAt` | Impact cooldown |

**The special-order tag is derived, not stored.** The HUD and the buyers core compare the provenance (role key, kind, tier, packaging) with the active order. When an order changes, nothing on the item needs rewriting. The card shows «Подходит к заказу ✓» or the missing requirement (sales §8.3).

**`FillData`, by class:**

| Class | Fields used |
|---|---|
| AnesthesiaSyringe | `Amount` (abstract units, up to the syringe capacity from `OperationTuning.syringeCapacity`), `Formula` 0–2 |
| AnestheticVial | `Amount` (units left), `Formula` |
| BloodSyringe | `Amount` 0..1 portion. `DonorPatientId`. `FilledAt`, for the 120 s unsealed expiry (ops T-06, `OperationTuning.unsealedBloodSeconds`). `FillSeq`: +1 per filling, so the sale identity of syringe blood is `{itemId}#{FillSeq}` and the syringe itself is never sold. |
| BloodBag | `Amount` = 1 (one sealed portion), `DonorPatientId`. No tier and no spoilage (ops §5.2). |
| ZipTies, OrganPouch, EmptyBloodBag, BodyBag | `Count` only |

The record does not store blood portions drawn from the donor; they stay on the NPC (`OperationState.bloodPortions`, capture D7).

### 3.5 Containers

| Kind | Id pattern | Slots | Accepts | Storage class | Open/close | Where |
|---|---|---|---|---|---|---|
| Pockets (hotbar) | `pockets:{playerId}` | **6** | Anything not two-handed | Room | Always open; only its owner moves items in or out | Each player |
| Van shelf | `vanshelf:{vanId}` | 12 | Anything not two-handed | Room | Open while a bay door is open | Rack along the bay wall |
| Van cooler mount | `vanmount:{vanId}:{n}` | 1 each, 2 in the stock van | Coolers only | – | – | Bay floor clamps |
| Cooler | = the cooler's item id | 8 | Organs, blood bags, blood syringes | **PortableCooler** | E opens the lid; it must be set down; lifting closes it | Carried, on the ground, in a van mount |
| Fridge | `fridge:{baseId}:{n}` | 24 | Organs, blood bags, blood syringes | **FridgePowered** while base electricity is paid, else FridgeUnpowered | E opens the door | Base furniture |
| Tray | `tray:{tableId}` | 6 (3 organs + 3 bags) | Anything not two-handed | Room | Open | Operating tray (replaces the table's private tray list) |
| Buyer case | `case:{meetingId}` | 8 | Organs | Room | Open while the buyer waits | Buyer surface (sales SG-D26/27). Loading **reserves**; it is not a sale. |
| Stash | `stash:{stashId}` | 4 | Organs | Room | Opens when its order is accepted | Sales §8.3 |
| Return tray | `return:{pointId}:{n}` | 8, more trays merge | Anything not two-handed | Room | Open | Unsold goods at a meeting point (SG-D48, P10). Removed when empty. |

**Rules:**
- **Nesting depth is at most 2:** an organ in a cooler, in a van mount. A cooler never goes into pockets, a fridge or another cooler.
- **The storage class comes from the item's direct container.** An organ in a cooler uses the cooler rate whether the cooler is carried, on the ground or in the van.
- **Preservation applies only to items actually in the container** (ops §13.2). An organ lying on top of a fridge is in the world, at the room rate.
- **Destroying a cooler** spills its contents into the world. Nothing vanishes.

### 3.6 Physical, held and stored

| State | Ledger place | What exists in the world |
|---|---|---|
| **Stored** (pockets, shelf, cooler, fridge, tray, case, stash, return tray) | Container | No NetworkObject per item. Containers with sockets (cooler, fridge, tray, case) show a model per occupied socket, driven by the container's replicated contents. Pockets show nothing except the selected item. |
| **In hands** | Container `pockets:{p}`, in the selected slot | A first-person view model for the owner and a hand-socket model on the remote body for everyone else. Not a NetworkObject. |
| **Loose** | World | One `WorldItemNet` NetworkObject (the evolution of `WorldItem` / `OperationPhysicalItem`). It is server-simulated and kinematic on clients, and never solid for the player (`PlayerPushPolicy`). |
| **Two-handed carry** (cooler, body bag) | Carried | The item's own physics NetworkObject, held by the server hold loop (the existing `CaptureCorpseHands` / `NetworkPhysicsBody` pattern) |

The body bag as a packed corpse stays what G35 built: an NPC ragdoll in a bag, not a ledger item. Only the **empty** body bag (a consumable) is an item.

### 3.7 Identity and the bodybuilder

- **Organs** are minted by the server at detachment through `MintOrgan(extractionId, …)`, inside the same atomic step as the table's extraction (ops §20.1).
- **Provenance is copied from `OperationState` / `CaptureFacts`:** patient id, district, NPC type and, once sales package F lands, `PersonId` and role key.
- **The twin rule** (Fedya, sales decision 3) is satisfied by matching on `DonorRoleKey`, not on `DonorPatientId`.
- **Blood bags** record the donor's patient id for receipts. Nothing in the buyers spec requires blood from a specific person.

---

## 4. Player UX

### 4.1 Feel goals

- **One verb per button,** the same everywhere.
- **Physical and readable:** you see the kidney in your hand, in the cooler, in the case. Friends see what you hold.
- **No inventory screen and no grid.** The hotbar, the hands and real containers you open in the world are the whole UI.
- **Comic risk, not bookkeeping:**
  - thrown organs bruise;
  - a dropped cooler hurts everything inside;
  - a teammate can grab the kidney out of the open case (SG-D71).
- **Follow the existing keys:** E interact, LMB grab with empty hands, Q hit, G drop, F/1–4 in the van.

### 4.2 Hands and hotbar

- **6 pocket slots** on keys 1–6. The wheel cycles them. The wheel is not taken over while you drag a body with LMB: then it keeps changing the grab distance, as today.
- **The selected slot is "in hands".** Selecting an empty slot, or pressing the selected slot's key again, gives **empty hands**. This matches today's "Z again puts it away".
- **Empty hands** keep every existing behaviour: LMB grabs and drags bodies, the gurney and loose items; E opens doors and seats.
- **Picking an item up** (E) puts it into the selected slot if that slot is empty, otherwise into the first free slot. The new item is **selected** so it is in your hands. If all slots are full: «Карманы полны», and nothing happens.
- **Two-handed carry** (cooler, body bag) does not use a slot:
  - the hotbar greys out;
  - tools cannot be used;
  - you walk at the carry speed cap (`OperationPlayerSpeed`);
  - pressing 1–6 does nothing until you put the item down.

### 4.3 Controls (Proposed)

| Input | Empty hands | Small item in hands | Carrying a cooler or body bag |
|---|---|---|---|
| **1–6, wheel** | Select a slot | Select a slot; same key again → empty hands | Ignored |
| **LMB** (tap / hold) | Grab and drag (existing). On an item in an open container: take it. | **Primary use** on the aimed target (table §4.5): tool on a person; put into the aimed open container; place gently on the aimed surface | Throw (existing body-bag convention) |
| **RMB** (hold) | – | **Secondary** action of the item (§4.5) | – |
| **E** | Interact (existing). On a loose item or a socket in an open container: take it into pockets. On a placed cooler or fridge: open or close. | Same as with empty hands (pick up and open still work) | Set down gently |
| **Hold E** (0.4 s) | On a cooler: lift with both hands (closes the lid) | Same | – |
| **G** | – | Put the item down at your feet (gentle, no impact) | Set down |
| **Hold G** (charge, max 0.6 s) | – | **Throw**; strength follows the charge | – |
| **Q** | Punch (unchanged) | Punch (unchanged; the item stays in the other hand) | – |
| **Tab** | Phone (unchanged) | The item is lowered while the phone is out; LMB goes to the phone (SG-D55) | Phone unavailable (put the load down first) |

- **Z/X/C** are removed once the hotbar tools work. During the transition they may stay as hidden aliases that select the first ties, anesthesia or blood syringe slot.
- **Hold R** packing stays as a shortcut until the body bag item exists (§4.5), then it is removed.

### 4.4 Using a tool on a person

- **Aim:** the crosshair target is resolved as today (`CaptureFieldKit`: reach 2.6 m, line of sight, NPC body part). Ties go to the **hands** when the aimed part is the upper body or arms, and to the **feet** for the legs.
- **Tap vs hold:** every tool action on a person is a **hold** with a ring under the crosshair:
  - ties about 1 s;
  - anesthesia is continuous, about 0.5 units/s, with the existing coloured dose bar;
  - blood about 4–5 s per portion (ops §5.1).
- **Release early:**
  - ties: nothing is used;
  - anesthesia: what was injected stays;
  - blood: the portion is not drawn (existing behaviour).
- **Valid targets:** NPC bodies and the table patient through the field route (D1, D7 rules unchanged). Not teammates (player knockout is future work, capture §12). Not buyers (sales decision 1: hit only).
- **Holding a body and using a tool at once** needs two players: one holds with empty hands, the other uses the tool. Solo, the player knocks the NPC down with Q first, then uses the tool. This gives up today's "LMB holds the body, RMB injects" combo (**Q3**).

### 4.5 Item by item

| Item | LMB (on target) | RMB (hold) | In hand / card |
|---|---|---|---|
| **Zip ties** (stack) | Hold ~1 s on hands or feet: tie, uses 1 | – | Count. Hint «ЛКМ — связать руки/ноги». |
| **Anesthesia syringe** | Hold on a person: inject (the existing dose model, anywhere, D1) | Hold ~1 s: refill from an anesthetic vial in pockets. A different formula is refused while the syringe is not empty. | Fill bar and formula name. The HUD keeps the existing blue/green/yellow/red guidance bar while injecting. |
| **Anesthetic vial** | – | – | Units left. It is used by the syringe's RMB. |
| **Blood syringe** (reusable) | Hold on a sleeping, knocked-out or restrained living person: draw 1 portion. Refused on a corpse or a struggling NPC (D7). | Hold ~1.2 s with a full syringe: transfer into an empty blood bag from pockets. A sealed **blood bag** item appears in that slot or the first free one; refused with «Нет места» if none. | Fill bar. Red «кровь свернётся» countdown after 120 s unsealed (T-06). |
| **Empty blood bag** (stack) | – | – | Count |
| **Blood bag** (sealed) | Put into the aimed cooler, fridge or tray. On C01: offer for sale (sales §6.1, hand to hand). | – | «Кровь · запечатана» |
| **Filled intro syringe** | On C01: offer (once, $10) | Same transfer as the blood syringe once bags exist | As the blood syringe |
| **Organ** | Put into the aimed open container (cooler, fridge, tray, case, stash); or place gently on the aimed surface | Hold ~1 s: pack into a pouch from pockets (ops §13.1). The model swaps to the sealed ORGANBAG. | **Card:** name, tier name + % + tier colour, freshness bar, ❄ «в холоде» or «тает», «упакован», donor line («Хутор · качок»), order match «✓ заказ» or the missing requirement |
| **Organ pouch** (stack) | – | – | Count. It is used by the organ's RMB. |
| **Body bag** (stack) | Hold ~1 s on a corpse (field, floor or a table patient with straps open): pack it (replaces hold R) | – | Count |
| **Scalpel / knife** | Hold on a tied limb: cut the tie (capture §11) | – | – |
| **Cooler** (two-handed) | Throw | – | Lid state and «5/8» when aimed at |

### 4.6 Drop, throw, catch and impacts

- **G** places the item about 0.8 m ahead on the ground; there is no impact.
- **Hold G** throws: release speed from 3 to 9 m/s with the charge (Proposed).
- **Impacts:**
  - A thrown or dropped organ that hits something above the existing threshold (2.4 m/s, cooldown 0.6 s, `OperationTuning`) loses 1 tier, once per impact event (ops §12.2).
  - A thrown cooler that lands above 4 m/s costs every organ inside 1 tier (**Q2**).
- **Passing to a friend:** throw it or put it down. An exact hand-over and a mid-air catch are parked for later (§9.3).

### 4.7 Containers by hand

1. **Look** at a placed cooler, fridge, case or tray: «E — открыть (5/8)».
2. **E opens it.** The lid or door animates, and the contents show as models in sockets.
3. **Put:** with an item in hand, **LMB** on the open container puts it into the aimed socket, or the first free one.
4. **Take:** **E** on an item in the container, or **LMB with empty hands**, takes it into pockets and selects it.
5. **The card** follows whatever you aim at: an item in a socket shows its card too.
6. **Close** with E. Lifting a cooler closes it automatically. Closed coolers and fridges refuse transfers.

**One item per click is deliberate:** it is the "вручную перекладывают" of the sales spec (SG-D16). If playtests find 8 clicks tedious, add Shift+LMB to move all organs of the aimed kind (§9.3).

**Sales surfaces:**
- **Buyer case (SG-D16/D71):** putting an organ in reserves it for the buyer (`LoadItem`); anyone can take it back out before the sale is confirmed. A confirmed sale retires the item and its socket empties with a short close animation (P13).
- **C01:** blood goes hand to hand. With a blood bag in hand, LMB on C01 offers it, and the negotiator confirms on the deal card.
- **Stash:** the same as the case. Depositing and the separate "Сдать" confirmation follow sales §8.3.

### 4.8 Van

- **Van shelf (12 slots):**
  - G while standing in the bay puts the item on the shelf;
  - a small item thrown into the bay that comes to rest inside the bay volume snaps to the shelf;
  - items are taken from the shelf with E, from inside the bay or through an open door within reach.
  - The shelf is uncooled.
- **Cooler mounts (2 in the stock van):** setting a cooler down inside the bay, or throwing one in, snaps it into a free mount. Opening it in place works.
  - With both mounts full: «Некуда поставить». A carried cooler stays in your hands; a thrown one stays a world object (the doors' existing blocking handles anything in the doorway).
- **Why not loose physics in the van:** there is no physics simulation of small items in a moving van. This avoids lost items and van-frame jitter (NETWORK §3.3) (**Q4**).
- **The driver** has no hotbar (doors on 1–4 and F as today).
- **Riding passengers** (NETWORK Q2 slots) keep the hotbar and can use tools on NPCs in the bay within reach (M3 acceptance).

### 4.9 Operating table

- The table keeps its own tool flow (1–4 in table mode). The hotbar is hidden in table mode.
- **The tray becomes the ledger container `tray:{tableId}`** (6 sockets). Extracted organs and filled bags live there as ledger items.
- **Table consumables become tray items:**
  - anesthetic vials and empty blood bags lie in the tray and are used from it;
  - `ServerAdmit` no longer refills them for each patient;
  - this ends the two pools (G3): field vials and bags can be put on the tray, and tray items can be taken to the field.
- **Leaving table mode** while holding an organ in the table hand puts it into pockets if there is room, otherwise back on the tray.

### 4.10 HUD

| Element | Content | Replaces |
|---|---|---|
| **Hotbar,** bottom centre | 6 slots of about 52 px. Each shows an icon (or the short label), a count badge, the organ's tier colour stripe and freshness bar, and a fill bar for syringes and bags. The selected slot is raised and outlined; empty hands show a small hand icon. It stays visible while it holds anything (no 3 s fade). | `InventoryHud` strip and the `CaptureHud` Z/X/C cards |
| **Item card,** above the hotbar | The selected or aimed item (table §4.5). The tier colours are the ops §12.1 palette. | `OperationHud` organ card (outside table mode) |
| **Hint line** | «ЛКМ (держать) — связать руки · G — положить» | Capture hint |
| **Crosshair ring** | Hold progress; anesthesia dose bar | Same as today |
| **Container label** | «Холодильник 5/8 · E — закрыть» | – |
| **Teammate label** | Aiming at a friend shows «держит: почка (Хорошее)» | – |
| **Toasts** | Refusal reasons («Карманы полны», «Сначала открой», «Кровь не набрать: дёргается») | Capture toasts |

### 4.11 Edge cases

| Case | Behaviour |
|---|---|
| **Arrest** (canon §80, ordinary street arrest) | The most valuable item in pockets or carry is confiscated (`MostValuableOf`), plus 10% from the shared fund (NETWORK Q4). The ops §19 inspection arrest stays separate. |
| **Knocked out** (future) | The item in hands drops; the pockets stay. |
| **Phone, table camera, buyer negotiation camera, driving** | The hotbar is inactive; the selection is remembered. |

---

## 5. Networking (FishNet 4.7.3, host-authoritative)

### 5.1 Components (Proposed)

| Component | Lives on | Role |
|---|---|---|
| `ItemServer` | `WorldNet` (server) | Owns the `ItemLedger`; settles spoilage at 1 Hz; spawns and despawns world items; bridges to `BuyerServer`; save hooks |
| `PlayerItems` | Player prefab (evolution of `NetworkInventory`; cash removed per NETWORK Q4) | Owner-only `SyncList<ItemView> pockets`; `SyncVar<byte> activeSlot` and `SyncVar<HeldView> held` for everyone; all player intents |
| `ContainerNet` | Cooler, fridge, tray, case, stash, return tray, van shelf and mounts | `SyncList<ItemView> contents`, `SyncVar<bool> open`, `SyncVar<bool> powered` |
| `WorldItemNet` | Loose item prefab (evolution of `WorldItem` + `OperationPhysicalItem`) | `SyncVar<string> ledgerId`, `SyncVar<ItemView> view`; server physics and impact detection; kinematic on clients |

`ItemView` is about 30 bytes:
- id;
- def id (ushort);
- count;
- tier;
- flags: packaged, cold, expired;
- fill byte;
- progress at anchor (ushort);
- rate class;
- anchor tick.

Clients extrapolate the freshness bar from the anchor and the rate class, the same way the `WorldClock` anchor works. They get no per-second updates.

### 5.2 Intents (all `ServerRpc(RequireOwnership = false)` on `PlayerItems`)

| Intent | Arguments | Server validation (NETWORK §3.0 item 3) | Effect |
|---|---|---|---|
| `SelectSlot` | slot 0–5, or 255 for empty hands | Owner; not driving, not carrying, not in the table camera | `activeSlot`, `held` |
| `Use` | pressId, phase (begin/hold/end), target NetworkObject, part, point | The active item's class allows this target. Reach 2.6 m from the **server's** copy of the player (from the slot when riding). Server raycast for line of sight. `CaptureRules` (asleep, restrained, dead). Stock present. | The hold streams like the table pointer (`(pressId, holding)` at 10–20 Hz, expiry 0.5 s); the server accumulates the time. On completion: rule effect, consumption and a cue. |
| `Secondary` | pressId, phase | The needed supply is in pockets (vial, empty bag, pouch); a free slot when one is needed | Ledger change: refill, transfer or pack |
| `Take` | requestId, container, slot | Open; reach 2.4 m; free pocket slot | `Move` to pockets |
| `Put` | requestId, container, slot or −1 | The active item is accepted; the container is open; reach | `Move` |
| `PickUp` | requestId, world item | Reach 2.5 m + 1.5 m tolerance (existing); free slot | Despawn the object; `Move` |
| `Drop` / `Throw` | requestId, slot, origin, dir, charge | Origin within 2.4 m of the eye; finite vectors (existing `ServerDrop` checks) | Spawn `WorldItemNet`; `Move` to World; impulse |
| `Place` | requestId, slot, point, normal | Reach, line of sight, a surface | Gentle spawn at the point |
| `SetOpen` | container, open (explicit state, never a toggle) | Reach; not carried | `ledger.SetOpen` |
| `Carry` begin / end / throw | – | One two-handed carry per player | The existing `CaptureCorpseHands` / `NetworkPhysicsBody` path + `Move` to Carried or World |

**Replies:**
- Refusals go back as `TargetRpc` hint ids (the Capture toast pattern).
- Successes are `ObserversRpc` cues on the source object: zip, inject, squelch into the cooler, lid, splash.

**Idempotency:**
- Request ids are monotonic per player.
- The ledger keeps the last 64 results per player, so a repeated request returns the first result and never moves twice.
- Organ minting is idempotent by extraction id.
- Sales confirmation stays idempotent by `ConfirmationId` (buyers core).

**Races.** Server RPCs are processed in order:
- The first of two "take the same kidney" requests wins; the second gets «Уже забрали».
- The first of two "put into the last slot" requests wins; the second gets «Нет места».
- A sale confirmation and a teammate pulling an organ out of the case: whichever reaches the host first wins. The ledger move out of the case happens only if the buyers core unload succeeds, and a confirmed sale retires the item before the next RPC.

### 5.3 What each client sees

| Data | Who receives it |
|---|---|
| Own pockets (all 6 slots, full detail) | The owner only (owner-only SyncList) |
| A teammate's held item (def, tier colour, fill) and his active slot | Everyone; it drives the third-person hand model and the aim label |
| A teammate's other pockets | Nobody (not needed; less UI noise) |
| Container contents and open state | Observers of the container (FishNet distance range of 200 m). The cooler, case and tray show their socket models. |
| Loose items | Observers, as `WorldItemNet` NetworkObjects (a NetworkTransform while moving, nothing at rest) |
| Tier changes | They arrive with the view of the item's place; the live buyer card re-quotes on tier changes only (sales review U6) |
| Private data | None. Scan results stay per player (sales K11), outside the ledger. |

### 5.4 Join, leave, host leaves

- **Late join:** container SyncLists and world items arrive in the spawn payloads. The joining player's `pockets:{playerId}` is found by `ov.playerId` (NETWORK Q5) and mirrored to him; a new player gets an empty pocket set and the start kit rule (§6.3).
- **A client leaves** (**Q5**):
  - The server releases his carry.
  - **Team merchandise** (organs, blood bags, filled syringes, his carried cooler) drops into the world at his last server position. If he was in the bay, it goes onto the van shelf and mounts where they have room.
  - **His tools and consumables** stay in `pockets:{playerId}` in the save, so he gets them back on rejoin.
- **The host leaves:** the session ends (NETWORK Q8). The host autosaves the ledger on quit and every 60 s.

### 5.5 Bandwidth and CPU

- **Pocket and container lists** change only on transfers, and send about 30 B per changed entry.
- **Tier changes:** with 100 organs at the room rate, one every 3 s on average.
- **Loose items at rest** send nothing.
- **Total:** below 0.5 KB/s per client in busy scenes. That is negligible against the ragdoll and van budgets (NETWORK §4).
- **CPU:** a 1 Hz settle over a few hundred records is negligible.

### 5.6 Fit with the network plan

- **NETWORK §3.4** deferred the field kit stock ("owner-only SyncVars … or consumable items in `NetworkInventory`, decided at M9"). This spec decides it now: **consumable items in the ledger**, used through intents.
- **M4's `RequestTie`/`RequestDose`/`RequestBlood`** become `Use` with the active item. Their validation rules are unchanged.
- **M1 ends the "two inventories" problem:** `PlayerItems` replaces both `LocalInventory` (map hotbar) and the physical-carry use of `NetworkInventory` on `Player_Map_Net_v01`.
- **NETWORK §3.9:** cash leaves the inventory. Purchases (`ServerRpc Purchase(itemId, txId)`) mint ledger items into the buyer's pockets, or into a delivery crate for large equipment (ops §15.5).

---

## 6. Save format and migration

### 6.1 Save v2

- **The ledger is part of the world block** of save v2 (NETWORK §3.8; `CaptureSaveData` revision 2). It is written by the host only, with the existing atomic `.tmp` → replace → `.bak`.
- **One ledger for all items, including pockets.** The per-player block keeps only the selection, so item data is never duplicated.

```json
{
  "version": 2,
  "items": {
    "version": 1,
    "nextSeq": 214,
    "activeSeconds": 18432.5,
    "items": [
      { "Id": "P-3f9a1c0b2e/kidney/0", "DefId": 102, "Count": 1, "Place": 1,
        "ContainerId": "I-000031", "Slot": 2, "CarrierId": "",
        "HasOrgan": true,
        "Organ": { "Kind": 0, "Tier": 3, "Progress": 0.41, "SettledAt": 18432.5,
                   "DonorPatientId": "P-3f9a1c0b2e", "DonorPersonId": "NPC-KHUTOR-BODYBUILDER-01",
                   "DonorRoleKey": "HAMLET_BODYBUILDER", "DonorNpcType": "HAMLET_BODYBUILDER",
                   "ExtractedAtGameSeconds": 113400, "Packaged": true,
                   "ColdSince": 17900.0, "LastColdStint": 0, "WarmSince": -1,
                   "CaseColdLatch": false, "LastImpactAt": -1e9 },
        "HasFill": false, "Revision": 7 },
      { "Id": "I-000031", "DefId": 301, "Count": 1, "Place": 1,
        "ContainerId": "vanmount:van01:0", "Slot": 0, "HasOrgan": false, "HasFill": false },
      { "Id": "I-000012", "DefId": 114, "Count": 6, "Place": 1,
        "ContainerId": "pockets:7c1e…", "Slot": 0, "HasOrgan": false, "HasFill": false }
    ],
    "containers": [
      { "Id": "pockets:7c1e…", "Kind": 0, "OwnerId": "7c1e…", "Capacity": 6, "Open": true,
        "Slots": ["I-000012", "", "", "", "", ""] },
      { "Id": "I-000031", "Kind": 3, "OwnerId": "I-000031", "Capacity": 8, "Open": false,
        "Slots": ["", "", "P-3f9a1c0b2e/kidney/0", "", "", "", "", ""] }
    ],
    "retiredIds": ["I-000004", "P-0a11b2c3d4/liver/0"]
  },
  "itemPoses": [ { "id": "I-000077", "position": [12.1, 0.4, -88.0], "rotation": [0, 0, 0, 1] } ],
  "players": [ { "playerId": "7c1e…", "activeSlot": 0 } ]
}
```

**Rules:**
- **`itemPoses`** hold World items and placed coolers. Items in containers have no pose; the container places them.
- **Time.** `activeSeconds` is the spoilage clock. On load it continues from that value: there is no offline time (ops §14, D13).
- **Retired ids** are kept forever, like the buyers core keeps sale tombstones, so a reload or a repeated network request cannot recreate a sold organ.
- **Containers come back by id.** Fridges and trays are restored by their stable ids from the scene. Cases, stashes and return trays come back with the buyer snapshot that owns their meeting or order.
- **JsonUtility:** null strings in `Slots` come back as `""`. The restore self-heals any slot or record mismatch, and an orphaned record goes to the world at its last pose (the prototype implements this).

### 6.2 Migration v1 → v2 (runs once on loading a v1 file)

| v1 field (`CaptureSaveData` v1) | v2 result |
|---|---|
| `kit.ties` | Zip-tie stack (114) in the host's pockets |
| `kit.anesthesiaBarrel` | Anesthesia syringe (112), `Fill.Amount` = barrel, formula 0 |
| `kit.anesthesiaStock` | Anesthetic vial (113), `Amount` = stock, if > 0 |
| `kit.bloodFill` | Blood syringe (111), `Amount` = fill, donor unknown, `FilledAt` = load time |
| `kit.bloodBags` (counter) | N sealed blood bags (110), donor unknown. They become sellable for the first time. |
| `kit.tool` | The host's `activeSlot` = the slot of the matching item |
| `bodyBags` | Body bag stack (202) in the host's pockets |
| `table.items` kind 0/1 | Organ records with the **same id**, `tier = grade + 1`, `Progress` 0, minted into the World at the saved pose. The Unity adapter then moves any within 7 cm of a tray socket (the table's own `SlotFree` test) into the tray container. |
| `table.items` kind 2 | Blood bag (110), donor = the id prefix |
| `table.items` kind 3 | Intro syringe (109) with `Amount` 1, or 0 if `expired` |
| `table.anesthesiaStock`, `anesthesiaBarrel`, `bloodFill`, `bagsUsedMask` | Tray items: a vial with the stock, empty bags = `bloodBagCount` − used. A partly filled table syringe stays a table tool. |
| Hotbar (`LocalInventory`, not saved in v1) | Nothing to migrate. If a dev save has stacks, organs become instances with the tier nearest to `UnitValue` (`TierFromValue`). |
| Corpses, bagged corpses, NPCs, van | Unchanged (they are not items) |
| `ClinicSave.money`, `LocalInventory.Cash` | Not item data: they go to the shared fund at M9 (NETWORK Q4) |

- **Overflow.** More than 6 items for the pockets go to the world at the player's position. The migration report lists them, and they are written to the log.
- **The v1 file is kept** as `capture_stageA_v01.v1.bak`, and only v2 is written afterwards.
- **Tested** in the prototype: 12 items minted, 4 overflowed, no warnings.

### 6.3 Start kit and restock

- **Today** `RestockAtBase()` refills the field kit for free. That stays as a **dev and prototype rule** until shops exist: at the base shed, E on the supply crate tops a player's pockets up to the start kit, minting items.
- **Start kit:** 10 ties, 1 anesthesia syringe, 1 vial, 1 blood syringe, 2 empty blood bags, 2 body bags.
- **When the economy lands,** the crate becomes the pharmacy and phone orders (ops §15.5) and minting goes through `Purchase`.

---

## 7. Spoilage and quality hooks

### 7.1 Rules (numbers are placeholders; prices and economy come later)

| Hook | Rule | Value | Source |
|---|---|---|---|
| Room: pockets, hands, world, tray, van shelf, case, stash, return tray | −1 tier per active interval | 300 s | ops §13.2 |
| Portable cooler | −1 tier per interval | 1500 s | ops §13.2 |
| Powered fridge | Paused | – | ops §13.2 |
| Unpowered fridge (electricity expired) | Room rate; settled at the moment power changes | 300 s | ops §13.2, §14 |
| Fractional progress across moves | Kept; only the rate changes | – | ops T-05 |
| Floor | Damaged (tier 1); no sixth tier | – | ops §12.2 |
| Impact | −1 tier per event above 2.4 m/s, cooldown 0.6 s | existing `OperationTuning` | ops §12.2 |
| Thrown cooler | Each organ inside −1 when the cooler hits above 4 m/s | 4 m/s | Proposed (Q2) |
| Packaging | No effect on spoilage | – | ops §13.1 |
| Sealed blood bag | No tier, no spoilage, no cooling needed; still uses a slot | – | ops §5.2, §13.2 |
| Unsealed syringe blood | Expires 120 s after drawing unless bagged. It can then only be squirted out (RMB). | 120 s | ops T-06, `unsealedBloodSeconds` |
| Organ taken from a corpse | Keeps its current tier. Progress = the elapsed fraction of the current 40 s corpse interval (0 during the 45 s grace), then the item rates apply. | – | ops §12.3, §9; the conversion is Proposed |
| Intrinsic tier, condition loss, table damage | Applied before minting (capture §6, ops §12.2) | – | Existing rules |
| Cooled delivery | See §7.3 | 60 s / 60 s | BUYERS v02, sales review S4; Proposed |
| Value for the UI and arrest | `base × tier multiplier` (0.3/1/1.6/2.6/4.2). Real sale prices come from the buyers core. | – | ops §15.2 |

### 7.2 Evaluation

- **Lazy settling.** Each organ stores `Tier`, `Progress` and `SettledAt`. On any move, power change, impact, query or 1 Hz tick, the server settles it:
  - `Progress += Δt / secondsPerGrade(storage)`;
  - while `Progress ≥ 1` and the tier is above Damaged: drop one tier and subtract 1.
- **Every drop raises `TierChanged`,** stamped with its exact time. `ItemServer` updates the view, calls `BuyerRules.UpdateQuality`, and the live deal card re-quotes (SG-32).
- **`NextGradeLossAt`** gives the exact next loss time for UI anchors and scheduling.

### 7.3 Cold chain → `DeliveredCooled`

- **When an organ goes into a buyer case,** the latch is set if:
  - it had been cold for at least **60 s** before it left the cold store (no flash-cooling right at the buyer);
  - **and** it is still cold, or left the cold store at most **60 s** ago (the hand carry from the cooler to the case, SG-D16).
- **While in the case** the item is warm (the case is uncooled, sales §6.3), but the latch stays. Inspection does not clear it (BUY-11).
- **Taking it out of the case** clears the latch; a later load is evaluated again. That covers the office-to-outing transfer of sales §4.4 item 6.
- **Who decides:** the buyers core reads `DeliveredCooled` from the adapter. The price effect (×0.9 when not cooled) stays the buyers core's.

### 7.4 Changes the buyers core needs (input to sales work package B)

| Need | Why |
|---|---|
| `UnloadItem(buyerId, itemId)` | A teammate takes an unsold organ out of the open case (SG-D71). There is a stash withdraw but no meeting unload. |
| `SetDeliveredCooled(itemId, bool)`, or a cooled argument on `LoadItem` | The latch is known only at load time; `RegisterItem` happens much earlier, at extraction |
| `RemoveItem(itemId)` | An unsold item destroyed outside a sale (disposal, confiscation) must leave the core's item list |
| Register through a host or team holder id | `RegisterItem` requires a present participant as holder. Items in team containers report the host id. |
| `SourceNpcId` = `DonorRoleKey` when set, else `DonorPatientId` | The twin-brother rule |

---

## 8. Implementation plan

### 8.1 Packages

**Sizes:**
- S: about 1 agent-day;
- M: 2–4;
- L: 5–8.

**Owners:**
- Claude: server, network and core;
- GPT: data, UI and text from a detailed brief.

**Unity:**
- "pure" means engine-free C# in staging;
- "Unity" needs Assets and the editor.

| WI | Content | Size | Owner | Unity? | Depends on | M-step |
|---|---|---|---|---|---|---|
| **A** | Decisions: the lead adopts the Proposed presets; Fedya answers Q1–Q5 | S | Lead | – | – | Now |
| **B** | **Items core:** ledger, definitions, spoilage, cold chain, impacts, receipts, save DTO, migration. The prototype exists (§11, 37 checks). Remaining: port the checks to NUnit in the Buyers-style staging project, add the corpse-progress conversion, review. | M (prototype done, S left) | Claude | Pure; moves to `Assets/OnlyVolunteers/Items/Core/` (no FishNet, no UnityEngine) after G35 is accepted | A | Now (staging) |
| **C** | **Item data:** `ItemDefinition` fields (class, stack, two-handed, container slots, organ kind); assets 111–117 and 301; `ItemDatabase` entries for 109, 110 and 202; RU/EN names, hint lines and refusal toasts; icon list; `WorkItemTuning` asset | S–M | **GPT** | Drafts now in `docs/drafts`; assets after G35 | B schema | Now (drafts) |
| **D** | **`ItemServer` + `PlayerItems`** (evolve `NetworkInventory`, drop its cash): intents, request ids, the owner pockets SyncList, held view, `WorldItemNet` (merge `WorldItem` and `OperationPhysicalItem`), pick up, drop, throw, place, impacts → ledger | L | Claude | Unity | B | Solo host first (i10 already runs a solo FishNet host); co-op at **M1** |
| **E** | **Hotbar UX:** an input map on the `OpsInput` OR-wrapper (1–6, wheel, G and hold G, LMB/RMB, E and hold E); arbitration with grabbers, phone, table, van and carry; HUD (hotbar, item card, rings, labels) replacing the CaptureHud cards and the InventoryHud strip; first-person view models and remote hand sockets | M | Mixed: Claude input arbitration (S–M); **GPT** HUD layout, icons and view-model placement from a brief (M) | Unity | D | With **M0** input wrapper, M1 |
| **F** | **Field tools as items:** `CaptureFieldKit` reads and consumes ledger items; LMB hold use; RMB refill and transfer; the blood syringe → bag; the body bag item replaces hold R; per-player stock; restock crate | M | Claude | Unity | D, E | Solo now; co-op at **M4** (`RequestTie`/`Dose`/`Blood` → `Use`) |
| **G** | **Containers:** cooler prefab (COOLER v03 after Fedya's OK: lid, 8 sockets, two-handed carry and throw on `NetworkPhysicsBody`); fridge (24 sockets, the power hook as a stub until bills exist); table tray → ledger (6 sockets, table stock as tray items); van shelf and 2 mounts | L | Mixed: Claude ledger and net hooks (M); **GPT** prefab and socket builders, art import (M) | Unity | D; van parts after M3/M5 | Solo, then **M5** for the moving van |
| **H** | **Packaging and blood:** organ pouch (ORGANBAG v01 art), the RMB pack action and model swap; sealed bag; intro syringe sale identity `{id}#{FillSeq}`; 120 s expiry | S–M | Claude rules (S) + GPT visuals (S) | Unity | F, G | Before sales Stage A |
| **I** | **Save v2 + migration:** the ledger in the world block, item poses, per-player `activeSlot`, v1 → v2 with `.v1.bak` | M | Claude | Unity (pure DTOs in B) | B, D | Solo save now; per-player blocks at **M9** |
| **J** | **Sales bridge:** `BuyerItemState` projection (register, quality, load and unload, deposit and withdraw, remove); buyer case, stash and return tray containers; the cooled latch; the core API additions of §7.4 | M | Claude | Unity + pure core changes | B, sales WP B/H | **M9** (with `BuyerServer`) |
| **K** | **Identity:** `PersonId` and role key carried from authored NPCs through `CaptureFacts`/`OperationState` into organ provenance | S here (M in sales F) | Claude | Unity | Sales WP F | After M1 |
| **L** | **Tests:** EditMode (ledger checks), PlayMode real input (hotbar select, LMB tie/inject/draw, cooler open and transfer, throw damage, save and reload), two-process `net-items-*` (pickup race, cooler race, leave-drop, late join with an open cooler) | M | Claude; GPT may draft case lists | Both | Each package | Every milestone |

### 8.2 Order and critical path

1. **Now, with no writes to Assets/:** A; B (port to NUnit in staging); C drafts; ask Fedya for the visual OK on the cooler v03, organ bag v01 and fridge.
2. **After G35 is accepted and the in-progress first pass is reviewed:** B moves into Assets, then D → E → F on the solo host. That gives the playable "tools are items, LMB use" slice with real per-instance organs and saves (G1–G8).
3. Then G (the cooler first, the tray, the fridge), H and I (solo save v2).
4. **Network steps:**
   - **M1:** `PlayerItems` on the networked player.
   - **M3/M4:** riding and co-op tool use.
   - **M5:** van shelf and mounts in the moving van.
   - **M8:** `WorldClock.ActiveSeconds` replaces `ItemServer`'s own saved accumulator.
   - **M9:** co-op save blocks, purchases and the J sales bridge.
5. **Sales Stage A needs** B, D, F (blood), G (cooler, case, stash, return tray), H (pouch), I, J and K.

**Critical path: B → D → G → J.**
- It is the sales review's work package E: this spec is its design.
- It sits under M9 together with `BuyerServer`: do not build a second inventory adapter for sales.

### 8.3 Who does what

- **Claude:** everything that decides state or crosses the network. That is the ledger, intents and validation, spawn and despawn, races, save and migration, the buyers bridge, and input arbitration.
- **GPT** works from detailed briefs that give exact ids, fields and screenshots of the existing HUD:
  - item definition assets and database entries;
  - RU/EN texts and toasts;
  - the hotbar and card layout;
  - icons;
  - socket placement on the cooler, fridge and tray;
  - prefab builders;
  - art import of the approved props.
  
  No human animation work goes to GPT.
- **Unity access** follows the shared lock rules. There is no Unity work during Fedya's playtests.

### 8.4 Fit with the first pass being built now

The other agent is moving the Z/X/C tools into hotbar items with LMB use. To keep that work:
- **Keep its input and HUD** where they match §4.3–§4.5. Adjust them when they differ (empty hands = same key again; RMB is the secondary action).
- **Do not add new count fields to `FieldKitSave` or `ItemStack`.** Every count added now needs a migration row later.
- **WI-D/F replace only the storage underneath.** The tools then read and consume ledger items instead of `CaptureFieldKit` counters or `ItemStack`s.
- **The lead should diff the first pass against this spec** before WI-D starts. This document was written without seeing that code.

---

## 9. Acceptance checks, rules and parked ideas

### 9.1 Acceptance checks (future verification)

| ID | Check |
|---|---|
| WI-01 | Extracting the same kidney twice (double click, two players) creates one item with the extraction id |
| WI-02 | 6 pocket slots: ties stack, organs never stack; a 7th item is refused with «Карманы полны» |
| WI-03 | Selecting the same slot again gives empty hands, and LMB drags a body as before |
| WI-04 | LMB hold with ties on the arms ties the hands, and one tie is used. On the legs it ties the feet. Releasing early uses nothing. |
| WI-05 | The anesthesia syringe injects with LMB anywhere (D1); RMB refills from a vial; mixing formulas is refused |
| WI-06 | The blood syringe draws only from a sleeping, knocked-out or restrained living NPC. RMB fills an empty bag, and the sealed bag records the donor. Unsealed blood expires at 120 s. |
| WI-07 | An organ in pockets loses 1 tier at 300 active seconds; in a cooler at 1500; in a powered fridge never. Moving keeps the fractional progress. Nothing restores quality. |
| WI-08 | Quitting with organs in a cooler and reloading gives the same tiers and progress; no offline time passed |
| WI-09 | A cooler is carried with both hands, the hotbar is disabled, lifting closes the lid, and a carried cooler cannot be opened |
| WI-10 | A thrown organ above 2.4 m/s loses 1 tier once per impact. A thrown cooler above 4 m/s costs each organ inside 1 tier. |
| WI-11 | Cooler (≥ 60 s) → hand (≤ 60 s) → case is delivered cooled. Pockets the whole way are not. Flash-cooling for 10 s is not. |
| WI-12 | Putting into the open buyer case reserves; a teammate takes it out before confirmation and the sum updates (SG-21); a confirmed item is gone and its id is retired |
| WI-13 | The bodybuilder's kidney and the twin's kidney both match the order via the role key; another bodybuilder's kidney does not |
| WI-14 | The packing RMB uses one pouch and marks the organ packaged; its spoilage rate is unchanged |
| WI-15 | The van shelf takes small items dropped in the bay; 2 coolers snap to mounts; nothing moves while driving at 60 km/h; a third cooler is refused |
| WI-16 | Co-op: two players take the same kidney in one tick: exactly one gets it. Two put into the last cooler slot: exactly one fits. |
| WI-17 | A client leaves holding a kidney, a blood bag and a carried cooler: they drop at his position; his syringe and ties come back when he rejoins |
| WI-18 | A late joiner sees the open cooler's contents, the loose organs and teammates' held items correctly |
| WI-19 | The host sees each cue once; a client never writes a save |
| WI-20 | A v1 save loads into v2: ties, syringes, bags and table organs exist as items with converted tiers; overflow lies at the player |
| WI-21 | A street arrest confiscates the most valuable pocket or carried item and nothing else |

### 9.2 Explicit non-goals (v1)

- No inventory screen or grid, weight system, durability, sterilisation or per-player cash.
- No taking items from a teammate's pockets.
- No loose-physics clutter in the van.
- No temperature minigame (ops §2).
- No new prices.

### 9.3 Parked ideas (fun, later, only if playtests ask)

- Catching a thrown organ: a teammate with empty hands holding LMB catches it within about 0.6 m.
- E on a teammate gives him the item in your hands.
- Shift+LMB moves all organs of one kind between open containers.
- Q with an organ in hand slaps with the organ: the same stun, and the organ loses a tier.

---

## 10. Вопросы к Феде (максимум 5)

**1. Карманов 6?**
Клавиши 1–6 и колесо. Каждый орган занимает целый слот. Стяжки, пакеты и мешки лежат пачкой в одном слоте. Если хочется больше органов с собой — бери холодильник.
**Рекомендую: да, 6.**

**2. Холодильник — только двумя руками?**
Пока несёшь холодильник, инструменты в руки не взять. Его можно бросить, но органы внутри от сильного удара потеряют по ступени.
**Рекомендую: да, двумя руками, и бросок бьёт органы.**

**3. Тащить тело и колоть его одновременно одному — оставляем?**
Сейчас можно: ЛКМ держит тело, ПКМ колет. Предлагаю проще: инструмент в руках + ЛКМ = применить, а тащить можно только пустыми руками. Держать тело — работа для друга. Одному: сначала вырубить (Q), потом колоть.
**Рекомендую: без такого комбо.**

**4. Вещи в бусике — аккуратная полка или куча?**
Вариант А: полка на 12 мелких вещей и 2 гнезда под холодильники. На ходу ничего не катается и не выпадает.
Вариант Б: всё валяется физически. Это смешнее, но органы будут биться и вылетать в двери.
**Рекомендую: А, полка.**

**5. Друг вышел из игры с органами в карманах — что с ними?**
Предлагаю: товар (органы, кровь, холодильник в руках) падает на землю там, где он стоял. Его инструменты и расходники остаются у него и вернутся, когда он зайдёт снова.
**Рекомендую: так.**

---

## 11. Prototype and verification of this document

**Prototype** (pure C#, netstandard2.1, C# 9, warnings as errors; no Unity, no FishNet, no NuGet). It lives in `C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\`.

**Source files:**
- `src\ItemCoreTypes.cs`: classes, definitions, `ItemRecord`, `OrganData`, `FillData`, containers, `WorkItemTuning`;
- `src\ItemLedger.cs`: the ledger: containers, mint and `MintOrgan` (idempotent), move/split/merge with per-actor request receipts, consume and retire, lazy spoilage, cold chain and case latch, impacts, leave-drop, arrest value, snapshot and restore with self-heal;
- `src\LegacyMigration.cs`: v1 → v2 mapping of §6.2;
- `selftest\Program.cs`: 37 console checks.

**Run:**
```
dotnet run -c Release --project C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\selftest
```
Result on 2026-10-18 with .NET SDK 8.0.425: **RESULT PASS 37/37**.

**Coverage.** The checks cover:
- id idempotency;
- pocket limits and stacking;
- the 300/1500/∞ rates and the exact loss times;
- progress carried across moves;
- the closed or carried cooler;
- two-handed rules;
- request dedup;
- the cold-chain cases;
- fridge power;
- impacts and the thrown cooler;
- consumption;
- leave-drop;
- arrest choice;
- the save round trip;
- migration.

**Not done:**
- no Unity compile of the prototype (it uses only BCL types compatible with Unity's C# 9);
- no NUnit port;
- no network code;
- no playtest.

**Document checks:**
- every cited spec and code path was read on 2026-10-18;
- the existing ids, fields and keys in §2 come from the code;
- all numbers marked "ops" match OPERATIONS v01 §12–§14 and `OperationTuning`.

**Files created by this task:** this file, plus the four prototype sources and two `.csproj` files in the staging folder. Build output was deleted after the run; `dotnet run` rebuilds it. Nothing under `Assets/` was changed, Unity was not opened, and nothing was staged or committed.

---

## Decisions (Fedya, 2026-10-18) — answers to §10 Q1–Q5. These override the Proposed text above.

1. **6 pocket slots — yes.** Plus: helper tools (zip ties, blood bags, body bags, syringes) may share ONE "kit" slot. Pressing that slot's number repeatedly **cycles** through the tools in it (ties → anaesthesia syringe → blood syringe → bags → body bags …), each acting as its own tool in hand; one more press after the last tool = empty hands. (Replaces "same key again = empty hands" for multi-tool slots; for single-item slots the same key again still empties the hands.)
2. **Cooler: two hands only — yes.** While carrying it no tool can be in hand. Throwing it damages the organs inside (as proposed).
3. **No "hold body with LMB + inject with RMB" combo — removed.** Tool in hand + LMB = use; dragging/holding a body only with empty hands.
4. **Van shelf is a PURCHASED van upgrade.** Items placed on it are attached/fixed and cannot fall off while driving (or the shelf is a closed cabinet — exact form decided later). Without the shelf, things in the cargo area are ordinary loose physical objects. 2 cooler mounts: same upgrade unless decided otherwise.
5. **A player who leaves keeps his ENTIRE inventory — nothing drops.** The host save stores each player's pockets (and anything in his hands, incl. a carried cooler with its contents) keyed by the player's persistent id; on rejoin he gets everything back exactly. While he is away those items are simply not in the world (the team can't use them). Remove the "leave-drop" behaviour from the ledger, tests and §5.4.
6. **Charged throw, game-wide (Fedya, 2026-10-18):** throwing any object is charged — the longer the throw key is held, the stronger the throw (tap = gentle toss; full charge ≈1–1.2 s; heavier items reach a lower max). One shared helper for all throw sites; the client sends charge 0..1, the server clamps and applies the velocity.
