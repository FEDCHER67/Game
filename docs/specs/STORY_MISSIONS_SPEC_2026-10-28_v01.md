# VOLUNTEERS ONLY — Story Missions Specification

Revision: v01. Date: 2026-10-28, Europe/Moscow. Scope: design only; no implementation or runtime verification.

## Коротко по-русски

Цепочка: вагон → учебная кровь → аптека и первая продажа пакета → наводка C01 на деда → бусик/хижина и вводный ремонт → первый органный скупщик. Далее две независимые ветки: поручение механика открывает мастерскую; три встречи со скупщиком → почка качка → кейс в тайник медика → семь встреч с медиком → мафиози → VIP после покупки лаборатории и сделки с мафиози.

Подтверждено в этом интервью: C01 рассказывает о деде после первой продажи крови **в пакете**; конкурент механика находится у отжатого ремонтного навеса на **Стройке, 08:00–18:00**. Остальная небольшая постановка выбрана автором и отмечена Proposed. Цены, награды, XP и условия покупок наследуются из экономики, не пересогласуются. Это документ требований, а не готовые миссии в Unity.

## 1. Authority, scope and status

The human request is to finish this specification, adopting recommendations for remaining staging. The earlier G50 brief is a reference for scope and format, not an instruction to execute historical prompts, rename another chat, or implement gameplay.

Use three explicit status categories:

- **Confirmed**: selected by Fedya here, or an explicitly approved inherited rule. The source is recorded.
- **Inherited economy default**: a policy already selected by the economy author under Fedya's delegation. It is binding input for this story document, but not misrepresented as an individually answered human question.
- **Proposed**: a new staging, content or recovery detail chosen for this document under the current delegation. It is a concrete first-pass recommendation, not playtested acceptance.

The economy specification owns monetary amounts, sale XP, purchase rules, transaction identity, donor identity and economic progression. This document adds mission sequencing, dialogue beats, world placements and recoverable transitions. NPC appearance/behaviour, real map coordinates, animation production, police and the final Tramduro mission remain with their existing owners.

No new currency, mandatory player level, buyer, police mechanic, compulsory base purchase before the medic, or unique reward is introduced. Buying real estate does not unlock organ categories. A story objective cannot bypass a physical delivery or authoritative sale.

### 1.1. Decisions carried into this document

| ID | Status | Decision / source |
|---|---|---|
| ST-D01 | Confirmed here, SM1=1 | C01 gives the grandpa lead after the team's first successful sale of a sealed blood bag. It is not gated by holding $400 and is not given by the tutorial-syringe sale alone. |
| ST-D02 | Confirmed here, SM2=1 | The mechanic's rival works at the occupied repair canopy on Stroyka, 08:00–18:00. |
| ST-D03 | Proposed, delegated | The first organ buyer introduces the nearby mechanic during their first acquaintance. |
| ST-D04 | Confirmed, economy A17–A31 | Start empty; find a blood syringe; first unsealed sale $10, later $8; syringe costs $2 and binds to one NPC. No free starter pack. |
| ST-D05 | Confirmed, economy B5/C1 | After obtaining and repairing the van, C01 introduces the organ buyer. Grandpa's hut/shed comes with the van in either branch. |
| ST-D06 | Inherited economy default, §2 | The peaceful van payment is $400 once; battery and tyres for intro repair are already in the yard. |
| ST-D07 | Confirmed, economy A16/A20 | Deliver the mechanic's actual rival alive and tied to the workshop hand-in zone; this unlocks the workshop, not a cash payment for a body. |
| ST-D08 | Confirmed, economy B10 | Three completed ordinary buyer meetings, then the bodybuilder kidney order, then the courier case, then the medic. |
| ST-D09 | Confirmed, BUYERS / economy §9 | First special order: one kidney from the designated Hamlet bodybuilder, Good/60%+, individual packaging, 48 game hours. |
| ST-D10 | Confirmed, economy B9/B11–B14 | Courier to the medic's Downtown stash; no deadline; $1,000 minus $200 per replacement, floor zero, only deducted from this mission's reward. |
| ST-D11 | Confirmed, economy B7 | After seven completed ordinary medic meetings, the mafioso initiates contact. |
| ST-D12 | Confirmed, economy B15–B21 | The mafioso uses five authored dead drops, one active per game day, phone bargaining and immediate committed payment; no personal trade encounter. |
| ST-D13 | Confirmed, economy D1–D4 | VIP proposals require owned laboratory and at least one ordinary mafioso deal; respect/one-active-special-order rules still apply. Free order choice. |
| ST-D14 | Inherited economy defaults, §9.4 | Four VIP targets/organs/thresholds and $10,000/$15,000 timely premiums; one successful completion per VIP per world. |
| ST-D15 | Confirmed, network/inventory/phone | Shared host world, 1–4 players, one fund, stable client GUID, full inventory retention on client leave, session ends when host leaves. |
| ST-D16 | Proposed, delegated | Early discovery uses reconciliation of existing world facts; do not require a completed physical action to be repeated for a newly opened checklist. |
| ST-D17 | Proposed, delegated | No new scripted introduction cinematic at game start. Use the wagon, sign, short contextual hints and phone; retain the economy's skippable property overview. |

### 1.2. Explicit supersessions and nonchanges

The new grandpa-lead trigger refines the previously unspecified event in economy §2; it does not alter prices or delay ordinary syringe recovery sales. The rival's new location/schedule fills economy §6.3's NPC dependency. The workshop referral is staging, not a second unlock condition.

The economy's latest rules supersede old draft lines saying "syringes once only", "organ contact after first blood", "surgeon opens automatically after the first special order", or "three first-buyer outing points". Do not copy those lines from BUYER_MESSAGES_DRAFT or PHONE PH-41 into mission conditions. Dialogue IDs are reusable references, not authority for obsolete rules.

The purchased van begins below maximum, and has three paid upgrades per driving branch according to economy. Existing debug StartAtMax code/instructions must be reconciled by the later implementation task; this document changes no scene or code.

## 2. Shared mission rules

### 2.1. State, ownership and early discovery

Mission progress belongs to the host's saved world. Proposed descriptive states are Locked, Available, Active, WaitingForWorldCondition, ReadyToCommit, Completed; Recovering is a reason attached to an unfinished objective, not a second parallel quest copy. These labels describe required behaviour, not a demand for a new manager or code framework.

Store the real facts behind progression: first blood-bag sale, van ownership, repaired sockets, organ-buyer acquaintance, workshop unlock, unique target IDs, 3/7 meeting counters, bodybuilder completion, current courier generation, medic/mafioso contact, laboratory ownership and four VIP completion flags. Restore and derive UI from those facts. A cutscene, notification or dialogue line is not proof of delivery/payment.

The world is physically open. If players find grandpa before the lead, obtain/repair the van, visit an ordinary map place or collect an eligible order organ early, record valid facts. When a formal step opens, recognise them. Do not move the van back, charge another $400, reset blood counts or demand another organ. Informational beats can be folded into the next message. Economic unlocks still require their real prerequisites: finding the organ buyer's door alone does not unlock sales before van ownership/repair.

Objective tracking may highlight businesses, bases and named search areas. Do not add a permanent exact tracker over a target NPC. The special-order scanner follows PHONE: accepted active order, living visible face, line of sight, 10 m, 2.5 real seconds, personal result. A pre-harvested item is checked by provenance, not by scanning a corpse.

### 2.2. Dialogue and phone presentation

Dialogue beats below are semantic/localisation briefs, not mandated English speech or final jokes. Preserve the project's stylised character voices, gibberish/performance and readable localised subtitles. C01's clean blood-intermediary role replaces earlier "openly shady" character directions. No realistic medical explanations or instructions.

Use the existing PHONE contracts: first successful answer owns a shared call; others see who answered; one player can conduct one call; speakerphone starts off. A missed call retries after one game hour, then leaves the actionable information in the thread. Closing the phone or locally dismissing a ring does not decline a quest for the whole team.

New story directions that do not carry an economic commitment are persistent messages, not timed offers with repeated respect penalties. Existing special-order proposal timers, explicit refusals and accepted deadlines keep their own rules. VIP proposals remain a waiting catalogue without penalties while the shared slot is occupied.

