# VOLUNTEERS ONLY: Operations Specification

Revision: v01  
Date: 2026-10-15  
Language: English  
Deliverable: game design specification for the existing project

## 1. Status and decision authority

This document consolidates the operations design interview. It describes the target game behavior, not an already implemented feature. The interview is complete for this first specification; remaining numerical presets are collected in section 24 for implementation and playtesting.

Three labels distinguish authority:

- **Confirmed:** explicitly selected or described by the user in the interview.
- **Existing contract:** a relevant requirement already present in project documentation.
- **Proposed preset:** a concrete implementation or tuning choice that the user has not approved individually. These choices must remain configurable and must not be reported as interview decisions.

Later interview decisions supersede earlier proposals within this feature. In particular, table capacities, equipment confiscation, skill progression and blood storage use the final decisions below. This file does not silently rewrite unrelated canon or authorize implementation of the whole design.

## 2. Purpose and scope

**Confirmed:** operations are a physical, cooperative activity. Players prepare an NPC, use tangible tools, open shared work zones, extract physical merchandise, manage storage and deal with the remaining body and mess. Friends can join, help, interfere and leave.

**Existing contract:** presentation remains stylized and comic. Interaction uses abstract game connections, prepared openings and large authored barrier pieces. This is not a simulation of medical procedures.

The specification covers:

- The wagon blood prologue and indoor organ operations.
- Base setup, table preparation and patient restraints.
- Shared operation cameras, tools, zones and extraction.
- Anesthesia, awakening, mortality and quality damage.
- Packaging, spoilage, cooling and electricity bills.
- Shared money, XP, purchases and staff automation.
- Cleanup and the operation-related police inspection loop.
- Persistence, multiplayer invariants and acceptance checks.

Current boundaries:

- Organ operations require a table inside an owned base building. Outdoor and mobile operations are deferred.
- The wagon has no operation table. Its introductory blood collection does not require one.
- The proposed living, eyeless NPC release scenario is a separate future content idea.
- There is no wound-closing or tape stage.
- There is no temperature-management minigame or portable-cooler refrigerant resource.
- The full city investigation simulation, complete XP tree and rare-trait catalog are outside this document.

## 3. Main player loop

1. Obtain an adult game NPC through the existing capture and transport loop.
2. Bring the NPC to the base. Preserve physical unloading and carrying.
3. Physically place the NPC on a free table.
4. Enter the table camera, adjust the working pose and fasten available restraints.
5. Administer anesthesia using a physical syringe and a player-chosen amount.
6. Select a zone and open its prepared access area with the appropriate tool actions.
7. Release the selected organ's stylized connections and pull it out.
8. Keep the extracted item in hand, pass it, place it in a tray, package it or store it.
9. Continue with other organs or zones while monitoring the NPC and time.
10. Remove the body, clean as desired and transport merchandise for sale.
11. Receive shared cash and sale XP; pay for equipment, supplies, staff and electricity.

**Confirmed:** leaving the operation camera does not cancel the operation or pause the world. Open zones, released connections, extracted items and patient state persist.

Completing a selected organ list is distinct from the NPC dying. Do not introduce an automatic death solely because the player or specialist has finished that list.

## 4. Bases and physical capacity

| Progression location | Maximum operation tables | Role |
|---|---:|---|
| Forest wagon | 0 | Free blood introduction |
| Hamlet hut | 1 | First indoor organ operations |
| Rough / disadvantaged district base | 2 | More room and parallel work |
| Downtown base | 3 | Expanded stock, expensive staff and assessment purchases |
| Final laboratory | No fixed design cap | Staff-supported production limited by usable space and actual performance |

These capacities supersede earlier proposals for one table in the wagon, two in Hamlet, four in Downtown or four globally. Four players do not imply a four-table limit in the laboratory.

**Confirmed:** earlier bases and their remaining equipment stay available after buying a later base. Each powered base has its own bill.

### 4.1 Starting conditions

The wagon is completely free, with no electricity bill and no table. Its blood activity is performed where the NPC is lying.

The initial Hamlet setup provides an old table without restraints or a lamp, plus a found, rusty basic knife. Previously acquired tools remain available. Other tools, restraint kits and consumables must be bought. A usable van parking and unloading area is required.

The first organ content is kidneys and liver, alongside blood collection. Other manual procedures become possible through the necessary tools; exact non-anesthesia unlock thresholds remain a project progression integration detail.

Downtown provides room for three tables and stock immediately. Tables are relatively affordable. Helpers and assessment equipment are expensive purchases intended for late Downtown progression. The operating specialist supports the transition to the final laboratory.

### 4.2 Placement and reach

- Large equipment uses a placement preview with a clear valid/invalid position.
- Small tools, trays, containers and merchandise use physical grabbing.
- A table work-area preview shows which nearby tools can be reached from its camera.
- Only physically reachable tools on the table, tray or adjacent trolley are available from that camera.
- A distant tool requires leaving table mode or having another player bring it.
- Space must accommodate carrying, preparation, staff paths, storage and van unloading, rather than merely fitting furniture bounding boxes.

Invalid placement must be readable before purchase placement or final confirmation. Do not silently consume equipment when placement fails.

## 5. Blood introduction and collection

### 5.1 Introductory sequence

**Confirmed:** the wagon scene uses a downed NPC and found nearby syringes. The player holds a syringe in first person, aims at the NPC and holds interaction. The syringe visibly fills over **4-5 seconds** per portion. No table camera or patient restraints are required.

The filled syringe is a physical item. Buyer C01 accepts an unpackaged filled syringe as the introductory exception. After that introduction, blood must be transferred into purchased bags. A later collection device can fill a bag directly, removing the learned transfer step.

**Integration requirement:** onboarding must provide access to the first syringe, the buyer and subsequent blood bags without requiring equipment that the player cannot yet afford. Syringe refill/recovery details and the initial unpackaged-blood timer are proposed tuning items, not additional settled mechanics.

### 5.2 Portion limits and value

| Collection from an ordinary NPC | Result |
|---|---|
| First portion | Nonfatal under the blood-collection rule |
| Second portion | Nonfatal; clearly weakened behavior warns the player |
| Third portion | Fatal |

These are game rules, not medical quantities. Other existing injuries or operation events can still kill an NPC before a third collection.

- A sealed blood bag sells for a fixed **$50**.
- An empty blood bag costs **$5**.
- Sealed blood has no organ quality grade, price multiplier or spoilage timer.
- Cooling is unnecessary for sealed blood.
- A bag placed inside a container still occupies one storage slot.
- An unsealed syringe does not acquire the sealed bag's preservation guarantee.

Record collection count on the stable NPC identity. Loading, carrying to another base or switching players cannot reset the two-portion allowance.

## 6. Patient positioning and restraints

**Confirmed:** players physically put the NPC on the table before assisted alignment. A short positioning animation supports that physical action; it does not fetch or teleport a distant NPC.

