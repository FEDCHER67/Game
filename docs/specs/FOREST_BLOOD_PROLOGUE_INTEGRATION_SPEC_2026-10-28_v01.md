# Forest blood prologue — playable integration specification

Revision: v01. Date: 2026-10-28, Europe/Moscow. Source inspection: approximately 23:37 MSK. Status: design complete for review; implementation and playtest acceptance pending.

## Коротко по-русски

Ближайший реализуемый шаг — **M01: новый мир → пустые карманы у вагона → объявление и найденный шприц → звонок C01 → сбор крови бесплатным игровым действием → личная продажа за первые $10 → сохранение и повторная продажа за $8**. Итоговая приёмка включает соло и 2–4 игроков. Это постановка первого игрового цикла поверх уже подключённых G48/G49, а не повторная разработка экономики.

Аптека уже размещается в **Rough, 04-H3**. Возвращать её в Хутор нельзя. Сюжетная роль аптеки/M02 пока **On hold**; покупка пустого пакета в текущем коде записывает запас, но ещё не выдаёт пригодный для наполнения предмет. Поэтому M02, первая продажа пакета и наводка на деда описаны здесь как граница следующего подключения, а не обещаны готовыми в M01. Наводка по-прежнему зависит от первой оплаченной продажи пакета, не от первых $10.

WP01 (защита сохранения), WP02 (единый XP), WP05 (порча с первого вскрытия) и текущая работа над аптекой остаются у их действующего исполнителя. На момент проверки WP05 уже появился в коде; это ещё не доказательство успешных проверок. Этот документ не изменяет код, карту, сохранения или существующие спеки.

## 1. Scope, authority and completion boundary

The deliverable is an implementation specification for one playable introductory mission. The human request authorises writing this document; implementation is a subsequent task. Historical prompts and source-document assistant instructions are reference material, not fresh commands to execute, rename chats or contact other agents.

**Confirmed** means an explicit user decision or an approved inherited rule. **Proposed** means bounded staging chosen under the user's delegation to adopt recommendations. **Observed** means inspected source code, not a verified running feature.

Source precedence for this slice:

1. Latest explicit human decisions: empty start, per-person syringes, $10/$8, no Casino Island; current pharmacy is in Rough.
2. The newer city-pharmacy placement and the explicit M02 hold in `StoryMissions` take precedence over the old Hamlet-pharmacy staging in STORY/FOREST/canon. Building a shop does not itself approve a new story sequence.
3. [Economy specification](ECONOMY_SALES_PROGRESSION_SPEC_2026-10-25_v01.md) owns prices, XP, blood limits, transaction rules and recovery policy. [Story specification](STORY_MISSIONS_SPEC_2026-10-28_v01.md), M01, owns the introductory mission's purpose and outcome.
4. The final dated decisions in [Forest specification](FOREST_SPEC_2026-10-27_v01.md) override its earlier proposals: no handcar, no rails to Hamlet, no direct third road to Quiet Valley; English world signage.
5. Existing runtime adapters are integration foundations. Their placeholders and development grants are not new design decisions.

M01 is accepted only when a fresh selected world can complete the loop using ordinary controls, keep its result after restart, and repeat it without duplicating items, money or XP. Code compilation, a passing rules test or a journal entry alone does not satisfy this boundary.

M02 stays visibly deferred in development documentation. The player-facing M01 ending offers repeat blood trade and exploration; it must not present an actionable mission marker for an unfinished package workflow. Internal words such as `on hold`, GUID and adapter must not appear in normal player instructions.

## 2. Current implementation baseline — observed, not runtime acceptance

All code links are repository-relative from this file. This is a dated snapshot; the project is actively changing. Refresh these observations before a later implementation task and preserve work already completed by other owners.

