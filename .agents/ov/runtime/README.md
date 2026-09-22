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

## Helper usage

Run these from any Git worktree in this repository; each helper anchors itself at that worktree's
repository root.

```powershell
# Create the Terra A worktree and task state; use -Lines 2 for Terra A and B.
.\.agents\ov\runtime\New-OVTask.ps1 -Task "my-task" -Lines 1

# After approved line checkpoint commits exist, create and cherry-pick into integration.
.\.agents\ov\runtime\New-OVIntegration.ps1 -Task "my-task"

# From the base branch, stage the reviewed integration result as a squash merge.
.\.agents\ov\runtime\Prepare-OVFinal.ps1 -Task "my-task"

# Read-only report of this worktree, agent branches, task states, and OV layout paths.
.\.agents\ov\runtime\Show-OVStatus.ps1

# After final integration/commit, safely remove only the recorded task worktrees and branches.
.\.agents\ov\runtime\Remove-OVTask.ps1 -Task "my-task"
```

`Remove-OVTask.ps1` only removes the exact worktrees and branches recorded for its task. It first
refuses dirty or unregistered worktrees, verifies every line branch is patch-preserved by
integration, and confirms the integration tree is preserved on the base result. Only then can it
force-delete those exact temporary branches; otherwise it retains the task state for safe recovery.

Quick Patch:

USER -> DEEPSEEK MAX -> DIRECT EDIT -> STOP
