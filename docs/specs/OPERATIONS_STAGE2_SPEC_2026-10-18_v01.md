# VOLUNTEERS ONLY: Operations Stage 2 — Chest and Cleanup

Revision: v01  
Date: 2026-10-18 (Europe/Moscow)  
Source: G40 interview with Fedya, lead designer; questions 1–29  
Status: design specification; implementation and gameplay acceptance have not been performed.

## 0. Коротко для Феди

- Грудь открывается молотком и остеотомом: поставить остеотом, сделать два точных удара. Обязательны шесть точек: обе половинки грудины и рёбра второй/третьей пар с обеих сторон. Затем руками раскрыть обе половинки до фиксации. Остальные рёбра можно убрать для удобства; крупные обломки собираются отдельно.
- Сердце держат две условные связки, парные лёгкие — три. Можно одновременно работать с обоими органами. Извлечение любого из них всегда убивает NPC; оставшиеся органы продолжают портиться по общей специи. Печень или вторая почка также всегда смертельны — решение от 18.10 сохраняется.
- Аккуратная операция всё равно оставляет немного «малинового варенья» и мусора; ошибки разреза/извлечения добавляют пятна. Швабра моет стол и пол, пачкается и полощется в ведре. Вода не расходуется. Прогресс уборки сохраняется; две швабры ускоряют работу максимум вдвое.
- Мусор собирается пакетом в руках, восемь предметов на пакет. Пустой и завязанный пакеты занимают по обычному слоту. Завязанный пакет нельзя открыть; утилизация — через обозначенный контейнер или существующие точки у воды. Сильный бросок об любой объект может разорвать пакет и рассыпать мусор, включая удар о пол, стену или тиммейта. При разрыве об тиммейта его экран заляпывается и сам очищается примерно через две секунды. Порог «от 80% заряда» ниже явно отмечен Proposed.
- Мешки уменьшают запах, но остаются уликами. Уборка убирает источники, а накопленную подозрительность регулирует G42. Статус базы показывает оставшиеся категории: пятна / мусор / тело. Цены и экономика — заглушки, не предмет этого решения.

## 1. Scope, authority and source contracts

This document specifies the chest operation, its physical output and base cleanup. It extends the existing capture → table → organ → inventory → sale loop. All surgical actions are stylized game interactions with authored targets and abstract connections.

**Confirmed** means Fedya selected the behavior in G40 or it is an inherited confirmed requirement cited below. **Proposed** means an explicitly identified authoring, interaction or tuning preset that Fedya has not separately approved. Proposed values are suitable for a first implementation pass, remain configurable and are not validated balance results.

Later dated Decisions sections take precedence over superseded tables in their source documents. G40 overrides only the details explicitly settled here. In particular, garbage collection in G40 replaces the older generic instruction to pick up every waste item by hand. Physical organ packaging and table interaction remain subject to the work-inventory and operations contracts.

| Read-only source under C:/Dev/Game/ | Relevant contract |
|---|---|
| docs/specs/OPERATIONS_SPEC_2026-10-15_v01.md | Physical tools; shared camera and free roles; connections and pulling; quality; mortality; preservation; cleanup; authoritative persistence. Section 11 Decision 2026-10-18 overrides the old liver/second-kidney chance rows. |
| docs/specs/CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md | Stable patient identity and condition; blood history; corpse decay; clothes becoming trash; corpse removal and water disposal; no offline progression. |
| docs/specs/BUYERS_SPEC_2026-10-15_v02.md | Five quality tiers; ordinary sales versus packaged special orders; organ provenance; sale-only rewards. |
| docs/specs/SALES_GAMEPLAY_SPEC_2026-10-18_v01.md, including Decisions | Surgeon accepts ordinary heart/paired-lung merchandise at Good or better; physical delivery and current-quality checks; packaging is distinct from cooling. |
| docs/specs/WORK_INVENTORY_SPEC_2026-10-18_v01.md, including Decisions | Six pockets and cycling kit slot; real item instances and containers; organ packaging; cooler restrictions; inventory retention on client departure. Earlier leave-drop text is superseded. |
| docs/specs/NETWORK_MAP_PLAN_v01.md, including Decisions | FishNet host/server authority; co-op 1–4; validated intents; one patient identity; host departure ends the session without migration. |
| docs/reports/CAPTURE_DELIVERY_STAGE_A_HOWTO_RU.md | Current playable solo flow, preparation/operation modes, shared chest/abdomen outer opening, corpse removal and prototype limitations. This report is not proof of multiplayer readiness. |
| Working/Reviews/Operations/organs_v04/PROGRESS.md | Existing v04 layout, lowered organ block, hinged ribcage and collision handoff; art verification is distinct from runtime acceptance. |
| ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/G38_collisions_manifest_v04.json | Four rib pairs, split sternum, BREAK markers, hinge parents, 96 UCX parts and SurgicalBone filtering. |
| docs/reports/PROPS_OPS_STAGE2_CLEANUP_v01.md, especially v02 amendment | Existing G34 props, separate mallet/osteotome, jam decals and seven trash visuals; collision/state handoff. |
| Working/Reviews/Props/ops_stage2_cleanup_v02.png | Visual reference for the existing cleanup kit; inspected during G40. |

The sources and all assets remain unchanged by this task. Existing model packages do not establish that chest interactions, cleanup, networking or save adapters already work.

In scope: chest access, heart and paired lungs, quality mistakes, jam mess, organ-bag packing, mop/bucket, waste bags, body-removal integration, evidence/odor hooks, co-op, interruption and persistence.

Outside this implementation contract: head/brain operations, new capture or van behavior, realistic anatomy, closing/stitching, tool sterilization or durability, staff AI implementation, complete police/suspicion rules, economy balancing, Unity changes and asset production. The existing lamp, cooler, refrigerator and body bag are reused through their established contracts.

## 2. Explicit decisions

### 2.1 Confirmed G40 decisions

