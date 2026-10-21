# ONLY VOLUNTEERS — Police and Suspicion Specification

Version: v01 | Date: 2026-10-18  
Status: design specification from the project owner's interview; not an implementation report.  
Project: `C:\Users\chern_0eqkb03\Desktop\GAME`

## Краткое резюме

Основное давление создают локальные зоны настороженности NPC: красное ядро и более широкая жёлтая область, видимые только на карте. Две жёлтые зоны дают красную только на пересечении. Районный фон меняется слабее; полиция не имеет отдельной шкалы хита. После отрыва полиция забывает команду, но настороженность жителей остаётся и постепенно остывает.

В лесу нет настороженности и сообщений; в хуторе максимум один медленный дед-полицейский с винтовкой. В неблагополучном районе вмешиваются братки и иногда полиция. Стройка получает городскую полицию; пляж и мини-порт обслуживаются Downtown. В Quiet Valley обычных NPC нет. Захват Трамдуро доступен только через специальную сюжетную операцию.

Полиция предупреждает и пытается задержать. За простой побег не стреляет; ответный огонь начинается после стрельбы игроков по полиции. Напарник может прервать надевание наручников, сбив полицейского. При задержании теряются небольшая часть общих денег и один случайный допустимый предмет; при смерти от полиции — больше денег и весь переносимый инвентарь. Денежные потери применяются отдельно к каждому пострадавшему.

На базу полиция приходит по конкретному поводу, требует открыть и затем выбивает дверь. Осмотр короткий; закрытые хранилища не открываются. Уборка и сокрытие помогают, но движение, голос и запах могут выдать спрятанного NPC. Чистая проверка заканчивает текущую претензию, даёт небольшой бонус к снижению районного фона и паузу от повторного визита. Анимации, радиусы, таймеры и суммы не утверждены; предложения отделены ниже.

## 1. Authority, sources and limits

The owner explicitly replaced Fedya as interview decision-maker. **Confirmed** means an explicit interview decision or a named existing contract. **Proposed** means an unapproved implementation/tuning default. This document describes target behavior, not completed functionality.

Only this specification is written. No Unity calls, Assets changes, commits, staging, WORK_SYNC edits or synced-source edits are part of the task.

Available read-only sources:

- `AGENTS.md`, `docs/AgentRules.md`, `docs/PRODUCT.md`, `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md`, and relevant material in `docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md`.
- `docs/specs/OPERATIONS_SPEC_2026-10-15_v01.md`: especially cleanup/inspection sections 18–19 and proposed presets in section 24.
- `docs/specs/BUYERS_SPEC_2026-10-15_v02.md`.
- `docs/drafts/POLICE_V1_DRAFT.md` and existing `Assets/OnlyVolunteers/Police` code: director, config, events, officer/unit states, car motor, map and road data.
- Owner-attached world map v73, dated 17.10.2026. This is a geographical reference, not proof that the latest layout is built in Unity. The attachment is not copied into the project.

### 1.1 Unavailable requested references

These files were not found in this checkout:

- `docs/specs/CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md`
- `docs/specs/SALES_GAMEPLAY_SPEC_2026-10-18_v01.md`
- `docs/specs/WORK_INVENTORY_SPEC_2026-10-18_v01.md`
- `docs/specs/NETWORK_MAP_PLAN_v01.md`
- `docs/reports/CAPTURE_DELIVERY_STAGE_A_HOWTO_RU.md`

The local Operations section 11 is Mortality Rules; the requested Decision 2026-10-18 was not found. This is a source-version mismatch, not proof that it is absent on Fedya's computer.

The initiating brief supplies these binding contracts despite missing sources: bagged corpse witness hook +2; unbagged corpse +10; head bag belongs to Capture Stage B; server-authoritative FishNet co-op for 1–4; host departure ends the session. The inventory most-valuable-item hook is explicitly replaced by the interview for ordinary detention. Do not claim unseen source contents were checked. Reconcile them before implementation.

## 2. What exists now, before changes

Source inspection only. CURRENT_STATE is dated 2026-10-11 and contains historical checks; none were rerun. The police draft is explicitly unapproved and offline.

