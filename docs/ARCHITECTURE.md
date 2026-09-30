# Architecture — current baseline, not a finished design

Unity 6000.5.11f1, URP, FishNet/Tugboat. Keep one game project and extend a small playable slice.

| Area | Responsibility |
| --- | --- |
| Assets/OnlyVolunteers/Player | First-person input, movement integration, local grab, shared force solver and tuning profile |
| Assets/OnlyVolunteers/Network | Sessions/spawning, player replication, validated grab requests, server simulation of shared bodies |
| Assets/OnlyVolunteers/Props | Imported table/scalpel assets, per-prop tuning, table wheel presentation |
| Assets/OnlyVolunteers/Scenes | Movement, local physics and co-op test scenes |
| Assets/OnlyVolunteers/Art | Current player model prototype |
| Assets/KinematicCharacterController | Third-party motor and the ExampleCharacter component/prefab actually used by the players |
| ArtSource | Editable prop models, exports, textures, previews and provenance for art review |
| docs | Product canon and concise current project context |

Movement is simulated by the owning player. Shared rigidbodies are simulated by the server; clients request grabs and observe replicated results. Multiple forces act on one authoritative body. The force solver must stay independent of FishNet.

Current limitations: no server reconciliation of player movement; the connection/UI/test-spawn responsibilities share NetworkSession; generic props allow four holders; local grabbing remains single-holder. These choices require review before expanding the game. Do not describe this prototype as production-ready networking.

Next gameplay boundaries, to implement only when needed: NPC body/grab points and resistance; environmental GripAnchor; van doors/loading state; NPC presentation. Capture and transport come before city/economy frameworks. No empty Core/Steam/manager layers.
