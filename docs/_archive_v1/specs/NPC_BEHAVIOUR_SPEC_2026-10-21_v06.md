# VOLUNTEERS ONLY — NPC Behaviour Specification

Revision: v06 · 2026-10-21 · Status: PARTIAL DRAFT

## Краткое резюме

Семь характеров: спокойный, трусливый, борзый, любопытный, заторможенный, находчивый и тупорылый. Тревожный объединён с трусливым; «умный» уточнён как «находчивый». Awareness определяет замечание и распознавание угрозы, характер — выбор действия. Район сдвигает среднюю awareness, но сохраняет разброс. Тупорылых много в лесу и хуторе, мало в даунтауне и на пляже; в Элите их нет, это опасная ловушка с охраной. Главная цель — смешные, разнообразные ситуации из небольшого набора общих действий. Последнее уточнение: почти вся толпа имеет тупорылую мимику; под опасностью комичное исполнение действий требуется для всех обычных характеров, включая умных и находчивых. Умное решение не отменяет смешной бег, панику и физическую неловкость. Характер «тупорылый» остаётся особенно выраженным вариантом, а не единственным источником юмора. Обычный проезжающий бусик сам по себе не вызывает паники. Пять общих выводов: «Всё нормально», «Мне мешают», «Что-то подозрительное», «Нападают!», «Непосредственная опасность!». Это не лестница: возможен прямой переход к любому обоснованному выводу. Найденный труп и бегущий NPC без глаз относятся к «Что-то подозрительное», если самого нападения и текущей непосредственной угрозы не видно.

## 1. Purpose, sources and current state

Make ordinary adult NPCs readable, varied and funny before and during physical van abduction. Comedy and enjoyable capture are the primary experiential goals. Avoid a crowd that always runs away or continuously performs simultaneous slapstick.

This revision records decisions approved in the current G42 conversation. The requested `NPC_BEHAVIOUR_SPEC_2026-10-21_v01.md` and its referenced historical decisions were not present in this checkout when checked. This file does not reconstruct or claim to incorporate that missing draft. Revision v02 recorded the initial approved characters; v03 added the five shared conclusions; v04 added minor-disturbance decisions and the crowd-wide comic baseline; v05 clarifies that comic execution under danger also applies to intelligent/resourceful NPCs. Historical integration remains open.

Read-only references:

- `docs/NPC.md`: base model, comic animation descriptions and presentation principles.
- `ArtSource/Characters/SAUSAGE_BUDDY_01/README.md` and `buddy_pool_*.py`: appearance pool, including excluded legacy types. Appearance assets are not approved behaviour profiles.
- `docs/drafts/CROWD_AI_DRAFT.md`: historical offline crowd design with walking routes, activity points, visibility checks and a witness reporting placeholder. It describes an old run-to-report / alert 0–5 system, not the target police contract. Its runtime status is not verified by this document.
- `Animations/Crowd_v01/crowd_manifest_v02.json` under the Buddy source folder: exported smoking and wall-lean transition clips. An export does not demonstrate runtime integration.
- `POLICE_SUSPICION_SPEC_2026-10-18_v01.md`, `CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md`, district specs and the current canon: connected contracts, subject to the explicit conflicts below.

Revision v06 separates shared conclusions, captive circumstances and persona presentation for a small common behaviour design. No Unity inspection, runtime verification or implementation is part of this revision.

## 2. Explicit decisions