| ID / question | Final decision | Status |
|---|---|---|
| D01 / Q1 | Place the physical osteotome at a target; it stays there while the player takes the mallet and strikes. A teammate may continue the work. | Confirmed |
| D02 / Q2, Q8 | Six mandatory BREAK targets: STERNUM_L, STERNUM_R, RIB_L_02, RIB_R_02, RIB_L_03, RIB_R_03. Other ribs may be removed for convenience. Rib pairs are numbered from head toward abdomen. | Confirmed |
| D03 / Q3 | Two accurate mallet strikes per target, with visible intermediate progress after the first. | Confirmed |
| D04 / Q4 | Players manually pull the released ribcage halves outward on hinges; each locks open. | Confirmed |
| D05 / Q5 | A few large authored bone fragments remain; obstructing fragments are removed manually. | Confirmed |
| D06 / Q6 | Heart: two short abstract connections. Paired lungs: three separated connections requiring work on both sides. | Confirmed |
| D07 / Q7 | Every operation creates a small baseline mess; mistakes add mess. | Confirmed |
| D08 / Q9 | Organ-connection work is available only after all six targets are completed and both halves are locked open. | Confirmed |
| D09 / Q10 | The mop becomes dirty and needs periodic rinsing in the bucket. Bucket water is not consumed. | Confirmed |
| D10 / Q11 | The same mop cleans stains on both table and floor. | Confirmed |
| D11 / Q12 | Partial stain-cleaning progress persists; another player can continue. | Confirmed |
| D12 / Q13 | Hold a garbage bag, aim at eligible waste and hold the collection action to put it inside. | Confirmed |
| D13 / Q14 | Eight eligible objects per garbage bag, independent of their allowed size; players may tie a partially filled bag. | Confirmed |
| D14 / Q15 | Tied waste bags can be disposed of at designated garbage containers or existing river/lake/canal disposal points. | Confirmed |
| D15 / Q16 | An unsuccessful mallet strike wastes time; wrong contact makes a dull sound and gives no progress. No progress rollback or extra soft-organ damage. | Confirmed |
| D16 / Q17 | Additional operation-error stains come from incision and extraction errors. A missed bone strike creates no stain. | Confirmed |
| D17 / Q18 | An unbagged corpse leaves sparse drips while carried. A loose, unpackaged organ makes a small stain on a strong fall. Packed cargo leaves no trails. | Confirmed |
| D18 / Q19 | Tied garbage/body bags reduce odor but do not eliminate it or erase evidence. | Confirmed |
| D19 / Q20 | A tied garbage bag cannot be deliberately reopened or emptied. | Confirmed |
| D20 / Q21 | Base feedback lists remaining categories: stains, waste, body. No exact object count, cleanliness percentage or location arrows. | Confirmed |
| D21 / Q22 | Cleanup removes sources and their future contribution. Existing district suspicion changes only through G42 rules. | Confirmed |
| D22 / Q23 | Different players may work on heart and lungs simultaneously in the same opened chest and physically interfere. | Confirmed |
| D23 / Q24 | First outer opening creates a small authored set of disposable waste. A vial becomes empty-vial waste when its last stock is consumed. Working reusable tools are retained. | Confirmed |
| D24 / Q25 | Two mops accelerate one stain up to 2×; a third cannot increase that rate. | Confirmed |
| D25 / Q26 | An unused or tied garbage bag occupies one ordinary pocket slot. A tied bag is not a two-handed cooler-style load. | Confirmed |
| D26 / Q27 | Garbage bags accept only recognized waste, including bone fragments and discarded clothing. They refuse organs and reusable tools. | Confirmed |
| D27 / Q28, final amendment and subsequent clarification | A sufficiently charged thrown garbage bag can rupture on impact with any object, including a teammate, wall or floor; it is not limited to teammate hits. Fedya described the strength as an 80%-force hit. Throw power depends on held throw-button duration. If it ruptures against a teammate, only that teammate's screen is dirtied and clears automatically after about two seconds. Precise threshold/impact interpretation is P07. | Confirmed |
| D28 / Q29 | Leaving table mode with a detached organ tries pockets, then the tray. If both are full, place it gently on a free table area, otherwise beside the table. | Confirmed |

Q2 initially mentioned two mandatory points as an answer option; Fedya explicitly replaced that count with six and selected their locations in Q8. Q28's strong-hit exception supersedes the option's unconditional no-rupture wording. Fedya subsequently extended rupture to impacts with any object and added a temporary dirty-screen effect for a struck teammate. These are final amendments, not unresolved contradictions.

### 2.2 Inherited confirmed decisions

| ID | Contract retained | Status |
|---|---|---|
| I01 | One persistent PatientId, condition, intrinsic organ grades, blood history, anesthesia and death state travel from capture to table. | Confirmed — capture/operations |
| I02 | Heart or combined paired-lung extraction kills a living NPC immediately, 100%. Liver and second-kidney extraction are also immediately fatal under the dated operations decision. | Confirmed — operations section 11 |
| I03 | The first kidney retains its chance roll: 10% plus 10 percentage points per prior blood portion. Never repeat survival rolls for a dead patient. | Confirmed — operations section 11 |
| I04 | Five quality tiers, floor Damaged; separate organ grades; condition loss; established incision, direct-cut, abrupt-pull, impact, early-overdose and decay rules. | Confirmed — operations/capture/buyers |
| I05 | Paired lungs are one merchandise item, one organ bag and one storage slot. The complete eight-organ set remains unchanged. | Confirmed — operations/inventory/sales |
| I06 | Ordinary sales do not require an organ bag. Special orders may require sealed individual packing. Packing does not cool or restore an organ. | Confirmed — operations/buyers/sales |
| I07 | Real reachable tools, shared fixed table camera, local magnifiers, no mandatory roles, joint pulling, persistent released connections and no world pause on camera exit. | Confirmed — operations |
| I08 | Body removal frees the table for another patient. Stains and small debris do not mechanically block the next operation. Helper duties do not include cleaning or automatic final disposal. | Confirmed — operations |
| I09 | Server-authoritative shared state; one item ledger, one body owner and one save path; no duplicate extraction, consumption or rewards. | Confirmed — operations/network/inventory |
| I10 | A departing client retains all inventory possessions, including held items and carried cooler contents, in the host save. They are unavailable to the team until rejoin. | Confirmed — inventory Decisions 5 |
| I11 | World closure freezes active-world time. Host departure ends the session; there is no host migration. | Confirmed — network/capture/operations |
| I12 | Private surgeon ordinary purchases: heart and paired lungs at Good / Хорошее (60%) or better. Foreman retains ordinary acceptance of all five tiers. | Confirmed — sales/buyers |

## 3. Existing content and required integration

Use the current v04 patient/organ layout and the existing prepared outer opening shared by chest and abdomen. If that opening is already complete, chest work does not require another skin-opening sequence. Chest access still has its own bone gate. Admission/cloud presentation must preserve the patient's identity and state.

The ribcage has four pairs of ribs and two sternum halves under RIBCAGE_HALF_L / RIBCAGE_HALF_R. Preserve the manifest's BREAK empties, UCX-to-visual mapping and local transforms. The six mandatory targets are the two sternum markers and the markers of rib pairs 02 and 03. Pair 01 and pair 04 are optional. Six targets at two strikes each means **12 successful strikes** for mandatory access; simultaneous players do not reduce the required event count by duplicating requests.

The manifest contains 96 convex UCX parts, including multiple parts per rib. A collider part is not a separate hit target or cleaning object. Resolve it back to its owning bone and BREAK identity. Mallet and osteotome queries/physical contacts include **SurgicalBone only** and exclude organ, heart/lung, vessel, diaphragm and body layers. Render meshes for UCX stay hidden. Art collision checks do not replace later engine cooking and contact checks.

The six verified marker names are BREAK_STERNUM_L, BREAK_STERNUM_R, BREAK_RIB_L_02, BREAK_RIB_R_02, BREAK_RIB_L_03 and BREAK_RIB_R_03. Their hinge parents in the manifest are the matching left/right ribcage halves. Preserve the marker-to-owner mapping rather than identifying targets by collider enumeration order.