Inside table mode, mouse interaction adjusts the limbs into usable positions and fastens restraints individually.

The restraint kit is one purchase containing five separately operated fasteners:

1. Left arm.
2. Right arm.
3. Left leg.
4. Right leg.
5. Torso.

### 6.1 Partial restraint behavior

**Confirmed:** the torso restraint prevents escape from the table. Arm and leg restraints reduce movement and make precise work easier. All five are useful, but all five are not required to prevent escape.

Operations without a kit are allowed while the NPC sleeps or friends physically hold the NPC. This preserves the unreliable early setup. An unrestrained, awake NPC can attempt to escape.

After at least one organ has been extracted, an awakening restrained NPC follows the eight-second re-anesthesia window and shock-death rule in section 10. Limb restraint does not remove that risk.

Initially, release each fastener separately. A later quick-release mechanism may replace the repeated release actions. Its unlock and price are tuning/integration items.

### 6.2 Separate organ connections

Patient restraints and organ connections are different systems. The five table restraints hold the NPC. The **2-3 stylized connections per organ** hold that organ inside its work zone. Releasing an organ connection never releases a table restraint.

## 7. Camera and cooperative participation

- All players joining one table use the same fixed camera viewpoint.
- The shared framing shows the whole NPC and relevant reachable work surfaces.
- Each player may use an individual magnifier for a local area while preserving the shared overview.
- Magnifier movement is local presentation and does not move another player's view.
- Players have individual tools, cursors and interactions; there are no mandatory roles.
- Different players can work on the three different zones concurrently.
- A solo player can open and switch between all zones. Existing openings persist.
- Players can give anesthesia, move items, adjust available restraints and help or obstruct extraction.

Players may jointly pull the same organ. Coordinated motion helps; opposing motion interferes. The resulting shared motion determines progress and abrupt-pull damage.

When every holder releases an attached organ, it springs toward its resting position. Released connections remain released. If another player is still holding it, one player's release does not force a reset.

Anesthesia, awakening and spoilage timers continue when players leave table mode. Leaving a still-running host is different from closing the saved world.

## 8. Work zones, tools and items

| Zone | Merchandise | Access and distinct actions |
|---|---|---|
| Head | Two separate eyes; one brain | Eyes have their own action and do not require opening the skull barrier. Brain access uses a prepared outer opening and saw-worked bone barrier. |
| Chest | One heart; one paired-lung item | Prepared outer opening, hammer-worked bone barrier, removal of loose large pieces, then organ interactions. |
| Abdomen | Two separate kidneys; one liver | Shared prepared opening, then individual organ connections and pulling. |

There are **eight organ merchandise items** in a complete set. The lungs are one combined item, not two separately tradable lungs. Extracting that combined item removes both lungs for the mortality rule.

Blood is a separate procedure, not a ninth organ in a zone.

### 8.1 Opening a zone

The player selects a zone, chooses a start position and direction, and the game constructs a suitable guide. The player follows it with a broad tolerance. Final openings use prepared geometry rather than arbitrary mesh surgery.

Minor deviation is forgiving. A predominantly sloppy local cut can reduce the quality of nearby organs by one grade. A direct cut into an organ independently causes a two-grade loss.

An opening serves the whole zone. Taking another organ from that zone does not repeat its complete opening sequence. Opening a zone alone does not start postmortem decay.

### 8.2 Saw and hammer

- The saw follows a marked segment through mouse movement.
- The hammer uses aiming and individual clicks for separate strikes.
- Barriers consist of large authored stylized pieces with readable progress.
- Freed obstructing pieces are removed manually and become physical debris.
- Tool differences should be visible and audible, without requiring a separate control language for every organ.

### 8.3 Tool ownership

Players pick actual tools from the reachable tray, table or trolley. Tools may be put down, passed or dropped. Do not replace the physical equipment setup with unlimited tools generated by the operation UI.

Core tools are reusable. Anesthetic stock, packaging and other explicitly consumable materials are depleted. Tool durability, sterilization and consumable cutting blades were not selected and are not required for this version.

## 9. Organ extraction and physical output

For each organ, release **2-3 abstract visible connections** with short tool movements, then grip and pull. Connection shape, arrangement, resistance and motion distinguish organs while preserving familiar controls.

Target active time is approximately **20-40 seconds per organ** early in progression. This is a feel target, not a mandatory hold timer. Shared zone access makes subsequent extractions faster; do not multiply a complete zone-opening sequence by the number of organs inside it.

During pulling:

- Smooth extraction is safe under the pulling rule.
- Abrupt pulling costs one quality grade.
- Visible stretch/motion and sound communicate tension.
- Cooperative pulling evaluates the shared result.
- Released attachment progress survives hand release and re-entry.

On detachment, the organ remains a physical object in the player's grasp. It may be passed, placed in a tray, put into storage, packaged or thrown. It is not automatically sold or credited as cash.

The organ's current quality is shown when inspecting the extracted item. Before extraction, appearance gives approximate information. Expensive assessment equipment reveals quality earlier.

There is no closing, stitching, tape or restorative step after extraction.

## 10. Anesthesia and awakening

### 10.1 Manual application

The player holds the application button while using a physical syringe. More time held delivers more of an abstract game amount and consumes more stock.

- NPC appearance and recognizable categories give approximate guidance.
- Face, movement and behavior communicate the outcome after application.
- Insufficient anesthesia produces inadequate sleep and an earlier awakening.
- A suitable amount gives the formula's intended sleep duration.
- Excessive administration can kill the NPC.
- There is no exact ideal-amount indicator or warning before overdose.

All amounts are game parameters. No real drug, dose, concentration, body-weight calculation or medical unit is required.

### 10.2 Formula tiers

| Formula | Intended sleep | Approximate stock price for ten nominal uses |
|---|---:|---:|
| Initial | 90 seconds | $200 |
| Improved | 180 seconds | $400 |
| Late | 300 seconds | $800 |

These stock sizes are approximate. Actual depletion depends on what players administer. Do not convert them into ten free activations regardless of button duration.

Formula access is unlocked through shared XP skills, not automatically by district entry and not by a separate cash fee for a recipe. The unlocked consumable must still be purchased.

### 10.3 Dosing tolerance and residual amount

The dosing subbranch widens the appropriate range in both directions: less is sufficient for full sleep and more is tolerated before overdose. It applies to every unlocked formula.

| Dosing rank | Width relative to the initial range |
|---|---:|
| None | 1.00x |
| I | 1.25x |
| II | 1.50x |
| III | 2.00x |

The bonuses are total improvements relative to the baseline, not additive or compounded bonuses. Dosing and duration can be upgraded independently.

The NPC retains a gradually decreasing abstract anesthesia amount. Additional administration adds to that remainder. Simultaneous applications from several players also add together. Reapplication is not an independent reset that ignores existing exposure.

Precise tolerance centers, depletion curves and mixed-formula behavior are proposed implementation presets in section 24. They must preserve the selected durations, widening rules, overdose risk and repeat-anesthesia rescue.