| ID | Status | Decision |
|---|---|---|
| NB-D01 | Confirmed | The main goal is comedy: the player should find NPC reactions funny and varied. Owner: «Главное, чтобы это было смешно». |
| NB-D02 | Confirmed | Districts shift average awareness while retaining individual variation. Downtown does not consist entirely of smart fleeing NPCs; Hamlet does not consist entirely of oblivious ones. |
| NB-D03 | Confirmed | Awareness and character are separate. Awareness governs noticing/recognition; character governs the chosen response. |
| NB-D04 | Confirmed | Seven primary characters: Composed, Fearful, Confrontational, Curious, Slow-reacting, Resourceful and Foolish. Anxious and cowardly are merged into Fearful; Smart is clarified as Resourceful. |
| NB-D05 | Confirmed | One primary character per NPC for the initial design. No independent Cunning character; deceptive acts are occasional options of suitable existing characters. |
| NB-D06 | Confirmed | An ordinary passing/parked van is not sufficient reason to panic or flee in a calm area. Suspicious actions, direct aggression, witnessed capture or recognition in a hot zone supply reasons to react. |
| NB-D07 | Confirmed | Many Foolish NPCs in early districts, especially Forest and Hamlet. Few in Downtown and City Beach. Construction and Rough proportions remain open. Owner: «тупорылых должно быть прям много». |
| NB-D08 | Confirmed | Elite Hill is a dangerous trap, not ordinary civilian harvesting territory. No Foolish NPCs there. The owner allows the possibility of abducting an FBI guard, not routine civilian targets or a guaranteed successful guard capture. |
| NB-D09 | Confirmed | Appearance/persona influences likely character and expressive presentation without forcing every instance of an appearance to behave identically. Exact assignments remain open. |
| NB-D10 | Confirmed | Use a small shared action/animation vocabulary. Variety comes from character, awareness, current activity, objects, surroundings and timing. No unique AI system per appearance. |
| NB-D11 | Confirmed | React to meaningful events/timers, retain a selected response through an episode, and avoid continuous expensive deliberation. Detailed behaviour belongs near players. |
| NB-D12 | Confirmed | Normally give one nearby participant the prominent gag while others respond simply. Do not turn every witness into a simultaneous slapstick performer. Exact group limits and cooldowns remain tuning proposals. |
| NB-D13 | Confirmed | Resourcefulness is not omniscience; foolishness is not helplessness; fear is not automatic surrender; confrontational behaviour is not a strength bonus. |
| NB-D14 | Confirmed | Use five shared conclusions: Normal, Being bothered, Something suspicious, An attack, Immediate danger. Many concrete stimuli map to the same conclusion; do not build a unique character response for every stimulus. |
| NB-D15 | Confirmed | Conclusions are not an ascending ladder. A meaningful perceived event can directly cause its relevant conclusion. |
| NB-D16 | Confirmed | A strike and a grab both mean An attack; the victim's actual physical state constrains available responses. A nearby shot means Immediate danger, while a direct hit also applies actual injury/incapacitation independently. |
| NB-D17 | Confirmed | Something suspicious includes finding a motionless corpse, seeing an eyeless escaped NPC running, finding a restrained person without visible captors, or hearing unexplained banging from closed cargo. It can be an obviously grave abnormality without a visible ongoing attacker or immediate threat. |
| NB-D18 | Confirmed | Distinguish an affected NPC from a witness without adding separate conclusion sets. Information is limited to what the NPC actually perceived; discovering aftermath does not reveal the culprit. |
| NB-D19 | Confirmed | When a disturbance or threat ends, NPCs can return to ordinary activities; minor disturbances clear faster than attacks. Exact cooldowns and escalation thresholds remain open, and returning to routine does not erase district hot zones or already completed reports. |
| NB-D20 | Confirmed | Minor disturbance has a shared response basis: look, step aside or express annoyance; character alters delivery rather than requiring seven separate systems. |
| NB-D21 | Confirmed | Being knocked down by a first accidental on-foot collision is initially a disturbance, not automatically an attack. Vehicle knockdown is a separate exception: the owner generally treats it as attack, but explicitly leaves district-dependent interpretation unresolved. |
| NB-D22 | Confirmed | Repeated interference becomes less plausibly accidental; tolerance depends on character. Confrontational NPCs may push the player after repeated harassment, with visible displeasure first. Exact thresholds are open. |
| NB-D23 | Confirmed | Foolish behaviour must include conspicuous comic survival acts: fleeing, ridiculous hiding and pretending to be dead, not merely a long stare or a question icon. Exact triggers and weights remain open. |
| NB-D24 | Confirmed | Latest owner clarification: foolish facial expression is the default tone for almost all ordinary NPCs; the later NB-D26 clarification requires comic execution under danger even from genuinely smart instances. Fear, bravado, curiosity and different reporting/recognition speeds coexist with this comic baseline. Owner: «ебаленки у них должны быть у всех тупорылые и действия довольно тупорылые, кроме парочки умных». |
| NB-D25 | Confirmed | The earlier low Foolish-character share in Downtown/Beach does not remove comic presentation there. Distinguish the dominant Foolish response preference from the crowd-wide comic execution layer. Exact character taxonomy/weights under this clarification still need review; no silent district percentage changes. |
| NB-D26 | Confirmed | Latest clarification: NPCs can have sensible intentions and intelligent decisions, but forced action under danger must be funny across ordinary characters, including Resourceful/smart instances. Running, tumbling, tripping, exaggerated flight, ridiculous hiding and fake death form the shared comic repertoire. Intelligence grants no exemption from comic physical execution. This does not require every NPC to perform every gag in every incident. |
| NB-D27 | Confirmed | Persona/skin supplies everyday activity, props and signature expression (e.g. streamer filming). Character supplies response preference; a gopnik skin does not force fighting. Common conclusions determine which responses are relevant. Exact per-persona actions remain open. |
| NB-D28 | Confirmed | Split the directly affected victim's experience into attacked while free, held/carried, inside cargo and at the base. These circumstances change available reactions without adding four more shared threat conclusions. |
| NB-D29 | Confirmed | A conscious captive brought to the base is strongly frightened by default; character changes expression and coping. Physical state, restraints and table straps still constrain every action. |
| NB-P03 | Proposed | Select one main behaviour action at a time, using a shared action pool filtered by physical feasibility. Character alters preferences; persona adds a small signature option/presentation, not a separate AI for every character/skin/conclusion combination. |
| NB-P04 | Proposed | Reconsider choices at meaningful events or bounded timer completion; keep presentation/movement running as necessary without constant high-level rerolls. Use cheap nearby candidates and an ordinary fallback; exact budgets and distances require implementation review and profiling. |
| NB-P01 | Proposed | Specific gag examples and clip assignments below are candidates, not a mandatory animation production list. |
| NB-P02 | Proposed | Numeric awareness distributions, action weights, group limits, distances, delays and gag cooldowns require design approval and playtesting. No numerical performance result is claimed. |