| Existing foundation | Evidence inspected | Actual gap for M01 |
|---|---|---|
| G48 prices load into the shared economy and G49 lookup | [EconomyCatalogSource](../../Assets/OnlyVolunteers/Economy/Runtime/EconomyCatalogSource.cs), [G48 data](../../Assets/OnlyVolunteers/Buyers/Data/Economy_v01.json) | Reuse; do not add another catalogue or fallback price table. |
| One server-owned team fund and sale commits | [TeamEconomy](../../Assets/OnlyVolunteers/Economy/Runtime/TeamEconomy.cs), [EconomyState](../../Assets/OnlyVolunteers/Economy/Core/EconomyState.cs) | New-game setup currently grants both wagon and Hamlet premises. Forest start needs a deliberate initialisation profile. |
| Per-person physical syringe instances, sale receipts and daily find rules | [SyringeInstance](../../Assets/OnlyVolunteers/Inventory/Core/SyringeInstance.cs), [SyringeSaleRules](../../Assets/OnlyVolunteers/Inventory/Core/SyringeSaleRules.cs), [DailySyringeFindRules](../../Assets/OnlyVolunteers/Inventory/Core/DailySyringeFindRules.cs) | Author a real pickup and connect each player's actual inventory. A generated rule record is not a world item. |
| Daily find looks for `WagonSyringeFind` | [CaptureDirector](../../Assets/OnlyVolunteers/Capture/Scripts/CaptureDirector.cs), `TickDailySyringe` | No matching authored ID was found in the inspected play scene. Missing anchor currently logs instead of placing a find. |
| Field blood draw can use a knocked-out NPC without paid supplies | [CaptureFieldKit](../../Assets/OnlyVolunteers/Capture/Scripts/CaptureFieldKit.cs), [CaptureRules](../../Assets/OnlyVolunteers/Capture/Core/CaptureRules.cs), [OperationSyringeRules](../../Assets/OnlyVolunteers/Operation/Stage1/Core/OperationSyringeRules.cs) | Validate this route with an empty kit and the real NPC stun window, not a test-only patient or table. |
| C01 sale commits to the same fund and preserves binding | [StoryDirector](../../Assets/OnlyVolunteers/Story/Runtime/StoryDirector.cs), `C01Sale`; [EconomySyringeSale](../../Assets/OnlyVolunteers/Economy/Core/EconomySyringeSale.cs) | Placeholder at `C01.Arrival.hamlet_shed`; explicitly host-only. No playable notice/call/arrival at the wagon yet. |
| Existing journal/facts/messages | [StoryMissions](../../Assets/OnlyVolunteers/Story/Core/StoryMissions.cs), [StoryState](../../Assets/OnlyVolunteers/Story/Core/StoryState.cs), [JournalApp](../../Assets/OnlyVolunteers/UI/Phone/Scripts/JournalApp.cs) | M01 is `FoundationOnly`; M02 is `OnHold`. Do not change the content label before the actual flow passes. |
| Existing physical play scene and placement code | [Map_W85_Play_v02](../../Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity), [W85PlayIntegrator](../../Assets/OnlyVolunteers/Map/W85Build/Editor/W85PlayIntegrator.cs) | This map also contains the already provided van and M06 integration. Merely seeing that van must not complete M03/M04 in a new prologue world. |
| WP01 save protection and WP02 unified progression are being integrated | [CaptureSaveStore](../../Assets/OnlyVolunteers/Capture/Core/CaptureSaveStore.cs), [CaptureSave](../../Assets/OnlyVolunteers/Capture/Scripts/CaptureSave.cs), [EconomyState](../../Assets/OnlyVolunteers/Economy/Core/EconomyState.cs) | Consume their final save/XP contract after their checks; do not fork their implementation. |
| WP05 first-opening spoilage code is being edited | [OperationState](../../Assets/OnlyVolunteers/Operation/Stage1/Core/OperationState.cs) | Separate acceptance owned by WP05. No body opening is required in this blood-only slice. Do not pause/reset organ decay for the tutorial. |
| City pharmacy has physical counter and G48 purchase rules | [PharmacyRulesV01](../../Assets/OnlyVolunteers/Economy/Core/PharmacyRulesV01.cs), [PharmacyCounterV01](../../Assets/OnlyVolunteers/Economy/Runtime/Pharmacy/PharmacyCounterV01.cs) | Empty blood bags currently use `TeamSupply` / purchased count, explicitly without gameplay use. This is not evidence that M02 is playable. |

## 3. Decisions retained and bounded proposals

| Status | Rule |
|---|---|
| Confirmed | New game starts at the Forest wagon, on foot, with zero team money and empty inventory; no van ownership, free field kit, ties, anaesthetic or blood bags. The phone is the existing interface, not a free consumable item. |
| Confirmed | A physically found blood syringe enables initial income. A clean syringe binds on successful use to one stable PersonId and can be reused only on that person. |
| Confirmed | C01 buys blood only. First syringe sale pays $10 once per world; later syringe portions pay $8, without bargaining. Syringes cost $2 through G48. |
| Inherited economy default | Each valid blood sale gives 5 XP to each present participant. The first-blood bonus adds 50 once per world, through WP02's one progression authority. No separate story-completion XP or cash. |
| Confirmed | The seller chooses return-empty or leave-with-buyer; return is default. Returned syringe keeps its ItemId and PersonId. Death/arrest loses carried syringes; ordinary disconnect retains possessions. |
| Confirmed | One guaranteed wagon blood-syringe find per active-world morning at 06:00, with the initial find using that same daily record; no joining gift, offline refill or accumulated unopened pile. |
| Inherited | C01 is callable 24/7, arrives after one game hour and waits three game hours. UI does not pause world time or blood freshness. |
| Confirmed | The first paid sealed-bag sale, not a syringe sale or a $400 balance, triggers GrandpaLead. The organ contact requires van acquisition and intro repair. |
| Proposed | A new Forest world begins at 08:00 active game time. Author a nearby ordinary adult Forest candidate area; use the existing free knockdown action for the initial field draw. No special immortal patient. |
| Proposed | The safe sequence is call → wait for C01 → collect nearby blood → return and sell. Explain it once; do not forbid legitimate early collection. |
| Proposed | Retain one active C01 visit per team. Repeated calls show the current visit; they do not create another buyer/car or restart its timers. |
| Proposed | Existing development/test worlds keep their prior setup. An explicit new Forest-world profile enables this slice; loading an old world never silently resets it to the wagon. |