Reuse G34 v02 mallet and separate osteotome, organ bag, cooler, fridge, lamp, mop/bucket, garbage bag, body bag and stain kit. The stain kit provides small/medium/large jam stains and a smear trail, plus glove, used syringe, gauze, torn organ pouch, empty vial, scalpel wrapper and sock visuals. Hats/glasses from admission also participate as existing discarded items. A used-syringe trash visual is not permission to consume a reusable working syringe.

Existing asset states provide presentation sources, not game rules. Bone-fragment authoring, bag rupture presentation, inventory definitions and disposal-volume bindings are later integration tasks. Do not claim that a distinct runtime fragment or ruptured-bag mesh already exists. No additional medical realism is required.

## 4. Chest interaction flow

### 4.1 Preparation and outer opening

The player physically brings the same patient to an owned indoor table. Existing pose, five individual table straps, anesthesia, field ties and awakening rules remain in force. No new requirement for all five straps or a mandatory assistant is introduced.

The operation uses the existing preparation/operation views and physical tool reach. Preserve table-mode input routing; the outside six-slot hotbar does not override table tools. Additional chest tools must be selected from real reachable equipment and visibly placed or held. Exact new table selection hints are P01.

Open the prepared outer access if needed. Minor guide deviation remains forgiving. Its completion emits the baseline opening mess/waste once per patient opening; switching zones, leaving the camera or reopening UI cannot spawn another set.

### 4.2 Osteotome and mallet

1. Take a reachable osteotome and place it at an eligible uncompleted BREAK point.
2. The placed tool remains seated independently of the player's hand. Another player can see it and strike or retrieve it.
3. Take a reachable mallet. Each click produces one deliberate strike; holding a button does not create uncontrolled frame-by-frame hits.
4. A validated hit on that seated target advances 0 → 1 or 1 → 2. The first produces a visible crack/progress cue; the second completes the target with distinct feedback.
5. Move the osteotome to another target and repeat. Removing the tool preserves successful hits.

There is no reaction-timing window, random success roll, tool durability cost or consumable blade. A miss or wrong contact gives time cost/dull feedback without reducing prior progress or damaging organs. Striking a completed target does not generate more debris or extra progress. Intent validation must distinguish two deliberate strikes from duplicate delivery of one strike.

Several real mallets/osteotomes permit parallel targets. One physical tool cannot occupy two points. Ownership/target claims serialize conflicts; the second player receives readable occupied/unavailable feedback instead of a copied tool.

### 4.3 Opening halves and clearing pieces

Until all six mandatory targets are complete, neither half can reach its final open lock. Before the lock, the game may show limited resistance/motion as presentation, but organ work remains gated.

After release, grip each half and pull outward on its hinge. Each locks open separately; different players may open opposite halves. Once locked, it stays open when released. There is no requirement for a player to hold the chest open throughout extraction. P02 gives the initial angle convention.

Both locks plus six completed targets unlock organ-connection interactions. There is no alternate raycast-through-bone shortcut. Ordinary tool reach and actual obstructing debris still matter.

A few large authored fragments become physical objects and remain until removed. Players manually move obstructing fragments aside; the garbage bag can subsequently collect them as eligible waste. Break progress is an abstract authored release mechanism: do not delete every entire rib automatically or generate procedural small shards. Optional rib removal uses the same osteotome/two-strike language and does not become another mandatory gate.

Chest and abdomen state are independent after their shared outer access: chest work does not reset abdominal connections, restore removed organs or undo a prior death.

## 5. Heart and paired lungs

The heart has two short readable abstract connections. Paired lungs have three separated connections distributed across both sides. Exact sockets and motion tolerances are authoring presets, not realistic anatomical procedures.

Release each organ's connections with the existing short cutting/tool movement, then take it with empty hands and pull. Released connections remain released after letting go, switching tools, camera exit, another player's takeover or loading.

Players can operate on heart and lungs concurrently, or jointly pull the same organ. Evaluate the resulting shared motion: coordinated pulling helps; opposing motion interferes. If the last holder releases an attached organ, it returns toward its resting position while retaining released connections. One holder leaving does not reset an organ still held by another.

The two lung art meshes remain one logical organ throughout connection tracking, pulling, quality, extraction identity, packing and sales. Do not expose a separately tradable left lung or allow one half to mint a second item. Heart/lung order is a player choice; neither requires the other to be extracted first.

Detachment is one server transaction: settle available quality and decay, mark the organ removed, mint its unique physical item with provenance, record patient death if applicable, and publish the result. The output stays in the extracting hand, rather than becoming money or an automatic sale.

Extracting either item from a living patient kills that patient immediately. If the patient was already killed by liver, both kidneys, overdose or another valid cause, continue from the same death age; there is no second death event or fresh grace period. Simultaneous completion is serialized so exactly one event starts death.

Death does not end the table session, disable the other organ or dispose of the body. Remaining work can continue during corpse decay. Existing early active-work target is approximately 20–40 seconds per organ, including shared access benefits; it remains a feel target, not an extra mandatory hold timer.

## 6. Quality, packing and cold storage

### 6.1 Quality inputs and events

Keep one quality history per organ. Initial quality comes from the saved intrinsic district/type result; condition loss at extraction is applied once: condition at least 75 loses none, 50–74 loses one tier, 25–49 loses two, below 25 loses three. The floor is tier 1.

| Tier | English name | Player display |
|---|---|---|
| 1 | Damaged | Убитое · 20% |
| 2 | Acceptable | Сойдёт · 40% |
| 3 | Good | Хорошее · 60% |
| 4 | Perfect | Отличное · 80% |
| 5 | Perfect+ | Идеальное · 100% |

The percentage is a tier label, not a separate continuously varying condition. Preserve approved tier colors. Exact current quality appears on inspection after extraction; earlier appearance remains approximate unless existing assessment equipment provides the established evaluation.

| Event | Inherited result |
|---|---|
| Predominantly sloppy local incision | −1 tier to associated nearby organs, not the entire patient |
| Direct blade cut into an organ | −2 tiers to that organ |
| Abrupt extraction pull | −1 tier |
| Strong organ drop/impact | −1 tier; gentle contact has no penalty |
| Overdose death before the first extraction | −2 tiers to all remaining organs, followed by ordinary decay |
| Missed mallet strike / bone contact alone | No organ quality loss |

Different events add together down to Damaged. One continuous damaging action is one event, independent of frame count, collider-part count or number of observers. Distinct later actions may cause further loss. Patient movement alone does not lower quality; resulting actual blade contact can.

Death starts the existing 45-second grace followed by one tier per 40 seconds inside the corpse. The existing proposed boundary convention places the first full loss at death +85 seconds; retain its Proposed status in P08. Opening a zone, packing a corpse or changing players cannot restart this timeline. Heart/lung death does not apply the special early-overdose penalty.

### 6.2 Individual organ bags

Use the work-inventory action: hold the secondary packing action on the owned extracted organ with an empty organ pouch available. The normal proposed duration is about one second. At successful completion consume exactly one empty pouch and set Packaged on the **same organ item**. One heart or the combined paired lungs uses one pouch and one slot. Empty pouches may follow the existing consumable stack/kit arrangement.