## 3. Layer A — ordinary life and persona

Adults walk, pause and perform simple activities appropriate to their district. Ordinary life supplies the calm contrast that makes a sudden reaction funny. Walking past a player is allowed; every encounter must not start a capture reaction.

Persona means appearance, occupation, props and manner: stash courier, grandmother, bodybuilder, office worker, streamer, etc. Character determines response preference. The same confrontational intention can appear as a grandmother brandishing a bag, a bodybuilder squaring up or Karen pointing a phone. These presentations are examples pending per-persona approval.

The current activity can distract an otherwise attentive NPC. Awareness is not a grade of intelligence. A Foolish person may notice an incident immediately and choose an absurd response; a Resourceful person may notice late and then choose well. Slow-reacting additionally delays visible action after recognition, so it is not merely a low-awareness preset.

Exact routine tables, activity weights, concurrent slots and per-persona character weights remain open. Existing appearance lists do not approve them automatically.

### 3.1 Comic baseline across characters — latest owner clarification

Almost all ordinary NPCs should look foolish and act with comic awkwardness. This comic direction is not an exclusive privilege of the Foolish primary character. The latest owner clarification explicitly applies funny execution under danger to intelligent/resourceful NPCs as well. A Fearful NPC may choose to escape but hide absurdly; a Composed NPC may choose to report but fumble their phone; a Confrontational NPC can confidently make an embarrassing mistake. These are examples of the direction, not new approved per-character assignments.

The Foolish primary character emphasizes bad interpretation and absurd choices. Other characters retain their principal intention while often executing it stupidly. Rare genuinely smart NPCs provide contrast through sound decisions, not an exemption from funny physical execution. A sensible escape plan can still be expressed through a ridiculous run, a stumble or an exaggerated recovery. Exact smart-character frequency remains open.

This latest direction expands earlier statements about occasional comic failure. Downtown and Beach can have fewer dominant Foolish characters while still looking like the same comic game. It does not automatically authorize Foolish Elite guards or reduce Elite's danger. A foolish expression is not proof that an NPC will be harmless, slow to call or easy to hold.

Do not turn this baseline into constant synchronized gag playback. The established rule of simple shared actions, varied timing and occasional prominent gags still applies. Comedy must be verified in playtesting rather than asserted from a design label.

## 4. Layer B — character and capture reactions

### 4.1 Composed / Спокойный