## 4. World creation and existing-save compatibility

### 4.1. Explicit Forest start

Create the world through the existing save owner with a new WorldId in the player's selected empty world slot. Use the [Save specification](SAVE_PROGRESS_SPEC_2026-10-28_v01.md) slot/world contract; a development entry can select a separate new test world without implementing the entire five-slot menu in this task. Never repurpose a player's current file or duplicate the Unity project to obtain a clean start.

Persist the initialisation profile/schema marker inside the same world save. Initialise it exactly once, before the first controllable frame:

- Wagon is the only owned base; team fund, personal XP/spends and mission receipts are empty.
- Spawn host and joining players at safe wagon start positions; create no pocket items, kit stocks, supplies or paid equipment. A syringe is a world pickup, not an inventory grant.
- The van and Hamlet premises visible elsewhere remain unowned. No driver/cargo permission or free repair/organ-contact fact is inferred from a scene object merely existing.
- M01 is active. C01's contact is initially undiscovered. M02 remains deferred; M03 and subsequent story facts are uncommitted unless later earned through their own valid interactions.
- Invoke the existing daily-find rule once at the initial world time. Save the resulting world/find identity, rather than adding a separate tutorial syringe.

The current `EconomyState.NewGame()` Hamlet grant and `ReconcileStory(teamVanInWorld: true, ...)` development shortcut must be profile-aware. In the Forest profile, scene presence is not ownership. This change must not erase genuine existing ownership or require the M06 development scene to replay M01.

This slice does not retune the van or implement its acquisition/repair. M03/M04 retain their own future tasks and prices.

### 4.2. Existing and problematic saves

An existing valid save without the new profile marker is a legacy/development world, not proof that its owner requested a new game. Preserve its position, money, XP, inventory, bases and genuine facts. Use the normal migration path; do not add new tutorial rewards while migrating.

An existing Forest-profile save resumes its persisted stage and physical instances. A corrupted, unreadable or newer-format save uses WP01's protected recovery UI. Do not treat load failure as a fresh empty world or overwrite the source file. Manual saves, autosaves and complete rollback use the existing owner.

A deliberate full rollback may return the world to before the first sale. Replaying that sale in the restored timeline is valid; merging a receipt, money or inventory from its abandoned future is not. Do not add a machine-global first-sale flag that would break separate worlds or legitimate rollback.

## 5. Player flow and minimum interactions

### 5.1. Notice, contact and physical find

At the wagon, the notice reads **BUYING BLOOD** plus C01's fictional number. Reuse an existing authored C01 number if present; otherwise Proposed display number is **555-0101**, stored once with that contact. Notice and phone resolve to the same C01 identity, not separate callable buyers. World lettering stays English; phone/dialogue/hints can be Russian/localised.

Reading the notice with the existing interaction action records `M01.sign` and unlocks the team's C01 contact once. Reading again reopens the same information. Picking up the syringe can happen before reading; do not reset either objective to force a strict order. No mandatory cutscene, dialogue quiz or all-player gathering.

The find is one clean G49 blood syringe, labelled as unused. Interaction transfers its actual instance to the interacting player's inventory after a capacity check. A full inventory leaves the item in the world. Two simultaneous interactions can produce only one owner. Successful pickup consumes the same daily record; dropping it afterwards must not make the morning find spawn again.

Direct selection of that physical syringe must work with no legacy kit item in the hotbar. Do not require the player to obtain the old all-in-one field-kit object to use a new G49 item.

### 5.2. Calling and waiting

The discovered C01 contact offers the ordinary call/visit action through the existing phone. The team selects its owned wagon destination for this slice. The server validates discovery, destination, ownership and whether a visit already exists.

