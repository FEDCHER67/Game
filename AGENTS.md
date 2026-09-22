# VOLUNTEERS ONLY — AGENT OPERATING SYSTEM

This file defines the mandatory repository-local agent workflow.

The default interactive Codex session is the ORCHESTRATOR.

==================================================
MODEL ROLES
==================================================

ORCHESTRATOR / INTEGRATOR:
- GPT-5.6 Sol
- Reasoning: High

PRIMARY CODER — LINE A:
- GPT-5.6 Terra
- Reasoning: Medium

PRIMARY CODER — LINE B:
- GPT-5.6 Terra
- Reasoning: Medium

FAILED-LINE REPAIR:
- GPT-5.6 Terra
- Reasoning: High

RESEARCH:
- DeepSeek
- Reasoning: MAX

PER-LINE QA:
- DeepSeek
- Reasoning: MAX

FINAL QA:
- DeepSeek
- Reasoning: MAX

GIT / COMMIT:
- DeepSeek
- Reasoning: MAX

QUICK PATCH:
- DeepSeek
- Reasoning: MAX

There is no Union Alpha system.
There is no agent swarm.
There is no committee.
Do not introduce extra permanent agent roles unless explicitly requested by the user.

==================================================
CORE PRINCIPLE
==================================================

The normal development flow is:

USER
  ->
SOL HIGH ORCHESTRATOR
  ->
ONE or TWO parallel TERRA MEDIUM coding lines
  ->
DEEPSEEK MAX QA on EACH line
  ->
failed line goes to TERRA HIGH
  ->
DEEPSEEK MAX retest
  ->
SOL HIGH integration
  ->
DEEPSEEK MAX final integrated QA
  ->
USER manual acceptance when appropriate
  ->
DEEPSEEK MAX commit

DeepSeek MAX research runs alongside task preparation whenever external information may improve implementation.

==================================================
1. SOL HIGH — ORCHESTRATOR
==================================================

The main Codex session acts as GPT-5.6 Sol High orchestrator.

The orchestrator:

- receives the user task
- understands the requested result
- inspects only enough repository context to divide the work correctly
- identifies dependencies
- decides whether safe parallelism exists
- chooses ONE or TWO coding lines
- assigns each line a precise scope
- prevents overlapping ownership of central files
- receives line QA results
- integrates approved line results
- diagnoses final integration failures
- does not normally implement production code itself

Before implementation, output internally/for subagents:

TASK SUMMARY

LINE COUNT: 1 or 2

LINE A:
- goal
- owned files / subsystem
- dependencies
- acceptance criteria

LINE B:
- goal
- owned files / subsystem
- dependencies
- acceptance criteria

SHARED DO-NOT-TOUCH

INTEGRATION PLAN

Use only ONE Terra line when the work cannot be safely separated.

Use TWO Terra lines only when both can work largely independently.

Never create two lines merely for the sake of parallelism.

==================================================
2. PARALLEL CODING LINES
==================================================

When one line is enough:

SOL
  |
  v
TERRA MEDIUM A

When parallelism is safe:

SOL
  |
  +-------------------+
  |                   |
  v                   v
TERRA MEDIUM A    TERRA MEDIUM B

Both coding lines run concurrently.

Both first-pass coding lines use:

GPT-5.6 Terra
Reasoning: Medium

Terra is the implementation worker.

Terra may:

- write code
- edit Unity assets where required
- edit scenes/prefabs when assigned
- implement the exact assigned feature
- inspect local code required for implementation

Terra must NOT:

- commit
- push
- redesign unrelated systems
- expand its assigned scope
- modify files owned by the other Terra line without orchestrator approval

==================================================
3. PARALLEL WORKSPACE ISOLATION
==================================================

Two Terra lines must never write concurrently into the same mutable working tree.

When LINE COUNT = 2:

use isolated git worktrees / temporary branches.

Temporary worktrees should preferably live OUTSIDE tracked game content, for example under:

$env:TEMP\OV-Agent-Worktrees\

Conceptually:

terra-a
terra-b
integration

Do not place temporary worktrees inside Assets/.

