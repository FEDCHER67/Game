# Review: OPERATIONS_STAGE2_SPEC_2026-10-18_v01

Revision: v01 · Date: 2026-10-18 · Reviewer: Claude (cloud, read-only review)
Base branch: `wip/claude-ops-round3`. Nothing except this file was changed.

Reviewed against: OPERATIONS_SPEC_2026-10-15_v01 (§6, §9, §11 Decision, §18–19, §24),
CAPTURE_DELIVERY_SPEC_2026-10-18_v01 (D6, D11, §7, §11–13), SALES_GAMEPLAY_SPEC_2026-10-18_v01 (SG-D37…D46),
WORK_INVENTORY_SPEC_2026-10-18_v01 (+Decisions 1–6), BUYERS_SPEC_2026-10-15_v02, NETWORK_MAP_PLAN_v01 (+Decisions),
`Organs_v05/G38_collisions_manifest_v05.json`, `Patient_v05/ORGANS_LAYOUT_v05.json`,
`TABLE-ASTRA-001/v05/OperationSutured_v05.json`, `docs/reports/PROPS_OPS_STAGE2_CLEANUP_v01.md`.
Lead decisions not yet in specs (L1–L5): **L1** torso strap removed, 4 limb straps; **L2** every operation ends with suturing
(a living patient can't be released unsutured; a dead one may leave unsutured with a skin patch); **L3** a living patient always
stays a living capture target (escapes when free; strap-combination escape animations planned); **L4** internals are hidden off
the table; **L5** objects never push the player.

Verdict: the chest/heart/lungs/cleanup rules are coherent and match sales, buyers, mortality and inventory retention.
It is **not implementable as-is** because of three lead decisions it predates (straps, suturing, hidden internals),
stale v04 art references, a charged-throw number that the inventory Decision superseded, and police ownership that moved to Vadim.
A v02 patch (WP0) fixes all of it without new interviews except the 5 questions in §6.

---

## 1. Коротко для Феди (≤20 строк)

1. Спека по груди хорошая: молоток+остеотом, 6 точек по 2 удара, раскрыть половинки, сердце (2 связки), лёгкие (3 связки), уборка шваброй, мусор в пакет — всё сходится с продажами, покупателями и инвентарём.
2. Но она написана до твоих последних решений. Надо поправить:
3. — В ней ещё 5 ремней и «торс не даёт сбежать». Теперь ремней 4 (руки/ноги), торса нет.
4. — В ней «зашивания нет». Теперь каждая операция заканчивается швом; живого без шва не отпустить, мёртвого можно с «заплаткой».
5. — Нет правила «внутренности не видны вне стола» и что живой после стола снова цель для поимки.
6. — Ссылки на старые модели v04; актуальны v05 (грудная клетка сдвинута, рёбра подрезаны). Числа 4 пары рёбер, 96 коллайдеров, слой SurgicalBone — совпадают.
7. — Сильный бросок: в спеке полный заряд 0,6 с, а по твоему решению 1–1,2 с. Предлагаю: пакет рвётся от 80% заряда, вес не важен.
8. — Полиция и подозрение теперь у Вадима. Мы только отправляем ему факты (пятна, мусор, тела, свидетели +2/+10 и т.д.). Контракт для него — раздел 5.
9. Чего не хватает для работы: правило шва, какие ремни держат, крупные обломки рёбер (модели нет), пакет «открытый/порванный», грязная швабра, мусорный бак на базе, где кнопки новых инструментов на столе.
10. Работу делим: правила/данные/сохранения/сервер/тесты и правки пропсов — GPT; руки, физика, ощущение, камера, анимации людей — Claude.
11. Тебе 5 простых вопросов в конце (раздел 6), у каждого есть рекомендуемый ответ — можно просто сказать «да».

---

## 2. Contradictions and proposed lead resolutions

| # | Stage 2 says | Conflicts with | Proposed resolution |
|---|---|---|---|
| C1 | §4.1 "five individual table straps … remain in force"; inherits ops §6.1 "torso restraint prevents escape". OP-05 tests torso-only. | **L1** (torso removed, 4 limb straps); strap-combination escape animations. | Replace with 4 limb straps. Escape outcome = function of strap combination (matrix in WP9). Proposed: all 4 closed → cannot escape; any open → combination-specific comic escape attempt. Retire OP-05; add OPS2 check per combination. Ops §6.1 needs the same amendment. (Q1) |
| C2 | §1 "Outside … closing/stitching"; inherits ops §9 "There is no closing, stitching, tape or restorative step". | **L2** every operation ends with suturing; art `OperationSutured_v05` (20 stitches, progress 0→1) already exists. | Add a Suture stage to Stage 2 and amend ops §9. Gate: a living patient's straps cannot release him from the table until suture progress = 1 (strap release still allowed for corpses). Dead: either suture, or one short "skin patch" action that hides the opening. Suturing gives no cash/XP, no quality change. (Q2) |
| C3 | §8.1 body removal / §10 never mention a living patient leaving the table; §8.6 "body" category treats patients as bodies. | **L3** living patient always stays a living capture target; capture D6 (escape when free). | Living, sutured, unstrapped patient = ordinary `GreyboxNpc` capture target with the same PatientId, missing-organ flags, blood history, condition. He is not a "body" cleanup source. Waking free → escape behaviour; can be re-captured; never a duplicate identity. |
| C4 | §8.1 lets a corpse be carried off with an open chest/abdomen; §11.2 saves half angles/locks; nothing hides organs, ribcage, vessels. | **L4** internals hidden off the table. | On leaving the table (grab/body bag/escape), server sets `OpeningCover = Sutured|Patch`; clients hide ABDOMEN_OPENING/INTESTINES/VESSELS/CORD_*, organs, RIBCAGE_HALF_L/R, CHEST_VESSELS and show the suture/patch mesh (per OperationSutured_v05 `unity` notes). Organ/chest state stays in data. A living patient cannot leave without the suture (C2), so only corpses use the patch. (Q4: re-admission of a patched corpse.) |
| C5 | P07: "Start with the inventory's proposed 0.6 s maximum"; §8.4 "charge is server-validated from held duration". | Inventory **Decision 6**: full charge ≈1–1.2 s, heavier items lower max, one shared helper, client sends charge 0..1 and server clamps. Inventory §6.x row "Hold G (max 0.6 s)" is superseded too. | Use the shared throw helper. Rupture rule: normalized charge `q ≥ 0.80` (after server clamp), independent of item mass; first impact only. Server additionally rejects `q` inconsistent with the press-to-release interval it observed (anti-cheat), not "computes q from duration". |
| C6 | §1, §3, OPS2-03 cite `Organs_v04/G38_collisions_manifest_v04.json` and the v04 layout. | Current art is **v05**: manifest v05 (BLENDER_V05_PASS, rigid shift −45 mm, posterior trims of ribs 03/04, re-cut UCX), `Patient_v05`, `TABLE-ASTRA-001/v05`. | Re-point all refs to v05. Verified in v05: 4 rib pairs, 10 bone owners (RIB_L/R_01–04, STERNUM_L/R), 96 convex UCX (10 per rib), layer `SurgicalBone`, tags `SurgicalRib`/`SurgicalSternum`, 10 BREAK empties incl. all six mandatory ones, hinge parents RIBCAGE_HALF_L/R, poses closed/open35 (P02 35° is consistent). `ready_for_runtime: false` — Unity cooking not run. |
| C7 | "G42" owns suspicion, police scheduling, odor buildup, complaints, warrants (§9, §8.6, §12 P10, OPS2-40/42). Inherits ops §19 inspection loop and T-08 odor presets. | Police/suspicion now belongs to **Vadim**. | Replace "G42" with "Police (Vadim)" everywhere; Stage 2 emits facts only (§5 of this review). Ops §19 and T-08 become Vadim's inputs, not our implementation. Odor *field* computation moves to Vadim; we supply per-source odor facts. |
| C8 | §9.3 "Existing witness hooks for carrying bodies remain owned by capture/G42" — no numbers. | Capture D11/§7: +5 carried person, +10 screaming, +2 bagged; capture §13: bagged corpse +2, unbagged corpse +10. | Witness *episode detection* stays on our side (it depends on carry/bag state, `CrowdWitness`); we emit one `WitnessEpisode` per witness per carry with the configured points; Vadim applies them to district suspicion. Put the table in Stage 2 §9 so both sides read one source. |
| C9 | §8.4 "use the established player-contact policy"; rupture "against a teammate". | **L5** + `PlayerPushPolicy`: items are never solid for the KCC, so a bag cannot physically collide with a player. | Teammate hit = server swept-sphere/overlap of the bag path against player capsules (not a physics contact); no impulse to the player. Fragments, ribcage halves, mop, bucket, bags, organs: never solid for players (assert in tests). Knockout ragdoll stays the only exception (capture §12). |
| C10 | §4.2/P01 add mallet, osteotome, pouch-from-tray as table tools; §8.2 mop cleans **table** stains. | Inventory: "table keeps its own tool flow (1–4); hotbar hidden in table mode". | Table mode gets contextual slots for physically reachable mallet/osteotome (picked from tray/table, not hotbar). Mop and garbage bag are **outside-table** first-person tools only; table-top stains are cleaned standing beside the table. Write this into P01. |
| C11 | D25 "unused garbage bag occupies one ordinary pocket slot". | Inventory rule 3: stateless consumables stack (pouches, body bags); kit slot cycles helper tools (Decision 1). | Unused bags = stateless stack, allowed in the kit slot like body bags. Open (partly filled) and tied bags = instances, one slot each. |
| C12 | §3 "existing prepared outer opening shared by chest and abdomen". | Layout v05 has separate `INC_CHEST` and `INC_ABDOMEN`; the sutured patch is authored only under `INC_ABDOMEN` (seam 0.317 m, outline = OperationAbdomen_v05). | Confirm in Unity that the v05 opening/patch outline covers the chest area under the ribcage halves. If not, a chest seam/patch variant is a prop-art fix (WP10). Until verified, treat "shared opening" as true for gameplay but blocked for suture visuals. |
| C13 | §10 keeps the 8 s post-extraction awakening rescue; nothing about awakening during suturing. | L2 (suture before release). | Anesthesia/awakening rules continue during suturing. Proposed: awakening during suture with open straps → C1 escape matrix; suture progress persists. No new shock rule. |

No contradictions found with: ops §11 Decision (liver or second kidney = death; first kidney 10% + 10 pp per blood portion), sales SG-D38 (heart/lungs Good+ for the surgeon, no packing for ordinary sale), buyers v02 (packing ≠ cooling, paired lungs one item), inventory Decision 5 (leaver keeps inventory), network Decisions (host authority, no migration).

---

## 3. Gaps blocking implementation

| # | Gap | Blocks | Owner of the fix |
|---|---|---|---|
| G1 | No suture rules: tool (needle/thread item?), input (hold/drag along seam), duration, co-op 2× cap, interruption, saved progress, dead "skin patch" action and its cost. | WP8 | Fedya Q2 → Sol writes into v02 |
| G2 | No 4-strap escape matrix (which combos can escape, what animation, condition cost, witness consequence). | WP9 | Fedya Q1 → Sol |
| G3 | No rule for closing the ribcage on a **living** patient whose chest was opened but no chest organ was taken (halves locked at 35°, 6 bones broken). | WP3, WP8 | Fedya Q3 |
| G4 | Internals-hide rule and re-admission of a patched/opened corpse (is opened state restored on the table?). | WP8, save | Fedya Q4 |
| G5 | Bone fragments: P03 has no count/shape; no fragment meshes in v05 (spec admits it). Needs authored pieces + mapping BREAK group → fragment ids. | WP2, WP3 | GPT prop art (WP10) |
| G6 | Garbage bag art has only EmptyFlat and FullTied: no open/partly-filled held state, no ruptured remnant. Mop has no dirty state; dirt must be readable. | WP6, WP7 | GPT prop art (WP10) |
| G7 | Disposal container: no prop/placement at the base; water-disposal points bound to body drop only. | WP7 | GPT data/scene (WP10) |
| G8 | Item definitions missing: mallet, osteotome, mop, bucket, garbage bag (stack/open/tied), waste kinds incl. hats/glasses/socks/bone fragments; ItemDatabase IDs and kit-slot membership. | all | Sol (WP1) |
| G9 | Table-mode input mapping for new tools (P01 is a placeholder) and how "one click = one strike" coexists with physical mallet swing. | WP3 | Claude (WP3) |
| G10 | Stain persistence: surface anchoring for table vs floor (table can be moved? fixed?), decal pooling limits, save schema. | WP5 | Astra |
| G11 | Witness detection ownership (ours vs Vadim's crowd code) and the odor field owner — needs Vadim's ack (§5). | WP12 | Vadim |
| G12 | Escaped living patient: does it emit anything to police (he saw the clinic)? Not in any spec. | WP9, §5 | Fedya Q5 |

---

## 4. Work packages

Owner rule (Fedya): purely technical (rules, state, data, save, server validation, tests, prop-art fixes like debris pieces) → **GPT** (Astra = heavy technical code, Sol = data/text); input, physics, feel, camera, human animation → **Claude**.

| WP | Content | Size | Owner | Depends on |
|---|---|---|---|---|
| WP0 | Spec v02 patch: C1–C13 resolutions, v05 refs, Fedya's answers to Q1–Q5, Vadim contract (§5) copied in; amend ops §6.1/§9 | S | GPT Sol | Fedya Q1–Q5 |
| WP1 | Item/waste definitions, ItemDatabase IDs, kit-slot membership, tuning asset with P01–P11 + suture/strap presets | S | GPT Sol | WP0 |
| WP2 | Chest state machine (server): BREAK hit counters with strike dedupe, seated-tool claims, half lock, gating, fragment ids, idempotent detach for heart/lungs, death serialization, save/late-join, NUnit + net scenario | L | GPT Astra | WP1, existing ops connection/extraction code |
| WP3 | Bone-tool feel: osteotome seating, mallet swing → one strike, SurgicalBone-only queries, hinge pull + resistance + lock cue, fragment pick/move, table camera framing for chest | M | Claude | WP2 interfaces, WP10 fragments |
| WP4 | Heart/lungs: 2 + 3 connections authoring on v05 sockets, joint pull/interference feel; state reuse from existing connection system | M | Claude (feel) + Astra (S, state) | WP2 |
| WP5 | Source registry: stains/waste/corpse/bag sources, creation receipts, revisions, Source* events, snapshot/restore, legacy-save receipt migration, tests | M–L | GPT Astra | WP1 |
| WP6 | Mop/bucket: aim+hold cleaning feel, dirt accrual/rinse, 2× cap feedback (state in WP5) | M | Claude | WP5, WP10 dirty mop |
| WP7 | Garbage bag: collect/tie/dispose ledger transactions (Astra, M); charged throw via shared helper, rupture sweep vs players, victim-only 2 s screen overlay (Claude, S–M) | M | Astra + Claude | WP5, inventory throw helper, WP10 |
| WP8 | Suture & release: rules/gates/save (Astra, M); suture interaction + stitch progress visuals, skin patch, hide-internals swap (Claude, M) | M | Astra + Claude | Q2–Q4, C12 verification |
| WP9 | 4-strap escape: combination matrix rules (Astra, S); escape animations per combination (Claude, L — human animation) | L | Astra + Claude | Q1, Q5 |
| WP10 | Prop art fixes: bone fragments (few large, per BREAK group), garbage bag open + ruptured remnant, dirty mop state, disposal container, chest seam/patch if C12 fails | M | GPT | WP0 |
| WP11 | Base status (stains/waste/body), aimed-object labels, bag occupancy text; RU strings | S | GPT Sol | WP5 |
| WP12 | Police adapter for Vadim: event emitter + query API + contract tests | S | GPT Astra | WP5, Vadim ack |
| WP13 | OPS2-01…50 automation (Astra, M); human playtest OPS2-50 + feel pass (Claude + Fedya) | M | Astra + Claude | all |

Critical path: Q1–Q5 → WP0 → WP1 → WP2/WP5 (parallel) → WP3/WP4/WP6/WP7/WP8 → WP13. WP10 runs in parallel from WP0.

---

## 5. Contract for Vadim (police) — TASK

**TASK for Vadim: consume operation/cleanup facts from the clinic side.** Our side never changes suspicion, never schedules police and never decides discovery. You own: district suspicion 0–100 and its persistence/decay, odor field buildup/fade, complaints/phone messages, visits, refusal/warrant (ops §19 is your input, not ours), search discovery, confiscation, arrest outcome.

### 5.1 Delivery rules
- Emitted **on the server/host only**, after the authoritative state change commits (same tick), never from client replicas or presentation callbacks.
- Every event: `eventId` (GUID, stable across reload), `sourceId`, `sourceRevision` (monotonic per source), `worldTime` (active-world seconds, frozen while the world is closed), `baseId`, `districtId`.
- At-least-once delivery; **you deduplicate by `eventId`, and ignore `sourceRevision ≤ last seen`.**
- No per-frame events. Persistent stains emit only on create/change/remove.
- On load and on late join of the host world we send `SourcesRestored` (full snapshot) — **state, not new crimes**; never add suspicion from it.

### 5.2 Events we emit

| Event | When | Fields (beyond the common ones) |
|---|---|---|
| `SourceCreated` | stain/waste/fragment/organ/corpse/bag first appears | `kind` ∈ {JamStain, OpDisposable, BoneFragment, Clothing, Organ, Corpse, GarbageBag, BodyBag}, `size` (S/M/L for stains), `patientId?`, `organType?`, `pose`, `surface` (Floor/Table/Other), `containerId?`, `holderPlayerId?`, `exposed` (bool), `odorFactor` (0..1, see 5.3), `creationReason` (Baseline, IncisionError, DirectCut, AbruptPull, OrganDrop, CorpseDrip, VialEmptied, Extraction, Death, Rupture) |
| `SourceChanged` | moved, contained/uncontained, packed, bagged/tied, cleaning progress step (≥25% buckets only), holder changed, player left/rejoined | changed fields only + `exposed`, `odorFactor`, `containedBy?`, `remainingWork01?`, `available` (false while its holder is offline) |
| `SourceRemoved` | stain fully cleaned; bag/body disposed (container or water); organ sold | `reason` ∈ {Cleaned, DisposedContainer, DisposedWater, Sold}, `containedIds[]` retired with it |
| `SourcesRestored` | world load, host start | `sources[]` = full current facts |
| `WitnessEpisode` | once per witness per continuous carry seen toward the base (capture D11/§7/§13) | `witnessId`, `carryId`, `cargo` ∈ {LivingNpc, LivingScreaming, BodyBag, Corpse}, `points` = 5 / 10 / **2** / **10**, `night` (bool; detection range already halved on our side), `pose` |
| `PatientReleasedAlive` | sutured living patient leaves the table/base free | `patientId`, `missingOrgans[]`, `pose` (consequence = Fedya Q5) |
| `PatientEscaped` | living patient escapes from table/van/floor (strap combo or untied) | `patientId`, `fromTable` (bool), `sutured` (bool), `pose` |
| `OperationNoise` | accepted bone strike, miss, patient scream on table | `noise` ∈ {BoneStrike, BoneMiss, Scream}, `pose`, `loudness01` |

Points are configurable and sent as values so the clinic and police read one number; **you** decide whether to apply them (e.g. your night/visit rules).

### 5.3 Odor facts (you compute the field)
- `odorFactor`: exposed corpse 1.0, exposed organ 0.5, jam stain S/M/L 0.1/0.2/0.3, loose waste 0.1, bone fragment 0.1; inside a tied garbage bag or body bag ×**0.5** (P10). Bagging never yields 0. Fridge/cooler: no reduction (preservation ≠ odor immunity) — confirm.
- After `SourceRemoved` the odor must fade gradually on your side; we never send a "base clean" reward.

### 5.4 Persistence split
- **Ours (host save):** all sources, revisions, receipts, retired ids, bag contents, absent players' inventory (inventory Decision 5).
- **Yours (host save):** suspicion per district, odor integrators, complaint episodes, last seen `eventId`/revision per source, inspection state.
- Offline time is never charged (both sides).

### 5.5 Query API we provide (no omniscience)
- `QuerySources(volume | containerId)` → physical sources inside a searched room/container only (for your search discovery).
- `TryConfiscate(sourceIds[], reason)` → atomic ledger removal on our side; returns what was actually removed. You never delete items directly.

### 5.6 What we expect back from you
1. Ack of the event list/fields above, or your changes, before we build WP12.
2. Decision: do you run witness detection (crowd code), or do we keep emitting `WitnessEpisode`? (We propose: we keep it.)
3. Your consumption of `PatientEscaped`/`PatientReleasedAlive` (after Fedya Q5).
4. Events back to us, server-side: `InspectionStarted/Ended` (we may lock table UI? — propose: no lock), `ConfiscationApplied`, `ArrestApplied(playerId)`, so our ledger/UI stay consistent.
5. A test fixture: feed our recorded event stream twice + a `SourcesRestored`, suspicion must be identical (idempotency).

---

## 6. Вопросы к Феде (только ты можешь ответить)

1. **Ремни.** Торса больше нет, ремни только на руках и ногах. Пациент не может сбежать, только если застёгнуты все 4? — *Рекомендую: да, все 4; если открыт хоть один — смешная попытка побега, своя анимация под каждую комбинацию.*
2. **Шов.** Чем и как шьём? — *Рекомендую: игла с ниткой из набора (как шприцы), зажать кнопку и вести вдоль шва ~5 с, вдвоём быстрее (максимум ×2), бросить можно — прогресс сохраняется. Заплатка для мёртвого — одно действие ~1 с.*
3. **Грудь у живого.** Если грудь вскрыли, но сердце/лёгкие не брали, а пациент жив — что дальше? — *Рекомендую: руками сложить половинки обратно и зашить; сломанные рёбра без штрафа, живой уходит как обычно.*
4. **Мёртвый с заплаткой.** Если тело с заплаткой снова положить на стол — можно достать оставшиеся органы? — *Рекомендую: да, один надрез снимает заплатку, всё внутри как было, порча продолжается.*
5. **Отпущенный или сбежавший живой.** Он рассказывает полиции? — *Рекомендую: да, один раз как кричащий свидетель (+10 подозрения), а точные правила — у Вадима.*

---

## 7. Checks performed
- Read Stage 2 spec fully; targeted reads of all listed specs (sections cited above).
- v05 manifest parsed: 10 owners, 10 BREAK empties, 96 UCX, layer SurgicalBone, hinge parents, `ready_for_runtime: false`.
- `ORGANS_LAYOUT_v05`: INC_CHEST/INC_ABDOMEN/INC_HEART/INC_LUNG_L/R and SOCKET_HEART/LUNG_L/R present.
- `OperationSutured_v05.json`: abdomen-only marker, 20 stitches, progress-driven reveal; hide list for internals.
- G34 props: mallet v03 + osteotome, mop/bucket (single state), garbage bag EmptyFlat/FullTied only, stain kit.
- NOT RUN: Unity, gameplay, network, save — this is a document review.
