# Review: PHONE_SPEC_2026-10-18_v01

Revision: v01 · Date: 2026-10-18 · Reviewer: Claude (cloud, read-only review)
Base branch: `wip/claude-ops-round3`. Nothing except this file was changed.

Reviewed against: SALES_GAMEPLAY_SPEC_2026-10-18_v01 (SG-D55, +Decisions 1–5; sales review K1–K11, esp. K5),
WORK_INVENTORY_SPEC_2026-10-18_v01 (+Decisions 1–6), BUYERS_SPEC_2026-10-15_v02, CAPTURE_DELIVERY_SPEC_2026-10-18_v01,
OPERATIONS_STAGE2_SPEC_2026-10-18_v01 (+Decisions), NETWORK_MAP_PLAN_v01 (+Decisions Q1–Q8),
POLICE_SUSPICION_SPEC_2026-10-18_v01 (Vadim), VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON, OPERATIONS_SPEC_2026-10-15_v01 §14,
code `Assets/OnlyVolunteers/UI/Phone/Scripts/*` (2.7k lines), `Map/Scripts/GreyboxPhone.cs`, `Vehicles/Scripts/*` (`_van.Handbrake`).

Verdict: the spec is unusually complete on rules (69 decisions, 69 checks) and **resolves K5 correctly** (walk with the phone,
no freeze; driver only stopped + handbrake). It is **not implementable as a single job**: it presumes M8/M9 network,
world clock, buyers and save adapters that do not exist yet, omits the police map layer Vadim's spec requires,
references a sales review file that is not in the repo, and leaves the fate of existing Messages/Bank/Camera/Gallery apps unstated.
A small v02 patch (WP0) plus the 5 questions in §6 unblock it.

---

## 1. Коротко для Феди (≤20 строк)

1. Спека телефона хорошая и подробная: все твои 69 ответов внесены, проверок тоже 69.
2. Главный спор из ревью продаж (K5) решён правильно: с телефоном ходишь (WASD), мышь — телефон, ПКМ — оглядеться. Заморозки больше нет.
3. Водитель — только стоя (≤0,1 м/с) и на ручнике. Ручник в коде фургона уже есть.
4. Внешний вид — старый телефон (серебристый, обои с бусиком, сетка 3×6). Новый дизайн не рисуем.
5. Что надо поправить в тексте:
6. — Нет слоя полиции на карте. У Вадима зоны (красная/жёлтая) видны ТОЛЬКО на карте телефона — значит, карта обязана их показывать.
7. — Непонятно, что с текущими приложениями «Сообщения», «Банк», «Камера», «Галерея»: в новом списке их нет.
8. — Штрафы полиции платятся из общего фонда — нужны чеки в «Финансах».
9. — Ссылки на файлы вида C:/Dev/... и на ревью продаж, которого нет в репозитории.
10. — Длина игрового дня: в игре сейчас 24 минуты, в спеке операций 45. Все напоминания телефона от этого зависят.
11. Что мешает начать: нет общего сервера для покупателей/денег/сохранений (это сетевые этапы M8–M9), нет плоской карты-картинки, нет звонков с голосом.
12. Можно начать сразу, не дожидаясь сети: управление (ходьба, ПКМ, водитель/ручник), значок цели в мире, сканер с кольцом, очередь баннеров.
13. Делим работу: данные/правила/сохранение/сервер/тесты и вёрстка по точному брифу — GPT; управление, ощущение, камера, анимация телефона в руке — Claude.
14. Для Вадима — раздел 5: что полиция даёт телефону и что берёт.
15. В конце 5 простых вопросов с рекомендуемыми ответами — можно ответить «да».

---

## 2. Contradictions and proposed lead resolutions