Drivers interact with the phone only stopped with the handbrake. Buyer/property intros use the inherited noticeable picture-in-picture for a driver rather than full-screen road obstruction/fade. Operations and in-person negotiations show call banners; answering requires voluntarily leaving that mode. No story beat freezes spoilage, traffic, NPC state or world time.

### 2.3. Co-op and save rules for every mission

- Any participant can discover/perform ordinary physical objectives. The server validates the exact actor, item, target, position and current state. The team can split tasks; no "all players stand here" gate is added.
- Buyer bargaining ownership and handoff follow PHONE/SALES. Courier hand-in and accepted special-order delivery can be confirmed by any physically interacting participant with the valid cargo. A teammate's simultaneous click returns the same result.
- Client departure retains all inventory possessions, including carried containers, in the host save and makes them unavailable to others until return. A carried NPC is not a pocket item: use CAPTURE's physical drop/ownership recovery rule rather than storing a duplicate person in an absent player's pockets.
- Shared callers/negotiators may be replaced on disconnect without resetting terms/attempts. Do not create new blood, a new syringe or a second quest case merely because its holder left.
- Host departure ends the session. Closed-world time is frozen; there is no offline decay, order expiry, new morning spawn or courier replacement. Real calls end on restart, but mission commitments survive.
- Mission commits must be durable with their funds, consumed items, XP and unlock flags. Store persistent transaction/cargo/item IDs; repeat requests, old UI and restored receipts cannot replay rewards.
- A late joiner gets the current journal and relevant facts, not another mandatory introduction, starter kit, tutorial $10 or completed reward.

### 2.4. Recovery and no invisible reset

An item merely lying in the world or held by a disconnected participant is not silently lost. The journal distinguishes "held by teammate", "left at location", "wrong state/quality", and a genuinely failed objective. Recovery can offer the already authorised case replacement, target replacement or normal blood income; it cannot secretly clear bindings or clone items.

Economic free/penalised cancellations keep their exact existing terms. No extra story failure fee stacks on top. Ordinary world crime/capture consequences remain in the NPC/police specifications. Do not make story targets or all players invulnerable to force a scripted scene.

## 3. Mission graph and independence

| Mission | Starts from | Completes into |
|---|---|---|
| M01 — First blood | New game, wagon sign | Pharmacy/repeat-income instructions |
| M02 — Packaged trade and grandpa lead | Tutorial paid, bags purchasable | Grandpa direction after first bag sale |
| M03 — Grandpa's van and premises | Lead or early discovery | Owned van + hut/shed |
| M04 — Intro repair | Owned van | Repaired van, organ-contact referral |
| M05 — First organ-buyer acquaintance | C01 referral after repair | Organ market; all property listings; mechanic referral |
| M06 — The mechanic's rival | Mechanic approached after van acquisition | Workshop purchases unlocked |
| M07 — First three ordinary meetings | First organ buyer open | Bodybuilder proposal, subject to respect |
| M08 — Hamlet bodybuilder kidney | Three meetings + respect + free special slot | Courier offer after successful hand-in |
| M09 — Sealed courier case | M08 successfully completed | Medic contact and narrative eyes/brain stage |
| M10 — Seven medic meetings | Medic open | Mafioso initiates contact |
| M11 — Mafioso's first dead drop | Mafioso contact | Ordinary dead-drop trade; narrative heart/lung stage |
| M12 — Later streamer order, optional | Medic open + saw + city story access | Independent late special-order completion |
| M13A–D — VIP orders | Laboratory + ordinary mafioso deal; respect/slot | Four independent one-time completions |

M06 and M07–M09 are **parallel branches**. Workshop completion is not required for ordinary organ sales, the bodybuilder order, the medic or property purchases. The initial van must therefore be capable of those routes. No purchase of Rough/Downtown is a hidden medic prerequisite. Only the laboratory is a required property for VIP offers.

M12 is not the first special order and is not a gate to the mafioso or VIP catalogue. Completing all four VIP orders is not newly required for Tramduro. The actual endgame mission is outside this specification.

## 4. M01 — First blood at the wagon

**Trigger:** new world with no tutorial sale committed. Resume an existing tutorial rather than creating another copy.

**Giver / dialogue beats:** the blood-purchase sign supplies C01's number. C01 explains that he buys blood, normally packaged, makes one introductory $10 purchase, and points towards the pharmacy after payment. Do not introduce organ trade or grandpa in the tutorial-syringe payout itself.

**NPCs / identity / schedule:** C01 is the existing blood buyer, available 24/7. Proposed: a nearby adult Forest tutorial candidate with a stable PersonId can be made eligible using the existing free interaction/capture states; paid anaesthetic/ties must not be mandatory before the first income. The candidate is not an immortal training dummy. NPC authoring must provide recovery if unavailable, without spawning a living duplicate.

**Map points:** wagon spawn, adjacent sign, guaranteed initial unused blood syringe, reachable tutorial search area and C01's safe external wagon arrival anchor. Proposed: keep the candidate close enough for the unsealed-blood freshness allowance; verify the real route, not aerial distance.

**Steps:**

1. Notice/read the sign and find the physical empty blood syringe. Do not auto-fill pockets.
2. Call C01; retain his normal one-game-hour arrival and three-hour wait.
3. Wait for him before collecting unsealed blood if otherwise the freshness allowance would be exceeded. The journal explains that order of actions.
4. Use the existing stylised procedure on an eligible NPC; bind the syringe at successful use and increment that NPC's blood count once.
5. Present the fresh portion; choose return-empty or leave-syringe; confirm the sale.

**Success / reward:** one committed tutorial sale. Economy pays $10, 5 blood XP plus the one-time +50 per present participant and applicable blood respect. No mission-completion cash/XP is added. Returning the syringe preserves its binding, not a clean replacement. Pharmacy purchases and repeat trade become available.

**Failure / restore:** spoiled portion is not paid; wrong/struggling target rejects before consuming supplies. Death/arrest loses carried syringes per economy; normal disconnect retains them. The existing guaranteed daily blood-syringe find and recovery hint remain available. No credit/free replacement vial. A missed buyer visit follows normal meeting consequences and can be rebooked. The first $10 flag is not consumed by a failed attempt.

**Phone:** C01 contact after reading the number; appointment timing; short "collect after the buyer arrives" guidance; tutorial receipt and pharmacy destination after payment. Before the sign is discovered, no unexplained organ-buyer contacts.

**Co-op:** one team sign/contact/tutorial payout; any eligible participant can perform the steps. Global §2.3 applies. One player's pre-bound syringe cannot be reset by handing it to another.

## 5. M02 — Pharmacy, repeat income and the grandpa lead

**Trigger:** M01 paid. This mission teaches packaged trade; the world remains open and free syringe recovery remains legal.

**Giver / dialogue beats:** C01 describes walking to the Hamlet pharmacy, buying bags for $5, and selling filled sealed bags for $50 before normal bargaining. After the first bag sale: "Walking limits this business; an old man near Hamlet has a van." He gives the location without waiting for the team to hold $400.

**NPCs / schedule:** C01 24/7. Proposed: pharmacy trade access is 24/7 through the existing shop interaction; no unique pharmacist character or new voiced conversation is required. Map authoring must actually supply the shop, rather than assuming the old district drawing already contains one.

**Map points:** a walkable existing Hamlet pharmacy/service anchor, wagon/C01 arrival anchor, ordinary permitted Forest candidates. Do not make the pharmacy require the van, a bought base or anaesthetic stock.

**Steps:** buy at least one bag after M01, collect a valid portion with a suitable syringe, package it, call/meet C01 and confirm a bag sale. The second portion of the tutorial NPC is eligible if that person is still alive and state permits; a third portion still has its existing lethal game outcome. There is no mission requirement to take three portions.

**Success / reward:** the first paid sealed-bag sale sets FirstBagSale and sends the grandpa lead exactly once. The bag's $50 and ordinary sale XP/respect come from economy. Do not repeat the first-blood +50. Money may already have been spent on supplies; holding $400 is not the lead trigger.