| Existing component | Observed behavior / limitation |
| --- | --- |
| PoliceDirector | Offline singleton; two suspect records, van and one walking pawn; wanted flags, last-known position/time, incident association, witness dispatch. Not per-player co-op police state. |
| District heat | Per-crowd-district array and decay; influences patrols, dispatch and extra officers. No new red/yellow incident-zone implementation is established by this inspection. |
| PoliceUnit | Parked, patrol, alerted, respond, pursue, dismount, search, give-up and return states. |
| PoliceOfficer | Idle, alert, respond, chase, beat, aim/fire, look, return and leave. Config includes hits-to-arrest and random nighttime shooting; these differ from the target. |
| Car / map / road model | Arcade Rigidbody car, baked route graph, patrol loops, station/base positions and travel-time routing. Reuse these responsibilities rather than introduce another police framework. |
| Witness integration | CrowdDirector.AlertRaised and GreyboxNpc.Incident feed the director. Old draft reporting via points/officers differs from the selected phone calls. |
| Escape | Sight/distance/time logic. Existing defaults include EvadeTime 10/15 seconds and EvadeDistance 80 m, with additional wanted-clear timers. These are not approved target values. |
| Base | Old safe exclusion/edge waiting can stop effective pursuit; target requires witnessed-return inspection. |
| Arrest | OnArrest calls LocalInventory.Model.ApplyArrestPenalty, reports seizure of the most expensive item, teleports to station exit and stands down pawn pursuers. It is a placeholder, not cuffing/rescue gameplay. |
| PoliceEvents | Local static pursuit/slapstick/arrest events, not replicated authoritative transactions. |

Current police tuning refers to a van at upgrade levels 1/3/3. The project now requires the player's van to start at maximum characteristics; pursuit tuning must use that actual van, not assume an underpowered stock van.

The source review does not establish working network inspections, zone UI, shared-fund penalty transactions or persistent police state. Existing separate prototypes are not proof of a completed business loop.

## 3. Explicit decisions list

### 3.1 Confirmed

| ID | Decision |
| --- | --- |
| C01 | Territorial NPC caution and police pursuit are separate. No independent accumulating police heat meter. |
| C02 | Strong local zones plus weaker district background; retain district scale 0–100. No ordinary global city meter is introduced. |
| C03 | Zones require an observed/reported incident, not automatic knowledge of unseen kidnapping. |
| C04 | Red core means strong fear; yellow exterior means weaker fear. Two distinct yellow contributions make only their overlap red. Red stays red. |
| C05 | Red cools to yellow, then disappears; new incidents renew pressure locally. Offline time does not cool state. |
| C06 | Zones appear only on the map. Exact caution behavior and animation are separately designed. |
| C07 | Witnesses use phones. Reactions may include hesitation/no call depending on caution. One event/body cannot create endless increments. |
| C08 | A witness may identify the shared van/crew, rather than only an individual attacker. No automatic knowledge of unseen positions. |
| C09 | No functional surveillance cameras. |
| C10 | Forest: no caution or outgoing kidnapping reports. Hamlet: weak caution; at most one very slow local policeman with rifle. |
| C11 | Rough: substantial caution, gang intervention and occasional police. Construction: medium pressure, harder than Hamlet. Downtown: strong caution/recognition. |
| C12 | Beach and mini-port use Downtown police. Port has few ordinary NPCs; Quiet Valley has none. |
| C13 | Assigned district/service forces join up to a limit. Same pursuers can cross boundaries; new-district forces do not automatically join. |
| C14 | Killed police can be replaced after a delay within the limit; killing escalates response. Hamlet still has only one active grandfather. |
| C15 | Warn and attempt detention first. Flight alone never permits shooting. Player gunfire against police permits return fire. |
| C16 | Escape requires lost sight followed by failure to find the crew nearby. Police forget this pursuit; NPC memory/zones remain. |
| C17 | Cuffing is visible and interruptible by a teammate knocking down the officer. No full convoy-rescue system required. |
| C18 | Ordinary detention: small shared-money loss plus one random eligible carried item. Police-death: larger shared-money loss plus all carried inventory. |
| C19 | Irreplaceable story items excluded from random confiscation. Non-detained teammates continue; no team teleport. |
| C20 | Ordinary money deductions apply separately per detained/dead player, including mixed outcomes, but each player's solo-equivalent cash penalty is divided by active team size `N` and deducted from the one shared fund (`Σ(Xᵢ/N)`). |
| C21 | A concrete report, detected odor/signs or observed pursued return can trigger base inspection. District background alone cannot. |
| C22 | Demand/knock, preparation interval, then entry or door breach. The old 75-point refusal/warrant gate no longer determines entry. |
| C23 | Brief inspection of main accessible places; police never open closed storage, including the closed fridge. |
| C24 | Cleanup/covering can hide evidence; odor, exposed parts, movement, voice or displaced covers can reveal it. Detailed hiding design is deferred. |
| C25 | Clean inspection ends that response, yields a small district bonus and repeat-visit grace. It does not erase all civilian memory/zones. |
| C26 | Odor alone cannot convict. One incidental stain is insufficient. Discovered bodies, body parts and organs are major evidence under Operations. |
| C27 | Body report sends police to the location. If no crew/van is found, they search briefly and leave; no automatic base tracking. |
| C28 | Time without new reports reduces caution. Cleanup prevents further reports, not deletion of past reports. |
| C29 | Bagged/unbagged corpse report hooks +2/+10 retained, deduplicated. |
| C30 | Head bag is Capture Stage B: obstructs sight, does not mute or stop physical resistance. Not a corpse bag. |
| C31 | Early free capture of Tramduro unavailable; special story operation and prerequisites authorize the exception. |
| C32 | Save zones, evidence, timers, active pursuit/inspection and applied consequences; loading cannot erase risk. |
| C33 | Buyer meetings keep ordinary witness/police rules; no buyer betrayal or extra patrol generation. |
| C34 | Team money rule (Vadim, 2026-10-19): sale/reward income is credited once at its full team amount; per-player cash penalties are divided by active team size, while one incident-level fine is divided once. |

