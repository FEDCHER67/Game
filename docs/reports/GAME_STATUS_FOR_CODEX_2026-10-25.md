# VOLUNTEERS ONLY: game status for a Codex/GPT agent (2026-10-25)

This document lets you work without the chat history. It covers what exists today, per aspect, with paths. It was written read-only from the repo, the docs, WORK_SYNC.md (TASK-000830 to TASK-000910) and git, on 2026-10-25.

Verification tags used below:
- **[PLAY-SCRIPT]**: an agent checked it in Unity play mode by script or MCP, without real key presses.
- **[TESTS]**: EditMode/PlayMode tests.
- **[HUMAN]**: Fedya or Vadim played it with real keys.
- **[UNVERIFIED]**: written or reported, but nobody ran it.

Almost nothing in the current W86 build is [HUMAN]. Treat "works" as "works in scripted checks" unless a line says otherwise.

Paths are repo-relative to `C:\Dev\Game`. `Assets/OV/` means `Assets/OnlyVolunteers/`.

---

## 0. The game in five lines

- 3D first-person co-op (1–4 players, full solo) comedy, Unity 6000.5.11f1, URP 17.5, FishNet 4.7.3 + Tugboat, KCC (Kinematic Character Controller), Input System 1.20, Git LFS.
- Loop (canon): find an adult cartoon NPC ("Sausage Buddy" style) → stun, tie and physically load it into the van → drive to a base → short cartoon operation (organs) → sell the organs → dispose of the body → money/XP → upgrades → new districts. Police and witnesses react.
- Tone: systemic slapstick, not gore, not a GTA clone, no realistic medicine. Adults only.
- Product docs: `docs/PRODUCT.md`: the short working spec (RU, 2026-10-11); `docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md`: the full canon (RU, 3,888 lines, updated 2026-10-15). Its status labels are CONFIRMED / PLANNED / PROPOSED / OPEN / REJECTED; Do not turn brainstorm text into requirements.
- **Stale docs:** `docs/CURRENT_STATE.md` (2026-10-11), `docs/Progress.md` and `docs/NextAction.md` (2026-10-13, v17 ClinicLoop) are out of date. Use this file, WORK_SYNC.md and `docs/reports/W86_2026-10-22/` instead.

---

## 1. Project and workflow

**Status: DONE (process in place).**

### Repo, branches, LFS

- Repo `C:\Dev\Game`, remote `https://github.com/FEDCHER67/Game.git`, one shared branch `main`. Git LFS is on: FBX, .blend, PNG, scenes and other binaries go through LFS (`.gitattributes`).
- HEAD = `origin/main` = `5694c185`, Vadim's merge of TASK-000900..000909 into Fedya's W86 and opt_v02 commits.
- Fedya's last commits: `b13aede2`: NPC opt_v02 LODs, logged as TASK-000910 in WORK_SYNC; `2a086c3d`: Map W86; `3f1ccdfc`: ops round 4 merge.
- Other branches are history:
  - local: `map-v76-local`, `wip/claude-ops-round3`, `cloud/*`, `codex/*`.
  - Remote branches not merged into main:
    - `claude/fp-hands-v01`: FP hands, code only, no art, not integrated (decision D6);
    - `claude/phone-review` and `claude/ops2-review`: docs only;
    - `cloud/*` art kits: already built into main by other paths, or superseded;
    - `codex/*` from late September;
    - `wip/claude-ops-round3`.
  - Do not merge any of them without a brief.
- Ignored or partly ignored: `Working/Reviews/`: review sheets, logs and FPS notes, local only. A few files were force-added; Library, Temp, Logs; Some `Generated` folders of older map builders. `Map/W85Build/Generated/` is tracked, about 10.6k files; Rule: when a live scene depends on an ignored Generated asset, force-add it (`git add -f`, through LFS).

### Uncommitted work on disk (2026-10-25, verify with `git status --short`)

This is Fedya's W86 finishing pass by Claude, documented in `docs/reports/W86_2026-10-22/FINISH_CHARACTERS_ANIM_CASH_RU.md`. It is NOT committed and must not be lost or reverted.

**Code:**
- `Capture/Core/CaptureRules.cs`: `CaptureSaveData.hasCash`, `cash`.
- `Capture/Scripts/CaptureSave.cs`: saves and restores the host's NetworkInventory cash.
- `Capture/Scripts/CaptureDirector.cs`: binds the hotbar cash source.
- `Inventory/Runtime/InventoryHud.cs`: `CashSource`.
- `UI/Phone/Scripts/BankApp.cs` and `Map/Scripts/GreyboxPhone.cs`: `PhoneWallet.Pocket` shows NetworkInventory cash.
- `Operation/Stage1/Scripts/OperationPresentation.cs`: a woken patient who cannot start an escape clip now Struggles. Before this, a strapped patient woke up and lay motionless.
- `Operation/Stage1/Scripts/NetworkOperationTable.cs`: the escape side uses `player.MotorPosition`, not the NetworkPlayer root.
- `Operation/Stage1/Editor/OperationStage1EscapeClips.cs`: escape-clip import copies Preserve Hierarchy from `Op_Dead_v01`. Without it the curve paths lost `Buddy_Rig_Mixamo65/`, the model blew up 100× and no bone moved.

**Assets:**
- 14 `.fbx.meta` in `Characters/SausageBuddy/Patient/Animations/Escape_v01/` (Preserve Hierarchy).
- 6 new v01b clips there with .meta: `Esc_SwingOff_L`, `Esc_HopRun_L`, `Esc_Slump_Edge_L/R`, `Esc_Stumble_Off_L/R`.
- `Patient_Operation.controller`: +6 states, 28 escape states in total.
- `Operation/Stage1/Data/OperationStage1_v02.asset`: `escapeMissingClips` = 0.

**ArtSource (untracked):**
- 6 `.blend` and 6 `.fbx` v01b in `ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Escape_v01/`.
- `ArtSource/Textures/ambientCG_2026-10-21/{Facade002,Facade006,Facade009,Logs001,PaintedPlaster006,PaintedPlaster017,WoodSiding008}/`.
- `docs/reports/W86_2026-10-22/FINISH_CHARACTERS_ANIM_CASH_RU.md`.

**Checks recorded for this pass:**
- Compile clean. EditMode Capture + Inventory 50/50, Operation 70/70 [TESTS].
- No console errors after the play sessions.
- Escape chain, side choice and cash save/load: [PLAY-SCRIPT].
- Clips not watched by a human. Not tested in a built .exe.

### Who owns what

