# VOLUNTEERS ONLY: Capture → Delivery Specification

Revision: v01
Date: 2026-10-18
Source: interview with Fedya (owner), main session, 2026-10-18
Scope: the link between the already-built capture loop and the operations/buyers specs.

## 1. Scope and authority

This spec connects:
- the capture loop: canon §109–148, §151; docs/drafts/NPC_CAPTURE_VAN_COOP_DRAFT.md, NPC_CAPTURE_STAGE1_NOTES.md; already playable offline;
- `OPERATIONS_SPEC_2026-10-15_v01.md` (the table, anesthesia, blood, quality);
- `BUYERS_SPEC_2026-10-15_v02.md` (sales, spoilage, the cooler).

It does NOT redesign capture physics, grips, resistance, police pursuit or the van driving. Those stay as the canon and the current build define them.

**Labels:**
- **Confirmed** — Fedya chose it in the interview.
- **Proposed preset** — a concrete number or behaviour the lead filled in; tune after playtest.

Where this spec conflicts with older drafts or code (`ClinicDropOff`, the single-grade `PatientRecord.Quality`, the 95/75/45 thresholds), this spec wins.

## 2. Confirmed decisions

| # | Topic | Decision |
|---|---|---|
| D1 | Anesthesia before the table | The anesthesia syringe works ANYWHERE: on the ground, in the van, while carried. Same dose rules, overdose risk and stock use as at the table (ops §10). The choice is to haul an awake, struggling NPC or spend anesthesia. |
| D2 | Restraints before the table | Zip ties/tape, a consumable at $10 per use (raised from $5 by Fedya, 2026-10-18), applied separately to the hands and to the feet. A head bag is a separate consumable. Combinations should produce comic situations (§5). |
| D3 | Arrival at the base | The drop-off pad is REMOVED. Players carry the NPC from the van straight to the table and throw/place him on it; he snaps into the table pose (ragdoll carry plus the magnet snap, as in the operations v04 work). |
| D4 | Model identity | NO model swap. The same NPC, same identity, lies on the table. |
| D5 | Van capacity | The stock van holds **3** lying NPCs. Cargo-body upgrades add +1 per level, up to 5. A 4th body cannot be carried in the stock van (§4). |
| D6 | Queue for the table | NPCs wait wherever they are put: in the van or on the base floor. There are no special waiting zones. They wake up over time; to keep them quiet, use anesthesia or restraints, otherwise they try to escape. |
| D7 | Blood outside the base | Blood can be drawn anywhere (ground, van, table). The portion count is stored ON THE NPC and travels with him, so the extraction death risk (ops §11, +10 points per portion) counts blood taken in the field. Drawing is impossible while he struggles: he must be asleep or restrained. A corpse gives no blood (D10). |
| D8 | Condition → organ quality | Condition (0–100) removes grades from ALL organs at extraction time: ≥75 no loss; 50–74 −1; 25–49 −2; <25 −3. The floor is «Убитое»/Damaged. |
| D9 | Intrinsic quality by district and type | The district sets the intrinsic organ-grade distribution (table §6). The NPC type shifts specific organs. Condition loss (D8) applies on top. |
| D10 | Death outside the table | A dead NPC is a corpse. Organs start the ops-spec decay at once: 45 s grace, then −1 grade per 40 s, continuing from Damaged to the unsellable Ruined state. A corpse does not resist; no blood can be drawn from it. Causes: overdose, being hit by the van at speed, a fall from a height, the 3rd blood portion. The head bag alone never kills. |
| D11 | Witnesses at the base | Any NPC or passer-by who sees players carrying a person toward the base: district suspicion +5 per episode, +10 if the carried NPC is screaming. Carrying a bagged body ("someone hauling a sack"): +2. Night lowers detection (§7). A van parked in the garage or right at the door: no witnesses. |
| D12 | Clothes on the table | When the NPC lands on the table, a short cartoon CLOUD («пуф») fully covers him; when it clears he is undressed. His own head, face and body build (thin/fat/muscle) stay; only the clothes become the patient shorts. Hats and glasses drop to the floor next to the table as small trash (cleanup evidence, ops §18). No pocket items or money. |
| D13 | Save and quit | Everything persists: position, condition, blood portions, anesthesia residual and sleep, restraints, bag, timers. Time is frozen while the session is closed: nobody wakes and nothing decays. A client leaving mid-carry: the NPC drops where he was. |
| D14 | First build scope | See §9. The bag combos, death on the road, base witnesses and cargo upgrades come in stage 2, «потом дополнять, если понравится». |

## 3. NPC state that travels with the body

One stable NPC identity (`PatientId`) from first knockdown to the end of the operation. Stored on the NPC and saved:

