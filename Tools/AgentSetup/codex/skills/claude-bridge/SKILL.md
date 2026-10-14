---
name: claude-bridge
description: "Bridge to Claude (Claude Code CLI) for the VOLUNTEERS ONLY project. Use when Codex wants a second opinion, an independent review of a plan/code/Blender model/Unity setup, or a cross-check from Claude; or when Fedya says «спроси клода», «сверься с клодом», «пусть клод глянет», «мост»."
---

# Claude bridge (GPT → Claude)

Fedya works with two assistants on the same machine: **GPT** (Codex / ChatGPT app) and **Claude** (Claude Code, Fedya's Work chat in `C:\Dev`). This skill lets Codex consult Claude directly instead of making Fedya copy text between chats. The mirror skill on the Claude side is `~/.claude/skills/gpt-bridge`.

## Roles

- The **active Work** (the chat Fedya is talking to) owns the task: it edits files, writes WORK_SYNC TASKs, commits/pushes only with Fedya's agreement.
- The **consultant** (the other assistant, called through this bridge) answers questions, reviews, double-checks. By default it is **read-only**: no file edits, no git, no WORK_SYNC, no paid actions.
- `docs/TEAM_WORKFLOW.md` still applies: one Work at a time. A bridge call is a consultation inside the active Work, not a second Work.

## How to call Claude

Read-only consultation (default), run from the repo root `C:\Dev\Game`:

```powershell
claude -p --permission-mode plan --output-format text "<prompt>"
```

If the shell has no stdin, Claude waits 3 s and continues; to skip the wait use `< NUL` (cmd) or `$null | claude -p ...` (PowerShell).

- Long prompts or attachments: write the prompt to `%USERPROFILE%\.ai-bridge\req_<timestamp>.md` (outside the repo) and pass `"Прочитай задачу в файле <path> и ответь"`. Images are passed by absolute path; Claude can open local images.
- Typical time 10–120 s; each call spends Fedya's Claude quota. Max 2 rounds per question, no loops.
- Edits by Claude (`--permission-mode acceptEdits`) **only** after Fedya explicitly asks Claude to change files in this task.
- Never put secrets, tokens or passwords into prompts.

## Prompt template

```
Ты консультант в проекте VOLUNTEERS ONLY (Unity 6000.5.11f1, URP, FishNet; репо C:\Dev\Game).
Активный Work — GPT. Ты только читаешь, ничего не меняешь.
Контекст: <что уже решено, какие файлы смотреть>
Вопрос: <конкретно>
Ответ: по-русски, коротко, пунктами; если не уверен — так и скажи.
```

## After the answer

- Treat Claude's answer as advice, not as Fedya's decision. Subjective acceptance (look, feel) is always Fedya's.
- Tell Fedya the gist in 1–3 lines; if it changed a decision, note «консультация Claude» in the TASK result.
- If Claude disagrees with a decision Fedya already made, show the disagreement to Fedya instead of silently switching.

## When Claude delegates work to you (executor mode)

Fedya's rule (2026-10-04): Claude leads, GPT executes the tasks Claude hands over (Tripo runs and concept images for models, plus easy/bulky side tasks). In that mode:

- Do exactly the brief: touch only the files/folders it names, keep existing naming/versioning rules (new numbered revisions, never overwrite deliverables).
- Never commit, push or edit WORK_SYNC.md; Claude reviews and publishes.
- Tripo: spend only on images Fedya personally approved; the Create button must read exactly 100 credits before every click; clear the input slots afterwards; report the balance before/after.
- Finish with a short Russian report: what was done, exact output paths, what you checked, what is uncertain. If Claude sends the work back, fix every listed defect.

## Strengths to delegate

Claude in this setup has Blender MCP, Unity MCP (mcp-for-unity 10.2.0), Serena, C# LSP, the Unity official plugin and agent-foundry skills, and drives the desktop via computer use. Procedural Blender models live next to their build scripts (e.g. `ArtSource/Props/VAN-TIER0-ASTRA-001/build_van.py`).