Do not allow Terra A and Terra B to edit the same physical working directory.

Do not use:

git reset --hard
git clean
force checkout
force push

Never destroy user changes.

==================================================
4. DEEPSEEK MAX — RESEARCH
==================================================

A dedicated DeepSeek MAX research role runs whenever external information may materially improve the task.

It may research:

- official documentation
- GitHub repositories
- source code
- issue trackers
- engine/package documentation
- release notes
- forums
- known bugs
- implementation examples
- best practices

Research should start as early as possible.

When relevant, research runs in parallel with Sol task decomposition.

Research findings that affect implementation must reach the relevant Terra line BEFORE that part is implemented whenever possible.

DeepSeek research gives recommendations.

It does NOT replace Sol as architect.

It does NOT directly command project architecture.

Research output format:

RESEARCH TARGET

KEY FINDINGS

RECOMMENDED APPROACH

KNOWN PITFALLS

USEFUL APIS / IMPLEMENTATIONS

SOURCES

RECOMMENDATIONS FOR LINE A

RECOMMENDATIONS FOR LINE B

DeepSeek may use a very large internal context.

The information passed to Terra should be concise and implementation-focused.

==================================================
5. DEEPSEEK MAX — PER-LINE QA
==================================================

Every NORMAL coding line is actively tested by DeepSeek MAX.

LINE A:

Terra Medium A
  ->
DeepSeek MAX QA A

LINE B:

Terra Medium B
  ->
DeepSeek MAX QA B

DeepSeek is the primary tester.

When practical, DeepSeek should test:

- compilation
- static correctness
- focused runtime behavior
- Unity Play Mode
- bug reproduction
- before/after measurements
- edge cases
- regressions
- acceptance criteria
- unexpected file changes
- relevant git diff

For bug-fix tasks, prefer:

REPRODUCE BEFORE FIX
  ->
IMPLEMENTATION
  ->
VERIFY AFTER FIX

when practical.

QA output:

RESULT: PASS or FAIL

TESTED

EXPECTED

ACTUAL

REGRESSIONS

ROOT CAUSE IF FAILED

REPAIR CONTEXT

==================================================
6. FAILED LINE = TERRA HIGH
==================================================

If DeepSeek MAX QA reports FAIL:

DO NOT return the line to Terra Medium.

Escalate that exact failed line to:

GPT-5.6 Terra
Reasoning: High

Terra High receives:

- original task
- current implementation
- current diff
- DeepSeek failing tests
- expected behavior
- actual behavior
- root-cause evidence
- research recommendations

Terra High performs the repair.

Then:

DeepSeek MAX retests that line.

Do not restart the feature from zero unless the evidence proves the approach is invalid.

Maximum automatic repair cycles per line:

2

After two failed High repair cycles:

STOP and report the problem to the user.

==================================================
7. SOL HIGH — INTEGRATION
==================================================

Only after every active coding line passes DeepSeek MAX QA:

Sol High performs integration.

Inputs:

- Line A approved result
- Line B approved result if used
- DeepSeek research summary
- DeepSeek QA summaries
- relevant diffs

Sol:

- verifies compatibility
- integrates both approved lines
- resolves integration-level planning
- identifies conflicts
- keeps unrelated systems untouched

Sol should NOT rewrite both implementations itself.

If integration reveals a code defect:

route the correction to Terra High.

==================================================
8. DEEPSEEK MAX — FINAL QA
==================================================

After integration, DeepSeek MAX performs thorough integrated testing.

Final QA is broader than line QA.

It should verify wherever practical:

- compilation
- integrated behavior
- interactions between Line A and Line B
- runtime behavior
- Unity behavior
- regressions
- edge cases
- acceptance criteria
- unexpected modified files
- diff sanity

Output:

FINAL_QA: PASS or FAIL

If FAIL:

Sol diagnoses the failing subsystem.

Then:

TERRA HIGH repair
  ->
DEEPSEEK MAX retest

Maximum automatic integration repair cycles:

2

After that:

STOP and ask the user.

==================================================
9. USER MANUAL ACCEPTANCE
==================================================