**Failure / restore:** buying, filling or dropping a bag is not a paid sale. Lost goods can be replaced from normal shops; if funds are exhausted use the existing syringe path. Invalid goods stay with the team. A newer restored save that already has an authoritative FirstBagSale should issue a missing informational lead once without paying again. Unknown historical sales must not be inferred from a dummy bank figure.

**Phone:** pharmacy pointer, live C01 meeting, receipt, then GrandpaLead and location. Proposed: only suggest further saving for the peaceful $400 option; do not make a numeric savings task compulsory for the alternative branch.

**Co-op:** any participant's valid bag sale triggers the team lead; simultaneous bag sales produce one story message. Global §2.3 applies.

## 6. M03 — Grandpa's van, hut and shed

**Trigger:** GrandpaLead, or legitimate early discovery. Existing physical ownership/payment facts are reconciled even if the player reached him before the formal lead.

**Giver / dialogue beats:** grandpa is weak and gravely ill, with no invented diagnosis. He wants $400 for the van to leave money for his funeral. Paying leaves him alive; the established alternative permits taking the van after his death. The peaceful branch includes permission to use the hut/shed. No compulsory funeral cinematic, immortality, new organ bounty or mandatory "kill for profit" objective is added.

**NPCs / schedule:** one authored grandpa at his existing Hamlet yard/home. Proposed: the initial conversation remains available 24/7 through a reachable yard/door anchor; no daily timetable can permanently block the main acquisition. Ordinary illness/death presentation must not force a countdown race. His later fate is separate content.

**Map points:** existing grandpa yard, hut, operation shed, van and repair-part locations, not a second newly invented house. The shared base volume must include usable unloading/parking access.

**Steps:** reach the yard; learn terms if grandpa is alive; either confirm the $400 shared-fund purchase or claim the van after the actual death state under the canon branch. Ownership commit grants the van and base-2 premises once. Then show the repair task.

**Success / reward:** van ownership and hut/shed access, including the inherited old table and found rusty knife; no lamp, straps, fridge or free consumables. Payment is an ordinary full-price shared-fund transaction. No extra mission XP/cash. The peaceful achievement is an inherited hook, not a cash reward; final achievement ID is an integration dependency.

**Failure / restore:** insufficient funds does not take partial payment or lock the branch. A hit, knockdown, client statement or unseen dialogue is not proof of death/payment. If paid and grandpa later dies, do not revoke ownership or pay a refund. If he was already dead before the lead, the claim route and repair note remain available. Do not reset/move the player's van to replay the introduction.

**Phone:** location/terms, shared ownership and "repair required"; distinguish the $400 van payment from free-with-van premises. The game may explain alternatives narratively without instructing a compulsory killing step.

**Co-op:** any participant may pay per the economy's no-vote rule. Competing pay/claim actions resolve to one ownership result, never a $400 double debit. Global §2.3 applies.

## 7. M04 — Intro repair and C01's organ referral

**Trigger:** owned van with incomplete intro repair. If repair is already valid, reconcile it immediately.

**Giver / dialogue beats:** living grandpa identifies the battery/tyres in his yard. Proposed: the same short written repair note beside the parts provides equivalent information if he is unavailable/dead; the note is the chosen solution to the canon's open dead-grandpa guidance, not a new paid quest giver. After repair, C01 mentions a contact on Stroyka who buys organs.

**NPCs / schedule:** grandpa if available; C01 for the referral. No mechanic summons is required for this repair. The mechanic's later workshop task must not be a prerequisite to make the van drive.

**Map points:** yard parts and authored van sockets. Proposed first preset: one battery and two marked tyre-replacement sockets, with matching recoverable parts already in the yard. Socket count/meshes must be authored coherently on the real van; not assumed present from a checklist.

**Steps:** find the supplied parts; physically bring each to its intended socket; use a short existing-style hold interaction to install; persist each installed socket; commit IntroRepairComplete once. This is a cartoon interaction brief, not a real repair procedure. No new tool purchase or multi-stage mechanic minigame.

**Success / reward:** the van becomes normally usable on economy driving tier 0; no free upgrades. C01's referral unlocks after VanOwned AND IntroRepairComplete. If he cannot be answered, the actionable address/contact persists in his thread under PHONE recovery. No first-blood-only organ unlock survives from old drafts.

**Failure / restore:** a dropped part remains a physical part. Proposed: an explicit "recover missing repair part" interaction at the yard returns an inaccessible uninstalled part to its original anchor and invalidates its previous instance; it never replaces an installed part or duplicates another player's held part. No charge; these parts were already free. Avoid an infinite duplicate-part sale: repair parts are not merchandise. Reload retains completed sockets, not a fresh full kit.

**Phone:** compact repair checklist, reason if a socket is incomplete, and C01's construction-site referral after completion. Driving before repair may use existing introductory stalling; permanent random breakdowns are not introduced.

**Co-op:** players can install different parts; two attempts at one socket consume one part. A held part belonging to an absent client is labelled accordingly rather than cloned. Global §2.3 applies.

## 8. M05 — First organ buyer, property overview and mechanic referral

**Trigger:** organ contact unlocked by C01 after M04. Early arrival at the office can show a closed informational state, but cannot bypass that unlock.

**Giver / dialogue beats:** the first buyer acknowledges C01's referral, explains ordinary kidney/liver sales, actual quality, cold transport and bargaining, and points to the base-2 working shed. He then describes purchasable premises and mentions the nearby mechanic. Proposed portrayal inherits the economy's ritual-business dealer default; an office on Stroyka does not automatically make him the old canonical foreman.

**NPCs / schedule:** the single first organ buyer, office available 24/7 when he is there. If already called to a team base, show his actual appointment/status rather than a second office copy. C01 does not become an organ trader.

**Map points:** existing office/desk on Stroyka between Hamlet and Rough, team-owned base arrival anchors, and the nearby workshop referral anchor. Exact coordinates require real-map placement. Remove the obsolete Forest/Hamlet/Rough outing rotation for this buyer; his office and visits to owned bases are the two modes.

**Steps:** visit/meet the unlocked buyer; complete or skip the brief acquaintance; expose ordinary organ trade and the shared property catalogue; play the economy's skippable three-property overview; leave the mechanic direction in the thread. A first organ sale is not required just to see prices or learn the mechanic address.

**Success / reward:** narrative kidneys/liver stage, base catalogue and mechanic referral, all once. No free saw, fridge, acquired property or money. Rough $8,100, Downtown $33,750 and laboratory $135,000 remain economy-owned prices; all purchasable immediately with enough shared funds. The existing base-2 table/knife remain available.

**Failure / restore:** interrupting/skipping a presentation does not erase the referral or buy anything. A driver uses the agreed safe picture-in-picture. An office-to-base move preserves commercial attempts and leaves goods physically where they were. Other party members do not get a second buyer actor or mandatory repeated introduction.

**Phone:** known buyer contact, office/base-call choices, factual trade receipt, property listings and workshop location. Unknown medic/mafioso contacts remain absent until their unlocks.

**Co-op:** one world acquaintance/property-show flag; independent personal reading. Any participant can proceed with the mechanic or trade branch. Global §2.3 applies.

## 9. M06 — The mechanic's rival

**Trigger:** owned van; mechanic approached after the M05 referral or discovered independently. Proposed: the mechanic can be met earlier, but the delivery offer starts only after van acquisition. The referral is guidance, not a second mandatory conversation gate.

**Giver / dialogue beats:** the mechanic explains that his rival took his repair spot; bring that rival alive and tied, and he will open his workshop service. He identifies the occupied canopy and the rival's 08:00–18:00 work schedule. There is no organ request, body sale price or demand to kill him.

**NPCs / schedule:** mechanic at the workshop, proposed interaction access 24/7. The rival is one authored adult PersonId at the occupied Stroyka canopy, **08:00–18:00 confirmed**. Proposed: outside the shift he follows a nearby non-work authored anchor and is not required to be exposed as an exact live map marker. His active capture/sleep/death state overrides the routine: the clock cannot teleport a tied rival out of the van or duplicate him at work.

**Map points:** mechanic/workshop interaction, occupied rival canopy and safe workshop hand-in volume, all on Stroyka. The rival canopy and the mechanic's receiving zone are distinct usable spaces; verify a short drivable route, turning/unloading clearance and witness sight lines without inventing new police rules.