### 3.2 Proposed defaults — not interview confirmations

| ID | Proposed implementation/tuning choice |
| --- | --- |
| P01 | Stable incident ID with position, district, report/evidence IDs and independent timed zone contribution. Derive overlap rather than recursively generating incidents. |
| P02 | Starting red/outer-yellow radii, metres: Hamlet 20/60; Construction 30/80; Rough 35/100; Downtown 40/120. Beach/Port initially use Downtown profile. |
| P03 | Start with 3 active-world minutes red, then 7 yellow; district duration multipliers configurable. |
| P04 | Same-event reports update knowledge without indefinitely refreshing caution. Only a new verified offense can refresh pressure. |
| P05 | One body/incident contributes +2 or +10 total; exposing previously bagged remains adds only +8. Moving the body slightly cannot create a new event. |
| P06 | Evidence weights feed stronger local and weaker district effects through separate configurable coefficients; +10 is not automatically ten whole district points. |
| P07 | Clean inspection subtracts 5 district points, clamped at zero, with no automatic deletion of local records. Replaces old -25. |
| P08 | Initial police car caps: Construction 2; Rough 2 plus a separately capped gang group; Downtown 3 shared with Beach/Port. Hamlet is one person. Exact staffing/gang cap needs tuning. |
| P09 | Initial escape: 10 seconds unreacquired and outside an 80 m nearby-search envelope. No extra heat score. |
| P10 | Initial knock interval 15 seconds; main-area search about 45 seconds; same-cause/base repeat grace 10 active-world minutes. A genuinely new witnessed offense can override grace. |
| P11 | Cuff action 3 seconds, canceled on officer knockdown/invalid reach; briefly prevent instant recuff by the interrupted attempt. |
| P12 | Uniform random choice among eligible carried item instances; server resolves once and persists the selection. |
| P13 | Money deductions clamp to available shared funds without a new debt system. Rates, amounts and caps are placeholders. |
| P14 | Police-death removes story items into protected recovery instead of permanently blocking progression. Owner protected random confiscation, not death: this recovery rule needs review. |
| P15 | Found remains produce one deduplicated caution event after report; a fruitless police visit adds no extra heat. |
| P16 | Firearm permission is scoped to the active crew/incident threat. Non-firearm physical rescue triggers physical pursuit, not automatic return fire. |

## 4. Territorial caution and NPC interface

Keep three concepts separate: district background D (0–100), local incident contributions, and current police knowledge/response state. District background must not automatically paint a whole district red or generate a visit. There is no second police heat number.

A position is red when any red contribution covers it or two distinct yellow contributions overlap. One yellow contribution gives yellow; otherwise no local tint. A single incident's exterior is an annulus outside its core and cannot overlap with itself. Combining overlays never creates new evidence or dispatch requests. Forest suppresses territorial contributions.

