# Project skills snapshot

The project keeps its downloaded development skills in `.agents/skills/` so the
same instructions are available when the Codex account changes. This snapshot
was copied from the local installations on 2026-09-30. Existing project skills
were retained without replacement.

| Source | Version | Newly copied |
| --- | --- | ---: |
| User-installed `%USERPROFILE%\.codex\skills` | local snapshot | 13 |
| Agent Foundry | 0.8.1 | 93 |
| AI 3D Foundry, including migrated command skill | 0.1.0 | 4 |
| Blender Texture Foundry, including migrated command skills | 0.1.0 | 18 |
| Unity plugin | 0.1.6-beta | 1 |

`agent-foundry-unity-cli` is the Agent Foundry skill renamed locally to avoid
overwriting the existing Unity plugin `unity-cli`. Its relative links were
updated to point to the renamed directory. License and notice files copied
from the plugin installations, plus the upstream Agency Agents license for
the user-installed role skills, are in `.agents/skills/_licenses/`.

The user has asked the project workflow to avoid MCP. Skills that describe MCP
still provide general guidance, but MCP steps are not part of this project's
current workflow. Use local files, Unity CLI, and ordinary command line tools.

For future isolated changes, stage from a clean feature worktree with
`git add .` as requested by the user. Do not stage all files from a checkout
that already contains unrelated work.