| # | Phone spec says | Conflicts with | Proposed resolution |
|---|---|---|---|
| C1 | §9 overlay table: self, teammates, van, bases, appointment, stash, search area, destination, ping. No police layer. | Police C06/§5/POL-03: caution zones (red core / yellow ring) are shown **only on the team map**, no world circles. | Add overlay row "Police caution zones — server-authored regions from Vadim, team-visible, no numbers" and check PH-70. The flat map renders them as tinted polygons/blobs. |
| C2 | PH-D21 app list: Contacts, Map, Catalogue, Progression, Finances, Market; PH-01 "six approved apps". | Existing code has Messages, Bank (`PhoneWallet`), Camera, Gallery, Market, Map; §15 says camera/gallery "not redesigned". | Messages → folded into Contacts threads; Bank → Finances (shared fund, Network Q4). Keep Camera+Gallery as extra local apps (photos stay local, Network §3.8). Write that into §3; PH-01 counts "six business apps + existing Camera/Gallery". (Q1) |
| C3 | §4.1: phone out → small held item lowered, hotbar inactive; carry/drag requires putting phone away. | Inventory Decision 1 (kit slot cycling) and Decision 2 (cooler two hands) are consistent; but the **Tab phone row in inventory §6 says "Phone unavailable (put the load down first)"** for cooler, while phone §4.1 allows a **banner** during carry. | No real conflict: banner yes, full phone no. Add one line to §4.1 citing inventory §6 so both specs read the same. |
| C4 | §12.3 / §11 / §2.2: game-time reminders (1h15m, 24/6/1 h, power 6/1 h) assume a settled day length; "M8 must settle the mismatch". | Ops §14: one game day = 45 real min; map scenes run `SkyClock22 cycleMinutes 24` (Network §2.8). | Lead: adopt ops 45 min as canonical (economy/power prices were balanced on it); retune SkyClock in M8. Phone uses only WorldClock game time, never Sky directly. (Q2) |
| C5 | S9 link `Working/Reviews/Sales/SALES_SPEC_REVIEW_v01.md`; all links `C:/Dev/Game/...`. | File is not in the repo on this base; absolute Windows paths break on GitHub/cloud. | WP0: relative links; either commit the sales review or quote K1/K2/K5/K10/K11 inline in §2.2. |
| C6 | §4.1 "WASD walks … do not apply MovementLocked". | `PhoneController.cs:148` sets `playerInput.MovementLocked = IsOpen`; RMB = Back (`:170`); hint text "RMB back"; `GreyboxPhone` puts phone away on entering the van, `PhoneController:158` relies on pawn being disabled while driving. | Expected (spec flags K5 as a behaviour change). Implementation must: remove lock, move Back to Backspace/on-screen, RMB = hold-look with click-through guard, keep phone component alive in the van, add driver gate. Not a spec change. |
| C7 | §4.1 "Tab in ordinary on-foot play opens the phone"; §5 passengers have full access. | Network Q2: passengers walk freely below ~6 km/h, fixed riding slots above. | Compatible; state that passenger phone works in both free-walk and riding-slot states, and Tab inside a riding slot opens the phone (riding input must not swallow Tab). |
| C8 | §8.3 scanner: any living NPC with visible face ≤10 m; nothing about noticeability. | Police C07/§6: witnesses perceive "relevant events"; red Downtown residents recognise the crew. | Lead: scanning is **not** a police event (not an offense, emits nothing). Holding a phone up 2.5 s at someone is flavour only. State it so Vadim doesn't invent a "suspicious photographing" hook. (Q3) |
| C9 | §6.2 speakerphone audible to players ≤10 m. | Police witnesses/hearing not addressed; buyer meetings "keep ordinary witness/police rules" (police C33). | Lead: speakerphone is heard by players only, never a witness stimulus. Buyer meetings themselves remain police-visible per C33. |
| C10 | §11 Finances: shared fund, receipts for sales/purchases/power. | Police §8: fines and confiscation money come from the team fund. | Add receipt kind "Police fine/confiscation" (shared, priority 1 banner "existing problem") fed by Vadim's outcome event. Confiscated items are not money and get an informational entry only. |
| C11 | §8.4 identity: stable PersonId → PatientId → organ provenance; twin rule. | Capture spec: PatientId GUIDs minted locally by host (`PatientRegistry`); crowd walkers have **no** stable PersonId today (Network §2.3 crowd offline, ids per spawn). | Dependency, not a rule change: a unique authored PersonId exists only for the bodybuilder (and later streamer). Scanner compares against `order.TargetPersonIds` (original + twin). Generic crowd needs no id. |
| C12 | PH-D25/PH-D48 handoff "any session participant who accepts"; §5 recipient "no blocking work/carry mode". | Inventory: cooler carry forbids phone. | Consistent; enumerate blocking modes once (table mode, in-person bargaining, two-handed carry, body drag, ineligible driver) and reuse that list for answer, handoff accept and bargaining. |