Proportionate, restrained response. A normal van is unremarkable. Incidental contact prompts a look, a step aside or annoyance. Recognized violence prompts withdrawal and a possible call for help. Direct capture prompts resistance and calling out. This character supplies contrast with exaggerated reactions, rather than being oblivious or passive.

### 4.2 Fearful / Трусливый

Self-preservation is the priority once there is a credible threat. Possible responses include fleeing, freezing or hiding; the NPC may abandon props or companions. Reporting can happen from safety where district rules permit it, but calling is not the automatic response to every scare. Once held, fear may produce vigorous resistance. Ordinary van traffic alone does not trigger flight.

### 4.3 Confrontational / Борзый

Challenges players, approaches an obstruction, pushes back or intervenes for another NPC. Direct capture provokes active resistance. Support can increase confidence; losing companions can make some instances back down. Others keep fighting. Bravado does not imply physical strength, courage under every condition or a unique combat system.

### 4.4 Curious / Любопытный

Approaches to inspect something unusual, including open cargo doors or an incident. Curiosity can temporarily override caution even after danger is noticed. Clear direct danger eventually changes the response: the NPC must not watch a kidnapping indefinitely merely because they are curious. This creates an opportunity by bringing a witness too close, without making them identical to Foolish.

### 4.5 Slow-reacting / Заторможенный

Recognition and/or action develops slowly. A contact may produce a delayed look; being lifted may initially produce little visible reaction, followed by a sudden burst of resistance during the carry. This is delayed participation, not guaranteed permanent inactivity. After the delay, the response can be appropriate rather than absurd.

### 4.6 Resourceful / Находчивый

Chooses useful actions from information actually perceived: preserve an exit, withdraw toward people, call from a safer position or grip an available useful support. Cannot detect unseen players, know every player's plan, invent an exit through geometry or guarantee escape. Comic execution under danger is required by the latest owner direction; it need not always fail or impair an otherwise sensible action. Awareness determines how early danger is noticed, not how competent this character's choice is.

### 4.7 Foolish / Тупорылый

Misinterprets an incident or energetically chooses an absurd solution. Maintain several variations within this one character: mistaken interpretation, ineffective hiding and overconfident bad decisions. An NPC can notice danger quickly and still act foolishly.

Foolish NPCs must be common and contribute materially to the early game's comic identity. They are not all stationary targets. Their decisions can accidentally complicate capture: gripping a movable bulky object, making noise or obstructing a doorway. Do not make every Foolish NPC perform the same gag.

### 4.8 Occasional deceptive actions

Pretending to be dead, false surrender and waiting for an escape opportunity are shared occasional actions. A Fearful NPC uses them for survival; a Resourceful NPC waits for an opening; a Foolish NPC may expose the deception by visibly peeking. Availability depends on physical state and surroundings. Do not add an eighth character to support these acts.

### 4.9 Threat and physical state take priority

Different stimuli share the five conclusions below. Incidental contact is not immediately kidnapping; a strike and a real grab share An attack. Repeated minor interference can change the conclusion when it supplies meaningful new information; exact thresholds remain open. A held NPC cannot ignore the actual grab to finish an unrelated gag.

Hands/feet restraints, head bags, sleep, death and existing capture physics constrain every character. No reaction grants a sleeping/dead NPC agency, tied hands a grip or a character an escape prohibited by their physical state. Do not replace physical capture with a character-specific progress bar.

### 4.10 Five shared conclusions

These are the NPC's interpretation, not five animations, five character types or a required escalation sequence. Character chooses a response from a small shared vocabulary after this interpretation. Do not implement the earlier exhaustive incident list as a separate reaction matrix per incident.

| Conclusion | Meaning | Examples and limits |
|---|---|---|
| Normal / «Всё нормально» | No relevant disturbance or danger; continue current activity | Ordinary passing/parked van, harmless nearby pedestrians. Open cargo alone is not proof of a crime. |
| Being bothered / «Мне мешают» | Minor interference, not yet interpreted as an attack | Incidental bump while running, blocked path, small accidental collision. A look, question icon, step aside or annoyance are the agreed general direction; exact character variants remain open. |
| Something suspicious / «Что-то подозрительное» | A relevant abnormal situation without a perceived ongoing attack or immediate hazard | Discovered motionless corpse; an eyeless NPC running; a restrained person with no captor visible; unexplained sounds from closed cargo. This label does not mean low seriousness or prevent reporting. Character and district determine the response. |
| An attack / «Нападают!» | Perceived violence against oneself or another | Strike, actual grab, dragging a resisting person, deliberate vehicle assault. Striking and grabbing share the conclusion; they still have different physical consequences. |
| Immediate danger / «Непосредственная опасность!» | A perceived urgent hazard that may require immediate protective action | Nearby gunshot, explosion or a van on a collision course. No mandatory slow passage through the other conclusions. Exact action delays and character exceptions remain open. |

