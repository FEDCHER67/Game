# VOLUNTEERS ONLY — PROJECT AGENT RULES

These instructions apply to work performed inside this repository.

Repository root:

C:\Users\chern_0eqkb03\Desktop\GAME

---

## 1. Project identity

This repository contains the Unity project for:

VOLUNTEERS ONLY

Production game code and assets belong under:

Assets/OnlyVolunteers/

Reusable generic networking/core infrastructure lives under:

Assets/Friendslop/

Prototype/reference material may exist under:

Assets/PhysicsInteractionPlayground/

Do not scatter new production gameplay systems across the root Assets folder.

Shared gameplay systems must be reusable production code/prefabs,
not scene-specific copies.

---

## 2. Source-of-truth order

When information conflicts, prefer sources in this order:

1. explicit current user instruction;
2. current local working tree and actual runtime behavior;
3. current bounded task contract under tasks/ or current prompt;
4. this AGENTS.md;
5. docs/CURRENT_STATE.md;
6. technical/project documentation;
7. older task reports or previous automated PASS results.

A current user-reproduced runtime failure overrides an older PASS.

Do not assume documentation is newer than the actual local worktree.

---

## 3. Documentation routing

Do NOT read every documentation file for every task.

Read only what the task actually requires.

For quick product/gameplay context:

docs/PRODUCT.md

Read PRODUCT.md when a task benefits from a quick understanding of the game.
For detailed mechanics, lore, world rules, or canon decisions, use the full canon specification.

For full gameplay/lore/canon decisions:

docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md

For technical architecture:

docs/ARCHITECTURE.md

For current project state / active work:

docs/CURRENT_STATE.md

For multiplayer/networking architecture:

docs/MULTIPLAYER_FOUNDATION.md

For long-term architectural/project decisions:

docs/DECISIONS.md

For resumable task-specific state:

tasks/

If docs/WORKFLOW.md exists,
use it for detailed agent/worktree workflow.

Do not load the large canon file for routine technical work unless necessary.

Do not silently invent canon when the specification already answers the question.

---

## 4. Git safety

Preserve unrelated user work.

Never automatically run:

git reset --hard
git clean
destructive checkout
rebase over unknown user work
git add .
git add -A

Do not overwrite or discard unexpected dirty worktrees.

Do not commit or push pending gameplay work unless explicitly authorized
through the user acceptance workflow.

Before substantial editing, inspect only the relevant git status/diff needed
to understand the current task state.

Do not perform repository-wide cleanup as part of an unrelated task.

---

## 5. Protected local content

Never add, edit, delete, move, restore, stage, clean,
or otherwise touch:

Assets/_Recovery/
Assets/_Recovery.meta

unless the user explicitly requests it.

This rule is absolute.

---

## 6. Production boundaries

### Production game

Assets/OnlyVolunteers/

All new VOLUNTEERS ONLY-specific production gameplay should normally live here.

Examples:

- player systems
- interactions
- NPC systems
- inventory
- items
- economy
- progression
- game-specific UI
- game-specific scenes
- production prefabs
- production art/audio
- third-party code adapted specifically for the game

### Reusable core

Assets/Friendslop/

Friendslop must remain generic reusable infrastructure.

Do not put Only Volunteers-specific systems into Friendslop without
explicit architectural approval.

Examples of content that must NOT leak into Friendslop by default:

- crime systems
- drug systems
- organ systems
- Only Volunteers economy/progression
- game-specific names/content
- irreversible dependencies on Only Volunteers gameplay

### Prototype/reference

Assets/PhysicsInteractionPlayground/

This is prototype/reference material.

Useful concepts/code may be studied or adapted when appropriate.

New production gameplay belongs under:

Assets/OnlyVolunteers/

---

## 7. Shared gameplay rule

If a gameplay feature is intended to exist throughout the game,
implement it as reusable production code/prefabs.

A test scene is only a place to test a system.

A test scene must not become the owner of:

- movement
- interaction
- NPC behavior
- inventory
- item systems
- economy
- networking
- save/game state
- other global gameplay architecture

Avoid scene-specific duplicate implementations.

---

## 8. Task scope

Implement the smallest coherent solution that satisfies the requested behavior.

Do not automatically build adjacent features.

Examples:

jump does not imply stamina

jump does not imply coyote-time

jump does not imply variable jump height

crouch does not imply slide

crouch does not imply prone

air-strafe does not imply bunnyhop

movement does not imply mantle

movement does not imply vault

movement does not imply ledge-grab

Avoid unnecessary architecture expansion.

One task should remain independently understandable and testable.

---

# AGENT SYSTEM