NPC interface: normal, yellow-cautious, red-afraid; recognition/report eligibility and panic/resistance modifiers. Red Downtown should discourage farming the same place: residents recognize the van/crew, panic sooner, phone sooner and resist loading more strongly. Exact behaviors/animations remain a separate specification, not invented percentages in this document.

After police forget a pursuit, new civilian recognition can generate a genuinely new call. Territorial memory is not an invisible perpetual police GPS. Show authoritative colored regions consistently on the team map; no world-space circles. A separate exact numeric HUD was not selected and is not required in v01.

## 5. District response profiles

| Territory | Target behavior |
| --- | --- |
| Forest | No locally generated caution/kidnapping reports. Existing outside pursuers may enter; crossing the boundary is not instant escape. |
| Hamlet | Weak civilian caution. One very slow local grandfather-policeman with rifle, never multiple simultaneous grandfathers. Final firearm rule overrides the earlier free-shooting description. |
| Construction | Compact medium-pressure site, harder than Hamlet. Police approach from the city; do not invent a separate on-site police institution. |
| Rough | Substantial caution; residents may call gang help, occasionally police. Gang beating/interference is distinct from official detention/confiscation. Preserve slapstick combinations. |
| Downtown | Strong recognition and fear in hot local zones; bounded main-city response. |
| Beach / mini-port | Downtown service. Few port NPCs; port is not a major capture-farming area. Do not duplicate Downtown's full pool for each location. |
| Quiet Valley | No ordinary civilians. A laboratory is not immune to incoming pursuit or a concrete police cause; exact patrol coverage is deferred. |
| Elite Hill | Very difficult captures/high security. Exact security encounter remains authored content, not an automatic physical capture ban. |
| Tramduro island | Restricted before story authorization. Owner described extreme early-intrusion missile retaliation; exact presentation is deferred. Story operation supplies the permitted access/capture exception. |

Responders travel from plausible origins and arrive gradually up to the service limit. Do not spawn visible cars directly on the van. Crossing districts neither resets pursuit nor allocates a fresh pool. Delayed casualty replacement cannot generate unlimited concurrent responders. Escalation uses incident flags/states, not an accumulating police meter.

## 6. Witnesses and evidence

Witnesses must perceive relevant events within valid range/occlusion. They may hesitate, investigate or call; caution, NPC type and situation influence that choice. A phone call is visible and takes time; no completed report before it finishes. Do not require running to a reporting station. Server resolves random choices; probabilities are configurable proposals, not selected values.

Reports carry the observed location, offense/evidence identity and observed crew/van information. Team-level identification is allowed; impossible tracking to an unseen base is not. Police-caused civilian collisions must not frame the crew by accidental proximity association.

| Evidence | Rule |
| --- | --- |
| Blood / cartoon jam stains | Minor inspection evidence; one incidental stain is insufficient. Cleanup removes source, not previous knowledge. Street stain does not identify its maker. No automatic police-heat increase. |
| Small trash / used supplies | Minor corroboration when actually discovered. Ordinary closed trash bags are not automatically proof; odor/signs can prompt interest. Minor scoring remains Proposed. |
| Bodies / body parts / extracted organs | Major evidence when discovered at inspection. Remote report is a lead, not proof the crew is present. |
| Bagged/unbagged corpse | +2/+10 accepted-report hooks, deduplicated. Seeing and completing a report are different. Closed bag does not grant impossible visual knowledge; odor/witnessed packing/suspicious signs can cause a report. |
| Odor | Persistent sources generate gradual odor. Can trigger interest/call/visit but not conviction alone. Removing sources fades odor rather than erasing past reports. |
| Hidden live NPC | Real sight, sound, movement or displaced cover can expose it; detailed hiding design is deferred. |
| Cameras | None: no footage, recognition or footage-deletion subsystem. |

A found-body caller may hesitate rather than phone. A completed call sends police to that place; if crew/van is absent, police search briefly and leave. The body need not magically disappear. One evidence object cannot repeatedly regenerate zones and responses without a new meaningful incident.

Odor near a base sometimes draws civilian investigation, sometimes a call. It is not a guaranteed victim lure or permission to walk through locked boundaries. Forest generates no outgoing reporting loop. No complex citywide forensic simulation is required.

