# Agent rules — shared by Claude Code and Codex

One source of the shared working rules for every AI agent in this repository. AGENTS.md (project rules, AI team) and CLAUDE.md point here. If this file and AGENTS.md disagree, AGENTS.md and the user's explicit instructions win.

Canon: docs/PRODUCT.md (V2 since 30.10.2026). Navigation: docs/INDEX.md. These rules came from the "Field Clinic" setup kit (`Tools/FieldClinicBrief/`, a v1-era reference; its patients-and-operation game does not apply to V2). The project is not new: never re-create, re-install or duplicate what already exists.

## 1. Verify, do not just generate

- A task is done when it was checked in the real tool: compiled in the open Unity 6000.5.11f1 editor, run in Play mode in the named scene, rendered/reimported in Blender. Writing code or a report is not proof.
- Report every check as PASS / FAIL / BLOCKED / NOT RUN with the exact command, scene, path and error. PASS only after the check really ran. Never invent results, numbers or screenshots.
- Compilation is not proof of fun, feel or network quality: movement, physics and visual acceptance need a human playtest.
- Separate new Console errors from the ones that were already there.

## 2. One system per category

- One Unity editor bridge at a time: the CoplayDev unity-mcp package (v10.2.0) is the bridge for Claude and Codex. Do not add the Unity Pipeline package or a second MCP bridge.
- One Blender bridge client at a time (ahujasid blender-mcp); disconnect one AI client before another uses it. `blender --background --python` is the fallback.
- One system per gameplay concern (one interaction key handler per action, one NPC capture lifecycle, one save format, one movement owner per body). Extend the existing system instead of adding a parallel one.
- Add an abstraction only for a concrete consumer. No empty manager layers or speculative scaffolding.

## 3. Versions, licences, packages

- Unity 6000.5.11f1, URP 17.5.0, FishNet 4.7.3, Input System 1.20.0, AI Navigation 2.0.14 are pinned (Packages/manifest.json, packages-lock.json). Never change the editor version or render pipeline automatically.
- Install a package only when a real gap needs it. Record name, exact version or commit, licence, URL and rollback in docs/Dependencies.md (or the task's report) before or with the change.
- Check the licence of code, models, textures and sounds separately. Never paste a third-party project over Assets/, Packages/ or ProjectSettings/.

## 4. Unity project hygiene

- Runtime content lives in Assets/OnlyVolunteers; third-party movement code stays in Assets/KinematicCharacterController. Editable art lives in ArtSource (outside the import tree).
- Preserve every .meta file and GUID. Check scene, prefab and code dependencies before moving or deleting an asset; never delete project files without the owner's OK.
- Never overwrite a deliverable: a new revision gets a new numbered name (…_v02, _v03), with matching exports and previews.
- One active editor of the project at a time. While a human plays in Unity, agents make no Unity calls, compilations or writes into Assets. Agents take the Unity lock described in their brief and release it.
- Never touch PlayerSettings.runInBackground. Set Application.runInBackground only during your own Play runs and restore it afterwards.
- Do not save a scene from Play mode. Leave the editor on the scene you found, Play stopped.

## 5. Safety

- No paid APIs, cloud generation credits or local AI models without the owner's explicit request. No secrets, keys or personal data in files, logs or reports.
- No destructive git: never commit, push, stage, reset --hard, clean or force-push unless the user asks; never edit WORK_SYNC.md as a worker.
- Do not disable OS protections. Ask for one concrete human action only when a system really blocks you (UAC, login, a GUI-only step).

## 6. Focus on the first playable loop

- Priority (V2, docs/PRODUCT.md): everything about the van and busification first (catch → load into the van → seat → soldier pops out), then waves, base and upgrades. Test scene: Assets/OnlyVolunteers/Scenes/Dev/VanOnly_v01.unity.
- Stylised and funny: no organs, operations, blood or gore.
- Captured NPC rules: one stable id, one movement owner at a time, no duplicate rewards, never a living copy and an attached copy of the same NPC at once.
- Keep the FishNet/network assumptions intact; offline map features say so in their docs.
- Work in small, reproducible steps; test after each and write down the result. Big outputs are written in parts.

## 7. Skills

Four general project skills `fc-*` (vehicle and cameras, low-poly pipeline, performance and playtests, atmosphere and audio) live in `.claude/skills/` (Claude Code) and `.agents/skills/` (Codex). They were written for v1; they are narrow guidance, not permission to override this file, AGENTS.md or the canon.
