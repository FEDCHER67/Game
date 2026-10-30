# Navigation — start here (V2)

Read only what your task needs, then search the relevant subtree. Do not read all of Assets, ArtSource or the reports at startup. Archives are off-limits without permission (AGENTS.md «Archives»).

## Read first

| What | Where |
| --- | --- |
| Canon (what the game is) | docs/PRODUCT.md; raw grill answers docs/specs/V2_GRILL_NOTES_2026-10-30.md |
| What is built now | docs/CURRENT_STATE.md |
| Code layout and boundaries | docs/ARCHITECTURE.md |
| Rules | AGENTS.md, docs/AgentRules.md, CLAUDE.md |
| Two developers, handoff | docs/TEAM_WORKFLOW.md, WORK_SYNC.md (top = newest; read only unseen and open tasks) |
| Taking something from v1 | docs/V1_ARCHIVE.md (only with permission) |

## Active roots

| Area | Path |
| --- | --- |
| Runtime code and assets | Assets/OnlyVolunteers/<area> (Vehicles/Van, Capture, Player, Characters, Network, Session, UI, Economy, Audio) |
| V2 test scene | Assets/OnlyVolunteers/Scenes/Dev/VanOnly_v01.unity |
| Main menu | Assets/OnlyVolunteers/Scenes/Menu/MainMenu_v01.unity |
| Builds | Assets/Editor/VadimBuilds.cs (targets), Assets/Editor/VadimVanLab.cs (VanOnly scene) |
| Editable art sources | ArtSource/<family> (van: ArtSource/Props/VAN-TIER0-ASTRA-001) |
| V2 references and planning (mostly local, not in Git) | V2_НОВАЯ_ИГРА/ (see its ПРОЧТИ.md) |
| Van layout reference | Working/Reviews/VanRedesign_2026-10-29/ |
| Agent setup | Tools/AgentSetup |

## Checks

- Compile: open the project in Unity 6000.5.11f1 (take the Unity lock first: `C:\Users\Zeyo-ne\.ai-bridge\unity_lock.ps1`); no Unity calls while `C:\Users\Zeyo-ne\.ai-bridge\PLAYTEST_ON` exists.
- Tests: Unity Test Runner, EditMode assemblies under Assets/OnlyVolunteers/*/Tests.
- Push: scene dependency check (`missing_deps.py` on `live_scenes.txt`) and the push preflight; never `git add -A/./-u`.