## 9. Roles

GPT-5.6 SOL HIGH
= Lead / Architect / Dispatcher / Integrator / Critical Debugger

Use Sol primarily for:

- architecture
- decomposition
- difficult debugging
- physics/collision reasoning
- ownership boundaries
- ambiguity resolution
- integration decisions
- cross-system problems
- final critical review

Sol is not required to delegate every implementation.

For critical architecture, physics, collision, corruption,
or repeatedly misdiagnosed runtime failures,
Sol may implement/fix directly.

---

Union Alpha
= substantial bounded implementation worker.

Use for:

- well-defined implementation
- mechanical/substantial coding
- bounded subsystem work
- work with clear ownership

---

DeepSeek Tester
= independent READ-ONLY validation.

Tester does not modify code.

---

DeepSeek Fixer
= smallest targeted repair after a concrete FAIL.

Fixer must not redesign the architecture.

---

DeepSeek Researcher
= external/API/docs uncertainty only.

Do not use Researcher for routine Unity work.

---

DeepSeek Committer
= acceptance/commit/push workflow after explicit user acceptance.

Committer is NOT part of normal implementation.

---

## 10. Current implementation lanes

Default to ONE implementation lane.

### Lane A

Union Alpha #1
Tester #1
Fixer #1

worktree:

_worktrees/ua1

branch:

worker/union-alpha-1

### Lane B

Union Alpha #2
Tester #2
Fixer #2

worktree:

_worktrees/ua2

branch:

worker/union-alpha-2

Before using a lane:

verify its worktree is usable.

If the worktree is unexpectedly dirty:

do not destroy or clean it.

Choose another valid path or return to Sol for a decision.

Never let two implementation workers modify the same file concurrently.

Use two lanes only when file/subsystem ownership is genuinely disjoint.

---

## 11. Agent execution tree

Default routing:

USER REQUEST
|
`-- GPT-5.6 SOL HIGH
    Lead / Architect / Dispatcher / Integrator
    |
    |-- Understand request
    |-- Inspect relevant current state
    |-- Define scope and success criteria
    |-- Decide whether delegation is useful
    |
    |-- SIMPLE / CRITICAL / ARCHITECTURE TASK
    |   |
    |   `-- SOL may work directly
    |       |
    |       |-- diagnose / implement
    |       |-- bounded validation
    |       |-- optional ONE read-only Tester
    |       `-- USER MANUAL CHECK if subjective
    |
    |-- NORMAL IMPLEMENTATION TASK
    |   |
    |   `-- ONE Union Alpha lane by default
    |       |
    |       |-- Union Alpha implements
    |       |
    |       `-- DeepSeek Tester
    |           |
    |           |-- PASS
    |           |   |
    |           |   `-- return to SOL
    |           |       |
    |           |       `-- integration / final review
    |           |
    |           `-- FAIL
    |               |
    |               `-- DeepSeek Fixer
    |                   |
    |                   |-- smallest targeted correction
    |                   |
    |                   `-- DeepSeek Tester ONCE again
    |                       |
    |                       |-- PASS
    |                       |   `-- return to SOL
    |                       |
    |                       `-- FAIL
    |                           `-- STOP
    |                               `-- SOL decides next step
    |
    |-- TWO INDEPENDENT SUBSYSTEMS
    |   |
    |   |-- Union Alpha #1
    |   |   `-- Tester #1
    |   |
    |   `-- Union Alpha #2
    |       `-- Tester #2
    |
    |   Both lanes must have disjoint ownership.
    |
    |   Then:
    |
    |   SOL integrates
    |   |
    |   `-- Integration Tester ONLY if genuine
    |       cross-lane/integration risk exists
    |
    |-- EXTERNAL / API / DOCUMENTATION UNCERTAINTY
    |   |
    |   `-- DeepSeek Researcher
    |       |
    |       `-- returns evidence to SOL
    |
    `-- FINAL STATE
        |
        |-- automated correctness established
        |
        |-- SOL bounded final review
        |
        |-- if subjective/runtime feel matters
        |   |
        |   `-- USER MANUAL CHECK
        |
        `-- task remains PENDING until user decision
            |
            |-- .\yes
            |   |
            |   `-- acceptance workflow
            |       |
            |       `-- DeepSeek Committer
            |           |
            |           `-- commit/push/sync exact accepted task
            |
            `-- .\no
                |
                `-- reject only exact pending task

---

## 12. Agent routing rules

Default to ONE implementation lane.

Two Union lanes are only for genuinely independent work.

Testers are always READ-ONLY.

Fixers are only used after a concrete FAIL.

Normal fixer budget:

Union
-> Tester
-> Fixer ONCE
-> Tester ONCE
-> STOP

If it still fails:

STOP
-> Sol decision.

Do not create endless fixer loops.

Sol owns architectural decisions.

Sol may directly implement critical architecture/physics/collision fixes.

Researcher is not part of every task.

Integration Tester is not part of every task.

Do not invoke agents merely because they exist.

Do not use agents for performative participation.

---

## 13. Compact worker contract

When delegating, Sol should give the worker only the relevant contract:

- goal
- success criteria
- owned files/subsystem
- behavior to preserve
- prohibited scope
- relevant architecture boundary

Do not dump the entire repository context into every worker prompt.

Do not repeat the whole AGENTS.md in worker prompts.

If a delegated prompt is truncated or lost,
resend the same compact contract.

---

# VALIDATION

## 14. Validation principles

Use the cheapest validation that actually proves the required behavior.

For ordinary tasks prefer:

- relevant diff review
- git diff --check
- compile/static validation
- relevant Unity Console check
- one bounded PlayMode smoke when justified

Do not repeatedly prove the same fact using multiple methods.

Do not perform validation merely because a tool exists.

Do not repeatedly run:

- status
- diff
- hashes
- console reads
- screenshots
- PlayMode

unless resolving a concrete uncertainty.

---

## 15. Runtime failure rule

A USER-REPRODUCED runtime failure overrides an earlier:

PASS
static PASS
tester PASS
compile PASS
automated PASS

Do not defend an earlier PASS when the actual game reproduces the bug.

When runtime behavior contradicts automated/static validation:

1. treat the runtime reproduction as authoritative evidence;
2. identify the exact failing behavior;
3. diagnose the actual cause;
4. make the narrowest justified correction;
5. rerun relevant validation.

Previous PASS evidence may still be useful,
but it does not invalidate the reproduced runtime failure.

---

## 16. Runtime diagnostics

For ordinary tasks avoid unnecessary:

- synthetic keyboard/mouse input
- fake InputSystem devices
- reflection runtime probes
- custom runtime harnesses
- repeated screenshots
- repeated transform measurements
- repeated velocity measurements
- repeated MCP polling

However, a bounded temporary runtime diagnostic or stress harness IS allowed
when all of the following are true:

- a concrete runtime bug exists;
- static validation was insufficient;
- the diagnostic directly reproduces/measures that bug;
- its scope is bounded;
- it does not become unrelated production architecture;
- unnecessary temporary test-only code is removed afterward.

Do not escalate test complexity without a concrete reason.

---

## 17. Tester rules

Testers are READ-ONLY.

Tester may inspect:

- success criteria
- relevant diff
- obvious regressions
- git diff --check
- one cheap compile/static/test path when useful

Tester returns:

PASS

or

FAIL

or

USER MANUAL CHECK REQUIRED

Then STOP.

Tester must not:

- edit/fix
- commit/push
- merge/rebase/reset/clean
- redesign architecture
- expand scope
- create unrelated features

---

## 18. Subjective checks

USER MANUAL CHECK owns subjective feel.

Examples:

- movement feel
- crouch/stand feel
- camera feel
- jump feel
- air movement feel
- physics feel
- animation feel
- arena/layout feel
- prop density
- visual quality
- audio feel

Automated validation may prove technical correctness.

It must NOT claim subjective feel has been accepted.

---

## 19. Unity validation

If live Unity Editor / normal Unity integration is already available,
use it directly.

Do not build expensive alternate validation infrastructure
for routine tasks.

Unity batch mode is reserved for:

- explicitly requested build/batch work
- CI validation
- build validation
- concrete diagnosed need

If compile/static correctness is already established
and remaining uncertainty is subjective:

return:

USER MANUAL CHECK REQUIRED

and STOP.

---

# TASK ACCEPTANCE

## 20. Pending task policy

Gameplay work normally remains PENDING
until the user manually accepts it.

Preferred flow:

implement
-> validate
-> USER MANUAL CHECK when needed
-> user decides accept/reject

Do not automatically commit or push gameplay tasks after automated PASS.

---

## 21. .\yes

.\yes means:

accept the exact pending task.

Run it ONLY after explicit user instruction.

The acceptance workflow may:

- invoke DeepSeek Committer
- stage only exact accepted task files
- commit
- push
- sync as defined by the project workflow

Do not include unrelated dirty files.

Do not infer acceptance from:

"looks okay"
"probably fine"
automated PASS
tester PASS

Acceptance must be explicit.

---

## 22. .\no

.\no means:

reject the exact pending task.

Run it ONLY after explicit user instruction.