### 10.4 Awakening after extraction

After at least one organ has been removed, an awakening NPC creates an **eight-second intervention window**:

- If the torso is restrained, the NPC screams and moves as much as the limb restraints allow. Without successful re-anesthesia, the NPC dies from the game's shock event.
- If unrestrained and not physically held, the NPC attempts to escape, then follows the comic fall-and-death sequence if not successfully re-anesthetized.
- Successful re-anesthesia inside the window interrupts the pending fatal sequence.
- Overdose during the rescue can still kill the NPC.
- Movement alone does not automatically damage an organ. Actual tool contact can do so.

Before any organ extraction, inadequate restraint creates an escape risk on awakening; do not apply the post-extraction shock rule merely because an untouched NPC woke up.

Friends can physically hold a patient. The exact strength and transition behavior of player holding is a tuning dependency of the existing shared-body system, rather than an additional restraint inventory item.

## 11. Mortality rules

### 11.1 Extraction events

| Extracted item while NPC is alive | Base death chance |
|---|---:|
| First kidney removed | 10% |
| Second kidney removed | 20% |
| Liver | 30% |
| Eye | 0% |
| Heart | 100% |
| Brain | 100% |
| Combined paired lungs | 100% |

First/second kidney refers to extraction order, not a fixed left/right identity. Each extraction has its own single check. A prior successful survival check does not guarantee survival of the next extraction.

Each previously collected blood portion adds **10 percentage points** to the kidney/liver check:

| Prior blood portions | First kidney | Second kidney | Liver |
|---|---:|---:|---:|
| 0 | 10% | 20% | 30% |
| 1 | 20% | 30% | 40% |
| 2 | 30% | 40% | 50% |

For all three abdominal organs, with no other death event, the resulting probability of death is 49.6% with no prior blood, 66.4% with one portion and 79% with two. These are derived totals, not additional death rolls.

The eye's base chance is zero. Whether the blood modifier also applies to eye checks is explicitly a proposed interpretation in section 24; it was not independently settled in the interview. Terminal organs always remain terminal.

Once an NPC is dead, do not repeat survival checks. Persist completed checks and outcomes across loading, player changes and specialist takeover.

> **Decision 2026-10-18 (Fedya, after the capture → table playtests; supersedes the second-kidney and liver rows above).** The **liver** and the **second kidney** are now **always fatal** (100 %, no roll): either kills the NPC immediately at the moment of extraction. The **first kidney** keeps the chance roll (10 % plus 10 percentage points per prior blood portion, as in the tables above). Fedya re-checked the old 20 % / 30 % values and keeps the new rule. Implemented as `OperationTuning.liverOrBothKidneysFatal = true` (stage 1, `OperationState.Extract`); EditMode tests `OP18_*` and `OperationAbdomenRulesTests` cover it. With all three abdominal organs the derived totals above no longer apply: taking the liver or both kidneys always ends with a death.

### 11.2 Death consequences

Death does not immediately destroy the remaining organs. It starts the body decay timeline. Players may continue extracting from opened or unopened zones during that timeline.

If overdose kills the NPC **before the first organ extraction**, every remaining organ immediately loses **two quality grades**. This penalty is additional to subsequent ordinary postmortem decay.

The special early-overdose penalty must not be silently extended to every other cause of death. Ordinary extraction death and shock death use their stated rules.

## 12. Organ quality and damage

### 12.1 Intrinsic quality

Each organ has its own initial quality. An NPC's category and condition give an approximate expectation, but do not force every organ in that NPC to have the same grade.

Careful play preserves quality; it does not manufacture a higher intrinsic grade. Expensive assessment helps evaluate organs before extraction. Exact current quality is available when inspecting the extracted item.

| Level | Display name | Reference color family | Price multiplier |
|---|---|---|---:|
| 1 | Damaged | Muted gray/brown | 0.3x |
| 2 | Acceptable | Muted yellow/olive | 1.0x |
| 3 | Good | Green | 1.6x |
| 4 | Perfect | Blue | 2.6x |
| 5 | Perfect+ | Purple | 4.2x |

Russian display names and percent labels (BUYERS_SPEC v02): Убитое 20%, Сойдёт 40%, Хорошее 60%, Отличное 80%, Идеальное 100%. The user's supplied five-level image is the visual reference for order and colors. Exact palette values were not specified. The old `Normal` display label becomes **Acceptable** without shifting its tier or multiplier.

### 12.2 Damage events

| Event | Quality loss |
|---|---:|
| Predominantly sloppy local incision | 1 grade for associated nearby organs |
| Direct blade cut into an organ | 2 grades |
| Abrupt extraction pull | 1 grade |
| Strong drop or impact | 1 grade |
| Ordinary gentle contact | None |
| Early pre-extraction overdose death | 2 grades for all remaining organs |

Different damage events can add together. The floor is **Damaged**. Do not introduce an unselected sixth, unsellable organ grade.

Small guide deviations are forgiven. A sloppy section affects nearby associated organs, not every organ in the whole opened zone. Author that association with the prepared zone geometry.

One continuous damaging action is one event, not one penalty per rendering or physics frame. This is an implementation safeguard against accidental instant loss. A new distinct damaging action can cause another loss.

NPC movement does not directly lower quality. If it causes a held blade to contact an organ, the direct-cut rule applies.

### 12.3 Decay inside a dead NPC

**Confirmed:** there is a **45-second grace period** after death, then deterioration at **one grade per 40 seconds**. Appearance changes gradually to communicate worsening condition.

Opening a living NPC's zone does not start that timer. Death starts it once for the patient; opening another zone does not restart it.

**Proposed boundary interpretation:** no grade is lost during the first 45 seconds; the first full deterioration interval then ends at 85 seconds after death. Further grade losses occur at 125, 165 seconds and so on, down to Damaged. This explicit boundary is a preset rather than an additional user decision.

Extracting an organ preserves the quality losses it has already received. It then uses the extracted-item storage rules.

## 13. Packaging, containers and preservation

### 13.1 Packaging actions

An extracted organ remains physical. To package it, place it into an individual bag and briefly hold the sealing action. One bag holds one organ item; the paired lungs still count as one item.

Ordinary buyers accept unpackaged organs. Selected expensive orders require packaging. Organ packaging does not itself stop or reverse spoilage; refrigeration provides preservation.

Blood is different: the sealed $50 blood bag does not spoil or use organ quality tiers. The initial syringe-to-bag transfer is a distinct action; the later direct-to-bag device removes that routine.

### 13.2 Capacity and cooling

| Storage condition | Organ deterioration | Capacity / requirement |
|---|---|---|
| Ordinary tray, room or uncooled container | 1 grade per 5 minutes | No refrigeration |
| Portable cooler | 1 grade per 25 minutes | 8 items; no electricity or refrigerant |
| Powered stationary refrigerator | Paused | 24 items; paid base electricity |
| Unpowered stationary refrigerator | 1 grade per 5 minutes | Contents remain physically stored |