The response states the arrival time and destination. The journal gives one actionable hint: **«Дождись C01 у вагона. Без упаковки кровь быстро портится — собирай её, когда он приедет.»** Opening/closing the phone does not change the appointment, freeze the NPC or refill the syringe.

No waiting fee, tutorial fast-forward, invisible early sale at the parking anchor or bonus payment is introduced. The player can scout the nearby area while waiting. An early collected portion uses the ordinary active freshness limit and can expire; that does not consume the first-$10 entitlement.

### 5.3. Collection with zero purchased supplies

Proposed first-use route: locate an ordinary adult Forest NPC, use the existing free cartoon knockdown action (`Q` in the current controls), select the blood syringe, and complete the existing field interaction while the NPC is eligible. This describes game controls, not medical technique.

`CaptureRules.CanDrawBlood` already permits a living `KnockedOutCold` target without ties or anaesthetic. Reuse that condition and `OperationRules.FillSyringe`; do not create a tutorial-only blood counter or paid-supply exemption. A table, organ procedure, surgical knife, blood bag and purchased base are not prerequisites.

Verify the actual authored NPC's eligible window against the current blood-draw duration (source default 4.5 seconds), including normal aiming/switching time. If the free route cannot complete, this is a failed integration dependency to resolve with the NPC/capture owner; do not declare success after granting hidden ties, locking consciousness or extending time only in a test.

During collection:

- Failed/partial use does not bind the syringe, consume a completed portion or grant XP. Existing cancellation and pending-person rules apply.
- On successful completion preserve the real ItemId, PersonId, PortionId and that person's lifetime blood-portion count.
- First two completed portions follow the existing nonfatal blood rule; the third has the existing lethal consequence. Ordinary injury/death rules still apply. No objective requires the third portion.
- Release/repress is required for another portion; holding the action must not roll through several portions.
- After a full draw the contextual hint offers returning to the waiting C01. Do not tell an M01 player that a missing table bag is the only available action.

The first scene population must supply at least one reachable eligible adult, with ordinary additional Forest NPCs available through its population system. An injured/dead/escaped person retains identity and consequences. Recovery uses other legitimate NPCs and normal population rules; starting or retrying M01 cannot resurrect or clone a previously changed person.

### 5.4. Physical sale and repeat income

Only a present C01 at the active wagon visit can accept a sale. The seller approaches with the valid selected blood syringe. The confirmation displays the current price and **«Забрать пустой шприц»** / **«Оставить C01»**, defaulting to return. Preserve normal reach/availability validation on the server at commit, not only when opening UI.

Commit through `SyringeSaleRules` → `EconomySyringePayout` → the existing shared economy transaction. Reuse per-portion deduplication. Validate the current quote; if another participant has just taken the one $10 sale, refresh this seller's quote to $8 before asking them to confirm the changed amount.

For a genuinely fresh world, first sale effects are one $10 team-fund credit, 55 XP to each participant present at commit, the existing applicable blood respect, the selected item outcome, and `StoryFacts.TutorialSale`/M01 sale objective. A subsequent distinct portion pays $8 and 5 XP each. Monetary income is never multiplied by player count. A migrated world that already consumed the first-blood bonus must not receive another +50 merely because its first syringe receipt is new.

Do not grant XP at draw, pickup, syringe return or journal completion. WP02 is the progression authority; the syringe record can retain compatibility information, not independently award the bonus again. Use existing respect rules without inventing a new tutorial reputation reward.

Returning clears the contents of the same syringe while preserving binding; leaving removes precisely that item. The sold PortionId cannot later be sold as a bag or supplied by another item. Replaying a request returns the prior result without a second payout, XP grant, discard or message.

M01 completion retains the contact and repeat trade. One localised receipt explains $8 repeat sales and the binding. Do not issue GrandpaLead, organ contacts, a van, equipment or a new mission reward at this boundary.

## 6. C01 visit lifecycle and physical staging

Reuse the existing [buyer meeting rules](../../Assets/OnlyVolunteers/Buyers/Core/BuyerState.cs) and [sales contract](SALES_GAMEPLAY_SPEC_2026-10-18_v01.md). Extend their world presentation; do not create a parallel buyer scheduler or a phone-only cash button.

| State | World/phone behaviour | Required transition |
|---|---|---|
| Undiscovered | No usable C01 contact. Notice can be read. | Server records discovery once. |
| Available | C01 can be called to an owned valid destination. | Accepted call creates one VisitId and fixed active-time arrival/wait bounds. |
| En route | One arrival estimate and destination; no sale. | C01's presentation reaches its safe arrival/parking point after the normal one-hour delay. |
| Waiting | One actor/car at the wagon arrival area; contextual sale available in range. | Sales preserve normal visit rules and never restart its deadline; at the three-hour wait limit the visit closes normally. |
| Departed/cancelled | No sale at an empty marker. Existing consequences and rebooking policy apply. | A later valid call creates a new visit, not a second copy of the departed one. |

