# Большая записка для Вадима — 07.10.2026 (от Феди / Work Феди)

Вадим, коротко по-человечески:
- **Теперь твоя часть — только КАРТА.** Всё остальное (внешка и разнообразие NPC, анимации, рэгдолл, ловля и бусик,
  толпа, полиция, звуки, операция, инвентарь, пропсы, новый стиль) делаем мы с Федей.
- Карта — по Фединому «Master v02» (9 районов) + пристань с яхтами у Elite Hill. Сначала 2D-схема Феде на «ок», потом 3D.
- Новый визуальный стиль (без «нейрослопа») уже собран в пробном кадре — Федя ждёт ТВОЙ отзыв по нему, потом карту
  в 3D собираем в этом стиле.
- Ниже — промпт для твоего агента целиком (на английском — так дешевле для Claude). Предыдущая записка
  `VADIM_AGENT_BRIEF_2026-10-05.md` остаётся как история; где они расходятся — права эта.

**Дополнение 11.10.2026 (после твоего пуша bc75706).**
- Твой пуш (TASK-000219…000283) влит без конфликтов: пул NPC по районам (25 типов на BASE v04), гэг-клипы BASE,
  телефон на Tab, `NpcHeldProps`, лесная поляна. Пересечение было одно — `MapGreyboxBuilder.cs` (твои 3 строки про
  телефон), сведено. Наши задачи нумеруются с TASK-000284.
- Твои типы NPC подключим в толпу по районам; на них же встанут наши анимации этапа 9 (45 клипов, тот же скелет
  Mixamo 65). Кто дальше делает новые типы (пляж и т. д.) — договоритесь с Федей.
- Карта: общую 2D-карту (твой MASTER из 9 районов) пришли Феде файлом, когда доделаешь. После вашего общего «ок»
  3D-сборку карты в новом стиле делаем мы.

---

## Prompt for Vadim's agent

You work for Vadim in the VOLUNTEERS ONLY repo (FEDCHER67/Game, branch main, Unity 6000.5.11f1 URP, FishNet, KCC).
Follow WORK_SYNC.md and docs/TEAM_WORKFLOW.md: read Fedya's TASKs you haven't seen (oldest first), mark them
`| SEEN: Вадим`, record each of Vadim's prompts as a new TASK, commit tags [vadim]/[shared]. Fedya's pushes since your last
pull include b0b3a98, b8617de, 7458c34 and the next big push (stage-9 ragdoll, sounds, police GTA model, style v2 …).

### 1. Work split (Fedya, 2026-10-07) — this overrides older notes

- **Vadim: the MAP only.**
- **Fedya's side: everything else** — NPC look and district variety (we reuse the running Sausage Buddies and finish them
  ourselves), NPC animations, the full ragdoll (stage 9), capture/van loading, crowd AI, police, sounds, the operation
  prototype, inventory/organ drop models, Tripo props, the new visual style kit. Don't edit those areas; ask Fedya.

### 2. After you pull

1. Run once, in this order: `OnlyVolunteers/Map/Build Map Look (latest plan)`, then
   `OnlyVolunteers/Map/Build Map Look + Gameplay (latest plan)` (→ `Map_Look_v12_Play`, the scene Fedya tests in), then
   `OnlyVolunteers/Map/Build Rough Greybox (latest plan)`. Generated map meshes are gitignored, so the scenes need these.
2. `OnlyVolunteers > Inventory > Assign Item World Models`; `OnlyVolunteers → Audio → Refill library from Audio folders`.
3. **Expected gaps:** 24 sound files (Mixkit licence: usable in the game, but not redistributable; the repo is public)
   are in `.gitignore` and exist only on Fedya's PC. Without them a few events pick other variants; `police_whistle` and
   `cash_register` have nothing yet (nothing plays them yet). Not an error.
