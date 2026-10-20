# VOLUNTEERS ONLY: Network Plan for the Map (Co-op 1–4)

Revision: v01
Date: 2026-10-18
Status: Phase 1, analysis and plan only. No project code was changed and Unity was not opened.
Scope: make the whole map game work for a host plus up to 3 clients, using FishNet 4.7.3 and Tugboat.

**Inputs read:**
- Docs:
  - `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md`;
  - `CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md` (§8);
  - `OPERATIONS_SPEC_2026-10-15_v01.md` (§14, §15, §20, §21);
  - `BUYERS_SPEC_2026-10-15_v02.md` (money and atomic sales);
  - the canon, §129–136 and §151;
  - `docs/drafts/NPC_CAPTURE_VAN_COOP_DRAFT.md` (§3–5, the old network sketch for the van).
- Reports and capture notes:
  - `docs/reports/OPERATIONS_STAGE1_v02.md` and `OPERATIONS_STAGE1_v04.md`;
  - `Working/Reviews/Capture/stageA/` (PROGRESS, HANDOFF, FEDYA_FEEDBACK).
- Runtime code under `Assets/OnlyVolunteers`, and the FishNet 4.7.3 sources in `Library/PackageCache`, checked for the features cited.

Line numbers refer to the files as they were on 2026-10-18 at about 06:00.

---

## 0. Summary

1. **Solo play becomes "host with 0 clients".** The map has one code path: the server simulates the world, and every peer, the host included, is a client of it. Capture Stage A already runs the map as a solo FishNet host, so this direction is established. The plumbing is single-player:
   - loopback bind;
   - one scene pawn handed to every connection;
   - no NetworkTransform on the pawn.
2. **What stays owner-simulated:** each player's KCC movement, camera, phone and HUD. This is the existing `NetworkPlayer` pattern: a client-authoritative NetworkTransform at the 30 Hz tick. Everything physical and shared is server-simulated:
   - the van and its doors;
   - NPC bodies and ragdolls;
   - the crowd and the police;
   - the clock and the save.
3. **Clients send intents, the server validates.** Intents are reach, line of sight, the rules and sequence numbers. Results replicate as small state SyncVars, NetworkTransforms, custom pose streams and cue RPCs. This copies the operations table, which already passes two-process tests.
4. **The van is server-simulated.** The driver's client sends input at 30 Hz. The host drives with zero latency; a client driver feels about one RTT plus the interpolation delay. If that is too much at 100 ms, the fallback is decision Q1.
   - **Passengers and cargo NPCs are replicated in van-local coordinates.** Each peer then places them relative to its own interpolated van, so nobody "lags out of the bay".
5. **NPCs become scene NetworkObjects with a compact server state.** The crowd pool and placed NPCs are already scene objects pooled with SetActive. FishNet 4.7.3 registers inactive scene objects and despawns scene objects by disabling them, so the pool maps onto `Spawn`/`Despawn` directly.
   - **Ragdoll poses** reuse the proven operation-patient stream: root-relative, delta-gated, buffered for late joiners. It is compressed and carrier-relative.
   - **Up to 3 holders per NPC:** `NetworkGrabber` grows a part index. A server hold loop then drives the NPC's existing `IGrabPointTarget`/`IGrabPointBodyGroup` claims (already 3 slots, per-part handles).
6. **The crowd is global and fixed.** It is about 61 walkers by day and 57 in the evening, plus 2–4 foot cops and 4 police cars with 8 crew: about 80 entities, everywhere, regardless of player count. Server simulation therefore does not grow with players. Replication is distance-culled at 200 m.
7. **Budget** (estimates; M0 adds measurement):

   | Scenario | Per client, downstream | Host upstream |
   |---|---|---|
   | Typical 4-player capture | ≈12.5 KB/s | ≈38 KB/s |
   | Chaos (6 flying ragdolls, the whole beach crowd in view) | ≈37 KB/s | ≈110 KB/s |
   | All 4 at the operation table | ≈50 KB/s | ≈150 KB/s |

   - The table case is driven by its 3 KB JSON snapshot, the first optimisation target.
   - Bandwidth is not the constraint; latency feel is.
   - The host's extra CPU for networking is estimated at 1 ms per frame or less. Clients are cheaper than the host.
8. **Ten milestones.**
   - M0 (harness and groundwork) through M5 make the core loop co-op: players, the van, passengers, the 3-holder capture, loading and delivery. That takes 33–43 agent-days.
   - M6–M9 add the crowd, the police, the clock and audio events, then saves, the economy and the phone. All ten take 50–67 agent-days.
   - M1–M5 and M7 are Claude-only. M0 and M8 are GPT-safe, and M6 and M9 are mixed.
9. **Nothing that writes into `Assets/` can start while G35 holds Unity.** Two things can start now: the PowerShell harness, outside Assets, and this plan's review. M0 starts right after G35 is accepted.

---

## 1. Working patterns to reuse (P1–P8)

