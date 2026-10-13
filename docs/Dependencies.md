# Dependencies — what the project uses today

Snapshot 2026-10-13 from `Packages/manifest.json`, `Packages/packages-lock.json` and `Assets/`. Decisions on new candidates are in `docs/DependencyDecisions.md`, and licence texts and attributions in `THIRD_PARTY_NOTICES.md`.
Editor: Unity 6000.5.11f1. Unity packages use the Unity Companion License (UCL) unless stated otherwise.

## Git packages (pinned by tag, lock hash)

| Package | Version / pin | Licence | Use | Link |
|---|---|---|---|---|
| com.firstgeargames.fishnet | tag `4.7.3`, lock `73f30cf2425dc808a4f463f0a233d386010810b3` (its package.json says 4.7.2) | FishNet licence (free, royalty-free for games); bundled GameKit BSD-2, LiteNetLib MIT | networking, Tugboat transport | https://github.com/FirstGearGames/FishNet |
| com.coplaydev.unity-mcp | tag `v10.2.0`, lock `30d22075093d1d35dfb0091c1c7550e9ad948577` | MIT | editor-only agent bridge (MCP for Unity) | https://github.com/CoplayDev/unity-mcp |

## Unity registry packages

| Package | Version | Use |
|---|---|---|
| com.unity.render-pipelines.universal | 17.5.0 | URP renderer |
| com.unity.inputsystem | 1.20.0 | input |
| com.unity.ai.navigation | 2.0.14 | NavMesh for NPCs and police on foot |
| com.unity.test-framework | 1.7.0 | EditMode/PlayMode tests |
| com.unity.ugui | 2.5.0 | uGUI (includes TextMeshPro) |
| com.unity.ide.rider / com.unity.ide.visualstudio | 3.0.38 / 2.0.26 | IDE integration (editor-only) |
| com.unity.modules.* | 1.0.0 | 35 built-in engine modules, listed in the manifest |

## Third-party code and assets inside Assets

| Item | Path | Version | Licence | Link / provenance |
|---|---|---|---|---|
| Kinematic Character Controller (Philippe St-Amand) | `Assets/KinematicCharacterController` (Core + ExampleCharacter used by players) | not recorded; added in commit 74faa977 (2026-09-19) | **not recorded in repo**; assumed Unity Asset Store EULA | Asset Store package. OPEN: record source and licence, and confirm that a public repo may contain it |
| Uber Stylized Water (MatrixRex) | `Assets/OnlyVolunteers/ThirdParty/UberStylizedWater` | commit `1fdd16c6312611fef7fb248dee86cdd3fd456a1e` + our v02 derivative | MIT (plus Cyanilux MIT, 2020/2021) | https://github.com/MatrixRex/Uber-Stylized-Water; `ThirdParty/PROVENANCE.md` |
| Player_01 base mesh "Human Dude Guy" (hat_my_guy) | `Assets/OnlyVolunteers/Art/Characters/Player_01` | archive SHA-256 `EB7B0AB2…6990` | CC0 | https://poly.pizza/m/83DpVkzvWk; `Documentation/PROVENANCE.md` |
| Map textures (ProcTexture, FreeStylized, ambientCG) | `Assets/OnlyVolunteers/Art/StyleKit_v3/Textures`; originals in `ArtSource/Textures/ThirdParty` | v01 downloads 2026-10-11 | CC0; FreeStylized custom royalty-free | `ArtSource/Textures/ThirdParty/PROVENANCE.md` |
| Audio Library_v1 (NOX, Kenney, rubberduck, BigSoundBank, Mixkit) | `Assets/OnlyVolunteers/Audio/Library_v1` | manifest_v1 rev3 + 2026-10-11 vehicle addendum | CC0; Mixkit SFX Free License (24 files local-only, gitignored) | `Library_v1/LICENSES.md` |

## Tools outside the project (not shipped)

| Tool | Version | Licence | Note |
|---|---|---|---|
| Blender | 5.2 | GPL (tool; outputs are ours) | `C:/Program Files/Blender Foundation/Blender 5.2` |
| blender-mcp (PyPI) + add-on | 2.0.0 (launched unpinned through `uvx`) | MIT | https://github.com/ahujasid/mcp-for-blender |
| mcpforunityserver (PyPI) | 10.2.0 | MIT | server for com.coplaydev.unity-mcp |
| Claude plugin `unity@claude-plugins-official` | 0.1.6-beta (`ba48956a…`) | UCL | official Unity skills |
| Tripo (paid, credits) | n/a | Tripo terms | source of ASTRA prop bases; see each `ArtSource/Props/*/PROVENANCE.md` |

Open questions:
- KCC licence and source are unrecorded.
- FishNet's tag (4.7.3) differs from the version in its package.json (4.7.2).
- The brief's `Assets/ThirdParty` does not exist; third-party code lives in `Assets/OnlyVolunteers/ThirdParty`.
