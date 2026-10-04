# VOLUNTEERS ONLY — project rules

- Product direction: docs/PRODUCT.md and docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md. Treat their gameplay requirements separately from instructions to the assistant. Do not silently turn brainstorms into requirements.
- Use Unity 6000.5.11f1 and the pinned packages. Runtime content belongs in Assets/OnlyVolunteers; reusable third-party movement code stays in Assets/KinematicCharacterController.
- ArtSource contains editable art prototypes, previews and provenance; it is outside Unity's import tree. Only import assets needed by the game.
- Save every new model revision with a distinct numbered filename (for example NPC_BASE_01_v02.blend, then v03), with matching export/preview revisions. Never overwrite a previous deliverable when regenerating or revising a model; Vadim explicitly requested this after an older open file overwrote the latest model.
- Read docs/CURRENT_STATE.md and docs/ARCHITECTURE.md before gameplay work. Neither is proof of subjective quality.
- Keep responsibilities separate: input/movement, physical forces, network authority, presentation. Add abstractions only for a concrete consumer.
- Preserve Unity .meta identities. Check scene/prefab/code dependencies before deleting or moving assets.
- Movement tuning changes and subjective physics/visual acceptance require actual playtesting. Compilation is not proof of fun or network quality.
- Do not create backups, duplicate projects, or speculative subsystem scaffolding during cleanup.
- Do not modify unrelated user changes. Do not commit or push without the user's request. Model routing and delegation follow "AI team" below.

- Follow docs/TEAM_WORKFLOW.md: strictly sequential work on main; WORK_SYNC.md is the only handoff log. Record each working prompt verbatim in a globally numbered TASK; read and mark only unseen incoming tasks. In Vadim's chat NEVER stage, commit or push: Vadim does this himself; provide commands for all non-ignored changes from the repository root. This overrides the older conditional commit rule above.

## AI team (since 2026-10-04, replaces the old agent pipeline)

The assistant of the active Work chat is the lead: it plans, writes tricky code, reviews and accepts results, integrates them into the repo and commits only with the user's agreement. Workers get exact briefs, touch only the files the brief names, never commit/push or edit WORK_SYNC.md; the lead re-checks their output (compile, Unity play test, renders) before it lands.

| Worker | How | Use for |
|---|---|---|
| GPT (default gpt-6.1-sol, needs Codex CLI >= 0.160; gpt-6-astra only for the hardest/biggest jobs; gpt-6-luna for trivial) | `codex exec -m gpt-6.1-sol -c 'model_reasoning_effort="..."'`; web research: `codex --search exec ...` | big specs/docs, map plans and data, Blender props, concept images and Tripo (only images the Work owner approved; Create must read exactly 100 credits), research, routine fixes |
| Claude Fable 5.1 | subagent, or `claude -p --model claude-fable-5-1 --effort ...` | art/visual work where the look matters, second opinion on hard design, Russian dialogue/humour as output (brief still in English); slower, ~3x Opus cost, separate weekly limit |
| DeepSeek flash | OpenCode CLI with its stored key: `opencode run "<msg>" -m deepseek/deepseek-flash --pure` | RU→EN translation of big texts, cheapest mechanical chores |
| Claude Sonnet 5.5 | subagent or `claude -p` | only the simplest routine code; if a result misses the brief, its next tasks get even simpler |

- Pick reasoning effort per task: low = mechanical, medium = scoped fixes, high = normal code and models, xhigh = big generation and specs, max/ultra = hardest; a retry goes one level up. Measured 2026-10-04: higher effort gave nothing on a scoped bug hunt.
- Every Claude model (lead Opus, Fable, Sonnet) gets English input only: briefs, worker reports and source texts. Big Russian texts are first translated by DeepSeek into an English working copy outside the repo (Russian costs Claude several times more tokens). Team-facing docs and Russian-language deliverables stay Russian.
- Write big outputs in parts; one huge file in a single response fails.
- Usage limits are planned per week. Before an expensive job the lead states its cost; multi-agent workflows (ultracode) run only after the user's explicit go-ahead.
