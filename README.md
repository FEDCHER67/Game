# VOLUNTEERS ONLY

3D first-person co-op for 1–4 players: funny people, physical chaos, business progression.

- Unity **6000.5.11f1**, URP, FishNet/Tugboat, KinematicCharacterController.
- Git LFS is required. Run `git lfs pull` before opening the project.
- Development scene: `Assets/OnlyVolunteers/Scenes/NetworkTest.unity` (host/client, cubes, table, scalpel).
- Local checks: ControllerTest for movement, PhysicsInteractionTest for grabbing.
- NPC capture, van loading and the business loop are not implemented yet.

## Project documentation

- [Рабочая спецификация](docs/PRODUCT.md)
- [Подробный канон](docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md)
- [Состояние и проверки](docs/CURRENT_STATE.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [Работа вдвоём и синхронизация](docs/TEAM_WORKFLOW.md)
- [Передача задач между Вадимом и Федей](WORK_SYNC.md)
- [Исходники моделей](ArtSource/README.md)

Sources, Unity assets with .meta, packages, project settings, art sources and documentation are tracked. Unity/IDE caches, local preferences and builds are generated separately on each PC. Pull does not remove unrelated local files; read the synchronization guide before updating a dirty checkout.