**Steps:** accept; find the actual rival; use ordinary capture; bind hands and feet (Proposed explicit hand-in interpretation, two normal ties); transport using the existing van; unload into the workshop receiving zone; physically interact to confirm. The server checks PersonId, alive state, both ties, location and absence of conflicting movement ownership at the final hand-in.

**Success / reward:** WorkshopUnlocked once, authoritatively resolving the rival handover. All driving tiers and cargo upgrades become purchasable for their economy prices. No cash bounty, extra XP, free repair upgrade or second van. Proposed: a brief acknowledgement then off-screen authored custody removes the rival from ordinary capture circulation without a new execution/operation scene; save the resolved identity before presentation.

**Failure / restore:** wrong NPC, dead target or missing ties rejects with a reason and keeps the target in the world. A rival who escapes remains that same target. If the rival dies or is irretrievably lost before successful hand-in, the economy's recovery contract permits an authored replacement next game morning; Proposed schedule convention: eligible from 06:00 and available at the next 08:00 shift. A live captured/held original is not replaced. Update the quest's authoritative target generation and phone hint once; do not retarget on every call. If he was captured before acceptance, the valid original qualifies.

**Phone:** workshop address, rival description/photo reference, canopy search area, working hours, hand-in checklist and any restoration reason. Proposed ordinary quest area guidance does not activate the special-order biometric scanner outside its already approved eligibility.

**Co-op:** any teammate may transport/confirm; tying/carrying retains CAPTURE ownership rules. Two hand-ins grant one unlock. A client leaving while physically holding the NPC drops/relinquishes him through the existing capture rule, not a new stored body copy. Global §2.3 applies.

## 10. M07 — Establish the first buyer relationship

**Trigger:** first organ buyer unlocked; starts counting ordinary successful meetings immediately, including qualifying sales before the journal card was read.

**Giver / dialogue beats:** the buyer asks for normal business first, explains why damaged goods pay less and offers the special job once the team has an established record. Proposed: communicate progress naturally at 1/3 and 2/3 through short thread updates, not three repeated introduction scenes.

**NPCs / schedule / map:** the same first buyer at his office or a chosen owned base, 24/7. His immediate base arrival/four-hour wait, office presence and one-NPC rule come from economy. Base-2 auto-crate sales from the old prototype are not retroactively certified as real buyer meetings without an explicit migration record.

**Steps:** complete three ordinary meetings with at least one successfully paid organ in each, then genuinely end each meeting. Kidney/liver goods, cooler use and purchases remain player choices. Different organ groups or repeated confirmation in one encounter count only once; blood, special orders, empty visits and failures do not count.

**Success / reward:** three-meeting fact, not a separate monetary reward. The bodybuilder proposal becomes available when that condition and the buyer's respect threshold permit it. The team need not own Rough or unlock the mechanic first. Actual sale money/XP/respect are paid by their transactions only.

**Failure / restore:** low respect blocks accepting the new special order, not ordinary trade. Show the reason and let normal successful trading repair the relationship. Interrupted office-to-base movement continues the same commercial context, not a free extra meeting. Preserve counters and qualifying meeting IDs across saves/disconnects.

**Phone:** compact "ordinary meetings 0–3" progress, buyer relationship tier and special-order eligibility. Do not hide the remaining respect condition behind a silent quest failure.

**Co-op:** the counter is shared, regardless of which player negotiated or stood at the encounter. Offline participants receive current state on return, not missing income multiplied by party size. Global §2.3 applies.

## 11. M08 — The Hamlet bodybuilder's kidney

**Trigger:** three ordinary first-buyer meetings, respect at least 40, and no other accepted active special order. It remains the first authored special order; the later streamer is not substituted.

**Giver / dialogue beats:** the first buyer wants a kidney specifically from the Hamlet bodybuilder; explain the photograph, morning pull-up location, Good-or-better condition, individual packaging, delivery stash and 48-game-hour deadline. Discuss/accept uses existing special-order bargaining before the timer starts.

**NPCs / schedule:** one designated HAMLET_BODYBUILDER at the Hamlet square pull-up bar, **06:00–10:00**, with existing adult strong-target capture characteristics. Off-hours activity is Proposed NPC authoring; it cannot erase his captured/transported state. This document adds no new strength minigame.

**Map points:** square pull-up/search area and approaches, base-2 table/workspace, first buyer's construction-material stash on Stroyka. Search area does not follow the NPC. The delivery stash has the inherited photo, landmarks and exact map destination.

**Steps:** accept with negotiated terms; identify/capture the right person using existing mechanics; obtain one qualifying kidney through the stylised operation; individually package it; physically load the order stash; review eligibility and explicitly confirm hand-in. A qualifying kidney collected before acceptance is valid if source identity is proven. Do not require re-capture just to tick an empty objective.

**Success / reward:** economy special-order organ price, timely +25% if applicable, negotiated percentage, cooling modifier and inherited XP/respect. No second story bounty. One successful hand-in closes the story milestone and makes M09 available. A valid late hand-in also satisfies this story milestone; it keeps only the reduced economic reward, not an eternal medic lock.

**Failure / restore:** deadline expiry applies the existing single −4 and removes the timely premium, but delivery/cancellation remain possible. Wrong donor/type, low grade, missing packaging and ruined goods do not get consumed or paid. Incorrect confirmed hand-in penalties are once per item/order, not per click. Declining the unaccepted proposal costs −1 and it returns after one game day; accepting then cancelling uses the different inherited rule. Do not impose both penalties for one action.

If the original bodybuilder was already dead before the order, inherit SALES' next-morning "twin brother" replacement and acceptance of a previously preserved qualifying original kidney. The active order stores its allowed donor IDs; changing a label alone cannot forge provenance. Preserve the replacement generation across reload. A dead original with a usable stored kidney does not require destroying that kidney or harvesting a new one.

**Phone:** pinned accepted-order card, personal scanner access, remaining time, source/quality/packaging reasons, stash destination, and committed receipt. Scanner result is not broadcast as a live target marker. Two kidneys do not imply two order rewards: select/consume only the required unit; other goods remain.

**Co-op:** first player discussing owns offer bargaining; any interacting teammate can confirm the agreed delivery. Team special slot, donor facts and deadline are shared. Global §2.3 applies.

## 12. M09 — Sealed case to the medic

**Trigger:** first three ordinary meetings and successful bodybuilder hand-in are recorded. Offer persists without a response deadline; accepting it does not occupy the special-order slot.

**Giver / dialogue beats:** the first buyer entrusts a sealed case to a Downtown recipient; place it in a described metal service cabinet, then the contact will call. State the $1,000 reward and the replacement deduction before issuing cargo. No content-opening/organ-selling side objective is invented.

**NPCs / schedule:** first buyer in his existing office/base mode. The medic is initially a remote recipient: no second medic actor waiting visibly at the stash and no need for him to be physically present. Courier hand-in is available 24/7; the medic's ordinary trading remains 18:00–06:00 after contact unlock.

**Map points:** buyer's issue anchor and the already planned medic metal cabinet in a Downtown service yard. Courier acceptance exposes that destination before the contact is known. It must not accidentally expose the mafioso's five dead drops.

**Steps:** accept; receive the one physical sealed CargoId; transport it; deposit into the designated cabinet; confirm delivery. Proposed: a small one-hand carry case using the normal item/container framework, no extra handling minigame. The final package cannot be opened for free contents or sold as ordinary merchandise.

**Success / reward:** one atomic cargo consumption, M09 completion, medic-contact unlock and payment `max(0, 1000 - 200 × replacements)`. No additional mission XP; no +25%, bargaining, organ commission or quality multiplier on that mission reward. Unlock the narrative eyes/brain stage, still requiring the right physical tools and implemented procedures. Trigger one medic introduction call, with the usual unanswered-call/thread fallback.