One organ or blood bag occupies one slot. A complete organ set occupies eight slots. A blood bag consumes capacity if stored, despite not needing cooling.

Preservation applies only to items actually accepted into the container's contents. Dropping an item near, on top of or through a refrigerator must not accidentally freeze its timer. The exact physical insertion/snap presentation is an implementation choice.

Cooling never restores lost quality. Changing containers must not reset deterioration progress. **Proposed implementation rule:** retain fractional progress toward the next grade loss and change its advancement rate with storage. Powered refrigeration freezes that progress; loss of power resumes it at the room rate.

## 14. Electricity and active-world time

One game day lasts **45 real minutes** of active-world time.

The phone's bills/taxes application lists every owned base, its paid-through time and current electricity status. Players can prepay **1, 3 or 7 game days** separately for each base. The phone warns before expiry.

| Base | Electricity per game day |
|---|---:|
| Wagon | $0 |
| Hamlet | $50 |
| Rough district | $100 |
| Downtown | $200 |
| Final laboratory | $500 |

These are flat base fees in the accepted first economy model. The wagon remains fully free.

When electricity expires, stationary refrigerators stop preserving organs and their contents use the ordinary room/tray deterioration rate. Paying again stops further refrigerator decay without repairing damage already incurred.

Daylight can be sufficient for early operations. Lamps and another player's light help in dark rooms and at night. The basic interactions must remain readable. Powered-device behavior beyond refrigeration is specified as a proposed preset in section 24, rather than a new requirement for a detailed electrical simulation.

Automatic renewal, electrical wiring placement, consumption meters and temperature controls were not selected. Do not add them as required systems.

When the saved world is closed, simulation time stops: no offline organ decay, electricity expiry, staff payday, awakening or XP progression. A client leaving an active host does not stop time.

## 15. Shared economy and purchase catalog

### 15.1 Shared business funds

Operation income and spending use a shared business cash fund. Any player can make purchases. Equipment, consumables, staff, electricity, operation-inspection bribes and inspection fines use this fund.

Record each transaction once. Simultaneous purchases cannot spend the same balance twice, and a failed transaction must not create merchandise or consume money.

### 15.2 Merchandise base prices

| Merchandise item | Quantity per complete set | Base price per item |
|---|---:|---:|
| Kidney | 2 | $250 |
| Liver | 1 | $350 |
| Paired lungs | 1 | $450 |
| Heart | 1 | $1,000 |
| Eye | 2 | $200 |
| Brain | 1 | $1,200 |
| Sealed blood portion | Separate collection | $50 fixed |

Ordinary organ sale value is base price multiplied by its current quality multiplier. Special-order premiums are a separate buyer contract, not another intrinsic quality tier.

A complete organ set has base value **$3,900**. At Good quality its gross value is **$6,240**. Using two nominal initial-anesthetic applications costs approximately $40, producing an illustrative **$6,200 before staff, electricity and other costs**.

That example is a comparison benchmark, not a measured average NPC profit: actual results depend on quality distribution, damage, survival, supplies and delays. An early Good abdominal set is only **$1,360 gross** before its own costs.

One concrete tuning issue is the specialist price gap. In a simplified all-Good complete set, a 5% per-organ one-grade error costs an expected $117 gross. After the specialist's 20% commission, avoiding those errors improves expected margin by $93.60 per set. The $60,000 higher hire price therefore takes about 641 such sets to recover through error avoidance alone, ignoring other differences. Preserve the selected prices in this revision, but do not describe their balance as validated; the premium needs a practical progression test.

### 15.3 Equipment prices

| Equipment | Purchase / hire price |
|---|---:|
| Replacement basic knife | $100 |
| Five-restraint kit | $500 |
| Work lamp | $250 |
| Saw | $1,500 |
| Hammer | $300 |
| Tray | $100 |
| Tool trolley | $500 |
| Portable cooler, 8 slots | $1,000 |
| Stationary refrigerator, 24 slots | $5,000 |
| Mop and bucket | $100 |
| Operation table | $1,500 |
| Helper, initial hire | $60,000 |
| Assessment / rare-feature equipment set | $90,000 |
| Basic operating specialist, initial hire | $120,000 |
| Error-free operating specialist, initial hire | $180,000 |

The assessment set provides early quality evaluation and supports later rare-feature / demanding-order content. Its exact rare-feature catalog and order rules are not invented by this specification.

### 15.4 Consumable prices

| Consumable | Price |
|---|---:|
| Empty blood bag | $5 |
| Individual organ packaging | $10 |
| Garbage bag | $5 |
| Initial anesthetic stock, about ten nominal uses | $200 |
| Improved anesthetic stock, about ten nominal uses | $400 |
| Late anesthetic stock, about ten nominal uses | $800 |

These prices are the accepted first economy model. Prices for the later direct-to-bag device and quick-release mechanism were not selected; proposed placeholders are listed separately in section 24.

### 15.5 Procurement

- Pharmacy: blood bags and initial supplies.
- Underground seller: specialist tools.
- Phone ordering: large equipment, delivered as physical crates at the base.

Delivered equipment still requires unpacking and placement. Delivery timing and seller-specific stock are implementation presets. Do not substitute instant installed furniture for the confirmed crate delivery.

## 16. Shared XP and anesthesia skills

### 16.1 Earning XP

> **Superseded on 2026-10-15** by `BUYERS_SPEC_2026-10-15_v02.md`, section «Решение v02 — опыт (XP)». Every sold organ gives 20 XP to each player present, and the first sale of a new organ type gives a large one-time bonus. Blood gives 5 per bag, with +50 for the first. An on-time special order gives +150. Team XP is the sum over the players present. The table below is the old v01 rule.

| First sale of a unique merchandise item | Shared XP |
|---|---:|
| Organ | 20 |
| Blood portion | 5 |

XP is awarded at first sale, not at cutting, detachment, packaging, dropping or transferring ownership. Specialist-produced merchandise also earns sale XP. A complete organ set yields **160 XP**, and two sold blood portions yield another 10 XP.

Each physical merchandise identity can reward XP once. Rebuying, reselling, reloading or moving an item between players cannot create repeated rewards.

### 16.2 Spending and ownership

Skills belong to the team in that saved world. Any player can use unlocked formulas.

Purchasing a skill directly spends free XP. Track lifetime earned XP separately so spending does not lower an already reached level. A skill purchase decreases free XP once and grants its unlock once.

### 16.3 Two independent subbranches

| Node | XP cost for this purchase | Prerequisite | Effect |
|---|---:|---|---|
| Initial formula | 0 | Starting access | 90-second intended sleep |
| Improved formula | 1,000 | Initial formula | Purchase access to 180-second stock |
| Late formula | 3,000 | Improved formula | Purchase access to 300-second stock |
| Dosing I | 500 | Initial dosing | Appropriate-range width 1.25x baseline |
| Dosing II | 1,000 | Dosing I | Appropriate-range width 1.50x baseline |
| Dosing III | 2,000 | Dosing II | Appropriate-range width 2.00x baseline |

