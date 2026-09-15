# Architecture

The reusable multiplayer architecture is frozen for Stage 12.2. Implementation has not started.

`A -> B` means assembly A may reference assembly B.

```text
Friendslop.Core

Friendslop.Network -> Friendslop.Core + FishNet runtime
Friendslop.Physics -> Friendslop.Core
Friendslop.Network.Physics -> Friendslop.Core + Friendslop.Network + Friendslop.Physics
Friendslop.Steam -> Friendslop.Network + Steam/FishySteamworks dependencies

Game-specific layer -> any required reusable assembly
```

`Friendslop.Network.Physics` is an optional integration bridge, not a general-purpose dumping ground. It prevents a direct `Physics <-> Network` cycle. It is created only when networked physics is implemented.

No reusable assembly may reference the game-specific layer. `Core` may not reference any higher layer. `Network` and `Physics` may not reference each other directly. `Network` may not reference `Steam`; platform integration points inward from `Steam` to `Network`. Cyclic assembly references are forbidden.

Assembly definitions will be introduced with the first Stage 12.2 code so these rules are compiler-enforced. Stage 12.2 creates `Friendslop.Network` and its test assemblies. Core, Physics, Network.Physics, and Steam assemblies wait until they contain real code with a real consumer; empty marker assemblies are forbidden.

Detailed responsibilities, authority, public boundaries, Stage 12.2 scope, and pass criteria are in [MULTIPLAYER_FOUNDATION.md](MULTIPLAYER_FOUNDATION.md).

The game-specific STOP-GATE remains CLOSED.