**Failure / restore:** no hard deadline, blood-like spoilage or automatic rejection for taking a detour. A lost/inaccessible case can be explicitly replaced by the buyer. Show the old/current holder and resulting reward first; replacement changes the active CargoId once and invalidates the previous case for hand-in. The current team fund is never debited and the mission never creates debt. At five or more replacements the cash reward is zero, but delivery still opens the medic. Existing duplicate/old cases cannot deliver twice.

If a client leaves with the case, retain it in that client's inventory and identify that in the journal. The team can wait or deliberately request the authorised replacement/deduction; do not duplicate the old valid generation silently. An interrupted successful hand-in restores its committed result, not another active paid case.

**Phone:** destination/photo, current case/holder, replacement count, resulting reward and clear "no delivery deadline". Until the commit, the unknown medic is not exposed as an ordinary available buyer. Afterwards the contact thread contains the introduction even if nobody answered the call.

**Co-op:** different teammates may accept, carry, replace and hand in using validated ownership. Only one cargo generation, payment and contact unlock exist. Global §2.3 applies.

## 13. M10 — Seven ordinary meetings with the medic

**Trigger:** medic unlocked by M09, not by the bodybuilder reward alone. A first introduction message can be received during daytime; actual trade obeys the night window.

**Giver / dialogue beats:** the medic acknowledges the courier and explains his higher-quality market. He buys all already story-unlocked categories at Acceptable or better, not just heart/lungs from the old surgeon draft. Proposed: short milestone acknowledgement after the first and fourth qualifying meetings; avoid repeated cinematic interruptions.

**NPCs / schedule:** the existing medic and black sedan, ordinary booking **18:00–06:00**, immediate arrival, waiting until the earlier of booking+four game hours and next 06:00. One actor and appointment per buyer. His three authored locations retain the existing no-repeat rotation.

**Map points:** two Downtown points (service yard and quiet alley) and a Stroyka-exit pocket; goods go into the neat case at the sedan. Authoritative appointed point remains fixed for the visit. These locations are not replaced by the first buyer's new base-call policy.

**Steps:** sell eligible ordinary merchandise in seven genuinely completed meetings. Existing early organs can count: the player does not have to own a saw, perform seven brain operations or complete the optional streamer order to unlock the mafioso. Each meeting must have at least one paid organ; all groups of that meeting together count once.

**Success / reward:** sale payouts/XP/respect only. On the seventh qualifying meeting's completion, queue the mafioso's one-time introductory call. It need not wait until next night or require a new base purchase. A call missed while driving/in an operation follows PHONE without losing the unlock.

**Failure / restore:** quality below Acceptable is rejected on ordinary loading without a new story fine; normal trade cancellation/bargaining consequences still apply. Preserve 0–7 progress. An older message naming a different threshold cannot reduce it, and a reload cannot count the seventh encounter twice.

**Phone:** night availability, actual meeting point/times, progress 0–7 and ordinary receipts. Before the seventh completion, no free mafioso contact just because a player bought the laboratory.

**Co-op:** shared meeting counter and present-player sale XP follow their existing contracts; the caller is not required to have personally conducted all seven meetings. Global §2.3 applies.

## 14. M11 — The mafioso's first dead drop

**Trigger:** seventh ordinary medic meeting completed. The mafioso initiates contact; his call can fall back to a persistent introduction message, never a permanently lost number.

**Giver / dialogue beats:** an eccentric mafioso introduces a higher-paying discreet channel, minimum Good quality, a marked drop location and phone bargaining after physical loading. He is not another medical specialist and does not promise personal collection at a base.

**NPCs / schedule:** remote mafioso contact available 24/7. No physical buyer actor/car is required at an ordinary dead drop. Existing NPC/police/witness behaviour still applies around deliveries; no newly generated betrayal or ambush.

**Map points:** five prepared hidden containers/niches from the economy contract. One active point is available immediately on contact unlock. Subsequent change at **06:00 game time**, no repeats until the authored list is cycled; saturation resets separately at 00:00. Exact five coordinates and clearance are map-authoring dependencies, not invented approved places.

**Steps:** read the appointment-free drop instruction; physically deliver eligible goods; open the thread's live cargo card; bargain per kind; confirm the current quote. No call can remotely sell an organ still in the van or absent player's pockets.

**Success / reward:** ordinary mafioso sale at ×2.2 with quality/cold/saturation/bargaining, paid once to the shared fund. Contact unlock enables the narrative heart/paired-lung stage; actual extraction still depends on tools and the approved operation content. The first committed ordinary deal, once closed, satisfies the economic-deal part of VIP availability; owned laboratory and respect/free slot remain separate conditions.

**Failure / restore:** old point cargo remains for collection after the 06:00 switch. A persistent "Collect remaining items" map entry stays until cleared; no teleport, deletion or unrequested sale. Old pending quotes invalidate at the generation boundary, without a new no-show fine. Actual goods must be moved to the active point to continue; preserve the ongoing deal's agreed percentage/attempts as economy requires. Already committed sales survive rollover.

Wrong quality or ownership is explained before commitment. The stash is not refrigerated; the delivery pipeline must preserve actual cold-transport provenance without freezing cargo forever. Save active point, queue, generation, return sections, pending negotiation and deal counters.

**Phone:** current point/photo/directions, 06:00 change time, actual loaded items, chances/quote, immediate receipt and separate return-only map entries. No fabricated waiting-car timer.

**Co-op:** any teammate physically loads valid owned goods; first bargaining participant owns the deal role, with ordinary handoff/recovery. A point switch and two simultaneous confirmations resolve on the host against one generation. Global §2.3 applies.

## 15. M12 — Optional later OLD_STREAMER order

**Trigger:** medic open, team owns the required saw, city story access is active and the shared special slot/respect allow acceptance. Economy defines city story access as the medic stage, not a physical barrier around Downtown.

**Giver / dialogue beats:** medic requests the brain of the specific OLD_STREAMER, Perfect/80% or better, packaged; photograph, whereabouts, schedule and search area must be authored for this actual NPC. Do not reuse the bodybuilder's morning photograph or call VIP_SPEEDSTER the same target.

**NPCs / schedule:** OLD_STREAMER is an independent authored adult target. The older source leaves hours/place open. Proposed first-pass resolution: **16:00–22:00**, a short pedestrian routine at the edge of the existing Downtown square and its public frontage, with one visible ordinary activity rather than a unique streaming simulation. The clue describes that fixed search area and the 16:00–22:00 window. These are new proposed staging values, not recovered canon. Actual coordinates, route clearance and the individual photograph still need authoring before publication.

**Map / steps:** target search area and medic's special-order cabinet; accept/identify/obtain the right brain with existing stylised procedure/package/physically deliver/confirm, as M08 but with its own target and threshold.

**Success / reward:** economy's organ special-order calculation, timely XP/respect and +25%; no VIP $10,000/$15,000 premium and no second buyer unlock. This order does not occupy a separate second active-special slot.

**Failure / restore:** ordinary special-order deadlines/refusal/cancellation/wrong item rules. Missing clue/target authoring means the offer is not published as an actionable broken quest. Proposed: use the same recoverable-target-generation contract as the economy's unique targets, without changing a currently accepted donor ID silently.

**Phone / co-op:** its own pinned card, accepted-order scanner and delivery receipt; donor state and deadline shared, scan result personal. Global §2.3 applies.

## 16. M13A–D — Four unique VIP orders

**Trigger:** mafioso known, at least one completed ordinary mafioso deal, and team owns the laboratory. Four offers become visible; acceptance additionally requires mafioso respect ≥40 and a free shared special-order slot. The offers wait without ignored-offer penalties.

**Giver / dialogue beats:** the mafioso presents four distinct specific-target requests and their requirements, timely premiums and single-completion nature. Proposed: one introductory catalogue message with four cards, not four forced ringing calls. Players choose the order; the story does not secretly require all four before Tramduro.

**NPCs / identity / schedule:** existing adult VIP model baseline and canon §152 remain the source of character/encounter direction. BAD_ALTGIRL stays VIP-only, excluded from ordinary Rough crowds. Each accepted order records one actual target identity/allowed generation; owning a same-type ordinary organ is insufficient.