Duration nodes do not require dosing nodes, and dosing nodes do not require advanced duration nodes. Dosing upgrades affect every formula. Formula unlocks do not provide unlimited or free anesthetic stock.

Buying both duration upgrades costs 4,000 XP total. Buying all dosing ranks costs 3,500 XP total. Buying all paid nodes costs **7,500 XP**.

At 20 XP per organ, the first formula costs 50 sold organs. With only two kidneys and a liver sold per early NPC, that is approximately 17 successful three-organ sets. This is a derived pacing warning for playtesting, not a guaranteed number of captures or a district lock.

## 17. Staff and automation

### 17.1 Helper

The helper costs **$60,000 to hire** and earns **10% of attributable merchandise profit**, settled daily.

Confirmed duties:

1. Carry a delivered NPC to an assigned table.
2. Position the NPC and fasten available patient restraints.
3. After the operation, release the restraints individually.
4. Carry the remaining body to a designated place inside the base.

A helper can service several assigned tables sequentially. The helper does not perform organ operations, collect the extracted merchandise, clean the workplace or automatically complete outdoor disposal.

The post-operation body task must distinguish a living patient from a corpse. A completed organ list alone must not silently kill the NPC or declare a living NPC safely disposed of.

### 17.2 Operating specialists

| Specialist | Initial hire | Execution error per extracted organ | Error loss | Commission |
|---|---:|---:|---:|---:|
| Basic | $120,000 | 5% | 1 quality grade | 20% |
| Error-free | $180,000 | 0% | None from execution error | 20% |

The error-free specialist preserves the quality that is still available; it does not improve intrinsic quality or reverse previous losses. Patient mortality and ordinary spoilage remain applicable to both types.

The basic specialist error check occurs once per extraction. Persist its outcome. It is distinct from the NPC survival check and must not roll every frame.

One specialist operates one assigned table. Parallel automatic operations require separate specialists. A helper can prepare and clear several of those tables in sequence.

For each table, players configure an organ list and extraction order. The configuration persists for later patients. A specialist begins with a prepared NPC when tools and consumables are available. Missing requirements pause work and report the reason; the world and patient timers continue.

Specialists use the physical setup and supplies. Do not create tools, anesthesia, output storage or free replacements for them.

### 17.3 Player takeover

When a player joins a specialist's operation, the specialist pauses. Players continue from the same shared state. The specialist resumes the saved stage after the last participating player leaves.

The specialist does not compete with a player's cursor for the same organ or tool. Pausing is not a world pause: anesthesia, awakening, decay and electricity continue.

### 17.4 Daily pay and debt

Staff pay is a percentage of profit from merchandise they worked on, not a percentage of all unrelated team revenue. When both helper and specialist participated, the two commission categories total **30%**.

Several helpers or specialists must not each charge their full category percentage on the same sale. Record participation and distribute that category's payment among eligible employees when necessary.

Commissions accrue from attributable sales and become due at the daily settlement. No additional fixed daily wage was chosen.

**Proposed profit definition:** sale revenue minus directly attributable consumables, before staff percentages and general overhead such as power, hiring and equipment. Allocate shared patient consumables once across that patient's output. Negative attributable profit generates no negative wage. This accounting definition needs implementation consistency; it was not separately selected by the user.

If the fund cannot pay, the amount remains a debt. Affected unpaid employees stop working until their debt is cleared. They remain hired; completed work is not undone. There is no automatic dismissal or forced negative shared cash balance under the selected rule.

## 18. Cleanup, smell and body removal

The table must be freed from its previous body before accepting the next NPC. Small stains and debris do not mechanically block the next operation, but leaving them has inspection consequences.

- Hold the cleaning action with the mop to remove a stain.
- Pick up larger waste manually and put it in a garbage bag.
- Carry the body separately.
- Other players may help with all these activities.
- Cleaning is physical work; it is not automatically included in helper duties.

Smell gradually increases while sources remain. It becomes noticeable inside before it reaches outside the base. Phone messages report neighbor complaints. Removing sources makes the smell fade gradually rather than instantly clearing all risk.

Smell can cause suspicion and a visit, but does not by itself provide enough evidence for arrest. Inspectors need corroborating findings.

**Existing contract:** disposal stays a simple game interaction. Existing designated river, lake and canal disposal locations remain valid game destinations. This does not erase witness risk or automatically reset district suspicion. A trash destination or comic disposal device may be content options, not a requirement to build a new complex subsystem.

The helper's indoor body-drop location is not final disposal. Placing a body there does not erase it, its smell or its evidence status. Waste containers likewise remain part of the physical world until the game disposal interaction actually completes.

Exact odor buildup, decay and evidence weights are proposed presets in section 24. A detailed city-wide discovery simulation is not required for this first version.

## 19. Operation-related police inspection

This section defines a specific base-inspection outcome. It must not accidentally apply an additional ordinary-arrest penalty on top of its own package.

### 19.1 Visit and entry

Both visible suspicious signs and accumulated district suspicion can cause visits. Smell contributes to suspicion and visit eligibility.

District suspicion uses a **0-100** scale:

- Below 75, players may refuse entry **before** police enter.
- A lawful refusal adds no suspicion penalty.
- At 75 or above, police have a warrant and entry cannot be refused.
- Once police have entered, the player cannot revoke the search through a refusal interaction.

Police arrive at the door and inspect accessible rooms after entry. The search must use discovered evidence rather than automatically reading every item owned anywhere in the world.

### 19.2 Evidence and successful inspection

A discovered body, body part or extracted organ is sufficient major evidence. Stains, used supplies and small waste accumulate evidence; a single incidental stain is insufficient.

The refrigerator is not immunity for its contents. Inspectors can discover stored merchandise. The details of search reach and minor-evidence scoring are presets; the distinction between discovery and omniscient inventory access is a required design boundary.

If the inspection finds insufficient evidence and passes cleanly, district suspicion decreases by **25 points**, clamped at zero.

### 19.3 Bribe or arrest

When sufficient evidence is found, players choose between paying the displayed bribe and the scripted arrest. Insufficient shared funds leave arrest as the available outcome.

| Inspected base location | Base bribe |
|---|---:|
| Hamlet | $500 |
| Rough district | $1,500 |
| Downtown | $4,000 |
| Final laboratory | $8,000 |

Total bribe = location base amount + **25% of the sale value of discovered merchandise at its current quality**. Blood uses its fixed $50 value. A body without discovered merchandise does not acquire an invented merchandise sale value.

Successful payment ends the inspection: police leave, there is no arrest or confiscation, and suspicion stays unchanged. Paying does not count as a clean inspection.

