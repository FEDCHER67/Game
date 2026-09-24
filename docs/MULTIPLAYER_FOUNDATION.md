# Reusable multiplayer foundation

Status (2026-09-24): The original Friendslop.Network implementation described below is retired history. The active first playable co-op prototype lives under `Assets/OnlyVolunteers/Network/` and uses the retained FishNet/Tugboat package. The historical design below is not a description of the active code.

## Current OnlyVolunteers.Network slice

- `NetworkTest` is the development startup scene. One FishNet NetworkManager and Tugboat transport run host or client sessions. A client can enter a hostname or IPv4 address and port; `-ov-host`, `-ov-client <address>`, and `-ov-port <port>` support development launches. Tugboat limits the session to four participants.
- The server spawns one `NetworkPlayer` for each connection after start scenes load and assigns one of four free spawn slots. The owning client runs the unchanged KCC input, camera, and network-specific grab input. Other instances disable their local KCC motor, input, camera, and AudioListener. FishNet NetworkTransform relays owner position/yaw; a small visual shows remote players, with view pitch sent to its head.
- The server alone simulates four `NetworkPhysicsBody` Rigidbody instances (5, 20, 50, and 100 kg). Clients keep the bodies kinematic and observe their FishNet NetworkTransform state. The server verifies an LMB grab ray, connection ownership, range, allowed body, and free holder slot. Exactly one holder is recorded per body; only server FixedUpdate applies hold forces. Release and disconnect clear that holder.
- The preserved `Assets/DefaultPrefabObjects.asset` registers exactly `NetworkPlayer` and `NetworkPhysicsBody`. Its GUID is unchanged. The old Friendslop.Network assemblies and scenes remain removed.
- Verification on 2026-09-24: Unity compilation and Windows development build succeeded. Editor Host/Stop/Host produced 1/0/1 players and 4/0/4 bodies with no duplicate. Separate host plus two client processes observed the same three players and four bodies; server bodies were dynamic, client copies kinematic, with matching settled positions. Client disconnect/despawn/reconnect, fourth participant, and fifth-client rejection were observed in process logs. Real keyboard/mouse movement and LMB grab competition across two humans remain unverified.

Historical status: The minimal Stage 12.2 bootstrap was implemented on 2026-09-16; final retained-build verification was PARTIAL because reconnect remained inconclusive. Deferred physics and platform policies were unresolved.

## 1. Architectural invariants

- Game-specific code may depend on reusable code. Reusable code must never depend on game-specific code.
- Dependencies point toward smaller, more stable contracts. Cycles are forbidden.
- Server authority is the baseline. Ownership identifies the client permitted to control or request; it does not grant authority to commit shared state.
- A host is an authoritative server plus an ordinary local client. Host-local input is not implicitly trusted.
- Unity lifecycle and transport callbacks are serialized through one session state machine on Unity's main thread.
- Do not add an abstraction until it protects a defined boundary or has a real consumer.

## 2. Layer responsibilities

### Friendslop.Core

Core contains only lifecycle-independent, reusable concepts shared by at least two reusable layers:

- small immutable IDs and value types whose meaning is not FishNet-, Steam-, physics-, or game-specific;
- minimal result/error and cancellation/lifetime contracts when shared across reusable assemblies;
- pure validation or utility code with no scene, transport, network, physics, or platform behavior.

Core public contracts should use BCL types and remain free of Unity object/lifecycle types where practical. When Core is introduced, its asmdef should set `noEngineReferences` if the actual code permits it.

Core must not contain MonoBehaviours, scene bootstrap, service locators, FishNet types, connection/session orchestration, replication, Steam APIs, Rigidbody logic, input maps, player presentation, or speculative generic frameworks. A type is not promoted to Core until a second reusable consumer needs it.

### Friendslop.Network

Network owns the reusable online-session boundary:

- the FishNet adapter and one NetworkManager lifecycle;
- host/client start, connection, disconnect, shutdown, and failure handling;
- connection and participant registration;
- exactly-one-player-object spawning per accepted connection;
- server-side assignment, removal, and observation of ownership;
- reusable request/authority/validation helpers;
- transport-neutral session state and diagnostics exposed to callers;
- the default local transport configuration for the Stage 12.2 proof.

The minimal public surface is deliberately narrow:

