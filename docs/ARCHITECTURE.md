# Architecture — current baseline, not a finished design

Updated 30.10.2026 for V2 (docs/PRODUCT.md). The player, network and force parts below are the reused v1 base; the V2 loop (busification, soldiers, waves, base) is not built yet.

Unity 6000.5.11f1, URP, FishNet/Tugboat. Keep one game project and extend a small playable slice.

| Area | Responsibility |
| --- | --- |
| Assets/OnlyVolunteers/Player | First-person input, movement integration, local grab, shared force solver and tuning profile |
| Assets/OnlyVolunteers/Network | Sessions/spawning, player replication, validated grab requests, server simulation of shared bodies |
| Assets/OnlyVolunteers/Capture, Map/Scripts (Greybox*) | NPC grab, carry, van cargo/seats, fist stun (reused for mobilisation) |
| Assets/OnlyVolunteers/Session, UI/MainMenu, UI/Pause, Economy | Main menu, world slots, lobby, settings, team fund |
| Assets/OnlyVolunteers/Props, Operation, Map/W85Build | v1 content (operation table, organs, map W86); stays until the v1 code cleanup |
| Assets/OnlyVolunteers/Vehicles | Van model/prefab, local WheelCollider driving (VanController), animated doors (VanDoor), test-only input/camera, editor rebuild tool |
| Assets/OnlyVolunteers/Scenes | Dev/VanOnly_v01 (V2 test), Menu/MainMenu_v01, v1 map and test scenes |
| Assets/OnlyVolunteers/Art | Current player model prototype |
| Assets/KinematicCharacterController | Third-party motor and the ExampleCharacter component/prefab actually used by the players |
| ArtSource | Editable prop models, exports, textures, previews and provenance for art review |
| docs | Product canon and concise current project context |

Movement is simulated by the owning player. Shared rigidbodies are simulated by the server; clients request grabs and observe replicated results. Multiple forces act on one authoritative body. The force solver must stay independent of FishNet.

Current limitations: no server reconciliation of player movement; the connection/UI/test-spawn responsibilities share NetworkSession; generic props allow four holders; local grabbing remains single-holder. These choices require review before expanding the game. Do not describe this prototype as production-ready networking.

Next gameplay boundaries (V2 order: van and busification first): van seats and the 10 s transformation, soldier spawn and simple soldier/enemy AI, van health and repair, waves, then base and upgrades. No empty Core/Steam/manager layers.