Exact rounding and valuation against special-order bonuses are implementation presets. A return-visit cooldown is needed so unchanged suspicion does not create immediate repeated bribe demands.

### 19.4 Arrest package

The chosen outcome is a short scripted arrest of players present at the base, followed by transfer to the station. Players elsewhere are not automatically teleported into this inspection arrest.

The financial and property consequences occur **once per inspection incident**, rather than once per arrested player:

1. Fine: **10% of the shared business cash fund**.
2. Confiscate all discovered organ and blood merchandise, including discovered refrigerator contents.
3. Confiscate equipment and tools worth approximately **30% of their pre-incident purchase value**, preserving approximately 70%.
4. Set the inspected district's suspicion to **30/100** after the punishment.

Confiscation affects the inspected base and detained players. Other owned bases are unaffected.

### 19.5 Protected working setup

Protect the existing stationary refrigerator and the basic working kit: a simple table, basic knife, syringe and one nominal initial-anesthetic application where those items already exist. The refrigerator still needs paid electricity.

The final 70% preservation rule supersedes the earlier near-total seizure proposal. The basic kit is a protection floor within that rule, not a second rule that limits survivors to starter items.

Do not grant free furniture or restore absent equipment. In particular, a wagon does not gain a table through arrest.

Because equipment is indivisible and protected items may make up most of a small base, the result can preserve more than 70%. **Proposed selection rule:** select eligible items as close as possible to 30% of total equipment purchase value without exceeding that target or touching the protected floor.

After the station sequence, return players to the station exit under the existing station-release contract. No additional prison minigame, sentence timer or escape quest was chosen.

The prior blanket protection against equipment seizure is explicitly superseded for this inspection scenario. The older ordinary-arrest rule of a 10% cash penalty plus the highest-value carried item must not be charged again on top of this package. Ordinary street arrests remain a separate integration contract.

## 20. Persistence and authoritative state

**Existing contract:** extend the existing project systems. Use one stable NPC identity, one movement owner per body and one authoritative shared rigidbody state. FishNet clients request interactions; shared-object results are authoritative. Do not build a second patient, grab, inventory, cash or save system just for operations.

Persist at least:

| Domain | Required state |
|---|---|
| NPC | Stable identity, alive/dead state, blood count, intrinsic organ grades, removed organs, death/check outcomes |
| Anesthesia | Remaining abstract amount, active formula contribution, remaining sleep, pending eight-second event |
| Table | Assigned NPC, pose, individual fasteners, open zones, barrier progress, released organ connections |
| Merchandise | Stable item identity, type, current grade where applicable, packaging, container, deterioration progress, sale/XP receipt status |
| Equipment | Identity, location, placement, table reach association, ownership |
| Power | Paid active-world time and current status per base |
| Staff | Hire type, assignments, table programs, paused stage, participation records, accrued commission and debt |
| Business | Shared balance, free XP, lifetime XP, purchased skill nodes |
| Inspection | District suspicion, active visit stage, discovered evidence, incident identity and already-applied consequences |
| Cleanup | Remaining stains/debris/body objects, smell progression and complaint/visit cooldown state |

All active-world timers resume from saved remaining time. Do not charge offline time by comparing an absolute real-world clock against saved organ or power deadlines.

### 20.1 Atomic events

Apply these once as coherent state transitions:

- Organ detachment, physical output creation, patient extraction state and the associated survival/error results.
- Merchandise sale, cash receipt, XP receipt and staff attribution.
- Skill payment and unlock.
- Equipment payment and delivery identity.
- Bribe payment and end of the inspection.
- Arrest fine, confiscation and district suspicion reset.

Two players completing the same action cannot create two organs, sell one item twice, release the same reward twice or pay the same incident twice.

If several organ extractions complete together, serialize their authoritative completion order. A terminal extraction may kill the NPC before a later completion; the later completion must then use the dead-patient path rather than reroll a survival state.

### 20.2 Leaving and interruption

Closing a local magnifier, leaving table mode, dropping a tool, disconnecting a client and pausing a specialist are not rollback events. Finished cuts and released connections remain finished. A pending pull can spring back when its last holder releases it.

World closure freezes simulation. Reopening continues the same simulation rather than rebuilding untouched NPCs, fresh goods or free bills.

## 21. Existing prototype and migration boundaries

The current project has an offline kidney-operation prototype and a clinic loop. Their existence is not evidence that this complete design is implemented or network-tested.

Relevant existing code includes:

- [KidneyMiniGame.cs](../../Assets/OnlyVolunteers/Operation/Scripts/KidneyMiniGame.cs): guided cutting, pulling, abrupt-pull penalty and the old tape stage.
- [OrganQuality.cs](../../Assets/OnlyVolunteers/Operation/Scripts/OrganQuality.cs): existing quality representation.
- [ClinicOperationRunner.cs](../../Assets/OnlyVolunteers/Clinic/Scripts/ClinicOperationRunner.cs): current clinic operation path.

Adapt existing behavior where useful:

| Current / earlier behavior | Target behavior |
|---|---|
| Separate kidney incision sequence per organ | Persistent shared zone opening |
| Old post-extraction tape stage | Removed |
| Tools generated for the isolated minigame | Physical tools from reachable work surfaces |
| Prototype operation completion can directly credit income | Physical merchandise sold through the buyer flow |
| `Normal` display tier | `Acceptable`, preserving tier identity |
| Earlier operation table in wagon | No wagon table; first-person blood only |
| Earlier four-table ordinary-base assumptions | 0 / 1 / 2 / 3 / no fixed laboratory cap |
| Earlier blanket permanent-equipment protection | Inspection-specific approximately 30% equipment seizure with protected floor |
| Earlier automatic district anesthesia access | Shared XP duration and dosing branches |
| Earlier generic blood spoilage assumption | Sealed blood is fixed-price and does not spoil |

Current-state documentation reports an isolated operation test and incomplete network validation. Do not claim a production-ready four-player operation, laboratory economy or save system based on that prototype.

Implementation should proceed in bounded stages:

1. One Hamlet table, one NPC, torso/limb restraints, initial anesthesia and abdomen extraction with physical output.
2. Quality damage, death/grace timing, blood packaging and storage/power.
3. Shared participation and authoritative interruption/save cases.
4. Additional zones and their stylized barriers/tools.
5. Staff, shared XP, procurement and economy integration.
6. Cleanup and operation-related inspection consequences.

These are implementation recommendations, not authorization to modify code as part of this document-writing task. Preserve working capture, van, movement and map systems.

## 22. Required presentation, assets and feedback

### 22.1 Physical content

Required content includes:

- Table, five individually readable fasteners, reachable tray and trolley.
- Knife, syringe, anesthetic stocks, saw, hammer, lamp, mop and bucket.
- Reusable operation-capable NPC presentation with prepared head/chest/abdomen openings.
- Large authored barrier pieces and removable debris; organ-local connection visuals.
- Eight organ outputs with the paired lungs treated as one item.
- Filled syringes, blood bags, organ bags and garbage bags.
- Portable cooler, stationary refrigerator and equipment-delivery crates.