A shot nearby is a perceived threat; being hit additionally changes health/condition and may incapacitate or kill. A conclusion cannot override those outcomes. A deliberate vehicle attack and an urgent collision can supply overlapping evidence; exact arbitration is still open, rather than assuming a universal numeric severity order.

Record whether the perceiver is directly affected or a witness, and use the perceived event/source/location where actually known. The same character and conclusion can lead to escape when free or struggling when held. Being tied, held, loaded, asleep or dead is a physical/lifecycle state, not another conclusion.

Someone discovering a body did not thereby witness the attack. Seeing an eyeless escapee does not reveal who removed their eyes or where the captors are. If an ongoing attacker or new urgent hazard is subsequently perceived, a different conclusion can be selected directly. No investigation, new eye-loss mechanic or extra aftermath outcome is introduced by these classification examples.

Once the relevant disturbance ends, return toward routine using a suitable cooldown. Exact durations, repetition memory and thresholds for repeated interference are open. Persistent hot zones, existing witness-report deduplication and completed calls are not reset by this personal return to routine. Forest reporting remains prohibited.

### 4.11 Being bothered — approved response basis

Use the same small shared basis across characters: look toward the interference, step aside, show displeasure. Facial expression, timing and execution supply personality. No seven independent minor-collision systems.

A first accidental on-foot collision, even if it knocks the NPC over, can produce getting up and puzzled attention rather than an immediate attack interpretation. The question icon is an allowed general presentation direction, not the only gag available. Repeated interference can change the interpretation; tolerance varies by character. A Confrontational NPC may visibly warn/show displeasure and then push the harassing player.

Do not apply that initial on-foot leniency universally to vehicle knockdowns. The owner described being knocked down by the van as an attack, then qualified that interpretation by district. Exact district rules, speed/impact distinctions and accidental-versus-deliberate treatment remain open. Physical injury still applies independently.

For Foolish NPCs, the owner specifically wants flight, ridiculous hiding and pretending to be dead available in the comic repertoire. This does not settle that every light brush immediately triggers those stronger acts. Decide their appropriate trigger, timing and repetition controls next; do not invent them as confirmed thresholds.

### 4.12 Compact organisation: interpretation, circumstances, intention and performance

Use the existing five shared conclusions to represent what the NPC understood. Do not duplicate them for every skin or capture stage. Awareness affects noticing/recognition; character affects intention; persona supplies ordinary activity and distinctive expression; the comic baseline governs execution under danger.

For a directly affected victim, describe four capture circumstances:

| Circumstance | Shared behavioural question | Status of action details |
|---|---|---|
| Attacked while free | Escape, resist, call, hide or deceive? | Shared intentions already described; exact availability/weights by character are open. |
| Held or being carried | How does the victim resist or cope without free locomotion? | Struggling, bracing, gripping a support or momentarily going limp are candidates, constrained by existing capture mechanics. Exact repertoire and timing are open. |
| Inside van cargo | What can a conscious occupant do with current doors/restraints? | Existing cargo documentation describes sitting up, knocking and escape opportunities; exact character variations and comic delivery remain open. |
| At the base | How does a very frightened captive react in their actual physical position? | Fear baseline is confirmed. Floor, carry and table require different feasible actions; detailed comic variations remain open. |

These are contextual descriptions, not a mandatory ladder and not four additional personality types. A captive can wake at the base, be released during a carry or be picked up again inside cargo. The implementation must represent actual location and mobility independently enough to handle those overlaps, rather than forcing four exclusive truth values. Actual restraint/incapacitation overrides action feasibility: asleep/dead means no active decision; held cannot freely run; tied hands cannot grip; table straps limit escape.

Proposed decision structure: a meaningful event updates the conclusion/circumstances → keep or select one feasible shared intention → perform it with character timing, persona expression and comic execution. Do not replace this with a full separate script for every combination. A signature act such as filming shares the same action-selection rules; it does not run a competing decision-maker. Exact interruption and priority rules are open.

