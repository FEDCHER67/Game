# Architecture — current baseline, not a finished design

Unity 6000.5.11f1, URP, FishNet/Tugboat. Keep one game project and extend a small playable slice.

| Area | Responsibility |
| --- | --- |
| Assets/OnlyVolunteers/Player | First-person input, movement integration, local grab, shared force solver and tuning profile |
| Assets/OnlyVolunteers/Network | Sessions/spawning, player replication, validated grab requests, server simulation of shared bodies |
| Assets/OnlyVolunteers/Props | Imported table/scalpel assets, per-prop tuning, table wheel presentation |
| Assets/OnlyVolunteers/Vehicles | Van model/prefab, local WheelCollider driving (VanController), animated doors (VanDoor), test-only input/camera, editor rebuild tool |
| Assets/OnlyVolunteers/Scenes | Movement, local physics and co-op test scenes |
| Assets/OnlyVolunteers/Art | Current player model prototype |
| Assets/KinematicCharacterController | Third-party motor and the ExampleCharacter component/prefab actually used by the players |
| ArtSource | Editable prop models, exports, textures, previews and provenance for art review |
| docs | Product canon and concise current project context |

Movement is simulated by the owning player. Shared rigidbodies are simulated by the server; clients request grabs and observe replicated results. Multiple forces act on one authoritative body. The force solver must stay independent of FishNet.

Current limitations: no server reconciliation of player movement; the connection/UI/test-spawn responsibilities share NetworkSession; generic props allow four holders; local grabbing remains single-holder. These choices require review before expanding the game. Do not describe this prototype as production-ready networking.

Next gameplay boundaries, to implement only when needed: NPC body/grab points and resistance; environmental GripAnchor; van doors/loading state; NPC presentation. Capture and transport come before city/economy frameworks. No empty Core/Steam/manager layers.

## Field Clinic kit

An instruction bundle for agents (Claude and Codex). It contains no code and no downloaded dependencies, and it does not replace this file or `docs/CURRENT_STATE.md`.

- **Kit:** `Tools/FieldClinicBrief/`. Start with `00_AUTOSTART.md`. It also holds:
  - `01_SETUP_REFERENCE.md`;
  - `02_FULL_GAME_BRIEF.md`, the full brief (an English copy for agents is kept outside the repo);
  - `03_REPOSITORIES.json`, the 47-entry catalogue;
  - `04_RESUME.md`, `05_CODEX_HANDOFF.md`, the original prompts and `CHECKSUMS.sha256`.
- **Skills:** nine `fc-*` skills, mirrored in `.claude/skills/` (Claude) and `.agents/skills/` (Codex). They are `fc-project-bootstrap`, `fc-game-design`, `fc-vehicle-and-cameras`, `fc-patient-lifecycle`, `fc-interaction-and-surgery`, `fc-world-and-roads`, `fc-lowpoly-pipeline`, `fc-atmosphere-and-audio` and `fc-performance-and-playtests`.
- **Persistent docs:**
  - `docs/AgentRules.md`, `docs/SetupReport.md` and `docs/EnvironmentReport.md` (setup and rules);
  - `docs/Progress.md` and `docs/NextAction.md` (current loop);
  - `docs/DependencyDecisions.md` (all 47 catalogue entries classified, plus the next integrations);
  - `docs/Dependencies.md` (what the project uses today);
  - `THIRD_PARTY_NOTICES.md` (licences and attributions);
  - `docs/ArtDirection.md` (the consolidated current look).
  The kit refers to `Docs/ArtBible.md`; in this repo that role is served by `docs/ArtDirection.md` together with `docs/art/STYLE_BIBLE_v2.md`.
- **Rule:** the kit's catalogue is a decision queue, not an install list. Existing systems are kept: FishNet, KCC, our van, ragdoll NPCs, the map pipeline and Uber Water. Duplicates of them are rejected (see `docs/DependencyDecisions.md`).