| Field | Meaning |
|---|---|
| `condition` | 0–100, existing GreyboxNpc.Condition costs (re-stun, fall impact, ankle drag, escape) plus new van costs |
| `bloodPortions` | 0–3 (D7) |
| `anesthesiaResidual`, `sleepRemaining` | the ops §10 model, active anywhere (D1) |
| `handsTied`, `feetTied`, `headBagged` | the restraint state (D2) |
| `alive`, `deathAge` | D10 |
| `districtId`, `npcTypeId` | for intrinsic quality (D9) and the table appearance (D12) |
| `intrinsicGrades[organ]` | rolled ONCE when the NPC is first captured, seeded per identity, so re-rolls cannot be farmed |

The lifecycle stages stay: Available → Captured → Loaded → AtBase → InOperation → Resolved. AtBase now means "inside the base volume, not on the table", replacing the pad hand-over.

## 4. Van

- **Capacity (D5).** Stock is 3 lying NPCs; each cargo-body upgrade level adds +1, up to 5.
- **Proposed preset — the 4th body in the stock van.** The cargo counter shows «тесно, не влезает». While more bodies than capacity are inside, the doors refuse to close and the van refuses to drive off: the engine stalls with a comic cough. Players must take one out.
- **Waking in the van.** Unchanged from the current build: SitUp_Cargo → Cargo_Sit_Idle → Cargo_Knock; he escapes when the door opens. With restraints (§5) the behaviour changes.
- **Proposed preset — rough driving.** A hard impact above ~25 km/h costs every NPC in the bay −3 condition, at most once per 2 s.

## 5. Restraints and head bag

### 5.1 Use
- Zip ties ($10) apply to hands OR feet: a short hold (~1 s) on a downed, asleep, held or restrained NPC. They come off automatically when the matching table strap is closed; or cut them with the scalpel/knife (a short hold).
- Head bag ($10) goes over the head of a downed or held NPC (short hold). It can be pulled off by players at any time. The bag never kills.
- All three are consumables bought at the pharmacy / underground seller.

### 5.2 Behaviour table (proposed presets; Fedya asked for comic interactions)

| State | Behaviour when awake |
|---|---|
| Hands tied | cannot grab the world, doors or players; can still walk/run, hop and scream |
| Feet tied | cannot run; hops in short jumps or crawls; easy to catch |
| Hands + feet tied | wriggles like a caterpillar, rolls; cannot escape the van on his own; carrying him is easier (−30% resistance) |
| Bag only | disoriented: runs in a random direction, bumps into walls and poles (comic bonk), screams muffled (less witness range) |
| Bag + feet tied | tries to pull the bag off, hops blindly, falls over, the bag stays on; repeats |
| Bag + hands tied | runs blindly with his hands behind him, cannot remove the bag |
| Bag + hands + feet | full burrito: rolls around, muffled screams |
| Asleep (any combination) | limp; restraints only matter when he wakes |

- Witness effect: a bagged NPC's screams are muffled (half the witness range); carrying a bagged body counts as «тащат мешок» (D11).

## 6. Organ quality: district, type, condition

1. **Intrinsic grade per organ.** Rolled at first capture from the district table (D9, Fedya approved the table):

   | District | Intrinsic distribution (per organ) |
   |---|---|
   | Rough District, Forest strip (junkies, homeless) | mostly «Сойдёт»/Acceptable; sometimes «Убитое»/Damaged or «Хорошее»/Good |
   | Hamlet, International Construction | mostly «Хорошее»/Good; sometimes «Сойдёт»/Acceptable |
   | Downtown, City Beach | «Хорошее»/Good and «Отличное»/Perfect equally |
   | Elite Hill, Quiet Valley | mostly «Отличное»/Perfect; sometimes «Идеальное»/Perfect+ |
   | Tramduro (VIP) | «Отличное»/Perfect and «Идеальное»/Perfect+ |

   Proposed preset weights:
   - "mostly X, sometimes Y/Z": 70% X, 15% each of Y/Z;
   - "X and Y equally": 50/50;
   - "mostly X, sometimes Y": 75/25.
   The districts not listed (Industrial Port) use the Hamlet row until specified.

2. **Type shifts** (proposed presets, ±1 grade, clamped):
   - junkie, drunk, homeless: liver −1;
   - bodybuilder, fitness coach: kidneys +1, lungs +1;
   - smoker types (smoke-corner, vaper): lungs −1;
   - old grandma/grandpa: all organs −1;
   - every other type has no shift.
3. **Condition loss** (D8) is applied when the organ is extracted, on top of the intrinsic grade and type shift, together with the ops damage events (sloppy cut, yank, etc.).
4. The inspection card shows the final grade. Before extraction, the patient's look gives an approximate hint (ops §12.1).

This replaces the current single `PatientRecord.Quality` from condition with thresholds 95/75/45.

## 7. Witnesses on the way into the base (D11)

- An episode is one continuous carry seen by a given witness. It is counted once per witness per carry: +5, +10 if screaming, +2 if bagged.
- **Proposed preset, night:** 22:00–05:00 halves the witness detection range.
- **Garage/door:** if the van's cargo door is within ~2 m of a base entrance, or inside a garage volume, the carry is not observable.
- These points feed the ops §19 district suspicion and its inspection loop; they do not call police directly.