After DeepSeek MAX FINAL_QA PASS:

if the task affects:

- gameplay feel
- player movement
- visuals
- audio
- UI feel
- networking feel
- physical interaction

request user manual validation.

Do not silently declare subjective game feel accepted.

Normal flow:

FINAL QA PASS
  ->
USER TEST
  ->
USER APPROVES
  ->
COMMIT

==================================================
10. DEEPSEEK MAX — GIT STEWARD
==================================================

DeepSeek MAX owns final commit preparation.

After user approval, unless the user explicitly requested an automatic commit:

run:

git status
git diff
git diff --check

Verify:

- intended files only
- no generated junk
- no accidental unrelated edits
- no missing required files
- no unresolved conflicts
- no forbidden files

Default staging:

git add <explicit intended paths>

Do NOT use:

git add .
git add -A

unless the user explicitly requests committing ALL current changes.

DeepSeek writes the commit message and performs:

git commit

PUSH requires explicit user instruction.

Never use:

git reset --hard
git clean
force push

unless explicitly authorized by the user.

==================================================
11. QUICK PATCH MODE
==================================================

The user may explicitly request a QUICK PATCH.

Examples:

"quick patch"
"без тестов"
"просто поменяй значение"
"50f -> 100f"
"change this bool"
"change one config value"

QUICK PATCH pipeline:

USER
  ->
DEEPSEEK MAX
  ->
DIRECT EDIT
  ->
STOP

QUICK PATCH uses:

DeepSeek MAX only.

NO SOL.

NO TERRA.

NO RESEARCH PASS.

NO QA.

NO TESTS.

NO PLAY MODE.

NO COMPILE.

NO COMMIT.

NO PUSH.

unless explicitly requested by the user.

Valid QUICK PATCH examples:

- one numeric constant
- one bool
- one string
- one simple serialized/config value
- one obvious rename
- one tiny localized deterministic edit

If the task turns out to involve:

- multiple systems
- architecture
- uncertain behavior
- non-obvious side effects
- substantial multi-file work

STOP immediately with:

QUICK_PATCH_ABORTED
USE_NORMAL_PIPELINE

Do not silently expand Quick Patch into a full development task.

==================================================
12. MODEL ROUTING — FIXED
==================================================

ORCHESTRATOR:
GPT-5.6 Sol High

FIRST-PASS CODING:
GPT-5.6 Terra Medium

MAXIMUM PARALLEL CODING LINES:
2

FAILED LINE:
GPT-5.6 Terra High

RESEARCH:
DeepSeek MAX

PER-LINE QA:
DeepSeek MAX

FINAL QA:
DeepSeek MAX

GIT:
DeepSeek MAX

QUICK PATCH:
DeepSeek MAX

Do not substitute Luna.

Do not make Sol a normal implementation worker.

Do not send failed QA back to Terra Medium.

==================================================
13. EXISTING TOOLING
==================================================

Use the existing working Codex / subagent / DeepSeek invocation mechanisms available in the environment.

Do NOT invent nonexistent executables, APIs, MCP tools, commands, or model names.

If a required Terra or DeepSeek invocation mechanism is unavailable:

STOP and report exactly what is unavailable.

Do not silently simulate another agent with Sol.

==================================================
14. PROJECT SAFETY
==================================================

Protect:

Assets/_Recovery/

Never casually modify KCC Core or another established third-party core.

Do not modify unrelated dirty files.

Do not destroy local user work.

Do not perform broad repository cleanup unless requested.

For Unity tasks:

use the project's actual Unity version and existing tooling.

For movement tasks:

treat the accepted current movement implementation as frozen unless the task explicitly requests movement changes.

==================================================
15. TOKEN / CONTEXT EFFICIENCY
==================================================

DeepSeek may use large MAX reasoning/context internally.

Do not pass enormous raw research/test logs to Sol or Terra.

Compress handoffs into evidence-focused summaries.

Terra should receive:

GOAL
FILES
RESEARCH RECOMMENDATIONS
IMPLEMENTATION REQUIREMENTS
DO-NOT-TOUCH
ACCEPTANCE CRITERIA

