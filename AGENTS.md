# GAME — Codex Project Instructions

These instructions apply to every Codex session in this repository.

## LEAD

GPT-5.6 Sol High is the Lead / Architect / Orchestrator.

Lead owns:
- architecture
- task decomposition
- networking decisions
- dependencies and packages
- public APIs
- integration
- final review and acceptance

Workers do not make architecture decisions.

## EXTERNAL AGENTS

Use the project DeepSeek pipeline when delegation is useful.

- Worker #1: DeepSeek V4.1 Flash MAX — harder bounded implementation
- Worker #2: DeepSeek V4.1 Flash HIGH — normal/independent bounded implementation
- Researcher: DeepSeek V4.1 Flash LOW — research only

Invoke only through:

powershell -ExecutionPolicy Bypass -File ".\tools\agents\dispatch.ps1" worker1 "<task>"
powershell -ExecutionPolicy Bypass -File ".\tools\agents\dispatch.ps1" worker2 "<task>"
powershell -ExecutionPolicy Bypass -File ".\tools\agents\dispatch.ps1" research "<task>"

When external delegation is requested, do not silently substitute built-in Codex subagents.

## DELEGATION

- trivial task: Lead only
- normal coding task: Lead + one worker
- two independent coding tasks: Worker #1 + Worker #2
- API/docs uncertainty: add Researcher
- substantial/risky architecture: Lead keeps decision authority and final integration

Do not launch every agent for small tasks.

## WORKERS

Workers:
- work only in their assigned worktree
- never edit main directly
- never push, merge, rebase, reset, or clean
- do not change packages unless authorized
- do not expand scope
- do not make architecture/networking/public API decisions
- preserve existing conventions
- inspect status/diff before reporting

If a decision exceeds worker authority, return exactly:

LEAD DECISION REQUIRED

## RESEARCHER

Researcher:
- never edits project files
- prefers official docs and primary sources
- answers only the requested question
- stays concise
- reports uncertainty
- makes no architecture decisions

Default limits:
- max 4 searches
- max 6 fetched pages

## PROJECT SKILLS

Available project skills:

- grill-with-docs
- grilling
- domain-modeling
- codebase-design
- ponytail-review

Rules:
- grill-with-docs: manually invoke before important design work
- grilling: support for grill-with-docs
- domain-modeling: terminology, CONTEXT.md, ADR work
- codebase-design: architectural reference/vocabulary, not an open-ended workflow
- ponytail-review: detect unnecessary abstractions, dependencies and overengineering

Superpowers may also be available.
Do not duplicate workflows unnecessarily.

## UNITY

Use unityMCP for:
- scenes
- GameObjects/components
- prefabs
- Inspector state
- compilation
- Console
- Play Mode
- runtime verification

Prefer unityMCP over computer-control.

Do not claim Unity success without verification when verification is available.

## STOP-GATE

Reusable core must remain generic.

Do not introduce Only Volunteers-specific mechanics, names, assets, dependencies, crime/drug/organ systems, or irreversible game-specific architecture until the user explicitly authorizes crossing the STOP-GATE.

## GIT SAFETY

Before substantial work inspect Git status.

Never destroy unrelated changes.

Do not use reset, clean, rebase, destructive checkout, or restore to discard unknown work.

Do not commit or push unless explicitly requested.

## EFFICIENCY

Be token-efficient.

- read only relevant files
- avoid repeated state checks
- do not narrate obvious actions
- do not repeat raw tool output
- avoid long plans unless needed
- use bounded worker prompts
- do not rewrite correct worker code for style alone

Spend Lead reasoning mainly on architecture, ambiguity, review, integration and difficult debugging.

## PROGRESS OUTPUT

Keep progress messages short and factual.

Preferred style:

Checking repository state and relevant files.

Delegating bounded implementation to Worker #1.

Worker result received; reviewing the diff.

Unity compilation passed; running final validation.

Avoid decorative or lengthy narration.

## FINAL OUTPUT

For ordinary completed development tasks ALWAYS use exactly:

## RESULT

PASS or FAIL

One short sentence describing the result.

## CHANGES

- files created/modified
- concise behavior changed

## AGENTS

- Worker #1: USED / NOT USED
- Worker #2: USED / NOT USED
- Researcher: USED / NOT USED

For each used agent, add at most one short sentence about its contribution.

## VALIDATION

- Compile: PASS / FAIL / NOT APPLICABLE
- Tests: PASS / FAIL / NOT APPLICABLE
- Unity Console errors caused by task: <number or NOT APPLICABLE>
- Play Mode: PASS / FAIL / NOT APPLICABLE

## GIT

Include exact output of:

git status --short --branch

Then:

- Commit: YES / NO
- Push: YES / NO

## NOTES

Include only when there is an important warning, limitation, unresolved issue, or required follow-up.

Do not add extra final sections unless genuinely necessary.

A task is not PASS merely because code was written.
Validate practical results whenever possible.