4. Read: `docs/drafts/NPC_CAPTURE_STAGE1_NOTES.md` (capture, keys, tests, every «что важно Вадиму» section),
   `docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md`, `docs/drafts/POLICE_V1_DRAFT.md`, `docs/drafts/CROWD_AI_DRAFT.md`,
   `docs/drafts/SFX_HOOKUP_DRAFT.md`, `docs/art/STYLE_BIBLE_v2.md`, `docs/art/STYLE_TRIAL_v2_NOTES.md`.

### 3. The map — your task

**Target.** Fedya's "Master v02" (06.10.2026): `ArtSource/References/Map/REF_FEDYA_MASTER_v02_map.png` — nine districts
on one coast, north up: 01 Forest (SW, wagon on rails at the coast, ponds), 02 Hamlet (W), 03 Crossing (road hub, river
bridges), 04 Rough District (N, panel blocks around courtyards, football pitch, garages), 05 Downtown (centre, grid blocks
around a square with a fountain), 06 Industrial Port (NE, walled port, pier), 07 Elite Hill (E, oval hill, mansions, pools,
loop road), 08 Quiet Valley (S, big building, pond, road to a small beach), 09 City Beach (S, long pier); mountain ridge
as the north/west world edge, a river from the mountains to the sea, a bay. Its scale bar shows 0–100 m (≈1 px = 1 m in
the PNG Fedya sent; ask him for the original high-res file — small labels and the black "player base" badges are not
readable in the 1280 px copy). **Add the elite marina** from our plan v14 to Elite Hill's coast:
`REF_FEDYA_MASTER_v02_marina.png` (pier with a T end, 3 floating jetties, 10 berths, 3 yachts, 4 motor boats, a breakwater
with a light, a track from the elite beach access).

