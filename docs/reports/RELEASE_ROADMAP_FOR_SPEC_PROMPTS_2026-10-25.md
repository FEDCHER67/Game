# VOLUNTEERS ONLY — what is left before release (input for the prompt-writing chat)

**For the prompt chat:** for each block below, write a ready-to-paste prompt for a separate Codex chat that will INTERVIEW Fedya and then write a spec for that block. That interviewing chat must:
- first read the repo files named in the block plus `docs/reports/GAME_STATUS_FOR_CODEX_2026-10-25.md` (current state of the whole game), the canon `docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md` (status labels CONFIRMED / PLANNED / PROPOSED / OPEN / REJECTED — never turn brainstorm into requirements) and `docs/PRODUCT.md`;
- never re-ask what is already decided in those files or listed under "Decided" below;
- ask Fedya questions in batches of 3–5, in Russian, each with numbered options, what each option changes (gameplay / look / work cost) and a recommended option first;
- after the interview, write the spec to `docs/specs/<BLOCK>_SPEC_2026-10-xx_v01.md` (Russian body, numbered sections, decisions appendix, open questions list, acceptance checks), and not implement anything;
- not edit any other file, not commit, not push.
One prompt per block. Blocks can be done in any order; Fedya's suggested order: 10 → 3 → 1 → 2 → 5 → 6 → 7 → 9 → 8 → 4.

Game in one line: 3D first-person co-op (1–4, full solo) slapstick comedy (Unity 6000.5.11f1 URP, FishNet, KCC). Loop: find an adult cartoon NPC (Sausage Buddy style) → stun, tie, load into the van → drive to a base → short cartoon operation (organs) → sell organs → dispose of the body → money/XP → upgrades → new districts. Police and witnesses react. Not gore, not GTA, no realistic medicine.

---

## 1. Core loop: capture to progression
Sub-items: capture Stage B (head bag; up to 3 players holding one NPC; player knockout); witnesses and crowd reaction to a capture; saving inventory/hotbar items (organs in hand); XP, levels and player progression; unlocking new districts during play.
Existing: `docs/specs/CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md` (Stage A done), capture code `Assets/OnlyVolunteers/Capture/`, save `Capture/Scripts/CaptureSave.cs` + `Capture/Core/CaptureRules.cs`, inventory `docs/specs/WORK_INVENTORY*` (find exact name).
Decided: Stage A loop works (stun, tie, load, drive, base 2, table); van always starts at max level in tests (`VanUpgrades.StartAtMax`); objects never push the player.
Open: what gives XP, level curve, what levels unlock, district unlock order and gates, witness rules (overlap with police — keep the police part out).

## 2. Operations
Sub-items: Stage 2 chest (ribs, heart, lungs — spec exists, not built); cure-or-kill outcomes and organ spoilage; time/difficulty balance; tools and consumables (bought, wear out); operating rooms at all 5 bases (only base 2 now).
Existing: operations specs in `docs/specs/` (OPERATIONS_SPEC*, ops stage 2 answers), code `Assets/OnlyVolunteers/Operation/Stage1/`, ops round 4 merged, escape animations fixed 2026-10-25.
Decided (Fedya earlier): stage 1 rules (FishNet, no tape, no payment/levels in stage 1, kidneys cut separately, blood and deaths in stage 1); stage 2: 4 straps, suture, spoilage after opening + a warning.
Open: stage 2 content order, tool shop/consumables, per-base operating room layouts and differences, difficulty curve.

## 3. Economy and sales
Sub-items: buyers (meetings, phone orders, prices, setup/ambush risk); phone (bank, history, contacts, orders — now placeholders); van upgrades for money (now free debug keys 7/8/9); base purchases (shelves, fridges, tools); VIP / special orders (3 VIP models imported: VIP_BEASTMAN, VIP_SPEEDSTER, VIP_BLINDFOLD); whole-game money balance.
Existing: sales spec in `docs/specs/` (SG-D27 = first buyer at base 2), Buyers core `Assets/OnlyVolunteers/Buyers/`, `FirstBuyerCrateV01.cs` (minimal crate at base 2, pays into inventory cash, behind a toggle), cash saved (host only), van upgrades code (find `VanUpgrades`), phone docs (`phone-review` branch docs).
Decided: inventory 6 slots with kit cycling; cooler two-handed; no combo; shelf must be bought; a leaving friend keeps everything; first buyer crate stays as a stand-in.
Open: buyer types and where they meet, price table per organ/quality, upgrade list + prices + where bought, VIP order flow, money sinks.

## 4. Police and heat — VADIM'S AREA
Sub-items: heat per sector, chase, losing the pursuer; stations, patrols, thin/fat cops; Elite FBI gate trap and Elite beach guard patrol; Tramduro army, missiles at the van on the bridge; Hamlet hunter grandpa.
Existing: `docs/specs/POLICE_SUSPICION_SPEC_2026-10-18_v01.md`, old Police v1 in the i10 scene (not in W86), models imported (POLICE_THIN/FAT v02, FBI_AGENT, ARMY_SOLDIER, HAMLET_HUNTER_GRANDPA), map markers (Elite trap 4 s + 2 s, beach patrol loop, Hamlet post at the square).
Rule: the interview prompt for this block must be addressed to VADIM, not Fedya, or only collect Fedya's wishes as notes for Vadim. Do not write police code.

