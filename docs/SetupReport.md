# Setup report — Field Clinic kit, stage A (2026-10-13)

Executed by a Claude Code worker (Opus) on Fedya's Windows 11 PC, local Claude Code with shell, Unity MCP and Blender CLI access. The Unity editor 6000.5.11f1 was open on `C:\Dev\Game`, scene `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v17_Play.unity`. Kit: `Tools/FieldClinicBrief/` (00_AUTOSTART, 01_SETUP_REFERENCE). The project is not new: existing bridges, packages and skills were reused, nothing was reinstalled. Environment details: [EnvironmentReport.md](EnvironmentReport.md). Shared rules: [AgentRules.md](AgentRules.md).

## Results

| # | Test | Result | Evidence |
|---|---|---|---|
| A | Project files: version and URP | PASS | `ProjectSettings/ProjectVersion.txt`: 6000.5.11f1 (5c3a1087d8e4); `Packages/manifest.json`: `com.unity.render-pipelines.universal` 17.5.0 |
| B1 | Skills visible to Claude Code | PASS | command and output below: all 9 `fc-*` names listed |
| B2 | Skills visible to Codex | UNVERIFIED (NOT RUN) | `.agents/skills/fc-*` present (9 folders, copied by the lead with identical checksums); needs a separate run in Fedya's Codex app |
| C | Unity scene test via MCP | PASS | `Assets/OnlyVolunteers/Scenes/Dev/FC_ConnectionTest.unity`; transform read back from the reopened file; no new Console errors |
| D1 | Blender test object via Blender MCP (live Blender) | BLOCKED | `mcp__blender__get_addon_status`: "Could not connect to Blender. Make sure the Blender addon is running." (Blender GUI with the addon was not running; the MCP server itself is registered and starts) |
| D2 | Blender test object via `blender --background` (fallback) | PASS | own collection `FC_ConnectionTest`, `ArtSource/Dev/FC_Test/FC_TestCrate_v01.blend`, preview PNG |
| E | Blender → FBX → Unity import | PASS (with a note) | `Assets/OnlyVolunteers/Art/Dev/FC_Test/FC_TestCrate_v01.fbx`: world size 1:1, upright, axis mapping, 3 URP materials, no import warnings |
| F | Unity CLI | PASS (2 doctor warnings) | `unity --version` = 1.0.0-beta.13; `unity doctor` exit 0 |
| G | State after a client restart | NOT RUN | no client restart was needed or done in this session |
| H | Unity Pipeline package | NOT RUN (by decision) | not installed on purpose: unity-mcp is the working bridge; two Unity bridges at once are forbidden (AgentRules §2) |

## Commands and details

### B1 — skills (Claude Code)

Working directory `C:\Dev\Game`:

```
claude -p --model haiku "List the names of available skills that start with fc-. Names only."
```

Output (exit 0):

```
- fc-atmosphere-and-audio
- fc-game-design
- fc-interaction-and-surgery
- fc-lowpoly-pipeline
- fc-patient-lifecycle
- fc-performance-and-playtests
- fc-project-bootstrap
- fc-vehicle-and-cameras
- fc-world-and-roads
```

### C — Unity scene test

All through the unity-mcp bridge (CoplayDev v10.2.0) while Map_Look_v17_Play stayed loaded and unmodified:

1. `execute_code`: `EditorSceneManager.NewScene(EmptyScene, Additive)`, saved as `Assets/OnlyVolunteers/Scenes/Dev/FC_ConnectionTest.unity` (the project's Dev scene folder instead of the kit's `Assets/_FieldClinic/Scenes/`), set active.
2. `manage_gameobject create`: cube `FC_UnityConnectionTest` at (0, 0.5, 0).
3. `manage_gameobject modify`: position (1.25, 2.5, -3.75), rotation (0, 45, 15), scale (2, 0.5, 1.5).
4. `manage_scene save`.
5. Readback: `execute_code` closed the scene, reopened it additively from disk and read `FC_UnityConnectionTest pos=(1.250, 2.500, -3.750) euler=(0.000, 45.000, 15.000) scale=(2.000, 0.500, 1.500)`; the YAML holds `m_LocalPosition: {x: 1.25, y: 2.5, z: -3.75}`, `m_LocalScale: {x: 2, y: 0.5, z: 1.5}`. Test scene closed again; v17 stayed active and not dirty.
6. `read_console` (errors + warnings) before and after: the same 2 pre-existing warnings only ("This project uses Input Manager, which is marked for deprecation…", "Unity is not designed to run with Administrator privileges."). No new errors.

### D2 / E — Blender round trip

Script (kept outside the repo, in the session scratchpad: `fc_scripts/fc_blender_roundtrip.py`), refuses to overwrite existing files:

```
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python-exit-code 1 --python fc_blender_roundtrip.py -- "C:/Dev/Game/ArtSource/Dev/FC_Test"
```