## 8. Networking and persistence

- The server owns the NPC body. Restraints, bag, injections and blood are requests validated by the server, the same pattern as the operations table.
- The ragdoll carry is server-simulated; clients receive the pose (as in the ops v04 ragdoll).
- Persistence follows D13. Closing the session freezes all timers. Offline time is never charged.
- Capture and delivery do not duplicate a sale reward: the buyer system credits the final sale amount once to the shared team fund, regardless of party size. Any cash penalty triggered by a later police outcome follows `NETWORK_MAP_PLAN_v01.md` §3.9; body/item losses retain their own rules.

## 9. Build stages

**Stage A (first build, D14):**
1. One NPC identity from capture → van → base → table, no model swap, no drop-off pad.
2. The undress cloud on the table (D12); hats and glasses as trash.
3. Anesthesia and blood syringes usable anywhere; the counters persist on the NPC (D1, D7).
4. Zip ties for hands and feet (D2 without the bag), with the hands/feet/both rows of §5.2.
5. Intrinsic quality by district and type plus the condition loss (§6).
6. Stock van capacity 3, hard limit (§4).
7. Save and quit (D13).

**Stage B (if Stage A is liked):**
- the head bag and all its combos;
- death on the road (D10 causes beyond overdose and blood);
- base witnesses (D11);
- cargo-body upgrades to 5;
- rough-driving condition loss.

## 10. Acceptance checks (Stage A)

| ID | Check |
|---|---|
| CD-01 | A captured NPC keeps the same identity from knockdown to the table; no drop-off pad exists; the NPC on the table is the same object or identity with the same head, face and build. |
| CD-02 | Landing on the table plays the cloud; afterwards he wears the patient shorts, with his own head and face; hats/glasses lie on the floor as trash. |
| CD-03 | An injection in the field or van puts him to sleep by the ops rules; the residual and sleep persist into the table; an overdose in the field kills. |
| CD-04 | Two blood portions drawn in the field give the patient bloodPortions = 2 at the table; the first-kidney death chance is 30%. |
| CD-05 | Blood cannot be drawn from an awake unrestrained NPC or from a corpse; it can be drawn while he is asleep or restrained. |
| CD-06 | Hands tied: he cannot grip doors or the world. Feet tied: he cannot run. Both: he cannot leave the van alone. Closing the matching table strap removes the tie. |
| CD-07 | Intrinsic grades follow the district table over ≥1,000 seeded rolls (±5%); type shifts apply; condition 60 removes 1 grade at extraction. |
| CD-08 | A 4th body in the stock van: the doors won't close and the van won't drive; with 3 it works. |
| CD-09 | Quit with NPCs in the van, reload: same positions, sleep, blood, ties; no time has passed. |
| CD-10 | Host + client: a client ties, injects and carries; the server state matches on both. |

## 11. Still open (not decided in the interview)

Lead decisions, 2026-10-18 (from the G33 report; Fedya delegated these):
- **Cutting ties:** any blade the player has cuts them with a short hold — the tier-0 knife (KnifeTier0Astra) or the scalpel. No separate field knife.
- **Cargo-body upgrade:** bought and fitted where the other van upgrades are (the existing engine/brakes/handling upgrade flow). It is installed instantly, like those, with no separate install time.
- **Prices:** G33's proposal stands for the first playtest — level 1 (4 seats) $2,500, level 2 (5 seats) $5,000; ties $10; head bag $10 (Fedya raised both to $10 on 2026-10-18).

Remaining open:
- The exact syringe stock and refills outside the base (ops §24 T-06).
- Industrial Port's distribution row (defaulted to Hamlet).
- The upgrade prices for the cargo body.
- The bag's price and shop.
- Whether the knife/scalpel used to cut ties is a separate field tool.

## 12. Future: player knockout (Fedya, 2026-10-18)

- Teammates can knock out a player; the player then becomes a ragdoll that teammates may carry or move. This is an allowed exception to the rule that objects never push the player.
- A player knocked out by a teammate stays down for LESS time than an NPC hit the same way. Proposed preset: 50% of the NPC stun for the same weapon and zone.

## 13. Corpse removal and disposal (Fedya, 2026-10-18)

- After death, with the straps open, the corpse can be taken off the table by the normal grab and carried as a ragdoll.
- Holding R next to a corpse packs it into a body bag (consumable). The result is one carryable cargo object: easier to carry, no flailing limbs, no snagging on doors. It is NOT disposal.
- Disposal is physical: carry the body to a river, lake or canal disposal point and drop it into the water. It sinks with a splash; the evidence is cleared.
- Witnesses: a bagged body seen being carried: +2 district suspicion; an unbagged corpse: +10. This lands in Stage B with D11.