The table adapter may use a physically reachable pouch from the tray; outside table mode use the established pocket/kit supply route. The selected source must be visible/readable and consumed only once. A failed/interrupted packing action does not consume a pouch; quality and time continue. The packing model does not mint replacement merchandise or discard donor/quality/cold-history fields.

Ordinary surgeon sales require heart/lungs at Good or better at confirmation. They do not acquire a new ordinary-sale packaging requirement. Packaged special orders retain their own requirements. Below-Good goods remain valid merchandise for a buyer who accepts them; there is no new unsellable tier.

### 6.3 Containers, lamp and power

Keep the established storage contract: room, hands, pockets, tray and an uncooled surface use one tier per five active-world minutes; portable cooler uses one per 25 minutes; powered stationary fridge pauses deterioration; unpowered fridge uses room rate. These are inherited tuning placeholders. Sealed blood remains a separate nonperishable item with no organ grade.

Cooler capacity is eight slots; stationary fridge capacity is 24. Packing does not stop spoilage or grant impact immunity. Moving an item does not restore quality or reset accumulated deterioration. Cooling applies only to an item actually accepted into storage, never merely lying on a fridge or beside a cooler. Preserve donor identity and cooled-delivery history through all transfers; actual sale checking stays in the sales system.

The portable cooler remains a two-handed load with no tool use while carried. Garbage bags use D25 instead. Use the existing lamp for visibility; lamp placement/light cues must keep bone targets and stains readable. Any dependence of installed lamps on paid power remains the existing Proposed electrical preset, not a new prerequisite for all chest work. Manual work remains possible with sufficient visibility.

## 7. Mess and waste generation

### 7.1 Persistent gameplay objects versus decoration

Use the existing raspberry-jam presentation: rounded flat red stains, short comic effects and large readable debris. Decorative particles disappear normally; a stain that matters for cleaning/evidence has its own authoritative identity, surface anchor and remaining cleaning work. No collider is added to a flat stain decal.

Create a small baseline stain and authored disposable-waste set once when the prepared outer opening first completes. A patient with an already-open abdomen/chest uses the existing receipt; entering chest mode cannot repeat it. There is no requirement for a second baseline set per chest organ.

Incision errors, direct organ cuts and abrupt extraction events may add local stains under D16. An unsuccessful bone strike creates none. A strong fall of an extracted unpackaged organ is the separate D17 handling exception: it creates a small stain at the impact location along with the established impact quality loss. Packing does not cancel that quality loss, although packed cargo creates no new stain/trail.

An unbagged corpse leaves sparse drips while actually carried through the base. A stationary corpse does not spawn a new stain every frame; ordinary source odor still persists. A bagged body produces no drip trail. Organs do not continuously trail drops while merely being carried. Drip spacing, stain size and cosmetic intensity are P04.

### 7.2 Eligible physical waste

Eligible garbage includes authored operation disposables, depleted empty vials, large bone fragments, and admission clothing trash such as hats/glasses. Emptying a vial transitions that instance into eligible empty-vial waste once; it does not leave both a stock item and an unrelated duplicate vial.

The baseline set may reuse gauze, glove and wrapper visuals as abstract procedure waste. It does not require new wearable-glove or bandaging mechanics. Reusable scalpel, knife, mallet, osteotome and working syringes stay usable. A used-syringe or torn-pouch decorative trash instance has an explicit waste definition; it is distinct from an inventory tool or a sealed organ pouch.

New waste generation is event-driven and idempotent. Reload, repeated empty-stock queries, invalid uses or player re-entry cannot farm trash. Non-waste objects are rejected by garbage collection with an immediate reason; no organ, living NPC, corpse, cooler or reusable tool is silently consumed.

## 8. Base cleanup loop

### 8.1 Table reuse and body removal

Clear the previous patient/body from the table before admission of another. Open the existing straps and use the normal body grab/carry path. Pack a corpse with the existing body-bag consumable/action; do not apply it to a living patient. Body packing produces the existing body cargo identity, not a new merchandise or garbage-ledger item.

Carry and dispose of the body separately. A body bag eases handling and reduces odor but is not disposal. Existing river/lake/canal body-disposal interactions remain valid. A garbage container does not acquire corpse disposal merely because it accepts garbage bags.

Small stains and waste do not hard-lock table use. Players may operate again in a dirty base and keep its remaining sources/consequences. A helper may release straps and move the body to its assigned indoor position under the original duties; that position is not final disposal. Helpers neither clean stains nor clear evidence automatically.

### 8.2 Mop and bucket

Take a real mop, aim at a stain on the table or floor and hold the cleaning action. Valid contact gradually reduces that stain's remaining work and its visible extent. Releasing, walking away, switching tools or leaving table mode preserves completed work. Cleaning works from reachable physical positions; it cannot target an unseen stain through a wall or floor.

The mop accumulates dirt as it works. Rinse it in a reachable bucket to restore cleaning capacity. Water is unlimited; there is no refill errand, detergent purchase, water-quality resource or temperature system. A dirty mop needs rinsing, not replacement. P05 defines first-pass durations and dirt capacity.

Each valid actively cleaning player contributes normal work, capped at two contributors' rate. Two usable mops on one stain provide at most 2× speed; a third provides no extra speed and receives appropriate feedback. Leaving one shared action cannot reset another player's progress. A dirty mop that cannot clean contributes no speed. Completion removes one source once and emits one shared completion cue.

### 8.3 Garbage bag collection and tying

An unused garbage bag is an ordinary small inventory item. Hold it, aim at recognized waste and hold primary use to collect one object. A partly filled, untied bag remains an ordinary bag item using one slot; it can be put down and taken by a teammate with its contents preserved. This is the same collection route regardless of who created the mess.

Capacity is eight eligible objects. Each object counts once, whether a small wrapper or a large allowed bone fragment. It does not matter how many collision parts an object has. Show held-bag occupancy for the bag itself; D20's absence of a base-wide count does not prohibit this container label.

Transfer waste identity into bag contents atomically. Remove its loose-world representation only after the transfer succeeds. A full bag refuses collection and leaves the target untouched. If two bags target the same object, the first valid completion wins; the second consumes nothing.

Players may tie at any fill level after collecting waste. Tying produces a closed bag occupying one ordinary slot, rather than a two-handed load or eight extra pocket items. Individual contents remain recorded for evidence, odor and the rupture exception. It cannot be voluntarily reopened, unloaded or topped up. P06 defines the initial tying action. An empty collection attempt never creates free disposal credit.

### 8.4 Throws, rupture and the teammate screen effect

Use the inventory throw convention: a short drop is gentle, holding the throw button charges force, release throws. The charge is server-validated from held duration. A sufficiently charged throw of a tied garbage bag can rupture it against any object or surface, including teammates, props, walls and floors.

Normal carrying, gentle dropping and weaker throws leave the tied bag intact. A qualifying strong thrown impact ruptures it and returns its recorded waste to the world at the hit location; it is not a disposal event. Floors and walls have no special immunity. No garbage vanishes and no already-cleaned stain is reset. The consumed torn bag shell can be a cosmetic remnant; its logical inventory item is retired once.