## 5. NPCs and behaviour
Sub-items: new AI per Vadim's NPC behaviour spec draft; stationary placement NPCs (buried on the beach, sand castle, metal detector, pull-up bar, lounger); Quiet Valley population theme; daily schedule (who is where by day/night); NPC sounds/voice lines.
Existing: 48 Sausage Buddy types (38 in district crowds, 10 import-only), `Assets/OnlyVolunteers/Characters/SausageBuddy/Types_v01/`, old crowd AI, `NpcSpot_*` empty markers (14) on the W86 map, Vadim's NPC behaviour spec draft (find in docs/specs), opt_v02 LODs.
Decided: specials import-only for now; BAD_ALTGIRL VIP-only; all NPCs adults.
Open: behaviour states and reactions, which placement roles and where (data missing for several), Valley theme, schedules, voice style.

## 6. Map and world
Sub-items: Vadim's acceptance of W86; relief pack for Vadim (height scheme + 4–6 ground/van shots, v10 §3.3); Quiet Valley theme + the casino building becoming a club + a later Casino Island; final base (lab, base 5) as the most elaborate base; van drive-through of all joins/hills, traps, colliders; day/night and weather.
Existing: `docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md`, `docs/reports/FEDYA_TO_VADIM_W86_2026-10-22.md`, `docs/reports/W86_2026-10-22/` (answers to 22 map questions, decisions), pipeline `Tools/MapV85` → `Assets/OnlyVolunteers/Map/W85Build/Data/v02`, scenes `Map_W85_Build_v02` / `Map_W85_Play_v02`.
Decided: see ANSWERS_FEDYA_2026-10-22.md and TEXTURES_DECISIONS_FEDYA.md; only two skyscrapers; no fences between districts except Elite; Quiet Valley casino sign has no name.
Open: lab interior and features, Valley theme, Casino Island scope, weather set, day/night cycle length.

## 7. Look, sound and performance
Sub-items: light and fog per district, tunnel exit glare; audio (van engine, districts, bases, music, operations); FPS in a real build (only editor numbers now) and quality settings; first-person hands; UI (menus, HUD, hints, control settings).
Existing: art direction docs (`docs/ArtDirection.md`, project memory notes), W86 look code (`W85Look`), FPS numbers in GAME_STATUS, skill `fc-atmosphere-and-audio`.
Decided: One-Armed Robber style; fog +8 %; dim functional lamps; grass distances 60/50/40 m; FP hands later.
Open: audio direction and sources, music style, UI style and menu flow, minimum PC spec and quality presets, FP hands style.

## 8. Co-op (up to 4 players)
Sub-items: network milestones M0–M9 (session split, server van, passengers, networked capture and operation — table fails with 2–3 clients now); shared wallet, client cash and saves; connection: LAN/IP now, Steam later.
Existing: `docs/specs/NETWORK_MAP_PLAN_v01.md` (Q1–Q8 decided), M0 part 1 done (`docs/reports/NETWORK_HARNESS_M0A.md`).
Decided: Q1 server-simulated van; Q2 passengers walk < 6 km/h, ride slots above; Q3 Tugboat LAN/IP now, Steam by M9; Q4 one shared fund; Q5 client-ID save key; Q6 cloud swap keeps PatientId; Q7 sandbox + real-map check per milestone; Q8 session ends when host leaves.
Open: mostly technical — this block may need only a short confirmation interview; the plan exists. Good candidate for GPT implementation briefs instead of a new spec.

## 9. Saves and progress
Sub-items: multiple slots, autosave; saving everything (inventory, XP, upgrades, world state); compatibility of old saves between versions.
Existing: one JSON per slot (`CaptureSaveData` v1), cash added 2026-10-25 (host only), slots listed in GAME_STATUS §11.
Open: slot count, autosave triggers, what world state persists (crowd? corpses? district heat?), version migration policy.

## 10. Build, testing and release
Sub-items: player-build crash "level0 is corrupted" (likely `W76LeaveCountryButton` in `W76MapMarkers.cs`) — top blocker; regular Windows builds with a desktop shortcut for testing; human playtests with real keys (most W86 checks were scripted); tutorial and first minutes; licences (CC0 and third-party notices), Steam page, trailer, achievements.
Existing: `THIRD_PARTY_NOTICES.md`, `docs/Dependencies.md`, build notes from Vadim (WORK_SYNC), skill `fc-performance-and-playtests`.
Open: tutorial content and flow, release scope (what's in 1.0 vs later), store assets, achievement list, playtest plan and who plays.
Note: the crash fix is a technical task, not a spec — the prompt chat can make a direct GPT/Claude fix brief for it instead of an interview.