Proposed presentation: use an already approved NPC/car asset and a short authored approach/park/depart path joining the existing Forest road. Do not add a traffic simulation, a new road, random ambush or a second buyer actor. If the approved art or safe path is missing, list that dependency; a floating debug label alone does not pass physical arrival acceptance. Asset production follows the existing reference/approval workflow separately.

The wagon entrance, notice, syringe and player path stay clear of the parked vehicle and sale UI. Validate top and ground views and a walking run in the current map. Do not rely on an old plan's coordinates after terrain changes. Existing scene-facing C01 placeholder references must not silently become valid permanent sale points for the new Forest profile.

Persist visit identity, destination, arrival/wait times and active state through the existing save owner. A transient real voice call can end on reload; an already accepted visit resumes against the frozen world clock with one actor. No offline arrival, wait expiry or repeated initial call reward. Following an ordinary disconnect, another participant can use the same team contact/visit.

Missing anchors or invalid approach paths must refuse a new booking with an understandable unavailable reason and a development diagnostic. Do not commit an appointment that can never arrive.

## 7. Authored map contract

Aliases inherited from STORY remain aliases; the concrete new IDs below are Proposed except the existing `WagonSyringeFind` lookup. Bind them once to approved authoring data. No blanket rename of existing objects/IDs.

| Logical place | Binding required for this slice | Acceptance property |
|---|---|---|
| Wagon start | Proposed `WagonStart`, plus safe join offsets | Player stands on navigable ground at the existing wagon; 1–4 players do not overlap scenery or each other. |
| `WagonSign` | Notice/read interaction at the existing pole | BUYING BLOOD and number readable at the ordinary interaction distance on the default Low preset. |
| `WagonSyringeFind` | Exact existing daily lookup ID | Physical, reachable unused blood syringe; not inside terrain, a wall or an inaccessible prop. |
| `WagonTutorialArea` | Existing ordinary Forest NPC area near the wagon | Free collection route works; no paid/captured NPC spawned directly into inventory or onto a table. |
| `BloodBuyerBaseAnchor(wagon)` | Proposed concrete `C01.Arrival.wagon`, registered to the same wagon base ID the economy uses | Safe approach, parked-car footprint, sale reach and departure; distinct from `C01.Arrival.hamlet_shed`. |
| Approach/depart route | Existing Forest road, approved plan v04 | C01 arrives at the wagon without a new direct road to Quiet Valley, blocked rails or a vehicle through the wagon wall. |

The find may use a modest existing prop/light/readability cue. No permanent x-ray marker to every syringe in every rubbish bin. Additional logical finds can be authored separately; a random find in every container is not required for M01 acceptance.

World lighting, existing Forest terrain and pharmacy art remain their owners' work. Shipped default graphics are **Low** per the latest root project decision; check readability there and visual quality at maximum. Do not change the default back to High. Casino Island, a handcar and rails continuing into Hamlet are excluded.

## 8. Multiplayer and authority

The finished slice supports one host plus zero to three clients. The current host-only C01 check is an acknowledged integration gap, not an accepted product limitation.

- The server owns discovery, the one daily find, NPC/person state, portion IDs, visits, shared fund, progression and mission facts. UI sends actor/item/visit intents through the existing network transport.
- Connect the map's per-player inventory to the existing inventory/network contract. Never use `CaptureDirector.Kit` or the host's selected slot as another client's sale item. No second inventory, copied hotbar mirror or local-only client payout.
- Pickup and use validate actual ownership and position. At sale, revalidate player connection, alive/interaction eligibility, selected ItemId, portion freshness, active VisitId and reach. A stale UI, moved item or departed buyer cannot commit.
- Any participant can read, call, collect or sell; team members may split steps. No host confirmation, vote or all-player proximity requirement.
- Two players cannot both own the wagon find or sell one portion. Distinct simultaneous sales receive at most one first-$10 price and one first-blood bonus. Participants for XP are captured at the authorised commit.
- Stable player GUIDs, not display names, identify retained inventories. Normal disconnect saves their entire possessions; teammates do not receive replacement copies. A returning participant gets the same owned instances and current journal.
- Late join gives no starter syringe, daily reset, second tutorial or repeated reward. If that participant misses the first sale commit, do not retroactively award its first-blood XP.
- Host departure ends the session. No host migration is added.