The ordinary Normal case should usually keep the current walk/idle/activity. Being bothered uses a short shared response. Suspicion allows inspection/withdrawal/reporting variations. An attack and Immediate danger activate suitable protective/capture reactions. More possibilities do not mean every NPC continuously evaluates or performs every option.

To control cost, do not repeatedly analyse the whole map for every thought. Use events/timers, a limited relevant set of nearby objects/actors and simpler distant routines where compatible with existing systems. Do not create an elaborate virtual psychology or full-day life simulation. Necessary movement, collisions and animation continue to update; event-driven decisions do not make those systems free. No claimed FPS improvement is established without actual profiling, including multi-player capture physics and perception/pathfinding costs.

## 5. Comedy with a small shared vocabulary

Use short, readable sequences: ordinary activity → notice → characteristic decision → physical consequence. A sudden change in intent is often the joke. A gag should create a player opportunity, surprise or manageable complication rather than become a repeated cutscene.

Candidate examples (Proposed):

| Situation | Candidate comic beat | Reusable basis |
|---|---|---|
| Fearful/Foolish NPC seeks cover | Chooses a pole much narrower than their body and peeks out | `Hide_Enter`, `Hide_Loop`; needs a suitable nearby object |
| Witness attempts a call | Fumbles phone, recovers and continues reporting | `PoliceCall`; reporting timing remains to be decided |
| NPC attempts deception | Falls rigidly, then peeks to check whether players left | `PlayDead_Fall/Loop/GetUp` |
| NPC tries an escape | Raises hands, waits and suddenly runs | `FakeSurrender_Flee` |
| NPC notices a real threat late | Looks away, double-takes and abruptly flees | `DoubleTake_Flee`; never triggered solely by ordinary van traffic |
| Flight goes badly | Trips or looks backward and hits a wall | `TripFall`, `LookBack_Bonk`; only where geometry permits |
| Slow-reacting captive wakes up to the situation | Quiet carry suddenly becomes struggling | Existing capture reactions; exact presentation to review |
| Foolish captive resists | Clings to a movable object that goes with them | Existing physical grips where supported; no special unverified clip assumed |

The listed clips are described in source documentation. This is not proof that each is connected, networked or suitable in the current build. Existing animations should be reused where appropriate; new animations require an identified gap.

Avoid continuous gag loops and immediate repetition on the same NPC. Keep nearby reactions varied: one conspicuous failed hiding attempt can coexist with ordinary flight and a reporting witness. When no suitable gag is available, use a simple valid reaction. Exact repetition controls and maximum gag duration are open. Comic delivery belongs to almost the whole crowd; a prominent animated gag remains limited so that universal comic style does not become universal simultaneous slapstick.

### 5.1 Intelligent intention, funny forced action

The owner explicitly distinguishes a potentially intelligent decision from the physical performance of that decision. When danger forces an ordinary NPC to act, the player should see comic flight, panic, hiding, falling/recovery or deception, not a switch into a uniformly serious competent crowd. This includes Resourceful characters.

A funny run or exaggerated startled turn can carry the comedy without every NPC falling or stopping for a gag. More conspicuous acts such as a tumble, failed pole hiding or fake death are selected variations, not a mandatory sequence for every actor. Resourceful NPCs can still escape successfully and report promptly while visibly behaving like characters from this game.

This clarification supersedes any implication that the rare intelligent NPCs are exempt from comic execution. Character still controls intention; awareness still controls noticing/recognition. Existing restraint, injury, geometry and district-security constraints remain in force. No weakening or new slapstick contract for Elite guards/police is silently approved here; those responder profiles remain separate.

## 6. Districts, awareness and scope

