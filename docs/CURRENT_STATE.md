# Current state (verified 2026-09-16)

- Canonical branch: `main`.
- The canonical worktree was clean before Stage 12.1 documentation edits.
- Unity editor version: `6000.5.11f1`.
- Universal Render Pipeline package: `17.5.0`.
- Input System package: `1.20.0`.
- Unity Test Framework package: `1.7.0`.
- `com.unity.multiplayer.center` `1.0.1` is present, but it is not a runtime networking stack.
- No FishNet, runtime transport, Steamworks, lobby, relay, or other networking package is installed.
- No project asmdefs or authored reusable/gameplay runtime systems exist. The only C# files are Unity tutorial/template scripts.
- The only enabled build scene is `Assets/Scenes/SampleScene.unity`.
- Stage 12.1 froze the reusable multiplayer architecture in documentation.
- FishNet is approved for Stage 12.2 but has not been installed or implemented.
- Stage 12.2 has not begun and requires explicit user approval.
- No game-specific implementation was introduced. The game-specific STOP-GATE remains CLOSED.
