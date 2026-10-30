# Записка для Вадима (05.10.2026, обновлена 06.10, от Феди / Work Феди)

Вадим, передай текст ниже своему агенту целиком. Если коротко:
- всё готовое наше уже в main (до 7458c34). Ещё не запушено и придёт следующим пушем Феди: схема карты v13, черновик полиции v1 и правки редактора карты;
- что мы поменяли в твоих файлах — список в разделе 2;
- твоя зона (внешний вид NPC, разнообразие по районам, эмоции, анимации) — раздел 3. Мы её не трогаем, у нас там стоит болванка Buddy v04;
- карту сейчас переделывает Федя (v13 — схема на согласовании, Unity только после «ок»), полицию и толпу тоже ведёт Федя — эти файлы не трогай (раздел 5).

---

## Prompt for Vadim's agent

You work for Vadim in the VOLUNTEERS ONLY repo (FEDCHER67/Game, branch main, Unity 6000.5.11f1 URP, FishNet, KCC). Fedya's side pushed a lot. Follow the shared protocol in WORK_SYNC.md and docs/TEAM_WORKFLOW.md:
- read Fedya's TASKs, from the oldest unread one up to TASK-000218;
- mark each `| SEEN: Вадим`;
- each Vadim prompt becomes a new TASK;
- commit tags are [vadim] / [shared].

### 0. UPDATE 2026-10-07 — overrides sections 3 and 5 where they conflict

Fedya re-split the work:
- **The MAP is now Vadim's.** Target: Fedya's "Master v02" map (06.10.2026, nine districts: 01 Forest, 02 Hamlet, 03 Crossing,
  04 Rough District, 05 Downtown, 06 Industrial Port, 07 Elite Hill, 08 Quiet Valley, 09 City Beach; mountain ridge as the
  north/west world edge, a river to the sea, a bay): `ArtSource/References/Map/REF_FEDYA_MASTER_v02_map.png`. Add the elite
  marina with yachts from our v14 to Elite Hill: `REF_FEDYA_MASTER_v02_marina.png`.
  - Fedya's process rules for the map: draw a 2D scheme first and get his OK, then build in 3D; later edits change only the
    named area (keep everything else identical); no fences on district borders (only the elite perimeter and natural edges).
  - Fedya wants the 3D map built with the NEW visual style, not the old "neuro-slop" textures. Fedya's side is finishing the
    style: `docs/art/STYLE_BIBLE_v2.md`, `ArtSource/Props/STYLE_KIT_v2`, trial scene `Scenes/Art/StyleTrial_v2.unity`.
    Use it once Fedya approves it.
  - Tools you can reuse: the plan JSON schema and checks in `ArtSource/References/Map/map_plan_v14.py`; dressing
    (`map_dressing_v12.py`), the look flattener (`Look/flatten_look.py`), `MapLookBuilder` / `MapLookGameplay`
    ("Build Map Look + Gameplay"), the police bake (`OnlyVolunteers/Map/Police/Bake Police Data (latest plan)` re-bakes
    stations, patrol loops and routes for any new plan), the crowd data generator (`ArtSource/References/Map/Crowd/crowd_v12.py`).
- **NPC ANIMATIONS and the FULL RAGDOLL (stage 9) are now Fedya's side.** Vadim does not make the animation set (section 3,
  item 4 is cancelled for Vadim). Fedya's side animates the current Sausage Buddy rig and keeps the animations retargetable to
  your final NPC. The NPC look, face and district variety stay yours unless Fedya says otherwise; keep the hook-up contract
  (section 4) so your NPC plugs into our animator, ragdoll, crowd and capture.

### 1. Pull and rebuild

1. Pull main. It must include b0b3a98, b8617de and 7458c34.
2. Generated map meshes are gitignored. After the pull, run these menu items once, in this order:
   - `OnlyVolunteers/Map/Build Map Look (latest plan)`, which builds Map_Look_v12;
   - `OnlyVolunteers/Map/Build Map Look + Gameplay (latest plan)`, which builds Map_Look_v12_Play, the scene Fedya tests in now;
   - `OnlyVolunteers/Map/Build Rough Greybox (latest plan)`, which builds Map_Greybox_v12.
3. Also run once:
   - `OnlyVolunteers > Inventory > Assign Item World Models`;
   - the SFX library importer, if the Audio/SFX_GEN clips are missing.
4. Read the docs:
   - docs/drafts/NPC_CAPTURE_STAGE1_NOTES.md: capture rules, keys, the scripted test NpcLoadingTest, and every "что важно Вадиму" section;
   - docs/drafts/CROWD_AI_DRAFT.md;
   - docs/drafts/SFX_HOOKUP_DRAFT.md;
   - docs/drafts/ORGAN_DROP_MODELS_DRAFT.md;
   - docs/drafts/OPERATION_PRESENTATION_DRAFT.md.

### 2. Changes Fedya's side made to Vadim's files

Vadim allowed these edits. Review them and tell Fedya if anything conflicts with your plans.

- **KCC:**
  - `ExampleCharacterController.cs`: capsule radius 0.35, stances (stand / stoop / crouch).
  - `KccFirstPersonInput.cs`: JumpBlocked, ExternalSpeedScale, stoop.
  - New `PlayerStance.cs`.
- **Grab:**
  - `PhysicsGrabber.cs`:
    - point-grab branch for `IGrabPointTarget`, so a lying NPC is held at ANY point under the crosshair;
    - a separate sideways force cap, used only when the profile sets it;
    - the grab point taken from the physics pose;
    - layer `VehicleInterior` excluded from the acquire ray.
  - New `IGrabPointTarget.cs`.
  - `GrabPhysicsSolver` usage.
  - Your default GrabPhysicsProfile path behaves as before (NetworkTest unchanged).