| District | Confirmed direction | Still open |
|---|---|---|
| Forest | Many Foolish NPCs; intoxicated NPCs can be slow/react minimally, stash couriers more alert. No police report originating here. | Exact character weights and activity profiles |
| Hamlet | Many Foolish NPCs with attentive/resourceful and confrontational exceptions | Exact weights and per-persona profiles |
| Rough | Mixed characters; local responder profile remains governed by police spec | Foolish proportion, group confidence settings |
| International Construction | Mixed characters and group context; nationality does not determine intelligence or character | Proportions, work routines and intervention choices |
| Downtown | Higher average awareness with real variation; few Foolish NPCs, not zero | Exact distribution and appearance weights |
| City Beach | Few Foolish NPCs; ordinary walking/resting remains valid | Awareness distribution and per-persona routines |
| Industrial Port | Existing small population and Downtown police dependency | Character mix and routines |
| Quiet Valley | No ordinary civilian population under the current police decision | Any exceptional occupants or patrols |
| Elite Hill | Dangerous trap; no Foolish NPCs, no routine civilian harvest. Possible guard capture is risky, not guaranteed. | Entry trigger, security response and guard capture limits |

Hot zones alter attention, recognition and response timing while preserving character. They do not convert every NPC into a Resourceful runner. Exact modifiers remain open. No global van recognition in calm areas is introduced.

The newer owner statement that Elite Hill is a trap takes priority over earlier brainstorming about ordinary foolish rich targets and the old Elite district presentation. This file does not silently rewrite the separate security/police spec or invent response timings.

## 7. Numbers, performance, co-op and persistence

All numeric behaviour presets are Proposed until explicitly chosen. This pass approves no percentages, radii or reaction delays. Do not interpret “many” or “few” as an approved exact spawn weight.

Use shared behaviour with parameters; events/timers and proximity-dependent detail should avoid expensive constant deliberation. Animation and environment combinations supply perceived variety. The handoff's approximately 80-entity whole-map crowd is a planning budget, not a demonstrated performance result. Multi-player proximity must consider all active players, not only the host. Exact simulation levels and update budgets remain open.

Server-authoritative FishNet co-op remains the target contract, with one NPC identity and one physical outcome. No local client may independently reroll characters or report duplicate episodes. Exact save fields for character, awareness, response progress and gag repetition are still to be specified. Existing capture/save rules remain in force; this document adds no offline timer progression or host migration.

## 8. What not to do

- Do not make a harmless passing van trigger unmotivated street-wide flight.
- Do not equate higher awareness with universal fleeing, flawless intelligence or a character change.
- Do not make Foolish a rare Easter egg in early districts, nor a majority on the beach by default.
- Do not conflate delayed reaction with foolish decision-making.
- Do not create a separate AI/large animation library for every appearance or a constant full-life simulation.
- Do not require simultaneous gags from every witness, or keep replaying a gag instead of respecting capture state.
- Do not grant police contact where district rules prohibit it; do not import the old crowd alert 0–5 as the target police model.
- Do not add realistic medical procedures, gore or underage capture targets.

## 9. Questions left open

1. Locate the absent v01 and reconcile historical decisions with this partial revision. The handoff also mentions police firing after prolonged noncompliance, differing from the current police spec's aggression-based lethal response; no police change is approved here.
2. Approve per-appearance primary-character probabilities, district awareness distributions and activity tables; reconcile the primary Foolish label with the now-confirmed shared comic execution under danger and rare genuinely smart decision-makers, who also retain that comic execution.
3. Approve the small shared action repertoire for each capture circumstance and conclusion. Then assign character preferences and a few persona-specific expressions; do not enumerate all possible combinations. Specify gag eligibility, especially for the Foolish repertoire. Avoid a separate reaction for every concrete trigger.
4. Define episode boundaries, notice/recognition/action timing, repeated-disturbance escalation, overlapping-conclusion arbitration, return-to-routine timing, reporting completion/interruption and hot-zone modifiers.
5. Approve the gag shortlist, environmental prerequisites, repetition controls and any genuinely missing animations.
6. Define group confidence, witness cooperation and small-group prominent-gag limits.
7. Specify detailed AI relevance ranges, co-op synchronization and persistence for the new behaviour fields; validate performance with an actual crowd.
8. Develop separate district response/security details, lure behaviour, night, relatives and Z events without treating handoff examples as newly approved requirements.
9. Resolve how vehicle knockdowns are interpreted by district; do not generalize on-foot first-collision leniency to all van impacts.

## 10. Acceptance checks

These are future checks, not executed runtime results.