## 7. Response stages, pursuit and rescue

These are operational stages, not numerical wanted levels:

| Stage | Trigger / result |
| --- | --- |
| Routine | Assigned patrol/availability without active crew pursuit. |
| Respond / investigate | Concrete report, direct sighting, police-detected odor/signs or justified base follow-up. Travel to known location. |
| Warn / pursue / search | Crew/van found; demand compliance, pursue using sightings/last-known location, add bounded origin-service reinforcements. |
| Attempt detention | Player submits or officer physically secures a close valid target; visible cuffing starts. |
| Armed response | Player gunfire against police permits return fire. Flight, zone color, nighttime or a closed door alone do not. |
| Stand down | Valid escape, fruitless search, completed detention or clean inspection closes the relevant response. |

The owner selected shooting back after player gunfire, superseding earlier general statements about aggression. Non-firearm interference can justify physical pursuit/restraint; it is not an automatic firearm trigger. No arbitrary nighttime shooting chance.

Another player can knock down the cuffing officer and interrupt the action. Rescue must cancel that attempt before penalties or station transfer commit. After completed detention, use a short processing presentation and station-exit release. No playable prison, long sentence or full convoy-interception system in v01. Other teammates remain in the world.

Escape closes current crew/van pursuit knowledge after loss-of-sight and unsuccessful nearby search. Closed reports cannot instantly reactivate the same response. A new recognition call or offense can. Driving into the base while observed does not count as escape; the prototype's safe disc cannot suppress the new inspection.

## 8. Base visit and short inspection

Valid cause: police saw the pursued van enter; a concrete civilian report; police detected odor or suspicious visible signs while passing. High district caution alone is insufficient.

Sequence: arrive at known entrance, demand/knock, preparation interval, enter if opened or breach if closed, briefly inspect accessible main areas, resolve discovered evidence. No instant teleport into the building. Breach is an entry sequence, not confirmed permanent destruction of an owned base; door restoration is a Proposed integration detail.

Players can clean stains, remove waste, store merchandise or cover NPCs during preparation. These are physical actions, not deletion of objects. Existing designated disposal destinations remain valid and do not reset caution automatically.

Police never open closed storage, including refrigerator/cupboard contents. Querying a container inventory does not count as discovering its contents. Open contents and exposed objects can be discovered. External odor/sound may create concern but does not override the closed-storage rule. This explicitly supersedes Operations' prior discoverable-fridge-contents assumption.

A cover blocks direct sight; exposed parts, motion, speech or displacement can expose the NPC. Awake/unrestrained NPCs may shed covers. Do not invent a universal per-frame random reveal roll. A cover alone is not proof of crime. Detailed covering interaction/animation and probabilities remain a separate design task.

Insufficient evidence: officers leave physically, close this response, apply the small district bonus once and activate repeat-visit grace. Ordinary district patrols remain. Local zone records and NPC memory do not disappear. The same unchanged odor episode cannot immediately restart the visit during grace.

Sufficient evidence: retain Operations' choice between displayed inspection bribe and its scripted arrest. All monetary rates/amounts are placeholders here. Bribery ends inspection without arrest/confiscation and does not count as clean. Only actually discovered merchandise contributes to valuation/seizure.

## 9. Consequences and explicit supersessions

### 9.1 Ordinary detention and police-caused death

| Outcome | Shared money | Inventory / world |
| --- | --- | --- |
| Escape | No outcome fine | Keep items; police response closes, civilian caution persists. |
| Completed live detention, including after attempted flight | Small placeholder deduction for that player | One random eligible carried item; irreplaceable story items excluded. Short processing/station exit. |
| Police-caused death | Larger placeholder deduction for that player | All carried inventory lost. Base, van cargo and teammates are not remotely seized. Story-item recovery is Proposed P14. |
| Rescue before cuffing completes | No detention deduction | Keep inventory; physical pursuit may continue. |

The final interview explicitly selected per-player shared-fund deductions: two detentions cause two deductions; a detention plus a police-death causes both deductions. Each victim's solo-equivalent amount is divided by active team size `N`; total debit is the sum of the affected players' amounts divided by `N`. Thus one affected player in a four-player team costs `X/4`; if all four each incur `X`, total debit is `X`. Each victim has one terminal outcome transaction; do not charge that same victim both detention and death for a single capture outcome. Snapshot `N` and affected player IDs with the incident outcome so disconnects or duplicate requests cannot change or repeat the amount.