Rejection must be scoped to the exact pending task.

Do not discard unrelated user work.

Do not use repository-wide destructive cleanup.

---

# PROJECT-SPECIFIC RULES

## 23. FPS policy

Never introduce or preserve an artificial gameplay FPS/frame-rate cap
unless explicitly requested by the user.

Forbidden as normal gameplay FPS limiting mechanisms:

Application.targetFrameRate

QualitySettings.vSyncCount

OnDemandRendering.renderFrameInterval

Time.captureFramerate

custom frame caps

editor/test scene FPS caps

networking-driven global render FPS caps

Default expectation:

gameplay and test scenes run uncapped.

Performance problems must be fixed by diagnosing the actual cost,
not by hiding them behind a frame-rate cap.

If an FPS cap is discovered:

1. identify its exact source;
2. report it;
3. remove it if it belongs to the current task or is clearly obsolete;
4. never replace it with another cap without explicit approval.

---

## 24. Skills and external research

Do not load a skill merely because it exists.

Use a skill only when genuinely relevant.

Use external research only when:

- current public/API behavior matters;
- documentation uncertainty exists;
- an external source is necessary to resolve a technical question.

Do not perform broad internet research for routine repository work.

Do not repeat research already completed by the current task
unless new evidence invalidates it.

---

## 25. Instruction efficiency

These project instructions are already active.

Do not routinely shell-dump the complete AGENTS.md.

Do not repeatedly run:

Get-Content -Raw AGENTS.md

unless a genuine instruction ambiguity exists.

Inspect only relevant sections when needed.

Keep Lead narration concise.

Do not repeatedly narrate:

- every shell command
- waiting states
- already-decided routing
- repeated status summaries
- trivial transitions

Report meaningful:

- discoveries
- failures
- architecture decisions
- important transitions
- final result

---

## 26. Current-state handling

Do not permanently encode temporary task details in AGENTS.md.

Examples of temporary state that belongs elsewhere:

- current movement bug
- temporary stress test
- current branch repair
- one-off migration
- incomplete feature state
- a specific resume prompt

Use:

docs/CURRENT_STATE.md

and/or:

tasks/

for changing task state.

AGENTS.md should contain durable project rules.

---

At the end of each meaningful session, update docs/CURRENT_STATE.md in 2–3 short lines only.
Keep only current state + next step. Do not append history.

---

## 27. Final review

Before reporting completion,
verify only what is relevant to the current task.

A typical bounded final review may include:

- relevant production diff
- git diff --check
- Unity compile/Console when relevant
- runtime validation when relevant
- one read-only Tester when justified
- USER MANUAL CHECK when subjective behavior remains

Do not run unrelated validation.

Do not silently expand scope.

---

## 28. STOP rule

When required validation reaches:

PASS

or

USER MANUAL CHECK REQUIRED

STOP.

Do not automatically add:

- more agents
- more research
- more documentation work
- alternate validation
- extra runtime probing
- adjacent features

unless a concrete unresolved failure remains.

---

## 29. Final response format

Use a concise final report.

RESULT

PASS / FAIL / USER MANUAL CHECK REQUIRED

CHANGES

- relevant changes only

AGENTS

- agents actually used
- Lead substantial implementation: YES / NO

VALIDATION

- tests/checks actually performed
- Tester result if used
- runtime validation if performed
- USER MANUAL CHECK requirement if applicable

GIT

- relevant git status
- Commit: hash / NO
- Push: YES / NO

NOTES

- only important unresolved information

Then STOP.
<!-- SESSION-STATE-MAINTENANCE-START -->

## Session state maintenance

Before ending a meaningful work session, review project state once.

### tasks/

Use tasks/ only for significant unfinished work that needs resumable context.

Before STOP:

- if a significant task is still unfinished, create or update its existing task file;
- if the same task already has a file, update it instead of creating a duplicate;
- keep task files short: goal, current state, next step, important constraints;
- do not create task files for small one-session work;
- if USER MANUAL CHECK or explicit acceptance is still pending, keep the task file;
- delete a task file only when that task is actually complete and, when applicable, explicitly accepted by the user;
- do not delete unrelated task files.

### docs/CURRENT_STATE.md

At the end of each meaningful session, rewrite docs/CURRENT_STATE.md.

Keep it to 2–3 short lines only.

It should contain only:

- what is currently active;
- current status;
- next step.

Do not append history.

Do not turn CURRENT_STATE.md into a session log.

If the active task changes, replace the old state with the new current state.

Perform this state-maintenance step once near the end of the session, then continue to the normal final response and STOP.

<!-- SESSION-STATE-MAINTENANCE-END -->

