# Agent setup for VOLUNTEERS ONLY: Fedya's toolset, for Vadim's PC

Goal: give Claude Code and Codex on this PC the same skills, agents, MCP servers and plugins that Fedya uses. Windows, PowerShell. Never put API keys or passwords in files or in the repository.

## 0. Already in the repository (nothing to install)
- `CLAUDE.md`, `AGENTS.md`, `docs/AgentRules.md`: project rules, read automatically.
- Project skills: `.claude/skills/fc-*` for Claude and `.agents/skills/` for Codex; nine Field Clinic skills.
- The Field Clinic kit in `Tools/FieldClinicBrief/`; start with `00_AUTOSTART.md`.
- Unity packages in `Packages/manifest.json`, including MCP for Unity (`com.coplaydev.unity-mcp`) and Asset Usage Detector. Unity installs them when the project opens.

## 1. Prerequisites (install whatever is missing)
- Git with **Git LFS**: `git lfs install`, then `git lfs pull` in the repository. The map meshes come through LFS.
- Unity **6000.5.11f1** through Unity Hub, and **Blender 5.2**.
- uv: `winget install --id=astral-sh.uv -e`. This provides `uvx`.
- Serena: `uv tool install serena-agent==1.7.0`.
- .NET SDK 8 or newer, then `dotnet tool install --global csharp-ls --version 0.28.0`.
- Node.js LTS (used by some plugins).
- Claude Code CLI (`claude`) and/or the Codex app or CLI.

## 2. Skills, agents and the Blender add-on
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Tools\AgentSetup\install.ps1
```
It installs:
- the user-level Claude skills: 13 game-dev roles from Agency Agents (MIT), grill-me, gpt-bridge, csharp-refactoring, analyzing-dotnet-performance, doc-coauthoring and canvas-design;
- the worker agents `worker-low|medium|high|xhigh|max`;
- the same skills for Codex, plus claude-bridge;
- the Blender add-on `blender_mcp.py`.

It never overwrites existing files; add `-Force` to replace them. Then enable the add-on in Blender: Preferences > Add-ons > "MCP for Blender".

## 3. MCP servers
The Unity instance name is the project folder name. Use `GAME` if the clone is in a folder called `Game`; otherwise put your own folder name.

**Claude Code** (user scope):
```powershell
claude mcp add-json unityMCP '{"type":"stdio","command":"uvx","args":["--from","mcpforunityserver==10.2.0","mcp-for-unity","--transport","stdio"],"env":{"UNITY_MCP_DEFAULT_INSTANCE":"GAME"}}' -s user
claude mcp add-json blender '{"type":"stdio","command":"uvx","args":["blender-mcp==2.0.0"]}' -s user
claude mcp add-json serena '{"type":"stdio","command":"serena","args":["start-mcp-server","--context=claude-code","--project-from-cwd"]}' -s user
```

**Codex**: add to `%USERPROFILE%\.codex\config.toml`, keeping any existing entries:
```toml
[mcp_servers.unityMCP]
command = "uvx"
args = ["--from", "mcpforunityserver==10.2.0", "mcp-for-unity", "--transport", "stdio"]
[mcp_servers.unityMCP.env]
UNITY_MCP_DEFAULT_INSTANCE = "GAME"

[mcp_servers.blender]
command = "uvx"
args = ["blender-mcp==2.0.0"]

[mcp_servers.serena]
command = "serena"
args = ["start-mcp-server", "--context=codex", "--project-from-cwd"]
```

## 4. Claude Code plugins
```powershell
claude plugin marketplace add anthropics/claude-plugins-official
claude plugin marketplace add furkantokkan/agent-foundry
claude plugin marketplace add promptfoo/promptfoo
claude plugin marketplace add obra/superpowers-marketplace
claude plugin install unity@claude-plugins-official
claude plugin install context7@claude-plugins-official
claude plugin install csharp-lsp@claude-plugins-official
claude plugin install pr-review-toolkit@claude-plugins-official
claude plugin install agent-foundry@agent-foundry
claude plugin install blender-texture-foundry@agent-foundry
claude plugin install ai-3d-foundry@agent-foundry
claude plugin install promptfoo@promptfoo
claude plugin install superpowers@superpowers-marketplace
```
If a command name differs in your Claude Code version, use the interactive `/plugin` menu with the same marketplaces and plugin names. context7 asks for its own sign-in; that is optional.

## 5. Verify, and report the results
1. Open the project in Unity 6000.5.11f1.
   - If "Administrator Privileges Detected" appears, press **Ignore Warning**.
   - Wait for "MCP-FOR-UNITY ... StdioBridgeHost started" in the Console.
2. Open Blender 5.2: sidebar > MCP > Connect.
3. Run `claude mcp list`. unityMCP, blender and serena must show Connected. For Codex, check its MCP list.
4. In Claude Code, start a new session in the repository and check:
   - the skills list includes game-designer, grill-me, fc-world-and-roads and the superpowers skills;
   - the agents list includes worker-high;
   - one read-only Unity call works, for example getting the active scene;
   - one Blender call works, for example getting the scene info.
5. Open `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i04_vanpaint.unity`. It must have ground, roads and buildings.
   - If it does not, run `git lfs pull` and reopen Unity.
6. Report what was installed, what was skipped and every check result.

## Not included (personal to Fedya)
- DeepSeek/OpenCode keys and the `translate.py` translator.
- Fedya's ChatGPT/Codex account and limits, and Tripo credits.
- His `.ai-bridge` orchestration scripts.
- TexTools for Blender is optional: get v1.6.1 from its official GitHub release if needed.