Use existing accepted assets where available. Asset replacement, provenance and visual acceptance follow the project art workflow; this spec does not approve a new visual style or paid generation.

### 22.2 Animation and interaction feedback

Cover these readable events:

- Physical table placement and short pose alignment.
- Limb adjustment, each fastener closing and each opening.
- Anesthesia application, sleep, weakening and awakening.
- Restrained movement, holding assistance, interrupted rescue, shock death and comic failed escape.
- Guided opening, distinct saw motion and hammer impacts.
- Connection release, shared pulling, spring return, abrupt pull and physical detachment.
- Packaging/sealing, container acceptance, power loss, cleaning and waste placement.
- Helper carrying/preparation and specialist work/pause/resume.
- Door visit, search, bribe acceptance, scripted arrest and station release.

Use short stylized effects and sound. The sound and deformation should explain resistance, mistakes and completion. Do not require realistic anatomy, detailed wounds or graphic gore to communicate a state.

### 22.3 Interface information

Provide readable feedback for:

- Selected zone and its existing opening/progress.
- Reachable tools and who is holding an object.
- Fastener state, especially whether the torso is secured.
- Approximate NPC sleep/waking behavior and the urgent eight-second intervention.
- Exact quality on inspected extracted organs, with the approved five names and colors.
- Container occupancy, active cooling and loss of base power.
- Shared funds, free/lifetime XP and skill cost/prerequisites.
- Bills per base and electricity-expiry notifications.
- Staff assignment, missing requirements and unpaid debt.
- Police entry/refusal availability, bribe total and arrest consequences.
- Neighbor complaints and source cleanup.

Do not add an exact ideal-anesthesia marker or advance overdose warning. Do not require the normal operation HUD to expose implementation counters.

## 23. Acceptance checks

These are requirements for future implementation verification. They were not executed against gameplay as part of writing this file.

| ID | Scenario | Required result |
|---|---|---|
| OP-01 | Start the blood prologue in the wagon | No table or electricity purchase required; first-person syringe collection is available. |
| OP-02 | Collect from one ordinary NPC | Portion takes 4-5 seconds; second collection clearly weakens the NPC; third is fatal; loading does not reset count. |
| OP-03 | Seal and sell blood | Bag sells for $50, has no organ grade and never spoils, including without cooling. |
| OP-04 | Move between progression bases | Table capacities are 0, 1, 2, 3; final laboratory has no fixed design cap; old bases remain. |
| OP-05 | Prepare a table with only the torso fastened | NPC cannot escape; unsecured limbs still move; other fasteners improve stability. |
| OP-06 | Operate without a kit | Sleeping/held operation is possible; awakening creates the selected risks rather than an artificial start lock. |
| OP-07 | Join one table with four players | Shared fixed viewpoint, local magnifiers, one shared patient, independent tools and concurrent zones. |
| OP-08 | Open abdomen and take several organs | Opening persists; no repeated complete incision or tape stage; later organs need less access work. |
| OP-09 | Work on head and chest | Eyes do not need skull opening; saw and hammer have distinct inputs; large freed pieces can be removed. |
| OP-10 | Release organ connections, pull and let go | 2-3 organ-local connections are distinct from restraints; spring return preserves released connections; another holder can continue. |
| OP-11 | Make local and direct-cut errors | Sloppy local incision affects associated organs by one grade; direct organ cut independently removes two; unrelated zone organs are unaffected. |
| OP-12 | Yank, drop and gently touch output | Abrupt pull and strong impact each cost one grade; gentle touches do not; repeated physics frames do not multiply one event. |
| OP-13 | Inspect organs from one NPC | Intrinsic grades may differ; output inspection reveals exact current grade; no skill creates a higher intrinsic grade. |
| OP-14 | Use too little, suitable and excessive anesthesia | Short sleep, formula sleep and overdose outcomes occur without an exact ideal marker or pre-overdose warning. |
| OP-15 | Apply anesthesia early or from two players | New amount adds to residual state; combined exposure can overdose; inputs cannot overwrite each other. |
| OP-16 | Wake an operated, torso-restrained NPC | Eight-second rescue window works; successful re-anesthesia cancels pending shock; failure causes death. |
| OP-17 | Wake an operated, unrestrained NPC | Escape/fall/death behavior follows the same intervention contract, without turning into permanent NPC invulnerability. |
| OP-18 | Remove organs and test mortality | Kidney/liver probabilities include prior blood; heart/brain/paired lungs are terminal; results occur once and persist. |
| OP-19 | Cause pre-first-extraction overdose death | All remaining organs immediately lose two grades; later ordinary corpse decay still applies. |
| OP-20 | Delay after death and extract later | Grace and post-grace deterioration operate; zone opening does not reset them; output retains existing losses. |
| OP-21 | Move organs between storage states | Room: 5 minutes/grade; portable: 25; powered stationary: paused; no progress reset or quality restoration. |
| OP-22 | Fill coolers and cut power | Capacity is 8/24 slots; paired lungs use one slot; power loss resumes normal deterioration; sealed blood remains preserved. |
| OP-23 | Pay electricity at two bases | Separate paid periods and flat fees; 1/3/7-day purchase options; warning before cutoff; wagon remains free. |
| OP-24 | Sell or repurchase the same merchandise | Cash/XP receipt is atomic; sale XP is 20/5 once per unique merchandise identity, including specialist output. |
| OP-25 | Buy all anesthesia nodes | Correct individual XP costs and prerequisites; two independent branches; lifetime XP does not decrease; final dosing width is 2x, not stacked bonuses. |
| OP-26 | Assign helper and specialists | Helper prepares/clears several tables serially; one specialist serves one table; helper does not clean or collect goods. |
| OP-27 | Join an automatic operation | Specialist pauses, players take over; it resumes after all player participants leave; world timers continue. |
| OP-28 | Test staff payout and shortage | Attribution does not tax unrelated sales or multiply category rates; 10% + 20% when both participate; unpaid staff pause and remain hired. |
| OP-29 | Leave stains and waste, then clean | New operation can begin after body removal; smell builds/fades gradually; mop and manual bagging work; helpers do not erase evidence automatically. |
| OP-30 | Refuse entry at suspicion 74 and 75 | Refusal available before entry at 74 without added suspicion; unavailable at 75; unavailable after entry at either level. |
| OP-31 | Pass inspection with insufficient evidence | Suspicion decreases by 25, clamped to zero; smell alone does not convict; one incidental stain is insufficient. |
| OP-32 | Pay a displayed inspection bribe | Correct district base plus 25% discovered merchandise value; one shared payment; no seizure or arrest; suspicion unchanged. |
| OP-33 | Accept an inspection arrest with several players | One 10% incident fine; discovered merchandise confiscated; approximately 30% equipment seizure respecting protected kit/fridge; other bases unaffected; station release; suspicion 30. |
| OP-34 | Save during work, bills and inspection | Identity, progress, outcomes, clocks and receipts survive; world closure causes no offline progression or duplicate penalties. |
| OP-35 | Exit table mode or disconnect one client | Host simulation continues; remaining players keep the same patient and physical outputs; completed stages do not reset. |

