---
name: gpt-bridge
description: "Delegate work to GPT (OpenAI Codex CLI) in the VOLUNTEERS ONLY project: Tripo/concept-image model runs, plus easy or bulky side tasks (drafts, simple scripts, file sweeps, checks) so Claude saves tokens; also second opinions. Use whenever a task fits GPT, or when Fedya says «спроси гпт», «отдай гпт», «пусть гпт сделает», «мост»."
---

# GPT bridge (Claude → GPT)

**Route (Fedya 2026-10-11, overrides the CLI route below): give GPT its tasks in the Codex desktop app on Fedya's screen** (computer-use: app "ChatGPT", bundle OpenAI.Codex): sidebar → project **Only_Volunteers** → a NEW chat per task in the **«Работа»** (Work) mode on the C:\Dev\Game repo; paste the brief through the clipboard (write_clipboard → click the composer → ctrl+v → Enter); read the answer with «Скопировать ответ» + PowerShell `[System.Windows.Forms.Clipboard]::GetText()` (-STA). Use `codex exec` only if the app is unavailable. Fedya: «в OpenCode GPT очень тупой», «давай больше заданий ГПТшке и можешь более сложные».
**Briefs must be very detailed and exact** — goal, exact files to read and to touch, APIs/names, step-by-step procedure, numbers, acceptance checks, forbidden actions, report format — so GPT never has to guess («иначе он будет хуйней заниматься»). Medium-complexity code is allowed with such a brief; Claude always verifies (compile, Unity, renders). Keep 2–4 GPT tasks running. Still never character/human animation.

Fedya's rule (2026-10-04): **GPT is the pawn, Claude is the lead.** Claude plans, delegates, reviews and owns the result; GPT executes. GPT spends the Tripo runs for models, and after that takes the easy/bulky tasks Claude judges suitable — not only models — so Claude does not burn tokens on trivial work. Fedya considers GPT weak: always run the strongest model, pick the reasoning effort by task difficulty, and make it redo poor work.

## Model and reasoning effort

Model: default `gpt-6.1-sol` (cheaper on the weekly Codex quota; needs Codex CLI >= 0.160 — 0.158 rejected it; `gpt-6-luna` for trivial work); `gpt-6-astra` ("frontier intelligence") only for the hardest or biggest jobs — Fedya 2026-10-04: stretch the weekly quota (check `~/.codex/models_cache.json` if models change). Reasoning effort is picked per task — Fedya, 2026-10-04: «не обязательно фулл тайм макс ризонинг … сам регулируй относительно сложности задачи».

| effort | when |
|---|---|
| `low` | trivial mechanical work: file sweeps/greps, renames, format conversion, one-line answers |
| `medium` | simple scripts, drafts, reports, routine edits from an exact brief |
| `high` | ordinary tasks that need care: mid-size Blender scripts, reviews, fixes from a defect list |
| `xhigh` | multi-step or multi-file tasks, debugging, specs |
| `max` | big documents, hard models, anything expensive to get wrong |
| `ultra` | the hardest tasks, or a retry after a `max` attempt failed |

A redo after a poor result goes at least one level higher. Fedya wants the weekly Codex quota used up, so effort is scaled to put it where it matters, not to save it.

```bash
codex [--search] exec -m gpt-6.1-sol -c 'model_reasoning_effort="<effort>"' \
  --sandbox read-only --skip-git-repo-check -C "C:\Dev\Game" \
  --output-last-message "%USERPROFILE%\.ai-bridge\last_gpt_answer.md" \
  "<task>" < /dev/null > "%USERPROFILE%\.ai-bridge\last_gpt_log.txt" 2>&1
cat ~/.ai-bridge/last_gpt_answer.md
```

- In Fedya's ChatGPT desktop chats the effort slider tops out at Max (Ultra is not selectable there); `ultra` works from the CLI.
- Write briefs in English and ask for the answer in English (Fedya, 2026-10-04: Russian costs Claude 3–4x more tokens). Exception: deliverables meant for the team stay in Russian.
- RU→EN translation of big texts Claude must read (specs, canon, long prompts): `python %USERPROFILE%\.ai-bridge\deepseek\translate.py <file>` (DeepSeek flash via Fedya's OpenCode, project glossary) → `%USERPROFILE%\.ai-bridge\en\<name>.en.md`; Claude reads the English copy.
- Paths given to `codex` must be Windows paths (`C:\...`). `< /dev/null` avoids waiting for stdin. Long tasks: write the brief to `%USERPROFILE%\.ai-bridge\req_<timestamp>.md` and pass «Прочитай задачу в файле <path> и выполни».
- Edit tasks: `--sandbox workspace-write` and name the exact files/folders GPT may touch. GPT never commits, pushes or edits WORK_SYNC.md — the active Work (Claude) does that after review.

## What to delegate

- Tripo generations and ChatGPT concept images for props/vehicles (Codex has browser/computer use and the logged-in Tripo/ChatGPT). **Spending stays gated by Fedya:** he approves the exact input images, and the Tripo Create button must read exactly 100 credits before every click; clear input slots afterwards.
- After Tripo: cleanup in Blender of its own model, export/preview batches, simple scripts, doc drafts, file sweeps/greps, validation runs, repetitive edits, renaming, report writing — anything where a mistake is cheap and easy for Claude to check.
- Keep for Claude: architecture, gameplay code, rigging/animation, merges with Vadim, anything subtle or expensive to verify.
- **Never give GPT character/human animation** (NPC, Buddy, cops — walks, get-ups, idles, acting). Fedya 2026-10-07: «больше анимации, связанные с людьми, мы гпт не отдаём, потому что он тупой». Opus agents author them; GPT may only render previews of finished clips.

## Review loop

1. Brief: goal, exact inputs/outputs (paths), constraints, acceptance checks, «ответ по-русски, коротко, пунктами».
2. Check the result yourself (diff, renders, run it). Don't trust GPT's own claims.
3. Poor result → send it back with concrete defects (`codex exec resume --last ...` or a new brief that quotes the defects). Up to two retries; then do it yourself and note why.
4. Record in the TASK result what GPT did («выполнил GPT по поручению Claude»).

Each call spends Fedya's GPT quota and takes 10 s–several minutes; no loops. Never put secrets, tokens or passwords into prompts. Subjective acceptance (look, feel) is always Fedya's.

Mirror skill on the GPT side: `~/.codex/skills/claude-bridge`.