If networking is implemented in a later substep, a verified solo milestone may be reported as such. Keep the final 1–4-player M01 acceptance incomplete until client pickup, use, sale and persistence pass; do not label it fully playable from host-only testing.

## 9. Persistence, recovery and player messages

### 9.1. One coherent save

Store the initialisation profile, notice/contact discovery, objective facts, active visit, syringe instances/locations, donor changes, sale receipts, first-price flag, WP02 progression and fund in the existing world snapshot. Extend the current versioned blocks only where needed; no second tutorial save file, wallet, XP pool or scheduler.

A committed sale and its item/mission/XP effects must be captured together through the existing save owner. A disk-write failure must be visible as unsaved state and retry the same coherent state without paying again. Never claim successful persistence from a money toast alone. After interruption, restore either the prior coherent revision or the entire committed revision, not cash without consumption or an empty syringe without its sale result.

Reconcile proven facts idempotently on load. A receipt can restore a missing informational message/objective; a message, balance or scene van cannot prove payment/ownership. Save the syringe's remaining active freshness; reloading, opening the phone, giving it to a teammate or dropping/picking it up must not renew it.

### 9.2. Recovery cases

| Situation | Required result |
|---|---|
| No eligible target / target wakes during draw | Explain the refusal; partial draw follows G49 cancellation. Use a legitimate candidate/free capture retry; no hidden supplies or automatic fresh portion. |
| Wrong person with a bound syringe | Show the existing binding refusal; consume nothing, preserve both persons' counters. Looking for another clean syringe is the recovery path. |
| Portion expires or buyer leaves | No payout or first-sale completion. Proposed context action «Вылить кровь» uses the existing empty rule on the player's owned syringe, with confirmation; it clears contents, not ItemId/PersonId or the donor's portion count, and gives no XP. Rebook/recollect normally; discarding the whole item remains an alternative. |
| Zero money and no usable syringe | Check the team's accessible possessions, not only one hotbar; hint at the wagon/logical finds. If today's guarantee was collected, explain the 06:00 active-world refill. No credit or free emergency kit. |
| Today's found syringe dropped nearby | It remains the same world item. No fresh daily duplicate. |
| Holder disconnected | Item stays retained under that player's identity. UI can say held by an absent teammate; do not mint a replacement or treat ordinary disconnect as arrest. |
| Player dies/is arrested carrying syringe | Apply existing loss once; the item cannot return as clean loot on reload. Other players' inventory is unaffected. |
| No required anchor/catalogue | Refuse the affected interaction, keep possessions/fund unchanged, expose a useful development diagnostic; do not use fallback prices or spawn at world origin. |
| Save blocked/corrupted | WP01 recovery path; do not initialise a new game over it or acknowledge the failed save as durable. |

Proposed message IDs: `m01.notice`, `m01.c01_booked:<VisitId>`, `m01.c01_arrived:<VisitId>`, `m01.receipt` and contextual recovery reasons. Retain existing IDs where already present, especially `m01.receipt`; do not create two receipts for one story event. Generalise UI copy without exposing debug placeholders in the production Forest profile.

## 10. M02 boundary — pharmacy, bags and GrandpaLead remain deferred

The existing city pharmacy stays at **Rough 04-H3** with its approved placement, counter, seller and STAFF ONLY door. This specification does not move/rebuild it, change its nine-offer assortment, prices or its ongoing verification work.

The following are dependencies before activating the continuation, not new features quietly included in M01:

1. Resolve the explicit M02 story hold: adapt the early route to the city pharmacy and validate a walkable Forest-to-Rough round trip before van ownership. Do not restore a Hamlet shop, add a free courier, teleport or require the unowned van to buy the first bag.
2. Connect purchased empty blood bags to actual usable item state. Existing `PharmacyGoods.TeamSupply` counts and old operating-table tray bags are not interchangeable proof of a purchased physical bag. Migration must not turn lifetime purchase totals into the same usable stock again after reload; use the owning inventory/supply contract with consumed/remaining state.
3. Connect collection/packaging for a wagon with **zero operating tables**. Use a paid bag and a real valid portion exactly once; adding a free table or unlimited tray bags violates the start economy. Keep the normal blood-syringe binding after emptying.
4. Connect physical packaged sale to C01, the shared transaction and the one WP02 XP authority: empty bag $5, sealed blood $50 before allowed bargaining, no spoilage/quality/saturation/cooling for sealed blood. Do not pay both syringe and bag for the same portion.
5. On the first paid sealed-bag sale, commit `FirstBagSale` and send the existing GrandpaLead once. A bag bought/filled/dropped or M01 complete is insufficient. No requirement to hold $400 at that moment.