Fedya and Vadim are two developers, each with his own Claude "Work" chat.
- **Fedya (`C:\Dev\Game`):** the 3D map build in Unity (W76/W85/W86); capture, operations, integration and play scenes; textures and props; NPC optimisation and import; character animations (Claude only, never GPT); the economy loop and the network plan.
- **Vadim (his PC, `C:\Users\chern_0eqkb03\Desktop\GAME`, his own Desktop\Map folder):** 2D world map and district plans (`ArtSource/References/Map/World_vNN/`, latest **v86** with Downtown v37); Sausage Buddy NPC type models (`ArtSource/Characters/SAUSAGE_BUDDY_01/buddy_pool_*.py`); the NPC behaviour spec; **police and suspicion (G42): Vadim's area. Do not edit police code or specs unless asked.**
- Vadim also builds Windows .exe games locally. His build/FPS/shortcut scripts are local only and not in git (`Assets/Editor/VadimBuilds.cs`, `VadimSceneLauncher.cs`, `Assets/VadimLocal`).

### WORK_SYNC protocol (`WORK_SYNC.md`, `docs/TEAM_WORKFLOW.md`)

- WORK_SYNC.md is the only handoff log. It is in Russian and the newest entry is on top.
- One working prompt = one `TASK-NNNNNN` with a global number. The last one is **TASK-000910** (Fedya).
- Each entry records the developer, the verbatim prompt, the result, the files, the checks and the status. The reader marks the other developer's tasks `SEEN`.
- Strictly sequential: one Work changes the repo at a time. "One Work at a time" also means one GPT chat holds Unity at a time.
- **Codex/GPT workers never edit WORK_SYNC.md.** The lead does.

### Hooks and tools on Fedya's PC (`~/.claude/settings.json`, PreToolUse)

- `~/.claude/hooks/bash_guard.py`:
  - blocks bulk staging (`git add -A`, `.`, `-u`, `--all`). Always stage explicit paths.
  - On `git push` it runs the push preflight (`missing_deps.py`): every GUID dependency of the live scenes listed in `C:\Users\Zeyo-ne\.ai-bridge\live_scenes.txt` must be tracked in git.
  - The live scenes are i10 capture_delivery, W76_Build_v01, Operation_Net_Stage1_v02, NetworkTest, W85_Build_v01/v02 and W85_Play_v01/v02.
  - A block is the rule working: fix the cause. The bypass file `ALLOW_PUSH_ONCE` needs Fedya's explicit OK.
- `unity_playtest_guard.py` blocks Unity MCP while `C:\Users\Zeyo-ne\.ai-bridge\PLAYTEST_ON` exists (Fedya is playing). While he plays: no Unity calls, no compiles, no writes into Assets.
- **Unity lock:** `powershell -NoProfile -File C:\Users\Zeyo-ne\.ai-bridge\unity_lock.ps1 -Cmd acquire|refresh|release|status -Id <chat id, e.g. G45>`.
  - Refresh at least every 20 min. The lock goes stale after 40 min.
  - Release when your Unity step is done; add `-Done` when you need Unity no more.
  - Only one editor of the project at a time.
- Unity runs elevated. At startup it shows "Administrator Privileges Detected": press **Ignore Warning**, never "Restart as Standard User".

### Scene and data version rules

- Never overwrite a deliverable. A new revision gets a new numbered name: models `_vNN`, data `Data/v02`, scenes `_v02`, docs `_v02`.
- Old scenes stay byte-identical: `Map_W85_*_v01`, i10 and W76.
- Map edits are local: change only the named district or coordinates. Everything else stays byte-for-byte.
- Scene changes go into the builder or integrator code (`W85PlayIntegrator.Make`), not by hand, so they survive rebuilds.
- Preserve `.meta` GUIDs. Check dependencies before moving or deleting.

---

## 2. How to launch and play now

**Status: PARTIAL.** It runs; the loop is closed up to money. Not [HUMAN]-tested with real keys in W86.