Random confiscation replaces most-valuable selection. No eligible item means no invented replacement loss. Money comes from the team fund, not a newly invented personal wallet. All percentages, fine caps and amounts are placeholders. Item confiscation remains per affected player and is not divided. Balancing must preserve a real choice: surrender limits losses; flight offers escape but risks worse losses. Do not force that balance by making ordinary flight automatically trigger gunfire.

The whole-inventory rule here concerns police-caused death. It does not silently define generic environmental/PvP death. Exact respawn presentation is deferred.

### 9.2 Separate Operations inspection package

Retain Operations' separate base-inspection punishment: confiscate discovered organ/blood merchandise; approximately 30% equipment purchase-value seizure while preserving the existing protected basic kit/stationary fridge; affect inspected base and detained players, not other owned bases; short station release; one financial/property package per inspection incident. Its one incident-level fine is divided once by active team size `N`; do not stack ordinary street-arrest penalties. Voluntarily choosing the displayed bribe remains a full-price payment. Monetary amounts/rates are placeholders. The new closed-storage rule limits what is actually discovered.

Do not stack an ordinary random-item seizure or ordinary per-player street detention fine on that same scripted inspection arrest. A genuine police-death is a separate outcome, but no victim receives duplicate terminal penalties. Equipment protection does not grant absent furniture or magically restore stock.

Operations' district setting to 30 after inspection punishment is retained as an existing inspection-specific contract, not a newly interviewed value or street-arrest reset. It does not remove local zones. Its fit with the weak district background needs source reconciliation before implementation.

### 9.3 Explicit supersessions

| Earlier behavior / proposal | Target |
| --- | --- |
| Most valuable ordinary arrest item | One random eligible carried item. |
| Heat/night-based ordinary gunfire | Warning/detention first; player gunfire permits return fire, flight alone does not. |
| District heat alone schedules base visits | Concrete cause required. |
| Refusal below 75, warrant at 75 | Justified visit leads to warning and entry/breach regardless of district number. |
| Clean inspection lowers district by 25 | Small bonus instead; 5 is Proposed. |
| Inspectors may discover closed fridge stock | Closed storage is never opened during this inspection. |
| Old safe-base exclusion ends practical pursuit | Observed pursued return can trigger inspection. |
| Suggested one ordinary fine per incident | Separate deduction per detained/dead player; base inspection retains its separate one-package contract. |

## 10. Head bag — Capture Stage B

Head bag obstructs captive vision. It does not automatically sedate, silence, restrain limbs, stop resistance, prevent escape or suppress voice. Other witnesses can still see the capture. It does not classify a living captive as a bagged corpse for +2.

Do not back-port this into Stage A. Equip/remove actions, exact visual-awareness effects and animations depend on the missing Capture Delivery source and separate NPC behavior design. This spec confirms scope and consequences, not completed assets or code.

## 11. Co-op and server authority

For 1–4 players, server owns incident acceptance, witness random choices/call completion, caution contributions/decay, overlap, dispatch caps, sightings, search closure, cuff/rescue validation, discovered inspection evidence, outcome resolution, random confiscation, shared money and persistent state. For each monetary outcome it snapshots active team size `N` and affected player IDs, then applies `Σ(Xᵢ/N)` once to the shared fund; sale income elsewhere is credited once at its full team amount. Clients request actions and display authoritative results. This extends shared-world authority; it does not claim existing player movement is fully server-reconciled.

Validate current state and physical reach for rescue, cleanup, storage, covering and detention. Give each cuff attempt and consequence transaction a stable identity. When rescue and completion race, exactly one authoritative terminal result wins. Late join/reconnect receives a full snapshot, not just subsequent events.

Reports may concern the crew, but one player's detention cannot teleport all four. Personal outcomes remain individual. Inspection arrests apply to those present/detained, not players elsewhere. Shared service caps prevent four players/callers from multiplying the roster.

Disconnect is not escape or a random-confiscation reroll. Preserve pending outcomes by stable player identity. Host leaves = session ends; no host migration. Save authoritative state so normal resume cannot cancel pursuit or inspection.

## 12. What persists in saves