Reactivating M02 requires reconciling its newer city route in a numbered story-spec revision or an explicit implementation scope that cites that decision. This document identifies the hold; it does not override it. M03/M04, the later organ/referral chain and the already implemented M06 workshop quest remain separate.

## 11. Implementation order and ownership dependencies

| Step | Result | Dependencies / boundary |
|---|---|---|
| P0 — Recheck handoff | Read the latest WP01/WP02/WP05 and pharmacy outcome; freeze the exact current code/scene baseline for this task. | Their existing owner finishes or hands off overlapping files. Do not edit the map while it is being rebuilt or the shared Unity Editor while another run is active. |
| P1 — New-world profile and map contract | Deliberate fresh Forest world, safe spawn, visible notice/find and no development ownership grants. | Existing save owner, story/economy initialisation, approved current map. Preserve old worlds and M06 test setup. |
| P2 — Contact and real visit | Discover C01, make one call, see arrival/wait/departure at the wagon. | Existing phone/meeting model, approved actor/car, safe road/anchors. |
| P3 — Free draw and shared sale | Selected G49 item, ordinary NPC rules, existing sale transaction and correct player hints. | WP02 final XP contract, real stun/draw timing; no surgery/bag dependency. |
| P4 — Clients and persistence | Clients perform the same physical loop; coherent restore and no duplicate ownership/rewards. | Existing per-player inventory/network adapter plus WP01. This is required for final 1–4-player acceptance. |
| P5 — Acceptance | Rules regressions, real Play run, standalone start/restart and multiplayer evidence. | Current scene/build; results tied to tested revision. |
| Later, outside M01 | M02 route, usable paid bags, packaging and first-bag lead. | Explicit hold resolution and a separate bounded integration task. |

P3 and P4 may share implementation work; ordering is a testable dependency sequence, not permission for multiple agents to edit shared files simultaneously. Reuse newer completed code discovered at P0 instead of recreating it.

WP05 is not a new blood-prologue prerequisite: no incision is needed. Its ongoing changes still require a regression run when the shared operation core is touched. No artificial suspension of organ spoilage or new XP category is allowed.

## 12. Tuning and checks of the experience

Inherited authoritative parameters: first/repeat prices from G48; one-hour travel and three-hour wait from meeting rules; daily 06:00 from the saved active clock; blood duration/freshness from the existing operation tuning. Do not copy them into UI constants or add a second clock. At the inherited 45-real-minute game day, one game hour is 112.5 active real seconds; use the actual world clock rather than a new real-time timer.

Proposed readability/pacing targets: a new player can find the notice and syringe near the wagon without a full-map search; the waiting interval allows scouting; the draw-to-sale walking route fits within the actual freshness budget with a practical margin. These are playtest targets, not measured results or permission to shorten every buyer timer. Do not promise a full Forest chapter duration or time to the van from M01 alone.

First test with stock controls and no granted items/XP, on default Low and then maximum graphics. Record whether the player understood waiting, found a free candidate, could switch tools within the real eligible window, and understood why the returned syringe still belongs to the same person. If not, adjust local staging/hints under the existing rules before inventing new mechanics.

## 13. Acceptance checks — FP-01 onward

All rows below are requirements for later implementation, **not passed results from this document-writing task**.