| # | Pattern | Where | Facts worth keeping |
|---|---|---|---|
| P1 | Session and spawning | `Network/Scripts/NetworkSession.cs` | `MaxPlayers` 4; port 7770; args `-ov-host`, `-ov-client [addr]`, `-ov-port`. Binds `0.0.0.0`. Spawns `playerPrefab` per connection at `playerSpawns[slot]` in `OnClientLoadedStartScenes`, kicks a 5th, despawns on disconnect. Mixed with NetworkTest test spawns (8 bodies, table, scalpel) and an OnGUI panel; needs splitting (ARCHITECTURE.md says so too). |
| P2 | Owner-simulated player | `Network/Scripts/NetworkPlayer.cs`, `Network/Prefabs/NetworkPlayer.prefab` | NetworkTransform with `_clientAuthoritative 1`, interval 1 tick, interpolation 2. Non-owners get input, motor, camera and listener disabled, and a `RemoteVisual`. Owner view pitch/yaw goes as an unreliable ServerRpc at 10 Hz, relayed with ObserversRpc(ExcludeOwner). Phone and HUD are owner-only. No reconciliation (accepted for co-op among friends). |
| P3 | Server-authoritative grab | `Network/Scripts/NetworkGrabber.cs`, `NetworkPhysicsBody.cs` | **Grab request** `ServerTryGrab(requestId, NetworkObject, origin, dir)`: request id monotonic; origin within 2.4 m of the motor; server re-raycast; allow-list. **Hold** `ServerHoldTarget(holdId, seq, target)`: unreliable, 20 Hz, stale sequences dropped. **Body:** up to 4 holders; 0.8 s target timeout; break distance; holder collisions ignored; force solved per holder with `mass / count`; release on disconnect. Clients are kinematic behind a server NetworkTransform. |
| P4 | Intent + validated state machine | `Operation/Stage1/Scripts/NetworkOperationTable.cs` | **Requests:** `ServerRpc(RequireOwnership = false)` (Join, Select, Return, Click, Pointer, Dev). Points are table-local; reach 3.2 m; participants keyed by client id. **Replies:** refusals go to one client as a `TargetRpc` hint id; pointer streams at 20 Hz with sequence and press ids and expires after 0.5 s. |
| P5 | Snapshot + cues | same | `SyncVar<string>` JSON `OperationView` (about 3 KB, `final-state.json` sizes 2.9–3.1 KB), published at no more than 15 Hz and sent only on change. `ObserversRpc` cues drive faces, sounds and toasts; remote cursors use unreliable ObserversRpc. |
| P6 | Ragdoll pose sync | `Operation/Stage1/Scripts/OperationPatientRagdoll.cs` | **Server:** simulates the 11 dynamic bodies. **Stream:** `ObserversRpc(BufferLast, ExcludeServer)` with 11 root-relative poses (Vector3 12 B + FishNet's default 32-bit Quaternion 4 B, about 190 B a message); at most 20 Hz, only when a bone moved more than 2 mm or 0.6°, with a 1 s heartbeat. **Clients:** kinematic copies with exponential smoothing (30/s); the held-or-lying collision rule is mirrored; the wake-blend hand-back runs from the last received pose. **Verified (net04):** 50 pose updates, 0 dynamic bodies on the client. |
| P7 | Atomic transitions | `NetworkOperationTable` extract; `Buyers/Core/BuyerTransactions.cs` | Extraction creates the WorldItem `PatientId/organ/index` exactly once; a client quitting mid-pull rolls nothing back (net02). `ConfirmSale` builds on a state copy, publishes once and is idempotent by `ConfirmationId`; it is not wired to any runtime code yet. |
| P8 | Real-input testability | `OpsInput.cs`, `OperationNetworkProbe*.cs`, `CaptureScenarioDriver.cs`, `run-localhost-v02/v04.ps1` | Virtual Mouse/Keyboard through the real view. Roles `-ops-scenario net-host/net-client`. Every step waits on replicated state (`WaitFor`). Evidence folders hold PASS/FAIL lines, screenshots and `final-state.json`. Two hidden processes run with a timeout and a kill. |

**Known weak points to fix on the way:**
- `NetworkGrabber` assumes one rigidbody per target (`GetComponentInParent<NetworkPhysicsBody>`, L155).
- `NetworkSession` has mixed responsibilities.
- The map HUD shows `LocalInventory`, not `NetworkInventory`.
- The map reads most keys with the legacy `Input` API, which the virtual devices cannot drive (CaptureScenarioDriver header, L20–27).

---

## 2. Inventory

### 2.1 Overview

The "Couplings" column counts the single-player assumptions that block co-op. Appendix A lists them with line numbers.

| System | Today | Main classes (paths under `Assets/OnlyVolunteers`) | Authoritative state it owns | Update / physics model | Couplings |
|---|---|---|---|---|---|
| Session | **Solo host on loopback** | `Capture/Scripts/CaptureDirector.cs` + scene NetworkManager `[Capture] Network (solo host)` (Tugboat; a disabled `NetworkSession`) | none | `StartHost` probes UDP ports 7791+; `ClientLoaded` hands over the pawn | `SetServerBindAddress("127.0.0.1")` (L143); `ClientLoaded` spawns or **re-owns the single scene pawn for every connection** (L179–187) |
| Player pawn | **Half-online:** scene NetworkObject, `externalControl`, **no NetworkTransform** | Player_KCC_Baseline + `Map/Scripts/GreyboxKccPawn.cs`, `Player/Scripts/KccFirstPersonInput.cs`, `Player/Scripts/Physics/PhysicsGrabber.cs`, `Map/Scripts/GreyboxInteractor.cs`, `GreyboxCargoRider.cs`, `GreyboxPhone.cs`, `Inventory/Runtime/LocalInventory.cs`; `NetworkPlayer`/`NetworkGrabber`/`NetworkInventory` for the table | KCC motor state; stance; seat; held point | KCC on the owner; input in Update; grab force in FixedUpdate | Legacy `Input` (KCC 9 lines, grabber 4, interactor 4); reflection on `_yaw`/`_pitch` (GreyboxKccPawn L16–17); static `GreyboxInput.EUsedFrame` |
| Van | **Offline** | `Vehicles/Van/Scripts/` VanController, VanDoor (5), VanCargoSpace, VanDriveInput, VanCameraRig, VanInteriorColliders, VanUpgrades; `Map/Scripts/` GreyboxVanSeat, GreyboxVanCargo, GreyboxDriverDummy, GreyboxVanAutopilot; `Capture/Scripts/CaptureVanCapacity.cs`; `Vehicles/Scripts/VehicleEngineAudio.cs`, `VehicleImpactAudio.cs`; `Vehicles/Paint/**` | Rigidbody 1800 kg, 4 WheelColliders; Throttle/Steer/Handbrake; door `TargetOpen`/openness ×5; upgrade levels[3]; seat; cargo dictionary; paint journal | WheelCollider FixedUpdate. Doors are kinematic poses on the van's compound body; force-limited pushes (250/300 N, 15 N·s shove) | One `GreyboxVanSeat.Pawn`; the pawn is `SetActive(false)` while driving; Main Camera swap; 3 writers of the inputs (seat, autopilot, capacity veto) |
| NPC body and brain | **Offline** | `Map/Scripts/GreyboxNpc.cs` (1310 lines), `GreyboxNpcBody.cs`, `Characters/Npc/Scripts/` NpcRagdoll (1953), NpcGetUp, NpcStruggle, NpcAnimDriver, NpcRagdollPart, INpcBody; `Characters/Scripts/NpcHeldProps.cs`; `Map/Scripts/Combat/WeaponStun.cs` | `NpcState`, `StunPhase`, StunLeft/Total, Condition, InCargo/Carrier, HandsBound, flee timers; `Claims[3]` (holder, part, local point); body mode | State in Update (stun counts down with `Time.deltaTime`, L608); physics in FixedUpdate. Free: `CharacterController.Move`. Down: capsule (28 kg) or 11-body ragdoll (28 kg, 10 ConfigurableJoints) | `FindAnyObjectByType` van/pawn (L294–296); static `All`, `Incident`; `NpcRagdoll.Listener` uses pawn + `Camera.main` (L974–977); static `NpcRagdoll.Mode`/`Cap` 12; unseeded `Random` |
| Capture Stage A | **Offline**, on top of the solo host | `Capture/Scripts/` CaptureNpc, CaptureFieldKit, CaptureTableBridge (server-only already), CaptureCloud, CaptureTieVisuals, CaptureHud, CaptureSave, CaptureDirector; `Capture/Core/` CaptureRules, CaptureGrades | `OperationState` on the NPC (residual, sleep, bloodPortions, alive, conditionLoss) and `CaptureFacts` (ties, district, type, intrinsic grades); kit stock per player | Rules tick in FixedUpdate; stun pinning in Update | `CaptureDirector.Instance`; the kit mutates NPC state in place (L211, L225, L248); one `Pawn` everywhere |
| Crowd | **Offline** | `Map/Scripts/Crowd/` CrowdDirector, CrowdWalker, CrowdWitness, CrowdData; data `Map/Data/crowd_v19_build_v07.json` | Walkers, `AlertLevel[10]`, `Evening`, POI slots, spawn timers | Update; `CharacterController.Move`; A* over CrowdGraph; O(N²) avoidance over `GreyboxNpc.All`; **global population, no activation radius** | `FindAnyObjectByType` pawn/van (L144–145, L372); `Camera.GetAllCameras` (L371); F11/F12 (F12 flips `Evening`); runtime `AddComponent<CrowdWalker>` (L347) |
| Police v1 | **Offline** | `Police/Scripts/` PoliceDirector, PoliceUnit, PoliceCarMotor, PoliceOfficer, PoliceConfig, PoliceMapData, PoliceEvents | Suspects {`VanSuspect`, `PawnSuspect`}, `Heat[10]`, unit and officer states, tips | Brains in Update; cars on 4 raycast springs (1300 kg) in FixedUpdate; officers `CharacterController` | One Pawn and one Van in every API (L160–168, L469); `Pawn.Knock`; arrest through `LocalInventory`; runtime `AddComponent<PoliceOfficer>` (L538) |
| Operations table | **Online** | `Operation/Stage1/Scripts/` NetworkOperationTable, OperationTool, OperationPatientRagdoll, OperationTableView, OperationHud, OperationPhysicalItem | `OperationWorldState` | Server rules in FixedUpdate | none blocking (P4–P6) |
| Inventory | **Mixed** | Online: `Inventory/Runtime/NetworkInventory.cs`, `WorldItem.cs`. Offline on the map HUD: `LocalInventory.cs`, `OfflineWorldItem.cs`, `InventoryInput.cs`, `InventoryHud.cs` | Slots, cash | Server model + owner-only SyncTypes (online) | The map HUD resolves `LocalInventory`; `InventoryInput` falls back to `Camera.main` (L95) |
| Clinic and saves | **Offline** | `Clinic/Scripts/` ClinicLoop (GameObject inactive in i10), ClinicSave, PatientRegistry, PatientLifecycle; `Capture/Scripts/CaptureSave.cs` | Save files; patient ids (GUIDs minted locally) | Autosave 60 s, K, on quit; atomic tmp/replace/.bak | One player block; `PatientRegistry` scans `GreyboxNpc.All` each frame |
| Time and sky | **Offline** | `Sky/G22_v04/Runtime/SkyClock22.cs`, `SkyRenderer22.cs`, `Integration/SkyDistrictV19Bridge22.cs`, `Sky/MapIntegration_i03_v01/SkyMapNight22I03.cs`, `Map/LookV3/Palette19/DistrictFog19V05.cs` | `hour`, `cycleMinutes` 24, `running`; no day count | Update with `Time.deltaTime` | Debug keys `\` `[` `]` via `Keyboard.current`; `CaptureSave` finds the clock (L88, L120) |
| Audio and VFX | **Local** | `Audio/Scripts/` Sfx, SfxLibrary, AmbiencePlayer, WaterBodyAudio, WaterQuery; vehicle audio | none (presentation) | `Sfx.PlayAt` fire-and-forget with per-id cooldowns | `Camera.main` (AmbiencePlayer L94, L270); `FindObjectsByType` every 2 s (VehicleEngineAudio L560–563, VehicleImpactAudio L74–78) |
| Phone | **Local, per player** | `UI/Phone/Scripts/` PhoneController, PhoneHome, MessagesApp, BankApp (`PhoneWallet`), MarketApp, MapApp, CameraApp, GalleryApp | Placeholder money (Bank 1251, Cash 85), threads, photos | Legacy mouse/Tab | `FindAnyObjectByType<EventSystem>` (L253); `VanPaintMapMode` finds the phone (L43) |
| Buyers | **Pure rules, unwired** | `Buyers/Core/` BuyerRules, BuyerTransactions, BuyerState, BuyerOrders | `SharedFunds` (decimal), orders, respect, XP | Single-host rules behind a lock | none; `decimal` is not serialised by JsonUtility |

### 2.2 Player pawn and interaction

- **Owner simulation already exists** (P2). The map pawn is a different object: a `Player_KCC_Baseline` instance in the scene with GreyboxKccPawn, PhysicsGrabber and GreyboxPhone on the root. `MapGreyboxBuilder.PlaceGameplay` (L351–485) adds the following to the motor GameObject:
  - SeaReturnTracker, GreyboxCargoRider;
  - LocalInventory, InventoryHud, InventoryInput;
  - GreyboxInteractor.
- **What Capture Stage A added:** `NetworkPlayer` with `externalControl` (it skips all local control switching, `NetworkPlayer.cs` L72–76), `NetworkGrabber` and `NetworkInventory`. There is no NetworkTransform, so the pawn's movement is not replicated at all.
- **Interaction keys.** `GreyboxInteractor` uses Q (hit, a local raycast followed by `npc.Hit` on the local NPC, L79–84), E (a priority chain: inside handle → `GreyboxUses.All` → `OfflineWorldItem` pickup → cargo door → seat), and F9/F10 (dev pins; F10 sets the global `NpcRagdoll.Mode`).
- **Two grab paths.** `CaptureGrabArbiter` (CaptureDirector.cs L421–454) switches the LMB between the offline `PhysicsGrabber` and `NetworkGrabber`, depending on whether a `NetworkPhysicsBody` is under the crosshair.
- **Push policy.** `PlayerPushPolicy` (static, installed at SubsystemRegistration) makes only movers solid for the KCC: the van, police cars and KCC motors. Items and NPC bodies are never solid. It must hold on every peer.

### 2.3 Van

- **`VanController`** is input-agnostic and has no statics; its comment at L5–6 already anticipates network driving.
  - Numbers (VanSetupBuilder L124–128, L240–248): 1800 kg, CoM (0, 0.55, −0.1); 4 WheelColliders of 25 kg; front drive and steering; MotorTorque 1250, BrakeTorque 4200; MaxSteer 34° → 11° at speed; top speed 105 km/h; AntiRoll 9000.
- **`VanDoor` ×5:** FrontLeft, FrontRight, Slide, and RearLeft + RearRight, which move together.
  - The door is a kinematic pose on the van's compound body, stepped in FixedUpdate and interpolated in Update. `TargetOpen` is marked "a network door mask later" (L70).
  - Blocking: OverlapBox, then ComputePenetration. Dynamic bodies are pushed with up to 250/300 N. `IDoorPushTarget` lets a ragdoll take the push once per group. A KCC is nudged when the door opens; a closing door stalls on a "foot in the door", then backs off after 0.6 s.
- **Seat (`GreyboxVanSeat`).** E within 3.5 m enters. Exit is allowed at 12 km/h or less, onto a free side.
  - **The pawn is deactivated** (`SetControlled(false)` → `SetActive(false)`), not seated. `VanDriveInput` (legacy keys) is enabled, and the Main Camera with `VanCameraRig` takes over.
  - `GreyboxDriverDummy` draws a grey driver that turns its head with the view.
- **Players in the bay (`GreyboxCargoRider`).** No parenting: `AttachedRigidbodyOverride` = the van Rigidbody, plus `RigidbodyInteractionType.None`, `IgnoreCollision` with all van colliders, and the van's yaw delta fed to the view.
  - Known buzz against the walls at speed (L22–24).
  - It works only where the van Rigidbody is dynamic and its pose is current.
- **NPCs in the bay (`GreyboxVanCargo`, order −50).** All per-tick work in FixedUpdate.
  - **Loading:** the pelvis and collar landmarks are in the box, nobody holds the NPC, the van is upright, and the speed relative to the van stays below 0.25 m/s for 0.5 s. A 400 N·s settle impulse follows.
  - **Kept inside by velocity matching:** lying bodies are damped toward the van's point velocity at 1.5/s; sitters at 4/s, plus `MoveRotation`.
  - **Escapes** through an open door (openness > 0.3), using `Random`. Above 12 km/h the escaper tumbles (−10 condition).
  - **Teleports:** `MoveRigid` carries every body along.
  - Single-pawn helpers: `RidingPawn()` (L778–783).
- **Capacity veto (`CaptureVanCapacity`, order 200).** With more than 3 bodies it forces the doors open, zeroes the throttle below 8 km/h, coughs and toasts. A third writer of the van inputs.
- **Audio.** `VehicleEngineAudio` (about 11 AudioSources per van) reads Throttle, `SpeedKmh`, Handbrake and `GreyboxVanSeat.Driving`. `VehicleImpactAudio` works from `OnCollisionEnter`.
- **Upgrades and paint.**
  - `VanUpgrades.TrySetLevel` + `LevelChanged`: 3 ints, 0..3, and its comment says a network layer only calls it.
  - Paint: a stroke journal (at most 256 strokes, 8192 dabs per stroke) with `StrokeCommitted` / an idempotent `ApplyStroke`. It is already transport-neutral, but undo and wipe have no command form. Saved per `vanId` under `persistentDataPath/VanPaint/`.

### 2.4 NPC body, brain and capture state

- **States:**
  - `NpcState {Free, Down, CargoSeated, Escaping, GettingUp}`;
  - `StunPhase {None, Out, Groggy, Awake}`, with `OutShare` 0.6;
  - flee speed 4.5 m/s; scared by the pawn within 7 m or the van within 14 m;
  - hit impulse 60 N·s;
  - condition costs: re-stun −5, hard impact above 5.5 m/s −5, ankle drag −1 per second above 1.5 m/s.
- **Body modes.** Capsule (`GreyboxNpcBody`): 28 kg downed, 40 kg seated sitter, 3 claims. Ragdoll (`NpcRagdoll`): 11 bodies.

  | Part | Mass (kg) |
  |---|---|
  | Pelvis | 5 |
  | Chest | 5.6 |
  | Head | 2.4 |
  | Upper arms | 1.3 each |
  | Forearms | 1.0 each |
  | Thighs | 3.0 each |
  | Calves | 2.2 each |

  It has 10 ConfigurableJoints, solver 12/4, and at most `Cap` = 12 live ragdolls.
  - **Bones:** the 54 non-simulated bones of the 65-bone rig are frozen at the knockdown pose, with the Animator off.
  - **Root:** it does not follow the ragdoll (moved only by `PlaceLying` and `MoveRigid`).
- **Holders.** There are already 3 claim slots per NPC, with per-part handles: Good 240 N, Medium 200 N (thighs), Bad 150 N (pelvis, belly).
  - Weight relief by holder count: {0, 0.20, 0.35, 0.45} × g.
  - Carry tone (limp, held, split carry) is set from the holder count.
  - A limb hold sends 40% of its force up the chain to the trunk.
  - Offline, the 2nd and 3rd holders are only F9 debug pins.
- **Animation.** `NpcAnimDriver` is the only Animator writer. Its `Compose(inputs)` is a pure function of State, Phase, Fleeing, held, speed, activity, gait and aim, so it can run on clients from replicated inputs.
- **Capture layer.**
  - `CaptureNpc` carries `CaptureFacts` and the same `OperationState` object the table later uses, so identity and counters travel with the body.
  - Intrinsic grades are seeded from (patientId, district, type), so they are deterministic.
  - Mapping of the spec's travelling state: condition = `GreyboxNpc.Condition`; bloodPortions, residual, sleepRemaining, alive and deathAge live in `OperationState`; hands and feet live in `CaptureFacts.restraints`; the head bag does not exist yet.
- **Table admission.** `CaptureTableBridge` (server-only) admits an unheld, slow NPC that is Down over the pad. It plays the cloud, calls `Destroy(npc.gameObject)` and `Table.ServerAdmit(state, …)`, which spawns the table's own patient prefab with the same `PatientId` and state.

### 2.5 Crowd

- **Population** (`crowd_v19_build_v07.json`):

  | | Day | Evening |
  |---|---|---|
  | Walkers | 61 | 57 |

  Other sizes:
  - foot patrol: 2 officers on a 1247 m loop;
  - pool: Σ max(day, evening) + 2 officers + 10 spare = **78 inactive scene NPCs**, plus templates;
  - graph: 20 routes, 70 POIs, 20 spawn points (each with `min_player_distance_m` 25 and a 2 s grace), 10 witness hotspots.
- **Global population:** there is no spawn, despawn or activation radius. The whole map's walkers are simulated wherever the player is. Spawns and despawns use fixed hidden points.
- **Visibility test.** `Visible(feet, minDistance)` returns true if any of these holds:
  - the single pawn is near;
  - the single van is near;
  - any enabled camera has the point in its viewport, checked with a Linecast.

  It gates spawn, despawn, prewarm, stuck teleports, officer vanish and police-car placement.
- **Witnesses** (`CrowdWitness`): 32 m by day, 20 m in the evening (×1.3 for police), a ±70° cone and a Linecast. They watch the **victim**, not the attacker. They report to a hotspot at 3.6 m/s, which raises `AlertLevel` (0–5, −1 level per 90 s).
- **Handoff to capture.** On Stunned or Captured, `CrowdWalker.Release` hands the same GameObject over as a plain GreyboxNpc and `Destroy(this)`s the walker component. The director spawns a replacement.

### 2.6 Police v1

- **Fleet:** 4 cars (2 patrol by day, 3 at night; 1 reserve), 2 crew per car (8, inactive while inside), 2 foot patrol officers, plus up to 2 extra at high heat.
- **Cars:** a Rigidbody on 4 raycast springs, not WheelColliders. `excludeLayers` = NpcMask. Pedestrians are scanned at 5 Hz and knocked over above 15 km/h.
- **Suspects and attribution.** There are exactly two suspects, `VanSuspect` and `PawnSuspect`; there is no numeric wanted level. `Attacker` attributes a stun to the pawn if it is within 4 m, else to the van if it is moving within 6 m.
- **Tuning:**

  | What | Value |
  |---|---|
  | Car sight | 45 m ±75°, 15 m all round, 70 m in pursuit, 5 Hz |
  | Evade | unseen for 10/15 s and more than 80 m away |
  | Base safe disc | 60 m |
  | Heat | 0–100, −1 point per 8 s |

- **Arrest.** The penalty goes through the pawn's `LocalInventory`, then the pawn is teleported. Officers apply `Pawn.Knock` (KCC velocity) directly.

### 2.7 Clinic, saves and identity

- **Live code in i10.** In `Map_Look_v19_Play_i10_capture_delivery.unity` the live loop is `CaptureDirector`. `FC_ClinicLoop` is inactive.
- **What `CaptureSave` stores** (JsonUtility, atomic `.tmp` → `File.Replace` → `.bak`):
  - one player (position, yaw, driving);
  - the van pose and doors;
  - every captured NPC (`CaptureNpcSave`, van-local when in the bay);
  - the table (`OperationWorldState`);
  - the field kit, `timeOfDay` and completed ids.
- **Not saved:** money, inventory slots, van upgrades, the phone, and a day count (none exists).
- **Paths:** `persistentDataPath/OnlyVolunteers/capture_stageA_{v01|editor|test}.json`.
- **Patient ids.** `PatientLifecycle.NewId()` mints `"P-"` plus 10 GUID hex characters on whatever machine runs it, so the registry and the director must run on the server only.

### 2.8 Time, audio, phone, inventory, buyers

- **Clock.**
  - All map Play scenes i04–i10 use `SkyClock22` v04 (hour 8, `cycleMinutes` 24, so one in-game hour per real minute); v02, v03 and v05 are unused on the map.
  - The ops spec defines one game day as **45 real minutes** (§14). That is a tuning mismatch, not a network issue.
  - Renderer, night lights and fog are presentation, evaluated per camera.
  - `CrowdDirector.Evening` is **not** linked to the clock (F12 only).
  - `BuyerRules` expects an `IBuyerClock.GameSeconds` that nothing provides yet.
- **Audio.** Everything is local. `Sfx.PlayAt` says "nothing networked" (L8). Ambience needs only the local `Camera.main` listener.
- **Phone.** Everything is per player and local. Money is a placeholder `PhoneWallet`; messages are scripted; photos are session-only JPGs.
- **Money exists in four unconnected places, and none is saved on the map:**
  - `LocalInventory.Cash` (start 500, shown on the HUD);
  - `NetworkInventory.cash` (owner-only SyncVar);
  - `PhoneWallet`;
  - `BuyerWorldState.SharedFunds` (unused).
- **Inventory.** `NetworkInventory` is already the correct server pattern: a server-side `InventoryModel`, owner-only `SyncList`/`SyncVar`, and validated pickup and drop RPCs.

### 2.9 Cross-cutting blockers (top 10)

1. **The session is single-player.** The bind is loopback, the single scene pawn is re-owned by every connection, and the pawn has no NetworkTransform (`CaptureDirector.cs` L143, L179–187).
2. **Single-pawn and single-van lookups sit inside gameplay logic.** They are in GreyboxNpc, CrowdDirector, PoliceDirector, NpcRagdoll, ClinicLoop, CaptureDirector, CaptureFieldKit, CaptureGrabArbiter, GreyboxVanSeat and GreyboxVanCargo (Appendix A).
3. **Driving deactivates the pawn GameObject.** `GreyboxVanSeat.SetDriving` calls `SetActive(false)`, which would also disable its NetworkObject and its NetworkBehaviours.
4. **Runtime `AddComponent` builds a behaviour's layout at runtime:**
   - `CrowdWalker` (CrowdDirector L347);
   - `PoliceOfficer` (PoliceDirector L538);
   - GreyboxNpc adding its body, ragdoll, get-up, struggle and animation drivers (L280–290).

   NetworkBehaviours cannot be added at runtime. Non-network behaviours are fine, but every network component must be present in the scene or prefab.
5. **Static registries and events are used as the event bus:** `GreyboxNpc.All`, `GreyboxNpc.Incident`, `VanCargoSpace.All`, `CrowdDirector.AlertRaised`, `PoliceEvents.*`. They are fine on the server, but must not fire on pure clients from local simulation.
6. **Legacy `Input` everywhere in the map** (§2.1). It cannot be driven by the test driver's virtual devices, and some reads have no owner check, for example `GreyboxVanSeat` E (L102–107).
7. **Unseeded `Random` and physics queries in NPC, crowd and police decisions.** Clients cannot reproduce them, so the server must decide.
8. **Three systems write the van's inputs:** the seat/drive input, `GreyboxVanAutopilot` and `CaptureVanCapacity`.
9. **Money is in four places and is not saved** (§2.8).
10. **Patient ids are minted locally** (`PatientLifecycle.NewId`). On a pure client this would fork identities.

---

## 3. Target authority model

### 3.0 Principles

1. **Solo = host.** Once M1 lands, the map has no separate offline path. A solo game is a host that nobody joined.
2. **The server owns all shared, physical and world state.** Each owner client owns only its own:
   - KCC movement;
   - camera and listener;
   - phone UI, HUD and view models.
3. **Clients send intents, never state.** The server validates each intent:
   - the sender has an active player object;
   - reach is measured from the **server's** copy of that player;
   - a server raycast confirms line of sight;
   - the rules allow it;
   - sequence or press ids are current;
   - cooldowns hold.
4. **Results replicate through four channels:**
   - state SyncVars, for rare discrete changes;
   - NetworkTransforms, for simple moving bodies;
   - custom snapshot streams, for the van and ragdoll poses;
   - cue RPCs, for one-shots.
5. **Presentation is derived on every peer** from replicated state: the animator, faces, sounds, HUD, tie visuals and night lights. Clients never simulate shared bodies; their copies are kinematic.
6. **Carrier-relative frames.** Anything inside the moving van (players riding, NPC bodies) replicates in van-local coordinates.
7. **One stable identity.** An NPC keeps its `PatientId` string from the first knockdown. NetworkObject ids are per session only.
8. **World simulation is server-gated.** Crowd, police, cargo, registry, director and NPC brains are inert until the `OnStartServer` of a scene `WorldNet` NetworkObject. Pure clients never enable them.
9. **Trust model.** This is co-op among friends, so there is no anti-cheat. Validation exists to prevent desync and double-application (atomic events, ops §20.1), not cheating.

### 3.1 Session and scene topology

- **Scene loading.** Every peer loads the same map scene from the build. The NetworkManager lives in the scene, as it does in NetworkTest and i10, and scene NetworkObjects match by SceneId (FishNet reserialize).
- **Roles** come from the existing args (`-ov-host`, `-ov-client <ip>`, `-ov-port`) or from the NetworkSession panel. A proper main menu comes later.
- **Responsibilities after M0/M1:**

| Component | Role |
|---|---|
| `NetworkSession` (kept, split in M0) | Connection lifecycle and bind `0.0.0.0`. 4 slots, one map player per connection at 4 base spawn points around the B02 yard. Despawn on disconnect; kick the 5th. Keep the UDP port probe from CaptureDirector for dev runs. |
| `NetworkTestSpawner` (new, moved out of NetworkSession) | The NetworkTest scene's 8 test bodies, table and scalpel. |
| `CaptureDirector` (slimmed in M1) | Loses StartHost, ClientLoaded and the port probe. Keeps: server-side table spawn, registry and save/load; creating the HUD and kit for the **local** player. |
| `WorldNet` (new scene NetworkObject) | Hosts WorldClock, the shared funds, the wanted mask and the global cue channel, and enables the world simulation on the server. |

- **The scene pawn is removed from the map scene.** `Player_Map_Net_v01.prefab` is spawned per connection instead.

### 3.2 Player

- **Prefab.** `Player_Map_Net_v01` is generated by an editor builder (never by hand). It starts from `NetworkPlayer.prefab` (KCC, client-authoritative NetworkTransform, RemoteVisual) and adds the map components:
  - GreyboxKccPawn, GreyboxCargoRider, GreyboxInteractor, SeaReturnTracker, GreyboxPhone;
  - `NetworkInventory`, with InventoryInput and InventoryHud bound to it;
  - NetworkGrabber v2;
  - CaptureFieldKit.
- **Owner-only components:** KccFirstPersonInput, the camera and AudioListener, phone, HUDs, GreyboxInteractor input, CaptureFieldKit input, GreyboxCargoRider, SeaReturnTracker. `NetworkPlayer.SetLocalControl` disables them on non-owners; its list is extended.
- **Replicated:**
  - the NetworkTransform (position + yaw, 30 Hz);
  - view pitch/yaw (existing, 10 Hz);
  - `SyncVar<byte> Stance` {Stand, Stoop, Crouch, Seated, Riding}, written by the owner through a ServerRpc.
- **Server effects on a player** go to the owner as TargetRpcs:
  - `Knock(velocity)`: police baton, van hit, door shove;
  - `Teleport(position, yaw)`: arrest, sea return, ejection from the van;
  - `HoldTension(byte)`: carry slowdown and hand line.
- **New registries** replace the single-pawn lookups. These are concrete consumers, not scaffolding.

  | Registry | Where | Holds | Used by |
  |---|---|---|---|
  | `LocalPlayer` (static) | Client | `Pawn` and `Net`; set in `NetworkPlayer.OnStartClient` when `IsOwner`, cleared in `OnStopClient` | Presentation: `NpcRagdoll.Listener`, HUD visibility, phone, paint mode |
  | `PlayerRegistry` | Server | All `NetworkPlayer`s, with motor position, view direction, seat or carrier, stance | Gameplay: NPC flee, crowd visibility, police targets, arrest, witnesses |

- **Vans and players.** `RemotePlayer × Vehicle` collisions are already ignored (`OvLayers` L15–19). A van that hits a player at speed is therefore detected by server logic (overlap at speed), followed by a `Knock` to the owner. The owner's KCC keeps treating the van proxy as a mover (`PlayerPushPolicy`).

### 3.3 Van

**Driving.**
- **Server.** `VanController` runs only on the server: a dynamic Rigidbody with 4 WheelColliders. Clients keep a kinematic proxy with the WheelColliders and `VanController.FixedUpdate` off.
- **`VanNetwork`** is a NetworkBehaviour on the van's new NetworkObject:
  - `SyncVar<int> DriverClientId`, −1 when nobody drives.
  - `ServerRpc(RequireOwnership = false) RequestSeat(bool enter)`. The server checks that its copy of the motor is within 3.5 m of the driver door, that the seat is free, and, to get out, that the speed is 12 km/h or less. It picks the exit spot with the existing `GetOut` logic, then sends a `Teleport`.
  - `ServerRpc DriveInput(ushort seq, sbyte throttle, sbyte steer, bool handbrake)`, unreliable at the 30 Hz tick, from the driver's client only. The newest sequence wins. With no input for 0.3 s: throttle 0 and handbrake on (lag spike or disconnect).
  - Driver disconnect: `DriverClientId = −1`, handbrake on, doors left as they are (draft §3).
  - Server order of input writers: driver input, then the `CaptureVanCapacity` veto (order 200). The dev autopilot runs on the host only, and only with no driver.
- **`VanNetSync`** is a custom snapshot stream from the server to observers, unreliable:
  - **Rate:** 30 Hz while moving, 2 Hz at rest. The last rest snapshot is kept in a SyncVar for late joiners.
  - **Contents (about 50 B):**

    | Field | Bytes |
    |---|---|
    | Tick | 2 |
    | Position | 12 |
    | Rotation (FishNet's default 32-bit quaternion) | 4 |
    | Linear velocity | 12 |
    | Angular velocity | 6 |
    | Steer | 1 |
    | Wheel spin phase ×2 | 2 |
    | Throttle | 1 |
    | Bits: handbrake, engine on, horn | 1 |
    | Door openness ×5 | 5 |
    | ResetCount | 1 |

  - **Client playback:** buffer and interpolate 2–3 ticks behind (66–100 ms); extrapolate for at most 100 ms on loss.
  - **The proxy is a KCC `PhysicsMover`** whose goal pose is the interpolated pose. KCC players standing in or on the van are then carried locally (draft B5). The replicated velocity feeds the audio and the wheel visuals.
  - **Why not a FishNet NetworkTransform here:** velocity, steer, wheels and doors must share one timeline, and the PhysicsMover must be the only writer of the transform.
- **Latency.** The host driver has zero latency. A client driver waits about RTT/2 for its input to reach the server, plus RTT/2 + 66–100 ms of interpolation to see the result. That is about 70–110 ms on a LAN and 170–200 ms at 100 ms RTT.
  - Mitigation without prediction: the local steering wheel and front-wheel visuals follow local input at once, and the chase camera follows the interpolated van with no extra lag.
  - Measure it in M2 with FishNet's `LatencySimulator`.
  - Client-side prediction of a WheelCollider car is **not** recommended. WheelCollider state cannot be rewound, and rewinding means re-simulating the whole PhysX scene.
  - The fallback is Q1.

**Seat and the driver's body.**
- No more `SetActive(false)`. "Seated" means:
  - the KCC motor and input are disabled, and capsule collisions are off;
  - `Stance = Seated`;
  - the pawn's NetworkTransform position sync is paused (`SetSynchronizePosition(false)`, available in 4.7.3).
- **On the server**, the seated pawn's server-side transform is placed at the seat socket every tick, so distance observers, police and the crowd see the right position.
- **On every peer**, the driver's RemoteVisual is attached to the van's seat socket. The hip is at about (−0.49, 1.05, 0.72) van-local (draft). Head yaw comes from the replicated view yaw. This replaces `GreyboxDriverDummy` for remote drivers.
- **Camera.** Only the driver's own client switches its own camera to `VanCameraRig`.

**Doors.**
- **Server-only simulation:** `VanDoor.Step`, the blocking test and the pushes.
- **Requests:** `ServerRpc RequestDoor(byte door, bool open)`. It carries an explicit state, never a toggle (draft §3); the rear pair is one request.
- **Who may open a door:**
  - the driver, for the slide-door button (canon §151);
  - a player whose server-side motor is within 2.0 m of the door handle;
  - a passenger at the inside handle.
- **Clients** pose the doors from the replicated openness bytes, with `BlockMask = 0`: no forces and no nudges. The owner's KCC is moved by the proxy's door colliders like any mover.
- **The capacity veto** stays server-only. The requester gets a toast hint; nearby players get a cough cue.

**Passengers (players in the bay).**
- **Below about 6 km/h: free KCC walking.**
  - The owner's KCC is carried by the client's `PhysicsMover` proxy and replicated through the normal world NetworkTransform.
  - The offset error at 6 km/h is about 1.7 m/s × 0.1 s = 0.17 m.
- **Above about 6 km/h: "Riding" (recommended in Q2).**
  - The passenger snaps to the nearest free bay slot (4 kneeling or sitting slots). The KCC motor pauses.
  - Looking around is allowed, and so are the field kit and grabs on NPCs within reach.
  - `NetworkPassenger` replicates it with `SyncVar<sbyte> Slot` plus carrier = the van. Every peer places the passenger at `van.TransformPoint(slotPose)` on its own interpolated van.
  - Free KCC resumes when the van has stayed below 4 km/h for 1 s.
- **Validation position:** the server derives a riding passenger's motor position from the slot.
- **Flip or water:** the server decides (`GreyboxVanCargo.EjectAll` logic) and sends a `Teleport` to each passenger.

**NPC cargo.**
- **Server-only `GreyboxVanCargo`:** loading test, velocity matching, escapes, capacity and rough-driving costs.
- **Replication.** The NPC body stream (§3.4) carries a carrier reference. With `Carrier = van`, the pelvis pose is van-local, and clients render it relative to their own interpolated van.
  - A body resting in a moving van hardly moves in the van frame. The existing delta gate (2 mm / 0.6°) then sends almost nothing (a 1 Hz heartbeat).
  - In world space the same body would stream at full rate and would visibly lag the van by v × delay (1.7 m at 60 km/h).

**Upgrades and paint.**
- **Upgrades:** `SyncVar<byte>` for Engine, Brakes and Handling (CargoLevel in Stage B), written by the server after a shared-funds purchase. Every peer calls `TrySetLevel` (clients only need it for HUD and audio).
- **Paint** (after M9):
  - The painter commits strokes locally. `ServerRpc PaintStroke(stroke)` is reliable; at most 8192 dabs per stroke, about 64 KB, so FishNet splits large reliable messages.
  - The server applies and saves, then broadcasts `ObserversRpc ApplyStroke` (idempotent by stroke id). A late joiner gets the mask PNG and the journal through a `TargetRpc`.
  - Undo and wipe become commands.

**Audio.**
- **Engine:** derived on every peer from `VanNetSync` (throttle, speed, engine on = a driver is present).
- **Impacts:** server-side `OnCollisionEnter` (the VehicleImpactAudio logic) becomes a cue on the van's NetworkObject, at most 4 per second.
- **Horn:** an input bit, then a cue.

### 3.4 NPCs

**Identity.**
- Every NPC that can be captured is a NetworkObject from spawn. On the map (78 pool NPCs, templates, 8 crew, placed NPCs) these are **scene NetworkObjects**; the builders add `NetworkObject` + `NpcNetwork` at build time.
- **FishNet 4.7.3 behaviour, checked in the package sources:**
  - Inactive scene NetworkObjects are registered without being spawned (`ServerObjects.SetupSceneObjects`).
  - A despawned scene object is deactivated, not destroyed (`ManagedObjects`).
  - For the client-host, objects it does not observe get their renderers hidden (`SetRenderersVisible(false)`).

  So the director's `Take` and `Despawn` become `ServerManager.Spawn(nob)` and `ServerManager.Despawn(nob)`, keeping the existing scene pool.
- **`SyncVar<string> PatientId`:** empty until the first knockdown, when the server's `CaptureDirector.Ensure` sets it. Type and district are static per scene object.

**State (`NpcNetwork`).** One struct SyncVar of about 16 B, sent on change:
- `state` (NpcState), `phase` (StunPhase), `bodyMode` (none, capsule, seated, ragdoll);
- flags: fleeing, released, handsTied, feetTied, headBagged, alive, inCargo, asleep, struggling;
- `condition` (byte), `activity` (byte);
- `getUpKind` + `getUpStartTick`;
- `holderCount` (0–3);
- `carrier` (NetworkObject or none);
- `stunEndsTick`, instead of a per-frame countdown.

NPCs with a PatientId also get a `SyncVar<CaptureCard>` of about 24 B: residual, sleepRemaining, bloodPortions, bloodProgress, deathAge and the condition-loss tier, for target cards and HUD hints. Intrinsic grades stay server-side until inspection, matching the ops §12.1 hint rule.

**Body and pose.**
- **Animated or free.** The server's `CharacterController` moves the root. A server NetworkTransform on the root sends position + yaw only:
  - every 3 ticks (10 Hz) for walkers;
  - every tick while in capsule mode and moving.

  The NetworkTransform sends nothing at rest. Clients run `NpcAnimDriver.Compose` from the replicated state plus the speed of the interpolated root.
- **Ragdoll.** `NpcBodySync` is generalised from `OperationPatientRagdoll` (P6):
  - **Bodies.** The server has 11 dynamic bodies. Clients build kinematic copies on the first pose (`NpcRagdoll.Activate` without physics, like `StartRagdoll(false)`).
  - **Message, about 70 B:** the carrier frame (world or van); the pelvis pose in that frame (12 + 4 B); 10 local rotations of 4 B each, relative to the parent bone (linear joint axes are locked, so positions follow from the rig); a header.
  - **Compared with today:** the patient sends 11 × (Vector3 12 + Quaternion 4) + headers, about 190 B (FishNet's default writer packs a Quaternion into 32 bits).
  - **Rate (unchanged):** at most 20 Hz while something moved more than 2 mm or 0.6°, a 1 s heartbeat, and the last pose buffered for late joiners and new observers.
  - **Transitions** carry their reason (knockdown, wake-blend start, get-up clip + start tick), so clients run the same NPC wake blend from the last pose, as the patient snap does.
  - **Non-simulated bones** (about 54) stay frozen at each peer's local knockdown pose; this small cosmetic difference is accepted.
- **Server-only and local parts.** `NpcGetUp` and `NpcStruggle` run on the server; their visible result is the pose stream or a get-up clip started by tick. `NpcHeldProps` stays local cosmetic debris, triggered by state.

**Holders (up to 3 per NPC, canon §131).**
- **Grab request.** NetworkGrabber v2 sends `ServerTryGrab(requestId, NetworkObject target, byte part, Vector3 partLocalPoint, origin, dir)`.
  - The server resolves `NpcNetwork` → `INpcBody` → the part's rigidbody.
  - It re-raycasts from its own copy of the requester and requires the hit collider to belong to that part (or its foot box).
  - It claims through the existing `IGrabPointTarget.TryClaim(holder, point)`, with the server-side `NetworkGrabber` as the holder (claims compare by reference).
- **Server hold loop.** The new `ServerNpcHold` is a port of `PhysicsGrabber.HoldPoint` (L384+):
  - the target comes from the existing `ServerHoldTarget` stream (20 Hz, sequence, 0.8 s timeout);
  - velocity feed-forward uses the filter from `NetworkPhysicsBody.SetTarget`;
  - force comes from `GrabPhysicsSolver.TryCalculateRelativeGrounded` and is applied through `IGrabPointBodyGroup.ApplyHoldForce(part)`, with the 14 kg hold mass;
  - when the holder rides, the van-relative frame velocity is used.
- **Release.** `RevokeAll`, `Tear` and an invalid claim end in `ServerBodyReleased`, then `TargetReleased` (the existing path). A 4th grab request finds no free claim and gets `TargetGrabResult(null)`.
- **Hold tension** goes to the owner at 10 Hz, driving `ExternalSpeedScale`.
- **Collisions:** every NPC collider ignores the holder's capsule while held (the `IgnoreHolderCollisions` idea).
- **Visual lag.** On a client the held body appears 100–150 ms behind the hand. The mitigation is presentation only: a local hand-to-target line (draft §3) and an optional visual bias of the held bone toward the hand.

**Hits and field kit.** These are intent RPCs on `NpcNetwork`, following P4.
- **`RequestHit(part, point, dir, weaponId)`.** The server checks reach (2 m from WeaponStun + 0.6 m latency slack), the 0.6 s cooldown and line of sight. It then calls `GreyboxNpc.Hit` with attacker = the requester, for police attribution.
- **Hold actions.** `RequestTie(limb)` (1 s), `RequestDose` (0.5 units/s) and `RequestBlood`:
  - they stream `(pressId, holding)` like the table pointer, and the server accumulates the hold time;
  - the server validates reach (2.6 m), line of sight, `CaptureRules` (asleep, restrained, dead) and the requester's kit stock.
- **Kit stock is per player:** owner-only SyncVars (ties, barrel, stock, blood fill, bags), or consumable items in `NetworkInventory`, decided at M9.
- **Feedback.** Refusals go back as a TargetRpc hint id, reusing the Capture toast texts. Successes are cues on the NPC: zip, puff, cough.

**Table admission and after.**
- `CaptureTableBridge` stays server-only.
- `Destroy(npc.gameObject)` becomes `ServerManager.Despawn(npc NetworkObject)`. `ServerAdmit` spawns the patient prefab with the same PatientId and state; the cloud is a cue to observers.
- Hats and glasses are cosmetic spawns from that cue. If they become cleanup evidence (ops §18), they turn into WorldItems later.
- **Corpse handling (G35 is building it offline now).**
  - The body bag fits as a `NetworkPhysicsBody` prefab: one rigidbody, and the existing grab works unchanged.
  - Disposal is a server trigger at the river, lake or canal: Despawn, a splash cue, and the identity is released.
- Q6: keep the "cloud swap" in co-op v1.

**Server decisions that used one pawn:**
- Flee and scare: the nearest threat in `PlayerRegistry` (on foot within 7 m), or the van (faster than 5 km/h within 14 m).
- `NpcRagdoll.Listener` (bone tracking within 30 m of "the player"): any player within 30 m on the server; `LocalPlayer` on a client.
- F10 (`NpcRagdoll.Mode`) becomes a host-only dev command.

### 3.5 Crowd

- **Server-only:** CrowdDirector, CrowdWalker, CrowdWitness and the CrowdData slots.
- **Clients** see walkers as NPC NetworkObjects (§3.4): a NetworkTransform at 10 Hz plus the activity byte, with the animator driven by speed.
- **Pre-bake the components.** The builders (MapCrowdPlacer, MapPolicePlacer) add `CrowdWalker` and `PoliceOfficer` disabled, and the runtime enables them instead of calling `AddComponent`. `CrowdWalker.Release` disables itself instead of calling Destroy.
- **`Visible(feet, minDistance)` on the server.** A point counts as visible if any of these holds:
  - any player motor in `PlayerRegistry` is within the minimum distance;
  - the van is;
  - it is inside any player's view. The camera is at motor + eye height (1.6 m, or 1.2 m stooped) and looks along the replicated pitch/yaw (already sent at 10 Hz). The view cone is FOV + 10° margin, up to 120 m, followed by the existing Linecast.

  Cost: 4 players × 20 spawn points × 4 Hz = 320 cone tests and at most 320 Linecasts per second.
- **Population stays global:** 61 by day, 57 in the evening (§4.5).
- **Evening** is derived from WorldClock on the server. F11 stays a local overlay; F12 becomes host-only dev.
- **Witnesses and alerts** run on the server. Hint toasts are cues to observers.

### 3.6 Police

- **Server-only:** PoliceDirector, PoliceUnit, PoliceCarMotor and PoliceOfficer.
- **Cars** are NetworkObjects with a server NetworkTransform at 30 Hz and `SyncVar<byte> UnitState`. Clients derive the siren, lights and label from the state.
- **Crew and foot officers** are NPC NetworkObjects (§3.4) with `SyncVar<byte> OfficerState`.
- **Suspects.** `VanSuspect` stays (one shared van). `PawnSuspect` becomes `PawnSuspects[clientId]`.
  - `Attacker` is the player passed by `RequestHit` or the capture code, with no distance guess.
  - `PawnInVan` is per player, from the seat and passenger state.
- **Effects on players.** `Pawn.Knock` becomes a `Knock` to that owner. Arrest means the server applies the penalty (Q4), then sends a `Teleport` to the station, and raises `PoliceEvents.ArrestRequested` on the server.
- **Wanted HUD:** `SyncVar<byte> WantedMask` on WorldNet, one bit per player plus a van bit. Heat stays hidden on the server.
- **Rams and slapstick:** server collisions between a police car and the van become cues.
- **Dev keys** (HUD, HomeBase cycling) work on the host only.

### 3.7 Time of day

- **`WorldClock` on WorldNet (server):**
  - `SyncVar<double> AnchorHours` (day × 24 + hour);
  - `SyncVar<uint> AnchorTick`;
  - `SyncVar<float> HoursPerSecond`;
  - `SyncVar<bool> Running`.
- **Clients** compute every frame `hours = AnchorHours + HoursPerSecond × (Tick − AnchorTick) × TickDelta`. The server re-anchors on scrub or pause and every 30 s.
- **Sky.** `SkyClock22` keeps working on every peer with `running = false`. A small adapter `SkyClockNetDriver` (in Network/, so the versioned Sky folders stay untouched) sets its hour each frame.
- **New values:** a day count (hours past 24 roll over) and `GameSeconds` for `BuyerRules`, both on the server.
- **Debug keys** (scrub, pause) are host-only.
- **Rules (spec D13, ops §14):** closing the host freezes time; a client leaving does not stop it.

### 3.8 Saves, join and leave

- **Host only.** These are gated on `IsServerStarted`: `CaptureDirector.Load`/`Save`, `ClinicSave`, `PatientRegistry` id minting, `VanPaintStorage` writes and `ClinicLoop`. Clients write nothing under `persistentDataPath/OnlyVolunteers`; photos stay in their own local folder.
- **Save v2** is a new `CaptureSaveData` revision; v1 stays readable.
  - **World block:** van pose, doors, upgrades and paint reference; NPCs; the table; clock hours + day; completed ids; shared funds; buyer state; wanted and heat.
  - **Per-player blocks**, keyed by a stable player id (Q5): position, yaw, seat or slot; field kit; inventory slots; personal XP.
- **Player id.** Each client keeps a GUID in PlayerPrefs (`ov.playerId`) and sends it once after connecting (`ServerRpc Hello(playerId, displayName)`). The host maps connection → player id. Steam ids come later.
- **Join mid-session.** The player spawns at the saved block's position if one exists, otherwise at a base spawn. Everything else arrives through SyncVars, BufferLast and scene object spawn payloads.
- **Leave.** Existing holds are released; the driver's seat is freed with the handbrake on; the passenger slot is freed; a carried NPC drops where he is (D13). Kit and inventory stay in the host's per-player block.
- **Host leaves.** The session ends for everyone; there is no host migration (Q8). The host autosaves on quit (the existing `OnApplicationQuit`) and every 60 s.

### 3.9 Phone and economy

- **One shared business fund** (ops §15.1; buyers: "Деньги поступают в общий фонд").
  - `SyncVar<long> FundsCents` on WorldNet.
  - Every spend and receipt is a server transaction: atomic and idempotent by transaction id, as `BuyerTransactions` already does with `ConfirmationId`.
  - It replaces `PhoneWallet`, `LocalInventory.Cash` on the map and `NetworkInventory.cash` (Q4).
- **Team cash rule (Vadim, 2026-10-19):** income from one sale/reward event is credited to the shared fund once at its final team amount, regardless of party size; never multiply it by the number of players. For a cash penalty, let `N` be the number of players in the active team snapshot for the incident, `K` the number of players who receive an individual penalty, and `Xᵢ` each player's solo-equivalent penalty: deduct `Σ(Xᵢ / N)` from the shared fund. Thus one affected player in a four-player team costs `X/4`; four separately affected players each costing `X` total `X`. A one-time incident fine is one `X/N` deduction. The server records `N`, affected player IDs and the transaction ID with the outcome so reconnects or duplicate requests cannot change or repeat it. Purchases, bills and voluntary bribes are charged once at their full listed cost; item confiscation, respect and XP follow their own rules.
- **The phone UI stays per player and local.**
  - Buyer contacts, threads and orders are server world state (`BuyerRules`), replicated as a compact read model: a JSON SyncVar sent on change, which is rare.
  - Purchases go through `ServerRpc Purchase(itemId, txId)`.
  - Photos and the map camera stay local.
- **Negotiator.** The player who confirms a buyer meeting is its negotiator (BUYERS v02), and the sale is idempotent by `ConfirmationId`.

### 3.10 Sound and VFX events

| Source | Examples | How it reaches peers |
|---|---|---|
| Replicated state, computed locally | Engine, siren, remote players' footsteps, faces and speech from `NpcState`, tie visuals, night lights | Nothing extra to send |
| Server events | NPC scream, gasp, thud, hurt; door latch and stall; van impact; police whistle, hit, thud; zip; puff; cough; disposal splash; cash register | `ObserversRpc Cue(ushort sfxId, byte variant, quantized local point)`, unreliable, on the **source** NetworkObject, so FishNet's observers filter by distance for free |
| Local physics on each peer | WaterBodyAudio splashes of interpolated bodies; UI sounds | Stays local |

- **Cooldowns.** The server keeps a per-(source, sfxId) cooldown that mirrors `Sfx`'s per-id cooldowns.
- **Budget.** At most 30 cues/s × about 14 B, so 0.4 KB/s in the worst case.
- **Ambience** is unchanged and local; only the owner's camera has an AudioListener.

### 3.11 Authority matrix

| System | Simulated by | Replicated through | Client-only presentation |
|---|---|---|---|
| Player movement | Owner client (KCC) | Client-auth NetworkTransform 30 Hz; view 10 Hz; `Stance` | Camera, HUD, phone, view models |
| Van | Server (WheelColliders) | `VanNetSync` 30 Hz; seat and upgrade SyncVars; door requests | Wheels, steering wheel, engine audio, chase camera |
| Passengers | Owner (slow) / van-local slot (fast) | NetworkTransform (slow) / `NetworkPassenger.Slot` (fast) | Body on the slot |
| NPC brain and state | Server | `NpcNetwork` state; `CaptureCard` | Animator, face, ties, props |
| NPC body | Server physics | Root NetworkTransform (animated, capsule); `NpcBodySync` (ragdoll, carrier-relative) | Kinematic bone copies, wake blend |
| Holds (≤3) | Server forces | Grab RPCs (P3 + part); `HoldTension` | Hand line |
| Field kit | Server rules | Intent RPCs; `CaptureCard`; hints and cues | Tool view models, rings |
| Crowd | Server | NPC NetworkTransform 10 Hz + activity; observers within 200 m | Animator, labels |
| Police | Server | Car NetworkTransform 30 Hz + state; officers as NPCs; `WantedMask` | Siren, lights, labels |
| Table and operation | Server (existing) | P4–P6 (existing) | Existing |
| Clock | Server | WorldClock anchor | Sky, night lights, fog |
| Save | Host only | — | — |
| Money and buyers | Server transactions | `FundsCents`; buyer read model | Phone UI |
| Sounds | Server cues + local state | Cue RPCs on sources | Ambience |

---

## 4. Bandwidth, CPU and interest management

### 4.1 Assumptions

| Item | Value | Source |
|---|---|---|
| FishNet tick | 30 Hz | TimeManager default `_tickRate = 30`; no TimeManager override in the scenes |
| Physics step | 60 Hz | `ProjectSettings/TimeManager.asset`, Fixed Timestep 0.016667 |
| Transport | Tugboat (LiteNetLib) over UDP | — |
| Packets | Messages are batched per tick into about one packet per connection | — |
| Packet overhead | ≈36 B (IP/UDP 28 + LiteNetLib about 4 + FishNet about 4), so ≈1.1 KB/s per connection while anything is sent every tick | — |
| Vector3 | 12 B, unpacked | FishNet `Writer` |
| Quaternion | 4 B (`WriteQuaternion32` is the `[DefaultWriter]`) | FishNet `Writer` |
| RPC header | ≈4–6 B | — |
| NetworkTransform update (position + yaw) | taken as 16 B | — |

Every figure below is an **estimate**. M0 adds measurement through FishNet's `StatisticsManager.TryGetNetworkTrafficStatistics` → `OnNetworkTraffic`, and each milestone checks its own number.

### 4.2 Cost per entity, downstream to one observing client

| Entity | Message | Rate | B/s |
|---|---|---|---|
| Remote player | NetworkTransform, 16 B | 30 Hz | 480 |
| Remote player view | 10 B | 10 Hz | 100 |
| Van, moving | `VanNetSync`, ≈55 B | 30 Hz | 1,650 |
| Van, at rest | ≈55 B | 2 Hz | 110 |
| Walker (animated NPC) | NetworkTransform, 14 B | 10 Hz | 140 |
| Capsule NPC, moving | NetworkTransform, 16 B | 30 Hz | 480 |
| Ragdoll, moving, today's format | ≈190 B | 20 Hz | 3,800 |
| Ragdoll, moving, compressed (§3.4) | ≈70 B | 20 Hz | 1,400 |
| Ragdoll at rest, in its carrier frame | heartbeat | 1 Hz | 70–190 |
| Police car | NetworkTransform, 16 B | 30 Hz | 480 |
| NPC state or capture card | 16–24 B | on change, ≈0.2 Hz | ≈5 |
| Cues | ≈14 B | at most 30/s in total | ≤420 |
| Operation table snapshot | ≈3 KB of JSON | at most 15 Hz, while it changes | ≤45,000 |
| Table remote cursor | ≈20 B | 20 Hz per operating player | 400 |

### 4.3 Scenario totals

| Scenario | Per client, downstream | Host upstream (×3 clients) |
|---|---|---|
| A. Typical capture | ≈12.5 KB/s (≈9.8 compressed) | ≈30–38 KB/s, about 0.3 Mbit/s |
| B. Chaos | ≈37 KB/s | ≈110 KB/s, about 0.9 Mbit/s |
| C. Operating at the base | ≈50 KB/s | ≈150 KB/s, about 1.2 Mbit/s |

**A. Typical capture.** 4 players in one district.

| Item | KB/s |
|---|---|
| 3 remote players | 1.7 |
| Moving van | 1.65 |
| One NPC carried by two players | 3.8 (1.4 compressed) |
| Two NPCs resting in the moving van, **van-local** | 0.4 (0.14 compressed) |
| 20 walkers within 200 m | 2.8 |
| 1 police car | 0.5 |
| State and cues | 0.5 |
| Packet overhead | 1.1 |

The same two cargo bodies streamed in world space would cost 7.6 KB/s. This is the bandwidth argument for carrier-relative frames, besides the visual one.

**B. Chaos.** 6 ragdolls flying (23), 61 walkers in view on the beach (8.5), 2 police cars (1), the van and players (3.4), overhead (1.1).

**C. All 4 operating at the base.** Scenario A without van motion, plus the table snapshot (at most 45) and cursors (1.2). The JSON snapshot is the largest single cost: optimisation O1.

**Client upstream is at most about 3 KB/s:**

| Item | KB/s |
|---|---|
| Own NetworkTransform | 0.5 |
| View | 0.1 |
| Hold target (20 Hz × 20 B) | 0.4 |
| Drive input (30 Hz × 10 B) | 0.3 |
| Table pointer (20 Hz × 30 B) | 0.6 |
| Packet overhead | 1.1 |

**Conclusion.** Even scenario C uses about a quarter of a 5 Mbit/s home upload. Bandwidth is not the constraint; latency feel (driving and carrying) is.

### 4.4 CPU

- **Host simulation.** It is the same world simulation the solo game runs today: the global crowd of 61, the police, the van and at most 12 ragdolls (`NpcRagdoll.Cap`). Networking does not multiply it.
- **New work on the host:**
  - 3 kinematic remote-player replicas;
  - at most 4 server hold loops;
  - ragdoll pose encoding (12 × 11 bones × 20 Hz);
  - NetworkTransform serialisation for about 90 objects × 3 connections;
  - distance observers for about 90 objects × 4 connections, on a timed interval;
  - crowd visibility for 4 players (about 320 cone tests and Linecasts per second).

  Estimate: at most 1 ms per frame in total. M6 measures it with Profiler markers on `NpcBodySync`, `VanNetSync` and the ObserverManager.
- **Host rendering** gets cheaper than today. FishNet already hides the renderers of objects the host's own client does not observe. Optimisation O3 also culls the Animators of server NPCs that are outside every player's 200 m.
- **Clients** run no crowd, police or NPC brains and no NPC physics. They animate the roughly 25 NPCs they observe and keep kinematic bone copies only for ragdolls in range. Clients are cheaper than the host, but each still loads the whole 33 MB map scene.
- **Ragdoll cap:** keep `Cap` = 12 on the server. The van carries 3 bodies (5 with upgrades); typical play has at most about 6 active ragdolls.

### 4.5 Interest management on the 2–2.5 km map

Add an `ObserverManager` to the scene NetworkManager with **no** default conditions, so an object without a `NetworkObserver` is seen by everyone. Then add a `NetworkObserver` per class:

| Class | Count | Condition | Notes |
|---|---|---|---|
| Players | 4 | none (global) | |
| Van | 1 | none | needed for HUD, map and chases |
| WorldNet | 1 | none | clock, funds, wanted, global cues |
| NPCs: walkers, captured, officers | ≤78 + 8 + 4 | `DistanceCondition` 200 m, hide at +20% (240 m) | Distance to each connection's player object. Captured NPCs in the van move with it |
| Police cars | 4 | `DistanceCondition` 500 m | sirens and chases |
| Table, tools, patient, organs, bags | ≈12 per base | `DistanceCondition` 150 m | the up-to-45 KB/s snapshot then reaches only players at the base |
| World items, body bags | few | `DistanceCondition` 150 m | |

- **Seated and riding players.** The server keeps their server-side transform at the seat or slot (§3.3), so their distance conditions follow the van.
- **Re-entering range.** FishNet re-spawns the scene object on that client with its current SyncVars, and the BufferLast pose restores a lying ragdoll. The burst is about 20 NPCs × 350 B ≈ 7 KB, once.
- **If the ObserverManager costs more than 0.3 ms** in the profiler, switch NPCs to `GridCondition`, which needs a `HashGrid` on the NetworkManager. Both conditions exist in 4.7.3.
- **Population rule.** Keep the crowd global and fixed: 61 walkers by day, 57 in the evening, plus police. Do **not** create per-player bubbles. The total simulation then stays flat with player count, and every player finds a living city wherever they go. Revisit only if the host profiler disagrees.

### 4.6 Optimisation queue (only after a measurement asks for it)

| # | Optimisation | Effect |
|---|---|---|
| O1 | Operation table snapshot: a binary struct with static and dynamic parts split, sent at 10 Hz | ≈ −80% table traffic |
| O2 | Ragdoll pose compression: pelvis pose + 10 local rotations | ≈ −63% per moving ragdoll |
| O3 | Cull server NPC Animators outside every player's 200 m | host CPU |
| O4 | Walkers beyond 100 m at interval 4 (7.5 Hz) via `NetworkTransform.SetInterval` | ≈ −25% crowd traffic |
| O5 | Van velocities as half floats | −12 B per van snapshot |

---

## 5. Migration milestones

Each milestone below gives its goal, scope and files, risks, the host+client acceptance checks (two-process runs, harness in §6), effort in agent-days (one worker session with verification ≈ one day), its tag, and what it depends on.

### Milestone overview

| # | Milestone | Effort (agent-days) | Tag | Depends on |
|---|---|---|---|---|
| M0 | Groundwork: harness, session split, input wrapper, sandbox scene | 4–5 | GPT-safe, with Claude review of the session split | G35 accepted |
| M1 | Players on the map (solo = host) | 5–7 | Claude-only (the lookup sweep can go to GPT) | M0 |
| M2 | Van: server-simulated driving, seat, doors | 6–8 | Claude-only | M1 |
| M3 | Players in the cargo bay | 4–5 | Claude-only | M2 |
| M4 | Networked NPCs, capture, 3-holder carry, field kit | 8–10 | Claude-only | M1 |
| M5 | Loading into the moving van, delivery to the table | 6–8 | Claude-only (cue and body-bag wiring GPT-safe) | M3, M4 |
| M6 | Crowd | 5–7 | Mixed | M4 |
| M7 | Police v1 | 5–7 | Claude-only (state → presentation GPT-safe) | M2, M6 |
| M8 | World clock, sky, cues and audio | 2–3 | GPT-safe | M1 |
| M9 | Saves, shared economy, phone | 5–7 | Mixed | M5, M8 |

**Totals.** M0–M5 (the core loop in co-op) take 33–43 agent-days; all ten take 50–67.

**Order.** Work stays sequential on main (TEAM_WORKFLOW). The one safe parallel track is M8, run beside M2–M4 (different files).

### M0 — Groundwork: harness, session split, input wrapper, sandbox

**Goal.** Make networked map work testable before any gameplay change.

**Scope:**
- **Harness.** `Working/Reviews/Network/run-net.ps1` (new, §6.2) and `Working/Reviews/Network/tools/compare_traces.py` (new). This is the only M0 item that can start during G35, because it is outside Assets.
- **Session split.** `Network/Scripts/NetworkSession.cs` keeps the lifecycle and player spawns. The test spawns move to the new `Network/Scripts/NetworkTestSpawner.cs`, and `Scenes/NetworkTest.unity` is rewired (by a builder or by the lead).
- **Dev scripts (new, dev-only)** in `Network/Scripts/Dev/`: `NetScenarioDriver.cs`, `NetTestBarrier.cs`, `NetTrafficLog.cs`, and `NetArgs.cs`, which maps `-ov-latency` and `-ov-loss` onto `TransportManager` → `LatencySimulator`.
- **Input wrapper.**
  - Extend `Operation/Stage1/Scripts/OpsInput.cs` to the map's keys and mouse delta. It is an **OR-wrapper** (legacy `Input` OR the virtual devices, the pattern `NetworkGrabber` already uses for LMB), so player feel does not change.
  - Route through it: `Player/Scripts/KccFirstPersonInput.cs`, `Player/Scripts/Physics/PhysicsGrabber.cs`, `Map/Scripts/GreyboxInteractor.cs`, `Map/Scripts/GreyboxVanSeat.cs`, `Vehicles/Van/Scripts/VanDriveInput.cs`, `VanCameraRig.cs`, `UI/Phone/Scripts/PhoneController.cs`, `PhoneHome.cs`, `MapApp.cs`.
- **Sandbox scene.** `Network/Editor/MapNetSandboxBuilder.cs` (new) builds `Scenes/Dev/MapNet_Sandbox_v01.unity`. It is the canon §133 "NPC + VAN FUN TEST" slice:
  - a flat 200 × 200 m area with a road loop;
  - the van and 4 player spawns;
  - 3 Buddy NPCs, a lamp post, a fence and a bench;
  - a table spawn;
  - NetworkManager + NetworkSession + ObserverManager.

  It is built from existing prefabs and never edits map scenes.

**Risks.** The input wrapper touches movement code; the OR-wrapper keeps the scaling unchanged. The session split may regress NetworkTest.

**Acceptance:**
- `run-net.ps1 -Scenario net-m0-join` with 1 client and with 3 clients: every process logs `RESULT PASS`; the host counts N+1 players; RTT is logged.
- With `-LatencyMs 100` the logged RTT rises by about the configured delay.
- Both logs print `NET up/down KB/s` once per second.
- **Regression:**
  - ops two-process `net02` (host 37 / client 26 PASS) and `net04` (37 / 22) still pass through `run-net.ps1`;
  - ops PlayMode 7/7;
  - the EditMode suite.
- `CaptureDeliveryPlayTests.FullLoop` still passes, now pressing Q and E through virtual keys instead of the scripted fallbacks.

**Effort:** 4–5. **Tag:** GPT-safe (harness, wrapper, builder), with Claude review of the session split.

### M1 — Players on the map (solo = host)

**Goal.** Up to 4 players walk the map together; the solo game is a host.

**Scope:**
- **Player prefab.** `Network/Editor/MapNetPlayerBuilder.cs` (new) builds `Network/Prefabs/Player_Map_Net_v01.prefab` (§3.2).
- **`Network/Scripts/NetworkPlayer.cs`:**
  - map mode: the owner-only list is extended, the phone and HUD come from GreyboxPhone (no second phone);
  - `Stance` SyncVar;
  - `Knock`/`Teleport` TargetRpcs;
  - the static `LocalPlayer`.
- **New:** `Network/Scripts/PlayerRegistry.cs`, and `Network/Scripts/WorldNet.cs` (server gating of the world simulation).
- **`Capture/Scripts/CaptureDirector.cs`.** StartHost, ClientLoaded, the port probe and the scene pawn are removed. The table, registry and save stay on the server; the HUD and kit go to `LocalPlayer`.
- **Single-pawn lookups replaced** (Appendix A):
  - GreyboxNpc L294–296; CrowdDirector L144–145, L372;
  - PoliceDirector L160–168, L469; NpcRagdoll L974–977; ClinicLoop L66–71;
  - CaptureFieldKit; CaptureGrabArbiter; VanPaintMapMode L43; InventoryInput L95.
- **New scene revision.** `Network/Editor/MapNetSceneBuilder.cs` builds `Map_Look_v19_Play_i11_net.unity` from the scene G35 leaves accepted. It removes the scene pawn and adds NetworkSession, ObserverManager, WorldNet and 4 spawn points. i10 is never edited.
- **World simulation is enabled only by `WorldNet.OnStartServer`.** On pure clients the crowd, police, cargo and registry stay off, so clients see an empty city until M4/M6. That is an accepted intermediate state.

**Risks:**
- many files touched;
- the capture tests expect the scene pawn;
- the KCC on the RemotePlayer layer can lose `Vehicle` from its collidable layers and fall through the van floor (`OvLayers` L15–19);
- ownership mistakes are silent, so the checks log them.

**Acceptance** (sandbox first, then i11):
- **2 processes.** The host spawns at slot 0 and the client at slot 1. Each walks a 10 m square while the other watches. The remote position error is at most 0.3 m after 0.2 s of settling, with traces compared by server tick.
- **4 processes.** 4 distinct pawns and OwnerIds; `GiveOwnership` is called 0 times.
- **Stance.** A client crouches; the host sees `Stance = Crouch` within 0.2 s.
- **Disconnect.** The host despawns a disconnected client's pawn within 1 s; reconnecting gives a new pawn.
- **Local UI.** The phone opens only in the process that pressed Tab, and each process has exactly one HUD.
- **Pure client.** 0 enabled `CrowdWalker`/`PoliceUnit` components and 0 locally simulated Down NPCs.
- **Solo host.** `CaptureDeliveryPlayTests`, updated for the spawned pawn, pass.

**Effort:** 5–7. **Tag:** Claude-only. The mechanical lookup sweep from Appendix A can go to GPT.

### M2 — The van: server-simulated driving, seat, doors

**Scope:**
- **New:** a NetworkObject on the map van (added by the scene builder), `Vehicles/Van/Scripts/VanNetwork.cs` and `VanNetSync.cs`. A KCC `PhysicsMover` drives the client proxy.
- **Changed:**

  | File | Change |
  |---|---|
  | `VanController.cs` | FixedUpdate only on the server |
  | `VanDoor.cs` | Blocking only on the server; clients posed from bytes |
  | `VanDriveInput.cs` | Sends `DriveInput` instead of writing the van |
  | `Map/Scripts/GreyboxVanSeat.cs` | `RequestSeat`; seated mode instead of `SetActive(false)` |
  | `GreyboxDriverDummy.cs` | Remote driver visual |
  | `GreyboxVanAutopilot.cs` | Host only |
  | `Capture/Scripts/CaptureVanCapacity.cs` | Server only |
  | `Vehicles/Scripts/VehicleEngineAudio.cs` | Reads `VanNetSync` (L175 `Driving`) |
  | `VehicleImpactAudio.cs` | Server cue |
  | `Map/Scripts/SeaReturnTracker.cs` (on the van) | Server only |
  | `VanInteriorColliders.cs` | Slide toggle on the server; identical colliders on every peer |

**Risks:**
- the client driver's feel under latency;
- jitter of the server van while nobody drives;
- replicating door stalls;
- PhysicsMover and KCC on clients;
- joining late while the van moves.

**Acceptance:**
- **`net-m2-host-drives`.** The host drives route v06 (B02 → bridge, 253 m) at 45 km/h. The client's proxy path deviates at most 0.3 m from the host path at equal server ticks. Arrival is within ±5% of the offline 31.0 s.
- **`net-m2-client-drives`.** The client drives the same route and ARRIVES. Logged at 0, 100 and 150 ms simulated latency: the delay from the first throttle sample to client proxy speed above 1 m/s. Target at 0 ms: at most 150 ms; other values are reported for Q1.
- **Seat race.** Host and client request the seat in the same tick: exactly one `DriverClientId`, and the loser gets a refusal hint.
- **Driver disconnect** at 40 km/h: the host's van is below 1 km/h within 4 s.
- **Doors.** A client opens the slide door: host openness reaches 0.95 within 1 s. A resting ragdoll in the doorway stalls the closing door on the server, and the client's door pose differs by at most 0.05.
- **Exit** is refused above 12 km/h and allowed below.
- **Late join** with the van at 30 km/h: the new client's proxy is within 0.5 m of the host after 1 s, and the door bytes are equal.
- **Upgrades.** Each level change on the host is seen by the client (HUD, audio). The host's route v06 time stays within 5% of the offline time for each level.

**Effort:** 6–8. **Tag:** Claude-only.

### M3 — Players in the cargo bay

**Scope:**
- `Map/Scripts/GreyboxCargoRider.cs` (owner side; riding slots).
- New `Vehicles/Van/Scripts/NetworkPassenger.cs`.
- `VanCargoSpace.cs` (slot poses).
- If still missing, the Stoop stance and the narrower KCC radius (draft B1) in `KinematicCharacterController/ExampleCharacter/Scripts/ExampleCharacterController.cs`, with motor tuning untouched.
- `GreyboxVanCargo.cs` (`EjectAll` sends teleports).

**Risks:**
- the KCC on a kinematic PhysicsMover at low speed;
- popping when entering or leaving a slot;
- crouch clearance at the door arches (1.04 m against the KCC's 1.0 m diameter, draft risk).

**Acceptance:**
- **`net-m3-ride`.** Two clients enter the bay at rest. The host drives for 60 s at up to 60 km/h with turns. On every peer each passenger's rendered position stays inside the bay box (+0.1 m) in every frame. Nobody falls out, and `Stance = Riding` shows on all peers.
- **Stop.** Both passengers walk again. One opens the slide door with the inside handle, and it opens on all peers.
- **Flip** (scripted torque on the server). Both passengers are teleported out by their own clients within 1.5 s, onto the ground outside the van.
- After M4: a riding client tops up an NPC in the bay with the syringe (reach is validated from the slot).

**Effort:** 4–5. **Tag:** Claude-only.

### M4 — Networked NPCs, capture and the 3-holder carry (sandbox)

**Scope:**
- **New** in `Characters/Npc/Scripts/Net/`: `NpcNetwork.cs`, `NpcBodySync.cs` (generalised from `OperationPatientRagdoll`), `ServerNpcHold.cs`.
- **Changed:**

  | File | Change |
  |---|---|
  | `Map/Scripts/GreyboxNpc.cs` | Server-only brain; threat from `PlayerRegistry`; incidents carry the attacker |
  | `GreyboxNpcBody.cs`, `Characters/Npc/Scripts/NpcRagdoll.cs` | Server and client modes, kinematic copies, `Listener` |
  | `NpcAnimDriver.cs` | Fed from replicated state on clients |
  | `NpcGetUp.cs`, `NpcStruggle.cs` | Server only |
  | `Network/Scripts/NetworkGrabber.cs` | Part index, NPC targets, tension |
  | `Map/Scripts/GreyboxInteractor.cs` | `RequestHit` |
  | `Capture/Scripts/CaptureNpc.cs` | Server-side capture state |
  | `CaptureFieldKit.cs` | Requests + per-player stock |
  | `CaptureGrabArbiter` | Removed: NetworkGrabber v2 handles props and NPCs |

- `OperationPatientRagdoll` switches to `NpcBodySync` (same wire behaviour), but only once the ops v04 suite passes on the new code.

**Risks.** The highest of the plan: ragdolls with remote holders under latency, the rubber-band carry feel on clients, the `RevokeAll`/`Tear` edge cases, the ragdoll cap, and pose compression artefacts.

**Acceptance** (sandbox; host + 2 clients, plus a 4th process where noted):
- **`net-m4-hit`.** Client 1 punches NPC A: Down on all peers within 0.3 s with the same `bodyMode`; the host log shows attacker = client 1.
- **`net-m4-carry3`.**
  - Host, client 1 and client 2 grab NPC A's collar, left calf and right calf: server `holderCount = 3`.
  - A 4th process's grab request is refused.
  - They carry him 20 m to a marker: the server's pelvis ends within 1.5 m of the marker, and each client's pelvis is within 0.25 m of the server's at the same tick.
- **Disconnect mid-carry.** Client 2 disconnects: its claim is released within 1 s, `holderCount = 2`, and the carry continues.
- **Wake while held.** `RevokeAll` sends `TargetReleased` to every holder; the NPC stands and flees on all peers.
- **`net-m4-kit` (CD-10).**
  - Client 1 ties the hands (1 s hold) and injects him to sleep: the server shows `restraints.hands = true` and `Sleeping`, and the host's card matches the client's.
  - Blood is refused while he is awake and unrestrained; only the requester gets the hint.
- **Late join.** A client that joins while NPC A lies ragdolled sees his pelvis within 2 cm of the host's.
- **Measured:**
  - a moving ragdoll costs at most 1.6 KB/s per observer compressed, or 4 KB/s in today's format;
  - clients hold 0 dynamic NPC bodies (logged);
  - stale hold targets are rejected (the sequence test from the feel probe).
- **Offline regressions on the solo host:** NPC Loading Test 19/19; Ragdoll Smoke Test at its 31/34 baseline (r6, r6b, r7 already failing).

**Effort:** 8–10. **Tag:** Claude-only.

### M5 — Loading into the moving van and delivery to the table

**Scope:**
- `Map/Scripts/GreyboxVanCargo.cs` (server only; sets the carrier on NPCs) and the carrier frame in `NpcBodySync`.
- `Capture/Scripts/CaptureVanCapacity.cs`.
- `CaptureTableBridge.cs` (Despawn + cue) and `CaptureCloud.cs` (cue-driven).
- G35's body bag and disposal: a `NetworkPhysicsBody` prefab and a server trigger.
- i11: NPC NetworkObjects on the placed NPCs the loop uses.

**Risks:**
- bodies inside a moving server van, now with remote holders whose targets lag;
- popping on clients at the carrier switch (load and unload);
- admission while two players hold the NPC.

**Acceptance** (`net-m5-loop`, host + client, i11 map, Hamlet → the B02 shed):
1. The client knocks out an NPC; two players carry him to the van and load him through the slide door. Server `InCargo` is set within 2 s of release.
2. The client closes the slide door, and the host drives 300 m at up to 40 km/h.
   - On the server every loaded body stays `InCargo`.
   - On the client every loaded pelvis stays within the bay box + 0.1 m in every frame (van-local check).
3. A 4th body: the doors refuse and the van stalls on both peers (CD-08).
4. Opening the door at a stop with an awake NPC inside: he escapes on both.
5. Unload and two-player carry to the table, then admission (CD-01):
   - the same `PatientId` on host and client;
   - the cloud cue is seen on both;
   - the NPC object is despawned and the patient spawned.
6. The client joins PREP, closes two straps and makes the belly cut. The host extracts one kidney: the organ item exists exactly once, with the same id on both (P7).
7. If G35 has delivered the body bag: the client bags a corpse, the host carries the bag to the canal, and disposal despawns it on both.

**Effort:** 6–8. **Tag:** Claude-only (cargo physics in a moving frame); the cloud cue and body-bag wiring are GPT-safe.

*After M5, the core loop is co-op.*

### M6 — The crowd on the network

**Scope:**
- `Map/Editor/MapCrowdPlacer.cs` and `Police/Editor/MapPolicePlacer.cs` pre-bake `NetworkObject`, `NpcNetwork`, a disabled `CrowdWalker`/`PoliceOfficer` and a 200 m `NetworkObserver`.
- `Map/Scripts/Crowd/CrowdDirector.cs`:
  - server only;
  - `Spawn`/`Despawn` of scene objects;
  - `Visible()` over `PlayerRegistry`;
  - Evening from WorldClock.
- `CrowdWalker.cs`: `Release` disables the component. `CrowdWitness.cs` runs on the server.
- The scene NetworkManager gets an ObserverManager; i11 is rebuilt (or i12 made).

**Risks:**
- builder changes need FishNet's scene-object reserialize, or FishNet logs an error and skips the object (`WasActiveDuringEdit`, `ServerObjects` L474);
- 90 more scene NetworkObjects in a 33 MB scene;
- how walkers look on clients when speed comes from interpolation.

**Acceptance** (`net-m6-crowd`, host + 3 clients placed in Hamlet, Rough and Downtown):
- For 5 minutes, checked every 10 s, each client observes the server's walker count within its 200 m (±2).
- No spawn or despawn happens within 25 m of any player or inside any player's view cone (server asserts).
- Crowd traffic to each client averages at most 4 KB/s (traffic log).
- Client 2 punches a walker: the handoff (walker released, NPC Down) shows on all peers. A crowd witness raises an alert from that client-caused incident.
- Evening population follows the host's clock at 21:00 (after M8; before M8 via host F12).

**Effort:** 5–7. **Tag:** mixed. Builders, pre-bake and observers are GPT-safe; `Visible()` and the handoff are Claude.

### M7 — Police v1 on the network

**Scope:**
- `Police/Scripts/PoliceDirector.cs`: per-player suspects, the attacker taken from requests, arrest and knock sent as TargetRpcs, server only.
- `PoliceUnit.cs` and `PoliceCarMotor.cs`: server only; cars get a NetworkObject and a NetworkTransform.
- `PoliceOfficer.cs`: `OfficerState` SyncVar; targets from `PlayerRegistry`.
- `PoliceEvents.cs`; the `WantedMask` on WorldNet; the MapPolicePlacer pre-bake.

**Risks:**
- chases change when the target is a remote player, whose position lags about 100 ms on the server;
- arresting a passenger who is riding;
- dev keys.

**Acceptance** (`net-m7-police`, host + client):
- The client punches an NPC in a patrol car's view: only the client's wanted bit is set.
- Pursuit of the van while the client drives: the car pose on the client stays within 0.5 m of the host trace, and siren and lights match.
- A ram produces exactly one slapstick cue on both peers.
- Three baton hits within 12 s arrest the client: it is teleported to the station in its own process, the penalty is applied once (Q4), and the host is unaffected.
- An evade (unseen for 10 s, more than 80 m away) clears the van's wanted bit on both HUDs.

**Effort:** 5–7. **Tag:** Claude-only for targeting and arrest; GPT-safe for state → siren, lights and labels.

### M8 — World clock, sky, cues and audio

**Scope:**
- New: `Network/Scripts/WorldClock.cs`, `SkyClockNetDriver.cs` and `NetCue.cs` (the cue channel).
- `CaptureSave` reads WorldClock, and `CrowdDirector.Evening` follows the clock.
- The server-side sound calls in GreyboxNpc, NpcRagdoll, VanDoor, the police and Capture go through cues. `Audio/Scripts/Sfx.cs` stays unchanged (local playback).

**Risks:** low. The one trap: the host must not hear a sound twice (a local call plus a cue), so cues replace local calls rather than add to them.

**Acceptance** (`net-m8-clock`):
- The host scrubs from 08:00 to 21:00: after 1 s the client's hour is within 1 game minute. Night lights are on in both. A client joining at night sees night on the first frame after spawning.
- Over 10 real minutes the client's clock drifts by at most 0.5 game minutes.
- A scream from an NPC 20 m from the client plays once there; an NPC 250 m away plays nothing (out of observation).
- The host plays every cue exactly once.

**Effort:** 2–3. **Tag:** GPT-safe.

### M9 — Saves, shared economy and the phone in co-op

**Scope:**
- **Saves.** `Capture/Core/CaptureRules.cs` gets the v2 save DTOs as new types (v1 stays readable). `Capture/Scripts/CaptureSave.cs` and `CaptureDirector.cs`: host-only save/load and per-player blocks.
- **Economy.**
  - `Network/Scripts/WorldNet.cs`: `FundsCents` and transactions.
  - The new server adapter `Buyers/Runtime/BuyerServer.cs` runs `Buyers/Core`, converting decimal to long cents at the boundary.
  - `Inventory/Runtime/NetworkInventory.cs`: cash removed or kept, per Q4.
- **Phone.** `UI/Phone/Scripts/BankApp.cs`, `MarketApp.cs`, `MessagesApp.cs` read the replicated model.
- **Server gates.** `Clinic/Scripts/ClinicSave.cs`; `Vehicles/Paint/Runtime/VanPaintStorage.cs` writes on the host only.

**Risks:** save migration, JsonUtility and `decimal`, and per-player identity without accounts.

**Acceptance** (`net-m9-save-a`, then `net-m9-save-b`):
- **a.** Host + client. The client ties and loads 2 NPCs and rides in the bay, with 3 ties and 2 items. The host saves (K).
- **b.** Both restart, and the client reconnects with the same `ov.playerId`:
  - its block is restored (position, kit, items);
  - the NPCs in the van have the same PatientIds, sleep, blood and ties;
  - the clock hour is equal and no time has passed (CD-09, now in co-op).
- The client's `persistentDataPath/OnlyVolunteers` listing is identical before and after: the client writes nothing.
- **Purchase race.** Two clients buy the last affordable item in the same tick: exactly one succeeds. Funds are equal on the host and both phones, and the transaction log has one entry.
- **Duplicate confirmation.** A buyer sale confirmed twice with the same `ConfirmationId` gives one sale and one payment (BUY-37, now in co-op).

**Effort:** 5–7. **Tag:** mixed. DTOs, gating and the phone read model are GPT-safe; transactions and identity are Claude.

### Later (outside the ten milestones)

- Van paint sync (§3.3).
- A second van.
- A Steam transport (Q3).
- Player knockout as a ragdoll (capture spec §12), reusing `NpcBodySync` for players.
- The Stage B head bag and its combos (new server rules and state flags).
- Host migration: not planned (Q8).

---

## 6. Test harness

### 6.1 Layers

| Layer | What it proves | Runs |
|---|---|---|
| EditMode | Pure rules and serialisers: pose compression round trip (error below 0.5° and 2 mm), `VanNetSync` pack/unpack, save v2 migration, transaction idempotency | Every milestone |
| PlayMode, one process (solo host) | Server-side behaviour and the real-input loop on the host. `OnlyVolunteers.Capture.PlayTests` and `OnlyVolunteers.Operation.PlayTests` must stay green | Every milestone |
| Two-to-four process builds | Replication, ownership, late join, disconnect, latency (`run-net.ps1`) | Every milestone |
| Human playtest, 2 PCs on a LAN | Feel of driving, carrying and the table | M2, M4, M5, then every release |

### 6.2 `Working/Reviews/Network/run-net.ps1`

It generalises `Working/Reviews/Operations/stage1_v2/run-localhost-v02.ps1`, which is kept unchanged for history.

**Parameters:**

| Parameter | Default | Meaning |
|---|---|---|
| `-Exe` | — | The player build |
| `-Run` | — | Evidence folder; never overwritten (`_NN` is appended) |
| `-Scenario` | — | Scenario name |
| `-Clients` | 1 | 1–3 |
| `-Port` | 7796 | |
| `-LatencyMs` | 0 | Simulated latency |
| `-LossPct` | 0 | Simulated packet loss |
| `-TimeoutSec` | 300 | |
| `-ExtraArgs` | — | Passed through as-is, so `-ops-scenario net-host` keeps working |

**Steps:**
1. Start the host: `-ov-host -net-scenario <s> -net-role host -net-evidence <dir>/host -ov-port P -ov-latency L -ov-loss X -screen-width 1280 -screen-height 720 -screen-fullscreen 0 -logFile <dir>/host.log`, in a hidden window as today.
2. Wait until `host.log` contains `[OV Network] server started`, polling every 0.5 s for at most 60 s. This replaces today's fixed 3 s sleep.
3. Start the clients 1 s apart: `-ov-client 127.0.0.1 -net-role client<i> -net-index <i> …`.
4. Wait for all of them or the timeout; kill on timeout; record the exit codes.
5. Parse the `PASS`/`FAIL`/`RESULT`/`NET` lines into `summary.txt`. Exit 1 on any FAIL or a missing RESULT.

**Validated without Unity.** It can be checked now against the existing ops build `Working/Reviews/Operations/stage1_v4/build/OperationsStage1v04.exe`: `-ExtraArgs "-ops-scenario net-host"` on the host and `net-client` on the client must reproduce `net04` (37/22 PASS).

`run-net-suite.ps1` runs the listed scenarios in sequence before a milestone is accepted: about 30–45 minutes after M9.

### 6.3 `NetScenarioDriver` (dev-only: editor and development builds)

It is modelled on `OperationNetworkProbe` and `CaptureScenarioDriver`.
- **Roles** come from the args. Each scenario has one coroutine per role, for example the host and client halves of `net-m2-client-drives`.
- **API:** the existing `Check`, `WaitFor`, `Shot` and `Line`. Evidence goes to `Working/Reviews/Network/<milestone>/<run>/<role>/`: `run-log.txt`, PNGs, and a role-specific `final-state.json` (van pose trace, pelvis traces, holder counts).
- **Synchronisation.** `NetTestBarrier` is a dev NetworkObject in the sandbox and i11 scenes, holding a `SyncDictionary<string, byte>` of the roles that reached each named step. `yield return Barrier("carry-start")` waits for every role. This replaces the fixed sleeps that made earlier probes depend on process-start skew.
- **Traces** are stamped with the server tick (`TimeManager.Tick`). `compare_traces.py` then aligns host and client traces offline and computes the position errors the acceptance checks use.
- **Input.** It plays only through the virtual devices of the extended `OpsInput` (WASD, E, Q, LMB, Z/X/C, Tab), so every RPC path is exercised. Operations v02 root cause 7 was probes calling RPCs directly and bypassing input; the scripted fallbacks of `CaptureScenarioDriver` stay for solo PlayMode only.
- **Traffic.** `NetTrafficLog` prints `NET up=… down=… KB/s` once a second per role, and the checker averages it per scenario phase.
- **Reproducibility.** `-net-seed` seeds the server-side randomness (stun spread, kicks, tears) in dev builds. Forced death rolls follow the existing `OperationTestHooks.ForcedRoll`.

### 6.4 Scenarios per milestone

| Milestone | Scenarios | Processes | Run time |
|---|---|---|---|
| M0 | `net-m0-join`; ops `net02`/`net04` via `-ExtraArgs` | 2 and 4 | ~2 min each |
| M1 | `net-m1-presence`, `net-m1-four`, `net-m1-disconnect` | 2, 4, 2 | ~2 min |
| M2 | `net-m2-host-drives`, `net-m2-client-drives` (×3 latencies), `net-m2-seat-race`, `net-m2-doors`, `net-m2-late-join` | 2–3 | ~3 min |
| M3 | `net-m3-ride`, `net-m3-flip` | 3 | ~3 min |
| M4 | `net-m4-hit`, `net-m4-carry3`, `net-m4-kit`, `net-m4-late-join` | 3–4 | ~3 min |
| M5 | `net-m5-loop` | 2 | ~6 min |
| M6 | `net-m6-crowd` | 4 | ~7 min |
| M7 | `net-m7-police` | 2 | ~5 min |
| M8 | `net-m8-clock` | 2 | ~12 min (drift check) |
| M9 | `net-m9-save-a`, then `net-m9-save-b` (restart in between) | 2 | ~4 min |

### 6.5 Regression gates at every milestone

- EditMode: the whole suite (240/240 when G35 started).
- `OnlyVolunteers.Operation.PlayTests` 7/7 and `OnlyVolunteers.Capture.PlayTests` (4, as updated in M1).
- Ops two-process `net04`: host 37 / client 22 PASS. The operation table must never regress.
- Solo host: NPC Loading Test 19/19; Ragdoll Smoke Test at its 31/34 baseline (r6, r6b, r7 already failing).
- Builds: a sandbox build (fast) for iteration, and a map development build (~6 min) when a milestone closes.

---

## 7. Conflicts with the Capture Stage A work in progress (G35)

### 7.1 What G35 owns now

From `Working/Reviews/Capture/stageA/PROGRESS.md` ("G35 continuation") and `FEDYA_FEEDBACK_2026-10-18.md`.
- **Table work:**
  - strap precision and PREP-only straps;
  - table mass and brake;
  - the v02 organ and opening visuals.

  Files: `NetworkOperationTable`, `OperationTableView`, `OperationHud`, the presentation scripts and the table prefab.
- **Corpse work.** Removal from the table, the body bag (hold R) and water disposal: new files plus `Capture/Scripts`.
- **Test and policy work.** Fixes to the capture scenarios (`CaptureScenarios*.cs`, `CaptureScenarioDriver.cs`) and push-policy checks (`PlayerPushPolicy`, `ExampleCharacterController`).
- **Possible carry and inventory seams:** `PhysicsGrabber`, `NetworkGrabber`, `NetworkInventory`, `GreyboxNpc`.
- **Scene and tooling.** The i10 scene (the only map scene it may change). The batch Unity editor + MCP under the shared lock.

### 7.2 Must wait until G35 has finished and been accepted

- **Anything that writes into `Assets/`.** A new or changed `.cs` file recompiles G35's batch editor in the middle of its runs, and AgentRules §4 allows one active editor.
- In particular:
  - M0's input wrapper (`GreyboxInteractor`, `PhysicsGrabber`, `KccFirstPersonInput` are G35's carry seams);
  - all of M1 (`CaptureDirector`, `NetworkPlayer`, and the i11 scene built from G35's final i10);
  - M4 (`GreyboxNpc`, `CaptureNpc`, `CaptureFieldKit`, `NetworkGrabber`);
  - M5 (`CaptureTableBridge`, `CaptureVanCapacity`, the body bag);
  - the refactor of the operation ragdoll.
- **The capture PlayMode tests and G35's interim build** assume the scene pawn and `externalControl`. M1 rewrites that path, so the lead must accept G35's deliverables first, then approve M1 changing them.

### 7.3 Can start now (no Unity, no writes to `Assets/`)

- `Working/Reviews/Network/run-net.ps1` and `tools/compare_traces.py`. They are plain PowerShell and Python, validated against the existing ops v04 build (§6.2).
- The lead's review of this plan and of decisions Q1–Q8.
- GPT briefs for the mechanical parts of M0: the input wrapper file list, the sandbox builder spec and the harness.

### 7.4 Right after G35

M0 in this order:
1. sandbox builder and session split;
2. input wrapper, on G35's final versions of `PhysicsGrabber` and `GreyboxInteractor`;
3. the first harness run on the sandbox.

### 7.5 Cheap requests to G35 now (optional; they avoid rework)

- **Body bag:** a `NetworkPhysicsBody` prefab (NetworkObject + Rigidbody + server NetworkTransform), not a plain Rigidbody. The existing networked grab then works on it unchanged.
- **Disposal:** decide it in server-side FixedUpdate (`IsServerInitialized`), with its effects in one method that a cue can call later.
- **No new single-pawn lookups.** No new `FindAnyObjectByType<GreyboxKccPawn>` or `Camera.main` in gameplay code; use `CaptureDirector.Pawn`, so M1 has one place to change.
- **New per-NPC state** goes into serialisable fields of `CaptureFacts` / `OperationState` (the existing pattern), not into MonoBehaviour-only fields.
- **No new consumers** of the scene pawn's ownership or of the solo host's port.

---

## 8. Open decisions for the lead

| # | Question | Options | Recommendation |
|---|---|---|---|
| Q1 | Who simulates the van when a **client** drives? | A: the server simulates; the client sends input at 30 Hz. B: the driver's client owns the van (client-authoritative transform); cargo bodies are frozen into van-local slots while a client drives. | **A.** Decide for good after M2's measured client-driver delay at 100 ms RTT and Fedya's LAN test. Switch to B for client drivers only if A feels bad. |
| Q2 | How do players ride in the bay at speed? | A: free KCC below about 6 km/h, fixed riding slots above (look around, use tools, grab). B: free walking at any speed (KCC on a moving proxy, van-local streaming). | **A** for v1. B is the draft's "medium risk, jitter above ~40 km/h" path; revisit after a playtest. |
| Q3 | Transport and connecting | Tugboat over LAN/direct IP now; later a Steam relay transport (no port forwarding for players) | **Tugboat now**, nothing else in M0–M8. Decide on Steam when the first remote-friend playtest is planned (at M9 at the latest). |
| Q4 | Where does money live? | One shared business fund on the server. Or personal cash plus a shared fund. | **One shared fund** (ops §15.1; buyers: "Деньги поступают в общий фонд"). It replaces `PhoneWallet`, `LocalInventory.Cash` on the map and `NetworkInventory.cash`; arrest penalties use the 2026-10-19 team-size scaling rule in §3.9. |
| Q5 | How are per-player saves keyed? | A client GUID in PlayerPrefs (`ov.playerId`). Or no per-player save (everyone respawns at the base with an empty kit). | **The GUID now**, the Steam id once Steam lands. |
| Q6 | The NPC at the table | Keep the cloud swap (despawn the map NPC, spawn the patient prefab with the same PatientId and state). Or one unified NPC/patient prefab. | **Keep the swap** for co-op v1. It meets D4 visually (the cloud covers it; identity, counters and looks carry over) and leaves `Operation/Stage1` untouched. |
| Q7 | Where to iterate | A small sandbox scene (canon §133, "NPC + VAN FUN TEST") for M0–M5, with each milestone also checked on the map. Or only the 33 MB map. | **The sandbox plus a map check.** Map builds take about 6 minutes and map runs are slow and flaky to stage. |
| Q8 | What happens when the host leaves? | The session ends for everyone (the host autosaves; clients see "host left" and return to the menu). Or host migration. | **The session ends**, with no host migration. It matches "the server is the physics authority" and the host-only save. |

---

## Appendix A. Single-player couplings to replace

Paths are under `Assets/OnlyVolunteers`.

| File | Lines | Coupling | Replacement | Milestone |
|---|---|---|---|---|
| `Capture/Scripts/CaptureDirector.cs` | 81–83 | `FindAnyObjectByType` pawn, van, NetworkManager | Spawned player via `LocalPlayer`/`PlayerRegistry`; serialised van reference | M1 |
| same | 143 | Server bound to `127.0.0.1` | `NetworkSession` binds `0.0.0.0` | M1 |
| same | 179–187 | `ClientLoaded` hands the one pawn to every connection | One spawn per connection | M1 |
| same | 32 | Static `Instance` (toasts, the arbiter) | Kept for local UI; server parts moved out | M1 |
| `Capture/Scripts/CaptureSave.cs` | 88, 120 | `FindAnyObjectByType<SkyClock22>` | `WorldClock` | M8, M9 |
| `Capture/Scripts/CaptureFieldKit.cs` | 77, 116–117, 152; 211, 225, 248 | One pawn; mutates NPC state in place | `LocalPlayer`; intent RPCs | M4 |
| `Map/Scripts/GreyboxNpc.cs` | 294, 296 | `FindAnyObjectByType` van, pawn | Van reference; `PlayerRegistry` | M1, M4 |
| same | 146, 148 | Static `All`, `Incident` | Server only | M4 |
| same | 443; `ThreatPosition` (used at 702, 757, 873) | Threat = the single pawn | Nearest player | M4 |
| `Characters/Npc/Scripts/NpcRagdoll.cs` | 974, 977 | Listener = pawn / `Camera.main` | `LocalPlayer` (client), `PlayerRegistry` (server) | M4 |
| same | 77, 79 | Static `Mode`, `Cap` | Host dev command; server cap | M4 |
| `Map/Scripts/Crowd/CrowdDirector.cs` | 144–145, 372 | Pawn, van | `PlayerRegistry` | M6 |
| same | 371 | `Camera.GetAllCameras` | Player view cones | M6 |
| same | 152–153 | F11/F12 (F12 changes Evening) | F12 host-only; Evening from the clock | M6, M8 |
| same | 347 | `AddComponent<CrowdWalker>` | Pre-baked, enabled | M6 |
| `Police/Scripts/PoliceDirector.cs` | 160–168, 469 | One pawn, one van | Per-player suspects | M7 |
| same | 501–509 | HUD and HomeBase keys | Host-only | M7 |
| same | 538 | `AddComponent<PoliceOfficer>` | Pre-baked | M6, M7 |
| `Police/Scripts/PoliceOfficer.cs` | 547 | `_d.Pawn.Knock` | `Knock` TargetRpc to the target's owner | M7 |
| `Clinic/Scripts/ClinicLoop.cs` | 66–71, 185 | Pawn, van, camera, LocalInventory | Inactive in i10: gate to the server or retire | M9 |
| `Clinic/Scripts/PatientLifecycle.cs` | 65 | `NewId()` minted on any machine | Server only | M1, M4 |
| `Clinic/Scripts/PatientRegistry.cs` | 103 | Scans `GreyboxNpc.All` each frame | Server only | M1 |
| `Map/Scripts/GreyboxInteractor.cs` | 79–95 | Legacy Q/E/F9/F10 | `OpsInput` wrapper | M0 |
| same | 84 | Local `npc.Hit` | `RequestHit` | M4 |
| same | 313 | `Camera.main` fallback | Owner view camera | M1 |
| same | 340 | Sets the global `NpcRagdoll.Mode` | Host dev command | M4 |
| `Map/Scripts/GreyboxVanSeat.cs` | 24 | One serialised `Pawn` | `DriverClientId` | M2 |
| same | 102–107 | Legacy E, no owner check | Owner-only, then `RequestSeat` | M0, M2 |
| same | 212–239 | `SetActive(false)` on the pawn; Main Camera swap | Seated mode; owner camera | M2 |
| `Map/Scripts/GreyboxVanCargo.cs` | 778–783 | `RidingPawn()` = the one pawn | Passengers from `PlayerRegistry` | M3 |
| `Map/Scripts/GreyboxVanAutopilot.cs` | 42 | P key; writes the van's inputs | Host-only dev | M2 |
| `Vehicles/Van/Scripts/VanDriveInput.cs` | 46–84 | Legacy keys; writes the van directly | Wrapper; `DriveInput` RPC | M0, M2 |
| `Vehicles/Van/Scripts/VanCameraRig.cs` | 40–44 | Legacy mouse | Owner only | M2 |
| `Map/Scripts/GreyboxKccPawn.cs` | 16–17 | Reflection on `_yaw`/`_pitch` | Keep on the owner; later a public API on `KccFirstPersonInput` | M1 |
| `Map/Scripts/GreyboxInput.cs` | 9 | Static `EUsedFrame` | Owner-only readers | M1 |
| `Vehicles/Scripts/VehicleEngineAudio.cs` | 175, 560–563 | `Seat.Driving`; scan every 2 s | `VanNetSync` inputs; keep the scan | M2 |
| `Vehicles/Scripts/VehicleImpactAudio.cs` | 74–78 | Local collision sounds | Server cue | M2 |
| `Vehicles/Paint/Integration/VanPaintMapMode.cs` | 43 | `FindAnyObjectByType<PhoneController>`; serialised Pawn | `LocalPlayer` | Later (paint) |
| `Audio/Scripts/AmbiencePlayer.cs` | 94, 270 | `Camera.main` | OK while only the owner's camera is enabled and tagged; verify | M1 |
| `Inventory/Runtime/InventoryInput.cs` | 95 | `Camera.main` fallback | Owner view camera | M1 |
| `UI/Phone/Scripts/PhoneController.cs` | 164–170, 253 | Legacy Tab and mouse; `FindAnyObjectByType<EventSystem>` | Wrapper; the find is OK | M0 |
| `Sky/G22_v04/Runtime/SkyClock22.cs` | 29–33 | Debug keys on every peer | Host-only through `SkyClockNetDriver` | M8 |
| `Network/Scripts/NetworkGrabber.cs` | 155 | `GetComponentInParent<NetworkPhysicsBody>` (one rigidbody) | Part-aware NPC target | M4 |
| `Operation/Stage1/Scripts/OperationPatientRagdoll.cs` | 152, 187 | `FindObjectsByType` table, players | `PlayerRegistry` | M4 |

## Decisions (Fedya, 2026-10-18)
Fedya accepted all eight recommendations:
- Q1: the server simulates the van, and the client driver sends input. Switch to driver-owned only if the M2 latency feels bad.
- Q2: passengers walk freely below ~6 km/h and use fixed riding slots above it.
- Q3: Tugboat over LAN/direct IP for now. Decide on Steam by M9 at the latest.
- Q4: one shared money fund.
- Q5: the per-player save key is a client ID in PlayerPrefs; a Steam ID later.
- Q6: the cloud swap at the table stays, with the same PatientId.
- Q7: a small sandbox scene (the "NPC + VAN FUN TEST"), plus a check on the real map at each milestone.
- Q8: when the host leaves, the session ends. No host migration.

## Decision (Vadim, 2026-10-19) — shared income and team-scaled cash penalties

For `N` players in the active team snapshot, a sale or other money reward credits its final team amount once to the shared fund, independent of `N`. A per-player cash penalty `Xᵢ` is divided by `N` for every affected player, so the total shared-fund debit is `Σ(Xᵢ / N)`. One detained player in a four-player team therefore costs `X/4`; if all four receive that same individual penalty, the team loses `X` total. A penalty defined once per incident is divided once by `N`. Purchases, bills and voluntary bribes retain their full listed cost; confiscated items and non-cash penalties retain their source rules. The server snapshots the team size and affected players with the idempotent outcome transaction.