| State | Required persistence |
| --- | --- |
| Evidence/world | Stable body/NPC/item IDs; positions/container membership; supported bag/cover/restraint state; stains, trash, odor sources and odor-episode identity. |
| Territorial memory | District background, incident positions/profiles, red/yellow remaining lifetimes, already-counted evidence/report IDs. Overlap can be reconstructed. |
| Witnesses | Resolved relevant random choices and in-progress/completed reporting stage; no duplicate completed calls. |
| Police response | Origin service, committed roster, losses/replacement delays, crew/van knowledge, last-known positions, search/escape timers and firearm permission. |
| Detention | Target/actor/attempt identity, cuff stage, rescue/completion outcome, pending processing and station release. |
| Inspection | Base/cause identity, knock/breach/search stage, discovered evidence, outcome, grace remaining and clean-bonus-applied marker. |
| Consequences | Cash deductions, team-size snapshot `N`, affected player IDs, chosen random item, confiscated IDs, applied-outcome keys and inspection equipment package. |
| Story access | Island prerequisites and operation authorization; no inferred unlock through ordinary police escalation. |

Timers use active-world time and resume remaining duration. Saving during knock, cuffing, an odor episode or corpse reporting must neither reset risk nor duplicate it. Persist resolved random outcomes. Do not infer prior payment from current cash alone. Save migration belongs to the project's existing save system; no parallel format is required here.

## 13. Numbered acceptance checks

Future implementation checks, **NOT RUN** in Unity for this document-only task. Checks involving Proposed defaults validate behavior/configurability, not owner approval of numerical tuning.

| ID | Scenario | Expected result |
| --- | --- | --- |
| POL-01 | Review implementation baseline | Existing offline police responsibilities identified; no duplicate police framework. |
| POL-02 | Unseen kidnapping without report | No omniscient zone/dispatch from the hidden act alone. |
| POL-03 | One accepted local incident | Red core/yellow exterior on map; no world-space circle. |
| POL-04 | Two yellow contributions overlap | Only intersection red; red/red remains red; one event cannot overlap with itself. |
| POL-05 | Incident ages without new reports | Red to yellow to none; no whole-district indefinite refresh. |
| POL-06 | Forest kidnapping / incoming pursuit | No local caution/calls; existing pursuers do not vanish at boundary. |
| POL-07 | Red Downtown repeat capture | Stronger recognition, fear/resistance hooks; fresh call can restart response after prior escape. |
| POL-08 | Several witnesses see one body | No endless increments; hooks remain +2 bagged / +10 unbagged. |
| POL-09 | Interrupt unfinished phone call | No completed report; persisted resolved choices do not reroll. |
| POL-10 | Camera trigger audit | No functional camera detection or footage subsystem for v01. |
| POL-11 | Body call without located crew/van | Respond to site, search briefly, leave; no invented base tracking. |
| POL-12 | Hamlet escalation | At most one slow local grandfather-policeman at a time. |
| POL-13 | Rough response | Gang interference and occasional police possible; gangs not silently granted arrest/confiscation powers. |
| POL-14 | Concurrent Downtown/Beach/Port calls | Shared Downtown cap, not fresh full pool per area/caller/player. |
| POL-15 | Cross district boundary | Same pursuers continue; no automatic new-area reinforcement or boundary escape. |
| POL-16 | Kill responders | Delayed replacement stays within concurrent cap. |
| POL-17 | Run/drive away at day or night | Warn/pursue; flight/night/caution alone cannot permit gunfire. |
| POL-18 | Fire on police | Appropriate active incident permits return fire, not permanent worldwide authorization. |
| POL-19 | Valid loss-of-sight escape | Current response closes after search condition; zones/background remain. |
| POL-20 | Teammate knocks down cuffing officer | Attempt canceled before penalty/teleport; no phantom arrest. |
| POL-21 | Complete ordinary detention | Small shared-fund deduction plus one random eligible carried item, not most valuable. |
| POL-22 | Only protected story items carried | Random confiscation skips them; no invented item loss or progression block. |
| POL-23 | Police-caused death | Larger deduction/all carried inventory loss; no remote base/van/teammate seizure. Story recovery is Proposed. |
| POL-24 | Two detentions / mixed death-detention | Separate deductions per victim; one terminal package per victim. |
| POL-25 | Observed pursued return to base | Demand/knock then entry/breach; old safe disc or suspicion under 75 cannot cancel. |
| POL-26 | High district background without concrete cause | No automatic inspection solely from number. |
| POL-27 | Odor attracts civilians | Variable interest/call; no guaranteed victim lure; odor alone insufficient to convict. |
| POL-28 | Inspect main areas | Brief physical search, actual perceived evidence, no inventory omniscience. |
| POL-29 | Closed fridge/cupboard | Never opened by inspection; unseen contents not automatically discovered/seized. |
| POL-30 | Covered live NPC quiet versus moving/speaking | Cover hides sight; real exposure/sound/motion can reveal; animation details separately reviewed. |
| POL-31 | One stain versus exposed organ | One stain insufficient; discovered organ major evidence. |
| POL-32 | Clean inspection | Officers leave, response closes, small bonus once/grace starts; civilian memory persists. |
| POL-33 | Same unchanged odor after clean visit | Grace prevents immediate repeated inspection; no frame-by-frame complaint loop. |
| POL-34 | Failed inspection/bribe/arrest | Existing separate package, no stacked ordinary random-item seizure or street detention fines. |
| POL-35 | Head bag on living Stage B captive | Vision obstruction only; voice/resistance remain; not corpse +2. Stage A unaffected. |
| POL-36 | Reload zones/pursuit/cuff/inspection | Restore remaining active-world time/state; no risk reset, random reroll or duplicate charge. |
| POL-37 | Concurrent rescue/detention/cash operations | One authoritative outcome per action/victim; matching client state. |
| POL-38 | Late join / host departure | Authoritative snapshot on join; host departure ends session without migration. |
| POL-39 | Ordinary buyer meeting | No betrayal or extra patrol spawn; ordinary observable-event reporting continues. |
| POL-40 | Early island approach / authorized finale | Early free capture unavailable; story prerequisites supply explicit exception. |
| POL-41 | Playtest surrender versus escape | Surrender limits loss; flight can succeed; police-death worse; neither option dominates every situation. |
| POL-42 | Vehicle balance review | Use actual maximum-start player van; do not assume weak stock-upgrade progression. |
| POL-43 | Apply cash outcome to a party | Each affected player's solo-equivalent penalty is divided by the incident's active team size; one victim in a four-player party costs `X/4`, and duplicate outcomes never charge twice. |