| Mission | Target baseline | Required item / minimum | Timely fixed premium from economy |
|---|---|---|---:|
| M13A | VIP_BEASTMAN | Heart, Perfect/80% | $15,000 |
| M13B | VIP_SPEEDSTER | Paired lungs, Good/60% | $10,000 |
| M13C | VIP_BLINDFOLD | Paired eyes, Perfect/80% | $15,000 |
| M13D | BAD_ALTGIRL | Brain, Good/60% | $10,000 |

Proposed first-pass availability windows and activity anchors, all within the existing Elite Hill setting:

| Target | Window | Activity / search setting |
|---|---|---|
| VIP_BEASTMAN | 10:00–18:00 | Existing pool/garden leisure area; shared idle/walk vocabulary |
| VIP_SPEEDSTER | 12:00–20:00 | Existing villa approach/courtyard; approved fan-oriented encounter hook remains separate |
| VIP_BLINDFOLD | 20:00–02:00 | Existing quieter terrace/path; character-specific protection follows the NPC contract, not a new health multiplier |
| BAD_ALTGIRL | 14:00–22:00 | Existing villa entrance/patio; camera-oriented approach follows the canon direction |

These rows do not assign one new villa/building to each target, require new animations or claim such actors already exist in the scene. Off-duty anchors are authored inside existing usable spaces. Their routines cannot override capture, death, transport or accepted-target identity. An existing appearance blindfold does not by itself invent a new scanner immunity; use the approved face-visibility predicate, with a readable eligible opportunity. World authoring must supply a reachable window for the accepted order within its 48-hour span.

**Map points:** existing late Elite Hill VIP setting/authoring, the team's chosen equipped base for the operation, and a valid mafioso special-order hand-in. Proposed: pin the active dead-drop location at order acceptance as that order's persistent hand-in point. It remains a special-order interaction for the accepted order after ordinary daily trading moves elsewhere. Reuse the container's separate order/ordinary/return sections; ordinary sales are still forbidden at yesterday's inactive point. This fills an unassigned order-destination detail without undoing daily rotation.

**Steps:** select/accept one offer after bargaining; inspect its actual clue/requirements/deadline; use an approved existing capture approach; obtain the specified organ, individually package and preserve it; physically deliver to the pinned order destination; confirm. Earlier harvested eligible organs are valid. Existing costume/camera/ability-oriented character ideas are advantages/directions, not newly mandatory purchase gates or guaranteed instant-loading cinematics.

**Success / reward:** organ price under mafioso special-order rules plus the fixed timely premium in the table. Premium is not multiplied by bargaining, quality, +25%, staff commission or player count. Timely sale also receives the inherited special-order XP/respect. Each mission sets its world completion flag once. All four timely premiums total $50,000; laboratory acquisition precedes their availability, so these rewards cannot fund its initial purchase.

**Failure / restore:** 48 game hours from negotiated acceptance. Late hand-in removes the fixed premium and +25% but retains the agreed bargaining percentage and still completes that unique order; it cannot then be repeated for a timely premium. Failure/refusal alone does not set completed. No wrong item is silently consumed.

Economy requires recoverable access to unfinished unique targets: if the target is permanently lost and no suitable item remains, an authored replacement can become available no earlier than next game morning. NPC authoring supplies a new identity, no simultaneous living duplicate. A currently accepted order never silently changes its required donor; resolve its original delivery/expiry/cancellation and bind a current valid target on a subsequent acceptance. Do not force a target to have the minimum quality by overwriting a failed extraction or paid outcome. Required quality must instead be attainable under the authored target/operation contract before publication.

**Phone:** four waiting cards, locked reasons, target clue, minimum quality/packaging, accepted negotiated price, fixed timely premium separately, 48-hour deadline and the persistent order destination. A card's missing photograph/individuality is a content blocker, not an excuse for an arbitrary current crowd target. Returning ordinary stock and accepted-order stock must be clearly separate.

**Co-op:** one active team special order across M08/M12/M13, even if players stand at different buyers. Any qualified physical hand-in can finish it once; personal scans remain personal. Global §2.3 applies.

## 17. Mission data, persistence and content dependencies

### 17.1. Minimal facts to persist

Reuse the existing host-world save and identity/transaction contracts. The following are required behaviours/data, not a proposed second save service:

| Group | Persistent facts |
|---|---|
| Tutorial and leads | Sign/contact discovery, committed tutorial sale, committed first bag sale, grandpa/organ/mechanic referrals, acknowledgement flags |
| Van and premises | Payment-or-claim result, ownership, base-2 access, battery/tyre socket installation, active uninstalled part identities, intro repair complete |
| Buyer progression | First-buyer acquaintance/property overview, completed ordinary meeting IDs, counters 3/7, medic/mafioso contact and organ-stage flags |
| Unique targets | PersonIds/allowed donor sets, active replacement generations, captured/alive/resolved state, authored schedule progress through existing NPC persistence |
| Mechanic | Offered/accepted state, exact rival generation, handover result and WorkshopUnlocked |
| Special orders | Accepted order, buyer, terms, deadline, item requirements, pinned hand-in destination, penalty/completion flags, shared active slot |
| Courier | Offered/accepted/completed, active CargoId, replacement count, previous invalid generations, reward result and medic-call delivery state |
| Mafia/VIP | Active ordinary drop/queue/generation, return-only cargo, ordinary deal count, owned laboratory, four VIP completed flags and their paid transaction IDs |
| Presentation | Seen/skipped introductions, current journal cards, retained messages/receipts; not an obligation to replay a half-watched cinematic |

Don't reconstruct committed missions from visible history alone: PHONE can trim old messages. A tutorial flag isn't inferred from a random syringe currently held. A same-type new NPC isn't inferred to be the old donor. A loaded item cannot be in both an absent player's inventory and a live stash.

Proposed journal reconciliation order on load: restore economic commits and item/target identities; restore world time and active obligations; resolve valid prerequisite facts; derive current objective cards; queue only never-delivered informational messages. Do not retroactively replay expired ringing calls or pay old rewards. This is an ordering contract, not code implemented here.

### 17.2. Logical map anchors

The aliases below name authoring requirements only. Bind them to existing approved data/anchors; they are not invented already-imported GameObjects, GUIDs or a mandate to rename existing IDs.

| Alias | Needed physical place |
|---|---|
| WagonSign / WagonSyringeFind / WagonTutorialArea | Discoverable sign, guaranteed unused blood-syringe find and nearby eligible adult target area |
| BloodBuyerBaseAnchor(baseId) | Safe external arrival spot for each owned base, including the wagon |
| HamletPharmacy | Walkable early shop with normal bag/syringe trade access |
| GrandpaYard / IntroRepairSockets | Existing yard, van, battery/two proposed tyre parts and matching valid installation positions |
| FirstBuyerOffice | Reachable Stroyka desk; no duplicate buyer actor |
| Workshop / RivalCanopy / RivalHandIn | Mechanic interaction, separate occupied canopy 08–18, receiving zone with unloading access |
| HamletPullupArea | Existing square pull-up/search area with bodybuilder 06–10 |
| FirstBuyerOrderStash | Construction-material crate for the bodybuilder order, not an automatic sale box |
| MedicMeeting01–03 | Two Downtown meeting areas and the Stroyka-exit pocket, with car/inspection clearance |
| MedicCabinet | Downtown service cabinet with separate courier/order contexts and valid physical return handling |
| MafiosoDrop01–05 | Five map-authored hidden drop containers; active ordinary, order-specific and return sections cannot share/duplicate ItemIds |
| StreamerSearch / VIPSearch(type) | Authored fixed clue areas, usable activity anchors, entry/exit paths and valid living identity for the proposed windows |

No change to map terrain/buildings is authorised by this document. The pharmacy/canopy/parking must be checked against the real approved layout before implementing markers. A pin pointing at a wall or an inaccessible container is a failed dependency, not a completed mission.

### 17.3. Per-mission dependency matrix

