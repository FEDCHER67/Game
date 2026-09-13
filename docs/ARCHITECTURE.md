# Architecture

Future layers (documentation only; not implemented yet):

- **Friendslop.Core** — reusable runtime contracts, input, lifecycle, and utilities.
- **Friendslop.Network** — host-client session, replication, ownership, and player state.
- **Friendslop.Physics** — deterministic-enough multiplayer physics, carried objects, and authority rules.
- **Friendslop.Steam** — future Steam/lobby integration boundary.
- **Game-specific layer** — replaceable content and rules built on the reusable layers.

Game-specific code must not be a dependency of reusable layers.