**Proposed P07:** treat the phrase “80% force” as normalized throw charge at least 0.80 at release, followed by its first impact with any object or surface. Below that threshold the bag stays intact. This is an explicit interpretation of the final amendment, not a separately confirmed numeric boundary. It can be tuned without restricting rupture to a particular target type.

**Confirmed teammate feedback:** if that rupture impact hits a teammate, show a comic jam/dirt overlay on the struck player's screen. The overlay clears automatically after about two seconds; no cleaning action is required. It affects only that player's view, not the thrower's or other participants' screens. This is temporary visual obstruction, without an additional input lock or world pause. The authoritative hit produces one targeted presentation cue; duplicate contact callbacks do not repeatedly restart the same hit's effect.

The bag's hit detection must respect line of flight and server obstacle checks. Use the established player-contact policy; the exception does not add a new teammate injury, knockout or player-pushing mechanic. It is a bag-rupture condition. One hit, repeated contact callbacks or a reloaded snapshot cannot spill the same contents twice.

### 8.5 Final waste disposal

Tied garbage bags have two valid destination types: an authored garbage-disposal container and the existing authored water-disposal points. Ordinary scenery bins and arbitrary shallow water are not automatic deletion volumes. Exact bindings and the initial interaction are P09.

Disposal retires the bag and contained waste identities as one authoritative transaction. It removes only those objects and their active source contributions. It does not erase the table's other stains, other bags, remaining organs, the corpse or previously accumulated district suspicion.

Putting a bag on the floor, in a pocket, in the van, at an indoor body-drop point or beside a bin does not dispose of it. Tied bag contents remain evidence-bearing and still contribute reduced odor wherever the world's source rules place them. A disposed bag cannot reappear after load.

### 8.6 Base feedback

Inside the base, provide a compact qualitative status listing the categories that remain: stains, waste, body. If none remain, show a clean-workplace state. This means those cleanup categories are absent, not that police must find nothing or district suspicion is zero.

Count unsafely stored or awaiting-disposal bodies/bags as remaining cleanup sources even when the table is empty. A tied waste bag awaiting disposal keeps the waste category active; a body bag keeps the body category active. A loose organ is still merchandise/evidence, not automatically a garbage target or a new cleanup percentage. If needed, show its ordinary item card rather than implying that the three-category status certifies a police-safe base.

No global percentage, exact remaining-object count, wall-visible outline or navigation arrow is required. An aimed stain shows its own cleaning progress; an aimed waste item shows collection eligibility; the held bag shows occupancy. Smell cues and neighbor-complaint presentation use the established operations/G42 integration.

## 9. Evidence and odor interface for G42

Stage 2 exposes factual source state and changes. G42 owns suspicion increments/decay, police scheduling, evidence weights, search discovery, complaints, warrants and incident outcomes. This document does not add a second police meter or repeat the older inspection economy as a new implementation.

### 9.1 Source state

| Field / concept | Required meaning |
|---|---|
| Stable source identity and revision | One stain, waste object, organ, corpse or bag; revisions prevent repeated application. |
| Origin | PatientId and event/organ identity where available; base/district association. |
| Kind | Jam stain, operation disposable, bone fragment, discarded clothing, extracted organ, corpse, garbage aggregate or body bag. |
| Place | World pose and surface; container/slot; holder/player; contained-by source. |
| State | Remaining cleaning work; bag open/tied/ruptured; disposed flag; current source availability. |
| Contents | Stable contained waste/body identities, sufficient to preserve classification and avoid double counting. |
| Odor facts | Eligible source present; exposed or bagged; configured reduction for tied garbage/body bags; no automatic suspicion reset. |
| Discovery facts | Physical world representation/container association; discoverability is evaluated by G42's search rules. |

Use the existing source/item/body identities. A loose waste item moved into a bag stops contributing as an independent exposed source; the aggregate represents its contents. Moving it back out on rupture reverses that containment without minting replacement evidence identities. Packaging or an inventory move changes exposure/location, not historical existence.

### 9.2 Change hooks

Proposed interface event names are descriptive contracts, not a request to create a new manager/framework:

- SourceCreated: new persistent mess, waste or physical output, with its creation event identity.
- SourceChanged: location, containment, packaging, cleaning amount, exposure or availability changed.
- SourceRemoved: stain fully cleaned or contents finally disposed, with a specific removal reason.
- SourcesRestored: saved snapshot applied as current facts, not replayed as new crime events.
- OperationNoise: accepted bone strike, miss or patient vocal cue, if G42 consumes audible-event hooks.

Each change has a stable event id, source revision, active-world time and base/district context. G42 must be able to rebuild current sources from a snapshot and deduplicate a repeated change. No per-frame suspicion call is emitted for a persistent stain.

### 9.3 Required boundaries

Odor builds while relevant sources remain and fades gradually after removal. Bagging reduces but does not zero garbage/body odor. Exact reduction and timing remain P10/G42 tuning. Do not instantly erase the odor field on a final cleaning click, and do not add an automatic “base cleaned” suspicion reward.

Existing operations rules distinguish smell from sufficient discovered evidence: smell alone cannot justify an arrest; a single incidental stain is insufficient. Discovered corpses/extracted organs retain the original major-evidence significance. Exact minor-waste/bone classification and scoring belong to G42; Stage 2 supplies their factual kinds and contents.

Refrigeration is preservation, not evidence immunity. A closed bag or fridge does not become an automatic warrant-free hiding place. Equally, Stage 2 must not omnisciently reveal every owned item to police; G42 applies its discovery rules to physical locations and searched containers.

Pocketed bags remain items with contents and location attached to their current holder. Inventory departure follows the latest Decisions: a departed player's possessions are absent from the world and unavailable to others until rejoin. Suspend their world-position source representation while absent; keep identity/history and do not lower existing suspicion. Rejoin restores sources from the retained item state rather than treating them as freshly generated waste. Timer treatment stays with the shared active-world item rules, not a separate Stage 2 clock.

Body/waste disposal clears its own source identities, not all evidence associated with the donor. Existing witness hooks for carrying bodies remain owned by capture/G42 and are not charged a second time by cleanup.

## 10. Co-op participation and interruption

Roles are temporary activities rather than classes, assigned seats or permissions. Solo can perform every step. A practical team can divide into chest worker, second-organ worker/anesthesia support, packer/cold-storage runner and cleaner/body carrier, and switch at any moment.

| Activity | Co-op behavior |
|---|---|
| Table view | Same fixed framing for participants; local magnifiers and cursors/tools; no forced switch for another player's magnification. |
| Bone access | Separate real tools can work on separate targets; shared target hit counters advance per validated strike. |
| Halves | Players may pull opposite halves concurrently; each lock is persistent. |
| Organ work | Heart/lungs can be worked in parallel; same-organ pulling combines holders' motion. |
| Support | Another player can bring reachable tools/supplies, administer anesthesia or move an output; no remote free tool spawning. |
| Packing/storage | Any player with valid physical possession and supplies can pack/transfer the same item. |
| Cleaning | Different surfaces can be cleaned in parallel; one stain uses the 2× cap; waste races are serialized. |
| Body | Normal shared body/strap rules; no automatic helper cleanup. |

