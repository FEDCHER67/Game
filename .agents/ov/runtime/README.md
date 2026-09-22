# OV Agent Runtime

Only the current OV architecture is valid.

Normal pipeline:

SOL 5.6 HIGH
    |
    +-------------------------+
    |                         |
TERRA 5.6 MEDIUM A      TERRA 5.6 MEDIUM B
    |                         |
DEEPSEEK MAX QA         DEEPSEEK MAX QA
    |                         |
FAIL                    FAIL
    |                         |
TERRA 5.6 HIGH          TERRA 5.6 HIGH
    |                         |
DEEPSEEK RETEST         DEEPSEEK RETEST
    +------------+------------+
                 |
            SOL 5.6 HIGH
             INTEGRATION
                 |
          DEEPSEEK MAX
             FINAL QA
                 |
              USER
                 |
          DEEPSEEK MAX
              COMMIT

DeepSeek MAX research runs in parallel when useful.

Two Terra workers must use separate branches and separate Git worktrees.

Branches:

agent/terra-a/<task>
agent/terra-b/<task>
agent/integration/<task>

Worktrees:

_agent_worktrees/terra-a-<task>
_agent_worktrees/terra-b-<task>
_agent_worktrees/integration-<task>

If only one coding line is required, Terra B is not created.

Quick Patch:

USER -> DEEPSEEK MAX -> DIRECT EDIT -> STOP
