# Decisions

- **Build reusable infrastructure first.** The concept is provisional, so foundations remain content-agnostic.
- **Keep the game-specific STOP-GATE closed.** No final rules, mechanics, content, names, art, or game-specific systems are part of the multiplayer foundation.
- **Use a host-client topology for 2-6 players.** The host runs both the authoritative server and a normal local client. Host-local actions follow the same request and validation path as remote-client actions.
- **Use server authority by default.** Clients submit intent; only the server validates and commits replicated state. A FishNet "owner" is the connection allowed to control/request for an object, not an authority bypass.
- **Approve FishNet for Stage 12.2.** FishNet 4.7.3 is the planned pinned baseline because current official documentation supports Unity 6+ and that release explicitly includes Unity 6.5 fixes. Approval is limited to the session/bootstrap proof; final physics synchronization and Steam integration remain unapproved implementation work.
- **Use Tugboat for the initial local proof.** Transport selection stays behind the Network boundary. Steam transport is deferred to `Friendslop.Steam`.
- **Enforce boundaries with asmdefs from the first code.** Stage 12.2 creates Network and necessary test assemblies. Core and the other planned assemblies wait for real cross-layer consumers; empty marker assemblies are not created.
- **Keep Physics independent of Network.** A future `Friendslop.Network.Physics` bridge may reference both; neither base layer references the other.
- **Keep Steam outside Core and below Network.** `Friendslop.Steam` may adapt Steam/FishySteamworks into Network's transport/session extension points; Network never references Steam.
- **Serialize session lifecycle transitions on Unity's main thread.** Start/stop requests are idempotent, overlapping transitions are rejected, and late callbacks from an old session generation are ignored.
- **Design for low-end PCs.** Prefer bounded simulation and replication cost; do not enable expensive prediction/state forwarding without measurement.

See [MULTIPLAYER_FOUNDATION.md](MULTIPLAYER_FOUNDATION.md) for the complete frozen decision.