Anesthesia and awakening continue during bone work, packing, cleanup and camera exit. Retain the existing eight-second post-extraction awakening rescue for a still-living patient. A patient already killed by a terminal extraction does not wake or receive another shock-death event.

Leaving table mode routes a detached held organ to the player's free pocket, then a free tray slot, then gentle placement at the table/beside it. The fallback is room storage and does not create an impact penalty or a new spill merely for exiting. Server-side placement selects a non-penetrating reachable position; P11 describes the initial placement policy.

On client departure, release transient tool-use and attached-organ pull claims. Completed hits/connections and locks stay. An attached organ follows remaining holders or the usual spring-return rule. World-placed osteotomes and tools remain shared objects. Inventory-owned/held detached items stay in that player's saved possessions under I10; do not apply the normal voluntary-exit world fallback as a disconnect drop. Preserve any table-hand item through the existing ledger's retained held-item state, including when pockets were full; this is not an extra usable pocket slot.

NPCs/corpses are shared body state rather than inventory merchandise. Their existing holder-release/drop behavior remains separate from inventory retention. A patient assigned to a table stays assigned until actually removed.

Late joiners receive the current patient, bone hits, seated tools, hinge/lock state, remaining connections, detached items, stains, bag contents and mop dirt. They do not see an untouched chest or a freshly clean base. When the host leaves, save the authoritative world and end the session for all peers.

## 11. Authority, atomic transitions and save data

Use the established FishNet server/host path for solo and 1–4-player co-op. Clients send action intents. The server checks participant identity, actual tool/item possession, reachable target, line of sight, current stage, finite/current input, target claims, available consumables and container capacity.

Persistent shared results replicate as state. Crack, thud, splash, zip, jam and cleaning sounds are presentation cues; missing a cue cannot undo or invent the result. Client replicas do not independently simulate bone progress, death, quality, source creation or bag rupture.

### 11.1 Atomic/idempotent events

| Transition | Must occur once together |
|---|---|
| Valid bone strike | Input-event receipt, target hit count and any newly released fragment/source |
| Organ detachment | Removed-organ state, settled quality/provenance, item mint, death-start state if applicable |
| Organ packing | One pouch consumed; same organ marked packaged; presentation/source exposure updated |
| Last vial stock use | Remaining stock exhausted; that vial transitions to empty waste exactly once |
| Stain completion | Remaining work reaches zero; source removed; completion cue |
| Waste collection | Loose object leaves world; same identity joins one bag; occupancy changes |
| Bag tying | Contents retained; open-to-tied state; one resulting item identity |
| Strong thrown impact against any object | One intact-to-ruptured transition; bag retired; same contents released; if a teammate is struck, one targeted temporary dirty-screen cue |
| Disposal | Bag/body and relevant contained identities retired; their current sources removed |

No cutting, bone work, cleaning, packing or disposal pays cash/XP. Merchandise rewards remain in the buyers' atomic sale flow. Duplicate requests or a saved already-completed state return the prior result rather than generating extra objects, bags, fines or rewards.

### 11.2 State to persist

| Domain | Required saved data |
|---|---|
| Patient | PatientId, condition, intrinsic/per-organ state, prior blood, anesthesia, alive/dead, original death age, extraction outcomes |
| Chest | Shared outer opening/mess receipt, per-BREAK hit count/completed state, seated tool identity, half angle/lock state, removed optional ribs, fragment identities |
| Organs | Released connections, removed flags, deterministic extraction identity; detached quality/provenance/packaging/decay and container state in the existing ledger |
| Mess | Stable stain ids, surface anchors/poses, remaining work, waste ids/poses, creation receipts and source revisions |
| Cleanup tools | Actual mop/bucket identities and poses; mop dirt; unlimited-water rule requires no water-stock save |
| Garbage | Bag id, open/tied/ruptured state, ordered/set contents, item place/owner/slot, disposed/retired identity receipts |
| Body | Existing corpse/body-bag state, straps, location and disposal receipt |
| Timers | Active-world decay, odor integration state owned by G42, persisted partial cleanup; no elapsed wall-clock catch-up |
| Players | Existing six-slot/kit/held-item state under persistent player id, including retained inventory of absent clients |

Do not duplicate organ records in a separate chest inventory. Reuse existing item/container and body save ownership. Transient held-button sessions/claims are released on restore; completed progress and actual placed objects remain. Restoring sources is a state reconciliation, not a second set of mess-generation events.

For a legacy save with a completed outer opening but no new mess-generation receipt, establish the receipt without replaying that opening or duplicating admission trash. Initialize only genuinely absent Stage 2 fields; preserve all existing patient, extraction and item identities. The concrete schema migration stays with the existing save owner.

Closing the saved world stops anesthesia, decay, odor and cleaning time. A client leaving a still-running host does not freeze that world. Invalid/stale intents cannot advance progress or consume an empty bag. If the operation camera or UI is interrupted, the same state must remain accessible on return.

## 12. Proposed presets and implementation dependencies

The interview has settled the gameplay choices. The following are explicit starting presets, not unanswered interview questions or newly confirmed numerical balance.

| ID | Proposed first-pass detail | Reason / boundary |
|---|---|---|
| P01 | Contextual table tool selection extends the existing preparation/operation input routes. Place osteotome with primary use; select an actual mallet; one click gives one strike. Display the selected tool and target state without a permanent row of new hotkeys. | Exact new selection binding is an integration detail; retain the physical/reachable-tool requirement and ordinary hold/click conventions. |
| P02 | Lock each half at the asset-reviewed 35-degree outward pose, clamped to its hinge axis. Use visible hinge resistance and a lock cue. | The manifest checked this pose; runtime clearance/feel still needs a real test. Larger travel is not presumed validated. |
| P03 | Author a few large debris pieces tied to completed target groups; no procedural shards. Determine their exact count and shape against the existing meshes. | D05 selects a few large fragments, not a guaranteed currently delivered fragment mesh set. |
| P04 | One small baseline stain; three baseline disposable pieces (glove/gauze/wrapper). Local error adds one nearby stain; strong loose-organ fall adds one small stain. Corpse drips are distance/time throttled, initially one small drip per 2 m and no faster than once per second. | Keep mess finite and readable; the baseline receipt is shared with abdomen opening. Actual counts and visual intensity need playtesting. |
| P05 | Normal single-mop cleaning: small 2 s, medium 3 s, large/trail 4 s. A clean mop has four small-stain equivalents of work before rinsing; fully dirty mop pauses cleaning. Rinse hold 1.5 s. Preserve partial work and normalize two valid contributors to at most 2×. | Tunes the confirmed hold/rinse/shared-progress loop without water procurement. Dirt accrues from actual work, not every frame/contact. |
| P06 | Garbage collection hold 0.6 s per eligible object; tie a nonempty bag with secondary hold for 1 s. No change to contents/consumables before completion. | Concrete controls/timing for the selected held-bag collection route. |
| P07 | Throw charge q is clamped held-duration/max-charge-duration. Start with the inventory's proposed 0.6 s maximum. A tied bag ruptures at q >= 0.80 on its first impact with any object or surface, including teammates, props, walls and floors. Spill contents at safe nearby poses; retire bag once; use the available flat/open visual for a brief cosmetic remnant. | Exact threshold and first-impact convention interpret Fedya's “80% force” amendment. The later any-object scope and roughly two-second victim-only dirty-screen effect are Confirmed. |
| P08 | Retain the existing proposed death +85 s first corpse-loss boundary and fractional deterioration progress across extraction/storage changes. | Rates and no-reset behavior are inherited; discrete boundary/fraction conversion are not a fresh G40 approval. |
| P09 | Bind designated existing base garbage receptacles as disposal endpoints. Held tied bag + primary hold 1 s at the receptacle completes disposal; dropping into an existing valid water-disposal volume uses the established splash/retire interaction. | Destination types are confirmed; precise container placement/authoring and hold duration are integration work. No new district disposal simulation is implied. |
| P10 | Supply a configurable bagged-odor multiplier strictly between 0 and 1; start at 0.5 for garbage/body bags. G42 owns temporal buildup/fade and all suspicion/evidence weights. | Confirms reduction without pretending that an exact odor percentage or police score was selected. |
| P11 | On full-pockets/full-tray camera exit, search a small free table placement area, then a safe adjacent floor location; place gently at rest and preserve item id/quality. | Guarantees D28 without blocking exit, clipping goods, scanning distant stores or resetting decay. |