- `ISessionController`: request start-host, start-client, and stop/disconnect operations;
- `SessionState`: `Stopped`, `StartingHost`, `Host`, `StartingClient`, `Client`, `Stopping`, or `Failed`;
- an immutable session snapshot containing state, local connection identity when available, connected-player count, and the last actionable failure;
- state/participant change notifications that are observational and read-only.

Exact C# signatures may be made idiomatic during Stage 12.2, but their semantics and dependency direction are frozen. FishNet types must not leak through the caller-facing session API. FishNet-specific components remain inside the Network assembly.

Network must not contain gameplay rules, presentation/UI, game-specific player behavior, Steam lobby/authentication code, grabbing/carrying logic, final physics synchronization, or direct references to Physics, Steam, or game-specific assemblies.

### Friendslop.Physics

Physics owns reusable local simulation policy and physics-facing contracts:

- reusable body/state descriptions and simulation adapters;
- tick/step coordination needed by reusable physics behavior;
- reusable policies for interpolation, prediction, reconciliation, and correction once they are proven necessary;
- authority-neutral physics constraints and diagnostics.

Physics does not own sessions, connections, RPCs, transport, FishNet components, Steam, player spawning, gameplay interactions, or game rules. It must run without a network and must not reference Network.

Networked physics belongs in a future `Friendslop.Network.Physics` bridge. The bridge translates Network ticks, snapshots, authority, and ownership into Physics operations. It may use FishNet prediction facilities, including `PredictionRigidbody`, but neither base assembly learns about the other. No physics or bridge assembly is created in Stage 12.2.

### Friendslop.Steam

Steam is a future platform adapter. It may own:

- Steam initialization and shutdown;
- Steam identity/authentication mapping;
- lobby discovery/invites and join metadata;
- FishySteamworks/Steamworks.NET transport provisioning;
- translation of Steam failures into Network's transport/session error model.

Steam references Network and its external Steam dependencies. Network never references Steam. Core contains no Steam concepts. Steam does not own generic session state, player spawning, authority rules, gameplay, or physics. No Steam code, package, asmdef, authentication, or lobby work is in Stage 12.2.

### Game-specific layer

The game-specific layer is reserved, behind the STOP-GATE, for replaceable rules and content: concrete player behavior and presentation, interactions, objectives, progression, economy, world content, UI/art/audio, and any mechanic-specific interpretation of reusable network or physics events.

It may reference the reusable assemblies it needs. No reusable assembly may reference it, reflect over it, load it by hard-coded name, or accept game-specific DTOs in its public API.

## 3. Allowed and forbidden references

`A -> B` means A may reference B.

| Assembly/layer | May reference | May be referenced by | Forbidden |
| --- | --- | --- | --- |
| `Friendslop.Core` | BCL; minimal Unity modules only if unavoidable | All reusable layers and game-specific code | Network, Physics, Steam, FishNet, Steam SDKs, game-specific code |
| `Friendslop.Network` | Core, FishNet runtime, required Unity modules | Network.Physics, Steam, game-specific code, Network tests | Physics, Steam, game-specific code, FishNet demos/editor assemblies |
| `Friendslop.Physics` | Core and required Unity physics modules | Network.Physics and game-specific code | Network, FishNet, Steam, game-specific code |
| `Friendslop.Network.Physics` | Core, Network, Physics, and only required FishNet runtime APIs | Game-specific code and its own tests | Steam and game-specific code |
| `Friendslop.Steam` | Network, Steamworks.NET/FishySteamworks, required Unity modules; Core only if a shared type is actually needed | Game-specific code and its own tests | Physics and game-specific code; Network must never reference Steam |
| Game-specific layer | Any explicitly required reusable assembly | Other game-specific assemblies only | Being referenced by any reusable assembly |

No direct `Network <-> Physics` reference, no `Network -> Steam` reference, and no cyclic reference are allowed. Direct FishNet references are confined to Network, a future integration bridge that genuinely needs FishNet prediction APIs, and the future Steam transport adapter if FishySteamworks requires them. Direct Steam references are confined to Steam.

## 4. Assembly strategy

Assembly definitions are required in Stage 12.2 because dependency direction must be enforced before reusable code grows.

Stage 12.2 creates only:

- `Friendslop.Network`: references the package runtime assembly currently named `FishNet.Runtime` (confirm the exact package-provided name after installation); never references FishNet demos, editor, or codegen assemblies directly;
- `Friendslop.Network.Tests.EditMode`: references Network, Unity Test Framework, and only the test dependencies it uses;
- `Friendslop.Network.Tests.PlayMode`: references Network, Unity Test Framework, and only the test dependencies it uses.

