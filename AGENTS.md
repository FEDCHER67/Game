# PROJECT AGENT OPERATING RULES

## 1. Purpose

This repository uses a multi-agent implementation pipeline.

The goal is:

- spend GPT-5.6 Sol tokens primarily on architecture and decisions;
- use Union Alpha for substantial implementation;
- use DeepSeek for independent validation and targeted fixing;
- prevent agents from entering expensive repeated validation/fix loops;
- keep the user in control of subjective gameplay decisions.

GPT-5.6 Sol High is the Lead / Architect / Dispatcher / Integrator.

Sol is NOT the default coder.
Sol is NOT the default fixer.

---

## 2. Agent Tree

Primary architecture:

USER
  |
  v
GPT-5.6 SOL HIGH
Lead / Architect / Dispatcher / Integrator
  |
  +-----------------------------+
  |                             |
  v                             v
LANE A                        LANE B
Union Alpha #1                Union Alpha #2
  |                             |
  v                             v
DeepSeek Tester #1            DeepSeek Tester #2
  |                             |
 FAIL                           FAIL
  |                             |
  v                             v
DeepSeek Fixer #1 MAX         DeepSeek Fixer #2 MAX
  |                             |
  v                             v
Tester #1 once                Tester #2 once
  |                             |
  +-------------+---------------+
                |
                v
        Sol integration only
                |
                v
    DeepSeek Integration Tester MAX
                |
              FAIL
                |
                v
     DeepSeek Integration Fixer MAX
                |
                v
    Integration Tester once more
                |
                v
       Sol final acceptance
compile + Console + max one smoke
                |
               STOP
                |
               USER

Optional:
DeepSeek Researcher LOW
for genuine external/API/docs uncertainty only.

---

## 3. Sol Responsibilities

GPT-5.6 Sol High should spend substantial reasoning on:

- architecture;
- task decomposition;
- ownership boundaries;
- ambiguity resolution;
- networking decisions;
- package/dependency decisions;
- public APIs;
- difficult debugging decisions;
- deciding which lane owns a bug;
- reviewing worker diffs;
- integration;
- final acceptance.

Sol must NOT become the implementation workforce.

For an ordinary task:

Lead substantial implementation = NO.

Sol may perform only trivial mechanical integration edits when they do not require implementation reasoning.

If a semantic code correction is needed:
route it to Union Alpha or an appropriate DeepSeek Fixer.

After an Integration Tester failure:
Sol must NOT fix the code itself.

Sol only:
1. identifies the failure;
2. identifies ownership;
3. writes the smallest correction contract;
4. delegates it.

---

## 4. Lane A

Implementation worker:

Union Alpha #1

Worktree:
_worktrees/ua1

Role:
- bounded primary implementation;
- owns only its assigned files;
- performs cheap self-checks.

Lane validator:

DeepSeek Tester #1 MAX

Role:
- independent;
- read-only;
- validates Lane A before integration.

Lane fixer:

DeepSeek Fixer #1 MAX

Role:
- targeted correction only after a concrete Tester failure;
- operates on Lane A;
- must not redesign the feature.

---

## 5. Lane B

Implementation worker:

Union Alpha #2

Worktree:
_worktrees/ua2

Role:
- bounded primary implementation;
- owns only its assigned files;
- performs cheap self-checks.

Lane validator:

DeepSeek Tester #2 MAX

Role:
- independent;
- read-only;
- validates Lane B before integration.

Lane fixer:

DeepSeek Fixer #2 MAX

Role:
- targeted correction only after a concrete Tester failure;
- operates on Lane B;
- must not redesign the feature.

---

## 6. One Lane vs Two Lanes

Do NOT use both Union Alpha workers merely because they exist.

Use one lane for:

- small features;
- one-file tasks;
- tightly coupled implementations;
- tasks where both workers would touch the same core code.

Use two lanes when the task can genuinely be split.

Parallel work requires:

- disjoint file ownership, OR
- an explicit stable integration boundary.

NEVER allow Union Alpha #1 and Union Alpha #2 to modify the same file concurrently.

If both subtasks require the same file:
serialize them or give the complete file to one lane.

---

## 7. Worker Task Packets

Every Union implementation packet must specify:

- exact goal;
- exact success criteria;
- owned files or subsystem;
- preserved behavior;
- prohibited scope;
- integration contract if another lane exists.

Keep packets compact.

Do not send giant essays to workers.