All price, purchase-cost, sale-premium, wage and economy numbers remain placeholders inherited from their own documents. This specification does not balance or reconfirm them. Existing cooling/quality timing values likewise require the relevant playable-loop test; no additional interview was spent on economy.

Later integration must provide: actual table tool controls for the new tools; eligible waste and garbage-bag item definitions; authored fragment/state mapping; existing disposal endpoint bindings; body/inventory/source adapters; source snapshots/events for G42; and required animations/sounds. These are implementation dependencies under a separate task, not proof of missing designer answers or authorization to edit assets here.

## 13. Acceptance checks OPS2-01…

These are future verification requirements. They have not been executed in Unity by this document-writing task. Checks tied to Proposed presets verify the documented first-pass interpretation and are identified as such.

| ID | Scenario | Required result |
|---|---|---|
| OPS2-01 | Admit an existing captured patient with blood/anesthesia/condition history | Same PatientId and state reach the table; no fresh intrinsic rolls or blood reset. |
| OPS2-02 | Start chest work after the shared outer opening is already complete | No second skin-opening sequence or duplicated baseline mess; abdominal progress remains. |
| OPS2-03 | Query rib/sternum colliders with both bone tools | Only SurgicalBone participates; 96 collider parts resolve to ten bone owners; soft organs/body are excluded. |
| OPS2-04 | Complete the mandatory access targets | Exactly two sternum and four middle-rib targets are required: L/R 02 and L/R 03; two successful strikes each, 12 total. |
| OPS2-05 | Place osteotome, change tool/player and strike | Tool stays physically seated with one identity; a real mallet can advance the same target; no duplicate tool. |
| OPS2-06 | Land one hit, miss, retrieve tool, exit and return | First-hit progress remains; miss gives no progress/quality loss and never erases that hit. |
| OPS2-07 | Strike a completed target or retransmit one strike | No extra completion, fragments or progress; a genuinely separate accepted strike counts once. |
| OPS2-08 | Try organ work before six targets and both locks | Connection cutting/pulling is gated; raycasts cannot bypass bones. |
| OPS2-09 | Pull the released halves and let go | Each locks open and stays; two players can open opposite sides; P02 pose is verified against actual clearance. |
| OPS2-10 | Remove optional ribs / obstructing large fragments | Optional work never becomes a seventh mandatory target; pieces stay physical until moved/collected; no tiny procedural cleanup shards. |
| OPS2-11 | Release heart/lung connections | Heart has two; the paired lungs have three distributed across both sides; progress persists on interruption. |
| OPS2-12 | Two players work on different chest organs | Both may act concurrently with independent real tools and shared authoritative state. |
| OPS2-13 | Two players jointly pull one organ, then one/both release | Resulting motion governs tension; remaining holder continues; last release returns attached organ while preserving connections. |
| OPS2-14 | Detach paired lungs | Exactly one merchandise item, extraction id, grade, pouch and storage slot; no independent left/right sales. |
| OPS2-15 | Extract heart or lungs from a living patient | Immediate guaranteed death once; table remains usable for further extraction; no automatic cash/disposal. |
| OPS2-16 | Extract liver or second kidney, then heart/lungs later | Original guaranteed abdominal death remains; later extraction does not restart death/grace or roll survival again. First-kidney chance remains unchanged. |
| OPS2-17 | Apply intrinsic/condition/operation damage at extraction | Saved organ-specific intrinsic result and one condition penalty; correct additive tier losses; floor Damaged. |
| OPS2-18 | Cause one sloppy cut, direct cut, abrupt pull and strong impact | Inherited −1/−2/−1/−1 losses apply to proper organs/events, not per frame or UCX part; gentle contact has no loss. |
| OPS2-19 | Kill by early overdose versus terminal organ extraction | Only pre-first-extraction overdose applies the two-tier all-remaining-organs penalty. |
| OPS2-20 | Continue on a corpse, switch zones, bag body, save/load | Death age never resets; grace/decay continue from active-world state. Check the explicitly Proposed P08 boundary separately. |
| OPS2-21 | Seal an organ; interrupt or race packing attempts | One pouch only on success; same organ id/provenance/grade; no fresh timer, free output or double consumption. |
| OPS2-22 | Present packed/unpacked heart/lungs at Good and Acceptable to surgeon | Ordinary acceptance requires Good or better; no extra ordinary packing rule; rejected goods remain available to the team/another valid buyer. |
| OPS2-23 | Move goods between room/cooler/powered/unpowered fridge | Inherited rates, 8/24 slots and no quality restoration/reset; packing is not cooling; physical proximity alone gives no preservation. |
| OPS2-24 | Complete first opening, re-enter chest UI, reload or revisit another zone | Baseline stain/waste is created once per opening receipt; P04 counts remain Proposed. |
| OPS2-25 | Make a cutting/extraction error or miss bone strike | Relevant error produces local additional mess; bone miss produces none; unrelated organ quality is unaffected. |
| OPS2-26 | Carry corpse/packed corpse and strongly drop loose/packed organ | Sparse unbagged corpse drips; loose unpackaged organ strong fall makes a small stain; packed cargo has no trail/new stain, but ordinary impact quality still applies. |
| OPS2-27 | Empty vial; query again; use reusable syringe | One vial becomes waste at depletion; no duplicates; working reusable syringe remains a tool. |
| OPS2-28 | Remove body while stains/debris remain | Next patient can be admitted; sources remain; helper body movement never counts as cleaning/final disposal. |
| OPS2-29 | Mop table and floor, stop halfway, another player resumes | Same tool cleans both; saved remaining work is shared and preserved. |
| OPS2-30 | Dirty/rinse mop with bucket | Cleaning dirt persists; rinsing restores capacity; water never depletes. P05 timings/capacity are tunable. |
| OPS2-31 | Use one, two and three valid mops on a stain | Up to 1×/2×/2× speed; completion/removal fires once; dirty/noncontact tools do not contribute. |
| OPS2-32 | Collect eight differently sized eligible waste objects | One object per slot in bag, total eight regardless of allowed size/UCX count; ninth stays in world with full feedback. |
| OPS2-33 | Aim garbage bag at organ, reusable tool, corpse or another filled bag | Collection refused; target/item/supplies remain unchanged. |
| OPS2-34 | Race two bag collections on one object or interrupt hold | One valid transfer; no duplication, deletion or progress-based free collection. |
| OPS2-35 | Tie a partially filled bag and take/drop it | Contents retained; one ordinary pocket slot; no two-handed restriction; cannot reopen/unload/top up. |
| OPS2-36 | Gently drop tied bag or weakly throw it against a teammate, prop, floor or wall | Bag stays intact; no free disposal or lost contents; no rupture-driven screen effect. |
| OPS2-37 | Strongly throw tied bag against teammate, prop, wall and floor in separate trials | Every target type permits rupture: same waste ids spill once and bag retires. A struck teammate alone gets a jam/dirt screen overlay clearing automatically after about two seconds, without a cleaning action, input lock or automatic injury. Under Proposed P07, test charge below 0.80, exactly 0.80 and above; first-contact walls/floors can trigger rupture too. |
| OPS2-38 | Dispose tied bag at designated bin and valid water point | Both work; bag/contained source retirement is atomic; scenery bins/shallow arbitrary water do not silently delete it. |
| OPS2-39 | Move waste into bag/pocket/van/body-drop corner without disposal | Identity/contents remain; odor is reduced by tied bag, never zero; mere relocation does not remove evidence. |
| OPS2-40 | Clean all stains/dispose waste/body | Source facts update; odor fades under its integration rules; district suspicion is not directly lowered by cleanup. |
| OPS2-41 | Inspect qualitative base status with floor stain, tied bag and body bag | Correct stains/waste/body categories remain; no global percentage/count/arrows or promise of police safety. |
| OPS2-42 | Feed source creation/containment/removal and repeated events to G42 adapter | Factual identities, location, contents/revision and removal reasons available; no duplicate source counting or per-frame suspicion calls. |
| OPS2-43 | Save/load current sources | Restores facts, not new crime episodes; disposed identities stay retired; fridge/bag storage does not invent evidence immunity. |
| OPS2-44 | Exit table mode with detached organ: free pocket, full pockets, full tray too | Pocket → tray → gentle free table/beside-table fallback; same item/quality; no blocked exit, lost item or forced impact stain. |
| OPS2-45 | Client leaves while pulling/using tool and holding detached inventory goods | Transient attached holds release; completed chest progress persists; inventory goods retained for persistent player id, unavailable until rejoin; no superseded leave-drop. |
| OPS2-46 | Late join during partly opened/cleaned operation | Identical hits, seated tools, locks, connections, items, stains, bags and mop dirt; correct authoritative patient state. |
| OPS2-47 | Host exits and world is reopened later | Session ends for all; authoritative save resumes with no offline anesthesia, decay, odor or cleaning progress. |
| OPS2-48 | Run in solo and host + 1–3 clients | Every stage is possible solo; 1–4 participants can assist without mandatory roles or duplicate bodies/items/events. |
| OPS2-49 | Review action rewards and helper behavior | No operation/cleanup/packing/disposal cash or XP; sales rewards remain in buyer flow; helper never silently cleans. |
| OPS2-50 | Playtest readability and pacing | Six targets, intermediate cracks, halves, heart/lung connections, tool reach, jam stains, mop state and bag occupancy readable; shared camera and physical interference remain understandable. Human acceptance required. |

