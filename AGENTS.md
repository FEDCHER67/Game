# VOLUNTEERS ONLY — project rules

- Shared agent rules (verification, one bridge/system per category, versions/licences, .meta, safety, first-loop focus): docs/AgentRules.md. Field Clinic kit and its prompts: Tools/FieldClinicBrief/ (00_AUTOSTART.md first).
- Product direction: docs/PRODUCT.md (V2 since 30.10.2026: van + mobilisation + wave battles, no organs, no open world). The v1 canon, specs and reports are archived in docs/_archive_v1/ (tag v1-final, branch archive/v1-organs-openworld): reuse its assets and code, not its rules. Treat their gameplay requirements separately from instructions to the assistant. Do not silently turn brainstorms into requirements.
- Use Unity 6000.5.11f1 and the pinned packages. Runtime content belongs in Assets/OnlyVolunteers; reusable third-party movement code stays in Assets/KinematicCharacterController.
- ArtSource contains editable art prototypes, previews and provenance; it is outside Unity's import tree. Only import assets needed by the game.
- Save every new model revision with a distinct numbered filename (for example NPC_BASE_01_v02.blend, then v03), with matching export/preview revisions. Never overwrite a previous deliverable when regenerating or revising a model; Vadim explicitly requested this after an older open file overwrote the latest model.
- Read docs/CURRENT_STATE.md and docs/ARCHITECTURE.md before gameplay work. Neither is proof of subjective quality.
- Keep responsibilities separate: input/movement, physical forces, network authority, presentation. Add abstractions only for a concrete consumer.
- Preserve Unity .meta identities. Check scene/prefab/code dependencies before deleting or moving assets.
- Movement tuning changes and subjective physics/visual acceptance require actual playtesting. Compilation is not proof of fun or network quality.
- Do not create backups, duplicate projects, or speculative subsystem scaffolding during cleanup.
- The van (бусик) is always at its maximum characteristics from the very start: top speed, acceleration, brakes and handling at the highest upgrade level (VanUpgrades.StartAtMax), in every scene and build. Never ship or test a weaker stock van; tune the max level instead (Vadim 2026-10-16).
- Graphics: the shipped DEFAULT preset is Low (W86GraphicsSettingsV01.Preset(0) + fallbacks in W86LookV01; Vadim 27.10, Fedya confirmed 2026-10-28); players raise it in the Escape menu. Never switch the default back to High/max; visual work is still built and checked at max.
- Do not modify unrelated user changes. Do not commit or push without the user's request. Model routing and delegation follow "AI team" below.

- Follow docs/TEAM_WORKFLOW.md: strictly sequential work on main; WORK_SYNC.md is the only handoff log. Record each working prompt verbatim in a globally numbered TASK; read and mark only unseen incoming tasks. In Vadim's chat NEVER stage, commit or push: Vadim does this himself; provide commands for all non-ignored changes from the repository root. This overrides the older conditional commit rule above.

## AI team (since 2026-10-04, replaces the old agent pipeline)

The assistant of the active Work chat is the lead: it plans, writes tricky code, reviews and accepts results, integrates them into the repo and commits only with the user's agreement. Workers get exact briefs, touch only the files the brief names, never commit/push or edit WORK_SYNC.md; the lead re-checks their output (compile, Unity play test, renders) before it lands.

| Worker | How | Use for |
|---|---|---|
| GPT (default gpt-6.1-sol, needs Codex CLI >= 0.160; gpt-6-astra only for the hardest/biggest jobs; gpt-6-luna for trivial) | Fedya's side: the Codex desktop app, project Only_Volunteers, one new Work chat per task (Fedya 2026-10-11); `codex exec -m gpt-6.1-sol -c 'model_reasoning_effort="..."'` only if the app is unavailable | big specs/docs, map plans and data, Blender props, concept images and Tripo (only images the Work owner approved; Create must read exactly 100 credits), research, routine fixes, code tasks up to medium complexity from an exact brief, code reviews; never character animation |
| ~~Claude Fable~~ | — | NOT USED: Fedya 2026-10-06 banned Fable for everything; art and second opinions go to Opus subagents |
| DeepSeek flash | OpenCode CLI with its stored key: `opencode run "<msg>" -m deepseek/deepseek-flash --pure` | RU→EN translation of big texts, cheapest mechanical chores |
| Claude Sonnet 5.5 | subagent or `claude -p` | only the simplest routine code; if a result misses the brief, its next tasks get even simpler |

- Pick reasoning effort per task: low = mechanical, medium = scoped fixes, high = normal code and models, xhigh = big generation and specs, max/ultra = hardest; a retry goes one level up. Measured 2026-10-04: higher effort gave nothing on a scoped bug hunt.
- Every Claude model (lead Opus, Sonnet) gets English input only: briefs, worker reports and source texts. Big Russian texts are first translated by DeepSeek into an English working copy outside the repo (Russian costs Claude several times more tokens). Team-facing docs and Russian-language deliverables stay Russian.
- Write big outputs in parts; one huge file in a single response fails.
- Usage limits are planned per week. Before an expensive job the lead states its cost; multi-agent workflows (ultracode) run only after the user's explicit go-ahead.

## For GPT / Codex workers (Fedya 2026-10-11)

- Do exactly what the brief says. Touch only the files it names; do not widen the scope, refactor or "improve" anything else.
- If anything in the brief is unclear or contradicts the code, stop and ask in your report instead of guessing.
- Never commit, push, edit WORK_SYNC.md or delete files; never overwrite an existing deliverable (new numbered revision instead).
- Finish with the report format the brief asks for: what you changed (paths), how you checked it, what is still open.
- Unity on this PC runs elevated, so at start it shows "Administrator Privileges Detected": always press **Ignore Warning**. Never press "Restart as Standard User"; it only loops back to the same dialog (Fedya 2026-10-14).