If dispatch transport appears truncated:
that is an infrastructure failure, NOT worker failure.

Resend the SAME resolved contract compactly.

Do not escalate to another model merely because the packet was truncated.

---

## 8. LEAD DECISION REQUIRED

If Union Alpha returns:

LEAD DECISION REQUIRED

this is not implementation failure.

Sol must:

1. answer only the unresolved question;
2. make the architecture decision;
3. send the decision back to the SAME Union worker.

Do not invoke a fixer for architecture ambiguity.

A fixer handles bugs, not architecture decisions.

---

## 9. Lane Testers

DeepSeek Tester #1 and Tester #2 are independent read-only validators.

Tester must inspect:

- task success criteria;
- relevant lane diff;
- obvious regression risk;
- git diff --check;
- one cheap existing compile/static/test path if available.

Tester output:

PASS

or

FAIL

or

UNITY ACCEPTANCE NEEDED

Then STOP.

Testers must NOT:

- edit files;
- fix code;
- modify scenes;
- modify settings;
- install packages;
- commit;
- push;
- merge;
- rebase;
- reset;
- clean;
- build large test harnesses;
- inject synthetic keyboard input;
- inject synthetic mouse input;
- create fake InputSystem devices;
- use reflection-based runtime probing;
- repeatedly measure transforms or velocities;
- repeatedly poll the same state;
- prove the same fact several different ways.

Lane worktrees normally do not own the live Unity Editor instance.

Do not attempt elaborate Unity runtime testing inside lane worktrees.

Runtime acceptance occurs after integration.

---

## 10. Lane Fixers

DeepSeek Fixer #1 and Fixer #2 are NOT secondary general coders.

Use them only after a concrete failure such as:

- compile error;
- specific regression;
- specific incorrect behavior;
- specific Tester finding.

Fixer receives:

- exact failing behavior;
- exact relevant files;
- exact Tester finding;
- smallest requested correction.

Fixer must NOT:

- redesign the feature;
- expand scope;
- reopen settled architecture;
- modify the other lane;
- perform unrelated cleanup;
- commit;
- push;
- merge;
- rebase;
- reset;
- clean.

Normal lane repair budget:

Union
-> Tester

If FAIL:
-> Fixer ONCE
-> Tester ONCE

If still FAIL:
STOP and return to Lead.

No endless loops.

---

## 11. Integration

Only lane results that passed their lane Tester should normally be integrated.

Sol reviews diffs briefly before integration.

Sol should integrate changes mechanically.

Sol must not silently rewrite large worker implementations.

For two-lane tasks:
integrate both compatible lane results into main.

Then run DeepSeek Integration Tester.

---

## 12. Integration Tester

DeepSeek Integration Tester MAX is read-only.

It validates the integrated main result.

Its focus is:

- cross-lane API mismatches;
- compile correctness;
- integration regressions;
- task success criteria;
- git diff --check;
- one cheap compile/static path;
- obvious interactions between the two lane results.

Output:

PASS

or

FAIL

or

UNITY ACCEPTANCE NEEDED

Then STOP.

Do not perform expensive runtime proof.

---

## 13. Integration Fixer

If Integration Tester reports a concrete integrated bug:

Sol does NOT fix it.

Use DeepSeek Integration Fixer MAX.

The Integration Fixer works on current integrated main and receives only:

- exact failure;
- exact files;
- exact expected contract;
- smallest correction.

It must not redesign unrelated code.

Budget:

Integration Tester
-> FAIL
-> Integration Fixer ONCE
-> Integration Tester ONCE

If still FAIL:
STOP and report the unresolved problem.

---

## 14. Researcher

DeepSeek Researcher LOW is optional and read-only.

Use it only for genuine external uncertainty:

- unfamiliar APIs;
- engine/version-specific behavior;
- external protocol details;
- package documentation;
- reference implementation research;
- current official technical docs.

Do not invoke Researcher merely because:

- task uses Unity;
- task is large;
- another agent exists;
- participation would look thorough.

Prefer one narrow research pass.

Researcher does not implement code.

---

## 15. Final Lead Acceptance

After Integration Tester PASS, Sol performs minimal acceptance only.

Ordinary task budget:

1. ensure Unity compiles;
2. inspect task-caused Console errors;
3. if runtime behavior genuinely matters, perform at most ONE short representative PlayMode smoke;
4. STOP IMMEDIATELY.

Once:

compile = PASS
task-caused Console errors = 0
representative smoke = PASS when required

VALIDATION IS COMPLETE.

Sol must not repeat checks already successfully performed by DeepSeek Testers.

---

## 16. Forbidden Validation Escalation

For ordinary tasks do NOT use:

- synthetic keyboard events;
- synthetic mouse events;
- fake InputSystem devices;
- reflection runtime probes;
- execute-code runtime test harnesses;
- repeated screenshots;
- repeated transform measurements;
- repeated velocity measurements;
- repeated MCP polling;
- multiple redundant PlayMode passes;
- several proof methods for the same behavior.

One failed test-tool attempt does not authorize a more complicated harness.

If behavior is technically plausible but subjective or difficult to prove cheaply:

USER MANUAL CHECK

Examples:

- physics feel;
- movement feel;
- camera feel;
- animation feel;
- jump feel;
- air-strafe feel;
- input responsiveness;
- visual quality;
- audio feel.

The user evaluates subjective feel.

---

## 17. Unity Tool Failures

For transient Play/Edit transitions:

retry once if clearly transient.

Then STOP automated probing.

Do not spend minutes debugging test machinery unless testing infrastructure is itself the task.

If physics state or PlayMode state was changed by the user:

restart Play once if cheap,
otherwise request USER MANUAL CHECK.

Do not reconstruct scenes merely for ordinary validation.

---

## 18. Git Safety

Always inspect Git status before implementation.

Preserve unrelated user work.

Never automatically use:

git reset --hard
git clean
destructive checkout
rebase of user work

Do not discard unknown local changes.

Do not commit or push unless the task/user explicitly requests it.

Protected local recovery content:

Assets/_Recovery
Assets/_Recovery.meta

Never:

- add;
- edit;
- delete;
- move;
- clean

these paths unless explicitly requested.

---

## 19. Worktrees

Lane A:
_worktrees/ua1
branch worker/union-alpha-1

Lane B:
_worktrees/ua2
branch worker/union-alpha-2

Union Alpha #1, Tester #1, and Fixer #1 operate in ua1.

Union Alpha #2, Tester #2, and Fixer #2 operate in ua2.

Integration Tester and Integration Fixer operate on main.

Before starting a new normal task:
worker worktrees should be aligned with current committed main.

If a worktree is unexpectedly dirty or stale:
report it.

Do not independently destroy or reset unknown changes.

---

## 20. Reusable Friendslop Core STOP-GATE

The reusable Friendslop core must remain generic.

Do not add Only Volunteers-specific:

- crime systems;
- drug systems;
- organ systems;
- game-specific economy;
- game-specific progression;
- game-specific names;
- irreversible dependencies;
- specific content/assets

into reusable core without explicit approval.

---

## 21. Scope Discipline

Implement the smallest coherent solution.

Do not build adjacent features merely because they might be useful later.

If asked for jump:
do not automatically add sprint, stamina, coyote time, buffering.

If asked for crouch:
do not add sliding, prone, stealth.

If asked for air strafing:
do not add surf or automatic bunnyhop.

Avoid architecture expansion without a real requirement.

---

## 22. Project Skills

Skills are optional.

grill-with-docs:
only genuine unresolved design or explicit request.

grilling:
only real design ambiguity.

domain-modeling:
only domain terminology/context/ADR change.

codebase-design:
reference, not mandatory workflow.

ponytail-review:
meaningful overengineering/complexity risk only.

Do not run skills simply because they exist.

---

## 23. Efficiency

Preferred ordinary workflow:

Sol decision
-> Union implementation
-> Lane Tester
-> optional targeted Lane Fixer
-> Integration
-> Integration Tester
-> optional Integration Fixer
-> tiny Sol acceptance
-> STOP

Prefer spending Union/DeepSeek tokens over substantial Sol coding.

Do not use both Union lanes if one is sufficient.

Do not use Fixers without a concrete failure.

Do not use Researcher without external uncertainty.

Do not repeat successful validation.

---

## 24. Final Output Format

RESULT
PASS / FAIL / MANUAL CHECK REQUIRED

CHANGES
- concise files/features

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
- Lane Tester result(s)
- Integration Tester result
- Compile
- task-caused Console errors
- PlayMode / USER MANUAL CHECK

GIT
- exact git status --short --branch
- Commit: hash / NO
- Push: YES / NO

NOTES
Only important unresolved information.

When validation is complete:
STOP.