No contradictions found with: sales Decisions 1–5 (violence −3, Stroyka not an outing, twin, driver PiP — upper-left per PH-D63, declined order −1 + returns in a day), buyers v02 progression/respect tiers, capture D11 witness numbers (phone emits none), ops-stage-2 Decisions (no phone content), inventory Decision 5 (leaver keeps all — PH-48), Network Q1/Q4/Q5/Q8 (server van, one fund, PlayerPrefs player id, no migration). Note Q5: "saved per stable player ID" means the PlayerPrefs client id until Steam — personal read state/destinations are lost if a player reinstalls; acceptable for now.

---

## 3. Gaps blocking implementation

| # | Gap | Blocks | Owner of the fix |
|---|---|---|---|
| G1 | No shared business server: buyers, offers, calls, orders, fund, receipts are local placeholders (`PhoneWallet`, scripted threads). Network plan puts economy+phone at M9. | Everything except local input/HUD work (WP1–WP3). | M8/M9 (network track). |
| G2 | No WorldClock service; Sky clock is presentation, day length unsettled (C4). | Reminders, waiting windows, 12+12 cycle, power. | M8 + Q2. |
| G3 | Flat illustrated map asset does not exist (current MapApp = live top-down camera). Need art + world↔map transform + district/label data. | PH-38, PH-39, pings, police layer. | Art (texture) + GPT (data). |
| G4 | Call system absent: no ring/answer/voice clip pipeline, no phone-effect voice, no speakerphone 3D emitter. Voice lines/resources not authored (spec §14). | PH-10…18. | Audio + GPT. |
| G5 | Buyer/meeting/stash/search-area anchors not placed on the map (spec §14). | Booking, map links, stash delivery. | World/map owner. |
| G6 | Scanner target identity: no authored PersonId for the bodybuilder/twin; "visible face" needs a head bone + bag state query. | PH-31…35. | Capture/crowd (GPT data) + Claude (aim/raycast feel). |
| G7 | Driver gate needs replicated `speed` and `Handbrake` of the server-simulated van on the driver's client and validated on the server (Network Q1). `_van.Handbrake` exists locally only. | PH-07, PH-08, PH-15. | Network (GPT). |
| G8 | Persistence schema for per-player phone blocks (read flags, destination, icon layout, private scans) and 200-entry histories; no save of phone today (Network §2.7). | PH-40, 54, 64, 67–69. | GPT (save). |
| G9 | Clue art final variant/caption (PH-P01) unapproved. | PH-30 polish only (not blocking logic). | Fedya/art. |
| G10 | Police map layer contract undefined (C1) and police→phone events (C10, §5). | PH-38 complete, finances receipts. | Vadim + GPT. |
| G11 | "Right third" placement + RMB-look: no brief on phone screen-space size at 16:9/21:9/4:3, cursor confinement, or how the phone sits while walking (bob, lowered item). | WP1 feel. | Claude (WP1). |

---

## 4. Work packages

Owner rule (Fedya): purely technical — data/rules/save/server/tests, UI layout from a precise brief → **GPT** (Astra heavy code, Sol data/text); input/feel/camera/animation → **Claude**.

| WP | Size | Content | Depends on | Owner |
|---|---|---|---|---|
| WP0 | S | Spec v02 patch: C1, C2, C5, C8–C10, C12 text; relative links; inline K-resolutions; PH-70 police layer check. | Q1–Q3 | Sol |
| WP1 | M | Input & feel: remove MovementLocked, WASD with phone, mouse cursor, hold-RMB look with click-through guard, Back→Backspace/on-screen, Tab arbitration (table, riding slot), held-item lowering, phone placement/bob in right third, open/close animation. | — (local, can start now) | **Claude** |
| WP2 | M | Vehicle gate: driver ≤0.1 m/s + handbrake (local first, server-validated later), auto-hide on loss, audio-only call continuation hook, passenger access in both riding states, driver PiP upper-left. | WP1; G7 for co-op | **Claude** (feel) + Astra (server validation) |
| WP3 | M | World destination icon with distance + edge clamp; scanner aiming: central reticle ring 2.5 s, reset rules, 2 s result, reacquire rule, LOS/face/10 m query. | WP1; G6 for real target ids | **Claude** |
| WP4 | M | Notification queue: 3 priorities, preemption/requeue, FIFO, same-type grouping without extension, 7 s; history 200 cap; personal read flags. Pure logic + EditMode tests. Layout from existing lower-right banner. | — (data model local) | Astra |
| WP5 | L | Shared phone read model on server: calls (15 s window, local dismiss, retry/message), ownership/handoff (15 s), Discuss claim, offers 12+12, booking/cancel with previews and K2 window, receipts, idempotent request ids (PH-P02), late-join snapshot. | G1, G2 | Astra |
| WP6 | M | Persistence: per-player phone block (read, destination, icons, private scans), history caps, restart recovery table §12.4, old-save migration entry. Tests PH-47, 62–69. | WP5, G8 | Astra |
| WP7 | M | Flat map app: texture + world↔map transform, wheel zoom/LMB pan, overlays (teammates, van, bases, appointments, stash, search area, destination, pings, **police zones**), deep links. | G3, G5, G10; WP5 for shared overlays | Layout/data: Sol+Astra; pan/zoom feel: Claude |
| WP8 | M | Apps content from precise brief: Contacts/threads, Catalogue, Progression, Finances (+power prepay, police fines), Market with base selection; Home summaries; Camera/Gallery kept. | WP5; Q1 | Astra (code) + Sol (texts RU/EN, buyer message ids) |
| WP9 | M | Call audio: ring, phone-effect voice playback, speakerphone 3D ≤10 m attenuation, foreman gibberish, audio-only continuation when hidden/driving. | G4, WP5 | Audio data: Sol; playback/feel: Claude |
| WP10 | S | Acceptance runner: PlayMode/EditMode tests for PH-01…70 that are automatable; manual checklist for feel items. | WP1–WP9 progressively | Astra |