- Blender 5.2.1 LTS, exit 0. Collection `FC_ConnectionTest`, object `FC_TestCrate`: a 1.0 (X) × 0.5 (Y) × 2.0 (Z) m body, origin at the bottom centre, plus a 0.2 m marker cube on +X (`FC_MarkerPosX`, yellow) and one on the front −Y (`FC_MarkerFrontNegY`, blue); body material `FC_Body` (red). Bounding box 1.2 × 0.7 × 2.0 m, 36 triangles, flat shading. The factory scene's own objects were left untouched.
- Outputs: `ArtSource/Dev/FC_Test/FC_TestCrate_v01.blend`, `FC_TestCrate_v01.fbx`, `FC_TestCrate_v01_preview.png` (Workbench render, 640×480; the factory default cube is visible behind it).
- FBX export with the project's settings from `ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS/README.md`: selected mesh only, `axis_forward=-Z`, `axis_up=Y`, `apply_unit_scale=True`, `global_scale=1`, `use_mesh_modifiers=False`, `mesh_smooth_type=FACE`, `bake_anim=False`, `path_mode=STRIP`, no custom properties.
- Unity import (`execute_code`): copied to `Assets/OnlyVolunteers/Art/Dev/FC_Test/FC_TestCrate_v01.fbx`, then ModelImporter: Scale Factor 1, Use File Scale on (file scale 0.01), Bake Axis Conversion on, normals Import, tangents None, no animation, no rig, no collider, no cameras/lights, materials "Import via MaterialDescription".
- Readback of an instance at the origin: renderer world bounds min (−0.500, 0.000, −0.450), max (0.700, 2.000, 0.250), size (1.200, 2.000, 0.700) = exactly the Blender size, 1 m = 1 m. Upright: Blender Z → Unity Y. Axis mapping: the +X marker centre lands at Unity (0.600, 1.500, 0.000) (Blender +X → Unity +X), the front marker at (0.000, 0.500, −0.350) (Blender −Y → Unity −Z). Mesh: 72 vertices, 36 triangles, 3 submeshes, normals yes, tangents no. Materials: `FC_Body`, `FC_MarkerPosX`, `FC_MarkerFrontNegY`, all `Universal Render Pipeline/Lit` with the Blender colours.
- Console: no import warnings or errors.
- Note: the imported root node carries rotation (90, 0, 0) and scale 100 (Blender's cm-based FBX unit). The world result is correct and every existing project FBX (e.g. `Art/Map/Landmarks/*`) imports the same way, so this matches the project's convention. For clean identity roots a later pipeline revision could export with `apply_scale_options='FBX_SCALE_ALL'` and "Apply Transform"; not changed here.

### F — Unity CLI

```
unity --version   ->  1.0.0-beta.13
unity doctor      ->  exit 0 (about 3 s)
```

Key `unity doctor` lines (account name and e-mail redacted):

```
platform win32 / arch x64 / .NET 10.0.12 / cliVersion 1.0.0-beta.13
installPath C:\Program Files\WindowsApps\UnityTechnologies.UnityCLI_1.0.0.20013_x64__2vrhnee42bhxm\app\unity.exe
check.binary-on-path        pass
check.path-duplicates       warn  C:\Users\Zeyo-ne\AppData\Local\Microsoft\WindowsApps\unity.exe and C:\Users\Zeyo-ne\AppData\Local\Unity\bin\unity.exe
check.windows-long-paths    warn
check.git-credential-helper pass (manager)
check.credential-store      pass (credential-manager)
auth.loggedIn true, auth.sessionState stale, auth.mode oauth
editor.0 6000.5.11f1 x86_64 C:\Program Files\Unity 6000.5.11f1\Editor\Unity.exe
proxy.url http://127.0.0.1:10809/ (from OS)
externalComponent.plastic / licensingClient / ugs / ai: not-installed
vcs: git 2.55.0.windows.5, git-lfs 3.7.1, gh 2.101.0
```

The two warnings (a second `unity.exe` on PATH, Windows long paths off) and the stale auth session do not block the CLI. `unity pipeline install` was deliberately NOT run (see H).

## Existing integrations used, not reinstalled

- Claude ↔ Unity: unity-mcp (package `com.coplaydev.unity-mcp` v10.2.0, server `mcpforunityserver==10.2.0` via uvx), `claude mcp list`: Connected. Codex has the same `unityMCP` server in its config (UNITY_MCP_DEFAULT_INSTANCE=GAME); not exercised from Codex here.
- Claude ↔ Blender and Codex ↔ Blender: blender-mcp via `uvx blender-mcp`; server starts, but the Blender-side addon was not running (D1 BLOCKED).
- Unity agent plugin for Claude: `unity@claude-plugins-official` 0.1.6-beta, enabled (user scope).
- Unity CLI 1.0.0-beta.13.
- Packages: Input System 1.20.0, AI Navigation 2.0.14, URP 17.5.0.
- Skills: 9 `fc-*` in `.claude/skills/` and `.agents/skills/` (copied by the lead).

## Changed files (stage A)

- New: `docs/SetupReport.md`, `docs/EnvironmentReport.md`, `docs/AgentRules.md`, `CLAUDE.md`.
- `AGENTS.md`: one line added at the top pointing to docs/AgentRules.md and the kit; nothing removed.
- New test assets: `Assets/OnlyVolunteers/Scenes/Dev/FC_ConnectionTest.unity` (+ folder), `Assets/OnlyVolunteers/Art/Dev/FC_Test/FC_TestCrate_v01.fbx` (+ folders, .meta files), `ArtSource/Dev/FC_Test/FC_TestCrate_v01.{blend,fbx}`, `FC_TestCrate_v01_preview.png`.
- No checkpoint commit was made (workers never commit; Vadim/Fedya commit by hand). Git status before work: only `.agents/`, `.claude/`, `Tools/` untracked.

## Still open

- Codex skill visibility and Codex ↔ Unity/Blender calls: one run in Fedya's Codex app (new chat in project Only_Volunteers): "List the names of available skills that start with fc-. Names only." — expected the same 9 names.
- Blender MCP live test: open Blender 5.2 with the blender-mcp addon connected, then repeat D in its own collection.