| Mission | Systems required | NPC/content required | Map anchors required |
|---|---|---|---|
| M01 | Phone call/meeting, blood procedure, syringe binding, one-time sale/XP, recovery find | C01; eligible adult tutorial candidate; sign and short hints | Wagon group; blood-buyer arrival |
| M02 | Pharmacy purchases, blood bag packing, ordinary C01 sale, first-bag fact | Shop interaction; grandpa-lead text | HamletPharmacy; wagon arrival; ordinary Forest activities |
| M03 | Valid payment/claim transaction, van/base ownership, ordinary NPC lifecycle | Grandpa, alive/dead dialogue branches, optional achievement hook | GrandpaYard, hut/shed/van |
| M04 | Physical parts, socket progress, valid repair event, call/message recovery | Grandpa hint and proposed written fallback | IntroRepairSockets; part anchors |
| M05 | Contact unlock, office/base trade, property catalogue, skippable driver-safe overview | First buyer, introductory beats, mechanic direction | FirstBuyerOffice; owned-base arrivals; existing property views |
| M06 | Capture/ties/carry/van delivery, exact target validation, restoration generation, workshop unlock | Mechanic/rival, shift routine, handover presentation | Workshop; RivalCanopy; RivalHandIn |
| M07 | Authoritative ordinary meeting completion and respect eligibility | Buyer progress acknowledgements | Existing buyer modes, no new locations |
| M08 | One special slot, bargaining/deadline, donor items, operation/packing/cold, scanner, stash commit | Bodybuilder/photo/twin recovery | HamletPullupArea; base workspace; FirstBuyerOrderStash |
| M09 | Persistent sealed case, ownership, replacement deduction, hand-in transaction, medic unlock | Cargo prop, buyer/medic messages, cabinet photo | Buyer issue point; MedicCabinet |
| M10 | Night appointment rotation, minimum quality, ordinary meeting counter | Medic/sedan, seven-meeting progression beats | MedicMeeting01–03 |
| M11 | Daily dead drops, phone bargaining, return sections, ordinary sale/identity save | Mafioso contact/voice, five place descriptions | MafiosoDrop01–05 |
| M12 | Saw/organ-stage checks, specific brain output, active special-order rules | OLD_STREAMER/photo, proposed 16–22 routine | StreamerSearch; MedicCabinet |
| M13A–D | Laboratory ownership, ordinary mafioso fact, special slot, all required procedures, pinned order destinations, one-time premiums | Four existing VIP baselines, individual clues and approved encounter hooks | VIPSearch(type); chosen equipped base; pinned mafioso order section |

Important terminology: the **narrative second organ stage** (eyes/brain after medic) is not the same as the implementation package named OPERATIONS_STAGE2 (chest). Chest code/assets can be developed earlier, but story availability of heart/lungs follows the mafioso. Do not accidentally reverse the accepted buyer progression because of a package name.

## 18. Acceptance checks SM-01 onward

These are future implementation checks, not tests executed by writing this document. Verify rules, save restoration, real-map placement and host/client behaviour separately.

| ID | Expected result |
|---|---|
| SM-01 | A new world starts at the wagon without the van/free consumable kit; the initial valid blood syringe is a real find. |
| SM-02 | The sign makes C01 discoverable; an unknown organ buyer/medic is not prepopulated as an unlocked contact. |
| SM-03 | The tutorial route is achievable without first buying ties or anaesthetic, and without requiring blood to survive longer than its allowed freshness. |
| SM-04 | First unsealed sale pays $10 and the one-time blood bonus once; ordinary recovery syringe sales pay $8 without restarting M01. |
| SM-05 | Returning the syringe preserves its PersonId; another player cannot use it on a different NPC to bypass binding. |
| SM-06 | Pharmacy/bag access follows the introductory sale; the player is not required to own the van to reach it. |
| SM-07 | Grandpa's formal lead triggers on the first paid sealed-bag sale, not a bag purchase/fill, tutorial syringe, or $400 balance. |
| SM-08 | Two simultaneous first-bag sales produce one lead; receiving/reading it does not repeat first-blood XP. |
| SM-09 | Early legitimate grandpa/van discovery is recognised; no reset or repeated payment is required to satisfy a new card. |
| SM-10 | Peaceful acquisition charges exactly $400 once and leaves grandpa alive at that transaction; insufficient funds charges nothing. |
| SM-11 | The death/claim branch requires authoritative death/claim facts, not a hit or client assertion. Both branches grant the same hut/shed access. |
| SM-12 | Later grandpa death doesn't revoke a paid van or generate a refund; the written repair guidance remains available without him. |
| SM-13 | Battery/tyre parts are provided in the yard, installed sockets persist, and missing-part recovery cannot clone held/installed parts. |
| SM-14 | Repair completion plus ownership triggers C01's organ referral; the first blood sale alone does not. |
| SM-15 | Missed introduction calls retain actionable information through PHONE retry/thread recovery; nobody is permanently locked out by driving. |
| SM-16 | First-buyer acquaintance exposes all three paid properties and mechanic guidance, without granting furniture or charging a purchase. |
| SM-17 | Skipping/property presentation/late join do not repeat unlocks, block driving or teleport players. |
| SM-18 | First buyer has one actor between office and owned-base appointment; obsolete outing points aren't used. |
| SM-19 | Mechanic/rival branch is independent of ordinary meeting/bodybuilder/medic progression. |
| SM-20 | The rival is findable at the Stroyka canopy during 08–18; leaving that shift cannot teleport a captured rival. |
| SM-21 | Only the designated living rival, hands and feet tied in the valid hand-in zone, opens the workshop. Wrong/dead/untied targets remain unconsumed. |
| SM-22 | Two hand-in requests yield one unlock and no cash/organ reward. Losing the target has a recoverable next-shift path without living duplicates. |
| SM-23 | Three first-buyer ordinary meetings count by completed encounter, not organs/groups/buttons; blood and special deliveries don't count. |
| SM-24 | Low respect after the third meeting explains the block while ordinary trade remains available. |
| SM-25 | The first special order is HAMLET_BODYBUILDER kidney Good/60%+, not OLD_STREAMER or an arbitrary same-type NPC. |
| SM-26 | Bodybuilder search uses the fixed pull-up area and 06–10 window; no global live NPC tracker is added. |
| SM-27 | An accepted-order scan uses living visible face, 10 m/line of sight, 2.5 seconds and private result. |
| SM-28 | A proven pre-harvested eligible kidney is accepted; the player needn't repeat capture for checklist order. |
| SM-29 | Bodybuilder/twin donor eligibility is stable across loads; replacing a name does not forge an eligible organ. |
| SM-30 | Only one required kidney is consumed; other organs remain. Successful hand-in grants economy rewards once. |
| SM-31 | Late valid bodybuilder delivery removes timely rewards but still allows the courier step; refusal/expiry don't create a permanent medic deadlock. |
| SM-32 | Courier offer follows the bodybuilder completion and three-meeting condition, not the workshop or purchase of Rough. |
| SM-33 | The courier's Downtown cabinet is exposed before the medic contact; that does not unlock ordinary medic trade early. |
| SM-34 | Courier delivery has no deadline, spoilage or special-slot occupation; the sealed case isn't saleable organ stock. |
| SM-35 | Case replacements 0/1/5/6 yield $1,000/$800/$0/$0 at successful delivery and never debit current funds. |
| SM-36 | Old case generations and repeated delivery attempts can't pay/unlock twice; an absent holder is shown before replacement. |
| SM-37 | Successful case delivery opens medic/eyes-brain stage and queues one recoverable introduction, even with a zero reward. |
| SM-38 | Medic accepts all unlocked Acceptable+ organ types, books only 18–06, and keeps its three specified meeting settings. |
| SM-39 | The seventh genuinely completed ordinary medic meeting triggers the mafioso once; a saw, streamer order or seventh organ isn't substituted for seven meetings. |
| SM-40 | The mafioso's first drop is available immediately on contact unlock; ordinary trading doesn't spawn a personal buyer encounter. |
| SM-41 | Five authored drops share one daily active point; change occurs at 06:00, saturation reset separately at 00:00. |
| SM-42 | Old-drop unsold goods remain collectable with persistent map entry; they're not teleported, destroyed or automatically sold. |
| SM-43 | The optional OLD_STREAMER order has its own specific brain/80% clue, saw requirement and later-stage gates, not the bodybuilder's photo/schedule. |
| SM-44 | The optional streamer order isn't a gate to the mafioso/VIP catalogue and shares the one accepted-special-order slot. |
| SM-45 | VIP proposals require known mafioso, a completed ordinary deal and owned laboratory; buying laboratory early doesn't create the missing contacts. |
| SM-46 | All four VIP proposals wait without penalties; only one can be accepted, and no forced four-target completion chain is introduced. |
| SM-47 | The four target/item/quality/premium rows match economy exactly; BAD_ALTGIRL never enters ordinary Rough crowd spawning. |
| SM-48 | Proposed VIP windows are reachable within the 48-hour order; capture/death and exact identity override routine schedules. |
| SM-49 | A VIP order's pinned hand-in remains valid for that accepted order after daily ordinary-drop rotation, without allowing ordinary sales at an inactive old point. |
| SM-50 | A timely premium is paid once; late successful delivery pays no fixed premium and still sets completed. Neither can be repeated for a second premium. |
| SM-51 | Order replacements don't silently change the donor of an accepted contract or spawn a live duplicate; old valid organs retain provenance. |
| SM-52 | Two clients confirming the same cargo/order/payment resolve to one host transaction; a restored receipt is not another reward. |
| SM-53 | Client leave retains all inventory/case/cooler possessions; a physically carried NPC uses capture's drop rule, not inventory duplication. |
| SM-54 | Host leave ends the session; closed-world deadlines, schedules, supply finds and world decay do not advance with real offline time. |
| SM-55 | Late join restores current shared missions and personal reading without another kit, payment, compelled intro or reset meeting counter. |
| SM-56 | An early completed world fact satisfies a subsequently visible objective without bypassing its economic contact/acceptance prerequisites. |
| SM-57 | Journal/history trimming cannot erase committed tutorial, 3/7 counts, courier reward or one-time VIP flags. |
| SM-58 | All proposed receiving/search/parking anchors are checked in the actual map for access, unloading and valid interactions before claiming scene integration. |
| SM-59 | The narrative eyes/brain stage and chest implementation-package naming do not invert organ unlock order. |
| SM-60 | No extra mission cash/XP, mandatory base, new level gate or random buyer betrayal is added by story presentation. |