Subjective acceptance requires actual playtesting: early organ timing, leg/arm adjustment, shared camera readability, tool reach, joint pulling, comedy and the cost of recovering from an inspection. A compile or scripted test cannot establish these qualities.

## 24. Proposed presets and remaining integration details

This section is deliberately separate from confirmed decisions. It replaces further interview rounds with visible, adjustable first-pass choices. These defaults may be used for an initial implementation, but are not approved balance results.

| Key | Proposed first-pass choice | Reason / unresolved boundary |
|---|---|---|
| T-01 | Appropriate amount centered on normalized target 1.0, with initial interval 0.8-1.2; widen symmetrically by rank. No real medical units. | Initial range width and category variation were not selected. At ranks I/II/III, example intervals become 0.75-1.25, 0.70-1.30 and 0.60-1.40. |
| T-02 | Keep a remaining-sleep timer and a separately decaying abstract amount. New valid application adds amount and extends sleep to at least its computed duration; never shortens an existing longer sleep. | Must support insufficient sleep, residual overdose risk, mixed formula stocks and repeat rescue without contradicting 90/180/300-second targets. Exact curves require a feel test. |
| T-03 | Apply the +10-point-per-blood-portion modifier to all nonterminal extraction rolls, including the eye's zero baseline. | Kidney/liver examples are confirmed; eye extension was not separately resolved. Keep this rule configurable. |
| T-04 | First corpse grade loss at death +85 seconds, following a 45-second grace and one complete 40-second interval. | The grace and interval are confirmed; the discrete boundary convention was not explicitly chosen. |
| T-05 | Preserve fractional extracted-organ deterioration across storage transitions. | Prevents cooling toggles from resetting the clock; does not change confirmed rates. |
| T-06 | Unpackaged introductory blood gets a 120-second active-world freshness allowance; sealing preserves it. Guarantee a usable first-sale route and subsequent syringe access. | Unsealed-blood allowance and syringe refill/recovery details were not chosen. Sealed blood remains fixed-price and nonperishable regardless of this preset. |
| T-07 | Minor evidence threshold 5; one stain 1, used supply 1, suspicious debris 2, discovered filled blood stock 3; major evidence bypasses the total. | Only the major/minor distinction and single-stain protection are confirmed. Repeated contacts with one object must not count it repeatedly. |
| T-08 | Persistent unattended sources become noticeable indoors after about 1 minute and externally after about 3; smell clears over about 2 minutes after all sources are removed. First external complaint adds 5 suspicion once per uncleared episode. | Numerical odor and suspicion tuning was not chosen; do not increment once per frame or automatically convict by smell. |
| T-09 | At least 10 active-world minutes between completed inspection visits to the same base, unless a separate explicitly authored escalation event occurs. | Prevents instant repeated visits after a bribe leaves suspicion unchanged. General city patrol scheduling remains outside this spec. |
| T-10 | Display whole dollars; round monetary fractions to nearest dollar with halves upward, consistently for bribes, fines and settled pay. | Rounding was not selected. Keep fractional commission accrual internally until settlement to avoid repeated rounding losses. |
| T-11 | Buy electricity as a rolling 45/135/315-minute active-world duration; warn with 5 minutes remaining. | Calendar boundary convention and warning lead time were not chosen. No offline expiry or automatic renewal. |
| T-12 | Base electricity also powers installed electric lamps and the assessment device. Manual knife/saw/hammer work remains possible without it when visibility is adequate. | Only refrigerator dependence and early natural-light play were explicitly settled. |
| T-13 | Direct-to-bag device $1,500; quick-release mechanism $2,000, offered after the corresponding manual routine is established. | Placeholder prices/unlocks, not part of the accepted catalog. No additional skill branch is implied. |
| T-14 | Garbage bag holds eight small waste pieces; body carrying stays separate. Cleaning progress persists on interruption. | Waste capacity, individual cleanup times and bag acceptance rules require content tuning. |
| T-15 | Large-equipment delivery creates one paid crate after 30 active-world seconds at a valid base delivery position. | Delivery delay and invalid-position recovery are unselected; guarantee no lost paid purchase or duplicated crate. |
| T-16 | Station exit release follows the short existing arrest sequence; no additional wait penalty. | The interview selected station consequences but not a separate jail activity. |

Additional integration work that does not require reopening the interview:

- Author NPC-category quality distributions and visual hints; use known-grade fixtures for the first tests rather than inventing a claimed production distribution.
- Define nominal stock consumption, input speed, tool tolerances and impact thresholds through the first playable slice.
- Use the profit definition in section 17 as a documented preset; choose a deterministic allocation for shared consumables and partial daily payments.
- Resolve street-arrest versus inspection-arrest fund attribution without stacking two penalty packages.
- Preserve the existing buyer contact progression and distinguish ordinary sales from packaging-required orders.
- Define the exact rare-feature set and demanding orders in their own content specification; the $90,000 assessment purchase does not approve an invented catalog.
- Map existing simple disposal points to game interactions; detailed waste rediscovery and later automatic disposal remain separate content work.
- Set performance and staff pathing limits for the physically uncapped final laboratory through measurement rather than a hidden four-table design limit.

## 25. Reference material and document verification

Reference files:

- [Product direction](../PRODUCT.md).
- [Current canon](../VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md), especially operations, disposal, police, XP and first-experience sections.
- [Current implementation state](../CURRENT_STATE.md).
- [Architecture](../ARCHITECTURE.md).
- [Earlier operation presentation draft](../drafts/OPERATION_PRESENTATION_DRAFT.md): reference only; its unapproved proposals do not override this interview.
- [Earlier economy/progression draft](../drafts/ECONOMY_PROGRESSION_DRAFT.md): reference only.
- [Map revision specification](MAP_SPEC_2026-10-13_v01.md): environment and layout companion.

The user's final interview decisions are the source for the confirmed rules in this revision. This document preserves unresolved numerical details as proposed presets, rather than presenting them as additional user approvals.

Document verification performed for this writing task:

- **PASS:** no Cyrillic text in the English specification.
- **PASS:** all 10 relative file links resolve locally.
- **PASS:** 25 numbered main sections and 35 uniquely identified acceptance scenarios are present.
- **PASS:** arithmetic for complete/abdominal set values, the consumable-cost benchmark, all three abdominal mortality totals, skill costs, sale XP and cooler rate was checked.
- **PASS:** final interview decisions were reviewed against their superseded variants; implementation presets remain labelled separately.
- **NOT RUN:** Unity gameplay, multiplayer, performance and subjective acceptance. This task changed only the new specification file.