**Fedya's process rules (keep them):**
- 2D scheme first (PNG for Fedya's OK), 3D only after his OK.
- Later edits change ONLY the named area (district or coordinates); everything else stays byte-identical — add a check
  that diffs geometry against the previous revision outside the declared change regions.
- No fences/walls on district borders (only the elite perimeter, natural edges like rocks/canal/terrain, yard fences,
  the port's own perimeter). Roads ≤ 2 lanes. The van must reach every gameplay point.
- Fedya wants the 3D map built in the NEW style (section 5), not the old "neuro-slop" textures.

**Tools you can reuse (all in the repo):**
- Plan JSON schema, checks and renderer: `ArtSource/References/Map/map_plan_v14.py` (+ v13/v12 it imports). The downstream
  tools read this schema: map dressing (`map_dressing_v12.py`), the look flattener (`Look/flatten_look.py`, extras),
  `MapLookBuilder` (`Build Map Look`), `MapLookGameplay` + `MapGreyboxBuilder.PlaceGameplay` (`Build Map Look + Gameplay`:
  van, player, NPC crowd, pickups, sea return, trip meter, police placement), `MapLookValidator`.
- A digitizing approach we prepared and paused (you may reuse): measure the scale bar → pixel→metre frame; trace each
  district from 2–3× upscaled crops into fragment JSON; assemble into the v14 schema; render an overlay of our scheme on top
  of the master to check the fit; review fidelity and data.
- After the new plan exists, Fedya's side re-bakes police (`OnlyVolunteers/Map/Police/Bake Police Data (latest plan)` —
  stations, patrol loops, routes) and regenerates crowd data (`ArtSource/References/Map/Crowd/crowd_v12.py` → routes, POIs,
  hidden spawns, witness spots). For that, **keep or tell us** the district ids (crowd/police/NPC variety key on them) and
  the gameplay point ids (bases B01–B06, P-points, CLOCK_SQUARE, police station P10, beach entries …): either reuse ids
  or give us an id mapping table.

### 4. Changes Fedya's side made in your files (cumulative since your last pull — please review)

- **KCC (stage 1):** `ExampleCharacterController.cs` capsule radius 0.35 + stances; `KccFirstPersonInput.cs`
  JumpBlocked, ExternalSpeedScale, stoop; new `PlayerStance.cs`.
- **Grab:** `PhysicsGrabber.cs` — point-grab branch for `IGrabPointTarget` (any point under the crosshair), separate
  sideways cap when the profile sets it, grab point from the physics pose, `VehicleInterior` excluded from the acquire ray,
  damping relative to the hand target, and the stage-9 hook (+18 lines marked `// OV stage9`) for the new
  `IGrabPointBodyGroup.cs` (ragdoll parts). Targets without the new interfaces (gurney, scalpel, capsule) run the old code;
  your default GrabPhysicsProfile path is unchanged.
- **Inventory:** `NetworkInventory.cs` (ServerDrop uses `database.WorldPrefabFor` + `ServerSetDefinition`), `WorldItem.cs`
  (SyncVar itemId, client-side world model, host guard), `Assets/DefaultPrefabObjects.asset` (FishNet added
  WorldItem_Generic). **Not tested yet: networked drop/pickup host + client — please test.**
- **ProjectSettings:** TagManager/DynamicsManager — layers 8–13 (NpcBody, NpcSeated, Vehicle, VehicleInterior, …) and the
  collision matrix; `DynamicsManager.m_ImprovedPatchFriction = 1` (the legacy patch friction made lying bodies stick to the
  ground ~1.3–1.5× harder than their materials; only lying bodies and dropped items are affected — rollback = set it back
  to 0). `PlayerSettings.runInBackground` stays false.
- NetworkTest should behave as before by design — please confirm on your side.

### 5. New visual style — Fedya wants your feedback

- Style bible: `docs/art/STYLE_BIBLE_v2.md` (palette of 22 swatches, flat colours, no photo grunge, facade grammar, tree
  species and heights, lighting/post). Kit: `ArtSource/Props/STYLE_KIT_v2` (28 low-poly assets + palette texture,
  Blender build scripts). Trial: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v13_trial.unity` (the whole old town rebuilt in
  the new style) and before/after renders `ArtSource/References/Art/StyleTrial_v2b_BeforeAfter.png`.
  Notes and the roll-out estimate: `docs/art/STYLE_TRIAL_v2_NOTES.md`.
- The new render settings (MSAA, 180 m shadows, SSAO) live only in the trial copy `PC_RPAsset_StyleTrial_v2` until Fedya
  approves. Fedya waits for YOUR opinion on the style before it becomes the map's look — tell him what you'd change.

### 6. Fedya's areas — do not edit (ask Fedya first)

`Assets/OnlyVolunteers/Characters/**` (NPC rig, ragdoll, animations), `Map/Scripts/Greybox*Npc*`, `GreyboxVanCargo`,
`Combat/*`, `Crowd/*`, `Assets/OnlyVolunteers/Police/**`, `Assets/OnlyVolunteers/Audio/**`, `Assets/OnlyVolunteers/Operation/**`,
`Assets/OnlyVolunteers/Inventory/**` (except fixing your own network code), `ArtSource/Props/*`, `ArtSource/Characters/*`,
`ArtSource/Audio/*`, `docs/art/*`. Map builders (`Map/Look/**`, `Map/Editor/Map*Builder*`, map plan scripts) are now yours —
tell Fedya before changing `PlaceGameplay`, because gameplay placement (van, NPCs, police, crowd) depends on it.

### 7. Hook-up notes you may need for the map

- NPC ids and states the crowd/capture use: `GreyboxNpc` (`NpcState`, `StunPhase`), `CrowdActivity` POI tags (bench sit,
  beach lie, shop queue, smoke corner, playground, bus wait, kiosk, bar door, church steps, casino door) — when you place
  benches, bus stops, kiosks, bars etc. on the new map, tag them so the crowd generator can turn them into POIs.
- Police needs: a police station point with a 4-car lot near the town centre, roads wide enough for cars (alleys
  < 4.5 m are excluded from police routes by default), and the team bases' safe circle (60 m) around base doors.