## 19. Questions left open

> **Fedya, 2026-10-28 — pharmacy:** the pharmacy will be in the city (not in Hamlet). Its exact place and its story role/objectives are NOT designed yet — deferred, we come back to it later. Until then M01–M02 steps that say "Hamlet pharmacy" are on hold; do not author a pharmacy anchor in Hamlet.

No additional human gameplay answer is required to finish this version. Fedya answered the two material staging choices and delegated the rest. Levels, the post-Tramduro ending and save-slot counts were explicitly deferred and are not answered here.

Production dependencies remain, not new interviews:

1. Bind the proposed logical anchors and schedules to real map coordinates/routes without changing other districts. In particular, confirm the Hamlet pharmacy, separate rival canopy/receiving zone and five mafioso drops exist and are accessible.
2. Author actual individual PersonIds, photographs and clues for the rival, streamer and VIPs; bind existing buyer IDs instead of silently renaming ORGANS_01/c02.*.
3. Supply only missing character/prop/voice resources and subtitle text; final names/jokes do not change the required mission conditions. Existing draft strings with obsolete rules need a future content revision, not edits by this task.
4. Verify the early blood route/eligible target and free repair parts in real play; a possible route in prose isn't proof of an achievable first payout or repaired van.
5. Bind proposed VIP activity windows/identity recovery to the NPC owner's encounter contract. Special approaches, guards and political endgame systems aren't implemented or redesigned here.
6. Implement the existing shared-item/fund/save/phone adapters and durable quest commits before scene acceptance. Respect current user work and project sequencing.

Proposed staging does not become Confirmed simply because a test passes. Real human pacing/fun approval and technical verification remain separate.

## 20. Sources, permitted output and verification

### 20.1. Read-only sources

Paths below are relative to this file in `C:/Dev/Game/docs/specs/`.

| Source | Use |
|---|---|
| [Economy](ECONOMY_SALES_PROGRESSION_SPEC_2026-10-25_v01.md), especially §§2,5,6.3,8,9,15 | Authoritative chain, money/rewards, base/workshop conditions, syringe recovery, counters and VIP rules |
| [Current canon](../VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md), especially §§29–30,51,97,152 | Blood prologue, grandpa branches/intro repair, retained character direction and scope limits |
| [Buyers v02](BUYERS_SPEC_2026-10-15_v02.md) | Respect, specific donors, quality, first/later special orders; later economy supersessions apply |
| [Sales gameplay](SALES_GAMEPLAY_SPEC_2026-10-18_v01.md), including Decisions | Physical sales, bodybuilder/twin, cancellation and buyer presentation |
| [Capture/delivery](CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md) | PersonId, capture, ties/carry, blood counts and physical NPC disconnect |
| [Phone](PHONE_SPEC_2026-10-18_v01.md), latest PH decisions | Calls/handoff, driver safety, shared threads, personal scans, 2.5-second identification and restoration |
| [Forest 27.10](FOREST_SPEC_2026-10-27_v01.md), including evening decisions | Wagon/Forest staging and existing intro direction; economy overrides old syringe restriction |
| [Buyer message draft](../drafts/BUYER_MESSAGES_DRAFT.md) | Reusable dialogue intents/keys only; obsolete prices/unlocks/refusals not adopted |
| [Capture message draft](../drafts/CAPTURE_MESSAGES_DRAFT.md) | Existing hint/reaction intents, not new capture mechanics or required literal English speech |
| [Operations](OPERATIONS_SPEC_2026-10-15_v01.md), [chest/cleanup](OPERATIONS_STAGE2_SPEC_2026-10-18_v01.md) | Physical procedure dependencies; no additional mission medical minigame |
| [Network](NETWORK_MAP_PLAN_v01.md), [work inventory](WORK_INVENTORY_SPEC_2026-10-18_v01.md), including Decisions | Shared world, GUID, host end, client possession retention and item identity |
| [AGENTS](../../AGENTS.md), [AgentRules](../AgentRules.md), [workflow](../TEAM_WORKFLOW.md) | Scope, read-only references and no commit/implementation constraints |

The economy document's inherited facts were already reviewed in this chat; source comparison was refreshed for this task. Runtime work outside this new file was visible in the working copy but not inspected, changed, accepted or claimed as this document's implementation. No Unity/Assets operation is part of this task.

### 20.2. Output boundary

Only the new `C:/Dev/Game/docs/specs/STORY_MISSIONS_SPEC_2026-10-28_v01.md` is written. The economy specification and all other references remain unchanged. No code, scenes, assets, project settings, WORK_SYNC, files under the Codex configuration tree, commits or publishing are part of this task. The previously posted G50 message saying no files had been created described that other chat's earlier state, not the output of this task.

### 20.3. Document checks

Final documentary verification covers numbered sections, table widths, existing local links, unique consecutive SM-01…SM-60, mission coverage, economic constants and the unchanged economy-file hash. This is not runtime testing.

| Check | Result | Evidence / limit |
|---|---|---|
| Structure | PASS | 20 sequential numbered sections, 13 mission sections covering M01–M13A–D, 10 rectangular Markdown tables including this report |
| Acceptance IDs | PASS | SM-01 through SM-60, each exactly once in the acceptance table |
| References | PASS | All 16 Markdown source links resolve to existing local files |
| Economy consistency | PASS for documentary scope | Checked $10/$8/$2 tutorial supplies, $400 van, 3/7 ordinary meetings, $1,000 less $200 per case replacement, thresholds and four $10,000/$15,000 VIP premiums against the read-only economy |
| Source preservation | PASS | Economy SHA-256 unchanged: BB303A9AE34B8E4F6CFED7BD480054F4E1DE13E756700ABDD29BE617F458E659 |
| Gameplay/integration | NOT RUN | No Unity, compilation, multiplayer, disk-failure, physical map validation or human playtests executed |

Method: read final UTF-8 text; inspect mission gates/recovery and source constants; run in-memory checks of heading sequence, table columns, acceptance IDs, existing paths and source hash; rerun structural checks after adding this report. No test/script files were created. PASS does not promote Proposed staging to Confirmed or assert implemented missions. The only authored output is this specification.
