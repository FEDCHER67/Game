# PROJECT AGENT OPERATING RULES

## 1. Core Architecture

GPT-5.6 SOL HIGH is the Lead / Architect / Dispatcher / Integrator.

Sol stays HIGH.

Sol should spend its intelligence on:
- architecture
- task decomposition
- ownership boundaries
- ambiguity resolution
- integration decisions
- difficult debugging decisions

Sol is NOT the default coder.
Sol is NOT the default fixer.
Sol must not become the implementation workforce.

Substantial implementation belongs to Union Alpha.

Validation and targeted repair belong primarily to DeepSeek.

---

## 2. Normal Agent Tree

Lane A:

Union Alpha #1
-> DeepSeek Tester #1
-> DeepSeek Fixer #1 only on concrete FAIL
-> Tester #1 once more

Lane B:

Union Alpha #2
-> DeepSeek Tester #2
-> DeepSeek Fixer #2 only on concrete FAIL
-> Tester #2 once more

Optional:

DeepSeek Researcher LOW
only for genuine external/API/docs uncertainty.

Integration Tester is conditional.
Integration Fixer is conditional.

---

## 3. Do Not Re-Read Root Instructions

The root AGENTS.md instructions are already supplied to the Lead.

During normal tasks Sol must NOT shell-read, dump, or re-ingest the complete AGENTS.md.

Do not routinely run:

Get-Content -Raw AGENTS.md

Only inspect a specific section if a genuine instruction ambiguity exists.

Do not waste context/tokens repeatedly reading instructions that are already active.

---

## 4. Compact Task Contracts

User prompts do not need to repeat the entire agent architecture.

Sol should convert the user request into a compact worker contract containing only:

- goal
- success criteria
- owned files/subsystem
- behavior to preserve
- prohibited scope
- integration boundary if needed

Keep worker packets compact.

Do not send giant essays unless complexity genuinely requires it.

---

## 5. One Lane vs Two Lanes

Do NOT use both implementation lanes merely because they exist.

Use one lane for:

- small features
- scene-only work
- one-file tasks
- tightly coupled changes
- work where both agents would need the same file

Use two lanes only when work can be genuinely split with:

- disjoint file ownership, OR
- explicit stable integration boundaries

NEVER allow both Union workers to modify the same file concurrently.

---

## 6. Single-Lane FAST PATH

Default workflow for a normal bounded one-lane task:

Sol decision
-> Union Alpha
-> Lane Tester
-> optional Lane Fixer only on concrete FAIL
-> mechanical integration
-> minimal final acceptance
-> STOP

If ALL are true:

- exactly one implementation lane was used
- Lane Tester returned PASS
- integration is byte-for-byte or otherwise purely mechanical
- Sol made no semantic implementation edits
- no cross-system integration uncertainty exists

then:

SKIP Integration Tester.

Do not run Integration Tester merely because it exists.

This is the preferred fast path.

---

## 7. When Integration Tester IS Required

Run DeepSeek Integration Tester when at least one is true:

- two implementation lanes were combined
- multiple independently modified subsystems interact
- integration required semantic code edits
- public APIs/contracts changed across boundaries
- a merge produced meaningful uncertainty
- combined behavior has a real integration risk
- Sol explicitly identifies a concrete integration concern

Otherwise, for a clean single-lane PASS:
skip it.

---

## 8. Lane Testers

Tester #1 and Tester #2 are independent and READ-ONLY.

They validate:

- requested success criteria
- relevant diff
- obvious regressions
- git diff --check
- one cheap compile/static/test path when useful

Output:

PASS

or

FAIL

or

UNITY ACCEPTANCE NEEDED

Then STOP.

Testers must NOT:

- edit
- fix
- commit
- push
- merge
- reset
- clean
- create elaborate runtime harnesses
- inject synthetic input
- repeatedly prove the same behavior

If subjective/runtime feel cannot be cheaply proven:
return UNITY ACCEPTANCE NEEDED.

---

## 9. Lane Fixers

Fixers run ONLY after a concrete Tester FAIL.

Fixer receives:

- exact failing behavior
- exact relevant files
- exact Tester finding
- smallest correction required

Fixer must not:

- redesign architecture
- expand scope
- modify the other lane
- perform unrelated cleanup
- commit
- push
- merge
- reset
- clean

Repair budget:

Union
-> Tester

if FAIL:

Fixer ONCE
-> Tester ONCE

if still FAIL:

STOP
-> Lead decision

No endless loops.

---

## 10. LEAD DECISION REQUIRED

If Union returns:

LEAD DECISION REQUIRED

this is NOT worker failure.

Sol should:

1. resolve only the missing architecture decision
2. send the decision back to the SAME worker

Do not invoke a Fixer for architecture ambiguity.

Fixers repair concrete implementation failures.

---

## 11. Mechanical Integration

Sol may perform small mechanical integration operations.

Examples:

- apply an already-tested patch
- copy an already-tested file byte-for-byte
- merge compatible worker results
- resolve pure line-ending/transport issues

A patch/apply/line-ending failure is NOT automatically a code failure.

If base revisions are equivalent and the lane result already passed:
use the smallest safe mechanical transport method.

Do not invoke a Fixer for a pure integration transport problem.

Sol must not silently rewrite substantial worker implementation.

---

## 12. Sol Final Acceptance Budget

After downstream PASS results, Sol validates ONLY facts that remain unproven.

Normal maximum:

- one brief relevant diff review
- one git diff --check/status check if needed
- one cheap compile/Console check if already available
- max ONE short PlayMode smoke if genuinely useful
- STOP

Never re-prove facts already established by a Tester.

Do not perform several equivalent validation methods.

---

## 13. Unity Availability Rule

If the live Unity Editor / normal Unity integration is already available:

Sol may request ONE cheap compile + Console check.

If live Unity is NOT available:

DO NOT:

- load computer-use just to find Unity
- read computer-use documentation
- open large guidance documents
- launch Unity batch mode merely for routine acceptance
- build alternate validation harnesses
- spend time debugging validation infrastructure

If a Tester already produced a valid compile/static PASS:

return USER MANUAL CHECK
and STOP.

Unity batch mode is appropriate only when:

- the task itself is about build/CI/batch operation, OR
- there is a specific concrete reason beyond routine final acceptance.

---

## 14. No Validation Escalation

For ordinary tasks do NOT use:

- synthetic keyboard input
- synthetic mouse input
- fake InputSystem devices
- reflection runtime probes
- custom runtime test harnesses
- repeated screenshots
- repeated transform measurements
- repeated velocity measurements
- repeated MCP polling
- multiple redundant PlayMode runs
- multiple proof methods for the same fact

One failed test-tool attempt does not authorize a more complicated testing system.

---

## 15. Subjective Gameplay Checks

The user evaluates subjective feel.

Use USER MANUAL CHECK for things such as:

- movement feel
- physics feel
- camera feel
- jump feel
- air-strafe feel
- animation feel
- prop density
- arena layout
- visual quality
- audio feel

Do not spend Sol tokens trying to mathematically prove subjective game feel.

---

## 16. Skills and Documentation

Do not load a skill merely because it exists.

Only load a skill when it is genuinely required to complete the task.

Researcher LOW:
only genuine external/API/docs uncertainty.

Do not use Researcher for routine Unity work.

Do not load computer-use for routine final validation.

Do not read large documentation files simply to confirm that no further work is needed.

---

## 17. Minimal Lead Narration

Keep Lead narration short.

Do not repeatedly narrate:

- that an agent is still working
- the already-decided routing
- every minor command
- repeated summaries between pipeline stages
- what will happen next when nothing changed

Report only:

- meaningful state transitions
- concrete failures
- LEAD DECISION REQUIRED
- integration issues
- final result

---

## 18. Ordinary Lead Action Budget

For a normal bounded task, Sol should typically perform only:

1. one initial repo/worktree safety check
2. one routing/decomposition decision
3. one worker delegation
4. one brief worker diff review
5. mechanical integration
6. only still-required final validation
7. STOP

Avoid repeated:

- git status
- git log
- hash checks
- diff scans

unless resolving a concrete problem.

---

## 19. Worktrees

Lane A:

_worktrees/ua1
branch worker/union-alpha-1

Used by:
- Union Alpha #1
- Tester #1
- Fixer #1

Lane B:

_worktrees/ua2
branch worker/union-alpha-2

Used by:
- Union Alpha #2
- Tester #2
- Fixer #2

Before normal implementation:
the selected lane should be aligned with current committed main.

If unexpectedly dirty or stale:
report it.

Do not destroy unknown work.

---

## 20. Integration Tester

Integration Tester is READ-ONLY.

When required, it checks:

- cross-lane API compatibility
- combined regressions
- task success criteria
- compile/static correctness
- git diff --check
- obvious subsystem interactions

Output:

PASS
FAIL
UNITY ACCEPTANCE NEEDED

Then STOP.

No expensive runtime proof.

---

## 21. Integration Fixer

If Integration Tester reports a concrete implementation failure:

Sol does NOT fix it.

Use Integration Fixer only for the exact reported integration bug.

Budget:

Integration Tester
-> FAIL
-> Integration Fixer ONCE
-> Integration Tester ONCE

If still FAIL:
STOP and report.

For a pure lane-owned bug:
prefer the owning Lane Fixer.

---

## 22. Git Safety

Always preserve unrelated user work.

Never automatically use:

git reset --hard
git clean
destructive checkout
rebase of unknown user work

Do not discard unknown changes.

Do not commit or push unless explicitly requested.

Protected local recovery content:

Assets/_Recovery
Assets/_Recovery.meta

Never:

- add
- edit
- delete
- move
- clean

these paths unless explicitly requested.

---

## 23. Friendslop Core STOP-GATE

The reusable Friendslop core must remain generic.

Do not add Only Volunteers-specific:

- crime systems
- drug systems
- organ systems
- game-specific economy
- game-specific progression
- game-specific names
- irreversible dependencies
- specific game content/assets

into reusable core without explicit approval.

---

## 24. Scope Discipline

Implement the smallest coherent solution.

Do not automatically add adjacent features.

Examples:

jump != stamina/coyote-time system
crouch != slide/prone system
air-strafe != surf/bunnyhop framework

Avoid architecture expansion without a real requirement.

---

## 25. Transport Failures

If worker input appears truncated or missing:

this is infrastructure failure, not worker failure.

Resend the SAME resolved task compactly.

Do not escalate models merely because transport failed.

---

## 26. Efficiency Priority

Preferred normal workflow:

Sol decision
-> Union implementation
-> Lane Tester
-> optional Fixer
-> mechanical integration
-> conditional Integration Tester
-> tiny Sol acceptance
-> STOP

Prefer spending Union/DeepSeek tokens over substantial Sol implementation.

Do not use:
- second lane without need
- Fixer without FAIL
- Researcher without uncertainty
- Integration Tester without integration risk
- repeated validation after PASS

---

## 27. STOP Means STOP

After required validation reaches:

PASS

or

USER MANUAL CHECK

STOP.

Do not continue with:

- extra skills
- extra documentation
- Unity batch validation
- second proof method
- extra agents
- additional runtime probing

unless a concrete unresolved failure exists.

---

## 28. Final Output

RESULT
PASS / FAIL / MANUAL CHECK REQUIRED

CHANGES
- concise summary

AGENTS
- Union Alpha #1: USED / NOT USED
- Tester #1: USED / NOT USED
- Fixer #1: USED / NOT USED
- Union Alpha #2: USED / NOT USED
- Tester #2: USED / NOT USED
- Fixer #2: USED / NOT USED
- Integration Tester: USED / NOT USED
- Integration Fixer: USED / NOT USED
- Researcher: USED / NOT USED
- Lead substantial implementation: YES / NO

VALIDATION
- Lane result(s)
- Integration result if required
- compile/Console if actually required
- USER MANUAL CHECK if applicable

GIT
- git status --short --branch
- Commit: hash / NO
- Push: YES / NO

NOTES
Only unresolved important information.

Then STOP.