| ID | Check and expected result |
|---|---|
| FP-01 | Create a new explicitly selected Forest world: safe wagon spawn, $0, empty pockets/stocks, only wagon owned, no van/repair/organ-contact facts. A clean syringe exists physically at the authored find. |
| FP-02 | Load a prior valid development world: previous money, equipment, owned bases, van and position are preserved; no forced Forest reset or extra tutorial payment. |
| FP-03 | Corrupt/unreadable save invokes WP01 recovery without overwriting it or silently starting a new world. |
| FP-04 | Read BUYING BLOOD notice: one C01 contact and journal fact appear for the team. Read again and late-join: no duplicate contacts/messages/rewards. Pickup before notice also works. |
| FP-05 | Two participants attempt the same wagon pickup: one receives the exact instance, the other does not. Full inventory leaves it in place. Drop/load/pickup never creates a second instance. |
| FP-06 | Initial find, same-day reload and joining use one daily record. An uncollected item does not accumulate; a collected find can refresh only at the next active 06:00, with no offline backfill. |
| FP-07 | Physical G49 blood syringe can be selected/used without a legacy kit item, ties, anaesthetic, table or bag. Complete the ordinary free-knockdown/draw route against the real authored NPC. |
| FP-08 | Partial/cancelled or refused draw creates no binding/completed portion/XP. Successful draw uses the real stable PersonId/ItemId/PortionId; holding input cannot take a second portion automatically. |
| FP-09 | Returned syringe works on the same eligible person and refuses another with no consumption. Person blood count persists through drop, reload, carry and table transitions; third-portion/corpse restrictions stay intact. |
| FP-10 | C01 booking accepts only a discovered contact and valid owned destination; repeated calls retain one VisitId/actor/timer. Missing anchor cannot create an impossible visit. |
| FP-11 | Actual call waits one game hour; C01 visibly arrives and waits three game hours. No sale before arrival, remotely, at the empty marker after departure or at the B02 placeholder in the Forest profile. |
| FP-12 | UI, waiting and reload do not pause/reset active freshness. Expired/empty/unknown-history/wrongly owned goods are refused without consuming the first-$10 entitlement. Emptying expired contents preserves the syringe's binding and donor count and gives no XP. |
| FP-13 | Fresh world's first paid portion adds $10 to the fund once and 55 XP to each participant present. A distinct repeat adds $8 and 5 XP each; no pickup/draw/journal XP is added. |
| FP-14 | For four present players first cash is still $10 total and each gets 55 XP. For an older world whose first-blood bonus is already consumed, no second +50 occurs. |
| FP-15 | Default return clears the same syringe while preserving its identity/binding; leave-with-buyer removes only that item. Repeated confirmation/request/load cannot repeat payment, XP, removal or receipt. |
| FP-16 | Concurrent distinct first sales produce one $10 result and subsequent $8 result; changed quote is shown before the second confirmation. One physical portion cannot sell twice or later become a paid bag. |
| FP-17 | Complete pickup, free draw and sale as a remote client; another client can perform a later portion/sale. Actual per-client selected items, positions and ownership are used, not the host hotbar. |
| FP-18 | Ordinary client disconnect/rejoin restores the same possession and current stage. Late join creates no starter kit, duplicate daily find, retroactive sale XP or new first sale. Host leaving ends the session. |
| FP-19 | Death/arrest loses carried syringes once; reload does not restore them clean. Other players retain their own items. Zero-fund recovery explains legal finds/next morning without credit. |
| FP-20 | Restart before collection, with a partial draw, during a visit, with full unsold blood and after payment: each restores coherent state without renewed freshness, an extra buyer or mismatched cash/items/XP. |
| FP-21 | A simulated save-write failure is visible; retry does not duplicate rewards. Deliberate full rollback restores one entire timeline; abandoned future receipts/items cannot be merged. |
| FP-22 | M01 completes only from a paid sale; repeat trade remains. No GrandpaLead, organ contact, free van, property, bag or additional mission reward is granted. M02 remains deferred. |
| FP-23 | Ordinary player instructions are contextual: wait before collection, bring full syringe to present C01, understand persistent binding/refusals. No missing-table-only instruction, debug sale marker or internal `on hold` text in the normal flow. |
| FP-24 | New Forest profile does not break prior G48/G49, WP01/WP02, M05/M06 and pharmacy behaviour. Existing user saves are not used as disposable test fixtures. |
| FP-25 | In the named real map, walk notice → find → candidate → C01 in Play and a standalone build, using normal controls and default Low. Check maximum graphics too; capture the parked-car/ground/path views and restart from that build. |

## 14. Verification and unresolved work

Required evidence for later implementation: exact tested scene/build and code revision, focused rules/integration results, a fresh-world solo walkthrough with restart, a 2–4-player run covering remote ownership/sale, and any failed/skipped acceptance IDs. Existing G48/G49 test files are useful regression inputs, not proof of this newly staged loop. Do not run all tests repeatedly after unchanged documentation.

The present authoring task checks source references, requirements consistency, unique acceptance IDs and document structure. It does not start Unity, generate art, run runtime tests or modify WP/pharmacy work.

Authoring verification: local link targets and Markdown tables checked; FP-01–FP-25 are unique and consecutive. The nine pre-existing design documents sampled before/after authoring retained the same SHA-256 hashes. Runtime/Unity/multiplayer checks: **NOT RUN** in this specification task; all implementation acceptance rows remain pending.

**Remaining production dependencies:** accepted WP01/WP02 handoff; actual client map-inventory adapter; authored wagon anchors and safe C01 route; approved reusable C01 actor/car; a measured free-capture window and ordinary candidate recovery. These are implementation checks, not another design questionnaire.

**Remaining story decision:** how the early M02 trip uses the new Rough pharmacy. Keep its hold until that route is explicitly resolved. No new question is required to implement M01 as specified here.

Only this new file is an output of the specification task. Existing references remain in place; no commits, code/scene changes or work-log edits are part of this deliverable.