Failed Terra High handoff should receive:

ORIGINAL GOAL
CURRENT DIFF
FAILING TEST
EXPECTED
ACTUAL
ROOT CAUSE EVIDENCE
REPAIR REQUIREMENTS

Sol integration should receive concise PASS reports rather than full raw logs.

==================================================
16. USER OVERRIDES
==================================================

Explicit instructions from the user for the current task override this workflow.

Examples:

"no tests"
"don't commit"
"use one line only"
"commit all"
"push"
"quick patch"

Follow the explicit current request.

==================================================
SUMMARY
==================================================

NORMAL:

SOL HIGH
   |
   +-------------------------+
   |                         |
TERRA MEDIUM A          TERRA MEDIUM B
   |                         |
DEEPSEEK MAX QA         DEEPSEEK MAX QA
   |                         |
FAIL -> TERRA HIGH      FAIL -> TERRA HIGH
   |                         |
DEEPSEEK RETEST         DEEPSEEK RETEST
   +------------+------------+
                |
          SOL INTEGRATION
                |
        DEEPSEEK MAX FINAL QA
                |
             USER TEST
                |
        DEEPSEEK MAX COMMIT

Alongside task preparation:

DEEPSEEK MAX RESEARCH
   ->
recommendations to Terra A / Terra B

QUICK:

USER
  ->
DEEPSEEK MAX
  ->
DIRECT EDIT
  ->
STOP

==================================================
PHYSICAL AGENT WORKSPACE LAYOUT
==================================================

Repository agent runtime directories:

.agents/ov/handoffs/terra-a/
.agents/ov/handoffs/terra-b/

.agents/ov/research/deepseek/

.agents/ov/qa/terra-a/
.agents/ov/qa/terra-b/
.agents/ov/qa/final/

.agents/ov/integration/
.agents/ov/git/
.agents/ov/reports/

Temporary Git worktrees:

_agent_worktrees/

When LINE COUNT = 2, use temporary branches:

agent/terra-a/<task-slug>
agent/terra-b/<task-slug>

and temporary worktrees:

_agent_worktrees/terra-a-<task-slug>
_agent_worktrees/terra-b-<task-slug>

After both lines pass DeepSeek MAX QA, integration may use:

agent/integration/<task-slug>

with:

_agent_worktrees/integration-<task-slug>

Terra A and Terra B MUST work in separate Git worktrees.

Research and QA reports may be written into .agents/ov only when persistent handoff material is useful. Do not dump huge raw logs there.

After successful integration and final QA:

- remove temporary Terra worktrees
- remove temporary integration worktree
- delete temporary agent branches after their work is safely integrated
- keep the main working tree clean

Do not use old:

_worktrees/ua1
_worktrees/ua2
Union Alpha
.opencode Union agents

They are obsolete.

==================================================
TEMPORARY AGENT BRANCH COMMITS
==================================================

Terra itself NEVER commits.

However, isolated worktree integration requires temporary branch checkpoints.

After a Terra line receives:

DEEPSEEK MAX QA: PASS

DeepSeek MAX Git is allowed to create a TEMPORARY CHECKPOINT COMMIT
inside that Terra line's temporary agent branch.

Examples:

agent/terra-a/<task>
agent/terra-b/<task>

These are internal transport commits only.

They are NOT the final user-facing project commit.

They exist only so Sol High can integrate isolated worktrees safely.

Integration process:

1. Terra Medium implements in its isolated worktree.
2. DeepSeek MAX QA tests the line.
3. If FAIL:
   Terra High repairs it.
4. DeepSeek MAX retests.
5. After PASS:
   DeepSeek MAX creates a temporary checkpoint commit on that agent branch.
6. Sol High creates the integration branch.
7. Approved line commits are integrated into the integration branch.
8. DeepSeek MAX performs FINAL QA.
9. User performs manual acceptance when required.
10. After user approval:
    the integration result is SQUASHED onto the real base branch.
11. DeepSeek MAX creates ONE final user-facing commit.
12. Temporary agent worktrees and branches are deleted.

Temporary agent commits must never be pushed.