1. Unity 6000.5.11f1. Open `Assets/OV/Scenes/Map/Map_W85_Play_v02.unity` (it is first in Build Settings; second is `NetworkTest.unity`). Press Play.
2. You spawn beside the van on base 2 (grandpa's hut, Hamlet). The map runs as a solo FishNet host.
   - Caveat: Fedya's current editor save may put the player on the Downtown square. Press **F3** or **F1** to get back to base 2.
3. Editor save slot: `capture_stageA_editor_W85_v02.json` (set by `W85EditorSaveSlot`). Builds use `capture_stageA_v01.json`. Both live in `persistentDataPath/OnlyVolunteers/` (LocalLow).

**F1–F8 teleports** (`GreyboxTripMeter` on the van; spots rewritten for W85 by `Map/W85Build/Editor/W85Teleports.cs`):

| Key | Spot |
|---|---|
| F1 | Grandpa's yard (P02) |
| F2 | B01 forest wagon |
| F3 | B02 hut |
| F4 | B03 Rough garage |
| F5 | B04 Downtown yard |
| F6 | Downtown square |
| F7 | B05 Quiet Valley lab |
| F8 | Construction fuel station |

**Known controls** (from code and playtest guides; check them yourself):

| Context | Controls |
|---|---|
| On foot | WASD, Shift sprint, Ctrl crouch, Space jump |
| Capture | **Q** hit/stun; **LMB** grab/drag bodies; **E** use/enter the van/table |
| Hotbar | **1–6** slots; slot **2** = field kit (tie / anaesthesia / blood) |
| Items | **G** drop/throw: hold to charge, release throws. **E** picks up |
| Corpse | **R** (hold) packs it into a body bag |
| Phone | **Tab** |
| Save | **K** save; **Shift+K** new game |
| Van | E at the door; exit at ≤12 km/h; **C** chase/cockpit camera; **R** reset; **7/8/9** debug upgrade cycle (kept by Fedya's decision D5) |
| Debug | **F10** capsule body for the next knockdown; **F11** crowd overlay; **F12** evening |
| Operation | tool slots 1–5 (hands, anaesthesia, blood, scalpel [4], suture [5]); wheel = close/wide top camera; Esc leaves |

**Play guides (RU, "do → see"):**
- `docs/reports/CAPTURE_DELIVERY_PLAYTEST_W85_RU.md`: W85 v01. Its F1–F8 warning is obsolete now.
- `CAPTURE_DELIVERY_PLAYTEST_v05_RU.md`: ops round 4.
- `OPERATIONS_STAGE1_v02_HOWTO_RU.md`.

**Other scenes:**
- `Map_W85_Build_v02.unity`: map without the player.
- `Map_Look_v19_Play_i10_capture_delivery.unity`: the old v19 map, the only one with Police v1.
- `Scenes/Dev/Operation_Net_Stage1_v02.unity`: the dev operation scene.
- `NetworkTest.unity`: the co-op test scene.
- `Map_Look_v17_Play` + `Clinic/`: the superseded v17 ClinicLoop. Do not revive it.

---

## 3. Map W86

**Status: DONE as a build; PARTIAL as content.** Built, textured, propped. Vadim's review is pending, and some audit items are unclear.

### Pipeline

1. **2D source:** Vadim's world map v85 + district plans (Downtown v37 drawn into W86) → `ArtSource/References/Map/World_v85/`, `World_v86/`.
2. **Data:** `Tools/MapV85/*.py` (s01_classify … s07_splat, `s04z_owner_decisions.py` = Fedya's answers, `DISTRICT_SCHEMA.md`) → `Assets/OV/Map/W85Build/Data/v02/`.
   - Contents: heightmap RAW16 2049, holes, steppe backdrop 1025, `roads_v85.json`, `border_v85.json`, and `districts/*_v85.json` for 10 districts.
   - The integrator picks the newest `Data/v*` automatically.
3. **Builder:** `Assets/OV/Map/W85Build/Editor/`.
   - Core: `W85Builder`, `W85Look`, `W85Rollout`.
   - W86 additions: `W86Relief`, `W86Districts`, `W86Facades`, `W86Models` (+ `W86Data/MODELS_M1.json`), `W86Decals`, `W86TexRollout`, `W86V07`, `W86ViewPocket`, `W86Extras`.
   - Output → `Map/W85Build/Generated/v02/` and `Scenes/Map/Map_W85_Build_v02.unity`. The last final build ran on 2026-10-22 in 454 s.
4. **Menus:**
   - `OnlyVolunteers → Map → W86 Build (data v02)`: the whole map, several minutes.
   - `OnlyVolunteers → Map → W86 Make Play scene (v02)` (`W85PlayIntegrator.MakeV02`): the play scene with capture, ops, crowds and type templates, the buyer crate, teleports and the save slot.
   - `OnlyVolunteers → Map → W86 Ground-fit check (open map scene)`: nothing floating or sunk.
   - `OnlyVolunteers → Map → Texture Test v07 → Build TextureTest_Houses_v07`.
   - The old v01 menus are under `OnlyVolunteers/Map/W85 Build/…`.
5. **Runtime:** `Map/W85Build/Runtime/`:
   - `W85GrassRenderer` + `W85GrassVisibility.compute`;
   - `W85CrowdCull`;
   - `W85LampShadowBudget`: the nearest 8 lamps cast shadows;
   - `W85FarView`: the steppe layer, far clip 4000;
   - `W86DecalHook`;
   - `W86DistrictFogNorthView.shader`;
   - `W85EditorSaveSlot`.

### What W86 changed versus W85 (FEDYA_TO_VADIM_W86_2026-10-22.md)

- **Relief:** the river "cake" wall became sloped banks; a steppe with hill ridges beyond the map edge, so the sea is no longer visible from Rough; Hamlet hills; a mountain lake with a 17 m waterfall, and a waterfall to the sea; a VIEW B spur road to a viewpoint at 46 m. Scheme: `docs/reports/W86_2026-10-22/relief_scheme_v86.jpg`.
- The audit (`AUDIT.md` §5, 15 ranked items: walls, Elite cut, road join steps, steep banks, Construction "cake", stretched textures on steep faces) predates W86. **Which items W86 fully fixed is not recorded per item [UNVERIFIED].**
- **Rough:** replanned from Vadim's 8 marks (`rough_v52_marked_by_vadim.webp`); houses squeezed 2.5 %; edge strips as in v52; the north edge is the state fence with a KPP (no district fence).
- **Downtown v37** (from Vadim's image): 3–6 floors, offices only 05/06, 8 gaps between houses; VIEW C closed by gates and trimmed hedges; two six-sided twisted twin towers (T4, 130 m) on the "Water axis" square.
- **Fedya's 22 answers** (`ANSWERS_FEDYA_2026-10-22.md`): fuel station at Construction built; base 1 = a real 24×3.2 m wagon; lab (base 5) rotated 90°, loading pad 14 m south; Elite gate trap 4 s + 2 s (marker only, no mechanic); Elite beach catchable with a guard patrol (waypoints only); FBI building 24×12 m; Valley casino sign with NO text; grandpa post on the Hamlet square; base 4 yard 12 m; tunnel exit as a T-join.
- **Textures and models:** textures everywhere from the v07 variants Fedya picked, plus agent picks by his taste (T1/T2); 203 low-poly props replace placeholder boxes: `Assets/OV/Art/Props/MapW86_v01`, sources `ArtSource/Props/MAP_W86_v01`; decals: markings, cracks, manholes, stains, oil, shore foam; chain-link fence; Decision docs: `FEDYA_TASTE_AND_RULES.md`, `PICKS_T1.md`, `PICKS_T2.md`, `TEXTURES_DECISIONS_FEDYA.md`; Online textures are CC0 only from ambientCG: `ArtSource/Textures/ambientCG_2026-10-22/SOURCES.md` (and `_2026-10-21`).

### Districts (order along the road: Forest → Hamlet → east past Construction → Downtown; Rough near the Hamlet)

| # | District | Plan source | State in W86 |
|---|---|---|---|
| 01 | Forest | v02 §8.1 | Finnish pine forest, dense = undrivable; base 1 wagon in a rail dead end; swamp and lake. Crowd: junkie, stasher |
| 02 | Hamlet | v07 + layout v06, HAMLET_SPEC | 24 houses (H5 izba look: log, brick plinth, dark metal roof, carved trims) + grandpa's hut = **base 2** (operating shed, paint table, van pad, buyer crate). Church, square with a table, pond. No street lamps. Known W85 issue: 8 izbas smaller than their plots sit 0.5–1.3 m deep (W86 status unknown) |
| 03 | Construction | v11 | One fence with a ~19 m gate, two unfinished buildings + crane, cabins, van workshop (entry through the main gate), fuel station. Look C2 |
| 04 | Rough | v52 + Vadim marks | Soviet panel KH2 (R2c), 3D balconies, grey and foggy, dry yellow-brown grass, garages, football box, arches, state fence + KPP, base 3 garage |
| 05 | Downtown | v37 | American restrained (D4: plaster/brick, palette dark blue-grey/brick/olive/ochre), offices O1 travertine grid, DS1 80 % / DS2+DS3 20 %, square DC3, twin towers, base 4 yard, police buildings 10/11 (no police). Streets 12 m + 2×5 m sidewalks |
| 06 | Port | v03 | Containers P1 multicolour, fence/vehicles/buildings P3, road through to the Tramduro bridge |
| 07 | Elite Hill | v12 | ~44 m hill, 180° stone road to the east gate, FBI building + 4 villas, look E2. No crowd, gate trap not built |
| 08 | Quiet Valley | v02 §8.8 | Base 5 lab (rotated), casino building without a sign text, low wooden fence. Look Q3. No crowd ("own theme later") |
| 09 | City beach | v06, BEACH_SPEC | White sand #F7F2E0, 2 lifeguard towers, pier, palms, loungers. Beach placements are not spawned |
| 10 | Tramduro island | 06 FINAL | Bridge from the port with a KPP, military south, palace north. No crowd, no systems |

### Open map questions and next steps

- Vadim has not reviewed W86 yet.
  - His TASK-000909 (in progress): pull W86 and build it as a Windows game with a desktop shortcut.
  - His Rough replan prompt lives only on his desktop and in `Working/Reviews/MapW86_Inputs_2026-10-22/`: arches of one size for the van, extra houses, higher garages, steppe at the KPP.
- **Build crash (likely still open):** in player builds, W85 crashed with "level0 is corrupted". Cause: the class `W76LeaveCountryButton` lives in `Assets/OV/Map/W76Build/Runtime/W76MapMarkers.cs`, which does not match its file name. Fix: move it to its own `W76LeaveCountryButton.cs` (Vadim TASK-000900). Verified 2026-10-25: the class is still in `W76MapMarkers.cs`.
- Downtown square gold statue = the TRAMDURO model cast in gold with a crown (Fedya 22.10). Not made.
- Process asks from Vadim: van drive-through of every road join and screenshots of the junctions (handoff v10 §6, §14).
- Main map handoff, highest priority first:
  1. `docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md`;
  2. district specs (`docs/specs/*_SPEC_*`, `DOWNTOWN_LEGEND_v26.md`, `ROUGH_LEGEND_v45.md`);
  3. handoff v02;
  4. the map image.
- Vadim's wishes checklist: `docs/reports/W86_2026-10-22/WISHES.md` (what he does NOT want: §N).

---

## 4. Look and performance

**Status: PARTIAL.** The look is approved per district by Fedya. Vadim has not accepted it. FPS is good in the editor; builds are not measured.

### Art direction

- One-Armed Robber (OAR) look: clean painted colours, soft volume, readable shapes, no photo grime, no acid colours. Real 3D depth beats painted detail.
- No brands, logos or Russian brand-like signage.
- Docs: `docs/ArtDirection.md` (consolidated 2026-10-13), `docs/art/STYLE_BIBLE_v2.md`, `docs/reports/W86_2026-10-22/FEDYA_TASTE_AND_RULES.md` (the picking compass).

### Light and atmosphere

- The i10 stack is carried over to W85/W86 by `W85Look`: sun, G18g district weather, fog and aerial haze, district light volumes, PostFX_v17; `DistrictFog19V05` mist banks moved to Rough and Forest.
- Fog +8 % map-wide (Fedya 21.10, `W85Look.FogBoost = 1.08`).
- City lamps: dimmer, functional flicker.
- Per-district mood: Hamlet: warmest and brightest; Rough: grey and foggy; Downtown: American restrained; Construction: bright and sunny; Elite: calm Mediterranean; Valley: mysterious green; Beach: Miami white sand.
- Day/night: F12 evening (Sky folder; reports `SKY_DAYNIGHT_v04.md`, `SKY_DAYNIGHT_INTEGRATION_i03_v01.md`). Not re-checked in W86 [UNVERIFIED].

### Grass

- `W85GrassRenderer`: a fork of MangoButtermilch ChunkedGrassRenderer (MIT, `ThirdParty/GrassInstancer_MB`).
- Draw distance 60/50/40 m by quality, density falloff, CPU frustum/distance/terrain-horizon chunk culling.
- PlayerPrefs `ov_grass_quality` High/Med/Low/Off.

### Trees

- COZY-style trees and forest kits from the i0x integrations (`docs/reports/TREES_*`, `LEAFY_TREES_*`, `OAKS_PINES_i09_v01.md`, `WIND_TREES_i06_v01.md`).

### LODs and culling

- NPC crowd: 3-level LODGroup (section 5); far NPCs (>190 m) are not animated (`W85CrowdCull`).
- 203 W86 props: one URP Lit material per family/colour, SRP-Batcher-friendly, 1024 px textures.

### FPS (editor play mode only)

| Where | FPS | Note |
|---|---|---|
| W85: base 2 | ~120 | |
| W85: Downtown | ~170 | |
| W86 build pass: base 2 | 155 | `Working/Reviews/MapW86_Build_2026-10-22/fps.txt` |
| W86 build pass: Downtown boulevard looking west | 114 | same file |
| W86 build pass: Rough | 184 | same file |
| Downtown square (F6), before opt_v02 LODs | 205 | |
| Downtown square (F6), after opt_v02 LODs | 205 | measured by script; whether the same method was used before is unknown |

- No FPS in a built player.

---

## 5. Characters and NPCs

**Status: PARTIAL.** 48 types modelled and imported; 38 walk in the crowd; behaviour is the old Crowd AI.

### Sausage Buddy system

- **Source:** `ArtSource/Characters/SAUSAGE_BUDDY_01/`: builder `build_buddy.py`, `buddy_body/clothes/rig/anim/gags/wear/geo/render.py`; type registry `buddy_types.py` (POOLS); district pools `buddy_pool_*.py` (bad, bad2, bad3, beach, construction, forces, forest, hamlet, oldtown 1–3, prom, transit 1–2, vip); Types are built by Blender 5.2 into `Types/<ID>/`.
- **Rig and clips:** Mixamo 65-bone skeleton `Buddy_Rig_Mixamo65`, shared by all types; 13 shared clips live in the .blend; the FBX carries Idle only; Unity uses the shared `SausageBuddy_Greybox.controller` with Buddy A's avatar.
- **Optimisation:**
  - `Types_opt_v01/build_types_opt_v01.py`: hidden faces removed, garments decimated within 1.5 mm, crowd budget 15k.
  - `Types_opt_v02/build_types_opt_v02.py`: LOD0 is −2.5 % (only the hidden eye interiors are cut; lossless on renders); LOD1 ≈ 50 % from 15 m; LOD2 ≈ 25 % from 40 m; culled after 150 m.
  - Tables: `Types_opt_v02/README.md`; status: `UNITY_STATUS.md`.
- **Unity:** `Assets/OV/Characters/SausageBuddy/Types_v01/`, with folders `Models`, `Prefabs/SausageBuddy_<ID>.prefab`, `Data/Presets`, `Data/NpcSpawnTables_v01.asset`.
- **Importer:** `Editor/NpcTypesImportV01.cs`. Menus:
  - `Tools → Only Volunteers → Characters → NPC Types v01: Import, Presets, Spawn Tables`
  - `… NPC Types v01: Import W86 additions (Vadim 976100c7)`
  - `… NPC Types v01: Use Optimized Meshes + crowd LODs (opt_v02)`: run on all 48, 48 OK.
- **LODGroup:** fixed size 1.8 m, switches at 15 m / 40 m, cull at 150 m. Fade off. It assumes camera FOV 75 and lodBias 2.
- **Name-lookup fixes for LODs:** `GreyboxFace` (face shape keys on all LODs), `NpcHeldProps` (drops LOD0 and hides LOD1/2), `CaptureTableBridge.SpawnTrash` (LOD0 only), `CaptureUndress` (all LODs).

### 48 types; spawn tables in `NpcTypesImportV01.WriteTables`

| District | Types |
|---|---|
| forest | FOREST_OD_JUNKIE, FOREST_STASHER |
| hamlet | HAMLET_GRANNY, HAMLET_SHEPHERD, HAMLET_BOXERS_GRANDPA, HAMLET_BODYBUILDER, HAMLET_MUZHIK (new) |
| construction | CONSTR_INDIAN v08, CONSTR_UZBEK v05, CONSTR_MEXICAN v05, CONSTR_AFROAMERICAN, CONSTR_ARAB |
| rough | BAD_GOPNIK, BAD_DRUNK, BAD_RAPPER, BAD_HUSTLER, BAD_GIRL, BAD_BOMZH, BAD_BOMZHIHA, BAD_VAPER |
| downtown | OLD_RAPPER, OLD_STREAMER, OLD_STUDENT, OLD_OFFICE, OLD_FITNESS, OLD_COURIER, OLD_BUSINESSMAN, OLD_KAREN, OLD_POPKING (new) |
| port | PROM_FOREMAN, PROM_SAILOR |
| beach | BEACH_CORN, BEACH_SUNBURN, BEACH_LIFEGUARD, BEACH_NUDIST |
| elite, quiet_valley, tramduro | none (empty tables) |

- The placements table also holds BEACH_BURIED, BEACH_CASTLE and BEACH_DETECTOR, plus BEACH_SUNBURN on a lounger and the bodybuilder at a pull-up bar. Their templates exist, so 38 templates are in the scene. **No spawner reads `Placements`.**
- **Import-only (10)**, with prefab and preset but no spawns, because their systems do not exist yet: HAMLET_HUNTER_GRANDPA (the Hamlet responder; group "forces"); POLICE_THIN, POLICE_FAT (American cop pair); FBI_AGENT (Elite); ARMY_SOLDIER (Tramduro garrison); TRAMDURO (finale); VIP_BEASTMAN, VIP_SPEEDSTER, VIP_BLINDFOLD (Elite VIPs); BAD_ALTGIRL (Elite VIP only, removed from Rough by Vadim TASK-000883).
- Vadim's 14 new or updated models (commit `976100c7`) are all imported.
- Verified [PLAY-SCRIPT] 2026-10-25: 50–51 crowd NPCs of 28 types at start, all with LODGroup; faces drive LOD1/2; hand props on all LODs, one physical drop; the undressed escaped patient is in trunks on all LODs.
- Minor (also before LODs): an escaped patient holds his hand prop again.

### Crowd AI (old, working)

- `Assets/OV/Map/Scripts/Crowd/` (`CrowdDirector`, `CrowdWalker`, `CrowdWitness`), `GreyboxNpc`, ragdoll `Characters/Npc/NpcRagdoll` (11 bodies).
- Walk, flee, stun, witness alerts with "phone" fallback. `CrowdDirector.TypeTable.TakeFor()` draws types per district.
- Drafts: `docs/drafts/CROWD_AI_DRAFT.md`, `docs/NPC.md`.

### NpcSpot markers (placeholders, nothing visible)

- 14 empty `NpcSpot_*` transforms in the play scene: Hamlet: 7 gathering points on the square and the grandpa post; fuel station: cashier, pump driver, smoker, waiting driver; Elite beach: 2 guards.
- `Patrol_*` waypoint routes for the Elite beach guard and Tramduro.
- No AI and no types assigned.
- Missing data: points for the buried/castle/detector types; a Hamlet pull-up bar; types for the fuel station and square points; an Elite guard type.
- **Open decision for Fedya:** show some of them standing idle (INTEGRATION_PLAN C2)?

### Behaviour spec

- `docs/specs/NPC_BEHAVIOUR_SPEC_2026-10-21_v01.md`: Vadim, **DRAFT**, RU.
- Layer A, daily life: activities with weights and per-POI limits; dumb comic skits every 30–60 s in view.
- Layer B, district reactions: Downtown and the beach call the police; Hamlet calls the hunter grandpa (misses 90–95 %); in Rough the gopniks fight; the construction crew fights and the police cover their eyes; in the forest nobody reacts.
- Witnesses call on the spot.
- **Nothing of it is implemented.**

---

## 6. Player, van, capture and delivery

**Status: DONE (Stage A), [PLAY-SCRIPT] + [TESTS]**. W86 has not been played with real keys.

### Player

- KCC first-person (`Assets/KinematicCharacterController` + `Assets/OV/Player`); map pawn `Map/Scripts/GreyboxKccPawn`; interaction `GreyboxInteractor` (Q/E).
- Rule: objects, organs and ragdolls never push or lift the player. This is enforced by the `ColliderPolicy` hook in KCC `ExampleCharacterController.cs`. Only vehicles may push.

### Capture

- `Assets/OV/Capture/` (Core rules + Scripts): `CaptureDirector`, `CaptureFieldKit` (hotbar slot 2: tie, anaesthesia, blood), `CaptureVanCapacity` (3 bodies), `CaptureTableBridge`, `CaptureCloud` ("Poof! Undressed and on the table"), `CaptureUndress`, `CaptureCorpseDisposal`, `CaptureBodyBag`, `CaptureSave`, `CaptureHud`, plus scenario drivers.
- One PatientId and one state travel from the field through the van to the table (CAPTURE_DELIVERY spec §3).

### Van

- `Assets/OV/Vehicles/Van` (`VanController` WheelCollider 1800 kg, `VanDoor`, `VanCameraRig`, `VanDriveInput`, `VanUpgrades`) and `VanCargoSpace`.
- **Rule: the van always starts at max level** (`VanUpgrades.StartAtMax = true`; Vadim 2026-10-16). Tune the max level; never ship or test a weaker stock van.

### Flow

Q stun → kit (tie/inject) → LMB drag → load through the side/rear door → drive → base 2 pad → carry to the table in the shed → cloud swap → E at the table.

### Disposal

- Dead patient off the table: hold R to bag it (bag stock is saved).
- A bag or a corpse thrown into the river, lake or canal sinks, and evidence is cleared. A pond, swamp or pool does not sink it.
- Witness hooks record +2 (bagged) / +10 (unbagged). Suspicion itself is Vadim's G42, not implemented.

### Spec and reports

- Spec: `docs/specs/CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md`. Stage A is done; Stage B adds the head bag.
- Report: `docs/reports/CAPTURE_DELIVERY_STAGE_A.md` (G35): EditMode 240/240, full loop pass, NPC loading 19/19.
- **Ragdoll regression FAIL 32/34:** r7 pair-rear timing (known) and r25 wall-push. Still open.

### Not built

- Head bag (Stage B).
- Up to 3 players holding one NPC on the network (M4).
- Player knockout (future, spec §12).

---

## 7. Operations

**Status: PARTIAL.** Stage 1 is done through round 4 plus the 2026-10-25 fixes. Stage 2 (chest) is spec only.

### Code

- `Assets/OV/Operation/Stage1/` (Core / Scripts / Editor / Data / Tests / PlayTests). Main classes: `NetworkOperationTable`: server-owned; `OperationPresentation`, `OperationAbdomen`, `OperationSutureV05`, `OperationPatientRagdoll`, `OperatingTableStraps`, `OperationHud`; `OperationEscape` (core): the clip chain as data.
- Tuning asset: `Data/OperationStage1_v02.asset`.
- The old non-canon kidney mini-game in `Operation/Scripts` + `Clinic/` is superseded.

### What works

- **Patient:** straps (5), anaesthesia, blood draw, one big belly incision.
- **Organs:** kidneys: snip 2 cords below, pull with the hands; liver: guided loop cut, then pull.
- **Rules and states:** quality rules (sloppy −1, direct cut −2, yank −1); death rolls: first kidney 10 %, second 20 %, liver or both kidneys fatal; spoilage.
- **Round 4** (`OPS_ROUND4_CLOUD_HANDOFF.md`): reopen a sutured or patched belly with one scalpel stroke; smooth zipper suture; escape on clips (Escape_v01) at 1.5× speed; the escaped patient stays in trunks, also after save/load.
- **Anatomy v05:** closed back, lower organs, intestines, sutured state; heart, lungs and vessels modelled; 4 rib pairs + 96 `SurgicalBone` colliders; Integration menus: `OnlyVolunteers/Operation/Integrate anatomy v05 …`, `Build suture tool`, `Bake Player-Safe Query Meshes (v01)`, `Integrate escape clips v01`.
- **Organs as items:** `OperationPhysicalItem : IPhysicalInventoryItem` in NetworkInventory (kidney 0.15 m, liver 0.22 m). Charged throw (G) through `ThrowCharge`.
- **Network:** stage 1 v04 passed two processes over localhost: host 37 PASS / client 22 PASS (`OPERATIONS_STAGE1_v04.md`); 2–3 clients: FAIL (`NETWORK_HARNESS_M0A.md`).
- **Tests:** Operation EditMode 70/70 (2026-10-25); earlier the whole project ran 232/232 after the round 4 merge.

### Escape animations

- Contract and clips: `ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Escape_v01/` (20 core clips + 6 v01b, built by bpy scripts with `_authoring.json` validation).
- Chain: UnbuckleArm → SitUp → UnbuckleLegs → SwingOff_{side} → HopRun_{side} → hand-off to a field NPC at RUN0/RUN0_L.
- Interrupts: anaesthesia → Slump; re-strap while sitting → Slump_Sit; Slump_Edge; Stumble_Off falls face down.
- The side is away from the nearest player.
- Verified [PLAY-SCRIPT]: both sides, Slump_Edge_R, Stumble_Off_L, both arms strapped → Struggle.
- **Not verified:** watched by eye (Fedya's acceptance); the "open belly, no straps" struggle case; Stumble falling clear of the table legs.
- Known limits: Q on the table patient is not wired; tug loops are imported but unused; late joiners start the current clip at its saved time, with no drift correction.

### Specs

- `docs/specs/OPERATIONS_SPEC_2026-10-15_v01.md`: the full target; much of it is not built (containers, electricity, staff, XP, inspection).
- `OPERATIONS_STAGE2_SPEC_2026-10-18_v01.md` (G40), **not implemented**: chest opened with a hammer and osteotome; heart and lungs (always fatal); mess, mop and bucket cleanup.
- Fedya's decisions (15.10): FishNet; no tape, payment or levels in stage 1; kidneys cut separately; blood and deaths in stage 1; animations by Claude.

---

## 8. Economy: buyers, cash, inventory, phone, upgrades

**Status: PARTIAL.** A minimal sale and money exist. The full sales gameplay does not.

### First buyer crate (DONE, [PLAY-SCRIPT])

- `Assets/OV/Buyers/Runtime/FirstBuyerCrateV01.cs`: a wooden crate behind the operating shed at base 2 (sales spec SG-D27).
- Put an organ on it (G); after ~0.4 s it buys at `BuyerCatalog` price into the player's NetworkInventory cash and shows a toast "Скупщик забрал… +$".
- Observed: kidney +$225; a scripted loop run got +$360.
- Toggle: `W85PlayIntegrator.FirstBuyerCrate` or the scene object.
- No buyer NPC, no car, no haggling, no phone flow.

### Buyers core

- `Assets/OV/Buyers/Core` (`BuyerCatalog`, `BuyerRules`, `BuyerOrders`, `BuyerState`, `BuyerTransactions`) + JSON data + EditMode tests.
- Only the crate uses it. `BuyerState.SharedFunds` is unused.
- Specs: `docs/specs/BUYERS_SPEC_2026-10-15_v02.md`: C01 buys blood; 3 organ buyers unlock by story; `SALES_GAMEPLAY_SPEC_2026-10-18_v01.md` (G36): phone deals, meetings, haggling, special orders. Not implemented.
- Data reports: `docs/reports/BUYERS_DATA_v01.md`, `BUYERS_RULES_v01.md`, `ECONOMY_XP_CHECK_v02.md`.
- `cloud/economy-progression-draft` is a draft, not approved.

### Cash persistence (DONE, uncommitted, [PLAY-SCRIPT])

- The host's NetworkInventory cash goes into the capture save (`hasCash`/`cash`). Save version stays 1.
- Old saves load and keep the current cash. Shift+K resets it.
- Host only: clients have no record. Not tested in a build.
- Network plan decision Q4: one shared money fund. Vadim, 2026-10-19: income goes once to the fund; per-player penalties are divided by N. **Not implemented.**

### HUD and phone show the real cash (DONE, uncommitted)

- The hotbar (`InventoryHud.CashSource`) and the phone "Cash on you" (`PhoneWallet.Pocket`) read NetworkInventory. Both showed $225 after a sale.
- The phone bank balance ($1,251) and its history are **placeholders**: no bank account exists.
- The NetworkTest scene phone still shows $85.

### Inventory

- Live system: `Assets/OV/Inventory/` (`NetworkInventory`, `InventoryModel`, `InventoryHud`, `InventoryInput`, `ItemDatabase.asset`, `ThrowCharge`): hotbar slots, physical items.
- The new work-inventory core G39 is staged outside Assets, not integrated (decision D4: keep the live one): `ArtSource/Dev/WorkInventory_staging`, 351 pure tests, `docs/reports/WORK_INVENTORY_CORE_G39.md`, spec `WORK_INVENTORY_SPEC_2026-10-18_v01.md` (6 pocket slots, item ids, quality, donor, spoilage).
- `LocalInventory` ($500 start) is the old offline one. Do not use it for money.

### Phone (presentation mostly)

- Code: `Assets/OV/UI/Phone`, `Map/Scripts/GreyboxPhone.cs`. Tab opens it; the player stands still while it is out.
- Apps: Messages: "call buyer" spawns nobody; Camera + Gallery: session photos; Map: live top-down; Bank: placeholder; PayMarket: placeholder apps.
- Spec `docs/specs/PHONE_SPEC_2026-10-18_v01.md` (G41): shared team hub, scanner, calls and haggling. **Not implemented.** Review branch `claude/phone-review` is not merged.

### Van upgrades

- `VanUpgrades` (Engine/Brakes/Handling 0–3), debug keys 7/8/9.
- No prices and no purchase (decision D5 keeps the debug keys). The van starts at max anyway.

---

## 9. Police and heat

**Status: MISSING in W86. This is Vadim's area.**

- **Police v1** exists for the v19 map only: code: `Assets/OV/Police/` (`PoliceDirector`, `PoliceUnit`, `PoliceOfficer`, `PoliceCarMotor`, `PoliceMapData`, `PoliceRoadModel`, `PoliceEvents`, `PoliceConfig`; data `police_v19_build_v08.asset`); features: wanted level, patrols, car/foot pursuit, GTA-style loss of sight; it runs in `Map_Look_v19_Play_i10_capture_delivery.unity`; its baker reads the old `MAP_PLAN_R01_vNN.json` road graph, while W85 has only `roads_v85.json` polylines.
- **W86 has no police** (decision D2): `W85PlayIntegrator.Carry` omits "Police". Witnesses still raise alerts through the "phone" branch, and nothing responds.
- **Spec G42:** `docs/specs/POLICE_SUSPICION_SPEC_2026-10-18_v01.md` (RU/EN). Contents: local caution zones (red core, yellow ring, visible only on the map); district response profiles: Forest none; Hamlet = one slow hunter grandpa; Rough = gangs, sometimes police; Construction = city police; base inspection, evidence and smell. **Not implemented.**
- Our signals for Vadim (TASK-000835): witnesses +2 for a bagged body, +10 unbagged; evidence, smell, blood, waste, corpses.
- Police models POLICE_THIN/FAT v02 are imported only. `MapPolicePlacer` already names crews `PoliceCrew_N_Thin/Fat`.
- Porting Police v1 to W86 needs a new baker adapter, plus Vadim's and Fedya's decision (INTEGRATION_PLAN C7/A5).

---

## 10. Network and multiplayer

**Status: PARTIAL.** Solo works as a FishNet host. Co-op on the map is not built.

- **Baseline (`docs/ARCHITECTURE.md`):** FishNet 4.7.3 + Tugboat; owner-simulated KCC movement (client-authoritative NetworkTransform, 30 Hz); server-simulated shared rigidbodies; grab requests validated on the server; up to 4 holders on generic props; `NetworkSession` mixes connection, test spawns and UI; No server reconciliation of movement. Not production networking.
- **What runs networked today:** `NetworkTest.unity` (co-op cubes, table, scalpel); the operation table (two-process PASS with 1 client; FAIL with 2–3 clients); the capture map runs as a solo host (loopback, one scene pawn).
- **Plan:** `docs/specs/NETWORK_MAP_PLAN_v01.md` (1,250 lines), milestones M0–M9:

| Milestone | Scope |
|---|---|
| M0 | Harness, session split, input wrapper, sandbox |
| M1 | Players on the map |
| M2 | Server-simulated van |
| M3 | Players in the cargo bay |
| M4 | Networked NPCs, 3-holder carry |
| M5 | Loading and delivery |
| M6 | Crowd |
| M7 | Police |
| M8 | Clock, sky, audio cues |
| M9 | Saves, economy, phone |

- Estimate: 50–67 agent-days in total. M1–M5 and M7 are Claude-only; M0 and M8 are GPT-safe.
- Fedya accepted Q1–Q8: Q1: server-simulated van; Q2: passengers walk below 6 km/h, riding slots above; Q3: Tugboat LAN/IP now, Steam decided by M9; Q4: one shared fund; Q5: client-ID save key; Q6: the cloud swap keeps the PatientId; Q7: sandbox scene + a real-map check per milestone; Q8: the session ends when the host leaves.
- **Done:** M0 part 1 only, the external harness (G37), report `docs/reports/NETWORK_HARNESS_M0A.md`: Scripts: `Working/Reviews/Network/run-net.ps1`, `run-net-suite.ps1`, `tools/compare_traces.py`; Re-validation against real executables after the review fixes is pending.
- **Not started:** M0 part 2 (session split, input wrapper, sandbox) and M1+.

---

## 11. Saves

**Status: PARTIAL.**

- One JSON file per slot, written by `Capture/Scripts/CaptureSave.cs` (`CaptureSaveData`, version 1, `Capture/Core/CaptureRules.cs`).
- Contents: player position, yaw and driving flag; van pose and door states; time of day; captured NPCs with facts, ties and the undressed flag; table `OperationWorldState` + patient facts; field kit; body-bag stock; corpses and bags (poses, held state); completed patients; **cash (new, host only)**.
- K saves; Shift+K starts a new game (loads the first Build Settings scene, which is now W86 Play). It loads on start.
- Slots: build: `capture_stageA_v01.json`; editor: `capture_stageA_editor_W85_v02.json` (W86), `…_W85.json` (W85 v01), `capture_stageA_editor.json` (i10); Location: `%USERPROFILE%/AppData/LocalLow/<company>/<product>/OnlyVolunteers/`; A stale agent save was moved aside as `….stale_agentC_2026-10-22`.
- Not saved, as far as the code shows: hotbar/inventory items such as organs in hand [UNVERIFIED], the crowd, client players, XP and upgrades.
  - The old `Clinic/ClinicSave.cs` (`fc_loop_save_v1.json`) saved upgrades, but it is superseded and not in W86.
- Spec targets: OPERATIONS_SPEC §20, WORK_INVENTORY §6, NETWORK plan M9.

---

## 12. Animations and art pipeline

**Status: DONE as a pipeline; content keeps growing.**

### Characters

- Built procedurally with Blender 5.2 Python, deterministic scripts plus validators (`verify_*.py`).
- Never overwrite: every revision is `_vNN`, and optimised derivatives are `_opt_v01/_opt_v02`.
- Sheets go to `Working/Reviews/...`.

### Animation sets

- `ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/`: Cargo_v01, Crowd_v01, Escape_Police_v01, Escape_v01, GetUp_Idle_v01, GetUp_v03, Idle_Knock_v03, Locomotion_v01/v02, Operation_v01.
- Each set has build scripts, validators and an authoring JSON.
- Install path: `clips.json` → `NpcAnimatorBuilder`; patient clips → `Patient_Operation.controller` through the Operation menus.
- **Human/character animation is done by Claude only. GPT never does it.**

### Props and map art

- `ArtSource/Props/*` (procedural or Tripo); W86 kit at `ArtSource/Props/MAP_W86_v01`; facade kit `FACADE_KIT_v01`; grandpa yard `GRANDPA_YARD_v01`.
- Export rules: `docs/ArtDirection.md` §9.

### Textures

- Online textures only CC0 (ambientCG), repainted to the style. Record sources in `SOURCES.md` next to them (`ArtSource/Textures/ambientCG_<date>/`).
- Use 1024 px; 2048 only for big atlases.
- Rule for picks: make 3 variants, pick 1 by Fedya's taste, keep the other 2 switchable.

### Tripo and paid services

- Only for images the owner approved; a Create must read exactly 100 credits.
- **Workers never spend credits.**

### Licences

- `THIRD_PARTY_NOTICES.md`, `docs/Dependencies.md`, `docs/DependencyDecisions.md` (the Field Clinic kit catalogue is a decision queue, not an install list).
- Keep the existing systems: FishNet, KCC, our van, ragdoll NPCs, the map pipeline, Uber Water.

---

## 13. Open questions, known bugs, next steps

### Decisions log pointers

- `docs/reports/W86_2026-10-22/`: `INTEGRATION_DECISIONS_FEDYA.md` (D1–D6: crate yes; no police in this build; specials import-only; keep the inventory; keep keys 7/8/9; FP hands later); `ANSWERS_FEDYA_2026-10-22.md` (22 map answers), `TEXTURES_DECISIONS_FEDYA.md`, `INTEGRATION_PLAN.md` (loop status table, A1–C8).
- Decisions appendices at the end of each `docs/specs/*_v01.md` (Fedya, 2026-10-18).
- WORK_SYNC TASK-000835 (Fedya → Vadim: police signals), 000883 (ALTGIRL VIP-only), 000894 (hunter = forces group).

### Known bugs and gaps

1. Player build crash "level0 is corrupted": `W76LeaveCountryButton` is declared in `W76MapMarkers.cs`. Move it to its own file (still open).
2. One "missing script" warning on Play, from an object created at runtime. Not investigated.
3. Ragdoll regression r25 wall-push, r7 pair-rear timing (G35).
4. Escaped patient holds his hand prop again.
5. Phone bank and history are placeholders; NetworkTest phone shows $85.
6. Cash is saved for the host only; nothing tested in a built .exe.
7. NPC placements (buried, castle, detector, lounger, pull-up bar) not spawned; NpcSpot/Patrol markers are empty; Elite, Valley and Tramduro have no crowd.
8. W85 note: map materials were taken from the TextureTest v04 scene, so do not rebuild that scene. Whether W86 still depends on it is unknown: check before rebuilding any TextureTest scene.
9. Hamlet izbas sunk 0.5–1.3 m (W85; W86 unknown).
10. Real keys E/G and the escape clips have not been checked by a human in W86.

### Next steps (Fedya's likely order, not yet briefed)

1. **Commit the uncommitted 2026-10-25 work** (explicit paths, LFS for FBX/blend), after Fedya's OK. The lead writes the WORK_SYNC TASK.
2. Fedya playtests W86 with real keys: full loop to sale, K save, reload with cash, escape clips by eye.
3. Fix the `W76LeaveCountryButton` build crash; build and smoke-test a Windows player.
4. Vadim's review of W86 (map, textures, Rough, Downtown v37) → local map fixes per his notes.
5. Decide on visible NPC role placeholders (C2) and the placements spawner.
6. Unify the money: shared fund, bank app on real data.
7. Next economy step: buyer NPC, car or phone flow (sales stage A); upgrade prices (needs the economy draft approved).
8. Police on W86 (Vadim's call): port v1 or start G42.
9. Network M0 part 2 → M1.
10. Operations stage 2 (chest) per G40.
11. NPC behaviour spec implementation after Vadim finishes the draft.
12. Gold Tramduro statue on the Downtown square.

---

## Rules for Codex

- **Scope:** do exactly the brief. Touch only the files it names. If the brief is unclear or contradicts the code, stop and ask in your report.
- **Police and suspicion are Vadim's.** No edits to `Assets/OV/Police/`, the police spec or the police data unless the brief asks.
- **Git:** never `git add -A/./-u/--all` (the hook blocks it); stage explicit paths only; never commit or push unless the brief says so; **never push without Fedya's OK**; never use `ALLOW_PUSH_ONCE`; no reset, clean or force-push; never edit `WORK_SYNC.md`.
- **Unity:** take the lock (`unity_lock.ps1 -Cmd acquire -Id <your chat id>`), refresh at least every 20 min, release when done; never touch Unity while `PLAYTEST_ON` exists; press "Ignore Warning" on the admin dialog; never edit scripts while in Play mode, because a domain reload breaks KCC.
- **Keep the project compiling:** zero console errors after your change. Run the relevant EditMode tests (Capture, Inventory, Operation). Report PASS/FAIL/BLOCKED/NOT RUN honestly; compile is not proof of fun.
- **Versioned assets:** new revisions get new numbered names (`_vNN`, `Data/vNN`, `_v02` scenes); never overwrite a deliverable or an old scene; keep `.meta` GUIDs; put scene changes into builder/integrator code (`W85PlayIntegrator`), not by hand into `Map_W85_Play_v02.unity`.
- **Do not change:** the Unity version, URP or pinned packages; `ProjectSettings` (an agent once flipped `runInBackground` and Enter Play Mode options; revert such changes); the shared NPC get-up clips.
- **Gameplay invariants:** the van always starts at max level; objects never push the player; all NPCs are adults; no brands or logos; CC0-only online textures with a recorded source.
- **Never** do character animation, spend Tripo or other paid credits, or delete files.
- **Report:** what you changed (exact paths), how you checked it, what is still open.
