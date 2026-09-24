# DECISIONS

- Production gameplay lives in Assets/OnlyVolunteers/
- Assets/Friendslop/ stays generic and reusable
- Assets/PhysicsInteractionPlayground/ is prototype/reference only
- Never introduce an artificial FPS cap unless explicitly requested
- Subjective movement/physics/camera feel requires user manual acceptance
- Pending gameplay work is not committed/pushed before explicit user acceptance

- 2026-09-24: Retire the legacy `Assets/Friendslop/Network/` implementation and its validation assets. Keep FishNet and Tugboat installed and preserve the root `DefaultPrefabObjects` registry identity. Build replacement co-op networking in a separate task.
