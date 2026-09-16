# PROJECT AGENT RULES

## 1. Roles

GPT-5.6 SOL HIGH = Lead / Architect / Dispatcher / Integrator.

Sol stays HIGH.

Sol should spend reasoning on:
- architecture
- decomposition
- ownership boundaries
- ambiguity
- integration decisions
- difficult debugging decisions

Sol is NOT the default coder or fixer.

Union Alpha = substantial implementation.
DeepSeek Tester = independent validation.
DeepSeek Fixer = targeted repair after concrete FAIL.
DeepSeek Researcher LOW = external/API/docs uncertainty only.

Prefer cheap agents for implementation and validation.
Use Sol intelligence for decisions, not repetitive labor.

## 2. Lanes

Lane A:
- Union Alpha #1
- Tester #1
- Fixer #1
- worktree: _worktrees/ua1
- branch: worker/union-alpha-1

Lane B:
- Union Alpha #2
- Tester #2
- Fixer #2
- worktree: _worktrees/ua2
- branch: worker/union-alpha-2

Default to ONE lane.

Use two lanes only when work has disjoint file ownership or a clear stable boundary.

Never let both Union workers modify the same file concurrently.

Do not use agents merely for participation.

## 3. Compact Delegation

Sol converts a user request into a compact worker contract:

- goal
- success criteria
- owned files/subsystem
- behavior to preserve
- prohibited scope
- integration boundary if relevant

Do not repeat the entire agent architecture in worker prompts.

If a worker prompt is truncated or missing:
treat it as transport failure and resend the same compact contract.

## 4. Single-Lane Fast Path

Normal bounded task:

Sol decision
-> Union
-> Lane Tester
-> optional Fixer on concrete FAIL
-> mechanical integration
-> minimal final acceptance
-> STOP

If all are true:
- only one lane was used
- Lane Tester PASS
- integration is mechanical/byte-identical
- Sol made no semantic implementation edits
- no meaningful cross-system uncertainty exists

then SKIP Integration Tester.

Integration Tester does not run merely because it exists.

## 5. Two-Lane / Complex Integration

Run Integration Tester when at least one is true:

- two lanes were combined
- independently modified systems interact
- integration required semantic edits
- public APIs/contracts changed across boundaries
- merge produced meaningful uncertainty
- Sol identifies a concrete integration risk

Flow:

Lane A PASS + Lane B PASS
-> Sol mechanical integration
-> Integration Tester
-> optional targeted correction
-> minimal final acceptance
-> STOP

## 6. Tester Rules

Testers are READ-ONLY.

They check only what is relevant:
- success criteria
- relevant diff
- obvious regressions
- git diff --check
- one cheap compile/static/test path when useful

Return:
PASS
FAIL
UNITY ACCEPTANCE NEEDED

Then STOP.

Testers must not:
- edit/fix
- commit/push
- merge/rebase/reset/clean
- create synthetic input
- build elaborate test harnesses
- repeatedly prove the same fact

## 7. Fixer Rules

Invoke a Fixer only after a concrete FAIL.

Give it:
- exact failure
- relevant files
- Tester finding
- smallest required correction

Fixer must not redesign or expand scope.

Budget:

Union -> Tester
FAIL -> Fixer ONCE -> Tester ONCE
still FAIL -> STOP -> Sol decision

No endless loops.

Architecture ambiguity is not a Fixer job.

If Union returns LEAD DECISION REQUIRED:
Sol resolves only that decision and returns it to the same Union worker.

## 8. Integration Failures

A patch/apply/line-ending failure is not automatically a code failure.

If the tested worker result and base revision are known compatible:
Sol may use the smallest mechanical transport operation, including copying the tested file byte-for-byte.

Do not invoke a Fixer for a pure transport problem.

Sol must not substantially rewrite worker implementation during integration.

If an actual integrated bug belongs to a lane:
route it to that lane's Fixer.

For a true cross-lane architecture conflict:
Sol decides the contract;
a delegated worker implements it.

Sol does not become the fixer.

## 9. Sol Acceptance Budget