## 14. Questions left open

**None within the interviewed Stage 2 gameplay scope.** All 29 questions have answers, including the six-point amendment and strong-hit exception, subsequently extended to any impact target with temporary dirty-screen feedback for a struck teammate.

P01–P11 are labeled first-pass presets/authoring choices rather than undisclosed designer approvals. The exact interpretation of “80% force” remains explicitly Proposed P07; it does not block the confirmed exception or require silently changing it to unconditional bag immunity.

External work remains owned by its separate specification/task: G42 evidence scoring, odor progression and police outcomes; economy/prices; asset/runtime integration; network implementation; real-world placement of disposal endpoints; and playtesting of tools, cleanup pacing and visual feedback. These are not additional G40 interview questions.

## 15. Document verification and file scope

This task creates only C:/Dev/Game/docs/specs/OPERATIONS_STAGE2_SPEC_2026-10-18_v01.md. Reference materials were read without edits. No Unity work, asset changes, staging, commits or pushes are part of this task.

Checks performed on this exact file with read-only PowerShell text/regex validation and source inspection:

- **PASS:** all 29 interview question numbers are represented in the final decision table, including Q8 combined into the six-point decision and the Q28 amendment with subsequent any-object/teammate-screen clarification.
- **PASS:** 50 acceptance rows, OPS2-01 through OPS2-50, contiguous and unique; 11 explicitly listed Proposed presets, P01 through P11.
- **PASS:** Russian summary, English main specification, explicit decision statuses and Questions left open section are present; UTF-8 readback contains no replacement characters.
- **PASS:** all 11 listed reference-file paths exist. All six selected bone owners, BREAK markers and left/right hinge parents were checked against G38_collisions_manifest_v04.json.
- **PASS:** document review retains the dated liver/second-kidney fatal rule, terminal heart/paired-lung rule, existing quality/packing/storage contracts, latest inventory-retention decision and server-authoritative 1–4-player/no-host-migration contract.
- **NOT RUN:** Unity import/compilation, gameplay, physics, multiplayer, save-adapter and subjective pacing tests. They are outside this specification-only task. Acceptance scenarios above are future requirements, not claimed runtime passes.

Files created/changed by G40:

- C:/Dev/Game/docs/specs/OPERATIONS_STAGE2_SPEC_2026-10-18_v01.md

---

## Decisions (Fedya, 2026-10-18) — answers to review Q1–Q5 (docs/reviews/OPS_STAGE2_SPEC_REVIEW_v01.md §6, branch claude/ops2-review)
1. **Straps:** 4 limb straps only. The patient cannot escape only when all 4 are closed; any open strap → combination-specific comic escape attempt (own animation per combination).
2. **Suture:** needle and thread from the kit (like the syringes); hold and trace along the incision, ~5 s; two players faster (max ×2); can be abandoned, progress saved. Dead body: a one-action (~1 s) skin patch instead.
3. **Opening = spoilage starts.** As soon as the body is opened (incision/chest), ALL remaining organs start spoiling. Keeping the patient alive after opening must be unprofitable, so nobody wants to. Closing the chest halves + suturing a living patient is still allowed (no rib penalty). The FIRST operation must clearly warn the player about this (tutorial hint).
4. Patch body back on the table: one cut removes the patch, insides as they were, spoilage continues (accepted).
5. Released/escaped living patient and police: removed from our spec — Vadim decides in his police spec (we only emit the hook).