| ID | Check |
|---|---|
| NPC-01 | In a calm district an ordinary van passes/parks without causing unmotivated mass flight. |
| NPC-02 | District awareness samples overlap: lower-awareness Downtown and attentive Hamlet instances remain possible. |
| NPC-03 | Under the same recognized threat, different primary characters produce meaningfully different actions. |
| NPC-04 | Awareness changes notice/recognition without forcing all characters into the same response. |
| NPC-05 | Slow-reacting notices/acts late; Foolish can notice promptly and then choose badly. Players can distinguish the two. |
| NPC-06 | Foolish NPCs are visibly common in Forest/Hamlet, uncommon in Downtown/Beach and absent from Elite. Exact weights await approval. |
| NPC-07 | Fearful NPCs can resist strongly when caught; bravado alone does not supply extra physical strength. |
| NPC-08 | Some supported confrontational instances lose confidence when companions leave; this does not force every instance to surrender. |
| NPC-09 | Curious NPCs do not remain indefinitely indifferent to direct recognized danger. |
| NPC-10 | Resourceful actions use perceived information and real available exits/supports; no omniscient detection occurs. |
| NPC-11 | Gags use suitable geometry and do not override ties, sleep, capture, death or authoritative movement. |
| NPC-12 | One prominent nearby gag can coexist with simpler reactions; repeated exposure does not produce the same synchronized routine. |
| NPC-13 | A Forest incident cannot generate a police report through a character-specific bypass. |
| NPC-14 | Host and clients observe the same character choice and authoritative capture/report outcome. |
| NPC-15 | Profile a representative crowd with players spread across districts; measure behaviour cost before claiming FPS success. |
| NPC-16 | In playtesting, players can recount distinct funny encounters and enjoy repeating captures. Written approval and technical checks alone do not establish that it is funny. |
| NPC-17 | Harmless contact, observed violence and discovered aftermath feed shared conclusions rather than a unique reaction branch for every stimulus. |
| NPC-18 | A nearby shot can cause Immediate danger directly from Normal; no mandatory ladder is traversed. |
| NPC-19 | A strike and a grab both cause An attack, but a held victim cannot run as though physically free. |
| NPC-20 | A discovered corpse or running eyeless NPC can cause Something suspicious; no culprit is inferred without perceived evidence and the classification does not automatically prevent a valid report. |
| NPC-21 | A direct hit applies actual injury/incapacitation independently of interpretation; a dead/asleep NPC does not react. |
| NPC-22 | Ending a minor disturbance allows a return to routine without clearing district heat or undoing completed reporting. Exact timers await approval. |
| NPC-23 | First accidental on-foot knockdown permits getting up/puzzled attention without automatic attack interpretation; actual injury is preserved. |
| NPC-24 | Repeated harassment is less tolerated according to character; a Confrontational push has visible displeasure before it. Exact thresholds remain open. |
| NPC-25 | Foolish NPCs have more than a staring/question-icon routine: suitable flight, ridiculous hiding and fake-death acts are available once their triggers are approved. |
| NPC-26 | Downtown/Beach NPCs retain comic expressions/execution despite fewer dominant Foolish characters; genuinely smart NPCs can make better decisions but must also execute danger reactions comically. |
| NPC-27 | Comic expression does not erase district danger, witness reporting or physical resistance; Elite's approved trap/guard contract remains intact. |
| NPC-28 | Under danger, Resourceful/smart ordinary NPCs retain comic physical execution even when their decision is sensible; simple funny flight can coexist with selected larger gags without requiring every NPC to fall. |
| NPC-29 | The same shared conclusion can drive different feasible acts for a free, held, cargo or base captive; being picked up inside cargo or at the base preserves the correct physical constraints. |
| NPC-30 | Conscious base captives convey strong fear; sleeping/dead occupants do not execute active fear actions. |
| NPC-31 | Persona signatures do not force every gopnik to fight or create a competing behaviour owner; primary character still changes intention. |
| NPC-32 | Normal routines persist without constant new decisions; profiling checks high-level choice frequency and perception/pathfinding/capture costs separately. |

## 11. Verification and changed files

Documentation only. Seven characters, awareness separation, five shared conclusions, approved comic direction, district exceptions and unresolved integrations are recorded. No runtime implementation or playtest result is claimed.

Created in this pass: `docs/specs/NPC_BEHAVIOUR_SPEC_2026-10-21_v06.md`. Revisions v02 through v05 were preserved unchanged.

Unity, Assets, WORK_SYNC, other specs and Git publication were not changed by this pass.