## 14. Questions left open

Core police interview is complete. These are source dependencies, explicitly deferred features or Proposed tuning, not silently approved decisions:

1. Validate the 2026-10-19 shared-cash scaling rule against the connected capture, sales, inventory, operations and network implementations before release.
2. Separate NPC caution/hiding spec: precise recognition, resistance modifiers, panic/voice timing, cover displacement, conditions/chances by NPC type and all animations. Owner explicitly deferred this work.
3. Tune radii, durations, district coefficients, witness probabilities, staffing/gang cap, replacement delays and knock/search/grace/cuff timing. P01–P16 are starting proposals, not playtested values.
4. Monetary values/rates remain placeholders. Carried stack selection needs inventory integration; P12 currently selects one eligible instance.
5. Story-item recovery after whole-inventory police-death loss. P14 avoids progression deadlock but was not independently confirmed.
6. Elite security and Tramduro operation: prerequisites, permitted access, early missile deterrent presentation, exceptional forces, extraction/delivery and finale. No completed mission is invented here.
7. Quiet Valley patrol/base-service coverage with no ordinary civilians. Do not add civilians merely to solve reporting.
8. Retained Operations inspection punishment setting district to 30 versus newly weak district background: check authoritative source revision. Never apply this to street arrest or erase zones with it.
9. Door restoration, death/respawn presentation and existing save-schema migration. No camera, convoy-rescue or prison subsystem implied.

## 15. Verification and file scope

PASS — police rules now point to the shared-fund scaling contract in NETWORK §3.9; arrest inventory consequences align with the random eligible item rule.

PASS — Confirmed decisions remain separate from Proposed defaults; arrest money, team-size snapshot and persistence are explicit. Runtime behavior remains unverified.

NOT RUN — Unity compilation, Play mode, multiplayer and subjective balance checks. POL acceptance checks above are future checks, not reported results.

Updated in this documentation pass: shared-fund scaling and team-size persistence. No Unity or Assets changes and no commits were made.
