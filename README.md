# VOLUNTEERS ONLY

3D first-person co-op for 1–4 players: drive the van, stuff funny people into it, they pop out as soldiers and beat enemy waves; upgrade the van at the base (V2 since 30.10.2026).

- Unity **6000.5.11f1**, URP, FishNet/Tugboat, KinematicCharacterController.
- Git LFS is required. Run `git lfs pull` before opening the project.
- V2 test scene: `Assets/OnlyVolunteers/Scenes/Dev/VanOnly_v01.unity` (only the van and the player). Main menu: `Assets/OnlyVolunteers/Scenes/Menu/MainMenu_v01.unity`.
- State and what is implemented: docs/CURRENT_STATE.md. Navigation for agents: docs/INDEX.md.

## Project documentation

- [Рабочая спецификация](docs/PRODUCT.md)
- [Навигация](docs/INDEX.md)
- [Состояние и проверки](docs/CURRENT_STATE.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [Работа вдвоём и синхронизация](docs/TEAM_WORKFLOW.md)
- [Передача задач между Вадимом и Федей](WORK_SYNC.md)
- [Исходники моделей](ArtSource/README.md)

Sources, Unity assets with .meta, packages, project settings, art sources and documentation are tracked. Unity/IDE caches, local preferences and builds are generated separately on each PC. Pull does not remove unrelated local files; read the synchronization guide before updating a dirty checkout.