Stage 12.2 does not yet have two reusable consumers for a Core contract, so it must not create an empty `Friendslop.Core` assembly or move Network-only types into Core. When Core first has a real shared consumer, it is created with no project assembly references and `noEngineReferences` if its actual code permits it.

All project references are explicit. Unsafe code is disabled unless a later evidence-backed requirement changes that decision. Future Core, Physics, Network.Physics, and Steam asmdefs are created only with their first real implementation. Empty marker assemblies are forbidden.

## 5. Networking foundation decision

**FISHNET APPROVED FOR STAGE 12.2**

Approval rationale:

- The project is on Unity `6000.5.11f1`; FishNet's current compatibility table says Unity 6+ is fully supported, and release 4.7.3 explicitly adds Unity 6.5 scene-handle and entity/instance-ID support.
- FishNet directly supports the required host/client lifecycle through NetworkManager and supports server-spawned, connection-owned player objects.
- Tugboat is the default transport and is sufficient for the initial loopback/LAN proof without adding platform services.
- FishNet provides prediction and `PredictionRigidbody` facilities relevant to later physics experiments, while not forcing them into Stage 12.2.
- FishySteamworks provides a later Steam transport path without requiring Steam concerns in Core or the base Network API.
- The repository contains no conflicting Netcode for GameObjects runtime package.

Stage 12.2 should use the official UPM Git installation and pin release tag `4.7.3` rather than track the repository head: `https://github.com/FirstGearGames/FishNet.git?path=Assets/FishNet#4.7.3`. Package resolution, the exact package/asmdef names, and clean compilation under `6000.5.11f1` must be verified during Stage 12.2 before implementation proceeds beyond the bootstrap proof.

Approval is not evidence that FishNet physics will meet the final game, latency, bandwidth, or low-end-PC requirements. Release notes show recent fixes in prediction, reconcile, transport shutdown, and Unity 6.5 integration. Those are reasons to pin and validate, not to assume final suitability.

Current authoritative references:

