# Current state (verified 2026-09-16)

- Canonical branch: `main`; Stage 12.2 began from clean commit `b143040`.
- Unity editor version: `6000.5.11f1`.
- FishNet is pinned through UPM to `https://github.com/FirstGearGames/FishNet.git?path=Assets/FishNet#4.7.3`; the lockfile resolves official tag commit `73f30cf2425dc808a4f463f0a233d386010810b3`.
- The 4.7.3 tag's upstream `package.json` and `NetworkManager.FISHNET_VERSION` still report `4.7.2`; the immutable Git tag/hash, not that stale metadata field, is the resolved package evidence.
- The imported runtime assembly is `FishNet.Runtime`; `Friendslop.Network` references only that package assembly.
- `Friendslop.Network`, `Friendslop.Network.Tests.EditMode`, and `Friendslop.Network.Tests.PlayMode` exist. Core, Physics, Network.Physics, and Steam assemblies do not exist.
- The public reusable session boundary is `ISessionController`, `SessionState`, immutable `SessionSnapshot`, and read-only snapshot notifications. FishNet types do not cross that boundary.
- The neutral validation scene is `Assets/Friendslop/Network/Validation/MultiplayerBootstrapValidation.unity`; it contains one NetworkManager, Tugboat, session controller, camera, and light. Its neutral player has no movement, interaction, Rigidbody, abilities, inventory, or game-specific behavior.
- Focused Unity tests previously passed: EditMode 8/8 and PlayMode 1/1. The later shutdown-race fix and its focused `StopCompletionTracker` regression coverage are retained; no tests were rerun during the finalization-only pass.
- The retained strict Windows development build at `C:\Dev\GameBuilds\Stage12_2_FinalVerified\FriendslopMultiplayerValidation.exe` completed with 0 build errors. Unrelated warnings included the unlinked Unity Services project and deprecated In App Purchasing package.
- A manual run of distinct retained-build host and client processes proved host-only spawn, external connection, exactly two observed participants, neutral-player ownership, bounded failed-connection recovery, remote server cleanup, and host preservation after remote disconnect.
- Reconnect on the retained build is inconclusive: the validation runner failed an early two-connection assertion and stopped the host before the client attempted reconnect. This is neither a production reconnect PASS nor a production reconnect FAIL. Stage 12.2 therefore remains PARTIAL with reconnect as the only unsupported acceptance criterion.
- Steam, matchmaking, relay/NAT traversal, persistence, accounts, game-specific content, and final physics networking remain unimplemented.
- The game-specific STOP-GATE remains CLOSED.