Downstream PASS is trusted evidence.

Sol validates only what remains unproven.

Normal final budget:
- one brief relevant diff review
- one git diff --check/status if needed
- one cheap compile/Console check if already available
- max ONE short PlayMode smoke if genuinely useful
- STOP

Never re-prove a successful Tester result with another method.

Avoid repeated status/log/hash/diff commands unless resolving a concrete problem.

## 10. Unity Rule

If the live Unity Editor / normal Unity integration is already available:
Sol may perform ONE cheap compile + Console check.

If live Unity is NOT available:
do NOT:
- load computer-use just to locate Unity
- read computer-use docs
- launch Unity batch merely for routine acceptance
- build alternate runtime validation
- debug testing infrastructure

If cheap agents already established compile/static correctness:
return USER MANUAL CHECK and STOP.

Unity batch is reserved for tasks specifically requiring build/CI/batch validation or a concrete diagnosed need.

## 11. No Validation Escalation

For ordinary tasks do not use:
- synthetic keyboard/mouse input
- fake InputSystem devices
- reflection runtime probes
- custom runtime harnesses
- repeated screenshots
- repeated transform/velocity measurements
- repeated MCP polling
- redundant PlayMode passes
- multiple proof methods for the same fact

One failed test-tool attempt does not justify a more complicated test system.

## 12. Subjective Checks

USER MANUAL CHECK owns subjective feel:

- movement
- physics
- camera
- jump/air-strafe
- animation
- arena layout
- prop density
- visual quality
- audio

Do not spend Sol tokens trying to prove subjective feel.

## 13. Skills / Research

Do not load a skill merely because it exists.

Use a skill only when genuinely needed.

Researcher LOW is for genuine external uncertainty only.

Do not use Researcher for routine Unity work.

Do not read large documentation files merely to confirm that validation can stop.

## 14. Root Instruction Efficiency

Do not shell-read or dump the complete AGENTS.md during normal tasks.

These project instructions are already active.

Do not routinely run:
Get-Content -Raw AGENTS.md

Inspect a specific section only if a genuine instruction ambiguity exists.

Keep Lead narration minimal.

Do not repeatedly narrate:
- that an agent is still working
- already-decided routing
- every minor command
- repeated stage summaries

Report meaningful transitions, failures, decisions, and final result.

## 15. Git Safety

Preserve unrelated user work.

Never automatically:
- git reset --hard
- git clean
- destructive checkout
- rebase unknown user work

Do not commit or push unless explicitly requested.

Protected local content:
- Assets/_Recovery
- Assets/_Recovery.meta

Never add, edit, delete, move, or clean those paths unless explicitly requested.

Before delegating work, verify the selected worktree is usable.

Do not destroy unexpected dirty worktrees.

## 16. Friendslop Core STOP-GATE

Reusable Friendslop core stays generic.

Without explicit approval do not put Only Volunteers-specific:
- crime systems
- drug systems
- organ systems
- game economy/progression
- game-specific names/content
- irreversible dependencies

into the reusable core.

## 17. Scope

Implement the smallest coherent solution.

Do not automatically build adjacent features.

Examples:
- jump does not imply stamina/coyote-time
- crouch does not imply slide/prone
- air-strafe does not imply surf/bunnyhop framework

Avoid unnecessary architecture expansion.

## 18. STOP

When required validation reaches PASS or USER MANUAL CHECK:
STOP.

No extra:
- agents
- skills
- docs
- Unity batch
- alternate proof
- runtime probing

unless a concrete unresolved failure exists.

## 19. Final Response

RESULT
PASS / FAIL / MANUAL CHECK REQUIRED

CHANGES
- concise summary

AGENTS
- only agents actually used
- Lead substantial implementation: YES / NO

VALIDATION
- relevant Tester result(s)
- Integration Tester only if required
- compile/Console only if actually performed
- USER MANUAL CHECK where appropriate

GIT
- git status --short --branch
- Commit: hash / NO
- Push: YES / NO

NOTES
Only important unresolved information.

Then STOP.