- [Installing FishNet](https://fish-networking.gitbook.io/docs/tutorials/getting-started/installing-fish-networking)
- [Unity compatibility](https://fish-networking.gitbook.io/docs/overview/readme/features/unity-compatibility)
- [FishNet 4.7.3 release](https://github.com/FirstGearGames/FishNet/releases/tag/4.7.3)
- [Getting connected / NetworkManager](https://fish-networking.gitbook.io/docs/tutorials/getting-started/getting-connected)
- [Ownership](https://fish-networking.gitbook.io/docs/guides/features/ownership)
- [Transports](https://fish-networking.gitbook.io/docs/guides/high-level-overview/transports)
- [Prediction: controlling an object](https://fish-networking.gitbook.io/docs/guides/features/prediction/creating-code/controlling-an-object)
- [PredictionRigidbody](https://fish-networking.gitbook.io/docs/guides/features/prediction/predictionrigidbody)
- [FishySteamworks](https://fish-networking.gitbook.io/docs/fishnet-building-blocks/transports/fishysteamworks)

## 6. Baseline authority and ownership model

- **Server baseline:** the server is authoritative for session membership, spawning/despawning, ownership changes, and all replicated state mutations.
- **Player ownership:** after accepting a connection, the server spawns exactly one neutral player object and assigns that connection as FishNet owner. The server maintains the connection-to-player registry.
- **Player-controlled objects:** an owner may collect local input and submit intent. The server validates and applies it. Client ownership never permits arbitrary shared-state writes.
- **World-owned objects:** networked world objects are ownerless in FishNet terms and server-controlled by default. FishNet's server is not itself a client owner.
- **Client requests:** requests identify intent, not results. Never trust client-supplied identity, target authority, timing, position, velocity, quantity, or outcome.
- **Validation:** the server checks connection state, ownership/control eligibility, session phase, target existence, value bounds, rate/tick limits, and request freshness before mutation. Invalid requests are rejected and diagnostically classified without destabilizing the session.
- **Authoritative mutation:** only server-side code commits replicated state. Observers consume state; they do not race to write it. The host's local client uses the same request path.
- **Future physics objects:** start server-authoritative. Client prediction/reconciliation may be added selectively for latency-sensitive owned bodies only after measured prototypes. Snapshots, ticks, and corrections cross the Network.Physics bridge.
- **Future carried/grabbed objects:** remain ownerless/server-controlled by default. A client requests an interaction; the server validates and may grant a revocable control lease. Do not equate a gameplay lease with FishNet ownership. Any actual ownership transfer is server-only, explicit, exceptional, and reversible.
- **Disconnect cleanup:** the server atomically revokes connection-scoped leases/permissions, removes registry entries, despawns the disconnected player's object, clears pending requests, and returns affected world objects to the ownerless/server-controlled baseline. Cleanup is idempotent. Late callbacks are ignored using a session generation/epoch.

## 7. Session lifecycle and concurrency

One `ISessionController` owns one FishNet NetworkManager. All public lifecycle requests and all transport callbacks are handled on Unity's main thread through the documented `SessionState` machine.

- Starting while already starting/running returns a controlled failure and does not create a second manager/session.
- Stop/disconnect is idempotent from every state.
- A host starts server then local client and is considered `Host` only when both are ready.
- Host shutdown stops the local client and server, removes connection-scoped state, releases the transport, and ends in `Stopped`.
- A client connection failure or unexpected disconnect exposes one actionable failure, cleans partial state, and reaches `Failed` or `Stopped` without stale participants.
- Each start attempt increments a session generation. Callbacks from earlier generations cannot mutate the current session.
- Stage 12.2 does not add background-thread gameplay work, multiple simultaneous sessions, host migration, automatic retries, or a global service locator.

## 8. Minimum Stage 12.2 implementation scope

Stage 12.2 is a foundation proof only:

1. Install and pin FishNet 4.7.3 through UPM; allow only its required manifest and lockfile changes.
2. Create the Network runtime asmdef plus focused EditMode/PlayMode test asmdefs. Do not create an empty Core asmdef.
3. Implement the narrow session controller/state/snapshot API and FishNet adapter described above.
4. Configure one reusable NetworkManager bootstrap with Tugboat and a configurable address/port (loopback/default port is sufficient for validation).
5. Implement server-side connection registration and exactly-one neutral player-object spawn/despawn with correct connection ownership.
6. Create only the neutral bootstrap/player prefab and neutral multiplayer-foundation validation scene/assets required to run the proof. Do not modify an Only Volunteers/game-specific scene.
7. Add bounded, useful lifecycle/connection/ownership logs and actionable start/connect/shutdown errors; do not log per frame/tick.
8. Add focused automated tests for state transitions, idempotent stop, duplicate-start rejection, registry cleanup, and dependency-boundary checks where practical.
9. Verify host, external client, disconnect, reconnect, and clean restart in Unity `6000.5.11f1` using the Editor plus a standalone development build (or two standalone instances).

## 9. Explicit Stage 12.2 exclusions

Stage 12.2 must not include:

- grabbing or carrying;
- ragdolls;
- NPCs;
- inventory or economy;
- vehicles/van systems;
- Heat, buyers, progression, objectives, or other game rules;
- Only Volunteers UI, scenes, names, or content;
- Steam lobbies, Steam authentication, Steamworks.NET, or FishySteamworks installation;
- relay/NAT traversal, matchmaking, host migration, dedicated-server deployment, reconnection policy, or automatic retries;
- final movement, physics prediction, Rigidbody synchronization, collision reconciliation, or final physics tick-rate tuning;
- game-specific interactions, input actions, visuals, audio, or presentation;
- production menus or production UI;
- implementation of Friendslop.Physics, Friendslop.Network.Physics, or Friendslop.Steam.

## 10. Exact Stage 12.2 pass criteria

### Static and automated verification

- The project resolves the pinned FishNet dependency and compiles in Unity `6000.5.11f1` with no C# errors.
- Network, EditMode-test, and PlayMode-test assemblies compile; every new reusable source file is governed by its intended asmdef rather than falling into `Assembly-CSharp`.
- Automated tests for legal session transitions, duplicate-start rejection, idempotent stop, and disconnect registry cleanup pass.
- If a later stage introduces `Friendslop.Core`, it has no higher-layer or FishNet/Steam reference; Stage 12.2 does not create an empty Core assembly.
- In Stage 12.2, `Friendslop.Network` references only the required FishNet runtime assembly. It may also reference Core after Core legitimately exists; it has no Physics, Steam, or game-specific reference.
- No reusable asmdef references a game-specific asmdef, and no reusable source namespace/import contains game-specific or Only Volunteers symbols.
- Only the approved package files and reusable/neutral foundation assets are changed. No game-specific implementation is introduced.
- `git diff --check` passes.

### Unity Editor / multi-process verification

These behaviors require Unity runtime verification; static inspection or Unity MCP alone is insufficient:

1. Open the project in Unity `6000.5.11f1`; let package import/code generation finish; the Console has no red errors.
2. Start the neutral validation scene as host. Session state reaches `Host`; one accepted connection and exactly one player object exist; that object is owned by the host's local connection.
3. Start a separate client instance and connect to the host. The server reports two accepted connections and exactly two player objects. Both instances observe two players. Each player object has exactly its corresponding connection as owner; neither client owns the other player's object.
4. Disconnect the remote client normally. The server returns to one connection/player, despawns only the remote player's object, retains the host player, and reports no stale owner/registry entry.
5. Reconnect the client once. Counts return to two, exactly one new player object is created for the new connection, ownership is correct, and no duplicate/stale state appears.
6. Stop the client and host, then start a host again in the same process. The transport/port is released, state returns cleanly through `Stopped`, and no stale callbacks or players remain.
7. Exercise one failed client connection. One actionable error is surfaced, partial state is cleaned, and a subsequent valid attempt can start without restarting the Editor/process.
8. Across the sequence there are no unhandled exceptions, red Console errors, duplicate NetworkManagers, duplicate player objects, or unbounded per-frame/tick logs.

### Stage 12.2 verification record (2026-09-16)

- UPM resolved `#4.7.3` to official tag commit `73f30cf2425dc808a4f463f0a233d386010810b3`; the imported runtime asmdef is `FishNet.Runtime`.
- Upstream tag metadata still reports version `4.7.2`, so the pinned URL and immutable commit hash are the authoritative version evidence.
- Unity `6000.5.11f1` compiled the runtime and both test assemblies with no C# errors.
- Focused tests previously passed: EditMode 8/8 and PlayMode 1/1. The subsequent production shutdown-race fix retains focused `StopCompletionTracker` regression coverage; the finalization-only pass did not rerun tests.
- The retained strict Windows development build at `C:\Dev\GameBuilds\Stage12_2_FinalVerified\FriendslopMultiplayerValidation.exe` completed with 0 build errors. Unrelated warnings included the unlinked Unity Services project and deprecated In App Purchasing package.
- A manual run of distinct retained-build host and client processes proved host-only startup with one player, external connection with two observed participants, correct remote ownership, bounded failed-connection recovery, server-side remote cleanup, and preservation of the host player.
- Reconnect is inconclusive on the retained build. The validation runner failed an early two-connection assertion, invoked host shutdown, and only then did the client attempt reconnect. That sequence proves neither a production reconnect failure nor final reconnect success.
- Stage 12.2 is PARTIAL solely because final retained-build reconnect proof is absent. No further harness iteration was performed.
- No game-specific, Steam, interaction, Rigidbody synchronization, prediction, or Network.Physics implementation was added.

Unity MCP may assist observation, but it is not required. The two-peer ownership and lifecycle proof must use distinct network instances.

## 11. Remaining unresolved questions

These are deliberately deferred and do not authorize extra Stage 12.2 work:

- Whether FishNet prediction meets the eventual physics, latency, bandwidth, and low-end-PC budgets; this needs a later measured physics prototype.
- Final physics tick rate, snapshot rate, correction tolerances, interpolation, and state-forwarding policy.
- Which bodies, if any, may use client prediction or temporary control leases.
- Steam SDK/transport choice details, lobby/authentication design, and mapping Steam identity to reusable connection identity.
- Internet connectivity strategy (direct address, relay, NAT traversal), matchmaking, reconnect identity, and host migration.
- Dedicated-server support and client/server code stripping.
- Final game-specific composition root, player behavior, input, scenes, UI, content, and mechanics.

The exact FishNet package assembly names and import behavior under this specific Unity patch must be confirmed immediately after the pinned package is installed in Stage 12.2. If installation or clean compilation fails, stop and re-evaluate rather than weakening assembly boundaries.

## 12. STOP-GATE

The game-specific STOP-GATE remains CLOSED. This freeze authorizes no Stage 12.2 implementation by itself. Stage 12.2 begins only after explicit user approval.