Critical path: WP0 → (WP1, WP4 now) → WP2/WP3 → [M8/M9: G1, G2, G7, G8] → WP5 → WP6/WP7/WP8/WP9 → WP10.
First playable slice without network: WP1 + WP2 (local) + WP3 + WP4 on solo host with placeholder data.

---

## 5. Police (Vadim) contract lines

**Police → Phone (Vadim provides):**
- P→Ph1 `CautionZones` snapshot + delta: per zone `{zoneId, district, centre/polygon, level: Yellow|Red, version}`; server-authoritative, team-visible; no numeric heat (police C06, §5). Phone map draws only these.
- P→Ph2 `PoliceOutcome` event: `{outcomeId, kind: Fine|Confiscation|Arrest|Inspection, playerIds, amount?, itemKinds?, gameTime}`; idempotent by `outcomeId`. Phone creates one shared receipt (fines from team fund) and one priority-1 banner.
- P→Ph3 `BaseInspection` notice: `{baseId, state: Announced|Knocking|Searching|Ended}` → priority-1/2 banner and base marker status (optional, if Vadim wants players warned remotely; otherwise omit).
- P→Ph4 Optional `PursuitActive` flag per crew (bool) for a Home warning; never positions of officers.

**Phone → Police (Vadim consumes):** nothing gameplay-relevant.
- Ph→P1 Scanning, speakerphone, pings, destinations, calls and bookings emit **no** suspicion/witness events (C8, C9). Buyer meetings stay ordinary world events under police C33 (that is sales/world, not phone).
- Ph→P2 Phone exposes read-only "phone open" state per player if Vadim wants officers/NPC animation to react (cosmetic only).

**Boundary rules:** NPC witness phone calls (police C07, POL-09) are NPC behaviour, not the player phone — no shared code assumption. Police money effects go only through the shared fund transaction API used by sales (no second wallet). Late join receives current zones snapshot; full host restart restores zones from Vadim's save, not the phone's.

---

## 6. Вопросы к Феде (≤5)

1. **Старые приложения.** «Сообщения» и «Банк» убираем (их заменят «Контакты» и «Финансы»), а «Камеру» и «Галерею» оставляем как есть? — *Рекомендую: да.*
2. **Длина игрового дня.** Считаем, что игровой день = 45 реальных минут (как в спеке операций), а не 24 минуты, как сейчас в небе? — *Рекомендую: 45 минут.*
3. **Сканер и полиция.** Наводить телефон на человека 2,5 секунды — это НЕ подозрительно для свидетелей и полиции? — *Рекомендую: не подозрительно.*
4. **Полиция в телефоне.** Штраф или обыск базы — приходит ли уведомление в телефон и чек в «Финансах»? — *Рекомендую: да, чек и красное уведомление; где полицейские — не показываем.*
5. **Порядок работ.** Начинаем с управления (ходьба с телефоном, водитель на ручнике, сканер, значок цели) ещё до сетевой части, на заглушках? — *Рекомендую: да.*