- **Inventory:**
  - `NetworkInventory.cs`: ServerDrop takes the prefab via `database.WorldPrefabFor` and calls `ServerSetDefinition`. Server authority is unchanged.
  - `WorldItem.cs`:
    - SyncVar itemId;
    - the client builds the item's world model;
    - host guard `if (!IsServerInitialized) resolved = null;`.
  - `Assets/DefaultPrefabObjects.asset`: FishNet added WorldItem_Generic itself.
  - **Not tested yet: networked drop/pickup in a host + client session. Please test it.**
- **ProjectSettings:**
  - TagManager / DynamicsManager: layers 8–13 (NpcBody, NpcSeated, Vehicle, VehicleInterior, …) and the collision matrix;
  - `runInBackground` stays false.

### 3. Vadim's area (Fedya's side does NOT touch it)

Fedya's decisions of 05.10. Our side keeps the Sausage Buddy v04 placeholder until your NPC is ready.

1. **Final NPC look:** model, face and LOD (NPC_BASE_01 line).
2. **Variety by district**, plus random colours:

   | District | Outfit |
   |---|---|
   | bad district / alley district | tracksuits |
   | old town | hoodies and caps |
   | elite | suits |
   | beach | swimwear |
   | industrial | overalls |

   Separate roles with their own look: police officer, security guard, bartender, the hospital contact C03, buyers.

   Key the variety by the map's district ids. Plan v13 keeps them: `residential` is now the alley district (podvorotni, panel houses
   with shops and bars), `industrial` moved to the NE corner, and there is a new `beach_parking` (beach visitors). The other ids are
   `forest`, `village` (the hamlet), `transition`, `old_town`, `elite`, `fields` (the small valley with the casino) and `beach`.
   Districts with no outfit in the table above use your default look until Fedya decides.
3. **Facial emotions:**
   - fear and anger;
   - "stars" after a hit, X eyes while knocked out, tears;
   - mouth flaps while screaming;
   - gaze follows the player.
4. **Animation set:**
   - walk, run, panic flee, several idles;
   - "struggling while carried";
   - sitting in the cargo bay, knocking on the wall;
   - jumping out of the van when escaping;
   - poses for the crowd activities: bench sit, beach lie, shop queue, smoke corner, playground, bus wait, kiosk, bar door, church steps, casino door.

After your animations land, Fedya's side does the full ragdoll (stage 9) and plugs your finished NPC into the crowd and the capture.

### 4. Hook-up contract (proposal, agree it with Fedya)

What our runtime already exposes, so your NPC can drive its Animator and face from it:
- `GreyboxNpc.State`: `NpcState { Free, Down, CargoSeated, Escaping }`.
- `GreyboxNpc` stun phase: `StunPhase { None, Out, Groggy, Awake }`. Out is the first 50% of the stun (eyes shut, limp); Groggy is the rest (scared, kicks, crawls).
- `NpcIncident { Stunned, Captured }`, which witnesses react to.
- Crowd: `CrowdWalker` mode and `CrowdActivity { BenchSit, BeachLie, ShopQueue, SmokeCorner, Playground, BusWait, Kiosk, BarDoor, ChurchSteps, CasinoDoor, Other }`; `CrowdRole { Walker, Police }`.
- The current face is driven through `GreyboxFace.Set(shape, target)`. Blend-shape weights are applied in LateUpdate, after the Animator.
- The lying body is one Rigidbody capsule (GreyboxNpcBody, 28 kg while stunned) until stage 9.

Suggested: your NPC prefab has an Animator with parameters
- `Speed` (float), `Panic` (bool), `StunPhase` (int), `Carried` (bool), `InCargo` (bool), `Activity` (int, = CrowdActivity);
- triggers `KnockOnWall` and `JumpOut`;

plus a small face component with `SetEmotion(...)`. Our side then maps the states above onto it. Change the names if you prefer, but write them down so both sides use the same contract.

### 5. Do not touch (Fedya's area, work in progress)

- **The map:** ArtSource/References/Map/*, Assets/OnlyVolunteers/Map/** and the Map scenes. Fedya is redesigning it as plan v13.
  The scheme (map_plan_v13.py, MAP_PLAN_R01_v13.*) is local and waits for Fedya's OK; Unity is rebuilt from it only after that.
  - The bad district becomes an alley district: 11 panel houses, 10 podvorotnya arches (2 for the van), narrow lanes, and 13
    trashy businesses mixed in (discounter, ATM shop, beer, pawn shop, shawarma, payday loans, betting, bars, kiosks, 24h shop).
    The den P07 stays.
  - The hamlet and forest follow Fedya's picture: the church in the NW corner, 5 striped fields, a swamp, a lake, a hill with a
    spiral path, and the drinkers' clearing by the wagon B01.
  - The industrial zone moves to the top-right corner, with its outfall into the sea. A beach car park replaces it.
  - There are no fences on district borders. The top of the beach is closed to the van by a dune.
  - All point ids are kept (B01–B06, P-points), so do not hard-code old positions.
- **Fedya's other systems:**
  - the crowd AI;
  - police v1 (docs/drafts/POLICE_V1_DRAFT.md);
  - SFX;
  - the operation prototype;
  - the old-town variants (docs/drafts/OLD_TOWN_VARIANTS_v13.md);
  - the Tripo props (ArtSource/Props/*-ASTRA-*).
- Fedya also has uncommitted local edits in Assets/OnlyVolunteers/Map/** (greybox and look builders, crowd placer, materials).
  Do not edit those files until his next push lands, or you will get merge conflicts.

If you need a change there, ask Fedya first.
